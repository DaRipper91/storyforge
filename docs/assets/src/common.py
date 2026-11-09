"""Shared helpers for the StoryForge README asset generators (stdlib only)."""
from __future__ import annotations

import json
from pathlib import Path
from xml.sax.saxutils import escape

SRC = Path(__file__).resolve().parent
ASSETS = SRC.parent
REPO = ASSETS.parent.parent

PALETTE = json.loads((ASSETS / "palette.json").read_text())
DARK, LIGHT, FONTS = PALETTE["dark"], PALETTE["light"], PALETTE["fonts"]
TOKENS = list(DARK)


def esc(s: str) -> str:
    return escape(str(s))


def base_css() -> str:
    """Colour utility classes (f-* fill, s-* stroke, t-* text) + light overrides."""
    dark, light = [], []
    for t in TOKENS:
        for pre, prop in (("f", "fill"), ("s", "stroke")):
            dark.append(f".{pre}-{t}{{{prop}:{DARK[t]}}}")
            light.append(f".{pre}-{t}{{{prop}:{LIGHT[t]}}}")
    dark.append(".nofill{fill:none}")
    css = "\n".join(dark)
    css += f"\n.disp{{font-family:{FONTS['display']}}}\n.mono{{font-family:{FONTS['mono']}}}\n"
    css += "@media (prefers-color-scheme: light){\n" + "\n".join(light) + "\n}\n"
    return css


MOTION_CSS = """\
@media (prefers-reduced-motion: no-preference){
.pulse{transform-box:fill-box;transform-origin:center;animation:pulse 3.2s ease-out infinite}
.march{animation:march 2.4s linear infinite}
.twinkle{animation:twinkle 5s ease-in-out infinite}
.ink{animation:ink 7s ease-in-out infinite}
}
@media (prefers-reduced-motion: reduce){
.pulse,.march,.twinkle,.ink{animation:none}
}
@keyframes pulse{0%{transform:scale(.8);opacity:.85}70%{transform:scale(2.1);opacity:0}100%{transform:scale(2.1);opacity:0}}
@keyframes march{to{stroke-dashoffset:-18}}
@keyframes twinkle{0%,100%{opacity:.15}50%{opacity:.75}}
@keyframes ink{0%,100%{opacity:.55}50%{opacity:.9}}
"""


def svg_open(w: int, h: int, title: str, desc: str, motion: bool = False) -> str:
    css = base_css() + (MOTION_CSS if motion else "")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="{w}" height="{h}" role="img" aria-labelledby="t d">\n'
        f"<title id=\"t\">{esc(title)}</title>\n<desc id=\"d\">{esc(desc)}</desc>\n"
        f"<style>\n{css}</style>\n"
    )


def text(x, y, s, size=12, cls="f-text", family="mono", anchor="start", extra=""):
    return (
        f'<text x="{x:g}" y="{y:g}" font-size="{size:g}" class="{family} {cls}" '
        f'text-anchor="{anchor}" {extra}>{esc(s)}</text>\n'
    )


def write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8", newline="\n")
    print(f"wrote {path.relative_to(REPO)} ({path.stat().st_size} bytes)")
