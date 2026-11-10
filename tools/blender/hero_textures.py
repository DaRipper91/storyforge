"""Procedural texture generation for hand-modelled heroes (numpy inside Blender), baked to PNG images that glTF can carry."""
import bpy, numpy as np, os


def _grid(n):
    y, x = np.mgrid[0:n, 0:n].astype(np.float32) / n
    return x, y


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)


def value_noise(n, cells, seed):
    rng = np.random.default_rng(seed)
    g = rng.random((cells + 1, cells + 1)).astype(np.float32); g[-1, :] = g[0, :]; g[:, -1] = g[:, 0]
    x, y = _grid(n)
    xi, yi = (x * cells), (y * cells)
    x0, y0 = xi.astype(int) % cells, yi.astype(int) % cells
    fx, fy = smooth(0, 1, xi - np.floor(xi)), smooth(0, 1, yi - np.floor(yi))
    a, b = g[y0, x0], g[y0, x0 + 1]
    c, d = g[y0 + 1, x0], g[y0 + 1, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def fbm(n, seed, octaves=4, base=4):
    out = np.zeros((n, n), np.float32); amp = 1.0; tot = 0.0
    for o in range(octaves):
        out += amp * value_noise(n, base * 2 ** o, seed + o); tot += amp; amp *= 0.5
    return out / tot


def voronoi(n, cells, seed):
    """Returns (edge_distance F2-F1, cell_id_value), tiling."""
    rng = np.random.default_rng(seed)
    pts = (np.stack(np.meshgrid(np.arange(cells), np.arange(cells)), -1).reshape(-1, 2) + rng.random((cells * cells, 2))) / cells
    x, y = _grid(n)
    d1 = np.full((n, n), 9, np.float32); d2 = np.full((n, n), 9, np.float32); cid = np.zeros((n, n), np.float32)
    for k, (px, py) in enumerate(pts):
        for ox in (-1, 0, 1):
            for oy in (-1, 0, 1):
                d = np.hypot(x - (px + ox), y - (py + oy))
                closer = d < d1
                d2 = np.where(closer, d1, np.minimum(d2, d)); cid = np.where(closer, rng.random() if False else (k * 0.6180339) % 1.0, cid)
                d1 = np.where(closer, d, d1)
    return (d2 - d1) * cells, cid


def normal_from_height(h, strength=2.0):
    gx = np.roll(h, -1, 1) - np.roll(h, 1, 1)
    gy = np.roll(h, -1, 0) - np.roll(h, 1, 0)
    nx, ny, nz = -gx * strength * h.shape[0] / 64, gy * strength * h.shape[0] / 64, np.ones_like(h)
    l = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.stack([nx / l * 0.5 + 0.5, ny / l * 0.5 + 0.5, nz / l * 0.5 + 0.5, np.ones_like(h)], -1)


def to_image(name, rgba, outdir, colorspace="sRGB"):
    n = rgba.shape[0]
    img = bpy.data.images.new(name, n, n, alpha=True)
    img.colorspace_settings.name = colorspace
    img.pixels = np.clip(rgba[::-1], 0, 1).astype(np.float32).ravel()    # Blender rows run bottom-up
    os.makedirs(outdir, exist_ok=True)
    img.filepath_raw = os.path.join(outdir, name + ".png"); img.file_format = 'PNG'; img.save()
    img.reload()
    img.pack()      # packed images carry real pixels into the glTF export
    return img


def bind(material, base=None, normal=None, emission=None, emission_strength=1.0):
    """Wire image textures into a Principled material (they export as glTF textures)."""
    nt = material.node_tree; b = nt.nodes["Principled BSDF"]
    def tex(img, cs):
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = img; img.colorspace_settings.name = cs; return t
    if base is not None:
        t = tex(base, "sRGB"); nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
        if material.surface_render_method == 'BLENDED':
            nt.links.new(t.outputs["Alpha"], b.inputs["Alpha"])
    if normal is not None:
        t = tex(normal, "Non-Color"); nm = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(t.outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    if emission is not None:
        t = tex(emission, "sRGB"); nt.links.new(t.outputs["Color"], b.inputs["Emission Color"])
        b.inputs["Emission Strength"].default_value = emission_strength
