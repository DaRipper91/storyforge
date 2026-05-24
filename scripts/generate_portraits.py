#!/usr/bin/env python3
"""
Generate 800×1120 PNG portrait cards for all 35 StoryForge races.

Run from the project root:
    uv run python scripts/generate_portraits.py

Output: godot/assets/characters/<race_id>.png
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
import os, math, random

OUT = os.path.join(os.path.dirname(__file__), "..", "godot", "assets", "characters")
W, H = 800, 1120

# ── Color helpers ──────────────────────────────────────────────────────────────

def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def _lighten(c, amt=60):
    return tuple(min(255, v + amt) for v in c)

def _darken(c, amt=60):
    return tuple(max(0, v - amt) for v in c)

def _blend(c1, c2, t):
    return tuple(int(c1[i] * (1 - t) + c2[i] * t) for i in range(3))


# ── Low-level layer helpers ────────────────────────────────────────────────────

def _radial_alpha(cx, cy, r_inner, r_outer, W=W, H=H):
    """Return an (H, W) float32 array: 1.0 inside r_inner, 0.0 outside r_outer."""
    yy, xx = np.mgrid[0:H, 0:W]
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2).astype(np.float32)
    mask = np.clip((r_outer - dist) / max(r_outer - r_inner, 1), 0.0, 1.0)
    return mask


def _solid_rgba(color_rgb, alpha_map):
    """Build RGBA array from solid RGB + float alpha map."""
    arr = np.zeros((H, W, 4), dtype=np.uint8)
    arr[:, :, 0] = color_rgb[0]
    arr[:, :, 1] = color_rgb[1]
    arr[:, :, 2] = color_rgb[2]
    arr[:, :, 3] = (alpha_map * 255).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def _noise_layer(seed, scale=4, low=0, high=60):
    """Create a grayscale noise RGBA layer using simple sum-of-sin waves."""
    rng = np.random.default_rng(seed)
    freqs = rng.uniform(0.5, 3.0, (8, 2))
    phases = rng.uniform(0, 2 * math.pi, 8)
    yy, xx = np.mgrid[0:H, 0:W]
    field = np.zeros((H, W), dtype=np.float32)
    for (fx, fy), ph in zip(freqs, phases):
        field += np.sin(xx * fx / (W / scale) + yy * fy / (H / scale) + ph)
    field = (field - field.min()) / (field.max() - field.min() + 1e-9)
    v = (field * (high - low) + low).astype(np.uint8)
    arr = np.zeros((H, W, 4), dtype=np.uint8)
    arr[:, :, 3] = v
    return Image.fromarray(arr, "RGBA")


def _glow_blob(cx, cy, radius, color, alpha=180, blur=40):
    """Return an RGBA image with a single soft-glowing blob."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")
    d.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
              fill=(*color, alpha))
    return layer.filter(ImageFilter.GaussianBlur(blur))


def _scatter_particles(rng, color, count=80, alpha_max=140):
    """Scatter small glowing particles across the canvas."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")
    for _ in range(count):
        x = int(rng.uniform(20, W - 20))
        y = int(rng.uniform(20, H - 180))
        r = int(rng.uniform(1, 4))
        a = int(rng.uniform(30, alpha_max))
        d.ellipse([x - r, y - r, x + r, y + r], fill=(*color, a))
    blur_r = 2
    return layer.filter(ImageFilter.GaussianBlur(blur_r))


# ── Group-themed backgrounds ───────────────────────────────────────────────────

def _bg_cosmic(accent, seed):
    rng = np.random.default_rng(seed)
    # Deep space base
    arr = np.zeros((H, W, 4), dtype=np.uint8)
    arr[:, :, 2] = 18
    arr[:, :, 3] = 255
    img = Image.fromarray(arr, "RGBA")

    # Nebula wash
    nebula = _glow_blob(W // 2, H // 2 - 100, 380, accent, alpha=55, blur=90)
    img.alpha_composite(nebula)
    nebula2 = _glow_blob(W // 2 - 120, H // 3, 200, _lighten(accent, 30), alpha=28, blur=70)
    img.alpha_composite(nebula2)

    # Star field
    d = ImageDraw.Draw(img, "RGBA")
    for _ in range(600):
        x = int(rng.integers(0, W))
        y = int(rng.integers(0, H))
        b = float(rng.random())
        r = max(1, int(b * 2.5))
        a = int(b * 160 + 60)
        brightness = int(b * 200 + 55)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(brightness, brightness, brightness, a))

    # Subtle noise
    noise = _noise_layer(seed + 1, scale=6, low=0, high=25)
    arr2 = np.array(noise)
    arr2[:, :, 0] = arr2[:, :, 3] // 4
    arr2[:, :, 2] = arr2[:, :, 3]
    img.alpha_composite(Image.fromarray(arr2, "RGBA"))
    return img


def _bg_primal(accent, seed):
    rng = np.random.default_rng(seed)
    arr = np.zeros((H, W, 4), dtype=np.uint8)
    # Dark forest base — dark green-black
    arr[:, :, 1] = 14
    arr[:, :, 3] = 255
    img = Image.fromarray(arr, "RGBA")

    # Organic mid-glow
    glow = _glow_blob(W // 2, H // 2, 320, accent, alpha=40, blur=80)
    img.alpha_composite(glow)

    # Vine / root network using random lines
    d = ImageDraw.Draw(img, "RGBA")
    vine_color = _darken(accent, 40)
    for _ in range(30):
        x0 = int(rng.integers(-50, W + 50))
        y0 = int(rng.integers(H // 3, H + 50))
        for seg in range(int(rng.integers(3, 8))):
            dx = int(rng.integers(-80, 80))
            dy = int(rng.integers(-120, -20))
            x1, y1 = x0 + dx, y0 + dy
            d.line([x0, y0, x1, y1], fill=(*vine_color, 35), width=int(rng.integers(1, 3)))
            x0, y0 = x1, y1

    # Organic noise
    noise = _noise_layer(seed, scale=5, low=0, high=30)
    arr2 = np.array(noise)
    arr2[:, :, 1] = arr2[:, :, 3]
    arr2[:, :, 3] = arr2[:, :, 3] // 2
    img.alpha_composite(Image.fromarray(arr2, "RGBA"))
    return img


def _bg_eldritch(accent, seed):
    rng = np.random.default_rng(seed)
    arr = np.zeros((H, W, 4), dtype=np.uint8)
    arr[:, :, 0] = 12
    arr[:, :, 3] = 255
    img = Image.fromarray(arr, "RGBA")

    # Corruption glow
    glow = _glow_blob(W // 2, H // 2 + 50, 340, accent, alpha=45, blur=85)
    img.alpha_composite(glow)
    glow2 = _glow_blob(int(rng.integers(100, 700)), int(rng.integers(100, 600)),
                       180, _lighten(accent, 20), alpha=22, blur=60)
    img.alpha_composite(glow2)

    # Eldritch rune circles
    d = ImageDraw.Draw(img, "RGBA")
    for r in [280, 220, 160, 90]:
        d.ellipse([W // 2 - r, H // 2 - r, W // 2 + r, H // 2 + r],
                  outline=(*accent, 18), width=1)
    # Corruption tendrils
    for _ in range(20):
        angle = float(rng.uniform(0, 2 * math.pi))
        for seg in range(int(rng.integers(4, 10))):
            x0 = int(W // 2 + math.cos(angle) * seg * 40 + rng.integers(-20, 20))
            y0 = int(H // 2 + math.sin(angle) * seg * 40 + rng.integers(-20, 20))
            x1 = int(W // 2 + math.cos(angle) * (seg + 1) * 40 + rng.integers(-25, 25))
            y1 = int(H // 2 + math.sin(angle) * (seg + 1) * 40 + rng.integers(-25, 25))
            d.line([x0, y0, x1, y1], fill=(*accent, 20), width=1)

    noise = _noise_layer(seed, scale=4, low=0, high=30)
    arr2 = np.array(noise)
    arr2[:, :, 0] = arr2[:, :, 3]
    arr2[:, :, 3] = arr2[:, :, 3] // 2
    img.alpha_composite(Image.fromarray(arr2, "RGBA"))
    return img


def _bg_mechanical(accent, seed):
    rng = np.random.default_rng(seed)
    arr = np.zeros((H, W, 4), dtype=np.uint8)
    # Dark steel base
    v = 16
    arr[:, :, 0] = v
    arr[:, :, 1] = v
    arr[:, :, 2] = v + 8
    arr[:, :, 3] = 255
    img = Image.fromarray(arr, "RGBA")

    # Core energy glow
    glow = _glow_blob(W // 2, H // 2 + 80, 280, accent, alpha=50, blur=80)
    img.alpha_composite(glow)

    # Circuit / grid lines
    d = ImageDraw.Draw(img, "RGBA")
    grid_col = (*accent, 18)
    for x in range(0, W, 40):
        d.line([x, 0, x, H], fill=grid_col, width=1)
    for y in range(0, H, 40):
        d.line([0, y, W, y], fill=grid_col, width=1)

    # Circuit trace decorations
    for _ in range(25):
        x0 = int(rng.choice(range(0, W, 40)))
        y0 = int(rng.choice(range(0, H, 40)))
        length = int(rng.integers(2, 6)) * 40
        horiz = bool(rng.integers(0, 2))
        x1 = x0 + (length if horiz else 0)
        y1 = y0 + (0 if horiz else length)
        d.line([x0, y0, x1, y1], fill=(*accent, 28), width=2)
        d.ellipse([x1 - 4, y1 - 4, x1 + 4, y1 + 4], fill=(*accent, 45))

    return img


def _bg_humanoid(accent, seed):
    rng = np.random.default_rng(seed)
    arr = np.zeros((H, W, 4), dtype=np.uint8)
    # Dark stone base
    v = 20
    arr[:, :, 0] = v
    arr[:, :, 1] = int(v * 0.9)
    arr[:, :, 2] = int(v * 0.8)
    arr[:, :, 3] = 255
    img = Image.fromarray(arr, "RGBA")

    # Ambient glow behind character
    glow = _glow_blob(W // 2, H // 2, 320, accent, alpha=38, blur=100)
    img.alpha_composite(glow)

    # Stone texture with noise
    noise = _noise_layer(seed, scale=8, low=0, high=22)
    arr2 = np.array(noise)
    v2 = arr2[:, :, 3]
    arr2[:, :, 0] = v2
    arr2[:, :, 1] = (v2 * 0.9).astype(np.uint8)
    arr2[:, :, 2] = (v2 * 0.8).astype(np.uint8)
    arr2[:, :, 3] = (v2 * 0.6).astype(np.uint8)
    img.alpha_composite(Image.fromarray(arr2, "RGBA"))

    # Subtle heraldic diagonal lines
    d = ImageDraw.Draw(img, "RGBA")
    for i in range(-H, W + H, 60):
        d.line([i, 0, i + H, H], fill=(*accent, 8), width=1)

    return img


BG_MAKERS = {
    "Cosmic":     _bg_cosmic,
    "Primal":     _bg_primal,
    "Eldritch":   _bg_eldritch,
    "Mechanical": _bg_mechanical,
    "Humanoid":   _bg_humanoid,
}


# ── Character silhouette + glow compositing ────────────────────────────────────

def _composite_character(bg, silhouette_fn, cx, cy, base, accent, extra):
    """
    Draw character with:
      1. Large blurred aura behind character
      2. Soft inner glow slightly expanding silhouette
      3. Sharp silhouette on top
    """
    # 1. Aura — large blurred accent blob
    aura_r = extra.get("aura_r", 180)
    aura = _glow_blob(cx, cy, aura_r, accent, alpha=extra.get("aura_alpha", 60),
                      blur=extra.get("aura_blur", 55))
    bg.alpha_composite(aura)

    # 2. Soft glow — same silhouette, slightly expanded, accent colored, blurred
    glow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow_layer, "RGBA")
    silhouette_fn(gd, glow_layer, cx, cy, accent, accent, expand=10, **extra)
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(18))
    bg.alpha_composite(glow_layer)

    # 3. Sharp character on top
    char_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cd = ImageDraw.Draw(char_layer, "RGBA")
    silhouette_fn(cd, char_layer, cx, cy, base, accent, expand=0, **extra)

    # Rim light — draw a very thin highlight layer blurred lightly
    rim_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rd = ImageDraw.Draw(rim_layer, "RGBA")
    rim_col = _lighten(accent, 80)
    silhouette_fn(rd, rim_layer, cx - 12, cy - 8, rim_col, rim_col, expand=4, **extra)
    rim_layer = rim_layer.filter(ImageFilter.GaussianBlur(5))
    # Mask rim to only show where character is
    bg.alpha_composite(rim_layer)
    bg.alpha_composite(char_layer)


# ── Body-type silhouette functions ────────────────────────────────────────────
# Each function draws onto draw `d`, img `img`, centered at (cx, cy).
# `expand` offsets all sizes outward by this many px (used for glow silhouette).

def _ell(d, cx, cy, rx, ry, col, a=255, expand=0):
    rx += expand; ry += expand
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=(*col, a))

def _rect(d, x0, y0, x1, y1, col, a=255, expand=0):
    d.rectangle([x0 - expand, y0 - expand, x1 + expand, y1 + expand], fill=(*col, a))

def _poly(d, pts, col, a=255):
    d.polygon(pts, fill=(*col, a))


def draw_ethereal(d, img, cx, cy, base, accent, expand=0, **_):
    e = expand
    # Wide misty body tapering to wisps
    _ell(d, cx, cy - 40, 72 + e, 110 + e, base, 180)
    _ell(d, cx, cy - 80, 48 + e, 60 + e, base, 200)
    # Face void
    _ell(d, cx, cy - 100, 36 + e, 42 + e, _lighten(base, 30), 215)
    # Eyes
    _ell(d, cx - 16, cy - 110, 9 + e, 9 + e, accent, 240)
    _ell(d, cx + 16, cy - 110, 9 + e, 9 + e, accent, 240)
    # Wisp tails
    for ox, base_y in [(-50, cy + 60), (-20, cy + 80), (20, cy + 85), (50, cy + 65)]:
        for j in range(6):
            a_val = max(0, 170 - j * 28)
            _ell(d, cx + ox, base_y + j * 30, max(1, 12 + e - j * 2), max(1, 14 + e - j * 2),
                 base, a_val)
    # Shoulder wisps
    for ox in [-80, 80]:
        for j in range(4):
            _ell(d, cx + ox + (4 if ox > 0 else -4) * j, cy - 20 - j * 12,
                 max(1, 18 + e - j * 4), max(1, 16 + e - j * 4), base, 130 - j * 25)


def draw_insectoid(d, img, cx, cy, base, accent, legs=6, expand=0, **_):
    e = expand
    # Abdomen (bottom)
    _ell(d, cx, cy + 70, 32 + e, 55 + e, base, 205)
    # Thorax
    _ell(d, cx, cy - 10, 30 + e, 38 + e, base, 220)
    # Head
    _ell(d, cx, cy - 72, 24 + e, 30 + e, base, 235)
    # Mandibles
    d.line([cx - 20, cy - 52, cx - 38, cy - 80], fill=(*accent, 210), width=3 + e // 2)
    d.line([cx + 20, cy - 52, cx + 38, cy - 80], fill=(*accent, 210), width=3 + e // 2)
    # Antenna
    d.line([cx - 8, cy - 100, cx - 28, cy - 150], fill=(*accent, 200), width=2)
    d.line([cx + 8, cy - 100, cx + 28, cy - 150], fill=(*accent, 200), width=2)
    _ell(d, cx - 28, cy - 152, 6 + e, 6 + e, accent, 220)
    _ell(d, cx + 28, cy - 152, 6 + e, 6 + e, accent, 220)
    # Compound eyes
    for ex, ey in [(-13, cy - 74), (13, cy - 74)]:
        _ell(d, cx + ex, ey, 7 + e, 7 + e, accent, 245)
    # Legs — 3 pairs
    for i in range(legs // 2):
        yl = cy - 5 + i * 22
        for side in [-1, 1]:
            sx = cx + side * 30
            mx = cx + side * 80
            ex2 = cx + side * (100 + i * 5)
            ey2 = yl + 35
            d.line([sx, yl, mx, yl + 12], fill=(*base, 195), width=3)
            d.line([mx, yl + 12, ex2, ey2], fill=(*base, 165), width=2)


def draw_hulking(d, img, cx, cy, base, accent, expand=0, **_):
    e = expand
    # Legs
    _ell(d, cx - 32, cy + 110, 22 + e, 45 + e, base, 195)
    _ell(d, cx + 32, cy + 110, 22 + e, 45 + e, base, 195)
    # Hips
    _ell(d, cx, cy + 60, 70 + e, 40 + e, base, 210)
    # Torso
    _ell(d, cx, cy - 15, 78 + e, 70 + e, base, 218)
    # Massive shoulders
    _ell(d, cx - 95, cy - 40, 40 + e, 38 + e, base, 205)
    _ell(d, cx + 95, cy - 40, 40 + e, 38 + e, base, 205)
    # Upper arms
    _ell(d, cx - 100, cy + 15, 28 + e, 45 + e, base, 198)
    _ell(d, cx + 100, cy + 15, 28 + e, 45 + e, base, 198)
    # Forearms / fists
    _ell(d, cx - 105, cy + 78, 22 + e, 35 + e, base, 188)
    _ell(d, cx + 105, cy + 78, 22 + e, 35 + e, base, 188)
    # Neck
    _ell(d, cx, cy - 82, 24 + e, 22 + e, base, 225)
    # Head
    _ell(d, cx, cy - 125, 36 + e, 38 + e, base, 232)
    # Eyes
    for ex in [-14, 14]:
        _ell(d, cx + ex, cy - 132, 8 + e, 8 + e, accent, 245)
    # Chest runes / energy nodes
    for ox, oy in [(-22, cy - 30), (0, cy - 10), (22, cy - 30), (-14, cy + 20), (14, cy + 20)]:
        _ell(d, cx + ox, oy, 8 + e, 8 + e, accent, 160)


def draw_predator(d, img, cx, cy, base, accent, has_tail=True, expand=0, **_):
    e = expand
    # Legs
    _rect(d, cx - 26, cy + 58, cx - 8, cy + 145, base, 195, e)
    _rect(d, cx + 8, cy + 58, cx + 26, cy + 145, base, 195, e)
    # Lower body
    _ell(d, cx, cy + 35, 42 + e, 30 + e, base, 215)
    # Arms
    _ell(d, cx - 55, cy - 28, 22 + e, 55 + e, base, 192)
    _ell(d, cx + 55, cy - 28, 22 + e, 55 + e, base, 192)
    # Torso
    _ell(d, cx, cy - 20, 50 + e, 65 + e, base, 225)
    # Neck
    _ell(d, cx, cy - 82, 20 + e, 22 + e, base, 228)
    # Head — slightly angular
    _ell(d, cx, cy - 118, 32 + e, 36 + e, base, 235)
    # Muzzle hint
    _ell(d, cx, cy - 112, 18 + e, 12 + e, _darken(base, 15), 220)
    # Eyes
    for ex in [-14, 14]:
        _ell(d, cx + ex, cy - 126, 7 + e, 7 + e, accent, 248)
    if has_tail:
        pts = []
        for i in range(8):
            tx = cx + 30 + i * 15
            ty = cy + 50 + i * 18
            pts.append((tx, ty))
        for i in range(len(pts) - 1):
            w = max(1, 14 + e - i * 2)
            d.line([pts[i], pts[i + 1]], fill=(*base, 200 - i * 18), width=w)


def draw_avian(d, img, cx, cy, base, accent, expand=0, **_):
    e = expand
    # Wing spans — large impressive
    _poly(d, [cx, cy - 30,  cx - 160, cy - 60, cx - 140, cy + 45, cx - 25, cy + 20],
          base, 170)
    _poly(d, [cx, cy - 30,  cx + 160, cy - 60, cx + 140, cy + 45, cx + 25, cy + 20],
          base, 170)
    # Wing feather detail lines
    for ox, sign in [(-1, -1), (1, 1)]:
        for j in range(5):
            fx0 = cx + sign * (30 + j * 25)
            fy0 = cy - 22 + j * 8
            fx1 = cx + sign * (80 + j * 20)
            fy1 = cy + 32 + j * 4
            d.line([fx0, fy0, fx1, fy1], fill=(*accent, 80), width=2)
    # Body
    _ell(d, cx, cy + 10, 32 + e, 52 + e, base, 228)
    # Neck
    _ell(d, cx, cy - 52, 20 + e, 28 + e, base, 232)
    # Head
    _ell(d, cx, cy - 100, 30 + e, 34 + e, base, 240)
    # Crest feathers
    for ox, h in [(-16, 40), (-7, 55), (0, 62), (7, 55), (16, 40)]:
        _poly(d, [cx + ox - 5, cy - 130, cx + ox + 5, cy - 130, cx + ox, cy - 130 - h],
              accent, 200)
    # Eyes
    for ex in [-12, 12]:
        _ell(d, cx + ex, cy - 106, 7 + e, 7 + e, accent, 252)
    # Legs / talons
    for lx, side in [(-14, -1), (14, 1)]:
        d.line([cx + lx, cy + 60, cx + lx + side * 6, cy + 130], fill=(*base, 185), width=5)
        for j in range(3):
            tx0 = cx + lx + side * 6
            ty0 = cy + 130
            d.line([tx0, ty0, tx0 + side * (10 + j * 5), ty0 + 15],
                   fill=(*base, 160), width=2)


def draw_horror(d, img, cx, cy, base, accent, has_cape=False, has_bones=False, expand=0, **_):
    e = expand
    if has_cape:
        _poly(d, [cx, cy - 65,
                  cx - 110, cy + 30, cx - 90, cy + 165,
                  cx, cy + 130,
                  cx + 90, cy + 165, cx + 110, cy + 30], base, 110)
    # Thin elongated torso
    _ell(d, cx - 32, cy - 28, 22 + e, 52 + e, base, 190)
    _ell(d, cx + 32, cy - 28, 22 + e, 52 + e, base, 190)
    _ell(d, cx, cy - 20, 36 + e, 68 + e, base, 220)
    # Spindly neck
    _ell(d, cx, cy - 88, 14 + e, 24 + e, base, 228)
    # Elongated skull
    _ell(d, cx, cy - 135, 28 + e, 46 + e, base, 235)
    if has_bones:
        # Bone spurs on torso
        for ox, oy in [(-28, cy - 50), (-28, cy - 10), (28, cy - 50), (28, cy - 10),
                       (0, cy - 75)]:
            _poly(d, [cx + ox - 5, cy + oy, cx + ox + 5, cy + oy, cx + ox, cy + oy - 24],
                  accent, 210)
    # Glowing eyes
    for ex, ey in [(-12, cy - 145), (12, cy - 145)]:
        _ell(d, cx + ex, ey, 8 + e, 8 + e, accent, 255)
    # Clawed hands
    for sx, ey2 in [(-55, cy + 40), (55, cy + 40)]:
        for j in range(4):
            angle = math.pi * (0.2 + j * 0.2) * (-1 if sx < 0 else 1)
            fx = cx + sx + int(math.cos(angle) * 22)
            fy = ey2 + int(math.sin(angle) * 18)
            d.line([cx + sx, ey2, fx, fy], fill=(*base, 175), width=3)
    # Leg wisps
    for ox in [-16, 16]:
        _rect(d, cx + ox - 8, cy + 45, cx + ox + 8, cy + 140, base, 185, e)


def draw_arachnid(d, img, cx, cy, base, accent, expand=0, **_):
    e = expand
    # Large abdomen
    _ell(d, cx, cy + 65, 45 + e, 62 + e, base, 215)
    # Cephalothorax
    _ell(d, cx, cy - 10, 42 + e, 45 + e, base, 230)
    # Head with fang cluster
    _ell(d, cx, cy - 68, 26 + e, 28 + e, base, 242)
    # Chelicerae / fangs
    for fx, fy in [(-12, cy - 80), (12, cy - 80)]:
        d.line([cx + fx, cy - 58, cx + fx + (fx // abs(fx)) * 12, cy - 95],
               fill=(*accent, 200), width=3)
    # 8 eyes
    eye_pts = [(-16, cy - 74), (-8, cy - 80), (8, cy - 80), (16, cy - 74),
               (-12, cy - 68), (-4, cy - 72), (4, cy - 72), (12, cy - 68)]
    for ex, ey in eye_pts:
        _ell(d, cx + ex, ey, 4 + e, 4 + e, accent, 240)
    # 8 legs — 2-segment each
    leg_data = [
        (-42, cy - 18, -110, cy - 60, -140, cy - 10),
        (-42, cy,      -108, cy - 12, -138, cy + 40),
        (-42, cy + 18, -100, cy + 30, -128, cy + 78),
        (-42, cy + 36,  -85, cy + 60, -105, cy + 105),
        ( 42, cy - 18,  110, cy - 60,  140, cy - 10),
        ( 42, cy,       108, cy - 12,  138, cy + 40),
        ( 42, cy + 18,  100, cy + 30,  128, cy + 78),
        ( 42, cy + 36,   85, cy + 60,  105, cy + 105),
    ]
    for x0, y0, x1, y1, x2, y2 in leg_data:
        d.line([cx + x0, y0, cx + x1, y1], fill=(*base, 205), width=3)
        d.line([cx + x1, y1, cx + x2, y2], fill=(*base, 168), width=2)
        _ell(d, cx + x2, y2, 4, 4, accent, 100)


def draw_mechanical(d, img, cx, cy, base, accent, gear=False, wires=False, expand=0, **_):
    e = expand
    # Legs
    _rect(d, cx - 38, cy + 62, cx - 12, cy + 150, base, 200, e)
    _rect(d, cx + 12, cy + 62, cx + 38, cy + 150, base, 200, e)
    # Feet
    _rect(d, cx - 45, cy + 140, cx - 8, cy + 158, base, 185, e)
    _rect(d, cx + 8, cy + 140, cx + 45, cy + 158, base, 185, e)
    # Lower torso
    _rect(d, cx - 40, cy + 20, cx + 40, cy + 65, base, 215, e)
    # Chest plate
    _rect(d, cx - 52, cy - 65, cx + 52, cy + 25, base, 228, e)
    # Shoulder pauldrons
    _rect(d, cx - 90, cy - 75, cx - 48, cy - 10, base, 210, e)
    _rect(d, cx + 48, cy - 75, cx + 90, cy - 10, base, 210, e)
    # Arms
    _rect(d, cx - 85, cy - 8, cx - 50, cy + 58, base, 200, e)
    _rect(d, cx + 50, cy - 8, cx + 85, cy + 58, base, 200, e)
    # Panel lines on chest
    if not expand:
        d.line([cx - 50, cy - 22, cx + 50, cy - 22], fill=(*accent, 90), width=2)
        d.line([cx - 50, cy + 5, cx + 50, cy + 5], fill=(*accent, 60), width=2)
    # Neck
    _rect(d, cx - 16, cy - 88, cx + 16, cy - 65, base, 225, e)
    # Head
    _rect(d, cx - 30, cy - 140, cx + 30, cy - 88, base, 235, e)
    # Visor
    _rect(d, cx - 26, cy - 128, cx + 26, cy - 102, accent, 190, e)
    if gear:
        for ang in range(0, 360, 45):
            rad = math.radians(ang)
            gx = int(cx + math.cos(rad) * 28)
            gy = int(cy + 45 + math.sin(rad) * 28)
            _ell(d, gx, gy, 6 + e, 6 + e, accent, 130)
    if wires:
        for x0, y0, x1, y1 in [(-52, cy - 30, -100, cy - 60),
                                (52, cy - 30, 100, cy - 60),
                                (-38, cy + 40, -70, cy + 85)]:
            d.line([cx + x0, y0, cx + x1, y1], fill=(*accent, 160), width=3)


def draw_plant(d, img, cx, cy, base, accent, expand=0, **_):
    e = expand
    # Root-like legs
    for ox, w in [(-28, 12), (0, 10), (28, 12)]:
        ys = cy + 70
        for seg in range(5):
            curve = int(math.sin(seg * 0.8 + ox * 0.05) * 14)
            d.line([cx + ox + curve, ys + seg * 18,
                    cx + ox + curve + 4, ys + (seg + 1) * 18],
                   fill=(*base, 190 - seg * 15), width=max(1, w - seg * 2))
    # Torso
    _ell(d, cx, cy, 42 + e, 72 + e, base, 215)
    # Leaf-arms
    for side in [-1, 1]:
        _poly(d, [cx + side * 44, cy - 40,
                  cx + side * 110, cy - 75,
                  cx + side * 100, cy - 8,
                  cx + side * 40, cy + 15], base, 178)
        # Leaf veins
        for j in range(3):
            vx0 = cx + side * (50 + j * 15)
            d.line([vx0, cy - 35 + j * 15, vx0 + side * 30, cy - 55 + j * 10],
                   fill=(*accent, 60), width=1)
    # Neck / stem
    _ell(d, cx, cy - 95, 18 + e, 28 + e, base, 228)
    # Head — blossom/bulb
    _ell(d, cx, cy - 145, 38 + e, 44 + e, base, 235)
    # Petal crown
    for ang in range(0, 360, 72):
        rad = math.radians(ang)
        px = int(cx + math.cos(rad) * 52)
        py = int(cy - 148 + math.sin(rad) * 42)
        _ell(d, px, py, 14 + e, 20 + e, accent, 175)
    # Eyes
    for ex in [-12, 12]:
        _ell(d, cx + ex, cy - 150, 7 + e, 7 + e, accent, 245)


def draw_compact(d, img, cx, cy, base, accent, expand=0, **_):
    e = expand
    # Short legs
    _ell(d, cx - 22, cy + 85, 18 + e, 32 + e, base, 192)
    _ell(d, cx + 22, cy + 85, 18 + e, 32 + e, base, 192)
    # Stocky torso
    _ell(d, cx, cy + 10, 58 + e, 60 + e, base, 222)
    # Short arms
    _ell(d, cx - 68, cy - 12, 22 + e, 42 + e, base, 200)
    _ell(d, cx + 68, cy - 12, 22 + e, 42 + e, base, 200)
    # Neck
    _ell(d, cx, cy - 72, 24 + e, 20 + e, base, 228)
    # Oversized head
    _ell(d, cx, cy - 128, 50 + e, 54 + e, base, 238)
    # Horns / spikes
    for ox, h in [(-18, 52), (-8, 70), (8, 70), (18, 52)]:
        _poly(d, [cx + ox - 6, cy - 178, cx + ox + 6, cy - 178, cx + ox, cy - 178 - h],
              accent, 215)
    # Big eyes
    for ex in [-20, 20]:
        _ell(d, cx + ex, cy - 138, 12 + e, 14 + e, accent, 252)
        _ell(d, cx + ex, cy - 138, 6 + e, 7 + e, _darken(accent, 60), 255)
    # Chest core
    _ell(d, cx, cy - 20, 22 + e, 22 + e, accent, 190)


def draw_cephalopod(d, img, cx, cy, base, accent, expand=0, **_):
    e = expand
    # Large mantle/head
    _ell(d, cx, cy - 55, 88 + e, 80 + e, base, 215)
    # Narrower body collar
    _ell(d, cx, cy + 10, 55 + e, 35 + e, base, 228)
    # 4 large eyes
    eye_pts = [(-30, cy - 60), (-10, cy - 70), (10, cy - 70), (30, cy - 60)]
    for ex, ey in eye_pts:
        _ell(d, cx + ex, ey, 12 + e, 10 + e, accent, 235)
        _ell(d, cx + ex, ey, 6 + e, 6 + e, _darken(accent, 40), 255)
    # 8 tentacles
    for i in range(8):
        angle = math.pi * (i / 7.0)
        x0 = int(cx + math.cos(angle) * 50)
        y0 = cy + 35
        for seg in range(7):
            curve = int(math.sin(seg * 0.7 + i * 0.5) * 20)
            dx = int(math.cos(angle) * 10 + curve * 0.3)
            x1 = x0 + dx
            y1 = y0 + 35 + seg * 30
            d.line([x0, y0, x1, y1], fill=(*base, 200 - seg * 16), width=max(1, 10 - seg))
            _ell(d, x1, y1 + 10, 4 + e, 4 + e, accent, 80 - seg * 8)
            x0, y0 = x1, y1


def draw_humanoid(d, img, cx, cy, base, accent, feature="default", expand=0, **_):
    e = expand
    if feature == "cloak":
        _poly(d, [cx - 42, cy - 80,
                  cx - 110, cy + 20, cx - 95, cy + 170,
                  cx, cy + 140,
                  cx + 95, cy + 170, cx + 110, cy + 20, cx + 42, cy - 80],
              _darken(base, 20), 115)
    # Legs
    _rect(d, cx - 30, cy + 55, cx - 8, cy + 155, base, 195, e)
    _rect(d, cx + 8, cy + 55, cx + 30, cy + 155, base, 195, e)
    # Feet
    _ell(d, cx - 22, cy + 155, 22 + e, 12 + e, base, 182)
    _ell(d, cx + 22, cy + 155, 22 + e, 12 + e, base, 182)
    # Hips
    _ell(d, cx, cy + 45, 42 + e, 20 + e, base, 210)
    # Torso
    _ell(d, cx, cy - 18, 42 + e, 68 + e, base, 225)
    # Shoulders
    _ell(d, cx - 55, cy - 52, 22 + e, 22 + e, base, 208)
    _ell(d, cx + 55, cy - 52, 22 + e, 22 + e, base, 208)
    # Upper arms
    _rect(d, cx - 72, cy - 52, cx - 42, cy + 22, base, 198, e)
    _rect(d, cx + 42, cy - 52, cx + 72, cy + 22, base, 198, e)
    # Forearms
    _rect(d, cx - 70, cy + 20, cx - 44, cy + 82, base, 188, e)
    _rect(d, cx + 44, cy + 20, cx + 70, cy + 82, base, 188, e)
    # Neck
    _ell(d, cx, cy - 85, 18 + e, 22 + e, base, 228)
    # Head
    _ell(d, cx, cy - 135, 34 + e, 40 + e, base, 238)
    # Eyes
    for ex in [-14, 14]:
        _ell(d, cx + ex, cy - 142, 8 + e, 8 + e, accent, 245)

    if feature == "crown":
        for ox, h in [(-16, 22), (-7, 32), (0, 38), (7, 32), (16, 22)]:
            _poly(d, [cx + ox - 5, cy - 172, cx + ox + 5, cy - 172, cx + ox, cy - 172 - h],
                  accent, 228)
    elif feature == "aura":
        for r_a in [52, 38, 24]:
            ring = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            rd = ImageDraw.Draw(ring, "RGBA")
            rd.ellipse([cx - r_a, cy - 190 - r_a, cx + r_a, cy - 190 + r_a],
                       outline=(*accent, 140), width=3)
            ring = ring.filter(ImageFilter.GaussianBlur(4))
            img.alpha_composite(ring)
    elif feature == "scars":
        for sx, sy, ex_c, ey_c in [(-12, cy - 55, -4, cy - 25),
                                    (8, cy - 62, 16, cy - 32),
                                    (-6, cy + 5, 2, cy + 32)]:
            d.line([cx + sx, cy + sy, cx + ex_c, ey_c], fill=(*accent, 190), width=3)
    elif feature == "thorns_sm":
        for ox, oy in [(-44, cy - 58), (44, cy - 58), (-44, cy - 28), (44, cy - 28),
                       (-44, cy + 2), (44, cy + 2)]:
            _poly(d, [cx + ox - 4, cy + oy, cx + ox + 4, cy + oy, cx + ox, cy + oy - 18],
                  accent, 210)
    elif feature == "glow_body":
        for oy in range(-60, 80, 18):
            _ell(d, cx, cy + oy, 16 + e, 10 + e, accent, 100)
    elif feature == "fire_crown":
        for ox, h in [(-20, 30), (-10, 46), (0, 58), (10, 46), (20, 30)]:
            _poly(d, [cx + ox - 5, cy - 172, cx + ox + 5, cy - 172, cx + ox, cy - 172 - h],
                  accent, 210)
    elif feature == "fracture":
        for pts in [[(cx - 22, cy - 75), (cx - 8, cy + 12), (cx - 16, cy + 82)],
                    [(cx + 10, cy - 68), (cx + 20, cy + 5), (cx + 8, cy + 75)]]:
            d.line(pts, fill=(*accent, 130), width=2)
    elif feature == "halo":
        ring = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        rd = ImageDraw.Draw(ring, "RGBA")
        rd.ellipse([cx - 42, cy - 200, cx + 42, cy - 158], outline=(*accent, 200), width=5)
        ring = ring.filter(ImageFilter.GaussianBlur(6))
        img.alpha_composite(ring)
    elif feature == "split":
        d.line([(cx, cy - 175), (cx, cy + 170)], fill=(*accent, 80), width=2)
        _ell(d, cx - 12, cy - 148, 8 + e, 8 + e, _rgb("#e05030"), 240)
    elif feature == "antenna":
        for sign, ox in [(-1, -5), (1, 5)]:
            d.line([cx + ox, cy - 174, cx + ox + sign * 22, cy - 215],
                   fill=(*accent, 210), width=3)
            _ell(d, cx + ox + sign * 22, cy - 217, 8 + e, 8 + e, accent, 238)
    elif feature == "shadow_void":
        pass  # aura handles this one
    elif feature == "scales":
        for row in range(6):
            for col in range(4):
                sx = cx - 30 + col * 20
                sy = cy - 50 + row * 22
                d.ellipse([sx, sy, sx + 16, sy + 14], outline=(*accent, 100), width=2)
    elif feature == "wings_small":
        _poly(d, [cx - 44, cy - 68, cx - 105, cy - 20, cx - 90, cy + 30, cx - 38, cy - 10],
              base, 155)
        _poly(d, [cx + 44, cy - 68, cx + 105, cy - 20, cx + 90, cy + 30, cx + 38, cy - 10],
              base, 155)


# ── Frame & labels ─────────────────────────────────────────────────────────────

def _frame(img, accent):
    d = ImageDraw.Draw(img, "RGBA")
    # Outer border
    d.rectangle([2, 2, W - 3, H - 3], outline=(*accent, 120), width=3)
    # Inner border
    d.rectangle([8, 8, W - 9, H - 9], outline=(*accent, 45), width=1)
    # Corner diamonds
    for cx2, cy2 in [(8, 8), (W - 9, 8), (8, H - 9), (W - 9, H - 9)]:
        size = 12
        d.polygon([cx2, cy2 - size, cx2 + size, cy2, cx2, cy2 + size, cx2 - size, cy2],
                  fill=(*accent, 130))
    # Mid-border decorative lines
    mid_y = 16
    d.line([24, mid_y, W - 24, mid_y], fill=(*accent, 35), width=1)
    d.line([24, H - mid_y, W - 24, H - mid_y], fill=(*accent, 35), width=1)


def _labels(img, name, group, accent):
    d = ImageDraw.Draw(img, "RGBA")

    group_colors = {
        "Cosmic":     "#9ac8ff", "Primal":     "#a8e060",
        "Eldritch":   "#d8b4ff", "Mechanical": "#88ffcc",
        "Humanoid":   "#ffaa66",
    }
    badge_col = _rgb(group_colors.get(group, "#ffffff"))

    try:
        small_font = ImageFont.load_default(size=28)
        name_font  = ImageFont.load_default(size=48)
    except Exception:
        small_font = name_font = None

    # Group badge — top-left with accent backing
    badge_w, badge_h = 175, 42
    d.rectangle([12, 12, 12 + badge_w, 12 + badge_h], fill=(0, 0, 0, 175))
    d.rectangle([12, 12, 12 + badge_w, 12 + badge_h], outline=(*badge_col, 80), width=1)
    kw = {"font": small_font} if small_font else {}
    d.text((22, 18), group.upper(), fill=(*badge_col, 220), **kw)

    # Name bar — full-width gradient at bottom
    bar_h = 140
    bar_top = H - bar_h
    # gradient bands
    for i in range(bar_h):
        t = i / bar_h
        a = int(210 * (1 - t * 0.3))
        d.line([0, bar_top + i, W, bar_top + i], fill=(0, 0, 0, a))
    # Accent top-line of bar
    d.line([0, bar_top, W, bar_top], fill=(*accent, 110), width=2)
    d.line([0, bar_top + 3, W, bar_top + 3], fill=(*accent, 45), width=1)

    # Decorative side flourishes
    fw = 60
    d.line([0, bar_top + 18, fw, bar_top + 18], fill=(*accent, 70), width=1)
    d.line([W - fw, bar_top + 18, W, bar_top + 18], fill=(*accent, 70), width=1)
    d.ellipse([fw - 4, bar_top + 15, fw + 4, bar_top + 21], fill=(*accent, 100))
    d.ellipse([W - fw - 4, bar_top + 15, W - fw + 4, bar_top + 21], fill=(*accent, 100))

    kw2 = {"font": name_font} if name_font else {}
    if name_font:
        bbox = d.textbbox((0, 0), name.upper(), font=name_font)
        tw = bbox[2] - bbox[0]
        text_x = (W - tw) // 2
        text_y = H - 95
        # Shadow
        d.text((text_x + 2, text_y + 2), name.upper(), fill=(0, 0, 0, 160), **kw2)
        # Main text
        d.text((text_x, text_y), name.upper(), fill=(*accent, 230), **kw2)
    else:
        d.text((W // 2 - len(name) * 8, H - 90), name.upper(), fill=(*accent, 230))


def _vignette(img):
    d = ImageDraw.Draw(img, "RGBA")
    for i in range(80):
        a = int(i * 3.2)
        d.rectangle([i, i, W - i, H - i], outline=(0, 0, 0, a), width=1)


# ── Race table ─────────────────────────────────────────────────────────────────
# (race_id, display_name, group, body_fn, accent_hex, base_hex, extra_kwargs)

RACES = {
    # COSMIC
    "voidwraith":   ("Voidwraith",   "Cosmic",     draw_ethereal,   "#9ac8ff", "#070c1a", {"aura_r": 200, "aura_alpha": 65, "aura_blur": 60}),
    "nullshade":    ("Nullshade",    "Cosmic",     draw_ethereal,   "#778899", "#06080e", {"aura_r": 180, "aura_alpha": 50, "aura_blur": 55}),
    "ironlocust":   ("Ironlocust",   "Cosmic",     draw_insectoid,  "#d4b820", "#120e04", {"legs": 6, "aura_r": 160, "aura_alpha": 55}),
    "embervein":    ("Embervein",    "Cosmic",     draw_hulking,    "#ff6600", "#1e0600", {"aura_r": 210, "aura_alpha": 70}),
    "riftwalker":   ("Riftwalker",   "Cosmic",     draw_predator,   "#9ac8ff", "#04101a", {"has_tail": True, "aura_r": 170, "aura_alpha": 58}),
    # PRIMAL
    "solarlord":    ("Solarlord",    "Primal",     draw_avian,      "#ffe060", "#1a1200", {"aura_r": 220, "aura_alpha": 75}),
    "thornmimic":   ("Thornmimic",   "Primal",     draw_plant,      "#66cc44", "#040a02", {"aura_r": 175, "aura_alpha": 55}),
    "cinderkin":    ("Cinderkin",    "Primal",     draw_compact,    "#ff9900", "#160600", {"aura_r": 155, "aura_alpha": 65}),
    "deeptyrant":   ("Deeptyrant",   "Primal",     draw_cephalopod, "#00d4cc", "#000e0c", {"aura_r": 200, "aura_alpha": 60}),
    "grimcrow":     ("Grimcrow",     "Primal",     draw_avian,      "#9966cc", "#060008", {"aura_r": 175, "aura_alpha": 52}),
    # ELDRITCH
    "bloodweaver":  ("Bloodweaver",  "Eldritch",   draw_horror,     "#ff2244", "#0e0004", {"has_cape": True, "aura_r": 185, "aura_alpha": 62}),
    "dreamhusk":    ("Dreamhusk",    "Eldritch",   draw_ethereal,   "#d8b4ff", "#0c0818", {"aura_r": 195, "aura_alpha": 58}),
    "bonedrifter":  ("Bonedrifter",  "Eldritch",   draw_horror,     "#ddddd0", "#0a0a08", {"has_bones": True, "aura_r": 170, "aura_alpha": 50}),
    "mindspider":   ("Mindspider",   "Eldritch",   draw_arachnid,   "#aaffdd", "#00080a", {"aura_r": 180, "aura_alpha": 55}),
    "chaosling":    ("Chaosling",    "Eldritch",   draw_ethereal,   "#ff88cc", "#0e000c", {"aura_r": 200, "aura_alpha": 68}),
    # MECHANICAL
    "ironveil":     ("Ironveil",     "Mechanical", draw_mechanical, "#c8e8ff", "#060a10", {"aura_r": 165, "aura_alpha": 55}),
    "forgespawn":   ("Forgespawn",   "Mechanical", draw_mechanical, "#ff8800", "#100600", {"gear": True, "aura_r": 175, "aura_alpha": 65}),
    "cinderplate":  ("Cinderplate",  "Mechanical", draw_mechanical, "#ff4400", "#120400", {"aura_r": 168, "aura_alpha": 60}),
    "hexgear":      ("Hexgear",      "Mechanical", draw_mechanical, "#88ffcc", "#000a06", {"gear": True, "aura_r": 162, "aura_alpha": 55}),
    "wirewraith":   ("Wirewraith",   "Mechanical", draw_mechanical, "#ffff44", "#0e0e00", {"wires": True, "aura_r": 170, "aura_alpha": 60}),
    # HUMANOID
    "ashenborn":    ("Ashenborn",    "Humanoid",   draw_humanoid,   "#ff6644", "#100400", {"feature": "scars"}),
    "hollowsong":   ("Hollowsong",   "Humanoid",   draw_humanoid,   "#cc88ff", "#080010", {"feature": "aura"}),
    "veilborn":     ("Veilborn",     "Humanoid",   draw_humanoid,   "#6677aa", "#04060c", {"feature": "cloak"}),
    "thornweft":    ("Thornweft",    "Humanoid",   draw_humanoid,   "#66aa44", "#030802", {"feature": "thorns_sm"}),
    "ashcrown":     ("Ashcrown",     "Humanoid",   draw_humanoid,   "#eeeebb", "#0c0c0a", {"feature": "crown"}),
    "ironfast":     ("Ironfast",     "Humanoid",   draw_humanoid,   "#a0a0a0", "#080808", {"feature": "glow_body"}),
    "coreborn":     ("Coreborn",     "Humanoid",   draw_humanoid,   "#ff4422", "#100200", {"feature": "fire_crown"}),
    "warpbred":     ("Warpbred",     "Humanoid",   draw_humanoid,   "#cc4400", "#0e0200", {"feature": "fracture"}),
    "splitblood":   ("Splitblood",   "Humanoid",   draw_humanoid,   "#884422", "#0c0400", {"feature": "split"}),
    "duskweft":     ("Duskweft",     "Humanoid",   draw_humanoid,   "#aaaaff", "#04040e", {"feature": "shadow_void", "aura_r": 220, "aura_alpha": 70, "aura_blur": 65}),
    "glitchkin":    ("Glitchkin",    "Humanoid",   draw_humanoid,   "#00ffaa", "#000c06", {"feature": "antenna"}),
    "fractureline": ("Fractureline", "Humanoid",   draw_humanoid,   "#ffaa00", "#0c0800", {"feature": "fracture"}),
    "emberpact":    ("Emberpact",    "Humanoid",   draw_humanoid,   "#ff4444", "#100000", {"feature": "fire_crown"}),
    "fallenlight":  ("Fallenlight",  "Humanoid",   draw_humanoid,   "#ffff99", "#0c0c04", {"feature": "halo"}),
    "scaleworn":    ("Scaleworn",    "Humanoid",   draw_humanoid,   "#336633", "#020802", {"feature": "scales"}),
}


# ── Main generator ─────────────────────────────────────────────────────────────

def make_portrait(race_id, name, group, draw_fn, accent_hex, base_hex, extra):
    rng = np.random.default_rng(abs(hash(race_id)) % (2**31))
    accent = _rgb(accent_hex)
    base   = _rgb(base_hex)
    cx, cy = W // 2, H // 2 - 50  # character center slightly above mid

    # 1. Atmospheric background
    bg_fn = BG_MAKERS.get(group, _bg_humanoid)
    img = bg_fn(accent, abs(hash(race_id)) % (2**31))

    # 2. Ground shadow beneath character
    shadow = _glow_blob(cx, cy + 175, 110, (0, 0, 0), alpha=120, blur=35)
    img.alpha_composite(shadow)

    # 3. Ambient particles
    particle_layer = _scatter_particles(rng, accent, count=55, alpha_max=110)
    img.alpha_composite(particle_layer)

    # 4. Character with aura + glow + silhouette
    _composite_character(img, draw_fn, cx, cy, base, accent, extra)

    # 5. Vignette
    _vignette(img)

    # 6. Frame
    _frame(img, accent)

    # 7. Labels
    _labels(img, name, group, accent)

    os.makedirs(OUT, exist_ok=True)
    out_path = os.path.join(OUT, f"{race_id}.png")
    img.convert("RGB").save(out_path, optimize=True)
    print(f"  ✓  {race_id:16s}  {group}")


if __name__ == "__main__":
    print(f"Generating {len(RACES)} portraits at {W}x{H} -> {OUT}\n")
    for race_id, data in RACES.items():
        make_portrait(race_id, *data)
    print(f"\nDone.")
