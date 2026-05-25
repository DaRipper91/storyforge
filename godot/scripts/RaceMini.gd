extends Node3D

const RACE_COLORS: Dictionary = {
	"Cosmic":     Color(0.2, 0.4, 1.0),
	"Primal":     Color(0.1, 0.8, 0.2),
	"Eldritch":   Color(0.7, 0.1, 0.9),
	"Mechanical": Color(1.0, 0.5, 0.1),
	"Humanoid":   Color(1.0, 0.85, 0.6),
}

# Skin tones per race (base albedo for organic skin)
const RACE_SKIN: Dictionary = {
	"ashenborn":    Color(0.12, 0.10, 0.09),  # charcoal
	"hollowsong":   Color(0.82, 0.78, 0.72),  # pale silver-white
	"veilborn":     Color(0.18, 0.16, 0.22),  # deep violet-grey
	"thornweft":    Color(0.32, 0.42, 0.28),  # bark-green
	"ashcrown":     Color(0.88, 0.86, 0.90),  # near-translucent pale
	"ironfast":     Color(0.48, 0.38, 0.30),  # ruddy earth tone
	"coreborn":     Color(0.38, 0.30, 0.42),  # deep stone-purple
	"warpbred":     Color(0.45, 0.30, 0.35),  # bruised flesh
	"splitblood":   Color(0.55, 0.35, 0.30),  # warm mixed
	"duskweft":     Color(0.58, 0.52, 0.62),  # twilight grey-lavender
	"glitchkin":    Color(0.30, 0.55, 0.50),  # teal-grey
	"fractureline": Color(0.40, 0.35, 0.45),  # cracked stone
	"emberpact":    Color(0.52, 0.32, 0.22),  # ember-warmed brown
	"fallenlight":  Color(0.78, 0.76, 0.72),  # faded ivory
	"scaleworn":    Color(0.30, 0.42, 0.36),  # scaled green-grey
	"solarlord":    Color(0.90, 0.80, 0.55),  # golden avian
	"grimcrow":     Color(0.10, 0.10, 0.12),  # obsidian
	"thornmimic":   Color(0.28, 0.38, 0.22),  # dark bark
	"cinderkin":    Color(0.95, 0.70, 0.25),  # hot crystal
	"deeptyrant":   Color(0.22, 0.28, 0.42),  # deep-sea blue
	"bloodweaver":  Color(0.20, 0.12, 0.14),  # pale vampire
	"dreamhusk":    Color(0.68, 0.65, 0.60),  # spore beige
	"bonedrifter":  Color(0.80, 0.78, 0.72),  # bleached bone
	"mindspider":   Color(0.55, 0.60, 0.70),  # translucent blue-grey
	"chaosling":    Color(0.50, 0.30, 0.55),  # chaotic purple
}

const RACE_GROUP: Dictionary = {
	"voidwraith":   "Cosmic",    "nullshade":    "Cosmic",    "ironlocust":   "Cosmic",
	"embervein":    "Cosmic",    "riftwalker":   "Cosmic",
	"solarlord":    "Primal",    "thornmimic":   "Primal",    "cinderkin":    "Primal",
	"deeptyrant":   "Primal",    "grimcrow":     "Primal",
	"bloodweaver":  "Eldritch",  "dreamhusk":    "Eldritch",  "bonedrifter":  "Eldritch",
	"mindspider":   "Eldritch",  "chaosling":    "Eldritch",
	"ironveil":     "Mechanical","forgespawn":   "Mechanical","cinderplate":  "Mechanical",
	"hexgear":      "Mechanical","wirewraith":   "Mechanical",
	"ashenborn":    "Humanoid",  "hollowsong":   "Humanoid",  "veilborn":     "Humanoid",
	"thornweft":    "Humanoid",  "ashcrown":     "Humanoid",  "ironfast":     "Humanoid",
	"coreborn":     "Humanoid",  "warpbred":     "Humanoid",  "splitblood":   "Humanoid",
	"duskweft":     "Humanoid",  "glitchkin":    "Humanoid",  "fractureline": "Humanoid",
	"emberpact":    "Humanoid",  "fallenlight":  "Humanoid",  "scaleworn":    "Humanoid",
}

@onready var body: MeshInstance3D = $Body

const MODEL_DIR   := "res://assets/models/player/"
const RACE_GROUPS := {
	"voidwraith": "cosmic",   "nullshade":   "cosmic",   "ironlocust":  "cosmic",
	"embervein":  "cosmic",   "riftwalker":  "cosmic",
	"solarlord":  "primal",   "thornmimic":  "primal",   "cinderkin":   "primal",
	"deeptyrant": "primal",   "grimcrow":    "primal",
	"bloodweaver":"eldritch", "dreamhusk":   "eldritch", "bonedrifter": "eldritch",
	"mindspider": "eldritch", "chaosling":   "eldritch",
	"ironveil":   "mechanical","forgespawn": "mechanical","cinderplate":"mechanical",
	"hexgear":    "mechanical","wirewraith": "mechanical",
}
const ANIM_IDLE   := ["Idle", "Idle_A", "Standing", "idle"]
const ANIM_WALK   := ["Walking", "Walk", "Walk_A",  "walking"]
const ANIM_ATTACK := ["Attack",  "Slash","Attack_A","attack"]

var _color:          Color  = Color.WHITE
var _skin_color:     Color  = Color(0.6, 0.5, 0.45)
var _group:          String = "Humanoid"
var _race_id:        String = ""
var _selected:       bool   = false
var _selection_ring: MeshInstance3D = null
var _name_label:     Label3D        = null
var _bob_time:       float = 0.0
var _ring_pulse:     float = 0.0

var _anim_player:  AnimationPlayer = null
var _has_model:    bool = false


func _process(delta: float) -> void:
	if _selected and _selection_ring:
		_ring_pulse += delta * 3.0
		var mat := _selection_ring.material_override as StandardMaterial3D
		if mat:
			mat.emission_energy_multiplier = 0.8 + (sin(_ring_pulse) + 1.0) * 0.75

	if not _has_model:
		if not body:
			return
		body.rotate_y(delta * 0.4)
		_bob_time += delta
		body.position.y = 0.4 + sin(_bob_time * 1.2) * 0.012


# ── Animation API ────────────────────────────────────────────────────

func play_idle() -> void:
	_play(ANIM_IDLE)

func play_walk() -> void:
	_play(ANIM_WALK)

func play_attack() -> void:
	_play(ANIM_ATTACK)
	if _anim_player:
		var n := _resolve(ANIM_ATTACK)
		if not n.is_empty():
			var anim := _anim_player.get_animation(n)
			if anim:
				get_tree().create_timer(anim.get_length()).timeout.connect(play_idle)

func _resolve(names: Array) -> String:
	if not _anim_player:
		return ""
	for n in names:
		if _anim_player.has_animation(n):
			return n
	return ""

func _play(names: Array) -> void:
	if not _anim_player:
		return
	var n := _resolve(names)
	if n.is_empty() or _anim_player.current_animation == n:
		return
	_anim_player.play(n)


# ─── Public API ──────────────────────────────────────────────────────

func setup(race_id: String, char_name: String = "") -> void:
	var b: MeshInstance3D = body if body else get_node_or_null("Body") as MeshInstance3D
	if not b:
		return
	body = b

	_race_id    = race_id
	_group      = RACE_GROUP.get(race_id, "Humanoid")
	_color      = RACE_COLORS.get(_group, Color.WHITE)
	_skin_color = RACE_SKIN.get(race_id, Color(0.60, 0.50, 0.44))

	for child in b.get_children():
		child.queue_free()
	if _name_label and is_instance_valid(_name_label):
		_name_label.queue_free()
		_name_label = null
	if _selection_ring and is_instance_valid(_selection_ring):
		_selection_ring.queue_free()
		_selection_ring = null

	# Try loading a real .glb model first
	if _try_load_model(race_id):
		_has_model = true
		_add_name_label(char_name if char_name != "" else race_id)
		_add_selection_ring()
		return

	# Invisible placeholder body — all geometry added as children
	b.mesh = SphereMesh.new()
	(b.mesh as SphereMesh).radius = 0.001
	b.material_override = StandardMaterial3D.new()

	match _group:
		"Cosmic":     _setup_cosmic(b)
		"Primal":     _setup_primal(b)
		"Eldritch":   _setup_eldritch(b)
		"Mechanical": _setup_mechanical(b)
		"Humanoid":   _setup_humanoid(b)

	_apply_race_overrides(b)
	_add_plinth(b)
	_add_portrait(b, race_id)
	_add_name_label(char_name if char_name != "" else race_id)
	_add_selection_ring()


func _try_load_model(race_id: String) -> bool:
	# Try exact race file first, then group fallback
	var group_key: String = RACE_GROUPS.get(race_id, "humanoid")
	var candidates: Array[String] = [
		MODEL_DIR + race_id + ".glb",
		MODEL_DIR + group_key + ".glb",
	]
	for path in candidates:
		if ResourceLoader.exists(path):
			var scene := load(path) as PackedScene
			if not scene:
				continue
			var inst := scene.instantiate()
			inst.scale = Vector3(0.52, 0.52, 0.52)
			add_child(inst)
			body.visible = false   # hide placeholder body
			_anim_player = _find_anim_player(inst)
			play_idle()
			return true
	return false

func _find_anim_player(node: Node) -> AnimationPlayer:
	if node is AnimationPlayer:
		return node as AnimationPlayer
	for child in node.get_children():
		var found := _find_anim_player(child)
		if found:
			return found
	return null


func set_char_name(n: String) -> void:
	if _name_label:
		_name_label.text = _fmt_name(n)


func select() -> void:
	_selected = true
	if _selection_ring:
		_selection_ring.visible = true
		_ring_pulse = 0.0


func deselect() -> void:
	_selected = false
	if _selection_ring:
		_selection_ring.visible = false


# ─── Material factory ────────────────────────────────────────────────

func _skin_mat(tint: Color = Color.WHITE) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	var c := _skin_color * tint
	mat.albedo_color = c
	mat.roughness    = 0.88
	mat.metallic     = 0.0
	mat.subsurf_scatter_enabled  = true
	mat.subsurf_scatter_strength = 0.25
	mat.subsurf_scatter_skin_mode = true
	return mat


func _cloth_mat(color: Color, roughness: float = 0.92) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.roughness    = roughness
	mat.metallic     = 0.0
	return mat


func _armor_mat(color: Color, metallic: float = 0.75, roughness: float = 0.32) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.metallic     = metallic
	mat.roughness    = roughness
	mat.emission_enabled          = true
	mat.emission                  = _color * 0.12
	mat.emission_energy_multiplier = 0.3
	return mat


func _glow_mat(color: Color, energy: float = 2.5) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.albedo_color              = color.lightened(0.3)
	mat.emission_enabled          = true
	mat.emission                  = color
	mat.emission_energy_multiplier = energy
	mat.roughness = 0.2
	mat.metallic  = 0.0
	return mat


func _organic_mat(color: Color, roughness: float = 0.82) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.albedo_color             = color
	mat.roughness                = roughness
	mat.metallic                 = 0.0
	mat.subsurf_scatter_enabled  = true
	mat.subsurf_scatter_strength = 0.18
	return mat


func _make_mat(color: Color, energy: float = 1.2, metallic: float = 0.0, roughness: float = 0.75) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.albedo_color              = color.darkened(0.45)
	mat.emission_enabled          = true
	mat.emission                  = color
	mat.emission_energy_multiplier = energy
	mat.metallic                  = metallic
	mat.roughness                 = roughness
	return mat


# ─── Mesh builder helper ─────────────────────────────────────────────

func _add_mi(parent: Node3D, mesh: Mesh, pos: Vector3,
		mat: StandardMaterial3D = null, rot: Vector3 = Vector3.ZERO,
		scale_v: Vector3 = Vector3.ONE) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.mesh     = mesh
	mi.position = pos
	if rot   != Vector3.ZERO: mi.rotation = rot
	if scale_v != Vector3.ONE: mi.scale  = scale_v
	mi.material_override = mat if mat else body.material_override
	parent.add_child(mi)
	return mi


func _capsule(r: float, h: float) -> CapsuleMesh:
	var m := CapsuleMesh.new(); m.radius = r; m.height = h; return m

func _sphere(r: float) -> SphereMesh:
	var m := SphereMesh.new(); m.radius = r; m.height = r * 2.0; return m

func _box(x: float, y: float, z: float) -> BoxMesh:
	var m := BoxMesh.new(); m.size = Vector3(x, y, z); return m

func _cyl(r: float, h: float, segs: int = 12) -> CylinderMesh:
	var m := CylinderMesh.new()
	m.top_radius = r; m.bottom_radius = r; m.height = h
	m.radial_segments = segs; return m

func _prism(x: float, y: float, z: float) -> PrismMesh:
	var m := PrismMesh.new(); m.size = Vector3(x, y, z); return m


# ─── Humanoid figure (full anatomical detail) ────────────────────────
#
# Coordinate origin = body node (Y=0.4 world). All positions local to body.
# Figure stands ~0.9 units tall, feet near Y=-0.55, crown near Y=0.55

func _setup_humanoid(b: MeshInstance3D) -> void:
	var sk  := _skin_mat()
	var cl  := _cloth_mat(_color.darkened(0.35))
	var arm := _armor_mat(_color.darkened(0.2))
	var gl  := _glow_mat(_color)

	# ── HEAD ──
	_add_mi(b, _sphere(0.155), Vector3(0, 0.365, 0), sk)
	# Brow ridge (subtle forehead ledge)
	_add_mi(b, _box(0.22, 0.038, 0.08), Vector3(0, 0.41, 0.1), sk)
	# Nose
	_add_mi(b, _prism(0.055, 0.07, 0.06), Vector3(0, 0.365, 0.155),
		sk, Vector3(PI / 2.0, 0, 0))
	# Eye sockets (slightly darkened)
	for side in [-1, 1]:
		_add_mi(b, _sphere(0.028), Vector3(side * 0.072, 0.382, 0.136),
			_glow_mat(Color(0.9, 0.75, 0.3), 1.2))
	# Chin (lower jaw extension)
	_add_mi(b, _sphere(0.092), Vector3(0, 0.305, 0.04), sk)

	# ── NECK ──
	_add_mi(b, _capsule(0.052, 0.085), Vector3(0, 0.218, 0), sk)

	# ── TORSO ──
	# Upper chest (wider)
	_add_mi(b, _box(0.285, 0.175, 0.175), Vector3(0, 0.115, 0), cl)
	# Abdomen (slightly narrower)
	_add_mi(b, _box(0.245, 0.145, 0.158), Vector3(0, -0.048, 0), cl)
	# Belt
	_add_mi(b, _box(0.268, 0.032, 0.185), Vector3(0, -0.135, 0), arm)
	# Belt buckle
	_add_mi(b, _box(0.058, 0.042, 0.195), Vector3(0, -0.135, 0.0), gl)

	# ── HIPS ──
	_add_mi(b, _box(0.252, 0.118, 0.168), Vector3(0, -0.215, 0), cl)

	# ── SHOULDERS ──
	for side in [-1, 1]:
		_add_mi(b, _sphere(0.095), Vector3(side * 0.195, 0.132, 0), arm)

	# ── UPPER ARMS ──
	for side in [-1, 1]:
		_add_mi(b, _capsule(0.058, 0.215), Vector3(side * 0.218, 0.015, 0),
			cl, Vector3(0, 0, side * 0.15))

	# ── ELBOW JOINT ──
	for side in [-1, 1]:
		_add_mi(b, _sphere(0.048), Vector3(side * 0.232, -0.108, 0), sk)

	# ── FOREARMS ──
	for side in [-1, 1]:
		_add_mi(b, _capsule(0.046, 0.182), Vector3(side * 0.242, -0.205, 0),
			sk, Vector3(0, 0, side * 0.10))

	# ── HANDS ──
	for side in [-1, 1]:
		# Palm
		_add_mi(b, _box(0.072, 0.062, 0.052), Vector3(side * 0.252, -0.308, 0.012), sk)
		# Fingers (grouped as two bumps)
		_add_mi(b, _capsule(0.022, 0.072), Vector3(side * 0.240, -0.348, 0.014),
			sk, Vector3(PI * 0.08, 0, 0))
		_add_mi(b, _capsule(0.018, 0.060), Vector3(side * 0.268, -0.342, 0.012),
			sk, Vector3(PI * 0.08, 0, side * 0.15))

	# ── THIGHS ──
	for side in [-1, 1]:
		_add_mi(b, _capsule(0.075, 0.225), Vector3(side * 0.092, -0.33, 0), cl)

	# ── KNEE JOINT ──
	for side in [-1, 1]:
		_add_mi(b, _sphere(0.058), Vector3(side * 0.092, -0.455, 0.014), sk)

	# ── CALVES ──
	for side in [-1, 1]:
		_add_mi(b, _capsule(0.058, 0.195), Vector3(side * 0.092, -0.555, 0), cl)

	# ── BOOTS ──
	for side in [-1, 1]:
		# Ankle
		_add_mi(b, _sphere(0.052), Vector3(side * 0.092, -0.66, 0), arm)
		# Boot body
		_add_mi(b, _box(0.108, 0.082, 0.155), Vector3(side * 0.092, -0.712, 0.022), arm)
		# Boot toe
		_add_mi(b, _sphere(0.052), Vector3(side * 0.092, -0.715, 0.092),
			_armor_mat(_color.darkened(0.3)))


# ─── Cosmic (ethereal / stellar) ─────────────────────────────────────

func _setup_cosmic(b: MeshInstance3D) -> void:
	var gm := _glow_mat(_color, 0.55)

	# Outer shell — translucent
	var shell_mat := StandardMaterial3D.new()
	shell_mat.transparency              = StandardMaterial3D.TRANSPARENCY_ALPHA
	shell_mat.albedo_color              = Color(_color.r, _color.g, _color.b, 0.22)
	shell_mat.emission_enabled          = true
	shell_mat.emission                  = _color
	shell_mat.emission_energy_multiplier = 0.45
	shell_mat.subsurf_scatter_enabled   = true
	shell_mat.subsurf_scatter_strength  = 0.5
	_add_mi(b, _sphere(0.32), Vector3.ZERO, shell_mat)

	# Dense inner core
	_add_mi(b, _sphere(0.12), Vector3.ZERO, _glow_mat(_color, 3.2))

	# Mid-layer pulsing sphere
	_add_mi(b, _sphere(0.20), Vector3.ZERO, _glow_mat(_color.lightened(0.3), 0.8))

	# Three orbital ring planes
	for i in range(3):
		var rm := CylinderMesh.new()
		rm.top_radius = 0.30 + i * 0.06; rm.bottom_radius = rm.top_radius
		rm.height = 0.016; rm.radial_segments = 32
		_add_mi(b, rm, Vector3.ZERO, _glow_mat(_color, 1.2 - i * 0.25),
			Vector3(i * PI / 3.2, 0, i * PI / 5.0))

	# Trailing energy wisps
	for i in range(5):
		var angle := i * (TAU / 5.0)
		var wm := _capsule(0.032, 0.42)
		_add_mi(b, wm, Vector3(sin(angle) * 0.18, -0.24, cos(angle) * 0.18),
			_glow_mat(_color, 0.3), Vector3(sin(angle) * 0.5, 0, cos(angle) * 0.5))


# ─── Primal (beast / elemental) ──────────────────────────────────────

func _setup_primal(b: MeshInstance3D) -> void:
	var sk  := _organic_mat(_skin_color if _race_id in RACE_SKIN else _color.darkened(0.3))
	var fur := _cloth_mat(_color.darkened(0.28), 0.95)
	var gl  := _glow_mat(_color)

	# Body mass — hunched beast
	_add_mi(b, _capsule(0.22, 0.48), Vector3(0, 0.02, 0), fur)
	# Chest / pectoral mass
	_add_mi(b, _sphere(0.18), Vector3(0, 0.12, 0.08), fur)

	# Head — broad with muzzle
	_add_mi(b, _sphere(0.19), Vector3(0, 0.36, 0.03), sk)
	# Muzzle
	_add_mi(b, _box(0.12, 0.09, 0.12), Vector3(0, 0.34, 0.18), sk)
	# Nostrils
	for side in [-1, 1]:
		_add_mi(b, _sphere(0.022), Vector3(side * 0.032, 0.328, 0.245),
			_organic_mat(_skin_color.darkened(0.4) if _race_id in RACE_SKIN else Color(0.1, 0.1, 0.1)))
	# Beast eyes (deep-set amber)
	for side in [-1, 1]:
		_add_mi(b, _sphere(0.032), Vector3(side * 0.082, 0.38, 0.162),
			_glow_mat(Color(0.9, 0.55, 0.1), 1.8))

	# Shoulder humps
	for side in [-1, 1]:
		_add_mi(b, _sphere(0.128), Vector3(side * 0.275, 0.175, 0), fur)

	# Upper arms (thick, powerful)
	for side in [-1, 1]:
		_add_mi(b, _capsule(0.078, 0.24), Vector3(side * 0.31, 0.04, 0.05),
			sk, Vector3(0.28, 0, side * 0.45))

	# Forearms with claw tips
	for side in [-1, 1]:
		_add_mi(b, _capsule(0.065, 0.20), Vector3(side * 0.368, -0.135, 0.06),
			sk, Vector3(0.18, 0, side * 0.42))
		for c in range(3):
			var ca := (c - 1) * 0.12
			_add_mi(b, _prism(0.040, 0.12, 0.040),
				Vector3(side * (0.395 + c * 0.015), -0.24 - c * 0.01, 0.085 + c * 0.01),
				_glow_mat(_color, 1.5), Vector3(0.45 + ca, 0, side * 0.35))

	# Legs — haunched
	for side in [-1, 1]:
		_add_mi(b, _capsule(0.085, 0.22), Vector3(side * 0.105, -0.22, 0), fur)
		_add_mi(b, _capsule(0.070, 0.20), Vector3(side * 0.108, -0.42, 0.04),
			sk, Vector3(0.22, 0, 0))
		_add_mi(b, _box(0.10, 0.07, 0.18), Vector3(side * 0.108, -0.545, 0.04), sk)

	# Dorsal spines
	for i in range(4):
		_add_mi(b, _prism(0.045, 0.16 - i * 0.025, 0.045),
			Vector3(0, 0.20 + i * 0.08, -0.20 - i * 0.02), gl)


# ─── Eldritch (wrong things that persist) ────────────────────────────

func _setup_eldritch(b: MeshInstance3D) -> void:
	var sk := _organic_mat(_skin_color if _race_id in RACE_SKIN else Color(0.25, 0.18, 0.30), 0.78)
	var gl := _glow_mat(_color)
	var eye_mat := _glow_mat(Color(0.9, 0.05, 0.05), 3.0)

	# Central body mass — irregular sphere
	_add_mi(b, _sphere(0.26), Vector3(0, 0.04, 0), sk)
	# Secondary mass (off-center, unsettling)
	_add_mi(b, _sphere(0.16), Vector3(0.08, 0.18, -0.06), sk)

	# Eye cluster — three eyes, one red
	_add_mi(b, _sphere(0.068), Vector3(0.0,  0.09, 0.22), eye_mat)
	_add_mi(b, _sphere(0.048), Vector3(-0.16, 0.15, 0.18), gl)
	_add_mi(b, _sphere(0.040), Vector3(0.14,  0.22, 0.16), gl)
	# Eyelid crease rings
	_add_mi(b, _cyl(0.075, 0.018, 16), Vector3(0.0, 0.09, 0.22),
		_organic_mat(Color(0.08, 0.04, 0.06)), Vector3(PI / 2.0, 0, 0))

	# Jaw / maw
	_add_mi(b, _sphere(0.14), Vector3(0, -0.08, 0.14), _organic_mat(Color(0.18, 0.05, 0.10)))
	# Teeth
	for i in range(5):
		var ang := (i - 2) * 0.28
		_add_mi(b, _prism(0.028, 0.065, 0.028),
			Vector3(sin(ang) * 0.09, -0.095, 0.22 + cos(ang) * 0.03),
			_cloth_mat(Color(0.88, 0.86, 0.82)), Vector3(-0.5, ang, 0))

	# Tentacle appendages — 6, fanning down
	for i in range(6):
		var angle := i * (TAU / 6.0)
		var t_mat := _organic_mat(_color.darkened(0.2 + (i % 3) * 0.08))
		# Upper segment
		_add_mi(b, _capsule(0.048, 0.24), Vector3(sin(angle) * 0.20, -0.18, cos(angle) * 0.20),
			t_mat, Vector3(0.55 + (i % 2) * 0.15, 0, sin(angle) * 0.5))
		# Lower tip
		_add_mi(b, _capsule(0.030, 0.18), Vector3(sin(angle) * 0.30, -0.36, cos(angle) * 0.30),
			t_mat, Vector3(0.72 + (i % 3) * 0.12, 0, sin(angle) * 0.6))
		# Sucker nubs
		_add_mi(b, _sphere(0.022), Vector3(sin(angle) * 0.35, -0.38, cos(angle) * 0.35),
			_glow_mat(_color, 0.8))

	# Orbiting fragments
	for i in range(4):
		var angle := i * (TAU / 4.0)
		_add_mi(b, _sphere(0.055), Vector3(sin(angle) * 0.42, 0.06 + cos(angle * 2.0) * 0.18, cos(angle) * 0.42), gl)


# ─── Mechanical (construct / war-machine) ────────────────────────────

func _setup_mechanical(b: MeshInstance3D) -> void:
	var hull := _armor_mat(_color.darkened(0.15), 0.80, 0.18)
	var plate := _armor_mat(_color.darkened(0.05), 0.88, 0.12)
	var gl   := _glow_mat(_color)
	var dark := _cloth_mat(Color(0.08, 0.08, 0.10))

	# Chassis / torso
	_add_mi(b, _box(0.42, 0.46, 0.28), Vector3(0, 0.04, 0), hull)
	# Chest reactor window
	_add_mi(b, _box(0.20, 0.14, 0.30), Vector3(0, 0.08, 0), gl)
	# Reactor core inner
	_add_mi(b, _sphere(0.068), Vector3(0, 0.08, 0.06), _glow_mat(_color, 4.0))

	# Abdomen panel
	_add_mi(b, _box(0.36, 0.12, 0.30), Vector3(0, -0.14, 0), plate)
	# Hip joint caps
	for side in [-1, 1]:
		_add_mi(b, _sphere(0.065), Vector3(side * 0.21, -0.215, 0), hull)

	# Head unit
	_add_mi(b, _box(0.32, 0.20, 0.25), Vector3(0, 0.36, 0), hull)
	# Visor slit — glowing line
	_add_mi(b, _box(0.25, 0.048, 0.27), Vector3(0, 0.368, 0.0), _glow_mat(_color, 3.8))
	# Optic lenses
	for side in [-1, 1]:
		_add_mi(b, _sphere(0.036), Vector3(side * 0.075, 0.368, 0.13), _glow_mat(_color, 5.0))
	# Head panel seams
	_add_mi(b, _box(0.34, 0.012, 0.27), Vector3(0, 0.30, 0), dark)
	_add_mi(b, _box(0.34, 0.012, 0.27), Vector3(0, 0.42, 0), dark)

	# Pauldrons
	for side in [-1, 1]:
		_add_mi(b, _box(0.145, 0.18, 0.20), Vector3(side * 0.285, 0.195, 0), plate)
		_add_mi(b, _sphere(0.065), Vector3(side * 0.285, 0.305, 0), hull)

	# Upper arms
	for side in [-1, 1]:
		_add_mi(b, _box(0.10, 0.24, 0.10), Vector3(side * 0.305, 0.06, 0), hull)
	# Elbow joint
	for side in [-1, 1]:
		_add_mi(b, _sphere(0.052), Vector3(side * 0.308, -0.075, 0), plate)
	# Forearms
	for side in [-1, 1]:
		_add_mi(b, _box(0.095, 0.20, 0.095), Vector3(side * 0.308, -0.178, 0), hull)
	# Hands / grips
	for side in [-1, 1]:
		_add_mi(b, _box(0.11, 0.075, 0.115), Vector3(side * 0.308, -0.288, 0.018), plate)
		for i in range(3):
			_add_mi(b, _box(0.022, 0.052, 0.022),
				Vector3(side * (0.288 + i * 0.02), -0.332, 0.026), dark)

	# Leg upper
	for side in [-1, 1]:
		_add_mi(b, _box(0.115, 0.22, 0.115), Vector3(side * 0.105, -0.32, 0), hull)
	# Knee
	for side in [-1, 1]:
		_add_mi(b, _sphere(0.062), Vector3(side * 0.105, -0.445, 0.018), plate)
	# Leg lower
	for side in [-1, 1]:
		_add_mi(b, _box(0.105, 0.20, 0.115), Vector3(side * 0.105, -0.548, 0), hull)
	# Feet
	for side in [-1, 1]:
		_add_mi(b, _box(0.115, 0.065, 0.185), Vector3(side * 0.105, -0.66, 0.028), plate)

	# Antenna
	_add_mi(b, _capsule(0.018, 0.18), Vector3(0.085, 0.505, 0), hull)
	_add_mi(b, _sphere(0.034), Vector3(0.085, 0.600, 0), _glow_mat(_color, 4.5))


# ─── Plinth (coin base) ──────────────────────────────────────────────

func _add_plinth(b: MeshInstance3D) -> void:
	var disc := _cyl(0.38, 0.04, 32)
	var disc_mat := StandardMaterial3D.new()
	disc_mat.albedo_color              = _color.darkened(0.72)
	disc_mat.metallic                  = 0.72
	disc_mat.roughness                 = 0.22
	disc_mat.emission_enabled          = true
	disc_mat.emission                  = _color
	disc_mat.emission_energy_multiplier = 0.35
	_add_mi(b, disc, Vector3(0, -0.74, 0), disc_mat)

	var rim := _cyl(0.41, 0.010, 32)
	var rim_mat := StandardMaterial3D.new()
	rim_mat.albedo_color              = _color
	rim_mat.emission_enabled          = true
	rim_mat.emission                  = _color
	rim_mat.emission_energy_multiplier = 2.4
	_add_mi(b, rim, Vector3(0, -0.724, 0), rim_mat)


# ─── Portrait coin ───────────────────────────────────────────────────

func _add_portrait(b: MeshInstance3D, race_id: String) -> void:
	var path := "res://assets/characters/%s.png" % race_id
	if not ResourceLoader.exists(path):
		return
	var tex := load(path) as Texture2D
	if not tex:
		return
	var qm := QuadMesh.new(); qm.size = Vector2(0.68, 0.68)
	var pmat := StandardMaterial3D.new()
	pmat.albedo_texture  = tex
	pmat.albedo_color    = Color(1, 1, 1, 0.70)
	pmat.transparency    = StandardMaterial3D.TRANSPARENCY_ALPHA
	pmat.depth_draw_mode = StandardMaterial3D.DEPTH_DRAW_DISABLED
	var portrait := _add_mi(b, qm, Vector3(0, -0.716, 0), pmat)
	portrait.rotation.x = -PI / 2.0


# ─── Name label ──────────────────────────────────────────────────────

func _add_name_label(label_text: String) -> void:
	_name_label = Label3D.new()
	_name_label.text             = _fmt_name(label_text)
	_name_label.font_size        = 20
	_name_label.outline_size     = 7
	_name_label.modulate         = _color.lightened(0.25)
	_name_label.outline_modulate = Color(0, 0, 0, 0.92)
	_name_label.billboard        = BaseMaterial3D.BILLBOARD_ENABLED
	_name_label.no_depth_test    = true
	_name_label.position         = Vector3(0, 1.0, 0)
	add_child(_name_label)


# ─── Selection ring ───────────────────────────────────────────────────

func _add_selection_ring() -> void:
	_selection_ring = MeshInstance3D.new()
	_selection_ring.mesh = _cyl(0.50, 0.008, 32)
	var rmat := StandardMaterial3D.new()
	rmat.albedo_color              = Color(_color.r, _color.g, _color.b, 0.85)
	rmat.emission_enabled          = true
	rmat.emission                  = _color
	rmat.emission_energy_multiplier = 1.5
	rmat.transparency              = StandardMaterial3D.TRANSPARENCY_ALPHA
	_selection_ring.material_override = rmat
	_selection_ring.position          = Vector3(0, 0.01, 0)
	_selection_ring.visible           = false
	add_child(_selection_ring)


# ─── Helpers ─────────────────────────────────────────────────────────

func _fmt_name(s: String) -> String:
	return s.replace("_", " ").capitalize()


# ─── Per-race overrides ───────────────────────────────────────────────

func _apply_race_overrides(b: MeshInstance3D) -> void:
	match _race_id:

		# ── COSMIC ────────────────────────────────────────────────────
		"voidwraith":
			for mi in b.get_children():
				if mi is MeshInstance3D:
					var mat: Material = mi.material_override
					if mat and mat is StandardMaterial3D:
						mat.emission_energy_multiplier *= 2.0
						(mat as StandardMaterial3D).transparency = StandardMaterial3D.TRANSPARENCY_ALPHA
						(mat as StandardMaterial3D).albedo_color.a = 0.35

		"nullshade":
			b.scale = Vector3(1.0, 0.65, 1.0)
			for mi in b.get_children():
				if mi is MeshInstance3D and mi.material_override is StandardMaterial3D:
					(mi.material_override as StandardMaterial3D).albedo_color.a = 0.4
			for i in range(5):
				var angle := i * (TAU / 5.0)
				_add_mi(b, _capsule(0.028, 0.38), Vector3(sin(angle) * 0.15, -0.28, cos(angle) * 0.15),
					_glow_mat(_color, 0.45), Vector3(sin(angle) * 0.7, 0, cos(angle) * 0.7))

		"ironlocust":
			for i in range(8):
				var angle := i * (TAU / 8.0)
				_add_mi(b, _prism(0.055, 0.28, 0.055),
					Vector3(sin(angle) * 0.21, 0.04 + (i % 3) * 0.10, cos(angle) * 0.21),
					_glow_mat(_color, 2.0),
					Vector3(sin(angle) * 0.55, 0, cos(angle) * 0.38))

		"embervein":
			b.scale = Vector3(1.42, 1.18, 1.42)
			for i in range(4):
				var ang := i * (TAU / 4.0)
				_add_mi(b, _box(0.035, 0.52, 0.035),
					Vector3(sin(ang) * 0.17, 0.02, cos(ang) * 0.17),
					_glow_mat(Color(1.0, 0.28, 0.0), 3.8))

		"riftwalker":
			var ghost := MeshInstance3D.new()
			ghost.mesh = _sphere(0.30)
			var gmat := StandardMaterial3D.new()
			gmat.transparency = StandardMaterial3D.TRANSPARENCY_ALPHA
			gmat.albedo_color = Color(_color.r, _color.g, _color.b, 0.18)
			gmat.emission_enabled = true; gmat.emission = _color
			gmat.emission_energy_multiplier = 0.35
			ghost.material_override = gmat
			ghost.position = Vector3(0.20, 0, -0.12)
			ghost.scale    = Vector3(0.82, 0.82, 0.82)
			b.add_child(ghost)

		# ── PRIMAL ────────────────────────────────────────────────────
		"solarlord":
			var wm := _armor_mat(Color(1.0, 0.90, 0.45), 0.2, 0.3)
			for side in [-1, 1]:
				for seg in range(3):
					_add_mi(b, _box(0.35 - seg * 0.07, 0.035, 0.20 - seg * 0.05),
						Vector3(side * (0.30 + seg * 0.20), 0.10 - seg * 0.07, 0), wm,
						Vector3(0, 0, side * (0.22 + seg * 0.16)))
			for i in range(8):
				var ang := i * (TAU / 8.0)
				_add_mi(b, _prism(0.032, 0.24, 0.032),
					Vector3(sin(ang) * 0.25, 0.40, cos(ang) * 0.25),
					_glow_mat(Color(1.0, 0.95, 0.20), 3.5))

		"thornmimic":
			for i in range(12):
				var angle := i * (TAU / 12.0)
				_add_mi(b, _prism(0.042, 0.16 + (i % 3) * 0.05, 0.042),
					Vector3(sin(angle) * 0.22, -0.12 + (i % 4) * 0.13, cos(angle) * 0.22),
					_glow_mat(_color, 1.2),
					Vector3(sin(angle) * 0.48, 0, cos(angle + PI / 3.0) * 0.48))

		"cinderkin":
			b.scale = Vector3(0.58, 0.58, 0.58)
			for i in range(6):
				var ang := i * (TAU / 6.0)
				_add_mi(b, _prism(0.065, 0.24, 0.065),
					Vector3(sin(ang) * 0.17, 0.35, cos(ang) * 0.17),
					_glow_mat(Color(1.0, 0.65, 0.1), 3.2))

		"deeptyrant":
			for i in range(10):
				var ang := i * (TAU / 10.0)
				_add_mi(b, _capsule(0.035, 0.26),
					Vector3(sin(ang) * 0.20, 0.24, cos(ang) * 0.20),
					_organic_mat(_color.darkened(0.2)),
					Vector3(-0.55, 0, sin(ang) * 0.4))

		"grimcrow":
			var feath := _cloth_mat(Color(0.04, 0.04, 0.06), 0.96)
			for side in [-1, 1]:
				for seg in range(3):
					_add_mi(b, _box(0.42 - seg * 0.10, 0.028, 0.04),
						Vector3(side * (0.28 + seg * 0.18), 0.06 - seg * 0.05, -0.04 - seg * 0.01),
						feath, Vector3(0.25 + seg * 0.08, 0, side * (0.48 + seg * 0.12)))
			_add_mi(b, _prism(0.055, 0.18, 0.055),
				Vector3(0, 0.35, 0.19), _organic_mat(Color(0.08, 0.06, 0.0)),
				Vector3(PI / 2.2, 0, 0))

		# ── ELDRITCH ──────────────────────────────────────────────────
		"bloodweaver":
			b.scale = Vector3(0.80, 1.25, 0.80)
			var cape := _cloth_mat(Color(0.18, 0.02, 0.04), 0.95)
			for side in [-1, 1]:
				for seg in range(3):
					_add_mi(b, _box(0.32 - seg * 0.05, 0.5 - seg * 0.08, 0.032),
						Vector3(side * (0.24 + seg * 0.14), -0.04 - seg * 0.06, -0.09), cape,
						Vector3(0.15 + seg * 0.05, 0, side * (0.55 + seg * 0.18)))
			for side in [-1, 1]:
				_add_mi(b, _prism(0.036, 0.092, 0.036),
					Vector3(side * 0.046, 0.28, 0.17),
					_cloth_mat(Color(0.92, 0.90, 0.96)), Vector3(-0.28, 0, 0))

		"dreamhusk":
			var cap_mat := _organic_mat(_color.darkened(0.18))
			var cone := CylinderMesh.new()
			cone.top_radius = 0.0; cone.bottom_radius = 0.38; cone.height = 0.20; cone.radial_segments = 24
			_add_mi(b, cone, Vector3(0, 0.42, 0), cap_mat)
			_add_mi(b, _sphere(0.14), Vector3(0, 0.38, 0), cap_mat)
			for i in range(7):
				var ang := i * (TAU / 7.0)
				_add_mi(b, _capsule(0.020, 0.20),
					Vector3(sin(ang) * 0.26, 0.30, cos(ang) * 0.26),
					_glow_mat(_color, 0.45), Vector3(sin(ang) * 0.38, 0, cos(ang) * 0.3))

		"bonedrifter":
			var bone := _cloth_mat(Color(0.84, 0.82, 0.76), 0.88)
			for side in [-1, 1]:
				for i in range(4):
					_add_mi(b, _capsule(0.022, 0.20),
						Vector3(side * 0.17, 0.06 - i * 0.10, 0), bone,
						Vector3(0, 0, side * (0.68 + i * 0.06)))
			for side in [-1, 1]:
				_add_mi(b, _prism(0.045, 0.20, 0.045),
					Vector3(side * 0.092, 0.52, 0), bone)

		"mindspider":
			b.material_override.transparency = StandardMaterial3D.TRANSPARENCY_ALPHA
			b.material_override.albedo_color  = Color(_color.r, _color.g, _color.b, 0.50)
			for i in range(8):
				var ang := i * (TAU / 8.0)
				# Upper leg segment
				_add_mi(b, _capsule(0.026, 0.22),
					Vector3(sin(ang) * 0.22, -0.06, cos(ang) * 0.22),
					_organic_mat(_color.darkened(0.15)), Vector3(0.50, 0, ang))
				# Lower leg segment
				_add_mi(b, _capsule(0.018, 0.18),
					Vector3(sin(ang) * 0.38, -0.20, cos(ang) * 0.38),
					_organic_mat(_color.darkened(0.25)), Vector3(0.78, 0, ang))

		"chaosling":
			_add_mi(b, _box(0.20, 0.26, 0.16), Vector3(0.16, 0.08, 0), _glow_mat(_color, 1.8))
			_add_mi(b, _sphere(0.09), Vector3(-0.20, 0.22, 0),
				_glow_mat(Color(1, 0.08, 0.85), 2.8))
			_add_mi(b, _capsule(0.04, 0.22), Vector3(-0.28, -0.10, 0.08),
				_organic_mat(_color), Vector3(0.4, -0.3, -0.5))

		# ── MECHANICAL ────────────────────────────────────────────────
		"ironveil":
			b.scale = Vector3(1.38, 1.02, 0.15)
			for mi in b.get_children():
				if mi is MeshInstance3D and mi.material_override is StandardMaterial3D:
					(mi.material_override as StandardMaterial3D).metallic  = 0.96
					(mi.material_override as StandardMaterial3D).roughness = 0.04

		"forgespawn":
			var blob_mat := _armor_mat(_color, 0.92, 0.08)
			_add_mi(b, _sphere(0.38), Vector3(0, 0.02, 0), blob_mat)
			_add_mi(b, _cyl(0.44, 0.055, 24), Vector3(0, -0.31, 0), blob_mat)
			for i in range(5):
				var ang := i * (TAU / 5.0)
				_add_mi(b, _sphere(0.055),
					Vector3(sin(ang) * 0.36, -0.02, cos(ang) * 0.36),
					_glow_mat(_color, 1.8))

		"cinderplate":
			b.scale = Vector3(1.55, 1.0, 1.55)
			for side in [-1, 1]:
				_add_mi(b, _box(0.16, 0.44, 0.36),
					Vector3(side * 0.34, 0.02, 0), _armor_mat(_color.darkened(0.12), 0.88, 0.10))
			_add_mi(b, _cyl(0.062, 0.20), Vector3(0, 0.48, 0),
				_glow_mat(Color(1.0, 0.28, 0.0), 3.5))

		"hexgear":
			var hex_mat := _armor_mat(_color, 0.72, 0.18)
			var body_cyl := CylinderMesh.new()
			body_cyl.top_radius = 0.27; body_cyl.bottom_radius = 0.27
			body_cyl.height = 0.58; body_cyl.radial_segments = 6
			_add_mi(b, body_cyl, Vector3.ZERO, hex_mat)
			for i in range(4):
				var hm := CylinderMesh.new()
				hm.top_radius = 0.17; hm.bottom_radius = 0.17
				hm.height = 0.05; hm.radial_segments = 6
				_add_mi(b, hm, Vector3(0, -0.10 + i * 0.22, 0),
					_glow_mat(_color, 2.2 - i * 0.3))

		"wirewraith":
			for mi in b.get_children():
				if mi is MeshInstance3D and mi.material_override is StandardMaterial3D:
					(mi.material_override as StandardMaterial3D).metallic  = 0.97
					(mi.material_override as StandardMaterial3D).roughness = 0.03
					(mi.material_override as StandardMaterial3D).emission_energy_multiplier = 2.2
			for i in range(14):
				var ang := i * (TAU / 14.0)
				_add_mi(b, _capsule(0.010, 0.36 + (i % 3) * 0.08),
					Vector3(sin(ang) * 0.18, 0.08 + (i % 4) * 0.07, cos(ang) * 0.18),
					_glow_mat(_color, 2.6),
					Vector3(sin(ang) * 0.8, 0, cos(ang) * 0.8))

		# ── HUMANOID — ELF VARIANTS ───────────────────────────────────
		"hollowsong":
			b.scale = Vector3(0.78, 1.24, 0.78)
			for side in [-1, 1]:
				_add_mi(b, _prism(0.030, 0.13, 0.030),
					Vector3(side * 0.158, 0.415, 0.0), _skin_mat())
			_add_mi(b, _sphere(0.095), Vector3(0, 0.10, 0.14), _glow_mat(_color, 3.8))

		"ashcrown":
			b.scale = Vector3(0.80, 1.26, 0.80)
			for side in [-1, 1]:
				_add_mi(b, _prism(0.028, 0.14, 0.028),
					Vector3(side * 0.156, 0.418, 0.0), _skin_mat(Color(1.1, 1.05, 1.0)))
			for i in range(6):
				var ang := i * (TAU / 6.0)
				_add_mi(b, _prism(0.028, 0.155, 0.028),
					Vector3(sin(ang) * 0.125, 0.535, cos(ang) * 0.125),
					_glow_mat(_color, 2.8))

		"veilborn":
			b.scale = Vector3(0.84, 1.14, 0.84)
			for side in [-1, 1]:
				_add_mi(b, _prism(0.026, 0.115, 0.026),
					Vector3(side * 0.155, 0.408, 0.0), _skin_mat())
			for side in [-1, 1]:
				_add_mi(b, _sphere(0.032), Vector3(side * 0.068, 0.378, 0.142),
					_glow_mat(Color(0.72, 0.0, 1.0), 4.0))

		"thornweft":
			b.scale = Vector3(0.86, 1.10, 0.86)
			for side in [-1, 1]:
				_add_mi(b, _prism(0.026, 0.108, 0.026),
					Vector3(side * 0.154, 0.402, 0.0), _skin_mat())
			for i in range(7):
				var ang := i * (TAU / 7.0)
				_add_mi(b, _prism(0.038, 0.14 + (i % 2) * 0.05, 0.038),
					Vector3(sin(ang) * 0.21, -0.05 + (i % 3) * 0.12, cos(ang) * 0.21),
					_glow_mat(_color, 1.2),
					Vector3(sin(ang) * 0.5, 0, cos(ang + PI / 3.5) * 0.45))

		"duskweft":
			b.scale = Vector3(0.88, 1.08, 0.88)
			for side in [-1, 1]:
				_add_mi(b, _prism(0.025, 0.102, 0.025),
					Vector3(side * 0.153, 0.398, 0.0), _skin_mat())
			for mi in b.get_children():
				if mi is MeshInstance3D and mi.material_override is StandardMaterial3D:
					(mi.material_override as StandardMaterial3D).albedo_color.a = 0.78

		# ── HUMANOID — DWARF VARIANTS ─────────────────────────────────
		"ironfast":
			b.scale = Vector3(1.36, 0.72, 1.36)
			# Beard — layered blocks for volume
			_add_mi(b, _box(0.21, 0.09, 0.10), Vector3(0, 0.278, 0.118), _cloth_mat(Color(0.35, 0.28, 0.22)))
			_add_mi(b, _box(0.17, 0.07, 0.085), Vector3(0, 0.242, 0.125), _cloth_mat(Color(0.30, 0.24, 0.18)))
			# Heavy gauntlets
			for side in [-1, 1]:
				_add_mi(b, _box(0.135, 0.095, 0.135),
					Vector3(side * 0.228, -0.195, 0), _armor_mat(_color.darkened(0.2), 0.82, 0.22))

		"coreborn":
			b.scale = Vector3(1.30, 0.74, 1.30)
			for side in [-1, 1]:
				for i in range(4):
					_add_mi(b, _prism(0.055, 0.17 - i * 0.03, 0.055),
						Vector3(side * (0.205 + i * 0.035), 0.165 - i * 0.055, 0),
						_glow_mat(_color, 2.0 - i * 0.35))

		# ── HUMANOID — OTHER ──────────────────────────────────────────
		"ashenborn":
			for mi in b.get_children():
				if mi is MeshInstance3D and mi.material_override is StandardMaterial3D:
					if (mi.material_override as StandardMaterial3D).subsurf_scatter_enabled:
						(mi.material_override as StandardMaterial3D).albedo_color = Color(0.08, 0.06, 0.05)
			for i in range(5):
				var ang := i * (TAU / 5.0) + 0.3
				_add_mi(b, _prism(0.042, 0.20 + (i % 2) * 0.07, 0.042),
					Vector3(sin(ang) * 0.10, 0.44 + (i % 2) * 0.04, cos(ang) * 0.10),
					_glow_mat(Color(1.0, 0.38, 0.0), 3.2))

		"warpbred":
			b.scale = Vector3(1.10, 0.96, 0.86)
			_add_mi(b, _capsule(0.048, 0.22), Vector3(-0.28, 0.08, 0.10),
				_skin_mat(), Vector3(0.48, 0.38, -0.28))

		"splitblood":
			_add_mi(b, _box(0.148, 0.62, 0.20), Vector3(0.076, 0.02, 0),
				_glow_mat(Color(0.75, 0.08, 0.08), 1.2))

		"glitchkin":
			var ghost := MeshInstance3D.new()
			ghost.mesh = _sphere(0.155)
			var gmat := StandardMaterial3D.new()
			gmat.transparency = StandardMaterial3D.TRANSPARENCY_ALPHA
			gmat.albedo_color = Color(0.0, 1.0, 0.8, 0.28)
			gmat.emission_enabled = true; gmat.emission = Color(0.0, 1.0, 0.8)
			gmat.emission_energy_multiplier = 1.8
			ghost.material_override = gmat
			ghost.position = Vector3(0.115, 0.365, 0.0)
			b.add_child(ghost)

		"fractureline":
			for i in range(5):
				var ang := i * (TAU / 5.0)
				_add_mi(b, _box(0.016, 0.35, 0.016),
					Vector3(sin(ang) * 0.13, 0.02, cos(ang) * 0.13),
					_glow_mat(Color(0.1, 0.1, 0.1), 0.0))

		"emberpact":
			for side in [-1, 1]:
				for i in range(3):
					_add_mi(b, _prism(0.035, 0.11, 0.035),
						Vector3(side * (0.208 + i * 0.022), -0.33, 0.038),
						_glow_mat(Color(1.0, 0.45, 0.0), 3.2),
						Vector3(-0.38 + i * 0.18, 0, 0))

		"fallenlight":
			_add_mi(b, _cyl(0.195, 0.016, 32), Vector3(0, 0.545, 0),
				_glow_mat(Color(1.0, 0.94, 0.62), 1.4))
			for mi in b.get_children():
				if mi is MeshInstance3D and mi.material_override is StandardMaterial3D:
					if (mi.material_override as StandardMaterial3D).subsurf_scatter_enabled:
						(mi.material_override as StandardMaterial3D).albedo_color = \
							(mi.material_override as StandardMaterial3D).albedo_color.lerp(Color(0.85, 0.84, 0.80), 0.5)

		"scaleworn":
			for mi in b.get_children():
				if mi is MeshInstance3D and mi.material_override is StandardMaterial3D:
					(mi.material_override as StandardMaterial3D).metallic  = 0.42
					(mi.material_override as StandardMaterial3D).roughness = 0.52
			for i in range(10):
				var ang := i * (TAU / 10.0)
				_add_mi(b, _sphere(0.045),
					Vector3(sin(ang) * 0.17, -0.06 + (i % 3) * 0.10, cos(ang) * 0.17),
					_armor_mat(_color, 0.55, 0.45))
