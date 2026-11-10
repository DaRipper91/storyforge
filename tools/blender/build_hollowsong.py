"""hollowsong bespoke hero: concept-derived layered clothing and articulated humanoid rig.
Run with Blender -- <humanoid.glb> <scratch-output-directory>.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from humanoid_a_elf_draft import elf_hero

CONFIG = {'seed': 41, 'skin': (0.46, 0.42, 0.42), 'cloth': (0.035, 0.04, 0.065), 'overlay': (0.045, 0.055, 0.1), 'leather': (0.035, 0.03, 0.035), 'trim': (0.4, 0.36, 0.28), 'hair': (0.5, 0.49, 0.5), 'eye': (0.19, 0.24, 0.27), 'skirt': 0.24, 'mantle': 0.3, 'hair_length': 0.43}
elf_hero(sys.argv[-2], sys.argv[-1], "hollowsong", CONFIG)
