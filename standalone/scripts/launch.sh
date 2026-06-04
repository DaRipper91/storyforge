#!/bin/bash
# StoryForge Launcher

PROJECT_ROOT="/home/daripper/Projects/storyforge"
cd "$PROJECT_ROOT"

# Check if server is already running
if ! lsof -i:8765 > /dev/null; then
    echo "Starting StoryForge server..."
    # Start server in background
    uv run uvicorn storyforge.main:app --host 127.0.0.1 --port 8765 > /dev/null 2>&1 &
    # Give it a second to boot
    sleep 2
fi

# Open the browser
xdg-open "http://127.0.0.1:8765"
