class_name CharacterModel
extends Node3D
## A playable species rendered as one of the five rigged Quaternius bases (one per
## species group), animated by the shared HumanoidAnimLibrary and made distinct per race
## by tint, emissive accent and body proportions. No extra meshes are added.
##
## Layout:  CharacterModel -> Pivot (scale/ground/turn) -> <GLB root> -> CharacterArmature
##          -> Skeleton3D -> meshes, plus ONE AnimationPlayer parented to the GLB root.
## Forward is -Z, like every other Godot body (RaceMini's looking_at() code relies on it);
## the glTF front (+Z) is turned by the Pivot.

const _Races := preload("res://scripts/core/data/races_data.gd")

const BASE_DIR := "res://assets/models/player/"
const GROUP_BASES := {
	"Cosmic": "cosmic",
	"Primal": "primal",
	"Eldritch": "eldritch",
	"Mechanical": "mechanical",
	"Humanoid": "humanoid",
}
const NEUTRAL_ID := "humanoid_default"

## Standing height in world units: same as ModelLibrary.DEFAULT_HEIGHT, so a player model
## matches every other GLB token on the board (a cell is 1.0).
const DEFAULT_HEIGHT := 0.9

## Group glow colours; mirrors Tabletop.RACE_COLORS (which lives in a 2000-line scene script).
const GROUP_ACCENT := {
	"Cosmic":     Color(0.2, 0.4, 1.0),
	"Primal":     Color(0.1, 0.8, 0.2),
	"Eldritch":   Color(0.7, 0.1, 0.9),
	"Mechanical": Color(1.0, 0.5, 0.1),
	"Humanoid":   Color(1.0, 0.85, 0.6),
}
## Groups whose bodies carry an emissive accent.
const EMISSIVE_GROUPS := ["Cosmic", "Eldritch", "Mechanical"]

## Strength of the race colour on the base texture (0 = untouched, 1 = flat colour).
const TINT_STRENGTH := 0.85
## How strongly each body part takes the race colour (clothes carry it, skin and shoes less).
const PART_TINT := {"head": 0.55, "body": 1.0, "legs": 0.8, "feet": 0.45, "other": 0.7}
const EMISSION_BODY := 0.22
const EMISSION_HEAD := 1.1
## Primal/Humanoid bodies get a faint self-light in their race colour so dark armour stays
## readable in the dark, fogged rooms.
const BASE_LIFT := 0.16
const HIGHLIGHT_BOOST := 0.35

## Per-race proportions: x = height multiplier, y = girth (width/depth) multiplier.
const RACE_BUILD := {
	"voidwraith": Vector2(1.08, 0.85), "nullshade": Vector2(1.15, 0.70),
	"ironlocust": Vector2(0.95, 1.20), "embervein": Vector2(1.12, 1.20),
	"riftwalker": Vector2(1.05, 0.90),
	"solarlord": Vector2(1.12, 1.10), "thornmimic": Vector2(1.00, 0.85),
	"cinderkin": Vector2(0.85, 1.10), "deeptyrant": Vector2(1.25, 1.25),
	"grimcrow": Vector2(0.92, 0.85),
	"bloodweaver": Vector2(1.05, 0.85), "dreamhusk": Vector2(1.05, 0.80),
	"bonedrifter": Vector2(1.15, 0.70), "mindspider": Vector2(0.90, 1.10),
	"chaosling": Vector2(0.78, 0.95),
	"ironveil": Vector2(1.15, 1.20), "forgespawn": Vector2(1.20, 1.30),
	"cinderplate": Vector2(0.95, 1.30), "hexgear": Vector2(0.90, 1.00),
	"wirewraith": Vector2(1.10, 0.70),
	"ashenborn": Vector2(1.00, 1.00), "hollowsong": Vector2(1.05, 0.85),
	"veilborn": Vector2(1.00, 0.90), "thornweft": Vector2(1.00, 1.00),
	"ashcrown": Vector2(1.05, 1.00), "ironfast": Vector2(0.85, 1.25),
	"coreborn": Vector2(1.00, 1.05), "warpbred": Vector2(1.00, 1.00),
	"splitblood": Vector2(1.02, 1.00), "duskweft": Vector2(0.97, 0.90),
	"glitchkin": Vector2(0.80, 0.90), "fractureline": Vector2(1.00, 1.00),
	"emberpact": Vector2(1.03, 1.00), "fallenlight": Vector2(1.08, 0.95),
	"scaleworn": Vector2(1.05, 1.15),
}

## Clips that play once and then fall back to Idle/Walk.
const ONE_SHOTS: Array[StringName] = [
	HumanoidAnimLibrary.CLIP_INTERACT,
	HumanoidAnimLibrary.CLIP_HIT,
]

var race_id: String = ""
var group: String = ""
var body_height: float = DEFAULT_HEIGHT

## Multiplicative colour on the base texture; assigning re-applies the materials.
var tint: Color = Color.WHITE:
	set(value):
		tint = value
		_apply_colours()
## Emissive accent colour (Cosmic/Eldritch/Mechanical only); assigning re-applies.
var accent: Color = Color.WHITE:
	set(value):
		accent = value
		_apply_colours()
## Brighter emission while selected / hovered.
var highlighted: bool = false:
	set(value):
		highlighted = value
		_apply_colours()

var _pivot: Node3D = null
var _root: Node3D = null
var _skeleton: Skeleton3D = null
var _anim: AnimationPlayer = null
var _walking := false
var _dead := false
var _emissive := false
var _mats: Array[StandardMaterial3D] = []
var _base_albedo: Array[Color] = []
var _is_head: Array[bool] = []
var _part_weight := PackedFloat32Array()
var _body_aabb := AABB()

## base glb path -> Array of {name, mesh, skin}: the mirrored halves, built once per base.
static var _mirror_cache := {}


## Normalises "Void Wraith"/"voidwraith" style ids.
static func normalise_id(id: String) -> String:
	return id.strip_edges().to_lower().replace(" ", "_").replace("-", "_")


static func is_known_race(id: String) -> bool:
	id = normalise_id(id)
	return id == NEUTRAL_ID or _Races.RACES.has(id)


static func group_of(id: String) -> String:
	id = normalise_id(id)
	if _Races.RACES.has(id):
		return _Races.RACES[id].get("group", "Humanoid")
	return "Humanoid"


static func base_path(grp: String) -> String:
	return BASE_DIR + GROUP_BASES.get(grp, "humanoid") + ".glb"


## Default (tint, accent) for a race, from the existing colour tables.
static func colours_for(id: String) -> Dictionary:
	id = normalise_id(id)
	var grp := group_of(id)
	var group_glow: Color = GROUP_ACCENT.get(grp, Color.WHITE)
	if id == NEUTRAL_ID or not RaceMini.RACE_COLORS.has(id):
		return {"tint": Color.WHITE, "accent": group_glow}
	var race_col: Color = RaceMini.RACE_COLORS[id]
	return {"tint": race_col, "accent": group_glow.lerp(race_col, 0.45)}


## Builds the model. opts: height (float), tint (Color), accent (Color), emissive (bool).
## Returns false (and leaves the node empty) if the base GLB cannot be loaded.
func setup(new_race_id: String, opts: Dictionary = {}) -> bool:
	_clear()
	race_id = normalise_id(new_race_id)
	group = group_of(race_id)
	var scene := load(base_path(group)) as PackedScene
	if scene == null:
		return false
	_root = scene.instantiate() as Node3D
	if _root == null:
		return false
	_skeleton = _find_skeleton(_root)
	if _skeleton == null or not HumanoidAnimLibrary.is_compatible(_skeleton):
		_root.free()
		_root = null
		_skeleton = null
		return false

	_add_mirrored_halves(base_path(group))

	_pivot = Node3D.new()
	_pivot.name = "Pivot"
	_pivot.rotation.y = PI
	add_child(_pivot)
	_pivot.add_child(_root)

	var build: Vector2 = RACE_BUILD.get(race_id, Vector2.ONE)
	body_height = float(opts.get("height", DEFAULT_HEIGHT)) * build.x
	_ground_and_scale(build.y)
	_collect_materials()

	_anim = AnimationPlayer.new()
	_anim.name = "AnimationPlayer"
	_root.add_child(_anim)
	_anim.add_animation_library(&"", HumanoidAnimLibrary.get_library(_skeleton))
	_anim.playback_default_blend_time = 0.15
	_anim.animation_finished.connect(_on_animation_finished)

	var cols := colours_for(race_id)
	_emissive = bool(opts.get("emissive", group in EMISSIVE_GROUPS))
	tint = opts.get("tint", cols["tint"])
	accent = opts.get("accent", cols["accent"])
	_walking = false
	_dead = false
	_anim.play(HumanoidAnimLibrary.CLIP_IDLE)
	return true


func is_ready() -> bool:
	return _anim != null


func get_animation_player() -> AnimationPlayer:
	return _anim


func get_skeleton() -> Skeleton3D:
	return _skeleton


## Bounding box of the standing body in this node's local space (feet at y = 0). Width and
## depth are estimated from the proportions: the raw mesh box is a T-pose and far too wide.
func get_body_aabb() -> AABB:
	return _body_aabb


func current_clip() -> StringName:
	return _anim.current_animation if _anim else &""


## Plays a clip by name (HumanoidAnimLibrary.CLIP_*). One-shots restart every call.
func play(clip: StringName) -> void:
	if _anim == null or not _anim.has_animation(clip):
		return
	if clip == HumanoidAnimLibrary.CLIP_DEATH:
		_dead = true
	elif _dead and clip != HumanoidAnimLibrary.CLIP_IDLE:
		return
	elif clip == HumanoidAnimLibrary.CLIP_IDLE:
		_dead = false
	if _anim.current_animation == clip and _anim.is_playing() and not clip in ONE_SHOTS:
		return
	_anim.play(clip)


## Walk while true, Idle while false. Cheap to call every frame.
func set_walking(walking: bool) -> void:
	_walking = walking
	if _anim == null or _dead:
		return
	if _anim.current_animation in ONE_SHOTS and _anim.is_playing():
		return
	var want := HumanoidAnimLibrary.CLIP_WALK if walking else HumanoidAnimLibrary.CLIP_IDLE
	if _anim.current_animation != want or not _anim.is_playing():
		_anim.play(want)


func is_walking() -> bool:
	return _walking


## Turns the body to face `dir` (a world-space direction on the ground plane).
func face_direction(dir: Vector3) -> void:
	dir.y = 0.0
	if dir.length_squared() < 0.0001:
		return
	global_basis = Basis.looking_at(dir.normalized(), Vector3.UP)


# ─── Internals ───────────────────────────────────────────────────────────────────────

func _clear() -> void:
	if _anim and _anim.animation_finished.is_connected(_on_animation_finished):
		_anim.animation_finished.disconnect(_on_animation_finished)
	if _pivot:
		remove_child(_pivot)
		_pivot.free()
	_pivot = null
	_root = null
	_skeleton = null
	_anim = null
	_mats.clear()
	_base_albedo.clear()
	_is_head.clear()
	_part_weight.clear()


func _on_animation_finished(clip: StringName) -> void:
	if clip in ONE_SHOTS:
		set_walking(_walking)


## The shipped Quaternius GLBs contain only the LEFT leg and foot (the export dropped the
## mirror modifier), so a model has one leg. This adds the missing right halves: each
## one-sided skinned mesh is mirrored in X, winding flipped, and re-bound to the opposite
## limb's bones. Symmetric meshes (body, head) are left alone. Cached per base GLB.
func _add_mirrored_halves(key: String) -> void:
	if not _mirror_cache.has(key):
		_mirror_cache[key] = _build_mirrors(_skeleton)
	for entry in _mirror_cache[key]:
		var mi := MeshInstance3D.new()
		mi.name = String(entry["name"]) + "_Mirrored"
		mi.mesh = entry["mesh"]
		mi.skin = entry["skin"]
		_skeleton.add_child(mi)


static func _mirror_bone_name(bone_name: String) -> String:
	for pair in [[".L", ".R"], [".R", ".L"], ["_L", "_R"], ["_R", "_L"], ["_l", "_r"], ["_r", "_l"]]:
		if bone_name.ends_with(pair[0]):
			return bone_name.substr(0, bone_name.length() - 2) + pair[1]
	return bone_name


static func _build_mirrors(skeleton: Skeleton3D) -> Array:
	var out := []
	for node in skeleton.get_children():
		var mi := node as MeshInstance3D
		if mi == null or mi.mesh == null or mi.skin == null:
			continue
		var box := mi.get_aabb()
		if absf(box.get_center().x) < 0.03:
			continue   # already symmetric
		var skin := Skin.new()
		for i in mi.skin.get_bind_count():
			var bone_name := mi.skin.get_bind_name(i)
			if bone_name.is_empty():
				bone_name = skeleton.get_bone_name(mi.skin.get_bind_bone(i))
			var mirrored := _mirror_bone_name(bone_name)
			var bone := skeleton.find_bone(mirrored)
			var pose := Transform3D.IDENTITY
			if bone >= 0:
				pose = skeleton.get_bone_global_rest(bone).affine_inverse()
			skin.add_named_bind(mirrored, pose)
		var mesh := ArrayMesh.new()
		var src := mi.mesh
		for surface in src.get_surface_count():
			var arrays := src.surface_get_arrays(surface)
			var verts: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			for v in verts.size():
				verts[v].x = -verts[v].x
			arrays[Mesh.ARRAY_VERTEX] = verts
			if arrays[Mesh.ARRAY_NORMAL] != null:
				var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
				for n in normals.size():
					normals[n].x = -normals[n].x
				arrays[Mesh.ARRAY_NORMAL] = normals
			if arrays[Mesh.ARRAY_TANGENT] != null:
				var tangents: PackedFloat32Array = arrays[Mesh.ARRAY_TANGENT]
				for t in range(0, tangents.size(), 4):
					tangents[t] = -tangents[t]
					tangents[t + 3] = -tangents[t + 3]
				arrays[Mesh.ARRAY_TANGENT] = tangents
			if arrays[Mesh.ARRAY_INDEX] != null:
				var idx: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
				for t in range(0, idx.size() - 2, 3):
					var tmp := idx[t + 1]
					idx[t + 1] = idx[t + 2]
					idx[t + 2] = tmp
				arrays[Mesh.ARRAY_INDEX] = idx
			var flags: int = src.surface_get_format(surface) & Mesh.ARRAY_FLAG_USE_8_BONE_WEIGHTS
			mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays, [], {}, flags)
			mesh.surface_set_material(surface, src.surface_get_material(surface))
		out.append({"name": mi.name, "mesh": mesh, "skin": skin})
	return out


static func _find_skeleton(node: Node) -> Skeleton3D:
	if node is Skeleton3D:
		return node as Skeleton3D
	for child in node.get_children():
		var found := _find_skeleton(child)
		if found:
			return found
	return null


func _ground_and_scale(girth: float) -> void:
	var box := {"found": false, "box": AABB()}
	_accumulate(_root, Transform3D.IDENTITY, box)
	var raw: AABB = box["box"]
	var s := body_height / maxf(raw.size.y, 0.001)
	_pivot.scale = Vector3(s * girth, s, s * girth)
	# The pivot is turned by PI about Y, so only y needs offsetting; x/z stay centred.
	_pivot.position = Vector3(0.0, -raw.position.y * s, 0.0)
	var half := body_height * 0.17 * girth
	_body_aabb = AABB(Vector3(-half, 0.0, -half), Vector3(half * 2.0, body_height, half * 2.0))


static func _accumulate(node: Node, parent_xform: Transform3D, acc: Dictionary) -> void:
	var xform := parent_xform
	if node is Node3D:
		xform = parent_xform * (node as Node3D).transform
	if node is MeshInstance3D:
		var mesh_box: AABB = xform * (node as MeshInstance3D).get_aabb()
		if acc["found"]:
			acc["box"] = (acc["box"] as AABB).merge(mesh_box)
		else:
			acc["box"] = mesh_box
			acc["found"] = true
	for child in node.get_children():
		_accumulate(child, xform, acc)


## Gives this instance its own copy of every surface material, so tinting one character
## never leaks into the shared PackedScene or another character.
func _collect_materials() -> void:
	for node in _root.find_children("*", "MeshInstance3D", true, false):
		var mi := node as MeshInstance3D
		if mi.mesh == null:
			continue
		var lname := String(mi.name).to_lower()
		var head := lname.contains("head")
		var part := "other"
		for candidate in ["head", "body", "feet"]:
			if lname.contains(candidate):
				part = candidate
		if lname.contains("legs") or lname.contains("pants"):
			part = "legs"
		for surface in mi.mesh.get_surface_count():
			var src := mi.get_active_material(surface) as StandardMaterial3D
			if src == null:
				continue
			var own := src.duplicate() as StandardMaterial3D
			mi.set_surface_override_material(surface, own)
			_mats.append(own)
			_base_albedo.append(own.albedo_color)
			_is_head.append(head)
			_part_weight.append(PART_TINT[part])


func _apply_colours() -> void:
	if _mats.is_empty():
		return
	var full := Color.WHITE.lerp(_readable(tint), TINT_STRENGTH)
	var boost := HIGHLIGHT_BOOST if highlighted else 0.0
	for i in _mats.size():
		var m := _mats[i]
		m.albedo_color = _base_albedo[i] * Color.WHITE.lerp(full, _part_weight[i])
		if _emissive:
			m.emission_enabled = true
			m.emission = accent
			m.emission_energy_multiplier = (EMISSION_HEAD if _is_head[i] else EMISSION_BODY) + boost
		else:
			m.emission_enabled = true
			m.emission = _readable(tint)
			m.emission_energy_multiplier = BASE_LIFT + boost


## Lifts near-black race colours so the model never turns into a silhouette.
static func _readable(c: Color) -> Color:
	var lum := c.get_luminance()
	if lum >= 0.28:
		return c
	return c.lerp(Color(0.5, 0.5, 0.55), (0.28 - lum) / 0.28 * 0.8)
