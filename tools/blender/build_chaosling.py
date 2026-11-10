"""Chaosling hero: reality-altered wild mage on the eldritch shared-skeleton base (Blender 5.x).
Run: blender -b -P build_chaosling.py -- <eldritch.glb> <out_dir>
Curly purple/silver hair with a gold-ringed braid, pointed ears, iridescent scale patches, asymmetric patchwork Chaos-Weave coat with gold
stitching over baggy trousers, crossed belts, spellbook + pouch, tall buckled boots and a halo of floating entropy-crystal shards.
Baked textures (patchwork x2, leather, iridescent scales)."""
import bpy, bmesh, math, sys, os, random
import numpy as np
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hero_common import *
import hero_textures as T

SRC, OUT = sys.argv[-2], sys.argv[-1]
random.seed(31)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
remove_objects("_Head", "_Feet")
TEX = os.path.join(OUT, "tex_cl")

# ---------- textures ----------
def patch_tex(name, palette, seed, cells=6):
    n = 512
    e, cid = T.voronoi(n, cells, seed)
    nz = T.fbm(n, seed + 1, 5, 8)
    pal = np.array(palette, np.float32)
    idx = (cid * 997 % 1.0 * len(pal)).astype(int) % len(pal)
    col = pal[idx] * (0.8 + 0.4 * nz[..., None])
    stitch = (1 - T.smooth(0.0, 0.07, e))
    dash = (np.sin(np.arange(n)[None, :] * 0.9 + np.arange(n)[:, None] * 0.9) > -0.2).astype(np.float32)
    st = stitch * dash * 0.7
    gold = np.array([0.85, 0.62, 0.22], np.float32)
    col = col * (1 - st[..., None]) + gold[None, None, :] * st[..., None]
    weave = 0.5 + 0.5 * np.sin(np.arange(n)[None, :] * 1.6) * np.sin(np.arange(n)[:, None] * 1.6)
    h = 0.3 * weave + 0.4 * nz + 0.6 * st
    emis = np.stack([st * 0.5, st * 0.3, st * 0.05, np.ones((n, n), np.float32)], -1)
    return (T.to_image(name + "_diffuse", np.concatenate([col, np.ones((n, n, 1), np.float32)], -1), TEX),
            T.to_image(name + "_normal", T.normal_from_height(h, 1.2), TEX, "Non-Color"))
def scale_tex():
    n = 512; e, cid = T.voronoi(n, 14, 77); nz = T.fbm(n, 78, 4, 6)
    cell = T.smooth(0.0, 0.3, e)
    ph = cid * 6.28 + nz * 3
    col = np.stack([0.65 + 0.3 * np.sin(ph), 0.62 + 0.3 * np.sin(ph + 2.1), 0.75 + 0.2 * np.sin(ph + 4.2)], -1) * (0.7 + 0.3 * cell[..., None])
    emis = np.concatenate([col * 0.5, np.ones((n, n, 1), np.float32)], -1)
    return (T.to_image("scale_diffuse", np.concatenate([col, np.ones((n, n, 1), np.float32)], -1), TEX),
            T.to_image("scale_normal", T.normal_from_height(cell, 1.5), TEX, "Non-Color"),
            T.to_image("scale_emission", emis, TEX))
def leather_tex():
    n = 256; nz = T.fbm(n, 51, 5, 6); crack = T.fbm(n, 52, 4, 20)
    col = np.array([0.26, 0.16, 0.12], np.float32)[None, None, :] * (0.7 + 0.6 * nz[..., None]) * (0.85 + 0.3 * crack[..., None])
    return (T.to_image("leather_diffuse", np.concatenate([col, np.ones((n, n, 1), np.float32)], -1), TEX),
            T.to_image("leather_normal", T.normal_from_height(0.5 * nz + 0.5 * crack, 1.2), TEX, "Non-Color"))
PURPLE = [(0.30, 0.10, 0.36), (0.45, 0.16, 0.40), (0.22, 0.10, 0.28), (0.52, 0.22, 0.34), (0.34, 0.30, 0.42), (0.55, 0.50, 0.55)]
GREYS  = [(0.26, 0.24, 0.30), (0.42, 0.36, 0.34), (0.50, 0.46, 0.44), (0.20, 0.17, 0.24), (0.36, 0.20, 0.38), (0.30, 0.30, 0.36)]
pa, pan = patch_tex("patchA", PURPLE, 3, 11); pb, pbn = patch_tex("patchB", GREYS, 9, 9)
IRID = [(0.35, 0.55, 0.70), (0.75, 0.40, 0.70), (0.55, 0.30, 0.85), (0.30, 0.70, 0.65)]
pc, pcn = patch_tex("patchC", IRID, 15, 7)
si, sn, se = scale_tex(); li, ln_ = leather_tex()

# ---------- materials ----------
M_SKIN   = mat("CL_Skin", (0.74, 0.60, 0.55), 0.55)
M_CLOTH  = mat("CL_Under", (0.18, 0.15, 0.22), 0.85)
M_TROUS  = mat("CL_Trousers", (0.24, 0.22, 0.22), 0.9)
M_PA     = mat("CL_PatchA", (0.38, 0.14, 0.38), 0.85)
M_PB     = mat("CL_PatchB", (0.34, 0.30, 0.34), 0.85)
M_PC     = mat("CL_PatchIrid", (0.5, 0.45, 0.7), 0.3, 0.2)
M_LEATH  = mat("CL_Leather", (0.26, 0.16, 0.12), 0.55)
M_BRASS  = mat("CL_Brass", (0.80, 0.58, 0.22), 0.3, 1.0)
M_HAIRP  = mat("CL_HairPurple", (0.30, 0.10, 0.40), 0.5)
M_HAIRS  = mat("CL_HairSilver", (0.72, 0.70, 0.76), 0.45)
M_EYE    = mat("CL_Eye", (0.62, 0.42, 0.14), 0.15, emit=(0.5, 0.3, 0.08), strength=0.5)
M_LIPS   = mat("CL_Lips", (0.60, 0.36, 0.36), 0.5)
M_LASH   = mat("CL_Lash", (0.15, 0.10, 0.10), 0.6)
M_IRSKIN = mat("CL_IridSkin", (0.7, 0.62, 0.8), 0.25, 0.1)
M_CRYST  = mat("CL_Crystal", (0.75, 0.55, 0.95), 0.05, 0.0, alpha=0.78, emit=(0.8, 0.45, 1.0), strength=1.6)
M_BOOK   = mat("CL_Book", (0.20, 0.13, 0.12), 0.5)
T.bind(M_PA, pa, pan); T.bind(M_PB, pb, pbn); T.bind(M_PC, pc, pcn); T.bind(M_LEATH, li, ln_); T.bind(M_BOOK, li, ln_)
T.bind(M_IRSKIN, si, sn, se, 0.7)
for _o in bpy.data.objects:
    if _o.type == "MESH" and _o.name.endswith(("_Body", "_Legs")):
        _o.data.materials.clear()
        if _o.name.endswith("_Body"): _o.data.materials.append(M_SKIN); _o.data.materials.append(M_CLOTH)
        else: _o.data.materials.append(M_TROUS)

CY = -0.043
# ---------- head ----------
bm = bmesh.new()
ell(bm, (0, -0.04, 1.655), (0.078, 0.102, 0.097), seg=18, rings=12)
ell(bm, (0, -0.085, 1.600), (0.059, 0.072, 0.068), seg=14, rings=9)
ell(bm, (0, -0.099, 1.548), (0.029, 0.038, 0.032), seg=12, rings=7)
for sx in (1, -1):
    ell(bm, (sx * 0.040, -0.062, 1.568), (0.020, 0.046, 0.036), seg=10, rings=6)
    ell(bm, (sx * 0.046, -0.108, 1.597), (0.015, 0.013, 0.011), seg=8, rings=5)
    ell(bm, (sx * 0.034, -0.134, 1.668), (0.036, 0.012, 0.008), rot=(0, sx * math.radians(12), 0), seg=8, rings=5)
    cone(bm, (sx * 0.074, -0.035, 1.640), (sx * 1.0, -0.2, 0.75), 0.017, 0.078, seg=6)                 # long pointed ears
tube(bm, (0, -0.138, 1.652), (0, -0.165, 1.612), 0.010, 0.013, seg=6)
ell(bm, (0, -0.167, 1.608), (0.013, 0.014, 0.011), seg=8, rings=5)
ell(bm, (0, -0.040, 1.50), (0.040, 0.040, 0.055), seg=10, rings=6)
attach(arm, "Hero_Face", bm, M_SKIN, "Head")
bm = bmesh.new()
ell(bm, (0, -0.148, 1.5725), (0.021, 0.010, 0.0065), seg=8, rings=4)
ell(bm, (0, -0.145, 1.5615), (0.019, 0.010, 0.0075), seg=8, rings=4)
attach(arm, "Hero_Lips", bm, M_LIPS, "Head")
bm = bmesh.new()
for sx in (1, -1):
    ell(bm, (sx * 0.035, -0.139, 1.653), (0.021, 0.0055, 0.0045), rot=(0, sx * math.radians(12), 0), seg=8, rings=4)
    ell(bm, (sx * 0.037, -0.145, 1.676), (0.026, 0.006, 0.0045), rot=(0, sx * math.radians(16), 0), seg=8, rings=4)
attach(arm, "Hero_Liner", bm, M_LASH, "Head")
bm = bmesh.new()
for sx in (1, -1):
    ell(bm, (sx * 0.035, -0.139, 1.640), (0.0155, 0.0085, 0.0095), seg=10, rings=6)
attach(arm, "Hero_Eyes", bm, M_EYE, "Head")
bm = bmesh.new()                                                                           # iridescent scale patches
for (x, y, z, s) in ((0.056, -0.112, 1.607, 0.020), (0.062, -0.095, 1.585, 0.016), (-0.050, -0.130, 1.665, 0.014), (0.045, -0.060, 1.698, 0.018),
                     (0.083, -0.07, 1.63, 0.014), (0.0, -0.157, 1.642, 0.008)):
    ell(bm, (x, y, z), (s * 0.7, s * 0.3, s * 0.8), seg=7, rings=4)
for (x, z) in ((0.025, 1.49), (-0.03, 1.47)):
    ell(bm, (x, -0.083, z), (0.020, 0.012, 0.024), seg=7, rings=4)
attach(arm, "Hero_ScalePatches", bm, M_IRSKIN, "Head")
bm = bmesh.new()
for sx in (1, -1):
    ell(bm, (sx * 0.088, -0.045, 1.607), (0.007, 0.007, 0.012), seg=4, rings=2)
    ell(bm, (sx * 0.088, -0.045, 1.585), (0.006, 0.006, 0.014), seg=4, rings=2)
attach(arm, "Hero_Earrings", bm, M_CRYST, "Head")

# ---------- hair: curly purple/silver mass, side braid + long gold-ringed ponytail braid ----------
bm = bmesh.new(); bs = bmesh.new()
ell(bm, (0, -0.025, 1.670), (0.092, 0.112, 0.100), seg=14, rings=9)
for k in range(60):
    ph = math.radians(random.uniform(-175, 175)); el = math.radians(random.uniform(5, 80))
    root = Vector((0.088 * math.sin(ph) * math.cos(el), -0.03 - 0.105 * math.cos(ph) * math.cos(el), 1.66 + 0.10 * math.sin(el)))
    out = Vector((math.sin(ph), -math.cos(ph), 0.5)).normalized()
    tgt = bs if k % 3 == 0 else bm
    p = root; up = Vector((0, 0, -1))
    for i in range(5):
        ang = i * 1.3 + k
        q = p + out * 0.03 * (1.2 - i * 0.15) + Vector((math.cos(ang), 0, math.sin(ang))) * 0.022 + Vector((0, 0, -0.03))
        tube(tgt, p, q, 0.012 - 0.0015 * i, 0.012 - 0.0015 * (i + 1), seg=4); p = q
for sx in (1, -1):                                                                          # loose face-framing curls
    for j in range(5):
        p = Vector((sx * 0.084, -0.085 - 0.006 * j, 1.62 + 0.012 * j))
        for i in range(5):
            q = p + Vector((sx * 0.012 * math.cos(i * 1.4 + j), -0.008, -0.045)) + Vector((0, 0.01 * math.sin(i * 1.4), 0))
            tube(bs if j % 2 else bm, p, q, 0.011 - 0.0015 * i, 0.011 - 0.0015 * (i + 1), seg=4); p = q
attach(arm, "Hero_HairPurple", bm, M_HAIRP, "Head"); attach(arm, "Hero_HairSilver", bs, M_HAIRS, "Head")
bm = bmesh.new(); bg = bmesh.new()
for i in range(13):                                                                         # long braid
    t = i / 12
    c = Vector((0.0, 0.10 + 0.04 * math.sin(t * 2.5), 1.69 - 0.46 * t))
    ell(bm, c + Vector((0.012 * (-1) ** i, 0, 0)), (0.026 - 0.008 * t, 0.024 - 0.006 * t, 0.025), seg=7, rings=4)
    if i % 4 == 1:
        bmesh.ops.create_cone(bg, cap_ends=False, segments=10, radius1=0.032 - 0.008 * t, radius2=0.032 - 0.008 * t, depth=0.014, matrix=Matrix.Translation(c))
attach(arm, "Hero_Braid", bm, M_HAIRP, "Head"); attach(arm, "Hero_BraidRings", bg, M_BRASS, "Head")
bm = bmesh.new()
for sx in (-1,):                                                                            # small front braid
    p = Vector((sx * 0.075, -0.10, 1.64))
    for i in range(7):
        q = p + Vector((sx * 0.004 * (-1) ** i, -0.006, -0.032)); ell(bm, q, (0.011, 0.011, 0.014), seg=6, rings=4); p = q
attach(arm, "Hero_SideBraid", bm, M_HAIRS, "Head")

# ---------- weights ----------
def skirt_w(co):
    t = smoothstep(1.0, 0.45, co.z)
    front = abs(co.y + CY) / max(1e-6, math.hypot(co.x, co.y + CY))
    wl = t * (0.2 + 0.55 * front)
    return {"Hips": 1.0 - wl, ("UpperLeg.L" if co.x >= 0 else "UpperLeg.R"): wl}

# ---------- baggy trousers ----------
for side, up, lo, tag in ((1, "UpperLeg.L", "LowerLeg.L", "L"), (-1, "UpperLeg.R", "LowerLeg.R", "R")):
    cx = side * 0.121
    def yl(z): return float(np.interp(z, [0.023, 0.533, 0.964], [-0.062, -0.087, -0.045]))
    def trs(r, c, cx=cx, yl=yl):
        a = 2 * math.pi * c; z = 1.04 - r * 0.66
        rad = float(np.interp(z, [0.38, 0.5, 0.7, 0.9, 1.04], [0.078, 0.108, 0.105, 0.082, 0.072]))
        return Vector((cx + rad * math.sin(a), yl(z) - rad * math.cos(a), z))
    skinned(arm, "Hero_Trousers_" + tag, strip(10, 16, trs), M_TROUS, lambda co, up=up, lo=lo: {up: smoothstep(0.40, 0.58, co.z), lo: 1 - smoothstep(0.40, 0.58, co.z)})

# ---------- boots: tall, laced, buckled ----------
for side, lower, foot in ((1, "LowerLeg.L", "Foot.L"), (-1, "LowerLeg.R", "Foot.R")):
    cx = side * 0.121
    def shaft(r, c, cx=cx):
        a = 2 * math.pi * c; z = 0.46 - r * 0.43
        rad = 0.062 - 0.008 * min(1.0, r * 1.6) + (0.012 if r < 0.05 else 0.0)
        return Vector((cx + rad * math.cos(a), -0.087 + 0.025 * r + rad * math.sin(a) * 1.05, z))
    def wshaft(co, lower=lower, foot=foot):
        t = smoothstep(0.30, 0.10, co.z); return {lower: 1.0 - t, foot: t}
    skinned(arm, "Hero_BootShaft_" + ("L" if side > 0 else "R"), strip(12, 18, shaft), M_LEATH, wshaft)
    bm = bmesh.new()
    ell(bm, (cx, -0.135, 0.050), (0.052, 0.105, 0.042), seg=12, rings=7)
    ell(bm, (cx, -0.046, 0.052), (0.047, 0.050, 0.050), seg=10, rings=6)
    ell(bm, (cx, -0.105, 0.016), (0.056, 0.138, 0.014), seg=12, rings=5)
    attach(arm, "Hero_BootFoot_" + ("L" if side > 0 else "R"), bm, M_LEATH, foot)
    bm = bmesh.new()
    for k in range(5):
        ell(bm, (cx - side * 0.01, -0.150, 0.40 - k * 0.05), (0.026, 0.008, 0.007), rot=(0, math.radians(22 * (1 if k % 2 else -1)), 0), seg=6, rings=3)
    for z in (0.16, 0.30):                                                                  # buckle straps
        ell(bm, (cx + side * 0.052, -0.08, z), (0.014, 0.034, 0.016), seg=6, rings=4)
    ell(bm, (cx, -0.185, 0.050), (0.024, 0.014, 0.020), seg=6, rings=4)
    attach(arm, "Hero_BootTrim_" + ("L" if side > 0 else "R"), bm, M_BRASS, foot)

# ---------- patchwork coat: asymmetric layered handkerchief skirts ----------
TIERS = [  # top, hem, material, extra radius, phase, points
    (1.08, 0.78, M_PA, 0.00, 0.0, 5),
    (1.02, 0.60, M_PB, 0.018, 1.7, 4),
    (0.96, 0.52, M_PC, 0.034, 3.1, 5),
    (0.90, 0.46, M_PA, 0.050, 0.9, 6),
    (0.84, 0.40, M_PB, 0.066, 2.4, 5),
]
def skirt_pt(r, c, top, hem, ex, ph, pts):
    a = 2 * math.pi * c
    tri = abs(((a * pts / (2 * math.pi) + ph) % 1.0) * 2 - 1)               # triangle wave 0..1: sharp handkerchief points
    drop = (1 - tri) ** 1.0 * 0.20 + 0.10 * math.sin(a + ph)
    z = top + r * (hem - drop * r - top)
    rad = 0.19 + ex + 0.07 * (r ** 1.2) + 0.012 * math.sin(a * 5 + ph) * r
    return Vector((rad * math.sin(a), CY - rad * math.cos(a) * 0.95, z))
for i, (top, hem, m, ex, ph, pts) in enumerate(TIERS):
    skinned(arm, f"Hero_Skirt{i}", strip(5, 64, lambda r, c, top=top, hem=hem, ex=ex, ph=ph, pts=pts: skirt_pt(r, c, top, hem, ex, ph, pts)), m, skirt_w)
def bodice(r, c):
    a = 2 * math.pi * c; z = 1.47 - r * 0.42
    w = 0.158 + 0.012 * r
    return Vector((w * 1.04 * math.sin(a), CY - w * 0.92 * math.cos(a), z))
skinned(arm, "Hero_Bodice", strip(8, 28, bodice), M_PA, lambda co: ({"Chest": 1.0} if co.z > 1.38 else {"Torso": smoothstep(1.2, 1.38, co.z), "Abdomen": 1 - smoothstep(1.2, 1.38, co.z)} if co.z > 1.2 else {"Abdomen": smoothstep(1.05, 1.2, co.z), "Hips": 1 - smoothstep(1.05, 1.2, co.z)}))
def wrapband(r, c):                                                                         # diagonal asymmetrical wrap panel across the chest
    t = r; x0, z0, x1, z1 = -0.13, 1.50, 0.15, 1.12
    x = x0 + (x1 - x0) * t; z = z0 + (z1 - z0) * t
    ry = 0.162 * math.sqrt(max(0.1, 1 - (x / 0.22) ** 2)) + 0.014
    w = (c - 0.5) * 0.15
    return Vector((x + w * 0.9, CY - ry, z + w * 0.4))
skinned(arm, "Hero_Wrap", strip(14, 4, wrapband), M_PB, lambda co: {"Chest": 1.0} if co.z > 1.3 else {"Torso": 1.0})
def collar(r, c):
    a = 2 * math.pi * c; rad = 0.092 + 0.04 * r + 0.004 * math.sin(c * 30)
    back = max(0.0, math.cos(a - math.pi)) * 0.03
    return Vector((rad * math.sin(a), CY - rad * math.cos(a), 1.47 + r * (0.09 + back)))
attach(arm, "Hero_Collar", strip(5, 28, collar), M_PA, "Chest")
def mant(r, c):                                                                              # patchwork shoulder pieces
    a = 2 * math.pi * c
    rx, ry = 0.12 + 0.17 * r, 0.10 + 0.07 * r
    z = 1.53 - r * (0.10 + 0.05 * abs(math.sin(a * 2.5)))
    return Vector((rx * math.sin(a), CY - ry * math.cos(a), z))
skinned(arm, "Hero_Mantle", strip(4, 40, mant), M_PB, lambda co: {"Chest": 1 - smoothstep(0.10, 0.28, abs(co.x)) * 0.85, ("Shoulder.L" if co.x >= 0 else "Shoulder.R"): smoothstep(0.10, 0.28, abs(co.x)) * 0.85})

# ---------- fitted patchwork sleeves + leather bracers ----------
for side, ua, la, tag in ((1, "UpperArm.L", "LowerArm.L", "L"), (-1, "UpperArm.R", "LowerArm.R", "R")):
    for mi, (x0, x1, m, rr) in enumerate(((0.14, 0.36, M_PC, 0.060), (0.34, 0.60, M_PA, 0.052))):
        def sl(r, c, side=side, x0=x0, x1=x1, rr=rr, mi=mi):
            a = 2 * math.pi * c; x = x0 + r * (x1 - x0)
            rad = rr - 0.010 * r + 0.003 * math.sin(a * 3 + mi)
            return Vector((side * x, -0.056 - 0.03 * min(1.0, max(0.0, (x - 0.33) / 0.24)) + rad * math.sin(a), 1.432 + rad * math.cos(a)))
        skinned(arm, f"Hero_Sleeve{mi}_{tag}", strip(7, 12, sl), m, lambda co, ua=ua, la=la: {ua: 1 - smoothstep(0.30, 0.40, abs(co.x)), la: smoothstep(0.30, 0.40, abs(co.x))})
    bm = bmesh.new()
    for k in range(3):
        bmesh.ops.create_cone(bm, cap_ends=False, segments=12, radius1=0.050, radius2=0.050, depth=0.026,
                              matrix=Matrix.Translation((side * (0.47 + k * 0.034), -0.075, 1.432)) @ Matrix.Rotation(math.radians(90), 4, 'Y'))
    attach(arm, "Hero_Bracer_" + tag, bm, M_LEATH, la)
    bm = bmesh.new()
    for k in range(3):
        ell(bm, (side * (0.47 + k * 0.034), -0.075, 1.432 + 0.052), (0.007, 0.01, 0.007), seg=5, rings=3)
    attach(arm, "Hero_BracerStuds_" + tag, bm, M_BRASS, la)

# ---------- belts, book, pouch ----------
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=False, segments=24, radius1=0.188, radius2=0.188, depth=0.045, matrix=Matrix.Translation((0, -0.045, 1.07)))
bmesh.ops.create_cone(bm, cap_ends=False, segments=24, radius1=0.195, radius2=0.195, depth=0.035, matrix=Matrix.Translation((0, -0.045, 1.015)) @ Matrix.Rotation(math.radians(8), 4, 'X'))
attach(arm, "Hero_Belts", bm, M_LEATH, "Hips")
bm = bmesh.new()
ell(bm, (0, -0.232, 1.07), (0.030, 0.010, 0.030), seg=8, rings=5); ell(bm, (0.08, -0.215, 1.015), (0.022, 0.010, 0.022), seg=8, rings=5)
for sx in (-1, 1): ell(bm, (sx * 0.10, -0.208, 1.07), (0.012, 0.008, 0.016), seg=6, rings=4)
attach(arm, "Hero_BeltBuckles", bm, M_BRASS, "Hips")
BX, BY, BZ = 0.275, -0.07, 0.92
bm = bmesh.new()
ell(bm, (BX, BY, BZ), (0.040, 0.075, 0.095), seg=10, rings=6)
attach(arm, "Hero_Spellbook", bm, M_BOOK, "Hips")
bm = bmesh.new()
for z in (-0.06, 0.06):
    ell(bm, (BX + 0.003, BY, BZ + z * 1.2), (0.043, 0.078, 0.008), seg=8, rings=3)
ell(bm, (BX + 0.04, BY, BZ), (0.004, 0.032, 0.032), rot=(0, 0, 0), seg=8, rings=4)
for k in range(4):
    a = k * math.pi / 4
    tube(bm, (BX + 0.043, BY - 0.030 * math.cos(a), BZ - 0.030 * math.sin(a)), (BX + 0.043, BY + 0.030 * math.cos(a), BZ + 0.030 * math.sin(a)), 0.003, 0.003, seg=4)
attach(arm, "Hero_BookGold", bm, M_BRASS, "Hips")
bm = bmesh.new()
ell(bm, (-0.27, 0.0, 0.93), (0.045, 0.07, 0.06), seg=10, rings=6)
attach(arm, "Hero_Pouch", bm, M_LEATH, "Hips")
bm = bmesh.new(); ring = bmesh.new()
bmesh.ops.create_cone(ring, cap_ends=False, segments=10, radius1=0.012, radius2=0.012, depth=0.006, matrix=Matrix.Translation((-0.318, 0.0, 0.94)) @ Matrix.Rotation(math.radians(90), 4, 'Y'))
attach(arm, "Hero_PouchRing", ring, M_BRASS, "Hips")

# ---------- halo of floating entropy crystals ----------
bm = bmesh.new(); bw = bmesh.new()
for k in range(9):
    a = math.radians(-115 + k * 28.75)
    cx_, cy_, cz_ = 0.30 * math.sin(a), -0.04 - 0.30 * math.cos(a) * 0.9, 1.66 + 0.05 * math.sin(k * 1.7) + 0.035 * (1 - abs(k - 4) / 4)
    s = 0.032 + 0.008 * (k % 3)
    rot = (math.radians(random.uniform(-25, 25)), math.radians(random.uniform(-25, 25)), -a)
    ell(bm, (cx_, cy_, cz_), (s * 0.55, s * 0.30, s * 2.4), rot=rot, seg=4, rings=2)
    ell(bw, (cx_, cy_, cz_), (s * 0.40, s * 0.40, s * 2.7), rot=rot, seg=4, rings=2)
attach(arm, "Hero_Crystals", bm, M_CRYST, "Head"); attach(arm, "Hero_CrystalCores", bw, M_BRASS, "Head")

print("CL_TOTAL_TRIS", tri_count())
bpy.ops.wm.save_as_mainfile(filepath=OUT + "/chaosling.blend")
bpy.ops.export_scene.gltf(filepath=OUT + "/chaosling.glb", export_format='GLB', export_apply=True,
                          export_animations=False, export_skins=True)
print("CL_DONE")
