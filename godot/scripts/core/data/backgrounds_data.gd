# GENERATED - do not edit by hand.
# Source: src/storyforge/core/character_factory.py
# Regenerate: uv run python tools/golden/gen_gd_data.py
extends RefCounted
## Backgrounds and feats (UI/prompt data).

const BACKGROUNDS := {
	"void_scavenger": {
		"name": "Void Scavenger",
		"flavor": "You stripped remnants from dead worlds and dying ships before the Paradox. You know how to find value in decay.",
		"perk_name": "Salvage Sense",
		"perk_description": "You can identify the approximate value and origin of any object with a moment's study.",
		"bonus_skills": ["Survival", "Sleight of Hand"],
		"skill_pool": ["Athletics", "Perception", "Stealth", "Investigation"],
	},
	"paradox_cultist": {
		"name": "Paradox Cultist",
		"flavor": "You worshipped the coming change, believing the Paradox was divine reckoning. You prepared for it — and it noticed.",
		"perk_name": "Paradox Scar",
		"perk_description": "You have uncanny insight into transformations and can sense when someone is about to change.",
		"bonus_skills": ["Arcana", "Religion"],
		"skill_pool": ["Insight", "Persuasion", "Deception", "History"],
	},
	"remnant_soldier": {
		"name": "Remnant Soldier",
		"flavor": "You served in the armies of the old world and lived through the Paradox. Your training survived the silence — barely.",
		"perk_name": "Battle Hardened",
		"perk_description": "You cannot be frightened while at full HP.",
		"bonus_skills": ["Athletics", "Intimidation"],
		"skill_pool": ["Acrobatics", "Perception", "Survival", "Animal Handling"],
	},
	"archive_scholar": {
		"name": "Archive Scholar",
		"flavor": "You preserved knowledge of what existed before, cataloguing species and civilizations as they dissolved.",
		"perk_name": "Living Catalogue",
		"perk_description": "Advantage on History and Nature checks related to pre-Paradox civilizations.",
		"bonus_skills": ["History", "Arcana"],
		"skill_pool": ["Investigation", "Nature", "Religion", "Medicine"],
	},
	"feral_wanderer": {
		"name": "Feral Wanderer",
		"flavor": "You had no home before the Paradox, and nothing to lose when it came. You drifted and survived on instinct alone.",
		"perk_name": "Apex Instinct",
		"perk_description": "You always have advantage on initiative rolls.",
		"bonus_skills": ["Survival", "Perception"],
		"skill_pool": ["Athletics", "Stealth", "Animal Handling", "Nature"],
	},
	"syndicate_broker": {
		"name": "Syndicate Broker",
		"flavor": "You ran deals, moved cargo no one was supposed to know about, and kept the underground's lights on through the silence.",
		"perk_name": "Network Ghost",
		"perk_description": "In any settlement, you can find someone who owes you a favor with a DC 12 Persuasion check.",
		"bonus_skills": ["Deception", "Persuasion"],
		"skill_pool": ["Stealth", "Investigation", "Sleight of Hand", "Intimidation"],
	},
	"settlement_warden": {
		"name": "Settlement Warden",
		"flavor": "You defended one of the fragile post-Paradox communities that clawed their way back to order. Some even survived.",
		"perk_name": "Guardian's Presence",
		"perk_description": "Allies within 10 feet have advantage on saving throws against fear effects.",
		"bonus_skills": ["Insight", "Medicine"],
		"skill_pool": ["Athletics", "Persuasion", "Perception", "Animal Handling"],
	},
	"void_oracle": {
		"name": "Void Oracle",
		"flavor": "The Paradox showed you things — glimpses of what was, what could be, what should never be. You're not sure if it was a gift.",
		"perk_name": "Fractured Sight",
		"perk_description": "Once per day, you may ask the DM a yes/no question about the immediate future.",
		"bonus_skills": ["Insight", "History"],
		"skill_pool": ["Arcana", "Perception", "Religion", "Deception"],
	},
}

const FEATS := {
	"apex_predator": {
		"name": "Apex Predator",
		"flavor": "Your transformed form inspires primal terror in prey.",
		"mechanical_effect": "+2 to Intimidation checks while transformed.",
	},
	"hive_mind": {
		"name": "Hive Mind",
		"flavor": "You share a wordless psychic link with those you trust.",
		"mechanical_effect": "Communicate telepathically with party members within 30 feet.",
	},
	"regenerator": {
		"name": "Regenerator",
		"flavor": "Your body knits itself back together faster than it can be broken.",
		"mechanical_effect": "At the start of your turn, if above 0 HP, regain 1 HP.",
	},
	"phase_shift": {
		"name": "Phase Shift",
		"flavor": "For a single suspended heartbeat, you exist between states.",
		"mechanical_effect": "Once per rest, pass through solid objects up to 5 feet.",
	},
	"pack_tactics": {
		"name": "Pack Tactics",
		"flavor": "Predators hunt better together.",
		"mechanical_effect": "Advantage on attack rolls when an ally is adjacent to the target.",
	},
	"void_touched": {
		"name": "Void Touched",
		"flavor": "The silence between worlds has left its mark on your biology.",
		"mechanical_effect": "Resistance to necrotic and psychic damage.",
	},
	"echo_memory": {
		"name": "Echo Memory",
		"flavor": "A touch can unlock what a creature knew, felt, or feared.",
		"mechanical_effect": "By touching a creature, access its most recent memory (DM discretion).",
	},
	"apex_form": {
		"name": "Apex Form",
		"flavor": "Desperation unlocks your most dangerous instincts.",
		"mechanical_effect": "Advantage on STR checks and saving throws when below half maximum HP.",
	},
}
