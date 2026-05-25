"""
Convert Quaternius .blend files → .glb and place them in the StoryForge project.
Run headless:  blender --background --python scripts/blender/convert_quaternius.py
"""

import bpy
import os
import sys

# ─── Mapping: source blend → dest filename (relative to assets/models/) ──────

CHAR_BLEND_DIR = os.path.expanduser(
    "~/Downloads/quaternius_characters/Humanoid Rig/Individual Characters/Blend"
)
ANIMAL_BLEND_DIR = os.path.expanduser(
    "~/Downloads/quaternius_animals_blends"
)

PROJECT_MODELS = os.path.expanduser(
    "~/Projects/storyforge/godot/assets/models"
)

CHARACTER_MAP = {
    # NPC models
    "Casual.blend":     "humanoid/npc_default.glb",
    "King.blend":       "humanoid/npc_royal.glb",
    "Adventurer.blend": "humanoid/npc_warrior.glb",
    "Suit.blend":       "humanoid/npc_mage.glb",
    "Punk.blend":       "humanoid/npc_performer.glb",
    # Player race group models
    "Farmer.blend":     "player/humanoid.glb",
    "Swat.blend":       "player/primal.glb",
    "Casual2.blend":    "player/eldritch.glb",
    "Worker.blend":     "player/mechanical.glb",
    "Spacesuit.blend":  "player/cosmic.glb",
}

ANIMAL_MAP = {
    "Husky.blend":    "animals/dog.glb",
    "Wolf.blend":     "animals/wolf.glb",
    "ShibaInu.blend": "animals/cat.glb",    # close enough for placeholder
    "Fox.blend":      "animals/bear.glb",   # placeholder until real bear found
}


def export_blend(blend_path: str, out_glb: str):
    """Load a .blend, export everything as GLB."""
    if not os.path.exists(blend_path):
        print(f"[SKIP] Not found: {blend_path}")
        return False

    os.makedirs(os.path.dirname(out_glb), exist_ok=True)

    print(f"[CONVERT] {os.path.basename(blend_path)} → {os.path.relpath(out_glb, PROJECT_MODELS)}")

    # Load the file fresh
    bpy.ops.wm.open_mainfile(filepath=blend_path)

    # Select everything
    bpy.ops.object.select_all(action='SELECT')

    bpy.ops.export_scene.gltf(
        filepath=out_glb,
        export_format='GLB',
        use_selection=False,
        export_animations=True,
        export_animation_mode='ACTIONS',   # export all actions (Blender 5.1)
        export_extra_animations=True,      # include actions not in NLA
        export_nla_strips=True,
        export_nla_strips_merged_animation_name='Idle',
        export_skins=True,
        export_morph=True,
        export_lights=False,
        export_cameras=False,
        export_yup=True,
    )
    print(f"[OK]  → {out_glb}")
    return True


def run():
    ok = 0
    fail = 0

    for src_name, dest_rel in CHARACTER_MAP.items():
        src = os.path.join(CHAR_BLEND_DIR, src_name)
        dst = os.path.join(PROJECT_MODELS, dest_rel)
        if export_blend(src, dst):
            ok += 1
        else:
            fail += 1

    for src_name, dest_rel in ANIMAL_MAP.items():
        src = os.path.join(ANIMAL_BLEND_DIR, src_name)
        dst = os.path.join(PROJECT_MODELS, dest_rel)
        if export_blend(src, dst):
            ok += 1
        else:
            fail += 1

    print(f"\n=== Done: {ok} exported, {fail} skipped ===")


run()
