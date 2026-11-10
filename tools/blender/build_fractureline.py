"""Build fractureline from its approved concept; unchanged shared humanoid rig.
Run: blender -b -P build_fractureline.py -- <humanoid.glb> <out_dir>.
All race geometry uses Hero_* names; see humanoid_c_common.py for construction.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from humanoid_c_common import build_hero

CONFIG = {'id': 'fractureline', 'seed': 111, 'cloth': (0.18, 0.075, 0.065), 'plate': (0.11, 0.12, 0.13), 'skin': (0.49, 0.34, 0.25), 'hair': (0.045, 0.035, 0.03), 'split': True, 'hem': 0.36}

if __name__ == "__main__":
    build_hero(sys.argv[-2], sys.argv[-1], CONFIG)
