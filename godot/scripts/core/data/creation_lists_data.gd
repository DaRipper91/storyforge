# GENERATED - do not edit by hand.
# Source: src/storyforge/core/character_factory.py
# Regenerate: uv run python tools/golden/gen_gd_data.py
extends RefCounted
## Creation lists and enemy base stats.

const STANDARD_ARRAY := [15, 14, 13, 12, 10, 8]

const SKILLS := [
	"Athletics",
	"Acrobatics",
	"Sleight of Hand",
	"Stealth",
	"Arcana",
	"History",
	"Investigation",
	"Nature",
	"Religion",
	"Animal Handling",
	"Insight",
	"Medicine",
	"Perception",
	"Survival",
	"Deception",
	"Intimidation",
	"Performance",
	"Persuasion",
]

const CANTRIPS := [
	"Voidbolt",
	"Shadowweave",
	"Mindspike",
	"Entangle",
	"Toll the Dead",
	"Minor Illusion",
	"Chill Touch",
	"Eldritch Blast",
	"Acid Splash",
	"Prestidigitation",
]

const ALIGNMENTS := [
	"Lawful Good",
	"Neutral Good",
	"Chaotic Good",
	"Lawful Neutral",
	"True Neutral",
	"Chaotic Neutral",
	"Lawful Evil",
	"Neutral Evil",
	"Chaotic Evil",
]

const DIALOGUE_STYLES := [
	{
		"id": "formal",
		"name": "Formal & Eloquent",
		"flavor": "Precise, measured language. You choose every word deliberately.",
	},
	{
		"id": "casual",
		"name": "Casual & Earthy",
		"flavor": "Plain speech, direct and honest. No pretense.",
	},
	{
		"id": "sarcastic",
		"name": "Sarcastic & Dry",
		"flavor": "Wit is your armor. You deflect with humor.",
	},
	{
		"id": "stoic",
		"name": "Stoic & Minimal",
		"flavor": "Silence speaks loudest. You say only what matters.",
	},
	{
		"id": "boisterous",
		"name": "Boisterous & Loud",
		"flavor": "Everything deserves enthusiasm. Volume is your birthright.",
	},
	{
		"id": "cryptic",
		"name": "Cryptic & Mysterious",
		"flavor": "You speak in metaphor and half-truths. Listeners work for it.",
	},
]

const RACE_ENEMY_BASES := {
	"voidwraith": [13, 10, 12, 15, 10, 8],
	"nullshade": [8, 15, 12, 13, 10, 10],
	"ironlocust": [12, 14, 13, 8, 10, 8],
	"embervein": [15, 8, 14, 10, 10, 8],
	"riftwalker": [10, 13, 10, 12, 14, 8],
	"solarlord": [10, 13, 10, 10, 14, 15],
	"thornmimic": [10, 13, 12, 10, 10, 14],
	"cinderkin": [8, 14, 10, 13, 10, 10],
	"deeptyrant": [13, 8, 12, 15, 10, 10],
	"grimcrow": [8, 12, 10, 13, 15, 10],
	"bloodweaver": [10, 12, 10, 13, 10, 15],
	"dreamhusk": [8, 10, 12, 10, 15, 13],
	"bonedrifter": [13, 8, 15, 10, 10, 10],
	"mindspider": [8, 13, 10, 15, 10, 10],
	"chaosling": [10, 14, 10, 10, 13, 8],
	"ironveil": [8, 15, 10, 13, 10, 10],
	"forgespawn": [15, 10, 14, 8, 10, 8],
	"cinderplate": [15, 8, 14, 10, 13, 8],
	"hexgear": [10, 13, 10, 15, 10, 8],
	"wirewraith": [8, 15, 10, 10, 13, 10],
	"ashenborn": [13, 10, 15, 8, 10, 8],
	"hollowsong": [8, 13, 10, 13, 15, 10],
	"veilborn": [8, 15, 12, 10, 10, 13],
	"thornweft": [10, 12, 14, 8, 15, 10],
	"ashcrown": [8, 13, 10, 15, 10, 13],
	"ironfast": [13, 8, 15, 10, 10, 10],
	"coreborn": [12, 8, 15, 13, 10, 10],
	"warpbred": [15, 10, 14, 8, 10, 8],
	"splitblood": [13, 10, 14, 8, 10, 10],
	"duskweft": [8, 15, 10, 10, 13, 10],
	"glitchkin": [8, 13, 10, 15, 10, 10],
	"fractureline": [8, 13, 10, 14, 10, 13],
	"emberpact": [13, 10, 12, 10, 10, 15],
	"fallenlight": [10, 13, 10, 10, 14, 15],
	"scaleworn": [15, 13, 12, 8, 10, 10],
}
