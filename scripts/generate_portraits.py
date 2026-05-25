#!/usr/bin/env python3
"""
Generate 800×1120 PNG portrait cards for all 35 StoryForge races.

Run from the project root:
    uv run python scripts/generate_portraits.py

Output: godot/assets/characters/<race_id>.png
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
import os
import math

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
                  outline=(*accent[:3], 18), width=1)
    # Corruption tendrils
    for _ in range(20):
        angle = float(rng.uniform(0, 2 * math.pi))
        for seg in range(int(rng.integers(4, 10))):
            x0 = int(W // 2 + math.cos(angle) * seg * 40 + rng.integers(-20, 20))
            y0 = int(H // 2 + math.sin(angle) * seg * 40 + rng.integers(-20, 20))
            x1 = int(W // 2 + math.cos(angle) * (seg + 1) * 40 + rng.integers(-25, 25))
            y1 = int(H // 2 + math.sin(angle) * (seg + 1) * 40 + rng.integers(-25, 25))
            d.line([x0, y0, x1, y1], fill=(*accent[:3], 20), width=1)

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
    grid_col = (*accent[:3], 18)
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
        d.line([x0, y0, x1, y1], fill=(*accent[:3], 28), width=2)
        d.ellipse([x1 - 4, y1 - 4, x1 + 4, y1 + 4], fill=(*accent[:3], 45))

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
        d.line([i, 0, i + H, H], fill=(*accent[:3], 8), width=1)

    return img


BG_MAKERS = {
    "Cosmic":     _bg_cosmic,
    "Primal":     _bg_primal,
    "Eldritch":   _bg_eldritch,
    "Mechanical": _bg_mechanical,
    "Humanoid":   _bg_humanoid,
}


# ── Low-level volumetric helpers ──────────────────────────────────────────────

def _radial_gradient(size, color1, color2, center=None, radius=None):
    """Create a radial gradient image."""
    w, h2 = size
    if center is None: center = (w // 2, h2 // 2)
    if radius is None: radius = max(w, h2) // 2
    
    yy, xx = np.mgrid[0:h2, 0:w]
    dist = np.sqrt((xx - center[0])**2 + (yy - center[1])**2)
    t = np.clip(dist / radius, 0, 1)
    
    # Linear interpolation between colors
    arr = np.zeros((h2, w, 4), dtype=np.uint8)
    for i in range(3):
        arr[:, :, i] = (color1[i] * (1 - t) + color2[i] * t).astype(np.uint8)
    arr[:, :, 3] = 255
    return Image.fromarray(arr, "RGBA")


def _draw_volumetric_sphere(img, cx, cy, r, base_col, highlight_col, shadow_col, light_offset=(-0.3, -0.3)):
    """Draw a sphere with 3D shading (highlight and shadow)."""
    # 1. Base shape
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    
    # 2. Shading layer
    # Center light slightly offset
    lx = cx + r * light_offset[0]
    ly = cy + r * light_offset[1]
    
    # Create a gradient from highlight to shadow
    grad = _radial_gradient((int(r*4), int(r*4)), highlight_col, shadow_col, 
                            center=(int(r*2 + r*light_offset[0]), int(r*2 + r*light_offset[1])),
                            radius=r*1.8)
    
    # Paste gradient onto a temporary layer and mask it
    temp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    temp.paste(grad, (int(cx - r*2), int(cy - r*2)))
    
    # Composite
    img.paste(temp, (0,0), mask)


def _draw_volumetric_capsule(img, x0, y0, x1, y1, width, base_col, highlight_col, shadow_col, light_offset=(-0.3, -0.3)):
    """Draw a capsule (rounded cylinder) with 3D shading."""
    # Simplified: draw two spheres and a rectangle
    # Calculate direction for highlight/shadow
    dx, dy = x1 - x0, y1 - y0
    dist = math.sqrt(dx*dx + dy*dy)
    if dist == 0: return
    
    r = width // 2
    # Draw body
    # Create mask for the capsule
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    md.line([x0, y0, x1, y1], fill=255, width=width)
    md.ellipse([x0 - r, y0 - r, x0 + r, y0 + r], fill=255)
    md.ellipse([x1 - r, y1 - r, x1 + r, y1 + r], fill=255)
    
    # Directional shading (linear-ish)
    # We'll use a linear gradient perpendicular to the capsule direction
    perp_x, perp_y = -dy/dist, dx/dist
    
    # Simple volumetric look: darker at the edges, lighter near the "light side"
    # For now, just draw spheres at ends and a shaded rectangle in middle
    _draw_volumetric_sphere(img, x0, y0, r, base_col, highlight_col, shadow_col, light_offset)
    _draw_volumetric_sphere(img, x1, y1, r, base_col, highlight_col, shadow_col, light_offset)
    
    # Mid-section
    # (Actually PIL's line with width is solid, so we just use the spheres for volume at joints)

# ── Character silhouette + glow compositing ────────────────────────────────────

def _composite_character(bg, silhouette_fn, cx, cy, base, accent, extra):
    """
    Draw character with:
      1. Large blurred aura behind character
      2. 3D Volumetric Shading pass
      3. Rim lighting
    """
    group = extra.get("group", "Humanoid")
    
    # 1. Aura
    aura_r = extra.get("aura_r", 180)
    aura = _glow_blob(cx, cy, aura_r, accent, alpha=extra.get("aura_alpha", 60),
                      blur=extra.get("aura_blur", 55))
    bg.alpha_composite(aura)

    # 2. 3D Shading Pass
    # Instead of a flat silhouette_fn, we'll need the silhouette_fn to use our volumetric helpers.
    # We'll inject our special volumetric draw context.
    
    char_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    
    highlight = _lighten(base, 40)
    shadow = _darken(base, 50)
    
    # Wrap drawing in a function that uses our 3D helpers
    def v_ell(d, cx2, cy2, rx, ry, col, a=255, expand=0):
        # rx/ry are roughly same for spheres in most of our silhouettes
        r2 = (rx + ry) // 2
        _draw_volumetric_sphere(char_layer, cx2, cy2, r2 + expand, col, _lighten(col, 60), _darken(col, 60))

    def v_rect(d, x0, y0, x1, y1, col, a=255, expand=0):
        # Approximate rectangle with volumetric capsule
        w = abs(x1 - x0) + expand
        _draw_volumetric_capsule(char_layer, x0, y0, x1, y1, w, col, _lighten(col, 60), _darken(col, 60))

    def v_poly(d, pts, col, a=255):
        # Simple shaded polygon
        if d: d.polygon(pts, fill=(*col, a))
        if len(pts) > 2:
            highlight_col = _lighten(col, 60)
            d.line([pts[0], pts[1]], fill=(*highlight_col, 100), width=3)

    def v_line(d, pts, col, width=1):
        if d: d.line(pts, fill=col, width=width)

    # Draw the character with volumetric helpers
    cd = ImageDraw.Draw(char_layer)
    silhouette_fn(cd, char_layer, cx, cy, base, accent, expand=0, 
                  custom_ell=v_ell, custom_rect=v_rect, custom_poly=v_poly, 
                  custom_line=v_line, **extra)
    
    bg.alpha_composite(char_layer)

    # 3. Rim Lighting
    mask_img = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask_img)
    dummy = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    silhouette_fn(md, dummy, cx, cy, (255, 255, 255), (255, 255, 255), expand=0, **extra)
    
    rim_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rd = ImageDraw.Draw(rim_layer)
    rim_col = _lighten(accent, 120)
    silhouette_fn(rd, rim_layer, cx - 12, cy - 8, rim_col, rim_col, expand=4, **extra)
    rim_layer = rim_layer.filter(ImageFilter.GaussianBlur(6))
    
    rim_clipped = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rim_clipped.paste(rim_layer, (0, 0), mask_img)
    bg.alpha_composite(rim_clipped)
    
    # 4. Final details (Eyes, feature-specific glows)
    detail_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(detail_layer)
    silhouette_fn(dd, detail_layer, cx, cy, (0,0,0,0), accent, expand=0, **extra)
    bg.alpha_composite(detail_layer)


# ── Body-type silhouette functions ────────────────────────────────────────────
# Each function draws onto draw `d`, img `img`, centered at (cx, cy).
# `expand` offsets all sizes outward by this many px (used for glow silhouette).

def _ell(d, cx, cy, rx, ry, col, a=255, expand=0, **kwargs):
    custom = kwargs.get("custom_ell")
    if custom:
        custom(d, cx, cy, rx, ry, col, a, expand)
    else:
        rx += expand; ry += expand
        if d:
            # Handle L-mode (grayscale) masks vs RGBA
            if isinstance(col, int):
                fill_col = col
            elif len(col) == 4:
                fill_col = col
            else:
                fill_col = (*col, a)
            
            if hasattr(d, "im") and d.im.mode == "L" and isinstance(fill_col, tuple):
                fill_col = fill_col[0]
            d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=fill_col)

def _rect(d, x0, y0, x1, y1, col, a=255, expand=0, **kwargs):
    custom = kwargs.get("custom_rect")
    if custom:
        custom(d, x0, y0, x1, y1, col, a, expand)
    else:
        if d:
            if isinstance(col, int):
                fill_col = col
            elif len(col) == 4:
                fill_col = col
            else:
                fill_col = (*col, a)
            
            if hasattr(d, "im") and d.im.mode == "L" and isinstance(fill_col, tuple):
                fill_col = fill_col[0]
            d.rectangle([x0 - expand, y0 - expand, x1 + expand, y1 + expand], fill=fill_col)

def _poly(d, pts, col, a=255, **kwargs):
    custom = kwargs.get("custom_poly")
    if custom:
        custom(d, pts, col, a)
    else:
        if d:
            if isinstance(col, int):
                fill_col = col
            elif len(col) == 4:
                fill_col = col
            else:
                fill_col = (*col, a)
            
            if hasattr(d, "im") and d.im.mode == "L" and isinstance(fill_col, tuple):
                fill_col = fill_col[0]
            d.polygon(pts, fill=fill_col)

def _line(d, pts, col, width=1, **kwargs):
    custom = kwargs.get("custom_line")
    if custom:
        custom(d, pts, col, width)
    else:
        if d:
            if isinstance(col, int):
                fill_col = col
            elif len(col) == 4:
                fill_col = col
            else:
                # Check if it looks like (R, G, B, A) or (R, G, B)
                # For line, if it's 3 elements, we might want to add alpha
                fill_col = col
            
            if hasattr(d, "im") and d.im.mode == "L" and isinstance(fill_col, tuple):
                fill_col = fill_col[0]
            d.line(pts, fill=fill_col, width=width)


def draw_ethereal(d, img, cx, cy, base, accent, expand=0, **kwargs):
    e = expand
    # Wide misty body tapering to wisps
    _ell(d, cx, cy - 40, 72 + e, 110 + e, base, 180, **kwargs)
    _ell(d, cx, cy - 80, 48 + e, 60 + e, base, 200, **kwargs)
    # Face void
    _ell(d, cx, cy - 100, 36 + e, 42 + e, _lighten(base, 30), 215, **kwargs)
    # Eyes
    _ell(d, cx - 16, cy - 110, 9 + e, 9 + e, accent, 240, **kwargs)
    _ell(d, cx + 16, cy - 110, 9 + e, 9 + e, accent, 240, **kwargs)
    # Wisp tails
    for ox, base_y in [(-50, cy + 60), (-20, cy + 80), (20, cy + 85), (50, cy + 65)]:
        for j in range(6):
            a_val = max(0, 170 - j * 28)
            _ell(d, cx + ox, base_y + j * 30, max(1, 12 + e - j * 2), max(1, 14 + e - j * 2),
                 base, a_val, **kwargs)
    # Shoulder wisps
    for ox in [-80, 80]:
        for j in range(4):
            _ell(d, cx + ox + (4 if ox > 0 else -4) * j, cy - 20 - j * 12,
                 max(1, 18 + e - j * 4), max(1, 16 + e - j * 4), base, 130 - j * 25, **kwargs)


def draw_insectoid(d, img, cx, cy, base, accent, legs=6, expand=0, **kwargs):
    e = expand
    # Abdomen (bottom)
    _ell(d, cx, cy + 70, 32 + e, 55 + e, base, 205, **kwargs)
    # Thorax
    _ell(d, cx, cy - 10, 30 + e, 38 + e, base, 220, **kwargs)
    # Head
    _ell(d, cx, cy - 72, 24 + e, 30 + e, base, 235, **kwargs)
    # Mandibles
    _line(d, [cx - 20, cy - 52, cx - 38, cy - 80], (*accent[:3], 210), width=3 + e // 2, **kwargs)
    _line(d, [cx + 20, cy - 52, cx + 38, cy - 80], (*accent[:3], 210), width=3 + e // 2, **kwargs)
    # Antenna
    _line(d, [cx - 8, cy - 100, cx - 28, cy - 150], (*accent[:3], 200), width=2, **kwargs)
    _line(d, [cx + 8, cy - 100, cx + 28, cy - 150], (*accent[:3], 200), width=2, **kwargs)
    _ell(d, cx - 28, cy - 152, 6 + e, 6 + e, accent, 220, **kwargs)
    _ell(d, cx + 28, cy - 152, 6 + e, 6 + e, accent, 220, **kwargs)
    # Compound eyes
    for ex, ey in [(-13, cy - 74), (13, cy - 74)]:
        _ell(d, cx + ex, ey, 7 + e, 7 + e, accent, 245, **kwargs)
    # Legs — 3 pairs
    for i in range(legs // 2):
        yl = cy - 5 + i * 22
        for side in [-1, 1]:
            sx = cx + side * 30
            mx = cx + side * 80
            ex2 = cx + side * (100 + i * 5)
            ey2 = yl + 35
            _line(d, [sx, yl, mx, yl + 12], (*base[:3], 195), width=3, **kwargs)
            _line(d, [mx, yl + 12, ex2, ey2], (*base[:3], 165), width=2, **kwargs)


def draw_hulking(d, img, cx, cy, base, accent, expand=0, **kwargs):
    e = expand
    # Legs
    _ell(d, cx - 32, cy + 110, 22 + e, 45 + e, base, 195, **kwargs)
    _ell(d, cx + 32, cy + 110, 22 + e, 45 + e, base, 195, **kwargs)
    # Hips
    _ell(d, cx, cy + 60, 70 + e, 40 + e, base, 210, **kwargs)
    # Torso
    _ell(d, cx, cy - 15, 78 + e, 70 + e, base, 218, **kwargs)
    # Massive shoulders
    _ell(d, cx - 95, cy - 40, 40 + e, 38 + e, base, 205, **kwargs)
    _ell(d, cx + 95, cy - 40, 40 + e, 38 + e, base, 205, **kwargs)
    # Upper arms
    _ell(d, cx - 100, cy + 15, 28 + e, 45 + e, base, 198, **kwargs)
    _ell(d, cx + 100, cy + 15, 28 + e, 45 + e, base, 198, **kwargs)
    # Forearms / fists
    _ell(d, cx - 105, cy + 78, 22 + e, 35 + e, base, 188, **kwargs)
    _ell(d, cx + 105, cy + 78, 22 + e, 35 + e, base, 188, **kwargs)
    # Neck
    _ell(d, cx, cy - 82, 24 + e, 22 + e, base, 225, **kwargs)
    # Head
    _ell(d, cx, cy - 125, 36 + e, 38 + e, base, 232, **kwargs)
    # Eyes
    for ex in [-14, 14]:
        _ell(d, cx + ex, cy - 132, 8 + e, 8 + e, accent, 245, **kwargs)
    # Chest runes / energy nodes
    for ox, oy in [(-22, cy - 30), (0, cy - 10), (22, cy - 30), (-14, cy + 20), (14, cy + 20)]:
        _ell(d, cx + ox, oy, 8 + e, 8 + e, accent, 160, **kwargs)


def draw_predator(d, img, cx, cy, base, accent, has_tail=True, expand=0, **kwargs):
    e = expand
    # Legs
    _rect(d, cx - 26, cy + 58, cx - 8, cy + 145, base, 195, e, **kwargs)
    _rect(d, cx + 8, cy + 58, cx + 26, cy + 145, base, 195, e, **kwargs)
    # Lower body
    _ell(d, cx, cy + 35, 42 + e, 30 + e, base, 215, **kwargs)
    # Arms
    _ell(d, cx - 55, cy - 28, 22 + e, 55 + e, base, 192, **kwargs)
    _ell(d, cx + 55, cy - 28, 22 + e, 55 + e, base, 192, **kwargs)
    # Torso
    _ell(d, cx, cy - 20, 50 + e, 65 + e, base, 225, **kwargs)
    # Neck
    _ell(d, cx, cy - 82, 20 + e, 22 + e, base, 228, **kwargs)
    # Head — slightly angular
    _ell(d, cx, cy - 118, 32 + e, 36 + e, base, 235, **kwargs)
    # Muzzle hint
    _ell(d, cx, cy - 112, 18 + e, 12 + e, _darken(base, 15), 220, **kwargs)
    # Eyes
    for ex in [-14, 14]:
        _ell(d, cx + ex, cy - 126, 7 + e, 7 + e, accent, 248, **kwargs)
    if has_tail:
        pts = []
        for i in range(8):
            tx = cx + 30 + i * 15
            ty = cy + 50 + i * 18
            pts.append((tx, ty))
        for i in range(len(pts) - 1):
            w = max(1, 14 + e - i * 2)
            _line(d, [pts[i], pts[i + 1]], (*base[:3], 200 - i * 18), width=w, **kwargs)


def draw_avian(d, img, cx, cy, base, accent, expand=0, **kwargs):
    e = expand
    # Wing spans — large impressive
    _poly(d, [cx, cy - 30,  cx - 160, cy - 60, cx - 140, cy + 45, cx - 25, cy + 20],
          base, 170, **kwargs)
    _poly(d, [cx, cy - 30,  cx + 160, cy - 60, cx + 140, cy + 45, cx + 25, cy + 20],
          base, 170, **kwargs)
    # Wing feather detail lines
    for ox, sign in [(-1, -1), (1, 1)]:
        for j in range(5):
            fx0 = cx + sign * (30 + j * 25)
            fy0 = cy - 22 + j * 8
            fx1 = cx + sign * (80 + j * 20)
            fy1 = cy + 32 + j * 4
            _line(d, [fx0, fy0, fx1, fy1], (*accent[:3], 80), width=2, **kwargs)
    # Body
    _ell(d, cx, cy + 10, 32 + e, 52 + e, base, 228, **kwargs)
    # Neck
    _ell(d, cx, cy - 52, 20 + e, 28 + e, base, 232, **kwargs)
    # Head
    _ell(d, cx, cy - 100, 30 + e, 34 + e, base, 240, **kwargs)
    # Crest feathers
    for ox, h in [(-16, 40), (-7, 55), (0, 62), (7, 55), (16, 40)]:
        _poly(d, [cx + ox - 5, cy - 130, cx + ox + 5, cy - 130, cx + ox, cy - 130 - h],
              accent, 200, **kwargs)
    # Eyes
    for ex in [-12, 12]:
        _ell(d, cx + ex, cy - 106, 7 + e, 7 + e, accent, 252, **kwargs)
    # Legs / talons
    for lx, side in [(-14, -1), (14, 1)]:
        _line(d, [cx + lx, cy + 60, cx + lx + side * 6, cy + 130], (*base[:3], 185), width=5, **kwargs)
        for j in range(3):
            tx0 = cx + lx + side * 6
            ty0 = cy + 130
            _line(d, [tx0, ty0, tx0 + side * (10 + j * 5), ty0 + 15],
                   (*base[:3], 160), width=2, **kwargs)


def draw_horror(d, img, cx, cy, base, accent, has_cape=False, has_bones=False, expand=0, **kwargs):
    e = expand
    if has_cape:
        _poly(d, [cx, cy - 65,
                  cx - 110, cy + 30, cx - 90, cy + 165,
                  cx, cy + 130,
                  cx + 90, cy + 165, cx + 110, cy + 30], base, 110, **kwargs)
    # Thin elongated torso
    _ell(d, cx - 32, cy - 28, 22 + e, 52 + e, base, 190, **kwargs)
    _ell(d, cx + 32, cy - 28, 22 + e, 52 + e, base, 190, **kwargs)
    _ell(d, cx, cy - 20, 36 + e, 68 + e, base, 220, **kwargs)
    # Spindly neck
    _ell(d, cx, cy - 88, 14 + e, 24 + e, base, 228, **kwargs)
    # Elongated skull
    _ell(d, cx, cy - 135, 28 + e, 46 + e, base, 235, **kwargs)
    if has_bones:
        # Bone spurs on torso
        for ox, oy in [(-28, cy - 50), (-28, cy - 10), (28, cy - 50), (28, cy - 10),
                       (0, cy - 75)]:
            _poly(d, [cx + ox - 5, cy + oy, cx + ox + 5, cy + oy, cx + ox, cy + oy - 24],
                  accent, 210, **kwargs)
    # Glowing eyes
    for ex, ey in [(-12, cy - 145), (12, cy - 145)]:
        _ell(d, cx + ex, ey, 8 + e, 8 + e, accent, 255, **kwargs)
    # Clawed hands
    for sx, ey2 in [(-55, cy + 40), (55, cy + 40)]:
        for j in range(4):
            angle = math.pi * (0.2 + j * 0.2) * (-1 if sx < 0 else 1)
            fx = cx + sx + int(math.cos(angle) * 22)
            fy = ey2 + int(math.sin(angle) * 18)
            _line(d, [cx + sx, ey2, fx, fy], (*base[:3], 175), width=3, **kwargs)
    # Leg wisps
    for ox in [-16, 16]:
        _rect(d, cx + ox - 8, cy + 45, cx + ox + 8, cy + 140, base, 185, e, **kwargs)


def draw_arachnid(d, img, cx, cy, base, accent, expand=0, **kwargs):
    e = expand
    # Large abdomen
    _ell(d, cx, cy + 65, 45 + e, 62 + e, base, 215, **kwargs)
    # Cephalothorax
    _ell(d, cx, cy - 10, 42 + e, 45 + e, base, 230, **kwargs)
    # Head with fang cluster
    _ell(d, cx, cy - 68, 26 + e, 28 + e, base, 242, **kwargs)
    # Chelicerae / fangs
    for fx, fy in [(-12, cy - 80), (12, cy - 80)]:
        _line(d, [cx + fx, cy - 58, cx + fx + (fx // abs(fx)) * 12, cy - 95],
               (*accent[:3], 200), width=3, **kwargs)
    # 8 eyes
    eye_pts = [(-16, cy - 74), (-8, cy - 80), (8, cy - 80), (16, cy - 74),
               (-12, cy - 68), (-4, cy - 72), (4, cy - 72), (12, cy - 68)]
    for ex, ey in eye_pts:
        _ell(d, cx + ex, ey, 4 + e, 4 + e, accent, 240, **kwargs)
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
        _line(d, [cx + x0, y0, cx + x1, y1], (*base[:3], 205), width=3, **kwargs)
        _line(d, [cx + x1, y1, cx + x2, y2], (*base[:3], 168), width=2, **kwargs)
        _ell(d, cx + x2, y2, 4, 4, accent, 100, **kwargs)


def draw_mechanical(d, img, cx, cy, base, accent, gear=False, wires=False, expand=0, **kwargs):
    e = expand
    # Legs
    _rect(d, cx - 38, cy + 62, cx - 12, cy + 150, base, 200, e, **kwargs)
    _rect(d, cx + 12, cy + 62, cx + 38, cy + 150, base, 200, e, **kwargs)
    # Feet
    _rect(d, cx - 45, cy + 140, cx - 8, cy + 158, base, 185, e, **kwargs)
    _rect(d, cx + 8, cy + 140, cx + 45, cy + 158, base, 185, e, **kwargs)
    # Lower torso
    _rect(d, cx - 40, cy + 20, cx + 40, cy + 65, base, 215, e, **kwargs)
    # Chest plate
    _rect(d, cx - 52, cy - 65, cx + 52, cy + 25, base, 228, e, **kwargs)
    # Shoulder pauldrons
    _rect(d, cx - 90, cy - 75, cx - 48, cy - 10, base, 210, e, **kwargs)
    _rect(d, cx + 48, cy - 75, cx + 90, cy - 10, base, 210, e, **kwargs)
    # Arms
    _rect(d, cx - 85, cy - 8, cx - 50, cy + 58, base, 200, e, **kwargs)
    _rect(d, cx + 50, cy - 8, cx + 85, cy + 58, base, 200, e, **kwargs)
    # Panel lines on chest
    if not expand:
        _line(d, [cx - 50, cy - 22, cx + 50, cy - 22], (*accent[:3], 90), width=2, **kwargs)
        _line(d, [cx - 50, cy + 5, cx + 50, cy + 5], (*accent[:3], 60), width=2, **kwargs)
    # Neck
    _rect(d, cx - 16, cy - 88, cx + 16, cy - 65, base, 225, e, **kwargs)
    # Head
    _rect(d, cx - 30, cy - 140, cx + 30, cy - 88, base, 235, e, **kwargs)
    # Visor
    _rect(d, cx - 26, cy - 128, cx + 26, cy - 102, accent, 190, e, **kwargs)
    if gear:
        for ang in range(0, 360, 45):
            rad = math.radians(ang)
            gx = int(cx + math.cos(rad) * 28)
            gy = int(cy + 45 + math.sin(rad) * 28)
            _ell(d, gx, gy, 6 + e, 6 + e, accent, 130, **kwargs)
    if wires:
        for x0, y0, x1, y1 in [(-52, cy - 30, -100, cy - 60),
                                (52, cy - 30, 100, cy - 60),
                                (-38, cy + 40, -70, cy + 85)]:
            _line(d, [cx + x0, y0, cx + x1, y1], (*accent[:3], 160), width=3, **kwargs)


def draw_plant(d, img, cx, cy, base, accent, expand=0, **kwargs):
    e = expand
    # Root-like legs
    for ox, w in [(-28, 12), (0, 10), (28, 12)]:
        ys = cy + 70
        for seg in range(5):
            curve = int(math.sin(seg * 0.8 + ox * 0.05) * 14)
            _line(d, [cx + ox + curve, ys + seg * 18,
                    cx + ox + curve + 4, ys + (seg + 1) * 18],
                   (*base[:3], 190 - seg * 15), width=max(1, w - seg * 2), **kwargs)
    # Torso
    _ell(d, cx, cy, 42 + e, 72 + e, base, 215, **kwargs)
    # Leaf-arms
    for side in [-1, 1]:
        _poly(d, [cx + side * 44, cy - 40,
                  cx + side * 110, cy - 75,
                  cx + side * 100, cy - 8,
                  cx + side * 40, cy + 15], base, 178, **kwargs)
        # Leaf veins
        for j in range(3):
            vx0 = cx + side * (50 + j * 15)
            _line(d, [vx0, cy - 35 + j * 15, vx0 + side * 30, cy - 55 + j * 10],
                   (*accent[:3], 60), width=1, **kwargs)
    # Neck / stem
    _ell(d, cx, cy - 95, 18 + e, 28 + e, base, 228, **kwargs)
    # Head — blossom/bulb
    _ell(d, cx, cy - 145, 38 + e, 44 + e, base, 235, **kwargs)
    # Petal crown
    for ang in range(0, 360, 72):
        rad = math.radians(ang)
        px = int(cx + math.cos(rad) * 52)
        py = int(cy - 148 + math.sin(rad) * 42)
        _ell(d, px, py, 14 + e, 20 + e, accent, 175, **kwargs)
    # Eyes
    for ex in [-12, 12]:
        _ell(d, cx + ex, cy - 150, 7 + e, 7 + e, accent, 245, **kwargs)


def draw_compact(d, img, cx, cy, base, accent, expand=0, **kwargs):
    e = expand
    # Short legs
    _ell(d, cx - 22, cy + 85, 18 + e, 32 + e, base, 192, **kwargs)
    _ell(d, cx + 22, cy + 85, 18 + e, 32 + e, base, 192, **kwargs)
    # Stocky torso
    _ell(d, cx, cy + 10, 58 + e, 60 + e, base, 222, **kwargs)
    # Short arms
    _ell(d, cx - 68, cy - 12, 22 + e, 42 + e, base, 200, **kwargs)
    _ell(d, cx + 68, cy - 12, 22 + e, 42 + e, base, 200, **kwargs)
    # Neck
    _ell(d, cx, cy - 72, 24 + e, 20 + e, base, 228, **kwargs)
    # Oversized head
    _ell(d, cx, cy - 128, 50 + e, 54 + e, base, 238, **kwargs)
    # Horns / spikes
    for ox, h in [(-18, 52), (-8, 70), (8, 70), (18, 52)]:
        _poly(d, [cx + ox - 6, cy - 178, cx + ox + 6, cy - 178, cx + ox, cy - 178 - h],
              accent, 215, **kwargs)
    # Big eyes
    for ex in [-20, 20]:
        _ell(d, cx + ex, cy - 138, 12 + e, 14 + e, accent, 252, **kwargs)
        _ell(d, cx + ex, cy - 138, 6 + e, 7 + e, _darken(accent, 60), 255, **kwargs)
    # Chest core
    _ell(d, cx, cy - 20, 22 + e, 22 + e, accent, 190, **kwargs)


def draw_cephalopod(d, img, cx, cy, base, accent, expand=0, **kwargs):
    e = expand
    # Large mantle/head
    _ell(d, cx, cy - 55, 88 + e, 80 + e, base, 215, **kwargs)
    # Narrower body collar
    _ell(d, cx, cy + 10, 55 + e, 35 + e, base, 228, **kwargs)
    # 4 large eyes
    eye_pts = [(-30, cy - 60), (-10, cy - 70), (10, cy - 70), (30, cy - 60)]
    for ex, ey in eye_pts:
        _ell(d, cx + ex, ey, 12 + e, 10 + e, accent, 235, **kwargs)
        _ell(d, cx + ex, ey, 6 + e, 6 + e, _darken(accent, 40), 255, **kwargs)
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
            _line(d, [x0, y0, x1, y1], (*base[:3], 200 - seg * 16), width=max(1, 10 - seg), **kwargs)
            _ell(d, x1, y1 + 10, 4 + e, 4 + e, accent, 80 - seg * 8, **kwargs)
            x0, y0 = x1, y1


def draw_humanoid(d, img, cx, cy, base, accent, feature="default", expand=0, **kwargs):
    e = expand
    if feature == "cloak":
        _poly(d, [cx - 42, cy - 80,
                  cx - 110, cy + 20, cx - 95, cy + 170,
                  cx, cy + 140,
                  cx + 95, cy + 170, cx + 110, cy + 20, cx + 42, cy - 80],
              _darken(base, 20), 115, **kwargs)
    # Legs
    _rect(d, cx - 30, cy + 55, cx - 8, cy + 155, base, 195, e, **kwargs)
    _rect(d, cx + 8, cy + 55, cx + 30, cy + 155, base, 195, e, **kwargs)
    # Feet
    _ell(d, cx - 22, cy + 155, 22 + e, 12 + e, base, 182, **kwargs)
    _ell(d, cx + 22, cy + 155, 22 + e, 12 + e, base, 182, **kwargs)
    # Hips
    _ell(d, cx, cy + 45, 42 + e, 20 + e, base, 210, **kwargs)
    # Torso
    _ell(d, cx, cy - 18, 42 + e, 68 + e, base, 225, **kwargs)
    # Shoulders
    _ell(d, cx - 55, cy - 52, 22 + e, 22 + e, base, 208, **kwargs)
    _ell(d, cx + 55, cy - 52, 22 + e, 22 + e, base, 208, **kwargs)
    # Upper arms
    _rect(d, cx - 72, cy - 52, cx - 42, cy + 22, base, 198, e, **kwargs)
    _rect(d, cx + 42, cy - 52, cx + 72, cy + 22, base, 198, e, **kwargs)
    # Forearms
    _rect(d, cx - 70, cy + 20, cx - 44, cy + 82, base, 188, e, **kwargs)
    _rect(d, cx + 44, cy + 20, cx + 70, cy + 82, base, 188, e, **kwargs)
    # Neck
    _ell(d, cx, cy - 85, 18 + e, 22 + e, base, 228, **kwargs)
    # Head
    _ell(d, cx, cy - 135, 34 + e, 40 + e, base, 238, **kwargs)
    # Eyes
    for ex in [-14, 14]:
        _ell(d, cx + ex, cy - 142, 8 + e, 8 + e, accent, 245, **kwargs)

    if feature == "crown":
        for ox, h in [(-16, 22), (-7, 32), (0, 38), (7, 32), (16, 22)]:
            _poly(d, [cx + ox - 5, cy - 172, cx + ox + 5, cy - 172, cx + ox, cy - 172 - h],
                  accent, 228, **kwargs)
    elif feature == "aura":
        for r_a in [52, 38, 24]:
            ring = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            rd = ImageDraw.Draw(ring, "RGBA")
            rd.ellipse([cx - r_a, cy - 190 - r_a, cx + r_a, cy - 190 + r_a],
                       outline=(*accent[:3], 140), width=3)
            ring = ring.filter(ImageFilter.GaussianBlur(4))
            img.alpha_composite(ring)
    elif feature == "scars":
        for sx, sy, ex_c, ey_c in [(-12, cy - 55, -4, cy - 25),
                                    (8, cy - 62, 16, cy - 32),
                                    (-6, cy + 5, 2, cy + 32)]:
            _line(d, [cx + sx, cy + sy, cx + ex_c, ey_c], (*accent[:3], 190), width=3, **kwargs)
    elif feature == "thorns_sm":
        for ox, oy in [(-44, cy - 58), (44, cy - 58), (-44, cy - 28), (44, cy - 28),
                       (-44, cy + 2), (44, cy + 2)]:
            _poly(d, [cx + ox - 4, cy + oy, cx + ox + 4, cy + oy, cx + ox, cy + oy - 18],
                  accent, 210, **kwargs)
    elif feature == "glow_body":
        for oy in range(-60, 80, 18):
            _ell(d, cx, cy + oy, 16 + e, 10 + e, accent, 100, **kwargs)
    elif feature == "fire_crown":
        for ox, h in [(-20, 30), (-10, 46), (0, 58), (10, 46), (20, 30)]:
            _poly(d, [cx + ox - 5, cy - 172, cx + ox + 5, cy - 172, cx + ox, cy - 172 - h],
                  accent, 210, **kwargs)
    elif feature == "fracture":
        for pts in [[(cx - 22, cy - 75), (cx - 8, cy + 12), (cx - 16, cy + 82)],
                    [(cx + 10, cy - 68), (cx + 20, cy + 5), (cx + 8, cy + 75)]]:
            _line(d, pts, (*accent[:3], 130), width=2, **kwargs)
    elif feature == "halo":
        ring = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        rd = ImageDraw.Draw(ring, "RGBA")
        rd.ellipse([cx - 42, cy - 200, cx + 42, cy - 158], outline=(*accent[:3], 200), width=5)
        ring = ring.filter(ImageFilter.GaussianBlur(6))
        img.alpha_composite(ring)
    elif feature == "split":
        _line(d, [(cx, cy - 175), (cx, cy + 170)], (*accent[:3], 80), width=2, **kwargs)
        _ell(d, cx - 12, cy - 148, 8 + e, 8 + e, _rgb("#e05030"), 240, **kwargs)
    elif feature == "antenna":
        for sign, ox in [(-1, -5), (1, 5)]:
            _line(d, [cx + ox, cy - 174, cx + ox + sign * 22, cy - 215],
                   (*accent[:3], 210), width=3, **kwargs)
            _ell(d, cx + ox + sign * 22, cy - 217, 8 + e, 8 + e, accent, 238, **kwargs)
    elif feature == "shadow_void":
        pass  # aura handles this one
    elif feature == "scales":
        for row in range(6):
            for col in range(4):
                sx = cx - 30 + col * 20
                sy = cy - 50 + row * 22
                lmode = hasattr(d, "im") and d.im.mode == "L"
                oc = 180 if lmode else (*accent[:3], 100)
                d.ellipse([sx, sy, sx + 16, sy + 14], outline=oc, width=2)
    elif feature == "wings_small":
        _poly(d, [cx - 44, cy - 68, cx - 105, cy - 20, cx - 90, cy + 30, cx - 38, cy - 10],
              base, 155, **kwargs)
        _poly(d, [cx + 44, cy - 68, cx + 105, cy - 20, cx + 90, cy + 30, cx + 38, cy - 10],
              base, 155, **kwargs)


# ── Frame & labels ─────────────────────────────────────────────────────────────

def _frame(img, accent):
    d = ImageDraw.Draw(img, "RGBA")
    # Outer border
    d.rectangle([2, 2, W - 3, H - 3], outline=(*accent[:3], 120), width=3)
    # Inner border
    d.rectangle([8, 8, W - 9, H - 9], outline=(*accent[:3], 45), width=1)
    # Corner diamonds
    for cx2, cy2 in [(8, 8), (W - 9, 8), (8, H - 9), (W - 9, H - 9)]:
        size = 12
        d.polygon([cx2, cy2 - size, cx2 + size, cy2, cx2, cy2 + size, cx2 - size, cy2],
                  fill=(*accent[:3], 130))
    # Mid-border decorative lines
    mid_y = 16
    d.line([24, mid_y, W - 24, mid_y], fill=(*accent[:3], 35), width=1)
    d.line([24, H - mid_y, W - 24, H - mid_y], fill=(*accent[:3], 35), width=1)


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
    d.line([0, bar_top, W, bar_top], fill=(*accent[:3], 110), width=2)
    d.line([0, bar_top + 3, W, bar_top + 3], fill=(*accent[:3], 45), width=1)

    # Decorative side flourishes
    fw = 60
    d.line([0, bar_top + 18, fw, bar_top + 18], fill=(*accent[:3], 70), width=1)
    d.line([W - fw, bar_top + 18, W, bar_top + 18], fill=(*accent[:3], 70), width=1)
    d.ellipse([fw - 4, bar_top + 15, fw + 4, bar_top + 21], fill=(*accent[:3], 100))
    d.ellipse([W - fw - 4, bar_top + 15, W - fw + 4, bar_top + 21], fill=(*accent[:3], 100))

    kw2 = {"font": name_font} if name_font else {}
    if name_font:
        bbox = d.textbbox((0, 0), name.upper(), font=name_font)
        tw = bbox[2] - bbox[0]
        text_x = (W - tw) // 2
        text_y = H - 95
        # Shadow
        d.text((text_x + 2, text_y + 2), name.upper(), fill=(0, 0, 0, 160), **kw2)
        # Main text
        d.text((text_x, text_y), name.upper(), fill=(*accent[:3], 230), **kw2)
    else:
        d.text((W // 2 - len(name) * 8, H - 90), name.upper(), fill=(*accent[:3], 230))


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
    print("\nDone.")
