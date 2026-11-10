extends SceneTree
## Dev tool: walks the Creation scene through every step on a real window and saves one PNG per step.
## Needs a display.  WAYLAND_DISPLAY=wayland-1 DISPLAY=:0 godot --path godot --resolution 2410x1080 \
##   -s res://tests/visual/creation_steps.gd -- --out-dir=/abs/dir [--prefix=ui-] [--swipes=3] [--race-extra=1]

const _Races := preload("res://scripts/core/data/races_data.gd")


func _init() -> void:
	call_deferred("_run")


func _arg(arg_name: String, default_value := "") -> String:
	var prefix := "--%s=" % arg_name
	for a in OS.get_cmdline_user_args():
		if a.begins_with(prefix):
			return a.substr(prefix.length())
	return default_value


func _frames(n := 8) -> void:
	for _i in n:
		await process_frame


func _shot(path: String) -> void:
	await _frames(12)
	var img := get_root().get_texture().get_image()
	print("SAVED %s %s err=%d" % [path, img.get_size(), img.save_png(path)])


func _run() -> void:
	var out_dir := _arg("out-dir", "/tmp")
	var prefix := _arg("prefix", "ui-")
	var swipes := int(_arg("swipes", "3"))
	var scene := (load("res://scenes/Creation.tscn") as PackedScene).instantiate()
	get_root().add_child(scene)
	await _frames(30)
	scene._setup_mock_catalog()
	scene.catalog["races"] = _Races.RACES.duplicate(true)
	scene.current_step = 0
	scene._render_step()
	await _shot("%s/%s0-era.png" % [out_dir, prefix])
	scene.current_step = 1
	scene._render_step()
	await _frames(6)
	await _shot("%s/%s1-race-first.png" % [out_dir, prefix])
	scene.carousel.select_index(swipes + 10)
	scene.carousel.settle()
	await _shot("%s/%s1-race-mid.png" % [out_dir, prefix])
	scene.carousel.select_index(30)
	scene.carousel.settle()
	await _shot("%s/%s1-race-humanoid.png" % [out_dir, prefix])
	scene.current_step = 2
	scene.selection["evolution_state"] = "phantom"
	scene._render_step()
	await _shot("%s/%s2-state.png" % [out_dir, prefix])
	scene.current_step = 3
	scene.selection["predator_role"] = "stalker"
	scene._render_step()
	await _shot("%s/%s3-role.png" % [out_dir, prefix])
	scene.current_step = 4
	scene.selection["abilities"]["STR"] = 15
	scene.selection["abilities"]["DEX"] = 14
	scene._focused_ability = "CON"
	scene._render_step()
	await _shot("%s/%s4-abilities.png" % [out_dir, prefix])
	scene.current_step = 5
	scene.selection["name"] = "Rook"
	scene._render_step()
	await _shot("%s/%s5-name.png" % [out_dir, prefix])
	quit(0)
