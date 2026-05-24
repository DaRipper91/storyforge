"""
StoryForge desktop launcher — PyInstaller entry point.

Runs the FastAPI brain in a daemon thread, then starts the Godot cinematic
client as a subprocess. Exits when Godot exits.

In dev mode (not frozen) reads GODOT_PATH and uses the godot/ project dir.
"""
from __future__ import annotations

import os
import sys
import subprocess
import threading
import time
from pathlib import Path


_PORT = 8765
_BIND = "127.0.0.1"


def _serve() -> None:
    import uvicorn
    from storyforge.main import app  # noqa: PLC0415

    uvicorn.run(app, host=_BIND, port=_PORT, log_level="warning")


def _godot_cmd() -> list[str] | None:
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
        name = "StoryForge_client.exe" if sys.platform == "win32" else "StoryForge_client"
        exe = base / name
        return [str(exe), "--local-server"] if exe.exists() else None

    # Dev mode — use GODOT_PATH env var or assume 'godot' is in PATH
    godot = os.environ.get("GODOT_PATH", "godot")
    project = Path(__file__).resolve().parents[3] / "godot"
    return [godot, "--path", str(project), "--", "--local-server"]


def main() -> None:
    threading.Thread(target=_serve, daemon=True, name="storyforge-server").start()
    time.sleep(1.5)

    cmd = _godot_cmd()
    if cmd is None:
        print("[storyforge] Godot client not found — headless mode. Ctrl+C to quit.")
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            pass
        return

    try:
        proc = subprocess.Popen(cmd)
        proc.wait()
    except FileNotFoundError:
        print(f"[storyforge] Godot binary not found: {cmd[0]}")
        print("Install Godot 4 or set the GODOT_PATH environment variable.")
        input("Press Enter to exit.")


if __name__ == "__main__":
    main()
