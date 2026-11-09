"""Shared Blender helpers for hand-modelled heroes (import via sys.path from the build scripts).
Front of a character is -Y, Z up, feet on z=0. Blender parents bone children at the bone TAIL, so the
parent-inverse below is built from the tail-translated bone matrix."""
import bpy, bmesh, math
from mathutils import Vector, Matrix, Euler


def mat(name, rgb, rough=0.6, metal=0.0, alpha=1.0, emit=None, strength=1.5):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha; m.surface_render_method = 'BLENDED'
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = strength
    m.use_backface_culling = False
    return m


def recolor_base(table):
    """Set Principled base colours on the base model's own materials (suffix .001 ignored)."""
    for m in bpy.data.materials:
        key = m.name.split(".")[0]
        if key in table and m.use_nodes:
            b = m.node_tree.nodes.get("Principled BSDF")
            if b: b.inputs["Base Color"].default_value = (*table[key], 1)


def remove_objects(*suffixes):
    for o in list(bpy.data.objects):
        if o.type == 'MESH' and (o.parent is None or any(o.name.endswith(s) for s in suffixes)):
            bpy.data.objects.remove(o)


def attach(arm, name, bm, material, bone, smooth=True):
    sc = bpy.context.scene
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); sc.collection.objects.link(o)
    me.materials.append(material)
    for p in me.polygons: p.use_smooth = smooth
    o.parent = arm; o.parent_type = 'BONE'; o.parent_bone = bone
    b = arm.data.bones[bone]
    o.matrix_parent_inverse = (arm.matrix_world @ b.matrix_local @ Matrix.Translation((0, b.length, 0))).inverted()
    return o


def skinned(arm, name, bm, material, weight_fn):
    sc = bpy.context.scene
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); sc.collection.objects.link(o)
    me.materials.append(material)
    for p in me.polygons: p.use_smooth = True
    o.parent = arm
    groups = {}
    for v in me.vertices:
        for b, w in weight_fn(v.co).items():
            if w <= 1e-4: continue
            g = groups.get(b) or o.vertex_groups.new(name=b); groups[b] = g
            g.add([v.index], w, 'REPLACE')
    mod = o.modifiers.new("Armature", 'ARMATURE'); mod.object = arm
    return o


def strip(rows, cols, fn):
    """Quad grid; fn(row_frac, col_frac) -> Vector."""
    bm = bmesh.new()
    vs = [[bm.verts.new(fn(r / (rows - 1), c / (cols - 1))) for c in range(cols)] for r in range(rows)]
    for r in range(rows - 1):
        for c in range(cols - 1):
            bm.faces.new((vs[r][c], vs[r][c + 1], vs[r + 1][c + 1], vs[r + 1][c]))
    return bm


def ell(bm, c, s, rot=(0, 0, 0), seg=10, rings=6):
    m = Matrix.Translation(Vector(c)) @ Matrix.LocRotScale(None, Euler(rot), Vector(s))
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0, matrix=m)


def cone(bm, base, direction, r, length, seg=5, r2=0.0):
    d = Vector(direction).normalized()
    m = Matrix.Translation(Vector(base) + d * length / 2) @ d.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r2, depth=length, matrix=m)


def tube(bm, p0, p1, r0, r1, seg=6):
    d = Vector(p1) - Vector(p0)
    cone(bm, p0, d, r0, d.length, seg=seg, r2=r1)


def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a))); return t * t * (3 - 2 * t)


def tri_count():
    return sum(len(p.vertices) - 2 for o in bpy.data.objects if o.type == 'MESH' for p in o.data.polygons)
