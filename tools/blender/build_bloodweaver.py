"""Bloodweaver hero v3: eldritch CC0 base + a fully bespoke head, boots, layered carapace armour, folded coat, cape (Blender 5.x).
Run: blender -b -P build_bloodweaver.py -- <eldritch.glb> <out_dir>
Front is -Y, T-pose rest, shared 49-bone skeleton untouched. All bespoke parts are named Hero_* (placed exactly as modelled)."""
import bpy, bmesh, math, sys, os, random
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hero_common import *
import numpy as np
import hero_textures as T

SRC, OUT = sys.argv[-2], sys.argv[-1]
random.seed(11)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
remove_objects("_Head", "_Feet")

# ---------- materials ----------
M_CARAPACE = mat("BW_Carapace", (0.40, 0.012, 0.03), 0.22, 0.35)
M_COAT     = mat("BW_Coat",     (0.17, 0.012, 0.035), 0.85)
M_COAT2    = mat("BW_CoatInner",(0.09, 0.008, 0.02), 0.9)
M_LEATHER  = mat("BW_Leather",  (0.03, 0.022, 0.022), 0.5)
M_GOLD     = mat("BW_Gold",     (0.78, 0.56, 0.2), 0.3, 1.0)
M_CAPE     = mat("BW_CapeSheer",(0.55, 0.02, 0.05), 0.4, 0.0, alpha=0.5)
M_VEIL     = mat("BW_Veil",     (0.6, 0.03, 0.06), 0.4, 0.0, alpha=0.38)
M_LASH     = mat("BW_Lash",     (0.28, 0.01, 0.03), 0.3, 0.2)
M_THORN    = mat("BW_Thorn",    (0.5, 0.02, 0.04), 0.3, 0.2, emit=(0.9, 0.05, 0.08), strength=1.8)
M_SKIN     = mat("BW_Skin",     (0.55, 0.46, 0.45), 0.55)
M_LIPS     = mat("BW_Lips",     (0.50, 0.25, 0.28), 0.4)
M_HAIR     = mat("BW_Hair",     (0.018, 0.014, 0.016), 0.4)
M_EYE      = mat("BW_Eye",      (0.70, 0.04, 0.07), 0.15, emit=(0.8, 0.03, 0.06), strength=0.8)
M_DARK     = mat("BW_Dark",     (0.01, 0.008, 0.01), 0.5)
M_CARAPACE_PLAIN = mat("BW_CarapacePlain", (0.40, 0.012, 0.03), 0.22, 0.35)

# ---------- baked procedural textures (1024 cloth, 512 carapace / cape) ----------
TEX = os.path.join(OUT, "tex")
def coat_textures():
    n = 1024; x, y = T._grid(n)
    nz = T.fbm(n, 3, 5, 6)
    weave = 0.5 + 0.5 * np.sin(x * n * 0.75) * np.sin(y * n * 0.75)
    base = np.array([0.17, 0.012, 0.035], np.float32)
    col = base[None, None, :] * (0.78 + 0.35 * nz[..., None]) * (0.92 + 0.08 * weave[..., None])
    X, Y = x * 12, y * 5
    a = np.sin(2 * np.pi * (X + 0.25 * np.sin(2 * np.pi * Y * 2))) * np.sin(2 * np.pi * (Y * 2 + 0.25 * np.sin(2 * np.pi * X * 0.5)))
    line = 1 - T.smooth(0.10, 0.24, np.abs(a))
    mask = np.maximum(T.smooth(0.60, 0.86, y), np.maximum(T.smooth(0.14, 0.05, x), T.smooth(0.86, 0.95, x)) * 0.95)
    k = (line * mask)[..., None]
    gold = np.array([0.78, 0.56, 0.2], np.float32)
    col = col * (1 - k) + gold[None, None, :] * k * (0.8 + 0.2 * nz[..., None])
    h = 0.35 * weave + 0.8 * (line * mask) + 0.15 * nz
    return (T.to_image("coat_diffuse", np.concatenate([col, np.ones((n, n, 1), np.float32)], -1), TEX),
            T.to_image("coat_normal", T.normal_from_height(h, 1.2), TEX, "Non-Color"))
def carapace_textures():
    n = 512
    e, cid = T.voronoi(n, 7, 5)
    nz = T.fbm(n, 9, 4, 8)
    cell = T.smooth(0.0, 0.28, e)
    base = np.array([0.42, 0.012, 0.03], np.float32)
    col = base[None, None, :] * (0.65 + 0.7 * cid[..., None]) * (0.85 + 0.3 * nz[..., None])
    col = col * (0.25 + 0.75 * cell[..., None]) + np.array([0.02, 0, 0.005], np.float32) * (1 - cell[..., None])
    vein = (1 - T.smooth(0.0, 0.16, e)) * (0.5 + 0.5 * nz)
    emis = np.stack([vein * 1.0, vein * 0.06, vein * 0.1, np.ones((n, n), np.float32)], -1)
    h = 0.8 * cell + 0.2 * nz
    return (T.to_image("carapace_diffuse", np.concatenate([col, np.ones((n, n, 1), np.float32)], -1), TEX),
            T.to_image("carapace_normal", T.normal_from_height(h, 2.5), TEX, "Non-Color"),
            T.to_image("carapace_emission", emis, TEX))
def cape_texture():
    n = 512; x, y = T._grid(n)
    nz = T.fbm(n, 21, 5, 5)
    vein = 1 - np.abs(2 * nz - 1)
    v = T.smooth(0.84, 0.97, vein)
    alpha = (0.30 + 0.12 * nz + 0.5 * v) * (1 - 0.55 * T.smooth(0.88, 1.0, y))
    col = np.stack([0.55 + 0.25 * v, 0.02 + 0.02 * v, 0.05 + 0.03 * v], -1)
    return T.to_image("cape_diffuse", np.concatenate([col, alpha[..., None]], -1), TEX)
_ci, _cn = coat_textures()
_ki, _kn, _ke = carapace_textures()
_pi = cape_texture()
T.bind(M_COAT, _ci, _cn)
T.bind(M_CARAPACE, _ki, _kn, _ke, 1.4)
T.bind(M_CAPE, _pi)

recolor_base({"LightBrown": (0.14, 0.012, 0.03), "LightBlue": (0.03, 0.025, 0.025), "Skin": (0.03, 0.024, 0.024)})

# ---------- head: sculpted face, ears, hair ----------
FX, FY, FZ = 0.0, -0.043, 1.64                           # head centre
bm = bmesh.new()
ell(bm, (0, -0.04, 1.655), (0.080, 0.104, 0.098), seg=18, rings=12)       # cranium
ell(bm, (0, -0.085, 1.600), (0.060, 0.072, 0.068), seg=14, rings=9)        # cheeks / face
ell(bm, (0, -0.100, 1.548), (0.030, 0.040, 0.034), seg=12, rings=7)        # chin
for sx in (1, -1):
    ell(bm, (sx * 0.040, -0.062, 1.568), (0.020, 0.046, 0.036), seg=10, rings=6)           # jaw
    ell(bm, (sx * 0.046, -0.108, 1.596), (0.015, 0.013, 0.011), seg=8, rings=5)            # cheekbone
    ell(bm, (sx * 0.034, -0.134, 1.668), (0.036, 0.013, 0.009), rot=(0, sx * math.radians(14), 0), seg=8, rings=5)   # brow ridge
    cone(bm, (sx * 0.078, -0.035, 1.634), (sx * 1.0, -0.15, 0.55), 0.016, 0.050, seg=6)   # pointed ear
tube(bm, (0, -0.138, 1.652), (0, -0.166, 1.610), 0.011, 0.014, seg=6)       # nose bridge
ell(bm, (0, -0.168, 1.607), (0.014, 0.015, 0.012), seg=8, rings=5)         # nose tip
for sx in (1, -1):
    ell(bm, (sx * 0.015, -0.158, 1.602), (0.010, 0.012, 0.009), seg=6, rings=4)            # nostril wing
ell(bm, (0, -0.040, 1.50), (0.042, 0.042, 0.055), seg=10, rings=6)         # neck
attach(arm, "Hero_Face", bm, M_SKIN, "Head")
bm = bmesh.new()
ell(bm, (0, -0.148, 1.5725), (0.022, 0.010, 0.0065), seg=8, rings=4)
ell(bm, (0, -0.145, 1.5615), (0.020, 0.010, 0.0075), seg=8, rings=4)
attach(arm, "Hero_Lips", bm, M_LIPS, "Head")
bm = bmesh.new()
for sx in (1, -1):
    ell(bm, (sx * 0.035, -0.134, 1.641), (0.021, 0.010, 0.012), seg=8, rings=5)            # dark socket / liner
    ell(bm, (sx * 0.036, -0.139, 1.653), (0.020, 0.0055, 0.0045), rot=(0, sx * math.radians(12), 0), seg=8, rings=4)   # lid
    ell(bm, (sx * 0.037, -0.145, 1.676), (0.026, 0.006, 0.0045), rot=(0, sx * math.radians(18), 0), seg=8, rings=4)    # eyebrow
attach(arm, "Hero_Liner", bm, M_DARK, "Head")
bm = bmesh.new()
for sx in (1, -1):
    ell(bm, (sx * 0.035, -0.139, 1.640), (0.0155, 0.0085, 0.0095), seg=10, rings=6)
attach(arm, "Hero_Eyes", bm, M_EYE, "Head")
bm = bmesh.new()
ell(bm, (0, -0.032, 1.667), (0.094, 0.112, 0.103), seg=16, rings=10)       # hair cap (front hairline left clear)
for k in range(46):                                                         # swept-back locks
    ph = math.radians(random.uniform(-120, 120))
    el = math.radians(random.uniform(10, 70))
    root = Vector((0.085 * math.sin(ph) * math.cos(el), -0.04 - 0.105 * math.cos(ph) * math.cos(el), 1.655 + 0.10 * math.sin(el)))
    sweep = Vector((math.sin(ph) * 0.5, 0.9 + abs(math.sin(ph)) * 0.2, -0.45 - 0.35 * math.sin(el) + random.uniform(-0.1, 0.1)))
    ln = random.uniform(0.07, 0.15) * (1.4 if abs(ph) > 1.4 else 1.0)
    tube(bm, root, root + sweep.normalized() * ln, 0.017, 0.002, seg=4)
for sx in (1, -1):                                                          # face-framing side locks
    for j in range(3):
        root = Vector((sx * 0.082, -0.095 + j * 0.01, 1.69 - j * 0.015))
        tube(bm, root, root + Vector((sx * 0.012, -0.01, -0.10 - j * 0.02)), 0.014, 0.002, seg=4)
for j in range(5):                                                          # fringe across the forehead
    x = (j - 2) * 0.03
    root = Vector((x, -0.125, 1.712 - abs(x) * 0.5))
    tube(bm, root, root + Vector((x * 0.9, -0.03, -0.055)), 0.012, 0.002, seg=4)
attach(arm, "Hero_Hair", bm, M_HAIR, "Head", smooth=True)

# ---------- tall leather boots with cuffs and buckles ----------
for side, lower, foot in ((1, "LowerLeg.L", "Foot.L"), (-1, "LowerLeg.R", "Foot.R")):
    cx = side * 0.121
    def shaft(r, c, cx=cx):
        a = 2 * math.pi * c
        z = 0.62 - r * 0.59
        rad = 0.062 - 0.012 * min(1.0, r * 1.6) + (0.012 if r < 0.05 else 0.0)
        ycen = -0.087 + 0.025 * r
        return Vector((cx + rad * math.cos(a), ycen + rad * math.sin(a) * 1.05, z))
    def wshaft(co, lower=lower, foot=foot):
        t = smoothstep(0.30, 0.10, co.z)
        return {lower: 1.0 - t, foot: t}
    skinned(arm, "Hero_BootShaft_" + ("L" if side > 0 else "R"), strip(12, 18, shaft), M_LEATHER, wshaft)
    def cuff(r, c, cx=cx):
        a = 2 * math.pi * c
        rad = 0.074 + 0.012 * r
        return Vector((cx + rad * math.cos(a), -0.087 + rad * math.sin(a) * 1.05, 0.62 + 0.035 * r))
    skinned(arm, "Hero_BootCuff_" + ("L" if side > 0 else "R"), strip(3, 18, cuff), M_COAT2, lambda co, lower=lower: {lower: 1.0})
    bm = bmesh.new()
    ell(bm, (cx, -0.135, 0.050), (0.052, 0.105, 0.042), seg=12, rings=7)                    # toe box
    ell(bm, (cx, -0.046, 0.052), (0.047, 0.050, 0.050), seg=10, rings=6)                    # heel counter
    ell(bm, (cx, -0.105, 0.016), (0.055, 0.135, 0.014), seg=12, rings=5)                    # sole
    ell(bm, (cx, -0.030, 0.024), (0.040, 0.038, 0.022), seg=8, rings=4)                     # heel block
    attach(arm, "Hero_BootFoot_" + ("L" if side > 0 else "R"), bm, M_LEATHER, foot)
    bm = bmesh.new()
    for z in (0.38, 0.27, 0.17):                                                            # buckle straps
        ell(bm, (cx + side * 0.045, -0.08 + (0.62 - z) * 0.04, z), (0.018, 0.026, 0.016), seg=6, rings=4)
    ell(bm, (cx, -0.185, 0.050), (0.024, 0.014, 0.020), seg=6, rings=4)                      # toe cap
    attach(arm, "Hero_BootTrim_" + ("L" if side > 0 else "R"), bm, M_GOLD, foot)

# ---------- coat: folded, front-slit, layered hem + gold lapel bands (skinned) ----------
def coat_pt(r, c, extra=0.0):
    a = math.radians(24 + c * (360 - 48))
    deg = math.degrees(a)
    z0 = 1.02
    flap = 0.13 if (deg < 80 or deg > 280) else 0.0
    saw = abs(math.sin(c * 31.0 + 0.6)) * 0.06 * (r ** 2)
    hem = 0.26 + 0.05 * math.sin(c * 13.0) + flap - saw
    z = z0 + r * (hem - z0)
    fold = 0.013 * math.sin(c * 44.0 + r * 2.0) * (r ** 1.2)
    rad = 0.185 + 0.17 * (r ** 1.5) + fold + extra
    return Vector((rad * math.sin(a), -rad * math.cos(a), z))
def coat_w(co):
    t = smoothstep(1.0, 0.45, co.z)
    front = max(0.0, -co.y / max(1e-6, math.hypot(co.x, co.y)))
    wl = t * (0.25 + 0.6 * front)
    return {"Hips": 1.0 - wl, ("UpperLeg.L" if co.x >= 0 else "UpperLeg.R"): wl}
skinned(arm, "Hero_Coat", strip(16, 72, coat_pt), M_COAT, coat_w)
skinned(arm, "Hero_CoatInner", strip(8, 72, lambda r, c: coat_pt(r, c, -0.028)), M_COAT2, coat_w)
skinned(arm, "Hero_CoatTrim", strip(2, 72, lambda r, c: coat_pt(1.0 - r * 0.045, c, 0.002)), M_GOLD, coat_w)
for tag, c0, c1 in (("A", 0.0, 0.03), ("B", 0.97, 1.0)):                                   # gold lapel bands on the slit edges
    skinned(arm, "Hero_Lapel" + tag, strip(16, 3, lambda r, c, c0=c0, c1=c1: coat_pt(r, c0 + c * (c1 - c0), 0.003)), M_GOLD, coat_w)
for tag, c0, c1 in (("A", 0.055, 0.115), ("B", 0.885, 0.945)):                              # embroidered front panels
    skinned(arm, "Hero_Panel" + tag, strip(16, 4, lambda r, c, c0=c0, c1=c1: coat_pt(r, c0 + c * (c1 - c0), 0.004)), M_COAT2, coat_w)

# sheer red veil: tattered translucent strips over the lower coat
def veil_pt(r, c):
    a = math.radians(30 + c * (360 - 60))
    saw = (abs(math.sin(c * 52.0)) ** 0.7) * 0.11 * (r ** 2)
    z = 0.98 + r * (0.14 - 0.98) - saw
    rad = 0.2 + 0.20 * (r ** 1.5) + 0.014 + 0.012 * math.sin(c * 38.0) * r
    return Vector((rad * math.sin(a), -rad * math.cos(a), z))
skinned(arm, "Hero_Veil", strip(10, 72, veil_pt), M_VEIL, coat_w)

# ---------- belt, straps, buckle ----------
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=0.178, radius2=0.178, depth=0.05, matrix=Matrix.Translation((0, -0.05, 1.03)))
ell(bm, (0, -0.222, 1.03), (0.040, 0.012, 0.040), seg=12, rings=6)
for sx in (1, -1):
    ell(bm, (sx * 0.10, -0.205, 1.03), (0.014, 0.008, 0.014), seg=6, rings=4)
attach(arm, "Hero_Belt", bm, M_GOLD, "Hips")
bm = bmesh.new()
ell(bm, (0, -0.2305, 1.03), (0.020, 0.006, 0.020), seg=8, rings=5)
attach(arm, "Hero_Ruby", bm, M_THORN, "Hips")

# ---------- collar: tall, scalloped, with gold wire and gorget plates ----------
def collar_pt(r, c, extra=0.0):
    a = math.radians(52 + c * (360 - 104))
    back = max(0.0, math.cos(a - math.pi))
    scallop = 0.018 * (abs(math.sin(c * 14.0)) ** 0.6) * r
    z = 1.43 + r * (0.085 + 0.09 * back + scallop)
    rad = 0.108 + 0.055 * r + extra
    return Vector((rad * math.sin(a), -rad * math.cos(a) - 0.035, z))
attach(arm, "Hero_Collar", strip(5, 40, collar_pt), M_CARAPACE, "Chest")
attach(arm, "Hero_CollarTrim", strip(2, 40, lambda r, c: collar_pt(1.0, c, 0.003) + Vector((0, 0, -r * 0.014))), M_GOLD, "Chest")
bm = bmesh.new()
for sx in (1, -1):
    for i in range(3):
        ell(bm, (sx * (0.075 + i * 0.03), -0.095, 1.447 - i * 0.012), (0.032, 0.05, 0.010), rot=(math.radians(-20), 0, sx * math.radians(-18 - 12 * i)), seg=7, rings=4)
attach(arm, "Hero_Gorget", bm, M_CARAPACE, "Chest", smooth=False)

# ---------- pauldrons: arching overlapping plates with gold rims and curved horns ----------
def arch_pt(side, x0, x1, R, tip, r, c, dr=0.0):
    ph = math.radians(-85 + c * 170)
    x_end = x1 + tip * (1 - abs(ph) / math.radians(85)) ** 1.3
    x = x0 + r * (x_end - x0)
    rad = (R * (1 - 0.10 * r)) + dr
    return Vector((side * x, -0.06 - rad * 0.95 * math.sin(ph), 1.432 + rad * 0.82 * math.cos(ph) - 0.04 * r * r))
PLATES = ((0.09, 0.235, 0.098, 0.035), (0.20, 0.30, 0.088, 0.028), (0.265, 0.345, 0.078, 0.024))
for side, bone, tag in ((1, "Shoulder.L", "L"), (-1, "Shoulder.R", "R")):
    for i, (x0, x1, R, tip) in enumerate(PLATES):
        attach(arm, f"Hero_Pauldron{i}_{tag}", strip(6, 13, lambda r, c, s=side, x0=x0, x1=x1, R=R, tip=tip: arch_pt(s, x0, x1, R, tip, r, c)), M_CARAPACE, bone)
        attach(arm, f"Hero_PauldronRim{i}_{tag}", strip(2, 13, lambda r, c, s=side, x0=x0, x1=x1, R=R, tip=tip: arch_pt(s, x0, x1, R, tip, 0.96 + r * 0.04, c, 0.004)), M_GOLD, bone)
    bm = bmesh.new()                                                           # big curved horn + two small spikes
    p = [Vector((side * 0.13, -0.06, 1.535)), Vector((side * 0.16, -0.045, 1.60)), Vector((side * 0.215, -0.03, 1.645)), Vector((side * 0.27, -0.02, 1.655))]
    for (a, b, r0, r1) in ((p[0], p[1], 0.026, 0.020), (p[1], p[2], 0.020, 0.012), (p[2], p[3], 0.012, 0.002)):
        tube(bm, a, b, r0, r1, seg=6)
    for xx, ln in ((0.225, 0.07),):
        tube(bm, Vector((side * xx, -0.06, 1.512)), Vector((side * (xx + 0.04), -0.055, 1.512 + ln)), 0.016, 0.002, seg=5)
    attach(arm, "Hero_Horns_" + tag, bm, M_CARAPACE_PLAIN, bone, smooth=False)

# ---------- vambraces: stacked carapace plates on the forearms ----------
for side, bone, tag in ((1, "LowerArm.L", "L"), (-1, "LowerArm.R", "R")):
    for i in range(3):
        x0 = 0.37 + i * 0.05; x1 = x0 + 0.066
        def vamb(r, c, s=side, x0=x0, x1=x1, i=i):
            ph = math.radians(-110 + c * 220)
            x = x0 + r * (x1 - x0) + 0.012 * (1 - abs(ph) / math.radians(110))
            rad = 0.052 - i * 0.002
            return Vector((s * x, -0.056 - rad * math.sin(ph), 1.432 + rad * math.cos(ph) * 0.95))
        attach(arm, f"Hero_Vambrace{i}_{tag}", strip(4, 10, vamb), M_CARAPACE, bone)
    bm = bmesh.new()
    for i in range(2):                                                          # two small spikes on the outer face
        x = side * (0.40 + i * 0.07)
        tube(bm, Vector((x, -0.056, 1.486)), Vector((x + side * 0.025, -0.056, 1.486 + 0.04)), 0.011, 0.002, seg=4)
    attach(arm, "Hero_VambraceSpikes_" + tag, bm, M_CARAPACE_PLAIN, bone, smooth=False)

# ---------- chest scales (front) and back carapace ----------
def scale_mesh(bm, cx, cz, w, h, surf, lift, uvm):
    rows, cols = 4, 5
    vs = []
    for ri in range(rows):
        v = ri / (rows - 1)
        row = []
        for ci in range(cols):
            u = (ci / (cols - 1)) * 2 - 1
            width = w * (1 - 0.88 * v ** 1.7)
            x = cx + u * width
            y = surf(x) - 0.004 * (1 - u * u) * 2 - lift * v
            nv = bm.verts.new(Vector((x, y, cz - v * h)))
            uvm[nv] = (ci / (cols - 1), 1.0 - ri / (rows - 1))
            row.append(nv)
        vs.append(row)
    for ri in range(rows - 1):
        for ci in range(cols - 1):
            bm.faces.new((vs[ri][ci], vs[ri][ci + 1], vs[ri + 1][ci + 1], vs[ri + 1][ci]))
bm = bmesh.new(); uvm = {}
for z, n in ((1.455, 6), (1.405, 5), (1.355, 6), (1.305, 5), (1.255, 4), (1.205, 3)):
    for k in range(n):
        x = (k - (n - 1) / 2) * 0.052
        scale_mesh(bm, x, z, 0.034, 0.075, lambda xx: -0.166 + xx * xx * 2.2, 0.018, uvm)
assign_uv(bm, uvm)
attach(arm, "Hero_ChestScales", bm, M_CARAPACE, "Chest", smooth=False)
bm = bmesh.new(); uvm = {}
for z, n, w in ((1.46, 4, 0.05), (1.395, 4, 0.047), (1.33, 3, 0.044), (1.265, 3, 0.04), (1.20, 2, 0.036)):
    for k in range(n):
        x = (k - (n - 1) / 2) * w * 1.7
        scale_mesh(bm, x, z, w * 0.8, 0.085, lambda xx: 0.09 - xx * xx * 2.0, -0.018, uvm)
for i in range(9):                                                              # spine ridge
    z = 1.47 - i * 0.034
    ell(bm, (0, 0.104, z), (0.014, 0.012, 0.022), seg=6, rings=4)
assign_uv(bm, uvm)
attach(arm, "Hero_BackPlates", bm, M_CARAPACE, "Chest", smooth=False)

# ---------- cape: folded, tattered, translucent ----------
def cape_pt(r, c):
    x = (c - 0.5) * (0.34 + 0.46 * r)
    z = 1.47 + r * (0.30 - 1.47)
    saw = (abs(math.sin(c * 21.0)) ** 0.8) * 0.07 * (r ** 2)
    fold = 0.022 * math.sin(c * 17.0 + r * 3.0) * r
    y = 0.108 + 0.09 * r + fold
    return Vector((x, y, z - saw))
attach(arm, "Hero_Cape", strip(20, 24, cape_pt), M_CAPE, "Chest")

# ---------- blood-spike lash ----------
hand = arm.matrix_world @ arm.data.bones["Hand.R"].head_local
cx = hand.x - 0.03
bm = bmesh.new(); bt = bmesh.new()
N, SIDES = 100, 6
path = []
for i in range(N):
    t = i / (N - 1)
    ang = t * 3.0 * 2 * math.pi
    rad = 0.075 * (1 - t) + 0.012
    path.append(Vector((cx + rad * math.cos(ang), hand.y + rad * math.sin(ang), hand.z - 0.09 - t * 0.40)))
rings = []
for i, p in enumerate(path):
    tan = (path[min(i + 1, N - 1)] - path[max(i - 1, 0)]).normalized()
    sd = tan.cross(Vector((0, 0, 1)))
    if sd.length < 1e-3: sd = Vector((1, 0, 0))
    sd.normalize(); up = sd.cross(tan).normalized()
    r = 0.012 * (1 - i / N * 0.72)
    rings.append([bm.verts.new(p + (sd * math.cos(2 * math.pi * k / SIDES) + up * math.sin(2 * math.pi * k / SIDES)) * r) for k in range(SIDES)])
for i in range(N - 1):
    for k in range(SIDES):
        bm.faces.new((rings[i][k], rings[i][(k + 1) % SIDES], rings[i + 1][(k + 1) % SIDES], rings[i + 1][k]))
    if i % 3 == 0:
        p = path[i]; out = p - Vector((cx, hand.y, p.z))
        out = out.normalized() if out.length > 1e-4 else Vector((0, -1, 0))
        cone(bt, p, out + Vector((0, 0, -0.3)), 0.011, 0.05 * (1 - i / N * 0.5), seg=4)
bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.024, radius2=0.019, depth=0.17, matrix=Matrix.Translation((cx, hand.y, hand.z - 0.02)))
for k in range(4):
    bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.027, radius2=0.027, depth=0.012, matrix=Matrix.Translation((cx, hand.y, hand.z - 0.06 + k * 0.035)))
attach(arm, "Hero_Lash", bm, M_LASH, "Hand.R")
attach(arm, "Hero_LashThorns", bt, M_THORN, "Hand.R", smooth=False)
hb = bmesh.new()
bmesh.ops.create_cone(hb, cap_ends=True, segments=10, radius1=0.03, radius2=0.03, depth=0.045, matrix=Matrix.Translation((cx, hand.y, hand.z + 0.075)))
cone(hb, (cx, hand.y, hand.z + 0.095), (0, 0, 1), 0.022, 0.05, seg=8)
attach(arm, "Hero_LashCap", hb, M_GOLD, "Hand.R")

print("BW_TOTAL_TRIS", tri_count())
bpy.ops.wm.save_as_mainfile(filepath=OUT + "/bloodweaver.blend")
bpy.ops.export_scene.gltf(filepath=OUT + "/bloodweaver.glb", export_format='GLB', export_apply=True,
                          export_animations=False, export_skins=True)
print("BW_DONE")
