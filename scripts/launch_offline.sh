#!/bin/bash
# StoryForge offline launcher: Godot client + in-process LocalBackend (no FastAPI server).
# Needs a display. Saves go to Godot's user:// dir (campaigns/ subfolder).

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT" || exit 1

exec godot --path "$PROJECT_ROOT/godot" -- --backend=local "$@"
