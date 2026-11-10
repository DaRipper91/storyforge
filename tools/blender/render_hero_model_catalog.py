"""Render every bespoke hero model in a labeled, front-facing catalog.

Run: blender -b -t 1 -P tools/blender/render_hero_model_catalog.py
"""
import bpy
import math
from pathlib import Path
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / "godot/assets/models/heroes"
OUT = ROOT / "docs/assets/heroes/model_catalog.png"
FILES = sorted(MODELS.glob("*.glb"))
assert len(FILES) == 23, f"Expected 23 bespoke hero GLBs, found {len(FILES)}"

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE"
sc.render.resolution_x, sc.render.resolution_y = 2100, 1850
sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = "PNG"
sc.view_settings.view_transform = "Standard"

world = bpy.data.worlds.new("Hero catalog studio")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.13, 0.16, 0.19, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.45
sc.world = world

backdrop = bpy.data.materials.new("Catalog slate")
backdrop.diffuse_color = (0.07, 0.09, 0.11, 1)
backdrop.use_nodes = True
backdrop.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.07, 0.09, 0.11, 1)
backdrop.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.9
label_mat = bpy.data.materials.new("Warm label")
label_mat.diffuse_color = (0.9, 0.88, 0.79, 1)
label_mat.use_nodes = True
label_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.9, 0.88, 0.79, 1)

columns, spacing = 5, 3.45
rows = math.ceil(len(FILES) / columns)
gap_z = 3.0
for index, path in enumerate(FILES):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    imported = [obj for obj in bpy.data.objects if obj not in before]
    meshes = [obj for obj in imported if obj.type == "MESH"]
    bpy.context.view_layer.update()
    points = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
    low = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    high = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    center = (low + high) * 0.5
    scale = 2.0 / max(high.z - low.z, 0.001)
    col, row = index % columns, index // columns
    gx = (col - (columns - 1) * 0.5) * spacing
    gz = (rows - 1 - row) * gap_z + 1.25
    root = bpy.data.objects.new("Catalog root " + path.stem, None)
    sc.collection.objects.link(root)
    for obj in imported:
        obj.parent = root
        obj.matrix_parent_inverse = Matrix.Identity(4)
    root.scale = (scale, scale, scale)
    root.location = (gx - center.x * scale, -0.55 - center.y * scale, gz - low.z * scale)
    label_data = bpy.data.curves.new(path.stem + " label", "FONT")
    label_data.body = path.stem.replace("_", " ").title()
    label_data.size = 0.22
    label_data.align_x = "CENTER"
    label = bpy.data.objects.new(path.stem + " label", label_data)
    sc.collection.objects.link(label)
    label.location = (gx, -1.35, gz - 1.18)
    label.rotation_euler.x = math.radians(90)
    label.data.materials.append(label_mat)

# A vertical slate panel behind the models gives each species a shared backdrop.
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 1.2, rows * gap_z * 0.5))
panel = bpy.context.object
panel.name = "Slate catalog backing"
panel.rotation_euler.x = math.radians(90)
panel.dimensions = (columns * spacing + 0.25, rows * gap_z + 0.25, 0)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
panel.data.materials.append(backdrop)

cam_data = bpy.data.cameras.new("Catalog camera")
cam = bpy.data.objects.new("Catalog camera", cam_data)
sc.collection.objects.link(cam)
cam.location = (0, -31, 7.65)
cam.rotation_euler = (Vector((0, 0, 7.65)) - cam.location).to_track_quat("-Z", "Y").to_euler()
cam.data.type = "ORTHO"
cam.data.ortho_scale = 16.0
sc.camera = cam
for name, location, energy, size in (
    ("Key", (-5, -9, 13), 2300, 8),
    ("Fill", (8, -8, 7), 1300, 7),
    ("Rim", (0, 1, 14), 1800, 6),
):
    light_data = bpy.data.lights.new(name, "AREA")
    light_data.energy = energy
    light_data.shape = "DISK"
    light_data.size = size
    light = bpy.data.objects.new(name, light_data)
    sc.collection.objects.link(light)
    light.location = location
    light.rotation_euler = (Vector((0, 0, 7)) - light.location).to_track_quat("-Z", "Y").to_euler()

sc.render.filepath = str(OUT)
bpy.ops.render.render(write_still=True)
print("HERO_MODEL_CATALOG_RENDERED", len(FILES), OUT)
