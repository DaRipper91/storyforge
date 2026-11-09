"""Iron-Locust hero: six-legged iron-shelled insect, own skeleton + Idle/Walk/Hit/Death clips (Blender 5.x).
Run: blender -b -P build_ironlocust.py -- <out_dir>
Front is -Y, feet on z=0, ~1.0 long x ~0.75 high. Parts are bone-parented (rigid) to a 25-bone armature."""
import bpy, bmesh, math, sys
from mathutils import Vector, Matrix, Euler

OUT = sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.fps = 30

def mat(name, rgb, rough=0.5, metal=0.0, emit=None, strength=2.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = strength
    m.use_backface_culling = False
    return m
M_SHELL = mat("IL_Shell", (0.22, 0.19, 0.17), 0.42, 0.75)
M_RUST  = mat("IL_Rust",  (0.40, 0.20, 0.09), 0.7, 0.5)
M_JOINT = mat("IL_Joint", (0.06, 0.055, 0.05), 0.5, 0.8)
M_EYE   = mat("IL_Eye",   (0.35, 0.08, 0.04), 0.2, 0.0, emit=(0.9, 0.25, 0.08), strength=1.2)
M_CLAW  = mat("IL_Claw",  (0.55, 0.52, 0.48), 0.3, 1.0)

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
def attach(name, bm, material, bone_name, smooth=True):
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

# ---------- body ----------
bm = bmesh.new()
ell(bm, (0, -0.10, 0.50), (0.21, 0.30, 0.19))                        # thorax
for i in range(5):                                                   # overlapping back plates
    ell(bm, (0, -0.30 + i * 0.12, 0.64 - 0.012 * i), (0.19 - 0.012 * i, 0.075, 0.07), rot=(math.radians(12), 0, 0), seg=8, rings=4)
attach("Hero_Thorax", bm, M_SHELL, "Body", smooth=False)

bm = bmesh.new()
ell(bm, (0, 0.40, 0.46), (0.25, 0.42, 0.22))
for i in range(6):
    ell(bm, (0, 0.10 + i * 0.12, 0.60 - 0.03 * abs(i - 2) * 0.5), (0.24 - 0.012 * i, 0.07, 0.07), rot=(math.radians(8), 0, 0), seg=8, rings=4)
attach("Hero_Abdomen", bm, M_SHELL, "Abdomen", smooth=False)

bm = bmesh.new()                                                     # rust staining on the shell
for (x, y, z, s) in ((0.12, 0.05, 0.69, 0.05), (-0.10, 0.30, 0.66, 0.06), (0.05, 0.55, 0.60, 0.05), (-0.14, -0.20, 0.66, 0.04)):
    ell(bm, (x, y, z), (s, s * 1.4, s * 0.35), seg=6, rings=3)
attach("Hero_Rust", bm, M_RUST, "Body", smooth=False)

# folded wing cases (elytra) over the abdomen
for s, sx in (("L", 1), ("R", -1)):
    bm = bmesh.new()
    ell(bm, (sx * 0.13, 0.28, 0.66), (0.15, 0.40, 0.08), rot=(math.radians(-8), 0, math.radians(sx * 6)), seg=12, rings=6)
    attach(f"Hero_Elytra_{s}", bm, M_SHELL, f"Elytra.{s}", smooth=True)

# head, eyes, mandibles, antennae
bm = bmesh.new()
ell(bm, (0, -0.42, 0.50), (0.13, 0.12, 0.11))
cone(bm, (0, -0.50, 0.50), (0, -1, -0.2), 0.05, 0.09, seg=6)
attach("Hero_Head", bm, M_SHELL, "Head", smooth=False)
bm = bmesh.new()
for sx in (1, -1):
    ell(bm, (sx * 0.085, -0.50, 0.56), (0.035, 0.03, 0.04), seg=6, rings=4)
attach("Hero_Eyes", bm, M_EYE, "Head")
for s, sx in (("L", 1), ("R", -1)):
    bm = bmesh.new()
    cone(bm, (sx * 0.05, -0.50, 0.44), (sx * -0.4, -1, -0.5), 0.028, 0.14, seg=5)
    for k in range(3):
        cone(bm, (sx * (0.045 - 0.008 * k), -0.54 - 0.025 * k, 0.425 - 0.012 * k), (sx * -1, 0, 0.3), 0.008, 0.03, seg=3)
    attach(f"Hero_Mandible_{s}", bm, M_CLAW, f"Mandible.{s}")
    bm = bmesh.new()
    tube(bm, (sx * 0.05, -0.46, 0.58), (sx * 0.10, -0.58, 0.78), 0.012, 0.008)
    tube(bm, (sx * 0.10, -0.58, 0.78), (sx * 0.14, -0.66, 0.92), 0.008, 0.004)
    attach(f"Hero_Antenna_{s}", bm, M_JOINT, f"Antenna.{s}")

# manipulator forelimbs with pincers
for s, sx in (("L", 1), ("R", -1)):
    bm = bmesh.new()
    tube(bm, (sx * 0.12, -0.34, 0.38), (sx * 0.14, -0.55, 0.28), 0.032, 0.024)
    ell(bm, (sx * 0.12, -0.34, 0.38), (0.04, 0.04, 0.04), seg=6, rings=4)
    attach(f"Hero_Arm_{s}", bm, M_SHELL, f"Arm.{s}")
    bm = bmesh.new()
    cone(bm, (sx * 0.14, -0.55, 0.28), (sx * 0.15, -1, 0.35), 0.03, 0.13, seg=5)
    cone(bm, (sx * 0.14, -0.55, 0.28), (sx * -0.15, -1, 0.15), 0.025, 0.12, seg=5)
    attach(f"Hero_Claw_{s}", bm, M_CLAW, f"Claw.{s}")

# six legs: femur + spiked tibia, joint balls, small foot spike
for s, sx in (("L", 1), ("R", -1)):
    for i in range(3):
        up, lo = arm_data.bones[f"Leg{i+1}.{s}.Upper"], arm_data.bones[f"Leg{i+1}.{s}.Lower"]
        hip, knee, foot = Vector(up.head_local), Vector(up.tail_local), Vector(lo.tail_local)
        bm = bmesh.new()
        tube(bm, hip, knee, 0.036, 0.028)
        ell(bm, hip, (0.045, 0.045, 0.045), seg=6, rings=4)
        ell(bm, knee, (0.04, 0.04, 0.04), seg=6, rings=4)
        attach(f"Hero_LegUpper_{i+1}{s}", bm, M_SHELL, f"Leg{i+1}.{s}.Upper")
        bm = bmesh.new()
        tube(bm, knee, foot, 0.026, 0.012)
        d = (foot - knee)
        for k in (0.3, 0.5, 0.7):
            p = knee + d * k
            cone(bm, p, (sx * 0.8, 0.5, 0.3), 0.01, 0.045, seg=4)
            cone(bm, p, (sx * 0.8, -0.5, 0.3), 0.01, 0.045, seg=4)
        cone(bm, foot + Vector((0, 0, 0.02)), (0, 0, -1), 0.014, 0.04, seg=4)
        attach(f"Hero_LegLower_{i+1}{s}", bm, M_SHELL if i != 1 else M_RUST, f"Leg{i+1}.{s}.Lower")

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
