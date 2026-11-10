"""veilborn bespoke hero: concept-derived layered clothing and articulated humanoid rig.
Run with Blender -- <humanoid.glb> <scratch-output-directory>.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from humanoid_a_elf_draft import elf_hero

CONFIG = {'seed': 43, 'skin': (0.23, 0.17, 0.25), 'cloth': (0.022, 0.017, 0.026), 'overlay': (0.1, 0.045, 0.13), 'leather': (0.025, 0.018, 0.025), 'trim': (0.3, 0.26, 0.23), 'hair': (0.65, 0.62, 0.64), 'eye': (0.28, 0.12, 0.35), 'skirt': 0.55, 'hair_length': 0.4}
elf_hero(sys.argv[-2], sys.argv[-1], "veilborn", CONFIG)
