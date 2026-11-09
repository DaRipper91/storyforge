"""Verify every relative link, image src and #anchor in README.md resolves."""
import re, sys
from pathlib import Path
from urllib.parse import unquote
repo = Path(__file__).resolve().parents[3]
txt = (repo / "README.md").read_text(encoding="utf-8")
ids = set(re.findall(r'(?:id|name)="([^"]+)"', txt))
for h in re.findall(r'^#{1,6}\s+(.*)$', txt, re.M):
    slug = re.sub(r'[^\w\- ]', '', h.lower().strip()).replace(' ', '-')
    ids.add(slug)
targets = re.findall(r'\]\(([^)\s]+)\)', txt) + re.findall(r'(?:src|href)="([^"]+)"', txt)
bad = 0
for t in targets:
    if t.startswith(("http://", "https://", "mailto:")):
        continue
    path, _, frag = t.partition("#")
    if path and not (repo / unquote(path)).exists():
        print("MISSING", t); bad += 1
    if frag and not path and frag not in ids:
        print("BAD ANCHOR", t); bad += 1
print(f"checked {len(targets)} targets, {bad} problems")
sys.exit(bad)
