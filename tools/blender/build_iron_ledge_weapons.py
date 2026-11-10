"""Build and render the first Iron Ledge weapon concept set.

Run: blender -b -P tools/blender/build_iron_ledge_weapons.py
Exports one editable .blend, game-ready .glb, and preview PNG per weapon.
"""
import bpy
import math
import os
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
OUT = os.path.join(ROOT, "godot/assets/models/weapons/iron_ledge")
PREVIEWS = os.path.join(ROOT, "docs/assets/weapons")
os.makedirs(OUT, exist_ok=True)
os.makedirs(PREVIEWS, exist_ok=True)


def material(name, color, metallic=0.0, roughness=0.55):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    p = m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Metallic"].default_value = metallic
    p.inputs["Roughness"].default_value = roughness
    return m


def materials():
    global STEEL, EDGE, IRON, WOOD, WOOD_LIGHT, LEATHER, COBALT, BRASS
    STEEL = material("Forged steel", (0.31, 0.36, 0.38), 0.78, 0.28)
    EDGE = material("Honed edge", (0.62, 0.67, 0.67), 0.85, 0.2)
    IRON = material("Dark iron", (0.105, 0.12, 0.12), 0.72, 0.38)
    WOOD = material("Oiled ashwood", (0.25, 0.125, 0.055), 0.02, 0.52)
    WOOD_LIGHT = material("Ashwood backing", (0.58, 0.37, 0.17), 0.03, 0.48)
    LEATHER = material("Oxblood leather", (0.19, 0.045, 0.035), 0.0, 0.72)
    COBALT = material("Wolfguard cobalt", (0.025, 0.12, 0.36), 0.0, 0.56)
    BRASS = material("Bellfound brass", (0.42, 0.25, 0.075), 0.68, 0.32)


def cube(name, loc, scale, mat, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.name = name
    o.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(mat)
    if bevel:
        b = o.modifiers.new("Soft forged edges", "BEVEL")
        b.width = bevel
        b.segments = 2
        o.modifiers.new("Weighted corner normals", "WEIGHTED_NORMAL")
    return o


def cylinder(name, loc, radius, depth, mat, vertices=12, direction=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc)
    o = bpy.context.object
    o.name = name
    o.data.materials.append(mat)
    if direction:
        o.rotation_euler = Vector((0, 0, 1)).rotation_difference(Vector(direction)).to_euler()
    return o


def rod(name, a, b, radius, mat, vertices=10):
    av, bv = Vector(a), Vector(b)
    mid = (av + bv) / 2
    return cylinder(name, mid, radius, (bv-av).length, mat, vertices, bv-av)


def blade(name, z0, z1, width0, width1, thickness, mat):
    # Double-faced tapered blade with a distinct point and a shallow ridge.
    verts = [(-width0/2, 0, z0), (width0/2, 0, z0),
             (-width1/2, 0, z1-0.12), (width1/2, 0, z1-0.12),
             (0, 0, z1), (-width0/2, thickness, z0), (width0/2, thickness, z0),
             (-width1/2, thickness, z1-0.12), (width1/2, thickness, z1-0.12),
             (0, thickness, z1)]
    faces = [(0,1,3,2),(2,3,4),(5,7,8,6),(7,9,8),
             (0,2,7,5),(1,6,8,3),(2,4,9,7),(3,8,9,4),(0,5,6,1)]
    mesh = bpy.data.meshes.new(name+" mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(mat)
    ob = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(ob)
    ob.data.polygons[0].material_index = 0
    return ob


def finish(name, slug, dims, camera_target):
    # The caller leaves only the current weapon geometry in the scene.
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = 900, 900
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.film_transparent = False
    # Use Standard so the renders work with the host's fallback OCIO config.
    sc.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("Warm neutral studio")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.28, 0.26, 0.23, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.55
    sc.world = world
    cam_data = bpy.data.cameras.new("Product camera")
    cam = bpy.data.objects.new("Product camera", cam_data)
    sc.collection.objects.link(cam)
    cam.location = (3.3, -7.2, 3.2)
    target = Vector(camera_target)
    cam.rotation_euler = (target-cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = dims
    sc.camera = cam
    for name_l, loc, energy, size in [
        ("Key softbox", (3, -4, 6), 850, 4.0),
        ("Fill softbox", (-4, -2, 3), 500, 3.5),
        ("Rim softbox", (1, 4, 5), 900, 3.0),
    ]:
        ld = bpy.data.lights.new(name_l, "AREA")
        ld.energy, ld.shape, ld.size = energy, "DISK", size
        lo = bpy.data.objects.new(name_l, ld)
        sc.collection.objects.link(lo)
        lo.location = loc
        lo.rotation_euler = (Vector(camera_target)-lo.location).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = os.path.join(PREVIEWS, slug + ".png")
    bpy.ops.render.render(write_still=True)
    # Keep the editable source clean: studio objects are hidden from export and removed before save.
    studio = [o for o in bpy.data.objects if o.type in {"CAMERA", "LIGHT"}]
    for o in studio:
        bpy.data.objects.remove(o, do_unlink=True)
    sc.world = None
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, slug + ".blend"))
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, slug + ".glb"), export_format="GLB",
                              export_apply=True, export_materials="EXPORT")
    bpy.ops.wm.read_factory_settings(use_empty=True)


def sword():
    # Vertical silhouette; point at +Z, grip below the crossguard.
    blade("Gateward blade", 0.55, 2.25, 0.22, 0.34, 0.055, STEEL)
    rod("Honed central ridge", (0, -0.032, 0.68), (0, -0.032, 2.08), 0.025, EDGE, 6)
    cube("Guard", (0, 0, 0.48), (0.82, 0.13, 0.12), IRON, 0.035)
    cylinder("Grip", (0, 0, 0.12), 0.075, 0.48, LEATHER)
    cylinder("Pommel", (0, 0, -0.17), 0.13, 0.09, IRON)
    cube("Leather grip wrap", (0, -0.076, 0.12), (0.075, 0.018, 0.39), LEATHER)
    finish("Gateward", "gateward_sword", 3.15, (0, 0, 1.0))


def spear():
    rod("Ashwood haft", (0,0,-0.05), (0,0,2.42), 0.055, WOOD, 12)
    blade("Leaf spearhead", 2.27, 3.05, 0.30, 0.015, 0.07, STEEL)
    cylinder("Reinforced socket", (0,0,2.32), 0.08, 0.25, IRON)
    # Restrained blue binding and heel cap.
    for i in range(6):
        z = 2.15 + i*0.035
        rod("Cobalt wrap %02d" % i, (-0.058,0,z), (0.058,0,z+0.05), 0.022, COBALT, 6)
    cylinder("Iron heel cap", (0,0,0.02), 0.07, 0.18, IRON)
    finish("Wolfguard Reach", "wolfguard_reach_spear", 3.85, (0, 0, 1.48))


def bow():
    # Bow lies in XZ plane, with a slight recurve at both tips.
    pts = [(0,0,0.05),(-0.25,0,0.20),(-0.43,0,0.58),(-0.52,0,1.05),
           (-0.48,0,1.48),(-0.30,0,1.91),(0,0,2.18)]
    for i in range(len(pts)-1):
        rod("Laminated bow limb", pts[i], pts[i+1], 0.045 if i not in (0,11) else 0.065,
            WOOD_LIGHT if i in (0,1,10,11) else WOOD, 8)
    rod("Waxed bowstring", (0,-0.035,0.05), (0,-0.035,2.18), 0.012, LEATHER, 6)
    # Grip sits near the lower-middle of the bow; narrow leather wrap.
    rod("Leather bow grip", (-0.49,-0.012,0.84), (-0.49,-0.012,1.24), 0.073, LEATHER, 10)
    for z in (0.86,0.96,1.06,1.16):
        rod("Grip binding", (-0.56,-0.025,z), (-0.42,-0.025,z+0.035), 0.016, IRON, 6)
    finish("Greenwood Longbow", "greenwood_longbow", 2.85, (0,0,1.1))


def knife():
    # Forward-curved field blade; hook remains visibly on the spine and is blunt.
    blade("Briarhook blade", 0.15, 1.08, 0.17, 0.28, 0.07, STEEL)
    # Slightly lean the blade forward, set from blade tip down to hand.
    cube("Knuckle guard", (0,0,0.10), (0.48,0.14,0.12), IRON, 0.035)
    rod("Handle core", (0,0,-0.48), (0,0,0.08), 0.075, WOOD, 10)
    for z in (-0.37,-0.11):
        cylinder("Handle pin", (0,-0.078,z), 0.028, 0.022, BRASS, 8, (0,1,0))
    # Blunt spine hook as an angular steel spur.
    rod("Blunt brush hook", (0.12,0,0.78), (0.29,0,0.91), 0.045, IRON, 8)
    rod("Hook return", (0.29,0,0.91), (0.25,0,1.02), 0.04, IRON, 8)
    cylinder("Lanyard eye", (0,-0.01,-0.51), 0.09, 0.045, IRON, 12)
    finish("Briarhook", "briarhook_field_knife", 2.15, (0,0,0.25))


def maul():
    rod("Ash maul haft", (0,0,-0.90), (0,0,0.72), 0.073, WOOD, 12)
    cube("Square maul face", (-0.19,0,0.82), (0.48,0.31,0.43), STEEL, 0.055)
    # Peen tapers toward the right, avoiding spike-like silhouette.
    cube("Tapered peen", (0.30,0,0.82), (0.47,0.25,0.28), IRON, 0.045)
    cube("Head wedge", (0,0,0.54), (0.16,0.36,0.20), IRON, 0.02)
    # Brass anti-rattle ring under the head.
    bpy.ops.mesh.primitive_torus_add(major_radius=0.095, minor_radius=0.018,
                                     major_segments=12, minor_segments=6, location=(0,0,0.31))
    bpy.context.object.name = "Brass anti-rattle ring"
    bpy.context.object.data.materials.append(BRASS)
    for z in (-0.78,-0.68,-0.58):
        rod("Grip leather wrap", (-0.06,-0.02,z), (0.06,-0.02,z+0.12), 0.084, LEATHER, 8)
    finish("Bellfound Maul", "bellfound_maul", 2.75, (0,0,0.25))


for build in (sword, spear, bow, knife, maul):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    materials()
    build()
print("BUILT_AND_RENDERED=5")
