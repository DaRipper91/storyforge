#!/usr/bin/env python3
"""
Generate 200×280 PNG portrait cards for all 35 StoryForge races.

Run from the project root:
    uv run python scripts/generate_portraits.py

Output: godot/assets/characters/<race_id>.png
"""
from PIL import Image, ImageDraw, ImageFilter
import os, math

OUT = os.path.join(os.path.dirname(__file__), "..", "godot", "assets", "characters")
W, H = 200, 280

# ── Helpers ─────────────────────────────────────────────────────────────────

def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def _glow(d, cx, cy, r, col, a=60, layers=3):
    for i in range(layers):
        ri, ai = r + i * 6, max(0, a - i * 18)
        d.ellipse([cx-ri, cy-ri, cx+ri, cy+ri], fill=(*col, ai))

def _vignette(img):
    v = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(v, "RGBA")
    for i in range(40):
        a = int(i * 3.5)
        d.rectangle([i, i, W-i, H-i], outline=(0, 0, 0, a), width=1)
    img.alpha_composite(v)

def _frame(d, accent):
    d.rectangle([1, 1, W-2, H-2], outline=(*accent, 110), width=2)
    d.rectangle([4, 4, W-5, H-5], outline=(*accent, 40), width=1)

def _labels(d, name, group, accent):
    group_colors = {
        "Cosmic": "#9ac8ff", "Primal": "#ffffc0", "Eldritch": "#d8b4ff",
        "Mechanical": "#88ffcc", "Humanoid": "#ffaa66",
    }
    badge_col = _rgb(group_colors.get(group, "#ffffff"))

    # Group badge — top-left
    d.rectangle([5, 5, 72, 18], fill=(0, 0, 0, 160))
    d.text((9, 7), group.upper(), fill=(*badge_col, 200))

    # Name bar — bottom
    d.rectangle([0, H-38, W, H], fill=(0, 0, 0, 195))
    d.line([0, H-38, W, H-38], fill=(*accent, 100), width=1)

    # Centered race name
    try:
        from PIL import ImageFont
        font = ImageFont.load_default(size=14)
        bbox = d.textbbox((0, 0), name.upper(), font=font)
        tw = bbox[2] - bbox[0]
        d.text(((W - tw) // 2, H - 25), name.upper(), fill=(*accent, 220), font=font)
    except Exception:
        d.text((W // 2 - len(name) * 3, H - 24), name.upper(), fill=(*accent, 220))


# ── Body-type draw functions ─────────────────────────────────────────────────

def draw_ethereal(d, img, cx, cy, base, accent, **_):
    _glow(d, cx, cy-18, 60, accent, a=22, layers=5)
    d.ellipse([cx-55, cy-68, cx+55, cy+28], fill=(*base, 190))
    _glow(d, cx, cy-22, 28, accent, a=90, layers=2)
    for ex, ey, er in [(-22, cy-32, 9), (22, cy-32, 9)]:
        _glow(d, cx+ex, ey, er, accent, a=140, layers=2)
        d.ellipse([cx+ex-5, ey-5, cx+ex+5, ey+5], fill=(*accent, 240))
    for ox, ys in [(-28, cy+25), (0, cy+30), (28, cy+25)]:
        for j in range(4):
            a = 160 - j * 35
            d.ellipse([cx+ox-5, ys+j*9-5, cx+ox+5, ys+j*9+5], fill=(*accent, a))

def draw_insectoid(d, img, cx, cy, base, accent, legs=6, **_):
    d.ellipse([cx-18, cy+12, cx+18, cy+52], fill=(*base, 200))
    d.ellipse([cx-20, cy-18, cx+20, cy+18], fill=(*base, 220))
    d.ellipse([cx-14, cy-52, cx+14, cy-18], fill=(*base, 235))
    for ex, ey in [(-8, cy-40), (8, cy-40)]:
        d.ellipse([cx+ex-4, ey-4, cx+ex+4, ey+4], fill=(*accent, 240))
    d.line([cx-4, cy-52, cx-22, cy-78], fill=(*accent, 200), width=2)
    d.line([cx+4, cy-52, cx+22, cy-78], fill=(*accent, 200), width=2)
    d.ellipse([cx-25, cy-82, cx-18, cy-75], fill=(*accent, 220))
    d.ellipse([cx+18, cy-82, cx+25, cy-75], fill=(*accent, 220))
    for i in range(legs // 2):
        yl = cy - 8 + i * 14
        d.line([cx-20, yl, cx-52, yl+8], fill=(*base, 185), width=2)
        d.line([cx-52, yl+8, cx-62, yl+22], fill=(*base, 155), width=2)
        d.line([cx+20, yl, cx+52, yl+8], fill=(*base, 185), width=2)
        d.line([cx+52, yl+8, cx+62, yl+22], fill=(*base, 155), width=2)

def draw_hulking(d, img, cx, cy, base, accent, **_):
    _glow(d, cx, cy, 70, accent, a=18, layers=4)
    d.ellipse([cx-68, cy-18, cx+68, cy+58], fill=(*base, 215))
    d.ellipse([cx-62, cy-42, cx-22, cy+12], fill=(*base, 200))
    d.ellipse([cx+22, cy-42, cx+62, cy+12], fill=(*base, 200))
    d.ellipse([cx-26, cy-78, cx+26, cy-18], fill=(*base, 232))
    for ox, oy in [(-18, 18), (12, 2), (-4, 38), (24, 24)]:
        _glow(d, cx+ox, cy+oy, 7, accent, a=150, layers=2)
    for ex, ey in [(-11, cy-56), (11, cy-56)]:
        d.ellipse([cx+ex-5, ey-5, cx+ex+5, ey+5], fill=(*accent, 245))
    d.ellipse([cx-42, cy+48, cx-14, cy+80], fill=(*base, 175))
    d.ellipse([cx+14, cy+48, cx+42, cy+80], fill=(*base, 175))

def draw_predator(d, img, cx, cy, base, accent, has_tail=True, **_):
    _glow(d, cx, cy, 38, accent, a=22, layers=3)
    d.ellipse([cx-38, cy-22, cx-12, cy+18], fill=(*base, 195))
    d.ellipse([cx+12, cy-22, cx+38, cy+18], fill=(*base, 195))
    d.ellipse([cx-20, cy-14, cx+20, cy+42], fill=(*base, 222))
    d.ellipse([cx-17, cy-62, cx+21, cy-10], fill=(*base, 232))
    for ex, ey in [(-9, cy-48), (6, cy-48)]:
        d.ellipse([cx+ex-5, ey-5, cx+ex+5, ey+5], fill=(*accent, 242))
    d.rectangle([cx-16, cy+36, cx-6, cy+75], fill=(*base, 190))
    d.rectangle([cx+6, cy+36, cx+16, cy+75], fill=(*base, 190))
    if has_tail:
        for i, (ox, oy) in enumerate([(24,28), (36,42), (44,58), (46,74)]):
            d.ellipse([cx+ox-6, cy+oy-6, cx+ox+6, cy+oy+6], fill=(*base, 200-i*30))

def draw_avian(d, img, cx, cy, base, accent, **_):
    _glow(d, cx-55, cy, 30, accent, a=18, layers=3)
    _glow(d, cx+55, cy, 30, accent, a=18, layers=3)
    d.polygon([cx, cy-8, cx-88, cy-28, cx-78, cy+28, cx-8, cy+18], fill=(*base, 175))
    d.polygon([cx, cy-8, cx+88, cy-28, cx+78, cy+28, cx+8, cy+18], fill=(*base, 175))
    for ox in [-80, -62, -44]:
        d.line([cx+ox//2, cy-2, cx+ox, cy+12], fill=(*accent, 115), width=1)
    for ox in [80, 62, 44]:
        d.line([cx+ox//2, cy-2, cx+ox, cy+12], fill=(*accent, 115), width=1)
    d.ellipse([cx-16, cy-8, cx+16, cy+38], fill=(*base, 232))
    d.ellipse([cx-15, cy-58, cx+15, cy-8], fill=(*base, 242))
    for ox, h in [(-6, 18), (0, 26), (6, 20)]:
        d.polygon([cx+ox-3, cy-58, cx+ox+3, cy-58, cx+ox, cy-58-h], fill=(*accent, 205))
    for ex, ey in [(-7, cy-43), (7, cy-43)]:
        d.ellipse([cx+ex-4, ey-4, cx+ex+4, ey+4], fill=(*accent, 252))
    d.ellipse([cx-12, cy+34, cx-3, cy+64], fill=(*base, 178))
    d.ellipse([cx+3, cy+34, cx+12, cy+64], fill=(*base, 178))

def draw_horror(d, img, cx, cy, base, accent, has_cape=False, has_bones=False, **_):
    _glow(d, cx, cy, 28, accent, a=32, layers=4)
    if has_cape:
        d.polygon([cx, cy-28, cx-62, cy+38, cx-48, cy+78, cx, cy+58, cx+48, cy+78, cx+62, cy+38], fill=(*base, 115))
    d.ellipse([cx-35, cy-12, cx-12, cy+22], fill=(*base, 185))
    d.ellipse([cx+12, cy-12, cx+35, cy+22], fill=(*base, 185))
    d.ellipse([cx-14, cy-18, cx+14, cy+48], fill=(*base, 222))
    d.ellipse([cx-17, cy-68, cx+17, cy-12], fill=(*base, 232))
    if has_bones:
        for ox, oy in [(-16, -10), (-16, 8), (16, -10), (16, 8)]:
            d.polygon([cx+ox-3, cy+oy, cx+ox+3, cy+oy, cx+ox, cy+oy-13], fill=(*accent, 205))
    for ex, ey in [(-8, cy-50), (8, cy-50)]:
        _glow(d, cx+ex, ey, 5, accent, a=160, layers=2)
        d.ellipse([cx+ex-4, ey-4, cx+ex+4, ey+4], fill=(*accent, 255))
    for i in range(3):
        d.line([cx-35+i, cy+22, cx-38+i*4, cy+42], fill=(*base, 155), width=1)
        d.line([cx+35-i, cy+22, cx+38-i*4, cy+42], fill=(*base, 155), width=1)
    d.rectangle([cx-11, cy+44, cx-3, cy+82], fill=(*base, 182))
    d.rectangle([cx+3, cy+44, cx+11, cy+82], fill=(*base, 182))

def draw_arachnid(d, img, cx, cy, base, accent, **_):
    _glow(d, cx, cy, 32, accent, a=22, layers=3)
    d.ellipse([cx-26, cy+18, cx+26, cy+68], fill=(*base, 210))
    d.ellipse([cx-20, cy-22, cx+20, cy+28], fill=(*base, 232))
    d.ellipse([cx-14, cy-52, cx+14, cy-18], fill=(*base, 242))
    for ex, ey in [(-8, cy-42), (-2, cy-47), (4, cy-42), (8, cy-47)]:
        d.ellipse([cx+ex-3, ey-3, cx+ex+3, ey+3], fill=(*accent, 242))
    leg_data = [
        (-20, -8, -68, -28, -78, 2), (-20, 2, -70, 6, -80, 26),
        (-20, 12, -66, 22, -73, 44), (-20, 22, -58, 36, -63, 58),
        (20, -8, 68, -28, 78, 2),   (20, 2, 70, 6, 80, 26),
        (20, 12, 66, 22, 73, 44),   (20, 22, 58, 36, 63, 58),
    ]
    for x1, y1, x2, y2, x3, y3 in leg_data:
        d.line([cx+x1, cy+y1, cx+x2, cy+y2], fill=(*base, 200), width=2)
        d.line([cx+x2, cy+y2, cx+x3, cy+y3], fill=(*base, 162), width=2)

def draw_mechanical(d, img, cx, cy, base, accent, gear=False, wires=False, **_):
    _glow(d, cx, cy, 38, accent, a=28, layers=3)
    d.rectangle([cx-24, cy-18, cx+24, cy+38], fill=(*base, 222))
    d.line([cx-24, cy+8, cx+24, cy+8], fill=(*accent, 80), width=1)
    d.line([cx-24, cy+24, cx+24, cy+24], fill=(*accent, 55), width=1)
    d.rectangle([cx-48, cy-24, cx-24, cy+10], fill=(*base, 202))
    d.rectangle([cx+24, cy-24, cx+48, cy+10], fill=(*base, 202))
    d.rectangle([cx-19, cy-66, cx+19, cy-18], fill=(*base, 232))
    d.rectangle([cx-15, cy-54, cx+15, cy-42], fill=(*accent, 185))
    _glow(d, cx, cy-48, 13, accent, a=85, layers=2)
    if gear:
        for angle in range(0, 360, 45):
            rad = math.radians(angle)
            gx, gy = cx + int(17 * math.cos(rad)), cy + 10 + int(17 * math.sin(rad))
            d.ellipse([gx-4, gy-4, gx+4, gy+4], fill=(*accent, 125))
        d.ellipse([cx-7, cy+3, cx+7, cy+17], fill=(*accent, 82))
    if wires:
        for sx, sy, ex, ey in [(-24, 0, -52, -10), (24, 0, 52, -10), (-18, 28, -48, 44)]:
            d.line([cx+sx, cy+sy, cx+ex, cy+ey], fill=(*accent, 155), width=2)
    d.rectangle([cx-21, cy+36, cx-7, cy+78], fill=(*base, 192))
    d.rectangle([cx+7, cy+36, cx+21, cy+78], fill=(*base, 192))
    d.rectangle([cx-23, cy+70, cx-4, cy+80], fill=(*base, 180))
    d.rectangle([cx+4, cy+70, cx+23, cy+80], fill=(*base, 180))

def draw_plant(d, img, cx, cy, base, accent, **_):
    _glow(d, cx, cy, 32, accent, a=22, layers=3)
    d.ellipse([cx-22, cy-18, cx+22, cy+44], fill=(*base, 212))
    for x1, y1, x2, y2, x3, y3 in [
        (-26, -4, -40, -18, -33, -4), (-30, 10, -48, 2, -38, 18),
        (26, -4, 40, -18, 33, -4),   (30, 10, 48, 2, 38, 18),
    ]:
        d.polygon([cx+x1, cy+y1, cx+x2, cy+y2, cx+x3, cy+y3], fill=(*accent, 205))
    d.ellipse([cx-17, cy-66, cx+17, cy-14], fill=(*base, 232))
    for i in range(4):
        d.arc([cx-22, cy+i*12-4, cx+22, cy+i*12+4], 200, 340, fill=(*accent, 58), width=1)
    for ex, ey in [(-7, cy-48), (7, cy-48)]:
        d.ellipse([cx+ex-4, ey-4, cx+ex+4, ey+4], fill=(*accent, 242))
    d.rectangle([cx-17, cy+40, cx-5, cy+74], fill=(*base, 182))
    d.rectangle([cx+5, cy+40, cx+17, cy+74], fill=(*base, 182))

def draw_compact(d, img, cx, cy, base, accent, **_):
    _glow(d, cx, cy-20, 30, accent, a=28, layers=4)
    for ox, h in [(-10, 18), (-3, 26), (4, 22)]:
        d.polygon([cx+ox-3, cy-65, cx+ox+3, cy-65, cx+ox, cy-65-h], fill=(*accent, 225))
    d.ellipse([cx-28, cy-62, cx+28, cy+8], fill=(*base, 232))
    _glow(d, cx, cy-28, 15, accent, a=85, layers=2)
    for ex, ey in [(-11, cy-40), (11, cy-40)]:
        d.ellipse([cx+ex-5, ey-5, cx+ex+5, ey+5], fill=(*accent, 252))
    d.ellipse([cx-22, cy-3, cx+22, cy+38], fill=(*base, 222))
    d.ellipse([cx-16, cy+32, cx-5, cy+54], fill=(*base, 182))
    d.ellipse([cx+5, cy+32, cx+16, cy+54], fill=(*base, 182))

def draw_cephalopod(d, img, cx, cy, base, accent, **_):
    _glow(d, cx, cy-12, 48, accent, a=18, layers=3)
    d.ellipse([cx-48, cy-58, cx+48, cy+8], fill=(*base, 212))
    d.ellipse([cx-28, cy-38, cx+28, cy+4], fill=(*base, 232))
    for ox, oy in [(-17, cy-26), (-6, cy-32), (6, cy-32), (17, cy-26)]:
        _glow(d, cx+ox, oy, 5, accent, a=125, layers=2)
        d.ellipse([cx+ox-4, oy-4, cx+ox+4, oy+4], fill=(*accent, 232))
    for x1, y1, x2, y2, x3, y3 in [
        (-38, 5, -52, 38, -42, 72), (-26, 8, -36, 44, -28, 78),
        (-14, 10, -16, 48, -10, 80), (-2, 10, 0, 50, 2, 82),
        (2, 10, 4, 50, 6, 82),      (14, 10, 16, 48, 14, 80),
        (26, 8, 36, 44, 32, 78),    (38, 5, 52, 38, 46, 72),
    ]:
        d.line([cx+x1, cy+y1, cx+x2, cy+y2], fill=(*base, 192), width=3)
        d.line([cx+x2, cy+y2, cx+x3, cy+y3], fill=(*base, 162), width=2)
        d.ellipse([cx+x3-3, cy+y3-3, cx+x3+3, cy+y3+3], fill=(*accent, 105))

def draw_humanoid(d, img, cx, cy, base, accent, feature="default", **_):
    _glow(d, cx, cy, 32, accent, a=18, layers=3)
    if feature == "cloak":
        d.polygon([cx-22, cy-14, cx-52, cy+18, cx-42, cy+78, cx, cy+58, cx+42, cy+78, cx+52, cy+18, cx+22, cy-14], fill=(*base, 105))
    d.ellipse([cx-36, cy-18, cx-12, cy+14], fill=(*base, 200))
    d.ellipse([cx+12, cy-18, cx+36, cy+14], fill=(*base, 200))
    d.rectangle([cx-34, cy+4, cx-18, cy+48], fill=(*base, 185))
    d.rectangle([cx+18, cy+4, cx+34, cy+48], fill=(*base, 185))
    d.ellipse([cx-20, cy-14, cx+20, cy+44], fill=(*base, 222))
    d.ellipse([cx-17, cy-68, cx+17, cy-10], fill=(*base, 236))
    for ex, ey in [(-8, cy-50), (8, cy-50)]:
        d.ellipse([cx+ex-4, ey-4, cx+ex+4, ey+4], fill=(*accent, 242))
    d.rectangle([cx-16, cy+38, cx-5, cy+78], fill=(*base, 192))
    d.rectangle([cx+5, cy+38, cx+16, cy+78], fill=(*base, 192))

    if feature == "crown":
        for ox, h in [(-10, 14), (-4, 20), (4, 20), (10, 14)]:
            d.polygon([cx+ox-3, cy-68, cx+ox+3, cy-68, cx+ox, cy-68-h], fill=(*accent, 225))
    elif feature == "aura":
        _glow(d, cx, cy-38, 30, accent, a=62, layers=3)
    elif feature == "scars":
        for sx, sy, ex, ey in [(-7, cy-28, -2, cy-13), (5, cy-33, 9, cy-18), (-4, cy+2, 1, cy+17)]:
            d.line([cx+sx, ey, cx+ex, cy+sy], fill=(*accent, 185), width=2)
    elif feature == "thorns_sm":
        for ox, oy in [(-26, -8), (26, -8), (-26, 10), (26, 10)]:
            d.polygon([cx+ox-2, cy+oy, cx+ox+2, cy+oy, cx+ox, cy+oy-11], fill=(*accent, 205))
    elif feature == "glow_body":
        for i in range(5):
            _glow(d, cx, cy - 8 + i * 12, 9, accent, a=82, layers=2)
    elif feature == "fire_crown":
        for ox, h in [(-12, 18), (-5, 28), (0, 33), (5, 28), (12, 18)]:
            d.polygon([cx+ox-3, cy-68, cx+ox+3, cy-68, cx+ox, cy-68-h], fill=(*accent, 205))
        _glow(d, cx, cy-82, 19, accent, a=82, layers=2)
    elif feature == "fracture":
        for sx, sy, ex, ey in [(-14, cy-38, -5, cy+8), (7, cy-46, 14, cy+4), (-9, cy-8, 4, cy+38)]:
            d.line([cx+sx, sy, cx+ex, ey], fill=(*accent, 125), width=1)
    elif feature == "halo":
        d.ellipse([cx-24, cy-86, cx+24, cy-66], outline=(*accent, 185), width=3)
        _glow(d, cx, cy-76, 18, accent, a=52, layers=2)
    elif feature == "split":
        d.line([cx, cy-68, cx, cy+78], fill=(*accent, 82), width=2)
        d.ellipse([cx-8, cy-54, cx, cy-46], fill=(*_rgb("#e05030"), 225))
    elif feature == "antenna":
        d.line([cx-3, cy-68, cx-14, cy-92], fill=(*accent, 205), width=2)
        d.line([cx+3, cy-68, cx+14, cy-92], fill=(*accent, 205), width=2)
        d.ellipse([cx-17, cy-96, cx-11, cy-90], fill=(*accent, 232))
        d.ellipse([cx+11, cy-96, cx+17, cy-90], fill=(*accent, 232))
    elif feature == "shadow_void":
        _glow(d, cx, cy, 52, accent, a=38, layers=4)
    elif feature == "scales":
        for row in range(4):
            for col in range(3):
                sx, sy = cx - 15 + col * 13, cy - 8 + row * 14
                d.ellipse([sx, sy, sx+11, sy+9], outline=(*accent, 102), width=1)
    elif feature == "wings_small":
        d.ellipse([cx-52, cy-14, cx-18, cy+18], fill=(*base, 148))
        d.ellipse([cx+18, cy-14, cx+52, cy+18], fill=(*base, 148))


# ── Race table ───────────────────────────────────────────────────────────────

RACES = {
    # id: (display_name, group, body_type, accent_hex, base_hex, extra_kwargs)

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
    "ethereal":   draw_ethereal,
    "insectoid":  draw_insectoid,
    "hulking":    draw_hulking,
    "predator":   draw_predator,
    "avian":      draw_avian,
    "horror":     draw_horror,
    "arachnid":   draw_arachnid,
    "mechanical": draw_mechanical,
    "plant":      draw_plant,
    "compact":    draw_compact,
    "cephalopod": draw_cephalopod,
    "humanoid":   draw_humanoid,
}


# ── Main generator ────────────────────────────────────────────────────────────

def make_portrait(race_id, name, group, body_type, accent_hex, base_hex, extra):
    img = Image.new("RGBA", (W, H), (10, 10, 18, 255))
    d = ImageDraw.Draw(img, "RGBA")

    accent = _rgb(accent_hex)
    base   = _rgb(base_hex)
    cx, cy = W // 2, H // 2 - 20

    # Subtle accent haze at bottom
    for i in range(30):
        a = int(i * 2.5)
        d.rectangle([0, H - i - 1, W, H - i], fill=(*accent, a // 6))

    DRAW_FNS[body_type](d, img, cx, cy, base, accent, **extra)
    _vignette(img)

    d2 = ImageDraw.Draw(img, "RGBA")
    _frame(d2, accent)
    _labels(d2, name, group, accent)

    os.makedirs(OUT, exist_ok=True)
    img.save(os.path.join(OUT, f"{race_id}.png"))
    print(f"  ✓  {race_id}.png")


if __name__ == "__main__":
    print(f"Generating {len(RACES)} portraits → {OUT}\n")
    for race_id, data in RACES.items():
        make_portrait(race_id, *data)
    print(f"\nDone.")
