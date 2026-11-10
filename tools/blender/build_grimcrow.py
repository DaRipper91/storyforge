"""Grimcrow v2: raven-headed corvid oracle on the primal shared-skeleton base (Blender 5.x), benchmark-level detail.
Run: blender -b -P build_grimcrow.py -- <primal.glb> <out_dir>
Replaces the base head and shoes. Real feather cards (head crest, ruff, mantle, forearms), wide ragged sleeves, torso tunic,
three tattered robe layers + hem fringe (skinned), bone-net shawl with tassels, scaled bird legs and talons, baked textures."""
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

# ---------- textures ----------
TEX = os.path.join(OUT, "tex_gc")
def feather_tex():
    n = 256; x, y = T._grid(n)                      # x across (0..1), y along the feather (0 = root, 1 = tip when v flipped)
    u = np.abs(x - 0.5) * 2
    barb = 0.5 + 0.5 * np.sin((y * 60 + u * 26) * np.pi)
    rib = np.exp(-((x - 0.5) / 0.018) ** 2)
    sheen = T.smooth(0.55, 1.0, barb) * (0.4 + 0.6 * np.sin(y * 7) ** 2)
    base = np.array([0.025, 0.03, 0.055], np.float32)
    col = base[None, None, :] * (0.7 + 0.5 * barb[..., None]) + np.stack([sheen * 0.02, sheen * 0.09, sheen * 0.22], -1)
    col += rib[..., None] * np.array([0.10, 0.10, 0.12], np.float32)
    h = 0.6 * barb + 0.8 * rib
    return (T.to_image("feather_diffuse", np.concatenate([col, np.ones((n, n, 1), np.float32)], -1), TEX),
            T.to_image("feather_normal", T.normal_from_height(h, 1.6), TEX, "Non-Color"))
def robe_tex():
    n = 1024; x, y = T._grid(n)
    nz = T.fbm(n, 4, 5, 6)
    weave = 0.5 + 0.5 * np.sin(x * n * 0.7) * np.sin(y * n * 0.7)
    base = np.array([0.07, 0.062, 0.07], np.float32)
    col = base[None, None, :] * (0.75 + 0.5 * nz[..., None]) * (0.9 + 0.1 * weave[..., None])
    fx, fy = (x * 40) % 1.0, (y * 9) % 1.0                       # diamond embroidery in the lower robe and hem
    dia = np.abs(fx - 0.5) + np.abs(fy - 0.5)
    ring = (np.abs(dia - 0.33) < 0.05) | (dia < 0.09)
    mask = T.smooth(0.55, 0.78, y)
    tan = np.array([0.42, 0.32, 0.19], np.float32)
    k = (ring * mask)[..., None]
    col = col * (1 - k) + tan[None, None, :] * k * (0.75 + 0.25 * nz[..., None])
    fray = T.smooth(0.9, 1.0, y) * nz                            # darker frayed lower edge
    col *= (1 - 0.5 * fray[..., None])
    h = 0.4 * weave + 0.9 * (ring * mask) + 0.2 * nz
    return (T.to_image("robe_diffuse", np.concatenate([col, np.ones((n, n, 1), np.float32)], -1), TEX),
            T.to_image("robe_normal", T.normal_from_height(h, 1.1), TEX, "Non-Color"))
def band_tex():
    n = 512; x, y = T._grid(n)
    fx, fy = (x * 3) % 1.0, (y * 12) % 1.0
    dia = np.abs(fx - 0.5) + np.abs(fy - 0.5)
    ring = ((np.abs(dia - 0.38) < 0.06) | (dia < 0.14)) & (np.abs(x - 0.5) < 0.46)
    nz = T.fbm(n, 8, 4, 8)
    bg = np.array([0.10, 0.075, 0.06], np.float32); tan = np.array([0.50, 0.38, 0.22], np.float32)
    col = np.where(ring[..., None], tan[None, None, :] * (0.8 + 0.2 * nz[..., None]), bg[None, None, :] * (0.8 + 0.4 * nz[..., None]))
    return T.to_image("band_diffuse", np.concatenate([col, np.ones((n, n, 1), np.float32)], -1), TEX)
def scale_tex():
    n = 256; e, cid = T.voronoi(n, 6, 3)
    cell = T.smooth(0.0, 0.3, e)
    col = np.array([0.05, 0.045, 0.05], np.float32)[None, None, :] * (0.6 + 0.9 * cid[..., None]) * (0.4 + 0.6 * cell[..., None])
    return (T.to_image("legscale_diffuse", np.concatenate([col, np.ones((n, n, 1), np.float32)], -1), TEX),
            T.to_image("legscale_normal", T.normal_from_height(cell, 2.0), TEX, "Non-Color"))

# ---------- materials ----------
M_FEATHER = mat("GC_Feather", (0.04, 0.045, 0.07), 0.32, 0.3)
M_BEAK    = mat("GC_Beak",    (0.045, 0.045, 0.055), 0.22, 0.5)
M_EYE     = mat("GC_Eye",     (0.45, 0.22, 0.05), 0.12, 0.0, emit=(0.6, 0.3, 0.05), strength=0.7)
M_CLOTH   = mat("GC_Cloth",   (0.075, 0.065, 0.075), 0.95)
M_CLOTH2  = mat("GC_ClothDark", (0.045, 0.04, 0.05), 0.95)
M_BAND    = mat("GC_Band",    (0.2, 0.15, 0.1), 0.85)
M_BONE    = mat("GC_Bone",    (0.78, 0.70, 0.54), 0.55)
M_TALON   = mat("GC_Talon",   (0.04, 0.04, 0.045), 0.3, 0.6)
M_LEG     = mat("GC_LegScale",(0.05, 0.045, 0.05), 0.4, 0.2)
fi, fn = feather_tex(); ri, rn = robe_tex(); bi = band_tex(); si, sn = scale_tex()
T.bind(M_FEATHER, fi, fn); T.bind(M_CLOTH, ri, rn); T.bind(M_BAND, bi); T.bind(M_LEG, si, sn)
recolor_base({"Skin": (0.02, 0.024, 0.045), "Swat": (0.075, 0.065, 0.07), "Swat_Black": (0.04, 0.035, 0.04)})

# ---------- feather card ----------
def feather(bm, uvm, root, direction, length, width, curl=0.25, rows=5):
    d = Vector(direction).normalized(); up = Vector((0, 0, 1))
    side = d.cross(up)
    if side.length < 1e-3: side = Vector((1, 0, 0))
    side.normalize(); nrm = side.cross(d).normalized()
    vs = []
    for r in range(rows):
        t = r / (rows - 1)
        pos = Vector(root) + d * length * t + nrm * (curl * length * t * t)
        w = width * (math.sin(min(1.0, 0.25 + t * 0.9) * math.pi / 2 * 1.0)) * (1 - t ** 2.2)
        row = []
        for c in range(3):
            v = bm.verts.new(pos + side * ((c - 1) * w) + nrm * (abs(c - 1) * w * 0.22))
            uvm[v] = (c / 2.0, 1.0 - t)
            row.append(v)
        vs.append(row)
    for r in range(rows - 1):
        for c in range(2):
            try: bm.faces.new((vs[r][c], vs[r][c + 1], vs[r + 1][c + 1], vs[r + 1][c]))
            except ValueError: pass

def ring_feathers(bm, uvm, cz, rad, n, ln, wd, sag, y0=-0.043, rot=0.0, jitter=0.15):
    for k in range(n):
        a = 2 * math.pi * k / n + rot
        p = Vector((rad * math.sin(a), y0 - rad * math.cos(a), cz))
        d = Vector((math.sin(a) * 0.7, -math.cos(a) * 0.7, -sag + random.uniform(-jitter, jitter)))
        feather(bm, uvm, p, d, ln * random.uniform(0.9, 1.15), wd)

# ---------- raven head ----------
bm = bmesh.new(); uv = {}
ell(bm, (0, -0.075, 1.635), (0.088, 0.112, 0.090), seg=16, rings=10)               # skull
ell(bm, (0, -0.025, 1.600), (0.072, 0.078, 0.066), seg=12, rings=8)                # nape
for sx in (1, -1):
    ell(bm, (sx * 0.062, -0.115, 1.642), (0.030, 0.030, 0.026), seg=8, rings=6)    # brow / eye socket bulge
    ell(bm, (sx * 0.064, -0.045, 1.600), (0.026, 0.05, 0.040), seg=8, rings=5)     # cheek
attach(arm, "Hero_RavenHead", bm, M_CLOTH2, "Head", smooth=True)
bm = bmesh.new(); uv = {}
for i in range(7):                                                                   # crown feathers
    for sx in (-1, 0, 1):
        root = Vector((sx * 0.05 * (1 - i * 0.1), -0.10 + i * 0.022, 1.705 - i * 0.012))
        feather(bm, uv, root, (sx * 0.25, 0.8, 0.55 - i * 0.12), 0.085 + i * 0.006, 0.026, curl=0.3)
for sx in (1, -1):                                                                   # cheek / auricular feathers swept back
    for j in range(5):
        root = Vector((sx * 0.082, -0.10 + j * 0.025, 1.64 - j * 0.012))
        feather(bm, uv, root, (sx * 0.5, 0.8, -0.25), 0.075, 0.024, curl=0.2)
for k in range(10):                                                                  # throat feathers
    a = math.radians(-60 + k * 13)
    root = Vector((0.07 * math.sin(a), -0.12 - 0.02 * math.cos(a), 1.565))
    feather(bm, uv, root, (math.sin(a) * 0.5, -0.4, -1.0), 0.06, 0.022, curl=0.3)
assign_uv(bm, uv)
attach(arm, "Hero_HeadFeathers", bm, M_FEATHER, "Head", smooth=True)
bm = bmesh.new()
tube(bm, (0, -0.165, 1.645), (0, -0.255, 1.640), 0.054, 0.040, seg=8)                # upper beak: thick base, ridge, hooked tip
tube(bm, (0, -0.255, 1.640), (0, -0.335, 1.612), 0.040, 0.020, seg=8)
tube(bm, (0, -0.335, 1.612), (0, -0.372, 1.572), 0.020, 0.004, seg=6)
tube(bm, (0, -0.165, 1.612), (0, -0.255, 1.602), 0.040, 0.028, seg=8)                # lower beak
tube(bm, (0, -0.255, 1.602), (0, -0.322, 1.588), 0.028, 0.010, seg=6)
for sx in (1, -1):
    ell(bm, (sx * 0.016, -0.215, 1.650), (0.007, 0.022, 0.005), seg=6, rings=4)       # nostril slits
attach(arm, "Hero_Beak", bm, M_BEAK, "Head")
bm = bmesh.new()
for sx in (1, -1):
    ell(bm, (sx * 0.079, -0.128, 1.652), (0.0165, 0.012, 0.0165), seg=10, rings=6)    # eye
attach(arm, "Hero_Eyes", bm, M_EYE, "Head")
bm = bmesh.new()
for sx in (1, -1):
    ell(bm, (sx * 0.0755, -0.122, 1.652), (0.0235, 0.011, 0.0235), seg=10, rings=6)   # lid ring
attach(arm, "Hero_EyeLids", bm, M_BEAK, "Head")

# ---------- neck ruff and mantle (feather layers) ----------
bm = bmesh.new(); uv = {}
for i, (z, rad, n, ln) in enumerate(((1.56, 0.075, 14, 0.07), (1.53, 0.095, 16, 0.085), (1.50, 0.115, 18, 0.10), (1.47, 0.135, 20, 0.115))):
    ring_feathers(bm, uv, z, rad, n, ln, 0.03 + i * 0.004, 0.95, rot=i * 0.17)
assign_uv(bm, uv)
attach(arm, "Hero_NeckRuff", bm, M_FEATHER, "Neck", smooth=True)
for side, bone, tag in ((1, "UpperArm.L", "L"), (-1, "UpperArm.R", "R")):            # shoulder mantle: three layers of feathers over the shoulder
    bm = bmesh.new(); uv = {}
    for layer, (x0, z0, ln, wd) in enumerate(((0.10, 1.50, 0.13, 0.04), (0.15, 1.49, 0.14, 0.042), (0.20, 1.475, 0.15, 0.044), (0.26, 1.46, 0.15, 0.044))):
        for k in range(7):
            yy = -0.06 + (k - 3) * 0.032
            feather(bm, uv, Vector((side * x0, yy, z0)), (side * 0.55, 0.05 * (k - 3), -0.8), ln, wd, curl=0.2)
    assign_uv(bm, uv)
    attach(arm, "Hero_Mantle_" + tag, bm, M_FEATHER, bone, smooth=True)

# ---------- torso tunic and wide ragged sleeves ----------
def tunic(r, c, extra=0.0):
    a = 2 * math.pi * c
    z = 1.47 - r * 0.50
    rx = 0.165 + 0.02 * r + extra; ry = 0.135 + 0.02 * r + extra
    return Vector((rx * math.sin(a), -0.043 - ry * math.cos(a) * 1.0, z))
def tunic_w(co):
    ch = smoothstep(1.18, 1.32, co.z); tq = smoothstep(1.02, 1.1, co.z) * (1 - ch)
    return {"Chest": ch, "Torso": tq, "Hips": max(0.0, 1.0 - ch - tq)}
skinned(arm, "Hero_Tunic", strip(8, 28, tunic), M_CLOTH, tunic_w)
for side, tag, up, lo in ((1, "L", "UpperArm.L", "LowerArm.L"), (-1, "R", "UpperArm.R", "LowerArm.R")):
    def sleeve(r, c, side=side):
        a = 2 * math.pi * c
        x = 0.15 + r * 0.46
        rad = 0.062 + 0.045 * r * r
        sag = 0.075 * r * r * (0.5 + 0.5 * math.cos(a - math.pi)) * 1.0
        rag = (0.03 * abs(math.sin(c * 21))) * (r ** 3) if r > 0.9 else 0.0
        return Vector((side * (x - rag), -0.06 + rad * math.sin(a) * 0.95, 1.432 + rad * math.cos(a) - sag))
    def sleeve_w(co, side=side, up=up, lo=lo):
        t = smoothstep(0.26, 0.36, abs(co.x))
        return {up: 1.0 - t, lo: t}
    skinned(arm, "Hero_Sleeve_" + tag, strip(10, 18, sleeve), M_CLOTH2, sleeve_w)
    bm = bmesh.new(); uv = {}                                                         # primary feathers hanging off the forearm
    for k in range(9):
        x = side * (0.30 + k * 0.032)
        for dy in (-0.04, 0.04):
            feather(bm, uv, Vector((x, -0.06 + dy, 1.40)), (side * 0.18, dy * 1.4, -1.0), 0.15 + 0.012 * k, 0.034, curl=0.15)
    assign_uv(bm, uv)
    attach(arm, "Hero_ArmFeathers_" + tag, bm, M_FEATHER, lo, smooth=True)

# ---------- tattered robe: three skinned layers + embroidered band + hem fringe ----------
def robe_w(co):
    t = smoothstep(1.0, 0.4, co.z)
    front = max(0.0, -co.y / max(1e-6, math.hypot(co.x, co.y)))
    wl = t * (0.25 + 0.6 * front)
    return {"Hips": 1.0 - wl, ("UpperLeg.L" if co.x >= 0 else "UpperLeg.R"): wl}
def robe_pt(r0, r1, zhem, ragged, phase, fold):
    def fn(r, c):
        a = math.radians(14 + c * (360 - 28))
        z = 1.04 + r * (zhem - 1.04)
        saw = (math.sin(c * 46 + phase) * 0.5 + 0.5) ** 2
        z -= 0 if r < 0.7 else (r - 0.7) / 0.3 * ragged * saw
        rad = r0 + (r1 - r0) * (r ** 1.4) + fold * math.sin(c * 33 + phase) * r
        return Vector((rad * math.sin(a), -rad * math.cos(a), z))
    return fn
skinned(arm, "Hero_RobeUnder", strip(12, 64, robe_pt(0.19, 0.31, 0.16, 0.07, 0.0, 0.010)), M_CLOTH2, robe_w)
skinned(arm, "Hero_RobeMid",   strip(12, 64, robe_pt(0.205, 0.34, 0.23, 0.09, 1.7, 0.012)), M_CLOTH, robe_w)
skinned(arm, "Hero_RobeOuter", strip(12, 64, robe_pt(0.22, 0.37, 0.33, 0.10, 3.1, 0.014)), M_CLOTH, robe_w)
def band(r, c):
    a = math.radians(-8 + c * 16)
    rad = 0.227 + 0.15 * (r ** 1.4) + 0.006
    return Vector((rad * math.sin(a), -rad * math.cos(a), 1.04 + r * (0.36 - 1.04)))
skinned(arm, "Hero_RobeBand", strip(14, 5, band), M_BAND, robe_w)
bm = bmesh.new(); uvf = {}                                                           # hem fringe: many frayed strips
fr = robe_pt(0.22, 0.37, 0.33, 0.10, 3.1, 0.014)
for k in range(90):
    c = k / 89.0
    p = fr(1.0, c)
    ln = random.uniform(0.04, 0.10)
    feather(bm, uvf, p, (p.x * 1.5, p.y * 1.5, -1.0), ln, 0.012, curl=0.05, rows=3)
assign_uv(bm, uvf)
skinned(arm, "Hero_Fringe", bm, M_CLOTH, robe_w)

# ---------- bone net shawl, beads, sash, fate-talon ----------
bm = bmesh.new()
rows = ((1.455, 0.215, 0.135), (1.395, 0.235, 0.15), (1.335, 0.25, 0.16)); N = 20
for ri, (z, rx, ry) in enumerate(rows):
    pts = []
    for k in range(N):
        a = 2 * math.pi * k / N
        pts.append(Vector((rx * math.sin(a), -0.043 - ry * math.cos(a), z + (0.03 if k % 2 == 0 else -0.03))))
    for k in range(N):
        tube(bm, pts[k], pts[(k + 1) % N], 0.0085, 0.0085, seg=5)
        ell(bm, pts[k], (0.015, 0.015, 0.015), seg=6, rings=4)
        if ri == len(rows) - 1 and k % 2 == 1:
            cone(bm, pts[k], (0, 0, -1), 0.009, 0.10, seg=5)
            ell(bm, pts[k] + Vector((0, 0, -0.07)), (0.012, 0.012, 0.018), seg=6, rings=4)
for ri in range(len(rows) - 1):
    for k in range(0, N, 2):
        a = 2 * math.pi * k / N
        z0, rx0, ry0 = rows[ri]; z1, rx1, ry1 = rows[ri + 1]
        tube(bm, Vector((rx0 * math.sin(a), -0.043 - ry0 * math.cos(a), z0 - 0.03)), Vector((rx1 * math.sin(a), -0.043 - ry1 * math.cos(a), z1 + 0.03)), 0.007, 0.007, seg=4)
attach(arm, "Hero_BoneNet", bm, M_BONE, "Chest")
bm = bmesh.new()
for k in range(16):
    a = math.radians(-72 + k * 144 / 15)
    ell(bm, (0.125 * math.sin(a), -0.043 - 0.125 * math.cos(a) - 0.06, 1.44 - 0.03 * math.cos(a * 1.3)), (0.014, 0.014, 0.014), seg=6, rings=4)
cone(bm, (0, -0.19, 1.415), (0, -0.2, -1), 0.015, 0.07, seg=6)
attach(arm, "Hero_Beads", bm, M_BONE, "Chest")
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=28, radius1=0.246, radius2=0.236, depth=0.10, matrix=Matrix.Translation((0, -0.043, 1.04)))
for k in range(7):
    x = -0.075 + k * 0.025
    cone(bm, (x, -0.257, 1.0), (0, 0, -1), 0.007, 0.08 + 0.025 * (k % 2), seg=4)
    ell(bm, (x, -0.257, 0.90 - 0.025 * (k % 2)), (0.01, 0.01, 0.014), seg=5, rings=3)
attach(arm, "Hero_Sash", bm, M_BAND, "Hips")
bm = bmesh.new()
tube(bm, (0.17, -0.24, 0.98), (0.19, -0.26, 0.86), 0.024, 0.017, seg=6)
tube(bm, (0.19, -0.26, 0.86), (0.175, -0.28, 0.77), 0.017, 0.005, seg=6)
ell(bm, (0.17, -0.24, 0.99), (0.028, 0.028, 0.028), seg=6, rings=4)
for k, dx in enumerate((-0.028, 0.0, 0.028)):
    cone(bm, (0.17 + dx, -0.24, 0.97), (dx * 3, 0, -1), 0.007, 0.11 + 0.02 * k, seg=4)
attach(arm, "Hero_FateTalon", bm, M_BONE, "Hips")

# ---------- bird legs (scaled tarsus, backward-looking knee) and talons ----------
for side, foot in ((1, "Foot.L"), (-1, "Foot.R")):
    fx, fy = side * 0.121, -0.062
    bm = bmesh.new(); uvl = {}
    # tarsus as a UV'd lofted tube so the scale texture shows
    def tars(r, c, fx=fx, fy=fy):
        a = 2 * math.pi * c
        z = 0.06 + r * 0.30
        rad = 0.016 + 0.010 * r
        return Vector((fx + rad * math.cos(a), fy + 0.02 * r + rad * math.sin(a), z))
    tb = strip(8, 10, tars)
    attach(arm, "Hero_Tarsus_" + ("L" if side > 0 else "R"), tb, M_LEG, foot)
    bm = bmesh.new()
    ell(bm, (fx, fy + 0.02, 0.37), (0.030, 0.030, 0.026), seg=8, rings=5)                  # knee joint
    ell(bm, (fx, fy + 0.012, 0.075), (0.026, 0.030, 0.028), seg=8, rings=5)                # ankle
    cone(bm, (fx, fy + 0.03, 0.12), (0, 1, 0.2), 0.009, 0.05, seg=4)                       # heel spur
    for dx, ln in ((-0.055, 0.17), (0.0, 0.21), (0.055, 0.17)):                            # three forward toes, jointed
        tip = Vector((fx + dx * 1.4, fy - ln, 0.02)); mid = Vector((fx + dx * 0.9, fy - ln * 0.5, 0.032))
        tube(bm, Vector((fx, fy - 0.01, 0.06)), mid, 0.016, 0.013)
        tube(bm, mid, tip, 0.013, 0.010)
        ell(bm, mid, (0.016, 0.016, 0.014), seg=6, rings=4)
        tube(bm, tip, tip + Vector((dx * 0.5, -0.03, -0.012)), 0.010, 0.004, seg=4)       # curved talon, two segments
        tube(bm, tip + Vector((dx * 0.5, -0.03, -0.012)), tip + Vector((dx * 0.8, -0.05, -0.04)), 0.004, 0.0015, seg=4)
    tip = Vector((fx, fy + 0.11, 0.02))                                                    # hallux
    tube(bm, Vector((fx, fy + 0.01, 0.06)), tip, 0.014, 0.01)
    tube(bm, tip, tip + Vector((0, 0.03, -0.02)), 0.010, 0.002, seg=4)
    attach(arm, "Hero_Talons_" + ("L" if side > 0 else "R"), bm, M_TALON, foot)

print("GC_TOTAL_TRIS", tri_count())
bpy.ops.wm.save_as_mainfile(filepath=OUT + "/grimcrow.blend")
bpy.ops.export_scene.gltf(filepath=OUT + "/grimcrow.glb", export_format='GLB', export_apply=True,
                          export_animations=False, export_skins=True)
print("GC_DONE")
