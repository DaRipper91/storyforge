# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

## What this is

StoryForge is a hybrid Virtual Tabletop (VTT) + AI Dungeon Master for family D&D 5e. A FastAPI backend serves a vanilla JS frontend; Gemini acts as a narrative renderer (not a state machine). State is local-first and JSON-snapshotted to disk. There is also a `gui.py` desktop wrapper using `pywebview` + PyQt6 that embeds the app in a native window.

## Commands

All commands use `uv`. No npm, no build step for the frontend.

```bash
# Dev server (hot-reload on src/)
uv run uvicorn storyforge.main:app --reload --host 127.0.0.1 --port 8765 --reload-dir src
# or
fish scripts/dev.fish

# Lint
uv run ruff check src/
uv run ruff format src/

# Tests (note: no tests exist yet — tests/ is empty)
uv run pytest
uv run pytest tests/path/to/test_file.py::test_name   # single test
uv run pytest -x -q                                    # fail-fast, quiet

# Install deps / sync venv
uv sync
uv sync --group dev
```

The app is served at `http://127.0.0.1:8765`. Swagger UI is at `/docs`.

## Environment

Copy `.env` and set:
```
STORYFORGE_GEMINI_API_KEY=your_google_ai_studio_key
STORYFORGE_GEMINI_MODEL=gemini-2.0-flash-exp   # optional
STORYFORGE_CAMPAIGN_ID=family_campaign_01       # optional
```

All settings use the `STORYFORGE_` prefix (via `pydantic-settings`). The live campaign state lives at `data/campaigns/<campaign_id>/state.json`, created automatically on first boot from `data/seeds/default_campaign.json`.

## Architecture

### Core invariants

1. **Python is the source of truth.** Gemini outputs are *proposals* — `validators.sanitize()` must gate every AI-proposed `StateDiff` before `state_manager.apply_diff()` is called. Never pass a raw Gemini response directly to `apply_diff`.
2. **All mutations go through `StateManager`.** It holds an `asyncio.Lock` that serializes concurrent writes. Every public mutator calls `_commit()` at the end, which increments `revision`, atomically saves to disk, and fans out to the `EventBus`.
3. **Prompts are Markdown files on disk**, not f-strings. Edit `src/storyforge/ai/prompts/*.md` to change AI behavior without touching Python.
4. **`core/` is pure logic — no I/O.** Don't import from `ai/`, `api/`, or `persistence/` inside `core/`.

### Data flow for a player action

```
Frontend click/text
  → POST /api/action/grid  or  /api/action/freeform
  → rules.check_grid_action()          # deterministic legality check
  → state_manager.apply_grid_action()  # or apply_diff() for freeform
      └─ _commit() → snapshot.save() → event_bus.publish()
  → narrator / interpreter (Gemini)    # text-only for grid; StateDiff+text for freeform
  → state_manager.append_narration()
  → EventBus fans out to all WebSocket clients (/ws/session/{room_id})
```

### Key modules

| Path | Responsibility |
|------|---------------|
| `src/storyforge/core/models.py` | Pydantic schemas — the contract between every layer. `GameState` is the root. `StateDiff` is the only thing Gemini may mutate. |
| `src/storyforge/core/state_manager.py` | In-memory `GameState` + asyncio.Lock. Only mutation point. |
| `src/storyforge/core/validators.py` | Sanitizes AI-proposed `StateDiff`. Philosophy: reject, don't repair. |
| `src/storyforge/core/character_factory.py` | Defines `RACES`, `STATES`, `ROLES` dicts; `build_character()` constructs `CharacterSheet` from a `CharacterCreationRequest`. Single source of truth for race/state/role mechanics. |
| `src/storyforge/core/rules.py` | Deterministic legality checks (`check_grid_action`). |
| `src/storyforge/core/grid.py` | Grid helper functions (`get_cell`, `set_cell`, `in_bounds`, `is_traversable`, `feet_between`). |
| `src/storyforge/ai/client.py` | `GeminiClient` singleton. Calls `generate_content` in a threadpool, enforces `AINarrationResponse` JSON schema, retries with backoff. |
| `src/storyforge/ai/interpreter.py` | Freeform text → `AINarrationResponse` (narrative + optional `StateDiff`). |
| `src/storyforge/ai/narrator.py` | Grid move → flavor narrative text (no `StateDiff`). |
| `src/storyforge/persistence/snapshot.py` | Atomic save/load via temp-file + `os.replace`. |
| `src/storyforge/events/bus.py` | In-process pub/sub. Each WebSocket subscriber gets its own `asyncio.Queue`. |
| `src/storyforge/api/routes_lobby.py` | Lobby + character creation endpoints (`/api/lobby/*`, `/api/character/create`). |
| `src/storyforge/api/ws_session.py` | WebSocket handler (`/ws/session/{room_id}`). |
| `src/storyforge/gui.py` | PyWebView + PyQt6 desktop wrapper — spawns uvicorn in a thread, opens a native window. |

### Phase state machine

`TITLE → MENU → MODE_SELECT → LOBBY → CREATION → EXPLORATION` (COMBAT is deferred to v0.2).

- `LOBBY`: waiting for gamepad/controller slots to be claimed.
- `CREATION`: players pick race, evolutionary state, predator role, name, ability scores.
- `EXPLORATION`: grid movement + freeform text actions active.

AI diffs (`StateDiff`) are rejected during `LOBBY` and `CREATION` phases. Phase changes to `COMBAT` are also rejected by `validators.py` until v0.2.

### Custom species system

This is **not** standard D&D races/classes. Characters are built from three orthogonal choices:

- **Race** (15 options across Sci-Fi, Mythic, Eldritch themes) — grants ability score bonuses and speed.
- **Evolutionary State** (Behemoth / Phantom / Swarm-Host / Mimic) — determines hit die and base AC.
- **Predator Role** (Stalker / Vanguard / Catalyst / Siphoner) — determines starting inventory.

Ability scores use the standard D&D array `[15, 14, 13, 12, 10, 8]` distributed across STR/DEX/CON/INT/WIS/CHA; racial bonuses are applied on top.

### `StateDiff` allowed fields

The validator whitelist (`core/validators.py`):
- `character_updates`: only `hp_current`, `conditions`, `movement_remaining` (direct `position` writes are rejected — use `cell_updates` instead)
- `cell_updates`: current room only, must be in-bounds
- `add_inventory`: max quantity 10 per item
- `remove_inventory`: character must own the item
- `phase_change`: `COMBAT` blocked in MVP
