"""Plate drawing primitives shared by banner + social preview."""
from __future__ import annotations

import json
import math
import random

from common import REPO, esc, text

SEED = REPO / "data" / "seeds" / "default_campaign.json"
ROOM_ID = "ironhold_keep"
FEET_PER_CELL = 5  # core/grid.py FEET_PER_CELL


def load_room():
    d = json.loads(SEED.read_text())
    room = d["rooms"][ROOM_ID]
    pins = [
        (k, n["position"]["x"], n["position"]["y"])
        for k, n in d["npcs"].items()
        if n.get("room_id") == ROOM_ID
    ]
    pins.sort(key=lambda p: (p[2], p[1]))
    return room, pins


def defs() -> str:
    return (
        '<defs>\n'
        '<pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" '
        'patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" '
        'class="s-border" stroke-width="1" opacity=".55"/></pattern>\n'
        '</defs>\n'
    )


def terrain(kind: str, x: float, y: float, s: float, grid: bool = True) -> str:
    """Draw one terrain cell of size s at (x, y)."""
    o = []
    r = f'x="{x:g}" y="{y:g}" width="{s:g}" height="{s:g}"'
    if kind == "wall":
        o.append(f'<rect {r} class="f-surface"/>')
        o.append(f'<rect {r} fill="url(#hatch)"/>')
        return "".join(o) + "\n"
    sw = .6 if grid else 0
    o.append(f'<rect {r} class="f-surface s-border" fill-opacity=".38" stroke-width="{sw}" stroke-opacity=".35"/>')
    cx, cy = x + s / 2, y + s / 2
    if kind == "door":
        o.append(f'<rect x="{x + s*.12:g}" y="{cy - s*.11:g}" width="{s*.76:g}" height="{s*.22:g}" class="f-accent"/>')
    elif kind == "table":
        o.append(f'<rect x="{x + s*.16:g}" y="{y + s*.28:g}" width="{s*.68:g}" height="{s*.44:g}" class="f-surface s-accent" stroke-width="1.2"/>')
        o.append(f'<line x1="{x + s*.16:g}" y1="{y + s*.28:g}" x2="{x + s*.84:g}" y2="{y + s*.72:g}" class="s-accent" stroke-width=".6" opacity=".6"/>')
    elif kind == "difficult":
        for i, (dx, dy) in enumerate([(.25, .3), (.7, .25), (.5, .5), (.28, .72), (.72, .7)]):
            o.append(f'<circle cx="{x + s*dx:g}" cy="{y + s*dy:g}" r="{max(.9, s*.045):g}" class="f-muted"/>')
    elif kind == "pillar":
        o.append(f'<circle cx="{cx:g}" cy="{cy:g}" r="{s*.34:g}" class="f-surface s-border" stroke-width="1.4"/>')
        o.append(f'<circle cx="{cx:g}" cy="{cy:g}" r="{s*.17:g}" class="nofill s-border" stroke-width=".8"/>')
    return "".join(o) + "\n"


def exit_tri(x: float, y: float, s: float, up: bool) -> str:
    cx = x + s / 2
    if up:
        pts = f"{cx - s*.2:g},{y + s*.7:g} {cx + s*.2:g},{y + s*.7:g} {cx:g},{y + s*.22:g}"
    else:
        pts = f"{cx - s*.2:g},{y + s*.3:g} {cx + s*.2:g},{y + s*.3:g} {cx:g},{y + s*.78:g}"
    return f'<polygon points="{pts}" class="f-accent"/>\n'


def plate(room, pins, ox: float, oy: float, cell: float, lab: float = 8.5, route=("cyrus", "snowie")) -> str:
    W, H = room["width"], room["height"]
    o = ['<g id="plate">\n']
    for i, c in enumerate(room["cells"]):
        x, y = i % W, i // W
        o.append(terrain(c["terrain"], ox + x * cell, oy + y * cell, cell))
    o.append(f'<rect x="{ox:g}" y="{oy:g}" width="{W*cell:g}" height="{H*cell:g}" class="nofill s-border" stroke-width="1.6"/>\n')
    # exits
    for key in room["exits"]:
        ex, ey = (int(v) for v in key.split(","))
        o.append(exit_tri(ox + ex * cell, oy + ey * cell, cell, up=(ey == 0)))
    # ticks + coordinate labels
    for x in range(W):
        cx = ox + x * cell + cell / 2
        o.append(f'<line x1="{cx:g}" y1="{oy-4:g}" x2="{cx:g}" y2="{oy:g}" class="s-border" stroke-width="1"/>')
        o.append(f'<line x1="{cx:g}" y1="{oy+H*cell:g}" x2="{cx:g}" y2="{oy+H*cell+4:g}" class="s-border" stroke-width="1"/>')
        o.append(text(cx, oy - 7, str(x), 8, "f-muted", anchor="middle"))
    for y in range(H):
        cy = oy + y * cell + cell / 2
        o.append(f'<line x1="{ox-4:g}" y1="{cy:g}" x2="{ox:g}" y2="{cy:g}" class="s-border" stroke-width="1"/>')
        o.append(f'<line x1="{ox+W*cell:g}" y1="{cy:g}" x2="{ox+W*cell+4:g}" y2="{cy:g}" class="s-border" stroke-width="1"/>')
        o.append(text(ox - 8, cy + 3, str(y), 8, "f-muted", anchor="end"))
    o.append("\n")
    pos = {k: (ox + (x + .5) * cell, oy + (y + .5) * cell) for k, x, y in pins}
    # dashed route between two pins, arcing over the pillar row
    if all(k in pos for k in route):
        (ax, ay), (bx, by) = pos[route[0]], pos[route[1]]
        r = cell * .16
        d = (f"M {ax + r:.1f} {ay - r:.1f} Q {(ax + bx)/2:.1f} {oy + cell*.62:.1f} {bx - r:.1f} {by - r:.1f}")
        o.append(f'<path id="route" d="{d}" class="nofill s-highlight march" stroke-width="1.8" stroke-dasharray="5 4" stroke-linecap="round"/>\n')
    # pins
    for n, (k, x, y) in enumerate(pins):
        cx, cy = pos[k]
        delay = f'style="animation-delay:{(n * 0.37) % 3.2:.2f}s"'
        o.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{cell*.24:.1f}" class="nofill s-accent pulse" stroke-width="1.2" {delay}/>')
        o.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{cell*.135:.1f}" class="f-highlight s-bg" stroke-width="1.4"/>')
        o.append(text(cx, cy + cell * .43, k, lab, "f-text", anchor="middle"))
    o.append("</g>\n")
    return "".join(o)


def compass(cx: float, cy: float, r: float) -> str:
    o = [f'<g id="compass">\n']
    o.append(f'<circle cx="{cx:g}" cy="{cy:g}" r="{r:g}" class="nofill s-border" stroke-width="1"/>')
    o.append(f'<circle cx="{cx:g}" cy="{cy:g}" r="{r*.78:g}" class="nofill s-border" stroke-width=".6" stroke-dasharray="2 3"/>')
    def star(rad_long, rad_short, n, rot, cls):
        pts = []
        for i in range(n * 2):
            a = math.radians(rot + i * 180 / n)
            rr = rad_long if i % 2 == 0 else rad_short
            pts.append(f"{cx + rr*math.sin(a):.1f},{cy - rr*math.cos(a):.1f}")
        return f'<polygon points="{" ".join(pts)}" class="{cls}"/>'
    o.append(star(r * .62, r * .16, 4, 45, "f-border"))
    o.append(star(r * 1.0, r * .2, 4, 0, "f-accent"))
    o.append(f'<circle cx="{cx:g}" cy="{cy:g}" r="{r*.07:g}" class="f-bg"/>')
    o.append(text(cx, cy - r - 6, "N", 13, "f-highlight", "disp", "middle", 'font-weight="bold"'))
    o.append("</g>\n")
    return "".join(o)


def scale_bar(x: float, y: float, cell: float, cells: int = 4) -> str:
    o = ['<g id="scale">\n']
    for i in range(cells):
        cls = "f-accent" if i % 2 == 0 else "f-bg"
        o.append(f'<rect x="{x + i*cell:g}" y="{y:g}" width="{cell:g}" height="6" class="{cls} s-accent" stroke-width="1"/>')
    for i in range(0, cells + 1, 2):
        o.append(text(x + i * cell, y + 19, f"{i*FEET_PER_CELL}", 9, "f-muted", anchor="middle"))
    o.append(text(x + cells * cell + 8, y + 6, "ft", 9, "f-muted"))
    o.append("</g>\n")
    return "".join(o)


def stars(rects_excluded, w, h, n=46, seed=7) -> str:
    rnd = random.Random(seed)
    o = ['<g id="stars">\n']
    placed = 0
    while placed < n:
        x, y = rnd.uniform(24, w - 24), rnd.uniform(24, h - 24)
        if any(a <= x <= c and b <= y <= d for a, b, c, d in rects_excluded):
            continue
        big = rnd.random() < .25
        o.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{1.5 if big else .9}" class="f-highlight twinkle" '
            f'style="animation-delay:{rnd.uniform(0, 5):.2f}s" opacity=".3"/>'
        )
        placed += 1
    o.append("\n</g>\n")
    return "".join(o)


def frame(w, h) -> str:
    o = [f'<rect width="{w}" height="{h}" class="f-bg"/>\n']
    o.append(f'<rect x="6" y="6" width="{w-12}" height="{h-12}" class="nofill s-border" stroke-width="1.6"/>\n')
    o.append(f'<rect x="13" y="13" width="{w-26}" height="{h-26}" class="nofill s-border" stroke-width=".6"/>\n')
    for x in range(40, w - 30, 40):
        o.append(f'<line x1="{x}" y1="6" x2="{x}" y2="13" class="s-border" stroke-width=".8"/>')
        o.append(f'<line x1="{x}" y1="{h-13}" x2="{x}" y2="{h-6}" class="s-border" stroke-width=".8"/>')
    for y in range(40, h - 30, 40):
        o.append(f'<line x1="6" y1="{y}" x2="13" y2="{y}" class="s-border" stroke-width=".8"/>')
        o.append(f'<line x1="{w-13}" y1="{y}" x2="{w-6}" y2="{y}" class="s-border" stroke-width=".8"/>')
    return "".join(o) + "\n"


def title_block(cx, y_title, size_title, y_sub, size_sub, spacing_t, spacing_s) -> str:
    o = []
    o.append(text(cx + spacing_t / 2, y_title, "STORYFORGE", size_title, "f-highlight ink", "disp", "middle",
                  f'font-weight="bold" letter-spacing="{spacing_t}"'))
    o.append(text(cx + spacing_s / 2, y_sub, "The Feral World", size_sub, "f-accent", "disp", "middle",
                  f'letter-spacing="{spacing_s}" style="font-variant:small-caps"'))
    return "".join(o) + "\n"
