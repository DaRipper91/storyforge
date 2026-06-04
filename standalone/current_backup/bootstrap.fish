#!/usr/bin/env fish
# bootstrap.fish - Senior-grade environment setup for StoryForge

echo "🗡️  Forging the StoryForge Environment..."

# 1. Create Core Structure
mkdir -p src/storyforge/{api,core,ai/prompts,persistence}
mkdir -p static/{css,js}
mkdir -p data/campaigns/family_campaign_01
mkdir -p scripts

# 2. Initialize .env if missing
if not test -f .env
    echo "STORYFORGE_GEMINI_API_KEY=your_key_here" > .env
    echo "⚠️  Created .env. Please add your Gemini API Key!"
end

# 3. Check for 'uv' (fastest python manager)
if not command -v uv >/dev/null
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
end

# 4. Sync Dependencies
echo "📦 Syncing dependencies..."
# Create a basic pyproject.toml if it doesn't exist
if not test -f pyproject.toml
    echo '[project]
name = "storyforge"
version = "0.1.0"
dependencies = [
    "fastapi",
    "uvicorn[standard]",
    "pydantic",
    "pydantic-settings",
    "google-genai",
]
' > pyproject.toml
end

uv sync

echo "✅ Bootstrap Complete. Use ./scripts/dev.fish to launch."
