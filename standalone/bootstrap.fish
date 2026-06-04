#!/usr/bin/env fish
# StoryForge environment bootstrap.
# Run from project root: ./bootstrap.fish

set -l PROJECT_ROOT (status dirname)
cd $PROJECT_ROOT

echo "─── StoryForge Bootstrap ───"

# 1. Verify uv is installed
if not command -v uv >/dev/null
    echo "uv not found. Installing via official script..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    set -gx PATH ~/.local/bin $PATH
end

# 2. Pin Python 3.14 (or latest available)
# uv python pin 3.14 # Might fail if 3.14 is not out yet, roadmap says 3.14+

# 3. Create project venv and install deps
echo "→ syncing dependencies..."
uv sync

# 4. Seed campaign state if absent
set -l CAMPAIGN_DIR data/campaigns/family_campaign_01
if not test -f $CAMPAIGN_DIR/state.json
    echo "→ seeding campaign state..."
    mkdir -p $CAMPAIGN_DIR
    cp data/seeds/default_campaign.json $CAMPAIGN_DIR/state.json
end

echo ""
echo "✓ Bootstrap complete."
echo ""
echo "Next: ./scripts/dev.fish    (launches the dev server)"
