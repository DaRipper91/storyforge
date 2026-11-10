"""Build emberpact from its approved concept; unchanged shared humanoid rig.
Run: blender -b -P build_emberpact.py -- <humanoid.glb> <out_dir>.
All race geometry uses Hero_* names; see humanoid_c_common.py for construction.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from humanoid_c_common import build_hero

CONFIG = {'id': 'emberpact', 'seed': 121, 'cloth': (0.2, 0.045, 0.031), 'plate': (0.16, 0.155, 0.14), 'skin': (0.39, 0.13, 0.075), 'hair': (0.018, 0.014, 0.012), 'hem': 0.46, 'eye': (0.8, 0.33, 0.025)}

if __name__ == "__main__":
    build_hero(sys.argv[-2], sys.argv[-1], CONFIG)
