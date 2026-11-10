"""ashcrown bespoke hero: concept-derived layered clothing and articulated humanoid rig.
Run with Blender -- <humanoid.glb> <scratch-output-directory>.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from humanoid_a_elf_draft import elf_hero

CONFIG = {'seed': 53, 'skin': (0.69, 0.56, 0.5), 'cloth': (0.58, 0.52, 0.4), 'overlay': (0.34, 0.28, 0.38), 'leather': (0.39, 0.34, 0.28), 'trim': (0.54, 0.4, 0.2), 'hair': (0.72, 0.64, 0.55), 'eye': (0.32, 0.32, 0.41), 'skirt': 0.2, 'mantle': 0.23, 'hair_length': 0.46, 'crown': True}
elf_hero(sys.argv[-2], sys.argv[-1], "ashcrown", CONFIG)
