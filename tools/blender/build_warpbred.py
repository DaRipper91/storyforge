"""Warpbred bespoke hero: reference-led layered costume, sculpted face and finger rig.
Run: blender -b -P warpbred.py -- <humanoid.glb> <outdir>."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from humanoid_b_common import build_hero

build_hero(sys.argv[-2], sys.argv[-1], {'seed': 57, 'skin': (0.27, 0.285, 0.19), 'cloth': (0.18, 0.07, 0.085), 'plate': (0.29, 0.28, 0.25), 'orc': True, 'slug': 'warpbred'})
