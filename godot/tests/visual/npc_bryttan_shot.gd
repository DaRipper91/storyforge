extends SceneTree
## Run the local game, travel to Ironhold Keep, spawn Bryttan and capture the real tabletop scene.
## godot --path godot --resolution 1280x720 -s res://tests/visual/npc_bryttan_shot.gd -- \
##   --backend=local --save-dir=/tmp/storyforge-bryttan-save --out=/tmp/bryttan-world.png

const NPC_ID := "bryttan_wolfholt"
const ABILITIES := {"STR": 8, "DEX": 15, "CON": 14, "INT": 10, "WIS": 12, "CHA": 13}

var _fails := 0


func _initialize() -> void:
	call_deferred("_run")


func _arg(arg_name: String, default_value := "") -> String:
	var prefix := "--%s=" % arg_name
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with(prefix):
			return arg.substr(prefix.length())
	return default_value


func _post(client: Node, path: String, body: Dictionary) -> Array:
	var request: Variant = client.post_request(path, body)
	return await request.request_completed


func _check(label: String, ok: bool, detail: String = "") -> void:
	if ok:
		print("  ok   ", label)
	else:
		_fails += 1
		printerr("  FAIL ", label, " ", detail)


func _save(path: String) -> void:
	var image := root.get_texture().get_image()
	var err := image.save_png(path)
	_check("save screenshot %s" % path, err == OK, "error %d" % err)
	print("SHOT %s %dx%d" % [path, image.get_width(), image.get_height()])


func _run() -> void:
	var client := root.get_node_or_null("PythonClient")
	if client == null:
		_check("PythonClient autoload exists", false)
		_finish()
		return
	for _i in 8:
		await process_frame

	var response := await _post(client, "/lobby/join", {"controller_id": "bryttan-shot"})
	_check("join local lobby", int(response[1]) == 200, str(response[1]))
	response = await _post(client, "/lobby/set_phase", {"phase": "creation"})
	_check("open character creation", int(response[1]) == 200, str(response[1]))
	response = await _post(client, "/character/create", {
		"abilities": ABILITIES, "evolution_state": "behemoth", "name": "Preview Hero",
		"predator_role": "vanguard", "race": "ironfast", "slot_index": 0, "starting_era": "after",
	})
	_check("create preview party member", int(response[1]) == 200, str(response[1]))
	response = await _post(client, "/lobby/start", {})
	_check("start tabletop", int(response[1]) == 200, str(response[1]))
	if _fails > 0:
		_finish()
		return

	var tabletop := (load("res://scenes/Tabletop.tscn") as PackedScene).instantiate()
	root.add_child(tabletop)
	for _i in 90:
		await process_frame
	response = await _post(client, "/action/travel", {"room_id": "ironhold_keep"})
	_check("travel to Ironhold Keep", int(response[1]) == 200, str(response[1]))
	for _i in 24:
		await process_frame

	var npc = tabletop._npc_tokens.get(NPC_ID)
	_check("Bryttan spawns from campaign NPC data", npc != null)
	_check("Bryttan uses her composed 3D model", npc != null and npc.has_model())
	if npc == null:
		_finish()
		return
	var model := npc._model as Node3D
	_check("model receives procedural idle animation",
		ModelLibrary.find_clip(ModelLibrary.find_anim_player(model), "idle") != "")
	await _save(_arg("out", "/tmp/bryttan-wolfguard.png"))

	var actor_id := str(tabletop._selected_cid)
	response = await _post(client, "/action/interact_entity", {
		"actor_id": actor_id, "target_id": NPC_ID,
	})
	_check("NPC interaction resolves", int(response[1]) == 200, str(response[1]))
	var payload: Dictionary = JSON.parse_string(response[3].get_string_from_utf8())
	var encounter: Dictionary = payload.get("encounter", {})
	_check("interaction returns Bryttan's NPC identity",
		encounter.get("npc_id", "") == NPC_ID and encounter.get("npc_name", "") == "Bryttan Wolfholt")
	tabletop._show_npc_dialog(encounter)
	_check("dialog presents the seeded NPC description",
		tabletop._npc_dialog.visible and tabletop._npc_dialog_title.text == "Bryttan Wolfholt"
		and tabletop._npc_dialog_desc.text.contains("Wolfguard"))
	await process_frame
	await _save(_arg("dialog-out", "/tmp/bryttan-wolfguard-dialog.png"))
	_finish()


func _finish() -> void:
	print("RESULT: %s (%d failures)" % ["OK" if _fails == 0 else "FAILED", _fails])
	quit(0 if _fails == 0 else 1)
