extends Node3D

@onready var ground_mesh     = $Ground
@onready var camera          = $Camera3D
@onready var table_lantern   = $TableLantern
@onready var particles_root  = $ParticlesRoot

# ─── Miniatures ─────────────────────────────────────────────────────
var _miniatures: Dictionary = {}
const CELL_SIZE   = 1.0
const MINI_Y      = 0.05   # sits on top of floor tile

# ─── Dungeon geometry ───────────────────────────────────────────────
var _dungeon_root: Node3D = null
var _current_room_id: String = ""

# Shared materials (created once, reused)
var _mat_wall:    StandardMaterial3D = null
var _mat_floor:   StandardMaterial3D = null
var _mat_door:    StandardMaterial3D = null
var _mat_hazard:  StandardMaterial3D = null

# Race group → emissive color for miniature glow
const RACE_COLORS: Dictionary = {
	"Cosmic":    Color(0.2, 0.4, 1.0),
	"Primal":    Color(0.1, 0.8, 0.2),
	"Eldritch":  Color(0.7, 0.1, 0.9),
	"Mechanical":Color(1.0, 0.5, 0.1),
	"Humanoid":  Color(1.0, 0.85, 0.6),
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

# ─── Camera gimbal ──────────────────────────────────────────────────
var _cam_yaw:      float = 0.0
var _cam_pitch:    float = -45.0
var _cam_distance: float = 14.14
var _cam_target:   Vector3 = Vector3.ZERO
var _is_orbiting:  bool = false
var _last_mouse:   Vector2 = Vector2.ZERO

# ─── Lantern flicker ────────────────────────────────────────────────
const _LANTERN_BASE  = 2.5
var _flicker_t: float = 0.0

# ─── Particle scenes ────────────────────────────────────────────────
var _paradox_scene:     PackedScene = null
var _magic_burst_scene: PackedScene = null


# ─── Lifecycle ──────────────────────────────────────────────────────

func _ready():
	_build_materials()

	_dungeon_root = Node3D.new()
	_dungeon_root.name = "DungeonRoot"
	add_child(_dungeon_root)

	# Hide flat ground until we have room data; show it as fallback
	ground_mesh.visible = true

	var pc = get_node_or_null("/root/PythonClient")
	if pc:
		pc.state_updated.connect(_on_state_updated)
		pc.paradox_triggered.connect(_on_paradox_triggered)
		pc.phase_changed.connect(_on_phase_changed)
		pc.npc_event_received.connect(_on_npc_event)
		pc.particle_event_received.connect(_on_particle_event)

	_update_camera()

	if ResourceLoader.exists("res://scenes/ParadoxParticles.tscn"):
		_paradox_scene = load("res://scenes/ParadoxParticles.tscn")
	if ResourceLoader.exists("res://scenes/MagicBurst.tscn"):
		_magic_burst_scene = load("res://scenes/MagicBurst.tscn")

	AudioManager.play_ambient("res://assets/audio/ambient_keep.wav")


func _build_materials():
	_mat_wall = StandardMaterial3D.new()
	_mat_wall.albedo_color = Color(0.28, 0.25, 0.22)
	_mat_wall.roughness = 0.9
	_mat_wall.metallic = 0.0

	_mat_floor = StandardMaterial3D.new()
	_mat_floor.albedo_color = Color(0.55, 0.50, 0.44)
	_mat_floor.roughness = 0.85

	_mat_door = StandardMaterial3D.new()
	_mat_door.albedo_color = Color(0.45, 0.28, 0.12)
	_mat_door.roughness = 0.75
	_mat_door.emission_enabled = true
	_mat_door.emission = Color(0.5, 0.3, 0.0)
	_mat_door.emission_energy_multiplier = 0.6

	_mat_hazard = StandardMaterial3D.new()
	_mat_hazard.albedo_color = Color(0.6, 0.1, 0.0)
	_mat_hazard.roughness = 0.8
	_mat_hazard.emission_enabled = true
	_mat_hazard.emission = Color(1.0, 0.1, 0.0)
	_mat_hazard.emission_energy_multiplier = 0.8


func _process(delta: float):
	_flicker_t += delta
	var flicker = sin(_flicker_t * 7.3) * 0.09 + sin(_flicker_t * 13.7) * 0.05
	table_lantern.light_energy = _LANTERN_BASE + flicker


# ─── Camera input ───────────────────────────────────────────────────

func _input(event: InputEvent):
	if event is InputEventMouseButton:
		match event.button_index:
			MOUSE_BUTTON_RIGHT:
				_is_orbiting = event.pressed
				if event.pressed:
					_last_mouse = event.position
			MOUSE_BUTTON_WHEEL_UP:
				_cam_distance = max(5.0, _cam_distance - 1.2)
				_update_camera()
			MOUSE_BUTTON_WHEEL_DOWN:
				_cam_distance = min(30.0, _cam_distance + 1.2)
				_update_camera()

	if event is InputEventMouseMotion and _is_orbiting:
		var d = event.position - _last_mouse
		_cam_yaw   -= d.x * 0.25
		_cam_pitch  = clamp(_cam_pitch - d.y * 0.2, -82.0, -8.0)
		_last_mouse = event.position
		_update_camera()

	if event is InputEventKey and event.pressed and event.keycode == KEY_R:
		_cam_yaw      = 0.0
		_cam_pitch    = -45.0
		_cam_distance = 14.14
		_cam_target   = Vector3.ZERO
		_update_camera()


func _update_camera():
	var yaw   = deg_to_rad(_cam_yaw)
	var pitch = deg_to_rad(_cam_pitch)
	var cp    = cos(pitch)
	var offset = Vector3(
		_cam_distance * cp * sin(yaw),
		_cam_distance * -sin(pitch),
		_cam_distance * cp * cos(yaw)
	)
	camera.position = _cam_target + offset
	camera.look_at(_cam_target, Vector3.UP)


# ─── Dungeon geometry ───────────────────────────────────────────────

func _rebuild_room(state: Dictionary):
	var room_id: String = state.get("current_room_id", "")
	if room_id == _current_room_id:
		return
	_current_room_id = room_id

	# Clear previous geometry
	for child in _dungeon_root.get_children():
		child.queue_free()

	var rooms = state.get("rooms", {})
	if not room_id in rooms:
		ground_mesh.visible = true
		return

	ground_mesh.visible = false

	var room: Dictionary = rooms[room_id]
	var w: int = room.get("width", 10)
	var h: int = room.get("height", 10)
	var cells: Array = room.get("cells", [])

	var wall_mesh   = BoxMesh.new()
	wall_mesh.size  = Vector3(CELL_SIZE, 2.5, CELL_SIZE)

	var floor_mesh  = BoxMesh.new()
	floor_mesh.size = Vector3(CELL_SIZE, 0.12, CELL_SIZE)

	var door_mesh   = BoxMesh.new()
	door_mesh.size  = Vector3(CELL_SIZE * 0.6, 2.2, 0.12)

	var hazard_mesh = BoxMesh.new()
	hazard_mesh.size = Vector3(CELL_SIZE, 0.12, CELL_SIZE)

	for y in range(h):
		for x in range(w):
			var idx = y * w + x
			var cell: Dictionary = cells[idx] if idx < cells.size() else {}
			var terrain: String = cell.get("terrain", "floor")
			var wx: float = x * CELL_SIZE
			var wz: float = y * CELL_SIZE

			var inst = MeshInstance3D.new()
			match terrain:
				"wall":
					inst.mesh = wall_mesh
					inst.material_override = _mat_wall
					inst.position = Vector3(wx, 1.25, wz)
				"door":
					# Floor tile under the door
					var floor_inst = MeshInstance3D.new()
					floor_inst.mesh = floor_mesh
					floor_inst.material_override = _mat_floor
					floor_inst.position = Vector3(wx, -0.06, wz)
					_dungeon_root.add_child(floor_inst)
					# Door frame
					inst.mesh = door_mesh
					inst.material_override = _mat_door
					inst.position = Vector3(wx, 1.1, wz)
				"hazard":
					inst.mesh = hazard_mesh
					inst.material_override = _mat_hazard
					inst.position = Vector3(wx, -0.06, wz)
				_:
					inst.mesh = floor_mesh
					inst.material_override = _mat_floor
					inst.position = Vector3(wx, -0.06, wz)

			_dungeon_root.add_child(inst)

	# Center camera on room
	_cam_target = Vector3((w - 1) * CELL_SIZE * 0.5, 0.0, (h - 1) * CELL_SIZE * 0.5)
	_cam_distance = max(w, h) * 0.9 + 4.0
	_update_camera()


# ─── State / miniatures ─────────────────────────────────────────────

func _on_state_updated(new_state: Dictionary):
	_rebuild_room(new_state)

	var characters = new_state.get("characters", [])
	for char_data in characters:
		var cid:     String = char_data.get("id", "")
		var pos             = char_data.get("position", {"x": 0, "y": 0})
		var race_id: String = char_data.get("race", "ashenborn")

		if cid in _miniatures:
			_move_miniature(cid, Vector2(pos.x, pos.y))
		else:
			spawn_miniature(cid, Vector2(pos.x, pos.y), race_id)


func spawn_miniature(character_id: String, grid_pos: Vector2, race_id: String) -> Node3D:
	var root = Node3D.new()
	root.name = "Mini_" + character_id

	# Body — capsule
	var body_inst = MeshInstance3D.new()
	var body_mesh = CapsuleMesh.new()
	body_mesh.radius = 0.18
	body_mesh.height = 0.55
	body_inst.mesh = body_mesh
	body_inst.position = Vector3(0.0, 0.38, 0.0)

	# Head — sphere
	var head_inst = MeshInstance3D.new()
	var head_mesh = SphereMesh.new()
	head_mesh.radius = 0.15
	head_mesh.height = 0.30
	head_inst.mesh = head_mesh
	head_inst.position = Vector3(0.0, 0.82, 0.0)

	# Material — race-group color with emissive glow
	var group: String = RACE_GROUP.get(race_id, "Humanoid")
	var glow_color: Color = RACE_COLORS.get(group, Color(1.0, 0.85, 0.6))

	var mat = StandardMaterial3D.new()
	mat.albedo_color = glow_color.darkened(0.35)
	mat.roughness = 0.6
	mat.metallic = 0.15
	mat.emission_enabled = true
	mat.emission = glow_color
	mat.emission_energy_multiplier = 0.9

	body_inst.material_override = mat
	head_inst.material_override = mat

	root.add_child(body_inst)
	root.add_child(head_inst)
	root.position = _grid_to_world(grid_pos)
	add_child(root)
	_miniatures[character_id] = root
	return root


func _move_miniature(character_id: String, grid_pos: Vector2):
	var mini: Node3D = _miniatures[character_id]
	var target = _grid_to_world(grid_pos)
	var tween  = create_tween()
	tween.tween_property(mini, "position", target, 0.3).set_trans(Tween.TRANS_SINE)
	spawn_magic_burst(target)
	AudioManager.play_sfx("res://assets/audio/sfx_move.wav")


func _grid_to_world(grid_pos: Vector2) -> Vector3:
	return Vector3(grid_pos.x * CELL_SIZE, MINI_Y, grid_pos.y * CELL_SIZE)


# ─── Particles ──────────────────────────────────────────────────────

func spawn_paradox_glitch(world_pos: Vector3):
	_spawn_particles(_paradox_scene, world_pos)
	AudioManager.play_sfx("res://assets/audio/sfx_paradox_glitch.wav")


func spawn_magic_burst(world_pos: Vector3):
	_spawn_particles(_magic_burst_scene, world_pos)


func _spawn_particles(scene: PackedScene, world_pos: Vector3):
	if scene == null:
		return
	var inst: GPUParticles3D = scene.instantiate()
	particles_root.add_child(inst)
	inst.global_position = world_pos
	inst.emitting = true
	var timer = get_tree().create_timer(inst.lifetime + 0.2)
	timer.timeout.connect(inst.queue_free)


# ─── Event handlers ─────────────────────────────────────────────────

func _on_paradox_triggered(_transformed_ids: Array):
	for cid in _miniatures:
		spawn_paradox_glitch(_miniatures[cid].global_position)
	AudioManager.play_sfx("res://assets/audio/sfx_paradox_glitch.wav")
	AudioManager.play_ambient("res://assets/audio/ambient_paradox.wav")


func _on_phase_changed(phase: String):
	match phase:
		"LOBBY":       AudioManager.play_ambient("res://assets/audio/ambient_inn.wav")
		"CREATION":    AudioManager.play_ambient("res://assets/audio/ambient_keep.wav")
		"EXPLORATION": AudioManager.play_ambient("res://assets/audio/ambient_wilderness.wav")


func _on_npc_event(ev: Dictionary):
	var npc    = ev.get("npc", "")
	var action = ev.get("action", "")
	match npc + "/" + action:
		"haylie/entrance":
			spawn_magic_burst(Vector3.ZERO)
			AudioManager.play_sfx("res://assets/audio/sfx_haylie_entrance.wav")
		"danna/boon_granted", "redvelvet/boon_granted":
			spawn_magic_burst(Vector3.ZERO)
			AudioManager.play_sfx("res://assets/audio/sfx_boon_granted.wav")
		"redvelvet/tip":
			AudioManager.play_sfx("res://assets/audio/sfx_tip_silver.wav")
		"redvelvet/heckle":
			AudioManager.play_sfx("res://assets/audio/sfx_heckle.wav")
		"jon/cactus":
			AudioManager.play_sfx("res://assets/audio/sfx_cactus.wav")
		"kodrik/dispatch":
			spawn_magic_burst(Vector3(3.0, 0.5, 3.0))


func _on_particle_event(ev: Dictionary):
	var pos  = ev.get("position", {"x": 0, "y": 0})
	var wpos = _grid_to_world(Vector2(pos.get("x", 0), pos.get("y", 0)))
	match ev.get("effect", "magic_burst"):
		"magic_burst":    spawn_magic_burst(wpos)
		"paradox_glitch": spawn_paradox_glitch(wpos)
