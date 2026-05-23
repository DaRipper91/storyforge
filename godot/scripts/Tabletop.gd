extends Node3D

@onready var ground_mesh = $Ground
@onready var camera = $Camera3D

# character_id → Sprite3D node
var _miniatures: Dictionary = {}

const CELL_SIZE = 1.0
const MINI_HEIGHT = 1.0

func _ready():
	var python_client = get_node_or_null("/root/PythonClient")
	if python_client:
		python_client.state_updated.connect(_on_state_updated)

func _on_state_updated(new_state: Dictionary):
	var characters = new_state.get("characters", [])
	for char_data in characters:
		var cid: String = char_data.get("id", "")
		var pos = char_data.get("position", {"x": 0, "y": 0})
		var race_id: String = char_data.get("race", "ashenborn")

		if cid in _miniatures:
			_move_miniature(cid, Vector2(pos.x, pos.y))
		else:
			spawn_miniature(cid, Vector2(pos.x, pos.y), race_id)

func spawn_miniature(character_id: String, grid_pos: Vector2, race_id: String) -> Sprite3D:
	var sprite = Sprite3D.new()
	sprite.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	sprite.pixel_size = 0.005
	sprite.shaded = true

	var portrait_path = "res://assets/characters/" + race_id + ".png"
	if ResourceLoader.exists(portrait_path):
		sprite.texture = load(portrait_path)

	sprite.position = Vector3(
		grid_pos.x * CELL_SIZE,
		MINI_HEIGHT,
		grid_pos.y * CELL_SIZE
	)

	add_child(sprite)
	_miniatures[character_id] = sprite
	return sprite

func _move_miniature(character_id: String, grid_pos: Vector2):
	var sprite: Sprite3D = _miniatures[character_id]
	var tween = create_tween()
	tween.tween_property(sprite, "position", Vector3(
		grid_pos.x * CELL_SIZE,
		MINI_HEIGHT,
		grid_pos.y * CELL_SIZE
	), 0.3).set_trans(Tween.TRANS_SINE)
