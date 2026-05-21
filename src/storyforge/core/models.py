"""
StoryForge canonical data model.

This module is the contract between every other layer. The Python referee
validates incoming actions against these schemas; Gemini receives the JSON
Schema export to constrain its structured output.
"""
from __future__ import annotations
from enum import StrEnum
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict
import datetime as dt

# ─────────────────────── Primitives ───────────────────────

class Coord(BaseModel):
    """A single grid cell. Origin (0,0) is top-left."""
    model_config = ConfigDict(frozen=True)
    x: int = Field(ge=0)
    y: int = Field(ge=0)


class Ability(StrEnum):
    STR = "STR"; DEX = "DEX"; CON = "CON"
    INT = "INT"; WIS = "WIS"; CHA = "CHA"


# ─────────────────────── Characters ───────────────────────

class AbilityScores(BaseModel):
    STR: int = Field(ge=1, le=30)
    DEX: int = Field(ge=1, le=30)
    CON: int = Field(ge=1, le=30)
    INT: int = Field(ge=1, le=30)
    WIS: int = Field(ge=1, le=30)
    CHA: int = Field(ge=1, le=30)


class InventoryItem(BaseModel):
    id: str                          # stable slug, e.g. "longsword_01"
    name: str
    quantity: int = Field(ge=0, default=1)
    equipped: bool = False
    value: int = Field(ge=0, default=0) # Value in silver
    notes: str | None = None


class CharacterSheet(BaseModel):
    """D&D 5e character. MVP-trimmed; expand as needed."""
    id: str                          # "cody", "dee", "nate", "bray"
    name: str
    player: str                      # real-world player name
    race: Race
    evolution_state: EvolutionaryState
    predator_role: PredatorRole
    level: int = Field(ge=1, le=20, default=1)
    evolution_points: int = Field(ge=0, default=0)
    silver: int = Field(ge=0, default=0)
    
    hp_current: int = Field(ge=0)
    hp_max: int = Field(ge=1)
    armor_class: int = Field(ge=1, default=10)
    speed: int = Field(ge=0, default=30)   # feet per turn; grid = 5ft/cell
    
    abilities: AbilityScores
    proficiency_bonus: int = Field(ge=2, le=6, default=2)
    inventory: list[InventoryItem] = Field(default_factory=list)
    
    # Combat-turn ephemeral state
    position: Coord
    movement_remaining: int = 0      # feet left this turn
    conditions: list[str] = Field(default_factory=list)  # "prone", "stunned"


# ─────────────────────── Grid / Room ───────────────────────

class TerrainKind(StrEnum):
    FLOOR = "floor"
    WALL = "wall"
    DOOR = "door"
    DIFFICULT = "difficult"          # half-speed
    HAZARD = "hazard"


class Cell(BaseModel):
    terrain: TerrainKind = TerrainKind.FLOOR
    occupant_id: str | None = None   # character_id or entity_id


class NpcSheet(BaseModel):
    """A non-player character placed on the grid."""
    id: str
    name: str
    position: Coord
    room_id: str | None = None          # which room this NPC belongs to (None = any)
    sprite_key: str = "npc_default"     # frontend canvas uses this to style the token
    interactable: bool = True
    encounter_id: str | None = None     # e.g. "john_shop" — links to encounter handler
    blocks_movement: bool = True        # if True the grid cell has occupant_id set
    description: str = ""


class Room(BaseModel):
    id: str
    name: str
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    # cells stored row-major: cells[y * width + x]
    cells: list[Cell]
    description: str                 # static room flavor for AI context
    # "x,y" -> room_id: when a player interacts with that door cell, everyone
    # transitions to the target room. Omitted from old saves (defaults to {}).
    exits: dict[str, str] = Field(default_factory=dict)


# ─────────────────────── Session State ───────────────────────

class TurnPhase(StrEnum):
    TITLE = "title"
    MENU = "menu"                # New Game / Saved Games
    MODE_SELECT = "mode_select"  # Solo / Multi
    LOBBY = "lobby"              # waiting for slot claims
    CREATION = "creation"        # claimed players picking race/class/name
    EXPLORATION = "exploration"
    COMBAT = "combat"


class CombatState(BaseModel):
    initiative_order: list[str]      # character_ids in order
    active_index: int = 0
    round_number: int = 1


class NarrativeEntry(BaseModel):
    revision: int                    # state revision at time of event
    actor_id: str | None             # None for DM narration
    kind: Literal["action", "narration", "system"]
    text: str
    timestamp: str                   # ISO 8601


class Race(StrEnum):
    # Cosmic
    VOIDWRAITH  = "voidwraith"
    NULLSHADE   = "nullshade"
    IRONLOCUST  = "ironlocust"
    EMBERVEIN   = "embervein"
    RIFTWALKER  = "riftwalker"
    # Primal
    SOLARLORD   = "solarlord"
    THORNMIMIC  = "thornmimic"
    CINDERKIN   = "cinderkin"
    DEEPTYRANT  = "deeptyrant"
    GRIMCROW    = "grimcrow"
    # Eldritch
    BLOODWEAVER  = "bloodweaver"
    DREAMHUSK    = "dreamhusk"
    BONEDRIFTER  = "bonedrifter"
    MINDSPIDER   = "mindspider"
    CHAOSLING    = "chaosling"
    # Mechanical
    IRONVEIL     = "ironveil"
    FORGESPAWN   = "forgespawn"
    CINDERPLATE  = "cinderplate"
    HEXGEAR      = "hexgear"
    WIREWRAITH   = "wirewraith"
    # Humanoid (After the Paradox)
    ASHENBORN    = "ashenborn"
    HOLLOWSONG   = "hollowsong"
    VEILBORN     = "veilborn"
    THORNWEFT    = "thornweft"
    ASHCROWN     = "ashcrown"
    IRONFAST     = "ironfast"
    COREBORN     = "coreborn"
    WARPBRED     = "warpbred"
    SPLITBLOOD   = "splitblood"
    DUSKWEFT     = "duskweft"
    GLITCHKIN    = "glitchkin"
    FRACTURELINE = "fractureline"
    EMBERPACT    = "emberpact"
    FALLENLIGHT  = "fallenlight"
    SCALEWORN    = "scaleworn"


class EvolutionaryState(StrEnum):
    BEHEMOTH = "behemoth"
    PHANTOM = "phantom"
    SWARM_HOST = "swarm_host"
    MIMIC = "mimic"


class PredatorRole(StrEnum):
    STALKER = "stalker"
    VANGUARD = "vanguard"
    CATALYST = "catalyst"
    SIPHONER = "siphoner"


class SlotStatus(StrEnum):
    EMPTY = "empty"               # no controller claimed
    CLAIMED = "claimed"           # controller bound, no character yet
    CREATING = "creating"         # player is picking race/state/role/name
    READY = "ready"               # character finalized, waiting for others


class LobbySlot(BaseModel):
    """One of up to 4 player slots in the lobby."""
    slot_index: int = Field(ge=0, le=3)
    status: SlotStatus = SlotStatus.EMPTY
    controller_id: str | None = None      # GamepadID string from frontend
    character_id: str | None = None        # set when SlotStatus.READY
    
    # Creation draft (temporary)
    race: Race | None = None
    evolution_state: EvolutionaryState | None = None
    predator_role: PredatorRole | None = None
    assigned_abilities: dict[str, int] | None = None
    name_draft: str | None = None


class CharacterCreationRequest(BaseModel):
    """POST body for /api/character/create."""
    slot_index: int = Field(ge=0, le=3)
    name: str = Field(min_length=1, max_length=24)
    race: Race
    evolution_state: EvolutionaryState
    predator_role: PredatorRole
    # Player chose which ability gets which standard-array value.
    # Must be a permutation of [15, 14, 13, 12, 10, 8].
    abilities: AbilityScores


class GameState(BaseModel):
    """Root state object. Snapshotted to data/campaigns/<id>/state.json."""
    campaign_id: str
    current_room_id: str
    phase: TurnPhase = TurnPhase.LOBBY
    
    characters: dict[str, CharacterSheet] = Field(default_factory=dict)
    npcs: dict[str, NpcSheet] = Field(default_factory=dict)
    rooms: dict[str, Room]
    combat: CombatState | None = None
    
    lobby_slots: list[LobbySlot] = Field(
        default_factory=lambda: [LobbySlot(slot_index=i) for i in range(4)]
    )
    
    narrative_log: list[NarrativeEntry] = Field(default_factory=list)
    revision: int = 0                # increments on every mutation


# ─────────────────────── Action Payloads ───────────────────────

class GridAction(BaseModel):
    """Sent when player clicks a target cell."""
    type: Literal["move", "attack", "interact"]
    actor_id: str
    target: Coord


class FreeformAction(BaseModel):
    """Sent when player types narrative input."""
    actor_id: str
    text: str = Field(min_length=1, max_length=500)


# ─────────────────────── AI Response Contract ───────────────────────

class StateDiff(BaseModel):
    """
    The ONLY thing Gemini is allowed to mutate. Validated and sanitized
    by core/validators.py before being applied to GameState.
    """
    character_updates: dict[str, dict] = Field(default_factory=dict)
    cell_updates: list[tuple[str, Coord, Cell]] = Field(default_factory=list)
    add_inventory: dict[str, list[InventoryItem]] = Field(default_factory=dict)
    remove_inventory: dict[str, list[str]] = Field(default_factory=dict)
    phase_change: TurnPhase | None = None


class AINarrationResponse(BaseModel):
    """What Gemini must return for every call."""
    narrative: str = Field(min_length=1)
    state_diff: StateDiff | None = None
