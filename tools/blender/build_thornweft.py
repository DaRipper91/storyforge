"""thornweft bespoke hero: concept-derived layered clothing and articulated humanoid rig.
Run with Blender -- <humanoid.glb> <scratch-output-directory>.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from humanoid_a_elf_draft import elf_hero

CONFIG = {'seed': 47, 'skin': (0.51, 0.34, 0.24), 'cloth': (0.075, 0.1, 0.045), 'overlay': (0.1, 0.12, 0.055), 'leather': (0.13, 0.075, 0.036), 'trim': (0.34, 0.25, 0.12), 'hair': (0.11, 0.058, 0.025), 'eye': (0.26, 0.3, 0.065), 'skirt': 0.5, 'hair_length': 0.38, 'bark': True}
elf_hero(sys.argv[-2], sys.argv[-1], "thornweft", CONFIG)
