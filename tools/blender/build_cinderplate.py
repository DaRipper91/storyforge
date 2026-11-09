"""Cinderplate hero: broad furnace-guard automaton in segmented cast-iron plate over cracked ceramic insulation (Blender 5.x).
Run: blender -b -P build_cinderplate.py -- <mechanical.glb> <out_dir>
Chamfered riveted iron plates, cream mineral-ceramic cores showing between them, glowing furnace grilles (belly, shoulder vents,
helmet eyes), brass heat-sink fin stacks on the shoulders and a brass back grille, brass hubs at the joints, chunky boots, forge-hammer on the back."""
import bpy, bmesh, math, sys, os, random
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mech_common import *

SRC, OUT = sys.argv[-2], sys.argv[-1]
random.seed(41)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
remove_objects("_Head", "_Feet")
TEX = os.path.join(OUT, "tex")

glow = glow_tex("CP_core_emission", TEX, (1.0, 0.45, 0.08), kind="cells", seed=7)
M_IRON = make_metal_mat("CP_Iron", (0.30, 0.28, 0.28), "oxid", TEX, 0.55, 0.6, seed=4, rust=(0.20, 0.11, 0.07))
M_CERAM = make_metal_mat("CP_Ceramic", (0.80, 0.74, 0.62), "plate", TEX, 0.85, 0.0, seed=14)
M_BRASS = make_metal_mat("CP_Brass", (0.72, 0.54, 0.22), "brass", TEX, 0.35, 0.7, seed=9)
M_DARK = make_metal_mat("CP_Dark", (0.10, 0.09, 0.09), "oxid", TEX, 0.6, 0.5, seed=21)
M_GLOW = mat("CP_Glow", (0.9, 0.4, 0.06), 0.4, 0.0, emit=(1.0, 0.42, 0.06), strength=4.5)
T.bind(M_GLOW, None, None, glow, 4.5)
M_LEATH = mat("CP_Leather", (0.16, 0.08, 0.05), 0.7, 0.0)
strip_base(); override_base(M_DARK)
P = Parts(arm)
X = Vector((1, 0, 0)); Z = Vector((0, 0, 1)); FRONT = Vector((0, -1, 0))
def S(m, b): return P.bm(m, b, True)
def sg(s, p): return Vector((p[0] * s, p[1], p[2]))
def L(s): return "L" if s > 0 else "R"

# ---------------------------------------------------------------- torso
cy = -0.05
blob(S(M_CERAM, "Chest"), (0, cy, 1.20), (0, cy, 1.50), 0.20, 0.18, 0.78, rows=8, n=14, pw=4.0, mid=1.1)
blob(S(M_CERAM, "Torso"), (0, -0.045, 1.02), (0, -0.045, 1.28), 0.14, 0.14, 0.85, rows=6, n=14, pw=6.0)
blob(S(M_CERAM, "Hips"), (0, -0.055, 0.88), (0, -0.055, 1.06), 0.17, 0.17, 0.78, rows=6, n=14, pw=6.0)
TS = Sweep((0, cy, 1.52), (0, -0.045, 1.18), X, FRONT, interp([(0, 0.205), (0.3, 0.235), (1, 0.185)]), interp([(0, 0.14), (0.3, 0.165), (1, 0.14)]))
b = P.bm(M_IRON, "Chest")
slab_e(b, (0, -0.205, 1.40), (0.34, 0.17, 0.045), (0.12, 0, 0), 0.014, 0.008)                    # breastplate
slab_e(b, (0, -0.19, 1.285), (0.28, 0.10, 0.04), (-0.10, 0, 0), 0.012)                    # lower sternum plate
for s in (-1, 1):
    slab_e(b, (s * 0.17, -0.185, 1.38), (0.12, 0.20, 0.04), (0.1, 0, s * 0.25), 0.012)  # side chest plates
    slab_e(b, (s * 0.20, 0.0, 1.35), (0.04, 0.30, 0.20), (0, 0, 0), 0.012)              # flank plates
slab_e(b, (0, 0.11, 1.38), (0.38, 0.045, 0.32), (0, 0, 0), 0.014)                          # back plate
slab_e(b, (0, 0.14, 1.20), (0.32, 0.03, 0.12), (0, 0, 0), 0.012)
# belly furnace core: glowing grille in an iron frame
bg = P.bm(M_GLOW, "Torso"); bd = P.bm(M_DARK, "Torso"); bi = P.bm(M_IRON, "Torso")
box(bg, (0, -0.178, 1.17), (0.17, 0.02, 0.11))
for k in range(5): box(bd, (-0.068 + k * 0.034, -0.19, 1.17), (0.008, 0.01, 0.115))
for dz in (0.065, -0.065): slab_e(bi, (0, -0.172, 1.17 + dz), (0.22, 0.03, 0.025), (0, 0, 0), 0.008)
for dx in (0.10, -0.10): slab_e(bi, (dx, -0.172, 1.17), (0.025, 0.03, 0.14), (0, 0, 0), 0.008)
# belt (brass) + tassets
blt = P.bm(M_BRASS, "Hips")
cyl(blt, (0, -0.058, 1.03), (0, 0, 1), 0.205, 0.035, 22)
box(blt, (0, -0.255, 1.03), (0.08, 0.02, 0.05))
bi = P.bm(M_IRON, "Hips")
slab_e(bi, (0, -0.225, 0.90), (0.20, 0.035, 0.22), (-0.10, 0, 0), 0.012, 0.006)              # front tasset
for s in (-1, 1):
    slab_e(bi, (s * 0.16, -0.18, 0.93), (0.10, 0.035, 0.17), (-0.05, 0, s * 0.5), 0.010)
    slab_e(bi, (s * 0.21, -0.05, 0.93), (0.04, 0.22, 0.16), (0, 0, 0), 0.010)
slab_e(bi, (0, 0.14, 0.92), (0.30, 0.035, 0.18), (0.08, 0, 0), 0.012)                   # rear tasset
# back brass heat-sink grille
bb = P.bm(M_BRASS, "Chest")
for k in range(9): box(bb, (-0.096 + k * 0.024, 0.155, 1.38), (0.010, 0.03, 0.26))
for dz in (0.14, -0.14): box(bb, (0, 0.145, 1.38 + dz), (0.23, 0.035, 0.014))
# neck ring + gorget
blob(S(M_DARK, "Neck"), (0, -0.043, 1.50), (0, -0.043, 1.58), 0.075, 0.08, 1.0, rows=4, n=12, pw=6.0)
slab_e(P.bm(M_IRON, "Neck"), (0, -0.115, 1.535), (0.17, 0.07, 0.04), (0.5, 0, 0), 0.010)

# ---------------------------------------------------------------- head: box helmet, skull-mask face, brass stripe
hb = P.bm(M_IRON, "Head")
slab_e(hb, (0, -0.04, 1.68), (0.20, 0.23, 0.13), (0, 0, 0), 0.026, 0.006)                      # helmet shell
slab_e(hb, (0, -0.135, 1.60), (0.15, 0.04, 0.15), (0, 0, 0), 0.016)                     # face plate
slab_e(hb, (0, 0.03, 1.58), (0.16, 0.12, 0.12), (0.2, 0, 0), 0.02)                      # back of skull
for s in (-1, 1):
    slab_e(hb, (s * 0.100, -0.06, 1.60), (0.04, 0.20, 0.13), (0, 0, 0), 0.012)          # cheek plates
hbr = P.bm(M_BRASS, "Head")
slab_e(hbr, (0, -0.045, 1.752), (0.045, 0.24, 0.012), (0, 0, 0), 0.004)                 # crown stripe
slab_e(hbr, (0, -0.152, 1.676), (0.045, 0.012, 0.06), (0, 0, 0), 0.004)                 # brow stripe
slab_e(hbr, (0, -0.152, 1.545), (0.14, 0.012, 0.012), (0, 0, 0), 0.003)
bdk = P.bm(M_DARK, "Head")
box(bdk, (0, -0.158, 1.612), (0.14, 0.006, 0.05))                                       # eye band
box(bdk, (0, -0.158, 1.567), (0.012, 0.006, 0.075))                                     # nose/mouth slit
for s in (-1, 1): box(bdk, (s * 0.034, -0.158, 1.560), (0.010, 0.006, 0.05))
for s in (-1, 1):
    ell(P.bm(M_GLOW, "Head", True), (s * 0.038, -0.161, 1.613), (0.020, 0.008, 0.020), seg=10, rings=6)
    cyl(P.bm(M_BRASS, "Head"), (s * 0.106, -0.04, 1.63), (1, 0, 0), 0.026, 0.016, 12)

# ---------------------------------------------------------------- arms
for s, tg in ((1, "L"), (-1, "R")):
    sh, up, lo, hd = "Shoulder." + tg, "UpperArm." + tg, "LowerArm." + tg, "Hand." + tg
    m = lambda p, s=s: sg(s, p)
    # shoulder pauldron: stacked iron plates, ceramic dome, glowing vent, brass heat-sink fins
    ell(S(M_CERAM, up), m((0.20, -0.056, 1.42)), (0.085, 0.085, 0.085), seg=12, rings=8)
    ib = P.bm(M_IRON, up)
    slab_e(ib, m((0.205, -0.056, 1.515)), (0.26, 0.20, 0.036), (0, s * 0.35, 0), 0.014, 0.008)
    slab_e(ib, m((0.235, -0.056, 1.465)), (0.24, 0.19, 0.034), (0, s * 0.55, 0), 0.014, 0.007)
    slab_e(ib, m((0.265, -0.056, 1.42)), (0.20, 0.17, 0.032), (0, s * 0.75, 0), 0.012)
    slab_e(ib, m((0.15, -0.14, 1.46)), (0.07, 0.03, 0.16), (0, 0, 0), 0.010)         # front rim
    gb = P.bm(M_GLOW, up); db = P.bm(M_DARK, up)
    box(gb, m((0.285, -0.056, 1.40)), (0.012, 0.13, 0.05), (0, s * 0.3, 0))
    for k in range(5): box(db, m((0.292, -0.056 - 0.05 + k * 0.025, 1.40)), (0.012, 0.007, 0.055), (0, s * 0.3, 0))
    fb = P.bm(M_BRASS, 'Chest')
    for k in range(6):                                                                  # fins leaning back
        hgt = 0.17 - 0.02 * k
        slab_e(fb, m((0.15 + 0.024 * k, 0.0, 1.545 + 0.5 * hgt * 0.4)), (0.011, hgt, 0.11), (-0.5, 0, 0), 0.003)
    # upper arm: ceramic core + big iron plates
    blob(S(M_CERAM, up), m((0.27, -0.057, 1.435)), m((0.40, -0.057, 1.435)), 0.068, 0.062, 1.0, rows=5, n=12, pw=6.0)
    UA = Sweep(m((0.20, -0.057, 1.435)), m((0.37, -0.057, 1.435)), Vector((0, -1, 0)), Z, 0.074, 0.074)
    plates_around(P.bm(M_IRON, up), UA, 0.5, (math.pi / 2, 0, math.pi, 1.5 * math.pi), 0.10, 0.14, 0.03, q=0.010, rivet=0.005)
    # elbow hub
    cyl(P.bm(M_BRASS, lo), m((0.40, -0.058, 1.435)), (0, 0, 1), 0.045, 0.15, 14)
    cyl(P.bm(M_DARK, lo), m((0.40, -0.058, 1.512)), (0, 0, 1), 0.02, 0.012, 10)
    # forearm: ceramic + vambrace plates
    blob(S(M_CERAM, lo), m((0.42, -0.064, 1.435)), m((0.575, -0.088, 1.435)), 0.07, 0.052, 1.0, rows=5, n=12, pw=6.0)
    FA = Sweep(m((0.40, -0.062, 1.435)), m((0.57, -0.088, 1.435)), Vector((0, -1, 0)), Z, 0.082, 0.082, )
    plates_around(P.bm(M_IRON, lo), FA, 0.45, (math.pi / 2, 0, math.pi, 1.5 * math.pi), 0.11, 0.16, 0.032, q=0.010, rivet=0.005)
    cyl(P.bm(M_BRASS, lo), m((0.572, -0.087, 1.435)), (1, 0, 0), 0.06, 0.022, 14)           # wrist band
    # gauntlet: iron back-of-hand block + finger blocks per bone
    hbm = P.bm(M_IRON, hd)
    slab_e(hbm, m((0.655, -0.088, 1.452)), (0.14, 0.10, 0.03), (0, 0, 0), 0.010)
    slab_e(hbm, m((0.655, -0.088, 1.415)), (0.12, 0.09, 0.03), (0, 0, 0), 0.008)
    for fbn in ("Index", "Middle", "Ring", "Pinky"):
        for seg in (2, 3, 4):
            bn = "%s%d.%s" % (fbn, seg, tg)
            bo = arm.data.bones[bn]; a, c = Vector(bo.head_local), Vector(bo.tail_local)
            if seg == 4: c = c + (c - a).normalized() * 0.012
            blob(S(M_IRON, bn), a - (c - a).normalized() * 0.004, c, 0.0165, 0.0155, 1.0, rows=3, n=6, pw=6.0)
    for seg in (2, 3):
        bn = "Thumb%d.%s" % (seg, tg)
        bo = arm.data.bones[bn]; a, c = Vector(bo.head_local), Vector(bo.tail_local)
        if seg == 3: c = c + (c - a).normalized() * 0.012
        blob(S(M_IRON, bn), a, c, 0.021, 0.017, 1.0, rows=3, n=6, pw=6.0)

# ---------------------------------------------------------------- legs
for s, tg in ((1, "L"), (-1, "R")):
    up, lo, ft = "UpperLeg." + tg, "LowerLeg." + tg, "Foot." + tg
    cx = 0.121 * s; outer = 0.0 if s > 0 else math.pi
    blob(S(M_CERAM, up), (cx, -0.05, 1.0), (cx, -0.086, 0.52), 0.095, 0.082, 1.1, rows=6, n=12, pw=6.0)
    TH = Sweep((cx, -0.05, 1.0), (cx, -0.086, 0.55), X, FRONT, interp([(0, 0.105), (1, 0.088)]), interp([(0, 0.115), (1, 0.098)]))
    pi_ = P.bm(M_IRON, up)
    plates_around(pi_, TH, 0.38, (math.pi / 2,), 0.15, 0.30, 0.04, q=0.014, rivet=0.007)
    plates_around(pi_, TH, 0.40, (outer,), 0.12, 0.28, 0.035, q=0.012)
    plates_around(pi_, TH, 0.45, (1.5 * math.pi,), 0.13, 0.22, 0.03, q=0.010)
    ell(S(M_BRASS, up), (cx, -0.05, 0.97), (0.04, 0.04, 0.04), seg=10, rings=6)
    # knee: brass hub discs on the sides + iron cop
    cyl(P.bm(M_BRASS, lo), (cx, -0.088, 0.535), (1, 0, 0), 0.05, 0.20, 16)
    cyl(P.bm(M_DARK, lo), (cx + s * 0.105, -0.088, 0.535), (1, 0, 0), 0.028, 0.012, 12)
    slab_e(P.bm(M_IRON, lo), (cx, -0.158, 0.545), (0.15, 0.13, 0.055), (0.0, 0, 0), 0.020, 0.008)
    slab_e(P.bm(M_IRON, lo), (cx, -0.150, 0.46), (0.12, 0.07, 0.04), (0.5, 0, 0), 0.012)
    # shin: ceramic + greaves
    blob(S(M_CERAM, lo), (cx, -0.085, 0.52), (cx, -0.058, 0.09), 0.078, 0.062, 1.0, rows=6, n=12, pw=6.0)
    SH = Sweep((cx, -0.085, 0.50), (cx, -0.060, 0.10), X, FRONT, interp([(0, 0.085), (1, 0.070)]), interp([(0, 0.093), (1, 0.078)]))
    pl = P.bm(M_IRON, lo)
    plates_around(pl, SH, 0.45, (math.pi / 2,), 0.14, 0.30, 0.04, q=0.014, rivet=0.007)
    plates_around(pl, SH, 0.5, (outer,), 0.12, 0.30, 0.035, q=0.012)
    plates_around(pl, SH, 0.5, (1.5 * math.pi,), 0.13, 0.30, 0.04, q=0.012)
    # boots: chunky iron with brass hub, ribbed sole
    cyl(P.bm(M_BRASS, ft), (cx, -0.062, 0.07), (1, 0, 0), 0.04, 0.19, 14)
    bf = P.bm(M_IRON, ft)
    slab_e(bf, (cx, -0.10, 0.085), (0.15, 0.30, 0.10), (0, 0, 0), 0.025)
    slab_e(bf, (cx, -0.24, 0.06), (0.14, 0.09, 0.08), (0, 0, 0), 0.02)                   # toe cap
    slab_e(bf, (cx, -0.185, 0.145), (0.12, 0.10, 0.04), (0.25, 0, 0), 0.012)
    slab_e(bf, (cx, 0.03, 0.12), (0.13, 0.06, 0.13), (0, 0, 0), 0.012)                   # heel counter
    for k in range(5): box(P.bm(M_DARK, ft), (cx, -0.22 + k * 0.055, 0.012), (0.155, 0.018, 0.024))

# ---------------------------------------------------------------- forge-hammer on the lower back
hd_ = P.bm(M_IRON, "Hips"); hl = P.bm(M_LEATH, "Hips")
cyl(hl, (-0.04, 0.18, 0.99), (1, 0, 0), 0.020, 0.40, 10)
cyl(P.bm(M_BRASS, "Hips"), (-0.245, 0.18, 0.99), (1, 0, 0), 0.026, 0.02, 10)
slab_e(hd_, (0.19, 0.18, 0.99), (0.15, 0.115, 0.115), (0, 0, 0), 0.016)
box(P.bm(M_GLOW, "Hips"), (0.19, 0.18 + 0.059, 0.99), (0.09, 0.006, 0.03))
slab_e(P.bm(M_BRASS, "Hips"), (0.12, 0.18, 0.99), (0.012, 0.122, 0.122), (0, 0, 0), 0.003)
for k in range(2): box(P.bm(M_BRASS, "Hips"), (-0.06 + k * 0.07, 0.178, 0.99), (0.018, 0.045, 0.045))

P.flush("")
print("TRIS", tri_count())
finish(OUT, "cinderplate")
