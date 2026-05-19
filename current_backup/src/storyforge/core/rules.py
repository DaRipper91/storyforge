"""
D&D 5e legality checks.

Pure functions: take a snapshot of state + an action, return a Legality
verdict. Never mutates. The state_manager calls these before applying
any structured (grid-click) action.
"""
from __future__ import annotations
from dataclasses import dataclass

from storyforge.core import grid
from storyforge.core.models import (
    CharacterSheet, Coord, GameState, GridAction, Room,
)


@dataclass(frozen=True)
class Legality:
    ok: bool
    reason: str = ""
    
    @classmethod
    def allow(cls) -> "Legality":
        return cls(ok=True)
    
    @classmethod
    def deny(cls, reason: str) -> "Legality":
        return cls(ok=False, reason=reason)


def check_grid_action(
    state: GameState,
    char: CharacterSheet,
    action: GridAction,
) -> Legality:
    """Top-level dispatcher for structured grid actions."""
    room = state.rooms[state.current_room_id]
    
    if not grid.in_bounds(room, action.target):
        return Legality.deny(f"target {action.target} is outside the room")
    
    match action.type:
        case "move":
            return _check_move(room, char, action.target)
        case "attack":
            return Legality.deny("attacks are v0.2; freeform-narrate it for now")
        case "interact":
            return _check_interact(room, char, action.target)
        case _:
            return Legality.deny(f"unknown action type: {action.type}")


def _check_move(room: Room, char: CharacterSheet, target: Coord) -> Legality:
    target_cell = grid.get_cell(room, target)
    
    if not grid.is_traversable(target_cell):
        return Legality.deny(
            f"target cell is {target_cell.terrain.value}"
            + (f" (occupied by {target_cell.occupant_id})"
               if target_cell.occupant_id else "")
        )
    
    feet_needed = grid.feet_between(char.position, target)
    if feet_needed > char.movement_remaining:
        return Legality.deny(
            f"need {feet_needed}ft, only {char.movement_remaining}ft remaining"
        )
    
    if not grid.path_is_clear(room, char.position, target):
        return Legality.deny("path is blocked between start and target")
    
    return Legality.allow()


def _check_interact(room: Room, char: CharacterSheet, target: Coord) -> Legality:
    # Must be adjacent (within 5ft) to interact
    if grid.feet_between(char.position, target) > grid.FEET_PER_CELL:
        return Legality.deny("interact target must be adjacent")
    return Legality.allow()
