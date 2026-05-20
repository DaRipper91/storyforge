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
    group: str = "Cosmic"
    before: str | None = None  # Humanoid only: the "Before" race name

RACES: dict[Race, RaceDef] = {
    # Cosmic — born between stars, beneath suns, inside the void
    Race.VOIDWRAITH: RaceDef(
        name="Voidwraith", speed=30, ability_bonuses={"INT": 2, "STR": 1}, group="Cosmic",
        flavor="Stellar scavengers that feast on dying magic and the bones of dead worlds."
    ),
    Race.NULLSHADE: RaceDef(
        name="Nullshade", speed=40, ability_bonuses={"DEX": 2, "INT": 1}, group="Cosmic",
        flavor="Formless hunters that stalk prey from the dark spaces between worlds."
    ),
    Race.IRONLOCUST: RaceDef(
        name="Iron-Locust", speed=35, ability_bonuses={"DEX": 2, "CON": 1}, group="Cosmic",
        flavor="Chitinous swarms that strip metal, stone, and bone with equal hunger."
    ),
    Race.EMBERVEIN: RaceDef(
        name="Embervein", speed=20, ability_bonuses={"STR": 2, "CON": 1}, group="Cosmic",
        flavor="Molten-blooded leviathans born in the cores of burning worlds."
    ),
    Race.RIFTWALKER: RaceDef(
        name="Riftwalker", speed=30, ability_bonuses={"DEX": 1, "WIS": 2}, group="Cosmic",
        flavor="Phase-hunters that slip between realms leaving no shadow and no sound."
    ),
    # Primal — ancient, elemental, rooted in myth and living world
    Race.SOLARLORD: RaceDef(
        name="Solar-Lord", speed=40, ability_bonuses={"CHA": 2, "WIS": 1}, group="Primal",
        flavor="Celestial avians who ride light-paths between suns and speak in stellar fire."
    ),
    Race.THORNMIMIC: RaceDef(
        name="Thornmimic", speed=30, ability_bonuses={"DEX": 1, "CHA": 2}, group="Primal",
        flavor="Bark-skinned shapeshifters who replace their prey in the oldest forests."
    ),
    Race.CINDERKIN: RaceDef(
        name="Cinderkin", speed=35, ability_bonuses={"INT": 1, "DEX": 2}, group="Primal",
        flavor="Crystalline fire-sprites forged in the hearts of volcanoes."
    ),
    Race.DEEPTYRANT: RaceDef(
        name="Deep-Tyrant", speed=30, ability_bonuses={"STR": 1, "INT": 2}, group="Primal",
        flavor="Ancient cephalopodic minds who rule kingdoms from the lightless abyss."
    ),
    Race.GRIMCROW: RaceDef(
        name="Grimcrow", speed=30, ability_bonuses={"WIS": 2, "INT": 1}, group="Primal",
        flavor="Obsidian-feathered oracles who steal living magic and bind it to bone."
    ),
    # Eldritch — things that should not be, things that persist anyway
    Race.BLOODWEAVER: RaceDef(
        name="Bloodweaver", speed=30, ability_bonuses={"CHA": 2, "INT": 1}, group="Eldritch",
        flavor="Regal horrors who conquer entire bloodlines from the inside out."
    ),
    Race.DREAMHUSK: RaceDef(
        name="Dreamhusk", speed=30, ability_bonuses={"WIS": 2, "CHA": 1}, group="Eldritch",
        flavor="Spore-borne entities that project the faces of the beloved dead."
    ),
    Race.BONEDRIFTER: RaceDef(
        name="Bonedrifter", speed=20, ability_bonuses={"CON": 2, "STR": 1}, group="Eldritch",
        flavor="Parasitic beings that rewrite their hosts skeleton-first into living prisons."
    ),
    Race.MINDSPIDER: RaceDef(
        name="Mindspider", speed=40, ability_bonuses={"INT": 2, "DEX": 1}, group="Eldritch",
        flavor="Translucent arachnids that harvest plans and secrets from sleeping prey."
    ),
    Race.CHAOSLING: RaceDef(
        name="Chaosling", speed=35, ability_bonuses={"DEX": 2, "WIS": 1}, group="Eldritch",
        flavor="Twitching fragments of unraveled reality stitched into borrowed flesh."
    ),
    # Mechanical — constructed, forged, refused to stop
    Race.IRONVEIL: RaceDef(
        name="Ironveil", speed=40, ability_bonuses={"DEX": 2, "INT": 1}, group="Mechanical",
        flavor="Gossamer-thin war constructs that fold themselves flat to slip through walls and armor plating. Deceptively fragile looking, catastrophically sharp."
    ),
    Race.FORGESPAWN: RaceDef(
        name="Forgespawn", speed=35, ability_bonuses={"STR": 2, "CON": 1}, group="Mechanical",
        flavor="Liquid-metal organisms that cool into whatever shape the battlefield demands. Born in furnaces, comfortable in fire."
    ),
    Race.CINDERPLATE: RaceDef(
        name="Cinderplate", speed=20, ability_bonuses={"STR": 2, "WIS": 1}, group="Mechanical",
        flavor="Armored plating over a molten core. They run hot, cool slow, and leave scorch marks on everything they touch."
    ),
    Race.HEXGEAR: RaceDef(
        name="Hexgear", speed=35, ability_bonuses={"INT": 2, "DEX": 1}, group="Mechanical",
        flavor="Six-sided modular beings that reconfigure their body layout mid-combat. No consistent face, no consistent silhouette."
    ),
    Race.WIREWRAITH: RaceDef(
        name="Wirewraith", speed=45, ability_bonuses={"DEX": 2, "WIS": 1}, group="Mechanical",
        flavor="Exposed-nerve constructs that transmit pain and data at the same speed. They feel everything, process it, and don't stop moving."
    ),
    # Humanoid — what the civilized races became after the Paradox
    Race.ASHENBORN: RaceDef(
        name="Ashenborn", speed=30, ability_bonuses={"CON": 2, "STR": 1}, group="Humanoid", before="Human",
        flavor="Humans who burned through the Paradox and came out the other side charred, fireproof, and furious."
    ),
    Race.HOLLOWSONG: RaceDef(
        name="Hollowsong", speed=35, ability_bonuses={"WIS": 2, "INT": 1}, group="Humanoid", before="Elf",
        flavor="Elves whose magic inverted; they no longer cast, they absorb, and it's starting to show."
    ),
    Race.VEILBORN: RaceDef(
        name="Veilborn", speed=40, ability_bonuses={"DEX": 2, "CHA": 1}, group="Humanoid", before="Dark Elf",
        flavor="Dark elves who were already living in the dark when the Paradox hit; they adapted faster than anyone and trust no one."
    ),
    Race.THORNWEFT: RaceDef(
        name="Thornweft", speed=30, ability_bonuses={"WIS": 2, "CON": 1}, group="Humanoid", before="Wood Elf",
        flavor="Wood elves who merged with the forests during the silence; bark grows where skin used to be."
    ),
    Race.ASHCROWN: RaceDef(
        name="Ashcrown", speed=35, ability_bonuses={"INT": 2, "CHA": 1}, group="Humanoid", before="High Elf",
        flavor="High elves who refused to change and paid for it; regal, brittle, and slowly going translucent."
    ),
    Race.IRONFAST: RaceDef(
        name="Ironfast", speed=25, ability_bonuses={"CON": 2, "STR": 1}, group="Humanoid", before="Dwarf",
        flavor="Dwarves whose bones calcified past stone; they are slower, denser, and nearly impossible to put down."
    ),
    Race.COREBORN: RaceDef(
        name="Coreborn", speed=25, ability_bonuses={"CON": 2, "INT": 1}, group="Humanoid", before="Deep Dwarf",
        flavor="Deep dwarves who pulled something up from below during the Paradox; it came with them."
    ),
    Race.WARPBRED: RaceDef(
        name="Warpbred", speed=35, ability_bonuses={"STR": 2, "CON": 1}, group="Humanoid", before="Orc",
        flavor="Orcs who leaned into the Paradox and asked it for more; nobody is sure what they traded."
    ),
    Race.SPLITBLOOD: RaceDef(
        name="Splitblood", speed=30, ability_bonuses={"STR": 1, "CON": 2}, group="Humanoid", before="Half-Orc",
        flavor="Half-orcs whose two halves stopped agreeing during the silence; they are in a constant negotiation with themselves."
    ),
    Race.DUSKWEFT: RaceDef(
        name="Duskweft", speed=40, ability_bonuses={"DEX": 2, "WIS": 1}, group="Humanoid", before="Halfling",
        flavor="Halflings who slipped sideways during the silence and haven't fully come back; they flicker."
    ),
    Race.GLITCHKIN: RaceDef(
        name="Glitchkin", speed=30, ability_bonuses={"INT": 2, "DEX": 1}, group="Humanoid", before="Gnome",
        flavor="Gnomes whose tinkering instinct turned inward; they've been modifying themselves ever since."
    ),
    Race.FRACTURELINE: RaceDef(
        name="Fractureline", speed=35, ability_bonuses={"INT": 2, "CHA": 1}, group="Humanoid", before="Half-Elf",
        flavor="Half-elves split cleanly down the middle during the Paradox; one half remembers the old world, the other doesn't."
    ),
    Race.EMBERPACT: RaceDef(
        name="Emberpact", speed=30, ability_bonuses={"CHA": 2, "STR": 1}, group="Humanoid", before="Tiefling",
        flavor="Tieflings whose infernal contracts dissolved in the Paradox; they kept the features and lost the leash."
    ),
    Race.FALLENLIGHT: RaceDef(
        name="Fallenlight", speed=35, ability_bonuses={"CHA": 2, "WIS": 1}, group="Humanoid", before="Aasimar",
        flavor="Aasimars whose divine connection severed; they still glow, but nothing answers when they call."
    ),
    Race.SCALEWORN: RaceDef(
        name="Scaleworn", speed=30, ability_bonuses={"STR": 2, "DEX": 1}, group="Humanoid", before="Dragonborn",
        flavor="Dragonborn whose draconic heritage collapsed inward; the fire is still there, the bloodline is not."
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
