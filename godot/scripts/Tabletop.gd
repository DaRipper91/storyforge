extends Node3D

# This script manages the 3D Tabletop scene, subscribing to state updates
# from the PythonClient and spawning/moving 2.5D miniatures accordingly.

@onready var ground_mesh = $Ground
@onready var camera = $Camera3D

func _ready():
	# Connect to the Python bridge (assuming it's loaded as an autoload or parent)
	var python_client = get_node_or_null("/root/PythonClient")
	if python_client:
		python_client.state_updated.connect(_on_state_updated)

func _on_state_updated(new_state: Dictionary):
	print("Tabletop received new state: ", new_state.get("phase", "unknown"))
	# Here we will iterate over characters and NPCs, spawning or tweening them.
	pass

# Helper to spawn a 2.5D billboard character
func spawn_miniature(character_id: String, position: Vector2, sprite_key: String):
	pass
