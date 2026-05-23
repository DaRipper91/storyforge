"""
StoryForge Integrated Launcher.

Orchestrates the 'Headless DM' (Python/FastAPI) and the 'Cinematic Client' (Godot).
"""
import os
import sys
import subprocess
import time
import signal
from pathlib import Path

# Configuration
PORT = 8765
GODOT_PATH = os.environ.get("GODOT_PATH", "godot") # Path to godot binary
PROJECT_ROOT = Path(__file__).resolve().parent

def start_backend():
    """Starts the Python FastAPI server in a background process."""
    print("🚀 Starting Headless DM (Python Server)...")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT / "src")
    
    # We use 'uv run' to ensure the correct environment
    process = subprocess.Popen(
        ["uv", "run", "uvicorn", "storyforge.main:app", "--port", str(PORT), "--host", "127.0.0.1"],
        cwd=PROJECT_ROOT,
        env=env,
        # stdout=subprocess.PIPE, # Uncomment to capture logs
        # stderr=subprocess.PIPE
    )
    return process

def start_godot():
    """Starts the Godot cinematic client."""
    print("🎬 Starting Cinematic Client (Godot)...")
    # In development, we run the project from the godot/ folder.
    # We assume 'godot' command is in PATH or provided via GODOT_PATH.
    try:
        process = subprocess.Popen(
            [GODOT_PATH, "--path", str(PROJECT_ROOT / "godot")],
            cwd=PROJECT_ROOT / "godot"
        )
        return process
    except FileNotFoundError:
        print("❌ Error: Godot binary not found. Please set GODOT_PATH environment variable.")
        return None

def main():
    backend = None
    client = None
    
    try:
        backend = start_backend()
        
        # Give the backend a moment to spin up
        print("⏳ Waiting for Brain to initialize...")
        time.sleep(2)
        
        client = start_godot()
        
        if client:
            print("✨ StoryForge is running.")
            client.wait() # Wait for the window to close
        else:
            print("⚠️ Godot failed to start. Running in Headless mode.")
            backend.wait()

    except KeyboardInterrupt:
        print("\n🛑 Shutting down StoryForge...")
    finally:
        if client and client.poll() is None:
            client.terminate()
        if backend and backend.poll() is None:
            backend.terminate()
        print("👋 Goodbye.")

if __name__ == "__main__":
    main()
