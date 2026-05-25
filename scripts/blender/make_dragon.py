"""
Blender 5.1 headless script — generates D&D dragon .glb models.
Run with:  blender --background --python scripts/blender/make_dragon.py

Outputs to godot/assets/models/dragons/:
  dragon_red.glb      — Large red fire dragon
  dragon_green.glb    — Medium green poison dragon
  dragon_blue.glb     — Large blue lightning dragon
  dragon_black.glb    — Medium black acid dragon
  dragon_white.glb    — Medium white cold dragon
  dragon_gold.glb     — Large gold metallic dragon (boss)
  dragon_whelp.glb    — Small young dragon (any color encounter)

Each .glb includes NLA animation tracks:
  Idle    — wing flex + head sway (90 frames)
  Attack  — head lunge + jaw snap (30 frames)
  Fly     — full wing flap cycle (48 frames)
  Death   — collapse + tumble (45 frames)
"""

import bpy
import bmesh
import math
import os
from mathutils import Euler

OUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "godot", "assets", "models", "dragons"
)
os.makedirs(OUT_DIR, exist_ok=True)


# ── Helpers ──────────────────────────────────────────────────────────────────

def clear():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for col in list(bpy.data.collections):
        bpy.data.collections.remove(col)


def mat(name: str, base: tuple, metallic=0.0, roughness=0.5,
        emission=None, alpha=1.0) -> bpy.types.Material:
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*base, 1.0)
    p.inputs["Metallic"].default_value = metallic
    p.inputs["Roughness"].default_value = roughness
    if emission:
        p.inputs["Emission Color"].default_value = (*emission, 1.0)
        p.inputs["Emission Strength"].default_value = 2.5
    if alpha < 1.0:
        p.inputs["Alpha"].default_value = alpha
        m.blend_method = 'BLEND'
    return m


def add_mesh(name: str, verts, faces, material=None, location=(0, 0, 0)) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(name + "_mesh")
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()
    bv = [bm.verts.new(v) for v in verts]
    bm.verts.ensure_lookup_table()
    for f in faces:
        try:
            bm.faces.new([bv[i] for i in f])
        except Exception:
            pass
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    obj.location = location
    if material:
        obj.data.materials.append(material)
    return obj


def prim(ptype: str, name: str, loc=(0, 0, 0), scale=(1, 1, 1),
         rot=(0, 0, 0), segments=8, **kwargs) -> bpy.types.Object:
    if ptype == "uvsphere":
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=kwargs.get("radius", 1.0),
            segments=segments, ring_count=segments // 2,
            location=loc
        )
    elif ptype == "cylinder":
        bpy.ops.mesh.primitive_cylinder_add(
            radius=kwargs.get("radius", 1.0),
            depth=kwargs.get("depth", 1.0),
            vertices=segments, location=loc
        )
    elif ptype == "cone":
        bpy.ops.mesh.primitive_cone_add(
            radius1=kwargs.get("radius1", 1.0),
            radius2=kwargs.get("radius2", 0.0),
            depth=kwargs.get("depth", 1.0),
            vertices=segments, location=loc
        )
    elif ptype == "cube":
        bpy.ops.mesh.primitive_cube_add(size=kwargs.get("size", 1.0), location=loc)
    elif ptype == "ico":
        bpy.ops.mesh.primitive_ico_sphere_add(
            radius=kwargs.get("radius", 1.0),
            subdivisions=kwargs.get("subdivisions", 2),
            location=loc
        )

    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    obj.rotation_euler = rot
    return obj


def assign_mat(obj, material):
    if obj.data.materials:
        obj.data.materials[0] = material
    else:
        obj.data.materials.append(material)


def join_to_root(parts: list) -> bpy.types.Object:
    """Join all parts into the first one and return it."""
    for o in parts:
        o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    result = bpy.context.active_object
    result.select_set(False)
    return result


def export(name: str):
    path = os.path.join(OUT_DIR, name + ".glb")
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format='GLB',
        export_animations=True,
        export_nla_strips=True,
        export_all_influences=False,
        use_selection=False,
    )
    print(f"[make_dragon] exported → {path}")


# ── Animation helpers ─────────────────────────────────────────────────────────

def insert_loc(obj, frame: int, loc):
    obj.location = loc
    obj.keyframe_insert("location", frame=frame)


def insert_rot(obj, frame: int, rot):
    obj.rotation_euler = rot
    obj.keyframe_insert("rotation_euler", frame=frame)


def insert_scale(obj, frame: int, sc):
    obj.scale = sc
    obj.keyframe_insert("scale", frame=frame)


def bake_action(obj, name: str, frame_start: int, frame_end: int):
    """Push current action into a new NLA track named `name`."""
    action = obj.animation_data.action if obj.animation_data else None
    if not action:
        return
    action.name = name
    track = obj.animation_data.nla_tracks.new()
    track.name = name
    strip = track.strips.new(name, frame_start, action)
    strip.name = name
    obj.animation_data.action = None


def add_dragon_animations(body, head, wing_l, wing_r, tail, size_scale=1.0):
    """Create Idle, Attack, Fly, Death NLA tracks on the dragon parts."""
    bpy.context.scene.frame_start = 1

    # ── Idle: head sway + gentle wing flex (90 frames) ──────────────────
    bpy.context.scene.frame_end = 90
    base_head_y = head.location.y
    base_head_z = head.location.z
    for obj in [body, head, wing_l, wing_r, tail]:
        obj.animation_data_create()
        if obj.animation_data.action:
            obj.animation_data.action = None

    for f, hy, hz, wr, wl_r in [
        (1,   base_head_y,       base_head_z,       (0, 0, 0),         (0, 0, 0)),
        (22,  base_head_y + 0.08 * size_scale, base_head_z + 0.04 * size_scale, (0, 0.08, 0), (0, -0.08, 0)),
        (45,  base_head_y,       base_head_z,       (0, 0, 0),         (0, 0, 0)),
        (67,  base_head_y - 0.06 * size_scale, base_head_z - 0.02 * size_scale, (0, -0.06, 0), (0, 0.06, 0)),
        (90,  base_head_y,       base_head_z,       (0, 0, 0),         (0, 0, 0)),
    ]:
        head.location.y = hy
        head.location.z = hz
        head.keyframe_insert("location", frame=f)
        wing_r.rotation_euler = Euler(wr)
        wing_r.keyframe_insert("rotation_euler", frame=f)
        wing_l.rotation_euler = Euler(wl_r)
        wing_l.keyframe_insert("rotation_euler", frame=f)

    for obj in [body, head, wing_l, wing_r, tail]:
        if obj.animation_data and obj.animation_data.action:
            bake_action(obj, "Idle", 1, 90)

    # ── Attack: head lunge forward + jaw suggestion (30 frames) ──────────
    bpy.context.scene.frame_end = 30
    for obj in [body, head, wing_l, wing_r, tail]:
        if obj.animation_data:
            obj.animation_data.action = None

    lunge_dist = 0.4 * size_scale
    for f, hy, hz in [
        (1,  base_head_y, base_head_z),
        (8,  base_head_y + lunge_dist * 0.5, base_head_z + 0.1 * size_scale),
        (15, base_head_y + lunge_dist,       base_head_z),
        (22, base_head_y + lunge_dist * 0.3, base_head_z - 0.05 * size_scale),
        (30, base_head_y, base_head_z),
    ]:
        head.location.y = hy
        head.location.z = hz
        head.keyframe_insert("location", frame=f)

    # body recoils slightly
    base_bx = body.location.x
    for f, bx in [(1, base_bx), (10, base_bx - 0.05 * size_scale),
                  (20, base_bx + 0.02 * size_scale), (30, base_bx)]:
        body.location.x = bx
        body.keyframe_insert("location", frame=f)

    for obj in [body, head, wing_l, wing_r, tail]:
        if obj.animation_data and obj.animation_data.action:
            bake_action(obj, "Attack", 1, 30)

    # ── Fly: full wing flap cycle (48 frames) ────────────────────────────
    bpy.context.scene.frame_end = 48
    for obj in [body, head, wing_l, wing_r, tail]:
        if obj.animation_data:
            obj.animation_data.action = None

    flap_angle = 0.7  # radians
    for f, angle, body_z_delta in [
        (1,  0,            0),
        (12, -flap_angle,  0.12 * size_scale),
        (24, flap_angle,   -0.05 * size_scale),
        (36, -flap_angle,  0.12 * size_scale),
        (48, 0,            0),
    ]:
        wing_l.rotation_euler = Euler((angle, 0, 0))
        wing_l.keyframe_insert("rotation_euler", frame=f)
        wing_r.rotation_euler = Euler((angle, 0, 0))
        wing_r.keyframe_insert("rotation_euler", frame=f)
        base_bz = body.location.z
        body.location.z = base_bz + body_z_delta
        body.keyframe_insert("location", frame=f)

    for obj in [body, head, wing_l, wing_r, tail]:
        if obj.animation_data and obj.animation_data.action:
            bake_action(obj, "Fly", 1, 48)

    # ── Death: collapse to ground (45 frames) ────────────────────────────
    bpy.context.scene.frame_end = 45
    for obj in [body, head, wing_l, wing_r, tail]:
        if obj.animation_data:
            obj.animation_data.action = None

    base_body_z = body.location.z
    for f, bz, rot_x in [(1, base_body_z, 0), (20, base_body_z - 0.2 * size_scale, 0.3),
                          (35, base_body_z - 0.5 * size_scale, 1.2),
                          (45, base_body_z - 0.8 * size_scale, math.pi * 0.45)]:
        body.location.z = bz
        body.keyframe_insert("location", frame=f)
        body.rotation_euler = Euler((rot_x, 0, 0))
        body.keyframe_insert("rotation_euler", frame=f)

    wing_l.rotation_euler = Euler((0, 0, 0))
    wing_l.keyframe_insert("rotation_euler", frame=1)
    wing_l.rotation_euler = Euler((0, 0, math.pi * 0.3))
    wing_l.keyframe_insert("rotation_euler", frame=45)
    wing_r.rotation_euler = Euler((0, 0, 0))
    wing_r.keyframe_insert("rotation_euler", frame=1)
    wing_r.rotation_euler = Euler((0, 0, -math.pi * 0.3))
    wing_r.keyframe_insert("rotation_euler", frame=45)

    for obj in [body, head, wing_l, wing_r, tail]:
        if obj.animation_data and obj.animation_data.action:
            bake_action(obj, "Death", 1, 45)


# ── Dragon builder ────────────────────────────────────────────────────────────

def make_dragon(color_name: str, color_rgb: tuple, accent_rgb: tuple,
                eye_rgb: tuple, breath_rgb: tuple,
                size: float = 1.0) -> dict:
    """
    Build a quadrupedal dragon with wings.
    size: 1.0 = adult, 0.6 = whelp
    Returns dict of key objects for animation.
    """
    s = size
    sc_mat = mat(f"scale_{color_name}", color_rgb, roughness=0.55, metallic=0.1)
    belly_mat = mat(f"belly_{color_name}", accent_rgb, roughness=0.65)
    eye_mat = mat(f"eye_{color_name}", eye_rgb, emission=eye_rgb, roughness=0.1)
    wing_mat = mat(f"wing_{color_name}", color_rgb, roughness=0.7, alpha=0.88)
    claw_mat = mat(f"claw_{color_name}", (0.15, 0.12, 0.1), metallic=0.3, roughness=0.4)
    horn_mat = mat(f"horn_{color_name}", (0.25, 0.22, 0.18), metallic=0.15, roughness=0.5)

    parts = []

    # ── Body ────────────────────────────────────────────────────────────
    body = prim("uvsphere", "body", loc=(0, 0, 0.55 * s), scale=(0.55 * s, 0.85 * s, 0.42 * s), segments=10)
    assign_mat(body, sc_mat)
    parts.append(body)

    # Belly plates
    belly = prim("uvsphere", "belly", loc=(0, 0, 0.35 * s), scale=(0.40 * s, 0.70 * s, 0.22 * s), segments=10)
    assign_mat(belly, belly_mat)
    parts.append(belly)

    # ── Neck ────────────────────────────────────────────────────────────
    neck = prim("cylinder", "neck", loc=(0, 0.55 * s, 0.82 * s),
                scale=(0.18 * s, 0.18 * s, 0.40 * s),
                rot=(0.7, 0, 0), segments=8, radius=1.0, depth=1.0)
    assign_mat(neck, sc_mat)
    parts.append(neck)

    # ── Head ────────────────────────────────────────────────────────────
    head = prim("uvsphere", "head", loc=(0, 1.0 * s, 1.05 * s),
                scale=(0.22 * s, 0.32 * s, 0.20 * s), segments=10)
    assign_mat(head, sc_mat)

    # Snout
    snout = prim("cone", "snout", loc=(0, 1.30 * s, 0.98 * s),
                 scale=(0.14 * s, 0.28 * s, 0.12 * s),
                 rot=(math.pi / 2, 0, 0), segments=8, radius1=1.0, radius2=0.3, depth=1.0)
    assign_mat(snout, sc_mat)
    parts.append(snout)

    # Eyes
    eye_l = prim("uvsphere", "eye_l", loc=(0.18 * s, 0.92 * s, 1.10 * s),
                 scale=(0.055 * s, 0.055 * s, 0.055 * s), segments=6)
    assign_mat(eye_l, eye_mat)
    parts.append(eye_l)

    eye_r = prim("uvsphere", "eye_r", loc=(-0.18 * s, 0.92 * s, 1.10 * s),
                 scale=(0.055 * s, 0.055 * s, 0.055 * s), segments=6)
    assign_mat(eye_r, eye_mat)
    parts.append(eye_r)

    # Horns (2 main)
    horn_l = prim("cone", "horn_l", loc=(0.20 * s, 0.85 * s, 1.22 * s),
                  scale=(0.06 * s, 0.06 * s, 0.28 * s),
                  rot=(-0.3, 0.2, 0.15), segments=5, radius1=1.0, radius2=0.0, depth=1.0)
    assign_mat(horn_l, horn_mat)
    parts.append(horn_l)

    horn_r = prim("cone", "horn_r", loc=(-0.20 * s, 0.85 * s, 1.22 * s),
                  scale=(0.06 * s, 0.06 * s, 0.28 * s),
                  rot=(-0.3, -0.2, -0.15), segments=5, radius1=1.0, radius2=0.0, depth=1.0)
    assign_mat(horn_r, horn_mat)
    parts.append(horn_r)

    # ── Tail ────────────────────────────────────────────────────────────
    tail = prim("cone", "tail", loc=(0, -1.10 * s, 0.38 * s),
                scale=(0.18 * s, 0.75 * s, 0.18 * s),
                rot=(-0.4, 0, 0), segments=8, radius1=1.0, radius2=0.05, depth=1.0)
    assign_mat(tail, sc_mat)

    tail_tip = prim("ico", "tail_tip", loc=(0, -1.55 * s, 0.28 * s),
                    scale=(0.10 * s, 0.14 * s, 0.10 * s),
                    radius=1.0, subdivisions=1)
    assign_mat(tail_tip, sc_mat)
    parts.append(tail_tip)

    # ── Legs ────────────────────────────────────────────────────────────
    for side_x, side_name, y_pos in [(0.45 * s, "front_r", 0.45 * s),
                                      (-0.45 * s, "front_l", 0.45 * s),
                                      (0.40 * s, "rear_r", -0.45 * s),
                                      (-0.40 * s, "rear_l", -0.45 * s)]:
        upper = prim("cylinder", f"upper_{side_name}", loc=(side_x, y_pos, 0.28 * s),
                     scale=(0.10 * s, 0.10 * s, 0.28 * s),
                     rot=(0.3 if "front" in side_name else -0.25, 0, 0),
                     segments=6, radius=1.0, depth=1.0)
        assign_mat(upper, sc_mat)
        parts.append(upper)

        lower = prim("cylinder", f"lower_{side_name}", loc=(side_x, y_pos + (0.08 if "front" in side_name else -0.08) * s, 0.10 * s),
                     scale=(0.08 * s, 0.08 * s, 0.22 * s),
                     rot=(0, 0, 0), segments=6, radius=1.0, depth=1.0)
        assign_mat(lower, sc_mat)
        parts.append(lower)

        # Claws (3 toes)
        for ci, cx in enumerate([-0.04 * s, 0.0, 0.04 * s]):
            claw = prim("cone", f"claw_{side_name}_{ci}", loc=(side_x + cx, y_pos + (0.12 if "front" in side_name else -0.12) * s, 0.02 * s),
                        scale=(0.04 * s, 0.09 * s, 0.04 * s),
                        rot=(0.4, 0, 0), segments=4, radius1=1.0, radius2=0.0, depth=1.0)
            assign_mat(claw, claw_mat)
            parts.append(claw)

    # ── Wings ────────────────────────────────────────────────────────────
    # Wing root connection
    wing_root_r = prim("uvsphere", "wing_root_r", loc=(0.58 * s, 0.10 * s, 0.72 * s),
                       scale=(0.10 * s, 0.10 * s, 0.10 * s), segments=6)
    assign_mat(wing_root_r, sc_mat)
    parts.append(wing_root_r)

    wing_root_l = prim("uvsphere", "wing_root_l", loc=(-0.58 * s, 0.10 * s, 0.72 * s),
                       scale=(0.10 * s, 0.10 * s, 0.10 * s), segments=6)
    assign_mat(wing_root_l, sc_mat)
    parts.append(wing_root_l)

    # Wing membranes (wide flat shapes)
    wing_r = prim("uvsphere", "wing_r", loc=(1.10 * s, 0.10 * s, 0.85 * s),
                  scale=(0.70 * s, 0.12 * s, 0.55 * s), segments=8)
    assign_mat(wing_r, wing_mat)

    wing_l = prim("uvsphere", "wing_l", loc=(-1.10 * s, 0.10 * s, 0.85 * s),
                  scale=(0.70 * s, 0.12 * s, 0.55 * s), segments=8)
    assign_mat(wing_l, wing_mat)

    # Wing finger spars
    for i, angle in enumerate([0.1, 0.3, 0.5]):
        spar_yr = 0.10 * s + math.sin(angle) * 0.3 * s
        spar_zr = 0.85 * s + math.cos(angle) * 0.25 * s
        spar_r = prim("cylinder", f"spar_r_{i}", loc=(1.55 * s + i * 0.06 * s, spar_yr, spar_zr),
                      scale=(0.03 * s, 0.03 * s, 0.38 * s),
                      rot=(angle, 0, 0.15), segments=4, radius=1.0, depth=1.0)
        assign_mat(spar_r, horn_mat)
        parts.append(spar_r)

        spar_l = prim("cylinder", f"spar_l_{i}", loc=(-1.55 * s - i * 0.06 * s, spar_yr, spar_zr),
                      scale=(0.03 * s, 0.03 * s, 0.38 * s),
                      rot=(angle, 0, -0.15), segments=4, radius=1.0, depth=1.0)
        assign_mat(spar_l, horn_mat)
        parts.append(spar_l)

    # Join static parts into body, keep wings + head + tail separate for animation
    all_static = parts
    joined_body = join_to_root(all_static) if len(all_static) > 1 else all_static[0]
    joined_body.name = "dragon_body"

    return {"body": joined_body, "head": head, "wing_r": wing_r, "wing_l": wing_l, "tail": tail}


# ── Dragon variants ───────────────────────────────────────────────────────────

DRAGONS = [
    # name,         body color,            belly/accent,          eye color,         breath color,    size
    ("dragon_red",   (0.72, 0.10, 0.06),  (0.50, 0.08, 0.05),  (1.0, 0.6, 0.0),  (1.0, 0.3, 0.0),  1.0),
    ("dragon_green", (0.12, 0.48, 0.10),  (0.08, 0.32, 0.08),  (0.0, 1.0, 0.2),  (0.2, 1.0, 0.0),  0.85),
    ("dragon_blue",  (0.10, 0.22, 0.75),  (0.08, 0.16, 0.55),  (0.4, 0.8, 1.0),  (0.4, 0.8, 1.0),  1.0),
    ("dragon_black", (0.10, 0.10, 0.10),  (0.18, 0.14, 0.14),  (0.8, 0.0, 0.8),  (0.6, 0.8, 0.0),  0.85),
    ("dragon_white", (0.90, 0.92, 0.95),  (0.70, 0.75, 0.80),  (0.6, 0.9, 1.0),  (0.7, 0.9, 1.0),  0.85),
    ("dragon_gold",  (0.85, 0.68, 0.10),  (0.70, 0.55, 0.08),  (1.0, 0.9, 0.3),  (1.0, 0.8, 0.2),  1.2),
    ("dragon_whelp", (0.62, 0.22, 0.10),  (0.45, 0.18, 0.08),  (1.0, 0.55, 0.1), (1.0, 0.3, 0.0),  0.6),
]


def main():
    for (name, body_c, belly_c, eye_c, breath_c, sz) in DRAGONS:
        print(f"[make_dragon] building {name} (size={sz})…")
        clear()
        parts = make_dragon(name, body_c, belly_c, eye_c, breath_c, size=sz)
        add_dragon_animations(
            parts["body"], parts["head"],
            parts["wing_l"], parts["wing_r"],
            parts["tail"], size_scale=sz
        )
        export(name)
        print(f"[make_dragon] {name} done.")

    print("[make_dragon] all dragons complete.")


main()
