"""Dreamhusk hero: serene fungal humanoid on the eldritch shared-skeleton base (Blender 5.x).
Run: blender -b -P build_dreamhusk.py -- <eldritch.glb> <out_dir>
Wide gilled mushroom-cap hood (moss + tiny mushrooms), mycelium hair, layered ragged husk skirts in olive/ochre/tan,
leaf mantle, wide husk sleeves, forager satchel with spore pods, lace-up boots. Baked textures (husk, gills, cap, leather)."""
import bpy, bmesh, math, sys, os, random
import numpy as np
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hero_common import *
import hero_textures as T

SRC, OUT = sys.argv[-2], sys.argv[-1]
random.seed(21)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
remove_objects("_Head", "_Feet")
TEX = os.path.join(OUT, "tex_dh")

# ---------- materials ----------
M_SKIN   = mat("DH_Skin", (0.74, 0.60, 0.46), 0.6)
M_BODY2  = mat("DH_BodyHusk", (0.36, 0.30, 0.17), 0.9)
M_LEGS   = mat("DH_LegWrap", (0.40, 0.33, 0.22), 0.9)
M_FACE   = mat("DH_Face", (0.78, 0.62, 0.50), 0.55)
M_HAIR   = mat("DH_Hair", (0.78, 0.66, 0.42), 0.5)
M_EYE    = mat("DH_Eye", (0.45, 0.38, 0.18), 0.2)
M_LIPS   = mat("DH_Lips", (0.62, 0.38, 0.32), 0.5)
M_DARK   = mat("DH_Lash", (0.20, 0.14, 0.08), 0.6)
M_CAP    = mat("DH_CapTop", (0.30, 0.34, 0.12), 0.8)
M_GILL   = mat("DH_Gills", (0.82, 0.52, 0.42), 0.55)
M_GREEN  = mat("DH_HuskGreen", (0.28, 0.32, 0.12), 0.9)
M_OCHRE  = mat("DH_HuskOchre", (0.52, 0.37, 0.12), 0.9)
M_TAN    = mat("DH_HuskTan", (0.55, 0.45, 0.30), 0.9)
M_SLEEVE = mat("DH_Sleeve", (0.62, 0.52, 0.36), 0.8, alpha=0.88)
M_LEATH  = mat("DH_Leather", (0.22, 0.13, 0.07), 0.55)
M_MOSS   = mat("DH_Moss", (0.30, 0.38, 0.08), 0.95)
M_SHROOM = mat("DH_Mushroom", (0.60, 0.38, 0.20), 0.6)
M_STEM   = mat("DH_Stem", (0.80, 0.70, 0.52), 0.7)
M_POD    = mat("DH_Pod", (0.62, 0.44, 0.24), 0.45)
M_BRASS  = mat("DH_Brass", (0.65, 0.48, 0.2), 0.35, 0.9)

# ---------- textures ----------
def husk_tex(name, base, seed):
    n = 512; x, y = T._grid(n)
    nz = T.fbm(n, seed, 5, 6)
    e, cid = T.voronoi(n, 16, seed + 3)
    vein = 1 - T.smooth(0.0, 0.14, e)
    fine = T.fbm(n, seed + 8, 3, 24)
    b = np.array(base, np.float32)
    col = b[None, None, :] * (0.65 + 0.7 * nz[..., None]) * (0.85 + 0.3 * cid[..., None])
    col = col * (1 - 0.3 * vein[..., None]) + 0.35 * vein[..., None] * np.array([0.72, 0.62, 0.45], np.float32) * (0.7 + 0.3 * fine[..., None])
    moss = T.smooth(0.55, 0.8, T.fbm(n, seed + 20, 4, 4))
    col = col * (1 - 0.5 * moss[..., None]) + moss[..., None] * 0.5 * np.array([0.22, 0.32, 0.06], np.float32)
    h = 0.6 * vein + 0.3 * nz + 0.15 * fine
    return (T.to_image(name + "_diffuse", np.concatenate([col, np.ones((n, n, 1), np.float32)], -1), TEX),
            T.to_image(name + "_normal", T.normal_from_height(h, 1.4), TEX, "Non-Color"))
def gill_tex():
    n = 512; x, y = T._grid(n); nz = T.fbm(n, 31, 4, 8)
    ln = 0.5 + 0.5 * np.sin(x * 160 * 2 * np.pi + 3 * nz)
    ln2 = 0.5 + 0.5 * np.sin(x * 80 * 2 * np.pi)
    g = ln * (0.7 + 0.3 * ln2)
    col = np.stack([0.88 - 0.25 * g, 0.62 - 0.22 * g, 0.50 - 0.18 * g], -1) * (0.8 + 0.3 * nz[..., None]) * (1 - 0.25 * T.smooth(0.8, 1.0, y))[..., None]
    return (T.to_image("gill_diffuse", np.concatenate([col, np.ones((n, n, 1), np.float32)], -1), TEX),
            T.to_image("gill_normal", T.normal_from_height(g, 1.6), TEX, "Non-Color"))
def cap_tex():
    n = 512; x, y = T._grid(n)
    nz = T.fbm(n, 41, 5, 5); nz2 = T.fbm(n, 43, 4, 14)
    moss = T.smooth(0.30, 0.55, nz)
    col = (np.array([0.50, 0.38, 0.28], np.float32)[None, None, :] * (1 - moss[..., None])
           + np.array([0.26, 0.34, 0.08], np.float32)[None, None, :] * moss[..., None]) * (0.75 + 0.5 * nz2[..., None])
    e, _ = T.voronoi(n, 8, 45); vein = 1 - T.smooth(0.0, 0.1, e)
    col = col + vein[..., None] * 0.08
    return (T.to_image("cap_diffuse", np.concatenate([col, np.ones((n, n, 1), np.float32)], -1), TEX),
            T.to_image("cap_normal", T.normal_from_height(0.5 * nz2 + 0.5 * moss + 0.3 * vein, 1.6), TEX, "Non-Color"))
def leather_tex():
    n = 256; nz = T.fbm(n, 51, 5, 6); crack = T.fbm(n, 52, 4, 20)
    col = np.array([0.24, 0.14, 0.07], np.float32)[None, None, :] * (0.7 + 0.6 * nz[..., None]) * (0.85 + 0.3 * crack[..., None])
    return (T.to_image("leather_diffuse", np.concatenate([col, np.ones((n, n, 1), np.float32)], -1), TEX),
            T.to_image("leather_normal", T.normal_from_height(0.5 * nz + 0.5 * crack, 1.2), TEX, "Non-Color"))
gi, gn = husk_tex("husk_green", (0.26, 0.30, 0.11), 3)
oi, on = husk_tex("husk_ochre", (0.56, 0.40, 0.13), 7)
ti, tn = husk_tex("husk_tan", (0.58, 0.47, 0.32), 11)
gli, gln = gill_tex(); cpi, cpn = cap_tex(); li, ln_ = leather_tex()
T.bind(M_GREEN, gi, gn); T.bind(M_OCHRE, oi, on); T.bind(M_TAN, ti, tn); T.bind(M_BODY2, ti, tn)
T.bind(M_GILL, gli, gln); T.bind(M_CAP, cpi, cpn); T.bind(M_LEATH, li, ln_)

for _o in bpy.data.objects:
    if _o.type == "MESH" and _o.name.endswith(("_Body", "_Legs")):
        if _o.name.endswith("_Body"):
            _o.data.materials.clear(); _o.data.materials.append(M_SKIN); _o.data.materials.append(M_BODY2)
        else:
            _o.data.materials.clear(); _o.data.materials.append(M_LEGS)

# ---------- face: serene, soft, no pointed ears ----------
bm = bmesh.new()
ell(bm, (0, -0.04, 1.655), (0.078, 0.102, 0.097), seg=18, rings=12)
ell(bm, (0, -0.085, 1.600), (0.059, 0.072, 0.068), seg=14, rings=9)
ell(bm, (0, -0.098, 1.550), (0.029, 0.038, 0.032), seg=12, rings=7)
for sx in (1, -1):
    ell(bm, (sx * 0.040, -0.062, 1.568), (0.020, 0.046, 0.036), seg=10, rings=6)
    ell(bm, (sx * 0.046, -0.108, 1.596), (0.014, 0.012, 0.010), seg=8, rings=5)
    ell(bm, (sx * 0.034, -0.134, 1.668), (0.034, 0.011, 0.007), rot=(0, sx * math.radians(10), 0), seg=8, rings=5)
    ell(bm, (sx * 0.078, -0.035, 1.634), (0.008, 0.020, 0.030), seg=8, rings=5)                  # small ear
tube(bm, (0, -0.138, 1.652), (0, -0.164, 1.612), 0.010, 0.013, seg=6)
ell(bm, (0, -0.166, 1.609), (0.013, 0.014, 0.011), seg=8, rings=5)
ell(bm, (0, -0.040, 1.50), (0.038, 0.040, 0.055), seg=10, rings=6)
attach(arm, "Hero_Face", bm, M_FACE, "Head")
bm = bmesh.new()
ell(bm, (0, -0.1475, 1.5725), (0.020, 0.010, 0.006), seg=8, rings=4)
ell(bm, (0, -0.145, 1.5625), (0.018, 0.010, 0.007), seg=8, rings=4)
attach(arm, "Hero_Lips", bm, M_LIPS, "Head")
bm = bmesh.new()
for sx in (1, -1):
    ell(bm, (sx * 0.035, -0.139, 1.653), (0.020, 0.005, 0.004), rot=(0, sx * math.radians(10), 0), seg=8, rings=4)
    ell(bm, (sx * 0.037, -0.144, 1.676), (0.024, 0.005, 0.004), rot=(0, sx * math.radians(14), 0), seg=8, rings=4)
attach(arm, "Hero_Liner", bm, M_DARK, "Head")
bm = bmesh.new()
for sx in (1, -1):
    ell(bm, (sx * 0.035, -0.139, 1.640), (0.0155, 0.0085, 0.0095), seg=10, rings=6)
attach(arm, "Hero_Eyes", bm, M_EYE, "Head")

# ---------- mycelium hair: long pale strands under the cap ----------
bm = bmesh.new()
ell(bm, (0, -0.030, 1.664), (0.088, 0.108, 0.098), seg=14, rings=9)
for k in range(70):
    ph = math.radians(random.uniform(-150, 150))
    root = Vector((0.085 * math.sin(ph), -0.04 - 0.10 * math.cos(ph), random.uniform(1.60, 1.72)))
    p = root; side = 1 if math.sin(ph) >= 0 else -1
    ln = random.uniform(0.22, 0.40) * (1.2 if abs(ph) > 1.2 else 0.8)
    n = 4
    for i in range(n):
        q = p + Vector((side * random.uniform(0.0, 0.02) * (1 if abs(ph) > 1.0 else 0.3), 0.004 + (0.012 if abs(ph) > 1.8 else 0), -ln / n))
        if abs(ph) < 0.9: q.y -= 0.004
        tube(bm, p, q, 0.0045 * (1 - i / n) + 0.0015, 0.0045 * (1 - (i + 1) / n) + 0.0012, seg=3)
        p = q
attach(arm, "Hero_Hair", bm, M_HAIR, "Head")

# ---------- mushroom cap hood ----------
CAP_C = Vector((0.0, -0.02, 0.0)); CAP_R = 0.31
def edge(a):
    R = CAP_R * (1 + 0.07 * math.sin(6 * a + 1.0) + 0.04 * math.sin(11 * a + 0.5))
    z = 1.665 + 0.032 * math.sin(8 * a + 0.3) + 0.022 * math.cos(a) - 0.012 * math.sin(a * 3)
    return R, z
def cap_pt(r, a, top=True):
    R, ez = edge(a)
    rad = R * r
    if top:
        z = ez + (1.93 - ez) * (1 - r ** 2.1)
        # ruffles near the rim
        z += 0.012 * math.sin(a * 14) * r ** 6
    else:
        z = ez + 0.19 * (1 - r) ** 1.0 - 0.004
    return Vector((CAP_C.x + rad * math.sin(a), CAP_C.y - rad * math.cos(a), z))
def cap_top(rr, c):
    return cap_pt(0.02 + 0.98 * (1 - rr), 2 * math.pi * c, True) if False else cap_pt(1.0 - rr * 0.98, 2 * math.pi * c, True)
attach(arm, "Hero_CapTop", strip(12, 40, lambda r, c: cap_pt(1.0 - r * 0.98, 2 * math.pi * c, True)), M_CAP, "Head")
attach(arm, "Hero_CapGills", strip(6, 40, lambda r, c: cap_pt(1.0 - r * 0.80, 2 * math.pi * c, False)), M_GILL, "Head")
bm = bmesh.new(); mb = bmesh.new(); st = bmesh.new()
for (a, r, s) in ((0.6, 0.45, 0.034), (0.9, 0.35, 0.026), (-0.5, 0.55, 0.030), (2.2, 0.50, 0.032), (2.5, 0.38, 0.025),
                  (-2.0, 0.60, 0.030), (3.6, 0.30, 0.040), (4.3, 0.55, 0.028), (1.6, 0.72, 0.026), (5.3, 0.70, 0.024)):
    p = cap_pt(r, a, True); n = Vector((math.sin(a) * 0.35 * r, -math.cos(a) * 0.35 * r, 1)).normalized()
    tube(st, p - n * 0.004, p + n * 0.030, s * 0.28, s * 0.22, seg=5)
    ell(mb, p + n * (0.030 + s * 0.1), (s, s, s * 0.45), seg=9, rings=5)
for (a, r) in ((0.1, 0.9), (1.3, 0.85), (2.9, 0.88), (4.0, 0.8), (5.0, 0.9), (0.4, 0.2), (3.1, 0.55), (5.8, 0.5), (1.9, 0.3), (4.7, 0.35)):
    p = cap_pt(r, a, True)
    for k in range(3):
        ell(bm, p + Vector((random.uniform(-.03, .03), random.uniform(-.03, .03), 0.008)), (0.032, 0.03, 0.014), seg=7, rings=4)
attach(arm, "Hero_CapMoss", bm, M_MOSS, "Head"); attach(arm, "Hero_CapShrooms", mb, M_SHROOM, "Head"); attach(arm, "Hero_CapStems", st, M_STEM, "Head")

# ---------- weights ----------
def skirt_w(co):
    t = smoothstep(1.0, 0.45, co.z)
    front = abs(co.y + 0.043) / max(1e-6, math.hypot(co.x, co.y + 0.043))
    wl = t * (0.2 + 0.55 * front)
    return {"Hips": 1.0 - wl, ("UpperLeg.L" if co.x >= 0 else "UpperLeg.R"): wl}

# ---------- bodice (green husk, under mantle) ----------
def bodice(r, c):
    a = 2 * math.pi * c
    z = 1.46 - r * 0.42
    w = 0.15 + 0.03 * math.sin(r * 3.0) - 0.02 * math.sin(r * math.pi) * 0.0 + 0.012 * r
    return Vector((w * 1.02 * math.sin(a), -0.043 - w * 0.9 * math.cos(a), z))
skinned(arm, "Hero_Bodice", strip(8, 28, bodice), M_GREEN, lambda co: ({"Chest": 1.0} if co.z > 1.38 else {"Torso": smoothstep(1.2, 1.38, co.z), "Abdomen": 1 - smoothstep(1.2, 1.38, co.z)} if co.z > 1.2 else {"Abdomen": smoothstep(1.05, 1.2, co.z), "Hips": 1 - smoothstep(1.05, 1.2, co.z)}))

# ---------- layered ragged husk skirts ----------
TIERS = [  # (top z, hem z, material, radius extra, phase, tooth amp)
    (1.07, 0.80, M_GREEN, 0.000, 0.0, 0.06),
    (1.00, 0.66, M_TAN, 0.016, 1.3, 0.07),
    (0.92, 0.54, M_OCHRE, 0.030, 2.1, 0.08),
    (0.84, 0.43, M_GREEN, 0.044, 0.7, 0.08),
    (0.74, 0.34, M_TAN, 0.058, 2.9, 0.07),
    (0.64, 0.28, M_OCHRE, 0.070, 1.9, 0.06),
]
def skirt_pt(r, c, top, hem, extra, ph, amp):
    a = 2 * math.pi * c
    tooth = (abs(math.sin(a * 7.5 + ph)) ** 0.7) * amp + 0.025 * math.sin(a * 3 + ph)
    z = top + r * (hem - tooth * r - top)
    rad = 0.185 + extra + (0.05 + 0.10 * (1.0 - top) ) * (r ** 1.2) + 0.012 * math.sin(a * 11 + ph) * r
    return Vector((rad * math.sin(a), -0.043 - rad * math.cos(a) * 0.95, z))
for i, (top, hem, m, ex, ph, amp) in enumerate(TIERS):
    skinned(arm, f"Hero_Skirt{i}", strip(5, 56, lambda r, c, top=top, hem=hem, ex=ex, ph=ph, amp=amp: skirt_pt(r, c, top, hem, ex, ph, amp)), m, skirt_w)
bm = bmesh.new()                                                                    # moss clumps on hems
for i, (top, hem, m, ex, ph, amp) in enumerate(TIERS):
    for k in range(5):
        c = random.random(); p = skirt_pt(0.97, c, top, hem, ex, ph, amp)
        ell(bm, p + Vector((0, 0, 0.01)), (0.026, 0.026, 0.014), seg=6, rings=4)
skinned(arm, "Hero_SkirtMoss", bm, M_MOSS, skirt_w)
# leg wraps between hem and boots
for side, lower in ((1, "LowerLeg.L"), (-1, "LowerLeg.R")):
    cx = side * 0.121
    def wrap(r, c, cx=cx):
        a = 2 * math.pi * c
        rad = 0.056 + 0.006 * math.sin(c * 40 + r * 9)
        return Vector((cx + rad * math.cos(a), -0.075 + rad * math.sin(a) * 1.05, 0.55 - r * 0.28))
    skinned(arm, "Hero_LegWrap_" + ("L" if side > 0 else "R"), strip(8, 14, wrap), M_LEGS, lambda co, lower=lower: {lower: 1.0})

# ---------- boots: lace-up, mossy ----------
for side, lower, foot in ((1, "LowerLeg.L", "Foot.L"), (-1, "LowerLeg.R", "Foot.R")):
    cx = side * 0.121
    def shaft(r, c, cx=cx):
        a = 2 * math.pi * c
        return Vector((cx + (0.060 - 0.008 * min(1.0, r * 1.6) + (0.012 if r < 0.05 else 0.0)) * math.cos(a),
                       -0.087 + 0.025 * r + (0.062 - 0.008 * min(1.0, r * 1.6)) * math.sin(a) * 1.05, 0.34 - r * 0.31))
    def wshaft(co, lower=lower, foot=foot):
        t = smoothstep(0.30, 0.10, co.z); return {lower: 1.0 - t, foot: t}
    skinned(arm, "Hero_BootShaft_" + ("L" if side > 0 else "R"), strip(10, 18, shaft), M_LEATH, wshaft)
    bm = bmesh.new()
    ell(bm, (cx, -0.135, 0.050), (0.052, 0.105, 0.042), seg=12, rings=7)
    ell(bm, (cx, -0.046, 0.052), (0.047, 0.050, 0.050), seg=10, rings=6)
    ell(bm, (cx, -0.105, 0.016), (0.056, 0.138, 0.014), seg=12, rings=5)
    attach(arm, "Hero_BootFoot_" + ("L" if side > 0 else "R"), bm, M_LEATH, foot)
    bm = bmesh.new()
    for k in range(5):                                                               # lacing
        z = 0.30 - k * 0.045
        ell(bm, (cx - side * 0.012, -0.147 + 0.0, z), (0.026, 0.008, 0.007), rot=(0, math.radians(20 * (1 if k % 2 else -1)), 0), seg=6, rings=3)
    tube(bm, (cx, -0.185, 0.07), (cx, -0.13, 0.14), 0.006, 0.006, seg=4)
    attach(arm, "Hero_BootLaces_" + ("L" if side > 0 else "R"), bm, M_TAN, foot)
    bm = bmesh.new()
    ell(bm, (cx + side * 0.01, -0.082, 0.325), (0.038, 0.032, 0.016), seg=7, rings=4)  # moss at cuff
    attach(arm, "Hero_BootMoss_" + ("L" if side > 0 else "R"), bm, M_MOSS, lower)

# ---------- leaf mantle (layered shoulder cape) ----------
def mant_pt(r, c, k):
    a = 2 * math.pi * c
    dz = (0.16, 0.24, 0.31)[k]
    tooth = (abs(math.sin(a * (8 + 2 * k) + k)) ** 0.7) * 0.05 * r
    rx, ry = 0.11 + (0.14 + 0.02 * k) * r, 0.10 + (0.08 + 0.015 * k) * r
    z = 1.505 - r * (dz + tooth) - 0.008 * k
    return Vector((rx * math.sin(a), -0.043 - ry * math.cos(a), z))
def mant_w_for(co):
    sd = "L" if co.x >= 0 else "R"
    s = smoothstep(0.10, 0.28, abs(co.x)) * 0.85
    return {"Chest": 1.0 - s, f"Shoulder.{sd}": s}
for k, m in enumerate((M_GREEN, M_OCHRE, M_TAN)):
    skinned(arm, f"Hero_Mantle{k}", strip(5, 56, lambda r, c, k=k: mant_pt(r, c, k)), (M_TAN, M_OCHRE, M_GREEN)[k], mant_w_for)
def scarf(r, c):
    a = 2 * math.pi * c; rad = 0.082 + 0.016 * math.sin(r * math.pi) + 0.004 * math.sin(c * 40)
    return Vector((rad * math.sin(a), -0.043 - rad * math.cos(a), 1.49 + r * 0.045))
attach(arm, "Hero_Scarf", strip(5, 26, scarf), M_GREEN, "Chest")
bm = bmesh.new()
for a in (0.4, 2.0, 3.5, 5.1):
    p = scarf(0.5, a / (2 * math.pi))
    for k in range(3):
        s = 0.020 - 0.003 * k
        ell(bm, p + Vector((0.01 * k, 0.0, 0.01 * k)), (s * 1.2, s * 1.2, s * 0.5), seg=8, rings=4)
attach(arm, "Hero_ScarfShrooms", bm, M_SHROOM, "Chest")

# ---------- wide husk sleeves ----------
for side, ua, la, tag in ((1, "UpperArm.L", "LowerArm.L", "L"), (-1, "UpperArm.R", "LowerArm.R", "R")):
    def sl(r, c, side=side):
        a = 2 * math.pi * c
        hem = 0.50 + 0.045 * (abs(math.sin(a * 3.5)) ** 0.7)
        x = 0.14 + r * (hem - 0.14)
        rad = 0.056 + 0.034 * r ** 1.5 + 0.008 * math.sin(a * 5 + 1.0) * r
        return Vector((side * x, -0.056 - 0.03 * (x - 0.15) / 0.4 + rad * math.sin(a) * 0.9, 1.432 + rad * math.cos(a)))
    def slw(co, ua=ua, la=la):
        s = smoothstep(0.26, 0.40, abs(co.x)); return {ua: 1.0 - s, la: s}
    skinned(arm, "Hero_Sleeve_" + tag, strip(9, 14, sl), M_SLEEVE, slw)
    def sl2(r, c, side=side):
        a = 2 * math.pi * c
        hem = 0.42 + 0.04 * (abs(math.sin(a * 2.5 + 1)) ** 0.7)
        x = 0.16 + r * (hem - 0.16)
        rad = 0.070 + 0.034 * r ** 1.5
        return Vector((side * x, -0.056 - 0.03 * (x - 0.15) / 0.4 + rad * math.sin(a) * 0.9, 1.432 + rad * math.cos(a) + 0.006))
    skinned(arm, "Hero_SleeveOver_" + tag, strip(7, 12, sl2), M_GREEN, slw)
    # wrist bangles
    bm = bmesh.new()
    for k in range(4):
        x = side * (0.585 + k * 0.018)
        bmesh.ops.create_cone(bm, cap_ends=False, segments=10, radius1=0.036, radius2=0.036, depth=0.011,
                              matrix=Matrix.Translation((x, -0.086, 1.432)) @ Matrix.Rotation(math.radians(90), 4, 'Y'))
    attach(arm, "Hero_Bangles_" + tag, bm, M_LEATH, la)

# ---------- belt with lace and charms ----------
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=False, segments=24, radius1=0.186, radius2=0.186, depth=0.045, matrix=Matrix.Translation((0, -0.045, 1.07)))
ell(bm, (0, -0.228, 1.07), (0.026, 0.010, 0.026), seg=8, rings=5)
attach(arm, "Hero_Belt", bm, M_LEATH, "Hips")
bm = bmesh.new()
for sx in (-1, 1):
    tube(bm, (sx * 0.02, -0.232, 1.06), (sx * 0.035, -0.236, 0.90), 0.005, 0.004, seg=4)
ell(bm, (0, -0.231, 1.07), (0.016, 0.006, 0.016), seg=8, rings=4)
attach(arm, "Hero_BeltLace", bm, M_BRASS, "Hips")

# ---------- forager satchel + strap + spore pods ----------
def strap(r, c):
    x = -0.10 + 0.36 * r; z = 1.50 - 0.60 * r
    ry = 0.19 * math.sqrt(max(0.08, 1 - (x / 0.24) ** 2))
    p = Vector((x, -0.043 - ry - 0.012, z))
    return p + Vector((0.016 * (c - 0.5) * 2 * 0.85, 0, 0.016 * (c - 0.5) * 2 * 0.5))
skinned(arm, "Hero_Strap", strip(26, 2, strap), M_LEATH, lambda co: {"Torso": 0.8, "Chest": 0.2} if co.z > 1.2 else {"Torso": 1.0})
SX, SY, SZ = 0.285, -0.075, 0.90
bm = bmesh.new()
ell(bm, (SX, SY, SZ), (0.045, 0.100, 0.085), seg=12, rings=8)
ell(bm, (SX + 0.005, SY, SZ + 0.052), (0.047, 0.108, 0.040), seg=12, rings=6)
attach(arm, "Hero_Satchel", bm, M_LEATH, "Hips")
bm = bmesh.new()
tube(bm, (SX + 0.01, SY - 0.02, SZ + 0.09), (-0.05 + 0.36, -0.2, 1.01), 0.008, 0.008, seg=4)
ell(bm, (SX + 0.052, SY, SZ + 0.04), (0.008, 0.03, 0.030), seg=7, rings=4)
attach(arm, "Hero_SatchelClasp", bm, M_BRASS, "Hips")
bm = bmesh.new(); bs = bmesh.new()
for k, (dy, dz, s) in enumerate(((-0.07, -0.14, 0.032), (-0.03, -0.19, 0.026), (0.01, -0.13, 0.022))):
    p = Vector((SX + 0.055, SY + dy, SZ + dz))
    tube(bm, p + Vector((0, 0, 0.12 + 0.02 * k)), p + Vector((0, 0, s * 1.1)), 0.003, 0.003, seg=3)
    ell(bm, p, (s * 0.8, s * 0.8, s * 1.25), seg=9, rings=6)
    cone(bs, p + Vector((0, 0, s * 1.1)), (0, 0, 1), s * 0.45, s * 0.5, seg=6, r2=0.003)
attach(arm, "Hero_Pods", bm, M_POD, "Hips"); attach(arm, "Hero_PodCaps", bs, M_BRASS, "Hips")

print("DH_TOTAL_TRIS", tri_count())
bpy.ops.wm.save_as_mainfile(filepath=OUT + "/dreamhusk.blend")
bpy.ops.export_scene.gltf(filepath=OUT + "/dreamhusk.glb", export_format='GLB', export_apply=True,
                          export_animations=False, export_skins=True)
print("DH_DONE")
