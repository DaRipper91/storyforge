"""Helpers for the Humanoid batch-A heroes (ashenborn, hollowsong, veilborn, thornweft, ashcrown).
Lives next to hero_common.py (which stays untouched). Front is -Y, Z up, feet on z=0, T-pose rest."""
import bpy, bmesh, math, os, random, json, hashlib
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
    # Replace the base hands rather than drawing a second set over them.
    for o in list(bpy.data.objects):
        if o.type == 'MESH' and o.name.endswith('_Body'):
            bm = bmesh.new(); bm.from_mesh(o.data)
            cut = [v for v in bm.verts if abs((o.matrix_world @ v.co).x) > 0.17]
            bmesh.ops.delete(bm, geom=cut, context='VERTS')
            bm.to_mesh(o.data); bm.free()
    # Keep the runtime-mirrored base leg as a proper inner trouser lining, inset
    # below the authored garment instead of letting its box silhouette protrude.
    for o in list(bpy.data.objects):
        if o.type == 'MESH' and o.name.endswith(('_Pants','_Legs')):
            for v in o.data.vertices:
                p = o.matrix_world @ v.co
                cx = .121 if p.x >= 0 else -.121
                p.x = cx + (p.x-cx)*.58
                p.y = -.07 + (p.y+.07)*.58
                v.co = o.matrix_world.inverted() @ p
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
    # Content-keyed scratch cache keeps geometry iteration independent of expensive baking.
    spec = [list(base), seed, kind, accent, n, wear, scale, normal_strength, emis]
    digest = hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()
    marker = os.path.join(outdir, name + ".sha256")
    suffixes = ["_diffuse", "_normal"] + (["_emission"] if emis else [])
    paths = [os.path.join(outdir, name + sf + ".png") for sf in suffixes]
    if os.path.exists(marker) and open(marker).read() == digest and all(os.path.exists(f) for f in paths):
        imgs = [bpy.data.images.load(f, check_existing=True) for f in paths]
        imgs[1].colorspace_settings.name = "Non-Color"
        for im in imgs: im.pack()
        return tuple(imgs)
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
        pores = T.smooth(0.24, 0.78, fine)
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
    with open(marker, "w") as cache_file: cache_file.write(digest)
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
    # Preserve authored normal-map detail in both the standalone GLB and source .blend.
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        obj.data.validate(clean_customdata=True)
        if obj.name.startswith('Hero_') and not obj.data.uv_layers:
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.uv.smart_project(island_margin=0.02, area_weight=0.0)
            bpy.ops.object.mode_set(mode='OBJECT')
    print(slug.upper() + "_TOTAL_TRIS", tri_count())
    bpy.ops.wm.save_as_mainfile(filepath=f"{out}/{slug}.blend")
    bpy.ops.export_scene.gltf(filepath=f"{out}/{slug}.glb", export_format='GLB', export_apply=True,
                              export_animations=False, export_skins=True)
    print(slug.upper() + "_DONE")
