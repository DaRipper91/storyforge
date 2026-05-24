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
    NarrativeEntry, StateDiff, TurnPhase, Era,
    CharacterCreationRequest, SlotStatus,
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
    
    async def set_phase(self, phase: TurnPhase) -> dict:
        """Explicitly change the game phase."""
        async with self._lock:
            self._state.phase = phase
            summary = {
                "type": "phase_changed",
                "phase": phase.value,
            }
            await self._commit(summary)
            return summary


    async def fast_travel(self, room_id: str) -> dict:
        """World-map teleport: move the party to any known room."""
        async with self._lock:
            diff = self._do_transition_room(room_id)
            await self._commit(diff)
        return diff

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
                    diff_summary = self._do_interact(char, action.target)
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
                    
                    summary = {
                        "type": "slot_claimed",
                        "slot_index": slot.slot_index,
                        "controller_id": controller_id,
                        "phase": self._state.phase.value,
                    }
                    await self._commit(summary)
                    return summary
            
            raise StateError("all 4 slots are claimed")


    async def update_slot_name(self, *, slot_index: int, name: str, controller_id: str) -> dict:
        """Update a slot's draft name. Claims the slot if it's empty."""
        async with self._lock:
            slot = self._state.lobby_slots[slot_index]
            
            if slot.status == SlotStatus.READY:
                raise StateError(f"slot {slot_index} is already ready")
            
            if slot.status == SlotStatus.EMPTY:
                slot.status = SlotStatus.CLAIMED
            
            slot.name_draft = name
            slot.controller_id = controller_id
            
            summary = {
                "type": "slot_name_updated",
                "slot_index": slot_index,
                "name": name,
                "controller_id": controller_id,
            }
            await self._commit(summary)
            return summary


    async def save_draft(self, *, controller_id: str, patch: dict) -> dict:
        """Persist mid-creation draft fields so a page-refresh can restore progress."""
        async with self._lock:
            for slot in self._state.lobby_slots:
                if slot.controller_id == controller_id:
                    if slot.status not in (SlotStatus.CLAIMED, SlotStatus.CREATING):
                        raise StateError(f"slot for {controller_id} is not in a creation state")
                    slot.status = SlotStatus.CREATING
                    for key, value in patch.items():
                        if hasattr(slot, key):
                            setattr(slot, key, value)
                    summary = {"type": "draft_saved", "controller_id": controller_id}
                    await self._commit(summary)
                    return summary
            raise StateError(f"no slot found for controller {controller_id}")

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
                    slot.race = None
                    slot.evolution_state = None
                    slot.predator_role = None
                    slot.assigned_abilities = None
                    slot.name_draft = None
                    slot.equipment_choice_id = None
                    slot.background = None
                    slot.skill_proficiencies = []
                    slot.feat = None
                    slot.cantrips = []
                    slot.alignment = None
                    slot.pronouns = "they/them"
                    slot.title = None
                    slot.dialogue_style = None
                    slot.physical_description = ""
                    slot.backstory = ""
                    slot.personality_traits = ""
                    slot.flaws = ""
                    slot.bonds = ""
                    slot.ideals = ""
                    slot.keepsake_name = None
                    slot.creation_step = "era"
                    
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
            
            # Build the sheet.
            sheet = build_character(
                char_id=char_id,
                player=slot.controller_id or "unknown",
                name=req.name,
                race=req.race,
                state=req.evolution_state,
                role=req.predator_role,
                abilities=req.abilities,
                game_state=self._state,
                starting_era=req.starting_era,
                background=req.background,
                equipment_choice_id=req.equipment_choice_id,
                skill_proficiencies=req.skill_proficiencies,
                feat=req.feat,
                cantrips=req.cantrips,
                alignment=req.alignment,
                pronouns=req.pronouns,
                title=req.title,
                dialogue_style=req.dialogue_style,
                physical_description=req.physical_description,
                backstory=req.backstory,
                personality_traits=req.personality_traits,
                flaws=req.flaws,
                bonds=req.bonds,
                ideals=req.ideals,
                keepsake_name=req.keepsake_name,
            )
            
            # Insert into state.
            self._state.characters[char_id] = sheet
            
            # Occupy the starting cell.
            room = self._state.rooms[self._state.current_room_id]
            cell = grid.get_cell(room, sheet.position)
            cell.occupant_id = char_id
            
            # Update the slot.
            slot.status = SlotStatus.READY
            slot.character_id = char_id
            slot.race = req.race
            slot.evolution_state = req.evolution_state
            slot.predator_role = req.predator_role
            slot.assigned_abilities = req.abilities.model_dump()
            slot.name_draft = req.name
            
            summary = {
                "type": "character_created",
                "slot_index": req.slot_index,
                "character_id": char_id,
                "character": sheet.model_dump(mode="json"),
            }
            await self._commit(summary)
            return summary


    async def transition_room(self, target_room_id: str) -> dict:
        """Move the whole party to a different room (callable from routes)."""
        async with self._lock:
            summary = self._do_transition_room(target_room_id)
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
            
            # Determine initial campaign era
            if any(not c.is_transformed for c in self._state.characters.values()):
                self._state.era = Era.BEFORE
            else:
                self._state.era = Era.AFTER

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

    async def trigger_paradox(self) -> dict:
        """The 'Race Switch' hits. All 'Before' characters become Feral Successors."""
        async with self._lock:
            transformed_ids = []
            for char_id, char in self._state.characters.items():
                if not char.is_transformed:
                    char.is_transformed = True
                    transformed_ids.append(char_id)
            
            # Global era always becomes AFTER when paradox is triggered
            self._state.era = Era.AFTER

            # Narrative event
            msg = "The air screams as the Paradox resolves. The past is rewritten in bone and steel."
            self._state.narrative_log.append(
                NarrativeEntry(
                    revision=self._state.revision + 1,
                    actor_id=None,
                    kind="narration",
                    text=msg,
                    timestamp=dt.datetime.now(dt.timezone.utc).isoformat(),
                )
            )

            summary = {
                "type": "paradox_triggered",
                "transformed_ids": transformed_ids,
                "text": msg
            }
            await self._commit(summary)
            return summary
    
    # ─────────────────── Internal Helpers ───────────────────
    
    def _do_interact(self, char: CharacterSheet, target: Coord) -> dict:
        """
        Resolve an interact action. In priority order:
          1. Target cell is occupied by an NPC → return encounter info.
          2. Target cell is a door with a room exit → transition the party.
          3. Generic interact (usable by freeform narration).
        """
        room = self._state.rooms[self._state.current_room_id]
        cell = grid.get_cell(room, target)

        # 1. NPC encounter
        if cell.occupant_id and cell.occupant_id in self._state.npcs:
            npc = self._state.npcs[cell.occupant_id]
            return {
                "type": "npc_encounter",
                "npc_id": npc.id,
                "npc_name": npc.name,
                "encounter_id": npc.encounter_id,
                "position": target.model_dump(),
            }

        # 2. Door exit
        exit_key = f"{target.x},{target.y}"
        if cell.terrain.value == "door" and exit_key in room.exits:
            return self._do_transition_room(room.exits[exit_key])

        # 3. Generic
        return {"type": "interact", "target": target.model_dump()}

    def _do_transition_room(self, target_room_id: str) -> dict:
        """Transition the entire party to another room (called inside the lock)."""
        if target_room_id not in self._state.rooms:
            raise StateError(f"unknown room: {target_room_id}")

        old_room = self._state.rooms[self._state.current_room_id]
        new_room = self._state.rooms[target_room_id]

        # Vacate all character cells in the old room
        for char in self._state.characters.values():
            try:
                old_cell = grid.get_cell(old_room, char.position)
                if old_cell.occupant_id == char.id:
                    old_cell.occupant_id = None
            except (IndexError, KeyError):
                pass

        self._state.current_room_id = target_room_id
        for char in self._state.characters.values():
            spawn = find_starting_position(self._state)
            char.position = spawn
            char.movement_remaining = char.speed
            grid.get_cell(new_room, spawn).occupant_id = char.id

        return {
            "type": "room_transition",
            "from_room": old_room.id,
            "to_room": target_room_id,
            "room_name": new_room.name,
        }

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
        
        if self._state.phase == TurnPhase.EXPLORATION:
            # In exploration, movement resets after every "stride"
            char.movement_remaining = char.speed
        else:
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
