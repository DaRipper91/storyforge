"""Build fallenlight from its approved concept; unchanged shared humanoid rig.
Run: blender -b -P build_fallenlight.py -- <humanoid.glb> <out_dir>.
All race geometry uses Hero_* names; see humanoid_c_common.py for construction.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from humanoid_c_common import build_hero

CONFIG = {'id': 'fallenlight', 'seed': 131, 'cloth': (0.65, 0.59, 0.45), 'plate': (0.48, 0.34, 0.16), 'skin': (0.34, 0.21, 0.12), 'hair': (0.065, 0.045, 0.026), 'hem': 0.16, 'eye': (0.8, 0.65, 0.27), 'eye_emit': (0.6, 0.45, 0.2)}

if __name__ == "__main__":
    build_hero(sys.argv[-2], sys.argv[-1], CONFIG)
