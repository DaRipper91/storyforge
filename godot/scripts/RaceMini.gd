extends Node3D

const RACE_COLORS: Dictionary = {
	"Cosmic":     Color(0.2, 0.4, 1.0),
	"Primal":     Color(0.1, 0.8, 0.2),
	"Eldritch":   Color(0.7, 0.1, 0.9),
	"Mechanical": Color(1.0, 0.5, 0.1),
	"Humanoid":   Color(1.0, 0.85, 0.6),
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

var _color:          Color  = Color.WHITE
var _group:          String = "Humanoid"
var _race_id:        String = ""
var _selected:       bool   = false
var _selection_ring: MeshInstance3D = null
var _name_label:     Label3D        = null
var _bob_time:       float = 0.0
var _ring_pulse:     float = 0.0


func _process(delta: float) -> void:
	if not body:
		return
	body.rotate_y(delta * 0.5)
	_bob_time += delta
	body.position.y = 0.4 + sin(_bob_time * 1.5) * 0.015

	if _selected and _selection_ring:
		_ring_pulse += delta * 3.0
		var mat := _selection_ring.material_override as StandardMaterial3D
		if mat:
			mat.emission_energy_multiplier = 0.8 + (sin(_ring_pulse) + 1.0) * 0.75


# ─── Public API ──────────────────────────────────────────────────────

func setup(race_id: String, char_name: String = "") -> void:
	# Support being called before _ready() (e.g. before add_child in tabletop)
	var b: MeshInstance3D = body if body else get_node_or_null("Body") as MeshInstance3D
	if not b:
		return
	body = b

	_race_id = race_id
	_group   = RACE_GROUP.get(race_id, "Humanoid")
	_color   = RACE_COLORS.get(_group, Color.WHITE)

	for child in b.get_children():
		child.queue_free()
	if _name_label and is_instance_valid(_name_label):
		_name_label.queue_free()
		_name_label = null
	if _selection_ring and is_instance_valid(_selection_ring):
		_selection_ring.queue_free()
		_selection_ring = null

	var capsule := CapsuleMesh.new()
	capsule.radius = 0.2
	capsule.height = 0.8
	b.mesh = capsule
	b.material_override = _make_mat(_color)

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


# ─── Helpers ─────────────────────────────────────────────────────────

func _fmt_name(s: String) -> String:
	return s.replace("_", " ").capitalize()


func _make_mat(color: Color, energy: float = 1.2, metallic: float = 0.0, roughness: float = 0.75) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.albedo_color              = color.darkened(0.45)
	mat.emission_enabled          = true
	mat.emission                  = color
	mat.emission_energy_multiplier = energy
	mat.metallic                  = metallic
	mat.roughness                 = roughness
	return mat


func _add_mi(parent: Node3D, mesh: Mesh, pos: Vector3, mat: StandardMaterial3D = null, rot: Vector3 = Vector3.ZERO) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.mesh     = mesh
	mi.position = pos
	if rot != Vector3.ZERO:
		mi.rotation = rot
	mi.material_override = mat if mat else body.material_override
	parent.add_child(mi)
	return mi


# ─── Plinth (coin-mini base) ─────────────────────────────────────────

func _add_plinth(b: MeshInstance3D) -> void:
	var disc := CylinderMesh.new()
	disc.top_radius    = 0.38
	disc.bottom_radius = 0.38
	disc.height        = 0.04
	var disc_mat := StandardMaterial3D.new()
	disc_mat.albedo_color              = _color.darkened(0.72)
	disc_mat.emission_enabled          = true
	disc_mat.emission                  = _color
	disc_mat.emission_energy_multiplier = 0.45
	disc_mat.metallic  = 0.65
	disc_mat.roughness = 0.28
	_add_mi(b, disc, Vector3(0, -0.38, 0), disc_mat)

	# Glowing rim ring
	var rim := CylinderMesh.new()
	rim.top_radius    = 0.41
	rim.bottom_radius = 0.41
	rim.height        = 0.012
	var rim_mat := StandardMaterial3D.new()
	rim_mat.albedo_color              = _color
	rim_mat.emission_enabled          = true
	rim_mat.emission                  = _color
	rim_mat.emission_energy_multiplier = 2.2
	_add_mi(b, rim, Vector3(0, -0.364, 0), rim_mat)


# ─── Portrait coin on the plinth ─────────────────────────────────────

func _add_portrait(b: MeshInstance3D, race_id: String) -> void:
	var path := "res://assets/characters/%s.png" % race_id
	if not ResourceLoader.exists(path):
		return
	var tex := load(path) as Texture2D
	if not tex:
		return

	var qm := QuadMesh.new()
	qm.size = Vector2(0.68, 0.68)
	var pmat := StandardMaterial3D.new()
	pmat.albedo_texture  = tex
	pmat.albedo_color    = Color(1, 1, 1, 0.72)
	pmat.transparency    = StandardMaterial3D.TRANSPARENCY_ALPHA
	pmat.depth_draw_mode = StandardMaterial3D.DEPTH_DRAW_DISABLED

	var portrait := _add_mi(b, qm, Vector3(0, -0.352, 0), pmat)
	portrait.rotation.x = -PI / 2.0


# ─── Name label (billboard, always faces camera) ─────────────────────

func _add_name_label(label_text: String) -> void:
	_name_label = Label3D.new()
	_name_label.text             = _fmt_name(label_text)
	_name_label.font_size        = 20
	_name_label.outline_size     = 7
	_name_label.modulate         = _color.lightened(0.25)
	_name_label.outline_modulate = Color(0, 0, 0, 0.92)
	_name_label.billboard        = BaseMaterial3D.BILLBOARD_ENABLED
	_name_label.no_depth_test    = true
	_name_label.position         = Vector3(0, 1.15, 0)
	add_child(_name_label)


# ─── Selection ring (floor pulse, child of root so it doesn't rotate) ─

func _add_selection_ring() -> void:
	_selection_ring = MeshInstance3D.new()
	var rm := CylinderMesh.new()
	rm.top_radius    = 0.52
	rm.bottom_radius = 0.52
	rm.height        = 0.008
	_selection_ring.mesh = rm

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


# ─── Group builders ───────────────────────────────────────────────────

func _setup_cosmic(b: MeshInstance3D) -> void:
	var sphere := SphereMesh.new()
	sphere.radius = 0.32
	sphere.height = 0.64
	b.mesh = sphere

	var mat := StandardMaterial3D.new()
	mat.transparency              = StandardMaterial3D.TRANSPARENCY_ALPHA
	mat.albedo_color              = Color(_color.r, _color.g, _color.b, 0.3)
	mat.emission_enabled          = true
	mat.emission                  = _color
	mat.emission_energy_multiplier = 0.55
	b.material_override = mat

	# Inner bright core
	var core := SphereMesh.new()
	core.radius = 0.14
	core.height = 0.28
	_add_mi(b, core, Vector3.ZERO, _make_mat(_color, 2.8))

	# Three orbital rings at different angles
	for i in range(3):
		var ring := CylinderMesh.new()
		ring.top_radius    = 0.28 + i * 0.07
		ring.bottom_radius = 0.28 + i * 0.07
		ring.height        = 0.018
		_add_mi(b, ring, Vector3.ZERO, _make_mat(_color, 1.0 - i * 0.2),
			Vector3(i * PI / 3.0, 0.0, i * PI / 4.5))

	# Wispy tendrils hanging below
	for i in range(4):
		var angle := i * PI / 2.0
		var tm := CapsuleMesh.new()
		tm.radius = 0.038
		tm.height = 0.38
		_add_mi(b, tm,
			Vector3(sin(angle) * 0.2, -0.26, cos(angle) * 0.2),
			_make_mat(_color, 0.35),
			Vector3(sin(angle) * 0.45, 0.0, cos(angle) * 0.45))


func _setup_primal(b: MeshInstance3D) -> void:
	var torso := CylinderMesh.new()
	torso.top_radius    = 0.21
	torso.bottom_radius = 0.17
	torso.height        = 0.52
	b.mesh = torso
	var mat := _make_mat(_color, 1.0, 0.12, 0.88)
	b.material_override = mat

	# Broad beast head
	var head := SphereMesh.new()
	head.radius = 0.19
	head.height = 0.36
	_add_mi(b, head, Vector3(0, 0.35, 0.04))

	# Shoulder humps
	for side in [-1, 1]:
		var sh := SphereMesh.new()
		sh.radius = 0.12
		sh.height = 0.22
		_add_mi(b, sh, Vector3(side * 0.27, 0.16, 0.0), mat)

	# Forearms + claw tips
	for side in [-1, 1]:
		var arm := CapsuleMesh.new()
		arm.radius = 0.062
		arm.height = 0.26
		_add_mi(b, arm, Vector3(side * 0.30, -0.02, 0.04), mat,
			Vector3(0.28, 0.0, side * 0.48))
		var claw := PrismMesh.new()
		claw.size = Vector3(0.055, 0.14, 0.055)
		_add_mi(b, claw, Vector3(side * 0.37, -0.15, 0.08),
			_make_mat(_color, 2.0), Vector3(0.4, 0.0, side * 0.5))

	# Dorsal spines
	for i in range(3):
		var spine := PrismMesh.new()
		spine.size = Vector3(0.048, 0.18 - i * 0.04, 0.048)
		_add_mi(b, spine, Vector3(0, 0.18 + i * 0.09, -0.19 - i * 0.02),
			_make_mat(_color, 1.6))


func _setup_eldritch(b: MeshInstance3D) -> void:
	var sphere := SphereMesh.new()
	sphere.radius = 0.26
	sphere.height = 0.52
	b.mesh = sphere
	b.material_override = _make_mat(_color, 0.85)

	# Eye cluster (one red, two group-color)
	for i in range(3):
		var angle := i * (PI * 2.0 / 3.0)
		var eye := SphereMesh.new()
		eye.radius = 0.068
		eye.height = 0.13
		var eye_color := Color(1.0, 0.05, 0.05) if i == 0 else _color
		_add_mi(b, eye, Vector3(sin(angle) * 0.17, 0.07, cos(angle) * 0.17),
			_make_mat(eye_color, 2.8))

	# Tentacle appendages fanning downward
	for i in range(6):
		var angle := i * (PI / 3.0)
		var tm := CapsuleMesh.new()
		tm.radius = 0.042
		tm.height = 0.30
		_add_mi(b, tm,
			Vector3(sin(angle) * 0.21, -0.22 - (i % 2) * 0.04, cos(angle) * 0.21),
			_make_mat(_color, 0.55),
			Vector3(0.52 + (i % 3) * 0.18, 0.0, sin(angle) * 0.55))

	# Orbiting chaos orbs
	for i in range(5):
		var angle := i * (PI * 2.0 / 5.0)
		var orb := SphereMesh.new()
		orb.radius = 0.062
		orb.height = 0.12
		_add_mi(b, orb,
			Vector3(sin(angle) * 0.44, 0.08 + cos(angle * 2.0) * 0.22, cos(angle) * 0.44),
			_make_mat(_color, 1.7))


func _setup_mechanical(b: MeshInstance3D) -> void:
	var box := BoxMesh.new()
	box.size = Vector3(0.42, 0.48, 0.30)
	b.mesh = box
	b.material_override = _make_mat(_color, 1.0, 0.75, 0.22)

	# Head unit
	var head := BoxMesh.new()
	head.size = Vector3(0.33, 0.20, 0.26)
	_add_mi(b, head, Vector3(0, 0.34, 0))

	# Visor — bright emissive strip across the face
	var visor := BoxMesh.new()
	visor.size = Vector3(0.27, 0.055, 0.30)
	_add_mi(b, visor, Vector3(0, 0.355, 0.01), _make_mat(_color, 3.2, 0.0, 0.05))

	# Shoulder pauldrons
	for side in [-1, 1]:
		var pld := BoxMesh.new()
		pld.size = Vector3(0.13, 0.17, 0.18)
		_add_mi(b, pld, Vector3(side * 0.275, 0.20, 0.0), _make_mat(_color, 0.85, 0.88, 0.1))

	# Arms + hands
	for side in [-1, 1]:
		var arm := BoxMesh.new()
		arm.size = Vector3(0.10, 0.27, 0.10)
		_add_mi(b, arm, Vector3(side * 0.295, 0.05, 0.0))
		var hand := BoxMesh.new()
		hand.size = Vector3(0.11, 0.075, 0.14)
		_add_mi(b, hand, Vector3(side * 0.295, -0.10, 0.03))

	# Glowing chest panel
	var panel := BoxMesh.new()
	panel.size = Vector3(0.26, 0.17, 0.34)
	_add_mi(b, panel, Vector3(0, 0.04, 0.0), _make_mat(_color, 2.0, 0.55, 0.18))

	# Antenna + tip
	var ant := CapsuleMesh.new()
	ant.radius = 0.022
	ant.height = 0.18
	_add_mi(b, ant, Vector3(0.09, 0.50, 0.0))
	var tip := SphereMesh.new()
	tip.radius = 0.038
	_add_mi(b, tip, Vector3(0.09, 0.61, 0.0), _make_mat(_color, 3.5))


func _setup_humanoid(b: MeshInstance3D) -> void:
	# Torso box (replaces default capsule)
	var torso := BoxMesh.new()
	torso.size = Vector3(0.30, 0.30, 0.19)
	b.mesh = torso
	b.material_override = _make_mat(_color)

	# Hips
	var hips := BoxMesh.new()
	hips.size = Vector3(0.26, 0.13, 0.17)
	_add_mi(b, hips, Vector3(0, -0.22, 0.0))

	# Legs + boots
	for side in [-1, 1]:
		var leg := CapsuleMesh.new()
		leg.radius = 0.068
		leg.height = 0.28
		_add_mi(b, leg, Vector3(side * 0.095, -0.37, 0.0))
		var boot := BoxMesh.new()
		boot.size = Vector3(0.10, 0.075, 0.13)
		_add_mi(b, boot, Vector3(side * 0.095, -0.535, 0.02))

	# Arms + hands
	for side in [-1, 1]:
		var arm := CapsuleMesh.new()
		arm.radius = 0.054
		arm.height = 0.25
		_add_mi(b, arm, Vector3(side * 0.21, -0.03, 0.0), null,
			Vector3(0.0, 0.0, side * 0.14))
		var hand := SphereMesh.new()
		hand.radius = 0.065
		_add_mi(b, hand, Vector3(side * 0.23, -0.175, 0.0))

	# Neck + head (slightly brighter emission to draw the eye)
	var neck := CapsuleMesh.new()
	neck.radius = 0.058
	neck.height = 0.092
	_add_mi(b, neck, Vector3(0, 0.185, 0.0))
	var head := SphereMesh.new()
	head.radius = 0.165
	head.height = 0.30
	_add_mi(b, head, Vector3(0, 0.34, 0.0), _make_mat(_color, 1.55))


# ─── Per-race overrides ────────────────────────────────────────────────

func _apply_race_overrides(b: MeshInstance3D) -> void:
	match _race_id:

		# ── COSMIC ────────────────────────────────────────────────────
		"voidwraith":
			b.material_override.emission_energy_multiplier = 3.5
			b.material_override.transparency = StandardMaterial3D.TRANSPARENCY_ALPHA
			b.material_override.albedo_color = Color(_color.r, _color.g, _color.b, 0.25)

		"nullshade":  # formless shadow — flat wisp, dark tendrils
			b.scale = Vector3(1.0, 0.6, 1.0)
			b.material_override.transparency = StandardMaterial3D.TRANSPARENCY_ALPHA
			b.material_override.albedo_color = Color(0.05, 0.05, 0.1, 0.5)
			for i in range(5):
				var angle := i * (PI * 2.0 / 5.0)
				var wisp := CapsuleMesh.new()
				wisp.radius = 0.03
				wisp.height = 0.4
				_add_mi(b, wisp,
					Vector3(sin(angle) * 0.15, -0.3, cos(angle) * 0.15),
					_make_mat(_color, 0.5),
					Vector3(sin(angle) * 0.7, 0.0, cos(angle) * 0.7))

		"ironlocust":  # chitinous swarm — insect spikes radiating out
			for i in range(8):
				var angle := i * (PI / 4.0)
				var spike := PrismMesh.new()
				spike.size = Vector3(0.06, 0.30, 0.06)
				_add_mi(b, spike,
					Vector3(sin(angle) * 0.22, 0.05 + (i % 3) * 0.12, cos(angle) * 0.22),
					_make_mat(_color, 2.0),
					Vector3(sin(angle) * 0.6, 0.0, cos(angle) * 0.4))

		"embervein":  # magma leviathan — massive, cracked with fire
			b.scale = Vector3(1.45, 1.2, 1.45)
			b.material_override.emission_energy_multiplier = 2.0
			for i in range(4):  # magma crack lines
				var angle := i * (PI / 2.0)
				var crack := BoxMesh.new()
				crack.size = Vector3(0.04, 0.55, 0.04)
				_add_mi(b, crack, Vector3(sin(angle) * 0.18, 0.0, cos(angle) * 0.18),
					_make_mat(Color(1.0, 0.3, 0.0), 3.5))

		"riftwalker":  # phase-hunter — ghost duplicate offset behind
			var ghost := MeshInstance3D.new()
			ghost.mesh = b.mesh
			var gmat := StandardMaterial3D.new()
			gmat.transparency = StandardMaterial3D.TRANSPARENCY_ALPHA
			gmat.albedo_color = Color(_color.r, _color.g, _color.b, 0.22)
			gmat.emission_enabled = true
			gmat.emission = _color
			gmat.emission_energy_multiplier = 0.4
			ghost.material_override = gmat
			ghost.position = Vector3(0.18, 0.0, -0.1)
			ghost.scale = Vector3(0.88, 0.88, 0.88)
			b.add_child(ghost)

		# ── PRIMAL ────────────────────────────────────────────────────
		"solarlord":  # celestial avian — large wings + solar crown
			var wing_mat := _make_mat(Color(1.0, 0.92, 0.15), 1.8)
			for side in [-1, 1]:
				for seg in range(3):
					var wing := BoxMesh.new()
					wing.size = Vector3(0.38 - seg * 0.08, 0.04, 0.22 - seg * 0.06)
					_add_mi(b, wing,
						Vector3(side * (0.32 + seg * 0.22), 0.12 - seg * 0.08, 0.0),
						wing_mat,
						Vector3(0.0, 0.0, side * (0.25 + seg * 0.18)))
			for i in range(8):  # solar crown
				var angle := i * (PI / 4.0)
				var ray := PrismMesh.new()
				ray.size = Vector3(0.035, 0.26, 0.035)
				_add_mi(b, ray, Vector3(sin(angle) * 0.27, 0.38, cos(angle) * 0.27),
					_make_mat(Color(1.0, 0.95, 0.2), 3.2))

		"thornmimic":  # bark shapeshifter — thorn protrusions everywhere
			for i in range(10):
				var angle := i * (PI / 5.0)
				var thorn := PrismMesh.new()
				thorn.size = Vector3(0.05, 0.18 + (i % 3) * 0.06, 0.05)
				_add_mi(b, thorn,
					Vector3(sin(angle) * 0.24, -0.1 + (i % 4) * 0.15, cos(angle) * 0.24),
					_make_mat(_color, 1.4),
					Vector3(sin(angle) * 0.5, 0.0, cos(angle + PI / 3.0) * 0.5))

		"cinderkin":  # fire sprite — SMALL, crystalline cluster head
			b.scale = Vector3(0.62, 0.62, 0.62)
			for i in range(6):
				var angle := i * (PI / 3.0)
				var crystal := PrismMesh.new()
				crystal.size = Vector3(0.07, 0.22, 0.07)
				_add_mi(b, crystal,
					Vector3(sin(angle) * 0.18, 0.38, cos(angle) * 0.18),
					_make_mat(Color(1.0, 0.7, 0.1), 3.0))

		"deeptyrant":  # cephalopod mind — tentacle crown on head
			for i in range(8):
				var angle := i * (PI / 4.0)
				var tent := CapsuleMesh.new()
				tent.radius = 0.038
				tent.height = 0.28
				_add_mi(b, tent,
					Vector3(sin(angle) * 0.22, 0.22, cos(angle) * 0.22),
					_make_mat(_color, 0.8),
					Vector3(-0.6, 0.0, sin(angle) * 0.4))

		"grimcrow":  # obsidian oracle — crow wings + beak
			var wing_mat := _make_mat(Color(0.05, 0.05, 0.08), 0.6)
			for side in [-1, 1]:
				var wing := BoxMesh.new()
				wing.size = Vector3(0.48, 0.32, 0.04)
				_add_mi(b, wing, Vector3(side * 0.35, 0.08, -0.05), wing_mat,
					Vector3(0.3, 0.0, side * 0.55))
			var beak := PrismMesh.new()
			beak.size = Vector3(0.06, 0.16, 0.06)
			_add_mi(b, beak, Vector3(0, 0.34, 0.18), _make_mat(Color(0.1, 0.08, 0.0), 0.5),
				Vector3(PI / 2.0, 0.0, 0.0))

		# ── ELDRITCH ──────────────────────────────────────────────────
		"bloodweaver":  # vampire — tall/thin, swept cape wings
			b.scale = Vector3(0.82, 1.22, 0.82)
			var cape_mat := _make_mat(Color(0.25, 0.0, 0.0), 0.5)
			for side in [-1, 1]:
				var cape := BoxMesh.new()
				cape.size = Vector3(0.38, 0.55, 0.04)
				_add_mi(b, cape, Vector3(side * 0.28, -0.05, -0.08), cape_mat,
					Vector3(0.2, 0.0, side * 0.6))
			var fang_mat := _make_mat(Color(0.9, 0.9, 0.95), 0.8)
			for side in [-1, 1]:
				var fang := PrismMesh.new()
				fang.size = Vector3(0.04, 0.1, 0.04)
				_add_mi(b, fang, Vector3(side * 0.05, 0.28, 0.16), fang_mat,
					Vector3(-0.3, 0.0, 0.0))

		"dreamhusk":  # spore entity — mushroom cap head, spore tendrils
			var cap := CylinderMesh.new()
			cap.top_radius    = 0.0
			cap.bottom_radius = 0.36
			cap.height        = 0.18
			_add_mi(b, cap, Vector3(0, 0.42, 0), _make_mat(_color, 0.9))
			for i in range(6):
				var angle := i * (PI / 3.0)
				var spore := CapsuleMesh.new()
				spore.radius = 0.022
				spore.height = 0.22
				_add_mi(b, spore,
					Vector3(sin(angle) * 0.28, 0.3, cos(angle) * 0.28),
					_make_mat(_color, 0.5),
					Vector3(sin(angle) * 0.4, 0.0, cos(angle) * 0.3))

		"bonedrifter":  # bone construct — rib cage protrusions + horns
			for side in [-1, 1]:
				for i in range(3):
					var rib := CapsuleMesh.new()
					rib.radius = 0.025
					rib.height = 0.22
					_add_mi(b, rib,
						Vector3(side * 0.18, 0.05 - i * 0.1, 0.0),
						_make_mat(Color(0.9, 0.88, 0.82), 0.5),
						Vector3(0.0, 0.0, side * (0.7 + i * 0.1)))
			for side in [-1, 1]:
				var horn := PrismMesh.new()
				horn.size = Vector3(0.05, 0.2, 0.05)
				_add_mi(b, horn, Vector3(side * 0.1, 0.5, 0.0),
					_make_mat(Color(0.9, 0.88, 0.82), 0.6))

		"mindspider":  # translucent arachnid — 8 legs + ghostly body
			b.material_override.transparency = StandardMaterial3D.TRANSPARENCY_ALPHA
			b.material_override.albedo_color  = Color(_color.r, _color.g, _color.b, 0.55)
			for i in range(8):
				var angle := i * (PI / 4.0)
				var leg := CapsuleMesh.new()
				leg.radius = 0.025
				leg.height = 0.26
				_add_mi(b, leg,
					Vector3(sin(angle) * 0.24, -0.1, cos(angle) * 0.24),
					_make_mat(_color, 0.9),
					Vector3(0.55, 0.0, angle))

		"chaosling":  # wild mage — deliberately asymmetric
			b.scale = Vector3(1.0, 1.0, 1.0)
			var lopsided := BoxMesh.new()
			lopsided.size = Vector3(0.22, 0.28, 0.18)
			_add_mi(b, lopsided, Vector3(0.18, 0.08, 0.0), _make_mat(_color, 1.8))
			var chaos_orb := SphereMesh.new()
			chaos_orb.radius = 0.1
			_add_mi(b, chaos_orb, Vector3(-0.22, 0.22, 0.0), _make_mat(Color(1, 0.1, 0.8), 2.5))

		# ── MECHANICAL ────────────────────────────────────────────────
		"ironveil":  # gossamer thin construct — very flat
			b.scale = Vector3(1.4, 1.0, 0.18)
			b.material_override.emission_energy_multiplier = 2.2
			b.material_override.metallic  = 0.95
			b.material_override.roughness = 0.05

		"forgespawn":  # liquid metal — fluid rounded blob shape
			var blob := SphereMesh.new()
			blob.radius = 0.38
			blob.height = 0.72
			b.mesh = blob
			b.material_override = _make_mat(_color, 1.5, 0.9, 0.12)
			var puddle := CylinderMesh.new()
			puddle.top_radius    = 0.42
			puddle.bottom_radius = 0.46
			puddle.height        = 0.06
			_add_mi(b, puddle, Vector3(0, -0.35, 0), _make_mat(_color, 0.8, 0.85, 0.15))

		"cinderplate":  # furnace guard — massive heavy armor
			b.scale = Vector3(1.6, 1.0, 1.6)
			b.material_override = _make_mat(_color, 1.2, 0.85, 0.15)
			for side in [-1, 1]:
				var plate := BoxMesh.new()
				plate.size = Vector3(0.18, 0.45, 0.38)
				_add_mi(b, plate, Vector3(side * 0.36, 0.0, 0.0),
					_make_mat(_color, 0.6, 0.9, 0.1))
			var exhaust := CylinderMesh.new()
			exhaust.top_radius = 0.07
			exhaust.bottom_radius = 0.07
			exhaust.height = 0.22
			_add_mi(b, exhaust, Vector3(0, 0.46, 0), _make_mat(Color(1.0, 0.3, 0.0), 2.5))

		"hexgear":  # modular 6-sided — hexagonal plates
			b.mesh = CylinderMesh.new()
			(b.mesh as CylinderMesh).top_radius = 0.28
			(b.mesh as CylinderMesh).bottom_radius = 0.28
			(b.mesh as CylinderMesh).height = 0.6
			(b.mesh as CylinderMesh).radial_segments = 6
			b.material_override = _make_mat(_color, 1.4, 0.72, 0.2)
			for i in range(3):
				var hex := CylinderMesh.new()
				hex.top_radius = 0.18
				hex.bottom_radius = 0.18
				hex.height = 0.06
				hex.radial_segments = 6
				_add_mi(b, hex, Vector3(0, -0.08 + i * 0.22, 0),
					_make_mat(_color, 2.0 - i * 0.3))

		"wirewraith":  # exposed-nerve construct — wiry extensions
			b.material_override.metallic              = 0.98
			b.material_override.roughness             = 0.04
			b.material_override.emission_energy_multiplier = 2.5
			for i in range(12):
				var angle := i * (PI / 6.0)
				var wire := CapsuleMesh.new()
				wire.radius = 0.012
				wire.height = 0.38 + (i % 3) * 0.1
				_add_mi(b, wire,
					Vector3(sin(angle) * 0.2, 0.1 + (i % 4) * 0.08, cos(angle) * 0.2),
					_make_mat(_color, 2.8),
					Vector3(sin(angle) * 0.8, 0.0, cos(angle) * 0.8))

		# ── HUMANOID — ELF VARIANTS (tall, slender, pointed ears) ────
		"hollowsong", "ashcrown":  # High Elf / Elf base — tallest, most upright
			b.scale = Vector3(0.80, 1.22, 0.80)
			for side in [-1, 1]:
				var ear := PrismMesh.new()
				ear.size = Vector3(0.035, 0.14, 0.035)
				_add_mi(b, ear, Vector3(side * 0.17, 0.42, 0.0),
					b.material_override)
			if _race_id == "ashcrown":  # crown of rays
				for i in range(6):
					var angle := i * (PI / 3.0)
					var ray := PrismMesh.new()
					ray.size = Vector3(0.03, 0.16, 0.03)
					_add_mi(b, ray, Vector3(sin(angle) * 0.14, 0.52, cos(angle) * 0.14),
						_make_mat(_color, 2.5))
			if _race_id == "hollowsong":  # inner magic leaking from chest
				var leak := SphereMesh.new()
				leak.radius = 0.12
				_add_mi(b, leak, Vector3(0, 0.08, 0.12), _make_mat(_color, 3.5))
				b.material_override.transparency = StandardMaterial3D.TRANSPARENCY_ALPHA
				b.material_override.albedo_color = Color(_color.r, _color.g, _color.b, 0.78)

		"veilborn":  # Dark Elf — medium, shadowy veil, glowing eyes
			b.scale = Vector3(0.86, 1.12, 0.86)
			b.material_override.transparency = StandardMaterial3D.TRANSPARENCY_ALPHA
			b.material_override.albedo_color  = Color(_color.r, _color.g, _color.b, 0.72)
			for side in [-1, 1]:
				var ear := PrismMesh.new()
				ear.size = Vector3(0.03, 0.12, 0.03)
				_add_mi(b, ear, Vector3(side * 0.16, 0.39, 0.0), b.material_override)
			for side in [-1, 1]:  # glowing eyes
				var eye := SphereMesh.new()
				eye.radius = 0.035
				_add_mi(b, eye, Vector3(side * 0.06, 0.38, 0.15),
					_make_mat(Color(0.8, 0.0, 1.0), 3.5))

		"thornweft":  # Wood Elf — bark growths, branch protrusions
			b.scale = Vector3(0.88, 1.08, 0.88)
			for side in [-1, 1]:
				var ear := PrismMesh.new()
				ear.size = Vector3(0.03, 0.11, 0.03)
				_add_mi(b, ear, Vector3(side * 0.16, 0.37, 0.0), b.material_override)
			for i in range(6):
				var angle := i * (PI / 3.0)
				var thorn := PrismMesh.new()
				thorn.size = Vector3(0.04, 0.12, 0.04)
				_add_mi(b, thorn,
					Vector3(sin(angle) * 0.2, -0.05 + (i % 2) * 0.15, cos(angle) * 0.2),
					_make_mat(_color, 1.2),
					Vector3(sin(angle) * 0.5, 0.0, cos(angle) * 0.4))
			var branch := CapsuleMesh.new()  # shoulder branch
			branch.radius = 0.03
			branch.height = 0.28
			_add_mi(b, branch, Vector3(0.24, 0.24, 0.0), _make_mat(_color, 1.0),
				Vector3(0.0, 0.0, PI / 3.5))

		# ── HUMANOID — DWARF VARIANTS (short, wide, dense) ────────────
		"ironfast":  # Dwarf — stocky, with beard
			b.scale = Vector3(1.38, 0.74, 1.38)
			var beard := BoxMesh.new()
			beard.size = Vector3(0.22, 0.18, 0.1)
			_add_mi(b, beard, Vector3(0.0, 0.22, 0.12), _make_mat(_color, 0.6))
			for side in [-1, 1]:  # thick gauntlets
				var gaunt := BoxMesh.new()
				gaunt.size = Vector3(0.14, 0.1, 0.14)
				_add_mi(b, gaunt, Vector3(side * 0.24, -0.2, 0.0),
					_make_mat(_color, 1.0, 0.8, 0.2))

		"coreborn":  # Deep Dwarf — stocky + crystal shoulder growths
			b.scale = Vector3(1.32, 0.76, 1.32)
			for side in [-1, 1]:
				for i in range(3):
					var crystal := PrismMesh.new()
					crystal.size = Vector3(0.06, 0.18 - i * 0.04, 0.06)
					_add_mi(b, crystal,
						Vector3(side * (0.22 + i * 0.04), 0.16 - i * 0.06, 0.0),
						_make_mat(_color, 2.0 - i * 0.4))

		# ── HUMANOID — OTHER ──────────────────────────────────────────
		"ashenborn":  # charred human — flame crest from head + shoulders
			for i in range(5):
				var angle := i * (PI / 2.5)
				var flame := PrismMesh.new()
				flame.size = Vector3(0.05, 0.22 + (i % 2) * 0.08, 0.05)
				_add_mi(b, flame,
					Vector3(sin(angle) * 0.12, 0.42 + (i % 2) * 0.04, cos(angle) * 0.12),
					_make_mat(Color(1.0, 0.4, 0.0), 3.0))
			b.material_override.albedo_color = Color(0.08, 0.06, 0.05)

		"warpbred":  # warped — asymmetric scale and extra limb
			b.scale = Vector3(1.12, 0.94, 0.88)
			var extra := CapsuleMesh.new()
			extra.radius = 0.05
			extra.height = 0.24
			_add_mi(b, extra, Vector3(-0.3, 0.1, 0.12), _make_mat(_color, 1.0),
				Vector3(0.5, 0.4, -0.3))

		"splitblood":  # half-and-half — second color on right side
			var half := BoxMesh.new()
			half.size = Vector3(0.16, 0.35, 0.22)
			_add_mi(b, half, Vector3(0.08, 0.0, 0.0),
				_make_mat(Color(0.8, 0.1, 0.1), 1.4))

		"glitchkin":  # glitch artifact — offset ghost copy
			var ghost := MeshInstance3D.new()
			ghost.mesh = b.mesh
			var gmat := StandardMaterial3D.new()
			gmat.transparency = StandardMaterial3D.TRANSPARENCY_ALPHA
			gmat.albedo_color = Color(_color.r, _color.g, _color.b, 0.3)
			gmat.emission_enabled = true
			gmat.emission = Color(0.0, 1.0, 0.8)
			gmat.emission_energy_multiplier = 1.5
			ghost.material_override = gmat
			ghost.position = Vector3(0.12, 0.04, 0.0)
			b.add_child(ghost)

		"fractureline":  # cracked — dark fracture lines on body
			for i in range(4):
				var angle := i * (PI / 2.0)
				var crack := BoxMesh.new()
				crack.size = Vector3(0.02, 0.38, 0.02)
				_add_mi(b, crack, Vector3(sin(angle) * 0.15, 0.0, cos(angle) * 0.15),
					_make_mat(Color(0.0, 0.0, 0.0), 0.0))

		"emberpact":  # ember pact — burning fists
			for side in [-1, 1]:
				for i in range(3):
					var ember := PrismMesh.new()
					ember.size = Vector3(0.04, 0.12, 0.04)
					_add_mi(b, ember,
						Vector3(side * (0.22 + i * 0.03), -0.22, 0.04),
						_make_mat(Color(1.0, 0.5, 0.0), 3.0),
						Vector3(-0.4 + i * 0.2, 0.0, 0.0))

		"fallenlight":  # fallen divine — faded halo ring above head
			var halo := CylinderMesh.new()
			halo.top_radius    = 0.2
			halo.bottom_radius = 0.2
			halo.height        = 0.018
			_add_mi(b, halo, Vector3(0, 0.55, 0),
				_make_mat(Color(1.0, 0.95, 0.6), 1.2))
			b.material_override.albedo_color = Color(0.3, 0.28, 0.22)  # faded

		"scaleworn":  # scaled — hexagonal scale bumps on torso
			b.material_override.metallic  = 0.4
			b.material_override.roughness = 0.55
			for i in range(8):
				var angle := i * (PI / 4.0)
				var scale_bump := SphereMesh.new()
				scale_bump.radius = 0.05
				scale_bump.height = 0.06
				_add_mi(b, scale_bump,
					Vector3(sin(angle) * 0.18, -0.05 + (i % 2) * 0.12, cos(angle) * 0.18),
					_make_mat(_color, 0.8, 0.5, 0.4))

		"duskweft":  # twilight elf — dim with fading edges
			b.scale = Vector3(0.9, 1.06, 0.9)
			b.material_override.emission_energy_multiplier = 0.5
			b.material_override.transparency = StandardMaterial3D.TRANSPARENCY_ALPHA
			b.material_override.albedo_color = Color(_color.r, _color.g, _color.b, 0.65)
			for side in [-1, 1]:
				var ear := PrismMesh.new()
				ear.size = Vector3(0.03, 0.10, 0.03)
				_add_mi(b, ear, Vector3(side * 0.16, 0.36, 0.0), b.material_override)
