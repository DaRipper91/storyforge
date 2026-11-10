"""Ashenborn hero: charred human survivor. Bone-scale vest, soot linen with rolled sleeves, baggy trousers, laced tall boots,
bare fissured hands, sculpted face, emberstone axe (Blender 5.x).
Run: blender -b -P build_ashenborn.py -- <humanoid.glb> <out_dir>
Front is -Y, T-pose rest, shared 49-bone skeleton untouched. All bespoke parts are named Hero_*."""
import bpy, bmesh, math, sys, os, random
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from humanoid_a_common import *

SRC, OUT = sys.argv[-2], sys.argv[-1]
random.seed(31); rnd = random.Random(31)
TEX = os.path.join(OUT, "tex")

bpy.ops.wm.read_factory_settings(use_empty=True)

# ---------- materials ----------
M_SKIN    = mat("AB_SkinArm", (0.09, 0.075, 0.07), 0.8)
M_SKINP   = mat("AB_Skin",    (0.10, 0.083, 0.078), 0.75)
M_LINEN   = mat("AB_Linen",   (0.30, 0.24, 0.17), 0.95)
M_TABARD  = mat("AB_Tabard",  (0.36, 0.31, 0.22), 0.95)
M_TROUSER = mat("AB_Trouser", (0.11, 0.095, 0.082), 0.95)
M_BONE    = mat("AB_BoneMail", (0.30, 0.20, 0.13), 0.6)
M_LEATHER = mat("AB_Leather", (0.20, 0.10, 0.055), 0.6)
M_BOOT    = mat("AB_Boot",    (0.21, 0.115, 0.065), 0.65)
M_LACE    = mat("AB_Lace",    (0.40, 0.27, 0.15), 0.7)
M_METAL   = mat("AB_Metal",   (0.42, 0.40, 0.38), 0.4, 0.9)
M_EMBER   = mat("AB_Ember",   (0.9, 0.3, 0.05), 0.4, emit=(1.0, 0.33, 0.04), strength=3.0)
M_HAIR    = mat("AB_Hair",    (0.03, 0.025, 0.022), 0.6)
M_LIPS    = mat("AB_Lips",    (0.14, 0.085, 0.08), 0.6)
M_SCLERA  = mat("AB_Sclera",  (0.55, 0.5, 0.45), 0.3)
M_IRIS    = mat("AB_Iris",    (0.55, 0.36, 0.1), 0.2, emit=(0.5, 0.25, 0.05), strength=0.5)
M_DARK    = mat("AB_Dark",    (0.01, 0.008, 0.008), 0.5)
M_HAFT    = mat("AB_Haft",    (0.19, 0.11, 0.07), 0.8)
M_STEEL   = mat("AB_AxeSteel", (0.22, 0.21, 0.21), 0.45, 0.85)

arm = prep(SRC, M_SKIN, M_TROUSER)

# ---------- textures (1024 px main surfaces) ----------
d, nm, em = tex_surface(TEX, "ab_skin", (0.09, 0.075, 0.07), 3, "skin", n=512, wear=0.4, emis=(1.0, 0.35, 0.05), normal_strength=0.4)
T.bind(M_SKIN, d, nm, em, 0.25)
d, nm = tex_surface(TEX, "ab_linen", (0.30, 0.24, 0.17), 5, "cloth", n=1024, wear=0.9, scale=1.0); T.bind(M_LINEN, d, nm)
d, nm = tex_surface(TEX, "ab_tabard", (0.36, 0.31, 0.22), 7, "cloth", n=512, wear=1.0, scale=0.8); T.bind(M_TABARD, d, nm)
d, nm = tex_surface(TEX, "ab_trouser", (0.11, 0.095, 0.082), 9, "cloth", n=512, wear=0.9, scale=1.3); T.bind(M_TROUSER, d, nm)
d, nm = tex_surface(TEX, "ab_bone", (0.32, 0.21, 0.13), 11, "bone", n=512, wear=0.8); T.bind(M_BONE, d, nm)
d, nm = tex_surface(TEX, "ab_boot", (0.21, 0.115, 0.065), 13, "leather", accent=(0.45, 0.3, 0.16), n=512, wear=1.0); T.bind(M_BOOT, d, nm)
d, nm = tex_surface(TEX, "ab_leather", (0.20, 0.10, 0.055), 15, "leather", accent=(0.45, 0.3, 0.16), n=512, wear=0.9); T.bind(M_LEATHER, d, nm)

uv_arm_cyl(next(o for o in bpy.data.objects if o.name.endswith("_Body")))

# ---------- head ----------
build_face(arm, M_SKINP, M_LIPS, M_HAIR, M_IRIS, M_SCLERA, M_DARK,
           dict(jaw=1.12, chin=1.1, brow=1.35, cheek=1.2, nose=1.05, eye=0.95, slant=6, neck=0.05, face_w=1.02))
face_o = bpy.data.objects["Hero_Face"]
# Union the individually sculpted anatomical volumes into one continuous skin surface.
bpy.context.view_layer.objects.active = face_o
rem = face_o.modifiers.new("SculptUnion", 'REMESH'); rem.mode='VOXEL'; rem.voxel_size=.0025
bpy.ops.object.modifier_apply(modifier=rem.name)
sm = face_o.modifiers.new("SculptRelax", 'SMOOTH'); sm.factor=.5; sm.iterations=3
bpy.ops.object.modifier_apply(modifier=sm.name)
dec = face_o.modifiers.new("FaceBudget", 'DECIMATE'); dec.ratio=min(1,1800/max(1,len(face_o.data.polygons)*2))
bpy.ops.object.modifier_apply(modifier=dec.name)
for p in face_o.data.polygons: p.use_smooth=True


def on_face(xz_pts, lift=0.0014):
    out = []
    for x, z in xz_pts:
        hit, loc, nrm, _ = face_o.ray_cast(Vector((x, -0.35, z)), Vector((0, 1, 0)))
        if hit: out.append(loc + nrm * lift)
    return out


bm = bmesh.new()
for pts in (
    [(0.058, 1.672), (0.062, 1.655), (0.056, 1.64), (0.060, 1.625), (0.052, 1.612), (0.046, 1.600), (0.040, 1.588)],
    [(0.056, 1.640), (0.066, 1.636), (0.072, 1.628)],
    [(0.052, 1.612), (0.060, 1.604), (0.064, 1.592)],
    [(-0.020, 1.724), (-0.026, 1.712), (-0.020, 1.700), (-0.026, 1.690)],
    [(-0.062, 1.610), (-0.058, 1.598), (-0.064, 1.585), (-0.058, 1.572)],
):
    p = on_face(pts)
    if len(p) > 2:
        sub = catmull(p, 2)
        sweep(bm, sub, [0.0017 * (1 - 0.6 * i / len(sub)) for i in range(len(sub))], sides=4)
attach(arm, "Hero_FaceFissure", bm, M_EMBER, "Head")

# hair: cropped, textured by short spikes
bm = bmesh.new()
ell(bm, (0, -0.030, 1.668), (0.088, 0.108, 0.098), seg=18, rings=10)
for k in range(150):
    ph = math.radians(rnd.uniform(-170, 170)); el = math.radians(rnd.uniform(5, 85))
    if abs(ph) < math.radians(55) and el < math.radians(58): continue      # keep the forehead clear
    root = Vector((0.092 * math.sin(ph) * math.cos(el), -0.032 - 0.112 * math.cos(ph) * math.cos(el), 1.668 + 0.104 * math.sin(el)))
    out = (root - Vector((0, -0.032, 1.66))).normalized()
    tube(bm, root, root + out * rnd.uniform(0.005, 0.012), 0.0045, 0.001, seg=4)
for sx in (1, -1):
    ell(bm, (sx * 0.083, -0.085, 1.62), (0.008, 0.026, 0.040), seg=7, rings=4)         # sideburns
attach(arm, "Hero_Hair", bm, M_HAIR, "Head")

# ---------- fully authored round forearms, replacing the angular CC0 base arms ----------
for side,suf in ((1,'L'),(-1,'R')):
    skinned(arm,'Hero_Forearm_'+suf,sleeve(side,.405,.583,.002,.001,rings=14,sides=16,fold=.0008,seed=31),M_SKIN,arm_w_full(side))

# ---------- hands (bare, charcoal) with ember cracks on the backs ----------
hands(arm, M_SKINP, nail_mat=M_DARK, tag="")
bm = bmesh.new()
for s, sx in (("L", 1), ("R", -1)):
    bm = bmesh.new()
    h0, h1 = bone("Hand." + s)
    for off in ((0.02, -0.03), (0.05, 0.0)):
        a = Vector((h0.x + sx * off[0], h0.y + off[1], 1.432 + 0.0178))
        b = a + Vector((sx * 0.03, 0.02, 0.0005))
        sweep(bm, catmull(crack_path(rnd, a, b, 0.004, 5), 2), 0.0014, sides=4)
    attach(arm, "Hero_HandFissure_" + s, bm, M_EMBER, "Hand." + s)


# ---------- linen shirt (loose, V neck, rolled sleeves) ----------
def shirt_pt(r, c):
    ang = 2 * math.pi * c
    d = abs(((ang + math.pi) % (2 * math.pi)) - math.pi)          # angular distance from front
    ztop = 1.538 - (0.075 * (1 - d / 0.42) if d < 0.42 else 0.0)
    z = lerp(1.0, ztop, r)
    cy, rx, ry = torso_profile(min(z, 1.47))
    g = 0.018 + 0.006 * math.sin(ang * 6 + r * 4) + 0.004 * math.sin(ang * 11)
    if z > 1.41:
        t = smoothstep(1.41, 1.538, z)
        rx = lerp(rx + g, 0.074, t); ry = lerp(ry + g, 0.062, t); cy = lerp(cy, -0.043, t); g = 0.0
    else:
        rx += g; ry += g
    return Vector((math.sin(ang) * rx, cy - math.cos(ang) * ry, z))


skinned(arm, "Hero_Shirt", ring_strip(14, 40, shirt_pt), M_LINEN, nearest_w(TORSO_BONES + ["UpperArm.L", "UpperArm.R"], 0.04))
for side, tag in ((1, "L"), (-1, "R")):
    skinned(arm, "Hero_Sleeve_" + tag, sleeve(side, 0.09, 0.44, 0.014, 0.012, rings=12, sides=16, fold=0.004, seed=side + 3), M_LINEN, arm_w_full(side))
    skinned(arm, "Hero_SleeveRoll_" + tag, sleeve(side, 0.395, 0.455, 0.020, 0.020, rings=4, sides=16, fold=0.003, seed=side + 8, hem_saw=0.01), M_LINEN, arm_w_full(side))

# ---------- bone-scale vest ----------
TWB = TORSO_BONES + ["UpperLeg.L", "UpperLeg.R"]


def scale_plate(bm, P, n, t, w, h, flare, win):
    """Pentagon-ish scale plate hanging from P; UV window (u0, v0, size) so every plate samples a different patch."""
    outline = [(-0.5, 0.0), (0.5, 0.0), (0.5, 0.55), (0.34, 0.88), (0.0, 1.0), (-0.34, 0.88), (-0.5, 0.55)]
    vs = []; uvs = []
    for u, v in outline:
        p = P + t * (u * w) + Vector((0, 0, -v * h)) + n * (flare * v + 0.004 * (1 - (2 * u) ** 2) + 0.002)
        vs.append(bm.verts.new(p)); uvs.append((win[0] + (u + 0.5) * win[2], win[1] + (1 - v) * win[2]))
    f = bm.faces.new(vs)
    layer = bm.loops.layers.uv.verify()
    for lp, uv in zip(f.loops, uvs): lp[layer].uv = uv


def vest_rows(rows, zs, hs, flares, ws, count_scale=1.0, grow=0.016, skip_arm=True):
    bm = bmesh.new()
    for i, z in enumerate(zs):
        cy, rx, ry = torso_profile(z)
        circ = 2 * math.pi * math.sqrt((rx ** 2 + ry ** 2) / 2)
        n_s = int(circ / (ws[i] * 0.82) * count_scale)
        off = (i % 2) * 0.5
        for k in range(n_s):
            ang = 2 * math.pi * (k + off) / n_s
            P = torso_pt(z, ang, grow=grow + 0.004 * i * 0.0)
            if skip_arm and abs(P.x) > 0.115 and z > 1.372: continue
            P2 = torso_pt(z, ang + 0.02, grow=grow)
            t = (P2 - P); t.z = 0; t.normalize()
            n = Vector((-t.y, t.x, 0)); n = n if n.dot(Vector((P.x, P.y - cy, 0))) > 0 else -n
            scale_plate(bm, P, n, t, ws[i] * 0.95, hs[i], flares[i], (rnd.random() * 0.75, rnd.random() * 0.75, 0.25))
    return bm


zs = [1.462 - i * 0.034 for i in range(10)]
bm = vest_rows(10, zs, [0.062] * 10, [0.016] * 10, [0.050] * 10)
skinned(arm, "Hero_BoneMail", bm, M_BONE, nearest_w(TORSO_BONES, 0.035))
zs2 = [1.115, 1.075, 1.035]
bm = vest_rows(3, zs2, [0.085, 0.09, 0.095], [0.026, 0.034, 0.042], [0.058, 0.060, 0.062], grow=0.02)
skinned(arm, "Hero_BoneTassets", bm, M_BONE, nearest_w(TWB, 0.03))
# lacing thongs between rows
bm = bmesh.new()
for i in (1, 3, 5, 7, 9):
    z = zs[i] + 0.004
    pts = [torso_pt(z, 2 * math.pi * k / 44, grow=0.019) for k in range(45)]
    pts = [p for p in pts if not (abs(p.x) > 0.115 and z > 1.372)]
    run = []
    for p in pts:
        run.append(p)
    sweep(bm, run, 0.0030, sides=3, cap0=False, cap1=False)
skinned(arm, "Hero_VestLacing", bm, M_LEATHER, nearest_w(TORSO_BONES, 0.035))
# shoulder straps
for sx, tag in ((1, "L"), (-1, "R")):
    def strap(r, c, sx=sx):
        t = r
        y = lerp(-0.128, 0.045, t); z = 1.455 + 0.075 * math.sin(math.pi * t) * 0.9 - 0.02 * (t > 0.5) * (t - 0.5)
        x = sx * (0.098 + 0.006 * math.sin(math.pi * t)) + (c - 0.5) * 0.034 * sx
        return Vector((x, y, z + 0.012 * (1 - (2 * c - 1) ** 2)))
    skinned(arm, "Hero_VestStrap_" + tag, strip(9, 3, strap), M_LEATHER, nearest_w(TORSO_BONES, 0.035))

# ---------- belt, buckle, pouch, cross strap, axe ----------
def belt_pt(r, c, gz=1.03, gr=0.036):
    ang = 2 * math.pi * c
    p = torso_pt(gz + (r - 0.5) * 0.058, ang, grow=gr, pw=2.4)
    return p
skinned(arm, "Hero_Belt", ring_strip(2, 44, belt_pt), M_LEATHER, nearest_w(["Hips", "Abdomen"], 0.03))
skinned(arm, "Hero_Belt2", ring_strip(2, 44, lambda r, c: belt_pt(r, c, 0.975, 0.036)), M_LEATHER, nearest_w(["Hips", "Abdomen"], 0.03))
bm = bmesh.new()
fy = torso_pt(1.03, 0, grow=0.04).y - 0.004
for dx in (-0.034, 0.034): ell(bm, (dx, fy, 1.03), (0.0055, 0.004, 0.034), seg=6, rings=4)
for dz in (-0.03, 0.03): ell(bm, (0, fy, 1.03 + dz), (0.040, 0.004, 0.0055), seg=6, rings=4)
tube(bm, (0, fy - 0.003, 1.03), (0.03, fy - 0.003, 1.03), 0.004, 0.004, seg=4)
attach(arm, "Hero_Buckle", bm, M_METAL, "Hips")
# pouch on the character's left hip
pb = bmesh.new()
px, py, pz = 0.185, -0.075, 0.975
blob(pb, (px, py, pz - 0.03), Vector((0.022, 0, 0)), Vector((0, 0.042, 0)), Vector((0, 0, 0.05)), seg=10, rings=6)
blob(pb, (px + 0.004, py - 0.004, pz + 0.012), Vector((0.025, 0, 0)), Vector((0, 0.044, 0)), Vector((0, 0, 0.028)), seg=10, rings=6)      # flap
blob(pb, (px + 0.012, py - 0.048, pz + 0.0), Vector((0.006, 0, 0)), Vector((0, 0.005, 0)), Vector((0, 0, 0.012)), seg=6, rings=4)
attach(arm, "Hero_Pouch", pb, M_LEATHER, "Hips")
# axe slung across the lower back
ab = bmesh.new(); ah = bmesh.new(); ae = bmesh.new(); aw = bmesh.new()
y0, z0 = 0.118, 1.045
sweep(ab, [Vector((-0.215, y0, z0 - 0.01)), Vector((-0.05, y0, z0)), Vector((0.12, y0, z0 + 0.008))], [0.0125, 0.012, 0.011], sides=8)
ell(ab, (-0.222, y0, z0 - 0.012), (0.014, 0.016, 0.016), seg=8, rings=5)
for xx in (-0.19, -0.172, -0.154, -0.136, -0.118):                       # wrap bands
    bmesh.ops.create_cone(aw, cap_ends=True, segments=8, radius1=0.0145, radius2=0.0145, depth=0.009,
                          matrix=Matrix.Translation((xx, y0, z0 - 0.007)) @ Matrix.Rotation(math.pi / 2, 4, 'Y'))
ax = 0.12
outline = [(0.0, 0.032), (0.03, 0.075), (0.09, 0.118), (0.135, 0.100), (0.118, 0.030), (0.124, -0.030), (0.140, -0.100), (0.092, -0.118), (0.03, -0.074), (0.0, -0.032)]
fv = [ah.verts.new((ax + u, y0 + 0.011, z0 + 0.008 + v)) for u, v in outline]
bv = [ah.verts.new((ax + u, y0 - 0.011, z0 + 0.008 + v)) for u, v in outline]
ah.faces.new(fv); ah.faces.new(bv[::-1])
for i in range(len(outline)): ah.faces.new((fv[i], fv[(i + 1) % len(fv)], bv[(i + 1) % len(fv)], bv[i]))
for (a, b) in (((0.105, 0.08), (0.110, 0.02)), ((0.110, 0.02), (0.100, -0.02)), ((0.100, -0.02), (0.118, -0.062))):
    tube(ae, (ax + a[0], y0 + 0.0125, z0 + 0.008 + a[1]), (ax + b[0], y0 + 0.0125, z0 + 0.008 + b[1]), 0.0017, 0.0015, seg=4)
attach(arm, "Hero_AxeHaft", ab, M_HAFT, "Hips"); attach(arm, "Hero_AxeWrap", aw, M_LEATHER, "Hips")
attach(arm, "Hero_AxeHead", ah, M_STEEL, "Hips", smooth=False); attach(arm, "Hero_AxeEmber", ae, M_EMBER, "Hips")

# ---------- tattered linen tabard (front + back, layered) ----------
def tabard(front, layer):
    def fn(r, c):
        half = 0.78 if front else 0.95
        a = (c - 0.5) * 2 * half + (0.0 if front else math.pi)
        zt = 1.0
        hemv = (0.72 if front else 0.66) + 0.04 * layer + 0.045 * math.sin(c * 17.0 + layer) + 0.05 * abs(math.sin(c * 41.0 + layer * 2)) - 0.07 * (abs(math.sin(c * 23.0 + 1.1 * layer)) ** 6) + (0.04 * (1 - abs(2 * c - 1)) if layer else 0)
        z = zt + r * (hemv - zt)
        g = 0.034 + 0.020 * layer + 0.075 * (r ** 1.4) + 0.008 * math.sin(c * 30 + r * 3) * r
        cy, rx, ry = torso_profile(1.0)
        return Vector((math.sin(a) * (rx + g), cy - math.cos(a) * (ry + g), z))
    return fn


def tab_w(co):
    t = smoothstep(1.0, 0.55, co.z) * 0.8
    s = "UpperLeg.L" if co.x >= 0 else "UpperLeg.R"
    return {"Hips": 1.0 - t, s: t} if t > 0.02 else {"Hips": 1.0}


for front, nm_ in ((True, "F"), (False, "B")):
    for layer in (0, 1):
        skinned(arm, f"Hero_Tabard{nm_}{layer}", strip(9, 26, tabard(front, layer)), M_TABARD, tab_w)

# ---------- baggy trousers ----------
def trouser_fn(side):
    def fn(r, c):
        z = lerp(1.04, 0.56, r)
        ang = 2 * math.pi * c
        if z > 0.533: ctr_y = -0.087 + (z - 0.533) * (0.042 / 0.431)
        else: ctr_y = -0.087 + 0.025 * (0.533 - z) / 0.51
        rad = lerp(0.112, 0.092, smoothstep(1.04, 0.80, z)) if z > 0.80 else lerp(0.092, 0.080, (0.80 - z) / 0.24)
        if z < 0.62: rad += 0.016 * smoothstep(0.62, 0.56, z)             # blousing over the boot tops
        rad += 0.006 * math.sin(ang * 4 + r * 9 + side) + 0.004 * math.sin(ang * 9 - r * 14)
        return Vector((side * 0.121 + math.cos(ang) * rad, ctr_y + math.sin(ang) * rad * 1.05, z))
    return fn
for side, s in ((1, "L"), (-1, "R")):
    skinned(arm, "Hero_Trouser_" + s, ring_strip(12, 18, trouser_fn(side)), M_TROUSER, nearest_w(side_leg(s), 0.045))

# ---------- tall laced boots ----------
def boot_rad(z):
    if z > 0.2: return lerp(0.060, 0.079, (z - 0.2) / 0.42)
    return lerp(0.067, 0.060, z / 0.2)
def boot_y(z):
    return -0.087 + 0.025 * (0.533 - z) / 0.51 if z <= 0.533 else -0.087 + (z - 0.533) * (0.042 / 0.431)

for side, s in ((1, "L"), (-1, "R")):
    cx = side * 0.121
    def shaft(r, c, cx=cx, side=side, grow=0.0, z0=0.625, z1=0.06):
        z = lerp(z0, z1, r); a = 2 * math.pi * c
        rad = boot_rad(z) + grow + 0.004 * math.sin(r * 44.0) * max(0.0, math.cos(a - math.pi / 2)) * smoothstep(0.55, 0.9, r) + 0.0025 * math.sin(a * 5 + r * 3)
        return Vector((cx + rad * math.cos(a), boot_y(z) + rad * math.sin(a) * 1.05, z))
    skinned(arm, "Hero_BootShaft_" + s, ring_strip(26, 20, shaft), M_BOOT, nearest_w(["LowerLeg." + s, "UpperLeg." + s, "Foot." + s], 0.03))
    skinned(arm, "Hero_BootCuff_" + s, ring_strip(3, 20, lambda r, c, f=shaft: f(0.0 + r * 0.06, c, grow=0.008 - r * 0.004)), M_LEATHER, nearest_w(["LowerLeg." + s, "UpperLeg." + s], 0.03))
    # straps with buckles
    for zc in (0.56, 0.43, 0.30):
        skinned(arm, f"Hero_BootStrap{int(zc * 100)}_{s}", ring_strip(2, 20, lambda r, c, zc=zc, f=shaft: Vector((cx + (boot_rad(zc + (r - 0.5) * 0.03) + 0.008) * math.cos(2 * math.pi * c), boot_y(zc) + (boot_rad(zc) + 0.008) * math.sin(2 * math.pi * c) * 1.05, zc + (r - 0.5) * 0.03))), M_LEATHER, nearest_w(["LowerLeg." + s], 0.03))
    bm = bmesh.new()
    for zc in (0.56, 0.43, 0.30):
        ell(bm, (cx + side * (boot_rad(zc) + 0.012), boot_y(zc) + 0.002, zc), (0.004, 0.012, 0.014), seg=6, rings=4)
    attach(arm, "Hero_BootBuckles_" + s, bm, M_METAL, "LowerLeg." + s)
    # criss-cross laces and eyelets up the front
    bm = bmesh.new(); be = bmesh.new()
    prev = None
    for i, z in enumerate([0.585 - k * 0.032 for k in range(14)]):
        yy = boot_y(z) - boot_rad(z) * 1.05 - 0.003
        a = Vector((cx - 0.016, yy + 0.0, z)); b = Vector((cx + 0.016, yy, z - 0.026))
        a2 = Vector((cx + 0.016, yy, z)); b2 = Vector((cx - 0.016, yy, z - 0.026))
        tube(bm, a, b, 0.0035, 0.0035, seg=4); tube(bm, a2, b2, 0.0035, 0.0035, seg=4)
        for sx in (-1, 1): ell(be, (cx + sx * 0.019, yy + 0.002, z), (0.004, 0.003, 0.004), seg=5, rings=3)
    attach(arm, "Hero_BootLaces_" + s, bm, M_LACE, "LowerLeg." + s)
    attach(arm, "Hero_BootEyelets_" + s, be, M_METAL, "LowerLeg." + s)
    # foot: toe box, heel, sole + welt, toe cap
    bm = bmesh.new()
    ell(bm, (cx, -0.135, 0.052), (0.054, 0.108, 0.044), seg=14, rings=8)
    ell(bm, (cx, -0.046, 0.054), (0.049, 0.052, 0.052), seg=12, rings=7)
    attach(arm, "Hero_BootFoot_" + s, bm, M_BOOT, "Foot." + s)
    bm = bmesh.new()
    ell(bm, (cx, -0.108, 0.014), (0.060, 0.142, 0.016), seg=14, rings=5)
    ell(bm, (cx, -0.030, 0.026), (0.044, 0.042, 0.026), seg=8, rings=4)
    attach(arm, "Hero_BootSole_" + s, bm, M_DARK, "Foot." + s)
    bm = bmesh.new()
    ell(bm, (cx, -0.200, 0.046), (0.036, 0.034, 0.030), seg=10, rings=6)
    for i in range(3): ell(bm, (cx, -0.098 - i * 0.0, 0.030 + i * 0.0), (0.0, 0.0, 0.0), seg=3, rings=2)
    attach(arm, "Hero_BootToe_" + s, bm, M_LEATHER, "Foot." + s)

# ---------- forearm wraps (leather bracers) ----------
for side, s in ((1, "L"), (-1, "R")):
    sk = bmesh.new()
    skinned(arm, "Hero_Wrap_" + s, sleeve(side, 0.47, 0.545, 0.0045, 0.004, rings=6, sides=14, fold=0.001, seed=4), M_LEATHER, arm_w_full(side))

# Reduce internal dense curved details to the production hero budget; preserve rig weights.
for o in list(bpy.data.objects):
    if o.type == 'MESH' and o.name.startswith('Hero_') and len(o.data.polygons) > 220:
        bpy.context.view_layer.objects.active = o
        mod = o.modifiers.new("DetailBudget", 'DECIMATE'); mod.ratio = 0.76
        bpy.ops.object.modifier_apply(modifier=mod.name)
finish(OUT, "ashenborn")
