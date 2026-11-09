"""Generate banner.svg and social-preview.svg from the real seed data."""
from __future__ import annotations

from atlas_lib import *  # noqa: F401,F403
from atlas_lib import (compass, defs, frame, load_room, plate, scale_bar, stars,
                       terrain, title_block, exit_tri, FEET_PER_CELL, SEED, ROOM_ID)
from common import ASSETS, REPO, svg_open, text, write


def legend(x, y):
    o = [text(x, y, "LEGEND", 10, "f-accent", extra='letter-spacing="3"')]
    items = [("wall", "wall"), ("floor", "floor"), ("door", "door"), ("table", "table (blocks)"),
             ("difficult", "difficult (half speed)"), ("pillar", "pillar (blocks)")]
    yy = y + 10
    for kind, label in items:
        o.append(terrain(kind, x, yy, 14))
        o.append(text(x + 24, yy + 11, label, 10.5, "f-text"))
        yy += 19
    o.append(exit_tri(x - 1, yy - 4, 18, True).replace("polygon", "polygon"))
    o.append(text(x + 24, yy + 11, "exit to adjacent room", 10.5, "f-text"))
    yy += 19
    o.append(f'<circle cx="{x+7}" cy="{yy+7}" r="5.5" class="f-highlight s-bg" stroke-width="1.4"/>')
    o.append(f'<circle cx="{x+7}" cy="{yy+7}" r="9" class="nofill s-accent" stroke-width="1"/>')
    o.append(text(x + 24, yy + 11, "NPC pin (seed x,y)", 10.5, "f-text"))
    yy += 19
    o.append(f'<line x1="{x}" y1="{yy+7}" x2="{x+16}" y2="{yy+7}" class="s-highlight" stroke-width="1.8" stroke-dasharray="5 4"/>')
    o.append(text(x + 24, yy + 11, "route (illustrative)", 10.5, "f-text"))
    return "".join(o) + "\n"


def banner() -> str:
    room, pins = load_room()
    W, H = 1280, 420
    cell = 37
    ox = (W - room["width"] * cell) / 2
    oy = 98
    s = svg_open(W, H, "StoryForge: The Feral World, Plate I",
                 f"Survey plate of Ironhold Keep ({room['width']}x{room['height']} cells) drawn from "
                 f"data/seeds/default_campaign.json, with {len(pins)} NPC pins at their seed coordinates.",
                 motion=True)
    s += defs()
    s += frame(W, H)
    mapbox = (ox - 40, oy - 20, ox + room["width"] * cell + 40, oy + room["height"] * cell + 20)
    s += stars([mapbox, (30, 90, 440, 390), (850, 90, 1250, 390), (420, 20, 860, 92)], W, H)
    s += title_block(W / 2, 56, 38, 77, 14, 12, 5)
    s += f'<line x1="{W/2-300}" y1="73" x2="{W/2-130}" y2="73" class="s-border" stroke-width=".8"/>\n'
    s += f'<line x1="{W/2+130}" y1="73" x2="{W/2+300}" y2="73" class="s-border" stroke-width=".8"/>\n'
    s += plate(room, pins, ox, oy, cell)
    # left column
    s += legend(52, 118)
    ly = 330
    s += text(52, ly, "ROOM", 9, "f-muted", extra='letter-spacing="2"') + text(110, ly, ROOM_ID, 10.5, "f-text")
    s += text(52, ly + 16, "GRID", 9, "f-muted", extra='letter-spacing="2"') + text(110, ly + 16, f"{room['width']} x {room['height']} cells, {FEET_PER_CELL} ft per cell", 10.5, "f-text")
    s += text(52, ly + 32, "PINS", 9, "f-muted", extra='letter-spacing="2"') + text(110, ly + 32, f"{len(pins)} NPCs", 10.5, "f-text")
    s += text(52, ly + 48, "SRC", 9, "f-muted", extra='letter-spacing="2"') + text(110, ly + 48, "data/seeds/default_campaign.json", 10.5, "f-text")
    # right column
    rcx = 1055
    s += text(rcx + 3, 124, "PLATE I", 24, "f-highlight", "disp", "middle", 'font-weight="bold" letter-spacing="6"')
    s += text(rcx, 142, "SURVEY OF IRONHOLD KEEP", 9.5, "f-muted", anchor="middle", extra='letter-spacing="1.5"')
    s += compass(rcx, 222, 44)
    s += scale_bar(rcx - 2 * cell, 296, cell)
    exits = {}
    for k, v in room["exits"].items():
        x, y = k.split(",")
        exits.setdefault((v, "top edge" if y == "0" else "bottom edge"), []).append(f"({x},{y})")
    yy = 346
    for (dest, edge), cells in exits.items():
        s += text(880, yy, f"{edge} {' '.join(cells)}", 10, "f-muted")
        s += text(1034, yy, "-> " + dest, 10, "f-text")
        yy += 16
    return s + "</svg>\n"


def social() -> str:
    room, pins = load_room()
    W, H = 1280, 640
    cell = 44
    ox = (W - room["width"] * cell) / 2
    oy = 214
    s = svg_open(W, H, "StoryForge: The Feral World",
                 "Social preview. Survey plate of Ironhold Keep drawn from the real seed data.", motion=False)
    s += defs()
    s += frame(W, H)
    mapbox = (ox - 50, oy - 24, ox + room["width"] * cell + 50, oy + room["height"] * cell + 30)
    s += stars([mapbox, (330, 30, 950, 200)], W, H, n=70, seed=11)
    s += title_block(W / 2, 112, 80, 156, 28, 18, 8)
    s += plate(room, pins, ox, oy, cell, lab=10)
    s += text(180, 330, "PLATE I", 30, "f-highlight", "disp", "middle", 'font-weight="bold" letter-spacing="6"')
    s += text(180, 354, "IRONHOLD KEEP", 12, "f-muted", anchor="middle", extra='letter-spacing="2"')
    s += compass(1100, 345, 54)
    s += scale_bar(1100 - 2 * cell, 450, cell)
    s += text(W / 2, 610, "Gemini narrates. Python decides.", 22, "f-text", "disp", "middle", 'style="font-variant:small-caps" letter-spacing="3"')
    return s + "</svg>\n"


if __name__ == "__main__":
    write(ASSETS / "banner.svg", banner())
    write(ASSETS / "social-preview.svg", social())
