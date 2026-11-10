"""Build glitchkin from its approved concept; unchanged shared humanoid rig.
Run: blender -b -P build_glitchkin.py -- <humanoid.glb> <out_dir>.
All race geometry uses Hero_* names; see humanoid_c_common.py for construction.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from humanoid_c_common import build_hero

CONFIG = {'id': 'glitchkin', 'seed': 101, 'cloth': (0.38, 0.33, 0.24), 'plate': (0.36, 0.25, 0.11), 'skin': (0.57, 0.34, 0.22), 'hair': (0.6, 0.56, 0.47), 'hem': 0.73}

if __name__ == "__main__":
    build_hero(sys.argv[-2], sys.argv[-1], CONFIG)
