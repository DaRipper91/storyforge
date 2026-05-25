extends CharacterBody3D
class_name RaceMini

@onready var mesh_instance: MeshInstance3D = $MeshInstance3D
@onready var nav_agent: NavigationAgent3D = $NavigationAgent3D

const MiniatureGlowShader = preload("res://assets/shaders/miniature_glow.gdshader")

var _material: ShaderMaterial
var move_speed: float = 5.0
var rotation_speed: float = 10.0

func _ready() -> void:
	_material = ShaderMaterial.new()
	_material.shader = MiniatureGlowShader
	_material.set_shader_parameter("albedo", Color(1.0, 1.0, 1.0))
	_material.set_shader_parameter("rim_color", Color(1.0, 1.0, 1.0))
	_material.set_shader_parameter("rim_intensity", 1.5)
	mesh_instance.material_override = _material

func setup(race_id: String, entity_name: String = "", is_enemy: bool = false) -> void:
	if not mesh_instance:
		return

	var color := Color(1, 1, 1)
	
	# Clear out the default mesh on the root MeshInstance3D so we can use children
	mesh_instance.mesh = null
	
	# Clean up any existing children if we are reusing this instance
	for child in mesh_instance.get_children():
		child.queue_free()

	if is_enemy:
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
			_build_humanoid_mesh()
	else:
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
			color = Color(0.3, 0.5, 0.8)
			_build_humanoid_mesh()
			
	_material.set_shader_parameter("albedo", color)
	_material.set_shader_parameter("rim_color", color * 1.5)

func _add_part(mesh: Mesh, pos: Vector3, rot: Vector3 = Vector3.ZERO) -> void:
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.material_override = _material
	mi.position = pos
	mi.rotation = rot
	mesh_instance.add_child(mi)

func _build_humanoid_mesh() -> void:
	var body := CapsuleMesh.new()
	body.radius = 0.35
	body.height = 1.3
	_add_part(body, Vector3(0, 0.65, 0))
	var head := SphereMesh.new()
	head.radius = 0.25
	head.height = 0.5
	_add_part(head, Vector3(0, 1.4, 0))

func _build_slender_humanoid_mesh() -> void:
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
	var horn := CylinderMesh.new()
	horn.top_radius = 0.01
	horn.bottom_radius = 0.05
	horn.height = 0.3
	_add_part(horn, Vector3(0.15, 1.6, 0.1), Vector3(0.3, 0, 0.3))
	_add_part(horn, Vector3(-0.15, 1.6, 0.1), Vector3(0.3, 0, -0.3))

func _build_mechanical_mesh() -> void:
	var body := BoxMesh.new()
	body.size = Vector3(0.7, 1.2, 0.4)
	_add_part(body, Vector3(0, 0.6, 0))
	var head := BoxMesh.new()
	head.size = Vector3(0.4, 0.4, 0.4)
	_add_part(head, Vector3(0, 1.4, 0))

func _build_ethereal_mesh() -> void:
	var core := SphereMesh.new()
	core.radius = 0.4
	core.height = 0.8
	_add_part(core, Vector3(0, 1.0, 0))
	var wisp := SphereMesh.new()
	wisp.radius = 0.15
	wisp.height = 0.3
	_add_part(wisp, Vector3(0.4, 0.6, 0.2))
	_add_part(wisp, Vector3(-0.3, 0.4, -0.3))

func _build_goblin_mesh() -> void:
	var body := CapsuleMesh.new()
	body.radius = 0.3
	body.height = 0.8
	_add_part(body, Vector3(0, 0.4, 0))
	var head := BoxMesh.new()
	head.size = Vector3(0.4, 0.3, 0.4)
	_add_part(head, Vector3(0, 0.9, 0.1))

func _build_skeleton_mesh() -> void:
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
	var body := BoxMesh.new()
	body.size = Vector3(1.2, 0.8, 2.0)
	_add_part(body, Vector3(0, 0.6, 0))
	var head := BoxMesh.new()
	head.size = Vector3(0.6, 0.6, 0.8)
	_add_part(head, Vector3(0, 1.0, 0.8))

func move_with_input(input_dir: Vector3, delta: float) -> void:
	if input_dir.length() > 0.1:
		velocity = input_dir * move_speed
		# Smooth rotation
		var target_quat = Quaternion(Basis.looking_at(input_dir))
		quaternion = quaternion.slerp(target_quat, rotation_speed * delta)
		play_walk()
	else:
		velocity = velocity.move_toward(Vector3.ZERO, move_speed * 10.0 * delta)
	
	move_and_slide()

func move_towards_target(delta: float) -> void:
	if nav_agent.is_navigation_finished():
		velocity = velocity.move_toward(Vector3.ZERO, move_speed * 10.0 * delta)
		move_and_slide()
		return
	
	var next_path_pos = nav_agent.get_next_path_position()
	var dir = global_position.direction_to(next_path_pos)
	dir.y = 0
	dir = dir.normalized()
	
	velocity = dir * move_speed
	
	if dir.length() > 0.1:
		var target_quat = Quaternion(Basis.looking_at(dir))
		quaternion = quaternion.slerp(target_quat, rotation_speed * delta)
		play_walk()
	
	move_and_slide()

func play_walk() -> void:
	# Keep the bounce for now as a stylized "hop" walk
	var tw := create_tween()
	tw.tween_property(mesh_instance, "position:y", 0.2, 0.1) # Relative hop
	tw.tween_property(mesh_instance, "position:y", 0.0, 0.1)
