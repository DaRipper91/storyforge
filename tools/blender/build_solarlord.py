"""Solar-Lord hero: eagle-headed celestial in gold-ivory feathermail on the primal shared-skeleton base (Blender 5.x).
Run: blender -b -P build_solarlord.py -- <primal.glb> <out_dir>
Eagle head (hooked beak, brow ridge, shingled head feathers, gold crest), feathermail torso rows, sun emblems, gold pauldrons,
feathered arms with vambraces and taloned hands, folded wings, feather skirt layers and tabard, thinned scaled bird legs with talons."""
import bpy, bmesh, math, sys, os, random
import numpy as np
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hero_common import *
import hero_textures as T

SRC, OUT = sys.argv[-2], sys.argv[-1]
random.seed(11)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
remove_objects("_Head", "_Feet")
TEX = os.path.join(OUT, "tex_sl")
GOLD = np.array([0.85, 0.58, 0.16], np.float32); IVORY = np.array([0.80, 0.72, 0.56], np.float32)


def rgba(col):
    return np.concatenate([col, np.ones(col.shape[:2] + (1,), np.float32)], -1)


# ---------- textures ----------
def feather_tex(name, rim, tip, seed):
    n = 256; x, y = T._grid(n)
    u = np.abs(x - 0.5) * 2
    barb = 0.5 + 0.5 * np.sin((y * 22 + u * 12) * np.pi)
    rib = np.exp(-((x - 0.5) / 0.02) ** 2)
    nz = T.fbm(n, seed, 4, 6)
    base = IVORY[None, None, :] * (0.82 + 0.28 * barb[..., None]) * (0.9 + 0.2 * nz[..., None])
    gold_amt = np.clip(tip * T.smooth(0.45, 1.0, y) + rim * T.smooth(0.55, 1.0, u) + 0.35 * rib, 0, 1)
    gold = GOLD[None, None, :] * (0.7 + 0.45 * barb[..., None])
    col = base * (1 - gold_amt[..., None]) + gold * gold_amt[..., None]
    col += rib[..., None] * 0.08
    h = 0.6 * barb + 0.9 * rib
    return (T.to_image(name + "_diffuse", rgba(np.clip(col, 0, 1)), TEX), T.to_image(name + "_normal", T.normal_from_height(h, 1.5), TEX, "Non-Color"))


def leg_tex():
    n = 256; e, cid = T.voronoi(n, 7, 3); cell = T.smooth(0.0, 0.3, e)
    col = np.array([0.55, 0.40, 0.17], np.float32)[None, None, :] * (0.65 + 0.7 * cid[..., None]) * (0.45 + 0.55 * cell[..., None])
    return (T.to_image("legscale_diffuse", rgba(col), TEX), T.to_image("legscale_normal", T.normal_from_height(cell, 2.0), TEX, "Non-Color"))


def tabard_tex():
    n = 512; x, y = T._grid(n); nz = T.fbm(n, 21, 5, 6)
    col = IVORY[None, None, :] * (0.85 + 0.25 * nz[..., None])
    edge = (np.abs(x - 0.5) > 0.42) | (y > 0.94 - np.abs(x - 0.5) * 0.0) | (np.abs(x - 0.5) < 0.012)
    cx, cy = 0.5, 0.2
    d = np.hypot(x - cx, (y - cy) * 1.0)
    ang = np.arctan2(y - cy, x - cx)
    rays = (d > 0.07) & (d < 0.18 * (0.6 + 0.4 * np.abs(np.cos(ang * 6)) ** 3))
    sun = (d < 0.06) | rays | (np.abs(d - 0.085) < 0.006)
    k = (edge | sun)[..., None]
    col = col * (1 - k) + GOLD[None, None, :] * (0.8 + 0.3 * nz[..., None]) * k
    return T.to_image("tabard_diffuse", rgba(np.clip(col, 0, 1)), TEX), T.to_image("tabard_normal", T.normal_from_height(0.4 * nz + 0.8 * k[..., 0], 1.0), TEX, "Non-Color")


def cloth_tex():
    n = 256; x, y = T._grid(n); nz = T.fbm(n, 8, 5, 6); weave = 0.5 + 0.5 * np.sin(x * n * 0.7) * np.sin(y * n * 0.7)
    col = IVORY[None, None, :] * 0.8 * (0.8 + 0.3 * nz[..., None]) * (0.92 + 0.08 * weave[..., None])
    return T.to_image("cloth_diffuse", rgba(col), TEX), T.to_image("cloth_normal", T.normal_from_height(0.5 * weave + 0.3 * nz, 1.0), TEX, "Non-Color")


def gold_tex():
    n = 256; x, y = T._grid(n); nz = T.fbm(n, 31, 5, 6)
    fx, fy = (x * 8) % 1.0, (y * 8) % 1.0
    eng = (np.abs(np.abs(fx - 0.5) + np.abs(fy - 0.5) - 0.32) < 0.03)
    col = GOLD[None, None, :] * (0.8 + 0.3 * nz[..., None]) * (1 - 0.35 * eng[..., None])
    return T.to_image("gold_diffuse", rgba(np.clip(col, 0, 1)), TEX), T.to_image("gold_normal", T.normal_from_height(0.3 * nz - 0.7 * eng, 1.2), TEX, "Non-Color")


fiv = feather_tex("fivory", 0.25, 0.35, 2)
fmail = feather_tex("fmail", 0.95, 0.55, 3)
fgold = feather_tex("fgold", 0.9, 1.0, 4)
li, ln_ = leg_tex(); ti, tn = tabard_tex(); ci, cn = cloth_tex(); gi, gn = gold_tex()

# ---------- materials ----------
M_FIV = mat("SL_FeatherIvory", (0.8, 0.72, 0.56), 0.5, 0.0)
M_MAIL = mat("SL_Feathermail", (0.8, 0.7, 0.5), 0.35, 0.25)
M_FGOLD = mat("SL_FeatherGold", (0.85, 0.58, 0.16), 0.3, 0.5)
M_GOLD = mat("SL_Gold", (0.85, 0.58, 0.16), 0.28, 1.0)
M_CLOTH = mat("SL_Cloth", (0.8, 0.72, 0.56), 0.9)
M_TAB = mat("SL_Tabard", (0.8, 0.72, 0.56), 0.8)
M_SKIN = mat("SL_Leg", (0.55, 0.40, 0.17), 0.45, 0.1)
M_BEAK = mat("SL_Beak", (0.9, 0.62, 0.12), 0.25, 0.3)
M_EYE = mat("SL_Eye", (0.95, 0.7, 0.1), 0.1, 0.0, emit=(1.0, 0.7, 0.1), strength=0.8)
M_PUPIL = mat("SL_Pupil", (0.01, 0.01, 0.01), 0.1)
M_TALON = mat("SL_Talon", (0.09, 0.08, 0.07), 0.3, 0.5)
M_SUN = mat("SL_SunGlow", (1.0, 0.8, 0.3), 0.3, 0.8, emit=(1.0, 0.7, 0.2), strength=1.2)
T.bind(M_FIV, *fiv); T.bind(M_MAIL, *fmail); T.bind(M_FGOLD, *fgold); T.bind(M_CLOTH, ci, cn)
T.bind(M_TAB, ti, tn); T.bind(M_SKIN, li, ln_); T.bind(M_GOLD, gi, gn)

# base body/legs: own material, no vertex-coloured generic look
for _o in bpy.data.objects:
    if _o.type == "MESH" and _o.name.endswith(("_Body", "_Legs")):
        _o.data.materials.clear(); _o.data.materials.append(M_SKIN)
        for p in _o.data.polygons: p.material_index = 0
        if _o.name.endswith("_Legs"):        # thin the shins into avian tarsi (pull toward the leg axis below the knee)
            mw = _o.matrix_world; mi = mw.inverted()
            for v in _o.data.vertices:
                w = mw @ v.co
                f = 1.0 - 0.58 * smoothstep(0.62, 0.40, w.z)
                if f < 1.0:
                    cx = 0.12 if w.x >= 0 else -0.12
                    w.x = cx + (w.x - cx) * f; w.y = -0.075 + (w.y + 0.075) * f
                    v.co = mi @ w
            _o.data.update()


# ---------- feather card ----------
def feather(bm, uvm, root, direction, length, width, curl=0.25, rows=4):
    d = Vector(direction).normalized(); up = Vector((0, 0, 1))
    side = d.cross(up)
    if side.length < 1e-3: side = Vector((1, 0, 0))
    side.normalize(); nrm = side.cross(d).normalized()
    vs = []
    for r in range(rows):
        t = r / (rows - 1)
        pos = Vector(root) + d * length * t + nrm * (curl * length * t * t)
        w = width * (math.sin(min(1.0, 0.25 + t * 0.9) * math.pi / 2)) * (1 - t ** 2.2)
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


def ring(bm, uv, cz, rx, ry, n, ln, wd, sag, rot=0.0, jit=0.12, cy=-0.043, out=0.6, skip=None, rows=4):
    for k in range(n):
        a = 2 * math.pi * k / n + rot
        if skip and skip(a): continue
        p = Vector((rx * math.sin(a), cy - ry * math.cos(a), cz))
        d = Vector((math.sin(a) * out, -math.cos(a) * out, -sag + random.uniform(-jit, jit)))
        feather(bm, uv, p, d, ln * random.uniform(0.92, 1.12), wd, rows=rows)


def sun(bm, c, r, rays=12, ray_len=1.0, spike=True):
    """Sun emblem facing -Y: boss + radiating rays (in the XZ plane) centred at c."""
    c = Vector(c)
    ell(bm, c, (r * 0.55, r * 0.22, r * 0.55), seg=14, rings=8)
    for k in range(rays):
        a = 2 * math.pi * k / rays
        dirv = Vector((math.sin(a), 0, math.cos(a)))
        cone(bm, c + dirv * r * 0.5, dirv, r * 0.16, r * ray_len * (1.0 if k % 2 == 0 else 0.7), seg=4)
    # rim ring
    for k in range(20):
        a0, a1 = 2 * math.pi * k / 20, 2 * math.pi * (k + 1) / 20
        tube(bm, c + Vector((math.sin(a0), 0, math.cos(a0))) * r * 0.62, c + Vector((math.sin(a1), 0, math.cos(a1))) * r * 0.62, r * 0.045, r * 0.045, seg=4)


# ---------- eagle head ----------
HC = Vector((0, -0.075, 1.635))
bm = bmesh.new()
ell(bm, HC, (0.082, 0.105, 0.088), seg=16, rings=10)
ell(bm, (0, -0.03, 1.60), (0.070, 0.075, 0.066), seg=12, rings=8)
ell(bm, (0, -0.04, 1.535), (0.040, 0.040, 0.065), seg=10, rings=6)       # neck column
for sx in (1, -1):
    ell(bm, (sx * 0.060, -0.125, 1.652), (0.034, 0.036, 0.020), rot=(0, sx * 0.4, 0), seg=10, rings=6)   # heavy brow ridge
attach(arm, "Hero_EagleHead", bm, M_FIV, "Head")
bm = bmesh.new(); uv = {}
for el in range(-2, 7):                                                    # shingled head feathers over the skull (skip the face)
    e = math.radians(el * 14 + 5)
    nph = max(6, int(22 * math.cos(e)))
    for k in range(nph):
        ph = 2 * math.pi * (k + 0.5 * (el % 2)) / nph
        if abs(math.sin(ph)) < 0.62 and math.cos(ph) > 0 and el < 3: continue   # front sector reserved for the face
        p = HC + Vector((0.086 * math.cos(e) * math.sin(ph), -0.108 * math.cos(e) * math.cos(ph), 0.092 * math.sin(e)))
        dd = Vector((math.sin(ph) * 0.4, 0.95 + 0.3 * math.sin(e), -0.5 - 0.3 * math.cos(e)))
        feather(bm, uv, p, dd, 0.055, 0.026, curl=0.3, rows=3)
for k in range(9):                                                         # throat / cheek feathers hanging
    a = math.radians(-70 + k * 17.5)
    feather(bm, uv, Vector((0.07 * math.sin(a), -0.12 - 0.02 * math.cos(a), 1.575)), (math.sin(a) * 0.5, -0.3, -1.0), 0.06, 0.024, rows=3)
assign_uv(bm, uv); attach(arm, "Hero_HeadFeathers", bm, M_FIV, "Head")
bm = bmesh.new(); uv = {}
for i in range(9):                                                         # gold crest swept back
    for sx in (-1, 0, 1):
        root = Vector((sx * 0.045 * (1 - i * 0.08), -0.10 + i * 0.024, 1.712 - i * 0.012))
        feather(bm, uv, root, (sx * 0.3, 0.85, 0.42 - i * 0.06), 0.11 + i * 0.012, 0.026, curl=0.35)
for sx in (1, -1):
    for j in range(5):
        feather(bm, uv, Vector((sx * 0.085, -0.10 + j * 0.025, 1.66)), (sx * 0.5, 0.8, 0.15), 0.10, 0.024, curl=0.3)
assign_uv(bm, uv); attach(arm, "Hero_Crest", bm, M_FGOLD, "Head")
bm = bmesh.new()                                                           # hooked beak
tube(bm, (0, -0.16, 1.652), (0, -0.22, 1.652), 0.046, 0.036, seg=8)
tube(bm, (0, -0.22, 1.652), (0, -0.28, 1.636), 0.036, 0.024, seg=8)
tube(bm, (0, -0.28, 1.636), (0, -0.318, 1.602), 0.024, 0.011, seg=7)
tube(bm, (0, -0.318, 1.602), (0, -0.312, 1.566), 0.011, 0.003, seg=6)
tube(bm, (0, -0.16, 1.616), (0, -0.23, 1.610), 0.034, 0.022, seg=8)
tube(bm, (0, -0.23, 1.610), (0, -0.285, 1.602), 0.022, 0.010, seg=6)
           # mouth line seam
attach(arm, "Hero_Beak", bm, M_BEAK, "Head")
bm = bmesh.new()
for sx in (1, -1):
    ell(bm, (sx * 0.074, -0.135, 1.645), (0.0185, 0.014, 0.0165), seg=10, rings=6)
attach(arm, "Hero_Eyes", bm, M_EYE, "Head")
bm = bmesh.new()
for sx in (1, -1):
    ell(bm, (sx * 0.0765, -0.1445, 1.645), (0.007, 0.006, 0.0085), seg=6, rings=4)
    ell(bm, (sx * 0.069, -0.123, 1.652), (0.026, 0.012, 0.024), seg=8, rings=5)
attach(arm, "Hero_EyePupils", bm, M_PUPIL, "Head")

# ---------- neck ruff, shoulder pauldrons ----------
bm = bmesh.new(); uv = {}
for i, (z, rad, n, ln) in enumerate(((1.56, 0.075, 14, 0.07), (1.53, 0.098, 16, 0.085), (1.50, 0.12, 18, 0.10), (1.47, 0.14, 20, 0.11))):
    ring(bm, uv, z, rad, rad, n, ln, 0.03 + i * 0.004, 0.9, rot=i * 0.17, rows=3)
assign_uv(bm, uv); attach(arm, "Hero_NeckRuff", bm, M_FIV, "Neck")
for side, bone, tag in ((1, "UpperArm.L", "L"), (-1, "UpperArm.R", "R")):
    bm = bmesh.new(); uv = {}
    for layer, (x0, z0, ln, wd) in enumerate(((0.09, 1.50, 0.12, 0.04), (0.14, 1.495, 0.13, 0.042), (0.19, 1.485, 0.14, 0.044), (0.25, 1.47, 0.14, 0.044), (0.30, 1.455, 0.13, 0.04))):
        for k in range(7):
            yy = -0.06 + (k - 3) * 0.030
            feather(bm, uv, Vector((side * x0, yy + 0.0, z0 + 0.03 * (1 - abs(k - 3) / 3.0))), (side * 0.6, 0.05 * (k - 3), -0.75), ln, wd, curl=0.2)
    assign_uv(bm, uv); attach(arm, "Hero_Pauldron_" + tag, bm, M_FGOLD, bone)

# ---------- torso: tunic + feathermail rows + sun emblem ----------
def tw(co):
    ch = smoothstep(1.18, 1.32, co.z); tq = smoothstep(1.02, 1.1, co.z) * (1 - ch)
    return {"Chest": ch, "Torso": tq, "Hips": max(0.0, 1.0 - ch - tq)}


def tunic(r, c):
    a = 2 * math.pi * c; z = 1.47 - r * 0.50
    return Vector(((0.165 + 0.02 * r) * math.sin(a), -0.043 - (0.135 + 0.02 * r) * math.cos(a), z))
skinned(arm, "Hero_Tunic", strip(8, 28, tunic), M_CLOTH, tw)
bm = bmesh.new(); uv = {}
for i in range(9):
    z = 1.455 - i * 0.050
    rx = 0.185 + 0.012 * i * 0.5; ry = 0.152 + 0.01 * i * 0.5
    ring(bm, uv, z, rx, ry, 22 if i < 5 else 24, 0.085 + 0.004 * i, 0.034, 0.95, rot=0.14 * i, out=0.35)
assign_uv(bm, uv); skinned(arm, "Hero_Feathermail", bm, M_MAIL, tw)
bm = bmesh.new()
sun(bm, (0, -0.245, 1.355), 0.085)
attach(arm, "Hero_ChestSun", bm, M_GOLD, "Chest")
bm = bmesh.new()                                                           # gorget / collar rim
for k in range(24):
    a0, a1 = 2 * math.pi * k / 24, 2 * math.pi * (k + 1) / 24
    for rr, zz in ((0.115, 1.47),):
        tube(bm, (rr * math.sin(a0), -0.043 - rr * 0.9 * math.cos(a0), zz), (rr * math.sin(a1), -0.043 - rr * 0.9 * math.cos(a1), zz), 0.011, 0.011, seg=4)
attach(arm, "Hero_Collar", bm, M_GOLD, "Chest")

# belt, buckle, hip plates
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=28, radius1=0.230, radius2=0.222, depth=0.07, matrix=Matrix.Translation((0, -0.043, 1.07)))
for sx in (1, -1):
    ell(bm, (sx * 0.12, -0.19, 1.07), (0.03, 0.012, 0.03), seg=8, rings=5)
sun(bm, (0, -0.268, 1.07), 0.065, rays=8)
attach(arm, "Hero_Belt", bm, M_GOLD, "Hips")

# ---------- skirt: ivory cloth under-layer, three feather rows, long tabard, back panel ----------
def skw(co):
    t = smoothstep(1.0, 0.4, co.z)
    front = max(0.0, -co.y / max(1e-6, math.hypot(co.x, co.y)))
    wl = t * (0.25 + 0.6 * front)
    return {"Hips": 1.0 - wl, ("UpperLeg.L" if co.x >= 0 else "UpperLeg.R"): wl}


def skirt_pt(r0, r1, zhem, ph):
    def fn(r, c):
        a = math.radians(10 + c * 340)
        z = 1.05 + r * (zhem - 1.05); rad = r0 + (r1 - r0) * (r ** 1.4) + 0.008 * math.sin(c * 30 + ph) * r
        return Vector((rad * math.sin(a), -0.04 - rad * math.cos(a), z))
    return fn
skinned(arm, "Hero_SkirtUnder", strip(10, 40, skirt_pt(0.19, 0.25, 0.40, 0.0)), M_CLOTH, skw)
bm = bmesh.new(); uv = {}
for i, (z, rr, n, ln) in enumerate(((1.0, 0.215, 24, 0.16), (0.90, 0.226, 26, 0.17), (0.80, 0.236, 26, 0.18), (0.70, 0.246, 26, 0.18), (0.60, 0.255, 26, 0.18), (0.50, 0.262, 26, 0.17))):
    skirt_f = lambda a: False
    ring(bm, uv, z, rr, rr * 0.98, n, ln, 0.05, 1.0, rot=i * 0.21, out=0.22, jit=0.06, rows=4)
assign_uv(bm, uv); skinned(arm, "Hero_SkirtFeathers", bm, M_FIV, skw)
bm = bmesh.new(); uv = {}                                                  # gold-tipped outer feathers along the sides
for i, z in enumerate((0.95, 0.82, 0.69, 0.56)):
    for sx in (1, -1):
        for k in range(3):
            a = math.radians(sx * (70 + 12 * k))
            rr = 0.24 + 0.014 * i
            feather(bm, uv, Vector((rr * math.sin(a), -0.04 - rr * math.cos(a), z)), (math.sin(a) * 0.25, -math.cos(a) * 0.25, -1), 0.21, 0.045)
assign_uv(bm, uv); skinned(arm, "Hero_SkirtGold", bm, M_FGOLD, skw)


def tabard_fn(r, c):                                                       # long front panel, pointed tip
    w = 0.09 * (1 - 0.0 * r) * (1 - max(0.0, (r - 0.82) / 0.18))
    return Vector(((c - 0.5) * 2 * max(w, 0.0), -0.268 - 0.045 * r * r, 1.03 - r * 0.58))
skinned(arm, "Hero_Tabard", strip(14, 3, tabard_fn), M_TAB, skw)
bm = bmesh.new()                                                           # gold edge trim down the tabard sides
for sx in (1, -1):
    for i in range(13):
        r0, r1 = i / 13, (i + 1) / 13
        w0 = 0.09 * (1 - max(0.0, (r0 - 0.82) / 0.18)); w1 = 0.09 * (1 - max(0.0, (r1 - 0.82) / 0.18))
        tube(bm, (sx * w0, -0.272 - 0.045 * r0 * r0, 1.03 - r0 * 0.58), (sx * w1, -0.272 - 0.045 * r1 * r1, 1.03 - r1 * 0.58), 0.007, 0.007, seg=4)
skinned(arm, "Hero_TabardTrim", bm, M_GOLD, skw)
bm = bmesh.new(); uv = {}                                                  # long back feathers (tail-coverts)
for k in range(9):
    x = (k - 4) * 0.05
    feather(bm, uv, Vector((x, 0.19 - 0.01 * abs(k - 4), 0.95)), (x * 0.5, 0.18, -1.0), 0.55 - 0.03 * abs(k - 4), 0.058, curl=0.1, rows=6)
assign_uv(bm, uv); skinned(arm, "Hero_BackFeathers", bm, M_FIV, skw)

# ---------- wings (folded) ----------
for side, tag in ((1, "L"), (-1, "R")):
    bm = bmesh.new(); uv = {}
    rows = ((8, 0.30, 0.075, 1.0), (8, 0.48, 0.085, 1.0), (7, 0.66, 0.09, 1.0), (6, 0.82, 0.095, 1.0))
    for j, (cnt, ln, wd, _) in enumerate(rows):
        for k in range(cnt):
            t = k / max(1, cnt - 1)
            root = Vector((side * (0.11 + 0.20 * t), 0.115 + 0.02 * j, 1.48 - 0.04 * t))
            ang = math.radians(-8 + 9 * t + 2 * j)
            dd = Vector((side * math.sin(ang), 0.14 + 0.04 * j, -math.cos(ang)))
            feather(bm, uv, root, dd, ln * (0.85 + 0.25 * (1 - abs(t - 0.5) * 2)) * (1.0 + 0.08 * t), wd, curl=0.12, rows=6)
    assign_uv(bm, uv); attach(arm, "Hero_Wing_" + tag, bm, M_FIV, "Chest")
    bm = bmesh.new(); uv = {}
    for k in range(7):                                                     # gold-tipped primaries
        t = k / 6.0
        root = Vector((side * (0.12 + 0.19 * t), 0.19, 1.47 - 0.05 * t))
        ang = math.radians(-6 + 9 * t)
        feather(bm, uv, root, (side * math.sin(ang), 0.16, -math.cos(ang)), 0.86 + 0.05 * t, 0.07, curl=0.1, rows=6)
    assign_uv(bm, uv); attach(arm, "Hero_WingPrimaries_" + tag, bm, M_FGOLD, "Chest")
    bm = bmesh.new()                                                       # wing bar (leading edge) in gold
    tube(bm, (side * 0.10, 0.10, 1.50), (side * 0.30, 0.13, 1.47), 0.026, 0.02, seg=6)
    attach(arm, "Hero_WingBar_" + tag, bm, M_FGOLD, "Chest")

# ---------- arms: feather sleeves, vambraces, taloned hands ----------
for side, tag, up, lo in ((1, "L", "UpperArm.L", "LowerArm.L"), (-1, "R", "UpperArm.R", "LowerArm.R")):
    def aw(co, up=up, lo=lo):
        t = smoothstep(0.30, 0.36, abs(co.x)); return {up: 1.0 - t, lo: t}
    bm = bmesh.new(); uv = {}
    for i in range(10):
        x = side * (0.19 + i * 0.041)
        r = 0.058 + (0.012 if i < 4 else 0.0)
        for k in range(8):
            a = 2 * math.pi * k / 8 + i * 0.4
            yc = -0.06 - 0.03 * (i / 9.0) * 1.0
            root = Vector((x, yc + r * math.sin(a), 1.43 + r * math.cos(a)))
            dd = Vector((side * 1.0, 0.45 * math.sin(a), 0.45 * math.cos(a) - 0.08))
            feather(bm, uv, root, dd, 0.085, 0.034, curl=0.2, rows=3)
    assign_uv(bm, uv); skinned(arm, "Hero_ArmFeathers_" + tag, bm, M_FIV, aw)

    def vam(r, c, side=side):
        a = 2 * math.pi * c; x = 0.40 + r * 0.16
        rad = 0.060 + 0.012 * math.sin(r * math.pi) + 0.004
        return Vector((side * x, -0.075 - 0.03 * (x - 0.33) / 0.24 + rad * math.sin(a), 1.43 + rad * math.cos(a)))
    skinned(arm, "Hero_Vambrace_" + tag, strip(6, 14, vam), M_GOLD, aw)

    def cuff(r, c, side=side):
        a = 2 * math.pi * c; x = 0.205 + r * 0.05
        rad = 0.062 + 0.012 * math.sin(r * math.pi)
        return Vector((side * x, -0.06 + rad * math.sin(a), 1.43 + rad * math.cos(a)))
    skinned(arm, "Hero_ArmCuff_" + tag, strip(4, 12, cuff), M_GOLD, aw)
    bm = bmesh.new()                                                       # talons on each finger plus thumb, scaly knuckle plates
    for yy, zz, dx in ((-0.12, 1.45, 0.0), (-0.09, 1.45, 0.02), (-0.06, 1.45, 0.0), (-0.03, 1.45, -0.02)):
        tip = Vector((side * (0.81 + dx), yy, zz))
        tube(bm, tip, tip + Vector((side * 0.04, 0, -0.025)), 0.009, 0.005, seg=5)
        tube(bm, tip + Vector((side * 0.04, 0, -0.025)), tip + Vector((side * 0.06, 0, -0.065)), 0.005, 0.0012, seg=4)
        ell(bm, tip - Vector((side * 0.06, 0, 0)), (0.013, 0.011, 0.011), seg=6, rings=4)
    tip = Vector((side * 0.70, -0.18, 1.40))
    tube(bm, tip, tip + Vector((side * 0.03, -0.01, -0.03)), 0.009, 0.0012, seg=4)
    ell(bm, (side * 0.62, -0.09, 1.465), (0.05, 0.045, 0.012), seg=8, rings=4)   # hand-back plate
    attach(arm, "Hero_Talons_" + ("Hand" + tag), bm, M_TALON, "Hand." + tag)

# ---------- legs: gold-scaled tarsus wraps, ankle fur, talons ----------
for side, foot, tag in ((1, "Foot.L", "L"), (-1, "Foot.R", "R")):
    fx, fy = side * 0.121, -0.062

    def tars(r, c, fx=fx, fy=fy):
        a = 2 * math.pi * c; z = 0.06 + r * 0.34; rad = 0.03 - 0.008 * r + 0.006 * math.sin(r * 14)
        return Vector((fx + rad * math.cos(a), -0.078 + 0.016 * r + rad * math.sin(a), z))
    skinned(arm, "Hero_Tarsus_" + tag, strip(14, 10, tars), M_SKIN, lambda co, tg=tag: {("LowerLeg." + tg): 0.5 + 0.5 * smoothstep(0.1, 0.35, co.z), ("Foot." + tg): 0.5 * (1 - smoothstep(0.1, 0.35, co.z))})
    bm = bmesh.new(); uv = {}                                              # feathered thigh-trousers tufts above the knee
    for i, z in enumerate((0.47, 0.41)):
        for k in range(10):
            a = 2 * math.pi * k / 10
            feather(bm, uv, Vector((fx + 0.035 * math.cos(a), -0.082 + 0.035 * math.sin(a), z)), (0.25 * math.cos(a), 0.25 * math.sin(a), -1), 0.11, 0.032, rows=3)
    assign_uv(bm, uv); attach(arm, "Hero_Spats_" + tag, bm, M_FIV, "LowerLeg." + tag)
    bm = bmesh.new()
    ell(bm, (fx, fy + 0.012, 0.075), (0.032, 0.034, 0.030), seg=8, rings=5)
    ell(bm, (fx, -0.075, 0.395), (0.036, 0.036, 0.020), seg=8, rings=4)
    cone(bm, (fx, fy + 0.03, 0.12), (0, 1, 0.2), 0.009, 0.05, seg=4)
    for dx, ln in ((-0.06, 0.18), (0.0, 0.23), (0.06, 0.18)):
        tip = Vector((fx + dx * 1.4, fy - ln, 0.02)); mid = Vector((fx + dx * 0.9, fy - ln * 0.5, 0.034))
        tube(bm, Vector((fx, fy - 0.01, 0.06)), mid, 0.019, 0.015)
        tube(bm, mid, tip, 0.015, 0.012)
        ell(bm, mid, (0.019, 0.019, 0.016), seg=6, rings=4)
        tube(bm, tip, tip + Vector((dx * 0.5, -0.035, -0.012)), 0.012, 0.005, seg=4)
        tube(bm, tip + Vector((dx * 0.5, -0.035, -0.012)), tip + Vector((dx * 0.8, -0.06, -0.045)), 0.005, 0.0015, seg=4)
    tip = Vector((fx, fy + 0.11, 0.02))
    tube(bm, Vector((fx, fy + 0.01, 0.06)), tip, 0.016, 0.011)
    tube(bm, tip, tip + Vector((0, 0.035, -0.02)), 0.011, 0.002, seg=4)
    attach(arm, "Hero_Feet_" + tag, bm, M_SKIN, foot)
    bm = bmesh.new()                                                       # talon tips in dark horn
    for dx, ln in ((-0.06, 0.18), (0.0, 0.23), (0.06, 0.18)):
        tip = Vector((fx + dx * 1.4, fy - ln, 0.02))
        tube(bm, tip + Vector((dx * 0.5, -0.035, -0.012)), tip + Vector((dx * 0.8, -0.06, -0.045)), 0.0056, 0.0016, seg=4)
    attach(arm, "Hero_Claws_" + tag, bm, M_TALON, foot)

print("SL_TOTAL_TRIS", tri_count())
bpy.ops.wm.save_as_mainfile(filepath=OUT + "/solarlord.blend")
bpy.ops.export_scene.gltf(filepath=OUT + "/solarlord.glb", export_format='GLB', export_apply=True,
                          export_animations=False, export_skins=True)
print("SL_DONE")
