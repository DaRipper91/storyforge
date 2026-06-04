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
