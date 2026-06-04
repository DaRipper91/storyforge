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
from storyforge.core.character_factory import (
    build_character, find_starting_position, generate_char_id,
)
from storyforge.core.models import (
    CharacterSheet, Coord, GameState, GridAction,
    NarrativeEntry, StateDiff, TurnPhase,
    CharacterCreationRequest, CharClass, LobbySlot, Race,
    SlotStatus,
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

    # ───────────────────── Lobby + Creation Mutators ─────────────────────

    async def claim_slot(self, *, controller_id: str) -> dict:
        """
        A controller pressed A in the lobby. Assign it to the first empty slot.
        
        Idempotent: if the controller_id already holds a slot, return that
        slot's info without re-claiming.
        """
        async with self._lock:
            if self._state.phase not in (TurnPhase.LOBBY, TurnPhase.CREATION):
                raise StateError(
                    f"cannot claim slot during phase '{self._state.phase.value}'"
                )
            
            # Already claimed? Return existing slot.
            for slot in self._state.lobby_slots:
                if slot.controller_id == controller_id and slot.status != SlotStatus.EMPTY:
                    return {"type": "slot_claimed", "slot_index": slot.slot_index,
                            "already_held": True}
            
            # Find first empty slot.
            for slot in self._state.lobby_slots:
                if slot.status == SlotStatus.EMPTY:
                    slot.status = SlotStatus.CLAIMED
                    slot.controller_id = controller_id
                    # Transition LOBBY -> CREATION when first slot claimed.
                    if self._state.phase == TurnPhase.LOBBY:
                        self._state.phase = TurnPhase.CREATION
                    
                    summary = {
                        "type": "slot_claimed",
                        "slot_index": slot.slot_index,
                        "controller_id": controller_id,
                        "phase": self._state.phase.value,
                    }
                    await self._commit(summary)
                    return summary
            
            raise StateError("all 4 slots are claimed")


    async def release_slot(self, *, controller_id: str) -> dict:
        """A controller pressed B to leave. Clear their slot."""
        async with self._lock:
            for slot in self._state.lobby_slots:
                if slot.controller_id == controller_id:
                    if slot.status == SlotStatus.READY:
                        # Already became a real character — remove from roster too.
                        if slot.character_id:
                            self._state.characters.pop(slot.character_id, None)
                    
                    released_index = slot.slot_index
                    slot.status = SlotStatus.EMPTY
                    slot.controller_id = None
                    slot.character_id = None
                    slot.chosen_name = None
                    slot.chosen_race = None
                    slot.chosen_class = None
                    slot.chosen_ability_layout = None
                    
                    # If nobody is in any slot, revert to LOBBY phase.
                    if all(s.status == SlotStatus.EMPTY for s in self._state.lobby_slots):
                        self._state.phase = TurnPhase.LOBBY
                    
                    summary = {
                        "type": "slot_released",
                        "slot_index": released_index,
                        "phase": self._state.phase.value,
                    }
                    await self._commit(summary)
                    return summary
            
            raise StateError(f"no slot held by controller {controller_id}")


    async def create_character(self, req: CharacterCreationRequest) -> dict:
        """
        Finalize a slot into a real CharacterSheet.
        
        Caller (the route) must have already verified that req.slot_index
        is claimed by an active controller.
        """
        async with self._lock:
            if self._state.phase != TurnPhase.CREATION:
                raise StateError(
                    f"character creation requires CREATION phase, "
                    f"current: {self._state.phase.value}"
                )
            
            slot = self._state.lobby_slots[req.slot_index]
            if slot.status not in (SlotStatus.CLAIMED, SlotStatus.CREATING):
                raise StateError(
                    f"slot {req.slot_index} is {slot.status.value}, cannot create"
                )
            
            # Generate a unique character ID.
            existing_ids = set(self._state.characters.keys())
            char_id = generate_char_id(req.name, existing_ids)
            
            # Find a starting position on the grid.
            position = find_starting_position(self._state)
            
            # Build the sheet (may raise ValueError on invalid abilities).
            sheet = build_character(
                char_id=char_id,
                player=slot.controller_id or "unknown",
                name=req.name,
                race=req.race,
                char_class=req.char_class,
                base_abilities=req.abilities,
                starting_position=position,
            )
            
            # Insert into state.
            self._state.characters[char_id] = sheet
            
            # Occupy the starting cell.
            room = self._state.rooms[self._state.current_room_id]
            cell = grid.get_cell(room, position)
            cell.occupant_id = char_id
            
            # Update the slot.
            slot.status = SlotStatus.READY
            slot.character_id = char_id
            slot.chosen_name = req.name
            slot.chosen_race = req.race
            slot.chosen_class = req.char_class
            slot.chosen_ability_layout = req.abilities.model_dump()
            
            summary = {
                "type": "character_created",
                "slot_index": req.slot_index,
                "character_id": char_id,
                "character": sheet.model_dump(mode="json"),
            }
            await self._commit(summary)
            return summary


    async def start_exploration(self) -> dict:
        """
        Transition from CREATION to EXPLORATION.
        
        Requires at least one slot in READY status. Empty/claimed slots are
        left alone — they can be filled later (in a v0.2 drop-in feature).
        """
        async with self._lock:
            if self._state.phase != TurnPhase.CREATION:
                raise StateError(
                    f"can only start from CREATION, currently {self._state.phase.value}"
                )
            
            ready_count = sum(
                1 for s in self._state.lobby_slots if s.status == SlotStatus.READY
            )
            if ready_count < 1:
                raise StateError("at least one character must be ready to start")
            
            self._state.phase = TurnPhase.EXPLORATION
            
            # Append an opening narrative entry so the chronicle isn't blank.
            roster = ", ".join(c.name for c in self._state.characters.values())
            opening = (
                f"The Crooked Tankard's door swings shut behind {roster}. "
                f"Pipe smoke hangs in the rafters, and a bard by the hearth "
                f"tunes a battered lute."
            )
            self._state.narrative_log.append(
                NarrativeEntry(
                    revision=self._state.revision + 1,
                    actor_id=None,
                    kind="narration",
                    text=opening,
                    timestamp=dt.datetime.now(dt.timezone.utc).isoformat(),
                )
            )
            
            summary = {
                "type": "exploration_started",
                "character_count": ready_count,
                "phase": self._state.phase.value,
            }
            await self._commit(summary)
            return summary
    
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
