"""Hexgear hero: a six-sided logic cube on a slender articulated frame, interlocking bronze and dark-steel faceted plates (Blender 5.x).
Run: blender -b -P build_hexgear.py -- <mechanical.glb> <out_dir>
The cube core (hex emblems, bronze strap frames, spokes) takes the place of torso and head; arms and legs are hex-prism frames with
bronze armour plates, bearing joints (cup + ring + hub) and faceted claw feet and fingers."""
import bpy, bmesh, math, sys, os, random
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mech_common import *

SRC, OUT = sys.argv[-2], sys.argv[-1]
random.seed(51)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
remove_objects("_Head", "_Feet")
TEX = os.path.join(OUT, "tex")

M_BRONZE = make_metal_mat("HG_Bronze", (0.58, 0.40, 0.18), "brass", TEX, 0.40, 0.7, seed=15)
M_STEEL = make_metal_mat("HG_Steel", (0.20, 0.20, 0.21), "oxid", TEX, 0.45, 0.65, seed=16)
M_JOINT = make_metal_mat("HG_Joint", (0.11, 0.105, 0.10), "oxid", TEX, 0.5, 0.6, seed=17, rust=(0.20, 0.12, 0.06))
M_CORE = mat("HG_Core", (0.9, 0.55, 0.12), 0.3, 0.0, emit=(1.0, 0.6, 0.12), strength=2.5)
strip_base(); override_base(M_JOINT)
P = Parts(arm)
X = Vector((1, 0, 0)); Y = Vector((0, 1, 0)); Z = Vector((0, 0, 1))
def S(m, b): return P.bm(m, b, True)
def sg(s, p): return Vector((p[0] * s, p[1], p[2]))

def bar(bm, p0, p1, w, th, nrm, q=0.003):
    p0, p1, nrm = Vector(p0), Vector(p1), Vector(nrm).normalized(); d = (p1 - p0)
    L = d.length; dy = d.normalized(); tx = dy.cross(nrm).normalized()
    slab(bm, (p0 + p1) / 2 + nrm * th / 2, (tx, dy, nrm), (w, L, th), min(q, th / 3, w / 3))

def taper_plate(bm, c, axes, w0, w1, h, th, q=0.008):
    """Long plate wider at the top (w0) than the bottom (w1), chamfered; axes = (tx, dy, oz)."""
    tx, dy, oz = [Vector(a) for a in axes]; c = Vector(c); pts = []
    for sy, w in ((1, w0), (-1, w1)):
        for sx in (1, -1):
            pts += [c + tx * sx * (w / 2 - q) + dy * sy * h / 2 + oz * th / 2,
                    c + tx * sx * w / 2 + dy * sy * (h / 2 - q * (1 if sy > 0 else 2.5)) + oz * (th / 2 - q),
                    c + tx * sx * w / 2 + dy * sy * (h / 2 - q * (1 if sy > 0 else 2.5)) - oz * th / 2]
    hull(bm, pts)

# ---------------------------------------------------------------- the cube
CC = Vector((0, -0.043, 1.545)); W, D, H = 0.36, 0.31, 0.31
bm = P.bm(M_STEEL, "Chest")
slab(bm, CC, (X, Z, Y), (W, H, D), 0.034)
def face(c, n, u, v, hu, hv, hexr, spokes=True, glow=False):
    n, u, v = Vector(n), Vector(u), Vector(v); c = Vector(c)
    bz = P.bm(M_BRONZE, "Chest"); st = P.bm(M_STEEL, "Chest"); jt = P.bm(M_JOINT, "Chest")
    ins = 0.026
    for sgn in (1, -1):                                                                   # border straps
        bar(bz, c + u * (hu - ins) * 1 * sgn - v * (hv - 0.05), c + u * (hu - ins) * sgn + v * (hv - 0.05), 0.022, 0.012, n)
        bar(bz, c + v * (hv - ins) * sgn - u * (hu - 0.05), c + v * (hv - ins) * sgn + u * (hu - 0.05), 0.022, 0.012, n)
    ax = n
    cyl(bz, c + n * 0.009, ax, hexr, 0.018, 6)                                            # outer hex ring
    cyl(st, c + n * 0.015, ax, hexr * 0.78, 0.018, 6)
    cyl(bz, c + n * 0.022, ax, hexr * 0.52, 0.018, 6)
    cyl(jt, c + n * 0.030, ax, hexr * 0.34, 0.012, 6)
    if glow: cone(P.bm(M_CORE, "Chest"), c + n * 0.034, n, hexr * 0.20, 0.026, seg=6, r2=0.0)
    else: cone(bz, c + n * 0.034, n, hexr * 0.20, 0.026, seg=6, r2=0.0)
    if spokes:
        for k in range(6):
            a = math.radians(30 + 60 * k)
            d = u * math.cos(a) + v * math.sin(a)
            p0 = c + d * hexr * 0.95
            edge = min(hu / max(abs(math.cos(a)), 1e-3), hv / max(abs(math.sin(a)), 1e-3)) - ins
            p1 = c + d * min(edge, hexr + 0.075)
            bar(bz, p0 + n * 0.0, p1, 0.016, 0.012, n)
        # dark inset panels between spokes
        for sx in (1, -1):
            for sy in (1, -1):
                slab(st, c + u * sx * (hu * 0.62) + v * sy * (hv * 0.62) + n * 0.002, (u, v, n), (hu * 0.5, hv * 0.5, 0.012), 0.004)
face(CC + Vector((0, -D / 2 - 0.001, 0)), (0, -1, 0), (1, 0, 0), (0, 0, 1), W / 2 - 0.01, H / 2 - 0.01, 0.095, True, True)
face(CC + Vector((0, D / 2 + 0.001, 0)), (0, 1, 0), (-1, 0, 0), (0, 0, 1), W / 2 - 0.01, H / 2 - 0.01, 0.085, True)
face(CC + Vector((W / 2 + 0.001, 0, 0)), (1, 0, 0), (0, 1, 0), (0, 0, 1), D / 2 - 0.01, H / 2 - 0.01, 0.07, True)
face(CC + Vector((-W / 2 - 0.001, 0, 0)), (-1, 0, 0), (0, -1, 0), (0, 0, 1), D / 2 - 0.01, H / 2 - 0.01, 0.07, True)
face(CC + Vector((0, 0, H / 2 + 0.001)), (0, 0, 1), (1, 0, 0), (0, -1, 0), W / 2 - 0.01, D / 2 - 0.01, 0.055, False)
face(CC + Vector((0, 0, -H / 2 - 0.001)), (0, 0, -1), (1, 0, 0), (0, 1, 0), W / 2 - 0.01, D / 2 - 0.01, 0.045, False)
# bronze corner caps
for sx in (1, -1):
    for sy in (1, -1):
        for sz in (1, -1):
            ell(P.bm(M_BRONZE, "Chest"), CC + Vector((sx * (W / 2 - 0.012), sy * (D / 2 - 0.012), sz * (H / 2 - 0.012))), (0.026, 0.026, 0.026), seg=6, rings=3)

# ---------------------------------------------------------------- spine, hex-disc stack and pelvis wedge
for k in range(6):
    cyl(P.bm(M_BRONZE if k % 2 == 0 else M_STEEL, "Torso"), (0, -0.045, 1.35 - k * 0.058), (0, 0, 1), 0.072 - 0.003 * k, 0.026, 6)
for sx in (1, -1):
    tube(P.bm(M_JOINT, "Torso"), (sx * 0.035, -0.07, 1.38), (sx * 0.035, -0.07, 1.03), 0.011, 0.011, seg=6)
    tube(P.bm(M_JOINT, "Torso"), (sx * 0.035, 0.0, 1.38), (sx * 0.035, 0.0, 1.03), 0.011, 0.011, seg=6)
ph = P.bm(M_STEEL, "Hips")
hull(ph, [(-0.17, -0.11, 1.07), (0.17, -0.11, 1.07), (-0.17, 0.04, 1.07), (0.17, 0.04, 1.07), (-0.13, -0.10, 0.94), (0.13, -0.10, 0.94),
          (-0.13, 0.03, 0.94), (0.13, 0.03, 0.94), (0.0, -0.10, 0.80), (0.0, 0.0, 0.86)])
taper_plate(P.bm(M_BRONZE, "Hips"), (0, -0.118, 0.97), (X, -Z, -Y), 0.22, 0.08, 0.24, 0.025, 0.010)
fan_plate(P.bm(M_JOINT, "Hips"), [(-0.03, -0.126, 1.01), (0.03, -0.126, 1.01), (0.0, -0.126, 0.95)], 0.004)
cyl(P.bm(M_BRONZE, "Hips"), (0, -0.045, 1.08), (0, 0, 1), 0.17, 0.03, 6)

# ---------------------------------------------------------------- arms
for s, tg in ((1, "L"), (-1, "R")):
    sh, up, lo, hd = "Shoulder." + tg, "UpperArm." + tg, "LowerArm." + tg, "Hand." + tg
    m = lambda p, s=s: sg(s, p)
    # axle from the cube to a shoulder module
    tube(P.bm(M_JOINT, sh), m((0.16, -0.058, 1.43)), m((0.25, -0.058, 1.43)), 0.028, 0.028, seg=8)
    ell(S(M_JOINT, up), m((0.255, -0.058, 1.43)), (0.045, 0.045, 0.045), seg=10, rings=6)
    cyl(P.bm(M_BRONZE, up), m((0.255, -0.058, 1.43)), (0, 1, 0), 0.05, 0.02, 6)
    # shoulder pod: bronze faceted hex-prism with a dark triangle emblem
    pb = P.bm(M_BRONZE, up); pj = P.bm(M_STEEL, up)
    slab_e(pb, m((0.27, -0.058, 1.50)), (0.13, 0.15, 0.04), (0, s * 0.35, 0), 0.016, 0.0)
    slab_e(pj, m((0.30, -0.058, 1.455)), (0.09, 0.13, 0.04), (0, s * 0.8, 0), 0.012)
    fan_plate(P.bm(M_JOINT, up), [m((0.25, -0.12, 1.545)), m((0.30, -0.12, 1.505)), m((0.22, -0.12, 1.50))], 0.004)
    # upper arm
    tube(P.bm(M_JOINT, up), m((0.27, -0.058, 1.43)), m((0.40, -0.058, 1.43)), 0.040, 0.034, seg=6)
    taper_plate(P.bm(M_BRONZE, up), m((0.335, -0.058, 1.468)), (Vector((0, 1, 0)), Vector((s, 0, 0)), Vector((0, 0, 1))), 0.10, 0.07, 0.15, 0.03, 0.010)
    taper_plate(P.bm(M_STEEL, up), m((0.335, -0.098, 1.43)), (Vector((0, 0, 1)), Vector((s, 0, 0)), Vector((0, -1, 0))), 0.085, 0.06, 0.14, 0.025, 0.008)
    # elbow bearing (hinge axis Z)
    cyl(P.bm(M_STEEL, lo), m((0.41, -0.06, 1.43)), (0, 0, 1), 0.04, 0.07, 10)
    for dz in (0.04, -0.04): cyl(P.bm(M_BRONZE, lo), m((0.41, -0.06, 1.43 + dz)), (0, 0, 1), 0.044, 0.012, 10)
    cyl(P.bm(M_JOINT, lo), m((0.41, -0.06, 1.43 + 0.05)), (0, 0, 1), 0.02, 0.012, 8)
    # forearm
    tube(P.bm(M_JOINT, lo), m((0.42, -0.063, 1.43)), m((0.565, -0.086, 1.43)), 0.036, 0.026, seg=6)
    taper_plate(P.bm(M_BRONZE, lo), m((0.49, -0.07, 1.462)), (Vector((0, 1, 0)), Vector((s, 0, 0)), Vector((0, 0, 1))), 0.08, 0.055, 0.16, 0.026, 0.008)
    taper_plate(P.bm(M_STEEL, lo), m((0.49, -0.07, 1.40)), (Vector((0, 1, 0)), Vector((s, 0, 0)), Vector((0, 0, -1))), 0.07, 0.05, 0.15, 0.022, 0.008)
    cyl(P.bm(M_BRONZE, lo), m((0.575, -0.087, 1.432)), (1, 0, 0), 0.034, 0.02, 8)
    # hand: knuckle plate + faceted thin fingers
    slab_e(P.bm(M_BRONZE, hd), m((0.65, -0.088, 1.448)), (0.11, 0.08, 0.016), (0, 0, 0), 0.006)
    for fb in ("Index", "Middle", "Ring", "Pinky"):
        for seg in (2, 3, 4):
            bn = "%s%d.%s" % (fb, seg, tg)
            bo = arm.data.bones[bn]; a, c = Vector(bo.head_local), Vector(bo.tail_local)
            if seg == 4: c = c + (c - a).normalized() * 0.01
            tube(P.bm(M_STEEL if seg != 3 else M_BRONZE, bn), a - (c - a).normalized() * 0.003, c, 0.0105, 0.0095, seg=6)
    for seg in (2, 3):
        bn = "Thumb%d.%s" % (seg, tg)
        bo = arm.data.bones[bn]; a, c = Vector(bo.head_local), Vector(bo.tail_local)
        if seg == 3: c = c + (c - a).normalized() * 0.01
        tube(P.bm(M_STEEL, bn), a, c, 0.013, 0.011, seg=6)

# ---------------------------------------------------------------- legs
for s, tg in ((1, "L"), (-1, "R")):
    up, lo, ft = "UpperLeg." + tg, "LowerLeg." + tg, "Foot." + tg
    cx = 0.121 * s
    ell(S(M_JOINT, up), (cx, -0.05, 0.965), (0.05, 0.05, 0.05), seg=10, rings=6)
    cyl(P.bm(M_BRONZE, up), (cx + s * 0.04, -0.05, 0.965), (1, 0, 0), 0.05, 0.02, 6)
    tube(P.bm(M_JOINT, up), (cx, -0.05, 0.96), (cx, -0.087, 0.545), 0.052, 0.042, seg=6)
    taper_plate(P.bm(M_BRONZE, up), (cx, -0.098, 0.78), (X, -Z, -Y), 0.150, 0.085, 0.36, 0.035, 0.014)        # front plate
    fan_plate(P.bm(M_JOINT, up), [(cx - 0.025, -0.131, 0.84), (cx + 0.025, -0.131, 0.84), (cx, -0.131, 0.78)], 0.004)
    taper_plate(P.bm(M_STEEL, up), (cx + s * 0.062, -0.065, 0.78), (Y, -Z, X * s), 0.12, 0.07, 0.32, 0.03, 0.010)
    taper_plate(P.bm(M_STEEL, up), (cx, -0.025, 0.78), (X, -Z, Y), 0.14, 0.08, 0.32, 0.03, 0.010)
    # knee bearing
    cyl(P.bm(M_STEEL, lo), (cx, -0.088, 0.535), (1, 0, 0), 0.052, 0.11, 12)
    for dx in (0.062, -0.062): cyl(P.bm(M_BRONZE, lo), (cx + dx, -0.088, 0.535), (1, 0, 0), 0.056, 0.014, 12)
    cyl(P.bm(M_JOINT, lo), (cx + s * 0.075, -0.088, 0.535), (1, 0, 0), 0.03, 0.012, 8)
    taper_plate(P.bm(M_BRONZE, lo), (cx, -0.140, 0.545), (X, -Z, -Y), 0.085, 0.07, 0.10, 0.04, 0.014)          # kneecap
    # shin
    tube(P.bm(M_JOINT, lo), (cx, -0.087, 0.52), (cx, -0.062, 0.08), 0.046, 0.034, seg=6)
    taper_plate(P.bm(M_BRONZE, lo), (cx, -0.130, 0.30), (X, -Z, -Y), 0.11, 0.065, 0.36, 0.032, 0.012)
    taper_plate(P.bm(M_STEEL, lo), (cx, -0.015, 0.33), (X, -Z, Y), 0.11, 0.07, 0.34, 0.05, 0.012)
    taper_plate(P.bm(M_STEEL, lo), (cx + s * 0.058, -0.075, 0.32), (Y, -Z, X * s), 0.10, 0.06, 0.32, 0.028, 0.010)
    # ankle bearing + faceted claw foot
    cyl(P.bm(M_BRONZE, ft), (cx, -0.062, 0.062), (1, 0, 0), 0.04, 0.10, 12)
    cyl(P.bm(M_JOINT, ft), (cx + s * 0.055, -0.062, 0.062), (1, 0, 0), 0.022, 0.012, 8)
    hull(P.bm(M_STEEL, ft), [(cx - 0.04, -0.03, 0.10), (cx + 0.04, -0.03, 0.10), (cx - 0.045, 0.03, 0.04), (cx + 0.045, 0.03, 0.04),
                              (cx - 0.045, 0.03, 0.0), (cx + 0.045, 0.03, 0.0), (cx - 0.05, -0.14, 0.02), (cx + 0.05, -0.14, 0.02), (cx - 0.04, -0.14, 0.06), (cx + 0.04, -0.14, 0.06)])
    taper_plate(P.bm(M_BRONZE, ft), (cx, -0.085, 0.09), (X, -Y, Z), 0.085, 0.06, 0.15, 0.02, 0.008)
    for k in range(3):
        tx = cx + (k - 1) * 0.038
        hull(P.bm(M_BRONZE if k == 1 else M_STEEL, ft), [(tx - 0.015, -0.13, 0.065), (tx + 0.015, -0.13, 0.065), (tx - 0.017, -0.13, 0.0), (tx + 0.017, -0.13, 0.0),
                                                           (tx, -0.235, 0.0), (tx, -0.20, 0.03)])

P.flush("")
print("TRIS", tri_count())
finish(OUT, "hexgear")
