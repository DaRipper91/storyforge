"""Iron-Locust hero: six-legged iron-shelled insect, own skeleton + Idle/Walk/Hit/Death clips (Blender 5.x).
Run: blender -b -P build_ironlocust.py -- <out_dir>
Front is -Y, feet on z=0, ~1.0 long x ~0.75 high. Parts are bone-parented (rigid) to a 25-bone armature.
Detail pass: baked iron/rust plate textures with box-projected UVs, segmented overlapping plates, domed ribbed elytra, ball-joint legs with
pistons and serrated tibiae, faceted compound eyes, serrated mandible shears, mining-processor forelimbs (hazard stripes, toothed drum, hose)."""
import bpy, bmesh, math, sys, os, random
import numpy as np
from mathutils import Vector, Matrix, Euler
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hero_textures as T

OUT = sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.fps = 30

random.seed(12)
TEX = os.path.join(OUT, "tex_il")

def mat(name, rgb, rough=0.5, metal=0.0, emit=None, strength=2.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = strength
    m.use_backface_culling = False
    return m

def shell_tex():
    n = 512; x, y = T._grid(n)
    nz = T.fbm(n, 5, 5, 6); nz2 = T.fbm(n, 15, 4, 14)
    e, cid = T.voronoi(n, 5, 7)
    edge = 1 - T.smooth(0.0, 0.07, e)
    iron = np.array([0.30, 0.26, 0.24], np.float32); rust = np.array([0.52, 0.27, 0.11], np.float32)
    rmask = T.smooth(0.58, 0.85, nz) * (0.5 + 0.4 * nz2)
    col = iron[None, None, :] * (0.7 + 0.5 * cid[..., None] * 0.6 + 0.4 * nz2[..., None])
    col = col * (1 - rmask[..., None]) + rust[None, None, :] * (0.6 + 0.6 * nz2[..., None]) * rmask[..., None]
    scr = (np.abs(((x * 3 + y * 11 + nz * 0.5) % 1.0) - 0.5) < 0.006) * T.smooth(0.4, 0.7, nz2)
    col = col * (1 - 0.35 * edge[..., None]) + scr[..., None] * 0.18
    h = 0.4 * nz + 0.25 * nz2 - 0.9 * edge + 0.2 * rmask
    return (T.to_image("shell_diffuse", np.concatenate([col, np.ones((n, n, 1), np.float32)], -1), TEX),
            T.to_image("shell_normal", T.normal_from_height(h, 1.4), TEX, "Non-Color"))

def metal_tex():
    n = 256; x, y = T._grid(n)
    nz = T.fbm(n, 21, 5, 8)
    col = np.array([0.16, 0.15, 0.15], np.float32)[None, None, :] * (0.6 + 0.8 * nz[..., None])
    wear = T.smooth(0.65, 0.9, T.fbm(n, 22, 4, 12))
    col = col + wear[..., None] * np.array([0.22, 0.2, 0.18], np.float32)
    return (T.to_image("metal_diffuse", np.concatenate([col, np.ones((n, n, 1), np.float32)], -1), TEX),
            T.to_image("metal_normal", T.normal_from_height(nz * 0.6 + wear * 0.3, 1.0), TEX, "Non-Color"))

def hazard_tex():
    n = 256; x, y = T._grid(n)
    nz = T.fbm(n, 31, 5, 8)
    stripe = (((x + y) * 6) % 1.0) < 0.5
    yel = np.array([0.82, 0.62, 0.08], np.float32); blk = np.array([0.06, 0.055, 0.05], np.float32)
    col = np.where(stripe[..., None], yel[None, None, :], blk[None, None, :]) * (0.7 + 0.5 * nz[..., None])
    chip = T.smooth(0.62, 0.8, T.fbm(n, 32, 4, 10))                   # worn / chipped paint
    col = col * (1 - 0.7 * chip[..., None]) + chip[..., None] * np.array([0.22, 0.2, 0.18], np.float32) * 0.7
    return (T.to_image("hazard_diffuse", np.concatenate([col, np.ones((n, n, 1), np.float32)], -1), TEX),
            T.to_image("hazard_normal", T.normal_from_height(nz * 0.4 + chip * 0.5, 1.0), TEX, "Non-Color"))

def eye_tex():
    n = 256
    e, cid = T.voronoi(n, 16, 9)
    facet = T.smooth(0.0, 0.25, e)
    col = np.stack([0.32 + 0.4 * cid, 0.06 + 0.1 * cid, 0.03 + 0.03 * cid], -1) * (0.3 + 0.9 * facet[..., None])
    em = np.stack([0.9 * facet * (0.6 + 0.4 * cid), 0.22 * facet, 0.06 * facet, np.ones((n, n), np.float32)], -1)
    return (T.to_image("eye_diffuse", np.concatenate([col, np.ones((n, n, 1), np.float32)], -1), TEX),
            T.to_image("eye_normal", T.normal_from_height(facet, 1.6), TEX, "Non-Color"),
            T.to_image("eye_emission", em, TEX))

sh_i, sh_n = shell_tex(); mt_i, mt_n = metal_tex(); hz_i, hz_n = hazard_tex(); ey_i, ey_n, ey_e = eye_tex()
M_SHELL = mat("IL_Shell", (0.30, 0.26, 0.24), 0.42, 0.7)
M_RUST  = mat("IL_Rust",  (0.40, 0.20, 0.09), 0.7, 0.5)
M_JOINT = mat("IL_Joint", (0.16, 0.15, 0.15), 0.5, 0.8)
M_EYE   = mat("IL_Eye",   (0.35, 0.08, 0.04), 0.2, 0.0, emit=(0.9, 0.25, 0.08), strength=1.0)
M_CLAW  = mat("IL_Claw",  (0.38, 0.36, 0.33), 0.5, 0.3)
M_HAZ   = mat("IL_Hazard", (0.8, 0.6, 0.1), 0.55, 0.3)
M_HOSE  = mat("IL_Hose",  (0.03, 0.03, 0.03), 0.6, 0.1)
M_PIST  = mat("IL_Piston", (0.42, 0.40, 0.38), 0.45, 0.3)
T.bind(M_SHELL, sh_i, sh_n); T.bind(M_JOINT, mt_i, mt_n); T.bind(M_HAZ, hz_i, hz_n); T.bind(M_EYE, ey_i, ey_n, ey_e, 1.0)
T.bind(M_RUST, sh_i, sh_n)

# ---------- skeleton ----------
arm_data = bpy.data.armatures.new("LocustArmature")
arm = bpy.data.objects.new("LocustArmature", arm_data); sc.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
E = arm_data.edit_bones
def bone(name, head, tail, parent=None):
    b = E.new(name); b.head = Vector(head); b.tail = Vector(tail)
    if parent: b.parent = E[parent]
    return b
bone("Root", (0, 0, 0), (0, 0, 0.12))
bone("Body", (0, 0.0, 0.46), (0, -0.2, 0.5), "Root")
bone("Abdomen", (0, 0.2, 0.46), (0, 0.6, 0.44), "Body")
bone("Head", (0, -0.3, 0.50), (0, -0.5, 0.50), "Body")
for s, sx in (("L", 1), ("R", -1)):
    bone(f"Antenna.{s}", (sx * 0.05, -0.46, 0.58), (sx * 0.14, -0.66, 0.92), "Head")
    bone(f"Mandible.{s}", (sx * 0.05, -0.50, 0.44), (sx * 0.04, -0.62, 0.40), "Head")
    bone(f"Elytra.{s}", (sx * 0.06, -0.05, 0.66), (sx * 0.15, 0.55, 0.52), "Body")
    bone(f"Arm.{s}", (sx * 0.12, -0.34, 0.38), (sx * 0.14, -0.55, 0.28), "Body")
    bone(f"Claw.{s}", (sx * 0.14, -0.55, 0.28), (sx * 0.14, -0.70, 0.30), f"Arm.{s}")
    for i, (ly, kx, kz, fx, fy) in enumerate(((-0.22, 0.42, 0.62, 0.60, -0.38), (-0.04, 0.46, 0.66, 0.66, -0.08), (0.16, 0.42, 0.62, 0.62, 0.26))):
        hip = (sx * 0.17, ly, 0.42)
        knee = (sx * kx, ly + (fy - ly) * 0.35, kz)
        foot = (sx * fx, fy, 0.02)
        bone(f"Leg{i+1}.{s}.Upper", hip, knee, "Body")
        bone(f"Leg{i+1}.{s}.Lower", knee, foot, f"Leg{i+1}.{s}.Upper")
bpy.ops.object.mode_set(mode='OBJECT')

# ---------- geometry helpers ----------
def uvproject(bm, scale=4.5):
    layer = bm.loops.layers.uv.get("UVMap") or bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        nrm = f.normal if f.normal.length > 0 else Vector((0, 0, 1))
        ax = max(range(3), key=lambda i: abs(nrm[i]))
        i1, i2 = [i for i in range(3) if i != ax]
        for lp in f.loops:
            lp[layer].uv = (lp.vert.co[i1] * scale, lp.vert.co[i2] * scale)

def attach(name, bm, material, bone_name, smooth=True, uv=True):
    if uv and material in (M_SHELL, M_RUST, M_JOINT):
        bm.normal_update(); uvproject(bm)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); sc.collection.objects.link(o)
    me.materials.append(material)
    for p in me.polygons: p.use_smooth = smooth
    o.parent = arm; o.parent_type = 'BONE'; o.parent_bone = bone_name
    o.matrix_parent_inverse = (arm.matrix_world @ arm.data.bones[bone_name].matrix_local @ Matrix.Translation((0, arm.data.bones[bone_name].length, 0))).inverted()  # Blender parents bone children at the bone TAIL
    return o

def ell(bm, c, s, rot=(0, 0, 0), seg=10, rings=6):
    m = Matrix.Translation(Vector(c)) @ Matrix.LocRotScale(None, Euler(rot), Vector(s))
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0, matrix=m)

def cone(bm, base, direction, r, length, seg=5, r2=0.0):
    d = Vector(direction).normalized()
    m = Matrix.Translation(Vector(base) + d * length / 2) @ d.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r2, depth=length, matrix=m)

def tube(bm, p0, p1, r0, r1, seg=6):
    cone(bm, p0, Vector(p1) - Vector(p0), r0, (Vector(p1) - Vector(p0)).length, seg=seg, r2=r1)

def collar(bm, p, d, r, depth=0.025, seg=10):
    cone(bm, Vector(p) - Vector(d).normalized() * depth / 2, d, r, depth, seg=seg, r2=r)

def box(bm, c, size, rot=(0, 0, 0)):
    m = Matrix.Translation(Vector(c)) @ Matrix.LocRotScale(None, Euler(rot), Vector(size))
    bmesh.ops.create_cube(bm, size=1.0, matrix=m)

def chain(bm, pts, r0, r1, seg=5):
    n = len(pts) - 1
    for i in range(n):
        tube(bm, pts[i], pts[i + 1], r0 + (r1 - r0) * i / n, r0 + (r1 - r0) * (i + 1) / n, seg=seg)

# ---------- body: overlapping segmented plates ----------
bm = bmesh.new()
ell(bm, (0, -0.10, 0.50), (0.215, 0.31, 0.195), seg=16, rings=10)                        # thorax mass
ell(bm, (0, -0.27, 0.585), (0.19, 0.15, 0.095), rot=(math.radians(-18), 0, 0), seg=16, rings=8)    # pronotum shield
ell(bm, (0, -0.375, 0.545), (0.155, 0.07, 0.065), rot=(math.radians(-25), 0, 0), seg=12, rings=6)
for sx in (1, -1):
    ell(bm, (sx * 0.14, -0.30, 0.57), (0.07, 0.10, 0.06), rot=(math.radians(-14), 0, sx * math.radians(25)), seg=10, rings=6)   # pronotum side flare
for i in range(5):                                                                        # overlapping back plates
    ell(bm, (0, -0.19 + i * 0.095, 0.665 - 0.014 * i), (0.205 - 0.015 * i, 0.085, 0.075), rot=(math.radians(10), 0, 0), seg=14, rings=6)
    cone(bm, (0, -0.19 + i * 0.095, 0.72 - 0.014 * i), (0, -0.2, 1), 0.014, 0.045, seg=4)    # keel spike
    for sx in (1, -1):
        ell(bm, (sx * (0.185 - 0.01 * i), -0.20 + i * 0.105, 0.50), (0.05, 0.075, 0.10), rot=(0, 0, sx * math.radians(18)), seg=8, rings=5)   # flank plates
for i in range(4):
    ell(bm, (0, -0.24 + i * 0.09, 0.335), (0.13 - 0.01 * i, 0.065, 0.04), rot=(math.radians(8), 0, 0), seg=10, rings=5)      # sternum chevrons
attach("Hero_Thorax", bm, M_SHELL, "Body", smooth=True)

bm = bmesh.new()
for i in range(7):                                                                        # tapering abdomen segments
    ell(bm, (0, 0.13 + 0.075 * i, 0.46 - 0.006 * i), (0.25 - 0.024 * i, 0.085, 0.215 - 0.022 * i), seg=14, rings=8)
cone(bm, (0, 0.62, 0.43), (0, 1.0, -0.15), 0.06, 0.13, seg=6)                                # pointed tail plate
for sx in (1, -1):
    for i in range(6):
        ell(bm, (sx * (0.235 - 0.022 * i), 0.15 + 0.075 * i, 0.43), (0.04, 0.06, 0.055), seg=6, rings=4)    # spiracle plates
attach("Hero_Abdomen", bm, M_SHELL, "Abdomen", smooth=True)

# domed, ribbed wing cases (elytra) folded over the abdomen
for s, sx in (("L", 1), ("R", -1)):
    bm = bmesh.new()
    cx, cy, cz = sx * 0.125, 0.27, 0.635
    sxr, syr, szr = 0.185, 0.50, 0.19
    ell(bm, (cx, cy, cz), (sxr, syr, szr), rot=(math.radians(-9), 0, sx * math.radians(7)), seg=20, rings=12)
    def surf(u, y):
        q = 1 - (u / sxr) ** 2 - ((y - cy) / syr) ** 2
        return cz + szr * math.sqrt(max(q, 0.0))
    for rib in (-0.55, -0.15, 0.30, 0.65):
        pts = []
        for k in range(11):
            y = cy - 0.78 * syr + 1.56 * syr * k / 10
            u = sxr * rib * (1 - 0.4 * ((y - cy) / syr) ** 2)
            pts.append(Vector((cx + sx * u * 0.9, y, surf(u, y) + 0.004 - 0.07 * ((y - cy) / syr) ** 2 * 0.3)))
        chain(bm, pts, 0.007, 0.005, seg=4)
    for k in range(10):                                                                    # seam ridge down the inner edge
        y = cy - 0.82 * syr + 1.64 * syr * k / 9
        ell(bm, (sx * 0.015, y, surf(0.0, y) - 0.015), (0.012, 0.03, 0.01), seg=5, rings=3)
    attach(f"Hero_Elytra_{s}", bm, M_SHELL, f"Elytra.{s}", smooth=True)

bm = bmesh.new()                                                                           # rust staining patches on the shell
for (x, y, z, sz) in ((0.12, 0.05, 0.70, 0.05), (-0.10, 0.30, 0.68, 0.06), (0.05, 0.55, 0.62, 0.05), (-0.14, -0.20, 0.68, 0.04), (0.17, 0.36, 0.58, 0.05)):
    ell(bm, (x, y, z), (sz, sz * 1.4, sz * 0.30), seg=7, rings=3)
attach("Hero_Rust", bm, M_RUST, "Body", smooth=False)

# ---------- head: clypeus, cheeks, compound eyes, sockets, palps ----------
bm = bmesh.new()
ell(bm, (0, -0.42, 0.50), (0.13, 0.12, 0.11), seg=14, rings=8)
ell(bm, (0, -0.46, 0.585), (0.105, 0.07, 0.04), rot=(math.radians(-15), 0, 0), seg=10, rings=5)         # frons plate
cone(bm, (0, -0.50, 0.52), (0, -1, -0.45), 0.075, 0.11, seg=6, r2=0.02)                                  # clypeus wedge
for sx in (1, -1):
    ell(bm, (sx * 0.095, -0.465, 0.46), (0.045, 0.055, 0.05), seg=8, rings=5)                          # cheek plates
    collar(bm, (sx * 0.05, -0.48, 0.60), (sx * 0.3, -0.5, 1), 0.018, depth=0.02)                       # antenna sockets
    for k in range(3):
        cone(bm, (sx * (0.085 - 0.02 * k), -0.535 - 0.012 * k, 0.405 - 0.0 * k), (sx * -0.3, -0.5, -1), 0.012, 0.045, seg=4)   # labial palp stubs
attach("Hero_Head", bm, M_SHELL, "Head", smooth=True)
bm = bmesh.new()
for sx in (1, -1):
    ell(bm, (sx * 0.092, -0.465, 0.555), (0.044, 0.04, 0.05), rot=(0, 0, sx * math.radians(-12)), seg=14, rings=9)
attach("Hero_Eyes", bm, M_EYE, "Head")
bm = bmesh.new()
for sx in (1, -1):
    for k in range(2):
        collar(bm, (sx * 0.092, -0.465, 0.555), (sx * 1, -0.2, 0.5), 0.052 - 0.002 * k, depth=0.006 + 0.0 * k, seg=14)  # eye rims
attach("Hero_EyeRims", bm, M_JOINT, "Head")

# serrated mandible shears (curved, with inner teeth)
for s, sx in (("L", 1), ("R", -1)):
    bm = bmesh.new()
    P = [Vector((sx * 0.060, -0.500, 0.445)), Vector((sx * 0.082, -0.535, 0.432)), Vector((sx * 0.083, -0.575, 0.418)),
         Vector((sx * 0.066, -0.615, 0.405)), Vector((sx * 0.040, -0.640, 0.397)), Vector((sx * 0.018, -0.652, 0.395))]
    chain(bm, P, 0.032, 0.004, seg=6)
    ell(bm, P[0], (0.04, 0.04, 0.04), seg=8, rings=5)
    for k in range(1, 5):
        for off in (0.0, 0.4):
            q = P[k].lerp(P[k + 1], off)
            cone(bm, q + Vector((-sx * 0.012, 0, 0)), (-sx * 1, -0.2, 0.1), 0.0075, 0.024, seg=3)
    attach(f"Hero_Mandible_{s}", bm, M_CLAW, f"Mandible.{s}", smooth=True, uv=False)
    bm = bmesh.new()                                                                       # segmented antennae
    path = [Vector((sx * 0.05, -0.46, 0.58)), Vector((sx * 0.075, -0.52, 0.68)), Vector((sx * 0.10, -0.58, 0.78)),
            Vector((sx * 0.12, -0.62, 0.86)), Vector((sx * 0.14, -0.66, 0.92))]
    for a in range(len(path) - 1):
        for k in range(4):
            p0 = path[a].lerp(path[a + 1], k / 4); p1 = path[a].lerp(path[a + 1], (k + 0.85) / 4)
            r = 0.011 - 0.0022 * (a + k / 4)
            tube(bm, p0, p1, r, r * 0.85, seg=5)
            ell(bm, p1, (r * 1.25, r * 1.25, r * 1.25), seg=5, rings=3)
    attach(f"Hero_Antenna_{s}", bm, M_JOINT, f"Antenna.{s}", uv=False)

# ---------- mining-processor forelimbs ----------
for s, sx in (("L", 1), ("R", -1)):
    S = Vector((sx * 0.12, -0.34, 0.38)); E_ = Vector((sx * 0.14, -0.55, 0.28))
    bm = bmesh.new()
    ell(bm, S, (0.055, 0.055, 0.055), seg=10, rings=6); collar(bm, S, (0, -1, -0.3), 0.06, depth=0.02)
    tube(bm, S, E_, 0.036, 0.028, seg=8)
    ell(bm, E_, (0.046, 0.046, 0.046), seg=10, rings=6); collar(bm, E_ + Vector((0, 0.02, 0)), E_ - S, 0.048, depth=0.02)
    ell(bm, S.lerp(E_, 0.45) + Vector((sx * 0.012, 0, 0.03)), (0.045, 0.07, 0.03), seg=8, rings=5)              # upper-arm armour plate
    attach(f"Hero_Arm_{s}", bm, M_SHELL, f"Arm.{s}", smooth=True)
    bm = bmesh.new()                                                                       # hydraulic piston beside the arm
    a0 = S + Vector((sx * 0.05, 0.0, 0.03)); a1 = E_ + Vector((sx * 0.045, 0.01, 0.025))
    tube(bm, a0, a0.lerp(a1, 0.55), 0.012, 0.012, seg=6); tube(bm, a0.lerp(a1, 0.5), a1, 0.006, 0.006, seg=5)
    ell(bm, a0, (0.016, 0.016, 0.016), seg=6, rings=4); ell(bm, a1, (0.014, 0.014, 0.014), seg=6, rings=4)
    attach(f"Hero_ArmPiston_{s}", bm, M_PIST, f"Arm.{s}", uv=False)
    bm = bmesh.new()                                                                       # processor: forearm, housing, intake, toothed drum
    C = E_; tipc = Vector((sx * 0.14, -0.70, 0.30))
    tube(bm, C, C.lerp(tipc, 0.45), 0.030, 0.034, seg=8)
    hc = Vector((sx * 0.14, -0.745, 0.285))
    box(bm, hc, (0.095, 0.115, 0.075), rot=(math.radians(-6), 0, 0))
    box(bm, hc + Vector((0, 0.0, 0.05)), (0.085, 0.105, 0.012))
    box(bm, hc + Vector((0, -0.045, -0.052)), (0.08, 0.085, 0.012), rot=(math.radians(10), 0, 0))              # resource intake tray
    for sgn in (1, -1):
        box(bm, hc + Vector((sgn * 0.052, -0.02, -0.03)), (0.008, 0.09, 0.03))
    attach(f"Hero_Processor_{s}", bm, M_JOINT, f"Claw.{s}", uv=False)
    bm = bmesh.new()                                                                       # hazard-striped side panels
    for sgn in (1, -1):
        box(bm, hc + Vector((sgn * 0.050, 0.0, 0.012)), (0.006, 0.10, 0.058), rot=(math.radians(-6), 0, 0))
    box(bm, hc + Vector((0, 0.0, 0.058)), (0.07, 0.09, 0.004))
    for q in bm.verts: pass
    lay = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for lp in f.loops: lp[lay].uv = (lp.vert.co[1] * 6 + lp.vert.co[2] * 6, lp.vert.co[0] * 6 + lp.vert.co[2] * 3)
    attach(f"Hero_ProcessorHazard_{s}", bm, M_HAZ, f"Claw.{s}", smooth=False, uv=False)
    bm = bmesh.new()                                                                       # toothed crusher drum
    dc = hc + Vector((0, -0.075, 0.0))
    for k in range(3):
        collar(bm, dc + Vector((sx * (k - 1) * 0.03, 0, 0)), (1, 0, 0), 0.032, depth=0.026, seg=12)
    for k in range(3):
        for a in range(10):
            ang = 2 * math.pi * a / 10 + k * 0.3
            cone(bm, dc + Vector((sx * (k - 1) * 0.03, 0.032 * math.sin(ang), 0.032 * math.cos(ang))), (0, math.sin(ang), math.cos(ang)), 0.008, 0.02, seg=4)
    tube(bm, dc + Vector((-0.055, 0, 0)), dc + Vector((0.055, 0, 0)), 0.01, 0.01, seg=6)
    attach(f"Hero_Drum_{s}", bm, M_CLAW, f"Claw.{s}", uv=False)
    bm = bmesh.new()                                                                       # hydraulic hose looping from upper arm to housing
    h0 = S.lerp(E_, 0.5) + Vector((sx * 0.035, 0.0, 0.045))
    h1 = hc + Vector((sx * 0.045, 0.02, 0.045))
    pts = []
    for k in range(10):
        t = k / 9
        p = h0.lerp(h1, t) + Vector((sx * 0.045 * math.sin(math.pi * t), 0, 0.045 * math.sin(math.pi * t) - 0.02 * t))
        pts.append(p)
    chain(bm, pts, 0.011, 0.011, seg=6)
    for k in (0, 9): collar(bm, pts[k], pts[min(k + 1, 9)] - pts[max(k - 1, 0)], 0.018, depth=0.012, seg=8)
    attach(f"Hero_Hose_{s}", bm, M_HOSE, f"Arm.{s}", uv=False)

# ---------- six legs: ball joints, pistons, plated and serrated tibiae, claws ----------
for s, sx in (("L", 1), ("R", -1)):
    for i in range(3):
        up, lo = arm_data.bones[f"Leg{i+1}.{s}.Upper"], arm_data.bones[f"Leg{i+1}.{s}.Lower"]
        hip, knee, foot = Vector(up.head_local), Vector(up.tail_local), Vector(lo.tail_local)
        dU = (knee - hip).normalized(); outn = Vector((sx, 0, 0.4)).normalized()
        bm = bmesh.new()
        tube(bm, hip, knee, 0.064, 0.048, seg=8)
        ell(bm, hip, (0.072, 0.072, 0.072), seg=10, rings=6); collar(bm, hip + dU * 0.03, dU, 0.072, depth=0.022)
        ell(bm, knee, (0.062, 0.062, 0.062), seg=10, rings=6); collar(bm, knee - dU * 0.03, dU, 0.060, depth=0.02)
        ell(bm, hip.lerp(knee, 0.5) + outn * 0.035, (0.034, 0.07, 0.03), rot=(0, 0, sx * math.radians(25)), seg=8, rings=5)    # femur armour plate
        attach(f"Hero_LegUpper_{i+1}{s}", bm, M_SHELL, f"Leg{i+1}.{s}.Upper", smooth=True)
        bm = bmesh.new()                                                                   # piston
        a0 = hip + outn * 0.062 + dU * 0.03; a1 = knee + outn * 0.056 - dU * 0.03
        tube(bm, a0, a0.lerp(a1, 0.55), 0.011, 0.011, seg=6); tube(bm, a0.lerp(a1, 0.5), a1, 0.0055, 0.0055, seg=5)
        ell(bm, a0, (0.015, 0.015, 0.015), seg=6, rings=4); ell(bm, a1, (0.013, 0.013, 0.013), seg=6, rings=4)
        attach(f"Hero_LegPiston_{i+1}{s}", bm, M_PIST, f"Leg{i+1}.{s}.Upper", uv=False)
        bm = bmesh.new()
        dL = (foot - knee).normalized()
        tube(bm, knee, foot, 0.050, 0.014, seg=8)
        for k in (0.25, 0.5, 0.72):
            p = knee + (foot - knee) * k
            collar(bm, p, dL, 0.054 - 0.026 * k, depth=0.018, seg=8)
        for k in (0.3, 0.5, 0.7):
            p = knee + (foot - knee) * k
            cone(bm, p, (sx * 0.8, 0.5, 0.3), 0.011, 0.05, seg=4)
            cone(bm, p, (sx * 0.8, -0.5, 0.3), 0.011, 0.05, seg=4)
        ell(bm, knee.lerp(foot, 0.3) + outn * 0.03, (0.025, 0.06, 0.02), rot=(0, 0, sx * math.radians(20)), seg=8, rings=5)  # tibia armour plate
        attach(f"Hero_LegLower_{i+1}{s}", bm, M_SHELL if i != 1 else M_RUST, f"Leg{i+1}.{s}.Lower")
        bm = bmesh.new()
        cone(bm, foot + Vector((0, 0, 0.03)), (0, 0, -1), 0.018, 0.06, seg=5)               # claw
        cone(bm, foot + Vector((0, 0.01, 0.02)), (0, 0.6, -0.8), 0.009, 0.045, seg=4)
        cone(bm, foot + Vector((0, -0.01, 0.02)), (0, -0.6, -0.8), 0.009, 0.045, seg=4)
        attach(f"Hero_LegClaw_{i+1}{s}", bm, M_CLAW, f"Leg{i+1}.{s}.Lower", uv=False)

# ---------- animation ----------
pose = arm.pose.bones
for pb in pose: pb.rotation_mode = 'QUATERNION'

def rot_world(pb, rx=0.0, ry=0.0, rz=0.0):
    """Pose rotation expressed in armature (world) axes, converted into the bone's own rest frame."""
    M = pb.bone.matrix_local.to_3x3()
    R = Matrix.Rotation(rz, 3, 'Z') @ Matrix.Rotation(ry, 3, 'Y') @ Matrix.Rotation(rx, 3, 'X')
    pb.rotation_quaternion = (M.inverted() @ R @ M).to_quaternion()

def reset():
    for pb in pose:
        pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)

def key(frame):
    for pb in pose:
        pb.keyframe_insert("rotation_quaternion", frame=frame)
        pb.keyframe_insert("location", frame=frame)

def new_action(name):
    reset()
    arm.animation_data_create()
    act = bpy.data.actions.new(name)
    arm.animation_data.action = act
    return act

def finish(act):
    act.use_fake_user = True
    arm.animation_data.action = None

LEGS = [(i, s) for i in (1, 2, 3) for s in ("L", "R")]
SIDE = {"L": 1, "R": -1}

# Idle: breathing bob, antenna sway, mandible snip (60 frames loop)
act = new_action("Idle")
for f in (1, 16, 31, 46, 61):
    t = (f - 1) / 60.0 * 2 * math.pi
    reset()
    pose["Body"].location = (0, 0, 0.012 * math.sin(t))
    rot_world(pose["Abdomen"], rx=0.03 * math.sin(t))
    for s in ("L", "R"):
        rot_world(pose[f"Antenna.{s}"], rx=0.18 * math.sin(t + 1), rz=SIDE[s] * 0.12 * math.sin(t))
        rot_world(pose[f"Mandible.{s}"], rz=SIDE[s] * -0.22 * max(0.0, math.sin(2 * t)))
        rot_world(pose[f"Claw.{s}"], rz=SIDE[s] * 0.1 * math.sin(t * 2))
    key(f)
finish(act)

# Walk: alternating tripod gait (24 frames loop)
act = new_action("Walk")
for f in range(1, 26, 3):
    ph = (f - 1) / 24.0 * 2 * math.pi
    reset()
    pose["Body"].location = (0, 0, 0.02 * abs(math.sin(ph)))
    rot_world(pose["Body"], rz=0.04 * math.sin(ph))
    rot_world(pose["Abdomen"], rx=0.05 * math.sin(ph * 2))
    for i, s in LEGS:
        group = 0 if (i + (0 if s == "L" else 1)) % 2 == 0 else math.pi    # tripods: 1L,2R,3L vs 1R,2L,3R
        a = ph + group
        swing = 0.42 * math.sin(a)
        lift = 0.38 * max(0.0, math.cos(a))
        rot_world(pose[f"Leg{i}.{s}.Upper"], rx=swing, ry=SIDE[s] * lift * -1)
        rot_world(pose[f"Leg{i}.{s}.Lower"], rx=-0.25 * swing, ry=SIDE[s] * lift * 0.9)
    for s in ("L", "R"):
        rot_world(pose[f"Antenna.{s}"], rx=0.25 * math.sin(ph * 2))
    key(f)
finish(act)

# Hit: rear back, legs flinch (12 frames)
act = new_action("Hit")
for f, k in ((1, 0.0), (4, 1.0), (8, 0.35), (12, 0.0)):
    reset()
    rot_world(pose["Body"], rx=0.35 * k)
    rot_world(pose["Head"], rx=0.3 * k)
    pose["Body"].location = (0, 0.06 * k, -0.03 * k)
    for i, s in LEGS:
        rot_world(pose[f"Leg{i}.{s}.Upper"], ry=SIDE[s] * 0.35 * k * -1)
    for s in ("L", "R"):
        rot_world(pose[f"Claw.{s}"], rz=SIDE[s] * 0.5 * k)
    key(f)
finish(act)

# Death: flips onto its back, legs curl up (45 frames, holds)
act = new_action("Death")
for f, k in ((1, 0.0), (10, 0.5), (24, 1.0), (45, 1.0)):
    reset()
    rot_world(pose["Root"], rx=0.0, ry=0.0, rz=0.0)
    rot_world(pose["Body"], ry=math.pi * 0.93 * k)
    pose["Body"].location = (0, 0, 0.16 * k)
    for i, s in LEGS:
        rot_world(pose[f"Leg{i}.{s}.Upper"], ry=SIDE[s] * 0.9 * k * -1, rx=0.2 * k * (i - 2))
        rot_world(pose[f"Leg{i}.{s}.Lower"], ry=SIDE[s] * 1.1 * k)
    for s in ("L", "R"):
        rot_world(pose[f"Antenna.{s}"], rx=-0.5 * k)
        rot_world(pose[f"Claw.{s}"], rz=SIDE[s] * 0.6 * k)
    key(f)
finish(act)
reset()

tris = sum(len(p.vertices) - 2 for o in bpy.data.objects if o.type == 'MESH' for p in o.data.polygons)
print("IL_TOTAL_TRIS", tris, "ACTIONS", [a.name for a in bpy.data.actions])
bpy.ops.wm.save_as_mainfile(filepath=OUT + "/ironlocust.blend")
bpy.ops.export_scene.gltf(filepath=OUT + "/ironlocust.glb", export_format='GLB', export_apply=True,
                          export_animations=True, export_animation_mode='ACTIONS', export_skins=True,
                          export_force_sampling=True)
print("IL_DONE")
