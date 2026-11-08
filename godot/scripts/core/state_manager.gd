class_name CoreStateManager
extends RefCounted
## Port of src/storyforge/core/state_manager.py (in-memory mutators only).
##
## `state` is a plain GameState Dictionary (model_dump(mode="json") shape) and
## is mutated in place. Python's asyncio.Lock, snapshot.save and EventBus are
## NOT part of this class: the later GameBackend wrapper attaches them through
## `commit_hook`, a Callable(state: Dictionary, summary: Dictionary) invoked at
## the end of every committing mutator AFTER revision was bumped (the point
## where Python saved to disk and published to the bus), and
## `snapshot_hook`, a Callable(state) invoked by append_narration (which saves
## but neither bumps revision nor publishes).
##
## Exceptions become CoreError dictionaries (StateError, IllegalActionError,
## IndexError, plus anything the factory returns, e.g. ValueError). Every
## mutator returns its summary Dictionary or a CoreError.

const _Grid := preload("res://scripts/core/grid.gd")
const _Rules := preload("res://scripts/core/rules.gd")
const _Enemies := preload("res://scripts/core/enemies.gd")
const _Factory := preload("res://scripts/core/character_factory.gd")
const _Roll := preload("res://scripts/core/roll_provider.gd")

## CharacterSheet / LobbySlot field names (what Python hasattr() accepts).
const CHARACTER_FIELDS := [
	"id", "name", "player", "race", "evolution_state", "predator_role", "level",
	"evolution_points", "silver", "hp_current", "hp_max", "armor_class", "speed",
	"abilities", "proficiency_bonus", "skill_proficiencies", "inventory", "position",
	"movement_remaining", "conditions", "is_transformed", "background", "feat",
	"cantrips", "alignment", "pronouns", "title", "dialogue_style",
	"physical_description", "backstory", "personality_traits", "flaws", "bonds",
	"ideals",
]
const SLOT_FIELDS := [
	"slot_index", "status", "controller_id", "character_id", "race", "evolution_state",
	"predator_role", "starting_era", "assigned_abilities", "name_draft",
	"equipment_choice_id", "background", "skill_proficiencies", "feat", "cantrips",
	"alignment", "pronouns", "title", "dialogue_style", "physical_description",
	"backstory", "personality_traits", "flaws", "bonds", "ideals", "keepsake_name",
	"creation_step",
]

var state: Dictionary
var rolls: CoreRollProvider
## Callable returning an ISO-8601 UTC timestamp String.
var clock: Callable
var commit_hook: Callable = Callable()
var snapshot_hook: Callable = Callable()


func _init(initial: Dictionary, roll_provider: CoreRollProvider = null, clock_fn: Callable = Callable()) -> void:
	state = initial
	rolls = roll_provider if roll_provider != null else _Roll.live()
	clock = clock_fn if clock_fn.is_valid() else Callable(CoreStateManager, "default_clock")


## UTC now as ISO-8601 with +00:00 (Python's isoformat() minus microseconds).
static func default_clock() -> String:
	return Time.get_datetime_string_from_system(true) + "+00:00"


# ─────────────────────── Helpers ───────────────────────

func _err(kind: String, message: String) -> Dictionary:
	return CoreError.make(kind, message)


func _commit(summary: Dictionary) -> void:
	state["revision"] = int(state["revision"]) + 1
	if commit_hook.is_valid():
		commit_hook.call(state, summary)


func _narrative(rev: int, actor_id: Variant, kind: String, text: String) -> Dictionary:
	return {"revision": rev, "actor_id": actor_id, "kind": kind, "text": text, "timestamp": str(clock.call())}


func get_character(char_id: String) -> Variant:
	var chars: Dictionary = state["characters"]
	if not chars.has(char_id):
		return _err("StateError", "unknown character: %s" % char_id)
	return chars[char_id]


## Pydantic defaults for an InventoryItem.
static func _norm_item(item: Dictionary) -> Dictionary:
	var out := {
		"id": null, "name": null, "quantity": 1, "equipped": false, "value": 0,
		"notes": null, "damage_dice": null, "armor_ac_bonus": 0,
	}
	out.merge(item.duplicate(true), true)
	return out


static func _norm_cell(cell: Dictionary) -> Dictionary:
	var out := {"terrain": "floor", "occupant_id": null}
	out.merge(cell.duplicate(true), true)
	return out


## Index into lobby_slots with Python semantics (negative wraps).
func _slot_at(index: int) -> Variant:
	var slots: Array = state["lobby_slots"]
	if index >= slots.size() or index < -slots.size():
		return _err("IndexError", "list index out of range")
	return slots[index]


# ─────────────────────── Public mutators ───────────────────────

func set_phase(phase: String) -> Dictionary:
	state["phase"] = phase
	var summary := {"type": "phase_changed", "phase": phase}
	_commit(summary)
	return summary


func attack_enemy(attacker_id: String, enemy_id: String) -> Variant:
	var chars: Dictionary = state["characters"]
	if not chars.has(attacker_id):
		return _err("StateError", "unknown character: %s" % attacker_id)
	var char: Dictionary = chars[attacker_id]
	var enemies: Dictionary = state["enemies"]
	if not enemies.has(enemy_id) or not enemies[enemy_id]["alive"]:
		return _err("StateError", "enemy not found or already dead: %s" % enemy_id)
	var enemy: Dictionary = enemies[enemy_id]

	var pr := _Enemies.resolve_player_attack(char, enemy, rolls)
	if pr["hit"]:
		enemy["hp_current"] = maxi(0, int(enemy["hp_current"]) - int(pr["damage"]))

	var result := {
		"type": "combat_round",
		"player_attack": {
			"hit": pr["hit"], "roll": pr["roll"], "total": pr["total"],
			"damage": pr["damage"], "hint": pr["hint"],
		},
		"enemy_hp": enemy["hp_current"],
	}

	if int(enemy["hp_current"]) <= 0:
		enemy["alive"] = false
		var rooms: Dictionary = state["rooms"]
		if rooms.has(state["current_room_id"]):
			var cell: Variant = _Grid.get_cell(rooms[state["current_room_id"]], enemy["position"])
			# Python swallows any exception here.
			if not CoreError.is_error(cell) and cell["occupant_id"] == enemy_id:
				cell["occupant_id"] = null
		char["evolution_points"] = int(char["evolution_points"]) + int(enemy["xp_reward"])
		result["enemy_died"] = true
		result["xp_reward"] = enemy["xp_reward"]
	else:
		var counter := _Enemies.resolve_enemy_attack(enemy, char, rolls)
		if counter["hit"]:
			char["hp_current"] = maxi(0, int(char["hp_current"]) - int(counter["damage"]))
		result["enemy_attack"] = {
			"hit": counter["hit"], "roll": counter["roll"], "total": counter["total"],
			"damage": counter["damage"], "hint": counter["hint"],
		}
		result["player_hp"] = char["hp_current"]

	_commit(result)
	return result


func fast_travel(room_id: String) -> Variant:
	var diff: Variant = _do_transition_room(room_id)
	if CoreError.is_error(diff):
		return diff
	_commit(diff)
	return diff


func transition_room(target_room_id: String) -> Variant:
	return fast_travel(target_room_id)


## char: the CharacterSheet Dictionary (live reference into state).
func apply_grid_action(char: Dictionary, action: Dictionary) -> Variant:
	var verdict: Variant = _Rules.check_grid_action(state, char, action)
	if CoreError.is_error(verdict):
		return verdict
	if not verdict["ok"]:
		return _err("IllegalActionError", str(verdict["reason"]))

	var summary: Variant
	match str(action["type"]):
		"move":
			summary = _do_move(char, action["target"])
		"interact":
			summary = _do_interact(char, action["target"])
		_:
			return _err("IllegalActionError", "unhandled action: %s" % str(action["type"]))
	if CoreError.is_error(summary):
		return summary
	_commit(summary)
	return summary


## diff: StateDiff Dictionary (missing keys take the pydantic defaults).
func apply_diff(diff: Dictionary) -> Variant:
	var applied := {
		"character_updates": {}, "cell_updates": [], "add_inventory": {},
		"remove_inventory": {}, "phase_change": null,
	}
	var chars: Dictionary = state["characters"]

	var cu: Dictionary = diff.get("character_updates", {})
	for char_id in cu:
		if not chars.has(char_id):
			continue
		var updates: Dictionary = cu[char_id]
		for field in updates:
			if field in CHARACTER_FIELDS:
				chars[char_id][field] = updates[field]
		applied["character_updates"][char_id] = updates.duplicate(true)

	var rooms: Dictionary = state["rooms"]
	for entry in diff.get("cell_updates", []):
		var room_id: String = str(entry[0])
		if not rooms.has(room_id):
			continue
		var coord: Dictionary = entry[1]
		var new_cell := _norm_cell(entry[2])
		var r: Variant = _Grid.set_cell(rooms[room_id], coord, new_cell)
		if CoreError.is_error(r):
			return r
		applied["cell_updates"].append([room_id, coord.duplicate(true), new_cell.duplicate(true)])

	var add: Dictionary = diff.get("add_inventory", {})
	for char_id in add:
		if not chars.has(char_id):
			continue
		var dumped: Array = []
		for raw in add[char_id]:
			var item := _norm_item(raw)
			(chars[char_id]["inventory"] as Array).append(item)
			dumped.append(item.duplicate(true))
		applied["add_inventory"][char_id] = dumped

	var rem: Dictionary = diff.get("remove_inventory", {})
	for char_id in rem:
		if not chars.has(char_id):
			continue
		var ids: Array = rem[char_id]
		var kept: Array = []
		for item in chars[char_id]["inventory"]:
			if not (item["id"] in ids):
				kept.append(item)
		chars[char_id]["inventory"] = kept
		applied["remove_inventory"][char_id] = ids.duplicate()

	var pc: Variant = diff.get("phase_change", null)
	if pc != null:
		state["phase"] = pc
		applied["phase_change"] = pc

	_commit(applied)
	return applied


## Appends a log entry. Does NOT bump revision; saves (snapshot_hook) only.
func append_narration(actor_id: Variant, kind: String, text: String) -> Variant:
	(state["narrative_log"] as Array).append(_narrative(int(state["revision"]), actor_id, kind, text))
	if snapshot_hook.is_valid():
		snapshot_hook.call(state)
	return null


# ─────────────────────── Lobby + creation ───────────────────────

func claim_slot(controller_id: String) -> Variant:
	var phase := str(state["phase"])
	if phase != "lobby" and phase != "creation":
		return _err("StateError", "cannot claim slot during phase '%s'" % phase)

	for slot in state["lobby_slots"]:
		if slot["controller_id"] == controller_id and slot["status"] != "empty":
			return {"type": "slot_claimed", "slot_index": slot["slot_index"], "already_held": true}

	for slot in state["lobby_slots"]:
		if slot["status"] == "empty":
			slot["status"] = "claimed"
			slot["controller_id"] = controller_id
			var summary := {
				"type": "slot_claimed", "slot_index": slot["slot_index"],
				"controller_id": controller_id, "phase": phase,
			}
			_commit(summary)
			return summary

	return _err("StateError", "all 4 slots are claimed")


func update_slot_name(slot_index: int, slot_name: String, controller_id: String) -> Variant:
	var slot: Variant = _slot_at(slot_index)
	if CoreError.is_error(slot):
		return slot
	if slot["status"] == "ready":
		return _err("StateError", "slot %d is already ready" % slot_index)
	if slot["status"] == "empty":
		slot["status"] = "claimed"
	slot["name_draft"] = slot_name
	slot["controller_id"] = controller_id
	var summary := {
		"type": "slot_name_updated", "slot_index": slot_index,
		"name": slot_name, "controller_id": controller_id,
	}
	_commit(summary)
	return summary


## Stores patch values UNVALIDATED for any known slot field (Python quirk).
func save_draft(controller_id: String, patch: Dictionary) -> Variant:
	for slot in state["lobby_slots"]:
		if slot["controller_id"] == controller_id:
			if slot["status"] != "claimed" and slot["status"] != "creating":
				return _err("StateError", "slot for %s is not in a creation state" % controller_id)
			slot["status"] = "creating"
			for key in patch:
				if key in SLOT_FIELDS:
					slot[key] = patch[key]
			var summary := {"type": "draft_saved", "controller_id": controller_id}
			_commit(summary)
			return summary
	return _err("StateError", "no slot found for controller %s" % controller_id)


func release_slot(controller_id: String) -> Variant:
	for slot in state["lobby_slots"]:
		if slot["controller_id"] == controller_id:
			if slot["status"] == "ready":
				var cid: Variant = slot["character_id"]
				if cid != null and str(cid) != "":
					(state["characters"] as Dictionary).erase(cid)
			var released_index = slot["slot_index"]
			slot["status"] = "empty"
			slot["controller_id"] = null
			slot["character_id"] = null
			slot["race"] = null
			slot["evolution_state"] = null
			slot["predator_role"] = null
			slot["assigned_abilities"] = null
			slot["name_draft"] = null
			slot["equipment_choice_id"] = null
			slot["background"] = null
			slot["skill_proficiencies"] = []
			slot["feat"] = null
			slot["cantrips"] = []
			slot["alignment"] = null
			slot["pronouns"] = "they/them"
			slot["title"] = null
			slot["dialogue_style"] = null
			slot["physical_description"] = ""
			slot["backstory"] = ""
			slot["personality_traits"] = ""
			slot["flaws"] = ""
			slot["bonds"] = ""
			slot["ideals"] = ""
			slot["keepsake_name"] = null
			slot["starting_era"] = null
			slot["creation_step"] = "era"

			var all_empty := true
			for s in state["lobby_slots"]:
				if s["status"] != "empty":
					all_empty = false
					break
			if all_empty:
				state["phase"] = "lobby"

			var summary := {"type": "slot_released", "slot_index": released_index, "phase": state["phase"]}
			_commit(summary)
			return summary
	return _err("StateError", "no slot held by controller %s" % controller_id)


## req: CharacterCreationRequest Dictionary (optional keys take defaults).
func create_character(req: Dictionary) -> Variant:
	if str(state["phase"]) != "creation":
		return _err("StateError", "character creation requires CREATION phase, current: %s" % str(state["phase"]))

	var slot_index := int(req["slot_index"])
	var slot: Variant = _slot_at(slot_index)
	if CoreError.is_error(slot):
		return slot
	if slot["status"] != "claimed" and slot["status"] != "creating":
		return _err("StateError", "slot %d is %s, cannot create" % [slot_index, str(slot["status"])])

	var chars: Dictionary = state["characters"]
	var char_id := _Factory.generate_char_id(str(req["name"]), chars.keys(), rolls)

	var p: Dictionary = req.duplicate(true)
	p["char_id"] = char_id
	var ctrl: Variant = slot["controller_id"]
	p["player"] = str(ctrl) if (ctrl != null and str(ctrl) != "") else "unknown"
	p["state"] = req["evolution_state"]
	p["role"] = req["predator_role"]
	p["game_state"] = state
	var sheet: Variant = _Factory.build_character(p)
	if CoreError.is_error(sheet):
		return sheet

	chars[char_id] = sheet
	var room: Dictionary = state["rooms"][state["current_room_id"]]
	var cell: Variant = _Grid.get_cell(room, sheet["position"])
	if CoreError.is_error(cell):
		return cell
	cell["occupant_id"] = char_id

	slot["status"] = "ready"
	slot["character_id"] = char_id
	slot["race"] = req["race"]
	slot["evolution_state"] = req["evolution_state"]
	slot["predator_role"] = req["predator_role"]
	slot["assigned_abilities"] = (req["abilities"] as Dictionary).duplicate(true)
	slot["name_draft"] = req["name"]

	var summary := {
		"type": "character_created", "slot_index": slot_index,
		"character_id": char_id, "character": (sheet as Dictionary).duplicate(true),
	}
	_commit(summary)
	return summary


func start_exploration() -> Variant:
	if str(state["phase"]) != "creation":
		return _err("StateError", "can only start from CREATION, currently %s" % str(state["phase"]))

	var ready_count := 0
	for s in state["lobby_slots"]:
		if s["status"] == "ready":
			ready_count += 1
	if ready_count < 1:
		return _err("StateError", "at least one character must be ready to start")

	state["phase"] = "exploration"

	var any_untransformed := false
	var names: Array[String] = []
	for c in (state["characters"] as Dictionary).values():
		if not c["is_transformed"]:
			any_untransformed = true
		names.append(str(c["name"]))
	state["era"] = "before" if any_untransformed else "after"

	var opening := "The Crooked Tankard's door swings shut behind %s. Pipe smoke hangs in the rafters, and a bard by the hearth tunes a battered lute." % ", ".join(names)
	(state["narrative_log"] as Array).append(_narrative(int(state["revision"]) + 1, null, "narration", opening))

	var summary := {"type": "exploration_started", "character_count": ready_count, "phase": state["phase"]}
	_commit(summary)
	return summary


func trigger_paradox() -> Variant:
	var transformed_ids: Array = []
	var chars: Dictionary = state["characters"]
	for char_id in chars:
		if not chars[char_id]["is_transformed"]:
			chars[char_id]["is_transformed"] = true
			transformed_ids.append(char_id)

	state["era"] = "after"
	var msg := "The air screams as the Paradox resolves. The past is rewritten in bone and steel."
	(state["narrative_log"] as Array).append(_narrative(int(state["revision"]) + 1, null, "narration", msg))

	var summary := {"type": "paradox_triggered", "transformed_ids": transformed_ids, "text": msg}
	_commit(summary)
	return summary


# ─────────────────────── Internal helpers ───────────────────────

func _do_interact(_char: Dictionary, target: Dictionary) -> Variant:
	var room: Dictionary = state["rooms"][state["current_room_id"]]
	var cell: Variant = _Grid.get_cell(room, target)
	if CoreError.is_error(cell):
		return cell
	var occ: Variant = cell["occupant_id"]

	# 1. Live enemy -> attack-flow signal
	var enemies: Dictionary = state["enemies"]
	if occ != null and str(occ) != "" and enemies.has(occ):
		var enemy: Dictionary = enemies[occ]
		if enemy["alive"]:
			return {
				"type": "enemy_encounter", "enemy_id": enemy["id"],
				"enemy_name": enemy["name"], "position": target.duplicate(true),
			}

	# 2. NPC (old saves may carry an "npc_" prefix)
	var occ_s := str(occ) if occ != null else ""
	var npc_key := occ_s.substr(4) if occ_s.begins_with("npc_") else occ_s
	var npcs: Dictionary = state["npcs"]
	if npc_key != "" and npcs.has(npc_key):
		var npc: Dictionary = npcs[npc_key]
		return {
			"type": "npc_encounter", "npc_id": npc["id"], "npc_name": npc["name"],
			"encounter_id": npc["encounter_id"], "position": target.duplicate(true),
		}

	# 3. Door exit
	var exit_key := "%d,%d" % [int(target["x"]), int(target["y"])]
	if str(cell["terrain"]) == "door" and (room["exits"] as Dictionary).has(exit_key):
		return _do_transition_room(str(room["exits"][exit_key]))

	# 4. Generic
	return {"type": "interact", "target": target.duplicate(true)}


func _do_transition_room(target_room_id: String) -> Variant:
	var rooms: Dictionary = state["rooms"]
	if not rooms.has(target_room_id):
		return _err("StateError", "unknown room: %s" % target_room_id)

	var old_room: Dictionary = rooms[state["current_room_id"]]
	var new_room: Dictionary = rooms[target_room_id]
	var chars: Dictionary = state["characters"]

	for char in chars.values():
		var old_cell: Variant = _Grid.get_cell(old_room, char["position"])
		# Python swallows IndexError/KeyError here.
		if not CoreError.is_error(old_cell) and old_cell["occupant_id"] == char["id"]:
			old_cell["occupant_id"] = null

	state["current_room_id"] = target_room_id
	for char in chars.values():
		var spawn: Variant = _Factory.find_starting_position(state)
		if CoreError.is_error(spawn):
			return spawn
		char["position"] = spawn
		char["movement_remaining"] = char["speed"]
		var ncell: Variant = _Grid.get_cell(new_room, spawn)
		if CoreError.is_error(ncell):
			return ncell
		ncell["occupant_id"] = char["id"]

	return {
		"type": "room_transition", "from_room": old_room["id"],
		"to_room": target_room_id, "room_name": new_room["name"],
	}


func _do_move(char: Dictionary, target: Dictionary) -> Variant:
	var room: Dictionary = state["rooms"][state["current_room_id"]]
	var feet_spent := _Grid.feet_between(char["position"], target)

	var old_cell: Variant = _Grid.get_cell(room, char["position"])
	if CoreError.is_error(old_cell):
		return old_cell
	old_cell["occupant_id"] = null
	var new_cell: Variant = _Grid.get_cell(room, target)
	if CoreError.is_error(new_cell):
		return new_cell
	new_cell["occupant_id"] = char["id"]

	var previous: Dictionary = char["position"]
	char["position"] = target.duplicate(true)

	if str(state["phase"]) == "exploration":
		char["movement_remaining"] = char["speed"]
	else:
		char["movement_remaining"] = int(char["movement_remaining"]) - feet_spent

	return {
		"type": "move", "actor_id": char["id"], "from": previous.duplicate(true),
		"to": target.duplicate(true), "feet_spent": feet_spent,
		"movement_remaining": char["movement_remaining"],
	}
