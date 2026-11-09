extends SceneTree
## Dev tool: renders one bespoke hero (res://assets/models/heroes/<race>.glb) through its clips on a clean stage.
## Needs a window (not --headless).
##
##   godot --path godot --resolution 1800x700 -s res://tests/visual/hero_sheet.gd -- \
##       --race=ironlocust --out=/abs/sheet.png [--yaw=35] [--height=0.62]
##
## Humanoid heroes go through CharacterModel (shared clips); creatures use their own clips. One row of frames:
## Idle, Walk at 4 phases, Hit peak, Death end. Writes <out>_0.png ... <out>_N.png.

const SHARED_PHASES := [0.0, 0.25, 0.5, 0.75]


func _init() -> void:
	call_deferred("_run")


func _arg(arg_name: String, default_value := "") -> String:
	var prefix := "--%s=" % arg_name
	for a in OS.get_cmdline_user_args():
		if a.begins_with(prefix):
			return a.substr(prefix.length())
	return default_value


func _run() -> void:
	var race := _arg("race", "ironlocust")
	var out := _arg("out", "/tmp/hero_sheet.png")
	var yaw := float(_arg("yaw", "35"))
	var height := float(_arg("height", "0.62"))
	for _i in 4:
		await process_frame

	var stage := Node3D.new()
	root.add_child(stage)
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.16, 0.14, 0.12)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.55, 0.52, 0.5)
	var we := WorldEnvironment.new()
	we.environment = env
	stage.add_child(we)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-50, 30, 0)
	sun.light_energy = 1.4
	stage.add_child(sun)

	var node: Node3D = null
	var is_char := false
	var cm := CharacterModel.new()
	stage.add_child(cm)
	if cm.setup(race):
		node = cm
		is_char = true
	else:
		cm.queue_free()
		node = ModelLibrary.instantiate_hero(race, height)
		if node == null:
			print("HERO no model for ", race)
			quit(2)
			return
		stage.add_child(node)
	node.rotation_degrees.y = yaw

	var ap: AnimationPlayer = cm.get_animation_player() if is_char else ModelLibrary.find_anim_player(node)
	var clips := {"idle": ModelLibrary.find_clip(ap, "idle"), "walk": ModelLibrary.find_clip(ap, "walk"),
		"hit": ModelLibrary.find_clip(ap, "hit"), "death": ModelLibrary.find_clip(ap, "death")}
	if is_char:   # shared library names
		clips = {"idle": "Idle", "walk": "Walk", "hit": "Hit", "death": "Death"}
	ap.playback_default_blend_time = 0.0   # a blend from the previous clip would hide the pose we seek
	print("HERO clips ", clips)

	var cam := Camera3D.new()
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	cam.size = height * 2.0
	stage.add_child(cam)
	cam.position = Vector3(0, height * 0.55, 4)
	cam.look_at(Vector3(0, height * 0.5, 0))

	var frames: Array[Image] = []
	var plan := [["idle", 0.3], ["walk", 0.0], ["walk", 0.25], ["walk", 0.5], ["walk", 0.75], ["hit", 0.12], ["death", 1.0]]
	for step in plan:
		var clip: String = clips[step[0]]
		if clip.is_empty() or not ap.has_animation(clip):
			continue
		var anim := ap.get_animation(clip)
		var t: float = float(step[1]) * anim.length if step[0] == "walk" else minf(float(step[1]), anim.length)
		ap.play(clip)
		ap.pause()
		ap.seek(t, true)
		for _i in 3:
			await process_frame
		frames.append(root.get_texture().get_image())

	if frames.is_empty():
		quit(3)
		return
	# One PNG per frame (<out> with _N before the extension); montage them with ImageMagick.
	var base := out.get_basename()
	var failed := false
	for i in frames.size():
		var path := "%s_%d.png" % [base, i]
		if frames[i].save_png(path) != OK:
			failed = true
		print("SAVED ", path, " (", frames[i].get_width(), "x", frames[i].get_height(), ")")
	quit(1 if failed else 0)
