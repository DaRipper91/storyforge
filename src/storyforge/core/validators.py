"""
Sanitize AI-proposed StateDiffs before they touch live state.

Philosophy: REJECT, don't repair. If the AI proposes something illegal,
drop it and log a system message. Repairing (clamping HP to max,
rounding teleports to nearest legal cell) creates magic the AI then
learns to exploit. Hard NO is teachable; soft maybe is gameable.

Returns a tuple of (sanitized_diff, rejections) where rejections is a
list of human-readable strings to append to the narrative log.
"""
from __future__ import annotations
from copy import deepcopy

from storyforge.core import grid
from storyforge.core.models import (
    Cell, Coord, GameState, InventoryItem, StateDiff, TurnPhase,
)


# Fields the AI is permitted to mutate on a CharacterSheet.
_ALLOWED_CHAR_FIELDS = {
    "hp_current",
    "conditions",
    "movement_remaining",
    "position",          # only via cell_updates, not direct write; see below
}

# Max delta the AI may apply to HP in a single turn without an explicit
# combat phase. Prevents "you find a healing fountain" giving +∞ HP.
_MAX_HP_DELTA_PER_TURN = 8


def sanitize(
    state: GameState,
    proposed: StateDiff,
) -> tuple[StateDiff, list[str]]:
    """Return (safe_diff, rejection_messages). The safe_diff is always
    a fresh StateDiff — never the input object."""
    rejections: list[str] = []
    safe = StateDiff()
    
    # During lobby/creation, AI shouldn't be proposing diffs at all —
    # but if it does (e.g. from a leftover narration call), reject everything.
    if state.phase in (TurnPhase.LOBBY, TurnPhase.CREATION):
        rejections.append(
            f"AI diffs are not accepted during {state.phase.value} phase"
        )
        return safe, rejections
    
    safe.character_updates = _filter_char_updates(
        state, proposed.character_updates, rejections,
    )
    safe.cell_updates = _filter_cell_updates(
        state, proposed.cell_updates, rejections,
    )
    safe.add_inventory = _filter_add_inventory(
        state, proposed.add_inventory, rejections,
    )
    safe.remove_inventory = _filter_remove_inventory(
        state, proposed.remove_inventory, rejections,
    )
    safe.phase_change = _filter_phase_change(
        state, proposed.phase_change, rejections,
    )
    
    return safe, rejections


# ─────────────────────── Per-section filters ───────────────────────

def _filter_char_updates(
    state: GameState,
    updates: dict[str, dict],
    rejections: list[str],
) -> dict[str, dict]:
    safe: dict[str, dict] = {}
    for char_id, fields in updates.items():
        if char_id not in state.characters:
            rejections.append(f"unknown character '{char_id}'")
            continue
        char = state.characters[char_id]
        safe_fields: dict = {}
        for field, value in fields.items():
            if field not in _ALLOWED_CHAR_FIELDS:
                rejections.append(
                    f"AI tried to modify forbidden field '{field}' on {char_id}"
                )
                continue
            
            # Field-specific guards
            if field == "hp_current":
                if not isinstance(value, int):
                    rejections.append(f"hp_current must be int, got {type(value).__name__}")
                    continue
                if value < 0:
                    rejections.append(f"hp_current cannot be negative ({char_id})")
                    continue
                if value > char.hp_max:
                    rejections.append(
                        f"hp_current {value} > max {char.hp_max} for {char_id}"
                    )
                    continue
                if abs(value - char.hp_current) > _MAX_HP_DELTA_PER_TURN:
                    rejections.append(
                        f"HP delta too large for {char_id}: "
                        f"{char.hp_current} → {value}"
                    )
                    continue
            
            if field == "movement_remaining":
                if not isinstance(value, int) or value < 0:
                    rejections.append(f"movement_remaining invalid for {char_id}")
                    continue
                if value > char.speed:
                    rejections.append(
                        f"movement_remaining {value} > speed {char.speed} for {char_id}"
                    )
                    continue
            
            if field == "conditions":
                if not isinstance(value, list):
                    rejections.append(f"conditions must be list for {char_id}")
                    continue
            
            if field == "position":
                # Disallow direct position writes — must go through cell_updates
                # so the cell occupancy is also updated.
                rejections.append(
                    f"position must be set via cell_updates, not character_updates ({char_id})"
                )
                continue
            
            safe_fields[field] = value
        
        if safe_fields:
            safe[char_id] = safe_fields
    return safe


def _filter_cell_updates(
    state: GameState,
    updates: list[tuple[str, Coord, Cell]],
    rejections: list[str],
) -> list[tuple[str, Coord, Cell]]:
    safe: list[tuple[str, Coord, Cell]] = []
    current_room_id = state.current_room_id
    
    for room_id, coord, new_cell in updates:
        if room_id != current_room_id:
            rejections.append(
                f"AI tried to modify room '{room_id}' but party is in '{current_room_id}'"
            )
            continue
        
        room = state.rooms.get(room_id)
        if room is None:
            rejections.append(f"unknown room '{room_id}'")
            continue
        
        if not grid.in_bounds(room, coord):
            rejections.append(f"cell {coord} out of bounds in {room_id}")
            continue
        
        safe.append((room_id, coord, new_cell))
    return safe


def _filter_add_inventory(
    state: GameState,
    additions: dict[str, list[InventoryItem]],
    rejections: list[str],
) -> dict[str, list[InventoryItem]]:
    safe: dict[str, list[InventoryItem]] = {}
    for char_id, items in additions.items():
        if char_id not in state.characters:
            rejections.append(f"unknown character '{char_id}' in inventory add")
            continue
        # For MVP, allow inventory additions but cap quantity to prevent
        # "AI gives you 999 healing potions"
        safe_items = []
        for item in items:
            if item.quantity > 10:
                rejections.append(
                    f"refused inventory add: quantity {item.quantity} > 10 ({item.name})"
                )
                continue
            safe_items.append(item)
        if safe_items:
            safe[char_id] = safe_items
    return safe


def _filter_remove_inventory(
    state: GameState,
    removals: dict[str, list[str]],
    rejections: list[str],
) -> dict[str, list[str]]:
    safe: dict[str, list[str]] = {}
    for char_id, item_ids in removals.items():
        char = state.characters.get(char_id)
        if char is None:
            rejections.append(f"unknown character '{char_id}' in inventory remove")
            continue
        owned_ids = {i.id for i in char.inventory}
        valid = [iid for iid in item_ids if iid in owned_ids]
        invalid = [iid for iid in item_ids if iid not in owned_ids]
        for iid in invalid:
            rejections.append(f"{char_id} does not own item '{iid}'")
        if valid:
            safe[char_id] = valid
    return safe


def _filter_phase_change(
    state: GameState,
    proposed: TurnPhase | None,
    rejections: list[str],
) -> TurnPhase | None:
    if proposed is None:
        return None
    # MVP: AI can suggest moving to COMBAT, but we reject — combat is v0.2.
    if proposed == TurnPhase.COMBAT:
        rejections.append("phase change to combat is deferred to v0.2")
        return None
    return proposed
