#!/usr/bin/env python3
"""
Generate 800×1120 PNG portrait cards for all 35 StoryForge races.

Run from the project root:
    uv run python scripts/generate_portraits.py

Output: godot/assets/characters/<race_id>.png
"""
from PIL import Image, ImageDraw, ImageFont
import os, math

OUT = os.path.join(os.path.dirname(__file__), "..", "godot", "assets", "characters")

SCALE = 4
W, H = 200 * SCALE, 280 * SCALE   # 800 × 1120

def s(n): return int(n * SCALE)

# ── Helpers ──────────────────────────────────────────────────────────────────

def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def _glow(d, cx, cy, r, col, a=60, layers=3):
    for i in range(layers):
        ri, ai = r + i * s(6), max(0, a - i * 18)
        d.ellipse([cx-ri, cy-ri, cx+ri, cy+ri], fill=(*col, ai))

def _vignette(img):
    v = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(v, "RGBA")
    for i in range(s(40)):
        a = int(i * 3.5 / SCALE)
        d.rectangle([i, i, W-i, H-i], outline=(0, 0, 0, a), width=1)
    img.alpha_composite(v)

def _frame(d, accent):
    d.rectangle([s(1), s(1), W-s(2), H-s(2)], outline=(*accent, 110), width=s(2))
    d.rectangle([s(4), s(4), W-s(5), H-s(5)], outline=(*accent, 40), width=s(1))

def _labels(d, name, group, accent):
    group_colors = {
        "Cosmic": "#9ac8ff", "Primal": "#ffffc0", "Eldritch": "#d8b4ff",
        "Mechanical": "#88ffcc", "Humanoid": "#ffaa66",
    }
    badge_col = _rgb(group_colors.get(group, "#ffffff"))

    try:
        small_font = ImageFont.load_default(size=s(9))
        name_font  = ImageFont.load_default(size=s(14))
    except Exception:
        small_font = name_font = None

    # Group badge — top-left
    d.rectangle([s(5), s(5), s(80), s(22)], fill=(0, 0, 0, 160))
    kw = {"font": small_font} if small_font else {}
    d.text((s(9), s(7)), group.upper(), fill=(*badge_col, 200), **kw)

    # Name bar — bottom
    d.rectangle([0, H-s(38), W, H], fill=(0, 0, 0, 195))
    d.line([0, H-s(38), W, H-s(38)], fill=(*accent, 100), width=s(1))

    kw2 = {"font": name_font} if name_font else {}
    if name_font:
        bbox = d.textbbox((0, 0), name.upper(), font=name_font)
        tw = bbox[2] - bbox[0]
        d.text(((W - tw) // 2, H - s(26)), name.upper(), fill=(*accent, 220), font=name_font)
    else:
        d.text((W // 2 - len(name) * s(3), H - s(24)), name.upper(), fill=(*accent, 220))


# ── Body-type draw functions ─────────────────────────────────────────────────

def draw_ethereal(d, img, cx, cy, base, accent, **_):
    _glow(d, cx, cy-s(18), s(60), accent, a=22, layers=5)
    d.ellipse([cx-s(55), cy-s(68), cx+s(55), cy+s(28)], fill=(*base, 190))
    _glow(d, cx, cy-s(22), s(28), accent, a=90, layers=2)
    for ex, ey, er in [(-s(22), cy-s(32), s(9)), (s(22), cy-s(32), s(9))]:
        _glow(d, cx+ex, ey, er, accent, a=140, layers=2)
        d.ellipse([cx+ex-s(5), ey-s(5), cx+ex+s(5), ey+s(5)], fill=(*accent, 240))
    for ox, ys in [(-s(28), cy+s(25)), (0, cy+s(30)), (s(28), cy+s(25))]:
        for j in range(4):
            a = 160 - j * 35
            d.ellipse([cx+ox-s(5), ys+j*s(9)-s(5), cx+ox+s(5), ys+j*s(9)+s(5)], fill=(*accent, a))

def draw_insectoid(d, img, cx, cy, base, accent, legs=6, **_):
    d.ellipse([cx-s(18), cy+s(12), cx+s(18), cy+s(52)], fill=(*base, 200))
    d.ellipse([cx-s(20), cy-s(18), cx+s(20), cy+s(18)], fill=(*base, 220))
    d.ellipse([cx-s(14), cy-s(52), cx+s(14), cy-s(18)], fill=(*base, 235))
    for ex, ey in [(-s(8), cy-s(40)), (s(8), cy-s(40))]:
        d.ellipse([cx+ex-s(4), ey-s(4), cx+ex+s(4), ey+s(4)], fill=(*accent, 240))
    d.line([cx-s(4), cy-s(52), cx-s(22), cy-s(78)], fill=(*accent, 200), width=s(2))
    d.line([cx+s(4), cy-s(52), cx+s(22), cy-s(78)], fill=(*accent, 200), width=s(2))
    d.ellipse([cx-s(25), cy-s(82), cx-s(18), cy-s(75)], fill=(*accent, 220))
    d.ellipse([cx+s(18), cy-s(82), cx+s(25), cy-s(75)], fill=(*accent, 220))
    for i in range(legs // 2):
        yl = cy - s(8) + i * s(14)
        d.line([cx-s(20), yl, cx-s(52), yl+s(8)],   fill=(*base, 185), width=s(2))
        d.line([cx-s(52), yl+s(8), cx-s(62), yl+s(22)], fill=(*base, 155), width=s(2))
        d.line([cx+s(20), yl, cx+s(52), yl+s(8)],   fill=(*base, 185), width=s(2))
        d.line([cx+s(52), yl+s(8), cx+s(62), yl+s(22)], fill=(*base, 155), width=s(2))

def draw_hulking(d, img, cx, cy, base, accent, **_):
    _glow(d, cx, cy, s(70), accent, a=18, layers=4)
    d.ellipse([cx-s(68), cy-s(18), cx+s(68), cy+s(58)], fill=(*base, 215))
    d.ellipse([cx-s(62), cy-s(42), cx-s(22), cy+s(12)], fill=(*base, 200))
    d.ellipse([cx+s(22), cy-s(42), cx+s(62), cy+s(12)], fill=(*base, 200))
    d.ellipse([cx-s(26), cy-s(78), cx+s(26), cy-s(18)], fill=(*base, 232))
    for ox, oy in [(-s(18), s(18)), (s(12), s(2)), (-s(4), s(38)), (s(24), s(24))]:
        _glow(d, cx+ox, cy+oy, s(7), accent, a=150, layers=2)
    for ex, ey in [(-s(11), cy-s(56)), (s(11), cy-s(56))]:
        d.ellipse([cx+ex-s(5), ey-s(5), cx+ex+s(5), ey+s(5)], fill=(*accent, 245))
    d.ellipse([cx-s(42), cy+s(48), cx-s(14), cy+s(80)], fill=(*base, 175))
    d.ellipse([cx+s(14), cy+s(48), cx+s(42), cy+s(80)], fill=(*base, 175))

def draw_predator(d, img, cx, cy, base, accent, has_tail=True, **_):
    _glow(d, cx, cy, s(38), accent, a=22, layers=3)
    d.ellipse([cx-s(38), cy-s(22), cx-s(12), cy+s(18)], fill=(*base, 195))
    d.ellipse([cx+s(12), cy-s(22), cx+s(38), cy+s(18)], fill=(*base, 195))
    d.ellipse([cx-s(20), cy-s(14), cx+s(20), cy+s(42)], fill=(*base, 222))
    d.ellipse([cx-s(17), cy-s(62), cx+s(21), cy-s(10)], fill=(*base, 232))
    for ex, ey in [(-s(9), cy-s(48)), (s(6), cy-s(48))]:
        d.ellipse([cx+ex-s(5), ey-s(5), cx+ex+s(5), ey+s(5)], fill=(*accent, 242))
    d.rectangle([cx-s(16), cy+s(36), cx-s(6), cy+s(75)], fill=(*base, 190))
    d.rectangle([cx+s(6),  cy+s(36), cx+s(16), cy+s(75)], fill=(*base, 190))
    if has_tail:
        for i, (ox, oy) in enumerate([(s(24),s(28)), (s(36),s(42)), (s(44),s(58)), (s(46),s(74))]):
            d.ellipse([cx+ox-s(6), cy+oy-s(6), cx+ox+s(6), cy+oy+s(6)], fill=(*base, 200-i*30))

def draw_avian(d, img, cx, cy, base, accent, **_):
    _glow(d, cx-s(55), cy, s(30), accent, a=18, layers=3)
    _glow(d, cx+s(55), cy, s(30), accent, a=18, layers=3)
    d.polygon([cx, cy-s(8), cx-s(88), cy-s(28), cx-s(78), cy+s(28), cx-s(8), cy+s(18)], fill=(*base, 175))
    d.polygon([cx, cy-s(8), cx+s(88), cy-s(28), cx+s(78), cy+s(28), cx+s(8), cy+s(18)], fill=(*base, 175))
    for ox in [-s(80), -s(62), -s(44)]:
        d.line([cx+ox//2, cy-s(2), cx+ox, cy+s(12)], fill=(*accent, 115), width=s(1))
    for ox in [s(80), s(62), s(44)]:
        d.line([cx+ox//2, cy-s(2), cx+ox, cy+s(12)], fill=(*accent, 115), width=s(1))
    d.ellipse([cx-s(16), cy-s(8),  cx+s(16), cy+s(38)], fill=(*base, 232))
    d.ellipse([cx-s(15), cy-s(58), cx+s(15), cy-s(8)],  fill=(*base, 242))
    for ox, h in [(-s(6), s(18)), (0, s(26)), (s(6), s(20))]:
        d.polygon([cx+ox-s(3), cy-s(58), cx+ox+s(3), cy-s(58), cx+ox, cy-s(58)-h], fill=(*accent, 205))
    for ex, ey in [(-s(7), cy-s(43)), (s(7), cy-s(43))]:
        d.ellipse([cx+ex-s(4), ey-s(4), cx+ex+s(4), ey+s(4)], fill=(*accent, 252))
    d.ellipse([cx-s(12), cy+s(34), cx-s(3), cy+s(64)], fill=(*base, 178))
    d.ellipse([cx+s(3),  cy+s(34), cx+s(12), cy+s(64)], fill=(*base, 178))

def draw_horror(d, img, cx, cy, base, accent, has_cape=False, has_bones=False, **_):
    _glow(d, cx, cy, s(28), accent, a=32, layers=4)
    if has_cape:
        d.polygon([cx, cy-s(28), cx-s(62), cy+s(38), cx-s(48), cy+s(78),
                   cx, cy+s(58), cx+s(48), cy+s(78), cx+s(62), cy+s(38)], fill=(*base, 115))
    d.ellipse([cx-s(35), cy-s(12), cx-s(12), cy+s(22)], fill=(*base, 185))
    d.ellipse([cx+s(12), cy-s(12), cx+s(35), cy+s(22)], fill=(*base, 185))
    d.ellipse([cx-s(14), cy-s(18), cx+s(14), cy+s(48)], fill=(*base, 222))
    d.ellipse([cx-s(17), cy-s(68), cx+s(17), cy-s(12)], fill=(*base, 232))
    if has_bones:
        for ox, oy in [(-s(16), -s(10)), (-s(16), s(8)), (s(16), -s(10)), (s(16), s(8))]:
            d.polygon([cx+ox-s(3), cy+oy, cx+ox+s(3), cy+oy, cx+ox, cy+oy-s(13)], fill=(*accent, 205))
    for ex, ey in [(-s(8), cy-s(50)), (s(8), cy-s(50))]:
        _glow(d, cx+ex, ey, s(5), accent, a=160, layers=2)
        d.ellipse([cx+ex-s(4), ey-s(4), cx+ex+s(4), ey+s(4)], fill=(*accent, 255))
    for i in range(3):
        d.line([cx-s(35)+i*SCALE, cy+s(22), cx-s(38)+i*s(4), cy+s(42)], fill=(*base, 155), width=s(1))
        d.line([cx+s(35)-i*SCALE, cy+s(22), cx+s(38)-i*s(4), cy+s(42)], fill=(*base, 155), width=s(1))
    d.rectangle([cx-s(11), cy+s(44), cx-s(3), cy+s(82)], fill=(*base, 182))
    d.rectangle([cx+s(3),  cy+s(44), cx+s(11), cy+s(82)], fill=(*base, 182))

def draw_arachnid(d, img, cx, cy, base, accent, **_):
    _glow(d, cx, cy, s(32), accent, a=22, layers=3)
    d.ellipse([cx-s(26), cy+s(18), cx+s(26), cy+s(68)], fill=(*base, 210))
    d.ellipse([cx-s(20), cy-s(22), cx+s(20), cy+s(28)], fill=(*base, 232))
    d.ellipse([cx-s(14), cy-s(52), cx+s(14), cy-s(18)], fill=(*base, 242))
    for ex, ey in [(-s(8), cy-s(42)), (-s(2), cy-s(47)), (s(4), cy-s(42)), (s(8), cy-s(47))]:
        d.ellipse([cx+ex-s(3), ey-s(3), cx+ex+s(3), ey+s(3)], fill=(*accent, 242))
    leg_data = [
        (-s(20),-s(8), -s(68),-s(28), -s(78),s(2)),  (-s(20),s(2),  -s(70),s(6),  -s(80),s(26)),
        (-s(20),s(12), -s(66),s(22),  -s(73),s(44)),  (-s(20),s(22), -s(58),s(36), -s(63),s(58)),
        ( s(20),-s(8),  s(68),-s(28),  s(78),s(2)),   ( s(20),s(2),   s(70),s(6),   s(80),s(26)),
        ( s(20),s(12),  s(66),s(22),   s(73),s(44)),  ( s(20),s(22),  s(58),s(36),  s(63),s(58)),
    ]
    for x1,y1,x2,y2,x3,y3 in leg_data:
        d.line([cx+x1, cy+y1, cx+x2, cy+y2], fill=(*base, 200), width=s(2))
        d.line([cx+x2, cy+y2, cx+x3, cy+y3], fill=(*base, 162), width=s(2))

def draw_mechanical(d, img, cx, cy, base, accent, gear=False, wires=False, **_):
    _glow(d, cx, cy, s(38), accent, a=28, layers=3)
    d.rectangle([cx-s(24), cy-s(18), cx+s(24), cy+s(38)], fill=(*base, 222))
    d.line([cx-s(24), cy+s(8),  cx+s(24), cy+s(8)],  fill=(*accent, 80), width=s(1))
    d.line([cx-s(24), cy+s(24), cx+s(24), cy+s(24)], fill=(*accent, 55), width=s(1))
    d.rectangle([cx-s(48), cy-s(24), cx-s(24), cy+s(10)], fill=(*base, 202))
    d.rectangle([cx+s(24), cy-s(24), cx+s(48), cy+s(10)], fill=(*base, 202))
    d.rectangle([cx-s(19), cy-s(66), cx+s(19), cy-s(18)], fill=(*base, 232))
    d.rectangle([cx-s(15), cy-s(54), cx+s(15), cy-s(42)], fill=(*accent, 185))
    _glow(d, cx, cy-s(48), s(13), accent, a=85, layers=2)
    if gear:
        for angle in range(0, 360, 45):
            rad = math.radians(angle)
            gx = cx + int(s(17) * math.cos(rad))
            gy = cy + s(10) + int(s(17) * math.sin(rad))
            d.ellipse([gx-s(4), gy-s(4), gx+s(4), gy+s(4)], fill=(*accent, 125))
        d.ellipse([cx-s(7), cy+s(3), cx+s(7), cy+s(17)], fill=(*accent, 82))
    if wires:
        for sx,sy,ex,ey in [(-s(24),0,-s(52),-s(10)), (s(24),0,s(52),-s(10)), (-s(18),s(28),-s(48),s(44))]:
            d.line([cx+sx, cy+sy, cx+ex, cy+ey], fill=(*accent, 155), width=s(2))
    d.rectangle([cx-s(21), cy+s(36), cx-s(7),  cy+s(78)], fill=(*base, 192))
    d.rectangle([cx+s(7),  cy+s(36), cx+s(21), cy+s(78)], fill=(*base, 192))
    d.rectangle([cx-s(23), cy+s(70), cx-s(4),  cy+s(80)], fill=(*base, 180))
    d.rectangle([cx+s(4),  cy+s(70), cx+s(23), cy+s(80)], fill=(*base, 180))

def draw_plant(d, img, cx, cy, base, accent, **_):
    _glow(d, cx, cy, s(32), accent, a=22, layers=3)
    d.ellipse([cx-s(22), cy-s(18), cx+s(22), cy+s(44)], fill=(*base, 212))
    for x1,y1,x2,y2,x3,y3 in [
        (-s(26),-s(4),-s(40),-s(18),-s(33),-s(4)), (-s(30),s(10),-s(48),s(2),-s(38),s(18)),
        ( s(26),-s(4), s(40),-s(18), s(33),-s(4)), ( s(30),s(10), s(48),s(2), s(38),s(18)),
    ]:
        d.polygon([cx+x1,cy+y1, cx+x2,cy+y2, cx+x3,cy+y3], fill=(*accent, 205))
    d.ellipse([cx-s(17), cy-s(66), cx+s(17), cy-s(14)], fill=(*base, 232))
    for i in range(4):
        d.arc([cx-s(22), cy+i*s(12)-s(4), cx+s(22), cy+i*s(12)+s(4)], 200, 340, fill=(*accent, 58), width=s(1))
    for ex, ey in [(-s(7), cy-s(48)), (s(7), cy-s(48))]:
        d.ellipse([cx+ex-s(4), ey-s(4), cx+ex+s(4), ey+s(4)], fill=(*accent, 242))
    d.rectangle([cx-s(17), cy+s(40), cx-s(5), cy+s(74)], fill=(*base, 182))
    d.rectangle([cx+s(5),  cy+s(40), cx+s(17), cy+s(74)], fill=(*base, 182))

def draw_compact(d, img, cx, cy, base, accent, **_):
    _glow(d, cx, cy-s(20), s(30), accent, a=28, layers=4)
    for ox, h in [(-s(10),s(18)), (-s(3),s(26)), (s(4),s(22))]:
        d.polygon([cx+ox-s(3), cy-s(65), cx+ox+s(3), cy-s(65), cx+ox, cy-s(65)-h], fill=(*accent, 225))
    d.ellipse([cx-s(28), cy-s(62), cx+s(28), cy+s(8)], fill=(*base, 232))
    _glow(d, cx, cy-s(28), s(15), accent, a=85, layers=2)
    for ex, ey in [(-s(11), cy-s(40)), (s(11), cy-s(40))]:
        d.ellipse([cx+ex-s(5), ey-s(5), cx+ex+s(5), ey+s(5)], fill=(*accent, 252))
    d.ellipse([cx-s(22), cy-s(3),  cx+s(22), cy+s(38)], fill=(*base, 222))
    d.ellipse([cx-s(16), cy+s(32), cx-s(5),  cy+s(54)], fill=(*base, 182))
    d.ellipse([cx+s(5),  cy+s(32), cx+s(16), cy+s(54)], fill=(*base, 182))

def draw_cephalopod(d, img, cx, cy, base, accent, **_):
    _glow(d, cx, cy-s(12), s(48), accent, a=18, layers=3)
    d.ellipse([cx-s(48), cy-s(58), cx+s(48), cy+s(8)],  fill=(*base, 212))
    d.ellipse([cx-s(28), cy-s(38), cx+s(28), cy+s(4)],  fill=(*base, 232))
    for ox, oy in [(-s(17),cy-s(26)), (-s(6),cy-s(32)), (s(6),cy-s(32)), (s(17),cy-s(26))]:
        _glow(d, cx+ox, oy, s(5), accent, a=125, layers=2)
        d.ellipse([cx+ox-s(4), oy-s(4), cx+ox+s(4), oy+s(4)], fill=(*accent, 232))
    for x1,y1,x2,y2,x3,y3 in [
        (-s(38),s(5), -s(52),s(38), -s(42),s(72)), (-s(26),s(8), -s(36),s(44), -s(28),s(78)),
        (-s(14),s(10),-s(16),s(48), -s(10),s(80)), (-s(2), s(10), 0,    s(50),  s(2), s(82)),
        ( s(2), s(10), s(4), s(50),  s(6), s(82)), ( s(14),s(10), s(16),s(48),  s(14),s(80)),
        ( s(26),s(8),  s(36),s(44),  s(32),s(78)), ( s(38),s(5),  s(52),s(38),  s(46),s(72)),
    ]:
        d.line([cx+x1,cy+y1, cx+x2,cy+y2], fill=(*base, 192), width=s(3))
        d.line([cx+x2,cy+y2, cx+x3,cy+y3], fill=(*base, 162), width=s(2))
        d.ellipse([cx+x3-s(3),cy+y3-s(3), cx+x3+s(3),cy+y3+s(3)], fill=(*accent, 105))

def draw_humanoid(d, img, cx, cy, base, accent, feature="default", **_):
    _glow(d, cx, cy, s(32), accent, a=18, layers=3)
    if feature == "cloak":
        d.polygon([cx-s(22),cy-s(14), cx-s(52),cy+s(18), cx-s(42),cy+s(78),
                   cx,cy+s(58), cx+s(42),cy+s(78), cx+s(52),cy+s(18), cx+s(22),cy-s(14)], fill=(*base, 105))
    d.ellipse([cx-s(36), cy-s(18), cx-s(12), cy+s(14)], fill=(*base, 200))
    d.ellipse([cx+s(12), cy-s(18), cx+s(36), cy+s(14)], fill=(*base, 200))
    d.rectangle([cx-s(34), cy+s(4),  cx-s(18), cy+s(48)], fill=(*base, 185))
    d.rectangle([cx+s(18), cy+s(4),  cx+s(34), cy+s(48)], fill=(*base, 185))
    d.ellipse([cx-s(20), cy-s(14), cx+s(20), cy+s(44)], fill=(*base, 222))
    d.ellipse([cx-s(17), cy-s(68), cx+s(17), cy-s(10)], fill=(*base, 236))
    for ex, ey in [(-s(8), cy-s(50)), (s(8), cy-s(50))]:
        d.ellipse([cx+ex-s(4), ey-s(4), cx+ex+s(4), ey+s(4)], fill=(*accent, 242))
    d.rectangle([cx-s(16), cy+s(38), cx-s(5), cy+s(78)], fill=(*base, 192))
    d.rectangle([cx+s(5),  cy+s(38), cx+s(16), cy+s(78)], fill=(*base, 192))

    if feature == "crown":
        for ox, h in [(-s(10),s(14)), (-s(4),s(20)), (s(4),s(20)), (s(10),s(14))]:
            d.polygon([cx+ox-s(3),cy-s(68), cx+ox+s(3),cy-s(68), cx+ox,cy-s(68)-h], fill=(*accent, 225))
    elif feature == "aura":
        _glow(d, cx, cy-s(38), s(30), accent, a=62, layers=3)
    elif feature == "scars":
        for sx,sy,ex,ey in [(-s(7),cy-s(28),-s(2),cy-s(13)), (s(5),cy-s(33),s(9),cy-s(18)), (-s(4),cy+s(2),s(1),cy+s(17))]:
            d.line([cx+sx, ey, cx+ex, cy+sy], fill=(*accent, 185), width=s(2))
    elif feature == "thorns_sm":
        for ox, oy in [(-s(26),-s(8)), (s(26),-s(8)), (-s(26),s(10)), (s(26),s(10))]:
            d.polygon([cx+ox-s(2),cy+oy, cx+ox+s(2),cy+oy, cx+ox,cy+oy-s(11)], fill=(*accent, 205))
    elif feature == "glow_body":
        for i in range(5):
            _glow(d, cx, cy-s(8)+i*s(12), s(9), accent, a=82, layers=2)
    elif feature == "fire_crown":
        for ox, h in [(-s(12),s(18)), (-s(5),s(28)), (0,s(33)), (s(5),s(28)), (s(12),s(18))]:
            d.polygon([cx+ox-s(3),cy-s(68), cx+ox+s(3),cy-s(68), cx+ox,cy-s(68)-h], fill=(*accent, 205))
        _glow(d, cx, cy-s(82), s(19), accent, a=82, layers=2)
    elif feature == "fracture":
        for sx,sy,ex,ey in [(-s(14),cy-s(38),-s(5),cy+s(8)), (s(7),cy-s(46),s(14),cy+s(4)), (-s(9),cy-s(8),s(4),cy+s(38))]:
            d.line([cx+sx, sy, cx+ex, ey], fill=(*accent, 125), width=s(1))
    elif feature == "halo":
        d.ellipse([cx-s(24),cy-s(86), cx+s(24),cy-s(66)], outline=(*accent, 185), width=s(3))
        _glow(d, cx, cy-s(76), s(18), accent, a=52, layers=2)
    elif feature == "split":
        d.line([cx, cy-s(68), cx, cy+s(78)], fill=(*accent, 82), width=s(2))
        d.ellipse([cx-s(8), cy-s(54), cx, cy-s(46)], fill=(*_rgb("#e05030"), 225))
    elif feature == "antenna":
        d.line([cx-s(3), cy-s(68), cx-s(14), cy-s(92)], fill=(*accent, 205), width=s(2))
        d.line([cx+s(3), cy-s(68), cx+s(14), cy-s(92)], fill=(*accent, 205), width=s(2))
        d.ellipse([cx-s(17), cy-s(96), cx-s(11), cy-s(90)], fill=(*accent, 232))
        d.ellipse([cx+s(11), cy-s(96), cx+s(17), cy-s(90)], fill=(*accent, 232))
    elif feature == "shadow_void":
        _glow(d, cx, cy, s(52), accent, a=38, layers=4)
    elif feature == "scales":
        for row in range(4):
            for col in range(3):
                sx = cx - s(15) + col * s(13)
                sy = cy - s(8)  + row * s(14)
                d.ellipse([sx, sy, sx+s(11), sy+s(9)], outline=(*accent, 102), width=s(1))
    elif feature == "wings_small":
        d.ellipse([cx-s(52), cy-s(14), cx-s(18), cy+s(18)], fill=(*base, 148))
        d.ellipse([cx+s(18), cy-s(14), cx+s(52), cy+s(18)], fill=(*base, 148))


# ── Race table ───────────────────────────────────────────────────────────────

RACES = {
    # COSMIC
    "voidwraith":   ("Voidwraith",   "Cosmic",     "ethereal",   "#9ac8ff", "#0e1828", {}),
    "nullshade":    ("Nullshade",    "Cosmic",     "ethereal",   "#8899aa", "#0e1018", {}),
    "ironlocust":   ("Ironlocust",   "Cosmic",     "insectoid",  "#d4b820", "#1a140a", {"legs": 6}),
    "embervein":    ("Embervein",    "Cosmic",     "hulking",    "#ff6600", "#2a0a00", {}),
    "riftwalker":   ("Riftwalker",   "Cosmic",     "predator",   "#9ac8ff", "#061420", {"has_tail": True}),
    # PRIMAL
    "solarlord":    ("Solarlord",    "Primal",     "avian",      "#ffffc0", "#2a1c00", {}),
    "thornmimic":   ("Thornmimic",   "Primal",     "plant",      "#66aa44", "#061006", {}),
    "cinderkin":    ("Cinderkin",    "Primal",     "compact",    "#ff9900", "#200810", {}),
    "deeptyrant":   ("Deeptyrant",   "Primal",     "cephalopod", "#00d4cc", "#001020", {}),
    "grimcrow":     ("Grimcrow",     "Primal",     "avian",      "#9966cc", "#08000e", {}),
    # ELDRITCH
    "bloodweaver":  ("Bloodweaver",  "Eldritch",   "horror",     "#ff2244", "#140006", {"has_cape": True}),
    "dreamhusk":    ("Dreamhusk",    "Eldritch",   "ethereal",   "#d8b4ff", "#100820", {}),
    "bonedrifter":  ("Bonedrifter",  "Eldritch",   "horror",     "#ddddd0", "#0e0e0c", {"has_bones": True}),
    "mindspider":   ("Mindspider",   "Eldritch",   "arachnid",   "#aaffdd", "#000e0c", {}),
    "chaosling":    ("Chaosling",    "Eldritch",   "ethereal",   "#ff88cc", "#12000e", {}),
    # MECHANICAL
    "ironveil":     ("Ironveil",     "Mechanical", "mechanical", "#c8e8ff", "#080e14", {}),
    "forgespawn":   ("Forgespawn",   "Mechanical", "mechanical", "#ff8800", "#140800", {"gear": True}),
    "cinderplate":  ("Cinderplate",  "Mechanical", "mechanical", "#ff4400", "#180600", {}),
    "hexgear":      ("Hexgear",      "Mechanical", "mechanical", "#88ffcc", "#00100a", {"gear": True}),
    "wirewraith":   ("Wirewraith",   "Mechanical", "mechanical", "#ffff44", "#141200", {"wires": True}),
    # HUMANOID
    "ashenborn":    ("Ashenborn",    "Humanoid",   "humanoid",   "#ff6644", "#140800", {"feature": "scars"}),
    "hollowsong":   ("Hollowsong",   "Humanoid",   "humanoid",   "#cc88ff", "#0c0012", {"feature": "aura"}),
    "veilborn":     ("Veilborn",     "Humanoid",   "humanoid",   "#6677aa", "#06080e", {"feature": "cloak"}),
    "thornweft":    ("Thornweft",    "Humanoid",   "humanoid",   "#66aa44", "#040a04", {"feature": "thorns_sm"}),
    "ashcrown":     ("Ashcrown",     "Humanoid",   "humanoid",   "#eeeebb", "#0e0e0c", {"feature": "crown"}),
    "ironfast":     ("Ironfast",     "Humanoid",   "humanoid",   "#999999", "#0a0a0a", {"feature": "glow_body"}),
    "coreborn":     ("Coreborn",     "Humanoid",   "humanoid",   "#ff4422", "#140600", {"feature": "fire_crown"}),
    "warpbred":     ("Warpbred",     "Humanoid",   "humanoid",   "#aa2200", "#120400", {"feature": "fracture"}),
    "splitblood":   ("Splitblood",   "Humanoid",   "humanoid",   "#884422", "#0e0604", {"feature": "split"}),
    "duskweft":     ("Duskweft",     "Humanoid",   "humanoid",   "#aaaaff", "#06060e", {"feature": "shadow_void"}),
    "glitchkin":    ("Glitchkin",    "Humanoid",   "humanoid",   "#00ffaa", "#00100a", {"feature": "antenna"}),
    "fractureline": ("Fractureline", "Humanoid",   "humanoid",   "#ffaa00", "#100c00", {"feature": "fracture"}),
    "emberpact":    ("Emberpact",    "Humanoid",   "humanoid",   "#ff4444", "#140404", {"feature": "fire_crown"}),
    "fallenlight":  ("Fallenlight",  "Humanoid",   "humanoid",   "#ffff99", "#0e0e08", {"feature": "halo"}),
    "scaleworn":    ("Scaleworn",    "Humanoid",   "humanoid",   "#336633", "#040c04", {"feature": "scales"}),
}

DRAW_FNS = {
    "ethereal": draw_ethereal, "insectoid": draw_insectoid, "hulking":    draw_hulking,
    "predator": draw_predator, "avian":     draw_avian,     "horror":     draw_horror,
    "arachnid": draw_arachnid, "mechanical":draw_mechanical,"plant":      draw_plant,
    "compact":  draw_compact,  "cephalopod":draw_cephalopod,"humanoid":   draw_humanoid,
}


# ── Main generator ────────────────────────────────────────────────────────────

def make_portrait(race_id, name, group, body_type, accent_hex, base_hex, extra):
    img = Image.new("RGBA", (W, H), (10, 10, 18, 255))
    d = ImageDraw.Draw(img, "RGBA")

    accent = _rgb(accent_hex)
    base   = _rgb(base_hex)
    cx, cy = W // 2, H // 2 - s(20)

    # Subtle accent radial haze
    for i in range(s(30)):
        a = max(0, int((i / SCALE) * 2.5) // 6)
        d.rectangle([0, H - i - 1, W, H - i], fill=(*accent, a))

    DRAW_FNS[body_type](d, img, cx, cy, base, accent, **extra)
    _vignette(img)

    d2 = ImageDraw.Draw(img, "RGBA")
    _frame(d2, accent)
    _labels(d2, name, group, accent)

    os.makedirs(OUT, exist_ok=True)
    img.save(os.path.join(OUT, f"{race_id}.png"))
    print(f"  ✓  {race_id}.png")


if __name__ == "__main__":
    print(f"Generating {len(RACES)} portraits at {W}×{H} → {OUT}\n")
    for race_id, data in RACES.items():
        make_portrait(race_id, *data)
    print(f"\nDone.")
