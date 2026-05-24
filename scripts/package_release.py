"""
Assemble the final release zip from build artifacts.

Run AFTER:
  1. uv run python scripts/build.py          (produces dist/StoryForge.exe)
  2. godot --headless --export-release ...    (produces dist/StoryForge_client.exe)

Produces:
  dist/StoryForge_v<version>_Windows.zip
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"

# Read version from pyproject.toml — no TOML parser needed
def _version() -> str:
    for line in (ROOT / "pyproject.toml").read_text().splitlines():
        if line.strip().startswith("version"):
            return line.split("=")[1].strip().strip('"')
    return "0.0.0"


README_TXT = """\
StoryForge: The Feral World — D&D 5e AI Dungeon Master
=======================================================

SETUP
-----
1. Copy .env.example to .env and fill in your API keys.
2. Double-click StoryForge.exe to launch.

CONTROLS (Godot client)
-----------------------
Right-drag   Orbit camera
Scroll       Zoom in/out
R            Reset camera to isometric view

REQUIREMENTS
------------
An internet connection is required for the Gemini AI Dungeon Master.
Get a free API key at https://aistudio.google.com/

SUPPORT
-------
https://github.com/DaRipper91/storyforge
"""


def main() -> None:
    version = _version()
    zip_name = f"StoryForge_v{version}_Windows.zip"
    zip_path = DIST / zip_name

    # Required artifacts
    launcher = DIST / "StoryForge.exe"
    client   = DIST / "StoryForge_client.exe"
    for f in (launcher, client):
        if not f.exists():
            print(f"[package] Missing artifact: {f}")
            print("Run build.py and the Godot export step first.")
            sys.exit(1)

    print(f"[package] Building {zip_name} ...")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        base = f"StoryForge_v{version}/"

        # Binaries
        zf.write(launcher, base + "StoryForge.exe")
        zf.write(client,   base + "StoryForge_client.exe")

        # Campaign seeds
        seeds_dir = ROOT / "data" / "seeds"
        for seed in seeds_dir.rglob("*"):
            if seed.is_file():
                zf.write(seed, base + "data/seeds/" + seed.relative_to(seeds_dir).as_posix())

        # .env template and readme
        env_example = ROOT / ".env.example"
        if env_example.exists():
            zf.write(env_example, base + ".env.example")

        zf.writestr(base + "README.txt", README_TXT)

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"[package] OK  →  {zip_path}  ({size_mb:.1f} MB)")
    print()
    print("itch.io:  butler push dist/StoryForge_v{version}_Windows.zip <user>/<game>:windows")
    print("Steam:    steamcmd +login ... +run_app_build ...")


if __name__ == "__main__":
    main()
