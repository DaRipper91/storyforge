#!/bin/bash
# Get the directory where this script is located
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# Ensure tools like 'uv' installed in ~/.local/bin are available
export PATH="$HOME/.local/bin:$PATH"

# Run the integrated launcher which starts both the Python Brain and Godot
uv run python main.py
