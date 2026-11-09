"""Wirewraith hero: slender data-ghost automaton, braided copper and silver wire woven round a dark ceramic frame (Blender 5.x).
Run: blender -b -P build_wirewraith.py -- <mechanical.glb> <out_dir>
Smooth dark ceramic egg head with two round cyan eyes in brass bezels, a crown of glowing fibre-optic strands, criss-crossed copper/silver
helical wire weave on every limb and the torso (skinned), a hanging wire-lattice skirt, brass spring/bearing joints, stiletto feet, neural-lash at the hip."""
import bpy, bmesh, math, sys, os, random
import numpy as np
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mech_common import *

SRC, OUT = sys.argv[-2], sys.argv[-1]
random.seed(61)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
remove_objects("_Head", "_Feet")
TEX = os.path.join(OUT, "tex")

def braid_tex(name, base, seed, n=256):
    x, y = T._grid(n); f = T.fbm(n, seed, 4, 8)
    a = np.sin(2 * np.pi * (x * 4 + y * 8)); b = np.sin(2 * np.pi * (x * 4 - y * 8))
    k = (0.65 + 0.35 * np.maximum(a * 0.5 + 0.5, b * 0.5 + 0.5))
    col = np.array(base, np.float32)[None, None, :] * k[..., None] * (0.85 + 0.3 * f[..., None])
    h = 0.5 * (a + b) * 0.5 + 0.3 * f
    return (T.to_image(name + "_diffuse", np.concatenate([np.clip(col, 0, 1), np.ones((n, n, 1), np.float32)], -1), TEX),
            T.to_image(name + "_normal", T.normal_from_height(h, 0.8), TEX, "Non-Color"))
M_COPPER = mat("WW_Copper", (0.74, 0.42, 0.24), 0.32, 0.85); T.bind(M_COPPER, *braid_tex("ww_copper", (0.78, 0.45, 0.26), 3))
M_SILVER = mat("WW_Silver", (0.78, 0.80, 0.84), 0.28, 0.9); T.bind(M_SILVER, *braid_tex("ww_silver", (0.80, 0.82, 0.86), 5))
M_FRAME = make_metal_mat("WW_Ceramic", (0.14, 0.14, 0.15), "plate", TEX, 0.35, 0.45, seed=33)
M_BRASS = make_metal_mat("WW_Brass", (0.66, 0.50, 0.22), "brass", TEX, 0.3, 0.9, seed=8)
M_GLOW = mat("WW_Glow", (0.3, 0.9, 1.0), 0.2, 0.0, emit=(0.25, 0.9, 1.0), strength=6.0)
M_FIBER = mat("WW_Fiber", (0.75, 0.88, 0.92), 0.25, 0.3, emit=(0.35, 0.8, 0.9), strength=0.9)
strip_base(); override_base(M_FRAME)
P = Parts(arm)
X = Vector((1, 0, 0)); Y = Vector((0, 1, 0)); Z = Vector((0, 0, 1)); FRONT = Vector((0, -1, 0))
def S(m, b): return P.bm(m, b, True)
def sg(s, p): return Vector((p[0] * s, p[1], p[2]))

def polytube(bm, pts, r, n=4, rfn=None, uvk=30.0):
    """Round wire along a polyline (parallel-transport frame), uv = (length*uvk, around)."""
    pts = [Vector(p) for p in pts]; N = len(pts); n = 3 if n == 4 else n
    if N < 2: return
    uvl = bm.loops.layers.uv.get("UVMap") or bm.loops.layers.uv.new("UVMap")
    t0 = (pts[1] - pts[0]).normalized(); u = t0.cross(Z)
    if u.length < 1e-3: u = t0.cross(X)
    u.normalize(); rows = []; acc = [0.0]
    for i in range(1, N): acc.append(acc[-1] + (pts[i] - pts[i - 1]).length)
    for i in range(N):
        t = ((pts[min(i + 1, N - 1)] - pts[max(i - 1, 0)])).normalized()
        u = (u - t * u.dot(t)).normalized(); v = t.cross(u)
        rr = r * (rfn(i / (N - 1)) if rfn else 1.0)
        rows.append([bm.verts.new(pts[i] + (u * math.cos(2 * math.pi * c / n) + v * math.sin(2 * math.pi * c / n)) * rr) for c in range(n)])
    for i in range(N - 1):
        for c in range(n):
            c2 = (c + 1) % n
            try: f = bm.faces.new((rows[i][c], rows[i][c2], rows[i + 1][c2], rows[i + 1][c]))
            except ValueError: continue
            uvs = ((acc[i] * uvk, c / n), (acc[i] * uvk, (c + 1) / n), (acc[i + 1] * uvk, (c + 1) / n), (acc[i + 1] * uvk, c / n))
            for lp, uv in zip(f.loops, uvs): lp[uvl].uv = uv

def helix(bm, sw, t0, t1, turns, a0, l, r, steps=14, direction=1, n=4, wob=0.0):
    pts = []
    for i in range(steps + 1):
        t = t0 + (t1 - t0) * i / steps
        a = a0 + direction * turns * 2 * math.pi * i / steps
        pts.append(sw.P(t, a, l + (wob * math.sin(i * 1.7 + a0) if wob else 0.0)))
    polytube(bm, pts, r, n)

def weave(bmc, bms, sw, t0, t1, turns, l, r, steps=14, strands=2, bone_bm=None):
    for k in range(strands):
        ph = 2 * math.pi * k / strands
        helix(bmc, sw, t0, t1, turns, ph, l, r, steps, 1, wob=0.0015)
        helix(bms, sw, t0, t1, turns, ph + math.pi / strands, l + 0.0008, r, steps, -1, wob=0.0015)

# ---------------------------------------------------------------- torso frame + weave (skinned)
tr = interp([(0.0, 0.088), (0.17, 0.098), (0.45, 0.074), (0.70, 0.068), (0.88, 0.092), (1.0, 0.104)])
tyf = interp([(0.0, 0.062), (0.17, 0.072), (0.45, 0.056), (0.70, 0.054), (0.88, 0.070), (1.0, 0.078)])
TS = Sweep((0, -0.055, 1.47), (0, -0.06, 0.95), X, FRONT, tr, tyf)
def torso_w(co):
    ch = smoothstep(1.30, 1.40, co.z); tq = smoothstep(1.12, 1.22, co.z) * (1 - ch); ab = smoothstep(1.00, 1.06, co.z) * (1 - ch - tq)
    return {"Chest": ch, "Torso": tq, "Abdomen": ab, "Hips": max(0.0, 1 - ch - tq - ab)}
fr = bmesh.new(); blob_sw(fr, TS, rows=14, n=14, pw=6.0)
skinned(arm, "Hero_TorsoFrame", fr, M_FRAME, torso_w)
wc = bmesh.new(); ws = bmesh.new()
for k in range(3):
    ph = 2 * math.pi * k / 3
    helix(wc, TS, 0.03, 0.97, 2.3, ph, 0.004, 0.0042, 34, 1, wob=0.002)
    helix(ws, TS, 0.03, 0.97, 2.3, ph + math.pi / 3, 0.0065, 0.0042, 34, -1, wob=0.002)
for z in (1.44, 1.30, 1.16, 1.04):                                                    # horizontal binding hoops
    t = (1.47 - z) / 0.52
    pts = [TS.P(t, 2 * math.pi * i / 20, 0.008) for i in range(21)]
    polytube(wc if z in (1.44, 1.16) else ws, pts, 0.0048, 4)
skinned(arm, "Hero_TorsoCopper", wc, M_COPPER, torso_w); skinned(arm, "Hero_TorsoSilver", ws, M_SILVER, torso_w)
# drapes: scarf cables crossing the chest/shoulders
dc = bmesh.new(); ds = bmesh.new()
def drape(bm, a_from, a_to, z0, z1, off, sag, r=0.0055):
    pts = []
    for i in range(24):
        t = i / 23
        a = a_from + (a_to - a_from) * t
        z = z0 + (z1 - z0) * t - sag * math.sin(math.pi * t)
        tt = (1.47 - z) / 0.52
        pts.append(TS.P(max(0, min(1, tt)), a, off))
    polytube(bm, pts, r, 4)
drape(dc, math.radians(-30), math.radians(250), 1.50, 1.10, 0.012, 0.04)
drape(ds, math.radians(210), math.radians(-70), 1.50, 1.08, 0.016, 0.05)
drape(dc, math.radians(170), math.radians(-20), 1.52, 1.40, 0.014, 0.02, 0.0065)
drape(ds, math.radians(10), math.radians(200), 1.52, 1.38, 0.018, 0.02, 0.0065)
skinned(arm, "Hero_DrapeCopper", dc, M_COPPER, torso_w); skinned(arm, "Hero_DrapeSilver", ds, M_SILVER, torso_w)
# collar rings at the neck + brass belt pins
for k in range(3):
    cyl(P.bm(M_BRASS, "Chest" if k else "Neck"), (0, -0.043, 1.50 + k * 0.012), (0, 0, 1), 0.043 - 0.004 * k, 0.008, 12)
for sx in (1, -1): ell(S(M_BRASS, "Hips"), (sx * 0.11, -0.06, 1.0), (0.012, 0.012, 0.012), seg=6, rings=4)

# ---------------------------------------------------------------- head: smooth egg, bezel eyes, brass collar, wire cap, fibre crown
hb = S(M_FRAME, "Head")
blob_sw(hb, Sweep((0, -0.04, 1.545), (0, -0.04, 1.755), X, FRONT, interp([(0, 0.040), (0.30, 0.074), (0.65, 0.082), (1, 0.040)]), interp([(0, 0.060), (0.3, 0.098), (0.65, 0.105), (1, 0.06)])), rows=11, n=14, pw=2.0)
blob(S(M_FRAME, "Neck"), (0, -0.043, 1.50), (0, -0.043, 1.58), 0.030, 0.026, 1.0, rows=4, n=10, pw=6.0)
for sx in (1, -1):
    c = Vector((sx * 0.046, -0.108, 1.628)); d = Vector((sx * 0.45, -1, 0.0)).normalized()
    cyl(P.bm(M_BRASS, "Head"), c, d, 0.0235, 0.012, 14)
    cyl(P.bm(M_FRAME, "Head"), c + d * 0.004, d, 0.0185, 0.012, 14)
    ell(S(M_GLOW, "Head"), c + d * 0.009, (0.0145, 0.0145, 0.006), rot=(0, 0, math.atan2(d.y, d.x) + math.pi / 2 + 0 if False else 0), seg=12, rings=6)
bwc = bmesh.new(); bws = bmesh.new()
HC = Vector((0, -0.04, 1.65))
def head_pt(az, el, l=0.004):
    rxh, ryh, rzh = 0.078, 0.100, 0.108
    return HC + Vector((math.cos(el) * math.sin(az) * (rxh + l), -math.cos(el) * math.cos(az) * (ryh + l), math.sin(el) * (rzh + l)))
for k in range(6):                                                                    # meridian wires over the skull
    az = math.radians(-150 + 60 * k + 15)
    pts = [head_pt(az, math.radians(-10 + 100 * i / 14)) for i in range(15)]
    polytube(bwc if k % 2 == 0 else bws, pts, 0.0033, 4)
for el in (30, 52, 72):
    pts = [head_pt(math.radians(-170 + 340 * i / 24), math.radians(el), 0.007) for i in range(25)]
    polytube(bws if el == 52 else bwc, pts, 0.003, 4)
attach(arm, "Hero_HeadCopper", bwc, M_COPPER, "Head"); attach(arm, "Hero_HeadSilver", bws, M_SILVER, "Head")
bf = bmesh.new(); bg = bmesh.new()
for k in range(40):                                                                   # fibre-optic crown, swept back and down
    az = random.uniform(-math.pi, math.pi); el = random.uniform(55, 88)
    root = head_pt(az, math.radians(el), 0.0)
    sx = math.sin(az); L = random.uniform(0.55, 0.95)
    pts = []
    for i in range(8):
        s = i / 7
        pts.append(root + Vector((sx * 0.16 * s * L + 0.02 * math.sin(s * 6 + k), (0.16 * s + 0.20 * s * s) * L, (0.12 * s - 0.50 * s * s) * L)))
    polytube(bf, pts, 0.0017, 3, rfn=lambda t: 1.0 - 0.5 * t)
    ell(bg, pts[-1], (0.0048, 0.0048, 0.0048), seg=4, rings=3)
attach(arm, "Hero_FiberCrown", bf, M_FIBER, "Head"); attach(arm, "Hero_FiberTips", bg, M_GLOW, "Head")

# ---------------------------------------------------------------- arms: ceramic frame + counter-wound wire weave
for s, tg in ((1, "L"), (-1, "R")):
    up, lo, hd = "UpperArm." + tg, "LowerArm." + tg, "Hand." + tg
    m = lambda p, s=s: sg(s, p)
    U = Vector((0, -1, 0))
    ell(S(M_FRAME, "Shoulder." + tg), m((0.155, -0.06, 1.43)), (0.040, 0.040, 0.040), seg=10, rings=6)
    cyl(P.bm(M_BRASS, up), m((0.155, -0.06, 1.43)), (0, 1, 0), 0.020, 0.074, 10)
    blob(S(M_FRAME, up), m((0.17, -0.057, 1.435)), m((0.345, -0.057, 1.435)), 0.032, 0.026, 1.0, rows=5, n=10, pw=6.0)
    UA = Sweep(m((0.18, -0.057, 1.435)), m((0.335, -0.057, 1.435)), U, Z, interp([(0, 0.034), (1, 0.027)]))
    weave(S(M_COPPER, up), S(M_SILVER, up), UA, 0.0, 1.0, 1.6, 0.004, 0.0035, 15, 2)
    cyl(P.bm(M_BRASS, lo), m((0.335, -0.058, 1.435)), (0, 0, 1), 0.026, 0.056, 12)               # elbow bearing
    cyl(P.bm(M_FRAME, lo), m((0.335, -0.058, 1.472)), (0, 0, 1), 0.014, 0.010, 10)
    blob(S(M_FRAME, lo), m((0.345, -0.06, 1.435)), m((0.57, -0.086, 1.435)), 0.026, 0.019, 1.0, rows=5, n=10, pw=6.0)
    FA = Sweep(m((0.35, -0.062, 1.435)), m((0.565, -0.086, 1.435)), U, Z, interp([(0, 0.028), (1, 0.021)]))
    weave(S(M_COPPER, lo), S(M_SILVER, lo), FA, 0.0, 1.0, 2.0, 0.004, 0.0035, 18, 2)
    for k in range(2): cyl(P.bm(M_BRASS, lo), m((0.552 + 0.012 * k, -0.085, 1.435)), (1, 0, 0), 0.026 - 0.003 * k, 0.010, 12)   # wrist rings
    for fb in ("Index", "Middle", "Ring", "Pinky"):                                       # brass finger knuckles
        hp = bone_pt(arm, fb + "2." + tg)
        ell(S(M_BRASS, fb + "2." + tg), hp, (0.0085, 0.0085, 0.0085), seg=6, rings=4)

# ---------------------------------------------------------------- legs
for s, tg in ((1, "L"), (-1, "R")):
    up, lo, ft = "UpperLeg." + tg, "LowerLeg." + tg, "Foot." + tg
    cx = 0.121 * s; wc_ = S(M_COPPER, up); ws_ = S(M_SILVER, up)
    ell(S(M_FRAME, up), (cx, -0.05, 0.965), (0.04, 0.04, 0.04), seg=10, rings=6)
    blob(S(M_FRAME, up), (cx, -0.05, 0.98), (cx, -0.087, 0.55), 0.058, 0.040, 1.05, rows=6, n=12, pw=6.0)
    TH = Sweep((cx, -0.05, 0.97), (cx, -0.087, 0.56), X, FRONT, interp([(0, 0.060), (1, 0.042)]), interp([(0, 0.064), (1, 0.045)]))
    weave(wc_, ws_, TH, 0.0, 1.0, 2.2, 0.004, 0.0038, 20, 3)
    # knee: ceramic bearing disc with a brass rim and glowing lens
    cyl(P.bm(M_FRAME, lo), (cx, -0.088, 0.535), (1, 0, 0), 0.040, 0.10, 14)
    for dx in (0.052, -0.052): cyl(P.bm(M_BRASS, lo), (cx + dx, -0.088, 0.535), (1, 0, 0), 0.042, 0.010, 14)
    ell(S(M_GLOW, lo), (cx + s * 0.056, -0.088, 0.535), (0.008, 0.016, 0.016), seg=8, rings=5)
    blob(S(M_FRAME, lo), (cx, -0.087, 0.53), (cx, -0.062, 0.12), 0.040, 0.026, 1.0, rows=6, n=12, pw=6.0)
    SH = Sweep((cx, -0.087, 0.52), (cx, -0.062, 0.13), X, FRONT, interp([(0, 0.044), (1, 0.029)]), interp([(0, 0.046), (1, 0.031)]))
    weave(S(M_COPPER, lo), S(M_SILVER, lo), SH, 0.0, 1.0, 2.0, 0.004, 0.0036, 18, 3)
    # ankle spring joint (brass coil) and stiletto foot
    pts = [Vector((cx + 0.022 * math.cos(4 * 2 * math.pi * i / 36), -0.062 + 0.022 * math.sin(4 * 2 * math.pi * i / 36), 0.125 - 0.075 * i / 36)) for i in range(37)]
    polytube(S(M_BRASS, ft), pts, 0.0045, 5)
    cyl(P.bm(M_BRASS, ft), (cx, -0.062, 0.128), (0, 0, 1), 0.028, 0.012, 12)
    cyl(P.bm(M_BRASS, ft), (cx, -0.062, 0.05), (0, 0, 1), 0.027, 0.010, 12)
    hull(P.bm(M_FRAME, ft), [(cx - 0.026, -0.04, 0.05), (cx + 0.026, -0.04, 0.05), (cx - 0.026, 0.02, 0.045), (cx + 0.026, 0.02, 0.045),
                              (cx - 0.03, -0.12, 0.012), (cx + 0.03, -0.12, 0.012), (cx - 0.024, -0.12, 0.03), (cx + 0.024, -0.12, 0.03),
                              (cx - 0.02, -0.2, 0.005), (cx + 0.02, -0.2, 0.005), (cx, -0.23, 0.003), (cx - 0.024, 0.015, 0.0), (cx + 0.024, 0.015, 0.0)])
    for k in range(4):                                                                  # toes
        ell(S(M_FRAME, ft), (cx + (k - 1.5) * 0.015, -0.2 - 0.004 * (1 - abs(k - 1.5) / 1.5), 0.008), (0.0075, 0.012, 0.007), seg=6, rings=4)

# ---------------------------------------------------------------- wire-lattice skirt (skinned to hips + thighs)
SK = Sweep((0, -0.058, 1.02), (0, -0.075, 0.50), X, FRONT, interp([(0, 0.150), (1, 0.215)]), interp([(0, 0.105), (1, 0.150)]))
skc = bmesh.new(); sks = bmesh.new()
NS = 20
def hem(a):                                                    # pointed hem: long at the front/back centres, short at the sides
    return 0.55 + 0.45 * abs(math.sin(a)) ** 1.5 if True else 1.0
for i in range(NS):
    a = 2 * math.pi * i / NS
    h = 0.40 + 0.6 * abs(math.sin(a)) ** 1.6 * (0.9 + 0.1 * math.sin(i * 2.3))
    h = min(h, 1.0)
    pts = [SK.P(h * j / 7, a, 0.004 + 0.005 * math.sin(j + i)) for j in range(8)]
    polytube(skc if i % 2 == 0 else sks, pts, 0.0034, 4)
    a2 = 2 * math.pi * (i + 2) / NS; h2 = min(0.38 + 0.6 * abs(math.sin(a2)) ** 1.6, 1.0)
    he = min(h, h2) * 0.95
    polytube(sks, [SK.P(he * j / 7, a + (a2 - a) * j / 7, 0.009) for j in range(8)], 0.0026, 4)
    polytube(skc, [SK.P(he * j / 7, a2 - (a2 - a) * j / 7, 0.013) for j in range(8)], 0.0026, 4)
for k in range(1, 4):                                          # horizontal hoops down the skirt
    t = 0.18 * k
    polytube(sks if k % 2 else skc, [SK.P(t, 2 * math.pi * i / 20, 0.01 + 0.003 * k) for i in range(21)], 0.0032, 4)
def skirt_w(co):
    t = smoothstep(0.98, 0.62, co.z); leg = "UpperLeg.L" if co.x >= 0 else "UpperLeg.R"
    wl = min(0.9, t * (0.2 + 0.7 * max(0.0, -co.y - 0.02) / 0.13) * smoothstep(0.0, 0.07, abs(co.x)))
    return {"Hips": 1.0 - wl, leg: wl}
skinned(arm, "Hero_SkirtCopper", skc, M_COPPER, skirt_w); skinned(arm, "Hero_SkirtSilver", sks, M_SILVER, skirt_w)

# ---------------------------------------------------------------- neural-lash: braided coil with a glowing plug at the left hip
lc = bmesh.new(); ls = bmesh.new(); lg = bmesh.new(); lf = bmesh.new()
cc = Vector((0.225, -0.03, 0.84)); R = 0.065
for ph, bmx, r in ((0.0, lc, 0.0065), (math.pi, ls, 0.0065)):
    pts = [cc + Vector((0.016 * (i / 18), R * math.cos(2 * math.pi * 2 * i / 18 + ph * 0.0) * 0.9, R * math.sin(2 * math.pi * 2 * i / 18) + 0.007 * (1 if bmx is lc else -1))) for i in range(37)]
    polytube(bmx, pts, r, 5)
tail = cc + Vector((0.032, R * 0.9, 0.0)); pt0 = tail
pts = [tail + Vector((0.01 * math.sin(i), -0.01 * i, -0.025 * i)) for i in range(8)]
polytube(lc, pts, 0.0065, 5); polytube(ls, [p + Vector((0, 0.004, 0.003)) for p in pts], 0.0065, 5)
end = pts[-1]
attach(arm, "Hero_LashCopper", lc, M_COPPER, "Hips"); attach(arm, "Hero_LashSilver", ls, M_SILVER, "Hips")
cyl(P.bm(M_BRASS, "Hips"), end + Vector((0, -0.015, -0.025)), (0, -0.4, -1), 0.016, 0.05, 10)
cyl(P.bm(M_GLOW, "Hips"), end + Vector((0, -0.017, -0.048)), (0, -0.4, -1), 0.0175, 0.012, 10)
cyl(P.bm(M_BRASS, "Hips"), end + Vector((0, -0.024, -0.07)), (0, -0.4, -1), 0.011, 0.03, 8)
for k in range(9):                                                                      # fibre spray off the plug
    a = random.uniform(0, 2 * math.pi); sp = Vector((math.cos(a) * 0.05, -0.06 + math.sin(a) * 0.02, -0.04)) * random.uniform(0.7, 1.3)
    base = end + Vector((0, -0.035, -0.088))
    ppts = [base + sp * (i / 7) + Vector((0, 0, -0.04 * (i / 7) ** 2)) for i in range(8)]
    polytube(lf, ppts, 0.0013, 3, rfn=lambda t: 1 - 0.4 * t); ell(lg, ppts[-1], (0.004, 0.004, 0.004), seg=4, rings=3)
attach(arm, "Hero_LashFiber", lf, M_FIBER, "Hips"); attach(arm, "Hero_LashTips", lg, M_GLOW, "Hips")
strip_ = P.bm(M_BRASS, "Hips"); strap(strip_, (0.18, -0.058, 1.01), (0.215, -0.03, 0.9), 0.014, 0.004)

P.flush("")
print("TRIS", tri_count())
finish(OUT, "wirewraith")
