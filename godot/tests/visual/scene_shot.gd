extends SceneTree
## Dev tool: load a scene on a real window, optionally put it into a known UI state, save a PNG.
## Needs a display (not --headless). Use it to look at a screen the way a player sees it.
##
##   godot --path godot --resolution 1280x720 -s res://tests/visual/scene_shot.gd -- \
##       --scene=res://scenes/UI_Overlay.tscn --out=/abs/shot.png [--prep=save_menu|main_menu] [--wait=20]
##
## --prep puts UI_Overlay into a state that normally needs a server round trip:
##   main_menu  title hidden, main menu shown
##   save_menu  save menu shown, filled through the real _on_campaigns_received() with fake saves
##   save_empty same, with an empty list ("No saved chronicles found.")

const FAKE_SAVES := [
	{"campaign_id": "family_campaign_01", "characters": ["Rook", "Mira"], "phase": "exploration"},
	{"campaign_id": "campaign_20261109_103045", "characters": ["Dax"], "phase": "creation"},
	{"campaign_id": "campaign_20261108_221500", "characters": [], "phase": "lobby"},
]


func _init() -> void:
	call_deferred("_run")


func _arg(arg_name: String, default_value := "") -> String:
	var prefix := "--%s=" % arg_name
	for a in OS.get_cmdline_user_args():
		if a.begins_with(prefix):
			return a.substr(prefix.length())
	return default_value


func _run() -> void:
	var scene_path := _arg("scene", "res://scenes/UI_Overlay.tscn")
	var out_path := _arg("out", "/tmp/scene_shot.png")
	var prep := _arg("prep")
	var waits := int(_arg("wait", "20"))

	var packed := load(scene_path) as PackedScene
	if packed == null:
		print("SHOT FAILED to load %s" % scene_path)
		quit(2)
		return
	var inst := packed.instantiate()
	get_root().add_child(inst)
	for _i in 4:
		await process_frame

	match prep:
		"main_menu":
			inst.title_screen.hide()
			inst.main_menu.show()
		"save_menu", "save_empty":
			inst.title_screen.hide()
			inst.main_menu.hide()
			inst.save_game_menu.show()
			inst._on_campaigns_received(FAKE_SAVES if prep == "save_menu" else [])
		"":
			pass
		_:
			print("SHOT unknown prep '%s'" % prep)

	for _i in waits:
		await process_frame
	var img := get_root().get_texture().get_image()
	var err := img.save_png(out_path)
	print("SAVED %s (%dx%d) err=%d" % [out_path, img.get_width(), img.get_height(), err])
	if prep == "save_menu" or prep == "save_empty":
		var list: Control = inst.save_list
		var sc: Control = list.get_parent()
		print("SAVELIST children=%d scroll_container_size=%s list_size=%s" % [
			list.get_child_count(), sc.size, list.size])
		for c in list.get_children():
			print("  row %s size=%s visible_in_tree=%s" % [c.get_class(), (c as Control).size, (c as Control).is_visible_in_tree()])
	quit(0 if err == OK else 1)
