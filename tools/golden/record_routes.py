#!/usr/bin/env python3
"""
Record ROUTE-level golden fixtures from the real FastAPI app.

    uv run python tools/golden/record_routes.py

Drives ``storyforge.main.app`` in-process with ``fastapi.testclient.TestClient``
(no lifespan, no uvicorn, no network) against a throw-away campaign directory.
Determinism comes from ``golden_lib`` (ScriptedRandom, frozen clock); see
tests/golden/ROUTES_README.md for the flow-file format.

Only CORE routes are covered (see docs/offline/CLIENT_BACKEND_CONTRACT.md).
Output is byte-identical between runs.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import warnings
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

warnings.filterwarnings("ignore")
os.environ.setdefault("STORYFORGE_GEMINI_API_KEY", "test-fake-key-not-real")

import golden_lib as gl  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from storyforge.api import routes_action, routes_state  # noqa: E402
from storyforge.core import character_factory as cf  # noqa: E402
from storyforge.core import state_manager as sm  # noqa: E402
from storyforge.core.models import GameState  # noqa: E402
from storyforge.encounters import enemies  # noqa: E402
from storyforge.events.bus import event_bus  # noqa: E402
from storyforge.main import app  # noqa: E402

FIXTURE_DIR = ROOT / "tests" / "golden" / "routes"
SEED_PATH = ROOT / "data" / "seeds" / "default_campaign.json"
FORMAT = "storyforge-route-flow/1"
MAIN_CAMPAIGN = "family_campaign_01"
FROZEN_MTIME = 1_700_000_000  # + index in sorted campaign-dir order


# ───────────────────────── RNG plumbing ─────────────────────────

class _RngProxy:
    """Delegates to the per-step ScriptedRandom; remembers any script failure
    (a failure inside a route would otherwise be swallowed into a 500)."""

    def __init__(self) -> None:
        self.current = gl.ScriptedRandom({})
        self.errors: list[str] = []

    def _wrap(self, name: str, *a: Any) -> Any:
        try:
            return getattr(self.current, name)(*a)
        except AssertionError as exc:
            self.errors.append(str(exc))
            raise

    def randint(self, a: int, b: int) -> int:
        return self._wrap("randint", a, b)

    def random(self) -> float:
        return self._wrap("random")

    def choice(self, seq: Any) -> Any:
        return self._wrap("choice", seq)

    def token_hex(self, nbytes: int | None = None) -> str:
        return self._wrap("token_hex", nbytes)


async def _narrator_stub(*_a: Any, **_k: Any) -> str:
    # POST /api/action/grid (plain move) asks Gemini for flavour text inside
    # try/except and falls back to "<name> moves to (x, y)." -- we force the
    # fallback so no AI is ever called. Flagged in every flow's "ai_stubs".
    raise RuntimeError("gemini stubbed out by record_routes.py")


async def _interpreter_stub(*_a: Any, **_k: Any) -> Any:
    raise AssertionError("a CORE flow reached the AI interpreter (freeform)")


AI_STUBS = [
    "storyforge.ai.narrator.narrate_movement -> raises; /api/action/grid uses its "
    "built-in fallback text '<name> moves to (x, y).'",
    "storyforge.ai.interpreter.interpret_freeform -> assertion if ever reached "
    "(freeform is class AI and is not recorded)",
]


@contextmanager
def _patched(proxy: _RngProxy, base: Path):
    fake_dt = SimpleNamespace(datetime=gl._FakeDatetime, timezone=gl._dt.timezone)
    fake_settings = SimpleNamespace(campaign_path=base / MAIN_CAMPAIGN)
    with mock.patch.object(enemies, "random", proxy), \
            mock.patch.object(cf, "secrets", proxy), \
            mock.patch.object(sm, "dt", fake_dt), \
            mock.patch.object(routes_state, "dt", fake_dt), \
            mock.patch.object(routes_state, "settings", fake_settings), \
            mock.patch.object(routes_action.narrator, "narrate_movement", _narrator_stub), \
            mock.patch.object(routes_action.interpreter, "interpret_freeform",
                              _interpreter_stub):
        yield


# ───────────────────────── execution ─────────────────────────

def _seed_dict() -> dict:
    return GameState.model_validate(json.loads(SEED_PATH.read_text())).model_dump(mode="json")


_SEED = _seed_dict()


def _trim(state: dict) -> dict:
    """Full state, except rooms identical to the seed's are listed by id only."""
    out = {k: v for k, v in state.items() if k != "rooms"}
    out["rooms"] = {k: v for k, v in state["rooms"].items() if v != _SEED["rooms"].get(k)}
    out["unchanged_rooms"] = sorted(k for k in state["rooms"] if k not in out["rooms"])
    return out


def _body(resp: Any) -> dict:
    try:
        return {"status": resp.status_code, "json": resp.json()}
    except ValueError:
        return {"status": resp.status_code, "text": resp.text}


def _freeze_mtimes(base: Path) -> None:
    dirs = sorted(p for p in base.iterdir() if p.is_dir() and (p / "state.json").exists())
    for i, d in enumerate(dirs):
        t = FROZEN_MTIME + i
        os.utime(d / "state.json", (t, t))


def S(name: str, method: str, path: str, json: Any = None, rng: dict | None = None,
      pre: list[str] | None = None, snap: bool | None = None,
      query: dict | None = None) -> dict:
    """Step spec. ``snap`` defaults to True for POST, False for GET."""
    return {"name": name, "method": method, "path": path, "query": query or {},
            "json": json, "rng": rng or {}, "pre": pre or [],
            "snap": (method == "POST") if snap is None else snap}


def execute(meta: dict, steps: list[dict]) -> dict:
    """Run steps against a fresh app state; return the flow document."""
    proxy = _RngProxy()
    bus_q = event_bus.subscribe()
    with tempfile.TemporaryDirectory(prefix="sf-routes-") as tmp:
        base = Path(tmp) / "campaigns"
        base.mkdir()
        # mirror main.lifespan: load saved campaign else seed (nothing saved yet)
        app.state.state_manager = sm.StateManager(
            GameState.model_validate(json.loads(SEED_PATH.read_text())),
            base / MAIN_CAMPAIGN)
        client = TestClient(app, raise_server_exceptions=False)
        recorded: list[dict] = []
        try:
            with _patched(proxy, base):
                prev = _trim(client.get("/api/state").json())
                for i, st in enumerate(steps):
                    for p in st["pre"]:
                        if p != "freeze_mtimes":
                            raise ValueError(f"unknown pre action {p}")
                        _freeze_mtimes(base)
                    proxy.current = gl.ScriptedRandom(st["rng"])
                    proxy.errors.clear()
                    kw: dict = {}
                    if st["query"]:
                        kw["params"] = st["query"]
                    if st["json"] is not None:
                        kw["json"] = st["json"]
                    resp = client.request(st["method"], st["path"], **kw)
                    where = f"{meta['flow']} step {i} ({st['name']})"
                    if proxy.errors:
                        raise RuntimeError(f"{where}: rng script failed: {proxy.errors}")
                    if proxy.current.leftover():
                        raise RuntimeError(
                            f"{where}: unconsumed rng {proxy.current.leftover()}")
                    events = []
                    while not bus_q.empty():
                        events.append(bus_q.get_nowait())
                    rec = {
                        "n": i, "name": st["name"],
                        "request": {"method": st["method"], "path": st["path"],
                                    "query": st["query"], "json": st["json"]},
                        "pre": st["pre"],
                        "rng_script": st["rng"],
                        "rng_bounds": proxy.current.randint_bounds,
                        "response": _body(resp),
                        "events": events,
                    }
                    if st["snap"]:
                        cur = _trim(client.get("/api/state").json())
                        rec["state_after"] = ({"same_as_previous": True} if cur == prev
                                              else cur)
                        prev = cur
                    recorded.append(rec)
        finally:
            event_bus.unsubscribe(bus_q)
    return {
        "format": FORMAT,
        "flow": meta["flow"],
        "description": meta["description"],
        "covers": sorted(meta["covers"]),
        "ai_stubs": AI_STUBS,
        "initial": {"seed": "data/seeds/default_campaign.json",
                    "main_campaign_dir": MAIN_CAMPAIGN,
                    "saved_campaigns": []},
        "steps": recorded,
    }


def specs_from_doc(doc: dict) -> list[dict]:
    """Rebuild executable step specs from a committed flow file (for replay)."""
    out = []
    for st in doc["steps"]:
        r = st["request"]
        out.append(S(st["name"], r["method"], r["path"], r["json"], st["rng_script"],
                     st["pre"], "state_after" in st, r["query"]))
    return out


def replay(doc: dict) -> dict:
    meta = {"flow": doc["flow"], "description": doc["description"],
            "covers": doc["covers"]}
    return execute(meta, specs_from_doc(doc))


# ───────────────────────── flow definitions ─────────────────────────

ABIL = {"STR": 8, "DEX": 15, "CON": 14, "INT": 10, "WIS": 12, "CHA": 13}
PLAYER = "godot_player"


def create_body(name: str = "Rook", slot: int = 0, **over: Any) -> dict:
    body = {"slot_index": slot, "name": name, "race": "veilborn",
            "evolution_state": "mimic", "predator_role": "stalker",
            "starting_era": "after", "abilities": dict(ABIL)}
    body.update(over)
    return body


def party_setup(snap_last: bool = True) -> list[dict]:
    """The exact request sequence the Godot client performs (UIManager +
    CreationManager) to get from a fresh campaign to EXPLORATION."""
    return [
        S("setup: join lobby", "POST", "/api/lobby/join", {"controller_id": PLAYER}, snap=False),
        S("setup: set_phase creation", "POST", "/api/lobby/set_phase",
          {"phase": "creation"}, snap=False),
        S("setup: create Rook", "POST", "/api/character/create", create_body(), snap=False),
        S("setup: start", "POST", "/api/lobby/start", {}, snap=snap_last),
    ]


def flow_boot_reads() -> tuple[dict, list[dict]]:
    meta = {"flow": "boot_reads", "covers": [
        "GET /api/state", "GET /api/revision", "GET /api/lobby/catalog",
        "GET /api/campaigns", "GET /api/enemy/room/{room_id}"],
        "description": "Client boot reads on a fresh seed campaign: state, revision, "
                       "creation catalog, (empty) campaign list, enemy listing per room."}
    steps = [
        S("fetch full state", "GET", "/api/state"),
        S("revision", "GET", "/api/revision"),
        S("creation catalog", "GET", "/api/lobby/catalog"),
        S("campaign list before any save", "GET", "/api/campaigns"),
        S("enemies in back_alley", "GET", "/api/enemy/room/back_alley"),
        S("enemies in empty room", "GET", "/api/enemy/room/central_hub"),
        S("enemies in unknown room", "GET", "/api/enemy/room/nowhere"),
    ]
    return meta, steps


def flow_lobby_slots() -> tuple[dict, list[dict]]:
    meta = {"flow": "lobby_slots", "covers": [
        "POST /api/lobby/join", "POST /api/lobby/leave", "POST /api/lobby/update_name",
        "POST /api/lobby/save_draft", "POST /api/lobby/set_phase", "POST /api/lobby/start"],
        "description": "Claim/leave slots, idempotent join, 5th player rejected, missing "
                       "controller id, name and draft updates, set_phase, premature start."}
    j = "/api/lobby/join"
    steps = [
        S("join p1", "POST", j, {"controller_id": "pad_1"}),
        S("join p1 again (idempotent)", "POST", j, {"controller_id": "pad_1"}),
        S("join p2", "POST", j, {"controller_id": "pad_2"}),
        S("join without controller_id", "POST", j, {}),
        S("join empty controller_id", "POST", j, {"controller_id": ""}),
        S("join p3", "POST", j, {"controller_id": "pad_3"}),
        S("join p4", "POST", j, {"controller_id": "pad_4"}),
        S("join p5 (all slots taken)", "POST", j, {"controller_id": "pad_5"}),
        S("leave p2", "POST", "/api/lobby/leave", {"controller_id": "pad_2"}),
        S("leave p2 again", "POST", "/api/lobby/leave", {"controller_id": "pad_2"}),
        S("leave without controller_id", "POST", "/api/lobby/leave", {}),
        S("join p5 takes freed slot", "POST", j, {"controller_id": "pad_5"}),
        S("update_name slot 0", "POST", "/api/lobby/update_name",
          {"slot_index": 0, "name": "Aria", "controller_id": "pad_1"}),
        S("update_name empty slot claims it", "POST", "/api/lobby/update_name",
          {"slot_index": 1, "name": "Bo", "controller_id": "pad_2"}),
        S("update_name bad slot", "POST", "/api/lobby/update_name",
          {"slot_index": 9, "name": "X", "controller_id": "pad_1"}),
        S("update_name too long", "POST", "/api/lobby/update_name",
          {"slot_index": 0, "name": "x" * 25, "controller_id": "pad_1"}),
        S("save_draft in LOBBY phase (slot only claimed)", "POST", "/api/lobby/save_draft",
          {"controller_id": "pad_1", "race": "veilborn", "creation_step": "race",
           "skill_proficiencies": ["stealth"]}),
        S("save_draft unknown controller", "POST", "/api/lobby/save_draft",
          {"controller_id": "ghost", "race": "veilborn"}),
        S("save_draft missing controller", "POST", "/api/lobby/save_draft", {"race": "x"}),
        S("save_draft unknown race string (stored unvalidated)", "POST",
          "/api/lobby/save_draft", {"controller_id": "pad_1", "race": "not_a_race"}),
        S("set_phase creation", "POST", "/api/lobby/set_phase", {"phase": "creation"}),
        S("set_phase invalid", "POST", "/api/lobby/set_phase", {"phase": "bogus"}),
        S("start with nobody ready", "POST", "/api/lobby/start", {}),
        S("leave everyone reverts phase", "POST", "/api/lobby/leave",
          {"controller_id": "pad_1"}),
    ]
    return meta, steps


def flow_character_creation() -> tuple[dict, list[dict]]:
    c = "/api/character/create"
    meta = {"flow": "character_creation", "covers": [
        "POST /api/lobby/join", "POST /api/lobby/set_phase", "POST /api/character/create",
        "POST /api/lobby/start", "POST /api/lobby/leave", "GET /api/state"],
        "description": "Creation end-to-end exactly as the client does it, plus validation "
                       "failures (bad array, unknown race/state, name length, slot state, "
                       "wrong phase), duplicate name (token_hex id), start/leave afterwards."}
    steps = [
        S("create before CREATION phase", "POST", c, create_body()),
        S("join", "POST", "/api/lobby/join", {"controller_id": PLAYER}),
        S("create in LOBBY phase", "POST", c, create_body()),
        S("set_phase creation", "POST", "/api/lobby/set_phase", {"phase": "creation"}),
        S("bad ability array (duplicate 15)", "POST", c,
          create_body(abilities={**ABIL, "STR": 15})),
        S("abilities not a standard-array permutation (all 10)", "POST", c,
          create_body(abilities={k: 10 for k in ABIL})),
        S("ability out of model range", "POST", c,
          create_body(abilities={**ABIL, "STR": 0})),
        S("ability missing key", "POST", c,
          create_body(abilities={k: v for k, v in ABIL.items() if k != "CHA"})),
        S("unknown race", "POST", c, create_body(race="dragonkin")),
        S("unknown evolution_state", "POST", c, create_body(evolution_state="blob")),
        S("unknown predator_role", "POST", c, create_body(predator_role="bard")),
        S("empty name", "POST", c, create_body(name="")),
        S("name too long", "POST", c, create_body(name="n" * 25)),
        S("slot_index out of range", "POST", c, create_body(slot=4)),
        S("slot not claimed", "POST", c, create_body(slot=1)),
        S("missing required keys", "POST", c, {"name": "Rook"}),
        S("create Rook (happy path)", "POST", c, create_body()),
        S("create again on a READY slot", "POST", c, create_body()),
        S("join p2", "POST", "/api/lobby/join", {"controller_id": "pad_2"}),
        S("duplicate name gets token suffix", "POST", c,
          create_body(slot=1, race="ashenborn", evolution_state="behemoth",
                      predator_role="vanguard"),
          rng={"token_hex": ["beef"]}),
        S("join p3", "POST", "/api/lobby/join",
          {"controller_id": "pad_3"}),
        S("create optional fields (era before)", "POST", c,
          create_body("Mira", 2, starting_era="before", background="void_scavenger",
                      pronouns="she/her", backstory="b", keepsake_name="Old Coin")),
        S("state after creation", "GET", "/api/state", snap=False),
        S("start game", "POST", "/api/lobby/start", {}),
        S("start again (phase is EXPLORATION)", "POST", "/api/lobby/start", {}),
        S("create after start", "POST", c, create_body("Late", 3)),
        S("join after start", "POST", "/api/lobby/join", {"controller_id": "late_pad"}),
        S("leave READY slot removes the character", "POST", "/api/lobby/leave",
          {"controller_id": "pad_3"}),
    ]
    return meta, steps


def flow_exploration() -> tuple[dict, list[dict]]:
    g = "/api/action/grid"

    def mv(x: int, y: int, actor: str = "rook", t: str = "move") -> dict:
        return {"actor_id": actor, "type": t, "target": {"x": x, "y": y}}
    meta = {"flow": "exploration", "covers": [
        "POST /api/action/grid", "POST /api/action/interact_entity",
        "POST /api/action/travel", "POST /api/lobby/set_phase"],
        "description": "Grid moves: legal near/far, onto self, blocked (wall/occupied), "
                       "out of bounds, negative coord, attack type, unknown actor (500), "
                       "wrong phase (lobby/creation/combat), interact non-adjacent / "
                       "NPC cell / generic, interact_entity NPC and unknown target."}
    steps = [
        S("move in LOBBY phase", "POST", g, mv(1, 6)),
        S("join", "POST", "/api/lobby/join", {"controller_id": PLAYER}, snap=False),
        S("set_phase creation", "POST", "/api/lobby/set_phase", {"phase": "creation"},
          snap=False),
        S("move in CREATION phase", "POST", g, mv(1, 6)),
        S("create Rook", "POST", "/api/character/create", create_body(), snap=False),
        S("start", "POST", "/api/lobby/start", {}),
        S("legal move one step", "POST", g, mv(1, 6)),
        S("legal move far (no range limit in EXPLORATION)", "POST", g, mv(15, 15)),
        S("move onto own cell", "POST", g, mv(15, 15)),
        S("move onto NPC-occupied cell", "POST", g, mv(10, 8)),
        S("out of bounds", "POST", g, mv(99, 99)),
        S("negative coordinate", "POST", g, mv(-1, 0)),
        S("attack type is v0.2", "POST", g, mv(3, 3, t="attack")),
        S("unknown action type", "POST", g, mv(3, 3, t="dance")),
        S("unknown actor", "POST", g, mv(3, 3, actor="nobody")),
        S("missing body keys", "POST", g, {"type": "move"}),
        S("interact non-adjacent", "POST", g, mv(0, 0, t="interact")),
        S("interact adjacent NPC cell (jon)", "POST", g, mv(10, 8, t="interact")),
        S("walk next to jon", "POST", g, mv(10, 9)),
        S("interact adjacent NPC cell (jon)", "POST", g, mv(10, 8, t="interact")),
        S("interact adjacent empty floor", "POST", g, mv(10, 10, t="interact")),
        S("interact_entity npc", "POST", "/api/action/interact_entity",
          {"actor_id": "rook", "target_id": "jon"}),
        S("interact_entity unknown target", "POST", "/api/action/interact_entity",
          {"actor_id": "rook", "target_id": "chest_9"}),
        S("interact_entity unknown actor, npc target", "POST",
          "/api/action/interact_entity", {"actor_id": "nobody", "target_id": "jon"}),
        S("travel to market_square", "POST", "/api/action/travel",
          {"room_id": "market_square"}),
        S("move onto wall", "POST", g, mv(0, 0)),
        S("move onto table (non-traversable)", "POST", g, mv(2, 2)),
        S("move through blocked path", "POST", g, mv(12, 6)),
        S("set_phase combat", "POST", "/api/lobby/set_phase", {"phase": "combat"}),
        S("move in COMBAT phase", "POST", g, mv(1, 2)),
        S("set_phase exploration", "POST", "/api/lobby/set_phase", {"phase": "exploration"}),
        S("move again after phase restored", "POST", g, mv(1, 2)),
    ]
    return meta, steps


def _atk(actor: str = "rook") -> dict:
    return {"actor_id": actor}


def flow_enemy_combat() -> tuple[dict, list[dict]]:
    meta = {"flow": "enemy_combat", "covers": [
        "POST /api/enemy/{enemy_id}/attack", "GET /api/enemy/room/{room_id}",
        "POST /api/action/travel"],
        "description": "Travel to back_alley, list enemies, attack bandit_01 (AC 12, hp 11) "
                       "with scripted d20/damage dice until it dies; miss, hit+counter, "
                       "crit kill; attack dead/unknown enemy and unknown/missing actor."}
    a = "/api/enemy/bandit_01/attack"
    steps = party_setup() + [
        S("travel to back_alley", "POST", "/api/action/travel", {"room_id": "back_alley"}),
        S("list enemies in back_alley", "GET", "/api/enemy/room/back_alley"),
        S("attack: miss, enemy misses", "POST", a, _atk(),
          rng={"randint": [2, 3]}),
        S("attack: hit, enemy hits back", "POST", a, _atk(),
          rng={"randint": [15, 3, 18, 2]}),
        S("attack unknown enemy", "POST", "/api/enemy/ghost_99/attack", _atk()),
        S("attack with unknown actor", "POST", a, _atk("nobody")),
        S("attack without actor_id", "POST", a, {}),
        S("attack enemy in another room (no room check)", "POST",
          "/api/enemy/ghoul_01/attack", _atk(), rng={"randint": [1, 1]}),
        S("attack: hit that kills", "POST", a, _atk(),
          rng={"randint": [18, 4]}),
        S("list enemies after kill", "GET", "/api/enemy/room/back_alley"),
        S("attack dead enemy", "POST", a, _atk()),
    ]
    return meta, steps


def flow_world_travel() -> tuple[dict, list[dict]]:
    t = "/api/action/travel"
    g = "/api/action/grid"
    meta = {"flow": "world_travel", "covers": [
        "POST /api/action/travel", "POST /api/action/grid", "GET /api/state"],
        "description": "Fast travel (known/unknown/same room, with and without characters) "
                       "and door-interact room transition from market_square to store_01."}
    steps = [
        S("travel in LOBBY with no characters", "POST", t, {"room_id": "crossroads"}),
        S("travel to unknown room", "POST", t, {"room_id": "atlantis"}),
        S("travel missing room_id", "POST", t, {}),
    ] + party_setup(snap_last=False) + [
        S("travel to market_square", "POST", t, {"room_id": "market_square"}),
        S("travel to same room (re-spawns party)", "POST", t, {"room_id": "market_square"}),
        S("walk next to the store door", "POST", g,
          {"actor_id": "rook", "type": "move", "target": {"x": 5, "y": 8}}),
        S("interact door (5,9): room transition", "POST", g,
          {"actor_id": "rook", "type": "interact", "target": {"x": 5, "y": 9}}),
        S("travel to ironhold_keep", "POST", t, {"room_id": "ironhold_keep"}),
        S("travel to central_hub", "POST", t, {"room_id": "central_hub"}),
    ]
    return meta, steps


def flow_campaigns() -> tuple[dict, list[dict]]:
    meta = {"flow": "campaigns", "covers": [
        "GET /api/campaigns", "POST /api/campaigns/new", "POST /api/campaigns/load",
        "POST /api/lobby/join", "GET /api/state"],
        "description": "Persistence through real files in a temp dir: first commit creates "
                       "the main save, new campaign swaps the live state, list (mtimes "
                       "frozen), load back, unknown id, path traversal."}
    steps = [
        S("join (first commit writes main save)", "POST", "/api/lobby/join",
          {"controller_id": "pad_1"}),
        S("new campaign", "POST", "/api/campaigns/new"),
        S("join in the new campaign", "POST", "/api/lobby/join",
          {"controller_id": "pad_9"}),
        S("list campaigns", "GET", "/api/campaigns", pre=["freeze_mtimes"]),
        S("load main campaign", "POST", "/api/campaigns/load",
          {"campaign_id": MAIN_CAMPAIGN}),
        S("state after load", "GET", "/api/state", snap=False),
        S("load unknown campaign", "POST", "/api/campaigns/load",
          {"campaign_id": "campaign_20990101_000000"}),
        S("load path traversal", "POST", "/api/campaigns/load", {"campaign_id": "../x"}),
        S("load '.' (base dir)", "POST", "/api/campaigns/load", {"campaign_id": "."}),
        S("load without campaign_id", "POST", "/api/campaigns/load", {}),
    ]
    return meta, steps


def flow_paradox_time() -> tuple[dict, list[dict]]:
    meta = {"flow": "paradox_time", "covers": [
        "POST /api/state/trigger_paradox", "POST /api/time/sync", "GET /api/revision"],
        "description": "time/sync sets NPC target_position from schedules (jon has hours "
                       "8/12/18) and bumps revision only on change; trigger_paradox "
                       "transforms 'before'-era characters."}
    ts = "/api/time/sync"
    steps = [
        S("time sync hour 6 (no schedule hit)", "POST", ts,
          {"day": 1, "hour": 6, "minute": 0}),
        S("time sync hour 8 (jon scheduled)", "POST", ts, {"day": 1, "hour": 8, "minute": 0}),
        S("time sync hour 8 again (no change)", "POST", ts,
          {"day": 1, "hour": 8, "minute": 30}),
        S("time sync hour 12", "POST", ts, {"day": 1, "hour": 12, "minute": 0}),
        S("time sync bad body", "POST", ts, {"day": 1}),
        S("revision", "GET", "/api/revision"),
        S("join", "POST", "/api/lobby/join", {"controller_id": PLAYER}, snap=False),
        S("set_phase creation", "POST", "/api/lobby/set_phase", {"phase": "creation"},
          snap=False),
        S("create Rook (before era)", "POST", "/api/character/create",
          create_body(starting_era="before"), snap=False),
        S("start", "POST", "/api/lobby/start", {}),
        S("trigger paradox", "POST", "/api/state/trigger_paradox"),
        S("trigger paradox again (nobody left to transform)", "POST",
          "/api/state/trigger_paradox"),
    ]
    return meta, steps


FLOWS = [flow_boot_reads, flow_lobby_slots, flow_character_creation, flow_exploration,
         flow_enemy_combat, flow_world_travel, flow_campaigns, flow_paradox_time]


def build_all() -> dict[str, str]:
    """{relative filename: text} for every flow (also used by the pytest re-record)."""
    out = {}
    for fn in FLOWS:
        meta, steps = fn()
        doc = execute(meta, steps)
        out[f"{doc['flow']}.json"] = gl.dumps(doc)
    return out


def main() -> int:
    files = build_all()
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    for p in FIXTURE_DIR.glob("*.json"):
        if p.name not in files:
            p.unlink()
    for name, text in files.items():
        (FIXTURE_DIR / name).write_text(text)
    total = sum(len(t.encode()) for t in files.values())
    print(f"wrote {len(files)} flow files, {total} bytes")
    for name, text in sorted(files.items()):
        print(f"  {name}: {len(text.encode())} bytes, {len(json.loads(text)['steps'])} steps")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
