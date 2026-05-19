#!/usr/bin/env fish
# scripts/dev.fish - Launch the dev server

set -l PROJECT_ROOT (status dirname)/..
cd $PROJECT_ROOT

echo "🚀 Launching StoryForge Dev Server..."
echo "Frontend: http://127.0.0.1:8765"
echo "API Docs: http://127.0.0.1:8765/docs"

# Use uv to run uvicorn with hot-reload
uv run uvicorn storyforge.main:app \
    --reload \
    --host 127.0.0.1 \
    --port 8765 \
    --reload-dir src
