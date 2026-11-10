extends RefCounted
## Small, non-blocking architectural props for Ironhold's keep courtyard. They reinforce the
## seeded signal-bell quest and the training-yard description without changing grid movement.

const WOOD: Material = preload("res://assets/materials/wood_planks.tres")
const DARK_WOOD: Material = preload("res://assets/materials/wood_dark.tres")
const METAL := Color("#554b3b")
const BRONZE := Color("#98703a")
const ROPE := Color("#9a8157")
const STRAW := Color("#8f7650")
const LANTERN_GLOW := Color("#ffc875")


static func populate(parent: Node3D, room_id: String, room_width: int, room_height: int) -> void:
	if room_id != "keep_courtyard" or room_width < 8 or room_height < 8:
		return
	var details := Node3D.new()
	details.name = "KeepCourtyardDetails"
	parent.add_child(details)
	_add_signal_bell(details, room_width, room_height)
	_add_supply_crates(details)
	_add_training_dummy(details)
	_add_wall_lantern(details, room_width, room_height)


static func _add_signal_bell(parent: Node3D, room_width: int, room_height: int) -> void:
	var x := float(room_width) - 1.8
	var z := float(room_height) * 0.5
	_piece(parent, "BellBacking", _box(Vector3(0.52, 0.58, 0.14)), DARK_WOOD,
		Vector3(x, 2.06, z))
	_piece(parent, "BellCrossbar", _box(Vector3(0.82, 0.09, 0.18)), DARK_WOOD,
		Vector3(x, 2.42, z))
	for side in [-1.0, 1.0]:
		_piece(parent, "BellHanger", _box(Vector3(0.07, 0.38, 0.10)), _mat(METAL, 0.56, 0.62),
			Vector3(x + side * 0.28, 2.20, z))
	var bell := CylinderMesh.new()
	bell.top_radius = 0.105
	bell.bottom_radius = 0.18
	bell.height = 0.24
	bell.radial_segments = 16
	_piece(parent, "BronzeSignalBell", bell, _mat(BRONZE, 0.34, 0.72), Vector3(x, 1.91, z))
	var rim := TorusMesh.new()
	rim.inner_radius = 0.155
	rim.outer_radius = 0.18
	rim.rings = 8
	rim.ring_segments = 16
	_piece(parent, "BellMouthRim", rim, _mat(BRONZE.lightened(0.12), 0.3, 0.78),
		Vector3(x, 1.80, z))
	var clapper := SphereMesh.new()
	clapper.radius = 0.045
	clapper.height = 0.09
	_piece(parent, "BellClapper", clapper, _mat(METAL.darkened(0.2), 0.48, 0.8),
		Vector3(x, 1.73, z))


static func _add_supply_crates(parent: Node3D) -> void:
	var crate_a := _box(Vector3(0.58, 0.52, 0.56))
	_piece(parent, "SupplyCrateA", crate_a, WOOD, Vector3(1.1, 0.27, 1.2))
	_piece(parent, "CrateA_Strapping", _box(Vector3(0.61, 0.045, 0.58)), _mat(ROPE, 0.9, 0.0),
		Vector3(1.1, 0.42, 1.2))
	_piece(parent, "SupplyCrateB", _box(Vector3(0.46, 0.42, 0.48)), DARK_WOOD,
		Vector3(1.48, 0.21, 1.42), Vector3(0.0, 0.18, 0.0))
	_piece(parent, "CrateB_CornerIron", _box(Vector3(0.045, 0.44, 0.50)), _mat(METAL, 0.5, 0.72),
		Vector3(1.25, 0.21, 1.42))


static func _add_training_dummy(parent: Node3D) -> void:
	var post := CylinderMesh.new()
	post.top_radius = 0.055
	post.bottom_radius = 0.075
	post.height = 1.45
	post.radial_segments = 10
	_piece(parent, "TrainingPost", post, DARK_WOOD, Vector3(13.8, 0.73, 10.25))
	_piece(parent, "TrainingDummyTorso", _capsule(0.22, 0.62), _mat(STRAW, 0.94, 0.0),
		Vector3(13.8, 1.12, 10.25))
	_piece(parent, "TrainingDummyHead", _sphere(0.17), _mat(ROPE, 0.96, 0.0),
		Vector3(13.8, 1.57, 10.25))
	_piece(parent, "DummyCrossbar", _cylinder(0.035, 0.035, 0.72, 8), DARK_WOOD,
		Vector3(13.8, 1.34, 10.25), Vector3(0.0, 0.0, PI * 0.5))
	_piece(parent, "DummyShoulderWrap", _box(Vector3(0.30, 0.08, 0.26)), _mat(ROPE, 0.94, 0.0),
		Vector3(13.8, 1.42, 10.25))


static func _add_wall_lantern(parent: Node3D, room_width: int, room_height: int) -> void:
	var x := float(room_width) - 1.75
	var z := float(room_height) * 0.5 - 1.3
	_piece(parent, "LanternWallArm", _box(Vector3(0.08, 0.07, 0.42)), _mat(METAL, 0.5, 0.7),
		Vector3(x, 2.15, z))
	_piece(parent, "CourtyardLanternFrame", _box(Vector3(0.16, 0.23, 0.16)), _mat(BRONZE, 0.38, 0.68),
		Vector3(x, 2.0, z))
	_piece(parent, "CourtyardLanternGlass", _box(Vector3(0.09, 0.15, 0.09)), _mat(LANTERN_GLOW, 0.24, 0.0, true),
		Vector3(x - 0.01, 2.0, z))
	var bulb := OmniLight3D.new()
	bulb.name = "CourtyardLanternLight"
	bulb.position = Vector3(x - 0.08, 2.0, z)
	bulb.light_color = LANTERN_GLOW
	bulb.light_energy = 0.45
	bulb.omni_range = 2.2
	bulb.shadow_enabled = false
	parent.add_child(bulb)


static func _piece(parent: Node, label: String, mesh: Mesh, material: Material,
		position: Vector3 = Vector3.ZERO, rotation: Vector3 = Vector3.ZERO) -> MeshInstance3D:
	var instance := MeshInstance3D.new()
	instance.name = label
	instance.mesh = mesh
	instance.material_override = material
	instance.position = position
	instance.rotation = rotation
	parent.add_child(instance)
	return instance


static func _mat(color: Color, roughness: float, metallic: float, glow: bool = false) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.roughness = roughness
	material.metallic = metallic
	if glow:
		material.emission_enabled = true
		material.emission = color
		material.emission_energy_multiplier = 0.8
	return material


static func _box(size: Vector3) -> BoxMesh:
	var mesh := BoxMesh.new()
	mesh.size = size
	return mesh


static func _sphere(radius: float) -> SphereMesh:
	var mesh := SphereMesh.new()
	mesh.radius = radius
	mesh.height = radius * 2.0
	mesh.radial_segments = 10
	mesh.rings = 5
	return mesh


static func _capsule(radius: float, height: float) -> CapsuleMesh:
	var mesh := CapsuleMesh.new()
	mesh.radius = radius
	mesh.height = height
	mesh.radial_segments = 8
	mesh.rings = 4
	return mesh


static func _cylinder(top: float, bottom: float, height: float, sides: int) -> CylinderMesh:
	var mesh := CylinderMesh.new()
	mesh.top_radius = top
	mesh.bottom_radius = bottom
	mesh.height = height
	mesh.radial_segments = sides
	return mesh
