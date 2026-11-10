"""Forgespawn hero: heavy liquid-metal industrial golem on the mechanical shared-skeleton base (Blender 5.x).
Run: blender -b -P build_forgespawn.py -- <mechanical.glb> <out_dir>
Rounded polished dark-nickel armour blobs on every limb, warm copper joint rings and neck hoses, big articulated fists (a rounded
capsule per finger bone), a domed helmet with a blocky face and copper ear discs, and a furnace-core pack with glowing vents."""
import bpy, bmesh, math, sys, os, random
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mech_common import *

SRC, OUT = sys.argv[-2], sys.argv[-1]
random.seed(31)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
remove_objects("_Head", "_Feet")
TEX = os.path.join(OUT, "tex")

glow = glow_tex("FS_furnace_emission", TEX, (1.0, 0.42, 0.06), kind="cells", seed=4)
M_NICKEL = make_metal_mat("FS_Nickel", (0.40, 0.39, 0.39), "brushed", TEX, 0.34, 0.62, seed=3)
M_FRAME = make_metal_mat("FS_Frame", (0.14, 0.13, 0.13), "oxid", TEX, 0.55, 0.55, seed=6, rust=(0.22, 0.10, 0.05))
M_COPPER = make_metal_mat("FS_Copper", (0.68, 0.36, 0.20), "brass", TEX, 0.30, 0.75, seed=9)
M_PACK = make_metal_mat("FS_Pack", (0.30, 0.28, 0.26), "oxid", TEX, 0.5, 0.65, seed=12, rust=(0.35, 0.17, 0.07))
M_GLOW = mat("FS_Glow", (0.9, 0.35, 0.05), 0.4, 0.0, emit=(1.0, 0.4, 0.06), strength=4.0)
T.bind(M_GLOW, None, None, glow, 4.0)
M_STRAP = mat("FS_Strap", (0.10, 0.09, 0.08), 0.8, 0.1)
M_EYE = mat("FS_Eye", (0.012, 0.014, 0.015), 0.18, 0.45)
strip_base(keep=("Hand.", "Index", "Middle", "Ring", "Pinky", "Thumb")); override_base(M_FRAME)
P = Parts(arm)
X = Vector((1, 0, 0)); Z = Vector((0, 0, 1)); FRONT = Vector((0, -1, 0))
def S(m, b): return P.bm(m, b, True)        # smooth bucket
def sgnv(s, p): return Vector((p[0] * s, p[1], p[2]))

def armour_shell(bm, p0, p1, widths, depths, rows=10, n=18):
    """Continuous tapered armour with open joint recesses, rather than capsule end caps."""
    u, v = frame(p0, p1)
    ring_tube(bm, Sweep(p0, p1, u, v, interp(widths), interp(depths)), 0, 1, rows, n, cap=True)

# ---------------------------------------------------------------- torso
cx0 = -0.050
chest = Sweep((0, cx0, 1.19), (0, cx0 - 0.005, 1.53), X, FRONT, interp([(0, 0.17), (0.3, 0.235), (0.62, 0.255), (1, 0.15)]), interp([(0, 0.14), (0.4, 0.185), (1, 0.14)]))
ring_tube(S(M_NICKEL, "Chest"), chest, 0, 1, 12, 24, cap=True)
blob(S(M_FRAME, "Torso"), (0, -0.04, 1.00), (0, -0.04, 1.26), 0.14, 0.14, 0.95, rows=6, n=14, pw=6.0)   # waist column
blob(S(M_NICKEL, "Abdomen"), (0, -0.075, 1.03), (0, -0.075, 1.24), 0.15, 0.17, 0.70, rows=8, n=16, pw=4.0)   # abdominal plate
blob(S(M_NICKEL, "Hips"), (0, -0.055, 0.86), (0, -0.055, 1.07), 0.19, 0.19, 0.80, rows=8, n=18, pw=4.0)   # pelvis block
# copper waist ring + chest rim
cyl(P.bm(M_COPPER, "Torso"), (0, -0.045, 1.07), (0, 0, 1), 0.165, 0.025, 20)
for s in (1, -1):
    blob(S(M_COPPER, "Chest"), (s * 0.19, -0.02, 1.20), (s * 0.19, -0.02, 1.35), 0.04, 0.04, 1.0, rows=4, n=8)   # side hoses
    # Separate breast plates follow the chest curvature, with a recessed central seam.
    fan_plate(P.bm(M_NICKEL, "Chest"), [(s * .012, -.232, 1.46), (s * .15, -.204, 1.48),
              (s * .218, -.172, 1.39), (s * .15, -.202, 1.28), (s * .014, -.231, 1.30)], .009)
    tube(P.bm(M_FRAME, "Chest"), (s * .012, -.237, 1.31), (s * .012, -.234, 1.46), .003, .003, seg=6)
# furnace-dark seam under the chest
cyl(P.bm(M_FRAME, "Chest"), (0, -0.05, 1.165), (0, 0, 1), 0.15, 0.035, 18)
# neck collar + copper hoses
blob(S(M_NICKEL, "Neck"), (0, -0.043, 1.505), (0, -0.043, 1.57), 0.085, 0.09, 1.0, rows=5, n=14, pw=6.0)
for s in (1, -1):
    pts = [(s * 0.07, -0.02, 1.52), (s * 0.14, 0.0, 1.55), (s * 0.15, -0.03, 1.64), (s * 0.085, -0.04, 1.62)]
    for a, b in zip(pts, pts[1:]): tube(S(M_COPPER, "Neck"), a, b, 0.016, 0.016, seg=8)
    for p in pts[1:3]: ell(S(M_COPPER, "Neck"), p, (0.02, 0.02, 0.02), seg=8, rings=5)

# ---------------------------------------------------------------- head: domed helmet, blocky face, copper ear discs
H = Vector((0, -0.043, 1.64))
blob_sw(S(M_NICKEL, "Head"), Sweep((0, -0.04, 1.545), (0, -0.04, 1.745), X, FRONT, interp([(0, 0.062), (0.35, 0.094), (1, 0.080)]), interp([(0, 0.088), (0.45, 0.115), (1, 0.100)])), rows=12, n=18, pw=2.2)
bm = P.bm(M_NICKEL, "Head")
hull(bm, [(-0.055, -0.10, 1.69), (0.055, -0.10, 1.69), (-0.062, -0.125, 1.64), (0.062, -0.125, 1.64), (-0.06, -0.13, 1.585), (0.06, -0.13, 1.585),
          (-0.045, -0.125, 1.55), (0.045, -0.125, 1.55), (-0.045, -0.085, 1.70), (0.045, -0.085, 1.70)])      # flat face plate
bmf = P.bm(M_FRAME, "Head")
box(bmf, (0, -0.128, 1.635), (0.115, 0.008, 0.016))                                                           # eye slit band
box(bmf, (0, -0.130, 1.572), (0.040, 0.008, 0.008))                                                           # mouth seam
for s in (1, -1):
    # Bring the articulated face in front of the helmet shell; the old eye band was buried.
    ell(P.bm(M_FRAME, "Head", True), (s * .035, -.158, 1.648), (.029, .012, .023), seg=12, rings=8)
    ell(P.bm(M_EYE, "Head", True), (s * .035, -.171, 1.648), (.018, .006, .010), seg=12, rings=8)
    fan_plate(P.bm(M_NICKEL, "Head"), [(s * .006, -.182, 1.677), (s * .066, -.163, 1.681),
              (s * .084, -.146, 1.649), (s * .060, -.175, 1.660), (s * .013, -.188, 1.660)], .004)
    fan_plate(P.bm(M_NICKEL, "Head"), [(s * .067, -.165, 1.632), (s * .079, -.142, 1.606),
              (s * .047, -.160, 1.566), (s * .016, -.182, 1.592), (s * .022, -.185, 1.625)], .005)
    tube(P.bm(M_FRAME, "Head"), (s * .018, -.189, 1.591), (s * .047, -.165, 1.578), .003, .003, seg=6)
    cyl(P.bm(M_COPPER, "Head"), (s * 0.098, -0.03, 1.62), (1, 0, 0), 0.036, 0.03, 16)
    cyl(P.bm(M_NICKEL, "Head"), (s * 0.114, -0.03, 1.62), (1, 0, 0), 0.022, 0.012, 14)
    cyl(P.bm(M_FRAME, "Head"), (s * 0.12, -0.03, 1.62), (1, 0, 0), 0.010, 0.006, 8)
box(P.bm(M_NICKEL, "Head"), (0, -0.125, 1.705), (0.045, 0.008, 0.03), (0.3, 0, 0))                           # brow crest
fan_plate(P.bm(M_NICKEL, "Head"), [(-.016, -.184, 1.704), (.016, -.184, 1.704),
          (.012, -.198, 1.627), (0, -.207, 1.616), (-.012, -.198, 1.627)], .004)
fan_plate(P.bm(M_NICKEL, "Head"), [(-.033, -.179, 1.586), (.033, -.179, 1.586),
          (.030, -.173, 1.558), (-.030, -.173, 1.558)], .005)

# ---------------------------------------------------------------- arms (rounded nickel, copper joints, big fists)
for sgn, tag in ((1, "L"), (-1, "R")):
    sh, up, lo, hd = "Shoulder." + tag, "UpperArm." + tag, "LowerArm." + tag, "Hand." + tag
    m = lambda p, s=sgn: sgnv(s, p)
    # shoulder dome + copper ring
    ell(S(M_NICKEL, sh), m((0.205, -0.055, 1.43)), (0.115, 0.105, 0.115), seg=16, rings=10)
    cyl(P.bm(M_COPPER, up), m((0.275, -0.057, 1.435)), (1, 0, 0), 0.082, 0.02, 20)
    cyl(P.bm(M_FRAME, up), m((0.255, -0.057, 1.435)), (1, 0, 0), 0.064, 0.05, 16)
    armour_shell(S(M_NICKEL, up), m((.275, -.057, 1.435)), m((.39, -.057, 1.435)),
                 [(0,.065),(.25,.085),(.7,.078),(1,.045)], [(0,.066),(.35,.080),(1,.050)])
    # elbow: copper hub on top/bottom (hinge axis Z)
    cyl(P.bm(M_COPPER, lo), m((0.40, -0.058, 1.435)), (0, 0, 1), 0.044, 0.15, 18)
    cyl(P.bm(M_NICKEL, lo), m((0.40, -0.058, 1.50)), (0, 0, 1), 0.030, 0.018, 14)
    cyl(P.bm(M_NICKEL, lo), m((0.40, -0.058, 1.37)), (0, 0, 1), 0.030, 0.018, 14)
    armour_shell(S(M_NICKEL, lo), m((.425, -.063, 1.435)), m((.575, -.088, 1.435)),
                 [(0,.050),(.25,.091),(.55,.083),(1,.054)], [(0,.051),(.3,.078),(1,.048)])
    cyl(P.bm(M_COPPER, lo), m((0.575, -0.086, 1.435)), (1, 0, 0), 0.062, 0.025, 16)                # wrist ring
    # fist: back-of-hand block + a rounded capsule per finger bone
    blob(S(M_NICKEL, hd), m((0.585, -0.088, 1.435)), m((0.735, -0.088, 1.438)), 0.052, 0.058, 0.62, rows=6, n=12, pw=3.0, up=(0, 0, 1))
    for fb in ("Index", "Middle", "Ring", "Pinky"):
        for seg in (2, 3, 4):
            bn = "%s%d.%s" % (fb, seg, tag)
            if bn in arm.data.bones:
                b = arm.data.bones[bn]; a, c = Vector(b.head_local), Vector(b.tail_local)
                if seg == 4: c = c + (c - a).normalized() * 0.012
                blob(S(M_NICKEL, bn), a - (c - a).normalized() * 0.004, c, 0.0155 if fb != "Pinky" else 0.013, 0.0135, 1.0, rows=4, n=8, pw=3.0)
    for seg in (2, 3):
        bn = "Thumb%d.%s" % (seg, tag)
        b = arm.data.bones[bn]; a, c = Vector(b.head_local), Vector(b.tail_local)
        if seg == 3: c = c + (c - a).normalized() * 0.012
        blob(S(M_NICKEL, bn), a, c, 0.02, 0.016, 1.0, rows=4, n=8, pw=3.0)

# ---------------------------------------------------------------- legs
for sgn, tag in ((1, "L"), (-1, "R")):
    up, lo, ft = "UpperLeg." + tag, "LowerLeg." + tag, "Foot." + tag
    cx = 0.121 * sgn
    armour_shell(S(M_NICKEL, up), (cx,-.05,.94), (cx,-.086,.59),
                 [(0,.080),(.2,.111),(.6,.097),(1,.056)], [(0,.095),(.25,.128),(.65,.102),(1,.060)])
    ell(S(M_COPPER, up), (cx, -0.05, 0.965), (0.05, 0.05, 0.05), seg=12, rings=8)                    # hip ball joint
    # knee: copper hub on the outside + front kneecap
    cyl(P.bm(M_COPPER, lo), (cx, -0.088, 0.535), (1, 0, 0), 0.050, 0.17, 18)
    cyl(P.bm(M_NICKEL, lo), (cx + sgn * 0.0925, -0.088, 0.535), (1, 0, 0), 0.032, 0.012, 14)
    ell(S(M_NICKEL, lo), (cx, -0.145, 0.545), (0.078, 0.062, 0.085), seg=14, rings=8)
    armour_shell(S(M_NICKEL, lo), (cx,-.085,.48), (cx,-.055,.09),
                 [(0,.063),(.2,.096),(.5,.078),(.85,.056),(1,.074)],
                 [(0,.073),(.22,.108),(.6,.080),(.85,.060),(1,.073)])
    ell(S(M_NICKEL, lo), (cx, -0.03, 0.38), (0.072, 0.052, 0.12), seg=12, rings=8)                    # calf guard
    cyl(P.bm(M_COPPER, ft), (cx, -0.062, 0.062), (1, 0, 0), 0.040, 0.18, 16)                         # ankle hub
    # foot: blocky boot with toe caps
    slab_e(P.bm(M_FRAME, ft), (cx,-.105,.019), (.18,.31,.036), q=.013)
    blob(S(M_NICKEL, ft), (cx,.03,.065), (cx,-.235,.065), .082,.088,.62, rows=8,n=14,pw=5.0,up=(0,0,1))
    for k in range(4):
        tx = cx + (k - 1.5) * 0.034
        blob(S(M_FRAME, ft), (tx, -0.225, 0.034), (tx, -0.27, 0.034), 0.0165, 0.0155, 0.9, rows=3, n=8, pw=3.0)

# panel-line bands (dark grooves ringing the limbs)
for sgn in (1, -1):
    cx = 0.121 * sgn
    for z, r in ((0.82, 0.116), (0.38, 0.088), (0.22, 0.078)):
        cyl(P.bm(M_FRAME, "UpperLeg." + ("L" if sgn > 0 else "R") if z > 0.6 else "LowerLeg." + ("L" if sgn > 0 else "R")), (cx, -0.07 + 0.02 * (0.8 - z), z), (0, 0, 1), r, 0.006, 18)
    for x, r, bn in ((0.33, 0.082, "UpperArm."), (0.50, 0.078, "LowerArm.")):
        cyl(P.bm(M_FRAME, bn + ("L" if sgn > 0 else "R")), (x * sgn, -0.06 - (x - 0.33) * 0.12, 1.435), (1, 0, 0), r, 0.006, 16)
# ---------------------------------------------------------------- back furnace-core pack
cy = 0.115
cyl(P.bm(M_PACK, "Chest"), (0, cy, 1.33), (0, 0, 1), 0.125, 0.30, 24)
for dz in (-0.15, 0.15): cyl(P.bm(M_COPPER, "Chest"), (0, cy, 1.33 + dz), (0, 0, 1), 0.133, 0.02, 24)
for k in range(2):
    cyl(P.bm(M_PACK, "Chest"), (0, cy, 1.33 + (k - 0.5) * 0.17), (0, 0, 1), 0.131, 0.014, 24)           # bands
bm = P.bm(M_GLOW, "Chest")
for k in range(5):                                                                                        # glowing vent slots
    a = math.radians(-50 + k * 25)
    c = Vector((0.125 * math.sin(a), cy + 0.125 * math.cos(a), 1.33))
    box(bm, c, (0.017, 0.012, 0.13), (0, 0, -a))
for s in (1, -1):                                                                                         # shoulder straps
    pts = [(s * 0.10, 0.08, 1.52), (s * 0.13, -0.02, 1.565), (s * 0.12, -0.14, 1.48), (s * 0.11, -0.185, 1.34)]
    for a, b in zip(pts, pts[1:]): strap(P.bm(M_FRAME, "Chest"), a, b, 0.045, 0.012)
    tube(S(M_COPPER, "Chest"), (s * 0.12, cy - 0.02, 1.47), (s * 0.19, 0.03, 1.40), 0.014, 0.014, seg=8)       # side pipes to the pack
    tube(S(M_COPPER, "Chest"), (s * 0.19, 0.03, 1.40), (s * 0.15, cy, 1.22), 0.014, 0.014, seg=8)
# two glowing vent slots on the upper back plate
for s in (1, -1):
    box(P.bm(M_FRAME, "Chest"), (s * 0.125, 0.095, 1.42), (0.075, 0.02, 0.05))
    box(P.bm(M_GLOW, "Chest"), (s * 0.125, 0.101, 1.42), (0.06, 0.012, 0.035))

P.flush("")
print("TRIS", tri_count())
finish(OUT, "forgespawn")
