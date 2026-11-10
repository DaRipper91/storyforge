"""Mindspider hero: translucent crystalline arachnid scholar, own skeleton + Idle/Walk/Hit/Death clips (Blender 5.x).
Run: blender -b -P build_mindspider.py -- <out_dir>
Front is -Y, feet on z=0, ~2 m leg span, ~0.95 m high. Pearly translucent chitin with a gold lattice dome head (violet psychic sac, four eyes),
bulbous lattice abdomen with a glowing violet core, 8 three-segment legs with gold claws, hanging sigil banner, satchel and scrolls.
Parts are bone-parented (rigid) to a ~40-bone armature. Baked textures (chitin, banner, leather)."""
import bpy, bmesh, math, sys, os
import numpy as np
from mathutils import Vector, Matrix, Euler
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hero_common import mat, attach, ell, cone, tube
import hero_textures as T

OUT = sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.fps = 30
TEX = os.path.join(OUT, "tex_ms")

# ---------- textures ----------
def chitin_tex():
    n = 512; x, y = T._grid(n); nz = T.fbm(n, 5, 5, 4); nz2 = T.fbm(n, 6, 4, 10)
    sheen = 0.5 + 0.5 * np.sin(6.0 * nz + 4 * x)
    col = np.stack([0.78 + 0.12 * sheen, 0.70 + 0.10 * nz, 0.90 + 0.05 * sheen], -1) * (0.85 + 0.2 * nz2[..., None])
    col[..., 0] -= 0.12 * (1 - nz)[...]; col[..., 1] -= 0.18 * (1 - nz)[...]
    alpha = 0.50 + 0.25 * nz
    return (T.to_image("chitin_diffuse", np.concatenate([np.clip(col, 0, 1), alpha[..., None]], -1), TEX),
            T.to_image("chitin_normal", T.normal_from_height(0.5 * nz + 0.3 * nz2, 0.8), TEX, "Non-Color"))
def banner_tex():
    n = 512; x, y = T._grid(n); nz = T.fbm(n, 12, 5, 8)
    weave = 0.5 + 0.5 * np.sin(x * n * 0.9) * np.sin(y * n * 0.9)
    col = np.array([0.20, 0.10, 0.34], np.float32)[None, None, :] * (0.7 + 0.4 * nz[..., None]) * (0.9 + 0.1 * weave[..., None])
    gold = np.zeros((n, n), np.float32)
    cx, cy = 0.5, 0.42
    r = np.hypot(x - cx, (y - cy) * 1.0)
    gold = np.maximum(gold, 1 - T.smooth(0.0, 0.008, np.abs(r - 0.20)))
    gold = np.maximum(gold, 1 - T.smooth(0.0, 0.008, np.abs(r - 0.12)))
    for k in range(5):                                                          # 5-point star
        a = k * 2 * np.pi * 2 / 5 + np.pi / 2
        a2 = (k + 1) * 2 * np.pi * 2 / 5 + np.pi / 2
        p0 = np.array([cx + 0.20 * np.cos(a), cy - 0.20 * np.sin(a)]); p1 = np.array([cx + 0.20 * np.cos(a2), cy - 0.20 * np.sin(a2)])
        d = p1 - p0; L = np.hypot(*d)
        t = np.clip(((x - p0[0]) * d[0] + (y - p0[1]) * d[1]) / (L * L), 0, 1)
        dist = np.hypot(x - (p0[0] + t * d[0]), y - (p0[1] + t * d[1]))
        gold = np.maximum(gold, 1 - T.smooth(0.0, 0.007, dist))
    border = np.maximum(1 - T.smooth(0.0, 0.01, np.abs(x - 0.06)), 1 - T.smooth(0.0, 0.01, np.abs(x - 0.94)))
    gold = np.maximum(gold, border * 0.8)
    gc = np.array([0.82, 0.62, 0.25], np.float32)
    col = col * (1 - gold[..., None]) + gc[None, None, :] * gold[..., None]
    emis = np.stack([gold * 0.3, gold * 0.2, gold * 0.05, np.ones((n, n), np.float32)], -1)
    return (T.to_image("banner_diffuse", np.concatenate([col, np.ones((n, n, 1), np.float32)], -1), TEX),
            T.to_image("banner_normal", T.normal_from_height(0.4 * weave + 0.5 * gold, 1.2), TEX, "Non-Color"))
def leather_tex():
    n = 256; nz = T.fbm(n, 51, 5, 6); crack = T.fbm(n, 52, 4, 20)
    col = np.array([0.26, 0.16, 0.10], np.float32)[None, None, :] * (0.7 + 0.6 * nz[..., None]) * (0.85 + 0.3 * crack[..., None])
    return (T.to_image("leather_diffuse", np.concatenate([col, np.ones((n, n, 1), np.float32)], -1), TEX),
            T.to_image("leather_normal", T.normal_from_height(0.5 * nz + 0.5 * crack, 1.2), TEX, "Non-Color"))
ci, cn = chitin_tex(); bi, bn = banner_tex(); li, ln_ = leather_tex()

# ---------- materials ----------
M_CHITIN = mat("MS_Chitin", (0.80, 0.72, 0.90), 0.18, 0.0, alpha=0.62)
M_LEG    = mat("MS_LegChitin", (0.78, 0.70, 0.90), 0.2, 0.0, alpha=0.72)
M_GOLD   = mat("MS_Lattice", (0.70, 0.55, 0.30), 0.3, 1.0)
M_CORE   = mat("MS_Core", (0.45, 0.20, 0.80), 0.2, 0.0, alpha=0.7, emit=(0.45, 0.15, 0.9), strength=1.0)
M_EYE    = mat("MS_Eye", (0.10, 0.04, 0.18), 0.08, 0.0, emit=(0.25, 0.1, 0.5), strength=0.8)
M_BAN    = mat("MS_Banner", (0.20, 0.10, 0.34), 0.85)
M_LEATH  = mat("MS_Leather", (0.26, 0.16, 0.10), 0.55)
M_SCROLL = mat("MS_Scroll", (0.85, 0.78, 0.60), 0.8)
T.bind(M_CHITIN, ci, cn); T.bind(M_LEG, ci, cn); T.bind(M_BAN, bi, bn); T.bind(M_LEATH, li, ln_)

# ---------- skeleton ----------
arm_data = bpy.data.armatures.new("SpiderArmature")
arm = bpy.data.objects.new("SpiderArmature", arm_data); sc.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
E_ = arm_data.edit_bones
def bone(name, head, tail, parent=None):
    b = E_.new(name); b.head = Vector(head); b.tail = Vector(tail)
    if parent: b.parent = E_[parent]
    return b
bone("Root", (0, 0, 0), (0, 0, 0.12))
bone("Body", (0, 0.0, 0.58), (0, -0.2, 0.6), "Root")
bone("Abdomen", (0, 0.15, 0.62), (0, 0.55, 0.62), "Body")
bone("Head", (0, -0.2, 0.64), (0, -0.34, 0.64), "Body")
bone("Banner", (0, -0.27, 0.52), (0, -0.27, 0.20), "Body")
for s, sx in (("L", 1), ("R", -1)):
    bone(f"Chelicera.{s}", (sx * 0.04, -0.33, 0.58), (sx * 0.035, -0.40, 0.44), "Head")
    bone(f"Palp.{s}", (sx * 0.09, -0.30, 0.56), (sx * 0.11, -0.43, 0.46), "Head")
LEGS = {}
THETA = (-52, -18, 18, 52)
REACH = (0.98, 0.94, 0.94, 1.02)
for i in range(4):
    for s, sx in (("L", 1), ("R", -1)):
        th = math.radians(THETA[i]); d = Vector((sx * math.cos(th), math.sin(th), 0))
        hip = Vector((sx * 0.10, -0.15 + 0.10 * i, 0.58))
        knee = hip + d * 0.36 + Vector((0, 0, 0.40))
        ank = hip + d * (REACH[i] * 0.82) + Vector((0, 0, -0.18 + 0.0)); ank.z = 0.30
        foot = hip + d * REACH[i]; foot.z = 0.0
        LEGS[(i, s)] = (hip, knee, ank, foot)
        bone(f"Leg{i+1}.{s}.Femur", hip, knee, "Body")
        bone(f"Leg{i+1}.{s}.Tibia", knee, ank, f"Leg{i+1}.{s}.Femur")
        bone(f"Leg{i+1}.{s}.Tarsus", ank, foot, f"Leg{i+1}.{s}.Tibia")
bpy.ops.object.mode_set(mode='OBJECT')

def ptube(bm, pts, r0, r1, seg=4):
    n = len(pts)
    for i in range(n - 1):
        tube(bm, pts[i], pts[i + 1], r0 + (r1 - r0) * i / (n - 1), r0 + (r1 - r0) * (i + 1) / (n - 1), seg=seg)
def lattice(bm, c, rad, nmer, nlat, r, top=0.0):
    rx, ry, rz = rad; c = Vector(c)
    P = lambda th, ph, k=1.025: c + Vector((rx * k * math.sin(th) * math.cos(ph), ry * k * math.sin(th) * math.sin(ph), rz * k * math.cos(th)))
    for m in range(nmer):
        ph = 2 * math.pi * m / nmer
        ptube(bm, [P(math.pi * t / 8, ph) for t in range(1, 8)], r, r, seg=4)
    for k in range(nlat):
        th = math.pi * (k + 1) / (nlat + 1)
        ptube(bm, [P(th, 2 * math.pi * j / 14) for j in range(15)], r, r, seg=4)

# ---------- body ----------
bm = bmesh.new()
ell(bm, (0, -0.04, 0.58), (0.17, 0.22, 0.13), seg=14, rings=8)                      # cephalothorax
attach(arm, "Hero_Thorax", bm, M_CHITIN, "Body")
bm = bmesh.new()
lattice(bm, (0, -0.04, 0.58), (0.17, 0.22, 0.13), 8, 3, 0.006)
attach(arm, "Hero_ThoraxLattice", bm, M_GOLD, "Body")
bm = bmesh.new()
ell(bm, (0, 0.40, 0.66), (0.31, 0.38, 0.31), seg=18, rings=12)                       # abdomen shell
attach(arm, "Hero_Abdomen", bm, M_CHITIN, "Abdomen")
bm = bmesh.new()
lattice(bm, (0, 0.40, 0.66), (0.31, 0.38, 0.31), 9, 5, 0.008)
attach(arm, "Hero_AbdomenLattice", bm, M_GOLD, "Abdomen")
bm = bmesh.new()
ell(bm, (0, 0.40, 0.66), (0.17, 0.22, 0.17), seg=12, rings=8)                        # glowing violet core
ell(bm, (0, 0.38, 0.69), (0.10, 0.13, 0.10), seg=10, rings=6)
attach(arm, "Hero_AbdomenCore", bm, M_CORE, "Abdomen")
# head dome + psychic sac
bm = bmesh.new()
ell(bm, (0, -0.22, 0.68), (0.145, 0.15, 0.15), seg=16, rings=10)
ell(bm, (0, -0.28, 0.58), (0.10, 0.09, 0.08), seg=10, rings=6)                       # face
attach(arm, "Hero_Head", bm, M_CHITIN, "Head")
bm = bmesh.new()
lattice(bm, (0, -0.22, 0.68), (0.145, 0.15, 0.15), 8, 3, 0.0055)
attach(arm, "Hero_HeadLattice", bm, M_GOLD, "Head")
bm = bmesh.new()
ell(bm, (0, -0.21, 0.70), (0.09, 0.09, 0.10), seg=10, rings=6)
attach(arm, "Hero_HeadSac", bm, M_CORE, "Head")
bm = bmesh.new()
for (x, z, s) in ((0.040, 0.595, 0.020), (-0.040, 0.595, 0.020), (0.075, 0.620, 0.013), (-0.075, 0.620, 0.013)):
    ell(bm, (x, -0.340 + (0.012 if abs(x) > 0.05 else 0.0), z), (s, s * 0.9, s), seg=8, rings=5)
attach(arm, "Hero_Eyes", bm, M_EYE, "Head")
bm = bmesh.new()
for sx in (1, -1):                                                                   # lattice brow ridges
    ptube(bm, [Vector((sx * 0.02, -0.355, 0.64)), Vector((sx * 0.07, -0.34, 0.655)), Vector((sx * 0.115, -0.30, 0.64))], 0.008, 0.006, seg=4)
attach(arm, "Hero_Brow", bm, M_GOLD, "Head")
for s, sx in (("L", 1), ("R", -1)):
    bm = bmesh.new()
    cone(bm, (sx * 0.04, -0.33, 0.58), (sx * -0.1, -0.35, -0.9), 0.032, 0.13, seg=6, r2=0.008)
    attach(arm, f"Hero_Chelicera_{s}", bm, M_LEG, f"Chelicera.{s}")
    bm = bmesh.new()
    cone(bm, (sx * 0.037, -0.36, 0.50), (sx * -0.1, -0.35, -0.9), 0.008, 0.07, seg=4, r2=0.003)
    attach(arm, f"Hero_Fang_{s}", bm, M_GOLD, f"Chelicera.{s}")
    bm = bmesh.new()
    ptube(bm, [Vector((sx * 0.09, -0.30, 0.56)), Vector((sx * 0.11, -0.38, 0.56)), Vector((sx * 0.11, -0.43, 0.46))], 0.018, 0.008, seg=5)
    attach(arm, f"Hero_Palp_{s}", bm, M_LEG, f"Palp.{s}")

# ---------- legs ----------
for (i, s), (hip, knee, ank, foot) in LEGS.items():
    bm = bmesh.new()
    ell(bm, hip, (0.045, 0.045, 0.045), seg=8, rings=5)
    tube(bm, hip, knee, 0.034, 0.025, seg=6)
    ell(bm, knee, (0.032, 0.032, 0.032), seg=7, rings=4)
    attach(arm, f"Hero_Femur_{i+1}{s}", bm, M_LEG, f"Leg{i+1}.{s}.Femur")
    bm = bmesh.new()
    tube(bm, knee, ank, 0.024, 0.014, seg=6)
    ell(bm, ank, (0.020, 0.020, 0.020), seg=6, rings=4)
    attach(arm, f"Hero_Tibia_{i+1}{s}", bm, M_LEG, f"Leg{i+1}.{s}.Tibia")
    bm = bmesh.new()
    tube(bm, ank, foot + Vector((0, 0, 0.03)), 0.012, 0.007, seg=5)
    attach(arm, f"Hero_Tarsus_{i+1}{s}", bm, M_LEG, f"Leg{i+1}.{s}.Tarsus")
    bm = bmesh.new()
    cone(bm, foot + Vector((0, 0, 0.05)), (0, 0, -1), 0.011, 0.055, seg=5, r2=0.0015)
    for t in (0.25, 0.55):
        p = hip.lerp(knee, t); bmesh.ops.create_cone(bm, cap_ends=False, segments=8, radius1=0.031 - 0.007 * t, radius2=0.031 - 0.007 * t, depth=0.010,
                                                      matrix=Matrix.Translation(p) @ (knee - hip).normalized().to_track_quat('Z', 'Y').to_matrix().to_4x4())
    for t in (0.5,):
        p = knee.lerp(ank, t); bmesh.ops.create_cone(bm, cap_ends=False, segments=8, radius1=0.020, radius2=0.020, depth=0.010,
                                                      matrix=Matrix.Translation(p) @ (ank - knee).normalized().to_track_quat('Z', 'Y').to_matrix().to_4x4())
    attach(arm, f"Hero_LegGold_{i+1}{s}", bm, M_GOLD, f"Leg{i+1}.{s}.Tarsus")

# ---------- scholar kit: banner, belt, satchel, scrolls ----------
from hero_common import strip
def ban(r, c):
    u = c * 2 - 1; z = 0.53 - r * 0.34
    w = 0.115 * (1 - 0.0 * r) * (1 - smooth_pt(r))
    return Vector((u * w, -0.275 + 0.03 * math.sin(r * 3.0) * 0 - 0.018 * r, z))
def smooth_pt(r):
    t = max(0.0, min(1.0, (r - 0.72) / 0.28)); return t * t * (3 - 2 * t) * 0.97
attach(arm, "Hero_Banner", strip(12, 5, ban), M_BAN, "Banner")
bm = bmesh.new()
tube(bm, (-0.115, -0.272, 0.54), (0.115, -0.272, 0.54), 0.014, 0.014, seg=6)
ell(bm, (0, -0.275, 0.52), (0.035, 0.012, 0.035), seg=10, rings=5)
for sx in (1, -1):
    for k in range(3):
        tube(bm, (sx * 0.075, -0.27, 0.54), (sx * (0.085 + 0.01 * k), -0.28, 0.36 - 0.01 * k), 0.003, 0.003, seg=3)
attach(arm, "Hero_BannerBar", bm, M_GOLD, "Banner")
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=False, segments=20, radius1=0.20, radius2=0.20, depth=0.04, matrix=Matrix.Translation((0, -0.02, 0.55)) @ Matrix.Rotation(math.radians(-14), 4, 'X'))
bmesh.ops.create_cone(bm, cap_ends=False, segments=20, radius1=0.19, radius2=0.19, depth=0.03, matrix=Matrix.Translation((0, -0.02, 0.60)) @ Matrix.Rotation(math.radians(10), 4, 'X'))
ell(bm, (0.17, 0.0, 0.46), (0.075, 0.06, 0.07), seg=10, rings=6)
ell(bm, (0.17, 0.0, 0.50), (0.078, 0.065, 0.032), seg=10, rings=5)
ell(bm, (-0.17, 0.02, 0.47), (0.055, 0.05, 0.06), seg=9, rings=5)
attach(arm, "Hero_Kit", bm, M_LEATH, "Body")
bm = bmesh.new()
ell(bm, (0.17, -0.062, 0.48), (0.012, 0.006, 0.020), seg=6, rings=4)
bmesh.ops.create_cone(bm, cap_ends=False, segments=10, radius1=0.20, radius2=0.20, depth=0.008, matrix=Matrix.Translation((0, -0.02, 0.575)) @ Matrix.Rotation(math.radians(-2), 4, 'X'))
attach(arm, "Hero_KitBrass", bm, M_GOLD, "Body")
bm = bmesh.new()
for k, (dx, dz, ln) in enumerate(((0.10, 0.60, 0.20), (0.14, 0.58, 0.18))):
    d = Vector((0.2, -0.1, -0.2)).normalized() if False else Vector((0.2, 0, -1)).normalized()
    cone(bm, (0.19 + dx * 0.4, 0.05 + 0.04 * k, 0.60 + 0.04 * k), (0.15, -0.2, -0.9), 0.022, ln, seg=8, r2=0.022)
attach(arm, "Hero_Scrolls", bm, M_SCROLL, "Body")

# ---------- animation ----------
pose = arm.pose.bones
for pb in pose: pb.rotation_mode = 'QUATERNION'
def rot_world(pb, rx=0.0, ry=0.0, rz=0.0):
    M = pb.bone.matrix_local.to_3x3()
    R = Matrix.Rotation(rz, 3, 'Z') @ Matrix.Rotation(ry, 3, 'Y') @ Matrix.Rotation(rx, 3, 'X')
    pb.rotation_quaternion = (M.inverted() @ R @ M).to_quaternion()
def reset():
    for pb in pose: pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)
def key(frame):
    for pb in pose:
        pb.keyframe_insert("rotation_quaternion", frame=frame); pb.keyframe_insert("location", frame=frame)
def new_action(name):
    reset(); arm.animation_data_create()
    act = bpy.data.actions.new(name); arm.animation_data.action = act; return act
def finish(act):
    act.use_fake_user = True; arm.animation_data.action = None
LL = [(i, s) for i in range(1, 5) for s in ("L", "R")]
SIDE = {"L": 1, "R": -1}

act = new_action("Idle")
for f in (1, 16, 31, 46, 61):
    t = (f - 1) / 60.0 * 2 * math.pi; reset()
    pose["Body"].location = (0, 0, 0.012 * math.sin(t))
    rot_world(pose["Abdomen"], rx=0.04 * math.sin(t + 0.5))
    rot_world(pose["Banner"], rx=0.07 * math.sin(t + 1.0))
    for s in ("L", "R"):
        rot_world(pose[f"Palp.{s}"], rx=0.25 * math.sin(2 * t + (0 if s == "L" else 1.6)))
        rot_world(pose[f"Chelicera.{s}"], rz=SIDE[s] * 0.12 * max(0.0, math.sin(t)))
    for i, s in LL:
        rot_world(pose[f"Leg{i}.{s}.Tarsus"], ry=-SIDE[s] * 0.05 * math.sin(t + i))
        if i in (1, 4): rot_world(pose[f"Leg{i}.{s}.Femur"], ry=-SIDE[s] * 0.06 * math.sin(t + i * 0.7), rz=0.03 * math.sin(t + i))
    key(f)
finish(act)

act = new_action("Walk")
for f in range(1, 26, 3):
    ph = (f - 1) / 24.0 * 2 * math.pi; reset()
    pose["Body"].location = (0, 0, 0.015 * abs(math.sin(ph * 2)))
    rot_world(pose["Body"], rz=0.03 * math.sin(ph))
    rot_world(pose["Abdomen"], rx=0.05 * math.sin(ph * 2), rz=0.05 * math.sin(ph))
    rot_world(pose["Banner"], rx=0.12 * math.sin(ph * 2 + 1))
    for i, s in LL:
        grp = 0 if (i + (0 if s == "L" else 1)) % 2 == 1 else math.pi              # tetrapods: 1L,2R,3L,4R vs the rest
        a = ph + grp
        swing = 0.30 * math.sin(a)
        lift = 0.50 * max(0.0, math.cos(a))
        rot_world(pose[f"Leg{i}.{s}.Femur"], ry=-SIDE[s] * lift, rz=SIDE[s] * swing)
        rot_world(pose[f"Leg{i}.{s}.Tibia"], ry=SIDE[s] * lift * 0.9)
        rot_world(pose[f"Leg{i}.{s}.Tarsus"], ry=-SIDE[s] * lift * 0.3)
    for s in ("L", "R"):
        rot_world(pose[f"Palp.{s}"], rx=0.3 * math.sin(ph * 2))
    key(f)
finish(act)

act = new_action("Hit")
for f, k in ((1, 0.0), (4, 1.0), (8, 0.35), (12, 0.0)):
    reset()
    rot_world(pose["Body"], rx=-0.32 * k)
    pose["Body"].location = (0, 0.07 * k, 0.02 * k)
    rot_world(pose["Head"], rx=0.25 * k); rot_world(pose["Abdomen"], rx=0.18 * k); rot_world(pose["Banner"], rx=-0.5 * k)
    for i, s in LL:
        rot_world(pose[f"Leg{i}.{s}.Femur"], ry=-SIDE[s] * 0.30 * k * (1.4 if i <= 2 else 0.4))
        rot_world(pose[f"Leg{i}.{s}.Tibia"], ry=SIDE[s] * 0.15 * k)
    for s in ("L", "R"):
        rot_world(pose[f"Chelicera.{s}"], rz=SIDE[s] * 0.5 * k)
    key(f)
finish(act)

act = new_action("Death")
for f, k in ((1, 0.0), (10, 0.5), (24, 1.0), (45, 1.0)):
    reset()
    pose["Body"].location = (0, 0.0, -0.26 * k)
    rot_world(pose["Body"], rx=0.15 * k, rz=0.1 * k)
    rot_world(pose["Abdomen"], rx=-0.20 * k); rot_world(pose["Head"], rx=0.25 * k)
    rot_world(pose["Banner"], rx=0.6 * k)
    for i, s in LL:
        rot_world(pose[f"Leg{i}.{s}.Femur"], ry=-SIDE[s] * 0.95 * k, rz=SIDE[s] * 0.2 * k * (i - 2.5) * -0.5)
        rot_world(pose[f"Leg{i}.{s}.Tibia"], ry=SIDE[s] * 2.1 * k)
        rot_world(pose[f"Leg{i}.{s}.Tarsus"], ry=SIDE[s] * 0.7 * k)
    for s in ("L", "R"):
        rot_world(pose[f"Palp.{s}"], rx=-0.5 * k)
    key(f)
finish(act)
reset()

tris = sum(len(p.vertices) - 2 for o in bpy.data.objects if o.type == 'MESH' for p in o.data.polygons)
print("MS_TOTAL_TRIS", tris, "ACTIONS", [a.name for a in bpy.data.actions])
bpy.ops.wm.save_as_mainfile(filepath=OUT + "/mindspider.blend")
bpy.ops.export_scene.gltf(filepath=OUT + "/mindspider.glb", export_format='GLB', export_apply=True,
                          export_animations=True, export_animation_mode='ACTIONS', export_skins=True,
                          export_force_sampling=True)
print("MS_DONE")
