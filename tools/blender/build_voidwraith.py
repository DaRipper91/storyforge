"""Voidwraith hero: slender masked astral explorer on the cosmic shared-skeleton base (Blender 5.x).
Run: blender -b -P build_voidwraith.py -- <cosmic.glb> <out_dir>
Smoky indigo translucent veil-hair, star-speckled mineral skin, crossed null-field wraps, layered kilt panels, belts, pouches,
crystal tool in a metal cage, bracers, strapped boots. Baked textures (mineral stars + gold cracks, veil, cloth, leather)."""
import bpy, bmesh, math, sys, os, random
import numpy as np
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hero_common import *
import hero_textures as T

SRC, OUT = sys.argv[-2], sys.argv[-1]
random.seed(9)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
remove_objects("_Head", "_Feet")
for _o in bpy.data.objects:
    if _o.type == "MESH" and _o.name.endswith(("_Body", "_Legs")):
        _o.data.materials.clear(); _o.data.materials.append(None)
TEX = os.path.join(OUT, "tex_vw")

# ---------- textures ----------
def mineral_tex():
    n = 512; x, y = T._grid(n); rng = np.random.default_rng(2)
    nz = T.fbm(n, 5, 5, 6)
    base = np.array([0.20, 0.19, 0.34], np.float32)
    col = base[None, None, :] * (0.7 + 0.6 * nz[..., None])
    stars = np.zeros((n, n), np.float32)
    ys, xs = rng.integers(0, n, 900), rng.integers(0, n, 900)
    stars[ys, xs] = rng.random(900) ** 2
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        stars += 0.35 * np.roll(np.roll(stars, dx, 1), dy, 0)
    e, _ = T.voronoi(n, 5, 4)
    crack = (1 - T.smooth(0.0, 0.05, e)) * T.smooth(0.52, 0.7, nz)
    gold = np.array([0.55, 0.42, 0.2], np.float32)
    col = col + stars[..., None] * np.array([0.5, 0.5, 0.7], np.float32) + crack[..., None] * gold[None, None, :]
    emis = np.stack([stars * 0.8 + crack * 0.5, stars * 0.8 + crack * 0.35, stars * 1.0 + crack * 0.15, np.ones((n, n), np.float32)], -1)
    h = 0.5 * nz + 0.6 * crack
    return (T.to_image("mineral_diffuse", np.concatenate([col, np.ones((n, n, 1), np.float32)], -1), TEX),
            T.to_image("mineral_normal", T.normal_from_height(h, 1.2), TEX, "Non-Color"),
            T.to_image("mineral_emission", emis, TEX))
def veil_tex():
    n = 512; x, y = T._grid(n)
    nz = T.fbm(n, 12, 5, 4)
    vein = T.smooth(0.82, 0.95, 1 - np.abs(2 * nz - 1))
    rng = np.random.default_rng(6); sp = np.zeros((n, n), np.float32)
    sp[rng.integers(0, n, 500), rng.integers(0, n, 500)] = 1
    sp = np.clip(sp + 0.4 * (np.roll(sp, 1, 0) + np.roll(sp, 1, 1)), 0, 1)
    col = np.stack([0.20 + 0.18 * vein, 0.18 + 0.16 * vein, 0.42 + 0.22 * vein], -1) + sp[..., None] * 0.4
    alpha = np.clip((0.22 + 0.22 * nz + 0.30 * vein + 0.5 * sp) * (1 - 0.5 * T.smooth(0.8, 1.0, y)), 0, 1)
    return T.to_image("veil_diffuse", np.concatenate([col, alpha[..., None]], -1), TEX)
def cloth_tex():
    n = 512; x, y = T._grid(n)
    nz = T.fbm(n, 7, 5, 6); weave = 0.5 + 0.5 * np.sin(x * n * 0.8) * np.sin(y * n * 0.8)
    base = np.array([0.13, 0.12, 0.16], np.float32)
    col = base[None, None, :] * (0.7 + 0.6 * nz[..., None]) * (0.9 + 0.1 * weave[..., None])
    fx, fy = (x * 6) % 1.0, (y * 2) % 1.0                         # thin geometric gold lines near the hem
    line = (np.abs(fx - 0.5) * 2 + np.abs(fy - 0.5) * 2 - 0.9)
    k = ((np.abs(line) < 0.05) * T.smooth(0.6, 0.9, y))[..., None]
    col = col * (1 - k) + np.array([0.5, 0.38, 0.2], np.float32)[None, None, :] * k
    return (T.to_image("cloth_diffuse", np.concatenate([col, np.ones((n, n, 1), np.float32)], -1), TEX),
            T.to_image("cloth_normal", T.normal_from_height(0.5 * weave + 0.3 * nz + k[..., 0], 1.0), TEX, "Non-Color"))
mi, mn, me = mineral_tex(); vi = veil_tex(); ci, cn = cloth_tex()

# ---------- materials ----------
M_MIN   = mat("VW_Mineral", (0.20, 0.19, 0.34), 0.42, 0.15)
M_SUIT  = mat("VW_Suit", (0.10, 0.095, 0.17), 0.5, 0.1)
M_VEIL  = mat("VW_Veil", (0.22, 0.19, 0.42), 0.35, 0.0, alpha=0.38)
M_CLOTH = mat("VW_Cloth", (0.13, 0.12, 0.16), 0.9)
M_LEATH = mat("VW_Leather", (0.075, 0.055, 0.045), 0.5)
M_METAL = mat("VW_Pewter", (0.42, 0.40, 0.40), 0.35, 0.9)
M_GOLD  = mat("VW_GoldInlay", (0.6, 0.46, 0.22), 0.3, 1.0)
M_CRYS  = mat("VW_Crystal", (0.5, 0.18, 0.85), 0.1, 0.0, emit=(0.55, 0.15, 1.0), strength=2.2)
M_EYE   = mat("VW_Eye", (0.01, 0.01, 0.03), 0.1, 0.0, emit=(0.15, 0.1, 0.4), strength=0.5)
T.bind(M_MIN, mi, mn, me, 0.8); T.bind(M_VEIL, vi); T.bind(M_CLOTH, ci, cn)
recolor_base({"SciFi_Light": (0.06, 0.055, 0.10), "SciFi_Light_Accent": (0.1, 0.09, 0.14), "SciFi_Main": (0.05, 0.045, 0.08),
              "SciFi_MainDark": (0.03, 0.028, 0.05), "Grey": (0.05, 0.045, 0.08)})

# ---------- masked head and flowing veil-hair ----------
bm = bmesh.new()
ell(bm, (0, -0.05, 1.652), (0.082, 0.108, 0.112), seg=18, rings=12)                    # cranium (elongated)
ell(bm, (0, -0.09, 1.595), (0.063, 0.075, 0.075), seg=14, rings=9)                     # mask face
ell(bm, (0, -0.103, 1.540), (0.034, 0.045, 0.038), seg=10, rings=7)                    # narrow chin
for sx in (1, -1):
    ell(bm, (sx * 0.05, -0.115, 1.618), (0.020, 0.018, 0.016), seg=8, rings=5)         # cheekbone ridge
    ell(bm, (sx * 0.070, -0.030, 1.640), (0.014, 0.030, 0.050), seg=8, rings=5)       # temple plate
tube(bm, (0, -0.150, 1.645), (0, -0.165, 1.600), 0.009, 0.012, seg=6)                  # faint nose ridge
ell(bm, (0, -0.040, 1.50), (0.036, 0.036, 0.055), seg=10, rings=6)                     # neck
attach(arm, "Hero_Mask", bm, M_MIN, "Head", smooth=True)
bm = bmesh.new()
for sx in (1, -1):                                                                     # slanted almond eyes
    ell(bm, (sx * 0.036, -0.1405, 1.628), (0.024, 0.006, 0.0105), rot=(0, sx * math.radians(-16), 0), seg=10, rings=5)
attach(arm, "Hero_Eyes", bm, M_EYE, "Head")
bm = bmesh.new()
ell(bm, (0, -0.1525, 1.69), (0.010, 0.003, 0.021), rot=(0, 0, math.radians(0)), seg=4, rings=3)      # forehead diamond inlay
for sx in (1, -1):
    ell(bm, (sx * 0.034, -0.143, 1.652), (0.022, 0.003, 0.003), rot=(0, sx * math.radians(-18), 0), seg=6, rings=3)   # brow line
    tube(bm, (sx * 0.05, -0.139, 1.612), (sx * 0.062, -0.12, 1.575), 0.003, 0.003, seg=4)                       # cheek line
attach(arm, "Hero_Inlay", bm, M_GOLD, "Head")
bm = bmesh.new()                                                                       # translucent veil-hair ribbons
for k in range(8):
    a = math.radians(-105 + k * 30)
    root = Vector((0.08 * math.sin(a), -0.04 - 0.08 * math.cos(a) * 0.4 + 0.02, 1.70))
    ln = random.uniform(0.55, 0.85)
    def rib(r, c, root=root, a=a, ln=ln, k=k):
        t = r; w = 0.05 * (1 - 0.45 * t) * (1 if t < 0.95 else 0.3)
        sway = 0.07 * math.sin(t * 5 + k) * t
        p = root + Vector((math.sin(a) * 0.12 * t + sway, 0.06 + 0.16 * t, -ln * t))
        return p + Vector((math.cos(a) * w * (c - 0.5) * 2, 0, 0))
    attach_bm = strip(12, 3, rib)
    bmesh.ops.recalc_face_normals(attach_bm, faces=attach_bm.faces)
    me = bpy.data.meshes.new("rib%d" % k); attach_bm.to_mesh(me); attach_bm.free()
    o = bpy.data.objects.new("Hero_VeilHair_%d" % k, me); bpy.context.scene.collection.objects.link(o)
    me.materials.append(M_VEIL)
    for p_ in me.polygons: p_.use_smooth = True
    o.parent = arm; o.parent_type = 'BONE'; o.parent_bone = "Head"
    b = arm.data.bones["Head"]
    o.matrix_parent_inverse = (arm.matrix_world @ b.matrix_local @ Matrix.Translation((0, b.length, 0))).inverted()
bm.free()

# ---------- cowl, scarf drape, crossed wraps over a tunic ----------
def tors(a, z, off=0.0):
    rx, ry = 0.165 + off, 0.135 + off
    return Vector((rx * math.sin(a), -0.043 - ry * math.cos(a), z))
def tunic(r, c):
    return tors(2 * math.pi * c, 1.50 - r * 0.50, 0.0) + Vector((0, 0, 0))
def tunic_w(co):
    ch = smoothstep(1.18, 1.32, co.z); tq = smoothstep(1.02, 1.1, co.z) * (1 - ch)
    return {"Chest": ch, "Torso": tq, "Hips": max(0.0, 1.0 - ch - tq)}
skinned(arm, "Hero_Tunic", strip(9, 28, tunic), M_CLOTH, tunic_w)
def cowl(r, c, layer):
    a = 2 * math.pi * c
    rad = 0.085 + 0.022 * layer + 0.03 * r
    return Vector((rad * math.sin(a), -0.043 - rad * math.cos(a), 1.545 - r * 0.07 - layer * 0.018))
for layer in range(3):
    attach(arm, f"Hero_Cowl{layer}", strip(4, 22, lambda r, c, l=layer: cowl(r, c, l)), M_CLOTH, "Chest")
def wrap_band(a0, a1, z0, z1, w, off, n=16):
    pts = [tors(a0 + (a1 - a0) * i / (n - 1), z0 + (z1 - z0) * i / (n - 1), off) for i in range(n)]
    def fn(r, c):
        i = int(round(r * (n - 1))); p = pts[i]
        tan = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        out = Vector((p.x, p.y + 0.043, 0)).normalized()
        wd = tan.cross(out).normalized()
        return p + wd * (c - 0.5) * 2 * w
    return strip(n, 3, fn)
bands = bmesh.new()
for a0, a1 in ((math.radians(-95), math.radians(95)), (math.radians(95), math.radians(-95))):
    pass
attach(arm, "Hero_WrapX1", wrap_band(math.radians(-100), math.radians(100), 1.47, 1.10, 0.034, 0.012), M_CLOTH, "Chest")
attach(arm, "Hero_WrapX2", wrap_band(math.radians(100), math.radians(-100), 1.47, 1.10, 0.034, 0.016), M_CLOTH, "Chest")
for z, off in ((1.16, 0.018), (1.10, 0.022), (1.045, 0.026)):
    attach(arm, f"Hero_Wrap_{int(z*100)}", wrap_band(0.0, 2 * math.pi, z, z, 0.030, off, n=28), M_CLOTH, "Torso")
bm = bmesh.new()                                                                      # bandolier strap + buckles (leather) over the X
for a0, a1 in ((math.radians(-60), math.radians(100)),):
    pts = [tors(a0 + (a1 - a0) * i / 14, 1.47 - 0.33 * i / 14, 0.028) for i in range(15)]
    for i in range(14): tube(bm, pts[i], pts[i + 1], 0.014, 0.014, seg=5)
    for i in (3, 8, 12): ell(bm, pts[i], (0.024, 0.012, 0.022), seg=6, rings=4)
attach(arm, "Hero_Bandolier", bm, M_LEATH, "Chest")
bm = bmesh.new()
for i in (3, 8, 12):
    p = tors(math.radians(-60) + (math.radians(160)) * i / 14, 1.47 - 0.33 * i / 14, 0.034)
    ell(bm, p, (0.014, 0.006, 0.012), seg=6, rings=3)
attach(arm, "Hero_Buckles", bm, M_METAL, "Chest")

# ---------- layered kilt panels, long veil layers, belt, pouches, crystal tool ----------
def panel(cx, width, zt, zb, depth, radius, phase):
    def fn(r, c):
        a = cx + (c - 0.5) * width * (1 - 0.35 * r)
        z = zt + r * (zb - zt)
        tip = 0.06 * (1 - abs(2 * c - 1)) * r
        rad = radius + 0.06 * r + 0.008 * math.sin(c * 12 + phase)
        return Vector((rad * math.sin(a), -rad * math.cos(a), z - tip))
    return fn
def kilt_w(co):
    t = smoothstep(1.0, 0.45, co.z); front = max(0.0, -co.y / max(1e-6, math.hypot(co.x, co.y)))
    wl = t * (0.25 + 0.6 * front)
    return {"Hips": 1.0 - wl, ("UpperLeg.L" if co.x >= 0 else "UpperLeg.R"): wl}
PANELS = ((0.0, 0.5, 1.03, 0.34, 0.205, 0.0), (0.8, 0.42, 1.03, 0.52, 0.2, 1.3), (-0.8, 0.42, 1.03, 0.52, 0.2, 2.1),
          (1.9, 0.5, 1.03, 0.46, 0.2, 0.7), (-1.9, 0.5, 1.03, 0.46, 0.2, 1.9), (math.pi, 0.7, 1.03, 0.40, 0.2, 0.2))
for i, (cx, w, zt, zb, rad, ph) in enumerate(PANELS):
    skinned(arm, f"Hero_Panel{i}", strip(10, 9, panel(cx, w, zt, zb, 0, rad, ph)), M_CLOTH, kilt_w)
def veil_skirt(r, c):
    a = math.radians(20 + c * 320)
    z = 0.98 + r * (0.12 - 0.98) - 0.10 * (abs(math.sin(c * 40)) ** 0.8) * r * r
    rad = 0.215 + 0.17 * (r ** 1.5) + 0.012 * math.sin(c * 30)
    return Vector((rad * math.sin(a), -rad * math.cos(a), z))
skinned(arm, "Hero_VeilSkirt", strip(12, 64, veil_skirt), M_VEIL, kilt_w)
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=26, radius1=0.2, radius2=0.2, depth=0.06, matrix=Matrix.Translation((0, -0.05, 1.04)))
bmesh.ops.create_cone(bm, cap_ends=True, segments=26, radius1=0.205, radius2=0.205, depth=0.022, matrix=Matrix.Translation((0, -0.05, 0.99)))
attach(arm, "Hero_Belt", bm, M_LEATH, "Hips")
bm = bmesh.new()
ell(bm, (0, -0.236, 1.04), (0.034, 0.010, 0.034), seg=10, rings=5)
for sx in (1, -1): ell(bm, (sx * 0.10, -0.21, 1.04), (0.012, 0.008, 0.012), seg=6, rings=4)
attach(arm, "Hero_BeltBuckle", bm, M_METAL, "Hips")
for sx, tag in ((-1, "R"), (1, "L")):                                                 # pouches on both hips
    bm = bmesh.new()
    for dz, dx in ((0, 0), (0.0, 0)):
        ell(bm, (sx * 0.175, -0.10, 0.93), (0.030, 0.055, 0.050), seg=8, rings=6)
        ell(bm, (sx * 0.175, -0.10, 0.975), (0.033, 0.058, 0.014), seg=8, rings=4)
    attach(arm, "Hero_Pouch_" + tag, bm, M_LEATH, "Hips")
bm = bmesh.new(); bc = bmesh.new()
cx_, cy_, cz_ = 0.205, -0.02, 0.76                                                    # crystal tool at the left hip
tube(bm, (cx_, cy_, 0.99), (cx_, cy_ - 0.01, 0.90), 0.006, 0.006, seg=4)
cone(bc, (cx_, cy_ - 0.01, 0.90), (0, 0, -1), 0.028, 0.10, seg=6)                      # crystal body
cone(bc, (cx_, cy_ - 0.01, 0.90), (0, 0, 1), 0.028, 0.04, seg=6)
for dz in (0.915, 0.86):
    bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.032, radius2=0.032, depth=0.010, matrix=Matrix.Translation((cx_, cy_ - 0.01, dz)))
for a_ in range(4):
    tube(bm, Vector((cx_ + 0.03 * math.cos(a_ * 1.57), cy_ - 0.01 + 0.03 * math.sin(a_ * 1.57), 0.92)), Vector((cx_ + 0.03 * math.cos(a_ * 1.57), cy_ - 0.01 + 0.03 * math.sin(a_ * 1.57), 0.84)), 0.004, 0.004, seg=4)
attach(arm, "Hero_ToolCage", bm, M_METAL, "Hips")
attach(arm, "Hero_Crystal", bc, M_CRYS, "Hips", smooth=False)

# ---------- bracers with straps ----------
for side, bone, tag in ((1, "LowerArm.L", "L"), (-1, "LowerArm.R", "R")):
    bm = bmesh.new(); bs = bmesh.new()
    for i, x0 in enumerate((0.34, 0.42, 0.50)):
        def band_fn(r, c, s=side, x0=x0):
            a = 2 * math.pi * c
            return Vector((s * (x0 + r * 0.055), -0.056 + 0.050 * math.sin(a), 1.432 + 0.050 * math.cos(a)))
        bb = strip(3, 14, band_fn)
        bm.from_mesh(bpy.data.meshes.new("t")) if False else None
        me = bpy.data.meshes.new(f"bracer{tag}{i}"); bb.to_mesh(me); bb.free()
        o = bpy.data.objects.new(f"Hero_Bracer{tag}{i}", me); bpy.context.scene.collection.objects.link(o)
        me.materials.append(M_METAL)
        for p_ in me.polygons: p_.use_smooth = True
        o.parent = arm; o.parent_type = 'BONE'; o.parent_bone = bone
        b = arm.data.bones[bone]; o.matrix_parent_inverse = (arm.matrix_world @ b.matrix_local @ Matrix.Translation((0, b.length, 0))).inverted()
        ell(bs, (side * (x0 + 0.028), -0.056 - 0.052, 1.432), (0.012, 0.006, 0.012), seg=6, rings=3)
    bm.free()
    attach(arm, "Hero_BracerBuckle_" + tag, bs, M_GOLD, bone)

# ---------- strapped boots ----------
for side, lower, foot in ((1, "LowerLeg.L", "Foot.L"), (-1, "LowerLeg.R", "Foot.R")):
    cx = side * 0.121
    def shaft(r, c, cx=cx):
        a = 2 * math.pi * c; z = 0.50 - r * 0.47
        rad = 0.056 - 0.010 * min(1.0, r * 1.6) + (0.012 if r < 0.05 else 0.0)
        return Vector((cx + rad * math.cos(a), -0.087 + 0.025 * r + rad * math.sin(a) * 1.05, z))
    skinned(arm, "Hero_BootShaft_" + ("L" if side > 0 else "R"), strip(10, 18, shaft), M_LEATH, lambda co, lower=lower, foot=foot: {lower: 1 - smoothstep(0.30, 0.10, co.z), foot: smoothstep(0.30, 0.10, co.z)})
    bm = bmesh.new()
    ell(bm, (cx, -0.135, 0.050), (0.050, 0.105, 0.040), seg=12, rings=7)
    ell(bm, (cx, -0.046, 0.052), (0.045, 0.050, 0.050), seg=10, rings=6)
    ell(bm, (cx, -0.105, 0.016), (0.053, 0.135, 0.014), seg=12, rings=5)
    attach(arm, "Hero_BootFoot_" + ("L" if side > 0 else "R"), bm, M_LEATH, foot)
    bm = bmesh.new()
    for z in (0.40, 0.31, 0.22, 0.14):
        bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.060 - (0.46 - z) * 0.02, radius2=0.060 - (0.46 - z) * 0.02, depth=0.012, matrix=Matrix.Translation((cx, -0.087 + 0.025 * (0.5 - z) / 0.47, z)))
        ell(bm, (cx + side * 0.052, -0.087, z), (0.010, 0.012, 0.010), seg=6, rings=3)
    ell(bm, (cx, -0.18, 0.050), (0.026, 0.016, 0.024), seg=6, rings=4)
    attach(arm, "Hero_BootStraps_" + ("L" if side > 0 else "R"), bm, M_METAL, foot)

for _o in bpy.data.objects:
    if _o.type == "MESH" and _o.name.endswith(("_Body", "_Legs")):
        _o.data.materials.clear(); _o.data.materials.append(M_SUIT)
        for _p in _o.data.polygons: _p.material_index = 0
print("VW_TOTAL_TRIS", tri_count())
bpy.ops.wm.save_as_mainfile(filepath=OUT + "/voidwraith.blend")
bpy.ops.export_scene.gltf(filepath=OUT + "/voidwraith.glb", export_format='GLB', export_apply=True,
                          export_animations=False, export_skins=True)
print("VW_DONE")
