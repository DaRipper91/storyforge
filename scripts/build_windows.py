import os
import subprocess
import sys
import shutil

def run_command(cmd):
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(1)
    return result.stdout

def build():
    print("Step 1: Installing dependencies...")
    run_command(["uv", "sync"])

    print("Step 2: Building executable with PyInstaller...")
    # Using the spec file
    run_command(["uv", "run", "pyinstaller", "storyforge.spec", "--clean", "-y"])

    print("Build complete! The executable is in 'dist/StoryForge'.")
    print("\nTo create an installer, you can use a tool like Inno Setup or NSIS")
    print("pointing to the 'dist/StoryForge' directory.")

if __name__ == "__main__":
    if os.name != 'nt':
        print("Warning: This script is intended to be run on Windows.")
        print("Continuing anyway, but PyInstaller will build for the current OS.")
    
    build()
