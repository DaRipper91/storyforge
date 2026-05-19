#!/bin/bash
# StoryForge Launcher (Feral Successors Update)

PROJECT_ROOT="/home/daripper/Projects/storyforge"
cd "$PROJECT_ROOT"

# Launch the native GUI wrapper
# This handles the FastAPI server and the Webview window in a single process
uv run python src/storyforge/gui.py
