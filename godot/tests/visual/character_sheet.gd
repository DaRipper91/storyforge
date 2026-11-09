extends SceneTree
## Dev tool: renders the shared-skeleton characters to PNGs. Needs a window (not --headless).
##
##   godot --path godot --resolution 1600x900 -s res://tests/visual/character_sheet.gd -- \
##       --out-dir=/abs/dir [--parts=idle,walk,phone] [--races=a,b,c] [--prefix=wp1-]
##
## idle  : every race standing in Idle, from the Tabletop camera angle (orthographic, 45 deg down)
## walk  : one race per group, 4 Walk frames + 1 Run frame + the final Death pose, side view
## phone : characters at phone scale (about 120 px tall on a 1080 px tall viewport) and at the
##         zoom the Tabletop camera really uses (ortho size 20 -> about 54 px per world unit)
##
## Prints one line per rendered image. Exit code 1 if any image failed to save.

const _Races := preload("res://scripts/core/data/races_data.gd")

const TABLETOP_PITCH := 45.0
const GROUP_SAMPLES := ["voidwraith", "solarlord", "bloodweaver", "ironveil", "ashenborn"]

var _fail := false


func _init() -> void:
	call_deferred("_run")


func _arg(arg_name: String, default_value := "") -> String:
	var prefix := "--%s=" % arg_name
	for a in OS.get_cmdline_user_args():
		if a.begins_with(prefix):
			return a.substr(prefix.length())
	return default_value


func _make_stage(viewport: Node, bg := Color(0.16, 0.14, 0.12)) -> Node3D:
	var stage := Node3D.new()
	viewport.add_child(stage)
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = bg
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.75, 0.72, 0.68)
	env.ambient_light_energy = 0.55
	var we := WorldEnvironment.new()
	we.environment = env
	stage.add_child(we)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-55.0, -30.0, 0.0)
	sun.light_energy = 1.2
	stage.add_child(sun)
	return stage


func _floor(stage: Node3D, centre: Vector3, size: Vector2) -> void:
	var mi := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = size
	mi.mesh = plane
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.30, 0.26, 0.21)
	mi.material_override = mat
	mi.position = centre + Vector3(0.0, -0.01, 0.0)
	stage.add_child(mi)


func _label(stage: Node3D, text: String, pos: Vector3, size := 0.0035) -> void:
	var l := Label3D.new()
	l.text = text
	l.font_size = 40
	l.pixel_size = size
	l.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	l.no_depth_test = true
	l.position = pos
	stage.add_child(l)


## `yaw_deg` turns the character about Y; 0 faces +Z (towards a camera on the +Z side).
func _spawn(stage: Node3D, race: String, pos: Vector3, yaw_deg := 0.0) -> CharacterModel:
	var cm := CharacterModel.new()
	stage.add_child(cm)
	if not cm.setup(race):
		printerr("CharacterModel.setup FAILED for ", race)
		_fail = true
	cm.position = pos
	cm.rotation.y = deg_to_rad(180.0 + yaw_deg)
	return cm


func _pose(cm: CharacterModel, clip: StringName, t: float) -> void:
	var ap := cm.get_animation_player()
	if ap == null:
		return
	ap.stop()
	ap.play(clip)
	ap.pause()
	ap.seek(t, true)


func _camera(stage: Node3D, focus: Vector3, size: float, pitch: float, yaw: float, dist := 30.0) -> Camera3D:
	var cam := Camera3D.new()
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	cam.size = size
	cam.far = 200.0
	stage.add_child(cam)
	var p := deg_to_rad(pitch)
	var y := deg_to_rad(yaw)
	cam.position = focus + Vector3(dist * cos(p) * sin(y), dist * sin(p), dist * cos(p) * cos(y))
	cam.look_at(focus, Vector3.UP)
	return cam


func _save(img: Image, path: String) -> void:
	var err := img.save_png(path)
	print("SAVED %s (%dx%d) err=%d" % [path, img.get_width(), img.get_height(), err])
	if err != OK:
		_fail = true


func _frames(n := 5) -> void:
	for _i in n:
		await process_frame


func _run() -> void:
	var out_dir := _arg("out-dir", "/tmp")
	var prefix := _arg("prefix", "")
	var parts := _arg("parts", "idle,walk,phone").split(",", false)
	var races: PackedStringArray = _arg("races").split(",", false)
	if races.is_empty():
		races = PackedStringArray(_Races.RACES.keys())
	var root := get_root()

	if "idle" in parts:
		var holder := Node.new()
		root.add_child(holder)
		var stage := _make_stage(holder)
		var cols := 7
		var cell := 1.7
		var rows := int(ceil(races.size() / float(cols)))
		for i in races.size():
			var c := i % cols
			var r := i / cols
			var pos := Vector3((c - (cols - 1) * 0.5) * cell, 0.0, (r - (rows - 1) * 0.5) * cell * 1.15)
			var cm := _spawn(stage, races[i], pos)
			_pose(cm, HumanoidAnimLibrary.CLIP_IDLE, 0.8)
			_label(stage, races[i], pos + Vector3(0.0, -0.02, 0.5))
		_floor(stage, Vector3.ZERO, Vector2(cols * cell + 1.0, rows * cell * 1.15 + 1.0))
		_camera(stage, Vector3(0.0, 0.5, 0.0), rows * cell * 1.15 * 0.78 + 2.2, TABLETOP_PITCH, 0.0)
		await _frames()
		_save(root.get_texture().get_image(), "%s/%sidle_grid.png" % [out_dir, prefix])
		holder.queue_free()
		await _frames(2)

	if "walk" in parts:
		var holder := Node.new()
		root.add_child(holder)
		var stage := _make_stage(holder)
		var times := [0.0, 0.2, 0.4, 0.6]
		var dx := 1.25
		for gi in GROUP_SAMPLES.size():
			var y := (2 - gi) * 1.25
			for ti in times.size():
				var pos := Vector3((ti - 2.5) * dx, y, 0.0)
				var cm := _spawn(stage, GROUP_SAMPLES[gi], pos, 90.0)
				_pose(cm, HumanoidAnimLibrary.CLIP_WALK, times[ti])
			_pose(_spawn(stage, GROUP_SAMPLES[gi], Vector3(1.5 * dx, y, 0.0), 90.0), HumanoidAnimLibrary.CLIP_RUN, 0.12)
			_pose(_spawn(stage, GROUP_SAMPLES[gi], Vector3(2.5 * dx + 0.3, y, 0.0), 90.0), HumanoidAnimLibrary.CLIP_DEATH, HumanoidAnimLibrary.DEATH_LENGTH)
			_label(stage, GROUP_SAMPLES[gi], Vector3(-4.6, y + 0.5, 0.0))
			var line := MeshInstance3D.new()
			var box := BoxMesh.new()
			box.size = Vector3(11.0, 0.01, 0.4)
			line.mesh = box
			line.position = Vector3(-0.6, y - 0.01, 0.0)
			stage.add_child(line)
		_camera(stage, Vector3(-0.3, 0.2, 0.0), 6.6, 0.0, 0.0, 30.0)
		await _frames()
		_save(root.get_texture().get_image(), "%s/%swalk_strip.png" % [out_dir, prefix])
		holder.queue_free()
		await _frames(2)

	if "closeup" in parts:
		# One race, side view, eight poses: judge limb direction, stance and grounding.
		var holder := Node.new()
		root.add_child(holder)
		var stage := _make_stage(holder)
		var race := _arg("closeup-race", "ironveil")
		var poses := [
			[HumanoidAnimLibrary.CLIP_IDLE, 0.8], [HumanoidAnimLibrary.CLIP_WALK, 0.2],
			[HumanoidAnimLibrary.CLIP_WALK, 0.6], [HumanoidAnimLibrary.CLIP_RUN, 0.12],
			[HumanoidAnimLibrary.CLIP_RUN, 0.37], [HumanoidAnimLibrary.CLIP_INTERACT, 0.45],
			[HumanoidAnimLibrary.CLIP_HIT, 0.15], [HumanoidAnimLibrary.CLIP_DEATH, 0.55],
		]
		var yaw := float(_arg("yaw", "90"))
		for i in poses.size():
			var pos := Vector3(((i % 4) - 1.5) * 1.3, (1 - i / 4) * 1.3, 0.0)
			_pose(_spawn(stage, race, pos, yaw), poses[i][0], poses[i][1])
			_label(stage, "%s %.2f" % [poses[i][0], poses[i][1]], pos + Vector3(0.0, -0.1, 0.0))
		_camera(stage, Vector3(0.0, 0.85, 0.0), 3.4, 0.0, 0.0, 30.0)
		await _frames()
		_save(root.get_texture().get_image(), "%s/%scloseup_%s.png" % [out_dir, prefix, race])
		holder.queue_free()
		await _frames(2)

	if "tokens" in parts:
		# The real game token (RaceMini scene): species with a model, one selected, a primitive
		# fallback, and a non-race id that must still use its primitive recipe.
		var holder := Node.new()
		root.add_child(holder)
		var stage := _make_stage(holder)
		var mini_scene := load("res://scenes/RaceMini.tscn") as PackedScene
		var ids := ["voidwraith", "solarlord", "bloodweaver", "ironveil", "ashenborn", "ashenborn", "goblin"]
		for i in ids.size():
			var mini := mini_scene.instantiate() as RaceMini
			stage.add_child(mini)
			mini.position = Vector3((i - (ids.size() - 1) * 0.5) * 1.4, 0.05, 0.0)
			if i == 5:
				mini.use_character_models = false
			mini.setup(ids[i])
			if i == 4:
				mini.select()
			if i == 3:
				mini.play_walk()
			print("token %s has_character=%s" % [ids[i], mini.has_character()])
			_label(stage, ids[i] + (" (selected)" if i == 4 else (" (primitive)" if i == 5 else "")), mini.position + Vector3(0.0, -0.02, 0.6))
		_floor(stage, Vector3.ZERO, Vector2(14.0, 5.0))
		_camera(stage, Vector3(0.0, 0.4, 0.0), 5.8, TABLETOP_PITCH, 0.0)
		await _frames(20)
		_save(root.get_texture().get_image(), "%s/%stokens.png" % [out_dir, prefix])
		holder.queue_free()
		await _frames(2)

	if "phone" in parts:
		# Offscreen 2400x1080 target, the Pixel 10 Pro's landscape size.
		for variant in ["phone120", "tabletop_zoom"]:
			var sv := SubViewport.new()
			sv.size = Vector2i(2400, 1080)
			sv.render_target_update_mode = SubViewport.UPDATE_ALWAYS
			root.add_child(sv)
			var stage := _make_stage(sv)
			var show := ["voidwraith", "nullshade", "solarlord", "deeptyrant", "bloodweaver", "chaosling", "ironveil", "wirewraith", "ashenborn", "fallenlight"]
			var spacing := 1.55 if variant == "phone120" else 1.55
			for i in show.size():
				var pos := Vector3((i - (show.size() - 1) * 0.5) * spacing * (1.0 if variant == "phone120" else 0.16), 0.0, 0.0)
				var cm := _spawn(stage, show[i], pos)
				_pose(cm, HumanoidAnimLibrary.CLIP_IDLE, 0.8)
			# 120 px for a 0.9 tall character: 0.9 * cos(45) world units on screen.
			var size_units := 1080.0 * 0.9 * cos(deg_to_rad(TABLETOP_PITCH)) / 120.0 if variant == "phone120" else 20.0
			_floor(stage, Vector3.ZERO, Vector2(60.0, 30.0))
			var cam := _camera(stage, Vector3(0.0, 0.3, 0.0), size_units, TABLETOP_PITCH, 0.0)
			cam.current = true
			await _frames(6)
			var img := sv.get_texture().get_image()
			if variant == "tabletop_zoom":
				img = img.get_region(Rect2i(900, 380, 600, 320))
			_save(img, "%s/%s%s.png" % [out_dir, prefix, variant])
			sv.queue_free()
			await _frames(2)

	quit(1 if _fail else 0)
