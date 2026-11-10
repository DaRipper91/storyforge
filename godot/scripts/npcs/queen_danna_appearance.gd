extends RefCounted
## Appearance pass for Queen D.Anna, grounded in the latest Gemini character sheet.
## Adds sovereign crimson-and-gold regalia and a light-focusing scepter without editing the shared rig.

const CRIMSON := Color("#6d1827")
const CLOAK := Color("#37151d")
const GOLD := Color("#c39a4c")
const DARK_GOLD := Color("#735326")
const HAIR := Color("#38231d")
const LIGHT := Color("#ffdc8a")


static func apply(model: Node3D) -> void:
	_apply_palette(model)
	var skeletons := model.find_children("*", "Skeleton3D", true, false)
	if skeletons.is_empty():
		return
	var skeleton := skeletons[0] as Skeleton3D
	_add_scepter(skeleton)
	_add_sun_signet(skeleton)
	_add_blessing_pouch(skeleton)


static func _apply_palette(model: Node3D) -> void:
	for node in model.find_children("*", "MeshInstance3D", true, false):
		var mesh := node as MeshInstance3D
		match mesh.name:
			"King_Body":
				_set_surface(mesh, 1, _mat(CRIMSON, 0.72, 0.12))
				_set_surface(mesh, 2, _mat(GOLD, 0.38, 0.72))
				_set_surface(mesh, 3, _mat(CLOAK, 0.88, 0.0))
				_set_surface(mesh, 4, _mat(DARK_GOLD, 0.52, 0.55))
			"King_Head":
				_set_surface(mesh, 1, _mat(HAIR, 0.9, 0.0))
			"King_Feet":
				_set_surface(mesh, 0, _mat(CLOAK, 0.86, 0.0))
			"King_Legs":
				_set_surface(mesh, 0, _mat(CLOAK, 0.88, 0.0))
				_set_surface(mesh, 1, _mat(GOLD, 0.45, 0.65))
				_set_surface(mesh, 2, _mat(DARK_GOLD, 0.6, 0.35))


static func _set_surface(mesh: MeshInstance3D, surface: int, material: StandardMaterial3D) -> void:
	if mesh.mesh and surface < mesh.mesh.get_surface_count():
		mesh.set_surface_override_material(surface, material)


static func _mat(color: Color, roughness: float, metallic: float, glow: bool = false) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.roughness = roughness
	material.metallic = metallic
	if glow:
		material.emission_enabled = true
		material.emission = color
		material.emission_energy_multiplier = 0.7
	return material


static func _mount(skeleton: Skeleton3D, bone: String, label: String, offset: Vector3) -> BoneAttachment3D:
	var mount := BoneAttachment3D.new()
	mount.name = label
	mount.bone_name = bone
	mount.position = offset
	skeleton.add_child(mount)
	return mount


static func _piece(parent: Node, label: String, mesh: Mesh, material: StandardMaterial3D,
		position: Vector3 = Vector3.ZERO, rotation: Vector3 = Vector3.ZERO) -> MeshInstance3D:
	var instance := MeshInstance3D.new()
	instance.name = label
	instance.mesh = mesh
	instance.material_override = material
	instance.position = position
	instance.rotation = rotation
	parent.add_child(instance)
	return instance


static func _add_scepter(skeleton: Skeleton3D) -> void:
	var hand := _mount(skeleton, "Hand.L", "SovereignScepterMount", Vector3(0.0, -0.02, 0.035))
	var shaft := CylinderMesh.new()
	shaft.top_radius = 0.014
	shaft.bottom_radius = 0.021
	shaft.height = 0.78
	shaft.radial_segments = 8
	_piece(hand, "ScepterShaft", shaft, _mat(DARK_GOLD, 0.44, 0.68), Vector3(0.0, 0.19, 0.0))
	var pommel := SphereMesh.new()
	pommel.radius = 0.035
	pommel.height = 0.07
	_piece(hand, "ScepterPommel", pommel, _mat(GOLD, 0.32, 0.78), Vector3(0.0, -0.22, 0.0))
	var focus := SphereMesh.new()
	focus.radius = 0.068
	focus.height = 0.136
	focus.radial_segments = 12
	focus.rings = 6
	_piece(hand, "MercyLightFocus", focus, _mat(LIGHT, 0.22, 0.08, true), Vector3(0.0, 0.61, 0.0))
	var halo := TorusMesh.new()
	halo.inner_radius = 0.078
	halo.outer_radius = 0.092
	halo.rings = 6
	halo.ring_segments = 12
	_piece(hand, "ScepterHalo", halo, _mat(GOLD, 0.28, 0.72), Vector3(0.0, 0.61, 0.0), Vector3(PI * 0.5, 0.0, 0.0))


static func _add_sun_signet(skeleton: Skeleton3D) -> void:
	var chest := _mount(skeleton, "Chest", "SovereignSignetMount", Vector3(0.0, 0.08, 0.13))
	var disk := CylinderMesh.new()
	disk.top_radius = 0.055
	disk.bottom_radius = 0.055
	disk.height = 0.016
	disk.radial_segments = 12
	_piece(chest, "GoldSunSignet", disk, _mat(GOLD, 0.34, 0.75), Vector3.ZERO, Vector3(PI * 0.5, 0.0, 0.0))
	var core := SphereMesh.new()
	core.radius = 0.025
	core.height = 0.05
	_piece(chest, "SignetLight", core, _mat(LIGHT, 0.25, 0.1, true), Vector3(0.0, 0.0, 0.018))


static func _add_blessing_pouch(skeleton: Skeleton3D) -> void:
	var hip := _mount(skeleton, "Hips", "BlessingPouchMount", Vector3(0.16, -0.02, 0.04))
	var pouch := BoxMesh.new()
	pouch.size = Vector3(0.11, 0.13, 0.055)
	_piece(hip, "BlessingTokenPouch", pouch, _mat(CLOAK, 0.92, 0.0))
