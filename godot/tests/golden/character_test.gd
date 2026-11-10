extends SceneTree
## Headless test of the shared-skeleton character pipeline:
##   res://scripts/characters/humanoid_anim_library.gd  (HumanoidAnimLibrary)
##   res://scripts/characters/character_model.gd        (CharacterModel)
## plus the RaceMini integration. No display needed.
##   godot --headless --path <scratch copy of godot/> -s res://tests/golden/character_test.gd
## Exit 0 only when every check passes; final stdout line is `RESULT: OK|FAILED`.
## Includes NEGATIVE controls: the track-resolution and leak assertions are re-run against
## deliberately broken inputs and must report failure, proving they can fail.

const _Races := preload("res://scripts/core/data/races_data.gd")

const SKELETON_GLBS := [
	"res://assets/models/player/cosmic.glb",
	"res://assets/models/player/eldritch.glb",
	"res://assets/models/player/humanoid.glb",
	"res://assets/models/player/mechanical.glb",
	"res://assets/models/player/primal.glb",
	"res://assets/models/humanoid/npc_default.glb",
	"res://assets/models/humanoid/npc_mage.glb",
	"res://assets/models/humanoid/npc_performer.glb",
	"res://assets/models/humanoid/npc_royal.glb",
	"res://assets/models/humanoid/npc_warrior.glb",
]

var _fails := 0
var _checks := 0


func _check(label: String, cond: bool, detail: String = "") -> void:
	_checks += 1
	if cond:
		print("  ok   ", label)
	else:
		_fails += 1
		printerr("  FAIL ", label, "  ", detail)


func _initialize() -> void:
	_run()


# ─── Assertions that the negative controls re-use ────────────────────────────────────

## "" when every track of every clip points at an existing bone under `inst`, else a message.
func _tracks_resolve(lib: AnimationLibrary, inst: Node) -> String:
	for clip_name in lib.get_animation_list():
		var anim := lib.get_animation(clip_name)
		if anim.get_track_count() == 0:
			return "%s has no tracks" % clip_name
		for t in anim.get_track_count():
			var path := anim.track_get_path(t)
			var skel := inst.get_node_or_null(NodePath(path.get_concatenated_names())) as Skeleton3D
			if skel == null:
				return "%s track %d: no Skeleton3D at %s" % [clip_name, t, path]
			var bone := String(path.get_concatenated_subnames())
			if skel.find_bone(bone) < 0:
				return "%s track %d: no bone %s" % [clip_name, t, bone]
	return ""


## Nodes created minus nodes freed by `work`, after one warm-up call (static caches fill once).
func _node_delta(work: Callable) -> int:
	work.call()
	var before := int(Performance.get_monitor(Performance.OBJECT_NODE_COUNT))
	work.call()
	return int(Performance.get_monitor(Performance.OBJECT_NODE_COUNT)) - before


func _skeleton_of(inst: Node) -> Skeleton3D:
	return inst.find_children("*", "Skeleton3D", true, false)[0] as Skeleton3D


# ─── Test body ───────────────────────────────────────────────────────────────────────

func _run() -> void:
	await process_frame   # nodes added to root before the first frame are not yet "inside the tree"
	# 1. Library: clip names, lengths, loop flags.
	var probe := (load(SKELETON_GLBS[0]) as PackedScene).instantiate() as Node3D
	get_root().add_child(probe)
	var skel := _skeleton_of(probe)
	var lib := HumanoidAnimLibrary.get_library(skel)
	var expected := {
		&"Idle": [HumanoidAnimLibrary.IDLE_LENGTH, true],
		&"Walk": [HumanoidAnimLibrary.WALK_LENGTH, true],
		&"Run": [HumanoidAnimLibrary.RUN_LENGTH, true],
		&"Interact": [HumanoidAnimLibrary.INTERACT_LENGTH, false],
		&"Hit": [HumanoidAnimLibrary.HIT_LENGTH, false],
		&"Death": [HumanoidAnimLibrary.DEATH_LENGTH, false],
	}
	var names := Array(lib.get_animation_list())
	names.sort()
	var want_names := expected.keys()
	want_names.sort()
	_check("library has exactly the six clips", names == want_names, str(names))
	_check("library is cached (same instance twice)", HumanoidAnimLibrary.get_library(skel) == lib)
	_check("HumanoidAnimLibrary.is_compatible on the shared skeleton", HumanoidAnimLibrary.is_compatible(skel))
	_check("documented lengths", is_equal_approx(HumanoidAnimLibrary.IDLE_LENGTH, 3.2)
		and is_equal_approx(HumanoidAnimLibrary.WALK_LENGTH, 0.8)
		and is_equal_approx(HumanoidAnimLibrary.RUN_LENGTH, 0.5)
		and is_equal_approx(HumanoidAnimLibrary.INTERACT_LENGTH, 1.0)
		and is_equal_approx(HumanoidAnimLibrary.HIT_LENGTH, 0.5)
		and is_equal_approx(HumanoidAnimLibrary.DEATH_LENGTH, 1.2))
	for clip_name in expected:
		var anim := lib.get_animation(clip_name)
		var length: float = expected[clip_name][0]
		var loops: bool = expected[clip_name][1]
		_check("%s length %.2f" % [clip_name, length], anim != null and is_equal_approx(anim.length, length))
		_check("%s loop flag %s" % [clip_name, loops],
			anim != null and (anim.loop_mode == Animation.LOOP_LINEAR) == loops)
	# Looping clips must close their loop: last key == first key on every rotation track.
	var seams_ok := true
	for clip_name in [&"Idle", &"Walk", &"Run"]:
		var anim := lib.get_animation(clip_name)
		for t in anim.get_track_count():
			if anim.track_get_type(t) != Animation.TYPE_ROTATION_3D:
				continue
			var last := anim.track_get_key_count(t) - 1
			var a: Quaternion = anim.track_get_key_value(t, 0)
			var b: Quaternion = anim.track_get_key_value(t, last)
			if not a.is_equal_approx(b) and not a.is_equal_approx(-b):
				seams_ok = false
	_check("looping clips close their loop", seams_ok)
	var finite_ok := true
	for clip_name in lib.get_animation_list():
		var anim := lib.get_animation(clip_name)
		for t in anim.get_track_count():
			if anim.track_get_type(t) == Animation.TYPE_ROTATION_3D:
				for k in anim.track_get_key_count(t):
					var q: Quaternion = anim.track_get_key_value(t, k)
					if not q.is_finite() or absf(q.length() - 1.0) > 0.001:
						finite_ok = false
	_check("every rotation key is a finite unit quaternion", finite_ok)
	var death := lib.get_animation(&"Death")
	var hips_track := death.find_track(NodePath("%s:Hips" % HumanoidAnimLibrary.SKELETON_PATH), Animation.TYPE_ROTATION_3D)
	_check("Death animates the Hips", hips_track >= 0)
	if hips_track >= 0:
		var end_q: Quaternion = death.track_get_key_value(hips_track, death.track_get_key_count(hips_track) - 1)
		var rest_q := skel.get_bone_rest(skel.find_bone("Hips")).basis.get_rotation_quaternion()
		var turned := rad_to_deg(rest_q.angle_to(end_q))
		_check("Death ends with the body ~90 degrees from upright", turned > 70.0 and turned < 120.0, "%.1f deg" % turned)
	probe.queue_free()

	# 2. Every track resolves in each of the 10 skeleton GLBs.
	for path in SKELETON_GLBS:
		var inst := (load(path) as PackedScene).instantiate() as Node3D
		get_root().add_child(inst)
		var problem := _tracks_resolve(lib, inst)
		_check("tracks resolve in %s" % path.get_file(), problem.is_empty(), problem)
		var sk := _skeleton_of(inst)
		_check("%s has the shared 49-bone skeleton" % path.get_file(),
			sk.get_bone_count() == 49 and sk.find_bone("Hips") >= 0 and sk.find_bone("UpperArm.L") >= 0)
		inst.queue_free()
	# Negative control: a library whose paths are wrong must be reported.
	var first := (load(SKELETON_GLBS[0]) as PackedScene).instantiate() as Node3D
	get_root().add_child(first)
	var broken := HumanoidAnimLibrary.build(_skeleton_of(first), "Nowhere/Skeleton3D")
	_check("NEGATIVE: wrong skeleton path is detected", not _tracks_resolve(broken, first).is_empty())
	first.queue_free()

	# 3. CharacterModel for all 35 races.
	var ids: Array = _Races.RACES.keys()
	_check("35 races in races_data", ids.size() == 35, str(ids.size()))
	var setup_ok := true
	var failed: Array = []
	var by_group := {}
	for id in ids:
		var creature_probe := ModelLibrary.instantiate_hero(id, 0.9)
		if creature_probe != null:
			creature_probe.free()
			continue   # bespoke creature with its own skeleton: covered by the creature checks below
		var cm := CharacterModel.new()
		get_root().add_child(cm)
		var ok := cm.setup(id) and cm.is_ready()
		if ok:
			var grp: String = _Races.RACES[id]["group"]
			by_group[grp] = int(by_group.get(grp, 0)) + 1
			ok = cm.group == grp and cm.body_height > 0.3 \
				and cm.get_body_aabb().position.y == 0.0 \
				and cm.get_node("Pivot").find_children("*", "AnimationPlayer", true, false).size() == 1
		if not ok:
			setup_ok = false
			failed.append(id)
		cm.free()
	_check("CharacterModel.setup succeeds for every humanoid-skeleton race (creatures use their own clips)", setup_ok, str(failed))
	_check("five groups covered", by_group.size() == 5, str(by_group))
	var neutral := CharacterModel.new()
	get_root().add_child(neutral)
	_check("neutral humanoid (no race) builds", neutral.setup(CharacterModel.NEUTRAL_ID))
	neutral.free()
	var bogus := CharacterModel.new()
	get_root().add_child(bogus)
	# An unknown id still gets the Humanoid base (callers decide whether to use it).
	_check("unknown id falls back to the Humanoid base", bogus.setup("not_a_race") and bogus.group == "Humanoid")
	bogus.free()

	# 4. Rig sanity on one model per group: grounded, both legs present, per-race tint.
	for id in ["voidwraith", "solarlord", "bloodweaver", "ironveil", "ashenborn"]:
		var cm := CharacterModel.new()
		get_root().add_child(cm)
		cm.setup(id)
		var lowest := INF
		var highest := -INF
		var mirrored := 0
		for node in cm.find_children("*", "MeshInstance3D", true, false):
			var mi := node as MeshInstance3D
			var box := mi.global_transform * mi.get_aabb()
			lowest = minf(lowest, box.position.y)
			highest = maxf(highest, box.end.y)
			if String(mi.name).ends_with("_Mirrored"):
				mirrored += 1
		_check("%s: feet on the ground (lowest y %.3f)" % [id, lowest], absf(lowest) < 0.03 * cm.body_height)
		_check("%s: height %.2f matches body_height %.2f" % [id, highest - lowest, cm.body_height],
			absf((highest - lowest) - cm.body_height) < 0.02)
		# Bespoke heroes replace the one-sided shoes with their own boots/talons, so only the legs mirror.
		var expected_mirrors := 2 if CharacterModel.hero_path(id).is_empty() else 1
		_check("%s: missing right leg/foot meshes were mirrored in" % id, mirrored == expected_mirrors, str(mirrored))
		cm.free()
	var tint_a := CharacterModel.new()
	var tint_b := CharacterModel.new()
	get_root().add_child(tint_a)
	get_root().add_child(tint_b)
	# Exercise tinting on the group base even after every real race has authored art.
	# Heroes deliberately preserve their own materials (checked separately below).
	tint_a.setup(CharacterModel.NEUTRAL_ID, {"tint": CharacterModel.colours_for("ashenborn")["tint"]})
	tint_b.setup(CharacterModel.NEUTRAL_ID, {"tint": CharacterModel.colours_for("emberpact")["tint"]})
	var col_a := _first_albedo(tint_a)
	var col_b := _first_albedo(tint_b)
	_check("races of one group are tinted differently", not col_a.is_equal_approx(col_b), "%s vs %s" % [col_a, col_b])
	tint_a.tint = Color(0.1, 0.9, 0.1)
	_check("assigning tint re-applies materials", not _first_albedo(tint_a).is_equal_approx(col_a))
	_check("tint of one instance does not leak into another", _first_albedo(tint_b).is_equal_approx(col_b))
	tint_a.free()
	tint_b.free()

	# 5. play() switches clips; walking / one-shots / death behave.
	var cm := CharacterModel.new()
	get_root().add_child(cm)
	cm.setup("voidwraith")
	_check("starts in Idle", cm.current_clip() == &"Idle")
	cm.play(&"Run")
	_check("play(Run) switches to Run", cm.current_clip() == &"Run")
	cm.play(&"Idle")
	cm.set_walking(true)
	_check("set_walking(true) plays Walk", cm.current_clip() == &"Walk" and cm.is_walking())
	cm.set_walking(false)
	_check("set_walking(false) returns to Idle", cm.current_clip() == &"Idle")
	cm.set_walking(true)
	cm.play(&"Interact")
	_check("play(Interact) interrupts Walk", cm.current_clip() == &"Interact")
	cm.get_animation_player().advance(HumanoidAnimLibrary.INTERACT_LENGTH + 0.5)
	await process_frame
	await process_frame
	_check("one-shot hands back to Walk while walking", cm.current_clip() == &"Walk", cm.current_clip())
	cm.play(&"Death")
	cm.set_walking(false)
	cm.set_walking(true)
	_check("Death sticks against set_walking", cm.current_clip() == &"Death")
	cm.play(&"Idle")
	_check("play(Idle) revives", cm.current_clip() == &"Idle")
	cm.play(&"NoSuchClip")
	_check("unknown clip is ignored", cm.current_clip() == &"Idle")
	cm.free()

	# 6. RaceMini integration: species use the model, everything else keeps primitives.
	var mini := (load("res://scenes/RaceMini.tscn") as PackedScene).instantiate() as RaceMini
	get_root().add_child(mini)
	mini.setup("voidwraith")
	_check("RaceMini uses CharacterModel for a species", mini.has_character() and mini.has_model())
	mini.play_walk()
	_check("RaceMini.play_walk drives the walk clip", mini.get_node("MeshInstance3D/Character").current_clip() == &"Walk")
	mini.play_idle()
	_check("RaceMini.play_idle drives the idle clip", mini.get_node("MeshInstance3D/Character").current_clip() == &"Idle")
	var box := mini.get_visual_aabb()
	_check("RaceMini.get_visual_aabb is a standing body", box.size.y > 0.5 and box.size.y < 1.6, str(box))
	mini.select()
	mini.deselect()
	_check("select/deselect keep the identity ring", mini.get_node_or_null("IdentityRing") != null)
	mini.setup("goblin")
	_check("non-species id keeps the primitive recipe", not mini.has_character())
	_check("primitive AABB is non-empty", mini.get_visual_aabb().size.y > 0.1)
	mini.use_character_models = false
	mini.setup("voidwraith")
	_check("use_character_models=false falls back to primitives", not mini.has_character())
	_check("primitive fallback still frames (AABB)", mini.get_visual_aabb().size.y > 0.1)
	mini.free()

	# 7. Leaks: building and freeing characters must not strand nodes.
	var leak_work := func() -> void:
		for id in ["voidwraith", "ashenborn", "wirewraith"]:
			var c := CharacterModel.new()
			get_root().add_child(c)
			c.setup(id)
			c.play(&"Walk")
			c.free()
	var delta := _node_delta(leak_work)
	_check("create/free leaves no nodes behind (delta %d)" % delta, delta == 0)
	var orphans := int(Performance.get_monitor(Performance.OBJECT_ORPHAN_NODE_COUNT))
	_check("no orphan nodes (%d)" % orphans, orphans == 0)
	# Negative control: a deliberate leak must be reported.
	var held: Array = []
	var leaky := func() -> void:
		var n := Node3D.new()
		get_root().add_child(n)
		held.append(n)
	_check("NEGATIVE: a deliberate leak is detected", _node_delta(leaky) > 0)
	for n in held:
		n.free()

	print("-- bespoke hero models")
	_check("bloodweaver has a hero GLB", not CharacterModel.hero_path("bloodweaver").is_empty())
	_check("an id without a hero has no bespoke GLB", CharacterModel.hero_path("not_a_race").is_empty())
	var hero := CharacterModel.new()
	get_root().add_child(hero)
	_check("hero model sets up on the shared skeleton", hero.setup("bloodweaver"))
	var hero_sk := hero.get_skeleton()
	var hero_parts := 0
	var mirrored_hero_parts := 0
	for node in hero.find_children("Hero_*", "MeshInstance3D", true, false):
		hero_parts += 1
		if String(node.name).ends_with("_Mirrored"):
			mirrored_hero_parts += 1
	_check("hero attachments are present (%d Hero_* meshes)" % hero_parts, hero_parts >= 6)
	_check("Hero_* parts are never mirrored", mirrored_hero_parts == 0)
	var base_before := _first_albedo(hero)
	hero.tint = Color(0.1, 0.9, 0.1)
	_check("race tint does not recolour an authored hero", _first_albedo(hero).is_equal_approx(base_before))
	hero.play(&"Walk")
	_check("hero plays the shared Walk clip", hero.current_clip() == &"Walk")
	hero.free()

	var grim := CharacterModel.new()
	get_root().add_child(grim)
	_check("grimcrow hero sets up on the shared skeleton", not CharacterModel.hero_path("grimcrow").is_empty() and grim.setup("grimcrow"))
	var grim_parts := grim.find_children("Hero_*", "MeshInstance3D", true, false).size()
	_check("grimcrow has its bespoke parts (%d Hero_* meshes)" % grim_parts, grim_parts >= 12)
	grim.free()

	var void_w := CharacterModel.new()
	get_root().add_child(void_w)
	_check("voidwraith hero sets up on the shared skeleton", not CharacterModel.hero_path("voidwraith").is_empty() and void_w.setup("voidwraith"))
	var void_parts := void_w.find_children("Hero_*", "MeshInstance3D", true, false).size()
	_check("voidwraith has its bespoke parts (%d Hero_* meshes)" % void_parts, void_parts >= 20)
	void_w.free()

	print("-- every bespoke hero GLB (data-driven: new heroes are covered automatically)")
	var hero_ids: Array[String] = []
	var hdir := DirAccess.open("res://assets/models/heroes")
	if hdir != null:
		for f in hdir.get_files():
			if f.ends_with(".glb"):
				hero_ids.append(f.get_basename())
	hero_ids.sort()
	_check("at least the pilot heroes are present (%d)" % hero_ids.size(), hero_ids.size() >= 4)
	for hid in hero_ids:
		_check("%s: is a known race id" % hid, CharacterModel.is_known_race(hid))
		var hcm := CharacterModel.new()
		get_root().add_child(hcm)
		var humanoid := hcm.setup(hid)
		var root_node: Node = hcm if humanoid else ModelLibrary.instantiate_hero(hid, 0.62)
		if not humanoid:
			hcm.free()
		_check("%s: loads (humanoid skeleton or creature with clips)" % hid, root_node != null)
		if root_node == null:
			continue
		var tris := 0
		for mnode in root_node.find_children("*", "MeshInstance3D", true, false):
			var hmi := mnode as MeshInstance3D
			if hmi.mesh != null:
				tris += hmi.mesh.get_faces().size() / 3
		_check("%s: triangle budget %d <= 26000" % [hid, tris], tris <= 26000)
		var parts := root_node.find_children("Hero_*", "MeshInstance3D", true, false)
		_check("%s: bespoke parts present (%d)" % [hid, parts.size()], parts.size() >= 10)
		var mirrored_parts := 0
		for pnode in parts:
			if String(pnode.name).ends_with("_Mirrored"):
				mirrored_parts += 1
		_check("%s: bespoke parts are never mirrored" % hid, mirrored_parts == 0)
		if humanoid:
			hcm.play(&"Walk")
			_check("%s: plays the shared Walk clip" % hid, hcm.current_clip() == &"Walk")
		else:
			var hap := ModelLibrary.find_anim_player(root_node)
			_check("%s: creature has idle/walk/hit/death clips" % hid, hap != null and not ModelLibrary.find_clip(hap, "idle").is_empty() and not ModelLibrary.find_clip(hap, "walk").is_empty() and not ModelLibrary.find_clip(hap, "hit").is_empty() and not ModelLibrary.find_clip(hap, "death").is_empty())
		root_node.free()

	print("-- bespoke creature (own skeleton and clips)")
	_check("ironlocust has a hero GLB", not CharacterModel.hero_path("ironlocust").is_empty())
	var cm_creature := CharacterModel.new()
	get_root().add_child(cm_creature)
	_check("CharacterModel refuses a non-humanoid skeleton (falls through to the creature path)", not cm_creature.setup("ironlocust"))
	cm_creature.free()
	var creature := ModelLibrary.instantiate_hero("ironlocust", 0.62)
	_check("ModelLibrary instantiates the creature", creature != null)
	if creature != null:
		var cap := ModelLibrary.find_anim_player(creature)
		_check("creature ships an AnimationPlayer", cap != null)
		for role in ["idle", "walk", "hit", "death"]:
			_check("creature has a %s clip" % role, cap != null and not ModelLibrary.find_clip(cap, role).is_empty())
		var cbox := {"found": false, "box": AABB()}
		ModelLibrary._accumulate_aabb(creature, Transform3D.IDENTITY, cbox)
		_check("creature stands at the requested height (%.2f)" % cbox["box"].size.y, absf(cbox["box"].size.y - 0.62) < 0.05)
		creature.free()
	var plain := ModelLibrary.instantiate_hero("ashenborn", 0.9)
	_check("no creature model for a plain humanoid race", plain == null)
	if plain != null:
		plain.free()

	print("")
	print("%d checks, %d failed" % [_checks, _fails])
	print("RESULT: OK" if _fails == 0 else "RESULT: FAILED")
	quit(0 if _fails == 0 else 1)


func _first_albedo(cm: CharacterModel) -> Color:
	for node in cm.find_children("*", "MeshInstance3D", true, false):
		var mi := node as MeshInstance3D
		var m := mi.get_surface_override_material(0) as StandardMaterial3D
		if m != null and String(mi.name).to_lower().contains("body"):
			return m.albedo_color
	return Color.BLACK
