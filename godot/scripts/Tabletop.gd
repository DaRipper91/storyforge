extends Node3D

@onready var ground_mesh     = $Ground
@onready var camera          = $Camera3D
@onready var table_lantern   = $TableLantern
@onready var particles_root  = $ParticlesRoot

# ─── Miniatures ─────────────────────────────────────────────────────
var _miniatures: Dictionary = {}
const CELL_SIZE  = 1.0
const MINI_HEIGHT = 1.0

# ─── Camera gimbal ──────────────────────────────────────────────────
var _cam_yaw:      float = 0.0       # degrees — 0 = looking along -Z
var _cam_pitch:    float = -45.0     # degrees — matches original isometric
var _cam_distance: float = 14.14    # sqrt(10²+10²), matches original
var _cam_target:   Vector3 = Vector3.ZERO
var _is_orbiting:  bool = false
var _last_mouse:   Vector2 = Vector2.ZERO

# ─── Lantern flicker ────────────────────────────────────────────────
const _LANTERN_BASE  = 2.5
var _flicker_t: float = 0.0

# ─── Particle scenes ────────────────────────────────────────────────
var _paradox_scene:    PackedScene = null
var _magic_burst_scene: PackedScene = null

# ─── Lifecycle ──────────────────────────────────────────────────────

func _ready():
	var pc = get_node_or_null("/root/PythonClient")
	if pc:
		pc.state_updated.connect(_on_state_updated)

	_update_camera()

	if ResourceLoader.exists("res://scenes/ParadoxParticles.tscn"):
		_paradox_scene = load("res://scenes/ParadoxParticles.tscn")
	if ResourceLoader.exists("res://scenes/MagicBurst.tscn"):
		_magic_burst_scene = load("res://scenes/MagicBurst.tscn")


func _process(delta: float):
	_flicker_t += delta
	# Two overlapping sine waves give organic irregular flicker
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

	# R = reset to default isometric view
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


# ─── State / miniatures ─────────────────────────────────────────────

func _on_state_updated(new_state: Dictionary):
	var characters = new_state.get("characters", [])
	for char_data in characters:
		var cid:    String = char_data.get("id", "")
		var pos            = char_data.get("position", {"x": 0, "y": 0})
		var race_id: String = char_data.get("race", "ashenborn")

		if cid in _miniatures:
			_move_miniature(cid, Vector2(pos.x, pos.y))
		else:
			spawn_miniature(cid, Vector2(pos.x, pos.y), race_id)


func spawn_miniature(character_id: String, grid_pos: Vector2, race_id: String) -> Sprite3D:
	var sprite = Sprite3D.new()
	sprite.billboard   = BaseMaterial3D.BILLBOARD_ENABLED
	sprite.pixel_size  = 0.005
	sprite.shaded      = true

	var path = "res://assets/characters/" + race_id + ".png"
	if ResourceLoader.exists(path):
		sprite.texture = load(path)

	sprite.position = _grid_to_world(grid_pos)
	add_child(sprite)
	_miniatures[character_id] = sprite
	return sprite


func _move_miniature(character_id: String, grid_pos: Vector2):
	var sprite: Sprite3D = _miniatures[character_id]
	var target = _grid_to_world(grid_pos)
	var tween  = create_tween()
	tween.tween_property(sprite, "position", target, 0.3).set_trans(Tween.TRANS_SINE)
	spawn_magic_burst(target)


func _grid_to_world(grid_pos: Vector2) -> Vector3:
	return Vector3(grid_pos.x * CELL_SIZE, MINI_HEIGHT, grid_pos.y * CELL_SIZE)


# ─── Particles ──────────────────────────────────────────────────────

func spawn_paradox_glitch(world_pos: Vector3):
	_spawn_particles(_paradox_scene, world_pos)


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
