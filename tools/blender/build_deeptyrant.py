"""Deep-Tyrant hero: cephalopod-headed abyssal scholar on the primal shared-skeleton base (Blender 5.x).
Run: blender -b -P build_deeptyrant.py -- <primal.glb> <out_dir>
Mauve mantle-dome head with bioluminescent spots, amber eyes, face + shoulder tentacles with suction cups (UV'd tubes), bone-white shell-plate armour
(pauldrons, back cape, gorget), layered dark-teal scholar robe with embroidered panels, belts, pouches, book, scrolls, armillary orb, strapped boots."""
import bpy, bmesh, math, sys, os, random
import numpy as np
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hero_common import *
import hero_textures as T

SRC, OUT = sys.argv[-2], sys.argv[-1]
random.seed(41)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
remove_objects("_Head", "_Feet")
TEX = os.path.join(OUT, "tex_dt")


def rgba(col):
    return np.concatenate([col, np.ones(col.shape[:2] + (1,), np.float32)], -1)


MAUVE = np.array([0.36, 0.22, 0.30], np.float32); BONE = np.array([0.72, 0.66, 0.52], np.float32); TEAL = np.array([0.06, 0.15, 0.17], np.float32)
CYAN = np.array([0.2, 0.9, 0.95], np.float32)


def skin_tex():
    n = 512; x, y = T._grid(n); nz = T.fbm(n, 2, 5, 6); fine = T.fbm(n, 3, 3, 30)
    col = MAUVE[None, None, :] * (0.7 + 0.6 * nz[..., None]) * (0.9 + 0.2 * fine[..., None]) + np.stack([0.05 * nz, 0.0 * nz, 0.05 * nz], -1)
    rng = np.random.default_rng(5); sp = np.zeros((n, n), np.float32)
    sp[rng.integers(0, n, 700), rng.integers(0, n, 700)] = rng.random(700)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1)):
        sp += 0.5 * np.roll(np.roll(sp, dx, 1), dy, 0)
    sp = np.clip(sp * 1.5, 0, 1)
    col = col + sp[..., None] * CYAN[None, None, :] * 0.3
    emis = rgba(sp[..., None] * CYAN[None, None, :] * 1.0)
    return (T.to_image("skin_diffuse", rgba(np.clip(col, 0, 1)), TEX), T.to_image("skin_normal", T.normal_from_height(fine * 0.6 + nz * 0.5, 1.4), TEX, "Non-Color"),
            T.to_image("skin_emission", emis, TEX))


def tent_tex():
    n = 256; x, y = T._grid(n); nz = T.fbm(n, 6, 4, 6)
    col = np.array([0.55, 0.36, 0.42], np.float32)[None, None, :] * (0.7 + 0.5 * nz[..., None])
    col = col * (0.75 + 0.5 * (1 - np.abs(x - 0.5) * 2)[..., None] * 0.0 + 0.0)
    fx, fy = x, (y * 14) % 1.0
    d = np.hypot((fx - 0.5) * 2.2, (fy - 0.5) * 1.0)
    band = np.abs(x - 0.5) < 0.22
    cup = band & (d < 0.42)
    rim = band & (np.abs(d - 0.42) < 0.07)
    col = np.where(cup[..., None], np.array([0.78, 0.55, 0.58], np.float32)[None, None, :] * (0.8 + 0.3 * (d[..., None] / 0.42)), col)
    col = np.where((np.abs(d - 0.17) < 0.05)[..., None] & band[..., None], np.array([0.30, 0.12, 0.16], np.float32)[None, None, :], col)
    h = 0.7 * rim + 0.3 * nz - 0.4 * (cup & (d < 0.18))
    return T.to_image("tent_diffuse", rgba(np.clip(col, 0, 1)), TEX), T.to_image("tent_normal", T.normal_from_height(h, 2.0), TEX, "Non-Color")


def shell_tex():
    n = 512; x, y = T._grid(n); nz = T.fbm(n, 7, 5, 6)
    ridge = 0.5 + 0.5 * np.sin((np.abs(x - 0.5) * 2 * 6 + y * 4 + nz * 1.5) * np.pi)
    col = BONE[None, None, :] * (0.65 + 0.35 * ridge[..., None]) * (0.8 + 0.4 * nz[..., None])
    col = col * (1 - 0.35 * T.smooth(0.6, 1.0, y)[..., None]) + np.array([0.04, 0.07, 0.07], np.float32)[None, None, :] * T.smooth(0.7, 1.0, 1 - nz)[..., None]
    return T.to_image("shell_diffuse", rgba(np.clip(col, 0, 1)), TEX), T.to_image("shell_normal", T.normal_from_height(ridge * 0.9 + nz * 0.4, 2.0), TEX, "Non-Color")


def robe_tex():
    n = 1024; x, y = T._grid(n); nz = T.fbm(n, 9, 5, 6)
    weave = 0.5 + 0.5 * np.sin(x * n * 0.3) * np.sin(y * n * 0.3)
    col = TEAL[None, None, :] * (0.7 + 0.7 * nz[..., None]) * (0.88 + 0.12 * weave[..., None])
    gold = np.array([0.55, 0.46, 0.25], np.float32)
    swirl = np.abs(np.sin((x * 14 + np.sin(y * 18) * 0.5) * np.pi)) < 0.06
    border = (np.abs(x - 0.5) > 0.44) | (y > 0.96)
    k = ((swirl & (y > 0.55)) | border)[..., None] * 0.9
    col = col * (1 - k) + gold[None, None, :] * k * (0.7 + 0.3 * nz[..., None])
    col *= (1 - 0.4 * T.smooth(0.85, 1.0, y)[..., None])
    return T.to_image("robe_diffuse", rgba(np.clip(col, 0, 1)), TEX), T.to_image("robe_normal", T.normal_from_height(0.5 * weave + 0.4 * nz + k[..., 0] * 0.8, 1.2), TEX, "Non-Color")


def panel_tex():
    n = 512; x, y = T._grid(n); nz = T.fbm(n, 12, 5, 6)
    col = TEAL[None, None, :] * 1.4 * (0.7 + 0.6 * nz[..., None])
    gold = np.array([0.6, 0.5, 0.28], np.float32)
    d = np.hypot((x - 0.5) * 2, (y - 0.3) * 1.2)
    ang = np.arctan2(y - 0.3, x - 0.5)
    ring = (np.abs(d - 0.3) < 0.025) | (np.abs(d - 0.12) < 0.03) | ((d < 0.5) & (d > 0.3) & (np.abs(np.sin(ang * 8)) < 0.1))
    border = (np.abs(x - 0.5) > 0.44) | (y > 0.95)
    k = (ring | border)[..., None] * 0.9
    col = col * (1 - k) + gold[None, None, :] * k
    return T.to_image("panel_diffuse", rgba(np.clip(col, 0, 1)), TEX)


si, sn, se = skin_tex(); ti, tn = tent_tex(); shi, shn = shell_tex(); ri, rn = robe_tex(); pni = panel_tex()
M_SKIN = mat("DT_Skin", (0.36, 0.22, 0.30), 0.62, 0.0, emit=(0.2, 0.9, 0.95), strength=0.8); T.bind(M_SKIN, si, sn, se, 0.8)
M_TENT = mat("DT_Tentacle", (0.55, 0.36, 0.42), 0.3); T.bind(M_TENT, ti, tn)
M_SHELL = mat("DT_Shell", (0.72, 0.66, 0.52), 0.6); T.bind(M_SHELL, shi, shn)
M_ROBE = mat("DT_Robe", (0.06, 0.15, 0.17), 0.95); T.bind(M_ROBE, ri, rn)
M_PANEL = mat("DT_Panel", (0.06, 0.15, 0.17), 0.9); T.bind(M_PANEL, pni)
M_LEATH = mat("DT_Leather", (0.17, 0.10, 0.07), 0.55)
M_BRASS = mat("DT_Brass", (0.6, 0.45, 0.2), 0.3, 1.0)
M_PAPER = mat("DT_Scroll", (0.75, 0.68, 0.52), 0.8)
M_EYE = mat("DT_Eye", (0.8, 0.55, 0.1), 0.1, 0.0, emit=(0.9, 0.6, 0.1), strength=0.8)
M_PUP = mat("DT_Pupil", (0.01, 0.01, 0.01), 0.1)
M_ORB = mat("DT_Orb", (0.2, 0.8, 0.85), 0.1, 0.0, emit=(0.2, 0.9, 0.95), strength=3.0)

for _o in bpy.data.objects:
    if _o.type == "MESH" and _o.name.endswith(("_Body", "_Legs")):
        _o.data.materials.clear(); _o.data.materials.append(M_SKIN)
        for p in _o.data.polygons: p.material_index = 0
        me = _o.data
        for ul in list(me.uv_layers): me.uv_layers.remove(ul)
        ul = me.uv_layers.new(name="UVMap"); mw = _o.matrix_world
        for poly in me.polygons:
            for li in poly.loop_indices:
                w = mw @ me.vertices[me.loops[li].vertex_index].co
                ul.data[li].uv = (abs(math.atan2(w.x, -w.y)) / math.pi * 1.0, w.z * 1.0)


# ---------- helpers ----------
def card(bm, uvm, root, direction, length, width, curl=0.2, rows=4, tipw=1.8):
    d = Vector(direction).normalized(); up = Vector((0, 0, 1))
    side = d.cross(up)
    if side.length < 1e-3: side = Vector((1, 0, 0))
    side.normalize(); nrm = side.cross(d).normalized()
    vs = []
    for r in range(rows):
        t = r / (rows - 1)
        pos = Vector(root) + d * length * t + nrm * (curl * length * t * t)
        w = width * math.sin(min(1.0, 0.35 + t * 0.9) * math.pi / 2) * (1 - t ** tipw)
        row = []
        for c in range(3):
            v = bm.verts.new(pos + side * ((c - 1) * w) + nrm * (abs(c - 1) * w * 0.3))
            uvm[v] = (c / 2.0, 1.0 - t); row.append(v)
        vs.append(row)
    for r in range(rows - 1):
        for c in range(2):
            try: bm.faces.new((vs[r][c], vs[r][c + 1], vs[r + 1][c + 1], vs[r + 1][c]))
            except ValueError: pass


def tentacle(pts, r0, r1, cols=7):
    """UV'd tapered tube following a polyline; u around, v along (suction cups on the underside band)."""
    n = len(pts)
    def fn(r, c):
        i = min(int(r * (n - 1)), n - 2); f = r * (n - 1) - i
        p = pts[i] * (1 - f) + pts[i + 1] * f
        tan = (pts[i + 1] - pts[i]).normalized()
        a1 = tan.cross(Vector((0, 1, 0)) if abs(tan.y) < 0.9 else Vector((1, 0, 0))).normalized(); a2 = tan.cross(a1)
        rad = r0 + (r1 - r0) * r
        ang = 2 * math.pi * c * (cols - 1) / cols if False else 2 * math.pi * c
        return p + (a1 * math.cos(ang) + a2 * math.sin(ang)) * rad
    return strip(n * 2, cols + 1, fn)


def curve(p0, p1, droop, sway, n=6, wig=0.0):
    p0, p1 = Vector(p0), Vector(p1); out = []
    for i in range(n):
        t = i / (n - 1)
        q = p0 + (p1 - p0) * t + Vector((sway * math.sin(t * math.pi), 0, 0)) + Vector((0, -droop * math.sin(t * math.pi), 0))
        q += Vector((wig * math.sin(t * 9 + droop * 20), wig * math.cos(t * 7), 0)) * t
        out.append(q)
    return out


def tw(co):
    ch = smoothstep(1.18, 1.32, co.z); tq = smoothstep(1.02, 1.1, co.z) * (1 - ch)
    return {"Chest": ch, "Torso": tq, "Hips": max(0.0, 1.0 - ch - tq)}


def skw(co):
    t = smoothstep(1.0, 0.4, co.z)
    front = max(0.0, -co.y / max(1e-6, math.hypot(co.x, co.y)))
    wl = t * (0.3 + 0.6 * front)
    return {"Hips": 1.0 - wl, ("UpperLeg.L" if co.x >= 0 else "UpperLeg.R"): wl}


# ---------- head ----------
bm = bmesh.new()
ell(bm, (0, 0.0, 1.72), (0.150, 0.185, 0.125), rot=(math.radians(-18), 0, 0), seg=22, rings=14)     # mantle dome swept back
ell(bm, (0, -0.075, 1.615), (0.085, 0.085, 0.085), seg=14, rings=9)                                    # face mass
ell(bm, (0, -0.12, 1.57), (0.05, 0.05, 0.05), seg=10, rings=7)                                         # mouth cluster
ell(bm, (0, -0.04, 1.52), (0.06, 0.06, 0.07), seg=10, rings=6)                                         # neck
for sx in (1, -1):
    ell(bm, (sx * 0.075, -0.115, 1.655), (0.034, 0.03, 0.026), seg=10, rings=6)                       # brow bulge
attach(arm, "Hero_Mantle", bm, M_SKIN, "Head")
bm = bmesh.new()
for sx in (1, -1):
    ell(bm, (sx * 0.083, -0.145, 1.640), (0.0195, 0.014, 0.0165), seg=10, rings=6)
attach(arm, "Hero_Eyes", bm, M_EYE, "Head")
bm = bmesh.new()
for sx in (1, -1):
    ell(bm, (sx * 0.0855, -0.157, 1.640), (0.0095, 0.006, 0.0150), seg=6, rings=4)                    # horizontal-ish slit pupil
    ell(bm, (sx * 0.083, -0.140, 1.653), (0.026, 0.017, 0.012), seg=8, rings=5)                       # heavy upper lid
attach(arm, "Hero_Lids", bm, M_SKIN, "Head")
bm = bmesh.new()
for k in range(8):                                                                                    # face tentacles hanging over the chest
    a = math.radians(-70 + k * 20)
    root = Vector((0.07 * math.sin(a), -0.15 - 0.03 * abs(math.cos(a)), 1.575))
    tip = Vector((0.12 * math.sin(a) * 1.4, -0.22 - 0.05 * (k % 2), 1.28 - 0.06 * (k % 3)))
    pts = curve(root, tip, 0.05 + 0.02 * (k % 3), 0.01 * math.sin(a), n=6, wig=0.025)
    bmx = tentacle(pts, 0.017, 0.004)
    me = bpy.data.meshes.new("t%d" % k); bmx.to_mesh(me); bmx.free()
    o = bpy.data.objects.new("Hero_FaceTentacle_%d" % k, me); bpy.context.scene.collection.objects.link(o)
    me.materials.append(M_TENT)
    for p_ in me.polygons: p_.use_smooth = True
    o.parent = arm; o.parent_type = 'BONE'; o.parent_bone = "Head"
    b = arm.data.bones["Head"]
    o.matrix_parent_inverse = (arm.matrix_world @ b.matrix_local @ Matrix.Translation((0, b.length, 0))).inverted()
bm.free()
for sx, tag in ((1, "L"), (-1, "R")):                                                                  # shoulder tentacles draping chest/back
    for j, (dy, ln) in enumerate(((-0.12, 0.36), (-0.02, 0.34), (0.09, 0.40))):
        root = Vector((sx * 0.07, -0.04 + dy * 0.2, 1.58)); tip = Vector((sx * 0.20, -0.04 + dy, 1.28 - 0.03 * j))
        pts = curve(root, tip, 0.06, sx * 0.02, n=6, wig=0.02)
        bmx = tentacle(pts, 0.022, 0.005)
        me = bpy.data.meshes.new("st"); bmx.to_mesh(me); bmx.free()
        o = bpy.data.objects.new("Hero_ShoulderTentacle_%s%d" % (tag, j), me); bpy.context.scene.collection.objects.link(o)
        me.materials.append(M_TENT)
        for p_ in me.polygons: p_.use_smooth = True
        o.parent = arm; o.parent_type = 'BONE'; o.parent_bone = "Neck"
        b = arm.data.bones["Neck"]
        o.matrix_parent_inverse = (arm.matrix_world @ b.matrix_local @ Matrix.Translation((0, b.length, 0))).inverted()

# ---------- torso robe, shell armour, sleeves ----------
def tunic(r, c):
    a = 2 * math.pi * c; z = 1.47 - r * 0.52
    return Vector(((0.172 + 0.02 * r) * math.sin(a), -0.043 - (0.142 + 0.02 * r) * math.cos(a), z))
skinned(arm, "Hero_Tunic", strip(8, 30, tunic), M_ROBE, tw)

def robe_pt(r0, r1, zhem, ph, rag):
    def fn(r, c):
        a = math.radians(8 + c * 344)
        saw = (math.sin(c * 40 + ph) * 0.5 + 0.5) ** 2
        z = 1.05 + r * (zhem - 1.05) - (max(0.0, r - 0.75) / 0.25) * rag * saw
        rad = r0 + (r1 - r0) * (r ** 1.3) + 0.01 * math.sin(c * 28 + ph) * r
        return Vector((rad * math.sin(a), -0.04 - rad * math.cos(a), z))
    return fn
skinned(arm, "Hero_RobeUnder", strip(14, 56, robe_pt(0.20, 0.30, 0.18, 0.0, 0.05)), M_ROBE, skw)
skinned(arm, "Hero_RobeMid", strip(14, 56, robe_pt(0.215, 0.32, 0.27, 1.9, 0.07)), M_ROBE, skw)
skinned(arm, "Hero_RobeOuter", strip(14, 56, robe_pt(0.23, 0.34, 0.38, 3.3, 0.08)), M_ROBE, skw)
def tab(zt, zb, w, off, tipv):
    def fn(r, c):
        ww = w * (1 - (max(0.0, r - 0.8) / 0.2) * 0.9 if tipv else 1.0)
        return Vector(((c - 0.5) * 2 * ww, -0.04 - (0.30 - 0.1 * (1 - r)) * off - 0.012, zt + r * (zb - zt)))
    return fn
skinned(arm, "Hero_TabardFront", strip(10, 3, tab(1.03, 0.30, 0.11, 1.0, True)), M_PANEL, skw)
def tab_back(r, c):
    return Vector(((c - 0.5) * 2 * 0.12, 0.04 + 0.3 - 0.1 * (1 - r) + 0.012 - 0.02, 1.03 + r * (0.28 - 1.03)))
skinned(arm, "Hero_TabardBack", strip(10, 3, tab_back), M_PANEL, skw)

for side, tag, up, lo in ((1, "L", "UpperArm.L", "LowerArm.L"), (-1, "R", "UpperArm.R", "LowerArm.R")):
    def sleeve(r, c, side=side):
        a = 2 * math.pi * c; x = 0.15 + r * 0.38
        rad = 0.066 + 0.05 * r * r
        sag = 0.06 * r * r * (0.5 + 0.5 * math.cos(a - math.pi))
        rag = 0.025 * abs(math.sin(c * 17)) * r ** 3 if r > 0.9 else 0.0
        return Vector((side * (x - rag), -0.065 + rad * math.sin(a) * 0.95, 1.432 + rad * math.cos(a) - sag))
    def sw(co, up=up, lo=lo):
        t = smoothstep(0.26, 0.36, abs(co.x)); return {up: 1.0 - t, lo: t}
    skinned(arm, "Hero_Sleeve_" + tag, strip(10, 16, sleeve), M_ROBE, sw)
    bm = bmesh.new(); uv = {}                                                                # shell pauldron plates
    for layer, (x0, z0, ln, wd) in enumerate(((0.10, 1.52, 0.12, 0.06), (0.14, 1.52, 0.14, 0.065), (0.19, 1.51, 0.16, 0.07), (0.25, 1.50, 0.16, 0.07), (0.31, 1.485, 0.15, 0.065))):
        for k in range(5):
            yy = -0.06 + (k - 2) * 0.04
            card(bm, uv, Vector((side * x0, yy, z0)), (side * 0.7, 0.05 * (k - 2), -0.7), ln, wd * 1.5, curl=0.15, tipw=3.0)
    assign_uv(bm, uv); attach(arm, "Hero_Pauldron_" + tag, bm, M_SHELL, up)
    bm = bmesh.new(); uv = {}                                                                # shell cuffs on forearm
    for i in range(4):
        x = side * (0.44 + i * 0.04)
        for k in range(8):
            a = 2 * math.pi * k / 8
            card(bm, uv, Vector((x, -0.08 + 0.055 * math.sin(a), 1.43 + 0.055 * math.cos(a))), (side * 1.0, 0.3 * math.sin(a), 0.3 * math.cos(a)), 0.065, 0.045, tipw=3.0)
    assign_uv(bm, uv); attach(arm, "Hero_ForearmShell_" + tag, bm, M_SHELL, lo)

bm = bmesh.new(); uv = {}                                                                    # back cape of layered shell scales + gorget
for i in range(7):
    z = 1.46 - i * 0.07; n = 7 - (i // 3)
    for k in range(n):
        a = math.radians(-100 + k * 200 / (n - 1))
        rr = 0.19 + 0.012 * i
        card(bm, uv, Vector((rr * math.sin(a) * 1.15, 0.0 + rr * 0.9 * math.cos(a) + 0.04, z)), (math.sin(a) * 0.3, 0.25, -1), 0.12 + 0.008 * i, 0.12, curl=0.1, tipw=3.0)
assign_uv(bm, uv); skinned(arm, "Hero_ShellCape", bm, M_SHELL, tw)
bm = bmesh.new(); uv = {}
for i in range(3):
    for k in range(9):
        a = math.radians(-120 + k * 30)
        card(bm, uv, Vector((0.13 * math.sin(a) * 1.1, -0.043 - 0.11 * math.cos(a), 1.50 - 0.04 * i)), (math.sin(a) * 0.3, -math.cos(a) * 0.4, -1), 0.10, 0.045, tipw=1.4)
assign_uv(bm, uv); skinned(arm, "Hero_Gorget", bm, M_SHELL, tw)
bm = bmesh.new(); uv = {}                                                                    # front chest shell plates
for i, (z, n) in enumerate(((1.26, 5), (1.19, 4), (1.12, 3))):
    for k in range(n):
        x = (k - (n - 1) / 2) * 0.055
        card(bm, uv, Vector((x, -0.205 - 0.01 * i, z)), (x * 1.2, -0.3, -1), 0.10, 0.05, tipw=1.3)
assign_uv(bm, uv); skinned(arm, "Hero_ChestPlates", bm, M_SHELL, tw)

# ---------- belts, pouches, book, scrolls, orb ----------
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=26, radius1=0.226, radius2=0.220, depth=0.045, matrix=Matrix.Translation((0, -0.043, 1.06)))
bmesh.ops.create_cone(bm, cap_ends=True, segments=26, radius1=0.222, radius2=0.216, depth=0.03, matrix=Matrix.Translation((0, -0.043, 0.99)))
attach(arm, "Hero_Belts", bm, M_LEATH, "Hips")
bm = bmesh.new()
for z in (1.06, 0.99):
    bm2 = None
    ell(bm, (0, -0.267, z), (0.026, 0.008, 0.02), seg=6, rings=4)
for sx in (1, -1):                                                                           # chest harness buckles
    ell(bm, (sx * 0.08, -0.215, 1.22), (0.018, 0.006, 0.014), seg=6, rings=4)
attach(arm, "Hero_Buckles", bm, M_BRASS, "Hips")
bm = bmesh.new()
for sx in (1, -1):                                                                           # harness straps from shoulders to belt
    for i in range(10):
        t0, t1 = i / 10, (i + 1) / 10
        p0 = Vector((sx * (0.10 - 0.04 * t0), -0.19 - 0.02 * t0, 1.44 - 0.38 * t0)); p1 = Vector((sx * (0.10 - 0.04 * t1), -0.19 - 0.02 * t1, 1.44 - 0.38 * t1))
        tube(bm, p0, p1, 0.011, 0.011, seg=4)
attach(arm, "Hero_Harness", bm, M_LEATH, "Chest")
bm = bmesh.new()                                                                             # book on right hip, pouch on left, scroll bundles
def box(bm, c, s):
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation(Vector(c)) @ Matrix.Diagonal((*s, 1.0)))
box(bm, (-0.26, -0.06, 0.90), (0.05, 0.16, 0.20))
attach(arm, "Hero_Book", bm, M_LEATH, "Hips")
bm = bmesh.new()
box(bm, (-0.262, -0.055, 0.91), (0.046, 0.14, 0.17))
for z in (0.97, 0.84):
    tube(bm, (-0.285, -0.14, z), (-0.285, 0.02, z), 0.004, 0.004, seg=4)
attach(arm, "Hero_BookClasp", bm, M_BRASS, "Hips")
bm = bmesh.new()
box(bm, (0.27, -0.08, 0.92), (0.07, 0.14, 0.15))
attach(arm, "Hero_Pouch", bm, M_LEATH, "Hips")
bm = bmesh.new()
for k in range(3):
    tube(bm, (0.25 + 0.02 * k, -0.2 + 0.04 * k, 0.78), (0.25 + 0.02 * k, -0.2 + 0.04 * k, 1.0), 0.02, 0.02, seg=7)
attach(arm, "Hero_Scrolls", bm, M_PAPER, "Hips")
bm = bmesh.new()
for k in range(3):
    for z in (0.82, 0.96):
        tube(bm, (0.25 + 0.02 * k, -0.2 + 0.04 * k, z), (0.25 + 0.02 * k, -0.2 + 0.04 * k, z + 0.012), 0.024, 0.024, seg=7)
attach(arm, "Hero_ScrollBands", bm, M_LEATH, "Hips")
bm = bmesh.new()                                                                             # armillary orb pendant on the chest
tube(bm, (0, -0.19, 1.50), (0, -0.215, 1.32), 0.004, 0.004, seg=4)
for k in range(8):
    a0, a1 = 2 * math.pi * k / 8, 2 * math.pi * (k + 1) / 8
    tube(bm, (0.03 * math.cos(a0), -0.222 - 0.0, 1.30 + 0.03 * math.sin(a0)), (0.03 * math.cos(a1), -0.222, 1.30 + 0.03 * math.sin(a1)), 0.003, 0.003, seg=4)
    tube(bm, (0.03 * math.cos(a0), -0.222 + 0.03 * math.sin(a0), 1.30), (0.03 * math.cos(a1), -0.222 + 0.03 * math.sin(a1), 1.30), 0.003, 0.003, seg=4)
attach(arm, "Hero_OrbCage", bm, M_BRASS, "Chest")
bm = bmesh.new(); ell(bm, (0, -0.222, 1.30), (0.02, 0.02, 0.02), seg=8, rings=5)
attach(arm, "Hero_Orb", bm, M_ORB, "Chest")

# ---------- boots (both sides) ----------
for side, foot, tag in ((1, "Foot.L", "L"), (-1, "Foot.R", "R")):
    cx = side * 0.12
    def boot(r, c, cx=cx):
        a = 2 * math.pi * c; z = 0.04 + r * 0.38; rad = 0.058 - 0.004 * r + 0.01 * math.sin(r * 12)
        return Vector((cx + rad * math.cos(a), -0.075 + rad * math.sin(a), z))
    skinned(arm, "Hero_BootShaft_" + tag, strip(10, 12, boot), M_LEATH, lambda co, tg=tag: {("LowerLeg." + tg): 1.0})
    bm = bmesh.new()
    ell(bm, (cx, -0.12, 0.04), (0.062, 0.12, 0.04), seg=12, rings=6)                       # foot
    ell(bm, (cx, -0.07, 0.07), (0.064, 0.06, 0.05), seg=10, rings=5)                         # ankle
    ell(bm, (cx, -0.205, 0.035), (0.052, 0.05, 0.03), seg=10, rings=5)                       # toe cap
    ell(bm, (cx, 0.0, 0.02), (0.05, 0.045, 0.025), seg=8, rings=4)                           # heel
    attach(arm, "Hero_BootFoot_" + tag, bm, M_LEATH, foot)
    bm = bmesh.new()
    for z in (0.12, 0.22, 0.32):                                                              # straps with brass buckles
        for k in range(14):
            a0, a1 = 2 * math.pi * k / 14, 2 * math.pi * (k + 1) / 14
            tube(bm, (cx + 0.064 * math.cos(a0), -0.075 + 0.064 * math.sin(a0), z), (cx + 0.064 * math.cos(a1), -0.075 + 0.064 * math.sin(a1), z), 0.006, 0.006, seg=4)
        ell(bm, (cx, -0.139, z), (0.012, 0.005, 0.012), seg=5, rings=3)
    attach(arm, "Hero_BootStraps_" + tag, bm, M_BRASS, "LowerLeg." + tag)

print("DT_TOTAL_TRIS", tri_count())
bpy.ops.wm.save_as_mainfile(filepath=OUT + "/deeptyrant.blend")
bpy.ops.export_scene.gltf(filepath=OUT + "/deeptyrant.glb", export_format='GLB', export_apply=True,
                          export_animations=False, export_skins=True)
print("DT_DONE")
