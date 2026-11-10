extends RefCounted
## Text-brief appearance pass for Bryttan Wolfholt.
## The source sheet was not included in the Gemini PDF export, so this uses only its
## stated slate, cobalt, wolf-crest, survival-dagger and power-pack details.

const SLATE := Color("#1a1c20")
const STEEL := Color("#59616b")
const LEATHER := Color("#44372f")
const COBALT := Color("#1b4f9c")
const GLOW := Color("#38b6ff")


static func apply(model: Node3D) -> void:
	_apply_palette(model)
	var skeletons := model.find_children("*", "Skeleton3D", true, false)
	if skeletons.is_empty():
		return
	var skeleton := skeletons[0] as Skeleton3D
	_add_pack(skeleton)
	_add_chest_badge(skeleton)
	_add_shoulders(skeleton)
	_add_pendant(skeleton)
	_add_dagger(skeleton)


static func _apply_palette(model: Node3D) -> void:
	for node in model.find_children("*", "MeshInstance3D", true, false):
		var mesh := node as MeshInstance3D
		match mesh.name:
			"Adventurer_Body":
				_set_surface(mesh, 1, _mat(SLATE, 0.78, 0.25))
				_set_surface(mesh, 2, _mat(STEEL, 0.72, 0.32))
			"Adventurer_Feet":
				_set_surface(mesh, 0, _mat(LEATHER, 0.88, 0.0))
			"Adventurer_Legs":
				_set_surface(mesh, 0, _mat(LEATHER, 0.86, 0.0))
				_set_surface(mesh, 1, _mat(SLATE, 0.80, 0.18))
			"Backpack":
				_set_surface(mesh, 0, _mat(LEATHER, 0.88, 0.0))
				_set_surface(mesh, 1, _mat(SLATE, 0.82, 0.18))
				_set_surface(mesh, 2, _mat(COBALT, 0.46, 0.35))


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
		material.emission_energy_multiplier = 0.8
	return material


static func _mount(skeleton: Skeleton3D, bone: String, label: String, offset: Vector3) -> BoneAttachment3D:
	var mount := BoneAttachment3D.new()
	mount.name = label
	mount.bone_name = bone
	mount.position = offset
	skeleton.add_child(mount)
	return mount


static func _piece(parent: Node, label: String, mesh: Mesh, material: StandardMaterial3D,
		position: Vector3 = Vector3.ZERO, rotation: Vector3 = Vector3.ZERO,
		scale: Vector3 = Vector3.ONE) -> MeshInstance3D:
	var instance := MeshInstance3D.new()
	instance.name = label
	instance.mesh = mesh
	instance.material_override = material
	instance.position = position
	instance.rotation = rotation
	instance.scale = scale
	parent.add_child(instance)
	return instance


static func _box(size: Vector3) -> BoxMesh:
	var mesh := BoxMesh.new()
	mesh.size = size
	return mesh


static func _sphere(radius: float, segments: int = 10, rings: int = 5) -> SphereMesh:
	var mesh := SphereMesh.new()
	mesh.radius = radius
	mesh.height = radius * 2.0
	mesh.radial_segments = segments
	mesh.rings = rings
	return mesh


static func _add_pack(skeleton: Skeleton3D) -> void:
	var mount := _mount(skeleton, "Chest", "WolfguardPackMount", Vector3(0.0, 0.02, -0.12))
	_piece(mount, "CobaltPowerCore", _sphere(0.075, 8, 4), _mat(GLOW, 0.35, 0.15, true),
		Vector3(0.0, 0.04, -0.055))
	_piece(mount, "PackTop", _box(Vector3(0.22, 0.08, 0.035)), _mat(LEATHER, 0.9, 0.0),
		Vector3(0.0, 0.15, -0.045))


static func _add_chest_badge(skeleton: Skeleton3D) -> void:
	var mount := _mount(skeleton, "Chest", "WolfCrestMount", Vector3(0.0, 0.035, 0.13))
	_piece(mount, "CrestBacking", _box(Vector3(0.20, 0.19, 0.025)), _mat(SLATE, 0.55, 0.5))
	_piece(mount, "WolfCrest", _wolf_crest(), _mat(COBALT, 0.48, 0.35, true), Vector3(0.0, 0.0, 0.018))


static func _wolf_crest() -> ArrayMesh:
	var outline := PackedVector2Array([
		Vector2(-0.075, 0.015), Vector2(-0.105, 0.095), Vector2(-0.035, 0.075),
		Vector2(0.0, 0.125), Vector2(0.035, 0.075), Vector2(0.105, 0.095),
		Vector2(0.075, 0.015), Vector2(0.045, -0.055), Vector2(0.0, -0.105),
		Vector2(-0.045, -0.055),
	])
	var center := Vector3(0.0, 0.015, 0.0)
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for i in outline.size():
		var a := outline[i]
		var b := outline[(i + 1) % outline.size()]
		st.set_normal(Vector3(0.0, 0.0, 1.0))
		st.add_vertex(center)
		st.add_vertex(Vector3(a.x, a.y, 0.0))
		st.add_vertex(Vector3(b.x, b.y, 0.0))
	return st.commit()


static func _add_shoulders(skeleton: Skeleton3D) -> void:
	for side in ["L", "R"]:
		var sign := -1.0 if side == "L" else 1.0
		var mount := _mount(skeleton, "Shoulder." + side, "WolfguardShoulder" + side,
			Vector3(sign * 0.045, 0.02, 0.0))
		_piece(mount, "SlatePauldron", _box(Vector3(0.16, 0.09, 0.18)), _mat(STEEL, 0.58, 0.52))
		_piece(mount, "CobaltRune", _box(Vector3(0.018, 0.075, 0.012)), _mat(GLOW, 0.4, 0.25, true),
			Vector3(0.0, 0.0, 0.097))


static func _add_pendant(skeleton: Skeleton3D) -> void:
	var mount := _mount(skeleton, "Chest", "WolfguardPendantMount", Vector3(0.0, 0.13, 0.16))
	_piece(mount, "ShardSetting", _sphere(0.052, 8, 4), _mat(LEATHER, 0.65, 0.45))
	_piece(mount, "BlueShard", _sphere(0.035, 6, 3), _mat(GLOW, 0.28, 0.15, true), Vector3(0.0, 0.0, 0.035))


static func _add_dagger(skeleton: Skeleton3D) -> void:
	var mount := _mount(skeleton, "Hand.R", "RuneDaggerMount", Vector3(0.0, -0.02, 0.04))
	_piece(mount, "DaggerGrip", _box(Vector3(0.035, 0.10, 0.035)), _mat(LEATHER, 0.9, 0.0),
		Vector3(0.0, -0.06, 0.0))
	_piece(mount, "DaggerGuard", _box(Vector3(0.09, 0.018, 0.025)), _mat(STEEL, 0.5, 0.65),
		Vector3(0.0, -0.005, 0.0))
	_piece(mount, "RunedBlade", _box(Vector3(0.025, 0.17, 0.012)), _mat(STEEL, 0.35, 0.72),
		Vector3(0.0, 0.09, 0.0))
	_piece(mount, "BladeRune", _box(Vector3(0.008, 0.08, 0.014)), _mat(GLOW, 0.35, 0.2, true),
		Vector3(0.0, 0.09, 0.012))
