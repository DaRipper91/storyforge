"""Build scaleworn from its approved concept; unchanged shared humanoid rig.
Run: blender -b -P build_scaleworn.py -- <humanoid.glb> <out_dir>.
All race geometry uses Hero_* names; see humanoid_c_common.py for construction.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from humanoid_c_common import build_hero

CONFIG = {'id': 'scaleworn', 'seed': 141, 'cloth': (0.09, 0.065, 0.048), 'plate': (0.16, 0.18, 0.2), 'skin': (0.26, 0.13, 0.055), 'hair': (0.04, 0.03, 0.015), 'hem': 0.47, 'eye': (0.85, 0.38, 0.025)}

if __name__ == "__main__":
    build_hero(sys.argv[-2], sys.argv[-1], CONFIG)
