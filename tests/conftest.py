"""
Shared fixtures for StoryForge tests.

The FastAPI app requires STORYFORGE_GEMINI_API_KEY at import time (via
pydantic-settings). We set a dummy value before importing anything from the
storyforge package so tests never touch the real Gemini API.
"""
import json
import os
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio
import httpx
from httpx import AsyncClient, ASGITransport

# Provide a fake key before any storyforge module is imported.
os.environ.setdefault("STORYFORGE_GEMINI_API_KEY", "test-fake-key-not-real")

from storyforge.main import app  # noqa: E402 — must follow env setup
from storyforge.core.models import GameState, TurnPhase
from storyforge.core.state_manager import StateManager
from storyforge.persistence import snapshot

# Absolute path to the seed file so tests work regardless of cwd.
_SEED_PATH = Path(__file__).resolve().parents[1] / "data" / "seeds" / "default_campaign.json"


def _load_seed() -> GameState:
    """Parse the default seed into a GameState."""
    return GameState.model_validate(json.loads(_SEED_PATH.read_text()))


@pytest.fixture()
def seed_state() -> GameState:
    """A fresh GameState loaded from the default seed. Not persisted."""
    return _load_seed()


@pytest.fixture()
def fresh_state_manager(tmp_path: Path) -> StateManager:
    """
    A StateManager initialised from the seed with a throwaway campaign
    directory so each test gets an isolated snapshot directory.
    """
    state = _load_seed()
    return StateManager(state, tmp_path / "campaign")


@pytest_asyncio.fixture()
async def client(tmp_path: Path):
    """
    AsyncClient wired to the FastAPI app with a freshly seeded StateManager.

    A new StateManager is installed on app.state before each test and torn
    down (no cleanup needed — tmp_path handles the snapshot dir).
    """
    state = _load_seed()
    campaign_dir = tmp_path / "campaign"
    campaign_dir.mkdir(parents=True, exist_ok=True)
    # Persist seed so snapshot.save() has a parent dir to write into.
    snapshot.save(campaign_dir, state)

    sm = StateManager(state, campaign_dir)

    # Install on app.state before the request is processed.
    app.state.state_manager = sm

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
