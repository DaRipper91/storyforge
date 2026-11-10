"""Coreborn bespoke hero: reference-led layered costume, sculpted face and finger rig.
Run: blender -b -P coreborn.py -- <humanoid.glb> <outdir>."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from humanoid_b_common import build_hero

build_hero(sys.argv[-2], sys.argv[-1], {'seed': 53, 'skin': (0.22, 0.22, 0.25), 'cloth': (0.11, 0.09, 0.085), 'plate': (0.14, 0.13, 0.13), 'dwarf': True, 'eye': (0.15, 0.48, 0.72), 'slug': 'coreborn'})
