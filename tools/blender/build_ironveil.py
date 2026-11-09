"""Ironveil hero: slender origami-steel automaton on the mechanical shared-skeleton base (Blender 5.x).
Run: blender -b -P build_ironveil.py -- <mechanical.glb> <out_dir>
Overlapping folded-steel lamellae over an oxidised inner frame, brass barrel hinges at every joint, a brass spine, a faceted
beak-like helmet with amber eye slits, a long skirt of spike lamellae, pointed heeled shoes and a coiled cable at the hip."""
import bpy, bmesh, math, sys, os, random
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mech_common import *

SRC, OUT = sys.argv[-2], sys.argv[-1]
random.seed(21)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
remove_objects("_Head", "_Feet")
TEX = os.path.join(OUT, "tex")

M_STEEL = make_metal_mat("IV_Steel", (0.50, 0.49, 0.47), "brushed", TEX, 0.38, 0.92, seed=2)
M_DARK = make_metal_mat("IV_Oxid", (0.24, 0.23, 0.22), "oxid", TEX, 0.5, 0.85, seed=5)
M_BRASS = make_metal_mat("IV_Brass", (0.66, 0.50, 0.22), "brass", TEX, 0.3, 1.0, seed=8)
M_EYE = mat("IV_Eye", (1.0, 0.55, 0.08), 0.2, 0.0, emit=(1.0, 0.5, 0.05), strength=6.0)
M_CABLE = mat("IV_Cable", (0.10, 0.10, 0.10), 0.55, 0.6)
strip_base(); override_base(M_DARK)
P = Parts(arm)
FRONT = Vector((0, -1, 0)); X = Vector((1, 0, 0)); Z = Vector((0, 0, 1))

# ---------------------------------------------------------------- torso lamellae (back left open for the brass spine)
torso_t = interp([(0.0, 0.100), (0.17, 0.112), (0.45, 0.090), (0.70, 0.082), (0.88, 0.102), (1.0, 0.115)])
torso_y = interp([(0.0, 0.075), (0.17, 0.082), (0.45, 0.070), (0.70, 0.066), (0.88, 0.080), (1.0, 0.085)])
TS = Sweep((0, -0.055, 1.47), (0, -0.06, 0.95), X, FRONT, torso_t, torso_y)
BACK = 1.5 * math.pi
for bone, ta, tb, rows in (("Chest", 0.0, 0.17, 1), ("Torso", 0.17, 0.60, 3), ("Abdomen", 0.60, 0.90, 2)):
    shingles(P.bm(M_STEEL, bone), TS, ta, tb, rows, 11, hw=0.34, lift=0.008, flare=0.010, fold=0.006, jitter=0.07, a0=BACK + 0.34, a1=BACK + 2 * math.pi - 0.34, overlap=2.3)

# big diagonal chest/hip facets (origami folds across the sternum)
bm = P.bm(M_STEEL, "Chest")
fan_plate(bm, [(-0.075, -0.128, 1.44), (0.02, -0.132, 1.46), (0.10, -0.10, 1.35), (0.015, -0.13, 1.27)], 0.014)
fan_plate(bm, [(0.075, -0.128, 1.44), (-0.02, -0.132, 1.46), (-0.10, -0.10, 1.33), (-0.01, -0.131, 1.30)], 0.012)
fan_plate(bm, [(-0.05, -0.122, 1.47), (0.05, -0.122, 1.47), (0.0, -0.14, 1.38)], 0.010)
bm = P.bm(M_STEEL, "Abdomen")
fan_plate(bm, [(-0.065, -0.12, 1.18), (0.065, -0.12, 1.18), (0.09, -0.125, 1.04), (0.0, -0.14, 0.98), (-0.09, -0.125, 1.04)], 0.012)
# neck collar plates
CS = Sweep((0, -0.045, 1.52), (0, -0.045, 1.47), X, FRONT, 0.065, 0.06)
shingles(P.bm(M_STEEL, "Chest"), CS, 0.0, 1.0, 1, 12, lift=0.01, flare=0.03, fold=0.008, overlap=2.0)
# back plates beside the spine + brass spine
bm = P.bm(M_BRASS, "Torso")
for s in (1, -1):
    pass
sp = lambda z: TS.P((1.47 - z) / 0.52, BACK, 0.006)
strap(bm, sp(1.46), sp(1.00), 0.022, 0.006)
for k in range(10):
    z = 1.44 - k * 0.043
    box(bm, sp(z), (0.040, 0.014, 0.016))
    rivets(bm, [sp(z) + Vector((0.013, 0.008, 0)), sp(z) + Vector((-0.013, 0.008, 0))], 0.0045)
bmd = P.bm(M_DARK, "Torso")
for s in (1, -1):
    strap(bmd, sp(1.46) + X * s * 0.022, sp(1.0) + X * s * 0.022, 0.008, 0.008)
# waist hinge links
for s in (1, -1):
    hinge(P.bm(M_BRASS, "Abdomen"), (s * 0.10, -0.05, 1.06), (0, 1, 0), 0.016, 0.036)

# ---------------------------------------------------------------- hip skirt of long spike lamellae (skinned to hips + thighs)
sk_r = interp([(0.0, 0.178), (1.0, 0.195)]); sk_y = interp([(0.0, 0.115), (1.0, 0.125)])
SK = Sweep((0, -0.058, 1.03), (0, -0.075, 0.68), X, FRONT, sk_r, sk_y)
skbm = bmesh.new()
shingles(skbm, SK, 0.0, 1.0, 2, 12, hw=0.30, lift=0.0, flare=0.03, fold=0.010, jitter=0.08, overlap=2.0)
def skirt_w(co):
    t = smoothstep(0.98, 0.62, co.z); leg = "UpperLeg.L" if co.x >= 0 else "UpperLeg.R"
    wl = t * (0.2 + 0.7 * max(0.0, -co.y - 0.02) / 0.13) * smoothstep(0.0, 0.07, abs(co.x))
    wl = min(wl, 0.9)
    return {"Hips": 1.0 - wl, leg: wl}
skinned(arm, "Hero_Skirt", skbm, M_STEEL, skirt_w)
inner = bmesh.new()
shingles(inner, SK, 0.0, 1.0, 2, 12, hw=0.34, lift=-0.012, flare=0.02, fold=0.004, jitter=0.08, overlap=2.0, a0=0.26, a1=2 * math.pi + 0.26)
skinned(arm, "Hero_SkirtInner", inner, M_DARK, skirt_w)
# belt + buckle
bm = P.bm(M_BRASS, "Hips")
ring_tube(bm, Sweep((0, -0.058, 1.035), (0, -0.058, 1.005), X, FRONT, 0.150, 0.110), 0, 1, 1, 24, 0.0)
box(bm, (0, -0.172, 1.02), (0.045, 0.016, 0.036))
rivets(bm, [(0.018, -0.182, 1.03), (-0.018, -0.182, 1.03), (0.018, -0.182, 1.01), (-0.018, -0.182, 1.01)], 0.004)

# ---------------------------------------------------------------- arms
for sgn, tag in ((1, "L"), (-1, "R")):
    sh, up, lo, hd = "Shoulder." + tag, "UpperArm." + tag, "LowerArm." + tag, "Hand." + tag
    U = Vector((0, -1, 0)); V = Z
    def m(p): return Vector((p[0] * sgn, p[1], p[2]))
    # pauldron over the shoulder (top half arc)
    PS = Sweep(m((0.05, -0.058, 1.455)), m((0.27, -0.056, 1.45)), U, V, interp([(0, 0.065), (0.5, 0.058), (1, 0.046)]))
    shingles(P.bm(M_STEEL, sh), PS, 0.0, 0.85, 3, 7, lift=0.008, flare=0.02, fold=0.012, a0=0.1, a1=math.pi - 0.1, jitter=0.1)
    ell(P.bm(M_BRASS, sh), m((0.155, -0.058, 1.432)), (0.034, 0.034, 0.034), seg=14, rings=8)
    cyl(P.bm(M_BRASS, sh), m((0.155, -0.058, 1.432)), (0, 1, 0), 0.022, 0.10, 12)
    cyl(P.bm(M_DARK, sh), m((0.155, -0.058, 1.432)), (0, 1, 0), 0.011, 0.115, 8)
    # upper arm
    UA = Sweep(m((0.19, -0.057, 1.442)), m((0.325, -0.057, 1.442)), U, V, interp([(0, 0.044), (1, 0.040)]))
    shingles(P.bm(M_STEEL, up), UA, 0.0, 1.0, 2, 6, hw=0.42, lift=0.006, flare=0.010, fold=0.006, jitter=0.06, overlap=2.2)
    # elbow hinge
    hinge(P.bm(M_BRASS, lo), m((0.334, -0.057, 1.442)), (0, 0, 1), 0.026, 0.09)
    strap(P.bm(M_BRASS, lo), m((0.334, -0.057, 1.487)), m((0.39, -0.065, 1.487)), 0.012, 0.004)
    strap(P.bm(M_BRASS, lo), m((0.334, -0.057, 1.397)), m((0.39, -0.065, 1.397)), 0.012, 0.004)
    # forearm
    FA = Sweep(m((0.36, -0.062, 1.437)), m((0.555, -0.085, 1.436)), U, V, interp([(0, 0.040), (0.5, 0.034), (1, 0.030)]))
    shingles(P.bm(M_STEEL, lo), FA, 0.0, 1.0, 3, 6, hw=0.42, lift=0.006, flare=0.010, fold=0.006, jitter=0.06, overlap=2.2)
    # wrist ring + hinge
    cyl(P.bm(M_BRASS, hd), m((0.585, -0.087, 1.433)), (1, 0, 0), 0.030, 0.022, 14, r2=0.028)
    hinge(P.bm(M_BRASS, hd), m((0.585, -0.087, 1.433)), (0, 0, 1), 0.014, 0.07, 10)
    # little finger-knuckle brass dots
    for b2, off in (("Index2.", 0.0), ("Middle2.", 0.0), ("Ring2.", 0.0), ("Pinky2.", 0.0)):
        hp = bone_pt(arm, b2 + tag)
        ell(P.bm(M_BRASS, b2 + tag), hp, (0.0085, 0.0085, 0.0085), seg=6, rings=4)

# ---------------------------------------------------------------- legs
for sgn, tag in ((1, "L"), (-1, "R")):
    up, lo, ft = "UpperLeg." + tag, "LowerLeg." + tag, "Foot." + tag
    cx = 0.121 * sgn
    TH = Sweep((cx, -0.055, 0.95), (cx, -0.085, 0.57), X, FRONT, interp([(0, 0.058), (1, 0.044)]), interp([(0, 0.064), (1, 0.050)]))
    shingles(P.bm(M_STEEL, up), TH, 0.0, 1.0, 3, 8, hw=0.34, lift=0.007, flare=0.012, fold=0.007, jitter=0.07, overlap=2.3)
    # knee hinge: horizontal barrel through the joint + side link plates
    hinge(P.bm(M_BRASS, lo), (cx, -0.088, 0.535), (1, 0, 0), 0.026, 0.12)
    ell(P.bm(M_BRASS, lo), (cx, -0.088, 0.535), (0.034, 0.034, 0.034), seg=12, rings=6) if False else None
    # knee cap kite
    fan_plate(P.bm(M_STEEL, lo), [(cx - 0.035, -0.125, 0.58), (cx + 0.035, -0.125, 0.58), (cx + 0.04, -0.138, 0.50), (cx, -0.15, 0.45), (cx - 0.04, -0.138, 0.50)], 0.012)
    SH = Sweep((cx, -0.085, 0.50), (cx, -0.062, 0.075), X, FRONT, interp([(0, 0.048), (0.5, 0.040), (1, 0.040)]), interp([(0, 0.056), (0.5, 0.044), (1, 0.046)]))
    shingles(P.bm(M_STEEL, lo), SH, 0.0, 1.0, 4, 8, hw=0.34, lift=0.007, flare=0.012, fold=0.007, jitter=0.07, overlap=2.3)
    # ankle hinge
    hinge(P.bm(M_BRASS, ft), (cx, -0.062, 0.058), (1, 0, 0), 0.022, 0.10)
    # pointed heeled shoe: hull of an ankle cuff, toe point, block heel
    bm = P.bm(M_STEEL, ft)
    hull(bm, [(cx - 0.040, -0.025, 0.10), (cx + 0.040, -0.025, 0.10), (cx - 0.040, -0.10, 0.095), (cx + 0.040, -0.10, 0.095),
              (cx - 0.040, 0.015, 0.035), (cx + 0.040, 0.015, 0.035), (cx - 0.028, 0.02, 0.0), (cx + 0.028, 0.02, 0.0),
              (cx - 0.042, -0.14, 0.04), (cx + 0.042, -0.14, 0.04), (cx - 0.034, -0.14, 0.012), (cx + 0.034, -0.14, 0.012),
              (cx, -0.30, 0.008), (cx, -0.25, 0.03)])
    fan_plate(P.bm(M_STEEL, ft), [(cx - 0.04, -0.15, 0.055), (cx + 0.04, -0.15, 0.055), (cx, -0.29, 0.026)], 0.010)
    cyl(P.bm(M_BRASS, ft), (cx, 0.0, 0.03), (0, 0, 1), 0.026, 0.012, 12)

# ---------------------------------------------------------------- head: faceted beak helmet
bm = P.bm(M_STEEL, "Head")
hull(bm, [(0, -0.03, 1.745), (0, 0.085, 1.700), (0.03, -0.11, 1.705), (-0.03, -0.11, 1.705),
          (0.062, -0.095, 1.668), (-0.062, -0.095, 1.668), (0.078, -0.015, 1.665), (-0.078, -0.015, 1.665),
          (0.06, 0.06, 1.64), (-0.06, 0.06, 1.64), (0.058, -0.095, 1.600), (-0.058, -0.095, 1.600),
          (0.05, -0.035, 1.560), (-0.05, -0.035, 1.560), (0, -0.115, 1.535), (0, -0.145, 1.640)])
bm = P.bm(M_DARK, "Head")                                  # dark visor wedge under the brow (inner shell)
hull(bm, [(0, -0.133, 1.652), (0.045, -0.105, 1.64), (-0.045, -0.105, 1.64), (0, -0.138, 1.585), (0.03, -0.11, 1.585), (-0.03, -0.11, 1.585)])
for s in (1, -1):                                          # swept-back crest blades
    for k, (dz, dy) in enumerate(((0.0, 0.0), (0.03, 0.02), (0.06, 0.03))):
        fan_plate(P.bm(M_STEEL, "Head"), [(s * (0.012 + 0.01 * k), 0.02, 1.735 - dz * 0.4), (s * (0.045 + 0.012 * k), 0.04, 1.69 - dz * 0.2),
                                          (s * 0.01, 0.17 + dy, 1.72 - dz * 1.3)], 0.014)
fan_plate(P.bm(M_STEEL, "Head"), [(0.0, -0.03, 1.745), (0.0, 0.17, 1.70), (0.0, 0.04, 1.69)], 0.012)
bm = P.bm(M_EYE, "Head")                                   # amber slits
for s in (1, -1):
    fan_plate(bm, [(s * 0.018, -0.128, 1.628), (s * 0.058, -0.108, 1.640), (s * 0.052, -0.108, 1.628), (s * 0.026, -0.130, 1.618)], 0.004)
bm = P.bm(M_BRASS, "Head")
for s in (1, -1):                                          # ear discs + cheek strap hinge
    cyl(bm, (s * 0.080, -0.02, 1.62), (1, 0, 0), 0.020, 0.018, 12)
    cyl(bm, (s * 0.088, -0.02, 1.62), (1, 0, 0), 0.008, 0.01, 8)
    strap(bm, (s * 0.07, -0.02, 1.60), (s * 0.058, -0.06, 1.545), 0.008, 0.004)
# neck: brass rods + stacked dark rings
bm = P.bm(M_DARK, "Neck")
for k in range(4): cyl(bm, (0, -0.043, 1.505 + k * 0.022), (0, 0, 1), 0.040 - 0.002 * k, 0.012, 12)
bm = P.bm(M_BRASS, "Neck")
for s in (1, -1): cyl(bm, (s * 0.03, -0.03, 1.555), (0, 0, 1), 0.007, 0.10, 6)

# ---------------------------------------------------------------- coiled cable at the right hip (3 turns + brass bands + plug)
cb = P.bm(M_CABLE, "Hips"); cbr = P.bm(M_BRASS, "Hips")
cc = Vector((-0.215, -0.04, 0.86)); R = 0.085; turns = 3; steps = 16
pts = []
for i in range(turns * steps + 1):
    a = 2 * math.pi * i / steps
    pts.append(cc + Vector((-0.020 * (i / steps), R * math.cos(a) * 0.9, R * math.sin(a))))
for i in range(len(pts) - 1): tube(cb, pts[i], pts[i + 1], 0.013, 0.013, seg=6)
for ang in (0.5, 3.6):                                     # two clamp bands wrapping the coil
    p = cc + Vector((-0.02, R * math.cos(ang) * 0.9, R * math.sin(ang)))
    cyl(cbr, p + Vector((-0.02, 0, 0)), (1, 0, 0), 0.033, 0.018, 10)
tail_a = pts[-1]; tail_b = tail_a + Vector((0, -0.05, -0.13))
tube(cb, tail_a, tail_b, 0.013, 0.013, seg=6)
cyl(cbr, tail_b + Vector((0, -0.012, -0.03)), (0, -0.3, -1), 0.020, 0.06, 10)    # connector plug
cyl(cbr, tail_b + Vector((0, -0.02, -0.075)), (0, -0.3, -1), 0.011, 0.03, 8)
tube(cb, cc + Vector((0, 0.09, 0.07)), cc + Vector((0.0, 0.1, 0.17)), 0.012, 0.012, seg=6)     # lead to belt
strap(cbr, (-0.19, -0.058, 1.01), (-0.225, 0.04, 0.95), 0.016, 0.004)

# ---------------------------------------------------------------- inner oxidised frame (rods) + hip/shoulder pivots
for sgn, tag in ((1, "L"), (-1, "R")):
    cx = 0.121 * sgn
    for bone, p0, p1, r0, r1 in (("UpperArm." + tag, (0.16 * sgn, -0.057, 1.44), (0.334 * sgn, -0.057, 1.44), 0.026, 0.022),
                                 ("LowerArm." + tag, (0.334 * sgn, -0.058, 1.437), (0.575 * sgn, -0.086, 1.434), 0.022, 0.018),
                                 ("UpperLeg." + tag, (cx, -0.052, 0.96), (cx, -0.087, 0.54), 0.036, 0.028),
                                 ("LowerLeg." + tag, (cx, -0.087, 0.54), (cx, -0.062, 0.06), 0.028, 0.024)):
        tube(P.bm(M_DARK, bone), p0, p1, r0, r1, seg=10)
    ell(P.bm(M_BRASS, "UpperLeg." + tag), (cx, -0.05, 0.965), (0.038, 0.038, 0.038), seg=12, rings=7)
    cyl(P.bm(M_BRASS, "UpperLeg." + tag), (cx, -0.05, 0.965), (0, 1, 0), 0.024, 0.10, 10)
core = bmesh.new()
ring_tube(core, Sweep((0, -0.055, 1.47), (0, -0.06, 0.95), X, FRONT, interp([(0, 0.086), (0.17, 0.098), (0.45, 0.078), (0.70, 0.070), (0.88, 0.090), (1.0, 0.100)]), interp([(0, 0.062), (0.17, 0.070), (0.45, 0.058), (0.70, 0.054), (0.88, 0.068), (1.0, 0.072)])), 0, 1, 10, 14, 0.0, cap=True)
def core_w(co):
    ch = smoothstep(1.30, 1.40, co.z); tq = smoothstep(1.12, 1.22, co.z) * (1 - ch); ab = smoothstep(1.00, 1.06, co.z) * (1 - ch - tq)
    return {"Chest": ch, "Torso": tq, "Abdomen": ab, "Hips": max(0.0, 1 - ch - tq - ab)}
skinned(arm, "Hero_TorsoCore", core, M_DARK, core_w)
P.flush("")

print("TRIS", tri_count())
finish(OUT, "ironveil")
