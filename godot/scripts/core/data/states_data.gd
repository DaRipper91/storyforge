# GENERATED - do not edit by hand.
# Source: src/storyforge/core/character_factory.py
# Regenerate: uv run python tools/golden/gen_gd_data.py
extends RefCounted
## Evolutionary state definitions keyed by enum value.

const STATES := {
	"behemoth": {
		"name": "Behemoth",
		"hit_die": 12,
		"base_armor_class": 16,
		"flavor": "A wall of muscle and chitin. High durability.",
	},
	"phantom": {
		"name": "Phantom",
		"hit_die": 6,
		"base_armor_class": 12,
		"flavor": "Incorporeal and ethereal. Hard to hit, but fragile.",
	},
	"swarm_host": {
		"name": "Swarm-Host",
		"hit_die": 10,
		"base_armor_class": 14,
		"flavor": "A living vessel for smaller entities. Balanced power.",
	},
	"mimic": {
		"name": "Mimic",
		"hit_die": 8,
		"base_armor_class": 13,
		"flavor": "Fluid and adaptive body structure. Versatile scout.",
	},
}
