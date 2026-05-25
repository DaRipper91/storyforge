"""
The single mutation point for GameState.

Public mutators must call self._commit() at the end so that:
    1. revision increments
    2. state is persisted to disk atomically
    3. an event is published to subscribers

Concurrency model: FastAPI runs handlers in async tasks on a single event
loop. We use an asyncio.Lock to serialize mutations so two near-simultaneous
WebSocket-driven changes can't interleave. Reads do not require the lock —
they snapshot via .model_copy(deep=True) if the caller needs isolation.
"""
from __future__ import annotations
import asyncio
import datetime as dt
from pathlib import Path
from typing import Literal

from storyforge.core import grid, rules
from storyforge.core.models import (
    CharacterSheet, Coord, GameState, GridAction,
    NarrativeEntry, StateDiff,
)
from storyforge.events.bus import event_bus
from storyforge.persistence import snapshot


# ─────────────────────── Errors ───────────────────────

class StateError(Exception):
    """Generic state-layer error."""


class IllegalActionError(StateError):
    """A grid action failed rules.check_grid_action."""


# ─────────────────────── Manager ───────────────────────

class StateManager:
    def __init__(self, initial: GameState, campaign_dir: Path) -> None:
        self._state = initial
        self._campaign_dir = campaign_dir
        self._lock = asyncio.Lock()
    
    @property
    def current(self) -> GameState:
        """Read-only handle to the live state. Don't mutate this directly."""
        return self._state
    
    def get_character(self, char_id: str) -> CharacterSheet:
        char = self._state.characters.get(char_id)
        if char is None:
            raise StateError(f"unknown character: {char_id}")
        return char
    
    # ─────────────────── Public Mutators ───────────────────
    
    async def apply_grid_action(
        self,
        char: CharacterSheet,
        action: GridAction,
    ) -> dict:
        """Apply a structured grid action. Raises IllegalActionError on failure."""
        async with self._lock:
            verdict = rules.check_grid_action(self._state, char, action)
            if not verdict.ok:
                raise IllegalActionError(verdict.reason)
            
            diff_summary: dict = {}
            
            match action.type:
                case "move":
                    diff_summary = self._do_move(char, action.target)
                case "interact":
                    diff_summary = {"type": "interact", "target": action.target.model_dump()}
                case _:
                    raise IllegalActionError(f"unhandled action: {action.type}")
            
            await self._commit(diff_summary)
            return diff_summary
    
    async def apply_diff(self, diff: StateDiff) -> dict:
        """
        Apply an AI-proposed (and validator-sanitized) diff.
        
        IMPORTANT: this assumes diff has already been through
        validators.sanitize(). Calling this with a raw Gemini response
        bypasses every safety check.
        """
        async with self._lock:
            applied: dict = {"character_updates": {}, "cell_updates": [],
                             "add_inventory": {}, "remove_inventory": {},
                             "phase_change": None}
            
            for char_id, updates in diff.character_updates.items():
                char = self._state.characters.get(char_id)
                if char is None:
                    continue
                for field, value in updates.items():
                    if hasattr(char, field):
                        setattr(char, field, value)
                applied["character_updates"][char_id] = updates
            
            for room_id, coord, new_cell in diff.cell_updates:
                room = self._state.rooms.get(room_id)
                if room is None:
                    continue
                grid.set_cell(room, coord, new_cell)
                applied["cell_updates"].append([room_id, coord.model_dump(),
                                                new_cell.model_dump()])
            
            for char_id, items in diff.add_inventory.items():
                char = self._state.characters.get(char_id)
                if char is None:
                    continue
                char.inventory.extend(items)
                applied["add_inventory"][char_id] = [i.model_dump() for i in items]
            
            for char_id, item_ids in diff.remove_inventory.items():
                char = self._state.characters.get(char_id)
                if char is None:
                    continue
                char.inventory = [i for i in char.inventory if i.id not in item_ids]
                applied["remove_inventory"][char_id] = item_ids
            
            if diff.phase_change is not None:
                self._state.phase = diff.phase_change
                applied["phase_change"] = diff.phase_change.value
            
            await self._commit(applied)
            return applied
    
    async def append_narration(
        self,
        actor_id: str | None,
        kind: Literal["action", "narration", "system"],
        text: str,
    ) -> None:
        """Append a narrative log entry. Does NOT bump revision."""
        async with self._lock:
            self._state.narrative_log.append(
                NarrativeEntry(
                    revision=self._state.revision,
                    actor_id=actor_id,
                    kind=kind,
                    text=text,
                    timestamp=dt.datetime.now(dt.timezone.utc).isoformat(),
                )
            )
            # Narration is part of state, so persist — but skip event bus
            # to avoid double-broadcast (the caller will publish the diff).
            snapshot.save(self._campaign_dir, self._state)
    
    # ─────────────────── Internal Helpers ───────────────────
    
    def _do_move(self, char: CharacterSheet, target: Coord) -> dict:
        """Pure mutation: vacate old cell, occupy new, decrement movement."""
        room = self._state.rooms[self._state.current_room_id]
        feet_spent = grid.feet_between(char.position, target)
        
        # Vacate old cell
        old_cell = grid.get_cell(room, char.position)
        old_cell.occupant_id = None
        
        # Occupy new cell
        new_cell = grid.get_cell(room, target)
        new_cell.occupant_id = char.id
        
        # Update character
        previous = char.position
        char.position = target
        char.movement_remaining -= feet_spent
        
        return {
            "type": "move",
            "actor_id": char.id,
            "from": previous.model_dump(),
            "to": target.model_dump(),
            "feet_spent": feet_spent,
            "movement_remaining": char.movement_remaining,
        }
    
    async def _commit(self, diff_summary: dict) -> None:
        """
        Single point of write-out + broadcast. ALWAYS called inside the lock.
        
        Order matters:
            1. Bump revision (so subscribers see the new number)
            2. Persist to disk (so crashes after publish still recover)
            3. Publish to bus (subscribers fire after disk is durable)
        """
        self._state.revision += 1
        snapshot.save(self._campaign_dir, self._state)
        await event_bus.publish({
            "type": "state_diff",
            "revision": self._state.revision,
            "diff": diff_summary,
        })
