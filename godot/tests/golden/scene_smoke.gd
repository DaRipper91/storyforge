extends SceneTree
## Instantiates one scene as a child of root, lets it run N frames, quits.
## Used by tools/golden/run_gd_scene_smoke.sh to diff script-error sets between modes/builds.
##   godot --headless --path <scratch godot/> -s res://tests/golden/scene_smoke.gd -- \
##         --scene=res://scenes/Tabletop.tscn --frames=90 [--backend=local]

func _initialize() -> void:
	_run()


func _run() -> void:
	var scene_path := ""
	var frames := 90
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--scene="):
			scene_path = arg.substr(8)
		elif arg.begins_with("--frames="):
			frames = int(arg.substr(9))
	var packed: PackedScene = load(scene_path)
	if packed == null:
		printerr("scene_smoke: cannot load ", scene_path)
		quit(2)
		return
	await process_frame
	var inst := packed.instantiate()
	root.add_child(inst)
	for i in frames:
		await process_frame
	print("scene_smoke: ran ", frames, " frames: ", scene_path)
	quit(0)
