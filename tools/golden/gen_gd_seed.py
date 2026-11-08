"""Generate godot/scripts/core/data/seed_campaign_data.gd from the default seed.

    uv run python tools/golden/gen_gd_seed.py

The app never serves the raw seed JSON: ``snapshot.load_seed`` runs it through
``GameState.model_validate`` (fills defaults such as lobby_slots, npc schedules,
drops unknown keys like ``world_name``). The offline backend has no pydantic, so
the generator applies the same validation and embeds the *effective* seed
(``model_dump(mode="json")``) as ONE compact GDScript const string plus a tiny
static accessor that JSON-parses it once and returns a deep copy per call.
data/seeds/default_campaign.json itself is never modified.

Deterministic: no timestamps, ASCII-only output, fixed key order (model order).
"""
from __future__ import annotations

import json
from pathlib import Path

from storyforge.core.models import GameState

ROOT = Path(__file__).resolve().parents[2]
SEED = ROOT / "data" / "seeds" / "default_campaign.json"
OUT = ROOT / "godot" / "scripts" / "core" / "data" / "seed_campaign_data.gd"

TEMPLATE = """# GENERATED - do not edit by hand.
# Source: data/seeds/default_campaign.json (after GameState.model_validate)
# Regenerate: uv run python tools/golden/gen_gd_seed.py
class_name SeedCampaignData
extends RefCounted
## The default campaign as the FastAPI app would load it (pydantic defaults filled in).

const SEED_JSON := "%s"

static var _parsed: Variant = null


## Fresh deep copy of the seed GameState Dictionary (JSON numbers as parsed by Godot).
static func get_state() -> Dictionary:
	if _parsed == null:
		_parsed = JSON.parse_string(SEED_JSON)
	return (_parsed as Dictionary).duplicate(true)
"""


def gdscript_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def main() -> None:
    raw = json.loads(SEED.read_text(encoding="utf-8"))
    state = GameState.model_validate(raw).model_dump(mode="json")
    compact = json.dumps(state, ensure_ascii=True, separators=(",", ":"))
    OUT.write_text(TEMPLATE % gdscript_escape(compact), encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(compact)} JSON chars)")


if __name__ == "__main__":
    main()
