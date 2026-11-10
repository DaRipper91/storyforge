"""Duskweft bespoke hero: reference-led layered costume, sculpted face and finger rig.
Run: blender -b -P duskweft.py -- <humanoid.glb> <outdir>."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from humanoid_b_common import build_hero

build_hero(sys.argv[-2], sys.argv[-1], {'seed': 67, 'skin': (0.54, 0.35, 0.25), 'cloth': (0.2, 0.1, 0.16), 'plate': (0.28, 0.25, 0.3), 'slug': 'duskweft'})
