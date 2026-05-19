"""
Character factory: builds CharacterSheet instances from creation requests.

This module is the single source of truth for race/state/role mechanics.
- Race: Grants unique ability bonuses and base speed.
- Evolutionary State: Determines base HP (Hit Die) and base Armor Class.
- Predator Role: Determines starting inventory and utility bonuses.
"""
from __future__ import annotations
import secrets
from dataclasses import dataclass

from storyforge.core import grid
from storyforge.core.models import (
    AbilityScores, CharacterSheet, Coord, GameState,
    InventoryItem, Race, EvolutionaryState, PredatorRole
)


STANDARD_ARRAY = (15, 14, 13, 12, 10, 8)


# ─────────────────────── Race definitions ───────────────────────

@dataclass(frozen=True)
class RaceDef:
    name: str
    speed: int
    ability_bonuses: dict[str, int]
    flavor: str

RACES: dict[Race, RaceDef] = {
    # Sci-Fi
    Race.ARCHON_VULTURE: RaceDef(
        name="Archon-Vulture", speed=30, ability_bonuses={"INT": 2, "STR": 1},
        flavor="Bio-magnetic scavengers that reanimate dead systems."
    ),
    Race.SIGNAL_SHADE: RaceDef(
        name="Signal-Shade", speed=40, ability_bonuses={"DEX": 2, "INT": 1},
        flavor="Formless data-entities striking from digital networks."
    ),
    Race.GEAR_LOCUST: RaceDef(
        name="Gear-Locust", speed=35, ability_bonuses={"DEX": 2, "CON": 1},
        flavor="Chitinous drones that disassemble gear in combat."
    ),
    Race.CORE_DRINKER: RaceDef(
        name="Core-Drinker", speed=20, ability_bonuses={"STR": 2, "CON": 1},
        flavor="Geothermal leviathans with fusion-grafted spines."
    ),
    Race.VOID_STRIDER: RaceDef(
        name="Void-Strider", speed=30, ability_bonuses={"DEX": 1, "WIS": 2},
        flavor="Radar-absorbing hunters blinking through Glitch-Space."
    ),
    # Mythic
    Race.SUN_SOVEREIGN: RaceDef(
        name="Sun-Sovereign", speed=40, ability_bonuses={"CHA": 2, "WIS": 1},
        flavor="Avian humanoids manipulating celestial light-leys."
    ),
    Race.ECHO_VINE: RaceDef(
        name="Echo-Vine", speed=30, ability_bonuses={"DEX": 1, "CHA": 2},
        flavor="Bark-skinned mimics replacing prey in sentient jungles."
    ),
    Race.CINDER_KIN: RaceDef(
        name="Cinder-Kin", speed=35, ability_bonuses={"INT": 1, "DEX": 2},
        flavor="Crystalline imps strategically melting tectonic plates."
    ),
    Race.TIDE_TYRANT: RaceDef(
        name="Tide-Tyrant", speed=30, ability_bonuses={"STR": 1, "INT": 2},
        flavor="Cephalopodic strategists manipulating trade via whirlpools."
    ),
    Race.RUNE_RAVEN: RaceDef(
        name="Rune-Raven", speed=30, ability_bonuses={"WIS": 2, "INT": 1},
        flavor="Obsidian scavengers grafting stolen runes into wings."
    ),
    # Eldritch
    Race.HEMATIC_WEAVER: RaceDef(
        name="Hematic-Weaver", speed=30, ability_bonuses={"CHA": 2, "INT": 1},
        flavor="Regal horrors conquering bloodlines and sleeper agents."
    ),
    Race.WHISPERING_HUSK: RaceDef(
        name="Whispering-Husk", speed=30, ability_bonuses={"WIS": 2, "CHA": 1},
        flavor="Fungal gases projecting illusions of lost loved ones."
    ),
    Race.MARROW_DRIFTER: RaceDef(
        name="Marrow-Drifter", speed=20, ability_bonuses={"CON": 2, "STR": 1},
        flavor="Microscopic parasites rewriting host skeletons into cages."
    ),
    Race.SYNAPSE_SPIDER: RaceDef(
        name="Synapse-Spider", speed=40, ability_bonuses={"INT": 2, "DEX": 1},
        flavor="Translucent arachnids snipping plans from dreaming minds."
    ),
    Race.VOID_FLEA: RaceDef(
        name="Void-Flea", speed=35, ability_bonuses={"DEX": 2, "WIS": 1},
        flavor="Twitching entities sewing glitched reality into carapaces."
    ),
}

# ─────────────────────── Evolutionary State definitions ───────────────────────

@dataclass(frozen=True)
class StateDef:
    name: str
    hit_die: int
    base_armor_class: int
    flavor: str

STATES: dict[EvolutionaryState, StateDef] = {
    EvolutionaryState.BEHEMOTH: StateDef(
        name="Behemoth", hit_die=12, base_armor_class=16,
        flavor="A wall of muscle and chitin. High durability."
    ),
    EvolutionaryState.PHANTOM: StateDef(
        name="Phantom", hit_die=6, base_armor_class=12,
        flavor="Incorporeal and ethereal. Hard to hit, but fragile."
    ),
    EvolutionaryState.SWARM_HOST: StateDef(
        name="Swarm-Host", hit_die=10, base_armor_class=14,
        flavor="A living vessel for smaller entities. Balanced power."
    ),
    EvolutionaryState.MIMIC: StateDef(
        name="Mimic", hit_die=8, base_armor_class=13,
        flavor="Fluid and adaptive body structure. Versatile scout."
    ),
}

# ─────────────────────── Predator Role definitions ───────────────────────

@dataclass(frozen=True)
class RoleDef:
    name: str
    starting_inventory: tuple[InventoryItem, ...]
    flavor: str

def _item(item_id: str, name: str, equipped: bool = False, qty: int = 1,
          notes: str | None = None) -> InventoryItem:
    return InventoryItem(id=item_id, name=name, quantity=qty,
                         equipped=equipped, notes=notes)

ROLES: dict[PredatorRole, RoleDef] = {
    PredatorRole.STALKER: RoleDef(
        name="Stalker",
        starting_inventory=(_item("razor_claws", "Razor Claws", equipped=True), _item("smoke_pellets", "Smoke Pellets", qty=3)),
        flavor="Single-target elimination and ambushing."
    ),
    PredatorRole.VANGUARD: RoleDef(
        name="Vanguard",
        starting_inventory=(_item("heavy_mandibles", "Heavy Mandibles", equipped=True), _item("reinforced_plating", "Reinforced Plating", equipped=True)),
        flavor="Zone control and intimidation."
    ),
    PredatorRole.CATALYST: RoleDef(
        name="Catalyst",
        starting_inventory=(_item("venom_sac", "Venom Sac", equipped=True), _item("web_strands", "Web Strands", qty=5)),
        flavor="Environmental manipulation and trapping."
    ),
    PredatorRole.SIPHONER: RoleDef(
        name="Siphoner",
        starting_inventory=(_item("energy_leech", "Energy Leech", equipped=True), _item("void_battery", "Void Battery")),
        flavor="Resource theft and adaptation."
    ),
}

# ─────────────────────── Factory logic ───────────────────────

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

def build_character(
    char_id: str,
    name: str,
    player: str,
    race: Race,
    state: EvolutionaryState,
    role: PredatorRole,
    abilities: AbilityScores,
    game_state: GameState
) -> CharacterSheet:
    r_def = RACES[race]
    s_def = STATES[state]
    p_def = ROLES[role]

    # Apply racial bonuses
    final_scores = abilities.model_copy(deep=True)
    for abi, bonus in r_def.ability_bonuses.items():
        curr = getattr(final_scores, abi)
        setattr(final_scores, abi, curr + bonus)

    hp_max = s_def.hit_die + _ability_modifier(final_scores.CON)
    ac = s_def.base_armor_class + _ability_modifier(final_scores.DEX)

    # Find a starting position on the grid.
    spawn_pos = find_starting_position(game_state)

    return CharacterSheet(
        id=char_id,
        name=name,
        player=player,
        race=race,
        evolution_state=state,
        predator_role=role,
        level=1,
        evolution_points=0,
        hp_current=hp_max,
        hp_max=hp_max,
        armor_class=ac,
        speed=r_def.speed,
        abilities=final_scores,
        proficiency_bonus=2,
        inventory=list(p_def.starting_inventory),
        position=spawn_pos,
        movement_remaining=r_def.speed,
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
