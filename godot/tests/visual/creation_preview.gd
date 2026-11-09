extends SceneTree
## Dev tool: boots the Creation scene, drives it to a few states and saves PNGs of the window.
## Needs a window.   godot --path godot --resolution 1600x900 -s res://tests/visual/creation_preview.gd -- \
##       --out-dir=/abs/dir [--races=bloodweaver,voidwraith] [--prefix=wp1-]

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
	await _frames(10)
	var img := get_root().get_texture().get_image()
	print("SAVED %s err=%d" % [path, img.save_png(path)])


func _run() -> void:
	var out_dir := _arg("out-dir", "/tmp")
	var prefix := _arg("prefix", "")
	var races := _arg("races", "bloodweaver,voidwraith,ironveil").split(",", false)
	var scene := (load("res://scenes/Creation.tscn") as PackedScene).instantiate()
	get_root().add_child(scene)
	await _frames(30)
	if scene.catalog.is_empty():
		scene._setup_mock_catalog()
		await _frames(2)
	# Offer all 35 races, whatever backend (or mock) supplied the catalog.
	scene.catalog["races"] = _Races.RACES.duplicate(true)
	if _arg("fallback", "0") == "1":
		scene.race_mini.use_character_models = false
	print("catalog races: ", scene.catalog["races"].size())
	await _shot("%s/%screation_era.png" % [out_dir, prefix])
	scene.current_step = 1
	scene._render_step()
	await _frames(4)
	var catalog_races: Dictionary = scene.catalog.get("races", {})
	for race in races:
		if not catalog_races.has(race):
			print("race not in catalog: ", race)
			continue
		scene.selection["race"] = race
		scene._render_step()
		await _frames(4)
		await _shot("%s/%screation_%s.png" % [out_dir, prefix, race])
	quit(0)
