extends RefCounted
## Per-instance material palette for named NPCs that share the project's rigged archetype GLBs.
## Archetypes keep the rig and mesh; these palettes give each person a readable work/role silhouette.

const PALETTES := {
	"kodrik": {"main": Color("#344653"), "trim": Color("#a7773e"), "dark": Color("#242b30")},
	"jon": {"main": Color("#58634b"), "trim": Color("#a78b5f"), "dark": Color("#3b342b")},
	"haylie": {"main": Color("#584454"), "trim": Color("#c2a66e"), "dark": Color("#33313b")},
	"samael": {"main": Color("#33384c"), "trim": Color("#88879a"), "dark": Color("#222430")},
	"cinder": {"main": Color("#722d35"), "trim": Color("#c2a258"), "dark": Color("#28242a")},
	"bryne": {"main": Color("#53634f"), "trim": Color("#8e9678"), "dark": Color("#343a35")},
	"nathis": {"main": Color("#3b4147"), "trim": Color("#bd8742"), "dark": Color("#27292c")},
	"mykael": {"main": Color("#70563e"), "trim": Color("#b29a73"), "dark": Color("#42372d")},
}


static func apply(model: Node3D, appearance_id: String) -> void:
	var palette: Dictionary = PALETTES.get(appearance_id, {})
	if palette.is_empty():
		return
	for node in model.find_children("*", "MeshInstance3D", true, false):
		var mesh := node as MeshInstance3D
		match mesh.name:
			"Casual_Body":
				_set_surface(mesh, 1, _mat(palette.main, 0.82, 0.04))
			"Casual_Feet":
				_set_surface(mesh, 1, _mat(palette.dark, 0.9, 0.0))
				_set_surface(mesh, 2, _mat(palette.trim, 0.72, 0.12))
			"Casual_Legs":
				_set_surface(mesh, 1, _mat(palette.main.darkened(0.18), 0.88, 0.0))
				_set_surface(mesh, 2, _mat(palette.dark, 0.9, 0.0))
			"Adventurer_Body":
				_set_surface(mesh, 1, _mat(palette.main, 0.72, 0.18))
				_set_surface(mesh, 2, _mat(palette.trim, 0.54, 0.48))
			"Adventurer_Feet":
				_set_surface(mesh, 0, _mat(palette.dark, 0.9, 0.0))
			"Adventurer_Legs":
				_set_surface(mesh, 0, _mat(palette.dark, 0.88, 0.0))
				_set_surface(mesh, 1, _mat(palette.main.darkened(0.16), 0.84, 0.08))
			"Backpack":
				_set_surface(mesh, 0, _mat(palette.dark, 0.9, 0.0))
				_set_surface(mesh, 1, _mat(palette.main, 0.84, 0.05))
				_set_surface(mesh, 2, _mat(palette.trim, 0.5, 0.44))
			"Cube.007": # npc_mage torso: tie, coat, shirt
				_set_surface(mesh, 1, _mat(palette.trim, 0.48, 0.2))
				_set_surface(mesh, 2, _mat(palette.main, 0.66, 0.12))
			"Cube.012": # npc_mage coat panel
				_set_surface(mesh, 0, _mat(palette.main, 0.66, 0.12))
			"Cube.001": # npc_performer torso
				_set_surface(mesh, 1, _mat(palette.trim.lightened(0.2), 0.8, 0.0))
				_set_surface(mesh, 2, _mat(palette.dark, 0.72, 0.08))
			"Cube.026": # npc_performer jacket and trim
				_set_surface(mesh, 5, _mat(palette.dark, 0.8, 0.0))
				_set_surface(mesh, 6, _mat(palette.main, 0.68, 0.08))
				_set_surface(mesh, 7, _mat(palette.trim, 0.36, 0.68))


static func _set_surface(mesh: MeshInstance3D, surface: int, material: StandardMaterial3D) -> void:
	if mesh.mesh and surface < mesh.mesh.get_surface_count():
		mesh.set_surface_override_material(surface, material)


static func _mat(color: Color, roughness: float, metallic: float) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.roughness = roughness
	material.metallic = metallic
	return material
