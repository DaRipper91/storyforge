"""Embervein hero: massive basalt-and-magma elemental in a leather harness on the cosmic shared-skeleton base (Blender 5.x).
Run: blender -b -P build_embervein.py -- <cosmic.glb> <out_dir>
Hundreds of jittered faceted basalt/obsidian boulders stacked around every limb (rigid, bone-parented), glowing magma seams in the
gaps, a hunched crested rock head with amber eyes, oversized fists and feet, studded leather harness + belt with pouches and a vial,
a tattered banner loincloth with leather flaps. Baked textures (basalt + crack emission, banner cloth, leather)."""
import bpy, bmesh, math, sys, os, random
import numpy as np
from mathutils import Vector, Matrix, Euler
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hero_common import *
import hero_textures as T

SRC, OUT = sys.argv[-2], sys.argv[-1]
random.seed(33)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
remove_objects("_Head", "_Feet")
TEX = os.path.join(OUT, "tex_ev")


# ---------- textures ----------
def basalt_tex():
    n = 512; x, y = T._grid(n)
    nz = T.fbm(n, 3, 5, 6); nz2 = T.fbm(n, 11, 4, 14)
    strata = 0.5 + 0.5 * np.sin((y * 9 + nz * 4) * np.pi)
    e, cid = T.voronoi(n, 7, 5)
    edge = 1 - T.smooth(0.0, 0.10, e)
    crack = edge * T.smooth(0.55, 0.8, nz2)                                    # only some cell borders glow
    dark = np.array([0.22, 0.20, 0.20], np.float32); warm = np.array([0.42, 0.31, 0.24], np.float32)
    k = (0.35 * nz + 0.35 * strata * nz2 + 0.3 * cid)[..., None]
    col = dark[None, None, :] * (1 - k) + warm[None, None, :] * k
    col = col * (1 - 0.6 * edge[..., None]) * (0.85 + 0.3 * nz2[..., None])
    col = col * (1 - crack[..., None]) + np.array([0.9, 0.4, 0.06], np.float32)[None, None, :] * crack[..., None]
    emis = np.stack([crack * 1.0, crack * 0.42, crack * 0.05, np.ones((n, n), np.float32)], -1)
    h = 0.5 * nz + 0.25 * nz2 + 0.2 * strata - 0.7 * edge
    return (T.to_image("basalt_diffuse", np.concatenate([col, np.ones((n, n, 1), np.float32)], -1), TEX),
            T.to_image("basalt_normal", T.normal_from_height(h, 1.6), TEX, "Non-Color"),
            T.to_image("basalt_emission", emis, TEX))


def banner_tex():
    n = 512; x, y = T._grid(n)
    nz = T.fbm(n, 6, 5, 8); weave = 0.5 + 0.5 * np.sin(x * n * 0.4) * np.sin(y * n * 0.4)
    red = np.array([0.42, 0.17, 0.13], np.float32)
    col = red[None, None, :] * (0.65 + 0.6 * nz[..., None]) * (0.92 + 0.08 * weave[..., None])
    u = np.abs(x - 0.5) * 2; v = y
    d = lambda cx, cy, rx, ry: ((np.abs(x - cx) / rx) + (np.abs(y - cy) / ry))
    sig = (np.abs(d(0.5, 0.52, 0.22, 0.14) - 1) < 0.10) | (np.abs(d(0.5, 0.44, 0.1, 0.08) - 1) < 0.2) | ((np.abs(x - 0.5) < 0.02) & (y > 0.40) & (y < 0.78))
    sig |= ((np.abs(np.abs(x - 0.5) - (y - 0.62) * 0.7) < 0.022) & (y > 0.62) & (y < 0.8))
    tan = np.array([0.72, 0.55, 0.36], np.float32)
    col = np.where(sig[..., None], tan[None, None, :] * (0.7 + 0.3 * nz[..., None]), col)
    edge = ((x < 0.05) | (x > 0.95) | (y < 0.03))
    col = np.where(edge[..., None], np.array([0.5, 0.38, 0.26], np.float32)[None, None, :] * (0.6 + 0.4 * nz[..., None]), col)
    fray = T.smooth(0.88, 1.0, y) * nz
    col *= (1 - 0.45 * fray[..., None])
    return (T.to_image("banner_diffuse", np.concatenate([col, np.ones((n, n, 1), np.float32)], -1), TEX),
            T.to_image("banner_normal", T.normal_from_height(0.3 * weave + 0.5 * sig + 0.3 * nz, 1.0), TEX, "Non-Color"))


def leather_tex():
    n = 512; x, y = T._grid(n)
    nz = T.fbm(n, 8, 5, 10); crack = T.smooth(0.55, 0.9, 1 - np.abs(2 * T.fbm(n, 4, 4, 18) - 1))
    base = np.array([0.30, 0.19, 0.11], np.float32)
    col = base[None, None, :] * (0.65 + 0.7 * nz[..., None]) * (1 - 0.35 * crack[..., None])
    edge = T.smooth(0.02, 0.0, np.abs(y - 0.5) - 0.44) * 0
    return (T.to_image("leather_diffuse", np.concatenate([col, np.ones((n, n, 1), np.float32)], -1), TEX),
            T.to_image("leather_normal", T.normal_from_height(0.5 * nz + 0.6 * crack, 1.3), TEX, "Non-Color"))


bi, bn, be = basalt_tex(); ni, nn = banner_tex(); li, ln = leather_tex()

# ---------- materials ----------
M_BASALT = mat("EV_Basalt", (0.17, 0.15, 0.145), 0.78, 0.05, emit=(1, 0.4, 0.05), strength=2.2)
M_OBS = mat("EV_Obsidian", (0.025, 0.022, 0.03), 0.18, 0.35)
M_MAGMA = mat("EV_Magma", (0.9, 0.3, 0.04), 0.4, 0.0, emit=(1.0, 0.25, 0.02), strength=1.8)
M_CORE = mat("EV_Core", (0.07, 0.04, 0.035), 0.6, 0.0, emit=(0.9, 0.25, 0.03), strength=0.25)
M_EYE = mat("EV_Eye", (1.0, 0.6, 0.1), 0.2, 0.0, emit=(1.0, 0.6, 0.12), strength=6.0)
M_LEATH = mat("EV_Leather", (0.30, 0.19, 0.11), 0.8)
M_BANNER = mat("EV_Banner", (0.42, 0.17, 0.13), 0.95)
M_STEEL = mat("EV_Steel", (0.5, 0.5, 0.52), 0.35, 0.9)
T.bind(M_BASALT, bi, bn, be, 2.2); T.bind(M_BANNER, ni, nn); T.bind(M_LEATH, li, ln)
recolor_base({"SciFi_Light": (0.5, 0.17, 0.04), "SciFi_Light_Accent": (0.5, 0.17, 0.04), "SciFi_Main": (0.5, 0.17, 0.04),
              "SciFi_MainDark": (0.3, 0.1, 0.03), "Grey": (0.5, 0.17, 0.04)})
for _o in bpy.data.objects:
    if _o.type == "MESH" and _o.name.endswith(("_Body", "_Legs")):
        _o.data.materials.clear(); _o.data.materials.append(M_CORE)
        for _p in _o.data.polygons: _p.material_index = 0

# ---------- rock factory (one bmesh per (bone, material); attached rigidly at the end) ----------
BM = {}
RNG = random.Random(7)


def bmf(bone, matkey="B"):
    k = (bone, matkey)
    if k not in BM:
        BM[k] = bmesh.new(); BM[k].loops.layers.uv.new("UVMap")
    return BM[k]


def basis_from(axis):
    a = Vector(axis).normalized()
    up = Vector((0, 0, 1)) if abs(a.z) < 0.9 else Vector((1, 0, 0))
    p1 = a.cross(up).normalized(); p2 = a.cross(p1).normalized()
    return Matrix((a, p1, p2)).transposed()            # columns = axis, perp1, perp2


def rock(bone, c, size, axis=(0, 0, 1), sub=1, jit=0.22, rot=0.45, mk="B"):
    bm = bmf(bone, mk)
    g = bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0, calc_uvs=True)['verts']
    B = basis_from(axis)
    R = Euler((RNG.uniform(-rot, rot), RNG.uniform(-rot, rot), RNG.uniform(-rot, rot))).to_matrix()
    flat = RNG.uniform(0.75, 1.0)
    for v in g:
        p = v.co * (1 + RNG.uniform(-jit, jit))
        p = Vector((p.x * size[0], p.y * size[1] * flat, p.z * size[2]))
        v.co = B @ (R @ p) + Vector(c)
    return g


def spike(bone, base, direction, r, length, seg=4, mk="O"):
    cone(bmf(bone, mk), base, direction, r, length, seg=seg)


def limb(bone, p0, p1, r0, r1, rows, per, size, sub=1, jit=0.22, seed=0, mk="B", twist=0.0, bulge=0.0):
    p0 = Vector(p0); p1 = Vector(p1); ax = (p1 - p0).normalized(); B = basis_from(ax)
    for i in range(rows):
        t = (i + 0.5) / rows
        c0 = p0.lerp(p1, t)
        r = r0 + (r1 - r0) * t + bulge * math.sin(math.pi * t)
        for k in range(per):
            a = 2 * math.pi * (k + (0.5 if i % 2 else 0.0)) / per + twist
            off = B @ Vector((0, math.cos(a), math.sin(a))) * r
            sz = (size[0] * 1.3 * RNG.uniform(0.9, 1.15), size[1] * 1.3 * RNG.uniform(0.85, 1.15), size[2] * 1.3 * RNG.uniform(0.85, 1.15))
            rock(bone, c0 + off, (sz[0], sz[2], sz[1]), axis=ax, sub=sub, jit=jit, mk=mk)


def seam(bone, pts, r=0.006, jag=0.008):
    bm = bmf(bone, "M")
    prev = None
    for p in pts:
        q = Vector(p) + Vector((RNG.uniform(-jag, jag), RNG.uniform(-jag, jag), RNG.uniform(-jag, jag)))
        if prev is not None: tube(bm, prev, q, r, r * 0.8, seg=3)
        prev = q


# ---------- torso (stacked plate rows around a broad, hunched chest) ----------
def torso_rows():
    rows = [(1.50, 0.215, 0.165, 14, "Chest", (0.075, 0.05, 0.05)), (1.41, 0.255, 0.185, 15, "Chest", (0.085, 0.055, 0.055)),
            (1.32, 0.255, 0.185, 15, "Torso", (0.085, 0.055, 0.055)), (1.23, 0.235, 0.175, 14, "Torso", (0.08, 0.055, 0.055)),
            (1.14, 0.215, 0.165, 13, "Abdomen", (0.078, 0.05, 0.05)), (1.05, 0.215, 0.17, 13, "Abdomen", (0.08, 0.05, 0.05))]
    for ri, (z, rx, ry, n, bone, sz) in enumerate(rows):
        for k in range(n):
            a = 2 * math.pi * (k + 0.5 * (ri % 2)) / n
            c = Vector((rx * math.sin(a), -0.043 - ry * math.cos(a), z))
            tang = Vector((math.cos(a), math.sin(a) * ry / rx * 1.0, 0)).normalized()
            front = max(0.0, -math.cos(a))
            big = 1.0 + 0.25 * front
            rock(bone, c, (sz[0] * big * 1.2, sz[1] * (1 + 0.3 * front) * 1.25, sz[2] * RNG.uniform(1.0, 1.3)), axis=tang, sub=1)
    # pectorals + sternum + back slabs (large, detailed rocks)
    for sx in (1, -1):
        rock("Chest", (sx * 0.105, -0.205, 1.425), (0.105, 0.075, 0.085), axis=(1, 0, 0), sub=2, jit=0.2)
        rock("Chest", (sx * 0.12, -0.17, 1.33), (0.10, 0.07, 0.075), axis=(1, 0, 0), sub=2, jit=0.2)
        rock("Torso", (sx * 0.08, -0.19, 1.2), (0.07, 0.06, 0.07), axis=(1, 0, 0), sub=2, jit=0.2)
        rock("Chest", (sx * 0.12, 0.085, 1.42), (0.12, 0.07, 0.10), axis=(1, 0, 0), sub=2, jit=0.2)       # back slabs
        rock("Torso", (sx * 0.1, 0.075, 1.26), (0.11, 0.07, 0.09), axis=(1, 0, 0), sub=2, jit=0.2)
    rock("Chest", (0, -0.215, 1.38), (0.04, 0.05, 0.12), axis=(0, 0, 1), sub=2, jit=0.18, mk="O")      # sternum plate
    rock("Chest", (0, 0.10, 1.34), (0.05, 0.05, 0.22), axis=(0, 0, 1), sub=2, jit=0.18, mk="O")       # spine ridge
    for i in range(5):
        spike("Chest", (0, 0.13, 1.55 - i * 0.07), (0, 0.9, 0.35 - 0.1 * i), 0.026 - 0.002 * i, 0.07 - 0.005 * i, seg=4)


torso_rows()

# ---------- neck + head ----------
for k in range(8):
    a = 2 * math.pi * k / 8
    rock("Neck", (0.075 * math.sin(a), -0.043 - 0.075 * math.cos(a) - 0.02, 1.55), (0.04, 0.035, 0.04), sub=1)
H = "Head"
rock(H, (0, -0.07, 1.67), (0.13, 0.135, 0.115), sub=2, jit=0.14)                           # skull
rock(H, (0, -0.165, 1.703), (0.105, 0.038, 0.026), axis=(1, 0, 0), sub=2, jit=0.1, rot=0.12)     # heavy brow ridge
for sx in (1, -1):
    rock(H, (sx * 0.085, -0.135, 1.640), (0.05, 0.05, 0.042), sub=2, jit=0.14)              # cheek blocks
    rock(H, (sx * 0.055, -0.185, 1.592), (0.036, 0.04, 0.03), sub=1, jit=0.12)             # tusk-like jaw knuckles
    rock(H, (sx * 0.13, -0.04, 1.69), (0.05, 0.06, 0.07), sub=1, jit=0.2)                  # temple crest
rock(H, (0, -0.15, 1.585), (0.085, 0.06, 0.04), axis=(1, 0, 0), sub=2, jit=0.14)             # jaw
rock(H, (0, -0.172, 1.640), (0.03, 0.04, 0.05), sub=1, jit=0.1)                              # blunt nose block
for i, (x, z, l) in enumerate(((0, 1.78, 0.10), (-0.045, 1.77, 0.08), (0.045, 1.77, 0.08), (-0.085, 1.74, 0.06), (0.085, 1.74, 0.06), (0, 1.74, 0.09))):
    spike(H, (x, -0.06 - 0.03 * (i == 5) * 0, z - 0.03), (x * 3, -0.2 if i == 5 else 0.3, 1.0), 0.026, l, seg=4, mk="O" if i % 2 else "B")
for sx in (1, -1):
    spike(H, (sx * 0.12, -0.07, 1.62), (sx * 1.0, 0.4, 0.3), 0.02, 0.08, seg=4)
    spike(H, (sx * 0.07, -0.20, 1.565), (sx * 0.15, -0.5, -0.9), 0.014, 0.05, seg=4)
bm = bmesh.new()
for sx in (1, -1):
    ell(bm, (sx * 0.048, -0.178, 1.668), (0.028, 0.012, 0.011), rot=(0, sx * math.radians(-18), 0), seg=8, rings=4)
attach(arm, "Hero_Eyes", bm, M_EYE, H)
bm = bmesh.new()
ell(bm, (0, -0.186, 1.575), (0.045, 0.01, 0.008), seg=8, rings=4)                            # glowing mouth slit
ell(bm, (0, -0.095, 1.738), (0.012, 0.03, 0.006), seg=6, rings=3)
attach(arm, "Hero_Mouth", bm, M_EYE, H)

# ---------- shoulders / arms / hands ----------
for sx, tag in ((1, "L"), (-1, "R")):
    UA, LA, HD = "UpperArm." + tag, "LowerArm." + tag, "Hand." + tag
    # pauldron: stacked boulders with obsidian spikes
    for (x, y, z, s) in ((0.235, -0.06, 1.505, (0.115, 0.105, 0.075)), (0.275, -0.05, 1.44, (0.105, 0.10, 0.085)), (0.215, -0.045, 1.57, (0.075, 0.08, 0.05)),
                         (0.165, -0.04, 1.545, (0.07, 0.07, 0.05)), (0.30, -0.06, 1.37, (0.08, 0.085, 0.08))):
        rock(UA, (sx * x, y, z), s, axis=(1, 0, 0), sub=2, jit=0.2)
    for i, (x, z, l) in enumerate(((0.20, 1.60, 0.12), (0.26, 1.57, 0.10), (0.31, 1.50, 0.09))):
        spike(UA, (sx * x, -0.05, z - 0.02), (sx * 0.35, -0.05, 1.0), 0.03, l, seg=4)
    limb(UA, (sx * 0.19, -0.057, 1.43), (sx * 0.34, -0.057, 1.43), 0.10, 0.092, 3, 6, (0.056, 0.05, 0.05), seed=1)
    limb(LA, (sx * 0.36, -0.06, 1.432), (sx * 0.57, -0.085, 1.432), 0.097, 0.108, 4, 6, (0.056, 0.056, 0.052), sub=1, seed=2, bulge=0.012)
    rock(LA, (sx * 0.345, -0.058, 1.432), (0.065, 0.12, 0.12), axis=(1, 0, 0), sub=2, jit=0.15)                  # elbow boulder
    rock(LA, (sx * 0.58, -0.085, 1.436), (0.045, 0.11, 0.11), axis=(1, 0, 0), sub=2, jit=0.15)                 # wrist guard
    spike(UA, (sx * 0.345, -0.058, 1.50), (sx * 0.2, 0.2, 1.0), 0.026, 0.09, seg=4)                            # elbow spike
    # fist-hands: palm + knuckles + fingers
    rock(HD, (sx * 0.665, -0.087, 1.435), (0.07, 0.105, 0.09), axis=(1, 0, 0), sub=2, jit=0.14)
    for fi, (yy, zz, ln) in enumerate(((-0.125, 1.442, 3), (-0.095, 1.447, 3), (-0.058, 1.447, 3), (-0.022, 1.443, 3))):
        for s_ in range(ln + 1):
            x = 0.725 + 0.044 * s_
            rock(HD, (sx * x, yy + 0.0, zz - 0.012 * s_), (0.036 - 0.003 * s_, 0.032, 0.032), axis=(1, 0, 0), sub=1, jit=0.18, rot=0.25)
    for s_ in range(2):
        rock(HD, (sx * (0.655 + 0.032 * s_), -0.15 - 0.03 * s_, 1.405), (0.042, 0.04, 0.038), axis=(1, -1, 0), sub=1, jit=0.18, rot=0.25)   # thumb
    rock(HD, (sx * 0.64, -0.087, 1.495), (0.04, 0.06, 0.03), axis=(1, 0, 0), sub=1, jit=0.18)                    # back-of-hand plate
    # seams
    seam(UA, [(sx * 0.17, -0.12, 1.52), (sx * 0.22, -0.13, 1.45), (sx * 0.30, -0.14, 1.40)])
    seam(UA, [(sx * 0.26, -0.01, 1.52), (sx * 0.30, 0.02, 1.46), (sx * 0.31, 0.0, 1.38)])
    seam(LA, [(sx * 0.40, -0.14, 1.45), (sx * 0.47, -0.17, 1.44), (sx * 0.54, -0.19, 1.45)])
    seam(LA, [(sx * 0.42, -0.02, 1.50), (sx * 0.50, -0.04, 1.51), (sx * 0.55, -0.05, 1.49)])

# ---------- legs / feet ----------
for sx, tag in ((1, "L"), (-1, "R")):
    UL, LL, FT = "UpperLeg." + tag, "LowerLeg." + tag, "Foot." + tag
    cx = sx * 0.135
    limb(UL, (cx, -0.05, 0.96), (cx, -0.085, 0.57), 0.07, 0.065, 5, 8, (0.05, 0.045, 0.048), seed=4)
    for z, y in ((0.80, 0.0), (0.66, 0.0)):
        rock(UL, (cx + sx * 0.06, -0.055 + y, z), (0.05, 0.06, 0.08), axis=(0, 0, 1), sub=2, jit=0.2)           # outer thigh slabs
    for zz_ in (0.88, 0.76, 0.64):
        rock(UL, (cx - sx * 0.01, 0.045, zz_), (0.07, 0.085, 0.085), axis=(0, 0, 1), sub=2, jit=0.18)
        rock(UL, (cx - sx * 0.05, -0.03, zz_), (0.06, 0.07, 0.075), axis=(0, 0, 1), sub=2, jit=0.18)
    rock(UL, (cx, 0.03, 0.80), (0.09, 0.06, 0.1), axis=(0, 0, 1), sub=2, jit=0.18)
    rock(UL, (cx, 0.02, 0.66), (0.085, 0.06, 0.08), axis=(0, 0, 1), sub=2, jit=0.18)
    rock(UL, (cx, -0.15, 0.58), (0.10, 0.07, 0.085), axis=(1, 0, 0), sub=2, jit=0.16)                                # knee cap
    spike(UL, (cx, -0.20, 0.585), (0, -1.0, 0.25), 0.03, 0.07, seg=4)
    limb(LL, (cx, -0.087, 0.50), (cx, -0.062, 0.09), 0.065, 0.06, 4, 7, (0.048, 0.044, 0.056), seed=5, bulge=0.014)
    rock(LL, (cx, -0.16, 0.36), (0.07, 0.05, 0.14), axis=(0, 0, 1), sub=2, jit=0.14)                                  # shin plate
    rock(LL, (cx, -0.095, 0.51), (0.115, 0.115, 0.05), axis=(1, 0, 0), sub=2, jit=0.14)
    # feet: boulder base, heel, toe blocks, ankle guard
    rock(FT, (cx, -0.15, 0.06), (0.135, 0.20, 0.062), axis=(0, -1, 0), sub=2, jit=0.12)
    rock(FT, (cx, -0.03, 0.062), (0.105, 0.09, 0.062), axis=(0, 1, 0), sub=2, jit=0.14)
    rock(FT, (cx, -0.055, 0.12), (0.115, 0.115, 0.06), axis=(1, 0, 0), sub=2, jit=0.14)
    for i, dx in enumerate((-0.07, -0.025, 0.025, 0.07)):
        rock(FT, (cx + sx * dx * 1.2, -0.31 - 0.008 * (i in (1, 2)), 0.048), (0.036, 0.075, 0.05), axis=(0, -1, 0), sub=1, jit=0.14, rot=0.2)
    rock(FT, (cx, -0.325, 0.045), (0.02, 0.02, 0.02), sub=1) if False else None
    seam(UL, [(cx - sx * 0.02, -0.17, 0.90), (cx - sx * 0.05, -0.18, 0.80), (cx, -0.19, 0.70)])
    seam(UL, [(cx + sx * 0.11, -0.05, 0.9), (cx + sx * 0.13, -0.05, 0.78), (cx + sx * 0.11, -0.06, 0.66)])
    seam(LL, [(cx + sx * 0.04, -0.19, 0.46), (cx, -0.2, 0.38), (cx - sx * 0.02, -0.17, 0.26)])
    seam(LL, [(cx - sx * 0.02, 0.03, 0.46), (cx + sx * 0.03, 0.03, 0.34), (cx, 0.02, 0.2)])
    seam(FT, [(cx, -0.2, 0.10), (cx + sx * 0.03, -0.24, 0.07), (cx, -0.28, 0.07)])

# chest + hip seams
seam("Chest", [(0, -0.225, 1.52), (0.04, -0.235, 1.46), (-0.03, -0.24, 1.38), (0.03, -0.24, 1.31)], r=0.007)
for sx in (1, -1):
    seam("Chest", [(sx * 0.05, -0.23, 1.50), (sx * 0.14, -0.215, 1.47), (sx * 0.22, -0.16, 1.45)], r=0.0065)
    seam("Torso", [(sx * 0.05, -0.23, 1.26), (sx * 0.12, -0.22, 1.2), (sx * 0.17, -0.19, 1.13)], r=0.006)
    seam("Chest", [(sx * 0.08, 0.14, 1.50), (sx * 0.12, 0.15, 1.40), (sx * 0.08, 0.15, 1.30)], r=0.006)

# ---------- hips: rock plates ----------
for k in range(12):
    a = 2 * math.pi * k / 12
    rock("Hips", (0.21 * math.sin(a), -0.05 - 0.17 * math.cos(a), 0.99), (0.075, 0.05, 0.06), axis=(math.cos(a), math.sin(a), 0), sub=1)

# ---------- flush BMs into objects ----------
MATS = {"B": M_BASALT, "O": M_OBS, "M": M_MAGMA}
for (bone, mk), b in BM.items():
    layer = b.loops.layers.uv.get("UVMap") or b.loops.layers.uv.new("UVMap")      # box-projected UVs: continuous texel density across boulders
    for f in b.faces:
        nrm = f.normal if f.normal.length > 0 else Vector((0, 0, 1))
        ax = max(range(3), key=lambda i: abs(nrm[i]))
        i1, i2 = [i for i in range(3) if i != ax]
        for lp in f.loops:
            co = lp.vert.co
            lp[layer].uv = ((co[i1] * 3.2) % 1.0 if False else co[i1] * 3.2, co[i2] * 3.2)

    attach(arm, f"Hero_Rock_{mk}_{bone.replace('.', '')}", b, MATS[mk], bone, smooth=False)

# ---------- harness, belt, pouches, vial, banner, flaps ----------
def chest_pt(x, z, off):
    rx = 0.26 + off if z < 1.46 else 0.22 + off
    ry = 0.20 + off if z < 1.46 else 0.17 + off
    q = max(0.0, 1 - (x / rx) ** 2)
    return Vector((x, -0.043 - ry * math.sqrt(q), z))


for sx in (1, -1):
    def strap_f(r, c, sx=sx):
        t = r; z = 1.62 - t * 0.50; x = sx * (0.145 - 0.07 * t + (c - 0.5) * 0.042)
        p = chest_pt(x, z, 0.035)
        return p
    attach(arm, "Hero_StrapF_" + ("L" if sx > 0 else "R"), strip(12, 3, strap_f), M_LEATH, "Chest")

    def strap_b(r, c, sx=sx):
        t = r; z = 1.62 - t * 0.5; x = sx * (0.145 - 0.07 * t + (c - 0.5) * 0.042)
        q = max(0.0, 1 - (x / 0.22) ** 2)
        return Vector((x, -0.043 + (0.17 + 0.04) * math.sqrt(q), z))
    attach(arm, "Hero_StrapB_" + ("L" if sx > 0 else "R"), strip(12, 3, strap_b), M_LEATH, "Chest")
    bm = bmesh.new()                                                  # steel rings and stitching studs on the straps
    pc = chest_pt(sx * 0.125, 1.53, 0.05)
    for i in range(14):
        a0 = 2 * math.pi * i / 14; a1 = 2 * math.pi * (i + 1) / 14
        tube(bm, pc + Vector((0.020 * math.cos(a0), -0.01, 0.020 * math.sin(a0))), pc + Vector((0.020 * math.cos(a1), -0.01, 0.020 * math.sin(a1))), 0.004, 0.004, seg=4)
    for t in (0.35, 0.55, 0.75, 0.9):
        p = chest_pt(sx * (0.145 - 0.07 * t), 1.62 - t * 0.5, 0.048)
        ell(bm, p, (0.007, 0.005, 0.007), seg=5, rings=3)
    attach(arm, "Hero_StrapMetal_" + ("L" if sx > 0 else "R"), bm, M_STEEL, "Chest")
    # strap over the shoulder top
    bs = strip(5, 3, lambda r, c, sx=sx: Vector((sx * (0.14 + (c - 0.5) * 0.04), -0.15 + r * 0.30, 1.585 + 0.03 * math.sin(math.pi * r))))
    attach(arm, "Hero_StrapTop_" + ("L" if sx > 0 else "R"), bs, M_LEATH, "Chest")

bm = bmesh.new()                                                       # wide belt (elliptical band) + second thin strap
for z, h in ((1.075, 0.065), (1.005, 0.024)):
    rows = []
    for i in range(28):
        a = 2 * math.pi * i / 28
        rows.append(a)
    verts = []
    for a in rows:
        for zz in (z - h / 2, z + h / 2):
            verts.append(bm.verts.new(Vector((0.262 * math.sin(a), -0.045 - 0.215 * math.cos(a), zz))))
    for i in range(28):
        j = (i + 1) % 28
        bm.faces.new((verts[2 * i], verts[2 * j], verts[2 * j + 1], verts[2 * i + 1]))
attach(arm, "Hero_Belt", bm, M_LEATH, "Hips")
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0, -0.27, 1.075)) @ Matrix.Diagonal((0.07, 0.016, 0.052, 1)))
bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0, -0.279, 1.075)) @ Matrix.Diagonal((0.03, 0.006, 0.036, 1)))
attach(arm, "Hero_Buckle", bm, M_STEEL, "Hips", smooth=False)
bm = bmesh.new()
for sx in (1, -1):
    for z in (1.04, 1.075, 1.11):
        pass
    for i in range(5):                                                  # belt studs
        a = math.radians(-60 + i * 30) * sx
        ell(bm, (0.264 * math.sin(a), -0.045 - 0.217 * math.cos(a), 1.075), (0.006, 0.006, 0.006), seg=4, rings=3)
attach(arm, "Hero_BeltStuds", bm, M_STEEL, "Hips")


def pouch(sx, ang, z, w, h, d):
    a = math.radians(ang) * sx
    c = Vector((0.27 * math.sin(a), -0.045 - 0.225 * math.cos(a), z))
    bm = bmesh.new()
    m = Matrix.Translation(c) @ Matrix.Rotation(-a, 4, 'Z')
    bmesh.ops.create_cube(bm, size=1.0, matrix=m @ Matrix.Diagonal((w, d, h, 1)))
    bmesh.ops.create_cube(bm, size=1.0, matrix=m @ Matrix.Translation((0, -d * 0.1, h * 0.35)) @ Matrix.Diagonal((w * 1.06, d * 1.1, h * 0.38, 1)))
    bmesh.ops.create_cube(bm, size=1.0, matrix=m @ Matrix.Translation((0, -d * 0.62, h * 0.15)) @ Matrix.Diagonal((w * 0.22, d * 0.1, h * 0.14, 1)))
    return bm


for sx, tag in ((1, "L"), (-1, "R")):
    attach(arm, "Hero_Pouch_" + tag, pouch(sx, 62, 0.97, 0.10, 0.12, 0.06), M_LEATH, "Hips")
bm = pouch(1, 118, 0.96, 0.07, 0.1, 0.05)
attach(arm, "Hero_PouchBack", bm, M_LEATH, "Hips")
bm = bmesh.new()                                                       # steel vial hanging at the back-left hip
vc = Vector((0.19, 0.12, 0.93))
bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.026, radius2=0.026, depth=0.11, matrix=Matrix.Translation(vc))
for dz in (-0.06, 0.06):
    bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.03, radius2=0.03, depth=0.014, matrix=Matrix.Translation(vc + Vector((0, 0, dz))))
tube(bm, vc + Vector((0, 0, 0.065)), (0.2, 0.15, 1.04), 0.004, 0.004, seg=4)
attach(arm, "Hero_Vial", bm, M_STEEL, "Hips")
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.016, radius2=0.016, depth=0.075, matrix=Matrix.Translation(vc))
attach(arm, "Hero_VialGlow", bm, M_MAGMA, "Hips")


def kw(co):
    t = smoothstep(1.0, 0.5, co.z); front = max(0.0, -(co.y + 0.05) / max(1e-6, math.hypot(co.x, co.y + 0.05)))
    wl = t * (0.15 + 0.35 * front)
    return {"Hips": 1.0 - wl, ("UpperLeg.L" if co.x >= 0 else "UpperLeg.R"): wl}


def banner(r, c):                                                       # hanging banner loincloth (front)
    w = 0.115 - 0.01 * r
    z = 1.04 - r * 0.50 - 0.04 * (abs(math.sin(c * 9)) ** 1.5) * smoothstep(0.7, 1.0, r) - 0.03 * (abs(c - 0.5) * 2) * r
    return Vector(((c - 0.5) * 2 * w + 0.01 * math.sin(r * 5), -0.285 - 0.03 * r - 0.01 * math.sin(c * 5), z))


skinned(arm, "Hero_Banner", strip(12, 7, banner), M_BANNER, kw)
for sx in (1, -1):                                                      # leather flap fringe at the hips (overlapping tattered strips)
    for k in range(6):
        a = math.radians(30 + 28 * k) * sx
        def flap(r, c, a=a, k=k):
            rad = 0.285 + 0.06 * r
            ln = 0.30 + 0.06 * ((k * 37) % 5) / 5
            w = 0.045 * (1 - 0.35 * r)
            z = 1.03 - r * ln - 0.02 * abs(c - 0.5) * 2 * r
            aa = a + (c - 0.5) * 2 * w / 0.28 * (1 if sx > 0 else -1)
            return Vector((rad * 0.9 * math.sin(aa), -0.05 - rad * 0.8 * math.cos(aa), z))
        skinned(arm, f"Hero_Flap_{'L' if sx > 0 else 'R'}{k}", strip(6, 3, flap), M_LEATH, kw)
for k in range(8):                                                      # back flaps
    a = math.radians(125 + k * 14)
    def bflap(r, c, a=a, k=k):
        rad = 0.265 + 0.05 * r; ln = 0.28 + 0.05 * ((k * 53) % 4) / 4
        aa = a + (c - 0.5) * 0.28
        return Vector((rad * 0.95 * math.sin(aa), -0.05 - rad * 0.8 * math.cos(aa), 1.03 - r * ln))
    skinned(arm, f"Hero_FlapBack{k}", strip(6, 3, bflap), M_LEATH, kw)

print("EV_TOTAL_TRIS", tri_count())
bpy.ops.wm.save_as_mainfile(filepath=OUT + "/embervein.blend")
bpy.ops.export_scene.gltf(filepath=OUT + "/embervein.glb", export_format='GLB', export_apply=True,
                          export_animations=False, export_skins=True)
print("EV_DONE")
