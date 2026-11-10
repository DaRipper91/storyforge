"""Thornmimic hero: woodland bark spirit on the primal shared-skeleton base (Blender 5.x).
Run: blender -b -P build_thornmimic.py -- <primal.glb> <out_dir>
Bark-skinned body, carved wooden face, branching antler-crown with leaves and thorns, layered bark-veil (cape + skirt strips, skinned),
thorn vines coiled around limbs and torso, moss clumps, lichen discs, twisted-root legs and gripping root feet. Baked bark/veil/moss/leaf textures."""
import bpy, bmesh, math, sys, os, random
import numpy as np
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hero_common import *
import hero_textures as T

SRC, OUT = sys.argv[-2], sys.argv[-1]
random.seed(23)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
remove_objects("_Head", "_Feet")
TEX = os.path.join(OUT, "tex_tm")


def rgba(col):
    return np.concatenate([col, np.ones(col.shape[:2] + (1,), np.float32)], -1)


# ---------- textures ----------
def bark_tex():
    n = 512; x, y = T._grid(n)
    nz = T.fbm(n, 3, 5, 5); stretch = T.fbm(n, 4, 4, 3)
    grain = 0.5 + 0.5 * np.sin((x * 38 + stretch * 6 + nz * 2) * np.pi)
    e, cid = T.voronoi(n, 5, 7)
    crack = 1 - T.smooth(0.0, 0.08, e * (0.5 + 0.5 * stretch))
    base = np.array([0.30, 0.20, 0.12], np.float32)
    col = base[None, None, :] * (0.65 + 0.55 * grain[..., None]) * (0.8 + 0.4 * nz[..., None])
    col *= (1 - 0.65 * crack[..., None])
    col += np.array([0.03, 0.04, 0.0], np.float32)[None, None, :] * T.smooth(0.6, 0.9, nz)[..., None]
    h = 0.5 * grain + 0.5 * nz - 0.9 * crack
    return T.to_image("bark_diffuse", rgba(np.clip(col, 0, 1)), TEX), T.to_image("bark_normal", T.normal_from_height(h, 2.0), TEX, "Non-Color")


def veil_tex():
    n = 512; x, y = T._grid(n); nz = T.fbm(n, 9, 5, 6); st = T.fbm(n, 10, 4, 3)
    grain = 0.5 + 0.5 * np.sin((x * 24 + st * 7) * np.pi)
    e, cid = T.voronoi(n, 4, 12)
    layer = T.smooth(0.0, 0.12, e)
    base = np.array([0.34, 0.20, 0.16], np.float32) * (0.5 + 0.9 * cid[..., None]) * 0.9 + np.array([0.10, 0.06, 0.04], np.float32)
    col = base * (0.7 + 0.45 * grain[..., None]) * (0.8 + 0.35 * nz[..., None]) * (0.55 + 0.45 * layer[..., None])
    lich = (T.fbm(n, 15, 4, 8) > 0.70) & (nz > 0.5)
    col = np.where(lich[..., None], np.array([0.55, 0.62, 0.52], np.float32)[None, None, :] * (0.8 + 0.3 * nz[..., None]), col)
    moss = (T.fbm(n, 18, 4, 6) > 0.68) & (y > 0.3) & ~lich
    col = np.where(moss[..., None], np.array([0.20, 0.30, 0.06], np.float32)[None, None, :] * (0.7 + 0.6 * nz[..., None]), col)
    h = 0.5 * grain + 0.6 * layer + 0.3 * nz + 0.3 * lich
    return T.to_image("veil_diffuse", rgba(np.clip(col, 0, 1)), TEX), T.to_image("veil_normal", T.normal_from_height(h, 1.6), TEX, "Non-Color")


def moss_tex():
    n = 256; nz = T.fbm(n, 31, 5, 10); fine = T.fbm(n, 32, 3, 40)
    col = np.stack([0.14 + 0.16 * nz, 0.24 + 0.26 * nz, 0.04 + 0.05 * nz], -1) * (0.7 + 0.5 * fine[..., None])
    return T.to_image("moss_diffuse", rgba(np.clip(col, 0, 1)), TEX), T.to_image("moss_normal", T.normal_from_height(fine * 0.8 + nz * 0.3, 1.5), TEX, "Non-Color")


def leaf_tex():
    n = 256; x, y = T._grid(n); u = np.abs(x - 0.5) * 2
    vein = np.exp(-((x - 0.5) / 0.02) ** 2) + 0.5 * np.exp(-(((u * 0.7 + y * 1.0) * 7 % 1.0 - 0.5) / 0.1) ** 2) * T.smooth(0.0, 0.6, 1 - u)
    nz = T.fbm(n, 41, 4, 6)
    col = np.stack([0.18 + 0.2 * y, 0.36 + 0.22 * (1 - y) + 0.1 * nz, 0.06 + 0.04 * nz], -1) * (0.8 + 0.3 * nz[..., None])
    col += vein[..., None] * np.array([0.12, 0.12, 0.03], np.float32)
    return T.to_image("leaf_diffuse", rgba(np.clip(col, 0, 1)), TEX), T.to_image("leaf_normal", T.normal_from_height(vein * 0.6 + nz * 0.2, 1.2), TEX, "Non-Color")


bk = bark_tex(); vl = veil_tex(); ms = moss_tex(); lf = leaf_tex()
M_BARK = mat("TM_Bark", (0.30, 0.20, 0.12), 0.85); T.bind(M_BARK, *bk)
M_VEIL = mat("TM_Veil", (0.34, 0.22, 0.16), 0.9); T.bind(M_VEIL, *vl)
M_MOSS = mat("TM_Moss", (0.2, 0.32, 0.06), 0.95); T.bind(M_MOSS, *ms)
M_LEAF = mat("TM_Leaf", (0.25, 0.45, 0.08), 0.6); T.bind(M_LEAF, *lf)
M_VINE = mat("TM_Vine", (0.28, 0.20, 0.10), 0.7)
M_THORN = mat("TM_Thorn", (0.42, 0.16, 0.08), 0.5)
M_LICHEN = mat("TM_Lichen", (0.62, 0.70, 0.58), 0.9)
M_EYE = mat("TM_Eye", (0.55, 0.5, 0.15), 0.1, 0.0, emit=(0.6, 0.55, 0.15), strength=0.9)
M_PUP = mat("TM_Pupil", (0.02, 0.02, 0.01), 0.1)
M_FACE = mat("TM_Face", (0.26, 0.17, 0.09), 0.7)
T.bind(M_VINE, *bk)

# base body/legs: bark material with cylindrical UVs
for _o in bpy.data.objects:
    if _o.type == "MESH" and _o.name.endswith(("_Body", "_Legs")):
        _o.data.materials.clear(); _o.data.materials.append(M_BARK)
        for p in _o.data.polygons: p.material_index = 0
        me = _o.data
        for ul in list(me.uv_layers): me.uv_layers.remove(ul)
        ul = me.uv_layers.new(name="UVMap")
        mw = _o.matrix_world
        for poly in me.polygons:
            for li in poly.loop_indices:
                w = mw @ me.vertices[me.loops[li].vertex_index].co
                ul.data[li].uv = (abs(math.atan2(w.x, -w.y)) / math.pi * 1.5 + (0.0 if w.x >= 0 else 0.0), w.z * 1.6)


# ---------- helpers ----------
def card(bm, uvm, root, direction, length, width, curl=0.2, rows=4, prof=1.0, tipw=2.2):
    d = Vector(direction).normalized(); up = Vector((0, 0, 1))
    side = d.cross(up)
    if side.length < 1e-3: side = Vector((1, 0, 0))
    side.normalize(); nrm = side.cross(d).normalized()
    vs = []
    for r in range(rows):
        t = r / (rows - 1)
        pos = Vector(root) + d * length * t + nrm * (curl * length * t * t)
        w = width * math.sin(min(1.0, 0.3 + t * 0.9) * math.pi / 2) * (1 - t ** tipw) * prof
        row = []
        for c in range(3):
            v = bm.verts.new(pos + side * ((c - 1) * w) + nrm * (abs(c - 1) * w * 0.25))
            uvm[v] = (c / 2.0, 1.0 - t); row.append(v)
        vs.append(row)
    for r in range(rows - 1):
        for c in range(2):
            try: bm.faces.new((vs[r][c], vs[r][c + 1], vs[r + 1][c + 1], vs[r + 1][c]))
            except ValueError: pass


def branch(bm, lbm, luv, tbm, p, d, ln, r, depth, leafy=True):
    """Recursive twig: tube segments with wander, thorns, forks, leaf cards at tips."""
    d = Vector(d).normalized(); p = Vector(p); segs = 3
    for i in range(segs):
        nd = (d + Vector((random.uniform(-.25, .25), random.uniform(-.25, .25), random.uniform(-.1, .2)))).normalized()
        q = p + nd * ln / segs
        r1 = r * (1 - 0.7 / segs)
        tube(bm, p, q, r, r1, seg=5)
        if random.random() < 0.5 and depth > 0:
            cone(tbm, q, (nd + Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))) * 0.8), r * 1.1, 0.018, seg=3)
        if depth > 0 and i >= 1 and random.random() < 0.8:
            sd = (nd + Vector((random.uniform(-.9, .9), random.uniform(-.9, .9), random.uniform(0, .6)))).normalized()
            branch(bm, lbm, luv, tbm, q, sd, ln * 0.62, r1 * 0.7, depth - 1, leafy)
        p = q; d = nd; r = r1
    if leafy and (depth == 0 or random.random() < 0.4):
        for k in range(2 if depth == 0 else 1):
            ld = (d + Vector((random.uniform(-.8, .8), random.uniform(-.8, .8), random.uniform(-.2, .8)))).normalized()
            card(lbm, luv, p, ld, random.uniform(0.045, 0.07), 0.024, curl=0.3, rows=3, tipw=2.5)


def helix(bm, tbm, p0, p1, rad, turns, tr, thorns=True, n=24, sway=0.0):
    p0, p1 = Vector(p0), Vector(p1); ax = (p1 - p0); L = ax.length; axn = ax.normalized()
    a1 = axn.cross(Vector((0, 0, 1)) if abs(axn.z) < 0.9 else Vector((1, 0, 0))).normalized(); a2 = axn.cross(a1)
    prev = None
    for i in range(n + 1):
        t = i / n; ang = turns * 2 * math.pi * t
        rr = rad * (1 + 0.1 * math.sin(t * 17))
        pt = p0 + ax * t + (a1 * math.cos(ang) + a2 * math.sin(ang)) * rr
        if prev is not None:
            tube(bm, prev[0], pt, tr, tr, seg=4)
            if thorns and i % 2 == 0:
                out = (pt - (p0 + ax * t)).normalized()
                cone(tbm, pt, out + axn * 0.3, tr * 1.3, 0.025, seg=3)
        prev = (pt,)


def ringpts(cz, rx, ry, n, rot=0.0, cy=-0.043):
    return [Vector((rx * math.sin(2 * math.pi * k / n + rot), cy - ry * math.cos(2 * math.pi * k / n + rot), cz)) for k in range(n)]


def tw(co):
    ch = smoothstep(1.18, 1.32, co.z); tq = smoothstep(1.02, 1.1, co.z) * (1 - ch)
    return {"Chest": ch, "Torso": tq, "Hips": max(0.0, 1.0 - ch - tq)}


def skw(co):
    t = smoothstep(1.0, 0.4, co.z)
    front = max(0.0, -co.y / max(1e-6, math.hypot(co.x, co.y)))
    wl = t * (0.25 + 0.6 * front)
    return {"Hips": 1.0 - wl, ("UpperLeg.L" if co.x >= 0 else "UpperLeg.R"): wl}


# ---------- head: carved face, crown of branches ----------
HC = Vector((0, -0.075, 1.635))
bm = bmesh.new()
ell(bm, HC, (0.076, 0.095, 0.10), seg=16, rings=10)                               # skull, slightly elongated
ell(bm, (0, -0.105, 1.595), (0.058, 0.06, 0.075), seg=12, rings=8)                # face plane
ell(bm, (0, -0.105, 1.545), (0.032, 0.04, 0.036), seg=10, rings=6)                # narrow chin
tube(bm, (0, -0.152, 1.645), (0, -0.172, 1.59), 0.010, 0.014, seg=6)              # nose ridge
ell(bm, (0, -0.172, 1.582), (0.016, 0.014, 0.011), seg=6, rings=4)                # nose tip
for sx in (1, -1):
    ell(bm, (sx * 0.044, -0.138, 1.634), (0.022, 0.015, 0.011), rot=(0, sx * -0.35, 0), seg=8, rings=5)   # brow ridge
    ell(bm, (sx * 0.048, -0.133, 1.59), (0.020, 0.018, 0.015), seg=8, rings=5)                          # cheekbone
    ell(bm, (sx * 0.062, -0.03, 1.62), (0.010, 0.025, 0.04), seg=6, rings=4)                            # ear knot
ell(bm, (0, -0.04, 1.51), (0.036, 0.036, 0.06), seg=10, rings=6)                  # neck
ell(bm, (0, -0.154, 1.553), (0.020, 0.006, 0.0035), seg=6, rings=3)               # mouth line
attach(arm, "Hero_Face", bm, M_FACE, "Head")
bm = bmesh.new()
for sx in (1, -1):
    ell(bm, (sx * 0.034, -0.1455, 1.622), (0.0145, 0.007, 0.0090), seg=8, rings=5)
attach(arm, "Hero_Eyes", bm, M_EYE, "Head")
bm = bmesh.new()
for sx in (1, -1):
    ell(bm, (sx * 0.034, -0.1515, 1.622), (0.005, 0.003, 0.0065), seg=5, rings=3)
    ell(bm, (sx * 0.034, -0.143, 1.6335), (0.019, 0.008, 0.005), seg=6, rings=3)
attach(arm, "Hero_EyePupils", bm, M_PUP, "Head")
bm = bmesh.new(); lbm = bmesh.new(); luv = {}; tbm = bmesh.new()
for k in range(8):                                                                # antler crown
    a = math.radians(-100 + k * 28)
    root = HC + Vector((0.07 * math.sin(a), 0.01 + 0.03 * abs(math.cos(a)), 0.07 + 0.015 * math.cos(a)))
    dd = Vector((math.sin(a) * 0.7, 0.25, 1.0))
    branch(bm, lbm, luv, tbm, root, dd, random.uniform(0.13, 0.2), 0.0085, 2)
for sx in (1, -1):                                                                  # long swept side branches
    branch(bm, lbm, luv, tbm, HC + Vector((sx * 0.07, 0.0, 0.05)), (sx * 0.9, 0.3, 0.7), 0.26, 0.010, 2)
    branch(bm, lbm, luv, tbm, HC + Vector((sx * 0.05, 0.05, 0.08)), (sx * 0.5, 0.8, 0.5), 0.22, 0.009, 2)
attach(arm, "Hero_Crown", bm, M_VINE, "Head")
assign_uv(lbm, luv); attach(arm, "Hero_CrownLeaves", lbm, M_LEAF, "Head")
attach(arm, "Hero_CrownThorns", tbm, M_THORN, "Head")
bm = bmesh.new()                                                                    # moss clumps on crown + lichen flowers
for k in range(8):
    a = random.uniform(0, 2 * math.pi)
    ell(bm, HC + Vector((0.075 * math.sin(a), 0.01 + 0.07 * math.cos(a), 0.06 + random.uniform(0, 0.03))), (0.022, 0.022, 0.014), seg=7, rings=4)
attach(arm, "Hero_CrownMoss", bm, M_MOSS, "Head")
bm = bmesh.new()
for (x, y, z) in ((0.07, -0.08, 1.70), (0.052, -0.09, 1.725), (-0.01, -0.05, 1.75)):
    for k in range(5):
        a = 2 * math.pi * k / 5
        ell(bm, (x + 0.011 * math.cos(a), y, z + 0.011 * math.sin(a)), (0.008, 0.003, 0.008), seg=5, rings=3)
    ell(bm, (x, y - 0.003, z), (0.006, 0.004, 0.006), seg=5, rings=3)
attach(arm, "Hero_Lichen", bm, M_LICHEN, "Head")

# ---------- bark-veil: shoulder cape, torso wrap strips, skirt layers ----------
def bark_strips(rows_def, root_fn, wd, sag, out, seed_rot=0.0, skip=None, tipw=1.6):
    bm = bmesh.new(); uv = {}
    for (z, rx, ry, n, ln) in rows_def:
        for k in range(n):
            a = 2 * math.pi * k / n + seed_rot + random.uniform(-0.05, 0.05)
            if skip and skip(a): continue
            p = Vector((rx * math.sin(a), -0.043 - ry * math.cos(a), z))
            d = Vector((math.sin(a) * out, -math.cos(a) * out, -sag + random.uniform(-0.2, 0.2)))
            card(bm, uv, p, d, ln * random.uniform(0.7, 1.25), wd * random.uniform(0.8, 1.3), curl=random.uniform(0.1, 0.35), rows=4, tipw=tipw)
    assign_uv(bm, uv); return bm


cape = bmesh.new(); cuv = {}
for layer, (z0, ln, n) in enumerate(((1.50, 0.13, 9), (1.45, 0.16, 10), (1.40, 0.19, 10))):
    for k in range(n):
        a = math.radians(-165 + k * (330 / (n - 1))) + 0.0
        rr = 0.13 + 0.035 * layer
        p = Vector((rr * math.sin(a) * 1.3, -0.043 - rr * math.cos(a) * 1.0, z0))
        d = Vector((math.sin(a) * 0.55, -math.cos(a) * 0.45, -1))
        card(cape, cuv, p, d, ln * random.uniform(0.8, 1.2), 0.095, curl=0.2, rows=4, tipw=1.7)
assign_uv(cape, cuv)
def capew(co):
    t = smoothstep(0.12, 0.26, abs(co.x))
    return {"Chest": 1 - t * 0.7, ("UpperArm.L" if co.x >= 0 else "UpperArm.R"): t * 0.7}
skinned(arm, "Hero_VeilCape", cape, M_VEIL, capew)
skinned(arm, "Hero_VeilTorso", bark_strips([(1.30 - i * 0.09, 0.17 + 0.006 * i, 0.14 + 0.005 * i, 11, 0.11) for i in range(3)], None, 0.085, 1.0, 0.4, seed_rot=0.3), M_VEIL, tw)
bm = bark_strips([(1.0 - i * 0.11, 0.215 + 0.012 * i, 0.215 + 0.012 * i, 13, 0.20 + 0.01 * i) for i in range(4)], None, 0.11, 1.0, 0.25, seed_rot=0.1, tipw=1.4)
skinned(arm, "Hero_VeilSkirt", bm, M_VEIL, skw)
def under(r, c):
    a = math.radians(10 + c * 340); z = 1.05 + r * (0.62 - 1.05)
    rad = 0.19 + 0.06 * r ** 1.4
    return Vector((rad * math.sin(a), -0.04 - rad * math.cos(a), z))
skinned(arm, "Hero_VeilUnder", strip(10, 36, under), M_VEIL, skw)
bm = bmesh.new(); uv = {}                                                           # long ragged back strips
for k in range(5):
    x = (k - 2) * 0.07
    card(bm, uv, Vector((x, 0.185, 1.0)), (x * 0.6, 0.15, -1), 0.42 - 0.04 * abs(k - 2), 0.09, curl=0.1, rows=6, tipw=1.5)
assign_uv(bm, uv); skinned(arm, "Hero_VeilBack", bm, M_VEIL, skw)

# ---------- vines: torso, arms, legs ----------
tb = bmesh.new(); vb = bmesh.new()
for rz0, rz1, ra in ((1.45, 1.05, 0.2),):                                           # torso spiral
    pts = ringpts(0, 0.1, 0.1, 2)
    n = 40; prev = None
    for i in range(n + 1):
        t = i / n; a = 4.5 * math.pi * t - math.pi * 0.2
        pt = Vector((0.21 * math.sin(a), -0.043 - 0.17 * math.cos(a), 1.46 - 0.42 * t))
        if prev: tube(vb, prev, pt, 0.011, 0.011, seg=4)
        if prev and i % 2 == 0: cone(tb, pt, (pt.x, pt.y + 0.043, 0.2), 0.014, 0.025, seg=3)
        prev = pt
attach(arm, "Hero_TorsoVine", vb, M_VINE, "Torso"); attach(arm, "Hero_TorsoThorns", tb, M_THORN, "Torso")
for side, tag, up, lo in ((1, "L", "UpperArm.L", "LowerArm.L"), (-1, "R", "UpperArm.R", "LowerArm.R")):
    def aw(co, up=up, lo=lo):
        t = smoothstep(0.30, 0.36, abs(co.x)); return {up: 1.0 - t, lo: t}
    vb = bmesh.new(); tb = bmesh.new()
    helix(vb, tb, (side * 0.17, -0.06, 1.43), (side * 0.56, -0.088, 1.43), 0.062, 3.5, 0.010, n=36)
    helix(vb, tb, (side * 0.22, -0.06, 1.43), (side * 0.50, -0.085, 1.43), 0.072, 2.0, 0.008, n=20)
    skinned(arm, "Hero_ArmVine_" + tag, vb, M_VINE, aw); skinned(arm, "Hero_ArmThorns_" + tag, tb, M_THORN, aw)
    bm = bmesh.new(); lbm = bmesh.new(); luv = {}; tbm = bmesh.new()                # elbow twig sprouts + finger twigs
    branch(bm, lbm, luv, tbm, (side * 0.34, -0.03, 1.46), (side * 0.2, 0.8, 0.6), 0.15, 0.011, 2)
    branch(bm, lbm, luv, tbm, (side * 0.45, -0.075, 1.48), (side * 0.3, -0.3, 1.0), 0.12, 0.009, 1)
    skinned(arm, "Hero_ArmTwigs_" + tag, bm, M_VINE, aw); assign_uv(lbm, luv); skinned(arm, "Hero_ArmLeaves_" + tag, lbm, M_LEAF, aw)
    skinned(arm, "Hero_ArmTwigThorns_" + tag, tbm, M_THORN, aw)
    bm = bmesh.new()
    for yy, dz, ln in ((-0.12, 0.0, 0.09), (-0.09, 0.01, 0.1), (-0.06, 0.01, 0.09), (-0.03, 0.0, 0.07)):     # finger twigs
        p = Vector((side * 0.81, yy, 1.445 + dz))
        tube(bm, p, p + Vector((side * ln * 0.6, 0, -0.02)), 0.007, 0.005, seg=4)
        tube(bm, p + Vector((side * ln * 0.6, 0, -0.02)), p + Vector((side * ln, 0, -0.06)), 0.005, 0.001, seg=4)
    tube(bm, (side * 0.70, -0.18, 1.40), (side * 0.73, -0.21, 1.37), 0.008, 0.001, seg=4)
    attach(arm, "Hero_FingerTwigs_" + tag, bm, M_VINE, "Hand." + tag)
    bm = bmesh.new()                                                                # moss on shoulder, lichen on forearm
    ell(bm, (side * 0.14, -0.06, 1.49), (0.05, 0.045, 0.022), seg=8, rings=5)
    ell(bm, (side * 0.22, -0.05, 1.485), (0.035, 0.03, 0.016), seg=7, rings=4)
    attach(arm, "Hero_ShoulderMoss_" + tag, bm, M_MOSS, up)
    bm = bmesh.new()
    for x, y in ((0.40, -0.075), (0.48, -0.085)):
        ell(bm, (side * x, y, 1.488), (0.026, 0.026, 0.006), seg=7, rings=3)
    attach(arm, "Hero_ForearmLichen_" + tag, bm, M_LICHEN, lo)

# moss draping from veil, lichen patches on chest/hip
bm = bmesh.new()
for k in range(16):
    a = random.uniform(-2.8, 2.8)
    z = random.uniform(0.55, 1.4); rr = 0.19 + (1.4 - z) * 0.09
    c = Vector((rr * math.sin(a), -0.043 - rr * math.cos(a), z))
    ell(bm, c, (0.032, 0.02, 0.022), seg=7, rings=4)
    tube(bm, c, c + Vector((0, 0, -random.uniform(0.04, 0.1))), 0.008, 0.001, seg=4)
skinned(arm, "Hero_VeilMoss", bm, M_MOSS, skw)
bm = bmesh.new()
for k in range(10):
    a = random.uniform(-2.5, 2.5); z = random.uniform(0.6, 1.4); rr = 0.2 + (1.4 - z) * 0.1 + 0.012
    c = Vector((rr * math.sin(a), -0.043 - rr * math.cos(a), z))
    for j in range(5):
        b = 2 * math.pi * j / 5
        ell(bm, c + Vector((0.012 * math.cos(b), 0, 0.012 * math.sin(b))), (0.009, 0.004, 0.009), seg=5, rings=3)
skinned(arm, "Hero_VeilLichen", bm, M_LICHEN, skw)

# ---------- legs: twisted root-vines, root feet ----------
for side, foot, tag in ((1, "Foot.L", "L"), (-1, "Foot.R", "R")):
    cx = side * 0.12
    vb = bmesh.new(); tb = bmesh.new()
    helix(vb, tb, (cx, -0.09, 0.55), (cx, -0.06, 0.07), 0.052, 3.0, 0.011, thorns=False, n=34)
    helix(vb, tb, (cx, -0.09, 0.55), (cx, -0.06, 0.07), 0.052, -3.0, 0.011, thorns=False, n=34)
    helix(vb, tb, (cx, -0.05, 0.96), (cx, -0.09, 0.55), 0.075, 2.5, 0.010, thorns=True, n=24)
    lw = lambda co, tg=tag: {("LowerLeg." + tg): smoothstep(0.62, 0.5, co.z), ("UpperLeg." + tg): smoothstep(0.5, 0.62, co.z)}
    skinned(arm, "Hero_LegVines_" + tag, vb, M_VINE, lw); skinned(arm, "Hero_LegThorns_" + tag, tb, M_THORN, lw)
    bm = bmesh.new()                                                                # root feet: knobby ankle, splayed roots
    ell(bm, (cx, -0.065, 0.07), (0.045, 0.05, 0.04), seg=8, rings=5)
    for k in range(7):
        a = math.radians(-65 + k * 22)
        dx, dy = math.sin(a) * 0.5, -math.cos(a)
        ln = 0.16 + 0.06 * (1 if k in (2, 3, 4) else 0)
        p0 = Vector((cx, -0.065, 0.06)); p1 = p0 + Vector((dx * ln * 0.5, dy * ln * 0.5, -0.03)); p2 = p0 + Vector((dx * ln, dy * ln, -0.045))
        tube(bm, p0, p1, 0.020, 0.013); tube(bm, p1, p2, 0.013, 0.003, seg=5)
    for k in range(2):
        a = math.radians(160 + k * 40)
        tube(bm, (cx, -0.055, 0.06), (cx + math.sin(a) * 0.08, -0.055 - math.cos(a) * 0.08, 0.01), 0.016, 0.004, seg=5)
    attach(arm, "Hero_RootFeet_" + tag, bm, M_VINE, foot)
    bm = bmesh.new()
    ell(bm, (cx + side * 0.03, -0.1, 0.38), (0.03, 0.025, 0.02), seg=7, rings=4)
    attach(arm, "Hero_KneeMoss_" + tag, bm, M_MOSS, "LowerLeg." + tag)

print("TM_TOTAL_TRIS", tri_count())
bpy.ops.wm.save_as_mainfile(filepath=OUT + "/thornmimic.blend")
bpy.ops.export_scene.gltf(filepath=OUT + "/thornmimic.glb", export_format='GLB', export_apply=True,
                          export_animations=False, export_skins=True)
print("TM_DONE")
