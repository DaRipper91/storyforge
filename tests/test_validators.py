"""
Tests for storyforge.core.validators.sanitize().

Each test constructs a minimal StateDiff, runs it through sanitize(), and
asserts the resulting safe_diff and rejection list match expectations.

We need a GameState in EXPLORATION phase because sanitize() rejects all diffs
during LOBBY/CREATION. We build one from the seed, add a dummy character, and
set the phase manually.
"""
import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("STORYFORGE_GEMINI_API_KEY", "test-fake-key-not-real")

from storyforge.core import validators
from storyforge.core.models import (
    AbilityScores,
    Cell,
    CharacterSheet,
    Coord,
    EvolutionaryState,
    GameState,
    InventoryItem,
    PredatorRole,
    Race,
    StateDiff,
    TerrainKind,
    TurnPhase,
)

_SEED_PATH = Path(__file__).resolve().parents[1] / "data" / "seeds" / "default_campaign.json"


def _exploration_state() -> tuple[GameState, str]:
    """
    Return a GameState in EXPLORATION phase with one character already placed.
    Also returns the character_id string.
    """
    gs = GameState.model_validate(json.loads(_SEED_PATH.read_text()))
    gs.phase = TurnPhase.EXPLORATION

    char = CharacterSheet(
        id="hero",
        name="Hero",
        player="pytest",
        race=Race.VOIDWRAITH,
        evolution_state=EvolutionaryState.MIMIC,
        predator_role=PredatorRole.STALKER,
        hp_current=10,
        hp_max=10,
        armor_class=13,
        speed=30,
        abilities=AbilityScores(STR=10, DEX=12, CON=13, INT=14, WIS=15, CHA=8),
        position=Coord(x=1, y=1),
        movement_remaining=30,
        inventory=[
            InventoryItem(id="razor_claws", name="Razor Claws", quantity=1),
        ],
    )
    gs.characters["hero"] = char
    return gs, "hero"


# ─────────────────────── HP updates ───────────────────────

def test_allow_hp_update():
    """A small hp_current change within limits passes sanitization."""
    gs, char_id = _exploration_state()
    diff = StateDiff(character_updates={char_id: {"hp_current": 8}})
    safe, rejections = validators.sanitize(gs, diff)
    assert rejections == []
    assert safe.character_updates[char_id]["hp_current"] == 8


def test_reject_hp_exceeds_max():
    """hp_current > hp_max must be rejected."""
    gs, char_id = _exploration_state()
    diff = StateDiff(character_updates={char_id: {"hp_current": 99}})
    safe, rejections = validators.sanitize(gs, diff)
    assert any("max" in r for r in rejections)
    assert char_id not in safe.character_updates


def test_reject_hp_negative():
    """Negative hp_current must be rejected."""
    gs, char_id = _exploration_state()
    diff = StateDiff(character_updates={char_id: {"hp_current": -1}})
    safe, rejections = validators.sanitize(gs, diff)
    assert any("negative" in r for r in rejections)
    assert char_id not in safe.character_updates


# ─────────────────────── Direct position write ───────────────────────

def test_reject_direct_position():
    """
    character_updates containing 'position' must be stripped out.
    Position changes must go through cell_updates.
    """
    gs, char_id = _exploration_state()
    diff = StateDiff(character_updates={char_id: {"position": {"x": 3, "y": 3}}})
    safe, rejections = validators.sanitize(gs, diff)
    assert any("position" in r for r in rejections)
    # The character_updates entry should either be absent or not contain 'position'.
    if char_id in safe.character_updates:
        assert "position" not in safe.character_updates[char_id]


def test_position_stripped_but_hp_passes():
    """
    In a mixed update, 'position' is rejected while 'hp_current' passes.
    """
    gs, char_id = _exploration_state()
    diff = StateDiff(character_updates={char_id: {
        "hp_current": 9,
        "position": {"x": 5, "y": 5},
    }})
    safe, rejections = validators.sanitize(gs, diff)
    assert any("position" in r for r in rejections)
    assert "hp_current" in safe.character_updates[char_id]
    assert "position" not in safe.character_updates[char_id]


# ─────────────────────── Phase changes ───────────────────────

def test_reject_combat_phase_change():
    """A StateDiff proposing phase_change=COMBAT must be rejected (v0.2 deferred)."""
    gs, _ = _exploration_state()
    diff = StateDiff(phase_change=TurnPhase.COMBAT)
    safe, rejections = validators.sanitize(gs, diff)
    assert any("combat" in r.lower() for r in rejections)
    assert safe.phase_change is None


def test_lobby_phase_rejects_all_diffs():
    """During LOBBY phase, every proposed diff is rejected wholesale."""
    gs = GameState.model_validate(json.loads(_SEED_PATH.read_text()))
    # seed starts in LOBBY
    assert gs.phase == TurnPhase.LOBBY

    diff = StateDiff(phase_change=TurnPhase.EXPLORATION)
    safe, rejections = validators.sanitize(gs, diff)
    assert len(rejections) >= 1
    assert safe.phase_change is None


# ─────────────────────── Inventory adds ───────────────────────

def test_allow_inventory_add():
    """add_inventory with quantity <= 10 passes."""
    gs, char_id = _exploration_state()
    item = InventoryItem(id="potion_01", name="Healing Potion", quantity=3)
    diff = StateDiff(add_inventory={char_id: [item]})
    safe, rejections = validators.sanitize(gs, diff)
    assert rejections == []
    assert char_id in safe.add_inventory
    assert safe.add_inventory[char_id][0].id == "potion_01"


def test_reject_inventory_over_qty():
    """add_inventory with quantity > 10 must be rejected."""
    gs, char_id = _exploration_state()
    item = InventoryItem(id="coin_pile", name="Gold Coins", quantity=11)
    diff = StateDiff(add_inventory={char_id: [item]})
    safe, rejections = validators.sanitize(gs, diff)
    assert any("quantity" in r or "qty" in r.lower() or "> 10" in r for r in rejections)
    assert char_id not in safe.add_inventory


def test_allow_inventory_add_exactly_10():
    """quantity == 10 is the limit and should pass."""
    gs, char_id = _exploration_state()
    item = InventoryItem(id="arrow_01", name="Arrow", quantity=10)
    diff = StateDiff(add_inventory={char_id: [item]})
    safe, rejections = validators.sanitize(gs, diff)
    assert rejections == []
    assert char_id in safe.add_inventory


# ─────────────────────── Inventory removes ───────────────────────

def test_reject_remove_unowned_item():
    """Trying to remove an item the character doesn't own is rejected."""
    gs, char_id = _exploration_state()
    diff = StateDiff(remove_inventory={char_id: ["nonexistent_sword"]})
    safe, rejections = validators.sanitize(gs, diff)
    assert any("nonexistent_sword" in r for r in rejections)
    assert char_id not in safe.remove_inventory


def test_allow_remove_owned_item():
    """Removing an item the character actually owns passes."""
    gs, char_id = _exploration_state()
    diff = StateDiff(remove_inventory={char_id: ["razor_claws"]})
    safe, rejections = validators.sanitize(gs, diff)
    assert rejections == []
    assert safe.remove_inventory[char_id] == ["razor_claws"]


# ─────────────────────── Cell updates ───────────────────────

def test_cell_update_in_bounds():
    """A cell update within the current room at a valid coordinate passes."""
    gs, _ = _exploration_state()
    room_id = gs.current_room_id
    gs.rooms[room_id]
    # Use a cell that's guaranteed in-bounds.
    coord = Coord(x=1, y=1)
    new_cell = Cell(terrain=TerrainKind.FLOOR)
    diff = StateDiff(cell_updates=[(room_id, coord, new_cell)])
    safe, rejections = validators.sanitize(gs, diff)
    assert rejections == []
    assert len(safe.cell_updates) == 1


def test_cell_update_out_of_bounds_rejected():
    """A cell update with coordinates outside room bounds is rejected."""
    gs, _ = _exploration_state()
    room_id = gs.current_room_id
    room = gs.rooms[room_id]
    # Way outside bounds.
    coord = Coord(x=room.width + 100, y=room.height + 100)
    new_cell = Cell(terrain=TerrainKind.FLOOR)
    diff = StateDiff(cell_updates=[(room_id, coord, new_cell)])
    safe, rejections = validators.sanitize(gs, diff)
    assert any("bounds" in r or "out" in r.lower() for r in rejections)
    assert len(safe.cell_updates) == 0


def test_cell_update_wrong_room_rejected():
    """A cell update targeting a room the party is not in is rejected."""
    gs, _ = _exploration_state()
    room_id = gs.current_room_id
    # Pick a different room (any room that isn't the current one).
    other_rooms = [r for r in gs.rooms if r != room_id]
    if not other_rooms:
        pytest.skip("seed has only one room")
    other_room = other_rooms[0]
    coord = Coord(x=0, y=0)
    new_cell = Cell(terrain=TerrainKind.FLOOR)
    diff = StateDiff(cell_updates=[(other_room, coord, new_cell)])
    safe, rejections = validators.sanitize(gs, diff)
    assert any(other_room in r for r in rejections)
    assert len(safe.cell_updates) == 0
