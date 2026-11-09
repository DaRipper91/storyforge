"""Build races-<group>.png contact sheets. Group membership is read from RACES, not hardcoded."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from common import ASSETS, REPO

sys.path.insert(0, str(REPO / "src"))
from storyforge.core.character_factory import RACES  # noqa: E402

CARDS = REPO / "godot" / "assets" / "characters"
BG = "#0f0c0a"
COLS = 5
BUDGET = 440 * 1024


def main() -> None:
    groups: dict[str, list[str]] = {}
    for race, d in RACES.items():
        groups.setdefault(d.group, []).append(race.value)
    for group, races in groups.items():
        files = []
        for r in races:
            f = CARDS / f"{r}.jpg"
            if not f.exists():
                raise SystemExit(f"missing card {f}")
            files.append(str(f))
        out = ASSETS / f"races-{group.lower()}.png"
        # montage (lossless) -> posterize via two quantisation passes until the sheet fits the budget
        tmp = out.with_suffix(".tmp.miff")
        subprocess.run(["magick", "montage", *files, "-tile", f"{COLS}x", "-geometry", "220x308+6+6",
                        "-filter", "Lanczos", "-background", BG, str(tmp)], check=True)
        for colors in (128, 96, 64, 48, 32):
            subprocess.run(["magick", str(tmp), "+dither", "-colors", "256", "+dither", "-colors", str(colors),
                            "-strip", "-define", "png:exclude-chunk=date,time,tIME,iTXt,tEXt,zTXt",
                            "-define", "png:compression-level=9", str(out)], check=True)
            if out.stat().st_size <= BUDGET:
                break
        tmp.unlink()
        print(f"wrote {out.relative_to(REPO)} ({out.stat().st_size} bytes, {len(files)} cards, {colors} colors)")


if __name__ == "__main__":
    main()
