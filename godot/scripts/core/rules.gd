class_name CoreRules
extends RefCounted
## Port of src/storyforge/core/rules.py. D&D 5e legality checks; never mutates.
##
## Legality is a Dictionary {"ok": bool, "reason": String}.

const _Grid := preload("res://scripts/core/grid.gd")


static func allow() -> Dictionary:
	return {"ok": true, "reason": ""}


static func deny(reason: String) -> Dictionary:
	return {"ok": false, "reason": reason}


## Top-level dispatcher for structured grid actions.
## state: GameState dict, char: CharacterSheet dict, action: GridAction dict.
static func check_grid_action(state: Dictionary, char: Dictionary, action: Dictionary) -> Dictionary:
	var room: Dictionary = state["rooms"][state["current_room_id"]]
	var target: Dictionary = action["target"]

	if not _Grid.in_bounds(room, target):
		return deny("target %s is outside the room" % _Grid.coord_str(target))

	match str(action["type"]):
		"move":
			return _check_move(state, char, target)
		"attack":
			return deny("attacks are v0.2; freeform-narrate it for now")
		"interact":
			return _check_interact(room, char, target)
		_:
			return deny("unknown action type: %s" % str(action["type"]))


static func _check_move(state: Dictionary, char: Dictionary, target: Dictionary) -> Dictionary:
	var room: Dictionary = state["rooms"][state["current_room_id"]]
	# Target is in bounds (checked by the caller), so get_cell cannot error.
	var target_cell: Dictionary = _Grid.get_cell(room, target)

	if not _Grid.is_traversable(target_cell):
		var msg := "target cell is %s" % str(target_cell.get("terrain", "floor"))
		var occ: Variant = target_cell.get("occupant_id", null)
		# Python truthiness: None and "" both skip the "(occupied by ...)" suffix.
		if occ != null and str(occ) != "":
			msg += " (occupied by %s)" % str(occ)
		return deny(msg)

	var feet_needed := _Grid.feet_between(char["position"], target)

	# Movement limit only applies in Combat (v0.2)
	if str(state["phase"]) == "combat":
		var remaining := int(char["movement_remaining"])
		if feet_needed > remaining:
			return deny("need %dft, only %dft remaining" % [feet_needed, remaining])

	var clear: Variant = _Grid.path_is_clear(room, char["position"], target)
	# char.position out of bounds would raise IndexError in Python; surface it.
	if CoreError.is_error(clear):
		return clear
	if not clear:
		return deny("path is blocked between start and target")

	return allow()


static func _check_interact(_room: Dictionary, char: Dictionary, target: Dictionary) -> Dictionary:
	# Must be adjacent (within 5ft) to interact
	if _Grid.feet_between(char["position"], target) > _Grid.FEET_PER_CELL:
		return deny("interact target must be adjacent")
	return allow()
