"""Bloodweaver pilot hero: eldritch CC0 base + bespoke armor/coat/cape/lash (Blender 5.x).
Run: blender -b -P build_bloodweaver.py -- <eldritch.glb> <out_dir>
Front of the character is -Y (Blender), T-pose rest, 49-bone shared skeleton kept untouched."""
import bpy, bmesh, math, sys, random
from mathutils import Vector, Matrix

SRC, OUT = sys.argv[-2], sys.argv[-1]
random.seed(7)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
for o in list(bpy.data.objects):          # drop stray helper from the import
    if o.type == 'MESH' and o.parent is None:
        bpy.data.objects.remove(o)

# ---------- materials ----------
def mat(name, rgb, rough=0.6, metal=0.0, alpha=1.0, emit=None):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
        m.surface_render_method = 'BLENDED'
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = 1.5
    m.use_backface_culling = False
    return m
M_CARAPACE = mat("BW_Carapace", (0.38, 0.015, 0.03), 0.22, 0.35)
M_COAT     = mat("BW_Coat",     (0.20, 0.02, 0.04), 0.85)
M_LEATHER  = mat("BW_Leather",  (0.035, 0.025, 0.025), 0.55)
M_GOLD     = mat("BW_Gold",     (0.75, 0.55, 0.2), 0.3, 1.0)
M_CAPE     = mat("BW_CapeSheer",(0.55, 0.02, 0.05), 0.4, 0.0, alpha=0.5)
M_LASH     = mat("BW_Lash",     (0.30, 0.01, 0.03), 0.3, 0.2, emit=(0.5, 0.0, 0.02))

# recolor the base's own materials
recolor = {"LightBrown": (0.16, 0.015, 0.03), "LightBlue": (0.03, 0.025, 0.025),
           "Red_Dark": (0.05, 0.03, 0.03), "White": (0.6, 0.45, 0.2),
           "Hair": (0.02, 0.015, 0.015), "Skin": (0.52, 0.42, 0.40), "Skin_Darker": (0.42, 0.33, 0.32),
           "Eyebrows": (0.02, 0.015, 0.015)}
for m in bpy.data.materials:
    if m.name.split(".")[0] in recolor and m.use_nodes:
        bsdf = m.node_tree.nodes.get("Principled BSDF")
        if bsdf: bsdf.inputs["Base Color"].default_value = (*recolor[m.name.split(".")[0]], 1)
    if m.name.startswith("Eye") and m.use_nodes:
        bsdf = m.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (0.35, 0.02, 0.03, 1)

# ---------- helpers ----------
def to_obj(name, bm, material, bone, smooth=True):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    me.materials.append(material)
    for p in me.polygons: p.use_smooth = smooth
    o.parent = arm; o.parent_type = 'BONE'; o.parent_bone = bone
    o.matrix_parent_inverse = (arm.matrix_world @ arm.data.bones[bone].matrix_local @ Matrix.Translation((0, arm.data.bones[bone].length, 0))).inverted()  # Blender parents bone children at the bone TAIL
    return o

def strip(rows, cols, fn, close=False):
    """fn(row_frac, col_frac) -> Vector. Quad-grid surface."""
    bm = bmesh.new()
    vs = [[bm.verts.new(fn(r / (rows - 1), c / (cols - 1))) for c in range(cols)] for r in range(rows)]
    for r in range(rows - 1):
        for c in range(cols - 1):
            bm.faces.new((vs[r][c], vs[r][c + 1], vs[r + 1][c + 1], vs[r + 1][c]))
    return bm

def ellipsoid(bm, center, scale, rot=(0, 0, 0), seg=10, rings=6):
    m = Matrix.Translation(center) @ Matrix.LocRotScale(None, __import__("mathutils").Euler(rot), Vector(scale))
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0, matrix=m)

def cone(bm, base, direction, radius, length, seg=6):
    d = Vector(direction).normalized()
    rot = d.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    m = Matrix.Translation(Vector(base) + d * length / 2) @ rot
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=radius, radius2=0.0, depth=length, matrix=m)


def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a))); return t * t * (3 - 2 * t)

def to_skinned(name, bm, material, weight_fn):
    """Armature-deformed mesh. weight_fn(vertex_co) -> {bone: weight}."""
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    me.materials.append(material)
    for p in me.polygons: p.use_smooth = True
    o.parent = arm
    groups = {}
    for v in me.vertices:
        for b, w in weight_fn(v.co).items():
            if w <= 1e-4: continue
            g = groups.get(b) or o.vertex_groups.new(name=b); groups[b] = g
            g.add([v.index], w, 'REPLACE')
    mod = o.modifiers.new("Armature", 'ARMATURE'); mod.object = arm
    return o

# ---------- long coat: skinned so the front panels follow the legs ----------
def coat(r, c):
    a = math.radians(26 + c * (360 - 52))
    z0 = 1.02
    deg = math.degrees(a)
    front_flap = 0.12 if (deg < 80 or deg > 280) else 0.0
    hem = 0.27 + 0.06 * math.sin(c * 17.0) * (0.5 + r) + front_flap
    z = z0 + r * (hem - z0)
    rad = 0.185 + 0.17 * (r ** 1.5)
    return Vector((rad * math.sin(a), -rad * math.cos(a), z))

def coat_weights(co):
    t = smoothstep(1.0, 0.45, co.z)               # 0 at hip -> 1 near the hem
    front = max(0.0, -co.y / max(1e-6, math.hypot(co.x, co.y)))
    wl = t * (0.25 + 0.6 * front)
    leg = "UpperLeg.L" if co.x >= 0 else "UpperLeg.R"
    return {"Hips": 1.0 - wl, leg: wl}
to_skinned("Hero_Coat", strip(9, 44, coat), M_COAT, coat_weights)
to_skinned("Hero_CoatTrim", strip(2, 44, lambda r, c: coat(1.0 - r * 0.06, c)), M_GOLD, coat_weights)

# ---------- high collar: wider front opening, lower at the sides ----------
def collar(r, c):
    a = math.radians(55 + c * (360 - 110))
    back = max(0.0, math.cos(a - math.pi))
    z = 1.43 + r * (0.085 + 0.09 * back)
    rad = 0.105 + 0.055 * r
    return Vector((rad * math.sin(a), -rad * math.cos(a) - 0.035, z))
to_obj("Hero_Collar", strip(3, 26, collar), M_CARAPACE, "Chest")
def collar_trim(r, c):
    return collar(1.0, c) + Vector((0, 0, 0.004 - r * 0.012))
to_obj("Hero_CollarTrim", strip(2, 26, collar_trim), M_GOLD, "Chest")

# ---------- pauldrons: layered arch plates over the shoulder, one spike each ----------
for side, bone in ((1, "Shoulder.L"), (-1, "Shoulder.R")):
    bm = bmesh.new()
    ellipsoid(bm, Vector((side * 0.105, -0.055, 1.49)), (0.07, 0.115, 0.045), rot=(0, side * math.radians(-12), 0), seg=8, rings=5)
    for i in range(4):
        x = side * (0.17 + i * 0.062); z = 1.505 - i * 0.014
        ellipsoid(bm, Vector((x, -0.055, z)), (0.062 - i * 0.004, 0.105 - i * 0.008, 0.02),
                  rot=(0, side * math.radians(-10 - 9 * i), 0), seg=8, rings=4)
    cone(bm, Vector((side * 0.11, -0.055, 1.525)), (side * 0.35, -0.1, 1.0), 0.02, 0.09, seg=5)
    cone(bm, Vector((side * 0.24, -0.055, 1.515)), (side * 0.6, 0.0, 1.0), 0.014, 0.06, seg=5)
    to_obj("Hero_Pauldron_" + ("L" if side > 0 else "R"), bm, M_CARAPACE, bone, smooth=False)

# ---------- chest: shingled scale rows (narrow diamonds, each row overlaps the one above) ----------
bm = bmesh.new()
for z, n in ((1.455, 6), (1.405, 5), (1.355, 6), (1.305, 5), (1.255, 4), (1.205, 3)):
    step = 0.052
    for k in range(n):
        x = (k - (n - 1) / 2) * step
        curve = -0.166 + (x * x) * 2.2                      # follow the chest's round front
        ellipsoid(bm, Vector((x, curve, z)), (0.032, 0.006, 0.05),
                  rot=(math.radians(14), 0, math.radians(-x * 90)), seg=4, rings=3)
to_obj("Hero_ChestPlates", bm, M_CARAPACE, "Chest", smooth=False)

# gold belt + clasp
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=20, radius1=0.175, radius2=0.175, depth=0.045,
                      matrix=Matrix.Translation((0, -0.05, 1.03)))
ellipsoid(bm, Vector((0, -0.215, 1.03)), (0.035, 0.012, 0.035))
to_obj("Hero_Belt", bm, M_GOLD, "Hips")

# ---------- sheer cape ----------
def cape(r, c):
    x = (c - 0.5) * (0.34 + 0.40 * r)
    z = 1.47 + r * (0.40 - 1.47)
    y = 0.095 + 0.09 * r + 0.025 * math.sin(c * 9 + r * 4) * r
    return Vector((x, y, z + 0.045 * math.sin(c * 14) * r))
to_obj("Hero_Cape", strip(14, 11, cape), M_CAPE, "Chest")

# ---------- blood-spike lash: tight coil hanging below the fist ----------
hand = arm.matrix_world @ arm.data.bones["Hand.R"].head_local
cx = hand.x - 0.03
bm = bmesh.new()
N, SIDES = 70, 5
path = []
for i in range(N):
    t = i / (N - 1)
    ang = t * 2.6 * 2 * math.pi
    rad = 0.07 * (1 - t) + 0.012
    path.append(Vector((cx + rad * math.cos(ang), hand.y + rad * math.sin(ang), hand.z - 0.09 - t * 0.34)))
rings = []
for i, p in enumerate(path):
    tan = (path[min(i + 1, N - 1)] - path[max(i - 1, 0)]).normalized()
    sd = tan.cross(Vector((0, 0, 1)))
    if sd.length < 1e-3: sd = Vector((1, 0, 0))
    sd.normalize(); up = sd.cross(tan).normalized()
    r = 0.010 * (1 - i / N * 0.7)
    rings.append([bm.verts.new(p + (sd * math.cos(2 * math.pi * k / SIDES) + up * math.sin(2 * math.pi * k / SIDES)) * r) for k in range(SIDES)])
for i in range(N - 1):
    for k in range(SIDES):
        bm.faces.new((rings[i][k], rings[i][(k + 1) % SIDES], rings[i + 1][(k + 1) % SIDES], rings[i + 1][k]))
    if i % 3 == 0:
        p = path[i]; out = (p - Vector((cx, hand.y, p.z)))
        out = out.normalized() if out.length > 1e-4 else Vector((0, -1, 0))
        cone(bm, p, out, 0.010, 0.035, seg=4)
bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.022, radius2=0.018, depth=0.17,
                      matrix=Matrix.Translation((cx, hand.y, hand.z - 0.02)))
to_obj("Hero_Lash", bm, M_LASH, "Hand.R")
hb = bmesh.new()
bmesh.ops.create_cone(hb, cap_ends=True, segments=8, radius1=0.026, radius2=0.026, depth=0.04,
                      matrix=Matrix.Translation((cx, hand.y, hand.z + 0.07)))
to_obj("Hero_LashCap", hb, M_GOLD, "Hand.R")

# ---------- stats + save ----------
tris = sum(len(p.vertices) - 2 for o in bpy.data.objects if o.type == 'MESH' for p in o.data.polygons)
print("BW_TOTAL_TRIS", tris)
bpy.ops.wm.save_as_mainfile(filepath=OUT + "/bloodweaver.blend")
bpy.ops.export_scene.gltf(filepath=OUT + "/bloodweaver.glb", export_format='GLB', export_apply=True,
                          export_animations=False, export_skins=True)
print("BW_DONE")
