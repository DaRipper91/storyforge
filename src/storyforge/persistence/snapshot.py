"""
Filesystem persistence for GameState.

Uses atomic write pattern: write to <file>.tmp, fsync, rename. This
guarantees that state.json is either the old version or the new version
on disk, never a torn write — even on power loss.
"""
from __future__ import annotations
import json
import os
import tempfile
from pathlib import Path

from storyforge.core.models import GameState
from storyforge.config import settings


STATE_FILENAME = "state.json"


def save(campaign_dir: Path, state: GameState) -> None:
    """
    Atomically persist state to <campaign_dir>/state.json.
    
    Pattern:
        1. Write to a sibling .tmp file in the same directory
           (same directory → atomic rename guaranteed on POSIX).
        2. fsync the file so bytes are on disk before rename.
        3. os.replace() — atomic on POSIX and Windows.
    """
    campaign_dir.mkdir(parents=True, exist_ok=True)
    target = campaign_dir / STATE_FILENAME
    
    payload = state.model_dump_json(indent=2)
    
    # tempfile in same directory to guarantee same filesystem (rename is
    # only atomic within a single fs).
    fd, tmp_path_str = tempfile.mkstemp(
        prefix=".state-",
        suffix=".tmp",
        dir=campaign_dir,
    )
    tmp_path = Path(tmp_path_str)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, target)
    except Exception:
        # Best-effort cleanup of orphaned tmp file
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise


def load(campaign_dir: Path) -> GameState | None:
    """Load state.json from a campaign directory, or None if absent."""
    target = campaign_dir / STATE_FILENAME
    if not target.exists():
        return None
    
    with target.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    
    return GameState.model_validate(raw)


def load_seed() -> GameState:
    """Fallback loader for fresh-install boot. Always validates against schema."""
    seed_path = settings.seeds_path / "default_campaign.json"
    if not seed_path.exists():
        raise FileNotFoundError(
            f"Seed campaign missing at {seed_path}. "
            "Run scripts/bootstrap.fish to provision it."
        )
    with seed_path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return GameState.model_validate(raw)
