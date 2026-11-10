"""Nullshade hero: hooded shadow-wisp mage in layered Dusk Veil drapery on the cosmic shared-skeleton base (Blender 5.x).
Run: blender -b -P build_nullshade.py -- <cosmic.glb> <out_dir>
Charcoal smoke-skin face with pale eyes, silver hair, pointed hood with silver trim, back drape + shoulder capelet,
fitted sleeves with long sheer hanging panels, crossed wraps, layered asymmetric sheer skirts, obi sash, crescent brooches
with chains, shadow-glass stiletto, pointed boots. Baked textures (skin, dusk cloth, sheer veil with silver filigree)."""
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
TEX = os.path.join(OUT, "tex_ns")
SCOL = np.array([0.80, 0.80, 0.86], np.float32)      # muted silver


# ---------- textures ----------
def skin_tex():
    n = 512; x, y = T._grid(n)
    nz = T.fbm(n, 31, 5, 5); nz2 = T.fbm(n, 77, 4, 9)
    base = np.array([0.37, 0.345, 0.42], np.float32)
    col = base[None, None, :] * (0.72 + 0.5 * nz[..., None])
    wisp = T.smooth(0.86, 0.97, 1 - np.abs(2 * nz2 - 1)) * 0.8                  # smoke wisps, silver edged
    col = col + wisp[..., None] * np.array([0.25, 0.25, 0.30], np.float32)
    h = 0.5 * nz + 0.5 * wisp
    return (T.to_image("skin_diffuse", np.concatenate([col, np.ones((n, n, 1), np.float32)], -1), TEX),
            T.to_image("skin_normal", T.normal_from_height(h, 0.8), TEX, "Non-Color"))


def cloth_tex():
    n = 512; x, y = T._grid(n)
    nz = T.fbm(n, 5, 4, 16); weave = 0.5 + 0.5 * np.sin(x * n * 0.35) * np.sin(y * n * 0.35)
    base = np.array([0.085, 0.07, 0.10], np.float32)
    col = base[None, None, :] * (0.7 + 0.7 * nz[..., None]) * (0.9 + 0.1 * weave[..., None])
    vein = T.smooth(0.90, 0.97, 1 - np.abs(2 * T.fbm(n, 13, 3, 12) - 1))
    col += vein[..., None] * SCOL[None, None, :] * 0.14
    hem = T.smooth(0.965, 0.985, y) * (1 - T.smooth(0.992, 1.0, y))      # thin silver hem line
    col = col * (1 - hem[..., None]) + SCOL[None, None, :] * 0.55 * hem[..., None]
    h = 0.12 * weave + 0.2 * nz + 0.3 * vein + 0.5 * hem
    return (T.to_image("cloth_diffuse", np.concatenate([col, np.ones((n, n, 1), np.float32)], -1), TEX),
            T.to_image("cloth_normal", T.normal_from_height(h, 1.0), TEX, "Non-Color"))


def sheer_tex():
    n = 512; x, y = T._grid(n)
    nz = T.fbm(n, 9, 4, 14); weave = 0.5 + 0.5 * np.sin(x * n * 0.4) * np.sin(y * n * 0.4)
    vein = T.smooth(0.88, 0.96, 1 - np.abs(2 * T.fbm(n, 15, 4, 10) - 1))
    base = np.array([0.20, 0.17, 0.24], np.float32)
    col = base[None, None, :] * (0.7 + 0.6 * nz[..., None]) + vein[..., None] * SCOL[None, None, :] * 0.12
    band = ((y > 0.935) & (y < 0.955)) | ((y > 0.972) & (y < 0.98))      # etched silver trim bands at the hem
    sc = ((x * 28) % 1.0 - 0.5) ** 2 + ((y * 28) % 1.0 - 0.5) ** 2
    dots = (sc < 0.012) & (y > 0.955) & (y < 0.972)
    trim = (band | dots)
    col = np.where(trim[..., None], SCOL[None, None, :] * 0.62, col)
    alpha = np.clip(0.36 + 0.22 * nz + 0.12 * vein + 0.05 * weave, 0.0, 0.8)
    alpha = np.where(trim, 0.95, alpha)
    h = 0.08 * weave + 0.7 * trim + 0.15 * vein
    return (T.to_image("sheer_diffuse", np.concatenate([col, alpha[..., None]], -1), TEX),
            T.to_image("sheer_normal", T.normal_from_height(h, 0.5), TEX, "Non-Color"))


si, sn = skin_tex(); ci, cn = cloth_tex(); shi, shn = sheer_tex()

# ---------- materials ----------
M_SKIN = mat("NS_Skin", (0.12, 0.11, 0.145), 0.55, 0.05)
M_SKINB = mat("NS_SkinBody", (0.12, 0.11, 0.145), 0.55, 0.05)
M_CLOTH = mat("NS_Cloth", (0.085, 0.07, 0.10), 0.92)
M_SHEER = mat("NS_Sheer", (0.20, 0.17, 0.24), 0.8, 0.0, alpha=0.5)
M_SILK = mat("NS_Silver", (0.62, 0.62, 0.68), 0.28, 1.0)
M_HAIR = mat("NS_Hair", (0.62, 0.62, 0.66), 0.45, 0.2)
M_EYE = mat("NS_Eye", (0.6, 0.64, 0.74), 0.1, 0.0, emit=(0.6, 0.66, 0.85), strength=0.9)
M_PUPIL = mat("NS_Pupil", (0.02, 0.02, 0.03), 0.1)
M_SOCK = mat("NS_Socket", (0.045, 0.04, 0.06), 0.7)
M_LIP = mat("NS_Lip", (0.16, 0.12, 0.17), 0.45)
M_LEATH = mat("NS_Leather", (0.045, 0.04, 0.055), 0.45)
M_GLASS = mat("NS_ShadowGlass", (0.08, 0.07, 0.14), 0.12, 0.4, emit=(0.22, 0.14, 0.45), strength=0.8)
M_NAIL = mat("NS_Nail", (0.35, 0.35, 0.4), 0.3, 0.9)
T.bind(M_SKIN, si, sn); T.bind(M_CLOTH, ci, cn); T.bind(M_SHEER, shi, shn)
recolor_base({"SciFi_Light": (0.12, 0.11, 0.145), "SciFi_Light_Accent": (0.12, 0.11, 0.145), "SciFi_Main": (0.12, 0.11, 0.145),
              "SciFi_MainDark": (0.1, 0.09, 0.12), "Grey": (0.12, 0.11, 0.145)})
for _o in bpy.data.objects:
    if _o.type == "MESH" and _o.name.endswith(("_Body", "_Legs")):
        _o.data.materials.clear(); _o.data.materials.append(M_SKINB)
        for _p in _o.data.polygons: _p.material_index = 0

CY = -0.05                                                              # torso/skirt centre line y


def ring(a, rad, z, rx=1.0, ry=1.0, cy=CY):
    return Vector((rad * rx * math.sin(a), cy - rad * ry * math.cos(a), z))


def new_obj_bone(name, bm, material, bone):
    return attach(arm, name, bm, material, bone)


# ---------- head: sculpted face ----------
bm = bmesh.new()
ell(bm, (0, -0.035, 1.655), (0.078, 0.095, 0.102), seg=16, rings=10)                    # cranium
ell(bm, (0, -0.060, 1.600), (0.058, 0.062, 0.070), seg=14, rings=9)                    # face mass
ell(bm, (0, -0.085, 1.548), (0.030, 0.034, 0.030), seg=12, rings=8)                     # chin
for sx in (1, -1):
    ell(bm, (sx * 0.046, -0.100, 1.600), (0.020, 0.020, 0.020), seg=10, rings=6)         # cheekbones
    ell(bm, (sx * 0.074, 0.000, 1.625), (0.012, 0.022, 0.030), seg=8, rings=5)           # ear
    ell(bm, (sx * 0.044, -0.080, 1.558), (0.020, 0.030, 0.030), seg=8, rings=5)          # jaw
    ell(bm, (sx * 0.032, -0.113, 1.648), (0.022, 0.012, 0.007), rot=(0, sx * math.radians(-14), 0), seg=8, rings=4)   # brow
tube(bm, (0, -0.116, 1.632), (0, -0.142, 1.594), 0.007, 0.011, seg=6)                    # nose bridge
ell(bm, (0, -0.139, 1.590), (0.014, 0.012, 0.011), seg=8, rings=5)                       # nose tip
for sx in (1, -1): ell(bm, (sx * 0.012, -0.132, 1.587), (0.008, 0.008, 0.007), seg=6, rings=4)
ell(bm, (0, -0.040, 1.50), (0.036, 0.040, 0.060), seg=12, rings=7)                       # neck
attach(arm, "Hero_Head", bm, M_SKIN, "Head")
bm = bmesh.new()
for sx in (1, -1):
    ell(bm, (sx * 0.032, -0.111, 1.628), (0.0155, 0.009, 0.0095), rot=(0, sx * math.radians(-14), 0), seg=10, rings=5)
attach(arm, "Hero_EyeSockets", bm, M_SOCK, "Head")
bm = bmesh.new()
for sx in (1, -1):
    ell(bm, (sx * 0.032, -0.116, 1.628), (0.0115, 0.0072, 0.0068), rot=(0, sx * math.radians(-14), 0), seg=10, rings=5)
attach(arm, "Hero_Eyes", bm, M_EYE, "Head")
bm = bmesh.new()
for sx in (1, -1): ell(bm, (sx * 0.032, -0.1225, 1.628), (0.0033, 0.002, 0.0033), seg=6, rings=4)
attach(arm, "Hero_Pupils", bm, M_PUPIL, "Head")
bm = bmesh.new()
ell(bm, (0, -0.1165, 1.5745), (0.018, 0.0055, 0.0055), seg=8, rings=4)
ell(bm, (0, -0.1165, 1.5640), (0.016, 0.0060, 0.0065), seg=8, rings=4)
attach(arm, "Hero_Lips", bm, M_LIP, "Head")

# silver hair: long loose strands framing the face, falling over the shoulders
bm = bmesh.new()
for sx in (1, -1):
    for k in range(5):
        r0 = Vector((sx * (0.070 + 0.004 * k), -0.085 - 0.004 * k, 1.665 - 0.012 * k))
        ln = 0.30 + 0.05 * k + random.uniform(-0.03, 0.03)
        w = 0.008 + 0.002 * (k % 2)
        def strand(r, c, r0=r0, ln=ln, w=w, k=k, sx=sx):
            t = r
            p = r0 + Vector((sx * (0.020 + 0.015 * t) + sx * 0.012 * math.sin(t * 7 + k), -0.020 * t - 0.012 * math.sin(t * 5 + k * 2), -ln * t * 1.02 - 0.0))
            return p + Vector((sx * w * (c - 0.5) * 2 * (1 - 0.7 * t), -0.004 * (c - 0.5), 0))
        b2 = strip(14, 2, strand)
        bm.from_mesh(bpy.data.meshes.new("x")) if False else None
        # merge manually
        vm = {}
        for v in b2.verts: vm[v] = bm.verts.new(v.co)
        uvl = bm.loops.layers.uv.get("UVMap") or bm.loops.layers.uv.new("UVMap")
        for f in b2.faces:
            nf = bm.faces.new([vm[v] for v in f.verts])
        b2.free()
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
attach(arm, "Hero_Hair", bm, M_HAIR, "Head")

# ---------- hood ----------
HC = Vector((0, -0.030, 1.655))


def hood_pt(e, a, off=0.0):
    rx, ry, rz = 0.128 + off, 0.152 + off, 0.150 + off
    ce = math.cos(e)
    return HC + Vector((rx * ce * math.sin(a), -ry * ce * math.cos(a), rz * math.sin(e)))


def half_open(e):
    return math.radians(47) * (1 - smoothstep(math.radians(8), math.radians(66), e))


E0, E1 = math.radians(-44), math.radians(90)


def hood_fn(off):
    def fn(r, c):
        e = E0 + (E1 - E0) * r
        h = half_open(e)
        a = h + (2 * math.pi - 2 * h) * c
        # lower rim flares out at the back and sides into a cowl
        p = hood_pt(e, a, off + (0.012 * (1 - smoothstep(-44, 0, math.degrees(e))) if False else 0))
        if e < math.radians(-15):
            k = (math.radians(-15) - e) / math.radians(29)
            p += Vector((0.05 * k * math.sin(a), 0.03 * k * (-math.cos(a)) * 0.3, -0.03 * k))
        return p
    return fn


attach(arm, "Hero_HoodShell", strip(14, 28, hood_fn(0.0)), M_CLOTH, "Head")
attach(arm, "Hero_HoodSheer", strip(14, 28, hood_fn(0.012)), M_SHEER, "Head")
bm = bmesh.new()                                                       # silver trim along the face opening
pts = []
for i in range(22):
    e = E0 + (E1 - E0) * 0.0 + math.radians(-40 + i * 5.8)
    h = half_open(e)
    pts.append((hood_pt(e, h, 0.014), hood_pt(e, 2 * math.pi - h, 0.014)))
for side in (0, 1):
    for i in range(len(pts) - 1):
        tube(bm, pts[i][side], pts[i + 1][side], 0.0035, 0.0035, seg=3)
attach(arm, "Hero_HoodTrim", bm, M_SILK, "Head")
# faint filigree on the hood crown
bm = bmesh.new()
for k in range(3):
    prev = None
    for i in range(18):
        t = i / 17
        e = math.radians(35 + 50 * t); a = math.radians(-50 + 100 * k / 2 * 1.0 + 25 * math.sin(t * 5 + k) + 90 * 0)
        p = hood_pt(e, math.pi * 0.0 + math.radians(60 * (k - 1)) + math.radians(14) * math.sin(t * 6 + k), 0.016)
        if prev is not None and e < math.radians(88): tube(bm, prev, p, 0.0022, 0.0022, seg=3)
        prev = p
attach(arm, "Hero_HoodFiligree", bm, M_SILK, "Head")

# ---------- back drape, shoulder capelet ----------
def back_drape(r, c):
    t = r; a = math.radians(105 + 150 * c)
    z = 1.575 - t * 1.12 + 0.12 * (1 - abs(2 * c - 1)) * t * t      # longer centre point
    rad = 0.155 + 0.07 * t + 0.01 * math.sin(c * 14)
    return ring(a, rad, z - 0.0, 1.0, 1.0)


def chest_w(co):
    if co.z > 1.18: return {"Chest": 1.0}
    q = smoothstep(1.18, 0.9, co.z)
    return {"Chest": 1 - q, "Hips": q * 0.6, ("UpperLeg.L" if co.x >= 0 else "UpperLeg.R"): q * 0.4}


skinned(arm, "Hero_BackDrape", strip(14, 22, back_drape), M_SHEER, chest_w)


def capelet(r, c):
    a = 2 * math.pi * c
    z = 1.47 - r * 0.30 - 0.09 * (abs(math.sin(a * 2.5)) ** 0.7) * r * r
    rad = 0.145 + 0.045 * r + 0.012 * math.sin(a * 6) * r
    return ring(a, rad, z, 1.20, 0.98)


skinned(arm, "Hero_Capelet", strip(8, 36, capelet), M_SHEER, chest_w)
for layer in range(3):
    def cowl(r, c, l=layer):
        a = 2 * math.pi * c
        rad = 0.085 + 0.022 * l + 0.04 * r
        return Vector((rad * 1.15 * math.sin(a), CY + 0.007 - rad * math.cos(a), 1.545 - r * 0.075 - l * 0.02))
    attach(arm, f"Hero_Cowl{layer}", strip(4, 24, cowl), M_CLOTH, "Chest")

# ---------- torso: bodice, crossed wraps, sash ----------
def tors(a, z, off=0.0):
    rx, ry = 0.165 + off, 0.135 + off
    return Vector((rx * math.sin(a), -0.043 - ry * math.cos(a), z))


def bodice(r, c):
    z = 1.50 - r * 0.40
    waist = 0.9 + 0.1 * (1 - abs(2 * r - 1.1) * 0.5)
    return tors(2 * math.pi * c, z, 0.004) * 1.0


def bodice_w(co):
    ch = smoothstep(1.18, 1.32, co.z); tq = smoothstep(1.02, 1.1, co.z) * (1 - ch)
    return {"Chest": ch, "Torso": tq, "Hips": max(0.0, 1.0 - ch - tq)}


skinned(arm, "Hero_Bodice", strip(9, 28, bodice), M_CLOTH, bodice_w)


def wrap_band(a0, a1, z0, z1, w, off, n=16):
    pts = [tors(a0 + (a1 - a0) * i / (n - 1), z0 + (z1 - z0) * i / (n - 1), off) for i in range(n)]
    def fn(r, c):
        i = int(round(r * (n - 1))); p = pts[i]
        tan = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        out = Vector((p.x, p.y + 0.043, 0)).normalized()
        wd = tan.cross(out).normalized()
        return p + wd * (c - 0.5) * 2 * w
    return strip(n, 3, fn)


for nm, a0, a1 in (("X1", -100, 100), ("X2", 100, -100)):
    o = skinned(arm, "Hero_Wrap" + nm, wrap_band(math.radians(a0), math.radians(a1), 1.46, 1.16, 0.045, 0.018), M_SHEER, chest_w)
for z, off in ((1.215, 0.022), (1.17, 0.026), (1.125, 0.03)):                       # obi-style sash layers
    skinned(arm, f"Hero_Sash_{int(z * 100)}", wrap_band(0.0, 2 * math.pi, z, z - 0.01, 0.034, off, n=30), M_CLOTH, bodice_w)
# sash hanging end (front tail with etched silver tip)
def sash_tail(r, c):
    z = 1.15 - r * 0.50
    x = 0.085 + 0.01 * math.sin(r * 5) + (c - 0.5) * (0.05 - 0.02 * r)
    return Vector((x, -0.222 - 0.012 * r, z))
skinned(arm, "Hero_SashTail", strip(10, 3, sash_tail), M_CLOTH, lambda co: {"Hips": 0.7, "Torso": 0.3})
bm = bmesh.new()                                                                    # silver tip of the tail
for z in (0.64, 0.60):
    ell(bm, (0.085, -0.228, z), (0.018, 0.005, 0.008), seg=6, rings=3)
cone(bm, (0.085, -0.228, 0.655), (0, 0, -1), 0.016, 0.07, seg=4)
attach(arm, "Hero_SashTip", bm, M_SILK, "Hips", smooth=False)


def crescent(bm, c, rad, thick, ang0=40, ang1=320, seg=14, plane='XZ', sx=1.0):
    pts = []
    for i in range(seg):
        a = math.radians(ang0 + (ang1 - ang0) * i / (seg - 1))
        pts.append(Vector(c) + Vector((rad * math.cos(a), 0, rad * math.sin(a))))
    for i in range(seg - 1):
        k = 1 - abs(2 * i / (seg - 2) - 1) * 0.55
        tube(bm, pts[i], pts[i + 1], thick * (0.5 + 0.5 * k), thick * (0.5 + 0.5 * k), seg=5)


bm = bmesh.new()
crescent(bm, (0.0, -0.232, 1.165), 0.022, 0.0065, ang0=-130, ang1=170)                 # sash crescent clasp
crescent(bm, (-0.155, -0.118, 1.385), 0.018, 0.0055, ang0=-30, ang1=250)               # shoulder crescent brooch (right shoulder)
attach(arm, "Hero_Crescents", bm, M_SILK, "Chest")
bm = bmesh.new()                                                                    # sagging chains from the brooch
p0 = Vector((-0.155, -0.125, 1.375)); p1 = Vector((-0.02, -0.215, 1.20))
for off in (0.0, 0.016, 0.032):
    pa = p0 + Vector((off * 0.4, -off * 0.4, -off)); pb = p1 + Vector((off * 0.5, 0, 0.012 * off * 10))
    prev = pa
    for i in range(1, 13):
        t = i / 12
        q = pa.lerp(pb, t) + Vector((0, -0.01 * math.sin(math.pi * t), -0.045 * math.sin(math.pi * t) * (1 + off * 8)))
        ell(bm, (prev + q) / 2, (0.0045, 0.0032, 0.0045), seg=4, rings=3)
        prev = q
attach(arm, "Hero_Chains", bm, M_SILK, "Chest")

# ---------- sleeves + long sheer hanging panels ----------
def arm_w(side):
    ua, la = ("UpperArm.L", "LowerArm.L") if side > 0 else ("UpperArm.R", "LowerArm.R")
    def w(co):
        t = smoothstep(0.26, 0.42, abs(co.x))
        return {ua: 1 - t, la: t} if abs(co.x) > 0.15 else {"Shoulder." + ("L" if side > 0 else "R"): 1.0}
    return w


for side, tag in ((1, "L"), (-1, "R")):
    def sleeve(r, c, s=side):
        x = 0.14 + r * 0.43                                           # shoulder to just before the wrist
        a = 2 * math.pi * c
        rad = 0.056 - 0.012 * r
        yc = -0.058 - 0.030 * smoothstep(0.34, 0.6, abs(x))
        return Vector((s * x, yc + rad * math.sin(a), 1.432 + rad * math.cos(a) * 1.0))
    skinned(arm, f"Hero_Sleeve_{tag}", strip(14, 14, sleeve), M_CLOTH, arm_w(side))

    def hang(r, c, s=side, lenf=1.0):
        x = 0.16 + r * 0.56
        saw = abs(((r * 4.5) % 1.0) - 0.5) * 2                      # triangular hem points
        drop = (0.06 + 0.55 * smoothstep(0.1, 1.0, r) * lenf) * (0.72 + 0.28 * saw ** 0.7)
        zz = 1.405 - c * drop - 0.02 * math.sin(r * 4)
        x = x + 0.05 * c * r
        yc = -0.058 - 0.030 * smoothstep(0.34, 0.6, x)
        sway = 0.03 * c * math.sin(r * 4 + (1 if s > 0 else 2)) + 0.02 * c * (1 - r)
        return Vector((s * x, yc + sway - 0.012 * c, zz))
    skinned(arm, f"Hero_ArmDrape_{tag}", strip(18, 8, hang), M_SHEER, arm_w(side))

    def hang2(r, c, s=side):                                          # second, shorter, offset layer
        x = 0.30 + r * 0.38
        saw = abs(((r * 3.0 + 0.3) % 1.0) - 0.5) * 2
        drop = (0.04 + 0.34 * smoothstep(0.0, 1.0, r)) * (0.65 + 0.35 * saw ** 0.7)
        zz = 1.40 - c * drop + 0.03 * math.sin(r * 7) * c
        yc = -0.062 - 0.030 * smoothstep(0.34, 0.6, x)
        return Vector((s * x, yc - 0.022 * c, zz))
    skinned(arm, f"Hero_ArmDrape2_{tag}", strip(14, 6, hang2), M_SHEER, arm_w(side))
    bm = bmesh.new()                                                  # silver cuff
    for xx in (0.55, 0.575):
        for i in range(14):
            a0 = 2 * math.pi * i / 14; a1 = 2 * math.pi * (i + 1) / 14
            rr = 0.047
            tube(bm, Vector((side * xx, -0.082 + rr * math.sin(a0), 1.432 + rr * math.cos(a0))),
                 Vector((side * xx, -0.082 + rr * math.sin(a1), 1.432 + rr * math.cos(a1))), 0.0045, 0.0045, seg=4)
    attach(arm, f"Hero_Cuff_{tag}", bm, M_SILK, "LowerArm." + tag)
    # long dark nails on the fingers
    bm = bmesh.new()
    for tail in ((0.807, -0.122, 1.446), (0.84, -0.089, 1.453), (0.815, -0.047, 1.449), (0.783, -0.016, 1.447)):
        cone(bm, (side * tail[0], tail[1], tail[2]), (side * 1.0, 0, 0.05), 0.0045, 0.034, seg=4)
    cone(bm, (side * 0.699, -0.183, 1.40), (side * 0.7, -0.7, -0.1), 0.005, 0.030, seg=4)
    attach(arm, f"Hero_Nails_{tag}", bm, M_NAIL, "Hand." + tag, smooth=False)

# ---------- layered skirts ----------
def skirt_w(co):
    t = smoothstep(1.0, 0.55, co.z)
    front = max(0.0, -(co.y - CY) / max(1e-6, math.hypot(co.x, co.y - CY)))
    wl = t * (0.12 + 0.28 * front)
    return {"Hips": 1.0 - wl, ("UpperLeg.L" if co.x >= 0 else "UpperLeg.R"): wl}


def skirt(zt, hem_fn, rad_top, rad_bot, a0=0.0, a1=360.0, rows=10, cols=44, wob=0.012, rx=1.0, tooth=0.0, phase=0.0):
    def fn(r, c):
        a = math.radians(a0 + (a1 - a0) * c)
        hem = hem_fn(a)
        z = zt + r * (hem - zt)
        rad = rad_top + (rad_bot - rad_top) * (r ** 1.4) + wob * math.sin(a * 7 + phase) * r
        if tooth: z -= tooth * (abs(math.sin(a * 5 + phase))) ** 0.8 * r ** 3
        return ring(a, rad, z, rx, 1.0)
    return strip(rows, cols, fn)


FLOOR = 0.045
skinned(arm, "Hero_SkirtUnder", skirt(1.04, lambda a: 0.06 + 0.04 * math.cos(a), 0.19, 0.33, wob=0.01), M_CLOTH, skirt_w)
skinned(arm, "Hero_SkirtMid", skirt(1.04, lambda a: 0.10 + 0.34 * (0.5 + 0.5 * math.cos(a - 2.2)), 0.205, 0.36, wob=0.015, tooth=0.05, phase=1.3), M_CLOTH, skirt_w)
skinned(arm, "Hero_SkirtSheerA", skirt(1.02, lambda a: 0.14 + 0.46 * (0.5 + 0.5 * math.cos(a + 1.0)), 0.215, 0.40, wob=0.02, tooth=0.13, phase=0.4, rows=11), M_SHEER, skirt_w)
skinned(arm, "Hero_SkirtSheerB", skirt(1.0, lambda a: 0.07 + 0.26 * (0.5 + 0.5 * math.cos(a - 0.6)), 0.225, 0.44, wob=0.02, tooth=0.14, phase=2.1, rows=11), M_SHEER, skirt_w)
# asymmetric front overwrap panel (draped diagonally, tips down)
def wrap_hem(a):
    return 0.30 + 0.30 * smoothstep(-0.6, 0.9, a)
skinned(arm, "Hero_SkirtWrap", skirt(1.06, wrap_hem, 0.222, 0.41, a0=-70, a1=70, rows=14, cols=22, wob=0.01, tooth=0.05, phase=0.7), M_CLOTH, skirt_w)
# long trailing back train
def train_fn(r, c):
    a = math.radians(120 + 120 * c)
    hem = 0.03 + 0.10 * (1 - abs(2 * c - 1)) * 0.0
    z = 1.0 + r * (hem - 1.0) + 0.0
    tip = 0.10 * (1 - abs(2 * c - 1)) ** 0.7 * r ** 2
    rad = 0.215 + 0.26 * r ** 1.5 + 0.012 * math.sin(c * 17)
    return ring(a, rad, max(0.0, z) - 0.0 + 0.0, 1.0, 1.0) + Vector((0, 0.05 * r * r, 0))
skinned(arm, "Hero_SkirtTrain", strip(14, 28, train_fn), M_SHEER, skirt_w)

bm = bmesh.new()                                                           # belt strap over the underskirt
bmesh.ops.create_cone(bm, cap_ends=True, segments=26, radius1=0.206, radius2=0.206, depth=0.03, matrix=Matrix.Translation((0, CY, 1.075)))
attach(arm, "Hero_Belt", bm, M_LEATH, "Hips")

# ---------- shadow-glass stiletto (hangs at the sash) ----------
bm = bmesh.new(); bl = bmesh.new(); bg = bmesh.new()
sx0, sy0, sz0 = 0.125, -0.236, 1.06
cone(bl, (sx0, sy0, sz0 - 0.03), (0, 0, -1), 0.014, 0.24, seg=4)           # blade (point down)
cone(bl, (sx0, sy0, sz0 - 0.03), (0, 0, 1), 0.014, 0.015, seg=4)
cone(bg, (sx0, sy0, sz0 + 0.12), (0, 0, -1), 0.011, 0.14, seg=6)           # leather-wrapped grip
for z in (sz0 + 0.004, sz0 + 0.044, sz0 + 0.085):
    bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.013, radius2=0.013, depth=0.005, matrix=Matrix.Translation((sx0, sy0, z)))
for sgn in (1, -1):                                                            # curved quillon spikes
    cone(bm, (sx0 + sgn * 0.01, sy0, sz0 - 0.01), (sgn * 0.9, 0, 0.5), 0.005, 0.03, seg=4)
ell(bm, (sx0, sy0, sz0 + 0.135), (0.013, 0.013, 0.011), seg=6, rings=4)       # pommel
for i in range(6): ell(bm, (sx0 + 0.012 + 0.004 * i * 0.0, sy0 - 0.002 - i * 0.0, sz0 + 0.12 - 0.017 * i), (0.003, 0.003, 0.004), seg=4, rings=3)
attach(arm, "Hero_StilettoBlade", bl, M_GLASS, "Hips", smooth=False)
attach(arm, "Hero_StilettoGuard", bm, M_SILK, "Hips")
attach(arm, "Hero_StilettoGrip", bg, M_LEATH, "Hips")

# ---------- pointed boots ----------
for side, lower, foot, tag in ((1, "LowerLeg.L", "Foot.L", "L"), (-1, "LowerLeg.R", "Foot.R", "R")):
    cx = side * 0.121
    def shaft(r, c, cx=cx):
        a = 2 * math.pi * c; z = 0.26 - r * 0.235
        rad = 0.05 + 0.0 * r + (0.01 if r > 0.8 else 0.0)
        return Vector((cx + rad * math.cos(a), -0.075 + 0.015 * r + rad * math.sin(a) * 1.05, z))
    skinned(arm, "Hero_BootShaft_" + tag, strip(8, 16, shaft), M_LEATH, lambda co, lower=lower, foot=foot: {lower: 1 - smoothstep(0.08, 0.03, co.z), foot: smoothstep(0.08, 0.03, co.z)})
    bm = bmesh.new()
    ell(bm, (cx, -0.13, 0.042), (0.040, 0.095, 0.034), seg=12, rings=7)
    ell(bm, (cx, -0.046, 0.050), (0.042, 0.048, 0.045), seg=10, rings=6)
    cone(bm, (cx, -0.20, 0.033), (0, -1, 0.1), 0.026, 0.08, seg=8)         # pointed toe
    ell(bm, (cx, -0.098, 0.016), (0.048, 0.135, 0.013), seg=12, rings=5)
    ell(bm, (cx, -0.020, 0.025), (0.028, 0.030, 0.030), seg=8, rings=5)    # heel
    attach(arm, "Hero_BootFoot_" + tag, bm, M_LEATH, foot)
    bm = bmesh.new()
    for z, rr in ((0.255, 0.054), (0.15, 0.052)):
        bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=rr, radius2=rr, depth=0.006, matrix=Matrix.Translation((cx, -0.075 + 0.015 * (0.26 - z) / 0.235, z)))
    for i in range(5):
        ell(bm, (cx + side * 0.002, -0.118 - 0.017 * i + 0.0, 0.062 - 0.004 * i), (0.003, 0.012, 0.003), seg=4, rings=3)
    attach(arm, "Hero_BootTrim_" + tag, bm, M_SILK, foot)

print("NS_TOTAL_TRIS", tri_count())
bpy.ops.wm.save_as_mainfile(filepath=OUT + "/nullshade.blend")
bpy.ops.export_scene.gltf(filepath=OUT + "/nullshade.glb", export_format='GLB', export_apply=True,
                          export_animations=False, export_skins=True)
print("NS_DONE")
