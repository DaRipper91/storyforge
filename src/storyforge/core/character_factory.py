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
    AbilityScores, CharacterSheet, Coord, EnemySheet, GameState,
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
    before: str | None = None      # Humanoid only: the "Before" race name
    race_weapon: InventoryItem | None = None
    race_armor: InventoryItem | None = None

def _weapon(item_id: str, name: str, dice: str, notes: str) -> InventoryItem:
    return InventoryItem(id=item_id, name=name, equipped=True,
                         damage_dice=dice, notes=notes)

def _armor(item_id: str, name: str, ac_bonus: int, notes: str) -> InventoryItem:
    return InventoryItem(id=item_id, name=name, equipped=True,
                         armor_ac_bonus=ac_bonus, notes=notes)


RACES: dict[Race, RaceDef] = {
    # ── Cosmic ──────────────────────────────────────────────────────────────
    Race.VOIDWRAITH: RaceDef(
        name="Voidwraith", speed=30, ability_bonuses={"INT": 2, "STR": 1}, group="Cosmic", before="Astral Spirit",
        flavor="Stellar scavengers that feast on dying magic and the bones of dead worlds.",
        race_weapon=_weapon("void_shard_blade", "Void-Shard Blade", "1d8",
            "Crystallized null-space; ignores magical wards on the first strike each combat."),
        race_armor=_armor("null_field_wrap", "Null-Field Wrap", 1,
            "Absorbs the first 2 points of energy damage each round."),
    ),
    Race.NULLSHADE: RaceDef(
        name="Nullshade", speed=40, ability_bonuses={"DEX": 2, "INT": 1}, group="Cosmic", before="Shadow-Wisp",
        flavor="Formless hunters that stalk prey from the dark spaces between worlds.",
        race_weapon=_weapon("umbra_stiletto", "Umbra Stiletto", "1d4",
            "Shadow-forged; +2 to hit in dim light or darkness."),
        race_armor=_armor("dusk_veil", "Dusk Veil", 0,
            "Grants advantage on Stealth checks; near-invisible in shadow."),
    ),
    Race.IRONLOCUST: RaceDef(
        name="Iron-Locust", speed=35, ability_bonuses={"DEX": 2, "CON": 1}, group="Cosmic", before="Mining Drone",
        flavor="Chitinous swarms that strip metal, stone, and bone with equal hunger.",
        race_weapon=_weapon("mandible_shears", "Mandible Shears", "1d6",
            "Serrated chitinous pincers; can cut through rope, thin metal, and leather as a bonus action."),
        race_armor=_armor("chitin_plating", "Chitin Plating", 2,
            "Harvested shell reinforcement; bludgeoning damage reduced by 1."),
    ),
    Race.EMBERVEIN: RaceDef(
        name="Embervein", speed=20, ability_bonuses={"STR": 2, "CON": 1}, group="Cosmic", before="Magma Elemental",
        flavor="Molten-blooded leviathans born in the cores of burning worlds.",
        race_weapon=_weapon("magma_fist", "Magma Fist", "1d8",
            "Molten-core impact; deals an extra 1 fire damage on hit. Melts ice and wax on contact."),
        race_armor=_armor("volcanic_carapace", "Volcanic Carapace", 2,
            "Ignores the first 3 points of fire damage each round."),
    ),
    Race.RIFTWALKER: RaceDef(
        name="Riftwalker", speed=30, ability_bonuses={"DEX": 1, "WIS": 2}, group="Cosmic", before="Planar Voyager",
        flavor="Phase-hunters that slip between realms leaving no shadow and no sound.",
        race_weapon=_weapon("phase_blade", "Phase Blade", "1d6",
            "Partially phased; ignores the AC bonus from light armor on the first hit each combat."),
        race_armor=_armor("rift_fold_cloak", "Rift-Fold Cloak", 1,
            "Phase-displacement layer; once per combat, the first melee hit against you is re-rolled."),
    ),
    # ── Primal ──────────────────────────────────────────────────────────────
    Race.SOLARLORD: RaceDef(
        name="Solar-Lord", speed=40, ability_bonuses={"CHA": 2, "WIS": 1}, group="Primal", before="High Seraph",
        flavor="Celestial avians who ride light-paths between suns and speak in stellar fire.",
        race_weapon=_weapon("sunlance", "Sunlance", "1d8",
            "Radiant piercing weapon; ignites flammable targets. Undead take +2 damage per strike."),
        race_armor=_armor("feathermail_aegis", "Feathermail Aegis", 1,
            "Celestial pinions woven into mail; resistance to falling damage."),
    ),
    Race.THORNMIMIC: RaceDef(
        name="Thornmimic", speed=30, ability_bonuses={"DEX": 1, "CHA": 2}, group="Primal", before="Wood Spirit",
        flavor="Bark-skinned shapeshifters who replace their prey in the oldest forests.",
        race_weapon=_weapon("thorn_whip", "Thorn-Whip", "1d6",
            "Reach weapon (10 ft); on a critical hit, target is entangled until end of its next turn."),
        race_armor=_armor("bark_veil", "Bark-Veil", 1,
            "Regenerates 1 HP per hour when in a natural environment (forest, grassland, etc.)."),
    ),
    Race.CINDERKIN: RaceDef(
        name="Cinderkin", speed=35, ability_bonuses={"INT": 1, "DEX": 2}, group="Primal", before="Sun-Spark",
        flavor="Crystalline fire-sprites forged in the hearts of volcanoes.",
        race_weapon=_weapon("ember_dart", "Ember Dart", "1d4",
            "Thrown 20/60 ft; ignites targets on hit. Carries 3 darts per rest."),
        race_armor=_armor("crystal_shard_shell", "Crystal-Shard Shell", 1,
            "Razor-edged crystal; attackers who grapple you take 1d4 piercing damage."),
    ),
    Race.DEEPTYRANT: RaceDef(
        name="Deep-Tyrant", speed=30, ability_bonuses={"STR": 1, "INT": 2}, group="Primal", before="Abyssal Guard",
        flavor="Ancient cephalopodic minds who rule kingdoms from the lightless abyss.",
        race_weapon=_weapon("crushing_tentacle", "Crushing Tentacle", "1d8",
            "Reach 10 ft; on hit, target must make DC 13 STR save or be grappled."),
        race_armor=_armor("abyssal_shell", "Abyssal Shell", 2,
            "Pressure-hardened plate; resistance to cold damage and crushing pressure."),
    ),
    Race.GRIMCROW: RaceDef(
        name="Grimcrow", speed=30, ability_bonuses={"WIS": 2, "INT": 1}, group="Primal", before="Fate-Watcher",
        flavor="Obsidian-feathered oracles who steal living magic and bind it to bone.",
        race_weapon=_weapon("fate_talon", "Fate-Talon", "1d4",
            "Siphons luck; target subtracts 1 from its next attack roll or saving throw on a hit."),
        race_armor=_armor("bone_woven_shroud", "Bone-Woven Shroud", 1,
            "Woven from prophesied bones; advantage on saving throws against divination effects."),
    ),
    # ── Eldritch ─────────────────────────────────────────────────────────────
    Race.BLOODWEAVER: RaceDef(
        name="Bloodweaver", speed=30, ability_bonuses={"CHA": 2, "INT": 1}, group="Eldritch", before="High Vampire",
        flavor="Regal horrors who conquer entire bloodlines from the inside out.",
        race_weapon=_weapon("blood_spike_lash", "Blood-Spike Lash", "1d6",
            "Necrotic barbs; heals you for 2 HP on each successful hit."),
        race_armor=_armor("crimson_veil", "Crimson Veil", 1,
            "Blood-thickened carapace; grants an extra +1 AC when your HP is below half maximum."),
    ),
    Race.DREAMHUSK: RaceDef(
        name="Dreamhusk", speed=30, ability_bonuses={"WIS": 2, "CHA": 1}, group="Eldritch", before="Sleep-Walker",
        flavor="Spore-borne entities that project the faces of the beloved dead.",
        race_weapon=_weapon("spore_burst", "Spore-Burst", "1d4",
            "5-ft radius on throw; DC 12 CON save or target is poisoned for 1 minute. 3 charges per rest."),
        race_armor=_armor("husk_skin", "Husk-Skin", 1,
            "Spore-secreting outer layer; creatures that strike you in melee must make DC 11 CON or be sickened."),
    ),
    Race.BONEDRIFTER: RaceDef(
        name="Bonedrifter", speed=20, ability_bonuses={"CON": 2, "STR": 1}, group="Eldritch", before="Bone-Construct",
        flavor="Parasitic beings that rewrite their hosts skeleton-first into living prisons.",
        race_weapon=_weapon("ossified_club", "Ossified Club", "1d6",
            "Dense bone-mass impact; advantage on Shove attempts. Counts as bludgeoning."),
        race_armor=_armor("bone_lattice_carapace", "Bone-Lattice Carapace", 2,
            "Reinforced skeleton; you cannot be knocked prone by effects that move less than 10 ft."),
    ),
    Race.MINDSPIDER: RaceDef(
        name="Mindspider", speed=40, ability_bonuses={"INT": 2, "DEX": 1}, group="Eldritch", before="Telepath",
        flavor="Translucent arachnids that harvest plans and secrets from sleeping prey.",
        race_weapon=_weapon("psychic_web", "Psychic-Web", "1d4",
            "Ranged 30 ft; on hit, target is restrained (DC 12 STR to escape as action). 3 charges per rest."),
        race_armor=_armor("silk_steel_exoskeleton", "Silk-Steel Exoskeleton", 1,
            "Web-reinforced chitin; resistance to psychic damage."),
    ),
    Race.CHAOSLING: RaceDef(
        name="Chaosling", speed=35, ability_bonuses={"DEX": 2, "WIS": 1}, group="Eldritch", before="Wild Mage",
        flavor="Twitching fragments of unraveled reality stitched into borrowed flesh.",
        race_weapon=_weapon("entropy_bolt", "Entropy Bolt", "1d6",
            "Damage type changes each round (fire → cold → lightning → thunder → repeat). 20/60 ft ranged."),
        race_armor=_armor("chaos_weave", "Chaos-Weave", 1,
            "Unpredictable energy deflection; attackers cannot gain advantage against you from flanking."),
    ),
    # ── Mechanical ───────────────────────────────────────────────────────────
    Race.IRONVEIL: RaceDef(
        name="Ironveil", speed=40, ability_bonuses={"DEX": 2, "INT": 1}, group="Mechanical", before="Security Automaton",
        flavor="Gossamer-thin war constructs that fold themselves flat to slip through walls and armor plating. Deceptively fragile looking, catastrophically sharp.",
        race_weapon=_weapon("razor_wire_whip", "Razor-Wire Whip", "1d6",
            "Reach 10 ft; deals 1 ongoing slashing damage per turn until target uses action to remove."),
        race_armor=_armor("folded_steel_plates", "Folded-Steel Plates", 1,
            "Paper-thin but razor-edged; attackers using bludgeoning weapons have -1 to hit against you."),
    ),
    Race.FORGESPAWN: RaceDef(
        name="Forgespawn", speed=35, ability_bonuses={"STR": 2, "CON": 1}, group="Mechanical", before="Industrial Golem",
        flavor="Liquid-metal organisms that cool into whatever shape the battlefield demands. Born in furnaces, comfortable in fire.",
        race_weapon=_weapon("molten_fist", "Molten Fist", "1d8",
            "Fire damage on hit; softens metal armor — targets in metal armor have -1 AC until their next turn."),
        race_armor=_armor("liquid_metal_skin", "Liquid-Metal Skin", 2,
            "Auto-seals wounds when heated; you regain 1 HP when you take fire damage instead of being harmed."),
    ),
    Race.CINDERPLATE: RaceDef(
        name="Cinderplate", speed=20, ability_bonuses={"STR": 2, "WIS": 1}, group="Mechanical", before="Furnace Guard",
        flavor="Armored plating over a molten core. They run hot, cool slow, and leave scorch marks on everything they touch.",
        race_weapon=_weapon("forge_hammer", "Forge-Hammer", "1d10",
            "Two-handed bludgeoning; ignores DR from nonmagical armor. Leaves scorched craters on stone."),
        race_armor=_armor("furnace_plate", "Furnace Plate", 2,
            "Built-in heat sink; immune to being set on fire. Glows red after sustained combat."),
    ),
    Race.HEXGEAR: RaceDef(
        name="Hexgear", speed=35, ability_bonuses={"INT": 2, "DEX": 1}, group="Mechanical", before="Logic-Cube",
        flavor="Six-sided modular beings that reconfigure their body layout mid-combat. No consistent face, no consistent silhouette.",
        race_weapon=_weapon("reconfigured_blade", "Reconfigured Blade", "1d6",
            "Damage type rotates each round (slashing → piercing → bludgeoning). Enemies can't predict its form."),
        race_armor=_armor("modular_shielding", "Modular Shielding", 1,
            "Reconfigures to match incoming attack type; reduces the first hit of each damage type per combat by 1."),
    ),
    Race.WIREWRAITH: RaceDef(
        name="Wirewraith", speed=45, ability_bonuses={"DEX": 2, "WIS": 1}, group="Mechanical", before="Data-Ghost",
        flavor="Exposed-nerve constructs that transmit pain and data at the same speed. They feel everything, process it, and don't stop moving.",
        race_weapon=_weapon("neural_lash", "Neural-Lash", "1d6",
            "Lightning damage; on a critical hit, target is paralyzed until end of its next turn."),
        race_armor=_armor("exposed_wire_mesh", "Exposed-Wire Mesh", 1,
            "Conducts electricity; metal-weapon attackers take 1 lightning damage on each hit against you."),
    ),
    # ── Humanoid ─────────────────────────────────────────────────────────────
    Race.ASHENBORN: RaceDef(
        name="Ashenborn", speed=30, ability_bonuses={"CON": 2, "STR": 1}, group="Humanoid", before="Human",
        flavor="Humans who burned through the Paradox and came out the other side charred, fireproof, and furious.",
        race_weapon=_weapon("emberstone_axe", "Emberstone Axe", "1d6",
            "Fire-infused blade; deals 1 extra fire damage per strike. The edge never dulls."),
        race_armor=_armor("charred_bone_mail", "Charred-Bone Mail", 1,
            "Fire-resistant; immunity to being ignited by nonmagical flames."),
    ),
    Race.HOLLOWSONG: RaceDef(
        name="Hollowsong", speed=35, ability_bonuses={"WIS": 2, "INT": 1}, group="Humanoid", before="Elf",
        flavor="Elves whose magic inverted; they no longer cast, they absorb, and it's starting to show.",
        race_weapon=_weapon("silence_staff", "Silence-Staff", "1d6",
            "Absorbs a magical effect on hit; DC 13 CON or target cannot cast spells until end of next turn."),
        race_armor=_armor("absorption_mantle", "Absorption Mantle", 1,
            "Absorbs the first 2 damage from any magical hit each round."),
    ),
    Race.VEILBORN: RaceDef(
        name="Veilborn", speed=40, ability_bonuses={"DEX": 2, "CHA": 1}, group="Humanoid", before="Dark Elf",
        flavor="Dark elves who were already living in the dark when the Paradox hit; they adapted faster than anyone and trust no one.",
        race_weapon=_weapon("shadow_blade", "Shadow-Blade", "1d6",
            "+2 to hit in dim light or darkness. Deals necrotic damage in darkness."),
        race_armor=_armor("drow_silk_harness", "Drow-Silk Harness", 1,
            "Near-invisible in shadow; advantage on Stealth checks in dim light or darkness."),
    ),
    Race.THORNWEFT: RaceDef(
        name="Thornweft", speed=30, ability_bonuses={"WIS": 2, "CON": 1}, group="Humanoid", before="Wood Elf",
        flavor="Wood elves who merged with the forests during the silence; bark grows where skin used to be.",
        race_weapon=_weapon("briar_spear", "Briar Spear", "1d8",
            "Reach 10 ft; plants thorns on hit — target takes 1 piercing damage per turn until removed (DC 11 Medicine)."),
        race_armor=_armor("living_bark_armor", "Living Bark Armor", 1,
            "Regenerates 1 HP per hour when exposed to sunlight or rain."),
    ),
    Race.ASHCROWN: RaceDef(
        name="Ashcrown", speed=35, ability_bonuses={"INT": 2, "CHA": 1}, group="Humanoid", before="High Elf",
        flavor="High elves who refused to change and paid for it; regal, brittle, and slowly going translucent.",
        race_weapon=_weapon("crystalline_rapier", "Crystalline Rapier", "1d6",
            "Precision blade; advantage on attack rolls against unarmored or lightly armored targets."),
        race_armor=_armor("translucent_shield", "Translucent Shield", 1,
            "Faded high-elf ward; reduces psychic damage by 2."),
    ),
    Race.IRONFAST: RaceDef(
        name="Ironfast", speed=25, ability_bonuses={"CON": 2, "STR": 1}, group="Humanoid", before="Dwarf",
        flavor="Dwarves whose bones calcified past stone; they are slower, denser, and nearly impossible to put down.",
        race_weapon=_weapon("stone_crusher_maul", "Stone-Crusher Maul", "1d10",
            "Two-handed; -1 to hit but +2 bonus damage. Breaks through fortifications and stone walls."),
        race_armor=_armor("calcite_plate", "Calcite Plate", 3,
            "Calcified bone reinforcement; you are immune to being moved involuntarily unless you fail a DC 14 STR save."),
    ),
    Race.COREBORN: RaceDef(
        name="Coreborn", speed=25, ability_bonuses={"CON": 2, "INT": 1}, group="Humanoid", before="Deep Dwarf",
        flavor="Deep dwarves who pulled something up from below during the Paradox; it came with them.",
        race_weapon=_weapon("deep_iron_pick", "Deep-Iron Pick", "1d6",
            "Ignores natural AC from thick hides and scales. What came up from below sharpens it still."),
        race_armor=_armor("abyssal_crust_armor", "Abyssal Crust Armor", 2,
            "Void-forged deep-earth plate; resistance to poison damage."),
    ),
    Race.WARPBRED: RaceDef(
        name="Warpbred", speed=35, ability_bonuses={"STR": 2, "CON": 1}, group="Humanoid", before="Orc",
        flavor="Orcs who leaned into the Paradox and asked it for more; nobody is sure what they traded.",
        race_weapon=_weapon("paradox_cleaver", "Paradox Cleaver", "1d8",
            "Variable damage type each hit (slashing/necrotic/psychic — enemy cannot predict or resist). +1 to hit."),
        race_armor=_armor("mutated_hide", "Mutated Hide", 2,
            "Grotesque paradox-flesh; reduces critical hits to normal hits once per combat."),
    ),
    Race.SPLITBLOOD: RaceDef(
        name="Splitblood", speed=30, ability_bonuses={"STR": 1, "CON": 2}, group="Humanoid", before="Half-Orc",
        flavor="Half-orcs whose two halves stopped agreeing during the silence; they are in a constant negotiation with themselves.",
        race_weapon=_weapon("half_blood_axe", "Half-Blood Axe", "1d6",
            "One side slashing, one bludgeoning; choose damage type per attack. Enemies resistant to one are hit by the other."),
        race_armor=_armor("contested_plate", "Contested Plate", 1,
            "Cobbled from both heritages; +1 STR saving throws and +1 CON saving throws."),
    ),
    Race.DUSKWEFT: RaceDef(
        name="Duskweft", speed=40, ability_bonuses={"DEX": 2, "WIS": 1}, group="Humanoid", before="Halfling",
        flavor="Halflings who slipped sideways during the silence and haven't fully come back; they flicker.",
        race_weapon=_weapon("flicker_dagger", "Flicker Dagger", "1d4",
            "Melee or thrown 20/60 ft; advantage on attacks made immediately after teleporting or repositioning."),
        race_armor=_armor("phase_cloth", "Phase-Cloth", 1,
            "Flickering displacement; critical hits against you are re-rolled once — attacker takes the lower result."),
    ),
    Race.GLITCHKIN: RaceDef(
        name="Glitchkin", speed=30, ability_bonuses={"INT": 2, "DEX": 1}, group="Humanoid", before="Gnome",
        flavor="Gnomes whose tinkering instinct turned inward; they've been modifying themselves ever since.",
        race_weapon=_weapon("modified_crossbow", "Modified Crossbow", "1d6",
            "Self-upgraded bolts; +1 to hit from precision modifications. Reloads as bonus action."),
        race_armor=_armor("self_repair_chassis", "Self-Repair Chassis", 1,
            "Auto-repairs 1 HP at the start of any turn in which you took no damage the previous round."),
    ),
    Race.FRACTURELINE: RaceDef(
        name="Fractureline", speed=35, ability_bonuses={"INT": 2, "CHA": 1}, group="Humanoid", before="Half-Elf",
        flavor="Half-elves split cleanly down the middle during the Paradox; one half remembers the old world, the other doesn't.",
        race_weapon=_weapon("split_edge_sword", "Split-Edge Sword", "1d6",
            "On a critical hit, make a second damage roll and add it — two halves, two cuts."),
        race_armor=_armor("paradox_split_shield", "Paradox-Split Shield", 1,
            "One side absorbs magic, one absorbs physical; reduce the first instance of each per combat by 1."),
    ),
    Race.EMBERPACT: RaceDef(
        name="Emberpact", speed=30, ability_bonuses={"CHA": 2, "STR": 1}, group="Humanoid", before="Tiefling",
        flavor="Tieflings whose infernal contracts dissolved in the Paradox; they kept the features and lost the leash.",
        race_weapon=_weapon("hellfire_scourge", "Hellfire Scourge", "1d6",
            "Fire + necrotic hybrid; deals 1 extra fire damage per strike. Smells of brimstone."),
        race_armor=_armor("infernal_remnant_plate", "Infernal Remnant Plate", 2,
            "Contract fragments stitched into metal; resistance to fire damage."),
    ),
    Race.FALLENLIGHT: RaceDef(
        name="Fallenlight", speed=35, ability_bonuses={"CHA": 2, "WIS": 1}, group="Humanoid", before="Aasimar",
        flavor="Aasimars whose divine connection severed; they still glow, but nothing answers when they call.",
        race_weapon=_weapon("severed_halo_blade", "Severed-Halo Blade", "1d6",
            "Radiant damage; weakened divine energy still burns undead (+2 vs undead) and fiends (+2 vs fiends)."),
        race_armor=_armor("diminished_radiance", "Diminished Radiance", 1,
            "Faded divine light as a deflective field; reduces necrotic damage by 2."),
    ),
    Race.SCALEWORN: RaceDef(
        name="Scaleworn", speed=30, ability_bonuses={"STR": 2, "DEX": 1}, group="Humanoid", before="Dragonborn",
        flavor="Dragonborn whose draconic heritage collapsed inward; the fire is still there, the bloodline is not.",
        race_weapon=_weapon("collapsed_fang_spear", "Collapsed-Fang Spear", "1d8",
            "Reach 10 ft; dragon heritage made weapon instead of bite. Deals +1 fire damage — the lineage bleeds through."),
        race_armor=_armor("inverted_scale_mail", "Inverted-Scale Mail", 1,
            "Scales turned inward for self-reinforcement; resistance to the original draconic damage type."),
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
    primary_item: InventoryItem
    equipment_choices: tuple[InventoryItem, ...]
    flavor: str

def _item(item_id: str, name: str, equipped: bool = False, qty: int = 1,
          notes: str | None = None) -> InventoryItem:
    return InventoryItem(id=item_id, name=name, quantity=qty,
                         equipped=equipped, notes=notes)

ROLES: dict[PredatorRole, RoleDef] = {
    PredatorRole.STALKER: RoleDef(
        name="Stalker",
        primary_item=_item("razor_claws", "Razor Claws", equipped=True),
        equipment_choices=(
            _item("smoke_pellets", "Smoke Pellets", qty=3, notes="Blind pursuers for one round."),
            _item("grappling_hook", "Grappling Hook", notes="Reach elevated positions instantly."),
            _item("caltrops", "Caltrops", qty=10, notes="Scatter to slow pursuit."),
        ),
        flavor="Single-target elimination and ambushing."
    ),
    PredatorRole.VANGUARD: RoleDef(
        name="Vanguard",
        primary_item=_item("heavy_mandibles", "Heavy Mandibles", equipped=True),
        equipment_choices=(
            _item("reinforced_plating", "Reinforced Plating", equipped=True, notes="+1 AC while worn."),
            _item("war_banner", "War Banner", notes="Allies within 10ft gain advantage on morale saves."),
            _item("battle_horn", "Battle Horn", notes="Demoralize enemies on a successful Intimidation check."),
        ),
        flavor="Zone control and intimidation."
    ),
    PredatorRole.CATALYST: RoleDef(
        name="Catalyst",
        primary_item=_item("venom_sac", "Venom Sac", equipped=True),
        equipment_choices=(
            _item("web_strands", "Web Strands", qty=5, notes="Restrain a target on a hit."),
            _item("explosive_spore", "Explosive Spore", qty=3, notes="5ft burst on impact."),
            _item("paralytic_dust", "Paralytic Dust", notes="DC 13 CON or target is slowed."),
        ),
        flavor="Environmental manipulation and trapping."
    ),
    PredatorRole.SIPHONER: RoleDef(
        name="Siphoner",
        primary_item=_item("energy_leech", "Energy Leech", equipped=True),
        equipment_choices=(
            _item("void_battery", "Void Battery", notes="Store stolen energy for a burst attack."),
            _item("essence_vial", "Essence Vial", qty=3, notes="Distilled lifeforce; heals 1d6 HP."),
            _item("null_trap", "Null Trap", qty=2, notes="Suppresses magic in a 10ft radius."),
        ),
        flavor="Resource theft and adaptation."
    ),
}


# ─────────────────────── Background definitions ───────────────────────

@dataclass(frozen=True)
class BackgroundDef:
    name: str
    flavor: str
    perk_name: str
    perk_description: str
    bonus_skills: tuple[str, ...]   # auto-granted
    skill_pool: tuple[str, ...]     # player picks 2 from this


BACKGROUNDS: dict[str, BackgroundDef] = {
    "void_scavenger": BackgroundDef(
        name="Void Scavenger",
        flavor="You stripped remnants from dead worlds and dying ships before the Paradox. You know how to find value in decay.",
        perk_name="Salvage Sense",
        perk_description="You can identify the approximate value and origin of any object with a moment's study.",
        bonus_skills=("Survival", "Sleight of Hand"),
        skill_pool=("Athletics", "Perception", "Stealth", "Investigation"),
    ),
    "paradox_cultist": BackgroundDef(
        name="Paradox Cultist",
        flavor="You worshipped the coming change, believing the Paradox was divine reckoning. You prepared for it — and it noticed.",
        perk_name="Paradox Scar",
        perk_description="You have uncanny insight into transformations and can sense when someone is about to change.",
        bonus_skills=("Arcana", "Religion"),
        skill_pool=("Insight", "Persuasion", "Deception", "History"),
    ),
    "remnant_soldier": BackgroundDef(
        name="Remnant Soldier",
        flavor="You served in the armies of the old world and lived through the Paradox. Your training survived the silence — barely.",
        perk_name="Battle Hardened",
        perk_description="You cannot be frightened while at full HP.",
        bonus_skills=("Athletics", "Intimidation"),
        skill_pool=("Acrobatics", "Perception", "Survival", "Animal Handling"),
    ),
    "archive_scholar": BackgroundDef(
        name="Archive Scholar",
        flavor="You preserved knowledge of what existed before, cataloguing species and civilizations as they dissolved.",
        perk_name="Living Catalogue",
        perk_description="Advantage on History and Nature checks related to pre-Paradox civilizations.",
        bonus_skills=("History", "Arcana"),
        skill_pool=("Investigation", "Nature", "Religion", "Medicine"),
    ),
    "feral_wanderer": BackgroundDef(
        name="Feral Wanderer",
        flavor="You had no home before the Paradox, and nothing to lose when it came. You drifted and survived on instinct alone.",
        perk_name="Apex Instinct",
        perk_description="You always have advantage on initiative rolls.",
        bonus_skills=("Survival", "Perception"),
        skill_pool=("Athletics", "Stealth", "Animal Handling", "Nature"),
    ),
    "syndicate_broker": BackgroundDef(
        name="Syndicate Broker",
        flavor="You ran deals, moved cargo no one was supposed to know about, and kept the underground's lights on through the silence.",
        perk_name="Network Ghost",
        perk_description="In any settlement, you can find someone who owes you a favor with a DC 12 Persuasion check.",
        bonus_skills=("Deception", "Persuasion"),
        skill_pool=("Stealth", "Investigation", "Sleight of Hand", "Intimidation"),
    ),
    "settlement_warden": BackgroundDef(
        name="Settlement Warden",
        flavor="You defended one of the fragile post-Paradox communities that clawed their way back to order. Some even survived.",
        perk_name="Guardian's Presence",
        perk_description="Allies within 10 feet have advantage on saving throws against fear effects.",
        bonus_skills=("Insight", "Medicine"),
        skill_pool=("Athletics", "Persuasion", "Perception", "Animal Handling"),
    ),
    "void_oracle": BackgroundDef(
        name="Void Oracle",
        flavor="The Paradox showed you things — glimpses of what was, what could be, what should never be. You're not sure if it was a gift.",
        perk_name="Fractured Sight",
        perk_description="Once per day, you may ask the DM a yes/no question about the immediate future.",
        bonus_skills=("Insight", "History"),
        skill_pool=("Arcana", "Perception", "Religion", "Deception"),
    ),
}


# ─────────────────────── Feat definitions ───────────────────────

@dataclass(frozen=True)
class FeatDef:
    name: str
    flavor: str
    mechanical_effect: str


FEATS: dict[str, FeatDef] = {
    "apex_predator": FeatDef(
        name="Apex Predator",
        flavor="Your transformed form inspires primal terror in prey.",
        mechanical_effect="+2 to Intimidation checks while transformed.",
    ),
    "hive_mind": FeatDef(
        name="Hive Mind",
        flavor="You share a wordless psychic link with those you trust.",
        mechanical_effect="Communicate telepathically with party members within 30 feet.",
    ),
    "regenerator": FeatDef(
        name="Regenerator",
        flavor="Your body knits itself back together faster than it can be broken.",
        mechanical_effect="At the start of your turn, if above 0 HP, regain 1 HP.",
    ),
    "phase_shift": FeatDef(
        name="Phase Shift",
        flavor="For a single suspended heartbeat, you exist between states.",
        mechanical_effect="Once per rest, pass through solid objects up to 5 feet.",
    ),
    "pack_tactics": FeatDef(
        name="Pack Tactics",
        flavor="Predators hunt better together.",
        mechanical_effect="Advantage on attack rolls when an ally is adjacent to the target.",
    ),
    "void_touched": FeatDef(
        name="Void Touched",
        flavor="The silence between worlds has left its mark on your biology.",
        mechanical_effect="Resistance to necrotic and psychic damage.",
    ),
    "echo_memory": FeatDef(
        name="Echo Memory",
        flavor="A touch can unlock what a creature knew, felt, or feared.",
        mechanical_effect="By touching a creature, access its most recent memory (DM discretion).",
    ),
    "apex_form": FeatDef(
        name="Apex Form",
        flavor="Desperation unlocks your most dangerous instincts.",
        mechanical_effect="Advantage on STR checks and saving throws when below half maximum HP.",
    ),
}


# ─────────────────────── Skills, Cantrips, Alignments, Dialogue Styles ────

SKILLS: list[str] = [
    "Athletics",
    "Acrobatics", "Sleight of Hand", "Stealth",
    "Arcana", "History", "Investigation", "Nature", "Religion",
    "Animal Handling", "Insight", "Medicine", "Perception", "Survival",
    "Deception", "Intimidation", "Performance", "Persuasion",
]

CANTRIPS: list[str] = [
    "Voidbolt", "Shadowweave", "Mindspike", "Entangle",
    "Toll the Dead", "Minor Illusion", "Chill Touch", "Eldritch Blast",
    "Acid Splash", "Prestidigitation",
]

ALIGNMENTS: list[str] = [
    "Lawful Good", "Neutral Good", "Chaotic Good",
    "Lawful Neutral", "True Neutral", "Chaotic Neutral",
    "Lawful Evil", "Neutral Evil", "Chaotic Evil",
]

DIALOGUE_STYLES: list[dict] = [
    {"id": "formal",      "name": "Formal & Eloquent",    "flavor": "Precise, measured language. You choose every word deliberately."},
    {"id": "casual",      "name": "Casual & Earthy",       "flavor": "Plain speech, direct and honest. No pretense."},
    {"id": "sarcastic",   "name": "Sarcastic & Dry",       "flavor": "Wit is your armor. You deflect with humor."},
    {"id": "stoic",       "name": "Stoic & Minimal",       "flavor": "Silence speaks loudest. You say only what matters."},
    {"id": "boisterous",  "name": "Boisterous & Loud",     "flavor": "Everything deserves enthusiasm. Volume is your birthright."},
    {"id": "cryptic",     "name": "Cryptic & Mysterious",  "flavor": "You speak in metaphor and half-truths. Listeners work for it."},
]

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
    game_state: GameState,
    starting_era: str = "after",
    # Customization
    background: str | None = None,
    equipment_choice_id: str | None = None,
    skill_proficiencies: list[str] | None = None,
    feat: str | None = None,
    cantrips: list[str] | None = None,
    alignment: str | None = None,
    pronouns: str = "they/them",
    title: str | None = None,
    dialogue_style: str | None = None,
    physical_description: str = "",
    backstory: str = "",
    personality_traits: str = "",
    flaws: str = "",
    bonds: str = "",
    ideals: str = "",
    keepsake_name: str | None = None,
) -> CharacterSheet:
    if not is_valid_standard_array(abilities):
        raise ValueError(
            "abilities must be a permutation of the standard array "
            f"{STANDARD_ARRAY}"
        )

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

    # Race armor contributes a flat AC bonus
    if r_def.race_armor:
        ac += r_def.race_armor.armor_ac_bonus

    # Build inventory: race gear first, then role gear
    inventory: list[InventoryItem] = []
    if r_def.race_weapon:
        inventory.append(r_def.race_weapon)
    if r_def.race_armor:
        inventory.append(r_def.race_armor)
    inventory.append(p_def.primary_item)

    chosen_secondary: InventoryItem | None = None
    if equipment_choice_id and p_def.equipment_choices:
        for item in p_def.equipment_choices:
            if item.id == equipment_choice_id:
                chosen_secondary = item
                break
    if chosen_secondary is None and p_def.equipment_choices:
        chosen_secondary = p_def.equipment_choices[0]
    if chosen_secondary is not None:
        inventory.append(chosen_secondary)

    # Add keepsake trinket
    if keepsake_name:
        inventory.append(_item(
            f"keepsake_{char_id}", keepsake_name,
            notes="A personal keepsake. No mechanical value."
        ))

    # Merge background auto-skills with player-picked skills (deduplicated)
    final_skills: list[str] = list(skill_proficiencies or [])
    if background and background in BACKGROUNDS:
        bg_def = BACKGROUNDS[background]
        for skill in bg_def.bonus_skills:
            if skill not in final_skills:
                final_skills.append(skill)

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
        skill_proficiencies=final_skills,
        inventory=inventory,
        position=spawn_pos,
        movement_remaining=r_def.speed,
        is_transformed=(starting_era == "after"),
        background=background,
        feat=feat,
        cantrips=cantrips or [],
        alignment=alignment,
        pronouns=pronouns,
        title=title,
        dialogue_style=dialogue_style,
        physical_description=physical_description,
        backstory=backstory,
        personality_traits=personality_traits,
        flaws=flaws,
        bonds=bonds,
        ideals=ideals,
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


# ─────────────────────── Race enemy builder ───────────────────────

# Canonical ability priorities per race group — used when building NPC enemies.
# Values are standard-array assignments biased toward the race's primary stats.
_RACE_ENEMY_BASES: dict[Race, tuple[int, int, int, int, int, int]] = {
    # STR, DEX, CON, INT, WIS, CHA
    Race.VOIDWRAITH:   (13, 10, 12, 15, 10,  8),
    Race.NULLSHADE:    ( 8, 15, 12, 13, 10, 10),
    Race.IRONLOCUST:   (12, 14, 13,  8, 10,  8),
    Race.EMBERVEIN:    (15, 8,  14, 10, 10,  8),
    Race.RIFTWALKER:   (10, 13, 10, 12, 14,  8),
    Race.SOLARLORD:    (10, 13, 10, 10, 14, 15),
    Race.THORNMIMIC:   (10, 13, 12, 10, 10, 14),
    Race.CINDERKIN:    ( 8, 14, 10, 13, 10, 10),
    Race.DEEPTYRANT:   (13,  8, 12, 15, 10, 10),
    Race.GRIMCROW:     ( 8, 12, 10, 13, 15, 10),
    Race.BLOODWEAVER:  (10, 12, 10, 13, 10, 15),
    Race.DREAMHUSK:    ( 8, 10, 12, 10, 15, 13),
    Race.BONEDRIFTER:  (13,  8, 15, 10, 10, 10),
    Race.MINDSPIDER:   ( 8, 13, 10, 15, 10, 10),
    Race.CHAOSLING:    (10, 14, 10, 10, 13,  8),
    Race.IRONVEIL:     ( 8, 15, 10, 13, 10, 10),
    Race.FORGESPAWN:   (15, 10, 14,  8, 10,  8),
    Race.CINDERPLATE:  (15,  8, 14, 10, 13, 8),
    Race.HEXGEAR:      (10, 13, 10, 15, 10,  8),
    Race.WIREWRAITH:   ( 8, 15, 10, 10, 13, 10),
    Race.ASHENBORN:    (13, 10, 15,  8, 10,  8),
    Race.HOLLOWSONG:   ( 8, 13, 10, 13, 15, 10),
    Race.VEILBORN:     ( 8, 15, 12, 10, 10, 13),
    Race.THORNWEFT:    (10, 12, 14,  8, 15, 10),
    Race.ASHCROWN:     ( 8, 13, 10, 15, 10, 13),
    Race.IRONFAST:     (13,  8, 15, 10, 10, 10),
    Race.COREBORN:     (12,  8, 15, 13, 10, 10),
    Race.WARPBRED:     (15, 10, 14,  8, 10,  8),
    Race.SPLITBLOOD:   (13, 10, 14,  8, 10, 10),
    Race.DUSKWEFT:     ( 8, 15, 10, 10, 13, 10),
    Race.GLITCHKIN:    ( 8, 13, 10, 15, 10, 10),
    Race.FRACTURELINE: ( 8, 13, 10, 14, 10, 13),
    Race.EMBERPACT:    (13, 10, 12, 10, 10, 15),
    Race.FALLENLIGHT:  (10, 13, 10, 10, 14, 15),
    Race.SCALEWORN:    (15, 13, 12,  8, 10, 10),
}


def build_race_enemy(
    enemy_id: str,
    race: Race,
    ev_state: EvolutionaryState,
    room_id: str,
    position: Coord,
    name_override: str | None = None,
    xp_reward: int | None = None,
) -> EnemySheet:
    """
    Build an EnemySheet for a hostile NPC using the race's weapon/armor and
    derived combat stats. Stats are scaled to NPC level — no standard-array
    constraint, but the same formulas as PCs.
    """
    r_def = RACES[race]
    s_def = STATES[ev_state]

    base = _RACE_ENEMY_BASES[race]
    str_, dex_, con_, int_, wis_, cha_ = base
    # Apply racial ability bonuses
    totals = {"STR": str_, "DEX": dex_, "CON": con_, "INT": int_, "WIS": wis_, "CHA": cha_}
    for abi, bonus in r_def.ability_bonuses.items():
        totals[abi] = totals.get(abi, 10) + bonus
    str_, dex_, con_ = totals["STR"], totals["DEX"], totals["CON"]

    con_mod = _ability_modifier(con_)
    dex_mod = _ability_modifier(dex_)
    str_mod = _ability_modifier(str_)
    best_mod = max(str_mod, dex_mod)

    hp_max = max(1, s_def.hit_die + con_mod)
    ac = s_def.base_armor_class + dex_mod
    if r_def.race_armor:
        ac += r_def.race_armor.armor_ac_bonus
    attack_bonus = best_mod + 2   # +2 proficiency

    weapon_dice = "1d6"
    if r_def.race_weapon and r_def.race_weapon.damage_dice:
        weapon_dice = r_def.race_weapon.damage_dice

    default_xp = max(25, hp_max * 6 + ac * 4)
    enemy_name = name_override or r_def.name
    weapon_name = r_def.race_weapon.name if r_def.race_weapon else "Natural Weapon"
    description = (
        f"A hostile {enemy_name}. "
        f"Wields {weapon_name}. {r_def.flavor}"
    )

    return EnemySheet(
        id=enemy_id,
        name=enemy_name,
        room_id=room_id,
        position=position,
        hp_current=hp_max,
        hp_max=hp_max,
        armor_class=ac,
        attack_bonus=attack_bonus,
        damage_dice=weapon_dice,
        xp_reward=xp_reward or default_xp,
        alive=True,
        sprite_key="enemy_race",
        description=description,
    )
