extends SceneTree
## Dev tool: render GLB/scene models side by side and save a PNG. Needs a window (not --headless).
##
##   godot --path godot --resolution 1600x800 -s res://tests/visual/model_gallery.gd -- \
##       --out=/abs/gallery.png --models=res://assets/models/player/cosmic.glb,res://... \
##       [--cols=5] [--pitch=20] [--yaw=0] [--target=1.8]
##
## Each model is scaled to --target metres tall and stood on a plane. Prints one line per model
## with height, mesh count, bone count and animation names, so rig and clip problems are visible
## without opening the editor.

const CELL := 2.4

func _init() -> void:
	call_deferred("_run")


func _arg(arg_name: String, default_value := "") -> String:
	var prefix := "--%s=" % arg_name
	for a in OS.get_cmdline_user_args():
		if a.begins_with(prefix):
			return a.substr(prefix.length())
	return default_value


func _collect_aabb(node: Node, acc: Array) -> void:
	if node is MeshInstance3D:
		var mi := node as MeshInstance3D
		var box: AABB = mi.global_transform * mi.get_aabb()
		if acc.is_empty():
			acc.append(box)
		else:
			acc[0] = (acc[0] as AABB).merge(box)
	for c in node.get_children():
		_collect_aabb(c, acc)


func _run() -> void:
	var out_path := _arg("out", "/tmp/gallery.png")
	var models := _arg("models").split(",", false)
	var cols := maxi(1, int(_arg("cols", "5")))
	var pitch := float(_arg("pitch", "20"))
	var yaw := float(_arg("yaw", "0"))
	var target := float(_arg("target", "1.8"))

	var root := get_root()
	var stage := Node3D.new()
	root.add_child(stage)

	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.13, 0.12, 0.11)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.7, 0.68, 0.64)
	env.ambient_light_energy = 0.6
	var we := WorldEnvironment.new()
	we.environment = env
	stage.add_child(we)

	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-50.0, -35.0, 0.0)
	sun.light_energy = 1.3
	stage.add_child(sun)

	var rows := int(ceil(models.size() / float(cols)))
	var width := cols * CELL
	var depth := rows * CELL

	var floor_mesh := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(width + 2.0, depth + 2.0)
	floor_mesh.mesh = plane
	var floor_mat := StandardMaterial3D.new()
	floor_mat.albedo_color = Color(0.2, 0.19, 0.17)
	floor_mesh.material_override = floor_mat
	floor_mesh.position = Vector3(0.0, 0.0, -depth * 0.5 + CELL * 0.5)
	stage.add_child(floor_mesh)

	for i in models.size():
		var path := models[i].strip_edges()
		var res = load(path)
		if res == null or not (res is PackedScene):
			print("MODEL %s FAILED to load" % path)
			continue
		var inst := (res as PackedScene).instantiate() as Node3D
		stage.add_child(inst)
		var acc: Array = []
		_collect_aabb(inst, acc)
		var box: AABB = acc[0] if not acc.is_empty() else AABB(Vector3.ZERO, Vector3.ONE)
		var s := target / maxf(box.size.y, 0.001)
		inst.scale = Vector3.ONE * s
		var col := i % cols
		var row := i / cols
		inst.position = Vector3((col - (cols - 1) * 0.5) * CELL, -box.position.y * s, -row * CELL)
		var bones := 0
		for sk in inst.find_children("*", "Skeleton3D", true, false):
			bones += (sk as Skeleton3D).get_bone_count()
		var anims: PackedStringArray = []
		for ap in inst.find_children("*", "AnimationPlayer", true, false):
			for a in (ap as AnimationPlayer).get_animation_list():
				anims.append(a)
		var meshes := inst.find_children("*", "MeshInstance3D", true, false).size()
		print("MODEL %s raw_h=%.2f scale=%.2f meshes=%d bones=%d anims=[%s]" % [
			path.get_file(), box.size.y, s, meshes, bones, ", ".join(anims.slice(0, 8))])
		var label := Label3D.new()
		label.text = path.get_file().get_basename()
		label.font_size = 48
		label.pixel_size = 0.004
		label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		label.position = inst.position + Vector3(0.0, -0.18, 0.5)
		stage.add_child(label)

	var cam := Camera3D.new()
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	cam.size = maxf(depth * 0.9 + target * 1.4, width * 0.45)
	stage.add_child(cam)
	var focus := Vector3(0.0, target * 0.5, -(rows - 1) * CELL * 0.5)
	cam.position = focus + Vector3(0.0, 0.0, 12.0).rotated(Vector3.RIGHT, deg_to_rad(-pitch)).rotated(Vector3.UP, deg_to_rad(yaw))
	cam.look_at(focus, Vector3.UP)

	for _i in 6:
		await process_frame
	var img := root.get_texture().get_image()
	var err := img.save_png(out_path)
	print("SAVED %s (%dx%d) err=%d" % [out_path, img.get_width(), img.get_height(), err])
	quit(0 if err == OK else 1)
