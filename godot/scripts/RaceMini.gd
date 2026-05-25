extends Node3D
class_name RaceMini

@onready var mesh_instance: MeshInstance3D = $MeshInstance3D

var _material: StandardMaterial3D

func _ready() -> void:
	_material = StandardMaterial3D.new()
	_material.albedo_color = Color(1.0, 1.0, 1.0) # Default to white
	mesh_instance.material_override = _material

func setup(race_id: String, entity_name: String = "", is_enemy: bool = false) -> void:
	if not mesh_instance:
		return

	# Determine base color and glow based on race/enemy type
	var color := Color(1, 1, 1)
	
	# Clear out the default mesh on the root MeshInstance3D so we can use children
	mesh_instance.mesh = null
	
	# Clean up any existing children if we are reusing this instance
	for child in mesh_instance.get_children():
		child.queue_free()

	if is_enemy:
		# NPCs/Enemies default to a more menacing red/gray color palette
		color = Color(0.8, 0.2, 0.2)
		if "goblin" in race_id:
			color = Color(0.2, 0.6, 0.2)
			_build_goblin_mesh()
		elif "skeleton" in race_id:
			color = Color(0.9, 0.9, 0.9)
			_build_skeleton_mesh()
		elif "dragon" in race_id:
			color = Color(0.8, 0.1, 0.1)
			_build_large_beast_mesh()
		else:
			_build_humanoid_mesh() # Fallback for enemies
	else:
		# Player race color groups and geometry
		if "void" in race_id:
			color = Color(0.4, 0.2, 0.8)
			_build_ethereal_mesh()
		elif "iron" in race_id or "mech" in race_id:
			color = Color(0.6, 0.6, 0.65)
			_build_mechanical_mesh()
		elif "ember" in race_id or "dragon" in race_id:
			color = Color(0.9, 0.4, 0.1)
			_build_horned_humanoid_mesh()
		elif "elf" in race_id or "sylvan" in race_id or "primal" in race_id:
			color = Color(0.2, 0.8, 0.4)
			_build_slender_humanoid_mesh()
		else:
			color = Color(0.3, 0.5, 0.8) # Default hero color
			_build_humanoid_mesh()
			
	_material.albedo_color = color

func _add_part(mesh: Mesh, pos: Vector3, rot: Vector3 = Vector3.ZERO) -> void:
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.material_override = _material
	mi.position = pos
	mi.rotation = rot
	mesh_instance.add_child(mi)

func _build_humanoid_mesh() -> void:
	# Standard Capsule Body + Sphere Head
	var body := CapsuleMesh.new()
	body.radius = 0.35
	body.height = 1.3
	_add_part(body, Vector3(0, 0.65, 0))
	
	var head := SphereMesh.new()
	head.radius = 0.25
	head.height = 0.5
	_add_part(head, Vector3(0, 1.4, 0))

func _build_slender_humanoid_mesh() -> void:
	# Taller, thinner Capsule Body
	var body := CapsuleMesh.new()
	body.radius = 0.25
	body.height = 1.5
	_add_part(body, Vector3(0, 0.75, 0))
	
	var head := SphereMesh.new()
	head.radius = 0.2
	head.height = 0.4
	_add_part(head, Vector3(0, 1.6, 0))

func _build_horned_humanoid_mesh() -> void:
	_build_humanoid_mesh()
	# Add horns
	var horn := CylinderMesh.new()
	horn.top_radius = 0.01
	horn.bottom_radius = 0.05
	horn.height = 0.3
	_add_part(horn, Vector3(0.15, 1.6, 0.1), Vector3(0.3, 0, 0.3))
	_add_part(horn, Vector3(-0.15, 1.6, 0.1), Vector3(0.3, 0, -0.3))

func _build_mechanical_mesh() -> void:
	# Boxy Body
	var body := BoxMesh.new()
	body.size = Vector3(0.7, 1.2, 0.4)
	_add_part(body, Vector3(0, 0.6, 0))
	
	var head := BoxMesh.new()
	head.size = Vector3(0.4, 0.4, 0.4)
	_add_part(head, Vector3(0, 1.4, 0))

func _build_ethereal_mesh() -> void:
	# Floating Sphere + smaller orbiting spheres (simulating a wisp/trail)
	var core := SphereMesh.new()
	core.radius = 0.4
	core.height = 0.8
	_add_part(core, Vector3(0, 1.0, 0))
	
	var wisp := SphereMesh.new()
	wisp.radius = 0.15
	wisp.height = 0.3
	_add_part(wisp, Vector3(0.4, 0.6, 0.2))
	_add_part(wisp, Vector3(-0.3, 0.4, -0.3))

# --- Enemy specific shapes ---

func _build_goblin_mesh() -> void:
	# Short, wide, big head
	var body := CapsuleMesh.new()
	body.radius = 0.3
	body.height = 0.8
	_add_part(body, Vector3(0, 0.4, 0))
	
	var head := BoxMesh.new()
	head.size = Vector3(0.4, 0.3, 0.4)
	_add_part(head, Vector3(0, 0.9, 0.1))

func _build_skeleton_mesh() -> void:
	# Very thin body
	var body := CylinderMesh.new()
	body.top_radius = 0.1
	body.bottom_radius = 0.1
	body.height = 1.3
	_add_part(body, Vector3(0, 0.65, 0))
	
	var head := SphereMesh.new()
	head.radius = 0.2
	head.height = 0.4
	_add_part(head, Vector3(0, 1.4, 0))

func _build_large_beast_mesh() -> void:
	# Large Boxy Quadruped
	var body := BoxMesh.new()
	body.size = Vector3(1.2, 0.8, 2.0)
	_add_part(body, Vector3(0, 0.6, 0))
	
	var head := BoxMesh.new()
	head.size = Vector3(0.6, 0.6, 0.8)
	_add_part(head, Vector3(0, 1.0, 0.8))


func play_walk() -> void:
	# A simple placeholder animation for movement
	var tw := create_tween()
	tw.tween_property(mesh_instance, "position:y", 1.0, 0.1)
	tw.tween_property(mesh_instance, "position:y", 0.8, 0.1)
