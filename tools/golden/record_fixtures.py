#!/usr/bin/env python3
"""
Record golden fixtures from the Python backend.

    uv run python tools/golden/record_fixtures.py

Output is deterministic (sorted keys, fixed layout, frozen clock, scripted
RNG), so running it twice yields byte-identical files. See
tests/golden/README.md for the fixture format.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

import golden_lib as gl  # noqa: E402
from storyforge.core import character_factory as cf  # noqa: E402
from storyforge.core.models import (  # noqa: E402
    Coord, Era, GameState, SlotStatus, TerrainKind, TurnPhase,
)

FIXTURE_DIR = ROOT / "tests" / "golden" / "fixtures"
SEED_PATH = ROOT / "data" / "seeds" / "default_campaign.json"

CASES: list[dict] = []


def case(module: str, function: str, name: str, inputs: dict,
         rng: dict | None = None, err: str | None = None) -> None:
    CASES.append({"module": module, "function": function,
                  "case": f"{function}__{name}", "inputs": inputs,
                  "rng": rng or {}, "err": err})


# ─────────────────────── builders ───────────────────────

_TERRAIN = {".": "floor", "#": "wall", "D": "door", "~": "difficult",
            "!": "hazard", "P": "pillar", "T": "table"}


def mk_room(rid: str, rows: list[str], exits: dict | None = None,
            occ: dict | None = None) -> dict:
    occ = occ or {}
    cells = []
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            cells.append({"terrain": _TERRAIN[ch],
                          "occupant_id": occ.get(f"{x},{y}")})
    return {"id": rid, "name": rid.title(), "width": len(rows[0]),
            "height": len(rows), "cells": cells,
            "description": "test room", "exits": exits or {}}


def cd(x: int, y: int) -> dict:
    return {"x": x, "y": y}


STD_PERMS = [
    dict(STR=15, DEX=14, CON=13, INT=12, WIS=10, CHA=8),
    dict(STR=8, DEX=15, CON=14, INT=10, WIS=12, CHA=13),
    dict(STR=10, DEX=12, CON=15, INT=13, WIS=14, CHA=8),
    dict(STR=12, DEX=8, CON=13, INT=15, WIS=14, CHA=10),
    dict(STR=13, DEX=10, CON=8, INT=14, WIS=15, CHA=12),
    dict(STR=14, DEX=13, CON=12, INT=8, WIS=10, CHA=15),
]


def mini_state(rows: list[str] | None = None, phase: str = "exploration") -> dict:
    rows = rows or ["########", "#......#", "#......#", "#......#", "#......#",
                    "#......#", "#......#", "########"]
    return {"campaign_id": "mini", "current_room_id": "mini", "phase": phase,
            "rooms": {"mini": mk_room("mini", rows)}, "revision": 0}


def place(st: GameState, cid: str, x: int, y: int) -> None:
    room = st.rooms[st.current_room_id]
    ch = st.characters[cid]
    room.cells[ch.position.y * room.width + ch.position.x].occupant_id = None
    ch.position = Coord(x=x, y=y)
    room.cells[y * room.width + x].occupant_id = cid


def load_base() -> GameState:
    """Trimmed seed: only back_alley + market_square, bandit_01 + thug_01."""
    seed = json.loads(SEED_PATH.read_text())
    keep_rooms = {"back_alley", "market_square"}  # market_square dropped per-case by base()
    keep_enemies = {"bandit_01", "thug_01"}
    seed["rooms"] = {k: v for k, v in seed["rooms"].items() if k in keep_rooms}
    seed["enemies"] = {k: v for k, v in seed["enemies"].items() if k in keep_enemies}
    seed["npcs"] = {}
    seed["characters"] = {}
    seed["narrative_log"] = []
    seed["current_room_id"] = "back_alley"
    seed["phase"] = "exploration"
    seed["revision"] = 1
    seed.pop("world_name", None)
    st = GameState.model_validate(seed)
    for cid, race, es, role, ab in [
        ("alpha", "ironfast", "behemoth", "vanguard", STD_PERMS[0]),
        ("beta", "veilborn", "phantom", "stalker", STD_PERMS[1]),
    ]:
        sheet = cf.build_character(
            char_id=cid, name=cid.title(), player=f"pad_{cid}",
            race=cf.Race(race), state=cf.EvolutionaryState(es),
            role=cf.PredatorRole(role), abilities=cf.AbilityScores(**ab),
            game_state=st)
        st.characters[cid] = sheet
        room = st.rooms[st.current_room_id]
        room.cells[sheet.position.y * room.width + sheet.position.x].occupant_id = cid
    for ch in st.characters.values():          # trim long flavour text (size only)
        # copy first: build_character shares the module-level RACES/ROLES items
        ch.inventory = [i.model_copy(update={"notes": None}) for i in ch.inventory]
    for en in st.enemies.values():
        en.description = ""
    for rm in st.rooms.values():
        rm.description = "trimmed"
    place(st, "beta", 9, 1)   # keep beta out of alpha's straight-line paths
    return st


_BASE = load_base()


def base(tweak=None, two_rooms=False, **top) -> dict:
    """Deep copy of the trimmed base state (as JSON), optionally tweaked.
    market_square is only kept when two_rooms=True (room transitions)."""
    st = _BASE.model_copy(deep=True)
    if not two_rooms:
        del st.rooms["market_square"]
    for k, v in top.items():
        setattr(st, k, v)
    if tweak:
        tweak(st)
    return st.model_dump(mode="json")


def setcell(st: GameState, x: int, y: int, terrain=None, occ="keep") -> None:
    room = st.rooms[st.current_room_id]
    c = room.cells[y * room.width + x]
    if terrain is not None:
        c.terrain = TerrainKind(terrain)
    if occ != "keep":
        c.occupant_id = occ


def bare(**over) -> dict:
    """Character JSON from the base state with overrides."""
    d = _BASE.characters["alpha"].model_dump(mode="json")
    d.update(over)
    return d


def enemy(**over) -> dict:
    d = _BASE.enemies["bandit_01"].model_dump(mode="json")
    d.update(over)
    return d


# ─────────────────────── grid ───────────────────────

R_A = mk_room("a", ["#######", "#..T..#", "#.~P.!#", "D.....#", "#######"],
              exits={"0,3": "b"}, occ={"2,3": "npc_x"})
R_B = mk_room("b", ["...", "...", "..."])

for nm, c in [("origin", cd(0, 0)), ("interior", cd(3, 2)), ("last", cd(6, 4)),
              ("second_row", cd(0, 1))]:
    case("grid", "cell_index", nm, {"room": R_A, "coord": c})
for nm, c in [("wall_corner", cd(0, 0)), ("table", cd(3, 1)),
              ("occupied_floor", cd(2, 3)), ("door", cd(0, 3)),
              ("difficult", cd(2, 2))]:
    case("grid", "get_cell", nm, {"room": R_A, "coord": c})
case("grid", "get_cell", "x_past_width", {"room": R_A, "coord": cd(7, 1)},
     err="out of bounds")
case("grid", "get_cell", "y_past_height", {"room": R_A, "coord": cd(1, 5)},
     err="out of bounds")
case("grid", "get_cell", "far_out", {"room": R_B, "coord": cd(40, 40)},
     err="out of bounds")
for nm, c, cell in [
    ("floor_to_wall", cd(1, 1), {"terrain": "wall", "occupant_id": None}),
    ("occupy", cd(4, 3), {"terrain": "floor", "occupant_id": "alpha"}),
    ("clear_occupant", cd(2, 3), {"terrain": "floor", "occupant_id": None}),
    ("last_cell", cd(6, 4), {"terrain": "hazard", "occupant_id": None}),
]:
    case("grid", "set_cell", nm, {"room": R_A, "coord": c, "cell": cell})
for nm, c in [("origin", cd(0, 0)), ("last", cd(6, 4)), ("x_eq_width", cd(7, 0)),
              ("y_eq_height", cd(0, 5)), ("both_over", cd(9, 9)),
              ("interior", cd(3, 3))]:
    case("grid", "in_bounds", nm, {"room": R_A, "coord": c})
for nm, a, b in [("same", cd(2, 2), cd(2, 2)), ("horizontal", cd(0, 0), cd(5, 0)),
                 ("vertical", cd(1, 6), cd(1, 1)), ("diagonal", cd(0, 0), cd(4, 4)),
                 ("knight", cd(1, 1), cd(3, 6)), ("reverse", cd(9, 2), cd(2, 4))]:
    case("grid", "chebyshev_distance", nm, {"a": a, "b": b})
    case("grid", "feet_between", nm, {"a": a, "b": b})
for nm, cell in [("floor", {"terrain": "floor", "occupant_id": None}),
                 ("door", {"terrain": "door", "occupant_id": None}),
                 ("difficult", {"terrain": "difficult", "occupant_id": None}),
                 ("hazard", {"terrain": "hazard", "occupant_id": None}),
                 ("wall", {"terrain": "wall", "occupant_id": None}),
                 ("pillar", {"terrain": "pillar", "occupant_id": None}),
                 ("table", {"terrain": "table", "occupant_id": None}),
                 ("occupied_floor", {"terrain": "floor", "occupant_id": "bob"}),
                 ("occupied_door", {"terrain": "door", "occupant_id": "bob"})]:
    case("grid", "is_traversable", nm, {"cell": cell})
    case("grid", "movement_cost_feet", nm, {"cell": cell})
for nm, a, b in [("single_point", cd(2, 2), cd(2, 2)), ("horizontal", cd(0, 1), cd(5, 1)),
                 ("vertical_up", cd(3, 5), cd(3, 1)), ("diagonal", cd(0, 0), cd(4, 4)),
                 ("shallow_slope", cd(0, 0), cd(7, 2)), ("steep_slope", cd(0, 0), cd(2, 7)),
                 ("reverse_shallow", cd(7, 2), cd(0, 0)), ("adjacent_diag", cd(2, 2), cd(3, 3))]:
    case("grid", "line_coords", nm, {"a": a, "b": b})
for nm, s, e in [("clear_row", cd(1, 3), cd(5, 3)), ("through_pillar", cd(1, 2), cd(5, 2)),
                 ("end_on_table", cd(3, 3), cd(3, 1)), ("end_on_occupant", cd(1, 3), cd(2, 3)),
                 ("through_occupant", cd(1, 3), cd(4, 3)), ("start_is_end", cd(1, 1), cd(1, 1)),
                 ("diagonal_clear", cd(1, 1), cd(2, 2)),
                 ("through_difficult_ok", cd(1, 2), cd(3, 2))]:
    case("grid", "path_is_clear", nm, {"room": R_A, "start": s, "end": e})
case("grid", "path_is_clear", "end_out_of_bounds",
     {"room": R_B, "start": cd(0, 0), "end": cd(5, 0)}, err="out of bounds")

# ─────────────────────── rules ───────────────────────

def rl(name, st, action, cid="alpha", err=None):
    case("rules", "check_grid_action", name,
         {"state": st, "char_id": cid, "action": {"actor_id": cid, **action}})


def mv(x, y): return {"type": "move", "target": cd(x, y)}
def it(x, y): return {"type": "interact", "target": cd(x, y)}


rl("move_legal_exploration", base(), mv(4, 6))
rl("move_legal_combat", base(phase=TurnPhase.COMBAT), mv(4, 6))
rl("move_out_of_bounds_x", base(), mv(12, 6))
rl("move_out_of_bounds_y", base(), mv(2, 8))
rl("move_into_wall", base(), mv(0, 6))
rl("move_into_table", base(), mv(5, 5))
rl("move_into_pillar", base(lambda s: setcell(s, 3, 6, "pillar")), mv(3, 6))
rl("move_onto_enemy", base(), mv(7, 5))
rl("move_onto_ally", base(), mv(2, 6))
rl("move_onto_self", base(), mv(1, 6))
rl("move_combat_too_far", base(phase=TurnPhase.COMBAT), mv(10, 6))
rl("move_combat_exact_budget",
   base(lambda s: setattr(s.characters["alpha"], "movement_remaining", 25), phase=TurnPhase.COMBAT),
   mv(6, 6))
rl("move_combat_zero_budget",
   base(lambda s: setattr(s.characters["alpha"], "movement_remaining", 0), phase=TurnPhase.COMBAT),
   mv(2, 5))
rl("move_exploration_ignores_budget",
   base(lambda s: setattr(s.characters["alpha"], "movement_remaining", 0)), mv(10, 6))
rl("move_path_blocked_by_table", base(lambda s: place(s, "alpha", 3, 5)), mv(8, 5))
rl("move_during_lobby_phase_allowed", base(phase=TurnPhase.LOBBY), mv(4, 6))
rl("move_during_creation_phase_allowed", base(phase=TurnPhase.CREATION), mv(4, 6))
rl("attack_denied_exploration", base(), {"type": "attack", "target": cd(7, 5)})
rl("attack_denied_combat", base(phase=TurnPhase.COMBAT), {"type": "attack", "target": cd(7, 5)})
rl("attack_out_of_bounds_reports_bounds_first", base(), {"type": "attack", "target": cd(30, 30)})
rl("interact_adjacent_ok", base(lambda s: place(s, "alpha", 6, 5)), it(7, 5))
rl("interact_diagonal_adjacent_ok", base(lambda s: place(s, "alpha", 6, 6)), it(7, 5))
rl("interact_far_denied", base(), it(7, 5))
rl("interact_self_cell_ok", base(), it(1, 6))
rl("interact_wall_adjacent_ok", base(), it(0, 6))
rl("interact_out_of_bounds", base(), it(20, 20))

# ─────────────────────── validators ───────────────────────

def sv(name, diff, st=None):
    case("validators", "sanitize", name, {"state": st or base(), "diff": diff})


def hp_state(cur):
    return base(lambda s: setattr(s.characters["alpha"], "hp_current", cur))


HPMAX = _BASE.characters["alpha"].hp_max
CU = lambda **f: {"character_updates": {"alpha": f}}  # noqa: E731

sv("lobby_phase_rejects_everything", {**CU(hp_current=1), "phase_change": "exploration"},
   base(phase=TurnPhase.LOBBY))
sv("creation_phase_rejects_everything", CU(hp_current=1), base(phase=TurnPhase.CREATION))
sv("combat_phase_still_sanitizes", CU(conditions=["prone"]), base(phase=TurnPhase.COMBAT))
sv("empty_diff", {})
sv("hp_within_delta_accepted", CU(hp_current=HPMAX - 5), hp_state(HPMAX))
sv("hp_delta_exactly_8_accepted", CU(hp_current=HPMAX - 8), hp_state(HPMAX))
sv("hp_delta_9_rejected", CU(hp_current=HPMAX - 9), hp_state(HPMAX))
sv("hp_heal_within_delta", CU(hp_current=6), hp_state(1))
sv("hp_over_max_rejected", CU(hp_current=HPMAX + 1), hp_state(HPMAX))
sv("hp_negative_rejected", CU(hp_current=-1))
sv("hp_zero_accepted_when_close", CU(hp_current=0), hp_state(3))
sv("hp_string_rejected", CU(hp_current="5"))
sv("hp_float_rejected", CU(hp_current=5.5))
sv("hp_unchanged_accepted", CU(hp_current=HPMAX), hp_state(HPMAX))
sv("unknown_character", {"character_updates": {"ghost": {"hp_current": 3}}})
sv("forbidden_field_name", CU(name="Hacker"))
sv("forbidden_field_hp_max", CU(hp_max=999))
sv("forbidden_field_inventory", CU(inventory=[]))
sv("conditions_list_accepted", CU(conditions=["prone", "stunned"]))
sv("conditions_not_list_rejected", CU(conditions="prone"))
sv("conditions_empty_list_accepted", CU(conditions=[]))
sv("movement_accepted", CU(movement_remaining=15))
sv("movement_at_speed_accepted", CU(movement_remaining=_BASE.characters["alpha"].speed))
sv("movement_zero_accepted", CU(movement_remaining=0))
sv("movement_negative_rejected", CU(movement_remaining=-5))
sv("movement_over_speed_rejected", CU(movement_remaining=_BASE.characters["alpha"].speed + 5))
sv("movement_non_int_rejected", CU(movement_remaining="fast"))
sv("position_direct_write_rejected", CU(position={"x": 3, "y": 3}))
sv("mixed_fields_partial_accept",
   {"character_updates": {"alpha": {"hp_current": HPMAX - 1, "name": "X", "position": cd(2, 2),
                                    "conditions": ["prone"]},
                          "beta": {"hp_current": -4}}})
sv("char_update_all_rejected_drops_key", CU(position=cd(1, 1)))
sv("cell_update_in_bounds_accepted",
   {"cell_updates": [["back_alley", cd(4, 4), {"terrain": "hazard", "occupant_id": None}]]})
sv("cell_update_other_room_rejected",
   {"cell_updates": [["market_square", cd(4, 4), {"terrain": "wall", "occupant_id": None}]]})
sv("cell_update_unknown_room_rejected",
   {"cell_updates": [["nowhere", cd(1, 1), {"terrain": "floor", "occupant_id": None}]]})
sv("cell_update_out_of_bounds_rejected",
   {"cell_updates": [["back_alley", cd(12, 1), {"terrain": "floor", "occupant_id": None}]]})
sv("cell_update_y_out_of_bounds_rejected",
   {"cell_updates": [["back_alley", cd(1, 8), {"terrain": "floor", "occupant_id": None}]]})
sv("cell_updates_mixed_order_preserved",
   {"cell_updates": [["back_alley", cd(2, 2), {"terrain": "door", "occupant_id": None}],
                     ["market_square", cd(2, 2), {"terrain": "door", "occupant_id": None}],
                     ["back_alley", cd(3, 3), {"terrain": "difficult", "occupant_id": "ghoul"}]]})


def itm(i="potion", q=1, **k):
    return {"id": i, "name": i.title(), "quantity": q, **k}


sv("add_inventory_accepted", {"add_inventory": {"alpha": [itm("potion", 3)]}})
sv("add_inventory_qty_10_accepted", {"add_inventory": {"alpha": [itm("arrows", 10)]}})
sv("add_inventory_qty_11_rejected", {"add_inventory": {"alpha": [itm("gold", 11)]}})
sv("add_inventory_partial", {"add_inventory": {"alpha": [itm("a", 11), itm("b", 2), itm("c", 999)]}})
sv("add_inventory_unknown_char", {"add_inventory": {"ghost": [itm("a", 1)]}})
sv("add_inventory_all_rejected_drops_key", {"add_inventory": {"alpha": [itm("a", 50)]}})
sv("add_inventory_zero_quantity_accepted", {"add_inventory": {"alpha": [itm("a", 0)]}})
OWNED = _BASE.characters["alpha"].inventory[0].id
sv("remove_inventory_owned", {"remove_inventory": {"alpha": [OWNED]}})
sv("remove_inventory_not_owned", {"remove_inventory": {"alpha": ["vorpal_sword"]}})
sv("remove_inventory_mixed", {"remove_inventory": {"alpha": [OWNED, "vorpal_sword", "other"]}})
sv("remove_inventory_unknown_char", {"remove_inventory": {"ghost": [OWNED]}})
sv("remove_inventory_other_chars_item", {"remove_inventory": {"beta": [OWNED]}})
sv("phase_change_combat_rejected", {"phase_change": "combat"})
sv("phase_change_exploration_accepted", {"phase_change": "exploration"})
sv("phase_change_lobby_accepted_quirk", {"phase_change": "lobby"})
sv("phase_change_title_accepted_quirk", {"phase_change": "title"})
sv("everything_at_once",
   {"character_updates": {"alpha": {"conditions": ["poisoned"], "movement_remaining": 10}},
    "cell_updates": [["back_alley", cd(1, 1), {"terrain": "hazard", "occupant_id": None}]],
    "add_inventory": {"beta": [itm("rope", 2)]},
    "remove_inventory": {"alpha": [OWNED]},
    "phase_change": "exploration"})

# ─────────────────────── enemies ───────────────────────

def pa(name, att, tgt, randint, **kw):
    case("enemies", "resolve_player_attack", name,
         {"attacker": att, "target": tgt}, {"randint": randint}, **kw)


def ea(name, en, tgt, randint, **kw):
    case("enemies", "resolve_enemy_attack", name,
         {"enemy": en, "target": tgt}, {"randint": randint}, **kw)


def weapon(dice, eq=True, i="w1"):
    return {"id": i, "name": i.upper(), "quantity": 1, "equipped": eq, "value": 0,
            "notes": None, "damage_dice": dice, "armor_ac_bonus": 0}


def abil(**kw):
    d = dict(STR=10, DEX=10, CON=10, INT=10, WIS=10, CHA=10)
    d.update(kw)
    return d


A_D8 = bare(abilities=abil(STR=16, DEX=12), proficiency_bonus=2, inventory=[weapon("1d8")], name="Hero")
# STR16 => mod +3, +2 prof => +5
T_AC12 = enemy(armor_class=12, hp_current=20, hp_max=20, name="Bandit")
pa("hit_d8_mid_roll", A_D8, T_AC12, [10, 4])           # 15 vs 12 -> hit, 4+3
pa("hit_exact_ac", A_D8, T_AC12, [7, 1])               # 12 vs 12 -> hit, min dmg 1+3
pa("miss_one_under_ac", A_D8, T_AC12, [6])             # 11 vs 12 -> miss
pa("miss_natural_one", A_D8, T_AC12, [1])              # nat 1 is just a low roll
pa("nat_one_still_hits_vs_low_ac", A_D8, enemy(armor_class=3, name="Rat"), [1, 5])
pa("crit_natural_20_double_dice", A_D8, T_AC12, [20, 6, 7])  # (6+7)+3
pa("crit_hits_even_if_total_below_ac", bare(abilities=abil(STR=1, DEX=1), proficiency_bonus=2,
                                           inventory=[weapon("1d8")]),
   enemy(armor_class=30, name="Wall"), [20, 2, 3])
pa("default_weapon_d6_when_unarmed", bare(abilities=abil(STR=14), inventory=[]), T_AC12, [12, 5])
pa("unequipped_weapon_ignored", bare(abilities=abil(STR=14), inventory=[weapon("1d12", eq=False)]),
   T_AC12, [12, 2])
pa("equipped_item_without_dice_skipped",
   bare(abilities=abil(STR=14), inventory=[{**weapon("1d4"), "damage_dice": None, "id": "plate"},
                                          weapon("2d4", i="blade")]),
   T_AC12, [12, 3, 4])
pa("dex_better_than_str", bare(abilities=abil(STR=8, DEX=18), inventory=[weapon("1d6")]), T_AC12, [9, 3])
pa("negative_mod_not_added_to_damage",
   bare(abilities=abil(STR=6, DEX=6), proficiency_bonus=2, inventory=[weapon("1d6")]),
   enemy(armor_class=5, name="Slime"), [10, 4])
pa("multi_dice_with_bonus", bare(abilities=abil(STR=12), inventory=[weapon("2d6+2")]), T_AC12, [14, 3, 5])
pa("negative_bonus_dice_floor_one", bare(abilities=abil(STR=10), inventory=[weapon("1d4-3")]), T_AC12, [14, 1])
pa("dead_target_still_resolved", A_D8, enemy(hp_current=0, alive=False, armor_class=10), [10, 4])
pa("high_proficiency", bare(abilities=abil(STR=20), proficiency_bonus=6, inventory=[weapon("1d10")]),
   enemy(armor_class=22, name="Dragon"), [11, 9])
pa("unparseable_dice_is_one", bare(abilities=abil(STR=10), inventory=[weapon("sword")]), T_AC12, [14])

E_D6 = enemy(attack_bonus=3, damage_dice="1d6", name="Goblin")
C_AC15 = bare(armor_class=15, name="Hero")
ea("hit_total_meets_ac", E_D6, C_AC15, [12, 4])          # 15 vs 15
ea("miss_total_below_ac", E_D6, C_AC15, [11])
ea("miss_natural_one", E_D6, C_AC15, [1])
ea("natural_20_hits_any_ac", enemy(attack_bonus=0), bare(armor_class=30), [20, 2])
ea("natural_20_no_double_damage", E_D6, bare(armor_class=10), [20, 6])
ea("multi_dice_bonus", enemy(damage_dice="2d6+2"), C_AC15, [18, 4, 5])
ea("negative_bonus_floor_one", enemy(damage_dice="1d4-2"), C_AC15, [18, 1])
ea("unparseable_dice_is_one", enemy(damage_dice="claws"), C_AC15, [18])
ea("negative_attack_bonus", enemy(attack_bonus=-2), bare(armor_class=10), [12, 3])
ea("dead_enemy_still_resolved", enemy(hp_current=0, alive=False), C_AC15, [18, 2])
ea("dead_target_still_resolved", E_D6, bare(hp_current=0, armor_class=10), [15, 3])

for nm, notation, vals in [
    ("1d8", "1d8", [5]), ("2d6_plus2", "2d6+2", [3, 4]), ("1d4_minus1", "1d4-1", [3]),
    ("minus_clamps_to_one", "1d4-9", [2]), ("leading_trailing_space", "  1d8 ", [8]),
    ("garbage", "banana", []), ("empty", "", []), ("no_count_d6", "d6", []),
    ("zero_dice", "0d6", []), ("trailing_text", "1d8 slashing", [2]),
    ("leading_junk_fails_match", "x1d8", []), ("big_count", "4d4+1", [1, 2, 3, 4]),
    ("uppercase_D_fails", "1D8", []), ("explicit_plus_zero", "1d6+0", [1]),
]:
    case("enemies", "_roll_dice", nm, {"notation": notation}, {"randint": vals})
for sc in [1, 8, 9, 10, 11, 12, 15, 20, 30]:
    case("enemies", "_mod", f"score_{sc}", {"score": sc})
case("enemies", "_weapon_dice", "first_equipped_with_dice",
     {"char": bare(inventory=[weapon("1d12", eq=False, i="a"), weapon("1d8", i="b"),
                              weapon("2d6", i="c")])})
case("enemies", "_weapon_dice", "default_when_none", {"char": bare(inventory=[])})

# ─────────────────────── character_factory ───────────────────────

MINI = mini_state()
RACE_BY_GROUP: dict[str, list[str]] = {}
for _r, _d in cf.RACES.items():
    RACE_BY_GROUP.setdefault(_d.group, []).append(_r.value)
_picks: list[str] = []
for _g in ("Cosmic", "Primal", "Eldritch", "Mechanical"):
    _picks += RACE_BY_GROUP[_g][:3]
_picks += RACE_BY_GROUP["Humanoid"][::1][:13]
STATES_L = ["behemoth", "phantom", "swarm_host", "mimic"]
ROLES_L = ["stalker", "vanguard", "catalyst", "siphoner"]
_combos = Counter()
for _i, _race in enumerate(_picks):
    _st = STATES_L[_i % 4]
    _ro = ROLES_L[(_i + _i // 4) % 4]
    _combos[(_st, "s")] += 1
    _combos[(_ro, "r")] += 1
    kw: dict = {}
    if _i % 5 == 0:
        kw = dict(background="void_scavenger", skill_proficiencies=["Athletics", "Survival"],
                  keepsake_name="Cracked Locket", starting_era="before")
    elif _i % 5 == 1:
        kw = dict(equipment_choice_id=[c.id for c in cf.ROLES[cf.PredatorRole(_ro)].equipment_choices][-1],
                  feat="apex_predator", cantrips=["light"], alignment="Chaotic Neutral",
                  pronouns="she/her", title="The Hollow", dialogue_style="gruff")
    elif _i % 5 == 2:
        kw = dict(equipment_choice_id="not_a_real_item", background="not_a_background",
                  physical_description="Tall.", backstory="Fell.", personality_traits="Calm",
                  flaws="Proud", bonds="Kin", ideals="Order")
    case("character_factory", "build_character", f"{_race}_{_st}_{_ro}",
         {"char_id": f"c{_i:02d}", "name": f"Tester {_i}", "player": "pad_1",
          "race": _race, "state": _st, "role": _ro, "abilities": STD_PERMS[_i % 6],
          "game_state": MINI, **kw})
assert len(_picks) == 25
assert all(v >= 2 for v in _combos.values()), _combos
assert {cf.RACES[cf.Race(r)].group for r in _picks} == set(RACE_BY_GROUP)

_BAD = lambda **a: {"char_id": "x", "name": "X", "player": "p", "race": "voidwraith",  # noqa: E731
                    "state": "mimic", "role": "stalker", "abilities": a, "game_state": MINI}
case("character_factory", "build_character", "bad_array_duplicate",
     _BAD(STR=15, DEX=15, CON=13, INT=12, WIS=10, CHA=8), err="standard array")
case("character_factory", "build_character", "bad_array_all_tens",
     _BAD(STR=10, DEX=10, CON=10, INT=10, WIS=10, CHA=10), err="standard array")
case("character_factory", "build_character", "bad_array_point_buy",
     _BAD(STR=16, DEX=14, CON=13, INT=12, WIS=10, CHA=8), err="standard array")
case("character_factory", "build_character", "unknown_race",
     {**_BAD(**STD_PERMS[0]), "race": "notarace"}, err="is not a valid Race")
case("character_factory", "build_character", "start_cell_after_wall_row",
     {**_BAD(**STD_PERMS[0]), "game_state": mini_state(
         ["########", "#......#", "#......#", "#......#", "#......#", "#......#",
          "###.####", "########"])})
for nm, ab in [("valid_std", STD_PERMS[2]),
               ("valid_reordered", dict(STR=8, DEX=10, CON=12, INT=13, WIS=14, CHA=15)),
               ("dup_top", STD_PERMS[0] | {"DEX": 15}),
               ("sum_ok_but_wrong", dict(STR=15, DEX=14, CON=13, INT=12, WIS=11, CHA=7))]:
    case("character_factory", "is_valid_standard_array", nm, {"abilities": ab})
case("character_factory", "generate_char_id", "plain", {"name": "Rook", "existing": []})
case("character_factory", "generate_char_id", "slug_strips_punct_and_case",
     {"name": "Dr. Ro-ok 99!", "existing": []})
case("character_factory", "generate_char_id", "empty_slug_falls_back",
     {"name": "!!!", "existing": []})
case("character_factory", "generate_char_id", "no_collision_consumes_no_rng",
     {"name": "Rook", "existing": ["alpha", "beta"]})
case("character_factory", "generate_char_id", "collision_appends_token",
     {"name": "Rook", "existing": ["rook"]}, {"token_hex": ["a1b2"]})
case("character_factory", "generate_char_id", "collision_on_fallback",
     {"name": "", "existing": ["char"]}, {"token_hex": ["00ff"]})
case("character_factory", "generate_char_id", "token_may_collide_again",
     {"name": "Rook", "existing": ["rook", "rook_a1b2"]}, {"token_hex": ["a1b2"]})
case("character_factory", "find_starting_position", "default_row6", {"state": MINI})
_s = mini_state()
_s["rooms"]["mini"]["cells"][6 * 8 + 1]["occupant_id"] = "x"
case("character_factory", "find_starting_position", "row6_first_occupied", {"state": _s})
_s = mini_state()
for _x in range(8):
    _s["rooms"]["mini"]["cells"][6 * 8 + _x]["occupant_id"] = "x"
case("character_factory", "find_starting_position", "row6_full_falls_to_row5", {"state": _s})
case("character_factory", "find_starting_position", "row6_walls_falls_to_row5",
     {"state": mini_state(["########", "#......#", "#......#", "#......#", "#......#", "#......#",
                           "########", "########"])})
case("character_factory", "find_starting_position", "short_room_uses_height_minus_2",
     {"state": mini_state(["....", "....", "...."])})
case("character_factory", "find_starting_position", "short_room_first_blocked",
     {"state": mini_state(["....", "T...", "...."])})
case("character_factory", "find_starting_position", "scan_wraps_to_row_zero",
     {"state": mini_state(["....", "####", "####", "####", "####", "####", "####", "####"])})
case("character_factory", "find_starting_position", "no_traversable_cells",
     {"state": mini_state(["####", "####", "####"])}, err="no traversable cells")
case("character_factory", "find_starting_position", "all_tables",
     {"state": mini_state(["TT", "TT"])}, err="no traversable cells")
for _race, _es, _extra in [
    ("ironfast", "behemoth", {}), ("veilborn", "phantom", {}), ("voidwraith", "swarm_host", {}),
    ("grimcrow", "mimic", {}), ("forgespawn", "behemoth", {"name_override": "Rusty"}),
    ("scaleworn", "phantom", {"xp_reward": 400}), ("hexgear", "mimic", {}),
    ("fallenlight", "swarm_host", {"name_override": "Halo", "xp_reward": 7}),
    ("cinderplate", "behemoth", {}), ("chaosling", "phantom", {}),
]:
    case("character_factory", "build_race_enemy", f"{_race}_{_es}",
         {"enemy_id": f"e_{_race}", "race": _race, "ev_state": _es, "room_id": "mini",
          "position": cd(3, 3), **_extra})

# ─────────────────────── state_manager ───────────────────────

def smc(fn, name, st, args, rng=None, err=None):
    case("state_manager", fn, name, {"state": st, "args": args}, rng, err)


def hp_of(cid, v):
    return lambda s: setattr(s.characters[cid], "hp_current", v)


def chain(*fs):
    def f(s):
        for g in fs:
            g(s)
    return f


# set_phase
for p in ["combat", "exploration", "lobby", "title"]:
    smc("set_phase", p, base(), {"phase": p})
smc("set_phase", "same_phase_still_bumps_revision", base(), {"phase": "exploration"})

# get_character
smc("get_character", "found", base(), {"char_id": "beta"})
smc("get_character", "unknown", base(), {"char_id": "ghost"}, err="unknown character")

# attack_enemy: alpha = ironfast behemoth vanguard
smc("attack_enemy", "hit_survives_counter_hits", base(), {"attacker_id": "alpha", "enemy_id": "bandit_01"},
    {"randint": [15, 2, 18, 3]})
smc("attack_enemy", "miss_counter_miss", base(), {"attacker_id": "alpha", "enemy_id": "bandit_01"},
    {"randint": [2, 3]})
smc("attack_enemy", "hit_kills_awards_xp_and_vacates_cell",
    base(lambda s: setattr(s.enemies["bandit_01"], "hp_current", 2)),
    {"attacker_id": "alpha", "enemy_id": "bandit_01"}, {"randint": [15, 3]})
smc("attack_enemy", "crit_kills", base(lambda s: setattr(s.enemies["bandit_01"], "hp_current", 4)),
    {"attacker_id": "alpha", "enemy_id": "bandit_01"}, {"randint": [20, 3, 3]})
smc("attack_enemy", "kill_leaves_foreign_occupant",
    base(chain(lambda s: setattr(s.enemies["bandit_01"], "hp_current", 1),
               lambda s: setcell(s, 5, 2, occ="someone_else"))),
    {"attacker_id": "alpha", "enemy_id": "bandit_01"}, {"randint": [18, 3]})
smc("attack_enemy", "counter_drops_player_to_zero_clamped",
    base(chain(hp_of("alpha", 1), lambda s: setattr(s.enemies["thug_01"], "damage_dice", "2d6+5"))),
    {"attacker_id": "alpha", "enemy_id": "thug_01"}, {"randint": [2, 18, 6, 6]})
smc("attack_enemy", "player_dead_can_still_attack", base(hp_of("alpha", 0)),
    {"attacker_id": "alpha", "enemy_id": "thug_01"}, {"randint": [18, 2, 18, 3]})
smc("attack_enemy", "beta_phantom_attacks", base(), {"attacker_id": "beta", "enemy_id": "thug_01"},
    {"randint": [16, 3, 12, 3]})
smc("attack_enemy", "no_range_or_phase_check_far_enemy", base(phase=TurnPhase.LOBBY),
    {"attacker_id": "alpha", "enemy_id": "thug_01"}, {"randint": [3, 5]})
smc("attack_enemy", "enemy_already_dead", base(lambda s: setattr(s.enemies["bandit_01"], "alive", False)),
    {"attacker_id": "alpha", "enemy_id": "bandit_01"}, err="already dead")
smc("attack_enemy", "unknown_attacker", base(), {"attacker_id": "ghost", "enemy_id": "bandit_01"},
    err="unknown character")
smc("attack_enemy", "unknown_enemy", base(), {"attacker_id": "alpha", "enemy_id": "dragon"},
    err="enemy not found")

# fast_travel / transition_room
smc("fast_travel", "to_market", base(two_rooms=True), {"room_id": "market_square"})
smc("fast_travel", "to_same_room", base(), {"room_id": "back_alley"})
smc("fast_travel", "unknown_room", base(), {"room_id": "atlantis"}, err="unknown room")
smc("fast_travel", "resets_movement_remaining",
    base(lambda s: setattr(s.characters["alpha"], "movement_remaining", 0), two_rooms=True), {"room_id": "market_square"})
smc("transition_room", "to_market_two_chars_get_distinct_spawns", base(two_rooms=True), {"target_room_id": "market_square"})
smc("transition_room", "no_characters", base(lambda s: s.characters.clear(), two_rooms=True), {"target_room_id": "market_square"})
smc("transition_room", "spawn_cell_already_occupied_by_other",
    base(lambda s: setcell(s, 1, 6, occ="x"), two_rooms=True), {"target_room_id": "market_square"})
smc("transition_room", "unknown_room", base(), {"target_room_id": "nope"}, err="unknown room")

# apply_grid_action
def agm(name, st, cid, action, **kw):
    smc("apply_grid_action", name, st, {"char_id": cid, "action": {"actor_id": cid, **action}}, **kw)


agm("move_exploration_resets_movement", base(lambda s: setattr(s.characters["alpha"], "movement_remaining", 5)),
    "alpha", mv(5, 6))
agm("move_combat_decrements_movement", base(phase=TurnPhase.COMBAT), "alpha", mv(4, 5))
agm("move_combat_diagonal_costs_chebyshev", base(lambda s: place(s, "alpha", 3, 6), phase=TurnPhase.COMBAT), "alpha", mv(5, 4))
agm("move_vacates_old_and_occupies_new", base(), "beta", mv(7, 1))
agm("move_denied_wall", base(), "alpha", mv(0, 6), err="target cell is wall")
agm("move_denied_occupied", base(), "alpha", mv(7, 5), err="occupied by thug_01")
agm("move_denied_out_of_bounds", base(), "alpha", mv(99, 99), err="outside the room")
agm("move_denied_too_far_combat", base(phase=TurnPhase.COMBAT), "alpha", mv(10, 6), err="ft remaining")
agm("move_denied_path_blocked", base(lambda s: place(s, "alpha", 3, 5)), "alpha", mv(8, 5),
    err="path is blocked")
agm("attack_denied", base(), "alpha", {"type": "attack", "target": cd(7, 5)}, err="v0.2")
agm("interact_generic_floor", base(lambda s: place(s, "alpha", 3, 4)), "alpha", it(3, 5))
agm("interact_enemy_alive", base(lambda s: place(s, "alpha", 6, 5)), "alpha", it(7, 5))
agm("interact_enemy_dead_falls_through_to_generic",
    base(chain(lambda s: place(s, "alpha", 6, 5), lambda s: setattr(s.enemies["thug_01"], "alive", False))),
    "alpha", it(7, 5))
def _npc(s):
    from storyforge.core.models import NpcSheet
    s.npcs["jon"] = NpcSheet(id="jon", name="Jon", position=Coord(x=3, y=6), room_id="back_alley",
                             encounter_id="jon_shop")
    setcell(s, 3, 6, occ="jon")
    place(s, "alpha", 2, 6)
    place(s, "beta", 1, 5)
def _npc_prefixed(s):
    _npc(s)
    setcell(s, 3, 6, occ="npc_jon")
agm("interact_npc_encounter", base(_npc), "alpha", it(3, 6))
agm("interact_npc_with_legacy_prefix", base(_npc_prefixed), "alpha", it(3, 6))
agm("interact_door_transitions_room", base(lambda s: place(s, "alpha", 1, 4), two_rooms=True), "alpha", it(0, 4))
agm("interact_door_without_exit_is_generic",
    base(chain(lambda s: place(s, "alpha", 1, 4), lambda s: s.rooms["back_alley"].exits.clear())),
    "alpha", it(0, 4))
agm("interact_not_adjacent_denied", base(), "alpha", it(7, 5), err="adjacent")
agm("interact_unknown_occupant_generic", base(chain(lambda s: place(s, "alpha", 3, 4),
                                                    lambda s: setcell(s, 3, 5, occ="mystery"))), "alpha", it(3, 5))

# apply_diff
def ad(name, diff, st=None, **kw):
    smc("apply_diff", name, st or base(), {"diff": diff}, **kw)


ad("empty_diff_bumps_revision", {})
ad("hp_and_conditions", {"character_updates": {"alpha": {"hp_current": 3, "conditions": ["prone"]}}})
ad("unknown_char_skipped_everywhere",
   {"character_updates": {"ghost": {"hp_current": 3}}, "add_inventory": {"ghost": [itm("a")]},
    "remove_inventory": {"ghost": ["a"]}})
ad("unknown_field_silently_ignored", {"character_updates": {"alpha": {"not_a_field": 5, "hp_current": 2}}})
ad("unsanitized_forbidden_field_is_applied_quirk",
   {"character_updates": {"alpha": {"name": "Renamed", "hp_max": 3}}})
ad("unsanitized_position_write_leaves_cell_stale_quirk",
   {"character_updates": {"alpha": {"position": cd(4, 4)}}})
ad("cell_update_overwrites_cell",
   {"cell_updates": [["back_alley", cd(2, 2), {"terrain": "hazard", "occupant_id": None}]]})
ad("cell_update_can_erase_occupant_quirk",
   {"cell_updates": [["back_alley", cd(1, 6), {"terrain": "floor", "occupant_id": None}]]})
ad("cell_update_unknown_room_skipped",
   {"cell_updates": [["nowhere", cd(2, 2), {"terrain": "hazard", "occupant_id": None}]]})
ad("cell_update_other_known_room",
   {"cell_updates": [["market_square", cd(1, 1), {"terrain": "wall", "occupant_id": None}]]},
   base(two_rooms=True))
ad("add_inventory_appends", {"add_inventory": {"alpha": [itm("potion", 2), itm("rope")]}})
ad("add_inventory_duplicate_id_not_merged", {"add_inventory": {"alpha": [itm(OWNED, 1)]}})
ad("remove_inventory_filters_by_id", {"remove_inventory": {"alpha": [OWNED]}})
ad("remove_inventory_missing_id_still_reported", {"remove_inventory": {"alpha": ["zzz"]}})
ad("phase_change_applied", {"phase_change": "combat"})
ad("phase_change_none_leaves_phase", {"phase_change": None})
ad("combined_diff",
   {"character_updates": {"beta": {"conditions": ["stunned"]}},
    "cell_updates": [["back_alley", cd(8, 1), {"terrain": "difficult", "occupant_id": None}]],
    "add_inventory": {"beta": [itm("flare", 3)]}, "remove_inventory": {"alpha": [OWNED]},
    "phase_change": "combat"})

# append_narration
for k, actor in [("narration", None), ("action", "alpha"), ("system", None)]:
    smc("append_narration", f"{k}_entry_does_not_bump_revision", base(),
        {"actor_id": actor, "kind": k, "text": f"A {k} line."})
smc("append_narration", "appends_to_existing_log",
    base(lambda s: s.narrative_log.append(__import__("storyforge.core.models", fromlist=["NarrativeEntry"]).NarrativeEntry(
        revision=0, actor_id=None, kind="system", text="first", timestamp="2025-12-31T00:00:00+00:00"))),
    {"actor_id": "beta", "kind": "action", "text": "second"})
smc("append_narration", "uses_current_revision", base(revision=41),
    {"actor_id": None, "kind": "narration", "text": "rev check"})

# lobby / creation
def lobby(tw=None, phase=TurnPhase.LOBBY):
    def f(s):
        s.characters.clear()
        for rm in s.rooms.values():
            for c in rm.cells:
                c.occupant_id = None
        if tw:
            tw(s)
    return base(f, phase=phase)


def claim(i, ctrl, status="claimed"):
    def f(s):
        s.lobby_slots[i].status = SlotStatus(status)
        s.lobby_slots[i].controller_id = ctrl
    return f


smc("claim_slot", "first_empty_in_lobby", lobby(), {"controller_id": "pad_a"})
smc("claim_slot", "skips_taken_slots", lobby(claim(0, "pad_x")), {"controller_id": "pad_b"})
smc("claim_slot", "idempotent_already_held", lobby(claim(0, "pad_a")), {"controller_id": "pad_a"})
smc("claim_slot", "allowed_in_creation_phase", lobby(phase=TurnPhase.CREATION), {"controller_id": "pad_a"})
smc("claim_slot", "wrong_phase", base(), {"controller_id": "pad_a"}, err="cannot claim slot")
smc("claim_slot", "all_slots_full",
    lobby(chain(*[claim(i, f"p{i}") for i in range(4)])), {"controller_id": "pad_z"}, err="all 4 slots")
smc("update_slot_name", "claims_empty_slot", lobby(), {"slot_index": 2, "name": "Rook", "controller_id": "pad_c"})
smc("update_slot_name", "overwrites_draft", lobby(claim(1, "pad_b")),
    {"slot_index": 1, "name": "Newname", "controller_id": "pad_b"})
smc("update_slot_name", "slot_ready_rejected", lobby(claim(0, "pad_a", "ready")),
    {"slot_index": 0, "name": "X", "controller_id": "pad_a"}, err="already ready")
smc("save_draft", "marks_creating_and_sets_fields", lobby(claim(0, "pad_a"), TurnPhase.CREATION),
    {"controller_id": "pad_a", "patch": {"race": "voidwraith", "backstory": "Born in a rift.",
                                          "creation_step": "race", "bogus_key": 1}})
smc("save_draft", "no_slot_for_controller", lobby(), {"controller_id": "nobody", "patch": {}},
    err="no slot found")
smc("save_draft", "empty_slot_rejected", lobby(claim(0, "pad_a", "empty")),
    {"controller_id": "pad_a", "patch": {}}, err="not in a creation state")
smc("release_slot", "clears_draft_and_reverts_to_lobby",
    lobby(chain(claim(0, "pad_a", "creating"), lambda s: setattr(s.lobby_slots[0], "name_draft", "Zed")),
          TurnPhase.CREATION), {"controller_id": "pad_a"})
smc("release_slot", "keeps_phase_when_other_slots_remain",
    lobby(chain(claim(0, "pad_a"), claim(1, "pad_b")), TurnPhase.CREATION), {"controller_id": "pad_a"})
smc("release_slot", "ready_slot_removes_character",
    base(lambda s: (setattr(s.lobby_slots[0], "status", SlotStatus.READY),
                    setattr(s.lobby_slots[0], "controller_id", "pad_alpha"),
                    setattr(s.lobby_slots[0], "character_id", "alpha")), phase=TurnPhase.CREATION),
    {"controller_id": "pad_alpha"})
smc("release_slot", "unknown_controller", lobby(), {"controller_id": "nobody"}, err="no slot held")

REQ = {"slot_index": 0, "name": "Rook", "race": "veilborn", "evolution_state": "mimic",
       "predator_role": "stalker", "starting_era": "after", "abilities": STD_PERMS[1],
       "background": "void_scavenger", "keepsake_name": "Old Coin"}
smc("create_character", "happy_path", lobby(claim(0, "pad_a"), TurnPhase.CREATION), {"request": REQ})
smc("create_character", "before_era_not_transformed", lobby(claim(0, "pad_a", "creating"), TurnPhase.CREATION),
    {"request": {**REQ, "starting_era": "before"}})
smc("create_character", "id_collision_uses_token",
    lobby(chain(claim(0, "pad_a"), lambda s: s.characters.update(
        {"rook": _BASE.characters["alpha"].model_copy(update={"id": "rook"})})), TurnPhase.CREATION),
    {"request": REQ}, {"token_hex": ["beef"]})
smc("create_character", "wrong_phase", lobby(claim(0, "pad_a")), {"request": REQ},
    err="requires CREATION phase")
smc("create_character", "slot_not_claimed", lobby(phase=TurnPhase.CREATION), {"request": REQ},
    err="cannot create")
smc("create_character", "invalid_standard_array", lobby(claim(0, "pad_a"), TurnPhase.CREATION),
    {"request": {**REQ, "abilities": dict(STR=15, DEX=15, CON=13, INT=12, WIS=10, CHA=8)}},
    err="standard array")

# start_exploration / trigger_paradox
def ready_state(transformed=True):
    def f(s):
        s.lobby_slots[0].status = SlotStatus.READY
        s.lobby_slots[0].character_id = "alpha"
        for c in s.characters.values():
            c.is_transformed = transformed
    return base(f, phase=TurnPhase.CREATION)


smc("start_exploration", "all_transformed_era_after", ready_state(True), {})
smc("start_exploration", "any_untransformed_era_before",
    base(lambda s: (setattr(s.lobby_slots[0], "status", SlotStatus.READY),
                    setattr(s.characters["beta"], "is_transformed", False)), phase=TurnPhase.CREATION), {})
smc("start_exploration", "wrong_phase", base(), {}, err="can only start from CREATION")
smc("start_exploration", "no_ready_slot", base(phase=TurnPhase.CREATION), {}, err="at least one character")
smc("trigger_paradox", "transforms_untransformed",
    base(lambda s: (setattr(s.characters["alpha"], "is_transformed", False),
                    setattr(s, "era", Era.BEFORE))), {})
smc("trigger_paradox", "already_transformed", base(), {})
smc("trigger_paradox", "no_characters", base(lambda s: s.characters.clear()), {})


# ─────────────────────── generation ───────────────────────

def build_all() -> dict[str, str]:
    """Run every case and return {relative_path: file_text}."""
    out: dict[str, str] = {}
    seen: set[tuple[str, str]] = set()
    problems: list[str] = []
    for c in CASES:
        key = (c["module"], c["case"])
        assert key not in seen, f"duplicate case {key}"
        seen.add(key)
        outcome, rng = gl.run_case(c["module"], c["function"], c["inputs"], c["rng"])
        left = rng.leftover()
        problem = None
        if left:
            problem = f"unconsumed rng script {left}"
        elif c["err"] is None and "expected" not in outcome:
            problem = f"unexpected {outcome}"
        elif c["err"] is not None and not outcome.get("raises"):
            problem = f"expected error, got {outcome}"
        elif c["err"] is not None and c["err"] not in outcome["message"]:
            problem = f"message {outcome['message']!r}"
        if problem:
            problems.append(f"{key}: {problem}")
            continue
        script = {k: c["rng"].get(k, []) for k in gl.RNG_KEYS}
        script["randint_bounds"] = rng.randint_bounds
        if "expected" in outcome:
            expected = outcome["expected"]
        else:
            expected = {"raises": outcome["raises"], "message_contains": c["err"]}
        doc = {"module": c["module"], "function": c["function"], "case": c["case"],
               "inputs": c["inputs"], "rng_script": script, "expected": expected}
        out[f"{c['module']}/{c['case']}.json"] = gl.dumps(doc)
    if problems:
        raise SystemExit("recording problems:\n" + "\n".join(problems))
    return out


def main() -> int:
    files = build_all()
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    wanted = set(files)
    for p in FIXTURE_DIR.rglob("*.json"):
        if str(p.relative_to(FIXTURE_DIR)) not in wanted:
            p.unlink()
    for rel, text in files.items():
        p = FIXTURE_DIR / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    counts = Counter(r.split("/")[0] for r in files)
    total = sum(len(t.encode()) for t in files.values())
    print(f"wrote {len(files)} fixtures, {total} bytes")
    for m, n in sorted(counts.items()):
        print(f"  {m}: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
