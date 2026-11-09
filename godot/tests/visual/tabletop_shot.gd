extends SceneTree
## Dev tool: put a character into the REAL Tabletop scene (offline backend, throwaway save dir) and
## screenshot it at the size of a phone window. Needs a display (not --headless).
##
##   godot --path godot --resolution 2410x1080 -s res://tests/visual/tabletop_shot.gd -- \
##       --backend=local --save-dir=/abs/dir --out=/abs/shot.png [--race=bloodweaver] [--zoom=-3] [--wait=90]
##
## --zoom=N sends |N| mouse-wheel steps (negative = zoom in, positive = out) through the same
## input path the wheel and the touch layer's pinch use, so it also proves zoom actually works.
## Prints the Camera3D size and the on-screen height of the player's mini so scale is measurable.

const ABILITIES := {"STR": 8, "DEX": 15, "CON": 14, "INT": 10, "WIS": 12, "CHA": 13}


func _init() -> void:
	call_deferred("_run")


func _arg(arg_name: String, default_value := "") -> String:
	var prefix := "--%s=" % arg_name
	for a in OS.get_cmdline_user_args():
		if a.begins_with(prefix):
			return a.substr(prefix.length())
	return default_value


func _post(pc: Node, path: String, body: Dictionary) -> Array:
	var http = pc.post_request(path, body)
	return await http.request_completed


func _run() -> void:
	var out_path := _arg("out", "/tmp/tabletop_shot.png")
	var race := _arg("race", "bloodweaver")
	var zoom := int(_arg("zoom", "0"))
	var waits := int(_arg("wait", "90"))

	var pc := get_root().get_node_or_null("PythonClient")
	if pc == null:
		print("SHOT no PythonClient autoload")
		quit(2)
		return
	for _i in 6:
		await process_frame

	await _post(pc, "/lobby/join", {"controller_id": "shot"})
	await _post(pc, "/lobby/set_phase", {"phase": "creation"})
	var r := await _post(pc, "/character/create", {
		"abilities": ABILITIES, "evolution_state": "behemoth", "name": "Hero",
		"predator_role": "vanguard", "race": race, "slot_index": 0, "starting_era": "after"})
	print("SHOT create_character status=%d" % int(r[1]))
	r = await _post(pc, "/lobby/start", {})
	print("SHOT start status=%d" % int(r[1]))

	var tabletop := (load("res://scenes/Tabletop.tscn") as PackedScene).instantiate()
	get_root().add_child(tabletop)
	for _i in waits:
		await process_frame

	for _i in absi(zoom):
		var ev := InputEventMouseButton.new()
		ev.button_index = MOUSE_BUTTON_WHEEL_UP if zoom < 0 else MOUSE_BUTTON_WHEEL_DOWN
		ev.pressed = true
		ev.position = Vector2(get_root().size) * 0.5
		Input.parse_input_event(ev)
		await process_frame
	for _i in 12:
		await process_frame

	var cam: Camera3D = tabletop.camera
	var info := "SHOT camera size=%.2f projection=%d" % [cam.size, cam.projection]
	for k in tabletop._miniatures:
		var mini: Node3D = tabletop._miniatures[k]
		var head := cam.unproject_position(mini.global_position + Vector3(0, 0.9, 0))
		var feet := cam.unproject_position(mini.global_position)
		info += " | mini %s height_px=%.0f" % [k, absf(feet.y - head.y)]
	print(info)

	var img := get_root().get_texture().get_image()
	var err := img.save_png(out_path)
	print("SAVED %s (%dx%d) err=%d" % [out_path, img.get_width(), img.get_height(), err])
	quit(0 if err == OK else 1)
