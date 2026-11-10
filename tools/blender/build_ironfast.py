"""Ironfast bespoke hero: reference-led layered costume, sculpted face and finger rig.
Run: blender -b -P ironfast.py -- <humanoid.glb> <outdir>."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from humanoid_b_common import build_hero

build_hero(sys.argv[-2], sys.argv[-1], {'seed': 51, 'skin': (0.39, 0.27, 0.19), 'cloth': (0.18, 0.13, 0.08), 'plate': (0.58, 0.49, 0.36), 'dwarf': True, 'slug': 'ironfast'})
