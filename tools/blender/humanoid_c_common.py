"""Geometry foundations adapted from the interrupted humanoid_a_common.py (Claude/Codex batch A).
Batch C owns this independent snapshot; existing shared helpers remain untouched.
Lives next to hero_common.py (which stays untouched). Front is -Y, Z up, feet on z=0, T-pose rest."""
import bpy, bmesh, math, os, random
import numpy as np
from mathutils import Vector, Matrix, Euler
from hero_common import mat, remove_objects, attach, skinned, assign_uv, strip, ell, cone, tube, smoothstep, tri_count
import hero_textures as T

# ----------------------------------------------------------------------------- rig / weights
_SEG = {}


def prep(src, body_mat, pants_mat):
    """Import the group base, drop head + feet, give the body/legs our own materials (nothing generic shows)."""
    bpy.ops.import_scene.gltf(filepath=src)
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    remove_objects("_Head", "_Feet")
    for o in bpy.data.objects:
        if o.type == "MESH" and o.name.endswith(("_Body", "_Pants", "_Legs")):
            m = body_mat if o.name.endswith("_Body") else pants_mat
            o.data.materials.clear(); o.data.materials.append(m)
            for p in o.data.polygons: p.material_index = 0
    _SEG.clear()
    for b in arm.data.bones:
        _SEG[b.name] = (arm.matrix_world @ b.head_local, arm.matrix_world @ b.tail_local)
    return arm


def bone(name):
    return _SEG[name]


def _sd(p, a, b):
    ab = b - a; t = max(0.0, min(1.0, (p - a).dot(ab) / max(1e-9, ab.length_squared)))
    return (p - (a + ab * t)).length


def nearest_w(bones, fall=0.04, minw=0.02):
    """Weight function: soft nearest-bone-segment blend (exp falloff on the distance gap)."""
    cache = {}
    def fn(co):
        key = (round(co.x, 4), round(co.y, 4), round(co.z, 4))
        if key in cache: return cache[key]
        ds = {b: _sd(co, *_SEG[b]) for b in bones}
        dm = min(ds.values())
        ws = {b: math.exp(-(d - dm) / fall) for b, d in ds.items()}
        tot = sum(ws.values())
        out = {b: w / tot for b, w in ws.items() if w / tot > minw}
        s = sum(out.values()); out = {b: w / s for b, w in out.items()}
        cache[key] = out
        return out
    return fn


SPINE = ["Hips", "Abdomen", "Torso", "Chest"]
TORSO_BONES = SPINE + ["Shoulder.L", "Shoulder.R"]
ARM_L = ["Shoulder.L", "UpperArm.L", "LowerArm.L", "Hand.L"]
ARM_R = ["Shoulder.R", "UpperArm.R", "LowerArm.R", "Hand.R"]


def side_leg(s):
    return ["Hips", "UpperLeg." + s, "LowerLeg." + s, "Foot." + s]


# ----------------------------------------------------------------------------- geometry
def blob(bm, c, ax, ay, az, seg=10, rings=6):
    """Ellipsoid with semi-axes given as vectors ax, ay, az (any orientation)."""
    m = Matrix(((ax.x, ay.x, az.x, c[0]), (ax.y, ay.y, az.y, c[1]), (ax.z, ay.z, az.z, c[2]), (0, 0, 0, 1)))
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0, matrix=m)


def blob_dir(bm, c, direction, half_len, r1, r2=None, seg=10, rings=6, up=(0, 0, 1)):
    d = Vector(direction).normalized(); u = Vector(up)
    s = d.cross(u)
    if s.length < 1e-4: s = Vector((1, 0, 0))
    s.normalize(); u2 = s.cross(d).normalized()
    blob(bm, c, d * half_len, s * r1, u2 * (r2 if r2 is not None else r1), seg, rings)


def sweep(bm, pts, radii, sides=8, cap0=True, cap1=True, squash=1.0, up=None):
    """Swept tube along pts (list of Vector) with per-point radius (float or (rA, rB)). Returns ring list."""
    pts = [Vector(p) for p in pts]; n = len(pts)
    rings = []; prev = None
    for i, p in enumerate(pts):
        tan = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        if prev is None:
            ref = Vector(up) if up is not None else Vector((0, 0, 1))
            if abs(tan.dot(ref)) > 0.95: ref = Vector((1, 0, 0))
            a = tan.cross(ref).normalized()
        else:
            a = (prev - tan * prev.dot(tan)).normalized()
        b = tan.cross(a).normalized(); prev = a
        r = radii[i] if isinstance(radii, (list, tuple)) else radii
        ra, rb = (r if isinstance(r, (tuple, list)) else (r, r * squash))
        rings.append([bm.verts.new(p + a * (math.cos(2 * math.pi * k / sides) * ra) + b * (math.sin(2 * math.pi * k / sides) * rb)) for k in range(sides)])
    for i in range(n - 1):
        for k in range(sides):
            bm.faces.new((rings[i][k], rings[i][(k + 1) % sides], rings[i + 1][(k + 1) % sides], rings[i + 1][k]))
    if cap0: bm.faces.new(rings[0][::-1])
    if cap1: bm.faces.new(rings[-1])
    return rings


def lerp(a, b, t):
    return a + (b - a) * t


def catmull(pts, sub=3):
    out = []
    P = [pts[0]] + list(pts) + [pts[-1]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for s in range(sub):
            t = s / sub
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(pts[-1])
    return out


def ring_strip(rows, cols, fn, closed=True):
    """Like strip() but the last column wraps back to the first (cylinders without a seam gap)."""
    bm = bmesh.new()
    vs = [[bm.verts.new(fn(r / (rows - 1), (c / cols) if closed else c / (cols - 1))) for c in range(cols)] for r in range(rows)]
    for r in range(rows - 1):
        for c in range(cols if closed else cols - 1):
            c2 = (c + 1) % cols
            bm.faces.new((vs[r][c], vs[r][c2], vs[r + 1][c2], vs[r + 1][c]))
    layer = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for lp in f.loops:
            vi = [(r, c) for r in range(rows) for c in range(cols) if vs[r][c] == lp.vert][0]
            lp[layer].uv = (vi[1] / cols, 1.0 - vi[0] / (rows - 1))
    for f in bm.faces:       # fix the wrap column so texture does not smear across the whole width
        us = [lp[layer].uv[0] for lp in f.loops]
        if max(us) - min(us) > 0.5:
            for lp in f.loops:
                if lp[layer].uv[0] < 0.5: lp[layer].uv = (lp[layer].uv[0] + 1.0, lp[layer].uv[1])
    return bm


def smooth_obj(o, smooth=True):
    for p in o.data.polygons: p.use_smooth = smooth


def torso_profile(z):
    """Base torso ellipse (centre y, half-width, half-depth) at height z (measured from the base body)."""
    k = [(0.95, -0.050, 0.150, 0.115), (1.05, -0.055, 0.148, 0.115), (1.15, -0.065, 0.134, 0.108),
         (1.28, -0.062, 0.134, 0.112), (1.40, -0.055, 0.150, 0.118), (1.48, -0.050, 0.150, 0.110)]
    if z <= k[0][0]: return k[0][1:]
    for i in range(len(k) - 1):
        if z <= k[i + 1][0]:
            t = (z - k[i][0]) / (k[i + 1][0] - k[i][0])
            return tuple(lerp(k[i][j], k[i + 1][j], t) for j in (1, 2, 3))
    return k[-1][1:]


def torso_pt(z, ang, grow=0.0, pw=2.0):
    """Point on the (super-)ellipse torso at angle ang (0 = front -Y, +pi/2 = +X)."""
    cy, rx, ry = torso_profile(z)
    s, c = math.sin(ang), math.cos(ang)
    x = (abs(s) ** (2 / pw)) * math.copysign(1, s) * (rx + grow)
    y = -(abs(c) ** (2 / pw)) * math.copysign(1, c) * (ry + grow)
    return Vector((x, cy + y, z))


# ----------------------------------------------------------------------------- arm geometry (for sleeves / cracks)
def arm_center(side, x):
    """Centre of the base arm at |x| along the arm (T-pose); returns Vector (side applied)."""
    a = abs(x)
    y = -0.056 if a < 0.334 else -0.056 + (a - 0.334) / (0.568 - 0.334) * (-0.030)
    if a > 0.568: y = -0.086 - (a - 0.568) * 0.01
    return Vector((side * a, y, 1.432))


def arm_radius(x):
    a = abs(x)
    pts = [(0.15, 0.062), (0.22, 0.060), (0.30, 0.057), (0.38, 0.049), (0.45, 0.043), (0.52, 0.037), (0.57, 0.031)]
    if a <= pts[0][0]: return pts[0][1]
    for i in range(len(pts) - 1):
        if a <= pts[i + 1][0]:
            t = (a - pts[i][0]) / (pts[i + 1][0] - pts[i][0]); return lerp(pts[i][1], pts[i + 1][1], t)
    return pts[-1][1]


def sleeve(side, x0, x1, grow0, grow1, rings=9, sides=14, flare=0.0, fold=0.0, seed=0, hem_saw=0.0):
    """Tube around the arm between |x| = x0 and x1 with radius = arm radius + grow."""
    rnd = random.Random(seed)
    ph = [rnd.random() * 6.28 for _ in range(3)]
    def fn(r, c):
        x = lerp(x0, x1, r)
        ctr = arm_center(side, x)
        g = lerp(grow0, grow1, r) + flare * r * r
        a = 2 * math.pi * c
        g += fold * math.sin(a * 5 + ph[0] + r * 3) * (0.4 + 0.6 * r) + fold * 0.5 * math.sin(a * 9 + ph[1])
        rad = arm_radius(x) + g
        xx = x
        if hem_saw and r > 0.9: xx = x + side * hem_saw * (abs(math.sin(a * 3.5 + ph[2])) - 0.5) * (r - 0.9) * 10
        return Vector((side * abs(xx), ctr.y + rad * math.cos(a) * 1.0, ctr.z + rad * math.sin(a)))
    return ring_strip(rings, sides, fn)


def arm_w(side):
    return nearest_w(ARM_L if side > 0 else ARM_R + [], 0.03)


def arm_w_full(side):
    s = "L" if side > 0 else "R"
    return nearest_w(["Chest", "Shoulder." + s, "UpperArm." + s, "LowerArm." + s, "Hand." + s], 0.03)


def crack_path(rnd, p0, p1, wobble=0.012, steps=9):
    """Jagged polyline from p0 to p1 (Vectors)."""
    pts = []
    for i in range(steps + 1):
        t = i / steps
        p = lerp(p0, p1, t)
        if 0 < i < steps:
            p = p + Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))) * wobble
        pts.append(p)
    return pts


def uv_arm_cyl(obj, arm_x_min=0.2):
    """Give the base body per-loop UVs: cylindrical around each arm, around the spine for the rest."""
    me = obj.data
    layer = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        cs = [me.vertices[me.loops[i].vertex_index].co for i in poly.loop_indices]
        mx = sum(c.x for c in cs) / len(cs)
        angs = []; us = []
        for c in cs:
            if abs(mx) > arm_x_min:
                ctr = arm_center(1 if mx > 0 else -1, c.x)
                angs.append(math.atan2(c.z - ctr.z, c.y - ctr.y)); us.append(abs(c.x) * 5.0)
            else:
                angs.append(math.atan2(c.x, -(c.y + 0.05))); us.append(c.z * 5.0)
        a0 = angs[0]
        angs = [a0 + ((a - a0 + math.pi) % (2 * math.pi) - math.pi) for a in angs]
        for li, a, u in zip(poly.loop_indices, angs, us):
            layer.data[li].uv = (u, a / (2 * math.pi))


# ----------------------------------------------------------------------------- hands
def hands(arm, material, nail_mat=None, grow=0.0, tag="", fingers=True):
    """Real hands: palm + 4 fingers (3 phalanges, joint bulges) + thumb, skinned to the finger bones."""
    out = []
    for s, sx in (("L", 1), ("R", -1)):
        bones = ["LowerArm." + s, "Hand." + s] + [f"{f}{i}.{s}" for f in ("Index", "Middle", "Ring", "Pinky") for i in (2, 3, 4)] + [f"Thumb{i}.{s}" for i in (2, 3)]
        bm = bmesh.new()
        h0, h1 = bone("Hand." + s)
        heads = [bone(f"{f}2.{s}")[0] for f in ("Index", "Middle", "Ring", "Pinky")]
        K = sum(heads, Vector()) / 4
        d = (K - h0); L = d.length
        blob_dir(bm, (h0 + K) / 2 + Vector((0, 0, 0.002)), d, L * 0.52 + 0.01, 0.047 + grow, 0.0155 + grow, seg=12, rings=8)     # palm
        blob_dir(bm, h0 + d * 0.08, d, 0.04, 0.034 + grow, 0.022 + grow, seg=10, rings=6)                                          # wrist / heel of palm
        radii = {"Index": 0.0108, "Middle": 0.0112, "Ring": 0.0104, "Pinky": 0.0092}
        for f in ("Index", "Middle", "Ring", "Pinky"):
            pts = [bone(f"{f}2.{s}")[0], bone(f"{f}3.{s}")[0], bone(f"{f}4.{s}")[0], bone(f"{f}4.{s}")[1]]
            r = radii[f] + grow * 0.5
            base = pts[0] - (pts[1] - pts[0]).normalized() * 0.012
            sub = catmull([base] + pts, 2)
            rr = [r * (0.95 - 0.28 * i / (len(sub) - 1) + 0.07 * math.cos(i * math.pi)) for i in range(len(sub))]
            sweep(bm, sub, rr, sides=7, squash=0.88, up=(0, 0, 1))
            tip = pts[-1]
            blob_dir(bm, tip, tip - pts[-2], 0.008, r * 0.66, r * 0.58, seg=7, rings=4)
        t2h = bone("Thumb2." + s)[0]; t3h, t3t = bone("Thumb3." + s)
        tp = [h0 + (t2h - h0) * 0.2, t2h, t3h, t3t]
        sub = catmull(tp, 2)
        sweep(bm, sub, [0.0175 - 0.007 * i / (len(sub) - 1) + grow * 0.5 for i in range(len(sub))], sides=7, squash=0.9, up=(0, 0, 1))
        blob_dir(bm, t3t, t3t - t3h, 0.008, 0.0085, 0.0075, seg=7, rings=4)
        o = skinned(arm, f"Hero_Hand{tag}_{s}", bm, material, nearest_w(bones, 0.012))
        out.append(o)
        if nail_mat is not None:
            nb = bmesh.new()
            for f in ("Index", "Middle", "Ring", "Pinky"):
                p3, p4 = bone(f"{f}4.{s}")
                dd = (p4 - p3).normalized()
                blob_dir(nb, p4 - dd * 0.004 + Vector((0, 0, 0.0075)), dd, 0.0058, 0.0058, 0.0016, seg=6, rings=3)
            skinned(arm, f"Hero_Nails{tag}_{s}", nb, nail_mat, nearest_w([f"{f}4.{s}" for f in ("Index", "Middle", "Ring", "Pinky")], 0.02))
    return out


# ----------------------------------------------------------------------------- face
def build_face(arm, skin, lips, brow, iris, sclera, dark, p=None, tag=""):
    """Sculpted head: cranium, face planes, jaw, cheekbones, brow ridge, nose, ears, eyes with lids, brows, lips.
    p: dict of proportion tweaks. Returns dict of created objects."""
    p = p or {}
    ear = p.get("ear", "round"); ear_len = p.get("ear_len", 0.05); ear_ang = p.get("ear_ang", 0.55)
    jaw = p.get("jaw", 1.0); chin = p.get("chin", 1.0); brow_r = p.get("brow", 1.0); nose_l = p.get("nose", 1.0)
    cheek = p.get("cheek", 1.0); eye_s = p.get("eye", 1.0); slant = math.radians(p.get("slant", 12))
    neck_r = p.get("neck", 0.042); face_w = p.get("face_w", 1.0); skull_h = p.get("skull_h", 1.0)
    eye_x = p.get("eye_x", 0.035); eye_z = p.get("eye_z", 1.641)
    out = {}
    bm = bmesh.new()
    ell(bm, (0, -0.04, 1.655), (0.080 * face_w, 0.104, 0.098 * skull_h), seg=20, rings=14)       # cranium
    ell(bm, (0, -0.085, 1.600), (0.060 * face_w, 0.072, 0.068), seg=16, rings=10)                  # face mass
    ell(bm, (0, -0.100, 1.548), (0.030 * chin, 0.040, 0.034), seg=12, rings=8)                      # chin
    ell(bm, (0, -0.118, 1.532), (0.018 * chin, 0.018, 0.016), seg=10, rings=6)                      # chin point
    for sx in (1, -1):
        ell(bm, (sx * 0.042 * jaw, -0.060, 1.566), (0.020 * jaw, 0.046, 0.036), seg=10, rings=6)    # jaw
        ell(bm, (sx * 0.0495 * face_w, -0.106, 1.597), (0.016 * cheek, 0.014 * cheek, 0.012 * cheek), seg=10, rings=6)   # cheekbone
        ell(bm, (sx * 0.034, -0.133, 1.667), (0.037, 0.013 * brow_r, 0.010 * brow_r), rot=(0, sx * math.radians(14), 0), seg=10, rings=6)   # brow ridge
        ell(bm, (sx * 0.033, -0.128, 1.618), (0.026, 0.010, 0.012), seg=8, rings=5)               # cheek under-eye plane
    for sx in (1, -1):                                                                  # lids frame the eye
        ex = sx * eye_x
        ell(bm, (ex, -0.137, eye_z + 0.0105 * eye_s), (0.0235 * eye_s, 0.0075, 0.0058 * eye_s), rot=(0, sx * slant, 0), seg=10, rings=5)     # upper lid
        ell(bm, (ex, -0.1355, eye_z - 0.0095 * eye_s), (0.0205 * eye_s, 0.0065, 0.0045 * eye_s), rot=(0, sx * slant, 0), seg=10, rings=5)   # lower lid
    tube(bm, (0, -0.138, 1.652), (0, -0.162 - 0.004 * nose_l, 1.608), 0.0105, 0.0135, seg=7)      # nose bridge
    ell(bm, (0, -0.1685 - 0.006 * (nose_l - 1), 1.606), (0.0145, 0.0155 * nose_l, 0.0125), seg=10, rings=6)    # nose tip
    for sx in (1, -1):
        ell(bm, (sx * 0.0155, -0.158, 1.601), (0.0105, 0.0125, 0.0095), seg=8, rings=5)         # nostril wing
        ell(bm, (sx * 0.0085, -0.1575, 1.5925), (0.0055, 0.0070, 0.0040), seg=6, rings=4)
    ell(bm, (0, -0.1455, 1.584), (0.0075, 0.007, 0.0055), seg=6, rings=4)                         # philtrum
    ell(bm, (0, -0.0415, 1.495), (neck_r, 0.042, 0.062), seg=14, rings=7)                         # neck
    out["face"] = attach(arm, "Hero_Face" + tag, bm, skin, "Head")
    # ears
    bm = bmesh.new()
    for sx in (1, -1):
        if ear == "round":
            ell(bm, (sx * 0.082, -0.036, 1.630), (0.007, 0.026, 0.034), rot=(0, 0, sx * math.radians(-12)), seg=10, rings=6)        # helix
            ell(bm, (sx * 0.079, -0.030, 1.612), (0.007, 0.012, 0.011), seg=7, rings=4)                                             # lobe
        else:
            d = Vector((sx * 1.0, -0.1, ear_ang))
            cone(bm, (sx * 0.076, -0.030, 1.628), d, 0.019, ear_len, seg=7, r2=0.0035)
            cone(bm, (sx * 0.078, -0.031, 1.622), d, 0.011, ear_len * 0.8, seg=6, r2=0.003)
            ell(bm, (sx * 0.078, -0.030, 1.612), (0.006, 0.010, 0.010), seg=7, rings=4)
    out["ears"] = attach(arm, "Hero_Ears" + tag, bm, skin, "Head")
    # lips
    bm = bmesh.new()
    ell(bm, (0, -0.1485, 1.5725), (0.023, 0.0105, 0.0066), seg=10, rings=5)
    ell(bm, (0, -0.1455, 1.5605), (0.021, 0.0105, 0.0078), seg=10, rings=5)
    out["lips"] = attach(arm, "Hero_Lips" + tag, bm, lips, "Head")
    bm = bmesh.new()
    ell(bm, (0, -0.1525, 1.5662), (0.020, 0.003, 0.0016), seg=8, rings=3)      # mouth line
    out["mouth"] = attach(arm, "Hero_Mouth" + tag, bm, dark, "Head")
    # brows
    bm = bmesh.new()
    for sx in (1, -1):
        ell(bm, (sx * 0.038, -0.1385, 1.6785), (0.027, 0.0065, 0.0050), rot=(0, sx * math.radians(18), 0), seg=8, rings=4)
        ell(bm, (sx * 0.0215, -0.1405, 1.6715), (0.011, 0.0058, 0.0050), rot=(0, sx * math.radians(30), 0), seg=8, rings=4)
    out["brows"] = attach(arm, "Hero_Brows" + tag, bm, brow, "Head")
    # eyes
    bm = bmesh.new(); bi = bmesh.new(); bp = bmesh.new()
    for sx in (1, -1):
        ex = sx * eye_x
        ell(bm, (ex, -0.1325, eye_z), (0.0165 * eye_s, 0.0085, 0.0095 * eye_s), seg=10, rings=6)
        ell(bi, (ex, -0.1385, eye_z), (0.0083 * eye_s, 0.0032, 0.0083 * eye_s), seg=10, rings=5)
        ell(bp, (ex, -0.1405, eye_z), (0.0038 * eye_s, 0.0018, 0.0038 * eye_s), seg=8, rings=4)
    out["sclera"] = attach(arm, "Hero_EyeWhite" + tag, bm, sclera, "Head")
    out["iris"] = attach(arm, "Hero_Iris" + tag, bi, iris, "Head")
    out["pupil"] = attach(arm, "Hero_Pupil" + tag, bp, dark, "Head")
    return out


# ----------------------------------------------------------------------------- textures
def tex_surface(outdir, name, base, seed, kind="cloth", accent=None, n=1024, wear=0.5, scale=1.0, normal_strength=1.4, emis=None):
    """Variation-rich procedural texture (no repeating cells). Returns (diffuse, normal[, emission]) images.
    kinds: cloth, leather, skin, bone, bark, metal. accent=(rgb) used for stitching/embroidery/veins."""
    x, y = T._grid(n)
    base = np.array(base, np.float32)
    big = T.fbm(n, seed, 5, 3); mid = T.fbm(n, seed + 11, 5, 8); fine = T.fbm(n, seed + 23, 4, 32)
    h = 0.5 * mid + 0.3 * fine
    col = base[None, None, :] * (0.62 + 0.75 * big[..., None]) * (0.88 + 0.24 * mid[..., None])
    emission = None
    if kind == "cloth":
        wob = 3.0 * T.fbm(n, seed + 5, 3, 6)
        wx = np.sin((x * 140 * scale) + wob) * 0.5 + 0.5
        wy = np.sin((y * 150 * scale) + 2.5 * T.fbm(n, seed + 6, 3, 6)) * 0.5 + 0.5
        weave = np.where(((x * 70 * scale).astype(int) + (y * 70 * scale).astype(int)) % 2 == 0, wx, wy)
        thread = 0.8 + 0.2 * weave
        col = col * thread[..., None]
        h = h * 0.5 + 0.8 * weave * 0.3
        slub = T.fbm(n, seed + 7, 3, 20)
        col = col * (0.92 + 0.12 * (slub > 0.62)[..., None])
    elif kind == "leather":
        e, cid = T.voronoi(n, 14, seed)
        grain = T.smooth(0.0, 0.5, e)
        col = col * (0.75 + 0.25 * grain[..., None]) * (0.9 + 0.2 * cid[..., None] * 0.5)
        h = h * 0.4 + 0.5 * grain
        crease = 1 - np.abs(2 * T.fbm(n, seed + 3, 3, 5) - 1)
        col = col * (1 - 0.35 * T.smooth(0.85, 0.99, crease)[..., None])
        h = h - 0.4 * T.smooth(0.85, 0.99, crease)
    elif kind == "skin":
        e, cid = T.voronoi(n, 40, seed)
        pores = T.smooth(0.02, 0.22, e)
        col = col * (0.85 + 0.15 * pores[..., None])
        h = h * 0.5 + 0.35 * pores
    elif kind == "bone":
        streak = T.fbm(n, seed + 9, 4, 3) * 0.5 + 0.5 * np.sin(y * 40 * scale + 6 * T.fbm(n, seed + 1, 3, 4)) * 0.5
        col = col * (0.8 + 0.3 * streak[..., None])
        pit = T.smooth(0.7, 0.8, fine)
        col = col * (1 - 0.35 * pit[..., None])
        h = h * 0.4 + 0.3 * streak - 0.3 * pit
    elif kind == "bark":
        ridge = 1 - np.abs(2 * T.fbm(n, seed + 3, 4, 4) - 1)
        ridge = ridge * (0.7 + 0.3 * np.sin(x * 60 * scale + 5 * mid))
        rv = T.smooth(0.55, 0.95, ridge)
        col = col * (0.6 + 0.6 * rv[..., None])
        h = h * 0.3 + 0.9 * rv
    elif kind == "metal":
        brush = T.fbm(n, seed + 4, 2, 2) * 0.3 + 0.7 * np.sin(y * 300) * 0.05 + 0.5
        col = col * (0.8 + 0.3 * brush[..., None])
    # wear on edges + soot/stains
    edge = np.minimum(np.minimum(x, 1 - x), np.minimum(y, 1 - y))
    e_w = T.smooth(0.07, 0.0, edge) * wear
    stain = T.smooth(0.6, 0.85, T.fbm(n, seed + 31, 4, 3)) * 0.5 * wear
    col = col * (1 - 0.55 * stain[..., None]) * (1 - 0.3 * e_w[..., None])
    if accent is not None:
        a = np.array(accent, np.float32)
        yy = (y * 9 * scale) % 1.0
        stitch = ((np.abs(yy - 0.5) < 0.04) & (((x * 120 * scale) % 1.0) < 0.55)).astype(np.float32)
        stitch *= (T.fbm(n, seed + 41, 2, 4) > 0.3)
        col = col * (1 - stitch[..., None]) + a[None, None, :] * stitch[..., None]
        h = h + 0.3 * stitch
    if emis is not None:
        # glowing fissures: thresholded ridge noise
        r = 1 - np.abs(2 * T.fbm(n, seed + 51, 5, 4) - 1)
        v = T.smooth(0.92, 0.985, r) * (0.4 + 0.6 * T.fbm(n, seed + 52, 3, 6))
        em = np.array(emis, np.float32)
        emission = np.concatenate([v[..., None] * em[None, None, :], np.ones((n, n, 1), np.float32)], -1)
        col = col * (1 - 0.8 * v[..., None]) + em[None, None, :] * v[..., None] * 0.6
        h = h - 0.5 * v
    rgba = np.concatenate([np.clip(col, 0, 1), np.ones((n, n, 1), np.float32)], -1)
    d = T.to_image(name + "_diffuse", rgba, outdir)
    nm = T.to_image(name + "_normal", T.normal_from_height(h.astype(np.float32), normal_strength), outdir, "Non-Color")
    if emission is not None:
        return d, nm, T.to_image(name + "_emission", emission, outdir)
    return d, nm


def tex_alpha_cloth(outdir, name, base, seed, n=512, alpha_lo=0.25, alpha_hi=0.7, vein=None):
    x, y = T._grid(n)
    nz = T.fbm(n, seed, 5, 5)
    v = T.smooth(0.84, 0.97, 1 - np.abs(2 * nz - 1))
    alpha = np.clip((alpha_lo + (alpha_hi - alpha_lo) * nz + 0.35 * v) * (1 - 0.5 * T.smooth(0.85, 1.0, y)), 0, 1)
    b = np.array(base, np.float32)
    col = b[None, None, :] * (0.8 + 0.4 * nz[..., None]) + (np.array(vein, np.float32) * v[..., None] if vein else 0)
    return T.to_image(name + "_diffuse", np.concatenate([np.clip(col, 0, 1), alpha[..., None]], -1), outdir)


def finish(out, slug):
    print(slug.upper() + "_TOTAL_TRIS", tri_count())
    bpy.ops.wm.save_as_mainfile(filepath=f"{out}/{slug}.blend")
    bpy.ops.export_scene.gltf(filepath=f"{out}/{slug}.glb", export_format='GLB', export_apply=True,
                              export_animations=False, export_skins=True)
    print(slug.upper() + "_DONE")


def box(bm, center, size):
    """Small bevel-free hardware; dimensions are full extents."""
    bmesh.ops.create_cube(bm, size=1, matrix=Matrix.Translation(center) @ Matrix.Diagonal((*size, 1)))


def surface_material(out, name, rgb, seed, kind='cloth', metal=0.0, n=512):
    """Nonperiodic broad wear and fine grain; cloth is given a low-amplitude weave."""
    m = mat(name, rgb, rough=0.69 if kind != 'metal' else 0.34, metal=metal)
    x, y = T._grid(n)
    broad = T.fbm(n, seed, 4, 3)
    detail = T.fbm(n, seed + 20, 3, 32)
    h = detail * 0.12
    if kind == 'cloth':
        h += 0.06 * np.sin(x * 530) * np.sin(y * 550)
    elif kind == 'metal':
        h += 0.05 * np.sin(y * 410 + 4 * broad)
    elif kind == 'leather':
        h += 0.13 * T.fbm(n, seed + 7, 3, 70)
    col = np.array(rgb)[None, None, :] * (0.74 + 0.42 * broad[..., None]) * (0.94 + 0.12 * detail[..., None])
    edge = np.minimum(np.minimum(x, 1-x), np.minimum(y, 1-y))
    wear = (1-T.smooth(0.01, 0.07, edge)) * 0.1
    col += wear[..., None] * np.array((0.20, 0.15, 0.08))[None, None, :]
    if kind=='cloth' and name.startswith(('fractureline','emberpact','fallenlight')):
        # Embroidered border is baked at fabric resolution; the wandering stem,
        # angled leaves and broken thread wear differ from repetitive cell grain.
        stem=.055+.014*np.sin(y*21)+.005*np.sin(y*51)
        motif=np.exp(-((x-stem)/.0022)**2)+np.exp(-((x-(1-stem))/.0022)**2)
        for j in range(8):
            yy=.06+j*.125
            for sx in (-1,1):
                for border in (.055,.945):
                    dx=x-(border+sx*.017); dy=y-yy
                    u=dx*.8+dy*sx*.6; v=-dx*sx*.6+dy*.8
                    motif+=np.exp(-(u/.020)**2-(v/.003)**2)
        motif=np.clip(motif,0,1)*(0.45+0.35*broad)
        gold=np.array((.50,.32,.12),np.float32)
        col=col*(1-motif[...,None])+gold[None,None,:]*motif[...,None]
        h+=motif*.12
    rgba = np.concatenate((col, np.ones((n,n,1))), axis=-1)
    T.bind(m, T.to_image(name+'_diffuse', rgba, out), T.to_image(name+'_normal', T.normal_from_height(h, 0.65), out, 'Non-Color'))
    return m


def build_hero(src, out, cfg):
    """Build a race-specific humanoid on the unchanged production skeleton."""
    os.makedirs(out, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    slug = cfg['id']; random.seed(cfg['seed'])
    tex = os.path.join(out, 'tex')
    cloth = surface_material(tex, slug+'_cloth', cfg['cloth'], cfg['seed'], n=1024)
    leather = surface_material(tex, slug+'_leather', (0.10,0.065,0.042), cfg['seed']+3, 'leather')
    plate = surface_material(tex, slug+'_plate', cfg['plate'], cfg['seed']+4, 'metal', 0.65)
    ivory = surface_material(tex, slug+'_ivory', (0.67,0.60,0.46), cfg['seed']+5, 'cloth')
    bronze = mat(slug+'_brass', (0.50,0.31,0.105), 0.36, 0.68)
    skin = surface_material(tex, slug+'_skin', cfg['skin'], cfg['seed']+8, 'skin', n=256)
    hair = mat(slug+'_hair', cfg['hair'], 0.55)
    lips = mat(slug+'_lip', tuple(v*0.60 for v in cfg['skin']), 0.57)
    dark = mat(slug+'_seams', (0.012,0.009,0.008), 0.82)
    eye = mat(slug+'_iris', cfg.get('eye',(0.20,0.12,0.035)), 0.3,
              emit=cfg.get('eye_emit'), strength=0.8)
    white = mat(slug+'_sclera', (0.52,0.47,0.37),0.4)
    arm = prep(src, cloth, leather)
    # Clothes and custom hands replace the complete generic body; preserve its
    # one-sided leg only because the production loader mirrors that base mesh.
    for o in list(bpy.data.objects):
        if o.type == 'MESH' and o.name.endswith('_Body'): bpy.data.objects.remove(o)
    # Smoothly profiled torso, with a slight angular breastplate silhouette.
    def torso(r,c):
        z=1.02+r*0.44; a=c*2*math.pi
        p=torso_pt(z,a,0.009)
        p.y += 0.004*math.sin(c*38+r*7)
        return p
    skinned(arm,'Hero_Tunic',ring_strip(12,28,torso),cloth,nearest_w(SPINE,0.035))
    # Legs and sleeves use the imported skeleton's actual segment positions.
    for s,sx in [('L',1),('R',-1)]:
        leg=side_leg(s)
        def trousers(r,c,s=s,sx=sx):
            z=0.37+r*0.68; a=c*2*math.pi
            rad=(0.068+0.030*r+0.004*math.sin(r*36+c*17))
            return Vector((sx*(0.12+0.005*math.sin(r*3)), -0.065, z))+Vector((rad*math.cos(a),rad*math.sin(a),0))
        skinned(arm,'Hero_Trousers_'+s,ring_strip(15,16,trousers),leather,nearest_w(leg,0.025))
        smat=ivory if cfg.get('split') and sx<0 else cloth
        skinned(arm,'Hero_Sleeve_'+s,sleeve(sx,0.14,0.575,0.010,0.004,fold=0.005,seed=cfg['seed']),smat,arm_w_full(sx))
        def boot(r,c,sx=sx):
            z=0.05+r*0.43; a=c*2*math.pi
            rad=0.056+0.010*r+0.003*math.sin(r*30+c*10)
            return Vector((sx*0.121+rad*math.cos(a),-0.07+rad*math.sin(a),z))
        skinned(arm,'Hero_Boot_'+s,ring_strip(10,16,boot),leather,nearest_w(leg,0.025))
        bm=bmesh.new()
        ell(bm,(sx*0.121,-0.13,0.049),(0.052,0.105,0.043),seg=12,rings=6)
        box(bm,(sx*0.121,-0.10,0.016),(0.106,0.24,0.025))
        attach(arm,'Hero_Toe_'+s,bm,leather,'Foot.'+s)
        # Rings, buckles and knee caps stay on the appropriate limb bones.
        bm=bmesh.new()
        for z in (0.16,0.39):
            box(bm,(sx*0.123,-0.126,z),(0.12,0.025,0.026))
        attach(arm,'Hero_BootStraps_'+s,bm,leather,'LowerLeg.'+s)
        bm=bmesh.new()
        for z in (0.16,0.39): box(bm,(sx*0.155,-0.143,z),(0.026,0.012,0.031))
        attach(arm,'Hero_BootBuckles_'+s,bm,bronze,'LowerLeg.'+s)
    hands(arm,skin if slug in ('fallenlight','glitchkin','scaleworn') else leather, bronze if slug=='scaleworn' else None)
    # A tailored skirt consists of individual overlapping pointed panels. Its
    # lower half blends to the corresponding upper leg, rather than rigid hips.
    count=10 if slug != 'glitchkin' else 2
    length=cfg.get('hem',0.48)
    for k in range(count):
        angle=2*math.pi*k/count
        if slug=='glitchkin': angle=(0,math.pi)[k]
        def panel(r,c,angle=angle,k=k):
            width=.95 if slug=='glitchkin' else 2*math.pi/count+0.10
            a=angle+(c-.5)*width
            rad=0.18+(.045 if slug=='glitchkin' else .10)*r+0.010*math.sin(c*12+k)*r
            hem=length+0.09*abs(c-.5)*2+0.018*math.sin(c*21+k)
            if slug=='glitchkin': hem=length+.009*math.sin(c*13+k)
            return Vector((rad*math.sin(a),-0.05-rad*0.8*math.cos(a),1.02+r*(hem-1.02)))
        def weights(co):
            t=smoothstep(1.0,0.45,co.z)*0.7
            return {'Hips':1-t, 'UpperLeg.L' if co.x>0 else 'UpperLeg.R':t}
        pm=ivory if cfg.get('split') and math.sin(angle)<0 else cloth
        if slug=='glitchkin': pm=leather
        skinned(arm,f'Hero_CoatPanel{k}',strip(13,7,panel),pm,weights)
        skinned(arm,f'Hero_Hem{k}',strip(2,7,lambda r,c: panel(0.98+r*0.02,c)+Vector((0,-0.002,0))),ivory if slug=='glitchkin' else bronze,weights)
    # Belt and diagonal harness avoid flat one-piece torsos.
    bm=bmesh.new()
    for z in (1.025,1.075):
        for i in range(24):
            a0=2*math.pi*i/24; a1=2*math.pi*(i+1)/24
            tube(bm,(0.18*math.sin(a0),-.055-.13*math.cos(a0),z),(0.18*math.sin(a1),-.055-.13*math.cos(a1),z),.013,.013,4)
    attach(arm,'Hero_DoubleBelt',bm,leather,'Hips')
    bm=bmesh.new(); box(bm,(0,-.197,1.05),(.045,.018,.047))
    attach(arm,'Hero_Buckle',bm,bronze,'Hips')
    def strap(r,c):
        z=1.09+r*.36; x=-.13+r*.26+(c-.5)*.038
        return Vector((x,-.222+.020*abs(x)/.13,z))
    skinned(arm,'Hero_ChestHarness',strip(12,3,strap),leather,nearest_w(SPINE,.04))
    if slug == 'glitchkin':
        def bib(r,c):
            x=(c-.5)*(.21+.015*r)
            return Vector((x,-.207-.002*math.sin(c*17+r*4),1.10+r*.28))
        skinned(arm,'Hero_LeatherApronBib',strip(10,9,bib),leather,nearest_w(SPINE,.035))
        bm=bmesh.new()
        for x in (-.08,.08):
            box(bm,(x,-.199,1.39),(.025,.016,.022))
            for z in (1.18,1.30): ell(bm,(x,-.20,z),(.004,.004,.004),seg=6,rings=4)
        attach(arm,'Hero_ApronRivets',bm,bronze,'Chest')
    elif slug in ('fractureline','emberpact'):
        for half in (-1,1):
            def cuirass(r,c,half=half):
                z=1.11+r*.30
                x=half*(.008+c*(.115+.022*r))
                y=-.207+.026*(abs(x)/.14)**2-.008*math.sin(r*math.pi)
                return Vector((x,y,z))
            m=ivory if slug=='fractureline' and half<0 else plate
            skinned(arm,'Hero_ChestPlate'+str(half),strip(9,8,cuirass),m,nearest_w(SPINE,.035))
            # Gold inset curves are continuous on the material, not floating blobs.
            def filigree(r,c,half=half):
                z=1.14+r*.24
                x=half*(.035+.016*math.sin(r*9)+(c-.5)*.003)
                return Vector((x,-.220+.002*math.sin(r*math.pi),z))
            skinned(arm,'Hero_CuirassEngraving'+str(half),strip(24,2,filigree),bronze,nearest_w(SPINE,.035))
    # Pouches have flaps, studs and tool loops; repeat at waist only.
    for sx in (-1,1):
        bm=bmesh.new(); box(bm,(sx*.17,-.17,.97),(.085,.06,.12)); box(bm,(sx*.17,-.205,1.015),(.09,.018,.045))
        attach(arm,f'Hero_Pouch{sx}',bm,leather,'Hips',smooth=False)
        bm=bmesh.new(); ell(bm,(sx*.17,-.217,1.00),(.007,.006,.007),seg=6,rings=4)
        attach(arm,f'Hero_PouchStud{sx}',bm,bronze,'Hips')
    # Three overlapping arched plates on each shoulder and segmented bracers.
    if slug!='fallenlight':
        for s,sx in [('L',1),('R',-1)]:
            for j in range(3):
                def shoulder(r,c,j=j,sx=sx):
                    a=(c-.5)*math.pi*1.12; rad=.084-j*.007
                    return Vector((sx*(.13+j*.047+r*.065),-.055-rad*math.sin(a),1.425+rad*math.cos(a)))
                m=ivory if cfg.get('split') and sx<0 else plate
                plate_bone=('Shoulder.' if j==0 else 'UpperArm.')+s
                attach(arm,f'Hero_Shoulder{j}_{s}',strip(4,13,shoulder),m,plate_bone,smooth=False)
                attach(arm,f'Hero_ShoulderRim{j}_{s}',strip(2,13,lambda r,c: shoulder(.94+r*.06,c)+Vector((0,0,.002))),bronze,plate_bone)
            if slug!='glitchkin':
                def bracer(r,c,sx=sx):
                    a=(c-.5)*math.pi*1.7
                    rad=.049-r*.014
                    return Vector((sx*(.39+r*.17),-.065-rad*math.cos(a),1.432+rad*math.sin(a)))
                attach(arm,'Hero_Bracer_'+s,strip(7,13,bracer),plate,'LowerArm.'+s)
    # Face and hair are built after costume so the head remains fully visible.
    if slug=='scaleworn':
        dragon_head(arm,skin,plate,bronze,eye,dark)
    else:
        proportions={'ear':'point','ear_len':.035,'face_w':.96,'jaw':.94}
        if slug=='glitchkin': proportions.update(face_w=1.1,nose=1.5,ear_len=.065,ear_ang=-.2,eye=.85)
        if slug=='emberpact': proportions.update(face_w=.91,jaw=.85,chin=.85)
        face_parts=build_face(arm,skin,lips,hair,eye,white,dark,proportions)
        # Fuse overlapping facial construction masses into a continuous sculpt.
        obj=face_parts['face']
        bpy.context.view_layer.objects.active=obj
        remesh=obj.modifiers.new('Continuous facial sculpt','REMESH')
        remesh.mode='VOXEL'; remesh.voxel_size=.0045
        bpy.ops.object.modifier_apply(modifier=remesh.name)
        face_tris=sum(len(p.vertices)-2 for p in obj.data.polygons)
        dec=obj.modifiers.new('Facial budget','DECIMATE'); dec.ratio=min(1.0,2400/max(1,face_tris))
        bpy.ops.object.modifier_apply(modifier=dec.name)
        for poly in obj.data.polygons: poly.use_smooth=True
        if slug=='fractureline':
            light_skin=mat('fractureline_lightPigment',(.57,.42,.32),.67)
            obj=face_parts['face']; obj.data.materials.append(light_skin)
            for poly in obj.data.polygons:
                if poly.center.x < 0: poly.material_index=1
        # A closed cranial cap with swept locks rather than an exposed sphere.
        def scalp(r,c):
            a=c*2*math.pi
            theta=.05+r*(1.45+.18*math.cos(a))
            return Vector((.088*math.sin(theta)*math.sin(a),-.032+.112*math.sin(theta)*math.cos(a),1.65+.108*math.cos(theta)))
        attach(arm,'Hero_HairCap',ring_strip(8,24,scalp),hair,'Head')
        for side in (-1,1):
            bm=bmesh.new()
            for j in range(10):
                a=math.pi*(j/9)
                x=side*(.07+.014*math.sin(j*2)); y=-.015+.09*math.cos(a)
                z=1.69-.04*math.sin(a)
                endz=1.49 if slug in ('fractureline','fallenlight') else 1.61
                if slug=='glitchkin': endz=1.65+random.uniform(-.01,.03)
                pts=[Vector((x,y,z)),Vector((x+side*.02,y+.025,z-.04)),Vector((x+side*.01,y+.045,endz))]
                sweep(bm,catmull(pts,3),[.014*(1-i/7*.8) for i in range(7)],sides=5)
            mh=ivory if cfg.get('split') and side<0 else hair
            attach(arm,f'Hero_Locks{side}',bm,mh,'Head')
    if slug=='glitchkin': engineer_details(arm,bronze,leather,dark,ivory)
    if slug=='emberpact':
        infernal_details(arm,leather,bronze,skin,ivory)
        bm=bmesh.new(); ell(bm,(0,.075,1.655),(.062,.047,.047),seg=12,rings=7)
        attach(arm,'Hero_TiedHairBun',bm,hair,'Head')
    if slug in ('fractureline','fallenlight','scaleworn'): shawl(arm,ivory if slug=='fallenlight' else cloth,bronze,slug)
    if slug=='fallenlight':
        halo(arm,bronze,eye)
        bm=bmesh.new()
        for sx in (-1,1):
            for j in range(6):
                tube(bm,(sx*(.014+j*.006),-.134,1.557+j*.002),(sx*(.008+j*.005),-.143,1.533+j*.002),.006,.003,5)
            tube(bm,(sx*.003,-.16,1.589),(sx*.025,-.153,1.579),.004,.003,5)
        attach(arm,'Hero_ShortBeard',bm,hair,'Head')
    if slug=='scaleworn':
        dragon_tail(arm,skin,bronze)
        for s,sx in [('L',1),('R',-1)]:
            obj=bpy.data.objects.get('Hero_Toe_'+s)
            if obj: bpy.data.objects.remove(obj)
            bm=bmesh.new(); claws=bmesh.new()
            ell(bm,(sx*.12,-.11,.065),(.065,.09,.055),seg=12,rings=6)
            for j in range(4):
                x=sx*.12+(j-1.5)*.031
                tube(bm,(x,-.12,.055),(x,-.222,.032),.019,.012,7)
                cone(claws,(x,-.218,.035),(0,-1,-.22),.011,.040,seg=6)
            attach(arm,'Hero_DraconicFoot_'+s,bm,skin,'Foot.'+s)
            attach(arm,'Hero_Claws_'+s,claws,ivory,'Foot.'+s)
    if slug=='glitchkin':
        # The unchanged skeleton is human-sized; the authored oversized head and
        # broad tunic preserve the gnome silhouette after runtime height scaling.
        for o in bpy.data.objects:
            if o.type=='MESH' and o.parent_type=='BONE' and o.parent_bone=='Head':
                for v in o.data.vertices:
                    v.co=Vector((0,-.04,1.64))+(v.co-Vector((0,-.04,1.64)))*1.22
    # Every mesh generated procedurally gets usable UVs, including hand/face
    # primitives. smart_project is only the fallback for small untextured bits.
    for o in bpy.data.objects:
        if o.type=='MESH' and o.name.startswith('Hero_') and not o.data.uv_layers:
            uv=o.data.uv_layers.new(name='UVMap')
            for p in o.data.polygons:
                for li in p.loop_indices:
                    co=o.data.vertices[o.data.loops[li].vertex_index].co
                    uv.data[li].uv=(co.x*2.7+co.y,co.z*1.7)
    finish(out,slug)


def engineer_details(arm,brass,leather,dark,ivory):
    # Brass eyepiece with open lens, screws, articulated braces and tool apron.
    bm=bmesh.new()
    for i in range(24):
        a=2*math.pi*i/24; b=2*math.pi*(i+1)/24
        tube(bm,(.035+.030*math.cos(a),-.156,1.643+.030*math.sin(a)),(.035+.030*math.cos(b),-.156,1.643+.030*math.sin(b)),.006,.006,5)
    for x in (-.006,.075):
        for z in (1.61,1.675): ell(bm,(x,-.158,z),(.005,.006,.005),seg=6,rings=4)
    attach(arm,'Hero_PrecisionEyepiece',bm,brass,'Head')
    bm=bmesh.new(); ell(bm,(.035,-.156,1.643),(.024,.003,.024),seg=16,rings=6)
    attach(arm,'Hero_SmokyLens',bm,dark,'Head')
    bm=bmesh.new()
    # Short forked beard leaves mouth and cheeks clear.
    for j in range(9):
        x=(j-4)*.007
        tube(bm,(x,-.137,1.55),(x*.55,-.15,1.51-abs(x)*.15),.009,.003,5)
    attach(arm,'Hero_WhiteGoatee',bm,ivory,'Head')
    bm=bmesh.new()
    for j in range(24):
        a=j*2*math.pi/24
        theta=.55+.24*math.sin(j*2.1)
        p=Vector((.088*math.sin(theta)*math.sin(a),-.032+.112*math.sin(theta)*math.cos(a),1.65+.108*math.cos(theta)))
        q=p+Vector((.014*math.cos(a),.014*math.sin(a),.006))
        sweep(bm,catmull([p,q,q+Vector((.012*math.cos(a),.012*math.sin(a),-.015))],3),[.009-i*.001 for i in range(7)],sides=6)
    attach(arm,'Hero_TousledWhiteCurls',bm,ivory,'Head')
    scarf=mat('glitchkin_burgundy_scarf',(.16,.045,.025),.85)
    def neck_wrap(r,c):
        a=c*2*math.pi
        rad=.060+.009*math.sin(r*8+c*13)
        return Vector((rad*math.sin(a),-.04-rad*math.cos(a),1.45+r*.075))
    skinned(arm,'Hero_NeckScarf',ring_strip(9,24,neck_wrap),scarf,nearest_w(['Neck','Chest'],.03))
    for s,sx in [('L',1),('R',-1)]:
        for bone,z,x in [('LowerArm.'+s,1.435,.47),('LowerLeg.'+s,.31,.12)]:
            bm=bmesh.new()
            if 'Arm' in bone:
                for y in (-.12,.015): tube(bm,(sx*.35,y,z),(sx*.55,y,z),.009,.009,8)
                ell(bm,(sx*.35,-.12,z),(.025,.010,.025),seg=12,rings=6)
            else:
                for dx in (-.055,.055): tube(bm,(sx*x+dx,-.07,.16),(sx*x+dx,-.07,.47),.009,.009,8)
                ell(bm,(sx*x,-.132,.46),(.035,.012,.03),seg=12,rings=6)
            attach(arm,'Hero_Chassis_'+bone,bm,brass,bone)
    bm=bmesh.new(); box(bm,(0,.105,1.29),(.14,.06,.16))
    for sx in (-1,1): tube(bm,(sx*.035,.14,1.21),(sx*.12,.11,1.08),.013,.013,8)
    attach(arm,'Hero_BackChassis',bm,brass,'Chest',smooth=False)
    bm=bmesh.new()
    for j in range(5):
        x=-.10+j*.05
        tube(bm,(x,-.225,.82),(x,-.225,.98),.007,.007,6)
        box(bm,(x,-.225,.97),(.018,.009,.025))
    attach(arm,'Hero_ApronTools',bm,brass,'Hips')


def infernal_details(arm,plate,brass,skin,parchment):
    bm=bmesh.new()
    for sx in (-1,1):
        pts=[Vector((sx*.066,-.015,1.72)),Vector((sx*.11,.005,1.79)),Vector((sx*.17,-.005,1.79)),Vector((sx*.185,-.025,1.72)),Vector((sx*.16,-.05,1.69))]
        curve=catmull(pts,3)
        sweep(bm,curve,[.027*(1-i/(len(curve)-1))+.002 for i in range(len(curve))],sides=10)
    attach(arm,'Hero_CurvedHorns',bm,plate,'Head')
    # Thin long tail with a distinct spear tip; rigid to hips, documented limitation.
    bm=bmesh.new(); pts=catmull([Vector((0,.09,.98)),Vector((.13,.18,.72)),Vector((.29,.15,.38)),Vector((.35,.03,.15)),Vector((.29,-.03,.20))],5)
    sweep(bm,pts,[.027*(1-i/(len(pts)-1))+.003 for i in range(len(pts))],sides=9)
    cone(bm,pts[-1],(-.3,-.1,.8),.023,.10,seg=4)
    attach(arm,'Hero_InfernalTail',bm,skin,'Hips')
    for sx,z in [(-1,1.39),(1,.86)]:
        bm=bmesh.new(); box(bm,(sx*.13,-.195,z),(.061,.015,.073))
        attach(arm,f'Hero_ContractFrame{z}',bm,brass,'Chest' if z>1 else 'Hips',smooth=False)
        bm=bmesh.new(); box(bm,(sx*.13,-.205,z),(.049,.008,.058))
        attach(arm,f'Hero_ContractPaper{z}',bm,parchment,'Chest' if z>1 else 'Hips',smooth=False)


def shawl(arm,cloth,gold,slug):
    def point(r,c):
        a=c*2*math.pi; z=1.51-r*.14
        rad=.07+r*.19+.013*math.sin(c*35+r*10)
        return Vector((rad*math.sin(a),-.045-rad*.72*math.cos(a),z+.012*math.sin(c*19)))
    skinned(arm,'Hero_FoldedShawl',ring_strip(12,36,point),cloth,nearest_w(['Chest','Shoulder.L','Shoulder.R'],.045))
    if slug=='fallenlight':
        def cape(r,c):
            x=(c-.5)*(.38+r*.20)
            return Vector((x,.10+r*.08+.022*math.sin(c*38+r*2),1.45-r*1.12-.055*abs(math.sin(c*19))*r*r))
        skinned(arm,'Hero_TatteredMantle',strip(20,28,cape),cloth,nearest_w(SPINE+['UpperLeg.L','UpperLeg.R'],.06))
        # Emblem embroidery constructed as rays so it reads at gameplay scale.
        bm=bmesh.new()
        for i in range(12):
            a=i*2*math.pi/12
            tube(bm,(.018*math.cos(a),-.307,.62+.018*math.sin(a)),(.062*math.cos(a),-.307,.62+.062*math.sin(a)),.002,.001,4)
        attach(arm,'Hero_SunEmbroidery',bm,gold,'Hips')


def halo(arm,gold,light):
    bm=bmesh.new()
    for lo,hi in [(15,77),(91,154),(193,236),(253,312),(329,350)]:
        n=max(3,int((hi-lo)/5))
        for i in range(n):
            a=math.radians(lo+(hi-lo)*i/n); b=math.radians(lo+(hi-lo)*(i+1)/n)
            tube(bm,(.15*math.sin(a),.035,1.69+.15*math.cos(a)),(.15*math.sin(b),.035,1.69+.15*math.cos(b)),.004,.004,6)
    for angle in (40,125,205,290):
        a=math.radians(angle); p=Vector((.15*math.sin(a),.035,1.69+.15*math.cos(a)))
        tube(bm,p,p+Vector((0,0,-.065)),.002,.002,5)
        cone(bm,p+Vector((0,0,-.055)),(0,0,-1),.009,.035,seg=4)
    attach(arm,'Hero_SeveredHalo',bm,gold,'Head')


def dragon_head(arm,skin,scales,brass,eye,dark):
    bm=bmesh.new()
    ell(bm,(0,-.025,1.65),(.075,.10,.11),seg=16,rings=10)
    ell(bm,(0,-.134,1.625),(.065,.105,.046),seg=14,rings=8)
    ell(bm,(0,-.145,1.588),(.057,.09,.020),seg=12,rings=6)
    ell(bm,(0,-.025,1.51),(.052,.05,.065),seg=12,rings=6)
    for sx in (-1,1):
        ell(bm,(sx*.055,-.107,1.671),(.035,.057,.018),rot=(0,sx*.25,0),seg=10,rings=5)
    attach(arm,'Hero_DraconicHead',bm,skin,'Head')
    bm=bmesh.new(); black=bmesh.new(); armor=bmesh.new()
    for sx in (-1,1):
        ell(bm,(sx*.062,-.14,1.658),(.018,.009,.012),seg=12,rings=6)
        ell(black,(sx*.062,-.147,1.658),(.002,.003,.010),seg=6,rings=4)
        ell(black,(sx*.035,-.229,1.628),(.008,.003,.004),seg=8,rings=4)
        pts=catmull([Vector((sx*.055,.015,1.72)),Vector((sx*.10,.04,1.77)),Vector((sx*.14,.11,1.75))],4)
        sweep(armor,pts,[.025*(1-i/(len(pts)-1))+.001 for i in range(len(pts))],sides=8)
        for j in range(6): cone(armor,(sx*.065,.025+j*.009,1.70-j*.022),(sx*.8,.5,.45),.021,.047,seg=4)
    tube(black,(-.052,-.217,1.602),(.052,-.217,1.602),.002,.002,5)
    attach(arm,'Hero_DragonEyes',bm,eye,'Head')
    attach(arm,'Hero_DragonMouth',black,dark,'Head')
    attach(arm,'Hero_DragonCrown',armor,scales,'Head',smooth=False)
    # Inverted scales are actual overlapping diamond plates, not painted cells.
    for side in (-1,1):
        bm=bmesh.new()
        for row in range(7):
            z=1.43-row*.047
            for col in range(5):
                x=(col-2)*.052+(row%2)*.019
                if abs(x)>.145: continue
                y=(-.183 if side<0 else .079)+x*x*(1.7 if side<0 else -1.7)
                verts=[bm.verts.new((x-.029,y,z)),bm.verts.new((x,y-.008*side,z+.020)),bm.verts.new((x+.029,y,z)),bm.verts.new((x,y-.018*side,z-.047))]
                bm.faces.new(verts)
        attach(arm,'Hero_InvertedMail'+str(side),bm,scales,'Chest',smooth=False)


def dragon_tail(arm,skin,gold):
    bm=bmesh.new(); pts=catmull([Vector((0,.08,.97)),Vector((.12,.21,.70)),Vector((.24,.26,.40)),Vector((.29,.18,.15)),Vector((.40,.02,.11))],5)
    sweep(bm,pts,[.065*(1-i/(len(pts)-1))+.005 for i in range(len(pts))],sides=12)
    attach(arm,'Hero_DragonTail',bm,skin,'Hips')
    bm=bmesh.new()
    for i in range(2,len(pts)-2):
        p=pts[i]; cone(bm,p+Vector((0,0,.02)),(0,.3,.8),.018*(1-i/len(pts))+.004,.036,seg=4)
    attach(arm,'Hero_TailScutes',bm,gold,'Hips',smooth=False)
