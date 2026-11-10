"""Build a small reusable forest-edge prop kit and a Blender preview render.

Run: blender -b -t 2 -P tools/blender/build_forest_edge_kit.py
"""
import bpy
import math
import os
from mathutils import Vector

bpy.ops.wm.read_factory_settings(use_empty=True)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
OUT = os.path.join(ROOT, "godot/assets/models/props/forest_edge_kit")
PREVIEW = os.path.join(ROOT, "docs/assets/world")
os.makedirs(OUT, exist_ok=True)
os.makedirs(PREVIEW, exist_ok=True)


def mat(name, color, metallic=0.0, rough=0.75):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    p = m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Metallic"].default_value = metallic
    p.inputs["Roughness"].default_value = rough
    return m


BARK = mat("Damp ironwood bark", (0.20, 0.105, 0.050))
BARK_LIGHT = mat("Cut heartwood", (0.47, 0.29, 0.12))
LEAF_DARK = mat("Deep forest leaf", (0.055, 0.16, 0.065))
LEAF_MID = mat("Moss green leaf", (0.13, 0.30, 0.095))
LEAF_LIGHT = mat("Canopy tips", (0.30, 0.42, 0.13))
PINE = mat("Blue spruce needles", (0.055, 0.20, 0.19))
MOSS = mat("Moss and ground cover", (0.17, 0.25, 0.09))
STONE = mat("Forest stone", (0.27, 0.29, 0.25))


def cylinder(name, loc, radius, depth, material, sides=9, direction=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=sides, radius=radius, depth=depth, location=loc)
    o = bpy.context.object
    o.name = name
    o.data.materials.append(material)
    if direction:
        o.rotation_euler = Vector((0, 0, 1)).rotation_difference(Vector(direction)).to_euler()
    return o


def limb(name, a, b, radius, material):
    av, bv = Vector(a), Vector(b)
    return cylinder(name, (av+bv)*0.5, radius, (bv-av).length, material, 7, bv-av)


def blob(name, loc, scale, material, subdivisions=1):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdivisions, radius=1, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    o.data.materials.append(material)
    return o


def oak(cx, cy):
    cylinder("Oak trunk", (cx,cy,1.20), 0.22, 2.4, BARK, 9)
    limb("Oak branch left", (cx,cy,1.55), (cx-0.85,cy,2.65), 0.10, BARK)
    limb("Oak branch right", (cx,cy,1.75), (cx+0.75,cy,2.75), 0.09, BARK)
    limb("Oak crown branch", (cx,cy,1.85), (cx+0.08,cy,3.10), 0.10, BARK)
    for i, (x,y,z,sx,sy,sz,m) in enumerate([
        (-0.55,0,2.85,.88,.67,.82,LEAF_DARK),
        (0.48,0.02,2.98,.82,.68,.80,LEAF_MID),
        (0.0,0.03,3.62,.88,.73,.83,LEAF_MID),
        (-0.18,-0.18,3.30,.65,.57,.58,LEAF_LIGHT),
        (0.60,0.12,3.42,.45,.50,.49,LEAF_DARK),
    ]):
        blob("Oak canopy %02d"%i, (cx+x,cy+y,z), (sx,sy,sz), m, 2)


def pine(cx, cy):
    cylinder("Pine trunk", (cx,cy,1.65), 0.15, 3.3, BARK, 8)
    for i, z in enumerate((1.30,1.95,2.60,3.25,3.90)):
        radius = (4.10-z)*0.39
        bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=radius, radius2=0.035,
                                        depth=1.30, location=(cx,cy,z+0.43))
        o=bpy.context.object; o.name="Layered spruce bough %02d"%i; o.data.materials.append(PINE if i%2==0 else LEAF_MID)


def stump(cx, cy):
    cylinder("Broken stump bark", (cx,cy,0.38), 0.29, 0.76, BARK, 8)
    cylinder("Exposed heartwood", (cx,cy,0.775), 0.265, 0.035, BARK_LIGHT, 8)
    limb("Snapped branch", (cx+0.10,cy,0.43), (cx+0.49,cy,0.78), 0.09, BARK)
    blob("Stump moss", (cx-0.12,cy-0.06,0.72), (0.21,0.18,0.10), MOSS, 1)


def fallen_log(cx, cy):
    cylinder("Fallen log", (cx,cy,0.32), 0.24, 1.8, BARK, 9, (1,0.08,0.02))
    cylinder("Fresh broken end", (cx+0.91,cy+0.07,0.34), 0.205, 0.04, BARK_LIGHT, 9, (1,0.08,0.02))
    for x in (-0.45,0.20):
        limb("Log branch", (cx+x,cy,0.36), (cx+x+0.12,cy+0.36,0.78), 0.07, BARK)
    blob("Log moss patch", (cx-0.24,cy-0.06,0.54), (0.40,0.23,0.10), MOSS, 1)


def rock(cx, cy, scale, material=STONE):
    o=blob("Low-poly woodland boulder", (cx,cy,scale[2]*0.55), scale, material, 1)
    o.rotation_euler=(0.11,0.22,0.37)


def build_scene():
    oak(-1.55,0.0)
    pine(1.42,0.12)
    stump(-0.45,-0.85)
    fallen_log(0.95,-1.10)
    rock(-2.45,-0.98,(0.48,0.42,0.34))
    rock(2.05,-0.88,(0.36,0.32,0.26),MOSS)
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0,0,-0.03))
    ground=bpy.context.object; ground.name="Studio ground"; ground.data.materials.append(MOSS)


def studio_render():
    sc=bpy.context.scene
    sc.render.engine="BLENDER_EEVEE"
    sc.render.resolution_x=900; sc.render.resolution_y=600; sc.render.resolution_percentage=100
    sc.render.image_settings.file_format="PNG"
    sc.view_settings.view_transform="Standard"
    world=bpy.data.worlds.new("Forest prop studio"); world.use_nodes=True
    world.node_tree.nodes["Background"].inputs[0].default_value=(0.15,0.19,0.15,1)
    world.node_tree.nodes["Background"].inputs[1].default_value=0.25; sc.world=world
    cd=bpy.data.cameras.new("Forest kit camera"); cam=bpy.data.objects.new("Forest kit camera",cd); sc.collection.objects.link(cam)
    cam.location=(7,-11,7); target=Vector((0,0,1.9)); cam.rotation_euler=(target-cam.location).to_track_quat("-Z","Y").to_euler()
    cd.type="ORTHO"; cd.ortho_scale=9.6; sc.camera=cam
    for name,loc,power,size in (("Key",(1,-5,8),210,5),("Fill",(-5,-1,4),110,4),("Rim",(0,5,6),230,3)):
        ld=bpy.data.lights.new(name,"AREA"); ld.energy=power; ld.shape="DISK"; ld.size=size
        lo=bpy.data.objects.new(name,ld); sc.collection.objects.link(lo); lo.location=loc
        lo.rotation_euler=(Vector((0,0,2))-lo.location).to_track_quat("-Z","Y").to_euler()
    sc.render.filepath=os.path.join(PREVIEW,"forest_edge_kit.png")
    bpy.ops.render.render(write_still=True)


build_scene()
studio_render()
# Keep only the actual kit in the editable asset and engine export.
for o in list(bpy.data.objects):
    if o.type in {"CAMERA","LIGHT"} or o.name=="Studio ground":
        bpy.data.objects.remove(o,do_unlink=True)
bpy.context.scene.world=None
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,"forest_edge_kit.blend"))
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT,"forest_edge_kit.glb"), export_format="GLB", export_apply=True)
print("FOREST_KIT_BUILT_AND_RENDERED")
