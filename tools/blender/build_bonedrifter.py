"""Bonedrifter hero: peaceful armoured bone-construct brute on the eldritch shared-skeleton base (Blender 5.x).
Run: blender -b -P build_bonedrifter.py -- <eldritch.glb> <out_dir>
Ivory carved-bone exoskeleton (rib lattice, layered pauldrons, slatted thigh/greave armour, bone boots, crested beaked skull mask)
over a tight dark knit textile underlayer, plus an ossified club. Bulky meshes on the shared skeleton. Baked textures (bone, knit)."""
import bpy, bmesh, math, sys, os, random
import numpy as np
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hero_common import *
import hero_textures as T

SRC, OUT = sys.argv[-2], sys.argv[-1]
random.seed(5)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
remove_objects("_Head", "_Feet")
TEX = os.path.join(OUT, "tex_bd")

# ---------- textures ----------
def bone_tex():
    n = 512; x, y = T._grid(n)
    nz = T.fbm(n, 3, 5, 5); fine = T.fbm(n, 4, 4, 22)
    ridge = 1 - np.abs(2 * T.fbm(n, 9, 5, 3) - 1)
    streak = T.smooth(0.88, 0.99, ridge)
    base = np.array([0.80, 0.70, 0.53], np.float32)
    col = base[None, None, :] * (0.82 + 0.30 * nz[..., None]) * (0.95 + 0.1 * fine[..., None])
    col = col * (1 - 0.35 * streak[..., None]) + streak[..., None] * 0.35 * np.array([0.5, 0.36, 0.2], np.float32)
    return (T.to_image("bone_diffuse", np.concatenate([col, np.ones((n, n, 1), np.float32)], -1), TEX),
            T.to_image("bone_normal", T.normal_from_height(0.5 * nz + 0.4 * fine + 0.3 * streak, 1.0), TEX, "Non-Color"))
def knit_tex():
    n = 512; x, y = T._grid(n); nz = T.fbm(n, 17, 4, 12)
    rows = np.floor(y * 40)
    h = 0.5 + 0.5 * np.sin(2 * np.pi * (x * 64 + (rows % 2) * 0.25)) * np.sin(2 * np.pi * y * 40 * 0.5 + 1.0)
    col = np.array([0.15, 0.12, 0.10], np.float32)[None, None, :] * (0.65 + 0.7 * h[..., None]) * (0.85 + 0.3 * nz[..., None])
    return (T.to_image("knit_diffuse", np.concatenate([col, np.ones((n, n, 1), np.float32)], -1), TEX),
            T.to_image("knit_normal", T.normal_from_height(h, 1.6), TEX, "Non-Color"))
bi, bn = bone_tex(); ki, kn = knit_tex()

# ---------- materials ----------
M_BONE = mat("BD_Bone", (0.80, 0.70, 0.53), 0.45, 0.0)
M_KNIT = mat("BD_Knit", (0.15, 0.12, 0.10), 0.95)
M_DARK = mat("BD_Socket", (0.015, 0.012, 0.01), 0.6)
M_JOINT = mat("BD_Joint", (0.58, 0.50, 0.36), 0.5)
T.bind(M_BONE, bi, bn); T.bind(M_JOINT, bi, bn); T.bind(M_KNIT, ki, kn)
for _o in bpy.data.objects:
    if _o.type == "MESH" and _o.name.endswith(("_Body", "_Legs")):
        _o.data.materials.clear()
        if _o.name.endswith("_Body"): _o.data.materials.append(M_BONE); _o.data.materials.append(M_KNIT)
        else: _o.data.materials.append(M_KNIT)

CY = -0.043
def ptube(bm, pts, r0, r1, seg=5):
    n = len(pts)
    for i in range(n - 1):
        tube(bm, pts[i], pts[i + 1], r0 + (r1 - r0) * i / (n - 1), r0 + (r1 - r0) * (i + 1) / (n - 1), seg=seg)

# ---------- head: crested beaked bone mask ----------
bm = bmesh.new()
ell(bm, (0, -0.045, 1.655), (0.078, 0.104, 0.092), seg=14, rings=9)
ell(bm, (0, -0.108, 1.615), (0.060, 0.070, 0.070), seg=12, rings=7)
cone(bm, (0, -0.125, 1.64), (0, -0.55, -0.85), 0.052, 0.105, seg=8, r2=0.012)            # beak / snout
for sx in (1, -1):
    ell(bm, (sx * 0.062, -0.07, 1.61), (0.018, 0.045, 0.045), rot=(0, 0, sx * 0.2), seg=8, rings=5)  # cheek plate
for i in range(6):                                                                     # crest of stacked plates
    t = i / 5
    ell(bm, (0, -0.085 + t * 0.10, 1.72 + 0.03 * math.sin(t * math.pi) + 0.02), (0.012 + 0.012 * math.sin(t * math.pi), 0.020, 0.032 + 0.02 * math.sin(t * math.pi)), seg=7, rings=4)
attach(arm, "Hero_Skull", bm, M_BONE, "Head")
bm = bmesh.new()
for sx in (1, -1):
    ell(bm, (sx * 0.036, -0.152, 1.652), (0.017, 0.012, 0.022), rot=(0, sx * math.radians(-15), 0), seg=8, rings=5)
    ell(bm, (sx * 0.020, -0.200, 1.585), (0.005, 0.004, 0.006), seg=4, rings=3)
attach(arm, "Hero_Sockets", bm, M_DARK, "Head")
def neck(r, c):
    a = 2 * math.pi * c; rad = 0.058 + 0.006 * math.sin(r * 5)
    return Vector((rad * math.sin(a), CY - rad * math.cos(a), 1.46 + r * 0.16))
skinned(arm, "Hero_Neck", strip(5, 14, neck), M_KNIT, lambda co: {"Neck": smoothstep(1.46, 1.52, co.z), "Chest": 1 - smoothstep(1.46, 1.52, co.z)})

# ---------- textile underlayer (bulky) ----------
def trx(z): return np.interp(z, [1.0, 1.15, 1.30, 1.45, 1.52], [0.20, 0.205, 0.235, 0.235, 0.15])
def try_(z): return np.interp(z, [1.0, 1.15, 1.30, 1.45, 1.52], [0.155, 0.16, 0.168, 0.16, 0.105])
def torso_w(co):
    ch = smoothstep(1.25, 1.40, co.z); tq = smoothstep(1.08, 1.2, co.z) * (1 - ch)
    ab = smoothstep(1.0, 1.1, co.z) * (1 - ch - tq)
    return {"Chest": ch, "Torso": tq, "Abdomen": max(0.0, ab), "Hips": max(0.0, 1 - ch - tq - max(0.0, ab))}
def torso(r, c):
    a = 2 * math.pi * c; z = 0.97 + r * 0.55
    return Vector((trx(z) * math.sin(a), CY - try_(z) * math.cos(a), z))
skinned(arm, "Hero_Torso", strip(14, 28, torso), M_KNIT, torso_w)
for side, ua, la, tag in ((1, "UpperArm.L", "LowerArm.L", "L"), (-1, "UpperArm.R", "LowerArm.R", "R")):
    def limb(r, c, side=side):
        a = 2 * math.pi * c; x = 0.15 + r * 0.45
        rad = 0.088 - 0.020 * smoothstep(0.1, 1.0, r) + 0.008 * math.sin(r * 4)
        return Vector((side * x, -0.056 - 0.03 * min(1, max(0, (x - 0.33) / 0.24)) + rad * math.sin(a), 1.432 + rad * math.cos(a)))
    skinned(arm, "Hero_ArmKnit_" + tag, strip(9, 12, limb), M_KNIT, lambda co, ua=ua, la=la: {ua: 1 - smoothstep(0.30, 0.38, abs(co.x)), la: smoothstep(0.30, 0.38, abs(co.x))})
for side, up, lo, tag in ((1, "UpperLeg.L", "LowerLeg.L", "L"), (-1, "UpperLeg.R", "LowerLeg.R", "R")):
    cx = side * 0.121
    def yl(z): return float(np.interp(z, [0.023, 0.533, 0.964], [-0.062, -0.087, -0.045]))
    def leg(r, c, cx=cx, yl=yl):
        a = 2 * math.pi * c; z = 1.02 - r * 1.0
        rad = float(np.interp(z, [0.02, 0.15, 0.35, 0.533, 0.75, 1.02], [0.066, 0.068, 0.092, 0.082, 0.112, 0.125]))
        return Vector((cx + rad * math.sin(a), yl(z) - rad * math.cos(a), z))
    skinned(arm, "Hero_LegKnit_" + tag, strip(14, 14, leg), M_KNIT, lambda co, up=up, lo=lo: {up: smoothstep(0.46, 0.60, co.z), lo: 1 - smoothstep(0.46, 0.60, co.z)})
# loincloth panels
def cloth(r, c, front):
    x = (c - 0.5) * 0.30; z = 1.05 - r * 0.34 - 0.02 * abs(math.sin(c * 9)) * r
    y = CY + (-1 if front else 1) * (0.158 + 0.04 * r + 0.01 * math.sin(c * 6))
    return Vector((x, y, z))
for front in (True, False):
    skinned(arm, "Hero_Loin_" + ("F" if front else "B"), strip(6, 8, lambda r, c, f=front: cloth(r, c, f)), M_KNIT,
            lambda co: {"Hips": 1 - 0.5 * smoothstep(0.95, 0.7, co.z), ("UpperLeg.L" if co.x >= 0 else "UpperLeg.R"): 0.5 * smoothstep(0.95, 0.7, co.z)})

# ---------- rib lattice, sternum, spine ----------
bm = bmesh.new()
for lvl in range(7):
    z0 = 1.465 - lvl * 0.047
    for sd in (1, -1):
        pts = []
        N = 15
        for i in range(N):
            t = i / (N - 1)
            a = math.radians(8 + t * 160)
            zz = z0 + 0.048 * math.cos(a) - 0.02 * t * (1 if lvl > 2 else 0.3)
            rx, ry = trx(zz) + 0.016, try_(zz) + 0.016
            pts.append(Vector((sd * rx * math.sin(a), CY - ry * math.cos(a), zz)))
        ptube(bm, pts, 0.020 - 0.0015 * lvl, 0.014, seg=5)
attach(arm, "Hero_Ribs", bm, M_BONE, "Torso")
bm = bmesh.new()
for i in range(10):                                                                        # sternum plates
    z = 1.485 - i * 0.040
    ell(bm, (0, CY - try_(z) - 0.022, z), (0.030 - 0.0018 * i, 0.016, 0.026), seg=8, rings=4)
for sx in (1, -1):                                                                         # clavicles
    ptube(bm, [Vector((sx * 0.02, -0.19, 1.485)), Vector((sx * 0.10, -0.18, 1.50)), Vector((sx * 0.19, -0.13, 1.49))], 0.022, 0.018, seg=6)
for i in range(11):                                                                        # spine
    z = 1.49 - i * 0.040
    ell(bm, (0, CY + try_(z) + 0.022, z), (0.026 - 0.0012 * i, 0.019, 0.022), seg=8, rings=4)
ell(bm, (0, CY + 0.14, 1.40), (0.17, 0.035, 0.11), seg=10, rings=6)                         # dorsal plate
for sx in (1, -1):
    ell(bm, (sx * 0.11, CY + 0.13, 1.33), (0.06, 0.03, 0.10), rot=(0, sx * 0.2, 0), seg=8, rings=5)  # shoulder-blade plates
attach(arm, "Hero_Sternum", bm, M_BONE, "Torso")

# ---------- pelvis plates ----------
def pelv(r, c):
    u = c * 2 - 1; z = 1.125 - r * 0.33
    w = 0.185 * (1 - 0.92 * r ** 1.3) + 0.008
    x = u * w
    y = CY - 0.156 * math.sqrt(max(0.0, 1 - (x / 0.21) ** 2)) - 0.030 - 0.02 * r
    return Vector((x, y, z))
attach(arm, "Hero_PelvisFront", strip(8, 11, pelv), M_BONE, "Hips")
bm = bmesh.new()
for sx in (1, -1):
    for k in range(3):
        ell(bm, (sx * (0.19 - 0.012 * k), CY - 0.02 + 0.01 * k, 1.08 - k * 0.075), (0.035, 0.085, 0.045), rot=(0, sx * 0.35, 0), seg=8, rings=5)
for k in range(3):
    ell(bm, (0, CY + 0.155 + 0.01 * k, 1.07 - k * 0.075), (0.11 - 0.015 * k, 0.03, 0.045), seg=8, rings=5)
attach(arm, "Hero_PelvisSide", bm, M_BONE, "Hips")

# ---------- pauldrons, arm plates ----------
def arch_pt(side, x0, x1, R, tip, r, c, z0):
    ph = math.radians(-85 + c * 170)
    x_end = x1 + tip * (1 - abs(ph) / math.radians(85)) ** 1.3
    x = x0 + r * (x_end - x0)
    rad = R * (1 - 0.10 * r)
    return Vector((side * x, -0.06 - rad * 0.95 * math.sin(ph), z0 + rad * 0.85 * math.cos(ph) - 0.05 * r * r))
PL = ((0.08, 0.25, 0.165, 0.045, 1.45), (0.15, 0.29, 0.155, 0.04, 1.42), (0.22, 0.34, 0.14, 0.035, 1.39))
for side, sb, ub, lb, tag in ((1, "Shoulder.L", "UpperArm.L", "LowerArm.L", "L"), (-1, "Shoulder.R", "UpperArm.R", "LowerArm.R", "R")):
    for i, (x0, x1, R, tip, z0) in enumerate(PL):
        attach(arm, f"Hero_Pauldron{i}_{tag}", strip(6, 13, lambda r, c, s=side, a=x0, b=x1, R_=R, t=tip, z=z0: arch_pt(s, a, b, R_, t, r, c, z)), M_BONE, sb if i == 0 else ub)
    bm = bmesh.new()                                                                      # shoulder joint ball + crest fin
    ell(bm, (side * 0.30, -0.056, 1.44), (0.085, 0.085, 0.085), seg=10, rings=6)
    ell(bm, (side * 0.14, -0.06, 1.60), (0.040, 0.025, 0.06), rot=(0, side * 0.4, 0), seg=7, rings=4)
    attach(arm, "Hero_ShoulderJoint_" + tag, bm, M_JOINT, ub)
    # upper-arm slats
    for k, (xa, xb) in enumerate(((0.34, 0.43),)):
        pass
    def ya(x): return -0.056 - 0.03 * min(1, max(0, (x - 0.33) / 0.24))
    for k in range(3):                                                                    # stacked upper-arm shells
        x0 = 0.34 + 0.0
    bm = bmesh.new()
    ell(bm, (side * 0.334, -0.056, 1.432), (0.06, 0.07, 0.07), seg=9, rings=6)           # elbow
    for k in range(2):
        ell(bm, (side * (0.27 + 0.0 + k * 0.0), -0.056 + 0.0, 1.50 - k * 0.0), (0.001, 0.001, 0.001), seg=3, rings=2)
    attach(arm, "Hero_Elbow_" + tag, bm, M_JOINT, lb)
    for k in range(4):                                                                    # gauntlet slat plates
        xs = 0.38 + k * 0.045
        def gaun(r, c, s=side, xs=xs, k=k):
            ph = math.radians(-125 + c * 250)
            x = xs + r * 0.072
            rad = 0.092 - 0.004 * k
            return Vector((s * x, -0.07 - 0.03 * (x - 0.33) / 0.24 - rad * math.sin(ph), 1.432 + rad * math.cos(ph)))
        attach(arm, f"Hero_Gauntlet{k}_{tag}", strip(3, 9, gaun), M_BONE, lb)
    bm = bmesh.new()
    ell(bm, (side * 0.63, -0.087, 1.445), (0.045, 0.05, 0.016), seg=8, rings=4)           # hand-back plate
    attach(arm, "Hero_HandPlate_" + tag, bm, M_BONE, f"Hand.{tag}")

# ---------- legs: slatted thigh armour, knees, greaves, bone boots ----------
for side, up, lo, foot, tag in ((1, "UpperLeg.L", "LowerLeg.L", "Foot.L", "L"), (-1, "UpperLeg.R", "LowerLeg.R", "Foot.R", "R")):
    cx = side * 0.121
    def yl(z): return float(np.interp(z, [0.023, 0.533, 0.964], [-0.062, -0.087, -0.045]))
    def shellfn(z0, z1, a0, a1, push, rf, bulge=0.012, cx=cx, yl=yl):
        def f(r, c):
            z = z0 + (z1 - z0) * r; a = math.radians(a0 + (a1 - a0) * c)
            rad = rf(z) + push + bulge * math.sin(math.pi * r)
            return Vector((cx + rad * math.sin(a), yl(z) - rad * math.cos(a), z))
        return f
    thr = lambda z: float(np.interp(z, [0.5, 0.75, 1.0], [0.092, 0.115, 0.128]))
    for k, (a0, a1) in enumerate(((-95, -45), (-30, 30), (45, 95), (-170, -115), (115, 170))):
        attach(arm, f"Hero_Thigh{k}_{tag}", strip(8, 5, shellfn(0.60, 0.97 - 0.03 * (k % 2), a0, a1, 0.018, thr, 0.014)), M_BONE, up)
    for k in range(2):                                                                    # thigh cross-bands
        attach(arm, f"Hero_ThighBand{k}_{tag}", strip(2, 20, shellfn(0.82 - 0.17 * k, 0.86 - 0.17 * k, -180, 180, 0.026, thr, 0.0)), M_JOINT, up)
    bm = bmesh.new()
    ell(bm, (cx, yl(0.53) - 0.10, 0.53), (0.082, 0.050, 0.095), seg=10, rings=7)         # knee cap
    ell(bm, (cx, yl(0.53) + 0.03, 0.53), (0.072, 0.060, 0.08), seg=8, rings=5)           # knee back
    attach(arm, "Hero_Knee_" + tag, bm, M_BONE, lo)
    shn = lambda z: float(np.interp(z, [0.05, 0.2, 0.35, 0.47], [0.074, 0.098, 0.115, 0.095]))
    for k, (a0, a1) in enumerate(((-100, -45), (-25, 25), (45, 100), (-175, -120), (120, 175))):
        attach(arm, f"Hero_Greave{k}_{tag}", strip(8, 5, shellfn(0.10, 0.47, a0, a1, 0.020, shn, 0.016)), M_BONE, lo)
    attach(arm, "Hero_AnkleBand_" + tag, strip(2, 20, shellfn(0.075, 0.115, -180, 180, 0.026, shn, 0.0)), M_JOINT, lo)
    bm = bmesh.new()
    ell(bm, (cx, -0.075, 0.062), (0.074, 0.105, 0.055), seg=12, rings=7)                 # heel / midfoot
    ell(bm, (cx, -0.155, 0.040), (0.070, 0.085, 0.036), seg=10, rings=6)
    for j in range(4):                                                                    # toe segments
        tx = cx + (j - 1.5) * 0.034
        ell(bm, (tx, -0.250 + 0.008 * abs(j - 1.5), 0.028), (0.020, 0.040, 0.024), seg=7, rings=5)
    ell(bm, (cx, -0.115, 0.095), (0.076, 0.085, 0.032), rot=(math.radians(-10), 0, 0), seg=10, rings=5)  # instep plate
    attach(arm, "Hero_Foot_" + tag, bm, M_BONE, foot)

# ---------- ossified club (right hand) ----------
hx, hy, hz = -0.625, -0.087, 1.435
bm = bmesh.new(); bj = bmesh.new()
z0 = hz - 0.58; z1 = hz + 0.45
tube(bm, (hx, hy, z0), (hx, hy, z1), 0.022, 0.026, seg=8)
for z in np.linspace(z0 + 0.1, z1 - 0.1, 4):
    ell(bj, (hx, hy, float(z)), (0.034, 0.034, 0.020), seg=8, rings=5)
ell(bj, (hx, hy, z0), (0.040, 0.040, 0.040), seg=8, rings=5)
ell(bm, (hx, hy, z1 + 0.05), (0.070, 0.070, 0.075), seg=10, rings=6)                     # head
for k in range(4):
    a = k * math.pi / 2 + math.pi / 4
    cone(bm, (hx + 0.05 * math.cos(a), hy + 0.05 * math.sin(a), z1 + 0.05), (math.cos(a), math.sin(a), 0.7), 0.035, 0.12, seg=6, r2=0.008)
cone(bm, (hx, hy, z1 + 0.10), (0, 0, 1), 0.04, 0.10, seg=6, r2=0.008)
attach(arm, "Hero_Club", bm, M_BONE, "Hand.R"); attach(arm, "Hero_ClubJoints", bj, M_JOINT, "Hand.R")

print("BD_TOTAL_TRIS", tri_count())
bpy.ops.wm.save_as_mainfile(filepath=OUT + "/bonedrifter.blend")
bpy.ops.export_scene.gltf(filepath=OUT + "/bonedrifter.glb", export_format='GLB', export_apply=True,
                          export_animations=False, export_skins=True)
print("BD_DONE")
