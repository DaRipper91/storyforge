"""Helpers shared by the Mechanical-group hero builders (build_ironveil.py, build_forgespawn.py, ...).
Kept separate from hero_common.py / hero_textures.py (which stay untouched). Blender 5.x, front is -Y, Z up.
Import: sys.path.insert(0, dirname(__file__)); from mech_common import *"""
import bpy, bmesh, math, os, random
import numpy as np
from mathutils import Vector, Matrix, Euler
from hero_common import *
import hero_textures as T


# ------------------------------------------------------------------ bmesh collector
class Parts:
    """Collects geometry per (material, bone, smooth) and attaches one Hero_* object per bucket on flush()."""
    def __init__(self, arm):
        self.arm = arm; self.b = {}
    def bm(self, material, bone, smooth=False):
        k = (material.name, bone, smooth)
        if k not in self.b: self.b[k] = (bmesh.new(), material)
        return self.b[k][0]
    def flush(self, tag=""):
        for (mn, bone, smooth), (bm, material) in self.b.items():
            if not bm.verts: bm.free(); continue
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            triplanar_uv(bm)
            name = "Hero_%s%s%s_%s" % (tag, mn, "_s" if smooth else "", bone.replace(".", "_"))
            attach(self.arm, name, bm, material, bone, smooth=smooth)
        self.b = {}


def triplanar_uv(bm, scale=3.5):
    """Give faces that have no UVs (cylinders, hulls, spheres) a box projection so the metal textures still apply."""
    uv = bm.loops.layers.uv.get("UVMap") or bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        if all(abs(lp[uv].uv[0]) + abs(lp[uv].uv[1]) < 1e-9 for lp in f.loops):
            n = f.normal; ax = max(range(3), key=lambda i: abs(n[i])); a, b = [i for i in range(3) if i != ax]
            for lp in f.loops:
                lp[uv].uv = (lp.vert.co[a] * scale, lp.vert.co[b] * scale)


# ------------------------------------------------------------------ geometry
def cyl(bm, c, axis, r, length, seg=10, r2=None):
    d = Vector(axis).normalized()
    m = Matrix.Translation(Vector(c)) @ d.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r if r2 is None else r2, depth=length, matrix=m)


def box(bm, c, size, rot=(0, 0, 0)):
    m = Matrix.Translation(Vector(c)) @ Matrix.LocRotScale(None, Euler(rot), Vector(size))
    bmesh.ops.create_cube(bm, size=1.0, matrix=m)


def hull(bm, pts):
    vs = [bm.verts.new(p) for p in pts]
    bmesh.ops.convex_hull(bm, input=vs)
    bmesh.ops.delete(bm, geom=[v for v in vs if not v.link_faces], context='VERTS')
    return vs


def fan_plate(bm, pts, lift, uvc=None, uvs=0.3):
    """Flat polygon with its centre raised along the normal: an origami-folded facet (crease lines to every corner)."""
    pts = [Vector(p) for p in pts]
    c = sum(pts, Vector()) / len(pts)
    n = (pts[1] - pts[0]).cross(pts[-1] - pts[0])
    n = n.normalized() if n.length > 1e-9 else Vector((0, 0, 1))
    vc = bm.verts.new(c + n * lift); vs = [bm.verts.new(p) for p in pts]
    uv = bm.loops.layers.uv.get("UVMap") or bm.loops.layers.uv.new("UVMap")
    ox, oy = uvc if uvc else (random.random(), random.random())
    fs = []
    for i in range(len(vs)):
        try: f = bm.faces.new((vs[i], vs[(i + 1) % len(vs)], vc))
        except ValueError: continue
        fs.append(f)
        for lp in f.loops:
            co = lp.vert.co
            lp[uv].uv = (ox + (co.x + co.y * 0.7) * uvs * 3 % 1.0 * 0.25, oy + (co.z + co.y * 0.4) * uvs * 3 % 1.0 * 0.25)
    return fs


class Sweep:
    """A tapered elliptic tube along p0->p1: P(t, a, l) = centre(t) + u cos(a) (rx(t)+l) + v sin(a) (ry(t)+l)."""
    def __init__(self, p0, p1, u, v, rx, ry=None):
        self.p0, self.p1 = Vector(p0), Vector(p1); self.u, self.v = Vector(u), Vector(v)
        self.rx = rx if callable(rx) else (lambda t, r=rx: r)
        ry = rx if ry is None else ry
        self.ry = ry if callable(ry) else (lambda t, r=ry: r)
    def P(self, t, a, l=0.0):
        c = self.p0 + (self.p1 - self.p0) * t
        return c + self.u * math.cos(a) * (self.rx(t) + l) + self.v * math.sin(a) * (self.ry(t) + l)


def interp(keys):
    """Piecewise-linear function of t from [(t, value), ...]."""
    def f(t):
        if t <= keys[0][0]: return keys[0][1]
        for (a, va), (b, vb) in zip(keys, keys[1:]):
            if t <= b: return va + (vb - va) * (t - a) / (b - a)
        return keys[-1][1]
    return f


def shingles(bm, sw, t0, t1, rows, n, hw=None, lift=0.006, flare=0.012, fold=0.008, jitter=0.0, a0=0.0, a1=2 * math.pi, stagger=True, overlap=1.35):
    """Overlapping kite-shaped lamellae wrapped round a sweep, tips pointing toward t1 (rows run t0 -> t1)."""
    span = a1 - a0; full = abs(span - 2 * math.pi) < 1e-3
    cols = n if full else n
    for r in range(rows):
        ta = t0 + (t1 - t0) * r / rows
        tb = t0 + (t1 - t0) * (r + overlap) / rows
        tb = min(tb, t1 + (t1 - t0) / rows * 0.4)
        tm = ta + (tb - ta) * 0.32
        off = (0.5 if (stagger and r % 2) else 0.0)
        for c in range(cols):
            a = a0 + span * (c + off) / (cols if full else max(cols - 1, 1)) if full else a0 + span * (c + off) / max(cols - 1, 1)
            ang_w = hw if hw else (span / cols) * 0.62
            j = 1.0 + random.uniform(-jitter, jitter)
            L = lift + 0.0015 * (r % 3)
            tl, tr = sw.P(ta, a - ang_w * j, L), sw.P(ta, a + ang_w * j, L)
            ml, mr = sw.P(tm, a - ang_w * 1.18 * j, L + flare * 0.3), sw.P(tm, a + ang_w * 1.18 * j, L + flare * 0.3)
            tip = sw.P(tb, a, L + flare)
            mc = sw.P(tm, a, L + flare * 0.3 + fold)
            tc = sw.P(ta, a, L)
            uv = bm.loops.layers.uv.get("UVMap") or bm.loops.layers.uv.new("UVMap")
            ox, oy = random.random(), random.random()
            vs = [bm.verts.new(p) for p in (tc, tl, tr, ml, mr, mc, tip)]
            tc_, tl_, tr_, ml_, mr_, mc_, tip_ = vs
            uvm = {tc_: (.5, 1), tl_: (.15, 1), tr_: (.85, 1), ml_: (0, .65), mr_: (1, .65), mc_: (.5, .62), tip_: (.5, 0)}
            for q in ((tl_, tc_, mc_, ml_), (tc_, tr_, mr_, mc_), (ml_, mc_, tip_), (mc_, mr_, tip_)):
                try: f = bm.faces.new(q)
                except ValueError: continue
                for lp in f.loops:
                    u_, v_ = uvm[lp.vert]; lp[uv].uv = (ox + u_ * 0.28, oy + v_ * 0.28)


def hinge(bm, c, axis, r=0.022, length=0.05, seg=12, screw=True, cap=0.6):
    """Brass-style barrel hinge with cap screws on both ends (call with a brass material bucket)."""
    d = Vector(axis).normalized()
    cyl(bm, c, d, r, length, seg)
    if screw:
        for s in (1, -1):
            pc = Vector(c) + d * s * (length / 2 + r * 0.12)
            cyl(bm, pc, d, r * cap, r * 0.3, 10)
            # screw slot
            side = d.cross(Vector((0, 0, 1)))
            if side.length < 1e-3: side = d.cross(Vector((0, 1, 0)))
            side.normalize()
            box(bm, pc + d * s * r * 0.15, (r * 0.09, r * 0.09, r * 0.09), (0, 0, 0)) if False else None


def strap(bm, p0, p1, w, thick=0.003, up=Vector((0, 0, 1))):
    """Flat thin bar between two points (hinge link plates, rods)."""
    p0, p1 = Vector(p0), Vector(p1); d = p1 - p0
    m = Matrix.Translation((p0 + p1) / 2) @ d.to_track_quat('Y', 'Z').to_matrix().to_4x4()
    bmesh.ops.create_cube(bm, size=1.0, matrix=m @ Matrix.Diagonal(Vector((w, d.length, thick, 1))))


def rivets(bm, pts, r=0.004):
    for p in pts: ell(bm, p, (r, r, r), seg=6, rings=3)


# ------------------------------------------------------------------ textures
def streaks(n, seed, win=48, vertical=False):
    rng = np.random.default_rng(seed); a = rng.random((n, n)).astype(np.float32)
    if vertical: a = a.T
    c = np.cumsum(np.concatenate([a[:, -win:], a], 1), 1)
    o = (c[:, win:] - c[:, :-win]) / win
    o = (o - o.min()) / (o.max() - o.min() + 1e-6)
    return o.T if vertical else o


def metal_tex(name, outdir, base, kind="brushed", n=512, seed=1, rust=(0.30, 0.16, 0.07), tint2=None):
    """Return (diffuse, normal) images for a metal: 'brushed' (streaked), 'oxid' (rust/patina patches), 'brass', 'plate' (rivetted panels)."""
    s = streaks(n, seed, 40); s2 = streaks(n, seed + 7, 12)
    f = T.fbm(n, seed + 3, 5, 4)
    base = np.array(base, np.float32)
    f2 = T.fbm(n, seed + 11, 3, 2)
    col = base[None, None, :] * (0.86 + 0.22 * s[..., None]) * (0.95 + 0.08 * s2[..., None]) * (0.72 + 0.55 * f2[..., None])
    h = 0.18 * s + 0.10 * s2
    x, y = T._grid(n)
    if kind == "oxid":
        m = T.smooth(0.50, 0.72, f)[..., None]
        col = col * (1 - m) + np.array(rust, np.float32)[None, None, :] * (0.6 + 0.6 * f[..., None]) * m
        h = h + 0.4 * m[..., 0] * f
    elif kind == "brass":
        pat = T.smooth(0.55, 0.8, T.fbm(n, seed + 9, 4, 6))[..., None]
        col = col * (1 - 0.35 * pat) + np.array([0.18, 0.12, 0.05], np.float32)[None, None, :] * 0.35 * pat
    elif kind == "plate":
        e, cid = T.voronoi(n, 4, seed)
        seam = 1 - T.smooth(0.0, 0.05, e)
        col = col * (1 - 0.55 * seam[..., None]) * (0.85 + 0.25 * cid[..., None])
        h = h + 0.9 * T.smooth(0.0, 0.1, e) - 0.3 * seam
        # rivet rows near seams
        riv = ((np.abs(((x * 16) % 1) - 0.5) < 0.12) & (np.abs(((y * 16) % 1) - 0.5) < 0.12) & (e < 0.22) & (e > 0.1))
        col = col + riv[..., None] * 0.18; h = h + riv * 0.8
    # scratches
    rng = np.random.default_rng(seed + 31)
    for _ in range(14):
        yy = rng.integers(0, n); xx = rng.integers(0, n); ln = rng.integers(30, 120)
        xs = (xx + np.arange(ln)) % n; ys = (yy + (np.arange(ln) * rng.uniform(-0.3, 0.3)).astype(int)) % n
        col[ys, xs] = col[ys, xs] * 0.7 + 0.16
    di = T.to_image(name + "_diffuse", np.concatenate([np.clip(col, 0, 1), np.ones((n, n, 1), np.float32)], -1), outdir)
    ni = T.to_image(name + "_normal", T.normal_from_height(h, 0.5), outdir, "Non-Color")
    return di, ni


def glow_tex(name, outdir, color, n=256, kind="cells", seed=3):
    """Emission map: hot veined cells (cores, furnaces) on near-black."""
    e, cid = T.voronoi(n, 5, seed); f = T.fbm(n, seed + 2, 4, 5)
    v = (1 - T.smooth(0.0, 0.2, e)) * (0.5 + 0.5 * f) if kind == "cells" else (0.4 + 0.6 * f)
    c = np.array(color, np.float32)
    rgba = np.concatenate([v[..., None] * c[None, None, :], np.ones((n, n, 1), np.float32)], -1)
    return T.to_image(name, rgba, outdir)


def hazard_tex(name, outdir, a=(0.75, 0.55, 0.05), b=(0.06, 0.06, 0.06), n=512, seed=5, wear=0.5):
    x, y = T._grid(n)
    stripe = (((x + y) * 8) % 1.0 < 0.5)[..., None]
    f = T.fbm(n, seed, 5, 5); s = streaks(n, seed + 1, 30)
    col = np.where(stripe, np.array(a, np.float32)[None, None, :], np.array(b, np.float32)[None, None, :]) * (0.7 + 0.5 * f[..., None])
    wornm = T.smooth(0.62, 0.85, f)[..., None] * wear
    col = col * (1 - wornm) + np.array([0.3, 0.29, 0.28], np.float32)[None, None, :] * wornm * (0.7 + 0.5 * s[..., None])
    h = 0.4 * f + 0.4 * s
    return (T.to_image(name + "_diffuse", np.concatenate([col, np.ones((n, n, 1), np.float32)], -1), outdir),
            T.to_image(name + "_normal", T.normal_from_height(h, 0.7), outdir, "Non-Color"))


def make_metal_mat(name, base, kind, outdir, rough=0.42, metal=0.92, seed=1, emission=None, emission_strength=1.0, rust=(0.30, 0.16, 0.07)):
    m = mat(name, base, rough, metal)
    di, ni = metal_tex(name.lower(), outdir, base, kind, seed=seed, rust=rust)
    T.bind(m, di, ni, emission, emission_strength)
    return m


def override_base(mat_body, mat_legs=None):
    """Replace the base body/legs vertex-coloured materials so none of the generic base shows."""
    for o in bpy.data.objects:
        if o.type == "MESH" and o.name.endswith(("_Body", "_Legs")):
            o.data.materials.clear(); o.data.materials.append(mat_legs if (mat_legs and o.name.endswith("_Legs")) else mat_body)
            for p in o.data.polygons: p.material_index = 0


def strip_base(keep=("Hand.", "Index", "Middle", "Ring", "Pinky", "Thumb"), keep_body_above=None):
    """Delete every base-mesh face whose dominant bone is not a hand/finger bone (and the whole base legs), so the
    bespoke slender body shows with only the base hands left; returns nothing."""
    for o in list(bpy.data.objects):
        if o.type != "MESH" or not o.name.endswith(("_Body", "_Legs")): continue
        if o.name.endswith("_Legs"):
            # The loader mirrors the one-sided base leg mesh into a right leg (and its test expects that), so keep it but
            # collapse it to a ~1 cm speck hidden inside the left shin: the bespoke legs are what you see.
            c = o.matrix_world.inverted() @ Vector((0.121, -0.07, 0.3))
            for v in o.data.vertices: v.co = c + (v.co - c) * 0.02
            o.data.update(); continue
        me = o.data; bm = bmesh.new(); bm.from_mesh(me)
        lay = bm.verts.layers.deform.active
        names = {g.index: g.name for g in o.vertex_groups}
        def dom(v):
            d = v[lay]
            if not d: return ""
            return names.get(max(d.items(), key=lambda kv: kv[1])[0], "")
        dead = [f for f in bm.faces if not all(dom(v).startswith(keep) for v in f.verts)]
        bmesh.ops.delete(bm, geom=dead, context='FACES')
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
        bm.to_mesh(me); bm.free()


def ring_tube(bm, sw, t0, t1, rows, n, l=0.0, cap=False):
    """Closed tube skin following a Sweep between t0 and t1 (inner frame for limbs / torso)."""
    vs = [[bm.verts.new(sw.P(t0 + (t1 - t0) * r / rows, 2 * math.pi * c / n, l)) for c in range(n)] for r in range(rows + 1)]
    for r in range(rows):
        for c in range(n):
            bm.faces.new((vs[r][c], vs[r][(c + 1) % n], vs[r + 1][(c + 1) % n], vs[r + 1][c]))
    if cap:
        for ring in (vs[0], vs[-1]):
            try: bm.faces.new(ring)
            except ValueError: pass


def frame(p0, p1):
    d = (Vector(p1) - Vector(p0)).normalized()
    u = d.cross(Vector((0, 0, 1)))
    if u.length < 1e-3: u = d.cross(Vector((0, 1, 0)))
    u.normalize(); v = d.cross(u).normalized()
    return u, v


def capfn(t, pw=4.0):
    return max(1e-3, (1.0 - abs(2 * t - 1) ** pw)) ** 0.5


def blob(bm, p0, p1, r0, r1=None, sy=1.0, rows=8, n=12, pw=4.0, mid=1.0, up=None):
    """Rounded capsule/ellipsoid from p0 to p1 (radius r0 -> r1, optionally flattened by sy in the 2nd axis, bulged by mid)."""
    r1 = r0 if r1 is None else r1
    u, v = frame(p0, p1)
    if up is not None:
        v = Vector(up); u = (Vector(p1) - Vector(p0)).cross(v).normalized(); v = (Vector(p1) - Vector(p0)).normalized().cross(u).normalized() * -1
    rf = lambda t, k=1.0: (r0 + (r1 - r0) * t) * (1 + (mid - 1) * math.sin(math.pi * t)) * capfn(t, pw) * k
    sw = Sweep(p0, p1, u, v, lambda t: rf(t), lambda t: rf(t, sy))
    ring_tube(bm, sw, 0.0, 1.0, rows, n, 0.0)


def blob_sw(bm, sw, rows=10, n=14, pw=4.0):
    """Closed rounded body along an existing Sweep (radii multiplied by a cap profile so both ends close)."""
    sw2 = Sweep(sw.p0, sw.p1, sw.u, sw.v, lambda t: sw.rx(t) * capfn(t, pw), lambda t: sw.ry(t) * capfn(t, pw))
    ring_tube(bm, sw2, 0.0, 1.0, rows, n, 0.0)


def slab(bm, c, axes, size, q=0.008, rivet=0.0):
    """Chamfered plate: width along axes[0], height along axes[1], thickness (outward) along axes[2]."""
    tx, dy, oz = [Vector(a) for a in axes]; w, h, th = size; c = Vector(c); pts = []
    for sx in (1, -1):
        for sy in (1, -1):
            for (kx, ky, kz) in ((w / 2 - q, h / 2 - q, th / 2), (w / 2, h / 2, th / 2 - q), (w / 2, h / 2, -th / 2)):
                pts.append(c + tx * sx * kx + dy * sy * ky + oz * kz)
    hull(bm, pts)
    if rivet > 0:
        for sx in (1, -1):
            for sy in (1, -1):
                cone(bm, c + tx * sx * (w / 2 - q - rivet * 2.4) + dy * sy * (h / 2 - q - rivet * 2.4) + oz * (th / 2 - 0.001), oz, rivet, rivet * 0.8, seg=6, r2=rivet * 0.45)


def slab_e(bm, c, size, rot=(0, 0, 0), q=0.008, rivet=0.0):
    m = Euler(rot).to_matrix()
    slab(bm, c, (m @ Vector((1, 0, 0)), m @ Vector((0, 1, 0)), m @ Vector((0, 0, 1))), size, q, rivet)


def plates_around(bm, sw, t, angles, w, h, th, l=0.0, q=0.008, tilt=0.0, rivet=0.0):
    """Chamfered plates standing on a Sweep at parameter t, one per angle, facing outward."""
    e = 0.01
    for a in angles:
        c = sw.P(t, a, l)
        d = (sw.P(min(t + e, 1.0), a, l) - sw.P(max(t - e, 0.0), a, l)).normalized()
        cen = sw.p0 + (sw.p1 - sw.p0) * t
        o = (c - cen); o = (o - d * o.dot(d)).normalized()
        tx = d.cross(o).normalized()
        d2 = (d * math.cos(tilt) + o * math.sin(tilt)).normalized(); o2 = tx.cross(d2).normalized() * -1
        slab(bm, c + o * th * 0.5, (tx, d2, o), (w, h, th), q, rivet)


def bone_pt(arm, bone, head=True):
    b = arm.data.bones[bone]
    return Vector(b.head_local if head else b.tail_local)


def finish(OUT, hid):
    print("TRIS", hid, tri_count())
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, hid + ".blend"))
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, hid + ".glb"), export_format='GLB', export_apply=True,
                              export_animations=False, export_skins=True)
    print("DONE", hid)
