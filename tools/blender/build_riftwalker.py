"""Riftwalker hero: weathered planar voyager in a layered Rift-Fold cloak on the cosmic shared-skeleton base (Blender 5.x).
Run: blender -b -P build_riftwalker.py -- <cosmic.glb> <out_dir>
Sculpted older male face with grey wavy hair, beard, braids and ponytail; stand collar; slate-blue tunic with pointed layered panels
and bronze arc embroidery; three-layer pointed-hem cloak with pearlescent edges and a ring-and-crystal clasp; crossed belts, pouch,
leather bracers, trousers, tall buckled boots, phase-crystal blade in an open metal frame. Baked textures (cloak, tunic, trousers,
skin, hair, leather)."""
import bpy, bmesh, math, sys, os, random
import numpy as np
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hero_common import *
import hero_textures as T

SRC, OUT = sys.argv[-2], sys.argv[-1]
random.seed(44)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
remove_objects("_Head", "_Feet")
TEX = os.path.join(OUT, "tex_rw")
BRONZE = np.array([0.72, 0.52, 0.30], np.float32)


# ---------- textures ----------
def fabric(name, base, motif, seed, hem_irid=False):
    n = 512; x, y = T._grid(n)
    nz = T.fbm(n, seed, 4, 14); weave = 0.5 + 0.5 * np.sin(x * n * 0.35) * np.sin(y * n * 0.35)
    base = np.array(base, np.float32)
    col = base[None, None, :] * (0.78 + 0.45 * nz[..., None]) * (0.93 + 0.07 * weave[..., None])
    emis = np.zeros((n, n, 4), np.float32); emis[..., 3] = 1
    h = 0.1 * weave + 0.25 * nz
    if motif == "geo":                                                  # fine geometric lines (rift-fold creases)
        d1 = np.abs(((x * 6 + y * 3) % 1.0) - 0.5); d2 = np.abs(((x * 6 - y * 3) % 1.0) - 0.5)
        lines = ((d1 < 0.012) | (d2 < 0.012)) * (0.35 + 0.65 * T.smooth(0.3, 0.8, nz))
        col = col * (1 - lines[..., None] * 0.7) + BRONZE[None, None, :] * 0.55 * lines[..., None]
        h += 0.25 * lines
    if motif == "arcs":
        fx, fy = (x * 3) % 1.0, (y * 3) % 1.0
        rr = np.hypot(fx - 0.5, fy - 1.0)
        arcs = ((np.abs(rr - 0.30) < 0.011) | (np.abs(rr - 0.45) < 0.011) | (np.abs(rr - 0.6) < 0.011)) & (fy < 0.9)
        arcs &= T.smooth(0.3, 0.45, nz) > 0.2
        col = col * (1 - arcs[..., None] * 0.8) + BRONZE[None, None, :] * 0.6 * arcs[..., None]
        h += 0.3 * arcs
    if hem_irid:                                                        # pearlescent edge: purple / teal / pink drift near the hem
        edge = T.smooth(0.80, 0.995, y) * (0.6 + 0.4 * T.smooth(0.2, 0.8, nz))
        ph = x * 6.0 + y * 4.0 + nz * 2.0
        irid = np.stack([0.72 + 0.2 * np.sin(ph), 0.72 + 0.2 * np.sin(ph + 2.1), 0.82 + 0.15 * np.sin(ph + 4.2)], -1)
        col = col * (1 - 0.45 * edge[..., None]) + irid * 0.45 * edge[..., None]
        emis[..., :3] = irid * 0.18 * (edge[..., None] ** 2)
        rim = ((y > 0.985)).astype(np.float32)
        col = col * (1 - rim[..., None]) + BRONZE[None, None, :] * 0.5 * rim[..., None]
    img = T.to_image(name + "_diffuse", np.concatenate([col, np.ones((n, n, 1), np.float32)], -1), TEX)
    nm = T.to_image(name + "_normal", T.normal_from_height(h, 0.9), TEX, "Non-Color")
    em = T.to_image(name + "_emission", emis, TEX) if hem_irid else None
    return img, nm, em


def skin_tex():
    n = 512; x, y = T._grid(n)
    nz = T.fbm(n, 61, 5, 8); fine = T.fbm(n, 62, 3, 40)
    col = np.array([0.62, 0.50, 0.43], np.float32)[None, None, :] * (0.82 + 0.3 * nz[..., None] + 0.1 * fine[..., None])
    wr = T.smooth(0.84, 0.95, 1 - np.abs(2 * T.fbm(n, 63, 3, 14) - 1))      # weathering lines
    col = col * (1 - 0.18 * wr[..., None])
    return (T.to_image("skin_diffuse", np.concatenate([col, np.ones((n, n, 1), np.float32)], -1), TEX),
            T.to_image("skin_normal", T.normal_from_height(0.4 * nz + 0.4 * fine + 0.5 * wr, 0.7), TEX, "Non-Color"))


def hair_tex():
    n = 256; x, y = T._grid(n)
    nz = T.fbm(n, 71, 3, 30)
    strand = 0.5 + 0.5 * np.sin(x * n * 0.9 + nz * 6)
    base = np.array([0.52, 0.51, 0.55], np.float32)
    col = base[None, None, :] * (0.55 + 0.6 * strand[..., None] * (0.7 + 0.3 * nz[..., None]))
    return (T.to_image("hair_diffuse", np.concatenate([col, np.ones((n, n, 1), np.float32)], -1), TEX),
            T.to_image("hair_normal", T.normal_from_height(strand * 0.8, 1.0), TEX, "Non-Color"))


def leather_tex():
    n = 512; x, y = T._grid(n)
    nz = T.fbm(n, 81, 5, 10); crack = T.smooth(0.55, 0.9, 1 - np.abs(2 * T.fbm(n, 82, 4, 20) - 1))
    base = np.array([0.34, 0.21, 0.13], np.float32)
    col = base[None, None, :] * (0.65 + 0.7 * nz[..., None]) * (1 - 0.15 * crack[..., None])
    scuff = T.smooth(0.7, 0.95, T.fbm(n, 83, 4, 6))
    col = col + scuff[..., None] * 0.07
    return (T.to_image("leather_diffuse", np.concatenate([col, np.ones((n, n, 1), np.float32)], -1), TEX),
            T.to_image("leather_normal", T.normal_from_height(0.5 * nz + 0.7 * crack, 1.2), TEX, "Non-Color"))


ki, kn = skin_tex(); hi, hn = hair_tex(); li, ln = leather_tex()
cloak_i, cloak_n, cloak_e = fabric("cloak", (0.20, 0.21, 0.31), "geo", 91, hem_irid=True)
tun_i, tun_n, _ = fabric("tunic", (0.22, 0.23, 0.33), "arcs", 92)
trs_i, trs_n, _ = fabric("trouser", (0.15, 0.13, 0.15), "plain", 93)

# ---------- materials ----------
M_SKIN = mat("RW_Skin", (0.4, 0.22, 0.14), 0.6, 0.0)
M_SKINB = mat("RW_SkinBody", (0.4, 0.22, 0.14), 0.6, 0.0)
M_CLOAK = mat("RW_Cloak", (0.2, 0.21, 0.31), 0.85, 0.0, emit=(1, 1, 1), strength=0.9)
M_TUNIC = mat("RW_Tunic", (0.22, 0.23, 0.33), 0.9)
M_TROUS = mat("RW_Trouser", (0.15, 0.13, 0.15), 0.92)
M_HAIR = mat("RW_Hair", (0.52, 0.51, 0.55), 0.55, 0.0)
M_LEATH = mat("RW_Leather", (0.34, 0.21, 0.13), 0.6)
M_LEATHD = mat("RW_LeatherDark", (0.16, 0.10, 0.07), 0.6)
M_BRONZE = mat("RW_Bronze", (0.72, 0.5, 0.26), 0.35, 1.0)
M_EYEW = mat("RW_EyeWhite", (0.8, 0.78, 0.74), 0.3)
M_IRIS = mat("RW_Iris", (0.2, 0.28, 0.3), 0.2)
M_LIP = mat("RW_Lip", (0.45, 0.24, 0.20), 0.5)
M_BROW = mat("RW_Brow", (0.35, 0.34, 0.37), 0.7)
M_CRYST = mat("RW_Crystal", (0.55, 0.5, 0.95), 0.08, 0.0, alpha=0.62, emit=(0.5, 0.4, 1.0), strength=0.9)
T.bind(M_SKIN, ki, kn); T.bind(M_CLOAK, cloak_i, cloak_n, cloak_e, 0.9); T.bind(M_TUNIC, tun_i, tun_n); T.bind(M_TROUS, trs_i, trs_n)
T.bind(M_HAIR, hi, hn); T.bind(M_LEATH, li, ln)
recolor_base({"SciFi_Light": (0.4, 0.22, 0.14), "SciFi_Light_Accent": (0.4, 0.22, 0.14), "SciFi_Main": (0.4, 0.22, 0.14),
              "SciFi_MainDark": (0.35, 0.19, 0.12), "Grey": (0.4, 0.22, 0.14)})
for _o in bpy.data.objects:
    if _o.type == "MESH" and _o.name.endswith(("_Body", "_Legs")):
        _o.data.materials.clear(); _o.data.materials.append(M_SKINB)
        for _p in _o.data.polygons: _p.material_index = 0

CY = -0.05


def ring(a, rad, z, rx=1.0, ry=1.0, cy=CY):
    return Vector((rad * rx * math.sin(a), cy - rad * ry * math.cos(a), z))


def tri(a, k, ph=0.0):                                    # 0..1 zig-zag, 1 at the points
    f = (a * k / (2 * math.pi) + ph) % 1.0
    return 1 - abs(2 * f - 1)


# ---------- head ----------
bm = bmesh.new()
ell(bm, (0, -0.035, 1.655), (0.080, 0.097, 0.104), seg=16, rings=10)
ell(bm, (0, -0.060, 1.598), (0.060, 0.064, 0.072), seg=14, rings=9)
ell(bm, (0, -0.090, 1.545), (0.034, 0.038, 0.032), seg=10, rings=7)
for sx in (1, -1):
    ell(bm, (sx * 0.047, -0.098, 1.598), (0.021, 0.022, 0.022), seg=8, rings=5)
    ell(bm, (sx * 0.079, 0.000, 1.625), (0.011, 0.022, 0.031), seg=8, rings=5)
    ell(bm, (sx * 0.046, -0.078, 1.556), (0.021, 0.032, 0.030), seg=8, rings=5)
    ell(bm, (sx * 0.032, -0.112, 1.620), (0.018, 0.012, 0.010), seg=8, rings=4)                    # lower lids / eye bags
    ell(bm, (sx * 0.033, -0.108, 1.640), (0.019, 0.011, 0.008), rot=(0, sx * math.radians(-8), 0), seg=8, rings=4)   # upper lids
tube(bm, (0, -0.116, 1.636), (0, -0.147, 1.592), 0.008, 0.012, seg=6)
ell(bm, (0, -0.145, 1.588), (0.017, 0.014, 0.012), seg=8, rings=5)
for sx in (1, -1): ell(bm, (sx * 0.015, -0.136, 1.586), (0.009, 0.009, 0.008), seg=6, rings=4)
ell(bm, (0, -0.040, 1.50), (0.040, 0.044, 0.062), seg=10, rings=7)                              # neck
attach(arm, "Hero_Head", bm, M_SKIN, "Head")
bm = bmesh.new()
for sx in (1, -1):
    ell(bm, (sx * 0.032, -0.1115, 1.628), (0.0125, 0.0070, 0.0075), rot=(0, sx * math.radians(-8), 0), seg=8, rings=4)
attach(arm, "Hero_EyeWhites", bm, M_EYEW, "Head")
bm = bmesh.new()
for sx in (1, -1): ell(bm, (sx * 0.032, -0.1175, 1.628), (0.0062, 0.0030, 0.0062), seg=8, rings=4)
attach(arm, "Hero_Irises", bm, M_IRIS, "Head")
bm = bmesh.new()
ell(bm, (0, -0.1175, 1.5755), (0.0165, 0.0050, 0.0040), seg=8, rings=4)
ell(bm, (0, -0.1170, 1.5675), (0.0150, 0.0055, 0.0055), seg=8, rings=4)
attach(arm, "Hero_Lips", bm, M_LIP, "Head")
bm = bmesh.new()                                                                                 # brows + moustache (grey)
for sx in (1, -1):
    ell(bm, (sx * 0.034, -0.1175, 1.652), (0.020, 0.0055, 0.0055), rot=(0, sx * math.radians(-12), 0), seg=8, rings=3)
    ell(bm, (sx * 0.013, -0.1215, 1.581), (0.016, 0.0065, 0.0065), rot=(0, sx * math.radians(14), 0), seg=8, rings=3)
attach(arm, "Hero_Brows", bm, M_BROW, "Head")


def beard(r, c):                                                    # jaw-hugging stubbled beard shell with a short chin point
    e = math.radians(8 - 100 * r)
    a0 = math.radians(100 - 40 * r)
    a = -a0 + 2 * a0 * c
    rx, ry, rz = 0.0665, 0.0705, 0.077
    p = Vector((0, -0.060, 1.598)) + Vector((rx * math.cos(e) * math.sin(a), -ry * math.cos(e) * math.cos(a), rz * math.sin(e)))
    return p + Vector((0, -0.004, -0.018 * (1 - abs(2 * c - 1)) * r))


attach(arm, "Hero_Beard", strip(6, 18, beard), M_HAIR, "Head")

# hair cap + wavy strands + ponytail + braids
HC = Vector((0, -0.030, 1.665))


def hair_pt(e, a, off=0.0):
    ce = math.cos(e)
    return HC + Vector(((0.089 + off) * ce * math.sin(a), -(0.106 + off) * ce * math.cos(a), (0.113 + off) * math.sin(e)))


def hair_fn(r, c):
    e = math.radians(-6 + 96 * r)
    h = math.radians(78) * (1 - smoothstep(math.radians(16), math.radians(46), e))
    a = h + (2 * math.pi - 2 * h) * c
    return hair_pt(e, a, 0.002 * math.sin(a * 9 + r * 7))


attach(arm, "Hero_HairCap", strip(10, 26, hair_fn), M_HAIR, "Head")
bm = bmesh.new()
for k in range(22):
    a = math.radians(40 + k * (280 / 21))
    root = hair_pt(math.radians(6), a, 0.0)
    ln = (0.12 + 0.09 * abs(math.sin(k * 1.7))) * (1.0 if abs(a - math.pi) > 0.5 else 1.15)
    side = 1 if math.sin(a) >= 0 else -1
    wv = random.uniform(0.0, 6)

    def strand(r, c, root=root, a=a, ln=ln, wv=wv):
        t = r
        out = Vector((math.sin(a), -math.cos(a), 0)) * (0.020 * math.sin(math.pi * min(1, t * 1.3)) + 0.012 * t)
        p = root + out + Vector((0.006 * math.sin(t * 9 + wv), 0.006 * math.cos(t * 7 + wv), -ln * t))
        wd = Vector((math.cos(a), math.sin(a), 0)) * (c - 0.5) * 2 * 0.011 * (1 - 0.6 * t)
        return p + wd
    b2 = strip(8, 3, strand)
    vm = {v: bm.verts.new(v.co) for v in b2.verts}
    for f in b2.faces: bm.faces.new([vm[v] for v in f.verts])
    b2.free()
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
attach(arm, "Hero_HairStrands", bm, M_HAIR, "Head")
bm = bmesh.new()
tube(bm, (0, 0.062, 1.655), (0, 0.105, 1.55), 0.026, 0.020, seg=6)                               # ponytail
tube(bm, (0, 0.105, 1.55), (0, 0.118, 1.42), 0.020, 0.010, seg=6)
for sx in (1, -1):                                                                               # braids over the chest
    prev = Vector((sx * 0.072, -0.095, 1.60))
    for i in range(1, 11):
        q = Vector((sx * (0.072 + 0.01 * math.sin(i * 1.1)), -0.115 - 0.01 * i * 0.5, 1.60 - 0.020 * i * 1.15))
        ell(bm, q, (0.0085, 0.0085, 0.0095), seg=5, rings=3)
        prev = q
attach(arm, "Hero_Ponytail", bm, M_HAIR, "Head")
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.022, radius2=0.022, depth=0.014, matrix=Matrix.Translation((0, 0.106, 1.545)))
for sx in (1, -1):
    ell(bm, (sx * 0.075, -0.125, 1.38), (0.012, 0.012, 0.016), seg=6, rings=4)                  # braid beads
    ell(bm, (sx * 0.072, -0.115, 1.50), (0.008, 0.008, 0.008), seg=5, rings=3)
attach(arm, "Hero_HairTies", bm, M_BRONZE, "Head")


# ---------- shared weighting ----------
def chest_w(co):
    if co.z > 1.18: return {"Chest": 1.0}
    q = smoothstep(1.18, 0.9, co.z)
    return {"Chest": 1 - q, "Hips": q * 0.6, ("UpperLeg.L" if co.x >= 0 else "UpperLeg.R"): q * 0.4}


def skirt_w(co):
    t = smoothstep(1.0, 0.55, co.z)
    front = max(0.0, -(co.y - CY) / max(1e-6, math.hypot(co.x, co.y - CY)))
    wl = t * (0.12 + 0.28 * front)
    return {"Hips": 1.0 - wl, ("UpperLeg.L" if co.x >= 0 else "UpperLeg.R"): wl}


def tors(a, z, off=0.0):
    rx, ry = 0.165 + off, 0.135 + off
    return Vector((rx * math.sin(a), -0.043 - ry * math.cos(a), z))


def bodice_w(co):
    ch = smoothstep(1.18, 1.32, co.z); tq = smoothstep(1.02, 1.1, co.z) * (1 - ch)
    return {"Chest": ch, "Torso": tq, "Hips": max(0.0, 1.0 - ch - tq)}


def panel(zt, hem_fn, rad_top, rad_bot, a0=0.0, a1=360.0, rows=10, cols=40, wob=0.008, phase=0.0, rx=1.0):
    def fn(r, c):
        a = math.radians(a0 + (a1 - a0) * c)
        hem = hem_fn(a)
        z = zt + r * (hem - zt)
        rad = rad_top + (rad_bot - rad_top) * (r ** 1.3) + wob * math.sin(a * 7 + phase) * r
        return ring(a, rad, z, rx, 1.0)
    return strip(rows, cols, fn)


# ---------- tunic: bodice, stand collar, sleeves, pointed panels ----------
skinned(arm, "Hero_Bodice", strip(9, 28, lambda r, c: tors(2 * math.pi * c, 1.52 - r * 0.50, 0.004)), M_TUNIC, bodice_w)
for layer in range(3):
    def collar(r, c, l=layer):
        a = 2 * math.pi * c
        rad = 0.070 + 0.012 * l + 0.030 * r
        top = 1.505 + 0.085 * max(0.0, math.cos(a - math.pi)) ** 1.3
        return Vector((rad * 1.1 * math.sin(a), CY + 0.008 - rad * math.cos(a), top - r * 0.06 - l * 0.016))
    attach(arm, f"Hero_Collar{layer}", strip(4, 20, collar), M_TUNIC, "Chest")


def wrap_band(a0, a1, z0, z1, w, off, n=16):
    pts = [tors(a0 + (a1 - a0) * i / (n - 1), z0 + (z1 - z0) * i / (n - 1), off) for i in range(n)]

    def fn(r, c):
        i = int(round(r * (n - 1))); p = pts[i]
        tan = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        out = Vector((p.x, p.y + 0.043, 0)).normalized()
        wd = tan.cross(out).normalized()
        return p + wd * (c - 0.5) * 2 * w
    return strip(n, 3, fn)


def arm_w(side):
    ua, la = ("UpperArm.L", "LowerArm.L") if side > 0 else ("UpperArm.R", "LowerArm.R")

    def w(co):
        t = smoothstep(0.26, 0.42, abs(co.x))
        return {ua: 1 - t, la: t} if abs(co.x) > 0.15 else {"Shoulder." + ("L" if side > 0 else "R"): 1.0}
    return w


for side, tag in ((1, "L"), (-1, "R")):
    def sleeve(r, c, s=side):
        x = 0.14 + r * 0.44
        a = 2 * math.pi * c
        rad = 0.056 - 0.012 * r
        yc = -0.058 - 0.030 * smoothstep(0.34, 0.6, abs(x))
        return Vector((s * x, yc + rad * math.sin(a), 1.432 + rad * math.cos(a)))
    skinned(arm, f"Hero_Sleeve_{tag}", strip(14, 14, sleeve), M_TUNIC, arm_w(side))
    bone = "LowerArm." + tag
    for i, (x0, x1) in enumerate(((0.385, 0.405), (0.405, 0.555))):                                  # leather bracer + bronze rims and arc
        def band(r, c, s=side, x0=x0, x1=x1):
            a = 2 * math.pi * c; x = x0 + (x1 - x0) * r
            rad = 0.0545 - 0.0105 * (x - 0.385) / 0.17 + (0.004 if i == 0 else 0.0)
            yc = -0.058 - 0.030 * smoothstep(0.34, 0.6, x)
            return Vector((s * x, yc + rad * math.sin(a), 1.432 + rad * math.cos(a)))
        attach(arm, f"Hero_Bracer_{tag}{i}", strip(3, 16, band), M_LEATH if i else M_BRONZE, bone)
    bm = bmesh.new()
    for xx in (0.390, 0.552):
        for j in range(16):
            a0 = 2 * math.pi * j / 16; a1 = 2 * math.pi * (j + 1) / 16
            rr = 0.054 - 0.0105 * (xx - 0.385) / 0.17
            yc = -0.058 - 0.030 * smoothstep(0.34, 0.6, xx)
            tube(bm, Vector((side * xx, yc + rr * math.sin(a0), 1.432 + rr * math.cos(a0))),
                 Vector((side * xx, yc + rr * math.sin(a1), 1.432 + rr * math.cos(a1))), 0.0035, 0.0035, seg=4)
    for t in range(5):                                                                              # engraved arc motif on the outer face
        a = math.radians(-80 + 40 * t)
        p0 = Vector((side * (0.43 + 0.02 * t), -0.100 - 0.0, 1.432 + 0.056 * math.cos(a)))
        tube(bm, Vector((side * 0.44, -0.092, 1.432 + 0.053 * math.cos(a) * 0.8)), Vector((side * 0.52, -0.098, 1.432 + 0.047 * math.cos(a) * 0.8)), 0.0016, 0.0016, seg=3)
    attach(arm, f"Hero_BracerTrim_{tag}", bm, M_BRONZE, bone)

# tunic skirt: full under-ring + pointed panels
skinned(arm, "Hero_TunicUnder", panel(1.04, lambda a: 0.66 - 0.07 * tri(a, 9), 0.19, 0.265, rows=9, cols=48), M_TUNIC, skirt_w)
skinned(arm, "Hero_PanelFront", panel(1.05, lambda a: 0.53 - 0.17 * (1 - abs(a) / math.radians(26)) if abs(a) < math.radians(26) else 0.7, 0.215, 0.275, a0=-26, a1=26, rows=12, cols=16), M_TUNIC, skirt_w)
skinned(arm, "Hero_PanelSideL", panel(1.04, lambda a: 0.62 - 0.12 * tri(a, 4, 0.3), 0.215, 0.29, a0=26, a1=100, rows=10, cols=20), M_TUNIC, skirt_w)
skinned(arm, "Hero_PanelSideR", panel(1.04, lambda a: 0.62 - 0.12 * tri(a, 4, 0.3), 0.215, 0.29, a0=-100, a1=-26, rows=10, cols=20), M_TUNIC, skirt_w)
skinned(arm, "Hero_PanelBack", panel(1.04, lambda a: 0.56 - 0.14 * tri(a, 4, 0.0), 0.215, 0.285, a0=100, a1=260, rows=10, cols=32), M_TUNIC, skirt_w)

# crossed belts, buckles, pouch
for nm, z, w, off in (("A", 1.115, 0.030, 0.020), ("B", 1.045, 0.026, 0.026)):
    skinned(arm, "Hero_Belt" + nm, wrap_band(0.0, 2 * math.pi, z, z, w, off, n=30), M_LEATH, bodice_w)
skinned(arm, "Hero_BeltDiag", wrap_band(math.radians(-70), math.radians(120), 1.17, 0.98, 0.026, 0.03, n=18), M_LEATHD, bodice_w)
bm = bmesh.new()
for (x, z) in ((-0.045, 1.115), (0.05, 1.045), (0.115, 1.06)):
    p = tors(math.asin(x / 0.19), z, 0.034)
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation(p + Vector((0, -0.008, 0))) @ Matrix.Diagonal((0.034, 0.008, 0.026, 1)))
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation(p + Vector((0, -0.014, 0))) @ Matrix.Diagonal((0.016, 0.006, 0.014, 1)))
attach(arm, "Hero_Buckles", bm, M_BRONZE, "Hips", smooth=False)
bm = bmesh.new(); bf = bmesh.new()
pc = Vector((0.19, -0.16, 0.96))
m = Matrix.Translation(pc) @ Matrix.Rotation(math.radians(-20), 4, 'Z')
bmesh.ops.create_cube(bm, size=1.0, matrix=m @ Matrix.Diagonal((0.07, 0.04, 0.075, 1)))
bmesh.ops.create_cube(bm, size=1.0, matrix=m @ Matrix.Translation((0, -0.004, 0.032)) @ Matrix.Diagonal((0.076, 0.046, 0.035, 1)))
bmesh.ops.create_cube(bf, size=1.0, matrix=m @ Matrix.Translation((0, -0.026, 0.020)) @ Matrix.Diagonal((0.016, 0.006, 0.02, 1)))
tube(bm, pc + Vector((0.0, 0.0, 0.07)), (0.17, -0.12, 1.06), 0.006, 0.006, seg=4)
attach(arm, "Hero_Pouch", bm, M_LEATH, "Hips")
attach(arm, "Hero_PouchClasp", bf, M_BRONZE, "Hips", smooth=False)

# ---------- cloak: three pointed layers, ring-and-crystal clasp ----------
def zig(z0, amp, k, ph=0.0, back=0.0, bp=1.0):
    return lambda a: z0 - amp * tri(a, k, ph) - back * max(0.0, math.cos(a - math.pi)) ** bp


skinned(arm, "Hero_CloakShort", panel(1.50, zig(1.12, 0.14, 5, 0.1), 0.175, 0.31, a0=24, a1=336, rows=10, cols=52, rx=1.15, wob=0.012), M_CLOAK, chest_w)
skinned(arm, "Hero_CloakMid", panel(1.47, zig(0.90, 0.12, 6, 0.4, back=0.30), 0.185, 0.335, a0=22, a1=338, rows=12, cols=60, rx=1.12, wob=0.014, phase=1.1), M_CLOAK, chest_w)
skinned(arm, "Hero_CloakLong", panel(1.45, zig(0.62, 0.10, 4, 0.0, back=0.40, bp=1.4), 0.19, 0.33, a0=70, a1=290, rows=14, cols=44, rx=1.1, wob=0.014, phase=0.5), M_CLOAK, chest_w)
for layer in range(2):                                                                               # folded hood pile at the nape
    def hood(r, c, l=layer):
        a = math.radians(70 + 220 * c)
        rad = 0.10 + 0.028 * l + 0.05 * r
        return ring(a, rad, 1.57 - r * 0.12 - l * 0.02, 1.2, 1.0)
    skinned(arm, f"Hero_HoodPile{layer}", strip(5, 20, hood), M_CLOAK, chest_w)

bm = bmesh.new()                                                                                    # clasp: double ring + crystal + pin
cc = Vector((0.095, -0.215, 1.40))
for rad, th in ((0.034, 0.0045), (0.024, 0.0040)):
    for j in range(16):
        a0 = 2 * math.pi * j / 16; a1 = 2 * math.pi * (j + 1) / 16
        tube(bm, cc + Vector((rad * math.cos(a0), -0.012, rad * math.sin(a0))), cc + Vector((rad * math.cos(a1), -0.012, rad * math.sin(a1))), th, th, seg=4)
tube(bm, cc + Vector((-0.045, -0.012, 0.0)), cc + Vector((0.05, -0.012, -0.012)), 0.004, 0.004, seg=4)
attach(arm, "Hero_Clasp", bm, M_BRONZE, "Chest")
bm = bmesh.new()
cone(bm, cc + Vector((0, -0.016, -0.026)), (0, 0, 1), 0.011, 0.052, seg=4, r2=0.0)
cone(bm, cc + Vector((0, -0.016, -0.026)), (0, 0, -1), 0.011, 0.030, seg=4, r2=0.0)
attach(arm, "Hero_ClaspCrystal", bm, M_CRYST, "Chest", smooth=False)

# ---------- trousers + tall buckled boots ----------
for side, tag in ((1, "L"), (-1, "R")):
    cx = side * 0.121

    def trouser(r, c, cx=cx):
        a = 2 * math.pi * c; z = 1.0 - r * 0.62
        rad = 0.088 - 0.020 * r + 0.006 * math.sin(r * 12 + c * 2)
        yy = -0.045 - 0.04 * r
        return Vector((cx + rad * math.cos(a), yy + rad * math.sin(a) * 1.05, z))

    def tw(co, tag=tag):
        t = smoothstep(0.50, 0.58, co.z)
        up = smoothstep(0.98, 1.05, co.z)
        return {"Hips": up, ("UpperLeg." + tag): t * (1 - up), ("LowerLeg." + tag): (1 - t) * (1 - up)}
    skinned(arm, "Hero_Trouser_" + tag, strip(10, 16, trouser), M_TROUS, tw)

    def shaft(r, c, cx=cx):
        a = 2 * math.pi * c; z = 0.46 - r * 0.435
        rad = 0.060 - 0.008 * smoothstep(0.35, 1.0, r) + (0.010 if r < 0.06 else 0.0)
        return Vector((cx + rad * math.cos(a), -0.080 + 0.018 * r + rad * math.sin(a) * 1.05, z))
    skinned(arm, "Hero_BootShaft_" + tag, strip(10, 18, shaft), M_LEATH, lambda co, tag=tag: {"LowerLeg." + tag: 1 - smoothstep(0.14, 0.05, co.z), "Foot." + tag: smoothstep(0.14, 0.05, co.z)})
    bm = bmesh.new()
    ell(bm, (cx, -0.135, 0.050), (0.052, 0.108, 0.042), seg=12, rings=7)
    ell(bm, (cx, -0.046, 0.054), (0.047, 0.052, 0.052), seg=10, rings=6)
    ell(bm, (cx, -0.105, 0.016), (0.056, 0.140, 0.015), seg=12, rings=5)
    ell(bm, (cx, -0.030, 0.014), (0.050, 0.045, 0.017), seg=8, rings=4)
    attach(arm, "Hero_BootFoot_" + tag, bm, M_LEATHD, "Foot." + tag)
    bm = bmesh.new(); bb = bmesh.new()
    for z in (0.37, 0.27, 0.17):
        zz = z
        rr = 0.060 + 0.0 - 0.008 * smoothstep(0.35, 1.0, (0.46 - z) / 0.435)
        yc = -0.080 + 0.018 * (0.46 - z) / 0.435
        bmesh.ops.create_cone(bm, cap_ends=True, segments=14, radius1=rr + 0.004, radius2=rr + 0.004, depth=0.020, matrix=Matrix.Translation((cx, yc, z)))
        bmesh.ops.create_cube(bb, size=1.0, matrix=Matrix.Translation((cx + side * (rr + 0.012), yc, z)) @ Matrix.Diagonal((0.008, 0.020, 0.024, 1)))
    bmesh.ops.create_cone(bm, cap_ends=True, segments=14, radius1=0.066, radius2=0.066, depth=0.012, matrix=Matrix.Translation((cx, -0.080, 0.455)))     # rolled top
    attach(arm, "Hero_BootStraps_" + tag, bm, M_LEATHD, "LowerLeg." + tag)
    attach(arm, "Hero_BootBuckles_" + tag, bb, M_BRONZE, "LowerLeg." + tag, smooth=False)

# ---------- phase blade in an open metal frame, hung at the left hip ----------
bd = Vector((0.20, -0.12, -1.0)).normalized()
bs = Vector((0.15, -0.265, 1.06))
bm = bmesh.new(); bc = bmesh.new(); bg = bmesh.new(); bl = bmesh.new()
cone(bg, bs + Vector((0, 0, 0.0)) + bd * -0.0, -bd, 0.013, 0.12, seg=6)                              # grip (up from the guard)
for i in range(1, 6):
    bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.0145, radius2=0.0145, depth=0.004, matrix=Matrix.Translation(bs - bd * 0.02 * i))
ell(bm, bs - bd * 0.13, (0.016, 0.016, 0.014), seg=6, rings=4)                                      # pommel
for sgn in (1, -1):                                                                                # crossguard curls
    tube(bm, bs + Vector((sgn * 0.006, 0, 0)), bs + Vector((sgn * 0.045, 0, 0.01)), 0.006, 0.0035, seg=4)
    tube(bm, bs + Vector((sgn * 0.045, 0, 0.01)), bs + Vector((sgn * 0.052, 0, 0.045)), 0.0035, 0.002, seg=4)
L = 0.46
tip = bs + bd * L
cone(bc, bs + bd * 0.01, bd, 0.020, L, seg=4, r2=0.0)                                              # crystal blade
for v in bc.verts: v.co = bs + (v.co - bs) * 1.0
for sgn in (1, -1):                                                                                # open frame rails + cross ties
    side_v = Vector((1, 0, 0)).cross(bd).normalized() * 0.0
    tube(bm, bs + bd * 0.02 + Vector((sgn * 0.022, 0, 0)), bs + bd * 0.33 + Vector((sgn * 0.016, 0, 0)), 0.0035, 0.0028, seg=4)
for i in (0.08, 0.17, 0.26):
    p = bs + bd * i
    tube(bm, p + Vector((-0.02, 0, 0)), p + Vector((0.02, 0, 0)), 0.003, 0.003, seg=4)
attach(arm, "Hero_PhaseHilt", bm, M_BRONZE, "Hips")
attach(arm, "Hero_PhaseGrip", bg, M_LEATHD, "Hips")
attach(arm, "Hero_PhaseBlade", bc, M_CRYST, "Hips", smooth=False)

print("RW_TOTAL_TRIS", tri_count())
bpy.ops.wm.save_as_mainfile(filepath=OUT + "/riftwalker.blend")
bpy.ops.export_scene.gltf(filepath=OUT + "/riftwalker.glb", export_format='GLB', export_apply=True,
                          export_animations=False, export_skins=True)
print("RW_DONE")
