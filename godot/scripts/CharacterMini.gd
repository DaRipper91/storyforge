extends Node3D

# Represents a 2.5D Miniature on the Tabletop.
# Smoothly interpolates to its target position and maintains billboard orientation.

@onready var sprite: Sprite3D = $Sprite3D
var target_position: Vector3 = Vector3.ZERO

func _ready():
	# Initial position sync
	target_position = global_position

func _process(delta: float):
	# Smoothly tween toward the target position
	if global_position.distance_to(target_position) > 0.01:
		global_position = global_position.lerp(target_position, 10.0 * delta)

func move_to(grid_x: int, grid_y: int):
	# Assuming grid cells are 2x2 units
	target_position = Vector3(grid_x * 2.0, 0.0, grid_y * 2.0)
	
func set_sprite(texture_path: String):
	# Load and assign the texture
	pass
