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
    "~/Downloads/quaternius_animals/Blends"
)
MONSTER_BLEND_DIR = os.path.expanduser(
    "~/Downloads/quaternius_monsters/Blends"
)
WEAPON_BLEND_DIR = os.path.expanduser(
    "~/Downloads/quaternius_weapons/Blends"
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
    # NOTE: pre-animated glTF exports are already in assets/models/animals/ —
    # only run this if you need GLB from blend (e.g. to add custom animations).
    "Husky.blend":      "animals/dog.glb",
    "Wolf.blend":       "animals/wolf.glb",
    "ShibaInu.blend":   "animals/cat.glb",
    "Fox.blend":        "animals/fox.glb",
    "Horse.blend":      "animals/horse.glb",
    "Horse_White.blend":"animals/horse_white.glb",
    "Bull.blend":       "animals/bull.glb",
    "Deer.blend":       "animals/deer.glb",
    "Stag.blend":       "animals/stag.glb",
    "Cow.blend":        "animals/cow.glb",
    "Donkey.blend":     "animals/donkey.glb",
    "Alpaca.blend":     "animals/alpaca.glb",
}

# quaternius_monsters/Blends — download from animatedmonster pack first
MONSTER_MAP = {
    "Dragon.blend":   "monsters/dragon.glb",
    "Bat.blend":      "monsters/bat.glb",
    "Skeleton.blend": "monsters/skeleton_animated.glb",
    "Slime.blend":    "monsters/slime.glb",
}

# quaternius_weapons/Blends — download from medievalweapons pack first
WEAPON_MAP = {
    "Sword.blend":              "weapons/sword.glb",
    "Sword_2.blend":            "weapons/sword_2.glb",
    "Sword_Big.blend":          "weapons/sword_big.glb",
    "Sword_Golden.blend":       "weapons/sword_golden.glb",
    "Claymore.blend":           "weapons/claymore.glb",
    "Axe.blend":                "weapons/axe.glb",
    "Axe_Double.blend":         "weapons/axe_double.glb",
    "Axe_Small.blend":          "weapons/axe_small.glb",
    "Dagger.blend":             "weapons/dagger.glb",
    "Dagger_2.blend":           "weapons/dagger_2.glb",
    "Hammer_Double.blend":      "weapons/hammer.glb",
    "Hammer_Small.blend":       "weapons/hammer_small.glb",
    "Scythe.blend":             "weapons/scythe.glb",
    "Spear.blend":              "weapons/spear.glb",
    "Bow_Wooden.blend":         "weapons/bow.glb",
    "Bow_Wooden2.blend":        "weapons/bow_2.glb",
    "Bow_Evil.blend":           "weapons/bow_evil.glb",
    "Bow_Golden.blend":         "weapons/bow_golden.glb",
    "Arrow.blend":              "weapons/arrow.glb",
    "Shield_Heater.blend":      "weapons/shield_heater.glb",
    "Shield_Heater_2.blend":    "weapons/shield_heater_2.glb",
    "Shield_Round.blend":       "weapons/shield_round.glb",
    "Shield_Round_2.blend":     "weapons/shield_round_2.glb",
    "Shield_Celtic_Golden.blend":"weapons/shield_celtic.glb",
}


def export_blend(blend_path: str, out_glb: str):
    """Load a .blend, export everything as GLB."""
    if not os.path.exists(blend_path):
        print(f"[SKIP] Not found: {blend_path}")
        return False

    os.makedirs(os.path.dirname(out_glb), exist_ok=True)

    print(f"[CONVERT] {os.path.basename(blend_path)} → {os.path.relpath(out_glb, PROJECT_MODELS)}")

    bpy.ops.wm.open_mainfile(filepath=blend_path)

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

    maps = [
        (CHARACTER_MAP, CHAR_BLEND_DIR),
        (ANIMAL_MAP,    ANIMAL_BLEND_DIR),
        (MONSTER_MAP,   MONSTER_BLEND_DIR),
        (WEAPON_MAP,    WEAPON_BLEND_DIR),
    ]

    for asset_map, blend_dir in maps:
        for src_name, dest_rel in asset_map.items():
            src = os.path.join(blend_dir, src_name)
            dst = os.path.join(PROJECT_MODELS, dest_rel)
            if export_blend(src, dst):
                ok += 1
            else:
                fail += 1

    print(f"\n=== Done: {ok} exported, {fail} skipped ===")


run()
