extends Node3D
## NPC / Pet miniature token.
## Loads a .glb from assets/models/ if present; falls back to a colored
## cylinder token. Exposes play_idle/walk/talk/attack/death so callers
## never need to care which rendering path is active.

const MODEL_DIR := "res://assets/models/"

# ── Model routing ────────────────────────────────────────────────────
const NPC_MODEL: Dictionary = {
	"jon":       "humanoid/npc_default",
	"haylie":    "humanoid/npc_default",
	"samael":    "humanoid/npc_mage",
	"danna":     "humanoid/npc_royal",
	"kodrik":    "humanoid/npc_warrior",
	"bryne":     "humanoid/npc_warrior",
	"nathis":    "humanoid/npc_default",
	"redvelvet": "humanoid/npc_performer",
	"mykael":    "animals/bear",
	# Pets
	"keeva":     "animals/dog",
	"teddy":     "animals/dog",
	"coco":      "animals/dog",
	"cole":      "animals/dog",
	"tyty":      "animals/dog",
	"cyrus":     "animals/wolf",
	"bink_bink": "animals/cat",
	"snowie":    "animals/cat",
}

# Scale to fit on a 1-unit grid cell
const SCALE_HUMANOID := Vector3(0.52, 0.52, 0.52)
const SCALE_ANIMAL   := Vector3(0.40, 0.40, 0.40)

# Animation name candidates — first match wins
const ANIM_IDLE   := ["Idle", "Idle_A", "Standing", "idle"]
const ANIM_WALK   := ["Walking", "Walk", "Walk_A",  "walking"]
const ANIM_TALK   := ["Interact", "Talk", "Wave",   "Pickup", "interact"]
const ANIM_ATTACK := ["Attack",   "Slash","Attack_A","attack"]
const ANIM_DEATH  := ["Death",    "Die",  "Fall",    "death"]

# ── State ────────────────────────────────────────────────────────────
var _npc_id:     String = ""
var _color:      Color  = Color(0.7, 0.9, 0.7)
var _is_animal:  bool   = false
var _has_model:  bool   = false

var _anim_player:    AnimationPlayer  = null
var _selection_ring: MeshInstance3D   = null
var _name_label:     Label3D          = null
var _selected:       bool  = false
var _ring_pulse:     float = 0.0
var _bob_time:       float = 0.0
var _proc_body:      Node3D = null   # procedural fallback root


# ── Lifecycle ────────────────────────────────────────────────────────

func _process(delta: float) -> void:
	if _selected and _selection_ring:
		_ring_pulse += delta * 3.0
		var mat := _selection_ring.material_override as StandardMaterial3D
		if mat:
			mat.emission_energy_multiplier = 0.8 + (sin(_ring_pulse) + 1.0) * 0.75

	if not _has_model and _proc_body:
		_bob_time += delta
		_proc_body.position.y = sin(_bob_time * 1.1) * 0.015


# ── Public API ───────────────────────────────────────────────────────

func setup(npc_id: String, display_name: String, color: Color) -> void:
	_npc_id    = npc_id
	_color     = color
	_is_animal = _model_key(npc_id).begins_with("animals/")

	if _try_load_model(npc_id):
		_has_model = true
	else:
		_build_procedural_token()

	_add_name_label(display_name)
	_add_selection_ring()


func play_idle() -> void:
	_play(ANIM_IDLE)

func play_walk() -> void:
	_play(ANIM_WALK)

func play_talk() -> void:
	_play(ANIM_TALK)
	if _anim_player:
		var anim_name := _resolve(ANIM_TALK)
		if not anim_name.is_empty():
			var anim := _anim_player.get_animation(anim_name)
			if anim:
				get_tree().create_timer(anim.get_length()).timeout.connect(play_idle)

func play_attack() -> void:
	_play(ANIM_ATTACK)
	if _anim_player:
		var anim_name := _resolve(ANIM_ATTACK)
		if not anim_name.is_empty():
			var anim := _anim_player.get_animation(anim_name)
			if anim:
				get_tree().create_timer(anim.get_length()).timeout.connect(play_idle)

func play_death() -> void:
	_play(ANIM_DEATH)

func select() -> void:
	_selected = true
	if _selection_ring:
		_selection_ring.visible = true
		_ring_pulse = 0.0

func deselect() -> void:
	_selected = false
	if _selection_ring:
		_selection_ring.visible = false


# ── Model loading ────────────────────────────────────────────────────

func _model_key(npc_id: String) -> String:
	return NPC_MODEL.get(npc_id, "")

func _try_load_model(npc_id: String) -> bool:
	var key := _model_key(npc_id)
	if key.is_empty():
		return false
	# Try exact model, then group fallback for animals/humanoid
	var candidates: Array[String] = [MODEL_DIR + key + ".glb"]
	if key.begins_with("animals/"):
		candidates.append(MODEL_DIR + "animals/dog.glb")
	elif key.begins_with("humanoid/"):
		candidates.append(MODEL_DIR + "humanoid/npc_default.glb")

	for path in candidates:
		if ResourceLoader.exists(path):
			var scene := load(path) as PackedScene
			if not scene:
				continue
			var inst := scene.instantiate()
			inst.scale = SCALE_ANIMAL if _is_animal else SCALE_HUMANOID
			add_child(inst)
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
	var anim_name := _resolve(names)
	if anim_name.is_empty():
		return
	if _anim_player.current_animation != anim_name:
		_anim_player.play(anim_name)


# ── Procedural fallback token ────────────────────────────────────────

func _build_procedural_token() -> void:
	_proc_body = Node3D.new()
	add_child(_proc_body)

	var is_cat := (_npc_id in ["bink_bink", "snowie"])
	var h := 0.28 if (_is_animal or is_cat) else 0.65

	var body_mesh := CylinderMesh.new()
	body_mesh.top_radius    = 0.17 if not _is_animal else 0.20
	body_mesh.bottom_radius = 0.22 if not _is_animal else 0.26
	body_mesh.height        = h
	body_mesh.radial_segments = 12

	var body_mat := StandardMaterial3D.new()
	body_mat.albedo_color = _color
	body_mat.roughness = 0.6
	body_mat.metallic  = 0.05

	var body_inst := MeshInstance3D.new()
	body_inst.mesh = body_mesh
	body_inst.material_override = body_mat
	body_inst.position = Vector3(0, h * 0.5, 0)
	_proc_body.add_child(body_inst)

	# Soft glow ring
	var ring_mesh := CylinderMesh.new()
	ring_mesh.top_radius    = 0.28
	ring_mesh.bottom_radius = 0.28
	ring_mesh.height        = 0.03
	ring_mesh.radial_segments = 16
	var ring_mat := StandardMaterial3D.new()
	ring_mat.albedo_color     = Color(_color.r, _color.g, _color.b, 0.55)
	ring_mat.emission_enabled = true
	ring_mat.emission         = _color * 0.7
	ring_mat.transparency     = BaseMaterial3D.TRANSPARENCY_ALPHA
	var ring_inst := MeshInstance3D.new()
	ring_inst.mesh = ring_mesh
	ring_inst.material_override = ring_mat
	ring_inst.position = Vector3(0, 0.015, 0)
	_proc_body.add_child(ring_inst)


# ── Name label ───────────────────────────────────────────────────────

func _add_name_label(label_text: String) -> void:
	_name_label = Label3D.new()
	_name_label.text             = label_text.replace("_", " ").capitalize()
	_name_label.font_size        = 18
	_name_label.outline_size     = 6
	_name_label.modulate         = _color.lightened(0.25)
	_name_label.outline_modulate = Color(0, 0, 0, 0.9)
	_name_label.billboard        = BaseMaterial3D.BILLBOARD_ENABLED
	_name_label.no_depth_test    = true
	_name_label.position         = Vector3(0, 1.1, 0)
	add_child(_name_label)


# ── Selection ring ───────────────────────────────────────────────────

func _add_selection_ring() -> void:
	_selection_ring = MeshInstance3D.new()
	var ring := CylinderMesh.new()
	ring.top_radius    = 0.50
	ring.bottom_radius = 0.50
	ring.height        = 0.008
	ring.radial_segments = 32
	_selection_ring.mesh = ring
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
