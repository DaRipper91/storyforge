"""Grimcrow pilot: raven-headed corvid oracle on the primal shared-skeleton base (Blender 5.x).
Run: blender -b -P build_grimcrow.py -- <primal.glb> <out_dir>
Replaces the base head and shoes with a raven head and bird talons; layered tattered robe (skinned),
bone-net shawl with tassels and beads, feathered forearms, fate-talon at the sash."""
import bpy, math, sys, os
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hero_common import *

SRC, OUT = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
remove_objects("_Head", "_Feet")          # stray helper + human head and shoes

M_FEATHER = mat("GC_Feather", (0.025, 0.03, 0.06), 0.32, 0.35)
M_BEAK    = mat("GC_Beak",    (0.06, 0.06, 0.07), 0.25, 0.5)
M_EYE     = mat("GC_Eye",     (0.35, 0.18, 0.05), 0.15, 0.0, emit=(0.5, 0.25, 0.06), strength=0.6)
M_CLOTH   = mat("GC_Cloth",   (0.075, 0.065, 0.075), 0.95)
M_CLOTH2  = mat("GC_ClothDark", (0.045, 0.04, 0.05), 0.95)
M_WEAVE   = mat("GC_Embroidery", (0.45, 0.34, 0.20), 0.8)
M_BONE    = mat("GC_Bone",    (0.78, 0.70, 0.54), 0.55)
M_TALON   = mat("GC_Talon",   (0.05, 0.045, 0.05), 0.3, 0.6)
recolor_base({"Skin": (0.025, 0.03, 0.055), "Swat": (0.09, 0.075, 0.075), "Swat_Black": (0.045, 0.04, 0.045)})

# ---------- raven head ----------
hb = bmesh.new() if False else None
import bmesh
bm = bmesh.new()
ell(bm, (0, -0.075, 1.635), (0.092, 0.115, 0.092))                                  # skull
ell(bm, (0, -0.02, 1.60), (0.075, 0.08, 0.07))                                      # nape
for i in range(5):                                                                  # crown feathers sweeping back
    ell(bm, (0, -0.03 + i * 0.018, 1.70 - i * 0.012), (0.045 - i * 0.003, 0.07, 0.016), rot=(math.radians(-20 - 5 * i), 0, 0), seg=6, rings=4)
tube(bm, (0, -0.165, 1.645), (0, -0.26, 1.635), 0.052, 0.036)                       # upper beak: tapered, hooked
tube(bm, (0, -0.26, 1.635), (0, -0.345, 1.595), 0.036, 0.012)
cone(bm, (0, -0.335, 1.60), (0, -0.4, -1.0), 0.012, 0.03, seg=4)
tube(bm, (0, -0.165, 1.612), (0, -0.26, 1.60), 0.04, 0.026)                         # lower beak
tube(bm, (0, -0.26, 1.60), (0, -0.325, 1.585), 0.026, 0.01)
attach(arm, "Hero_RavenHead", bm, M_FEATHER, "Head", smooth=False)
bm = bmesh.new()
tube(bm, (0, -0.165, 1.645), (0, -0.26, 1.635), 0.05, 0.034)                        # beak sheath overlay (own material)
tube(bm, (0, -0.26, 1.635), (0, -0.345, 1.595), 0.034, 0.010)
tube(bm, (0, -0.165, 1.612), (0, -0.26, 1.60), 0.038, 0.024)
tube(bm, (0, -0.26, 1.60), (0, -0.325, 1.585), 0.024, 0.009)
attach(arm, "Hero_Beak", bm, M_BEAK, "Head")
bm = bmesh.new()
for sx in (1, -1):
    ell(bm, (sx * 0.078, -0.135, 1.66), (0.022, 0.02, 0.022), seg=6, rings=4)
attach(arm, "Hero_Eyes", bm, M_EYE, "Head")

# neck ruff: three rings of swept feather cones
bm = bmesh.new()
for ring, (z, rad, n, ln) in enumerate(((1.545, 0.095, 12, 0.07), (1.515, 0.115, 14, 0.085), (1.485, 0.135, 16, 0.10))):
    for k in range(n):
        a = 2 * math.pi * k / n + ring * 0.2
        p = Vector((rad * math.sin(a), -0.043 - rad * math.cos(a), z))
        out = Vector((math.sin(a), -math.cos(a), -0.8))
        cone(bm, p, out, 0.022, ln, seg=4)
attach(arm, "Hero_NeckRuff", bm, M_FEATHER, "Neck", smooth=False)

# ---------- hood / cowl draped from the back of the head ----------
def cowl(r, c):
    a = math.radians(75 + c * 210)
    z = 1.64 - r * 0.26
    rad = 0.115 + 0.075 * r
    return Vector((rad * math.sin(a), -0.043 - rad * math.cos(a) * 1.0, z))
attach(arm, "Hero_Cowl", strip(5, 20, cowl), M_CLOTH2, "Chest")

# ---------- bone-net shawl across the shoulders ----------
bm = bmesh.new()
rows = ((1.455, 0.215, 0.135), (1.395, 0.235, 0.15), (1.335, 0.25, 0.16))
N = 18
for ri, (z, rx, ry) in enumerate(rows):
    pts = []
    for k in range(N):
        a = 2 * math.pi * k / N
        zz = z + (0.03 if k % 2 == 0 else -0.03)                                    # zigzag -> diamond lattice
        pts.append(Vector((rx * math.sin(a), -0.043 - ry * math.cos(a), zz)))
    for k in range(N):
        tube(bm, pts[k], pts[(k + 1) % N], 0.0075, 0.0075, seg=4)
        ell(bm, pts[k], (0.013, 0.013, 0.013), seg=5, rings=3)
        if ri == len(rows) - 1 and k % 2 == 1:                                      # tassels with a bead
            cone(bm, pts[k], (0, 0, -1), 0.008, 0.09, seg=4)
            ell(bm, pts[k] + Vector((0, 0, -0.06)), (0.011, 0.011, 0.016), seg=6, rings=4)
# diamond cross-links between rows
for ri in range(len(rows) - 1):
    for k in range(0, N, 2):
        a = 2 * math.pi * k / N
        for dz, (z, rx, ry) in ((0, rows[ri]), (1, rows[ri + 1])):
            pass
        z0, rx0, ry0 = rows[ri]; z1, rx1, ry1 = rows[ri + 1]
        p0 = Vector((rx0 * math.sin(a), -0.043 - ry0 * math.cos(a), z0 - 0.03))
        p1 = Vector((rx1 * math.sin(a), -0.043 - ry1 * math.cos(a), z1 + 0.03))
        tube(bm, p0, p1, 0.006, 0.006, seg=4)
attach(arm, "Hero_BoneNet", bm, M_BONE, "Chest")

# bead necklace with a talon pendant
bm = bmesh.new()
for k in range(14):
    a = math.radians(-70 + k * 140 / 13)
    ell(bm, (0.12 * math.sin(a), -0.043 - 0.12 * math.cos(a) - 0.06, 1.44 - 0.03 * math.cos(a * 1.3)), (0.013, 0.013, 0.013), seg=5, rings=3)
cone(bm, (0, -0.19, 1.415), (0, -0.2, -1), 0.014, 0.06, seg=5)
attach(arm, "Hero_Beads", bm, M_BONE, "Chest")

# ---------- tattered layered robe (skinned: front panels follow the legs) ----------
def robe_layer(radius0, radius1, z_hem, ragged, phase):
    def fn(r, c):
        a = math.radians(14 + c * (360 - 28))
        t = r
        z = 1.04 + t * (z_hem - 1.04)
        # ragged tatters: sawtooth hem
        saw = (math.sin(c * 46 + phase) * 0.5 + 0.5) ** 2
        z -= 0 if r < 0.7 else (r - 0.7) / 0.3 * ragged * saw
        rad = radius0 + (radius1 - radius0) * (t ** 1.4)
        return Vector((rad * math.sin(a), -rad * math.cos(a), z))
    return fn

def robe_weights(co):
    t = smoothstep(1.0, 0.4, co.z)
    front = max(0.0, -co.y / max(1e-6, math.hypot(co.x, co.y)))
    wl = t * (0.25 + 0.6 * front)
    return {"Hips": 1.0 - wl, ("UpperLeg.L" if co.x >= 0 else "UpperLeg.R"): wl}

skinned(arm, "Hero_RobeUnder", strip(9, 60, robe_layer(0.19, 0.31, 0.16, 0.07, 0.0)), M_CLOTH2, robe_weights)
skinned(arm, "Hero_RobeMid",   strip(9, 60, robe_layer(0.205, 0.34, 0.24, 0.09, 1.7)), M_CLOTH, robe_weights)
skinned(arm, "Hero_RobeOuter", strip(9, 60, robe_layer(0.22, 0.37, 0.34, 0.10, 3.1)), M_CLOTH2, robe_weights)

# embroidered band down the front of the outer layer
def band(r, c):
    a = math.radians(-9 + c * 18)
    t = r
    rad = 0.223 + (0.37 - 0.22) * (t ** 1.4) + 0.004
    return Vector((rad * math.sin(a), -rad * math.cos(a), 1.04 + t * (0.36 - 1.04)))
skinned(arm, "Hero_RobeBand", strip(9, 4, band), M_WEAVE, robe_weights)

# sash + beads + fate-talon
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=20, radius1=0.2, radius2=0.2, depth=0.07, matrix=__import__("mathutils").Matrix.Translation((0, -0.05, 1.03)))
for k in range(5):
    x = -0.05 + k * 0.025
    cone(bm, (x, -0.255, 1.0), (0, 0, -1), 0.007, 0.08 + 0.02 * (k % 2), seg=4)
    ell(bm, (x, -0.255, 0.9 - 0.02 * (k % 2)), (0.01, 0.01, 0.014), seg=5, rings=3)
attach(arm, "Hero_Sash", bm, M_WEAVE, "Hips")
bm = bmesh.new()
tube(bm, (0.17, -0.24, 0.98), (0.19, -0.255, 0.86), 0.022, 0.016)                   # curved talon: 3 segments
tube(bm, (0.19, -0.255, 0.86), (0.175, -0.27, 0.78), 0.016, 0.006)
ell(bm, (0.17, -0.24, 0.99), (0.026, 0.026, 0.026), seg=6, rings=4)
for k, dx in enumerate((-0.025, 0.0, 0.025)):
    cone(bm, (0.17 + dx, -0.24, 0.97), (dx * 3, 0, -1), 0.007, 0.1 + 0.02 * k, seg=4)
attach(arm, "Hero_FateTalon", bm, M_BONE, "Hips")

# ---------- feathered forearms ----------
for side, up, lo in ((1, "UpperArm.L", "LowerArm.L"), (-1, "UpperArm.R", "LowerArm.R")):
    bm = bmesh.new()
    for k in range(7):
        x = side * (0.17 + k * 0.045)
        for dy in (-0.03, 0.03):
            ell(bm, (x, -0.06 + dy, 1.40), (0.026, 0.012, 0.075), rot=(0, 0, side * math.radians(8)), seg=5, rings=3)
    attach(arm, "Hero_ArmFeathers_" + ("L" if side > 0 else "R"), bm, M_FEATHER, lo, smooth=False)

# ---------- bird feet: three forward toes, a back toe, talons ----------
for side, bone in ((1, "Foot.L"), (-1, "Foot.R")):
    bm = bmesh.new()
    fx, fy = side * 0.121, -0.062
    for dx, ln in ((-0.055, 0.17), (0.0, 0.21), (0.055, 0.17)):
        tip = Vector((fx + dx * 1.4, fy - ln, 0.02))
        tube(bm, Vector((fx, fy - 0.01, 0.06)), tip, 0.016, 0.011)
        cone(bm, tip, (dx * 2, -1, -0.5), 0.011, 0.05, seg=4)
    tip = Vector((fx, fy + 0.1, 0.02))
    tube(bm, Vector((fx, fy + 0.01, 0.06)), tip, 0.014, 0.01)
    cone(bm, tip, (0, 1, -0.5), 0.01, 0.045, seg=4)
    ell(bm, (fx, fy, 0.055), (0.03, 0.035, 0.04), seg=6, rings=4)
    attach(arm, "Hero_Talons_" + ("L" if side > 0 else "R"), bm, M_TALON, bone)

print("GC_TOTAL_TRIS", tri_count())
bpy.ops.wm.save_as_mainfile(filepath=OUT + "/grimcrow.blend")
bpy.ops.export_scene.gltf(filepath=OUT + "/grimcrow.glb", export_format='GLB', export_apply=True,
                          export_animations=False, export_skins=True)
print("GC_DONE")
