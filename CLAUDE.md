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

Required `.env` variables (all prefixed `STORYFORGE_` via `pydantic-settings`):
```
STORYFORGE_GEMINI_API_KEY=your_google_ai_studio_key
STORYFORGE_CAMPAIGN_ID=family_campaign_01       # optional
STORYFORGE_GOOGLE_CLIENT_ID=your_oauth_client_id  # optional — disables web auth if unset
STORYFORGE_JWT_SECRET=change-me-in-production     # optional — defaults to dev secret
```

AI model versions are **hardcoded constants** in `config.py` (`STORYFORGE_PRIMARY_MODEL`, `STORYFORGE_PRO_MODEL`), not env vars. The live campaign state lives at `data/campaigns/<campaign_id>/state.json`, created automatically on first boot from `data/seeds/default_campaign.json`. Campaign path is resolved relative to `cwd` (not the package dir) so PyInstaller bundles don't lose saves.

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
| `src/storyforge/api/routes_npc.py` | NPC encounter endpoints (`/api/npc/<name>/*`). Each NPC's state lives on `app.state`, not in the campaign snapshot. |
| `src/storyforge/api/routes_auth.py` | Auth endpoints (`/api/auth/*`). Two paths: web (Google GIS ID token) and desktop (InstalledAppFlow). |
| `src/storyforge/api/ws_session.py` | WebSocket handler (`/ws/session/{room_id}`). |
| `src/storyforge/auth.py` | `authenticate_google_user()` — blocking OAuth2 desktop flow, called via `anyio.to_thread.run_sync`. |
| `src/storyforge/gui.py` | PyWebView + PyQt6 desktop wrapper — spawns uvicorn in a thread, opens a native window. |

### Authentication

Two auth flows, both issuing an `HttpOnly` session cookie (`storyforge_session`, 24h JWT):

- **Web** (`POST /api/auth/google`): frontend sends a Google GIS ID token; backend verifies it with `google.oauth2.id_token.verify_oauth2_token`. Requires `STORYFORGE_GOOGLE_CLIENT_ID` to be set, otherwise returns 501.
- **Desktop** (`POST /api/auth/desktop_login`): triggers `InstalledAppFlow` (browser popup, localhost redirect) in a thread. Caches credentials to `token.json`. Used by Godot/native clients.

`GET /api/auth/me` returns current session from cookie. `POST /api/auth/logout` clears cookie.

The `get_current_user` dependency in `api/deps.py` decodes the session cookie and raises 401 if missing or invalid.

### NPC Encounters system

Each named NPC lives in `src/storyforge/encounters/<name>.py` and follows this pattern:

- `<Name>EncounterState` (Pydantic model) — mutable state for the encounter (turn count, mood, flags, etc.)
- `<Name>` service class — pure logic, never touches `GameState` directly; mutations return a `StateDiff` for the caller to apply.
- State is stored on `app.state.<npc>_encounter` (session-level; resets when app restarts, not persisted to the campaign snapshot).

Current NPCs: `ShopkeeperJon`, `SamaelTheDemigod`, `MadameHaylie`, `QueenDAnna`, `FireyRedVelvet`, `GuildmasterKodrik`, `WardenApprenticeBryne`, `FrontManNathis`.

Jon's "Haylie bailout" is a cross-NPC dependency: a critical escape fail on Jon sets `jon.encounter.bailout_available = True`, which `POST /api/npc/haylie/bailout` checks before triggering Haylie's intervention.

NPC AI system prompts are Markdown files at `src/storyforge/ai/prompts/npc_<name>.md`.

### Phase state machine

`TITLE → MENU → MODE_SELECT → LOBBY → CREATION → EXPLORATION` (COMBAT is deferred to v0.2).

- `LOBBY`: waiting for gamepad/controller slots to be claimed.
- `CREATION`: players pick race, evolutionary state, predator role, name, ability scores.
- `EXPLORATION`: grid movement + freeform text actions active.

AI diffs (`StateDiff`) are rejected during `LOBBY` and `CREATION` phases. Phase changes to `COMBAT` are also rejected by `validators.py` until v0.2.

### Custom species system

This is **not** standard D&D races/classes. Characters are built from three orthogonal choices:

- **Race** (35 options across Cosmic, Primal, Eldritch, Mechanical, and Humanoid themes) — grants ability score bonuses and speed.
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
