"""
Shared runner for the golden-fixture recorder and the pytest replay.

Both the recorder (record_fixtures.py) and tests/test_golden.py call
``run_case`` so a fixture can only pass if the *Python implementation*,
driven with the recorded inputs and scripted RNG, reproduces ``expected``.

Nothing here edits src/: time, RNG, persistence and the event bus are
patched only for the duration of ``run_case``.
"""
from __future__ import annotations

import asyncio
import dataclasses
import datetime as _dt
import json
import os
import warnings
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable
from unittest import mock

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
os.environ.setdefault("STORYFORGE_GEMINI_API_KEY", "test-fake-key-not-real")

from storyforge.core import character_factory as cf  # noqa: E402
from storyforge.core import grid, rules, state_manager as sm, validators  # noqa: E402
from storyforge.core.models import (  # noqa: E402
    AbilityScores, Cell, CharacterCreationRequest, CharacterSheet, Coord,
    EnemySheet, EvolutionaryState, GameState, GridAction,
    PredatorRole, Race, Room, StateDiff, TurnPhase,
)
from storyforge.encounters import enemies  # noqa: E402

# Fixed wall-clock used for every NarrativeEntry timestamp.
FROZEN_NOW = _dt.datetime(2026, 1, 1, 12, 0, 0, tzinfo=_dt.timezone.utc)
FROZEN_ISO = FROZEN_NOW.isoformat()

RNG_KEYS = ("random", "randint", "choice_index", "token_hex")


# ─────────────────────── JSON formatting ───────────────────────

INLINE_LIMIT = 640


def _inline(o: Any) -> str:
    if isinstance(o, dict):
        return "{" + ", ".join(
            f"{json.dumps(k)}: {_inline(v)}" for k, v in sorted(o.items())) + "}"
    if isinstance(o, list):
        return "[" + ", ".join(_inline(v) for v in o) + "]"
    return json.dumps(o)


def _fmt(o: Any, level: int) -> str:
    pad = "  " * level
    if not isinstance(o, (dict, list)) or not o:
        return _inline(o)
    inline = _inline(o)
    if len(inline) <= INLINE_LIMIT:
        return inline
    if isinstance(o, dict):
        body = ",\n".join(
            f"{pad}  {json.dumps(k)}: {_fmt(v, level + 1)}"
            for k, v in sorted(o.items()))
        return "{\n" + body + "\n" + pad + "}"
    parts = [_fmt(v, level + 1) for v in o]
    if all("\n" not in p and len(p) <= 60 for p in parts):
        # pack many tiny elements (grid cells) per line, wrapped at ~120 cols
        lines, cur = [], ""
        for p in parts:
            if cur and len(pad) + 2 + len(cur) + len(p) + 2 > 120:
                lines.append(cur)
                cur = ""
            cur = f"{cur}, {p}" if cur else p
        lines.append(cur)
        return "[\n" + ",\n".join(f"{pad}  {ln}" for ln in lines) + "\n" + pad + "]"
    body = ",\n".join(f"{pad}  {p}" for p in parts)
    return "[\n" + body + "\n" + pad + "]"


def dumps(obj: Any) -> str:
    """Deterministic JSON: sorted keys, 2-space indent; any object/array whose
    compact form is <= INLINE_LIMIT chars (cells, coords, cell rows, rng lists) is
    collapsed onto one line."""
    return _fmt(obj, 0) + "\n"


# ─────────────────────── Scripted RNG ───────────────────────

class ScriptedRandom:
    """Stand-in for ``random`` / ``secrets``. Pops values from the script and
    records the (lo, hi) bounds of every randint call."""

    def __init__(self, script: dict | None) -> None:
        script = script or {}
        self._q = {k: list(script.get(k, [])) for k in RNG_KEYS}
        self.randint_bounds: list[list[int]] = []

    def _pop(self, key: str) -> Any:
        if not self._q[key]:
            raise AssertionError(f"rng script exhausted for '{key}'")
        return self._q[key].pop(0)

    def randint(self, a: int, b: int) -> int:
        v = self._pop("randint")
        if not a <= v <= b:
            raise AssertionError(f"scripted randint {v} outside [{a},{b}]")
        self.randint_bounds.append([a, b])
        return v

    def random(self) -> float:
        return self._pop("random")

    def choice(self, seq: Any) -> Any:
        return seq[self._pop("choice_index")]

    def token_hex(self, nbytes: int | None = None) -> str:
        return self._pop("token_hex")

    def leftover(self) -> dict[str, list]:
        return {k: v for k, v in self._q.items() if v}


class _FakeDatetime(_dt.datetime):
    @classmethod
    def now(cls, tz=None):  # type: ignore[override]
        return FROZEN_NOW


class _StubBus:
    async def publish(self, message: dict) -> None:
        return None


class _StubSnapshot:
    @staticmethod
    def save(campaign_dir: Any, state: Any) -> None:
        return None


@contextmanager
def patched(rng: ScriptedRandom):
    fake_dt = SimpleNamespace(datetime=_FakeDatetime, timezone=_dt.timezone)
    with mock.patch.object(enemies, "random", rng), \
            mock.patch.object(cf, "secrets", rng), \
            mock.patch.object(sm, "snapshot", _StubSnapshot), \
            mock.patch.object(sm, "event_bus", _StubBus()), \
            mock.patch.object(sm, "dt", fake_dt):
        yield


# ─────────────────────── Handlers ───────────────────────

def _j(model: Any) -> Any:
    return model.model_dump(mode="json")


def _room(d: dict) -> Room:
    return Room.model_validate(d)


def _coord(d: dict) -> Coord:
    return Coord.model_validate(d)


def _state(d: dict) -> GameState:
    return GameState.model_validate(d)


def _jsonify(o: Any) -> Any:
    if hasattr(o, "model_dump"):
        return _j(o)
    if dataclasses.is_dataclass(o):
        return dataclasses.asdict(o)
    return o


def _h_grid(fn: str, i: dict) -> Any:
    if fn == "cell_index":
        return grid.cell_index(_room(i["room"]), _coord(i["coord"]))
    if fn == "get_cell":
        return _j(grid.get_cell(_room(i["room"]), _coord(i["coord"])))
    if fn == "set_cell":
        room = _room(i["room"])
        grid.set_cell(room, _coord(i["coord"]), Cell.model_validate(i["cell"]))
        return {"room": _j(room)}
    if fn == "in_bounds":
        return grid.in_bounds(_room(i["room"]), _coord(i["coord"]))
    if fn == "chebyshev_distance":
        return grid.chebyshev_distance(_coord(i["a"]), _coord(i["b"]))
    if fn == "feet_between":
        return grid.feet_between(_coord(i["a"]), _coord(i["b"]))
    if fn == "is_traversable":
        return grid.is_traversable(Cell.model_validate(i["cell"]))
    if fn == "movement_cost_feet":
        return grid.movement_cost_feet(Cell.model_validate(i["cell"]))
    if fn == "line_coords":
        return [_j(c) for c in grid.line_coords(_coord(i["a"]), _coord(i["b"]))]
    if fn == "path_is_clear":
        return grid.path_is_clear(
            _room(i["room"]), _coord(i["start"]), _coord(i["end"]))
    raise KeyError(fn)


def _h_rules(fn: str, i: dict) -> Any:
    state = _state(i["state"])
    char = state.characters[i["char_id"]]
    verdict = rules.check_grid_action(
        state, char, GridAction.model_validate(i["action"]))
    return {"ok": verdict.ok, "reason": verdict.reason}


def _h_validators(fn: str, i: dict) -> Any:
    state = _state(i["state"])
    safe, rejections = validators.sanitize(
        state, StateDiff.model_validate(i["diff"]))
    return {"diff": _j(safe), "rejections": rejections}


def _build_kwargs(i: dict) -> dict:
    kw = dict(i)
    gs = _state(kw.pop("game_state"))
    kw["race"] = Race(kw["race"])
    kw["state"] = EvolutionaryState(kw["state"])
    kw["role"] = PredatorRole(kw["role"])
    kw["abilities"] = AbilityScores.model_validate(kw["abilities"])
    return {**kw, "game_state": gs}


def _h_character_factory(fn: str, i: dict) -> Any:
    if fn == "build_character":
        return _j(cf.build_character(**_build_kwargs(i)))
    if fn == "is_valid_standard_array":
        return cf.is_valid_standard_array(AbilityScores.model_validate(i["abilities"]))
    if fn == "generate_char_id":
        return cf.generate_char_id(i["name"], set(i["existing"]))
    if fn == "find_starting_position":
        return _j(cf.find_starting_position(_state(i["state"])))
    if fn == "build_race_enemy":
        return _j(cf.build_race_enemy(
            i["enemy_id"], Race(i["race"]), EvolutionaryState(i["ev_state"]),
            i["room_id"], _coord(i["position"]),
            name_override=i.get("name_override"), xp_reward=i.get("xp_reward")))
    raise KeyError(fn)


def _h_enemies(fn: str, i: dict) -> Any:
    if fn == "resolve_player_attack":
        return _jsonify(enemies.resolve_player_attack(
            CharacterSheet.model_validate(i["attacker"]),
            EnemySheet.model_validate(i["target"])))
    if fn == "resolve_enemy_attack":
        return _jsonify(enemies.resolve_enemy_attack(
            EnemySheet.model_validate(i["enemy"]),
            CharacterSheet.model_validate(i["target"])))
    if fn == "_roll_dice":
        return enemies._roll_dice(i["notation"])
    if fn == "_mod":
        return enemies._mod(i["score"])
    if fn == "_weapon_dice":
        return enemies._weapon_dice(CharacterSheet.model_validate(i["char"]))
    raise KeyError(fn)


def _h_state_manager(fn: str, i: dict) -> Any:
    args = i["args"]
    state = _state(i["state"])

    async def go() -> Any:
        mgr = sm.StateManager(state, Path("campaign-not-used"))
        if fn == "set_phase":
            ret = await mgr.set_phase(TurnPhase(args["phase"]))
        elif fn == "attack_enemy":
            ret = await mgr.attack_enemy(args["attacker_id"], args["enemy_id"])
        elif fn == "fast_travel":
            ret = await mgr.fast_travel(args["room_id"])
        elif fn == "transition_room":
            ret = await mgr.transition_room(args["target_room_id"])
        elif fn == "apply_grid_action":
            ret = await mgr.apply_grid_action(
                mgr.get_character(args["char_id"]),
                GridAction.model_validate(args["action"]))
        elif fn == "apply_diff":
            ret = await mgr.apply_diff(StateDiff.model_validate(args["diff"]))
        elif fn == "append_narration":
            ret = await mgr.append_narration(
                args["actor_id"], args["kind"], args["text"])
        elif fn == "claim_slot":
            ret = await mgr.claim_slot(controller_id=args["controller_id"])
        elif fn == "update_slot_name":
            ret = await mgr.update_slot_name(
                slot_index=args["slot_index"], name=args["name"],
                controller_id=args["controller_id"])
        elif fn == "save_draft":
            ret = await mgr.save_draft(
                controller_id=args["controller_id"], patch=args["patch"])
        elif fn == "release_slot":
            ret = await mgr.release_slot(controller_id=args["controller_id"])
        elif fn == "create_character":
            ret = await mgr.create_character(
                CharacterCreationRequest.model_validate(args["request"]))
        elif fn == "start_exploration":
            ret = await mgr.start_exploration()
        elif fn == "trigger_paradox":
            ret = await mgr.trigger_paradox()
        elif fn == "get_character":
            ret = _j(mgr.get_character(args["char_id"]))
        else:
            raise KeyError(fn)
        return ret

    result = asyncio.run(go())
    return {"result": result, "state": _j(state)}


HANDLERS: dict[str, Callable[[str, dict], Any]] = {
    "grid": _h_grid,
    "rules": _h_rules,
    "validators": _h_validators,
    "character_factory": _h_character_factory,
    "enemies": _h_enemies,
    "state_manager": _h_state_manager,
}


def run_case(module: str, function: str, inputs: dict, rng_script: dict | None
             ) -> tuple[dict, ScriptedRandom]:
    """Execute one case. Returns ({"expected": ...} | {"raises":..,"message":..}, rng)."""
    rng = ScriptedRandom(rng_script)
    with patched(rng), warnings.catch_warnings():
        # quirk cases setattr() unvalidated values onto pydantic models
        warnings.simplefilter("ignore")
        try:
            out = HANDLERS[module](function, inputs)
        except Exception as exc:  # noqa: BLE001 - recorded as an outcome
            return {"raises": type(exc).__name__, "message": str(exc)}, rng
    return {"expected": out}, rng
