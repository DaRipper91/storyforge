class_name HumanoidAnimLibrary
extends RefCounted
## One procedural animation library for the shared 49-bone Quaternius humanoid skeleton
## (res://assets/models/player/*.glb and res://assets/models/humanoid/npc_*.glb).
##
## The GLBs ship NO clips, so all motion is authored here as code and baked into an
## AnimationLibrary once (see get_library). Every key is expressed as a world-axis offset
## from the bone's REST orientation, then converted to the bone's local pose using the
## real rest hierarchy of the skeleton passed in, so the bone names are the only thing
## the clips depend on (they are found by pattern, not by index).
##
## Conventions in skeleton space: +Y up, +Z is the character's front, +X is its left.
## A rotation about +X by a positive angle pitches the top of a segment toward +Z, so a
## limb hanging down swings FORWARD with a NEGATIVE angle and a knee/elbow flexes
## with the sign that moves the distal end toward the back / front respectively.

const SKELETON_PATH := "CharacterArmature/Skeleton3D"

const CLIP_IDLE := &"Idle"
const CLIP_WALK := &"Walk"
const CLIP_RUN := &"Run"
const CLIP_INTERACT := &"Interact"
const CLIP_HIT := &"Hit"
const CLIP_DEATH := &"Death"

## Clip table: length in seconds, loop flag, number of sampled intervals per clip.
## Tests assert these, so change them here only.
const IDLE_LENGTH := 3.2
const WALK_LENGTH := 0.8
const RUN_LENGTH := 0.5
const INTERACT_LENGTH := 1.0
const HIT_LENGTH := 0.5
const DEATH_LENGTH := 1.2

const CLIP_SPECS := {
	&"Idle":     {"length": IDLE_LENGTH,     "loop": true,  "steps": 16},
	&"Walk":     {"length": WALK_LENGTH,     "loop": true,  "steps": 16},
	&"Run":      {"length": RUN_LENGTH,      "loop": true,  "steps": 16},
	&"Interact": {"length": INTERACT_LENGTH, "loop": false, "steps": 14},
	&"Hit":      {"length": HIT_LENGTH,      "loop": false, "steps": 10},
	&"Death":    {"length": DEATH_LENGTH,    "loop": false, "steps": 16},
}

## Arm hang angle away from vertical in the relaxed A-pose.
const ARM_OUT_DEG := 14.0

static var _cache: AnimationLibrary = null
static var _cache_path: String = ""


## The shared library. Built on first use from `skeleton`'s rest pose and cached for the
## process; every compatible model reuses the same Animation resources.
static func get_library(skeleton: Skeleton3D, skeleton_path: String = SKELETON_PATH) -> AnimationLibrary:
	if _cache != null and _cache_path == skeleton_path:
		return _cache
	_cache = build(skeleton, skeleton_path)
	_cache_path = skeleton_path
	return _cache


static func clear_cache() -> void:
	_cache = null
	_cache_path = ""


## Builds a fresh library (no caching).
static func build(skeleton: Skeleton3D, skeleton_path: String = SKELETON_PATH) -> AnimationLibrary:
	var rig := _Rig.new(skeleton)
	var lib := AnimationLibrary.new()
	for clip_name in CLIP_SPECS:
		lib.add_animation(clip_name, _build_clip(rig, clip_name, skeleton_path))
	return lib


## True when `skeleton` has every bone the clips drive.
static func is_compatible(skeleton: Skeleton3D) -> bool:
	return _Rig.new(skeleton).complete


# ─── Rig: rest hierarchy + bone lookup by name pattern ──────────────────────────────

class _Rig extends RefCounted:
	var skeleton: Skeleton3D
	var count := 0
	var parent := PackedInt32Array()
	var g_rot: Array[Quaternion] = []   # rest orientation in skeleton space
	var g_pos: Array[Vector3] = []      # rest position in skeleton space
	var rest_pos: Array[Vector3] = []   # rest position in the parent's frame
	var bones := {}                     # key ("hips", "upperarm.l", ...) -> bone index
	var complete := true

	const WANTED := [
		["hips", ""], ["abdomen", ""], ["torso", ""], ["chest", ""], ["neck", ""], ["head", ""],
		["upperarm", "l"], ["upperarm", "r"], ["lowerarm", "l"], ["lowerarm", "r"],
		["upperleg", "l"], ["upperleg", "r"], ["lowerleg", "l"], ["lowerleg", "r"],
		["foot", "l"], ["foot", "r"],
	]

	func _init(sk: Skeleton3D) -> void:
		skeleton = sk
		count = sk.get_bone_count()
		parent.resize(count)
		for i in count:
			parent[i] = sk.get_bone_parent(i)
			var rest := sk.get_bone_rest(i)
			var q := rest.basis.orthonormalized().get_rotation_quaternion()
			rest_pos.append(rest.origin)
			if parent[i] < 0:
				g_rot.append(q)
				g_pos.append(rest.origin)
			else:
				g_rot.append(g_rot[parent[i]] * q)
				g_pos.append(g_pos[parent[i]] + g_rot[parent[i]] * rest.origin)
		for want in WANTED:
			var idx := find_bone(want[0], want[1])
			bones[key(want[0], want[1])] = idx
			if idx < 0:
				complete = false

	static func key(part: String, side: String) -> String:
		return part if side.is_empty() else part + "." + side

	## Matches names such as "UpperArm.L", "upperarm_l", "Hips" by base name + side.
	func find_bone(part: String, side: String) -> int:
		for i in count:
			var n := skeleton.get_bone_name(i).to_lower()
			var s := ""
			for suffix in [".l", "_l", ".r", "_r"]:
				if n.ends_with(suffix):
					s = suffix.substr(1)
					n = n.substr(0, n.length() - 2)
					break
			n = n.replace("_", "").replace(".", "")
			if n == part and s == side:
				return i
		return -1

	func idx(part: String, side: String = "") -> int:
		return bones.get(key(part, side), -1)

	## Direction of bone `i` toward its first child that is `child`, in skeleton space.
	func direction(i: int, child: int) -> Vector3:
		return (g_pos[child] - g_pos[i]).normalized()


# ─── Pose description ────────────────────────────────────────────────────────────────

## All angles in degrees, in the world-axis convention described at the top of the file.
class _Pose extends RefCounted:
	var hips_offset := Vector3.ZERO     # added to the Hips rest position (skeleton units)
	var hips_rot := Vector3.ZERO        # pitch (x), yaw (y), roll (z)
	var chest_rot := Vector3.ZERO       # extra rotation of Abdomen/Torso/Chest
	var head_rot := Vector3.ZERO
	var arm_swing := [0.0, 0.0]         # [L, R]; negative = forward
	var arm_bend := [0.0, 0.0]          # forearm extra; negative = forward
	var arm_out := [ARM_OUT_DEG, ARM_OUT_DEG]
	var leg_swing := [0.0, 0.0]         # [L, R]; negative = forward
	var leg_knee := [0.0, 0.0]          # positive = shin goes backward
	var foot_pitch := [0.0, 0.0]


static func _rx(deg: float) -> Quaternion:
	return Quaternion(Vector3.RIGHT, deg_to_rad(deg))


static func _euler(v: Vector3) -> Quaternion:
	return Quaternion(Vector3.UP, deg_to_rad(v.y)) * Quaternion(Vector3.BACK, deg_to_rad(v.z)) * Quaternion(Vector3.RIGHT, deg_to_rad(v.x))


static func _smooth(a: float, b: float, x: float) -> float:
	var t := clampf((x - a) / (b - a), 0.0, 1.0)
	return t * t * (3.0 - 2.0 * t)


# ─── Per-clip pose functions (u in [0, 1]) ───────────────────────────────────────────

static func _pose_idle(u: float) -> _Pose:
	var p := _Pose.new()
	var a := TAU * u
	var breath := sin(a)
	p.hips_offset = Vector3(0.0, -0.004 * (1.0 - cos(a)) * 0.5, 0.0)
	p.hips_rot = Vector3(0.0, 1.2 * sin(a), 1.0 * sin(a))
	p.chest_rot = Vector3(-1.5 * breath, -1.0 * sin(a), 0.0)
	p.head_rot = Vector3(1.0 * breath, 4.0 * sin(a + 0.8), 0.0)
	p.arm_swing = [1.5 * sin(a + 0.4), -1.5 * sin(a + 0.4)]
	p.arm_bend = [-6.0 + 1.5 * breath, -6.0 + 1.5 * breath]
	p.arm_out = [ARM_OUT_DEG + 1.5 * breath, ARM_OUT_DEG + 1.5 * breath]
	return p


static func _pose_gait(u: float, leg_amp: float, knee_amp: float, arm_amp: float, elbow: float, lean: float, bob: float, twist: float) -> _Pose:
	var p := _Pose.new()
	var a := TAU * u
	var s := sin(a)
	var c := cos(a)
	p.hips_offset = Vector3(0.0, -bob * cos(2.0 * a), 0.0)
	p.hips_rot = Vector3(lean * 0.5, twist * s, 3.0 * s)
	p.chest_rot = Vector3(lean * 0.5, -twist * 1.6 * s, -2.0 * s)
	p.head_rot = Vector3(-lean * 0.7, twist * 0.6 * s, 0.0)
	# Left and right legs are half a cycle apart; the arms oppose the legs.
	var sl := s
	var sr := -s
	var cl := c
	var cr := -c
	p.leg_swing = [-leg_amp * sl, -leg_amp * sr]
	p.leg_knee = [knee_amp * maxf(0.0, cl) + 4.0, knee_amp * maxf(0.0, cr) + 4.0]
	p.foot_pitch = [-0.2 * (p.leg_swing[0] + p.leg_knee[0]), -0.2 * (p.leg_swing[1] + p.leg_knee[1])]
	p.arm_swing = [arm_amp * sl, arm_amp * sr]
	p.arm_bend = [-elbow - 0.25 * arm_amp * maxf(0.0, -sl), -elbow - 0.25 * arm_amp * maxf(0.0, -sr)]
	p.arm_out = [ARM_OUT_DEG - 4.0, ARM_OUT_DEG - 4.0]
	return p


static func _pose_walk(u: float) -> _Pose:
	return _pose_gait(u, 22.0, 40.0, 20.0, 14.0, 3.0, 0.016, 5.0)


static func _pose_run(u: float) -> _Pose:
	var p := _pose_gait(u, 38.0, 75.0, 45.0, 75.0, 10.0, 0.032, 8.0)
	p.arm_out = [8.0, 8.0]
	return p


static func _pose_interact(u: float) -> _Pose:
	var p := _pose_idle(u * 0.5)
	var env := _smooth(0.0, 0.25, u) * (1.0 - _smooth(0.72, 1.0, u))
	var wag := sin(TAU * 2.5 * u) * env
	p.chest_rot += Vector3(8.0 * env, -10.0 * env, 0.0)
	p.head_rot += Vector3(6.0 * env, 12.0 * env, 0.0)
	# Right arm reaches forward and a little across the body; left arm shifts with it.
	p.arm_swing[1] = lerpf(p.arm_swing[1], -72.0, env)
	p.arm_bend[1] = lerpf(p.arm_bend[1], -38.0 + 10.0 * wag, env)
	p.arm_out[1] = lerpf(p.arm_out[1], 4.0, env)
	p.arm_swing[0] = lerpf(p.arm_swing[0], 10.0, env)
	p.hips_offset += Vector3(0.0, -0.01 * env, 0.0)
	return p


static func _pose_hit(u: float) -> _Pose:
	var p := _pose_idle(0.0)
	# Fast flinch, slower recovery.
	var env := sin(PI * pow(u, 0.55))
	p.hips_rot += Vector3(-6.0 * env, 0.0, 4.0 * env)
	p.hips_offset += Vector3(0.0, -0.02 * env, 0.03 * env)
	p.chest_rot += Vector3(-10.0 * env, 10.0 * env, 0.0)
	p.head_rot += Vector3(-12.0 * env, -8.0 * env, 0.0)
	p.arm_swing = [lerpf(p.arm_swing[0], 18.0, env), lerpf(p.arm_swing[1], 18.0, env)]
	p.arm_out = [lerpf(p.arm_out[0], 38.0, env), lerpf(p.arm_out[1], 38.0, env)]
	p.arm_bend = [lerpf(p.arm_bend[0], -20.0, env), lerpf(p.arm_bend[1], -20.0, env)]
	p.leg_swing = [8.0 * env, -6.0 * env]
	p.leg_knee = [12.0 * env, 8.0 * env]
	return p


static func _pose_death(u: float) -> _Pose:
	var p := _pose_idle(0.0)
	# Stagger back, then topple over backwards and settle flat. `fall` eases in, `settle`
	# adds a small bounce when the body lands.
	var stagger := _smooth(0.0, 0.25, u)
	var fall := _smooth(0.15, 0.85, u)
	var land := _smooth(0.8, 1.0, u)
	var bounce := sin(PI * _smooth(0.78, 0.95, u)) * 0.012
	p.hips_rot = Vector3(-90.0 * fall - 6.0 * stagger, 0.0, 14.0 * fall)
	p.hips_offset = Vector3(0.0, -0.735 * fall + bounce, -0.05 * stagger)
	p.chest_rot = Vector3(-10.0 * stagger + 6.0 * land, 0.0, 0.0)
	p.head_rot = Vector3(-10.0 * stagger + 8.0 * land, 14.0 * land, 0.0)
	p.arm_swing = [lerpf(0.0, 25.0, fall), lerpf(0.0, -35.0, fall)]
	p.arm_out = [lerpf(ARM_OUT_DEG, 62.0, fall), lerpf(ARM_OUT_DEG, 48.0, fall)]
	p.arm_bend = [lerpf(-6.0, -25.0, fall), lerpf(-6.0, -40.0, fall)]
	p.leg_swing = [lerpf(0.0, -8.0, fall), lerpf(0.0, 12.0, fall)]
	p.leg_knee = [lerpf(0.0, 28.0, fall), lerpf(0.0, 8.0, fall)]
	return p


static func _pose_for(clip_name: StringName, u: float) -> _Pose:
	match clip_name:
		CLIP_WALK: return _pose_walk(u)
		CLIP_RUN: return _pose_run(u)
		CLIP_INTERACT: return _pose_interact(u)
		CLIP_HIT: return _pose_hit(u)
		CLIP_DEATH: return _pose_death(u)
	return _pose_idle(u)


# ─── Pose -> per-bone world offsets -> local rotations ───────────────────────────────

## Bone index -> absolute world offset W: the bone's final orientation is W * rest_global.
static func _world_offsets(rig: _Rig, p: _Pose) -> Dictionary:
	var w := {}
	var hips_w := _euler(p.hips_rot)
	w[rig.idx("hips")] = hips_w
	var chest_w := hips_w * _euler(p.chest_rot)
	w[rig.idx("abdomen")] = hips_w * _euler(p.chest_rot * 0.35)
	w[rig.idx("torso")] = hips_w * _euler(p.chest_rot * 0.7)
	w[rig.idx("chest")] = chest_w
	var head_w := chest_w * _euler(p.head_rot)
	w[rig.idx("neck")] = chest_w * _euler(p.head_rot * 0.4)
	w[rig.idx("head")] = head_w
	for side_i in 2:
		var side := "l" if side_i == 0 else "r"
		var sign_x := 1.0 if side_i == 0 else -1.0   # +X is the character's left
		var ua := rig.idx("upperarm", side)
		var la := rig.idx("lowerarm", side)
		if ua >= 0 and la >= 0:
			var out := deg_to_rad(p.arm_out[side_i])
			var hang := Vector3(sign_x * sin(out), -cos(out), 0.0)
			var lower := Quaternion(rig.direction(ua, la), hang)
			w[ua] = chest_w * _rx(p.arm_swing[side_i]) * lower
			w[la] = chest_w * _rx(p.arm_swing[side_i] + p.arm_bend[side_i]) * lower
		var ul := rig.idx("upperleg", side)
		var ll := rig.idx("lowerleg", side)
		var ft := rig.idx("foot", side)
		if ul >= 0:
			w[ul] = hips_w * _rx(p.leg_swing[side_i])
		if ll >= 0:
			w[ll] = hips_w * _rx(p.leg_swing[side_i] + p.leg_knee[side_i])
		if ft >= 0:
			w[ft] = _rx(p.foot_pitch[side_i])
	w.erase(-1)
	return w


static func _build_clip(rig: _Rig, clip_name: StringName, skeleton_path: String) -> Animation:
	var spec: Dictionary = CLIP_SPECS[clip_name]
	var length: float = spec["length"]
	var steps: int = spec["steps"]
	var looping: bool = spec["loop"]

	var anim := Animation.new()
	anim.length = length
	anim.loop_mode = Animation.LOOP_LINEAR if looping else Animation.LOOP_NONE

	var tracks := {}   # bone index -> track index
	var pos_track := anim.add_track(Animation.TYPE_POSITION_3D)
	var hips := rig.idx("hips")
	anim.track_set_path(pos_track, NodePath("%s:%s" % [skeleton_path, rig.skeleton.get_bone_name(hips)]))
	anim.track_set_interpolation_type(pos_track, Animation.INTERPOLATION_LINEAR)

	for k in steps + 1:
		var u := float(k) / float(steps)
		# A looping clip's last key repeats its first so the wrap is seamless.
		var pose := _pose_for(clip_name, 0.0 if (looping and k == steps) else u)
		var offsets := _world_offsets(rig, pose)
		var time := u * length

		anim.position_track_insert_key(pos_track, time, rig.rest_pos[hips] + pose.hips_offset)

		# Resolve the offset every bone ends up with, unanimated bones inheriting their parent's.
		var resolved: Array[Quaternion] = []
		resolved.resize(rig.count)
		for i in rig.count:
			var parent_w := Quaternion.IDENTITY if rig.parent[i] < 0 else resolved[rig.parent[i]]
			resolved[i] = offsets[i] if offsets.has(i) else parent_w
		for i in offsets:
			var local: Quaternion
			if rig.parent[i] < 0:
				local = resolved[i] * rig.g_rot[i]
			else:
				var pw := resolved[rig.parent[i]]
				local = rig.g_rot[rig.parent[i]].inverse() * pw.inverse() * resolved[i] * rig.g_rot[i]
			if not tracks.has(i):
				var t := anim.add_track(Animation.TYPE_ROTATION_3D)
				anim.track_set_path(t, NodePath("%s:%s" % [skeleton_path, rig.skeleton.get_bone_name(i)]))
				anim.track_set_interpolation_type(t, Animation.INTERPOLATION_LINEAR)
				tracks[i] = t
			anim.rotation_track_insert_key(tracks[i], time, local.normalized())
	return anim
