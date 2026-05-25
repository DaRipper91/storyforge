"""
Generates .glb enemy models for StoryForge using Blender 5.x headless.
Run: blender --background --python make_enemies.py

Outputs to godot/assets/models/enemies/
Each model includes Idle, Attack, and Death NLA actions.
"""
import bpy, bmesh, math, os, sys

OUT = os.path.join(os.path.dirname(__file__),
                   "../../godot/assets/models/enemies")
OUT = os.path.realpath(OUT)
os.makedirs(OUT, exist_ok=True)


# ── Utilities ──────────────────────────────────────────────────────────

def clear():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=True)
    for d in [bpy.data.meshes, bpy.data.materials,
              bpy.data.armatures, bpy.data.actions]:
        for item in list(d):
            d.remove(item)


def mat(name, color, roughness=0.85, metallic=0.0,
        emission=None, emission_strength=3.0, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    n = m.node_tree.nodes
    n.clear()
    b = n.new('ShaderNodeBsdfPrincipled')
    b.inputs['Base Color'].default_value = (*color, alpha)
    b.inputs['Roughness'].default_value  = roughness
    b.inputs['Metallic'].default_value   = metallic
    if alpha < 1.0:
        m.blend_method = 'BLEND'
        b.inputs['Alpha'].default_value  = alpha
    if emission:
        b.inputs['Emission Color'].default_value    = (*emission, 1.0)
        b.inputs['Emission Strength'].default_value = emission_strength
    o = n.new('ShaderNodeOutputMaterial')
    m.node_tree.links.new(b.outputs['BSDF'], o.inputs['Surface'])
    return m


def add_mesh(verts, faces, name, material):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(material)
    return ob


def prim(kind, loc=(0,0,0), scale=(1,1,1), rot=(0,0,0), mat=None, **kw):
    """Add a primitive and return the object."""
    bpy.ops.object.select_all(action='DESELECT')
    if kind == 'sphere':
        bpy.ops.mesh.primitive_uv_sphere_add(
            segments=kw.get('segs', 16), ring_count=kw.get('rings', 8),
            radius=kw.get('r', 0.5), location=loc)
    elif kind == 'cylinder':
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=kw.get('verts', 12), radius=kw.get('r', 0.5),
            depth=kw.get('h', 1.0), location=loc)
    elif kind == 'cone':
        bpy.ops.mesh.primitive_cone_add(
            vertices=kw.get('verts', 8),
            radius1=kw.get('r1', 0.5), radius2=kw.get('r2', 0.0),
            depth=kw.get('h', 1.0), location=loc)
    elif kind == 'cube':
        bpy.ops.mesh.primitive_cube_add(location=loc)
    ob = bpy.context.active_object
    ob.scale = scale
    ob.rotation_euler = rot
    if mat:
        if ob.data.materials:
            ob.data.materials[0] = mat
        else:
            ob.data.materials.append(mat)
    bpy.ops.object.transform_apply(scale=True, rotation=True)
    return ob


def join_all(name):
    bpy.ops.object.select_all(action='SELECT')
    bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]
    bpy.ops.object.join()
    bpy.context.active_object.name = name
    return bpy.context.active_object


def add_animations(ob):
    """Add Idle / Attack / Death NLA actions via keyframe_insert (Blender 5.x)."""
    ob.animation_data_create()

    ox, oy, oz = ob.location.x, ob.location.y, ob.location.z
    rx, ry, rz = ob.rotation_euler.x, ob.rotation_euler.y, ob.rotation_euler.z

    def kl(f, x, y, z):
        ob.location = (x, y, z)
        ob.keyframe_insert(data_path='location', frame=f)

    def kr(f, ex, ey, ez):
        ob.rotation_euler = (ex, ey, ez)
        ob.keyframe_insert(data_path='rotation_euler', frame=f)

    def push(name, start=1):
        act = ob.animation_data.action
        if not act:
            return
        act.name = name
        track = ob.animation_data.nla_tracks.new()
        track.name = name
        track.strips.new(name, start, act)
        ob.animation_data.action = None

    # Idle — gentle Y bob, 60 frames
    kl(1,  ox, oy,        oz)
    kl(15, ox, oy + 0.04, oz)
    kl(30, ox, oy,        oz)
    kl(45, ox, oy - 0.02, oz)
    kl(60, ox, oy,        oz)
    push("Idle")

    # Attack — forward lunge + head tilt, 24 frames
    kl(1,  ox, oy,        oz); kr(1,  rx,   ry, rz)
    kl(8,  ox, oy + 0.35, oz); kr(8,  0.4,  ry, rz)
    kl(16, ox, oy,        oz); kr(16, rx,   ry, rz)
    kl(24, ox, oy,        oz); kr(24, rx,   ry, rz)
    push("Attack")

    # Death — collapse Z + tip forward, 30 frames
    kl(1,  ox, oy, oz);       kr(1,  rx,  ry, rz)
    kl(30, ox, oy, oz - 1.2); kr(30, 1.5, ry, rz)
    push("Death")

    ob.location = (ox, oy, oz)
    ob.rotation_euler = (rx, ry, rz)


def export(ob, filename):
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    path = os.path.join(OUT, filename)
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format='GLB',
        use_selection=True,
        export_animations=True,
        export_nla_strips=True,
        export_yup=True,
    )
    print(f"  ✓ {filename}")


# ── Skeleton ───────────────────────────────────────────────────────────

def make_skeleton():
    clear()
    bone_mat  = mat('Bone',  (0.88, 0.85, 0.74), roughness=0.9)
    eye_mat   = mat('Eye',   (0.1,  0.95, 0.2),  roughness=0.2,
                    emission=(0.1, 0.95, 0.2), emission_strength=6.0)

    # Skull
    prim('sphere', loc=(0,0,1.65), scale=(1,1,1), r=0.14, mat=bone_mat)
    # Jaw
    prim('sphere', loc=(0,0.02,1.50), scale=(1.0,1.3,0.6), r=0.10, mat=bone_mat)
    # Eye sockets
    prim('sphere', loc=(-0.06,0.10,1.64), scale=(1,1,1), r=0.035, mat=eye_mat)
    prim('sphere', loc=( 0.06,0.10,1.64), scale=(1,1,1), r=0.035, mat=eye_mat)
    # Neck
    prim('cylinder', loc=(0,0,1.47), scale=(1,1,1), r=0.04, h=0.14, mat=bone_mat)
    # Spine
    prim('cylinder', loc=(0,0,1.10), scale=(1,1,1), r=0.045, h=0.55, mat=bone_mat)
    # Pelvis
    prim('sphere', loc=(0,0,0.78), scale=(1.6,1.0,0.7), r=0.16, mat=bone_mat)

    # Ribcage — 5 pairs of ribs
    for i, z in enumerate([1.32, 1.25, 1.18, 1.11, 1.04]):
        r = 0.13 + i * 0.01
        for side in [-1, 1]:
            prim('cylinder', loc=(side*r*0.6, 0, z),
                 scale=(1, 1, 1), r=0.025, h=r*1.1,
                 rot=(0, side * (math.pi/2 - 0.3), 0), mat=bone_mat)

    # Collar bones
    for side in [-1, 1]:
        prim('cylinder', loc=(side*0.13, 0, 1.38),
             scale=(1,1,1), r=0.025, h=0.25,
             rot=(0, side*math.pi/2, 0), mat=bone_mat)
    # Shoulder
    for side in [-1, 1]:
        prim('sphere', loc=(side*0.24, 0, 1.36), scale=(1,1,1), r=0.05, mat=bone_mat)
    # Upper arm
    for side in [-1, 1]:
        prim('cylinder', loc=(side*0.27, 0, 1.22),
             scale=(1,1,1), r=0.03, h=0.28,
             rot=(0, 0, side*0.2), mat=bone_mat)
    # Elbow
    for side in [-1, 1]:
        prim('sphere', loc=(side*0.30, 0, 1.06), scale=(1,1,1), r=0.04, mat=bone_mat)
    # Forearm
    for side in [-1, 1]:
        prim('cylinder', loc=(side*0.33, 0, 0.93),
             scale=(1,1,1), r=0.025, h=0.24,
             rot=(0, 0, side*0.15), mat=bone_mat)
    # Hand (3 finger bones)
    for side in [-1, 1]:
        for fi in range(3):
            fz = 0.80 + (fi - 1) * 0.025
            prim('cylinder', loc=(side*0.35, (fi-1)*0.035, fz),
                 scale=(1,1,1), r=0.015, h=0.08,
                 rot=(0.3, 0, side*0.1), mat=bone_mat)

    # Hip joints
    for side in [-1, 1]:
        prim('sphere', loc=(side*0.12, 0, 0.76), scale=(1,1,1), r=0.055, mat=bone_mat)
    # Thighs
    for side in [-1, 1]:
        prim('cylinder', loc=(side*0.11, 0, 0.55),
             scale=(1,1,1), r=0.04, h=0.38,
             rot=(0, 0, side*0.08), mat=bone_mat)
    # Knees
    for side in [-1, 1]:
        prim('sphere', loc=(side*0.11, 0, 0.36), scale=(1,1,1), r=0.045, mat=bone_mat)
    # Shins
    for side in [-1, 1]:
        prim('cylinder', loc=(side*0.10, 0, 0.17),
             scale=(1,1,1), r=0.032, h=0.34, mat=bone_mat)
    # Feet
    for side in [-1, 1]:
        prim('sphere', loc=(side*0.10, 0.06, 0.02), scale=(1.0,2.0,0.5),
             r=0.065, mat=bone_mat)

    ob = join_all("skeleton")
    add_animations(ob)
    export(ob, "skeleton.glb")


# ── Ghoul ──────────────────────────────────────────────────────────────

def make_ghoul():
    clear()
    flesh = mat('GhoulFlesh', (0.28, 0.38, 0.22), roughness=0.95)
    claw  = mat('GhoulClaw',  (0.18, 0.15, 0.12), roughness=0.7)
    eye   = mat('GhoulEye',   (0.9, 0.3, 0.0),
                emission=(1.0, 0.4, 0.0), emission_strength=5.0)

    # Hunched torso
    prim('sphere', loc=(0,-0.08,1.05), scale=(1.0,0.9,0.85), r=0.25, mat=flesh)
    # Pelvis — lower, hunched forward
    prim('sphere', loc=(0,-0.04,0.72), scale=(1.2,0.8,0.7), r=0.20, mat=flesh)
    # Head — elongated forward
    prim('sphere', loc=(0,0.10,1.50), scale=(0.85,1.15,0.90), r=0.18, mat=flesh)
    # Jaw — protruding
    prim('sphere', loc=(0,0.18,1.36), scale=(0.90,1.35,0.55), r=0.12, mat=flesh)
    # Eyes (sunken, glowing)
    prim('sphere', loc=(-0.07,0.21,1.50), scale=(1,1,1), r=0.04, mat=eye)
    prim('sphere', loc=( 0.07,0.21,1.50), scale=(1,1,1), r=0.04, mat=eye)
    # Neck (short, thick)
    prim('cylinder', loc=(0,0.05,1.30), scale=(1,1,1), r=0.08, h=0.25,
         rot=(-0.3,0,0), mat=flesh)

    # Long arms reaching forward+down
    for side in [-1,1]:
        prim('sphere', loc=(side*0.28,-0.04,1.18), scale=(1,1,1), r=0.07, mat=flesh)
        # Upper arm (angled out and forward)
        prim('cylinder', loc=(side*0.32,0.05,1.02),
             scale=(1,1,1), r=0.05, h=0.38,
             rot=(0.3, 0, side*0.35), mat=flesh)
        # Forearm (longer than human, forward)
        prim('cylinder', loc=(side*0.40,0.15,0.76),
             scale=(1,1,1), r=0.04, h=0.38,
             rot=(0.5, 0, side*0.2), mat=flesh)
        # Claw hand
        prim('sphere', loc=(side*0.46,0.22,0.58), scale=(1.2,1,0.7), r=0.07, mat=claw)
        for fi in range(3):
            angle = side * (0.2 + fi * 0.25)
            prim('cylinder', loc=(side*(0.46+fi*0.04),0.26+fi*0.03,0.50-fi*0.02),
                 scale=(1,1,1), r=0.018, h=0.10,
                 rot=(0.6+fi*0.1, 0, angle), mat=claw)

    # Legs — slightly bent
    for side in [-1,1]:
        prim('sphere', loc=(side*0.13,0,0.70), scale=(1,1,1), r=0.065, mat=flesh)
        prim('cylinder', loc=(side*0.12,-0.04,0.52),
             scale=(1,1,1), r=0.055, h=0.35,
             rot=(-0.1,0,side*0.06), mat=flesh)
        prim('sphere', loc=(side*0.11,-0.06,0.34), scale=(1,1,1), r=0.05, mat=flesh)
        prim('cylinder', loc=(side*0.10,-0.02,0.17),
             scale=(1,1,1), r=0.04, h=0.33, mat=flesh)
        prim('sphere', loc=(side*0.10,0.06,0.02), scale=(1.0,2.2,0.5), r=0.06, mat=claw)

    ob = join_all("ghoul")
    add_animations(ob)
    export(ob, "ghoul.glb")


# ── Bandit (cloaked humanoid) ──────────────────────────────────────────

def make_bandit():
    clear()
    cloak   = mat('Cloak',  (0.12, 0.10, 0.08), roughness=0.95)
    leather = mat('Leath',  (0.22, 0.16, 0.10), roughness=0.85, metallic=0.05)
    skin    = mat('Skin',   (0.52, 0.38, 0.28), roughness=0.9)
    blade   = mat('Blade',  (0.6,  0.65, 0.7),  roughness=0.2, metallic=0.9)
    eye     = mat('BEye',   (0.9, 0.75, 0.2),
                  emission=(1.0, 0.8, 0.1), emission_strength=2.0)

    # Head (hood shadow)
    prim('sphere', loc=(0,0,1.58), scale=(1,1,1), r=0.14, mat=skin)
    prim('sphere', loc=(-0.07,0.10,1.60), scale=(1,1,1), r=0.028, mat=eye)
    prim('sphere', loc=( 0.07,0.10,1.60), scale=(1,1,1), r=0.028, mat=eye)
    # Hood
    prim('cone', loc=(0,-0.03,1.75), scale=(1,1,1),
         r1=0.20, r2=0.04, h=0.28, mat=cloak)
    # Cloak body
    prim('cone', loc=(0,-0.04,1.05), scale=(1.0,0.85,1),
         r1=0.42, r2=0.22, h=1.10, mat=cloak)
    # Torso under cloak
    prim('cylinder', loc=(0,0,1.10), scale=(1,1,1), r=0.20, h=0.52, mat=leather)
    # Belt
    prim('cylinder', loc=(0,0,0.82), scale=(1,1,1), r=0.22, h=0.06, mat=blade)
    # Legs
    for side in [-1,1]:
        prim('cylinder', loc=(side*0.10,0,0.55), scale=(1,1,1), r=0.075, h=0.44, mat=leather)
        prim('cylinder', loc=(side*0.10,0,0.20), scale=(1,1,1), r=0.062, h=0.36, mat=leather)
        prim('sphere',   loc=(side*0.10,0.05,0.03), scale=(1,2,0.5), r=0.07, mat=leather)
    # Weapon hand (right)
    prim('sphere', loc=(0.25,0,0.95), scale=(1,1,1), r=0.06, mat=skin)
    # Dagger
    prim('cylinder', loc=(0.32,0,0.85), scale=(1,1,1), r=0.015, h=0.35,
         rot=(0.4,0,0), mat=blade)
    prim('cone', loc=(0.32,0.155,0.78), scale=(1,1,1),
         r1=0.03, r2=0.005, h=0.08, rot=(0.4,0,0), mat=blade)
    # Shield arm (left)
    prim('sphere', loc=(-0.26,0,0.95), scale=(1,1,1), r=0.06, mat=skin)

    ob = join_all("bandit")
    add_animations(ob)
    export(ob, "bandit.glb")
    export(ob, "thug.glb")  # thug shares the bandit model


# ── Animated Armor ─────────────────────────────────────────────────────

def make_animated_armor():
    clear()
    plate  = mat('Plate',  (0.45, 0.48, 0.50), roughness=0.2, metallic=0.92)
    dark   = mat('Dark',   (0.05, 0.06, 0.08), roughness=0.5, metallic=0.3)
    glow   = mat('Soul',   (0.2,  0.6,  1.0),
                 emission=(0.2, 0.6, 1.0), emission_strength=8.0)

    # Helm
    prim('sphere', loc=(0,0,1.68), scale=(1.0,0.9,1.05), r=0.18, mat=plate)
    prim('sphere', loc=(0,0,1.68), scale=(0.85,0.7,0.90), r=0.17, mat=dark)  # hollow inside
    # Visor glow
    prim('cylinder', loc=(0,0.13,1.66), scale=(1.4,0.1,0.35),
         r=0.08, h=0.04, rot=(math.pi/2,0,0), mat=glow)
    # Eye sockets
    for side in [-1,1]:
        prim('sphere', loc=(side*0.07,0.14,1.67), scale=(1,0.5,0.7), r=0.04, mat=glow)
    # Neck gorget
    prim('cylinder', loc=(0,0,1.48), scale=(1,1,1), r=0.11, h=0.14, mat=plate)

    # Chest plate
    prim('sphere', loc=(0,0,1.24), scale=(1.5,0.9,1.0), r=0.25, mat=plate)
    # Back plate
    prim('sphere', loc=(0,-0.05,1.24), scale=(1.3,0.5,0.95), r=0.23, mat=plate)
    # Soul core (glowing chest center)
    prim('sphere', loc=(0,0.18,1.24), scale=(0.6,0.3,0.5), r=0.12, mat=glow)
    # Abdomen
    prim('cylinder', loc=(0,0,0.95), scale=(1,1,1), r=0.18, h=0.35, mat=plate)
    # Waist plate
    prim('cylinder', loc=(0,0,0.76), scale=(1.3,1,0.4), r=0.20, h=0.08, mat=plate)

    # Pauldrons
    for side in [-1,1]:
        prim('sphere', loc=(side*0.30,0,1.40), scale=(1,0.85,0.80), r=0.13, mat=plate)
    # Upper arms
    for side in [-1,1]:
        prim('cylinder', loc=(side*0.30,0,1.18), scale=(1,1,1), r=0.085, h=0.30,
             rot=(0,0,side*0.15), mat=plate)
    # Elbow plates
    for side in [-1,1]:
        prim('sphere', loc=(side*0.32,0,1.01), scale=(1,1,0.7), r=0.08, mat=plate)
    # Forearms
    for side in [-1,1]:
        prim('cylinder', loc=(side*0.32,0,0.86), scale=(1,1,1), r=0.075, h=0.28,
             rot=(0,0,side*0.10), mat=plate)
    # Gauntlets
    for side in [-1,1]:
        prim('sphere', loc=(side*0.33,0,0.72), scale=(1.1,0.8,0.75), r=0.09, mat=plate)
        for fi in range(3):
            prim('cylinder', loc=(side*(0.32+fi*0.01),0.05+fi*0.01,0.65-fi*0.01),
                 scale=(1,1,1), r=0.02, h=0.06, rot=(0.2,0,0), mat=plate)

    # Hip plates
    for side in [-1,1]:
        prim('sphere', loc=(side*0.17,0,0.72), scale=(1,0.8,0.7), r=0.10, mat=plate)
    # Thigh plates
    for side in [-1,1]:
        prim('cylinder', loc=(side*0.14,0,0.53), scale=(1,1,1), r=0.092, h=0.34,
             rot=(0,0,side*0.05), mat=plate)
    # Knee cops
    for side in [-1,1]:
        prim('sphere', loc=(side*0.13,0.04,0.35), scale=(1.1,0.7,0.85), r=0.09, mat=plate)
    # Greaves
    for side in [-1,1]:
        prim('cylinder', loc=(side*0.12,0,0.20), scale=(1,1,1), r=0.080, h=0.32, mat=plate)
    # Sabatons
    for side in [-1,1]:
        prim('sphere', loc=(side*0.12,0.08,0.03), scale=(1.0,2.2,0.55), r=0.08, mat=plate)

    ob = join_all("animated_armor")
    add_animations(ob)
    export(ob, "animated_armor.glb")


# ── Shadow ─────────────────────────────────────────────────────────────

def make_shadow():
    clear()
    shadow_mat = mat('ShadowBody', (0.04, 0.02, 0.08),
                     roughness=0.95, alpha=0.72)
    core_mat   = mat('ShadowCore', (0.3, 0.0, 0.5),
                     emission=(0.5, 0.0, 1.0), emission_strength=6.0)
    eye_mat    = mat('ShadowEye',  (0.8, 0.0, 1.0),
                     emission=(1.0, 0.0, 1.0), emission_strength=10.0)

    # Main body — amorphous wispy mass
    prim('sphere', loc=(0,0,0.95), scale=(1.0,0.85,1.2), r=0.30, mat=shadow_mat)
    # Upper mass
    prim('sphere', loc=(0.06,0,1.30), scale=(0.75,0.70,0.90), r=0.24, mat=shadow_mat)
    # Tendrils drifting off
    for i in range(5):
        angle = i * (math.tau / 5)
        prim('sphere', loc=(math.sin(angle)*0.28, math.cos(angle)*0.25, 0.85 + i*0.06),
             scale=(0.5, 0.5, 1.8), r=0.10, mat=shadow_mat)
    # Lower wisp
    prim('cone', loc=(0,-0.05,0.35), scale=(1,0.8,1),
         r1=0.05, r2=0.22, h=0.55, mat=shadow_mat)
    # Glowing eyes
    prim('sphere', loc=(-0.09, 0.18, 1.32), scale=(1,0.5,0.8), r=0.055, mat=eye_mat)
    prim('sphere', loc=( 0.09, 0.18, 1.32), scale=(1,0.5,0.8), r=0.055, mat=eye_mat)
    # Soul core
    prim('sphere', loc=(0.04, 0.10, 1.00), scale=(0.5,0.4,0.6), r=0.14, mat=core_mat)

    ob = join_all("shadow")
    # Shadow floats — use Z axis for hover, same keyframe_insert approach
    ob.animation_data_create()
    oz = ob.location.z
    ox, oy = ob.location.x, ob.location.y
    rx, ry, rz = ob.rotation_euler.x, ob.rotation_euler.y, ob.rotation_euler.z

    def kl(f, z): ob.location.z = z; ob.keyframe_insert(data_path='location', frame=f)
    def kr(f, ex): ob.rotation_euler.x = ex; ob.keyframe_insert(data_path='rotation_euler', frame=f)
    def push(name, start=1):
        act = ob.animation_data.action
        if not act: return
        act.name = name
        t = ob.animation_data.nla_tracks.new(); t.name = name
        t.strips.new(name, start, act)
        ob.animation_data.action = None

    kl(1, oz); kl(20, oz + 0.08); kl(40, oz); kl(60, oz)
    push("Idle")
    kl(1, oz); kr(1, rx); kl(8, oz + 0.30); kr(8, 0.4); kl(16, oz); kr(16, rx)
    push("Attack")
    kl(1, oz); kr(1, rx); kl(25, oz - 1.5); kr(25, rx)
    push("Death")

    ob.location.z = oz; ob.rotation_euler.x = rx
    export(ob, "shadow.glb")


# ── Skeleton Race Enemy (generic armored alien) ────────────────────────

def make_race_enemy():
    clear()
    hull  = mat('RaceHull',  (0.30, 0.22, 0.45), roughness=0.45, metallic=0.65)
    skin  = mat('RaceSkin',  (0.20, 0.18, 0.25), roughness=0.90)
    glow  = mat('RaceGlow',  (0.6,  0.3,  1.0),
                emission=(0.7, 0.2, 1.0), emission_strength=5.0)
    blade = mat('RaceBlade', (0.5,  0.6,  0.8),  roughness=0.15, metallic=0.95)

    # Head (alien, angular)
    prim('sphere', loc=(0,0,1.60), scale=(0.9,0.85,1.1), r=0.16, mat=skin)
    prim('sphere', loc=(-0.07,0.10,1.62), scale=(1,0.6,0.9), r=0.05, mat=glow)
    prim('sphere', loc=( 0.07,0.10,1.62), scale=(1,0.6,0.9), r=0.05, mat=glow)
    # Neck
    prim('cylinder', loc=(0,0,1.44), scale=(1,1,1), r=0.07, h=0.20, mat=hull)
    # Torso
    prim('sphere', loc=(0,0,1.15), scale=(1.3,0.85,1.0), r=0.25, mat=hull)
    # Reactor core
    prim('sphere', loc=(0,0.18,1.15), scale=(0.7,0.3,0.6), r=0.10, mat=glow)
    # Abdomen
    prim('cylinder', loc=(0,0,0.90), scale=(1,1,1), r=0.19, h=0.30, mat=hull)
    # Pelvis
    prim('sphere', loc=(0,0,0.73), scale=(1.4,0.85,0.65), r=0.18, mat=hull)

    # Shoulders
    for side in [-1,1]:
        prim('sphere', loc=(side*0.30,0,1.36), scale=(1,0.85,0.80), r=0.12, mat=hull)
    # Upper arms
    for side in [-1,1]:
        prim('cylinder', loc=(side*0.30,0,1.17), scale=(1,1,1), r=0.08, h=0.30,
             rot=(0,0,side*0.20), mat=hull)
    # Forearms
    for side in [-1,1]:
        prim('cylinder', loc=(side*0.32,0,0.93), scale=(1,1,1), r=0.07, h=0.28,
             rot=(0,0,side*0.12), mat=skin)
    # Weapon (energy blade right hand)
    prim('sphere', loc=(0.33,0,0.76), scale=(1,1,1), r=0.07, mat=skin)
    prim('cylinder', loc=(0.38,0.10,0.65), scale=(1,1,1), r=0.025, h=0.40,
         rot=(0.5,0,0), mat=blade)
    # Shield (left)
    prim('sphere', loc=(-0.33,0.10,0.90), scale=(0.3,0.1,0.6), r=0.22, mat=hull)

    # Legs
    for side in [-1,1]:
        prim('sphere', loc=(side*0.14,0,0.70), scale=(1,1,1), r=0.07, mat=hull)
        prim('cylinder', loc=(side*0.13,0,0.53), scale=(1,1,1), r=0.09, h=0.34,
             rot=(0,0,side*0.06), mat=hull)
        prim('sphere', loc=(side*0.12,0.02,0.35), scale=(1,0.9,0.8), r=0.07, mat=hull)
        prim('cylinder', loc=(side*0.11,0,0.19), scale=(1,1,1), r=0.075, h=0.30, mat=hull)
        prim('sphere', loc=(side*0.11,0.07,0.04), scale=(1.1,2.0,0.5), r=0.07, mat=hull)

    ob = join_all("race_enemy")
    add_animations(ob)
    export(ob, "race_enemy.glb")


# ── Main ───────────────────────────────────────────────────────────────

print("\n=== Generating enemy models ===")
print(f"Output: {OUT}\n")

make_skeleton()
make_ghoul()
make_bandit()
make_animated_armor()
make_shadow()
make_race_enemy()

print("\nAll enemies done.")
