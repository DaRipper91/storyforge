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

	# Normalize race_id
	race_id = race_id.to_lower().replace(" ", "_")

	var color := Color(1, 1, 1)
	
	# Clear out the default mesh
	mesh_instance.mesh = null
	for child in mesh_instance.get_children():
		child.queue_free()

	# ─── BUILD UNIQUE MESH ───
	match race_id:
		# COSMIC
		"voidwraith":  _build_voidwraith(); color = Color(0.1, 0.05, 0.3)
		"nullshade":   _build_nullshade();  color = Color(0.2, 0.2, 0.2)
		"ironlocust":  _build_ironlocust(); color = Color(0.4, 0.4, 0.5)
		"embervein":   _build_embervein();  color = Color(0.8, 0.2, 0.0)
		"riftwalker":  _build_riftwalker(); color = Color(0.3, 0.1, 0.6)
		
		# PRIMAL
		"solarlord":   _build_solarlord();  color = Color(1.0, 0.9, 0.4)
		"thornmimic":  _build_thornmimic(); color = Color(0.2, 0.5, 0.1)
		"cinderkin":   _build_cinderkin();  color = Color(0.9, 0.4, 0.1)
		"deeptyrant":  _build_deeptyrant(); color = Color(0.1, 0.3, 0.4)
		"grimcrow":    _build_grimcrow();   color = Color(0.15, 0.15, 0.2)
		
		# ELDRITCH
		"bloodweaver": _build_bloodweaver();color = Color(0.6, 0.0, 0.1)
		"dreamhusk":   _build_dreamhusk();  color = Color(0.7, 0.5, 0.8)
		"bonedrifter": _build_bonedrifter();color = Color(0.9, 0.85, 0.75)
		"mindspider":  _build_mindspider(); color = Color(0.5, 0.2, 0.5)
		"chaosling":   _build_chaosling();  color = Color(0.4, 0.8, 0.9)
		
		# MECHANICAL
		"ironveil":    _build_ironveil();   color = Color(0.6, 0.6, 0.65)
		"forgespawn":  _build_forgespawn(); color = Color(0.5, 0.3, 0.2)
		"cinderplate": _build_cinderplate();color = Color(0.4, 0.4, 0.4)
		"hexgear":     _build_hexgear();    color = Color(0.7, 0.5, 0.1)
		"wirewraith":  _build_wirewraith(); color = Color(0.0, 1.0, 0.8)
		
		# HUMANOID
		"ashenborn":   _build_humanoid_mesh(); color = Color(0.4, 0.45, 0.55)
		"hollowsong":  _build_hollowsong(); color = Color(0.5, 0.6, 0.8)
		"veilborn":    _build_veilborn();   color = Color(0.2, 0.1, 0.3)
		"thornweft":   _build_thornweft();  color = Color(0.3, 0.4, 0.2)
		"ashcrown":    _build_ashcrown();   color = Color(0.9, 0.8, 0.5)
		"ironfast":    _build_ironfast();   color = Color(0.5, 0.5, 0.6)
		"coreborn":    _build_coreborn();   color = Color(0.4, 0.7, 1.0)
		"warpbred":    _build_warpbred();   color = Color(0.6, 0.4, 0.7)
		"splitblood":  _build_splitblood(); color = Color(0.7, 0.1, 0.2)
		"duskweft":    _build_duskweft();   color = Color(0.4, 0.3, 0.5)
		"glitchkin":   _build_glitchkin();  color = Color(0.0, 0.8, 0.5)
		"fractureline":_build_fractureline();color = Color(0.8, 0.8, 0.8)
		"emberpact":   _build_emberpact();  color = Color(1.0, 0.5, 0.0)
		"fallenlight": _build_fallenlight(); color = Color(0.95, 0.95, 1.0)
		"scaleworn":   _build_scaleworn();  color = Color(0.3, 0.6, 0.2)
		
		_:
			if is_enemy:
				_build_humanoid_mesh()
				color = Color(0.8, 0.2, 0.2)
			else:
				_build_humanoid_mesh()
				color = Color(0.3, 0.5, 0.8)

	_material.set_shader_parameter("albedo", color)
	_material.set_shader_parameter("rim_color", color * 1.5)

func _add_part(mesh: Mesh, pos: Vector3, rot: Vector3 = Vector3.ZERO, scale: Vector3 = Vector3.ONE) -> void:
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.material_override = _material
	mi.position = pos
	mi.rotation = rot
	mi.scale = scale
	mesh_instance.add_child(mi)

# ─── COSMIC BUILDERS ───

func _build_voidwraith():
	var core = SphereMesh.new(); core.radius = 0.3; core.height = 0.6
	_add_part(core, Vector3(0, 1.0, 0))
	var shard = BoxMesh.new(); shard.size = Vector3(0.1, 0.4, 0.1)
	for i in range(5):
		var angle = i * TAU / 5.0
		_add_part(shard, Vector3(cos(angle)*0.5, 1.0 + sin(angle*2.0)*0.2, sin(angle)*0.5), Vector3(angle, angle, 0))

func _build_nullshade():
	var body = CapsuleMesh.new(); body.radius = 0.15; body.height = 1.8
	_add_part(body, Vector3(0, 0.9, 0))
	var eye = SphereMesh.new(); eye.radius = 0.05; eye.height = 0.1
	for i in range(3):
		_add_part(eye, Vector3(0, 1.4 + i*0.15, 0.15))

func _build_ironlocust():
	var body = BoxMesh.new(); body.size = Vector3(0.4, 0.3, 0.8)
	_add_part(body, Vector3(0, 0.5, 0))
	var leg = CylinderMesh.new(); leg.top_radius = 0.02; leg.bottom_radius = 0.02; leg.height = 0.6
	for i in range(6):
		var side = 1 if i % 2 == 0 else -1
		_add_part(leg, Vector3(0.3 * side, 0.3, (i/2 - 1) * 0.3), Vector3(0, 0, 0.5 * side))

func _build_embervein():
	var body = BoxMesh.new(); body.size = Vector3(0.6, 1.2, 0.6)
	_add_part(body, Vector3(0, 0.6, 0))
	var crack = BoxMesh.new(); crack.size = Vector3(0.7, 0.1, 0.7)
	for i in range(4):
		_add_part(crack, Vector3(0, 0.3 + i*0.3, 0), Vector3(0, i*0.8, 0))

func _build_riftwalker():
	var half = CapsuleMesh.new(); half.radius = 0.2; half.height = 1.4
	_add_part(half, Vector3(0.2, 0.7, 0))
	_add_part(half, Vector3(-0.2, 0.7, 0))

# ─── PRIMAL BUILDERS ───

func _build_solarlord():
	_build_humanoid_mesh()
	var halo = TorusMesh.new(); halo.inner_radius = 0.4; halo.outer_radius = 0.5
	_add_part(halo, Vector3(0, 1.5, -0.2), Vector3(PI/2, 0, 0))

func _build_thornmimic():
	var body = CylinderMesh.new(); body.top_radius = 0.1; body.bottom_radius = 0.3; body.height = 1.4
	_add_part(body, Vector3(0, 0.7, 0))
	var thorn = PrismMesh.new(); thorn.size = Vector3(0.1, 0.2, 0.1)
	for i in range(12):
		_add_part(thorn, Vector3(0, i*0.1, 0.2).rotated(Vector3.UP, i*2.1), Vector3(1.5, i*2.1, 0))

func _build_cinderkin():
	var body = CapsuleMesh.new(); body.radius = 0.3; body.height = 0.8
	_add_part(body, Vector3(0, 0.4, 0), Vector3(1.2, 0, 0))
	var flame = ConeMesh.new(); flame.top_radius = 0.0; flame.bottom_radius = 0.2; flame.height = 0.4
	_add_part(flame, Vector3(0, 0.8, -0.2), Vector3(-0.5, 0, 0))

func _build_deeptyrant():
	var head = SphereMesh.new(); head.radius = 0.5; head.height = 0.8
	_add_part(head, Vector3(0, 1.0, 0))
	var tentacle = CylinderMesh.new(); tentacle.top_radius = 0.05; tentacle.bottom_radius = 0.1; tentacle.height = 0.8
	for i in range(8):
		var angle = i * TAU / 8.0
		_add_part(tentacle, Vector3(cos(angle)*0.4, 0.4, sin(angle)*0.4), Vector3(0.4, angle, 0))

func _build_grimcrow():
	var body = CapsuleMesh.new(); body.radius = 0.25; body.height = 1.2
	_add_part(body, Vector3(0, 0.6, 0))
	var beak = ConeMesh.new(); beak.top_radius = 0.0; beak.bottom_radius = 0.05; beak.height = 0.3
	_add_part(beak, Vector3(0, 1.3, 0.2), Vector3(PI/2, 0, 0))

# ─── ELDRITCH BUILDERS ───

func _build_bloodweaver():
	var body = SphereMesh.new(); body.radius = 0.2; body.height = 0.4
	_add_part(body, Vector3(0, 1.0, 0))
	var leg = CylinderMesh.new(); leg.top_radius = 0.01; leg.bottom_radius = 0.02; leg.height = 1.2
	for i in range(4):
		var angle = i * TAU / 4.0
		_add_part(leg, Vector3(cos(angle)*0.6, 0.5, sin(angle)*0.6), Vector3(0.2, angle, 0))

func _build_dreamhusk():
	var cloak = ConeMesh.new(); cloak.top_radius = 0.1; cloak.bottom_radius = 0.5; cloak.height = 1.6
	_add_part(cloak, Vector3(0, 0.8, 0))
	var eye = SphereMesh.new(); eye.radius = 0.1; eye.height = 0.1
	_add_part(eye, Vector3(0, 1.4, 0.1))

func _build_bonedrifter():
	var bone = BoxMesh.new(); bone.size = Vector3(0.2, 0.1, 0.1)
	for i in range(10):
		_add_part(bone, Vector3(randf_range(-0.3, 0.3), i*0.15, randf_range(-0.3, 0.3)), Vector3(randf()*TAU, randf()*TAU, 0))

func _build_mindspider():
	var brain = SphereMesh.new(); brain.radius = 0.4; brain.height = 0.6
	_add_part(brain, Vector3(0, 1.2, 0))
	var leg = CylinderMesh.new(); leg.top_radius = 0.02; leg.bottom_radius = 0.02; leg.height = 1.0
	for i in range(3):
		var angle = i * TAU / 3.0
		_add_part(leg, Vector3(cos(angle)*0.4, 0.5, sin(angle)*0.4), Vector3(0.3, angle, 0))

func _build_chaosling():
	var shapes = [BoxMesh.new(), SphereMesh.new(), CylinderMesh.new(), PrismMesh.new()]
	for i in range(5):
		var s = shapes[i % 4]
		_add_part(s, Vector3(randf_range(-0.4, 0.4), i*0.3, randf_range(-0.4, 0.4)), Vector3(randf()*TAU, randf()*TAU, 0), Vector3.ONE * 0.3)

# ─── MECHANICAL BUILDERS ───

func _build_ironveil():
	var body = BoxMesh.new(); body.size = Vector3(0.7, 1.3, 0.5)
	_add_part(body, Vector3(0, 0.65, 0))
	var visor = BoxMesh.new(); visor.size = Vector3(0.5, 0.1, 0.1)
	_add_part(visor, Vector3(0, 1.4, 0.25))

func _build_forgespawn():
	var body = BoxMesh.new(); body.size = Vector3(0.8, 1.0, 0.8)
	_add_part(body, Vector3(0, 0.5, 0))
	var hammer = BoxMesh.new(); hammer.size = Vector3(0.4, 0.4, 0.8)
	_add_part(hammer, Vector3(0.6, 0.8, 0.3), Vector3(0, 0.4, 0))

func _build_cinderplate():
	var body = CylinderMesh.new(); body.top_radius = 0.35; body.bottom_radius = 0.35; body.height = 1.2
	_add_part(body, Vector3(0, 0.6, 0))
	var vent = BoxMesh.new(); vent.size = Vector3(0.1, 0.1, 0.1)
	for i in range(4):
		_add_part(vent, Vector3(0, 0.2 + i*0.2, 0.35))

func _build_hexgear():
	var body = CylinderMesh.new(); body.top_radius = 0.3; body.bottom_radius = 0.3; body.height = 0.4; body.radial_segments = 6
	_add_part(body, Vector3(0, 0.8, 0), Vector3(PI/2, 0, 0))
	var wheel = CylinderMesh.new(); wheel.top_radius = 0.2; wheel.bottom_radius = 0.2; wheel.height = 0.1
	_add_part(wheel, Vector3(0.3, 0.2, 0), Vector3(0, 0, PI/2))
	_add_part(wheel, Vector3(-0.3, 0.2, 0), Vector3(0, 0, PI/2))

func _build_wirewraith():
	var wire = CylinderMesh.new(); wire.top_radius = 0.01; wire.bottom_radius = 0.01; wire.height = 1.6
	for i in range(8):
		_add_part(wire, Vector3(randf_range(-0.2, 0.2), 0.8, randf_range(-0.2, 0.2)), Vector3(0, i*0.5, 0.1))

# ─── HUMANOID BUILDERS (SPECIFIC) ───

func _build_hollowsong():
	_build_humanoid_mesh()
	var ear = BoxMesh.new(); ear.size = Vector3(0.05, 0.4, 0.1)
	_add_part(ear, Vector3(0.25, 1.5, 0), Vector3(0, 0, -0.4))
	_add_part(ear, Vector3(-0.25, 1.5, 0), Vector3(0, 0, 0.4))

func _build_veilborn():
	var cloak = ConeMesh.new(); cloak.top_radius = 0.05; cloak.bottom_radius = 0.45; cloak.height = 1.7
	_add_part(cloak, Vector3(0, 0.85, 0))

func _build_thornweft():
	_build_humanoid_mesh()
	var vine = CylinderMesh.new(); vine.top_radius = 0.02; vine.bottom_radius = 0.02; vine.height = 0.8
	_add_part(vine, Vector3(0.3, 0.8, 0.2), Vector3(0.5, 0.5, 0))
	_add_part(vine, Vector3(-0.3, 1.0, -0.2), Vector3(-0.5, -0.5, 0))

func _build_ashcrown():
	_build_humanoid_mesh()
	var horn = ConeMesh.new(); horn.top_radius = 0.0; horn.bottom_radius = 0.05; horn.height = 0.4
	_add_part(horn, Vector3(0.15, 1.6, 0), Vector3(0, 0, -0.5))
	_add_part(horn, Vector3(-0.15, 1.6, 0), Vector3(0, 0, 0.5))

func _build_ironfast():
	var body = BoxMesh.new(); body.size = Vector3(0.8, 1.2, 0.4)
	_add_part(body, Vector3(0, 0.6, 0))
	var head = BoxMesh.new(); head.size = Vector3(0.3, 0.3, 0.3)
	_add_part(head, Vector3(0, 1.3, 0))

func _build_coreborn():
	_build_humanoid_mesh()
	var core = SphereMesh.new(); core.radius = 0.15; core.height = 0.3
	_add_part(core, Vector3(0, 0.9, 0.25))

func _build_warpbred():
	var body = CapsuleMesh.new(); body.radius = 0.3; body.height = 1.4
	_add_part(body, Vector3(0.1, 0.7, 0), Vector3(0, 0, 0.2))

func _build_splitblood():
	var side = CapsuleMesh.new(); side.radius = 0.15; side.height = 1.4
	_add_part(side, Vector3(0.15, 0.7, 0))
	_add_part(side, Vector3(-0.15, 0.7, 0))

func _build_duskweft():
	var body = CapsuleMesh.new(); body.radius = 0.3; body.height = 1.5
	_add_part(body, Vector3(0, 0.75, 0))
	# We can't easily change transparency per instance with override, 
	# but we can use scale to make it look "thin"
	mesh_instance.scale = Vector3(0.8, 1.0, 0.5)

func _build_glitchkin():
	var body = BoxMesh.new(); body.size = Vector3(0.5, 1.4, 0.5)
	_add_part(body, Vector3(0, 0.7, 0), Vector3(0.2, 0.2, 0.2))

func _build_fractureline():
	var block = BoxMesh.new(); block.size = Vector3(0.3, 0.3, 0.3)
	_add_part(block, Vector3(0, 0.2, 0))
	_add_part(block, Vector3(0.1, 0.6, 0.1))
	_add_part(block, Vector3(-0.1, 1.0, -0.1))
	_add_part(block, Vector3(0, 1.4, 0))

func _build_emberpact():
	_build_humanoid_mesh()
	var hair = ConeMesh.new(); hair.top_radius = 0.0; hair.bottom_radius = 0.2; hair.height = 0.6
	_add_part(hair, Vector3(0, 1.6, 0))

func _build_fallenlight():
	_build_humanoid_mesh()
	var eye = SphereMesh.new(); eye.radius = 0.05; eye.height = 0.1
	_add_part(eye, Vector3(0.1, 1.4, 0.2))
	_add_part(eye, Vector3(-0.1, 1.4, 0.2))

func _build_scaleworn():
	_build_humanoid_mesh()
	var tail = CylinderMesh.new(); tail.top_radius = 0.01; tail.bottom_radius = 0.1; tail.height = 0.8
	_add_part(tail, Vector3(0, 0.4, -0.4), Vector3(-1.0, 0, 0))

# ─── UTILS ───

func _build_humanoid_mesh() -> void:
	var body := CapsuleMesh.new()
	body.radius = 0.35
	body.height = 1.3
	_add_part(body, Vector3(0, 0.65, 0))
	var head := SphereMesh.new()
	head.radius = 0.25
	head.height = 0.5
	_add_part(head, Vector3(0, 1.4, 0))

func move_with_input(input_dir: Vector3, delta: float, look_at_pos: Vector3 = Vector3.ZERO) -> void:
	if input_dir.length() > 0.1:
		velocity = input_dir * move_speed
		# Smooth rotation
		var target_quat: Quaternion
		if look_at_pos != Vector3.ZERO:
			var dir_to_target = global_position.direction_to(look_at_pos)
			dir_to_target.y = 0
			if dir_to_target.length_squared() > 0.01:
				target_quat = Quaternion(Basis.looking_at(dir_to_target))
			else:
				target_quat = Quaternion(Basis.looking_at(input_dir))
		else:
			target_quat = Quaternion(Basis.looking_at(input_dir))
			
		quaternion = quaternion.slerp(target_quat, rotation_speed * delta)
		play_walk()
	else:
		velocity = velocity.move_toward(Vector3.ZERO, move_speed * 10.0 * delta)
		if look_at_pos != Vector3.ZERO:
			var dir_to_target = global_position.direction_to(look_at_pos)
			dir_to_target.y = 0
			if dir_to_target.length_squared() > 0.01:
				var target_quat = Quaternion(Basis.looking_at(dir_to_target))
				quaternion = quaternion.slerp(target_quat, rotation_speed * delta)
	
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
	var tw := create_tween()
	tw.tween_property(mesh_instance, "position:y", 0.2, 0.1)
	tw.tween_property(mesh_instance, "position:y", 0.0, 0.1)
