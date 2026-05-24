"""
StoryForge build script.

Step 1 (this script): Bundle the Python server + launcher into StoryForge.exe.
Step 2 (Godot editor):
    godot --headless --export-release "Windows Desktop" dist/StoryForge_client.exe

The release zip should contain:
    StoryForge.exe          <- Python launcher (this build)
    StoryForge_client.exe   <- Godot cinematic client (Godot export step)
    data/seeds/             <- Campaign seed data
    .env.example            <- API key template
    README.txt              <- Player instructions

Usage:
    uv run python scripts/build.py
"""
import sys
import platform
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "StoryForge.spec"
DIST = ROOT / "dist"


def main():
    print("=== StoryForge build ===")
    print(f"Platform : {platform.system()} {platform.machine()}")
    print(f"Python   : {sys.version.split()[0]}")
    print(f"Spec     : {SPEC}")
    print()

    # Ensure dist/ exists
    DIST.mkdir(exist_ok=True)

    # Run PyInstaller via the spec file so all options are version-controlled
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", str(SPEC), "--distpath", str(DIST)],
        cwd=ROOT,
    )
    if result.returncode != 0:
        print("\n[build] PyInstaller failed.")
        sys.exit(result.returncode)

    launcher = DIST / ("StoryForge.exe" if platform.system() == "Windows" else "StoryForge")
    if launcher.exists():
        size_mb = launcher.stat().st_size / (1024 * 1024)
        print(f"\n[build] OK  ->  {launcher}  ({size_mb:.1f} MB)")
        print()
        print("Next step: export the Godot client")
        print("  godot --headless --export-release \"Windows Desktop\" dist/StoryForge_client.exe")
        print()
        print("Then run scripts/package_release.py to produce the final release zip.")
    else:
        print(f"\n[build] Warning: expected output not found at {launcher}")


if __name__ == "__main__":
    main()
