"""Cinderkin hero: slender amber-crystal fire sprite on the primal shared-skeleton base (Blender 5.x).
Run: blender -b -P build_cinderkin.py -- <primal.glb> <out_dir>
Faceted amber body with glowing internal cracks (baked diffuse+normal+emission), pointed-ear face with glowing eyes, crystal-shard hair,
layered Crystal-Shard Shell (chest, skirt, shoulders, forearm/shin shards, skinned), crystal feet, ember darts at the hip."""
import bpy, bmesh, math, sys, os, random
import numpy as np
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hero_common import *
import hero_textures as T

SRC, OUT = sys.argv[-2], sys.argv[-1]
random.seed(31)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
remove_objects("_Head", "_Feet")
TEX = os.path.join(OUT, "tex_ck")


def rgba(col):
    return np.concatenate([col, np.ones(col.shape[:2] + (1,), np.float32)], -1)


AMB = np.array([0.85, 0.42, 0.14], np.float32); DEEP = np.array([0.20, 0.08, 0.04], np.float32); HOT = np.array([1.0, 0.55, 0.12], np.float32)


def body_tex():
    n = 512; e, cid = T.voronoi(n, 7, 5); nz = T.fbm(n, 6, 5, 6)
    cell = T.smooth(0.0, 0.25, e)
    col = (DEEP[None, None, :] * (1 - cid[..., None]) + AMB[None, None, :] * cid[..., None] * 1.1) * (0.6 + 0.5 * nz[..., None]) * (0.55 + 0.45 * cell[..., None])
    crack = (1 - T.smooth(0.0, 0.10, e)) * T.smooth(0.3, 0.6, nz)
    col = col + crack[..., None] * HOT[None, None, :] * 0.8
    emis = rgba(crack[..., None] * HOT[None, None, :] * 1.0 + (T.smooth(0.65, 0.9, nz) * 0.15)[..., None] * HOT[None, None, :])
    return (T.to_image("body_diffuse", rgba(np.clip(col, 0, 1)), TEX), T.to_image("body_normal", T.normal_from_height(cell * 0.7 + 0.3 * nz, 2.0), TEX, "Non-Color"),
            T.to_image("body_emission", emis, TEX))


def shard_tex():
    n = 256; x, y = T._grid(n); u = np.abs(x - 0.5) * 2; nz = T.fbm(n, 12, 4, 5)
    e, cid = T.voronoi(n, 4, 9)
    facet = 0.5 + 0.5 * cid
    core = np.exp(-(u / 0.22) ** 2) * T.smooth(0.0, 0.5, 1 - y * 0.8)            # glowing core line at the base, fades toward the tip
    col = (DEEP[None, None, :] * (1 - facet[..., None]) + AMB[None, None, :] * facet[..., None]) * (0.65 + 0.5 * (1 - u[..., None])) * (0.8 + 0.3 * nz[..., None])
    col += core[..., None] * HOT[None, None, :] * 0.35
    emis = rgba(core[..., None] * HOT[None, None, :] * 0.9 * (0.5 + 0.5 * T.smooth(0.2, 1.0, nz))[..., None])
    h = 0.5 * facet + 0.4 * (1 - u)
    return (T.to_image("shard_diffuse", rgba(np.clip(col, 0, 1)), TEX), T.to_image("shard_normal", T.normal_from_height(h, 2.0), TEX, "Non-Color"),
            T.to_image("shard_emission", emis, TEX))


bt = body_tex(); st = shard_tex()
M_BODY = mat("CK_Body", (0.55, 0.28, 0.1), 0.35, 0.1, emit=(1, 0.5, 0.1), strength=1.0)
M_SHARD = mat("CK_Shard", (0.55, 0.28, 0.1), 0.2, 0.15, emit=(1, 0.5, 0.1), strength=1.0)
M_FACE = mat("CK_Face", (0.42, 0.20, 0.07), 0.35, 0.05, emit=(0.9, 0.35, 0.05), strength=0.35)
M_GLOW = mat("CK_Glow", (1.0, 0.6, 0.15), 0.2, 0.0, emit=(1.0, 0.55, 0.1), strength=3.0)
M_EYE = mat("CK_Eye", (1.0, 0.75, 0.15), 0.1, 0.0, emit=(1.0, 0.7, 0.1), strength=3.5)
M_DART = mat("CK_Dart", (0.5, 0.26, 0.1), 0.15, 0.2, emit=(1.0, 0.45, 0.08), strength=1.3)
M_STRAP = mat("CK_Strap", (0.12, 0.07, 0.05), 0.8)
T.bind(M_BODY, *bt, emission_strength=1.4); T.bind(M_SHARD, *st, emission_strength=1.4); T.bind(M_DART, *st, emission_strength=1.2)

for _o in bpy.data.objects:
    if _o.type == "MESH" and _o.name.endswith(("_Body", "_Legs")):
        _o.data.materials.clear(); _o.data.materials.append(M_BODY)
        for p in _o.data.polygons: p.material_index = 0
        me = _o.data
        for ul in list(me.uv_layers): me.uv_layers.remove(ul)
        ul = me.uv_layers.new(name="UVMap"); mw = _o.matrix_world
        for poly in me.polygons:
            for li in poly.loop_indices:
                w = mw @ me.vertices[me.loops[li].vertex_index].co
                ul.data[li].uv = (abs(math.atan2(w.x, -w.y)) / math.pi * 1.2, w.z * 1.4)


# ---------- helpers ----------
def shard(bm, uvm, root, direction, length, width, rows=4, curl=0.1, bias=0.45):
    """Pointed crystal blade: widest at `bias`, point at both ends."""
    d = Vector(direction).normalized(); up = Vector((0, 0, 1))
    side = d.cross(up)
    if side.length < 1e-3: side = Vector((1, 0, 0))
    side.normalize(); nrm = side.cross(d).normalized()
    vs = []
    for r in range(rows):
        t = r / (rows - 1)
        prof = math.sin(math.pi * (t ** (math.log(0.5) / math.log(bias)) if bias != 0.5 else t))
        pos = Vector(root) + d * length * t + nrm * (curl * length * t * t)
        w = width * max(prof, 0.0) + 0.0005
        row = []
        for c in range(3):
            v = bm.verts.new(pos + side * ((c - 1) * w) + nrm * ((1 - abs(c - 1)) * w * 0.55))
            uvm[v] = (c / 2.0, 1.0 - t); row.append(v)
        vs.append(row)
    for r in range(rows - 1):
        for c in range(2):
            try: bm.faces.new((vs[r][c], vs[r][c + 1], vs[r + 1][c + 1], vs[r + 1][c]))
            except ValueError: pass


def ring(bm, uv, cz, rx, ry, n, ln, wd, sag, rot=0.0, jit=0.12, cy=-0.043, out=0.5, skip=None):
    for k in range(n):
        a = 2 * math.pi * k / n + rot
        if skip and skip(a): continue
        p = Vector((rx * math.sin(a), cy - ry * math.cos(a), cz))
        d = Vector((math.sin(a) * out, -math.cos(a) * out, -sag + random.uniform(-jit, jit)))
        shard(bm, uv, p, d, ln * random.uniform(0.85, 1.2), wd * random.uniform(0.9, 1.2), curl=random.uniform(0.0, 0.2))


def tw(co):
    ch = smoothstep(1.18, 1.32, co.z); tq = smoothstep(1.02, 1.1, co.z) * (1 - ch)
    return {"Chest": ch, "Torso": tq, "Hips": max(0.0, 1.0 - ch - tq)}


def skw(co):
    t = smoothstep(1.0, 0.4, co.z)
    front = max(0.0, -co.y / max(1e-6, math.hypot(co.x, co.y)))
    wl = t * (0.25 + 0.6 * front)
    return {"Hips": 1.0 - wl, ("UpperLeg.L" if co.x >= 0 else "UpperLeg.R"): wl}


# ---------- head: sharp elfin face, glowing eyes, shard hair ----------
HC = Vector((0, -0.075, 1.635))
bm = bmesh.new()
ell(bm, HC, (0.074, 0.092, 0.092), seg=16, rings=10)
ell(bm, (0, -0.10, 1.595), (0.056, 0.056, 0.072), seg=12, rings=8)
ell(bm, (0, -0.108, 1.545), (0.028, 0.036, 0.034), seg=10, rings=6)
tube(bm, (0, -0.145, 1.640), (0, -0.168, 1.590), 0.008, 0.011, seg=5)
ell(bm, (0, -0.168, 1.585), (0.012, 0.012, 0.009), seg=6, rings=4)
for sx in (1, -1):
    ell(bm, (sx * 0.044, -0.132, 1.640), (0.021, 0.014, 0.008), rot=(0, sx * -0.4, 0), seg=8, rings=5)      # slanted brow
    ell(bm, (sx * 0.046, -0.128, 1.592), (0.018, 0.016, 0.013), seg=8, rings=5)                            # cheek facet
    cone(bm, (sx * 0.07, -0.05, 1.64), (sx * 0.8, 0.45, 0.45), 0.018, 0.10, seg=4)                        # pointed ear
ell(bm, (0, -0.04, 1.51), (0.030, 0.030, 0.06), seg=10, rings=6)
ell(bm, (0, -0.148, 1.552), (0.016, 0.006, 0.003), seg=6, rings=3)
attach(arm, "Hero_Face", bm, M_FACE, "Head")
bm = bmesh.new()
for sx in (1, -1):
    ell(bm, (sx * 0.034, -0.1405, 1.620), (0.0135, 0.007, 0.0075), rot=(0, sx * -0.3, 0), seg=8, rings=5)
attach(arm, "Hero_Eyes", bm, M_EYE, "Head")
bm = bmesh.new(); uv = {}
for el in range(0, 7):                                                              # spiky shard hair
    e = math.radians(el * 14 + 10)
    nph = max(6, int(14 * math.cos(e)))
    for k in range(nph):
        ph = 2 * math.pi * (k + 0.5 * (el % 2)) / nph
        if math.cos(ph) > 0.3 and abs(math.sin(ph)) < 0.7 and el < 3: continue
        p = HC + Vector((0.08 * math.cos(e) * math.sin(ph), -0.10 * math.cos(e) * math.cos(ph), 0.09 * math.sin(e)))
        out = Vector((math.sin(ph) * math.cos(e), -math.cos(ph) * math.cos(e), math.sin(e)))
        dd = out + Vector((0, 0.5, 0.2))
        shard(bm, uv, p, dd, random.uniform(0.07, 0.12) * (1.3 if el > 3 else 1.0), 0.026, curl=0.15)
for k in range(5):                                                                  # tall crown shards
    a = math.radians(-50 + 25 * k)
    shard(bm, uv, HC + Vector((0.04 * math.sin(a), -0.01, 0.085)), (math.sin(a) * 0.4, 0.25, 1.0), 0.14 + 0.03 * (k % 2), 0.03)
for sx in (1, -1):
    for j in range(3):
        shard(bm, uv, HC + Vector((sx * 0.075, -0.035 + j * 0.04, 0.0)), (sx * 0.9, 0.5, -0.1 + 0.15 * j), 0.075, 0.024)
assign_uv(bm, uv); attach(arm, "Hero_HairShards", bm, M_SHARD, "Head")

# ---------- shoulders, collar, chest shell ----------
bm = bmesh.new(); uv = {}
for k in range(10):
    a = 2 * math.pi * k / 10
    shard(bm, uv, Vector((0.07 * math.sin(a), -0.04 - 0.07 * math.cos(a), 1.50)), (math.sin(a) * 0.6, -math.cos(a) * 0.6, 0.6), 0.075, 0.026)
assign_uv(bm, uv); attach(arm, "Hero_Collar", bm, M_SHARD, "Neck")
for side, tag, bone in ((1, "L", "UpperArm.L"), (-1, "R", "UpperArm.R")):
    bm = bmesh.new(); uv = {}
    for k, (x0, z0, dx, dz, ln, wd) in enumerate(((0.10, 1.49, 0.5, 0.9, 0.12, 0.034), (0.15, 1.495, 0.6, 0.8, 0.14, 0.036), (0.20, 1.49, 0.8, 0.6, 0.15, 0.036),
                                                  (0.25, 1.48, 1.0, 0.35, 0.14, 0.034), (0.13, 1.47, 0.3, 0.6, 0.09, 0.03), (0.19, 1.47, 0.6, 0.35, 0.09, 0.03))):
        for dy in (-0.035, 0.0, 0.035):
            shard(bm, uv, Vector((side * x0, -0.06 + dy, z0)), (side * dx, dy * 3, dz), ln * (1.15 if dy == 0 else 0.9), wd)
    assign_uv(bm, uv); attach(arm, "Hero_ShoulderShards_" + tag, bm, M_SHARD, bone)


def tunic(r, c):
    a = 2 * math.pi * c; z = 1.47 - r * 0.50
    return Vector(((0.165 + 0.02 * r) * math.sin(a), -0.043 - (0.135 + 0.02 * r) * math.cos(a), z))
skinned(arm, "Hero_TorsoCore", strip(8, 28, tunic), M_BODY, tw)
bm = bmesh.new(); uv = {}
for i in range(4):                                                                  # layered chest shell, V-shaped in front
    z = 1.44 - i * 0.07
    n = 13
    for k in range(n):
        a = 2 * math.pi * k / n + 0.2 * (i % 2)
        rx, ry = 0.185, 0.15
        p = Vector((rx * math.sin(a), -0.043 - ry * math.cos(a), z + (0.02 * abs(math.sin(a)) if math.cos(a) > 0 else 0)))
        d = Vector((math.sin(a) * 0.35, -math.cos(a) * 0.35, -1))
        shard(bm, uv, p, d, 0.085 + 0.008 * i, 0.05, curl=0.15)
assign_uv(bm, uv); skinned(arm, "Hero_ChestShell", bm, M_SHARD, tw)

# ---------- skirt ----------
bm = bmesh.new(); uv = {}
for i, (z, rr, n, ln) in enumerate(((1.0, 0.205, 11, 0.15), (0.90, 0.22, 12, 0.17), (0.80, 0.235, 12, 0.17))):
    ring(bm, uv, z, rr, rr, n, ln, 0.075, 1.0, rot=i * 0.25, out=0.3, cy=-0.05)
assign_uv(bm, uv); skinned(arm, "Hero_SkirtShards", bm, M_SHARD, skw)
bm = bmesh.new(); uv = {}
for k in range(5):
    x = (k - 2) * 0.07
    shard(bm, uv, Vector((x, 0.165, 1.0)), (x * 0.6, 0.15, -1), 0.3 - 0.03 * abs(k - 2), 0.06)
assign_uv(bm, uv); skinned(arm, "Hero_BackShards", bm, M_SHARD, skw)
def under(r, c):
    a = math.radians(10 + c * 340); z = 1.05 + r * (0.68 - 1.05); rad = 0.18 + 0.04 * r
    return Vector((rad * math.sin(a), -0.04 - rad * math.cos(a), z))
skinned(arm, "Hero_SkirtCore", strip(5, 30, under), M_BODY, skw)

# ---------- ember darts (belt + 3 darts) ----------
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=20, radius1=0.20, radius2=0.20, depth=0.025, matrix=Matrix.Translation((0, -0.043, 1.03)))
attach(arm, "Hero_Belt", bm, M_STRAP, "Hips")
bm = bmesh.new(); uv = {}
for k in range(3):
    base = Vector((0.20 + 0.0 * k, -0.02 + 0.045 * k, 0.96 - 0.02 * k))
    shard(bm, uv, base + Vector((0, 0, 0.0)), (0.25, 0.0, -1), 0.20, 0.022, rows=5, bias=0.35)
assign_uv(bm, uv); attach(arm, "Hero_Darts", bm, M_DART, "Hips")
bm = bmesh.new()
ell(bm, (0, -0.215, 1.03), (0.025, 0.012, 0.03), seg=6, rings=4)                    # ember buckle gem
ell(bm, (0, -0.19, 1.36), (0.02, 0.01, 0.035), seg=6, rings=4)                      # chest core gem
attach(arm, "Hero_Gems", bm, M_GLOW, "Chest")

# ---------- arms: forearm shards, wrist, elbow spike; legs: knee/shin/thigh shards; crystal feet ----------
for side, tag, up, lo in ((1, "L", "UpperArm.L", "LowerArm.L"), (-1, "R", "UpperArm.R", "LowerArm.R")):
    def aw(co, up=up, lo=lo):
        t = smoothstep(0.30, 0.36, abs(co.x)); return {up: 1.0 - t, lo: t}
    bm = bmesh.new(); uv = {}
    for i in range(5):
        x = side * (0.38 + i * 0.045)
        for a0 in (60, 150, 240):
            a = math.radians(a0); rr = 0.045
            shard(bm, uv, Vector((x, -0.075 + rr * math.sin(a) * 0.0 - 0.0, 1.43 + rr * math.cos(a))), (side * 0.6, 0.0 + 0.5 * math.sin(a), 0.5 * math.cos(a)), 0.09, 0.022)
    for k in range(3):                                                                   # upper arm fins
        shard(bm, uv, Vector((side * (0.20 + 0.04 * k), -0.06, 1.475)), (side * 0.7, 0, 0.5), 0.09, 0.022)
    shard(bm, uv, Vector((side * 0.34, 0.0, 1.43)), (side * 0.15, 1.0, 0.1), 0.12, 0.03)           # elbow spike
    assign_uv(bm, uv); skinned(arm, "Hero_ArmShards_" + tag, bm, M_SHARD, aw)
    bm = bmesh.new(); uv = {}
    for k in range(5):                                                                   # wrist cuff of tiny shards
        a = 2 * math.pi * k / 5
        shard(bm, uv, Vector((side * 0.57, -0.09 + 0.04 * math.sin(a), 1.43 + 0.04 * math.cos(a))), (side * 0.6, 0.4 * math.sin(a), 0.4 * math.cos(a)), 0.07, 0.018)
    assign_uv(bm, uv); attach(arm, "Hero_WristShards_" + tag, bm, M_SHARD, lo)

for side, foot, tag in ((1, "Foot.L", "L"), (-1, "Foot.R", "R")):
    cx = side * 0.12
    bm = bmesh.new(); uv = {}
    for z0, n, ln in ((0.52, 5, 0.12), (0.34, 5, 0.11), (0.20, 4, 0.09)):                # shin shell, pointing down; front shards bigger
        for k in range(n):
            a = 2 * math.pi * (k + 0.5 * (z0 > 0.3)) / n
            rr = 0.045
            shard(bm, uv, Vector((cx + rr * math.sin(a), -0.075 - rr * math.cos(a), z0)), (math.sin(a) * 0.25, -math.cos(a) * 0.25, -1), ln, 0.028)
    for k in range(3):                                                                   # knee crest
        shard(bm, uv, Vector((cx + (k - 1) * 0.02, -0.125, 0.54)), (0, -0.4, 1.0), 0.1, 0.028)
    assign_uv(bm, uv); attach(arm, "Hero_ShinShards_" + tag, bm, M_SHARD, "LowerLeg." + tag)
    bm = bmesh.new(); uv = {}
    for z0, n in ((0.88, 6), (0.74, 6)):
        for k in range(n):
            a = 2 * math.pi * (k + 0.5) / n; rr = 0.07
            shard(bm, uv, Vector((cx + rr * math.sin(a), -0.07 - rr * math.cos(a), z0)), (math.sin(a) * 0.2, -math.cos(a) * 0.2, -1), 0.15, 0.035)
    assign_uv(bm, uv); skinned(arm, "Hero_ThighShards_" + tag, bm, M_SHARD, lambda co, tg=tag: {("UpperLeg." + tg): 1.0})
    def calf(r, c, cx=cx):
        a = 2 * math.pi * c; z = 0.07 + r * 0.30; rad = 0.032 + 0.016 * r * r
        return Vector((cx + rad * math.cos(a), -0.072 + rad * math.sin(a), z))
    skinned(arm, "Hero_Ankle_" + tag, strip(6, 8, calf), M_BODY, lambda co, tg=tag: {("LowerLeg." + tg): 0.6})
    bm = bmesh.new()                                                                      # crystal foot: ankle, instep wedge, toes
    ell(bm, (cx, -0.07, 0.07), (0.034, 0.036, 0.05), seg=8, rings=5)
    ell(bm, (cx, -0.13, 0.035), (0.03, 0.07, 0.025), seg=8, rings=5)
    for k in range(5):
        tx = cx + (k - 2) * 0.017
        cone(bm, (tx, -0.18, 0.02), (0, -1, -0.05), 0.009, 0.045 + (0.01 if k in (1, 2) else 0), seg=4)
    tube(bm, (cx, -0.04, 0.07), (cx, 0.0, 0.025), 0.02, 0.008, seg=5)
    attach(arm, "Hero_Feet_" + tag, bm, M_SHARD, foot)

print("CK_TOTAL_TRIS", tri_count())
bpy.ops.wm.save_as_mainfile(filepath=OUT + "/cinderkin.blend")
bpy.ops.export_scene.gltf(filepath=OUT + "/cinderkin.glb", export_format='GLB', export_apply=True,
                          export_animations=False, export_skins=True)
print("CK_DONE")
