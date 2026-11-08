class_name CoreEnemies
extends RefCounted
## Port of src/storyforge/encounters/enemies.py. Pure combat resolution.
##
## CharacterSheet / EnemySheet are plain Dictionaries (model_dump JSON shape).
## AttackResult is returned as a Dictionary with the dataclass field names.
## Randomness comes from a CoreRollProvider; pass null for a live one.

const _Grid := preload("res://scripts/core/grid.gd")
const _Roll := preload("res://scripts/core/roll_provider.gd")


static func _provider(rolls) -> CoreRollProvider:
	if rolls == null:
		return _Roll.live()
	return rolls


## Parse and roll e.g. '2d6+2', '1d8', '1d4'.
## Emulates Python `re.match(r"(\d+)d(\d+)([+-]\d+)?", notation.strip())`:
## a PREFIX match anchored at the start (so "1d8 slashing" works, "1D8" and
## "d6" do not, and fall back to 1). Result is clamped to a minimum of 1.
static func _roll_dice(notation: String, rolls = null) -> int:
	var rp := _provider(rolls)
	var re := RegEx.new()
	re.compile("^([0-9]+)d([0-9]+)([+-][0-9]+)?")
	var m := re.search(notation.strip_edges())
	if m == null:
		return 1
	var count := m.get_string(1).to_int()
	var sides := m.get_string(2).to_int()
	var bonus_s := m.get_string(3)
	var bonus := 0
	if bonus_s != "":
		bonus = bonus_s.substr(1).to_int()
		if bonus_s.begins_with("-"):
			bonus = -bonus
	var total := 0
	for i in count:
		total += rp.randint(1, sides)
	return maxi(1, total + bonus)


## Python floor division: (score - 10) // 2 (GDScript int division truncates).
static func _mod(score: int) -> int:
	return floori((score - 10) / 2.0)


## Damage dice of the first equipped weapon with dice, else default 1d6.
static func _weapon_dice(char: Dictionary) -> String:
	for item in char.get("inventory", []):
		# Python truthiness: damage_dice must be a non-empty string.
		var dd: Variant = item.get("damage_dice", null)
		if item.get("equipped", false) and dd != null and str(dd) != "":
			return str(dd)
	return "1d6"


static func resolve_player_attack(attacker: Dictionary, target: Dictionary, rolls = null) -> Dictionary:
	var rp := _provider(rolls)
	var ab: Dictionary = attacker["abilities"]
	var best_mod := maxi(_mod(int(ab["STR"])), _mod(int(ab["DEX"])))
	var bonus := best_mod + int(attacker["proficiency_bonus"])
	var roll := rp.randint(1, 20)
	var total := roll + bonus
	var crit := roll == 20
	var ac := int(target["armor_class"])
	var hit := crit or total >= ac
	var damage := 0

	if hit:
		var dice := _weapon_dice(attacker)
		var dmg_roll := _roll_dice(dice, rp) + maxi(best_mod, 0)
		if crit:
			dmg_roll += _roll_dice(dice, rp)  # crit: roll weapon dice twice
		damage = maxi(1, dmg_roll)

	var aname := str(attacker["name"])
	var tname := str(target["name"])
	var hint: String
	if crit:
		hint = "%s scores a critical hit on %s for %d damage!" % [aname, tname, damage]
	elif hit:
		hint = "%s hits %s for %d damage." % [aname, tname, damage]
	else:
		hint = "%s swings at %s but misses (rolled %d vs AC %d)." % [aname, tname, total, ac]

	return {
		"hit": hit, "roll": roll, "total": total, "damage": damage,
		"attacker_name": aname, "target_name": tname, "hint": hint,
	}


static func resolve_enemy_attack(enemy: Dictionary, target: Dictionary, rolls = null) -> Dictionary:
	var rp := _provider(rolls)
	var roll := rp.randint(1, 20)
	var total := roll + int(enemy["attack_bonus"])
	var hit := roll == 20 or total >= int(target["armor_class"])
	var damage := _roll_dice(str(enemy["damage_dice"]), rp) if hit else 0

	var ename := str(enemy["name"])
	var tname := str(target["name"])
	var hint: String
	if hit:
		hint = "%s strikes back at %s for %d damage!" % [ename, tname, damage]
	else:
		hint = "%s lunges at %s but can't connect." % [ename, tname]

	return {
		"hit": hit, "roll": roll, "total": total, "damage": damage,
		"attacker_name": ename, "target_name": tname, "hint": hint,
	}
