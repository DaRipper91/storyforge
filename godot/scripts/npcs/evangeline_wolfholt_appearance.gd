extends RefCounted
## Appearance pass for Evangeline Wolfholt's watch-scout and field-scholar role.
## The source describes her role and relationships more clearly than her exact clothing, so the
## slate-and-cobalt outfit and compact field kit are visual proposals rather than fixed canon.

const SLATE := Color("#303b49")
const COBALT := Color("#315f96")
const LEATHER := Color("#514237")
const PAPER := Color("#d6c69a")
const BRASS := Color("#9a7744")
const LANTERN := Color("#ffd487")
const HAIR := Color("#4b3327")


static func apply(model: Node3D) -> void:
	_apply_palette(model)
	var skeletons := model.find_children("*", "Skeleton3D", true, false)
	if skeletons.is_empty():
		return
	var skeleton := skeletons[0] as Skeleton3D
	_add_field_codex(skeleton)
	_add_lantern(skeleton)
	_add_patch_charm(skeleton)


static func _apply_palette(model: Node3D) -> void:
	for node in model.find_children("*", "MeshInstance3D", true, false):
		var mesh := node as MeshInstance3D
		match mesh.name:
			"Casual_Body":
				_set_surface(mesh, 1, _mat(COBALT, 0.8, 0.08))
			"Casual_Feet":
				_set_surface(mesh, 1, _mat(LEATHER, 0.88, 0.0))
				_set_surface(mesh, 2, _mat(SLATE, 0.78, 0.08))
			"Casual_Head":
				_set_surface(mesh, 5, _mat(HAIR, 0.9, 0.0))
			"Casual_Legs":
				_set_surface(mesh, 1, _mat(SLATE, 0.84, 0.05))
				_set_surface(mesh, 2, _mat(LEATHER, 0.86, 0.0))


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
		position: Vector3 = Vector3.ZERO, rotation: Vector3 = Vector3.ZERO) -> MeshInstance3D:
	var instance := MeshInstance3D.new()
	instance.name = label
	instance.mesh = mesh
	instance.material_override = material
	instance.position = position
	instance.rotation = rotation
	parent.add_child(instance)
	return instance


static func _add_field_codex(skeleton: Skeleton3D) -> void:
	var mount := _mount(skeleton, "Hand.L", "FieldCodexMount", Vector3(0.0, -0.015, 0.04))
	var cover := BoxMesh.new()
	cover.size = Vector3(0.13, 0.18, 0.035)
	_piece(mount, "FieldCodexCover", cover, _mat(COBALT.darkened(0.25), 0.82, 0.0),
		Vector3(0.0, -0.005, 0.0), Vector3(0.0, 0.0, -0.15))
	var pages := BoxMesh.new()
	pages.size = Vector3(0.105, 0.15, 0.012)
	_piece(mount, "CodexPages", pages, _mat(PAPER, 0.96, 0.0), Vector3(0.0, -0.005, 0.021))
	var clasp := BoxMesh.new()
	clasp.size = Vector3(0.012, 0.04, 0.009)
	_piece(mount, "CodexClasp", clasp, _mat(BRASS, 0.42, 0.64), Vector3(0.0, -0.005, 0.03))


static func _add_lantern(skeleton: Skeleton3D) -> void:
	var mount := _mount(skeleton, "Hand.R", "WatchLanternMount", Vector3(0.0, -0.025, 0.035))
	var body := BoxMesh.new()
	body.size = Vector3(0.09, 0.12, 0.075)
	_piece(mount, "LanternFrame", body, _mat(BRASS, 0.4, 0.7), Vector3(0.0, -0.1, 0.0))
	var pane := BoxMesh.new()
	pane.size = Vector3(0.055, 0.075, 0.055)
	_piece(mount, "LanternGlass", pane, _mat(LANTERN, 0.25, 0.05, true), Vector3(0.0, -0.1, 0.0))
	var handle := TorusMesh.new()
	handle.inner_radius = 0.025
	handle.outer_radius = 0.033
	handle.rings = 6
	handle.ring_segments = 10
	_piece(mount, "LanternHandle", handle, _mat(BRASS, 0.42, 0.65), Vector3(0.0, -0.015, 0.0), Vector3(PI * 0.5, 0.0, 0.0))


static func _add_patch_charm(skeleton: Skeleton3D) -> void:
	var mount := _mount(skeleton, "Chest", "BunnyPatchMount", Vector3(0.10, -0.015, 0.115))
	var body := SphereMesh.new()
	body.radius = 0.022
	body.height = 0.044
	_piece(mount, "PatchBunnyBody", body, _mat(PAPER, 0.88, 0.0))
	var ear := CapsuleMesh.new()
	ear.radius = 0.008
	ear.height = 0.045
	ear.radial_segments = 6
	_piece(mount, "PatchBunnyEarL", ear, _mat(PAPER, 0.88, 0.0), Vector3(-0.012, 0.032, 0.0), Vector3(0.0, 0.0, 0.12))
	_piece(mount, "PatchBunnyEarR", ear, _mat(PAPER, 0.88, 0.0), Vector3(0.012, 0.032, 0.0), Vector3(0.0, 0.0, -0.12))
