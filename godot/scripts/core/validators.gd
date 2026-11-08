class_name CoreValidators
extends RefCounted
## Port of src/storyforge/core/validators.py. Sanitize AI-proposed StateDiffs.
##
## REJECT, don't repair. sanitize() returns the Python tuple
## (safe_diff, rejections) as {"diff": Dictionary, "rejections": Array[String]}.
## The proposed diff is a StateDiff JSON dict; missing sections take the
## pydantic defaults (and InventoryItem / Cell defaults are filled in, exactly
## as StateDiff.model_validate would do before the Python code sees them).

const _Grid := preload("res://scripts/core/grid.gd")

const _ALLOWED_CHAR_FIELDS := ["hp_current", "conditions", "movement_remaining", "position"]
const _MAX_HP_DELTA_PER_TURN := 8


# ─────────────────────── Python type emulation ───────────────────────
# JSON numbers arrive as float. Divergence (unavoidable): Python tells 5 from
# 5.0; here an integral float is treated as an int. bool stays distinct but,
# like Python (bool subclasses int), is accepted wherever int is.

static func _is_int(v: Variant) -> bool:
	if typeof(v) == TYPE_INT or typeof(v) == TYPE_BOOL:
		return true
	return typeof(v) == TYPE_FLOAT and is_finite(v) and v == floorf(v)


## Numeric value of an "int" (bool counts as 0/1).
static func _num(v: Variant) -> int:
	if typeof(v) == TYPE_BOOL:
		return 1 if v else 0
	return int(v)


## Python type(value).__name__ for JSON-origin values.
static func _py_type_name(v: Variant) -> String:
	match typeof(v):
		TYPE_NIL: return "NoneType"
		TYPE_BOOL: return "bool"
		TYPE_INT: return "int"
		TYPE_FLOAT: return "int" if _is_int(v) else "float"
		TYPE_STRING: return "str"
		TYPE_ARRAY: return "list"
		TYPE_DICTIONARY: return "dict"
	return "object"


# ─────────────────────── Model default filling ───────────────────────

static func _norm_item(item: Dictionary) -> Dictionary:
	var out := item.duplicate(true)
	for k in ["quantity", "equipped", "value", "notes", "damage_dice", "armor_ac_bonus"]:
		if not out.has(k):
			out[k] = {"quantity": 1, "equipped": false, "value": 0, "notes": null, "damage_dice": null, "armor_ac_bonus": 0}[k]
	return out


static func _norm_cell(cell: Dictionary) -> Dictionary:
	var out := cell.duplicate(true)
	if not out.has("terrain"):
		out["terrain"] = "floor"
	if not out.has("occupant_id"):
		out["occupant_id"] = null
	return out


# ─────────────────────── Entry point ───────────────────────

static func sanitize(state: Dictionary, proposed: Dictionary) -> Dictionary:
	var rejections: Array[String] = []
	var safe := {
		"character_updates": {}, "cell_updates": [], "add_inventory": {},
		"remove_inventory": {}, "phase_change": null,
	}

	var phase := str(state["phase"])
	if phase == "lobby" or phase == "creation":
		rejections.append("AI diffs are not accepted during %s phase" % phase)
		return {"diff": safe, "rejections": rejections}

	safe["character_updates"] = _filter_char_updates(state, proposed.get("character_updates", {}), rejections)
	safe["cell_updates"] = _filter_cell_updates(state, proposed.get("cell_updates", []), rejections)
	safe["add_inventory"] = _filter_add_inventory(state, proposed.get("add_inventory", {}), rejections)
	safe["remove_inventory"] = _filter_remove_inventory(state, proposed.get("remove_inventory", {}), rejections)
	safe["phase_change"] = _filter_phase_change(state, proposed.get("phase_change", null), rejections)
	return {"diff": safe, "rejections": rejections}


# ─────────────────────── Per-section filters ───────────────────────

static func _filter_char_updates(state: Dictionary, updates: Dictionary, rejections: Array[String]) -> Dictionary:
	var safe := {}
	var characters: Dictionary = state["characters"]
	for char_id in updates:
		if not characters.has(char_id):
			rejections.append("unknown character '%s'" % char_id)
			continue
		var ch: Dictionary = characters[char_id]
		var fields: Dictionary = updates[char_id]
		var safe_fields := {}
		for field in fields:
			var value: Variant = fields[field]
			if not (field in _ALLOWED_CHAR_FIELDS):
				rejections.append("AI tried to modify forbidden field '%s' on %s" % [field, char_id])
				continue

			if field == "hp_current":
				if not _is_int(value):
					rejections.append("hp_current must be int, got %s" % _py_type_name(value))
					continue
				var hv := _num(value)
				var hp_cur := int(ch["hp_current"])
				var hp_max := int(ch["hp_max"])
				if hv < 0:
					rejections.append("hp_current cannot be negative (%s)" % char_id)
					continue
				if hv > hp_max:
					rejections.append("hp_current %d > max %d for %s" % [hv, hp_max, char_id])
					continue
				if absi(hv - hp_cur) > _MAX_HP_DELTA_PER_TURN:
					rejections.append("HP delta too large for %s: %d → %d" % [char_id, hp_cur, hv])
					continue

			if field == "movement_remaining":
				if not _is_int(value) or _num(value) < 0:
					rejections.append("movement_remaining invalid for %s" % char_id)
					continue
				var speed := int(ch["speed"])
				if _num(value) > speed:
					rejections.append("movement_remaining %d > speed %d for %s" % [_num(value), speed, char_id])
					continue

			if field == "conditions":
				if typeof(value) != TYPE_ARRAY:
					rejections.append("conditions must be list for %s" % char_id)
					continue

			if field == "position":
				# Disallow direct position writes - must go through cell_updates.
				rejections.append("position must be set via cell_updates, not character_updates (%s)" % char_id)
				continue

			safe_fields[field] = value

		if not safe_fields.is_empty():
			safe[char_id] = safe_fields
	return safe


static func _filter_cell_updates(state: Dictionary, updates: Array, rejections: Array[String]) -> Array:
	var safe: Array = []
	var current_room_id := str(state["current_room_id"])
	for upd in updates:
		var room_id := str(upd[0])
		var coord: Dictionary = upd[1]
		var new_cell := _norm_cell(upd[2])

		if room_id != current_room_id:
			rejections.append("AI tried to modify room '%s' but party is in '%s'" % [room_id, current_room_id])
			continue

		# Unreachable in Python too (room != current fires first); kept for parity.
		if not (state["rooms"] as Dictionary).has(room_id):
			rejections.append("unknown room '%s'" % room_id)
			continue
		var room: Dictionary = state["rooms"][room_id]

		if not _Grid.in_bounds(room, coord):
			rejections.append("cell %s out of bounds in %s" % [_Grid.coord_str(coord), room_id])
			continue

		safe.append([room_id, {"x": int(coord["x"]), "y": int(coord["y"])}, new_cell])
	return safe


static func _filter_add_inventory(state: Dictionary, additions: Dictionary, rejections: Array[String]) -> Dictionary:
	var safe := {}
	for char_id in additions:
		if not (state["characters"] as Dictionary).has(char_id):
			rejections.append("unknown character '%s' in inventory add" % char_id)
			continue
		# MVP: allow additions but cap quantity ("AI gives you 999 healing potions").
		var safe_items: Array = []
		for raw in additions[char_id]:
			var item := _norm_item(raw)
			if int(item["quantity"]) > 10:
				rejections.append("refused inventory add: quantity %d > 10 (%s)" % [int(item["quantity"]), str(item["name"])])
				continue
			safe_items.append(item)
		if not safe_items.is_empty():
			safe[char_id] = safe_items
	return safe


static func _filter_remove_inventory(state: Dictionary, removals: Dictionary, rejections: Array[String]) -> Dictionary:
	var safe := {}
	var characters: Dictionary = state["characters"]
	for char_id in removals:
		if not characters.has(char_id):
			rejections.append("unknown character '%s' in inventory remove" % char_id)
			continue
		var owned := {}
		for it in characters[char_id].get("inventory", []):
			owned[str(it["id"])] = true
		var item_ids: Array = removals[char_id]
		var valid: Array = []
		var invalid: Array = []
		for iid in item_ids:
			if owned.has(iid):
				valid.append(iid)
			else:
				invalid.append(iid)
		# Python reports invalid ids after splitting; order = input order.
		for iid in invalid:
			rejections.append("%s does not own item '%s'" % [char_id, str(iid)])
		if not valid.is_empty():
			safe[char_id] = valid
	return safe


static func _filter_phase_change(_state: Dictionary, proposed: Variant, rejections: Array[String]) -> Variant:
	if proposed == null:
		return null
	# MVP: AI can suggest COMBAT, but it is rejected - combat is v0.2.
	if str(proposed) == "combat":
		rejections.append("phase change to combat is deferred to v0.2")
		return null
	return proposed
