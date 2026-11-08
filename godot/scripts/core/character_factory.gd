class_name CoreCharacterFactory
extends RefCounted
## Port of src/storyforge/core/character_factory.py (logic only; the race /
## state / role tables are GENERATED into res://scripts/core/data/*.gd by
## tools/golden/gen_gd_data.py).
##
## Sheets are plain Dictionaries with the pydantic model_dump(mode="json")
## shape. Python exceptions come back as CoreError dictionaries.
## Every inventory item handed out is a deep copy of the template, so sheets
## never alias each other (Python shared the InventoryItem objects).

const _Grid := preload("res://scripts/core/grid.gd")
const _Roll := preload("res://scripts/core/roll_provider.gd")
const _Races := preload("res://scripts/core/data/races_data.gd")
const _States := preload("res://scripts/core/data/states_data.gd")
const _Roles := preload("res://scripts/core/data/roles_data.gd")
const _Backgrounds := preload("res://scripts/core/data/backgrounds_data.gd")
const _Lists := preload("res://scripts/core/data/creation_lists_data.gd")

const ABILITY_KEYS := ["STR", "DEX", "CON", "INT", "WIS", "CHA"]


static func _provider(rolls) -> CoreRollProvider:
	if rolls == null:
		return _Roll.live()
	return rolls


## Python: (score - 10) // 2 (floor division).
static func _ability_modifier(score: int) -> int:
	return floori((score - 10) / 2.0)


## True if the abilities are a permutation of [15,14,13,12,10,8].
static func is_valid_standard_array(abilities: Dictionary) -> bool:
	var values: Array = []
	for k in ABILITY_KEYS:
		values.append(int(abilities[k]))
	values.sort()
	values.reverse()
	var std: Array = _Lists.STANDARD_ARRAY
	return values == std


static func _std_array_text() -> String:
	return "(15, 14, 13, 12, 10, 8)"


static func _item(item_id: String, item_name: String, notes: Variant) -> Dictionary:
	return {
		"id": item_id, "name": item_name, "quantity": 1, "equipped": false,
		"value": 0, "notes": notes, "damage_dice": null, "armor_ac_bonus": 0,
	}


## Slugify name; append one token_hex(2) suffix on collision (not re-checked).
static func generate_char_id(char_name: String, existing: Array, rolls = null) -> String:
	var slug := ""
	for i in char_name.length():
		var c := char_name.substr(i, 1)
		if _is_alnum(c):
			slug += c.to_lower()
	if slug == "":
		slug = "char"
	if not (slug in existing):
		return slug
	return "%s_%s" % [slug, _provider(rolls).token_hex(2)]


## Python str.isalnum() for one character (letters and numbers, any script).
static func _is_alnum(c: String) -> bool:
	var re := RegEx.new()
	re.compile("^[\\p{L}\\p{N}]$")
	return re.search(c) != null


## Empty floor cell near the southern entrance. Returns Coord or CoreError.
static func find_starting_position(state: Dictionary) -> Variant:
	var room: Dictionary = state["rooms"][state["current_room_id"]]
	var height := int(room["height"])
	var width := int(room["width"])
	var preferred_y := 6 if height > 6 else height - 2
	var ys: Array = [preferred_y, preferred_y - 1, preferred_y + 1]
	for y in height:
		ys.append(y)
	for y in ys:
		if y < 0 or y >= height:
			continue
		for x in width:
			var coord := {"x": x, "y": y}
			var cell: Variant = _Grid.get_cell(room, coord)
			if CoreError.is_error(cell):
				return cell
			if _Grid.is_traversable(cell):
				return coord
	return CoreError.make("RuntimeError", "no traversable cells available for new character")


## kwargs-dictionary entry point mirroring build_character(...). Keys are the
## Python parameter names (race/state/role as enum value strings,
## abilities as {STR..CHA}, game_state as a GameState dict).
## Returns a CharacterSheet Dictionary or a CoreError.
static func build_character(p: Dictionary) -> Variant:
	var race := str(p["race"])
	var state := str(p["state"])
	var role := str(p["role"])
	if not _Races.RACES.has(race):
		return CoreError.make("ValueError", "'%s' is not a valid Race" % race)
	if not _States.STATES.has(state):
		return CoreError.make("ValueError", "'%s' is not a valid EvolutionaryState" % state)
	if not _Roles.ROLES.has(role):
		return CoreError.make("ValueError", "'%s' is not a valid PredatorRole" % role)
	var abilities: Dictionary = p["abilities"]
	if not is_valid_standard_array(abilities):
		return CoreError.make("ValueError", "abilities must be a permutation of the standard array %s" % _std_array_text())

	var r_def: Dictionary = _Races.RACES[race]
	var s_def: Dictionary = _States.STATES[state]
	var p_def: Dictionary = _Roles.ROLES[role]

	var final_scores := {}
	for k in ABILITY_KEYS:
		final_scores[k] = int(abilities[k])
	var bonuses: Dictionary = r_def["ability_bonuses"]
	for abi in bonuses:
		final_scores[abi] = int(final_scores[abi]) + int(bonuses[abi])

	var hp_max: int = int(s_def["hit_die"]) + _ability_modifier(int(final_scores["CON"]))
	var ac: int = int(s_def["base_armor_class"]) + _ability_modifier(int(final_scores["DEX"]))
	if r_def["race_armor"] != null:
		ac += int(r_def["race_armor"]["armor_ac_bonus"])

	var inventory: Array = []
	if r_def["race_weapon"] != null:
		inventory.append((r_def["race_weapon"] as Dictionary).duplicate(true))
	if r_def["race_armor"] != null:
		inventory.append((r_def["race_armor"] as Dictionary).duplicate(true))
	inventory.append((p_def["primary_item"] as Dictionary).duplicate(true))

	var choices: Array = p_def["equipment_choices"]
	var chosen: Variant = null
	var choice_id: Variant = p.get("equipment_choice_id", null)
	if choice_id != null and str(choice_id) != "" and not choices.is_empty():
		for item in choices:
			if item["id"] == str(choice_id):
				chosen = item
				break
	if chosen == null and not choices.is_empty():
		chosen = choices[0]
	if chosen != null:
		inventory.append((chosen as Dictionary).duplicate(true))

	var keepsake: Variant = p.get("keepsake_name", null)
	if keepsake != null and str(keepsake) != "":
		inventory.append(_item("keepsake_%s" % str(p["char_id"]), str(keepsake), "A personal keepsake. No mechanical value."))

	var final_skills: Array = []
	var picked: Variant = p.get("skill_proficiencies", null)
	if picked != null:
		final_skills = (picked as Array).duplicate()
	var background: Variant = p.get("background", null)
	if background != null and str(background) != "" and _Backgrounds.BACKGROUNDS.has(str(background)):
		for skill in _Backgrounds.BACKGROUNDS[str(background)]["bonus_skills"]:
			if not (skill in final_skills):
				final_skills.append(skill)

	var spawn: Variant = find_starting_position(p["game_state"])
	if CoreError.is_error(spawn):
		return spawn

	var cantrips: Variant = p.get("cantrips", null)
	var era := str(p.get("starting_era", "after"))
	return {
		"id": p["char_id"],
		"name": p["name"],
		"player": p["player"],
		"race": race,
		"evolution_state": state,
		"predator_role": role,
		"level": 1,
		"evolution_points": 0,
		"silver": 0,
		"hp_current": hp_max,
		"hp_max": hp_max,
		"armor_class": ac,
		"speed": int(r_def["speed"]),
		"abilities": final_scores,
		"proficiency_bonus": 2,
		"skill_proficiencies": final_skills,
		"inventory": inventory,
		"position": spawn,
		"movement_remaining": int(r_def["speed"]),
		"conditions": [],
		"is_transformed": era == "after",
		"background": background,
		"feat": p.get("feat", null),
		"cantrips": [] if (cantrips == null or (cantrips as Array).is_empty()) else (cantrips as Array).duplicate(),
		"alignment": p.get("alignment", null),
		"pronouns": p.get("pronouns", "they/them"),
		"title": p.get("title", null),
		"dialogue_style": p.get("dialogue_style", null),
		"physical_description": p.get("physical_description", ""),
		"backstory": p.get("backstory", ""),
		"personality_traits": p.get("personality_traits", ""),
		"flaws": p.get("flaws", ""),
		"bonds": p.get("bonds", ""),
		"ideals": p.get("ideals", ""),
	}


## EnemySheet for a hostile NPC of the given race/state. Returns a Dictionary
## or a CoreError("ValueError"/"KeyError") for unknown ids.
static func build_race_enemy(enemy_id: String, race: String, ev_state: String, room_id: String,
		position: Dictionary, name_override: Variant = null, xp_reward: Variant = null) -> Variant:
	if not _Races.RACES.has(race):
		return CoreError.make("ValueError", "'%s' is not a valid Race" % race)
	if not _States.STATES.has(ev_state):
		return CoreError.make("ValueError", "'%s' is not a valid EvolutionaryState" % ev_state)
	var r_def: Dictionary = _Races.RACES[race]
	var s_def: Dictionary = _States.STATES[ev_state]

	var base: Array = _Lists.RACE_ENEMY_BASES[race]
	var totals := {}
	for n in ABILITY_KEYS.size():
		totals[ABILITY_KEYS[n]] = int(base[n])
	var bonuses: Dictionary = r_def["ability_bonuses"]
	for abi in bonuses:
		totals[abi] = int(totals.get(abi, 10)) + int(bonuses[abi])

	var con_mod := _ability_modifier(int(totals["CON"]))
	var dex_mod := _ability_modifier(int(totals["DEX"]))
	var str_mod := _ability_modifier(int(totals["STR"]))
	var best_mod := maxi(str_mod, dex_mod)

	var hp_max := maxi(1, int(s_def["hit_die"]) + con_mod)
	var ac: int = int(s_def["base_armor_class"]) + dex_mod
	if r_def["race_armor"] != null:
		ac += int(r_def["race_armor"]["armor_ac_bonus"])
	var attack_bonus := best_mod + 2

	var weapon_dice := "1d6"
	var weapon: Variant = r_def["race_weapon"]
	if weapon != null and weapon["damage_dice"] != null and str(weapon["damage_dice"]) != "":
		weapon_dice = str(weapon["damage_dice"])

	var default_xp := maxi(25, hp_max * 6 + ac * 4)
	var enemy_name: String = str(r_def["name"])
	if name_override != null and str(name_override) != "":
		enemy_name = str(name_override)
	var weapon_name := str(weapon["name"]) if weapon != null else "Natural Weapon"
	var description := "A hostile %s. Wields %s. %s" % [enemy_name, weapon_name, str(r_def["flavor"])]
	var xp := default_xp
	if xp_reward != null and int(xp_reward) != 0:
		xp = int(xp_reward)

	return {
		"id": enemy_id,
		"name": enemy_name,
		"room_id": room_id,
		"position": position.duplicate(true),
		"hp_current": hp_max,
		"hp_max": hp_max,
		"armor_class": ac,
		"attack_bonus": attack_bonus,
		"damage_dice": weapon_dice,
		"xp_reward": xp,
		"alive": true,
		"sprite_key": "enemy_race",
		"description": description,
		"loot": [],
	}
