# 🛠️ StoryForge — Pass 4: Dynamic Character Creation Lobby

> **Pivot acknowledged.** Hardcoded roster scrapped. Replacing it with a **lobby → creation → exploration** state machine where any of four controllers claims a slot by pressing A, then walks through race/class/name selection. The diagram above shows the phase transitions and the new API endpoints landing in this pass.

The shift is bigger than it looks. We're going from "state is the world, characters are part of it" to "state has a *mode*, and the world is only valid in some modes." That changes the validator (characters can be *added* during creation), the persistence model (an empty `characters` dict is now legal), and the entire frontend boot path (Konva doesn't mount until exploration starts).

---

## 1. Decision Manifest — What I'm Locking In

Five new axioms specific to this pass. Push back on any that don't match your intent before you copy the code.

| # | Decision | Reasoning |
|---|---|---|
| **L1** | **`LOBBY` and `CREATION` are separate phases** | Lobby = "waiting for players to claim slots." Creation = "all claimed players are picking race/class/name." This avoids the "is everyone ready?" UI bug where one player is still picking while another already started exploring. |
| **L2** | **Controller-to-slot binding is dynamic and persistent for the session** | When controller index 2 presses A in the lobby, slot index 2 is claimed and *bound* to that controller's GamepadID. Stays bound even if the player disconnects/reconnects mid-session. |
| **L3** | **Stats are server-side generated, not client-input** | Player picks race + class + name. Server rolls (or assigns standard array — see L4) the ability scores. Prevents min-max cheating and keeps the API contract narrow. |
| **L4** | **MVP uses the 5e Standard Array** (15, 14, 13, 12, 10, 8) | No dice rolling for ability scores. Player picks which ability gets which value during creation. Faster, no RNG surprises, family-friendly. Random rolling is a v0.2 toggle. |
| **L5** | **Minimum 1 player to start exploration, maximum 4** | Solo play is supported. The "Start Game" button activates the moment one player completes creation; others can still join in the lobby until someone confirms start. |

---

## 2. Files Touched in This Pass

| Layer | File | Change Type |
|---|---|---|
| Backend | `src/storyforge/core/models.py` | Add `LOBBY` + `CREATION` phases, `CharacterCreationRequest`, `Race`/`ClassDef` enums, lobby slot model |
| Backend | `src/storyforge/core/character_factory.py` | **NEW** — Race + class catalog, stat assignment, starting position picker |
| Backend | `src/storyforge/core/state_manager.py` | Add `claim_slot`, `release_slot`, `create_character`, `start_exploration` mutators |
| Backend | `src/storyforge/core/validators.py` | Allow empty characters dict during LOBBY/CREATION phases |
| Backend | `src/storyforge/api/routes_lobby.py` | **NEW** — Lobby join/leave, character creation, start game |
| Backend | `src/storyforge/api/routes_action.py` | Reject grid/freeform actions outside EXPLORATION phase |
| Backend | `src/storyforge/main.py` | Mount new lobby router |
| Backend | `data/seeds/default_campaign.json` | Replace with empty-character seed |
| Frontend | `frontend/index.html` | Add lobby + creation screens, hide canvas until exploration |
| Frontend | `frontend/css/lobby.css` | **NEW** — Lobby/creation screen styling |
| Frontend | `frontend/js/lobby.js` | **NEW** — Lobby/creation state machine + UI |
| Frontend | `frontend/js/gamepad.js` | Drop hardcoded index mapping, add `slot_claim` event |
| Frontend | `frontend/js/api.js` | Add lobby endpoint wrappers |
| Frontend | `frontend/js/main.js` | Phase-based view router, defer Konva mount |

That's ~480 lines of new code, ~120 lines modified. Manageable in one sitting.

---

## 3. Backend Changes

### 3.1 `src/storyforge/core/models.py` — Diff

Three additions and one enum extension. Keeping the existing models intact; appending new ones at the bottom and modifying `TurnPhase` + `GameState`.

```python
# ─── MODIFIED: TurnPhase enum gets two new values ─────────────────────
class TurnPhase(StrEnum):
    LOBBY = "lobby"              # NEW: waiting for slot claims
    CREATION = "creation"        # NEW: claimed players picking race/class/name
    EXPLORATION = "exploration"
    COMBAT = "combat"
```

```python
# ─── NEW: Race + Class catalog enums ──────────────────────────────────
class Race(StrEnum):
    HUMAN = "human"
    ELF = "elf"
    DWARF = "dwarf"
    HALFLING = "halfling"
    HALF_ORC = "half_orc"
    TIEFLING = "tiefling"


class CharClass(StrEnum):
    FIGHTER = "fighter"
    WIZARD = "wizard"
    ROGUE = "rogue"
    CLERIC = "cleric"
    RANGER = "ranger"
    BARBARIAN = "barbarian"
```

```python
# ─── NEW: Lobby slot tracking ─────────────────────────────────────────
class SlotStatus(StrEnum):
    EMPTY = "empty"               # no controller claimed
    CLAIMED = "claimed"           # controller bound, no character yet
    CREATING = "creating"         # player is picking race/class/name
    READY = "ready"               # character finalized, waiting for others


class LobbySlot(BaseModel):
    """One of up to 4 player slots in the lobby."""
    slot_index: int = Field(ge=0, le=3)
    status: SlotStatus = SlotStatus.EMPTY
    controller_id: str | None = None      # GamepadID string from frontend
    character_id: str | None = None        # set when SlotStatus.READY
    
    # Creation-phase scratch space — what the player has picked so far
    chosen_name: str | None = None
    chosen_race: Race | None = None
    chosen_class: CharClass | None = None
    chosen_ability_layout: dict[str, int] | None = None  # AbilityScores draft


# ─── NEW: Character creation request payload ──────────────────────────
class CharacterCreationRequest(BaseModel):
    """POST body for /api/character/create."""
    slot_index: int = Field(ge=0, le=3)
    name: str = Field(min_length=1, max_length=24)
    race: Race
    char_class: CharClass
    # Player chose which ability gets which standard-array value.
    # Must be a permutation of [15, 14, 13, 12, 10, 8].
    abilities: AbilityScores
```

```python
# ─── MODIFIED: GameState gets a lobby field, characters defaults empty ──
class GameState(BaseModel):
    """Root state object."""
    campaign_id: str
    current_room_id: str
    phase: TurnPhase = TurnPhase.LOBBY  # CHANGED: default to LOBBY, not EXPLORATION
    
    # CHANGED: characters now defaults to empty dict
    characters: dict[str, CharacterSheet] = Field(default_factory=dict)
    rooms: dict[str, Room]
    combat: CombatState | None = None
    
    # NEW: lobby state lives on the root so it persists with the campaign
    lobby_slots: list[LobbySlot] = Field(
        default_factory=lambda: [LobbySlot(slot_index=i) for i in range(4)]
    )
    
    narrative_log: list[NarrativeEntry] = Field(default_factory=list)
    revision: int = 0
```

**Teaching note on persisting lobby state:** Putting `lobby_slots` on `GameState` (instead of in a separate in-memory dict) means that if you close the browser mid-character-creation, the next page load picks up exactly where you left off — slot 1's chosen race is still "elf," slot 2 is still picking, etc. The atomic-write persistence layer from Pass 2 gives us this for free. The trade-off is that lobby chatter writes to disk; for a 4-slot lobby with maybe 20 mutations total during creation, that's negligible.

### 3.2 `src/storyforge/core/character_factory.py` — NEW File

The catalog and the assembler. Race definitions, class definitions, starting equipment, and the deterministic builder that turns a `CharacterCreationRequest` into a fully-populated `CharacterSheet`.

```python
"""
Character factory: builds CharacterSheet instances from creation requests.

This module is the single source of truth for race/class mechanics.
Race grants ability bonuses + speed; class grants HP, hit die, starting
inventory, and proficiency bonus. The factory composes both and adds a
starting position (an empty floor cell near the southern entrance).

Standard Array for MVP: [15, 14, 13, 12, 10, 8].
The player has already assigned these to abilities client-side; the
factory just validates the permutation and applies racial bonuses.
"""
from __future__ import annotations
import secrets
from dataclasses import dataclass

from storyforge.core import grid
from storyforge.core.models import (
    AbilityScores, CharacterSheet, CharClass, Coord, GameState,
    InventoryItem, Race,
)


STANDARD_ARRAY = (15, 14, 13, 12, 10, 8)


# ─────────────────────── Race definitions ───────────────────────

@dataclass(frozen=True)
class RaceDef:
    name: str
    speed: int
    ability_bonuses: dict[str, int]   # e.g. {"STR": 2, "CON": 1}
    flavor: str


RACES: dict[Race, RaceDef] = {
    Race.HUMAN: RaceDef(
        name="Human",
        speed=30,
        ability_bonuses={"STR": 1, "DEX": 1, "CON": 1, "INT": 1, "WIS": 1, "CHA": 1},
        flavor="Versatile and adaptable. +1 to every ability score.",
    ),
    Race.ELF: RaceDef(
        name="Elf",
        speed=30,
        ability_bonuses={"DEX": 2, "INT": 1},
        flavor="Graceful and keen-eyed. Darkvision and fey ancestry.",
    ),
    Race.DWARF: RaceDef(
        name="Dwarf",
        speed=25,
        ability_bonuses={"CON": 2, "WIS": 1},
        flavor="Stout and resilient. Stonecunning and poison resistance.",
    ),
    Race.HALFLING: RaceDef(
        name="Halfling",
        speed=25,
        ability_bonuses={"DEX": 2, "CHA": 1},
        flavor="Small, brave, and lucky. Hard to scare, easy to underestimate.",
    ),
    Race.HALF_ORC: RaceDef(
        name="Half-Orc",
        speed=30,
        ability_bonuses={"STR": 2, "CON": 1},
        flavor="Fierce and enduring. Relentless in the face of death.",
    ),
    Race.TIEFLING: RaceDef(
        name="Tiefling",
        speed=30,
        ability_bonuses={"INT": 1, "CHA": 2},
        flavor="Infernal heritage. Fire resistance and arcane intuition.",
    ),
}


# ─────────────────────── Class definitions ───────────────────────

@dataclass(frozen=True)
class ClassDef:
    name: str
    hit_die: int             # d-X for HP at level up; level 1 = max + CON mod
    base_armor_class: int    # AC before DEX/shield (10 = unarmored baseline)
    starting_inventory: tuple[InventoryItem, ...]
    flavor: str


def _item(item_id: str, name: str, equipped: bool = False, qty: int = 1,
          notes: str | None = None) -> InventoryItem:
    return InventoryItem(id=item_id, name=name, quantity=qty,
                         equipped=equipped, notes=notes)


CLASSES: dict[CharClass, ClassDef] = {
    CharClass.FIGHTER: ClassDef(
        name="Fighter",
        hit_die=10,
        base_armor_class=16,    # chain mail + shield
        starting_inventory=(
            _item("longsword", "Longsword", equipped=True),
            _item("shield", "Shield", equipped=True),
            _item("chain_mail", "Chain Mail", equipped=True),
            _item("rations_5", "Trail Rations", qty=5),
        ),
        flavor="Master of arms and armor. Frontline brawler.",
    ),
    CharClass.WIZARD: ClassDef(
        name="Wizard",
        hit_die=6,
        base_armor_class=11,    # unarmored + DEX
        starting_inventory=(
            _item("quarterstaff", "Quarterstaff", equipped=True),
            _item("spellbook", "Spellbook", notes="bound in violet leather"),
            _item("component_pouch", "Component Pouch"),
            _item("ink_quill", "Ink and Quill"),
        ),
        flavor="Scholar of arcane forces. Fragile but devastating.",
    ),
    CharClass.ROGUE: ClassDef(
        name="Rogue",
        hit_die=8,
        base_armor_class=13,    # leather armor + DEX
        starting_inventory=(
            _item("shortsword", "Shortsword", equipped=True),
            _item("dagger", "Dagger", equipped=True),
            _item("leather_armor", "Leather Armor", equipped=True),
            _item("thieves_tools", "Thieves' Tools"),
        ),
        flavor="Light-footed opportunist. Sneak attack and lockpicking.",
    ),
    CharClass.CLERIC: ClassDef(
        name="Cleric",
        hit_die=8,
        base_armor_class=16,    # chain mail + shield
        starting_inventory=(
            _item("mace", "Mace", equipped=True),
            _item("shield", "Shield", equipped=True),
            _item("chain_mail", "Chain Mail", equipped=True),
            _item("holy_symbol", "Holy Symbol"),
        ),
        flavor="Divine conduit. Healing, blessings, and radiant strikes.",
    ),
    CharClass.RANGER: ClassDef(
        name="Ranger",
        hit_die=10,
        base_armor_class=14,    # studded leather + DEX
        starting_inventory=(
            _item("longbow", "Longbow", equipped=True),
            _item("arrows", "Arrows", qty=20),
            _item("studded_leather", "Studded Leather", equipped=True),
            _item("explorers_pack", "Explorer's Pack"),
        ),
        flavor="Wilderness scout. Bow and tracker.",
    ),
    CharClass.BARBARIAN: ClassDef(
        name="Barbarian",
        hit_die=12,
        base_armor_class=14,    # unarmored defense, assume DEX + CON
        starting_inventory=(
            _item("greataxe", "Greataxe", equipped=True),
            _item("handaxe_2", "Handaxes", qty=2),
            _item("explorers_pack", "Explorer's Pack"),
        ),
        flavor="Primal warrior. Reckless rage and raw toughness.",
    ),
}


# ─────────────────────── Validation helpers ───────────────────────

def is_valid_standard_array(abilities: AbilityScores) -> bool:
    """True if the AbilityScores are a permutation of [15,14,13,12,10,8]."""
    values = sorted([
        abilities.STR, abilities.DEX, abilities.CON,
        abilities.INT, abilities.WIS, abilities.CHA,
    ], reverse=True)
    return tuple(values) == STANDARD_ARRAY


def _ability_modifier(score: int) -> int:
    """D&D 5e ability modifier: floor((score - 10) / 2)."""
    return (score - 10) // 2


# ─────────────────────── The factory ───────────────────────

def build_character(
    *,
    char_id: str,
    player: str,
    name: str,
    race: Race,
    char_class: CharClass,
    base_abilities: AbilityScores,
    starting_position: Coord,
) -> CharacterSheet:
    """
    Compose a CharacterSheet from a creation request.
    
    Applies racial bonuses on top of the player's standard-array assignment,
    rolls level-1 HP at max (PHB convention), and copies the class's
    starting inventory.
    """
    if not is_valid_standard_array(base_abilities):
        raise ValueError(
            "abilities must be a permutation of the standard array "
            f"{STANDARD_ARRAY}"
        )
    
    race_def = RACES[race]
    class_def = CLASSES[char_class]
    
    # Apply racial bonuses
    bumped = base_abilities.model_dump()
    for ability, bonus in race_def.ability_bonuses.items():
        bumped[ability] += bonus
    final_abilities = AbilityScores.model_validate(bumped)
    
    # Level 1 HP: hit die max + CON modifier (5e PHB rule)
    con_mod = _ability_modifier(final_abilities.CON)
    hp_max = class_def.hit_die + con_mod
    
    return CharacterSheet(
        id=char_id,
        name=name,
        player=player,
        char_class=class_def.name,
        level=1,
        hp_current=hp_max,
        hp_max=hp_max,
        armor_class=class_def.base_armor_class,
        speed=race_def.speed,
        abilities=final_abilities,
        proficiency_bonus=2,
        inventory=list(class_def.starting_inventory),
        position=starting_position,
        movement_remaining=race_def.speed,
        conditions=[],
    )


# ─────────────────────── Starting position picker ───────────────────────

def find_starting_position(state: GameState) -> Coord:
    """
    Find an empty floor cell near the southern entrance for a new character.
    
    Scans row 6 (the row we used in the original seed) left-to-right for
    the first unoccupied floor cell. Falls back to a broader scan if row 6
    is full.
    """
    room = state.rooms[state.current_room_id]
    
    # Preferred row: same row the original hardcoded characters used
    preferred_y = 6 if room.height > 6 else room.height - 2
    
    for y in [preferred_y, preferred_y - 1, preferred_y + 1] + list(range(room.height)):
        if y < 0 or y >= room.height:
            continue
        for x in range(room.width):
            coord = Coord(x=x, y=y)
            cell = grid.get_cell(room, coord)
            if grid.is_traversable(cell):
                return coord
    
    raise RuntimeError("no traversable cells available for new character")


# ─────────────────────── Char ID generator ───────────────────────

def generate_char_id(name: str, existing: set[str]) -> str:
    """Slugify name and append a short token if collision."""
    slug = "".join(c.lower() for c in name if c.isalnum()) or "char"
    if slug not in existing:
        return slug
    suffix = secrets.token_hex(2)
    return f"{slug}_{suffix}"
```

**Teaching note on the standard array validation:** I'm checking *after* the player has assigned values, not letting the client tell me "I rolled these." If the player sends `{STR: 20, DEX: 20, ...}`, the `is_valid_standard_array` check rejects it before any HP/AC math runs. The validator never trusts client input on stat values — only on the *permutation* of the canonical six values.

### 3.3 `src/storyforge/core/state_manager.py` — Diff

Four new public mutators bolted onto the existing class. All follow the same pattern: acquire lock → mutate state → call `_commit` so persistence and event broadcast happen.

```python
# Add these imports at the top
from storyforge.core.character_factory import (
    build_character, find_starting_position, generate_char_id,
)
from storyforge.core.models import (
    CharacterCreationRequest, CharClass, LobbySlot, Race,
    SlotStatus,
)
```

```python
# Add these new methods inside the StateManager class

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
```

### 3.4 `src/storyforge/core/validators.py` — Diff

The original validator was written assuming characters always exist. We need to soften that during LOBBY/CREATION phases since character mutations don't apply to nonexistent characters.

```python
# Modify the top of sanitize() to short-circuit non-exploration phases:

def sanitize(
    state: GameState,
    proposed: StateDiff,
) -> tuple[StateDiff, list[str]]:
    """Return (safe_diff, rejection_messages)."""
    rejections: list[str] = []
    safe = StateDiff()
    
    # During lobby/creation, AI shouldn't be proposing diffs at all —
    # but if it does (e.g. from a leftover narration call), reject everything.
    if state.phase in (TurnPhase.LOBBY, TurnPhase.CREATION):
        rejections.append(
            f"AI diffs are not accepted during {state.phase.value} phase"
        )
        return safe, rejections
    
    # Original sanitize logic continues below unchanged...
    safe.character_updates = _filter_char_updates(...)
```

### 3.5 `src/storyforge/api/routes_lobby.py` — NEW File

Four endpoints. All thin — they delegate to `StateManager` mutators and let the lock-and-commit machinery do its job.

```python
"""
Lobby + character creation routes.

Endpoints:
    POST /api/lobby/join      — claim a slot with a controller ID
    POST /api/lobby/leave     — release a slot
    POST /api/character/create — finalize a slot into a CharacterSheet
    POST /api/lobby/start     — transition to EXPLORATION
    GET  /api/lobby/catalog   — race + class definitions for the UI
"""
from __future__ import annotations
from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field

from storyforge.api.deps import get_state_manager
from storyforge.core.character_factory import CLASSES, RACES
from storyforge.core.models import CharacterCreationRequest
from storyforge.core.state_manager import StateError, StateManager


router = APIRouter(prefix="/api", tags=["lobby"])


# ───────────────────────── Request models ─────────────────────────

class JoinRequest(BaseModel):
    controller_id: str = Field(min_length=1, max_length=200)


class LeaveRequest(BaseModel):
    controller_id: str = Field(min_length=1, max_length=200)


# ───────────────────────── Endpoints ─────────────────────────

@router.get("/lobby/catalog")
async def get_catalog() -> dict:
    """Static reference data for the creation UI. Cached client-side."""
    return {
        "races": {
            race.value: {
                "name": rdef.name,
                "speed": rdef.speed,
                "ability_bonuses": rdef.ability_bonuses,
                "flavor": rdef.flavor,
            }
            for race, rdef in RACES.items()
        },
        "classes": {
            klass.value: {
                "name": cdef.name,
                "hit_die": cdef.hit_die,
                "base_armor_class": cdef.base_armor_class,
                "starting_inventory": [
                    item.model_dump(mode="json") for item in cdef.starting_inventory
                ],
                "flavor": cdef.flavor,
            }
            for klass, cdef in CLASSES.items()
        },
        "standard_array": [15, 14, 13, 12, 10, 8],
    }


@router.post("/lobby/join")
async def join_lobby(
    req: JoinRequest,
    state: StateManager = Depends(get_state_manager),
) -> dict:
    try:
        return await state.claim_slot(controller_id=req.controller_id)
    except StateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/lobby/leave")
async def leave_lobby(
    req: LeaveRequest,
    state: StateManager = Depends(get_state_manager),
) -> dict:
    try:
        return await state.release_slot(controller_id=req.controller_id)
    except StateError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/character/create")
async def create_character(
    req: CharacterCreationRequest,
    state: StateManager = Depends(get_state_manager),
) -> dict:
    try:
        return await state.create_character(req)
    except (StateError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/lobby/start")
async def start_game(
    state: StateManager = Depends(get_state_manager),
) -> dict:
    try:
        return await state.start_exploration()
    except StateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
```

### 3.6 `src/storyforge/api/routes_action.py` — Diff

Reject actions during non-exploration phases. Two-line addition to each handler.

```python
# At the top of handle_grid():
async def handle_grid(
    action: GridAction,
    state: StateManager = Depends(get_state_manager),
) -> dict:
    """Structured click → deterministic mutation → flavor narration."""
    if state.current.phase != TurnPhase.EXPLORATION:
        raise HTTPException(
            status_code=409,
            detail=f"grid actions require EXPLORATION phase, "
                   f"currently {state.current.phase.value}",
        )
    
    char = state.get_character(action.actor_id)
    # ... rest of handler unchanged
```

```python
# At the top of handle_freeform(), same pattern:
async def handle_freeform(
    action: FreeformAction,
    state: StateManager = Depends(get_state_manager),
) -> dict:
    if state.current.phase != TurnPhase.EXPLORATION:
        raise HTTPException(
            status_code=409,
            detail=f"freeform actions require EXPLORATION phase, "
                   f"currently {state.current.phase.value}",
        )
    
    # ... rest of handler unchanged
```

### 3.7 `src/storyforge/main.py` — Diff

Mount the new router.

```python
# Add the import:
from storyforge.api import routes_state, routes_action, routes_lobby, ws_session

# In the app setup:
app.include_router(routes_state.router)
app.include_router(routes_action.router)
app.include_router(routes_lobby.router)   # NEW
app.include_router(ws_session.router)
```

### 3.8 `data/seeds/default_campaign.json` — Replace

Empty characters, empty lobby slots, phase = `lobby`. The room and the bard stay.

```json
{
  "campaign_id": "family_campaign_01",
  "current_room_id": "tavern_01",
  "phase": "lobby",
  "revision": 0,
  "narrative_log": [],
  "characters": {},
  "lobby_slots": [
    {"slot_index": 0, "status": "empty", "controller_id": null, "character_id": null,
     "chosen_name": null, "chosen_race": null, "chosen_class": null, "chosen_ability_layout": null},
    {"slot_index": 1, "status": "empty", "controller_id": null, "character_id": null,
     "chosen_name": null, "chosen_race": null, "chosen_class": null, "chosen_ability_layout": null},
    {"slot_index": 2, "status": "empty", "controller_id": null, "character_id": null,
     "chosen_name": null, "chosen_race": null, "chosen_class": null, "chosen_ability_layout": null},
    {"slot_index": 3, "status": "empty", "controller_id": null, "character_id": null,
     "chosen_name": null, "chosen_race": null, "chosen_class": null, "chosen_ability_layout": null}
  ],
  "rooms": {
    "tavern_01": {
      "id": "tavern_01",
      "name": "The Crooked Tankard",
      "width": 10,
      "height": 8,
      "description": "A cramped common room with low oak beams smoke-stained nearly black. A stone hearth dominates the back wall. Two round tables sit askew between you and the bar. A bard tunes a lute in the far corner.",
      "cells": [
        {"terrain":"wall","occupant_id":null},{"terrain":"wall","occupant_id":null},{"terrain":"wall","occupant_id":null},{"terrain":"wall","occupant_id":null},{"terrain":"wall","occupant_id":null},{"terrain":"wall","occupant_id":null},{"terrain":"wall","occupant_id":null},{"terrain":"wall","occupant_id":null},{"terrain":"wall","occupant_id":null},{"terrain":"wall","occupant_id":null},
        {"terrain":"wall","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"hazard","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":"bard"},{"terrain":"floor","occupant_id":null},{"terrain":"wall","occupant_id":null},
        {"terrain":"wall","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"wall","occupant_id":null},
        {"terrain":"wall","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"difficult","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"difficult","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"wall","occupant_id":null},
        {"terrain":"wall","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"difficult","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"difficult","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"wall","occupant_id":null},
        {"terrain":"wall","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"wall","occupant_id":null},
        {"terrain":"wall","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"wall","occupant_id":null},
        {"terrain":"wall","occupant_id":null},{"terrain":"wall","occupant_id":null},{"terrain":"wall","occupant_id":null},{"terrain":"wall","occupant_id":null},{"terrain":"wall","occupant_id":null},{"terrain":"door","occupant_id":null},{"terrain":"wall","occupant_id":null},{"terrain":"wall","occupant_id":null},{"terrain":"wall","occupant_id":null},{"terrain":"wall","occupant_id":null}
      ]
    }
  },
  "combat": null
}
```

---

## 4. Frontend Changes

### 4.1 `frontend/index.html` — Diff

Three new screens (lobby, creation, the existing game view) wrapped in a single shell. Only one is visible at a time, controlled by `data-phase` on `<body>`.

```html
<!DOCTYPE html>
<html lang="en" data-paper="vellum" data-ink="midnight">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>StoryForge</title>
  <script src="https://unpkg.com/konva@9.3.16/konva.min.js"></script>
  <link rel="stylesheet" href="/static/css/styles.css" />
  <link rel="stylesheet" href="/static/css/parchment.css" />
  <link rel="stylesheet" href="/static/css/ink-effects.css" />
  <link rel="stylesheet" href="/static/css/lobby.css" />
</head>
<body data-phase="lobby">

  <!-- ─────── LOBBY VIEW ─────── -->
  <section id="lobby-view" class="phase-view parchment-surface">
    <h1 class="lobby-title ink-gilded">StoryForge</h1>
    <p class="lobby-subtitle">Press <kbd>A</kbd> on any controller to join the table</p>
    
    <div id="lobby-slots" class="lobby-slot-grid">
      <!-- Populated by lobby.js -->
    </div>
    
    <div class="lobby-actions">
      <button id="start-game-btn" class="btn btn-primary" disabled>
        Begin Adventure
      </button>
      <p class="lobby-hint">
        At least one character must be ready. Press <kbd>Start</kbd> on any controller.
      </p>
    </div>
  </section>

  <!-- ─────── CREATION VIEW ─────── -->
  <section id="creation-view" class="phase-view parchment-surface hidden">
    <h1 class="creation-title ink-gilded">Forge Your Hero</h1>
    
    <div class="creation-steps">
      <div class="step-pill" data-step="race">1. Race</div>
      <div class="step-pill" data-step="class">2. Class</div>
      <div class="step-pill" data-step="abilities">3. Abilities</div>
      <div class="step-pill" data-step="name">4. Name</div>
    </div>
    
    <div id="creation-stage" class="creation-stage">
      <!-- Active step's content rendered here by lobby.js -->
    </div>
    
    <div class="creation-controls">
      <button id="creation-back" class="btn">Back</button>
      <span id="creation-slot-label" class="creation-slot-label">Slot —</span>
      <button id="creation-next" class="btn btn-primary">Next</button>
    </div>
  </section>

  <!-- ─────── GAME VIEW (existing) ─────── -->
  <div id="game-view" class="hidden">
    <header id="party-bar" class="party-bar parchment-strip">
      <div class="portrait-row" id="portrait-row"></div>
      <div class="status-cluster">
        <span id="kbd-indicator" class="indicator">⌨ <span>KBD</span></span>
        <span id="gamepad-indicator" class="indicator">
          🎮 <span id="gp-slot-0">·</span><span id="gp-slot-1">·</span><span id="gp-slot-2">·</span><span id="gp-slot-3">·</span>
        </span>
      </div>
    </header>

    <main id="stage">
      <section id="canvas-pane" class="parchment-surface">
        <div id="konva-mount"></div>
      </section>
      <aside id="log-pane" class="parchment-surface ink-midnight">
        <h2 class="log-title">Chronicle</h2>
        <ol id="narrative-log" class="narrative-log"></ol>
      </aside>
    </main>

    <footer id="action-bar" class="action-bar parchment-strip">
      <div id="active-summary" class="active-summary">
        <span class="label">Active:</span>
        <span id="active-name" class="active-name ink-gilded">—</span>
        <span id="active-class" class="active-class">—</span>
        <span class="stat">HP <span id="active-hp">—</span></span>
        <span class="stat">AC <span id="active-ac">—</span></span>
        <span class="stat">MOVE <span id="active-move">—</span></span>
        <span class="stat">POS <span id="active-pos">—</span></span>
      </div>
      <div class="hints">
        <span class="hint"><kbd>A</kbd> Confirm</span>
        <span class="hint"><kbd>B</kbd> Cancel</span>
        <span class="hint"><kbd>Y</kbd> Speak</span>
        <span class="hint"><kbd>LB</kbd>/<kbd>RB</kbd> Cycle</span>
      </div>
    </footer>
  </div>

  <!-- ─────── FREEFORM MODAL (unchanged) ─────── -->
  <div id="freeform-modal" class="modal hidden" role="dialog" aria-modal="true">
    <div class="modal-card parchment-surface">
      <h2 class="ink-crimson">Speak Your Action</h2>
      <p class="hint-small">Press <kbd>Esc</kbd> or <kbd>B</kbd> to cancel · <kbd>Enter</kbd> to commit</p>
      <textarea id="freeform-input" rows="4" maxlength="500"
                placeholder="I creep along the shadowed wall toward the bard..."></textarea>
      <div class="modal-actions">
        <button id="freeform-cancel" class="btn">Cancel</button>
        <button id="freeform-commit" class="btn btn-primary">Commit</button>
      </div>
    </div>
  </div>

  <script type="module" src="/static/js/main.js"></script>
</body>
</html>
```

The body's `data-phase` attribute is the master switch. CSS targets it to show/hide the right view.

### 4.2 `frontend/css/lobby.css` — NEW File

```css
/* ═══════════════════════════════════════════════════════════════════════
   Lobby + Creation Screens
   Phase-based visibility controlled by body[data-phase].
   ═══════════════════════════════════════════════════════════════════════ */

.phase-view {
  position: fixed;
  inset: 0;
  padding: var(--space-5);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  gap: var(--space-4);
  overflow-y: auto;
}

.hidden { display: none !important; }

/* Body-driven view switching */
body[data-phase="lobby"]       #lobby-view    { display: flex; }
body[data-phase="lobby"]       #creation-view,
body[data-phase="lobby"]       #game-view     { display: none; }

body[data-phase="creation"]    #creation-view { display: flex; }
body[data-phase="creation"]    #lobby-view,
body[data-phase="creation"]    #game-view     { display: none; }

body[data-phase="exploration"] #game-view     { display: grid; grid-template-rows: var(--top-h) 1fr var(--bottom-h); position: fixed; inset: 0; }
body[data-phase="exploration"] #lobby-view,
body[data-phase="exploration"] #creation-view { display: none; }

/* ─── Lobby ─── */
.lobby-title {
  font-size: var(--fs-display);
  margin: var(--space-3) 0 0 0;
  letter-spacing: 0.03em;
}

.lobby-subtitle {
  font-size: var(--fs-lg);
  margin: 0;
  opacity: 0.85;
}

.lobby-subtitle kbd {
  background: var(--ink-midnight);
  color: #f4ead4;
  padding: 0.2rem 0.8rem;
  border-radius: 6px;
  font-family: "JetBrains Mono", monospace;
}

.lobby-slot-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(280px, 1fr));
  gap: var(--space-4);
  width: min(95vw, 1200px);
}

.lobby-slot {
  border: 4px solid var(--ink-midnight);
  border-radius: 16px;
  padding: var(--space-4);
  min-height: 220px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: var(--space-2);
  background: rgba(255, 245, 220, 0.55);
  transition: all 0.18s ease;
  position: relative;
}

.lobby-slot[data-status="empty"] {
  border-style: dashed;
  opacity: 0.55;
}

.lobby-slot[data-status="claimed"] {
  border-color: var(--ink-gilded);
  box-shadow: var(--glow-gold);
}

.lobby-slot[data-status="creating"] {
  border-color: var(--ink-violet);
  box-shadow: 0 0 1.5rem rgba(74, 26, 107, 0.5);
}

.lobby-slot[data-status="ready"] {
  border-color: var(--ink-emerald);
  background: rgba(220, 245, 220, 0.7);
  box-shadow: 0 0 1.5rem rgba(30, 90, 58, 0.4);
}

.slot-index {
  font-size: var(--fs-xl);
  font-weight: 700;
  color: var(--ink-burgundy);
}

.slot-status-text {
  font-size: var(--fs-lg);
  font-style: italic;
}

.slot-character-preview {
  font-size: var(--fs-base);
  text-align: center;
  line-height: 1.4;
}

.slot-character-preview .char-name {
  font-size: var(--fs-lg);
  font-weight: 700;
}

.lobby-actions {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  margin-top: var(--space-3);
}

#start-game-btn {
  font-size: var(--fs-xl);
  padding: var(--space-3) var(--space-5);
  min-width: 400px;
}

#start-game-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.lobby-hint {
  font-size: var(--fs-sm);
  opacity: 0.7;
  margin: 0;
}

/* ─── Creation ─── */
.creation-title {
  font-size: var(--fs-display);
  margin: 0;
}

.creation-steps {
  display: flex;
  gap: var(--space-3);
  font-size: var(--fs-base);
}

.step-pill {
  padding: var(--space-2) var(--space-3);
  border: 3px solid var(--ink-midnight);
  border-radius: 999px;
  opacity: 0.4;
  transition: opacity 0.18s, background 0.18s;
}

.step-pill.active {
  opacity: 1;
  background: var(--ink-gilded);
  color: var(--ink-midnight);
  font-weight: 700;
}

.step-pill.done {
  opacity: 0.85;
  background: rgba(30, 90, 58, 0.3);
}

.creation-stage {
  flex: 1;
  width: min(95vw, 1400px);
  display: grid;
  gap: var(--space-3);
  align-content: start;
}

/* Race + Class grid */
.option-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: var(--space-3);
}

.option-card {
  border: 4px solid var(--ink-midnight);
  border-radius: 12px;
  padding: var(--space-3);
  background: rgba(255, 245, 220, 0.6);
  cursor: pointer;
  transition: transform 0.12s, box-shadow 0.12s, border-color 0.12s;
}

.option-card:hover,
.option-card.focused {
  transform: translateY(-4px);
  box-shadow: var(--glow-gold);
}

.option-card.selected {
  border-color: var(--ink-emerald);
  background: rgba(220, 245, 220, 0.8);
}

.option-card h3 {
  margin: 0 0 var(--space-1) 0;
  font-size: var(--fs-lg);
}

.option-card .flavor {
  font-size: var(--fs-base);
  margin: 0 0 var(--space-2) 0;
  font-style: italic;
  opacity: 0.85;
}

.option-card .stats {
  font-size: var(--fs-sm);
  font-family: "JetBrains Mono", monospace;
  opacity: 0.85;
}

/* Ability assignment */
.ability-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-4);
  max-width: 900px;
  margin: 0 auto;
}

.ability-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) var(--space-3);
  border: 3px solid var(--ink-midnight);
  border-radius: 8px;
  background: rgba(255, 245, 220, 0.7);
  font-size: var(--fs-lg);
}

.ability-row.focused {
  box-shadow: var(--glow-gold);
}

.ability-name { font-weight: 700; }

.ability-value {
  font-family: "JetBrains Mono", monospace;
  font-size: var(--fs-xl);
  font-weight: 700;
  color: var(--ink-burgundy);
  min-width: 3rem;
  text-align: center;
}

.ability-pool {
  display: flex;
  gap: var(--space-2);
  justify-content: center;
  flex-wrap: wrap;
  margin-top: var(--space-3);
}

.ability-chip {
  font-family: "JetBrains Mono", monospace;
  font-size: var(--fs-lg);
  font-weight: 700;
  padding: var(--space-2) var(--space-3);
  border: 3px solid var(--ink-midnight);
  border-radius: 8px;
  background: rgba(255, 245, 220, 0.6);
  min-width: 4rem;
  text-align: center;
}

.ability-chip.used { opacity: 0.3; text-decoration: line-through; }

/* Name input */
.name-stage {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  margin-top: var(--space-4);
}

.name-input {
  font-family: "Cardo", Georgia, serif;
  font-size: var(--fs-display);
  text-align: center;
  padding: var(--space-3) var(--space-4);
  border: 4px solid var(--ink-midnight);
  border-radius: 12px;
  background: rgba(255, 245, 220, 0.9);
  color: var(--ink-midnight);
  width: min(80vw, 800px);
  user-select: text;
}

.name-input:focus {
  outline: none;
  box-shadow: var(--glow-gold);
}

.creation-controls {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  width: min(95vw, 1400px);
  justify-content: space-between;
  padding: var(--space-3) 0;
}

.creation-slot-label {
  font-size: var(--fs-base);
  opacity: 0.75;
  font-family: "JetBrains Mono", monospace;
}
```

### 4.3 `frontend/js/gamepad.js` — Diff

Drop the hardcoded `index → character` mapping. Add a stable GamepadID accessor and a `slot_claim_attempt` semantic event so the lobby code doesn't need to inspect button bytes.

```javascript
// Add this near the top:

/**
 * Stable identifier for a connected controller. Combines the gamepad
 * `id` (vendor string, e.g. "Xbox Wireless Controller") with the OS-
 * provided index. Persists across the session so the backend can bind
 * a slot to a specific physical controller.
 */
export function makeControllerId(pad) {
  return `${pad.id}::${pad.index}`;
}
```

```javascript
// Modify the GamepadManager class. Add this method:

/**
 * Get the controller_id string for a specific OS-level controller index.
 * Returns null if no controller is connected at that index.
 */
controllerIdFor(index) {
  const pads = navigator.getGamepads?.() ?? [];
  const pad = pads[index];
  return pad ? makeControllerId(pad) : null;
}
```

```javascript
// Modify _pollButtons to attach controller_id to every event:

_pollButtons(i, pad) {
  const prev = this._prevButtons[i];
  const controllerId = makeControllerId(pad);
  for (let b = 0; b < pad.buttons.length; b++) {
    const pressed = pad.buttons[b].pressed;
    const wasPressed = prev[b] ?? false;
    if (pressed && !wasPressed) {
      this._emit("button_pressed", { index: i, button: b, controllerId });
    } else if (!pressed && wasPressed) {
      this._emit("button_released", { index: i, button: b, controllerId });
    }
    prev[b] = pressed;
  }
}
```

```javascript
// Same for _pollDirection:

_pollDirection(i, pad, nowMs) {
  let dx = 0, dy = 0;
  // ... existing dx/dy detection ...
  
  const controllerId = makeControllerId(pad);
  const hold = this._dirHold[i];
  if (dx === 0 && dy === 0) {
    this._dirHold[i] = null;
    return;
  }
  if (!hold || hold.dx !== dx || hold.dy !== dy) {
    this._dirHold[i] = { dx, dy, sinceMs: nowMs, lastRepeatMs: nowMs };
    this._emit("dpad_repeat", { index: i, dx, dy, controllerId });
    return;
  }
  const heldFor = nowMs - hold.sinceMs;
  const sinceLast = nowMs - hold.lastRepeatMs;
  if (heldFor >= INITIAL_REPEAT_MS && sinceLast >= REPEAT_INTERVAL_MS) {
    hold.lastRepeatMs = nowMs;
    this._emit("dpad_repeat", { index: i, dx, dy, controllerId });
  }
}
```

```javascript
// Also update the controller_connected event:

window.addEventListener("gamepadconnected", (e) => {
  this._connected.add(e.gamepad.index);
  this._emit("controller_connected", {
    index: e.gamepad.index,
    controllerId: makeControllerId(e.gamepad),
  });
});
```

### 4.4 `frontend/js/api.js` — Diff

Add the lobby endpoint wrappers.

```javascript
// Append to the existing file:

export async function fetchCatalog() {
  const res = await fetch(`${API_BASE}/api/lobby/catalog`);
  return jsonOrThrow(res);
}

export async function joinLobby(controllerId) {
  const res = await fetch(`${API_BASE}/api/lobby/join`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ controller_id: controllerId }),
  });
  return jsonOrThrow(res);
}

export async function leaveLobby(controllerId) {
  const res = await fetch(`${API_BASE}/api/lobby/leave`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ controller_id: controllerId }),
  });
  return jsonOrThrow(res);
}

export async function createCharacter({ slotIndex, name, race, charClass, abilities }) {
  const res = await fetch(`${API_BASE}/api/character/create`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      slot_index: slotIndex,
      name,
      race,
      char_class: charClass,
      abilities,
    }),
  });
  return jsonOrThrow(res);
}

export async function startGame() {
  const res = await fetch(`${API_BASE}/api/lobby/start`, {
    method: "POST",
  });
  return jsonOrThrow(res);
}
```

### 4.5 `frontend/js/lobby.js` — NEW File

The state machine for both the lobby and creation screens. Keyboard- and gamepad-driven, no clicks required, but mouse clicks still work as a fallback.

```javascript
/**
 * Lobby + Creation state machine.
 *
 * Two phases this module owns:
 *   LOBBY    — show 4 slot cards; press A on any controller to claim a slot.
 *   CREATION — selected controller walks through race → class → abilities → name.
 *
 * Per-controller creation state is held in `_drafts` keyed by controller_id.
 * Only one draft is "active" (rendering in the creation stage) at a time;
 * we cycle between drafts with LB/RB so multiple players can take turns.
 */

import {
  fetchCatalog, joinLobby, leaveLobby, createCharacter, startGame,
} from "./api.js";

const STANDARD_ARRAY = [15, 14, 13, 12, 10, 8];
const ABILITIES = ["STR", "DEX", "CON", "INT", "WIS", "CHA"];

export class Lobby {
  constructor({ state, audio, onExplorationStarted, onStateRefetch }) {
    this.state = state;
    this.audio = audio;
    this.onExplorationStarted = onExplorationStarted;
    this.onStateRefetch = onStateRefetch;
    
    this.catalog = null;
    this._drafts = new Map();       // controllerId -> draft object
    this._activeControllerId = null; // whose creation flow is on screen
    this._focusIndex = 0;            // for keyboard navigation within a step
    
    this._dom = {
      lobbyView:     document.getElementById("lobby-view"),
      lobbySlots:    document.getElementById("lobby-slots"),
      startBtn:      document.getElementById("start-game-btn"),
      creationView:  document.getElementById("creation-view"),
      stage:         document.getElementById("creation-stage"),
      stepPills:     document.querySelectorAll(".step-pill"),
      slotLabel:     document.getElementById("creation-slot-label"),
      backBtn:       document.getElementById("creation-back"),
      nextBtn:       document.getElementById("creation-next"),
    };
    
    this._dom.startBtn.addEventListener("click", () => this.handleStartGame());
    this._dom.backBtn.addEventListener("click", () => this.handleBack());
    this._dom.nextBtn.addEventListener("click", () => this.handleNext());
  }
  
  async init(currentState) {
    this.catalog = await fetchCatalog();
    this.setState(currentState);
  }
  
  setState(state) {
    this.state = state;
    document.body.dataset.phase = state.phase;
    
    // Hydrate drafts from server-persisted lobby_slots.
    for (const slot of state.lobby_slots) {
      if (slot.status === "creating" || slot.status === "claimed") {
        if (slot.controller_id && !this._drafts.has(slot.controller_id)) {
          this._drafts.set(slot.controller_id, this._draftFromSlot(slot));
        }
      }
    }
    
    if (state.phase === "lobby" || state.phase === "creation") {
      this._renderLobby();
    }
    if (state.phase === "creation") {
      // Auto-focus the first claiming controller if none is active.
      if (!this._activeControllerId) {
        const firstClaiming = state.lobby_slots.find(
          s => s.status === "claimed" || s.status === "creating"
        );
        if (firstClaiming) {
          this._activeControllerId = firstClaiming.controller_id;
        }
      }
      this._renderCreation();
    }
  }
  
  // ─────────────────────── Gamepad / Keyboard input ───────────────────────
  
  handleControllerButton({ controllerId, button }) {
    if (this.state.phase === "lobby" || this.state.phase === "creation") {
      // A = claim slot (if no slot held) or confirm in creation
      if (button === 0) {  // A
        this._handleAButton(controllerId);
      } else if (button === 1) {  // B
        this._handleBButton(controllerId);
      } else if (button === 4 || button === 5) {  // LB/RB
        this._cycleActiveDraft(button === 5 ? +1 : -1);
      } else if (button === 9) {  // Start
        this.handleStartGame();
      }
    }
  }
  
  handleControllerDpad({ controllerId, dx, dy }) {
    if (this.state.phase !== "creation") return;
    if (controllerId !== this._activeControllerId) return;
    this._moveFocus(dx, dy);
  }
  
  handleKeyboard(e) {
    if (this.state.phase === "lobby") {
      if (e.key === "Enter") this.handleStartGame();
      return;
    }
    if (this.state.phase !== "creation") return;
    
    if (e.key === "ArrowLeft")  this._moveFocus(-1, 0);
    if (e.key === "ArrowRight") this._moveFocus(+1, 0);
    if (e.key === "ArrowUp")    this._moveFocus(0, -1);
    if (e.key === "ArrowDown")  this._moveFocus(0, +1);
    if (e.key === "Enter")      this.handleNext();
    if (e.key === "Escape")     this.handleBack();
    if (e.key === "Tab") {
      e.preventDefault();
      this._cycleActiveDraft(e.shiftKey ? -1 : +1);
    }
  }
  
  // ─────────────────────── Slot claim / release ───────────────────────
  
  async _handleAButton(controllerId) {
    // Already in creation? Treat A as "confirm/next".
    if (this._drafts.has(controllerId) && this.state.phase === "creation") {
      if (controllerId === this._activeControllerId) {
        await this.handleNext();
      } else {
        // Take focus.
        this._activeControllerId = controllerId;
        this._renderCreation();
        this.audio?.playCursor();
      }
      return;
    }
    
    // Brand-new claim.
    try {
      const result = await joinLobby(controllerId);
      this.audio?.playConfirm();
      // Initialize an empty draft.
      this._drafts.set(controllerId, {
        controllerId,
        slotIndex: result.slot_index,
        step: "race",
        race: null,
        charClass: null,
        abilities: { STR: null, DEX: null, CON: null, INT: null, WIS: null, CHA: null },
        name: "",
      });
      if (!this._activeControllerId) {
        this._activeControllerId = controllerId;
      }
      await this.onStateRefetch?.();
    } catch (err) {
      console.warn("[lobby] join failed:", err.message);
      this.audio?.playDeny();
    }
  }
  
  async _handleBButton(controllerId) {
    if (!this._drafts.has(controllerId)) return;
    
    if (this.state.phase === "creation") {
      // Back in creation flow first.
      const draft = this._drafts.get(controllerId);
      if (draft.step !== "race") {
        this.handleBack();
        return;
      }
    }
    
    // From race step or lobby: release the slot.
    try {
      await leaveLobby(controllerId);
      this._drafts.delete(controllerId);
      if (this._activeControllerId === controllerId) {
        this._activeControllerId = this._drafts.keys().next().value ?? null;
      }
      this.audio?.playDeny();
      await this.onStateRefetch?.();
    } catch (err) {
      console.warn("[lobby] leave failed:", err.message);
    }
  }
  
  _cycleActiveDraft(direction) {
    const ids = [...this._drafts.keys()];
    if (ids.length === 0) return;
    const currentIdx = ids.indexOf(this._activeControllerId);
    const nextIdx = (currentIdx + direction + ids.length) % ids.length;
    this._activeControllerId = ids[nextIdx];
    this._focusIndex = 0;
    this._renderCreation();
    this.audio?.playCursor();
  }
  
  // ─────────────────────── Step navigation ───────────────────────
  
  async handleNext() {
    if (!this._activeControllerId) return;
    const draft = this._drafts.get(this._activeControllerId);
    if (!draft) return;
    
    const order = ["race", "class", "abilities", "name"];
    const idx = order.indexOf(draft.step);
    
    // Validate current step before advancing.
    if (!this._isStepComplete(draft, draft.step)) {
      this.audio?.playDeny();
      return;
    }
    
    if (idx === order.length - 1) {
      // Final step — commit to server.
      await this._commitDraft(draft);
    } else {
      draft.step = order[idx + 1];
      this._focusIndex = 0;
      this._renderCreation();
      this.audio?.playPageTurn();
    }
  }
  
  handleBack() {
    if (!this._activeControllerId) return;
    const draft = this._drafts.get(this._activeControllerId);
    if (!draft) return;
    
    const order = ["race", "class", "abilities", "name"];
    const idx = order.indexOf(draft.step);
    if (idx === 0) return;  // Can't go back from first step
    
    draft.step = order[idx - 1];
    this._focusIndex = 0;
    this._renderCreation();
    this.audio?.playPageTurn();
  }
  
  async _commitDraft(draft) {
    try {
      await createCharacter({
        slotIndex: draft.slotIndex,
        name: draft.name.trim(),
        race: draft.race,
        charClass: draft.charClass,
        abilities: draft.abilities,
      });
      this.audio?.playConfirm();
      this._drafts.delete(draft.controllerId);
      
      // Move focus to next unfinished draft.
      const ids = [...this._drafts.keys()];
      this._activeControllerId = ids[0] ?? null;
      
      await this.onStateRefetch?.();
    } catch (err) {
      console.error("[creation] commit failed:", err.message);
      this.audio?.playDeny();
    }
  }
  
  async handleStartGame() {
    if (this._dom.startBtn.disabled) return;
    try {
      await startGame();
      this.audio?.playConfirm();
      await this.onStateRefetch?.();
      this.onExplorationStarted?.();
    } catch (err) {
      console.error("[lobby] start failed:", err.message);
      this.audio?.playDeny();
    }
  }
  
  // ─────────────────────── Rendering: lobby ───────────────────────
  
  _renderLobby() {
    this._dom.lobbySlots.innerHTML = "";
    for (const slot of this.state.lobby_slots) {
      const card = document.createElement("div");
      card.className = "lobby-slot";
      card.dataset.status = slot.status;
      
      const idx = document.createElement("div");
      idx.className = "slot-index";
      idx.textContent = `Slot ${slot.slot_index + 1}`;
      card.appendChild(idx);
      
      const status = document.createElement("div");
      status.className = "slot-status-text";
      status.textContent = this._slotStatusText(slot);
      card.appendChild(status);
      
      if (slot.status === "ready" && slot.character_id) {
        const char = this.state.characters[slot.character_id];
        if (char) {
          const preview = document.createElement("div");
          preview.className = "slot-character-preview";
          preview.innerHTML = `
            <div class="char-name ink-gilded">${this._escape(char.name)}</div>
            <div>${this._escape(char.char_class)}</div>
            <div>HP ${char.hp_max} · AC ${char.armor_class}</div>
          `;
          card.appendChild(preview);
        }
      }
      
      this._dom.lobbySlots.appendChild(card);
    }
    
    // Update Start button.
    const readyCount = this.state.lobby_slots.filter(s => s.status === "ready").length;
    this._dom.startBtn.disabled = readyCount < 1;
    this._dom.startBtn.textContent = readyCount > 0
      ? `Begin Adventure (${readyCount} ${readyCount === 1 ? "hero" : "heroes"})`
      : "Begin Adventure";
  }
  
  _slotStatusText(slot) {
    switch (slot.status) {
      case "empty":    return "Press A to join";
      case "claimed":  return "Choosing race...";
      case "creating": return "Forging...";
      case "ready":    return "Ready";
      default:         return slot.status;
    }
  }
  
  // ─────────────────────── Rendering: creation ───────────────────────
  
  _renderCreation() {
    if (!this._activeControllerId) {
      this._dom.stage.innerHTML = "<p>Waiting for players...</p>";
      return;
    }
    const draft = this._drafts.get(this._activeControllerId);
    if (!draft) return;
    
    // Update step pills.
    const stepOrder = ["race", "class", "abilities", "name"];
    const currentIdx = stepOrder.indexOf(draft.step);
    this._dom.stepPills.forEach((pill, i) => {
      pill.classList.remove("active", "done");
      if (i === currentIdx) pill.classList.add("active");
      if (i < currentIdx)  pill.classList.add("done");
    });
    
    this._dom.slotLabel.textContent =
      `Slot ${draft.slotIndex + 1} of ${this._drafts.size}`;
    
    // Render the current step.
    this._dom.stage.innerHTML = "";
    switch (draft.step) {
      case "race":      this._renderRaceStep(draft); break;
      case "class":     this._renderClassStep(draft); break;
      case "abilities": this._renderAbilitiesStep(draft); break;
      case "name":      this._renderNameStep(draft); break;
    }
  }
  
  _renderRaceStep(draft) {
    const grid = document.createElement("div");
    grid.className = "option-grid";
    
    const entries = Object.entries(this.catalog.races);
    entries.forEach(([raceKey, rdef], idx) => {
      const card = document.createElement("div");
      card.className = "option-card";
      if (draft.race === raceKey) card.classList.add("selected");
      if (idx === this._focusIndex) card.classList.add("focused");
      
      card.innerHTML = `
        <h3>${this._escape(rdef.name)}</h3>
        <p class="flavor">${this._escape(rdef.flavor)}</p>
        <div class="stats">
          Speed: ${rdef.speed}ft · 
          ${Object.entries(rdef.ability_bonuses).map(([a, b]) => `${a} +${b}`).join(", ")}
        </div>
      `;
      
      card.addEventListener("click", () => {
        draft.race = raceKey;
        this._renderCreation();
        this.audio?.playCursor();
      });
      grid.appendChild(card);
    });
    
    this._dom.stage.appendChild(grid);
  }
  
  _renderClassStep(draft) {
    const grid = document.createElement("div");
    grid.className = "option-grid";
    
    const entries = Object.entries(this.catalog.classes);
    entries.forEach(([classKey, cdef], idx) => {
      const card = document.createElement("div");
      card.className = "option-card";
      if (draft.charClass === classKey) card.classList.add("selected");
      if (idx === this._focusIndex) card.classList.add("focused");
      
      const inventoryNames = cdef.starting_inventory.map(i => i.name).join(", ");
      card.innerHTML = `
        <h3>${this._escape(cdef.name)}</h3>
        <p class="flavor">${this._escape(cdef.flavor)}</p>
        <div class="stats">
          d${cdef.hit_die} HP · AC ${cdef.base_armor_class}<br>
          Starts with: ${this._escape(inventoryNames)}
        </div>
      `;
      
      card.addEventListener("click", () => {
        draft.charClass = classKey;
        this._renderCreation();
        this.audio?.playCursor();
      });
      grid.appendChild(card);
    });
    
    this._dom.stage.appendChild(grid);
  }
  
  _renderAbilitiesStep(draft) {
    const stage = document.createElement("div");
    
    const help = document.createElement("p");
    help.style.textAlign = "center";
    help.innerHTML = `Assign the standard array to each ability. Click an unused value, then click an ability to set it.`;
    stage.appendChild(help);
    
    const grid = document.createElement("div");
    grid.className = "ability-grid";
    
    ABILITIES.forEach((abil, i) => {
      const row = document.createElement("div");
      row.className = "ability-row";
      if (i === this._focusIndex) row.classList.add("focused");
      
      const name = document.createElement("span");
      name.className = "ability-name";
      name.textContent = abil;
      
      const val = document.createElement("span");
      val.className = "ability-value";
      val.textContent = draft.abilities[abil] ?? "—";
      
      row.appendChild(name);
      row.appendChild(val);
      
      row.addEventListener("click", () => {
        if (this._pendingValue != null) {
          // Place the pending value.
          if (draft.abilities[abil] != null) {
            // Restore the displaced value to the pool.
            this._pool.push(draft.abilities[abil]);
          }
          draft.abilities[abil] = this._pendingValue;
          this._pool = this._pool.filter(v => v !== this._pendingValue);
          this._pendingValue = null;
          this._renderCreation();
          this.audio?.playConfirm();
        } else if (draft.abilities[abil] != null) {
          // Take this value back.
          this._pendingValue = draft.abilities[abil];
          this._pool.push(this._pendingValue);
          draft.abilities[abil] = null;
          this._renderCreation();
          this.audio?.playCursor();
        }
      });
      grid.appendChild(row);
    });
    
    stage.appendChild(grid);
    
    // Pool of available values.
    if (!this._pool) {
      const assigned = Object.values(draft.abilities).filter(v => v != null);
      this._pool = STANDARD_ARRAY.filter(v => !assigned.includes(v));
    }
    
    const pool = document.createElement("div");
    pool.className = "ability-pool";
    STANDARD_ARRAY.forEach(v => {
      const chip = document.createElement("div");
      chip.className = "ability-chip";
      if (!this._pool.includes(v)) chip.classList.add("used");
      if (this._pendingValue === v) chip.style.background = "var(--ink-gilded)";
      chip.textContent = String(v);
      chip.addEventListener("click", () => {
        if (this._pool.includes(v)) {
          this._pendingValue = v;
          this._renderCreation();
          this.audio?.playCursor();
        }
      });
      pool.appendChild(chip);
    });
    stage.appendChild(pool);
    this._dom.stage.appendChild(stage);
  }
  
  _renderNameStep(draft) {
    const wrap = document.createElement("div");
    wrap.className = "name-stage";
    
    const label = document.createElement("p");
    label.style.fontSize = "var(--fs-lg)";
    label.textContent = "What is your hero called?";
    wrap.appendChild(label);
    
    const input = document.createElement("input");
    input.type = "text";
    input.className = "name-input";
    input.maxLength = 24;
    input.placeholder = "Kael, Lyra, Whisper...";
    input.value = draft.name;
    input.addEventListener("input", (e) => { draft.name = e.target.value; });
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && draft.name.trim()) this.handleNext();
    });
    wrap.appendChild(input);
    
    const preview = document.createElement("p");
    preview.style.opacity = "0.7";
    preview.style.fontStyle = "italic";
    preview.textContent =
      `${draft.race ? this.catalog.races[draft.race].name : "—"} ` +
      `${draft.charClass ? this.catalog.classes[draft.charClass].name : "—"}`;
    wrap.appendChild(preview);
    
    this._dom.stage.appendChild(wrap);
    setTimeout(() => input.focus(), 50);
  }
  
  // ─────────────────────── Helpers ───────────────────────
  
  _isStepComplete(draft, step) {
    switch (step) {
      case "race":      return draft.race != null;
      case "class":     return draft.charClass != null;
      case "abilities": return ABILITIES.every(a => draft.abilities[a] != null);
      case "name":      return draft.name.trim().length >= 1;
      default:          return false;
    }
  }
  
  _moveFocus(dx, dy) {
    // Step-specific focus model. For race/class grids, dx/dy moves through
    // the cards in row-major order assuming ~3 columns.
    const draft = this._drafts.get(this._activeControllerId);
    if (!draft) return;
    
    const stepSizes = {
      race: Object.keys(this.catalog.races).length,
      class: Object.keys(this.catalog.classes).length,
      abilities: ABILITIES.length,
      name: 1,
    };
    const max = stepSizes[draft.step] ?? 0;
    if (max === 0) return;
    
    const columns = (draft.step === "race" || draft.step === "class") ? 3 : 1;
    let next = this._focusIndex + dx + dy * columns;
    next = Math.max(0, Math.min(max - 1, next));
    this._focusIndex = next;
    this._renderCreation();
    this.audio?.playCursor();
  }
  
  _draftFromSlot(slot) {
    return {
      controllerId: slot.controller_id,
      slotIndex: slot.slot_index,
      step: slot.chosen_race ? (slot.chosen_class ? "abilities" : "class") : "race",
      race: slot.chosen_race,
      charClass: slot.chosen_class,
      abilities: slot.chosen_ability_layout ??
        { STR: null, DEX: null, CON: null, INT: null, WIS: null, CHA: null },
      name: slot.chosen_name ?? "",
    };
  }
  
  _escape(s) {
    return String(s).replace(/[&<>"']/g, c =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[c])
    );
  }
}
```

### 4.6 `frontend/js/main.js` — Diff

The conductor needs to be phase-aware. It defers Konva/character-panel setup until exploration starts.

```javascript
import { fetchState, openSession, postGridAction, postFreeformAction } from "./api.js";
import { GridCanvas } from "./canvas.js";
import { GamepadManager, XBOX } from "./gamepad.js";
import { CharacterPanel } from "./characters.js";
import { NarrativeLog } from "./log.js";
import { AudioEngine } from "./audio.js";
import { Lobby } from "./lobby.js";       // NEW

const els = {
  konvaMount:    document.getElementById("konva-mount"),
  portraitRow:   document.getElementById("portrait-row"),
  narrativeLog:  document.getElementById("narrative-log"),
  freeformModal: document.getElementById("freeform-modal"),
  freeformInput: document.getElementById("freeform-input"),
  freeformCommit:document.getElementById("freeform-commit"),
  freeformCancel:document.getElementById("freeform-cancel"),
  kbdIndicator:  document.getElementById("kbd-indicator"),
  gpIndicators:  [0, 1, 2, 3].map(i => document.getElementById(`gp-slot-${i}`)),
  summary: {
    name:  document.getElementById("active-name"),
    klass: document.getElementById("active-class"),
    hp:    document.getElementById("active-hp"),
    ac:    document.getElementById("active-ac"),
    move:  document.getElementById("active-move"),
    pos:   document.getElementById("active-pos"),
  },
};

const audio = new AudioEngine();
const gp    = new GamepadManager();

// Game-phase modules (lazy-init when exploration starts)
let canvas = null;
let characters = null;
let log = null;
let lobby = null;

let appState = null;
let session  = null;

// ─────────────────────── Boot ───────────────────────

(async function boot() {
  appState = await fetchState();
  document.body.dataset.phase = appState.phase;
  
  lobby = new Lobby({
    state: appState,
    audio,
    onExplorationStarted: () => initExplorationView(),
    onStateRefetch: async () => {
      appState = await fetchState();
      lobby.setState(appState);
      // If we transitioned to exploration via another client, init game view.
      if (appState.phase === "exploration" && !canvas) {
        initExplorationView();
      }
    },
  });
  await lobby.init(appState);
  
  session = openSession({
    roomId: appState.current_room_id,
    onConnect:    () => console.log("[ws] connected"),
    onDisconnect: () => console.log("[ws] disconnected"),
    onMessage: handleServerEvent,
  });
  
  wireGamepad();
  wireKeyboard();
  wireFreeformModal();
  
  // If we boot directly into exploration (state already advanced), init now.
  if (appState.phase === "exploration") {
    initExplorationView();
  }
  
  gp.start();
})();

function initExplorationView() {
  if (canvas) return;  // idempotent
  
  canvas = new GridCanvas({
    mountEl: els.konvaMount,
    onCellConfirmed: handleGridConfirm,
  });
  characters = new CharacterPanel({
    portraitRowEl: els.portraitRow,
    summaryEls:    els.summary,
    onActiveChanged: () => audio.playCursor(),
  });
  log = new NarrativeLog({ listEl: els.narrativeLog, audio });
  
  canvas.setState(appState);
  characters.setState(appState);
  log.setInitial(appState.narrative_log);
  
  const active = characters.activeCharacter;
  if (active) canvas.setCursor(active.position);
}

// ─────────────────────── Server events ───────────────────────

async function handleServerEvent(msg) {
  if (msg.type !== "state_diff") return;
  appState = await fetchState();
  
  // Always update body phase
  document.body.dataset.phase = appState.phase;
  
  // Lobby/creation: hand to lobby module
  if (appState.phase === "lobby" || appState.phase === "creation") {
    lobby?.setState(appState);
    return;
  }
  
  // Exploration: ensure game view is initialized
  if (appState.phase === "exploration" && !canvas) {
    initExplorationView();
    return;
  }
  
  if (canvas) {
    canvas.setState(appState);
    characters.setState(appState);
    for (const entry of appState.narrative_log.slice(-3)) {
      log.append(entry);
    }
  }
}

// ─────────────────────── Action handlers (exploration only) ───────────────────────

async function handleGridConfirm(target) {
  if (appState.phase !== "exploration") return;
  const active = characters.activeCharacter;
  if (!active) return;
  try {
    await postGridAction({
      actorId: active.id,
      type: "move",
      target,
    });
    audio.playConfirm();
  } catch (err) {
    console.warn("[grid] rejected:", err.message);
    audio.playDeny();
    log.append({
      revision: appState?.revision ?? 0,
      actor_id: null,
      kind: "system",
      text: `[ref] illegal action: ${err.message}`,
      timestamp: new Date().toISOString(),
    });
  }
}

async function commitFreeform() {
  if (appState.phase !== "exploration") return;
  const text = els.freeformInput.value.trim();
  if (!text) return;
  const active = characters.activeCharacter;
  if (!active) return;
  closeFreeformModal();
  audio.playPageTurn();
  try {
    await postFreeformAction({ actorId: active.id, text });
  } catch (err) {
    console.error("[freeform] failed", err);
    audio.playDeny();
  }
}

// ─────────────────────── Gamepad wiring ───────────────────────

function wireGamepad() {
  gp.on("controller_connected", ({ index, controllerId }) => {
    els.gpIndicators[index]?.classList.add("live");
    els.gpIndicators[index].textContent = String(index + 1);
    console.log(`[gp] connected slot=${index} id=${controllerId}`);
  });
  gp.on("controller_disconnected", ({ index }) => {
    els.gpIndicators[index]?.classList.remove("live");
    els.gpIndicators[index].textContent = "·";
  });
  
  gp.on("dpad_repeat", (e) => {
    if (appState?.phase === "exploration") {
      canvas?.moveCursor(e.dx, e.dy);
      audio.playCursor();
    } else {
      lobby?.handleControllerDpad(e);
    }
  });
  
  gp.on("button_pressed", (e) => {
    // Lobby/creation phases: delegate everything to lobby module.
    if (appState?.phase === "lobby" || appState?.phase === "creation") {
      lobby?.handleControllerButton(e);
      return;
    }
    
    // Exploration: existing button mapping.
    switch (e.button) {
      case XBOX.A:  canvas?.confirmCursor(); break;
      case XBOX.B:
        if (!els.freeformModal.classList.contains("hidden")) closeFreeformModal();
        break;
      case XBOX.X:  canvas?.inspectCursor(); break;
      case XBOX.Y:  openFreeformModal(); break;
      case XBOX.LB:
        characters?.cycleActive(-1);
        recenterCursorOnActive();
        break;
      case XBOX.RB:
        characters?.cycleActive(+1);
        recenterCursorOnActive();
        break;
    }
  });
}

function recenterCursorOnActive() {
  const active = characters?.activeCharacter;
  if (active && canvas) canvas.setCursor(active.position);
}

// ─────────────────────── Keyboard fallback ───────────────────────

function wireKeyboard() {
  window.addEventListener("keydown", (e) => {
    if (document.activeElement === els.freeformInput) return;
    
    // Lobby/creation phases: delegate.
    if (appState?.phase === "lobby" || appState?.phase === "creation") {
      // Allow text inputs in creation to receive keys.
      if (document.activeElement?.tagName === "INPUT") return;
      lobby?.handleKeyboard(e);
      return;
    }
    
    // Exploration: existing keymap.
    switch (e.key) {
      case "ArrowLeft":  canvas?.moveCursor(-1, 0); audio.playCursor(); break;
      case "ArrowRight": canvas?.moveCursor(+1, 0); audio.playCursor(); break;
      case "ArrowUp":    canvas?.moveCursor(0, -1); audio.playCursor(); break;
      case "ArrowDown":  canvas?.moveCursor(0, +1); audio.playCursor(); break;
      case "Enter":      canvas?.confirmCursor(); break;
      case "Escape":     closeFreeformModal(); break;
      case "Tab":
        e.preventDefault();
        characters?.cycleActive(e.shiftKey ? -1 : +1);
        recenterCursorOnActive();
        break;
      case "/":
      case "t":
        e.preventDefault();
        openFreeformModal();
        break;
    }
  });
  els.kbdIndicator.classList.add("connected");
}

// ─────────────────────── Freeform modal (unchanged) ───────────────────────

function wireFreeformModal() {
  els.freeformCommit.addEventListener("click", commitFreeform);
  els.freeformCancel.addEventListener("click", closeFreeformModal);
  els.freeformInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      commitFreeform();
    } else if (e.key === "Escape") {
      closeFreeformModal();
    }
  });
}

function openFreeformModal() {
  if (appState?.phase !== "exploration") return;
  els.freeformModal.classList.remove("hidden");
  els.freeformInput.value = "";
  setTimeout(() => els.freeformInput.focus(), 50);
  audio.playPageTurn();
}

function closeFreeformModal() {
  els.freeformModal.classList.add("hidden");
}
```

---

## 5. Migration Path for Existing Saves

If you already have a `data/campaigns/family_campaign_01/state.json` from Pass 3 with the four hardcoded characters, it'll fail to load because the schema now requires `lobby_slots`. One-time migration:

```fish
# scripts/migrate_lobby.fish
#!/usr/bin/env fish
# One-shot migration: add lobby_slots field and set phase appropriately
# to existing campaign saves.

set -l SAVE data/campaigns/family_campaign_01/state.json

if not test -f $SAVE
    echo "no existing save at $SAVE — nothing to migrate"
    exit 0
end

uv run python -c "
import json, sys
from pathlib import Path

p = Path('$SAVE')
data = json.loads(p.read_text())

# If state already has lobby_slots, no-op.
if 'lobby_slots' in data:
    print('already migrated')
    sys.exit(0)

# Seed lobby_slots based on existing characters.
char_ids = list(data.get('characters', {}).keys())
slots = []
for i in range(4):
    if i < len(char_ids):
        slots.append({
            'slot_index': i, 'status': 'ready',
            'controller_id': f'migrated::{char_ids[i]}',
            'character_id': char_ids[i],
            'chosen_name': data['characters'][char_ids[i]]['name'],
            'chosen_race': None, 'chosen_class': None,
            'chosen_ability_layout': None,
        })
    else:
        slots.append({
            'slot_index': i, 'status': 'empty', 'controller_id': None,
            'character_id': None, 'chosen_name': None,
            'chosen_race': None, 'chosen_class': None,
            'chosen_ability_layout': None,
        })

data['lobby_slots'] = slots

# If characters exist, jump straight to exploration; otherwise lobby.
data['phase'] = 'exploration' if char_ids else 'lobby'

p.write_text(json.dumps(data, indent=2))
print(f'migrated {len(char_ids)} character(s), set phase={data[\"phase\"]}')
"
```

Run once: `chmod +x scripts/migrate_lobby.fish && ./scripts/migrate_lobby.fish`

---

## 6. Verification Checklist (Pass 4)

Six checks, each isolating a layer of the new flow.

```fish
# ─── 1. Schema accepts the new phases ──────────────────────────
uv run python -c "
from storyforge.core.models import GameState, TurnPhase
from storyforge.persistence.snapshot import load_seed
s = load_seed()
assert s.phase == TurnPhase.LOBBY, f'expected LOBBY, got {s.phase}'
assert len(s.lobby_slots) == 4, f'expected 4 slots, got {len(s.lobby_slots)}'
assert len(s.characters) == 0, f'expected no characters, got {len(s.characters)}'
print(f'✓ schema accepts new phases, 4 slots seeded, 0 characters')
"

# ─── 2. Character factory builds a sheet ───────────────────────
uv run python -c "
from storyforge.core.character_factory import build_character
from storyforge.core.models import AbilityScores, Coord, Race, CharClass

sheet = build_character(
    char_id='test_01', player='test', name='Testarossa',
    race=Race.ELF, char_class=CharClass.WIZARD,
    base_abilities=AbilityScores(STR=8, DEX=14, CON=12, INT=15, WIS=13, CHA=10),
    starting_position=Coord(x=3, y=6),
)
print(f'✓ built {sheet.name}: {sheet.char_class} (DEX={sheet.abilities.DEX}, INT={sheet.abilities.INT}, HP={sheet.hp_max})')
# Expected: DEX 16 (14+2 elf), INT 16 (15+1 elf), HP 7 (d6=6 + CON mod 1)
"

# ─── 3. Boot the dev server, hit the catalog ───────────────────
./scripts/dev.fish &
sleep 2
curl -sf http://127.0.0.1:8765/api/lobby/catalog | jq '.races | keys, .classes | keys'
# Expected: arrays containing race and class keys

# ─── 4. Full lobby-join → create → start round-trip ────────────
# Join:
curl -sf -X POST http://127.0.0.1:8765/api/lobby/join \
    -H "Content-Type: application/json" \
    -d '{"controller_id": "test::1"}' | jq
# Expected: slot_index 0, phase "creation"

# Create:
curl -sf -X POST http://127.0.0.1:8765/api/character/create \
    -H "Content-Type: application/json" \
    -d '{"slot_index": 0, "name": "Testarossa", "race": "elf",
         "char_class": "wizard",
         "abilities": {"STR": 8, "DEX": 14, "CON": 12, "INT": 15, "WIS": 13, "CHA": 10}}' | jq
# Expected: character_id, character object

# Start:
curl -sf -X POST http://127.0.0.1:8765/api/lobby/start | jq
# Expected: phase "exploration", character_count 1

# Verify final state:
curl -sf http://127.0.0.1:8765/api/state | jq '.phase, (.characters | length)'
# Expected: "exploration", 1

# ─── 5. Action routes reject when not in exploration ───────────
# (Reset the seed first: rm data/campaigns/family_campaign_01/state.json && restart)
curl -i -X POST http://127.0.0.1:8765/api/action/grid \
    -H "Content-Type: application/json" \
    -d '{"actor_id": "test", "type": "move", "target": {"x": 1, "y": 1}}'
# Expected: 409 Conflict, detail about phase

# ─── 6. Open the browser ───────────────────────────────────────
xdg-open http://127.0.0.1:8765
# You should see: parchment Lobby screen with 4 dashed slot cards.
# Plug in a controller, press A → first slot lights gold.
# UI transitions to creation screen with 4 step pills at top.
# Walk through race → class → abilities → name with D-pad + A.
# Press Start → exploration view with your character on the grid.
```

---

## 7. Known Edge Cases (Inventory)

| Scenario | Behavior | Mitigation |
|---|---|---|
| Controller disconnects mid-creation | Draft persists in `lobby_slots` since it's server-side. Reconnect and the draft is restored. | Already handled by `_draftFromSlot`. |
| Same controller_id joins twice (page refresh) | Server's idempotency check returns the existing slot. | `claim_slot` checks for existing controller_id first. |
| Player picks empty name | `handleNext()` validates via `_isStepComplete`; backend also rejects via `min_length=1`. | Two-layer defense. |
| Player tries to start with 0 characters | `start_exploration` raises `StateError`; UI disables button until ≥1 READY. | Both checks active. |
| Two controllers press A simultaneously | `asyncio.Lock` serializes the claims; second controller gets next available slot. | Lock pattern from Pass 2 carries through. |
| Re-running creation after exploration started | `state.phase != CREATION` → 409 Conflict. To restart, delete `state.json` and reboot. | "New campaign" UI is a v0.2 feature. |

---

## 8. Commit Sequence

Suggested commit cadence for your dual-remote workflow:

```fish
cd ~/projects/storyforge

# Schema + factory
git add src/storyforge/core/models.py \
        src/storyforge/core/character_factory.py
git commit -m "feat(core): add lobby/creation phases + character factory

- TurnPhase: LOBBY and CREATION states added
- New models: LobbySlot, SlotStatus, Race, CharClass, CharacterCreationRequest
- character_factory.py: race + class catalog, standard array validation,
  HP/AC/inventory composition, starting position picker
- GameState.characters now defaults to empty; lobby_slots field added"

# State manager + validator + routes
git add src/storyforge/core/state_manager.py \
        src/storyforge/core/validators.py \
        src/storyforge/api/routes_lobby.py \
        src/storyforge/api/routes_action.py \
        src/storyforge/main.py
git commit -m "feat(api): lobby join/create/start endpoints + phase gating

- StateManager: claim_slot, release_slot, create_character, start_exploration
- validators.sanitize short-circuits AI diffs during lobby/creation
- action routes return 409 Conflict outside EXPLORATION phase
- new router mounted at /api/lobby/* and /api/character/create"

# Seed
git add data/seeds/default_campaign.json scripts/migrate_lobby.fish
git commit -m "feat(data): empty-character seed + migration helper

- default_campaign.json: phase=lobby, characters={}, 4 empty slots
- scripts/migrate_lobby.fish: one-shot migration for Pass 3 saves"

# Frontend lobby
git add frontend/index.html \
        frontend/css/lobby.css \
        frontend/js/lobby.js \
        frontend/js/gamepad.js \
        frontend/js/api.js \
        frontend/js/main.js
git commit -m "feat(frontend): dynamic lobby + character creation flow

- index.html: 3-view shell (lobby / creation / game) with data-phase switching
- lobby.css: parchment-themed slot cards, step pills, option grids
- lobby.js: complete creation state machine (race/class/abilities/name)
- gamepad.js: drop hardcoded index mapping, expose stable controllerId
- main.js: phase-aware view router, lazy-init Konva on exploration start
- api.js: lobby + creation endpoint wrappers"

# Push to both
git push origin main
git push gitlab main
```

---

## 9. Looking Forward to v0.2 (Reset on This)

Two natural extensions that fall out of this pass for free:

1. **"New Campaign" button** in the exploration view. Calls a new `POST /api/campaign/reset` that wipes characters, clears the narrative log, resets lobby_slots, and sets `phase=lobby`. The atomic-save pattern means it's safe even mid-write.

2. **Mid-game player join**. Since `lobby_slots` is persistent and there's no hard binding between "characters in roster" and "slots claimed," you could allow a 5th player to press A during exploration, drop into a mini-creation flow, and be inserted into a free cell. Requires lifting the phase gate on the lobby routes and adding a "characters merge into running session" pathway in `StateManager.create_character`.

---

## 10. What I Held Back From This Pass

Deliberate omissions, so you can decide if they're MVP-blockers:

| Omitted | Reason | Add later? |
|---|---|---|
| **Random rolling option for abilities** | Standard array is faster and family-friendly | v0.2 toggle |
| **Subraces / archetypes** (high elf vs wood elf) | Doubles the catalog size; not core to MVP | v0.3 |
| **Backstory / personality fields** | Pure flavor, no mechanical impact | v0.2 |
| **Avatar / portrait selection** | Generated `name[0]` initial works for now | When you add a real portrait asset pipeline |
| **Multi-screen creation** (each player on own device) | Would require WebSocket-based slot reservation; conflicts with "hot seat" axiom F3 | v0.4 if you ever leave the couch |

Plug it all in, run the verification checklist, and your family can sit down with four controllers and watch their characters take shape on screen before the door of the Crooked Tankard ever opens.
