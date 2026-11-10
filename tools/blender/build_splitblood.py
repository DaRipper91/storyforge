"""Splitblood bespoke hero: reference-led layered costume, sculpted face and finger rig.
Run: blender -b -P splitblood.py -- <humanoid.glb> <outdir>."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from humanoid_b_common import build_hero

build_hero(sys.argv[-2], sys.argv[-1], {'seed': 61, 'skin': (0.4, 0.32, 0.23), 'cloth': (0.23, 0.09, 0.08), 'plate': (0.2, 0.17, 0.13), 'orc': True, 'slug': 'splitblood'})
