"""Render front/side/back previews of a .blend. blender -b file.blend -P render_views.py -- <out_prefix>"""
import bpy, sys, math
from mathutils import Vector
pre = sys.argv[-1]
sc = bpy.context.scene
for e in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT', 'BLENDER_WORKBENCH'):
    try: sc.render.engine = e; break
    except TypeError: continue
print("ENGINE", sc.render.engine)
sc.render.resolution_x, sc.render.resolution_y = 640, 960
sc.render.film_transparent = False
w = bpy.data.worlds.new("W"); w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.5, 0.48, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.9
sc.world = w
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 2.4
for n, (loc, rot) in {"sun": ((2, -3, 4), (math.radians(50), 0, math.radians(30)))}.items():
    l = bpy.data.objects.new(n, bpy.data.lights.new(n, 'SUN')); l.data.energy = 3.5; l.location = loc; l.rotation_euler = rot; sc.collection.objects.link(l)
fill = bpy.data.objects.new("fill", bpy.data.lights.new("fill", 'SUN')); fill.data.energy = 1.2; fill.rotation_euler = (math.radians(70), 0, math.radians(-140)); sc.collection.objects.link(fill)
for name, ang in (("front", 0), ("side", 90), ("back", 180)):
    a = math.radians(ang); d = 6
    cam.location = (math.sin(a) * d * -1 * -1, -math.cos(a) * d, 0.95)
    cam.location = (d * math.sin(a), -d * math.cos(a), 0.95)
    cam.rotation_euler = (math.radians(90), 0, a)
    sc.render.filepath = f"{pre}_{name}.png"; bpy.ops.render.render(write_still=True)
