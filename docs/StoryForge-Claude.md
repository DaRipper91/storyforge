# 🎯 StoryForge — Architectural Roadmap

> **Da-Architect mode engaged.** Skipping the discovery interview — your spec is self-contained and the architectural axes are already pinned (FastAPI + Canvas + Gemini, hybrid logic loop, local-first, Aether-compatible). Going straight to the blueprint.

---

## 0. Architectural Axioms (the "why" before the "what")

Before the structure, let me lock in **five non-negotiables** that shape every decision below. If any of these are wrong, the rest collapses — push back now.

| # | Axiom | Consequence |
|---|---|---|
| **A1** | **Python is the source of truth.** Gemini is a *renderer*, not a state machine. | All state mutations route through a Python validator before persisting. Gemini's JSON payloads are *proposals*, not commits. |
| **A2** | **State is JSON-serializable and snapshot-able.** | Save/load works for free. Time-travel debugging is trivial. Aether can ingest the same state. |
| **A3** | **Real-time multi-client requires WebSockets, not polling.** | One WS endpoint broadcasts state diffs. REST handles one-shot queries (character sheets, room metadata). |
| **A4** | **AI prompts are versioned files on disk, not f-strings in `.py`.** | You can iterate on Gemini's behavior without touching code. Aether's prompt-engineering tooling reuses the same templates. |
| **A5** | **MVP scope = one room, four pre-built character sheets, grid movement + freeform text, single Gemini call per turn.** | Combat dice math, spellcasting, inventory transactions all land in v0.2. Today we ship the loop. |

If A5 surprises you (you wanted combat in MVP), say so — I can extend the schema below, but it adds ~3 hours of plumbing.

---

## 1. Directory Structure

Modular `src/` layout. Backend, frontend, prompts, and state are physically separated so Aether can later mount any of them independently.

```
storyforge/
├── pyproject.toml                  # uv-managed; Python 3.14+
├── .python-version                 # pinned to 3.14
├── README.md
├── .gitignore
├── scripts/
│   ├── bootstrap.fish              # one-shot env setup
│   ├── dev.fish                    # launch dev server with reload
│   └── seed.fish                   # generate initial campaign state
│
├── src/
│   └── storyforge/
│       ├── __init__.py
│       ├── main.py                 # FastAPI entrypoint
│       ├── config.py               # env vars, paths, Gemini API key
│       │
│       ├── api/                    # HTTP + WS routing layer
│       │   ├── __init__.py
│       │   ├── deps.py             # dependency injection (state mgr, AI client)
│       │   ├── routes_state.py     # GET /api/state, /api/character/{id}
│       │   ├── routes_action.py    # POST /api/action/grid, /api/action/freeform
│       │   └── ws_session.py       # WebSocket /ws/session/{room_id}
│       │
│       ├── core/                   # pure business logic, zero I/O
│       │   ├── __init__.py
│       │   ├── models.py           # Pydantic schemas (THE contract)
│       │   ├── state_manager.py    # in-memory state + JSON persistence
│       │   ├── grid.py             # 2D grid math, LOS, distance
│       │   ├── rules.py            # D&D 5e legality checks (movement, etc.)
│       │   └── validators.py       # sanitize AI-proposed state diffs
│       │
│       ├── ai/                     # Gemini integration
│       │   ├── __init__.py
│       │   ├── client.py           # google-genai SDK wrapper
│       │   ├── narrator.py         # high-level: state → narrative text
│       │   ├── interpreter.py      # high-level: freeform → state diff + text
│       │   └── prompts/            # version-controlled prompt templates
│       │       ├── system_dm.md
│       │       ├── narrate_movement.md
│       │       ├── narrate_combat.md
│       │       ├── interpret_freeform.md
│       │       └── schemas/
│       │           └── state_diff.schema.json
│       │
│       ├── persistence/
│       │   ├── __init__.py
│       │   └── snapshot.py         # save/load campaign state to disk
│       │
│       └── events/
│           ├── __init__.py
│           └── bus.py              # internal pub/sub for state changes
│
├── frontend/
│   ├── index.html                  # served as static by FastAPI
│   ├── css/
│   │   └── styles.css
│   └── js/
│       ├── main.js                 # bootstrap, WS connection
│       ├── canvas.js               # grid rendering, click handling
│       ├── api.js                  # fetch wrappers
│       └── log.js                  # narrative scroll feed
│
├── data/                           # runtime state, gitignored except seeds
│   ├── campaigns/
│   │   └── family_campaign_01/
│   │       ├── state.json
│   │       ├── characters/
│   │       │   ├── cody.json
│   │       │   ├── dee.json
│   │       │   ├── nate.json
│   │       │   └── bray.json
│   │       └── rooms/
│   │           └── room_01_tavern.json
│   └── seeds/                      # version-controlled starter content
│       └── default_campaign.json
│
└── tests/
    ├── test_state_manager.py
    ├── test_validators.py
    └── test_routes.py
```

### Why this shape

- **`core/` has zero I/O.** No FastAPI, no Gemini, no file reads. This is what Aether will eventually import directly — pure logic is portable.
- **`api/` is thin.** Routes parse requests, call `core/`, optionally call `ai/`, return responses. No business logic.
- **`ai/prompts/` as `.md` files.** You edit prompts without redeploying. Diffs in `git log` show prompt evolution. Aether's prompt library can symlink this directory.
- **`data/campaigns/` outside `src/`.** State is *user data*, not code. Easy to back up, easy to share between family members via Syncthing or your dual-remote Git.

---

## 2. Core Data Model

Two layers: **Pydantic models** (runtime validation, type safety) and **JSON instances** (what hits disk). Pydantic 2.x emits JSON Schema for free, which Gemini consumes for structured output.

### 2.1 Pydantic Schemas (`src/storyforge/core/models.py`)

```python
"""
StoryForge canonical data model.

This module is the contract between every other layer. The Python referee
validates incoming actions against these schemas; Gemini receives the JSON
Schema export to constrain its structured output.
"""
from __future__ import annotations
from enum import StrEnum
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


# ─────────────────────── Primitives ───────────────────────

class Coord(BaseModel):
    """A single grid cell. Origin (0,0) is top-left."""
    model_config = ConfigDict(frozen=True)
    x: int = Field(ge=0)
    y: int = Field(ge=0)


class Ability(StrEnum):
    STR = "STR"; DEX = "DEX"; CON = "CON"
    INT = "INT"; WIS = "WIS"; CHA = "CHA"


# ─────────────────────── Characters ───────────────────────

class AbilityScores(BaseModel):
    STR: int = Field(ge=1, le=30)
    DEX: int = Field(ge=1, le=30)
    CON: int = Field(ge=1, le=30)
    INT: int = Field(ge=1, le=30)
    WIS: int = Field(ge=1, le=30)
    CHA: int = Field(ge=1, le=30)


class InventoryItem(BaseModel):
    id: str                          # stable slug, e.g. "longsword_01"
    name: str
    quantity: int = Field(ge=0, default=1)
    equipped: bool = False
    notes: str | None = None


class CharacterSheet(BaseModel):
    """D&D 5e character. MVP-trimmed; expand as needed."""
    id: str                          # "cody", "dee", "nate", "bray"
    name: str
    player: str                      # real-world player name
    char_class: str                  # "Fighter", "Wizard", etc.
    level: int = Field(ge=1, le=20, default=1)
    
    hp_current: int = Field(ge=0)
    hp_max: int = Field(ge=1)
    armor_class: int = Field(ge=1, default=10)
    speed: int = Field(ge=0, default=30)   # feet per turn; grid = 5ft/cell
    
    abilities: AbilityScores
    proficiency_bonus: int = Field(ge=2, le=6, default=2)
    inventory: list[InventoryItem] = Field(default_factory=list)
    
    # Combat-turn ephemeral state
    position: Coord
    movement_remaining: int = 0      # feet left this turn
    conditions: list[str] = Field(default_factory=list)  # "prone", "stunned"


# ─────────────────────── Grid / Room ───────────────────────

class TerrainKind(StrEnum):
    FLOOR = "floor"
    WALL = "wall"
    DOOR = "door"
    DIFFICULT = "difficult"          # half-speed
    HAZARD = "hazard"


class Cell(BaseModel):
    terrain: TerrainKind = TerrainKind.FLOOR
    occupant_id: str | None = None   # character_id or entity_id


class Room(BaseModel):
    id: str
    name: str
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    # cells stored row-major: cells[y * width + x]
    cells: list[Cell]
    description: str                 # static room flavor for AI context


# ─────────────────────── Session State ───────────────────────

class TurnPhase(StrEnum):
    EXPLORATION = "exploration"      # freeform, no initiative
    COMBAT = "combat"


class CombatState(BaseModel):
    initiative_order: list[str]      # character_ids in order
    active_index: int = 0
    round_number: int = 1


class GameState(BaseModel):
    """Root state object. Snapshotted to data/campaigns/<id>/state.json."""
    campaign_id: str
    current_room_id: str
    phase: TurnPhase = TurnPhase.EXPLORATION
    
    characters: dict[str, CharacterSheet]   # keyed by character_id
    rooms: dict[str, Room]
    combat: CombatState | None = None
    
    narrative_log: list[NarrativeEntry] = Field(default_factory=list)
    revision: int = 0                # increments on every mutation
    

class NarrativeEntry(BaseModel):
    revision: int                    # state revision at time of event
    actor_id: str | None             # None for DM narration
    kind: Literal["action", "narration", "system"]
    text: str
    timestamp: str                   # ISO 8601


# ─────────────────────── Action Payloads ───────────────────────

class GridAction(BaseModel):
    """Sent when player clicks a target cell."""
    type: Literal["move", "attack", "interact"]
    actor_id: str
    target: Coord


class FreeformAction(BaseModel):
    """Sent when player types narrative input."""
    actor_id: str
    text: str = Field(min_length=1, max_length=500)


# ─────────────────────── AI Response Contract ───────────────────────

class StateDiff(BaseModel):
    """
    The ONLY thing Gemini is allowed to mutate. Validated and sanitized
    by core/validators.py before being applied to GameState.
    """
    character_updates: dict[str, dict] = Field(default_factory=dict)
    cell_updates: list[tuple[str, Coord, Cell]] = Field(default_factory=list)
    add_inventory: dict[str, list[InventoryItem]] = Field(default_factory=dict)
    remove_inventory: dict[str, list[str]] = Field(default_factory=dict)
    phase_change: TurnPhase | None = None


class AINarrationResponse(BaseModel):
    """What Gemini must return for every call."""
    narrative: str = Field(min_length=1)
    state_diff: StateDiff | None = None
```

### 2.2 Example Serialized State (`data/seeds/default_campaign.json` — trimmed)

```json
{
  "campaign_id": "family_campaign_01",
  "current_room_id": "tavern_01",
  "phase": "exploration",
  "revision": 0,
  "characters": {
    "cody":  { "id": "cody",  "name": "Kael",     "player": "Cody",
               "char_class": "Fighter", "level": 1,
               "hp_current": 12, "hp_max": 12, "armor_class": 16, "speed": 30,
               "abilities": { "STR": 16, "DEX": 12, "CON": 14,
                              "INT": 10, "WIS": 12, "CHA": 8 },
               "proficiency_bonus": 2, "inventory": [],
               "position": { "x": 2, "y": 5 },
               "movement_remaining": 30, "conditions": [] },
    "dee":   { "id": "dee",   "name": "Lyra",     "player": "Dee",   "...": "..." },
    "nate":  { "id": "nate",  "name": "Thorne",   "player": "Nate",  "...": "..." },
    "bray":  { "id": "bray",  "name": "Whisper",  "player": "Bray",  "...": "..." }
  },
  "rooms": {
    "tavern_01": {
      "id": "tavern_01", "name": "The Crooked Tankard",
      "width": 10, "height": 8,
      "description": "Low oak beams, smoke-stained. A bard tunes a lute by the hearth.",
      "cells": [ {"terrain": "floor", "occupant_id": null}, "..." ]
    }
  },
  "combat": null,
  "narrative_log": []
}
```

---

## 3. API Routing Blueprint

Three routing surfaces, each with a different latency profile:

| Surface | Protocol | Use Case | Latency Tolerance |
|---|---|---|---|
| **REST: read** | `GET /api/...` | Initial page load, character sheet inspection | <100ms |
| **REST: write** | `POST /api/action/...` | Player-initiated actions (grid clicks, freeform) | <3s (Gemini call) |
| **WebSocket** | `WS /ws/session/{room_id}` | Broadcasting state diffs to all connected clients | <50ms after server commit |

### 3.1 Route Map

```
GET    /                            → serves frontend/index.html
GET    /static/*                    → serves frontend/{css,js}/

GET    /api/state                   → full GameState (initial sync)
GET    /api/character/{id}          → single CharacterSheet
GET    /api/room/{id}               → single Room

POST   /api/action/grid             → GridAction → state mutation + narration
POST   /api/action/freeform         → FreeformAction → AI interprets + mutation

WS     /ws/session/{room_id}        → bidirectional state diff stream
```

### 3.2 The Dispatch Logic (the core of the Hybrid Logic Loop)

This is where the "Python Referee vs AI Narrator" decision lives. **The fork happens at the route, not inside the AI module.**

```
┌──────────────────────────────────────────────────────────────────┐
│                    INCOMING ACTION                               │
└──────────────────────────────────────────────────────────────────┘
                            │
                ┌───────────┴────────────┐
                │                        │
        Structured click            Freeform text
                │                        │
                ▼                        ▼
   ┌─────────────────────┐   ┌─────────────────────────┐
   │  POST /action/grid  │   │ POST /action/freeform   │
   └─────────────────────┘   └─────────────────────────┘
                │                        │
                ▼                        ▼
   ┌─────────────────────┐   ┌─────────────────────────┐
   │ rules.validate()    │   │ build prompt:           │
   │ (legal move? has    │   │   system_dm.md          │
   │  movement points?)  │   │ + interpret_freeform.md │
   └─────────────────────┘   │ + current GameState     │
                │            │ + player text           │
                │ if legal   └─────────────────────────┘
                ▼                        │
   ┌─────────────────────┐               ▼
   │ state.apply_move()  │   ┌─────────────────────────┐
   │ (deterministic;     │   │ Gemini call             │
   │  no AI yet)         │   │ → AINarrationResponse   │
   └─────────────────────┘   │   { narrative,          │
                │            │     state_diff }        │
                ▼            └─────────────────────────┘
   ┌─────────────────────┐               │
   │ ai.narrator.flavor()│               ▼
   │ Gemini called with  │   ┌─────────────────────────┐
   │ narrate_movement.md │   │ validators.sanitize()   │
   │ + diff context.     │   │ (clamp HP, reject       │
   │ TEXT-ONLY output.   │   │  illegal teleports,     │
   └─────────────────────┘   │  forbid new items       │
                │            │  ex nihilo)             │
                ▼            └─────────────────────────┘
   ┌─────────────────────┐               │
   │  append narrative,  │               ▼
   │  bump revision      │   ┌─────────────────────────┐
   └─────────────────────┘   │ state.apply_diff()      │
                │            │ append narrative        │
                │            │ bump revision           │
                │            └─────────────────────────┘
                │                        │
                └───────────┬────────────┘
                            ▼
              ┌──────────────────────────────┐
              │ event_bus.publish(state_diff)│
              └──────────────────────────────┘
                            │
                            ▼
              ┌──────────────────────────────┐
              │ WebSocket broadcast to all   │
              │ connected clients            │
              └──────────────────────────────┘
```

### 3.3 Critical Design Detail: The Validator Layer

The **single most important security/integrity component**. Gemini will hallucinate. `core/validators.py` rejects state diffs that:

- Increase HP above max without an explicit healing action in the prompt
- Move characters more than their `movement_remaining` allows
- Add inventory items not present in any prompt context
- Change `armor_class` outside of an equip event
- Modify cells outside the current room

If a diff fails validation, the **narrative still gets shown**, but the diff is silently dropped and a `system` log entry is added: `"[ref] state diff rejected: <reason>"`. This means Gemini's flavor text never breaks, but Gemini can never break the world.

### 3.4 Skeleton Implementations

**`src/storyforge/api/routes_action.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from storyforge.core.models import (
    GridAction, FreeformAction, AINarrationResponse,
)
from storyforge.core.state_manager import StateManager
from storyforge.core import rules, validators
from storyforge.ai import narrator, interpreter
from storyforge.events.bus import event_bus
from storyforge.api.deps import get_state_manager

router = APIRouter(prefix="/api/action", tags=["action"])


@router.post("/grid")
async def handle_grid(
    action: GridAction,
    state: StateManager = Depends(get_state_manager),
) -> dict:
    """Structured click → deterministic mutation → flavor narration."""
    char = state.get_character(action.actor_id)
    
    # 1. Python referee validates the move
    legality = rules.check_grid_action(state.current, char, action)
    if not legality.ok:
        raise HTTPException(status_code=400, detail=legality.reason)
    
    # 2. Apply the deterministic mutation
    diff = state.apply_grid_action(char, action)
    
    # 3. Ask Gemini for flavor text (text-only, no state diff allowed)
    narrative = await narrator.flavor_for(state.current, action, diff)
    
    # 4. Log and broadcast
    state.append_narration(actor_id=char.id, kind="action", text=narrative)
    await event_bus.publish(state.snapshot_diff())
    
    return {"narrative": narrative, "revision": state.current.revision}


@router.post("/freeform")
async def handle_freeform(
    action: FreeformAction,
    state: StateManager = Depends(get_state_manager),
) -> dict:
    """Freeform text → AI interprets → validated mutation → broadcast."""
    # 1. Build prompt + call Gemini for structured output
    response: AINarrationResponse = await interpreter.interpret(
        game_state=state.current,
        action=action,
    )
    
    # 2. Sanitize the proposed diff (drop illegal mutations)
    if response.state_diff is not None:
        safe_diff, rejections = validators.sanitize(
            state.current, response.state_diff,
        )
        state.apply_diff(safe_diff)
        for r in rejections:
            state.append_narration(actor_id=None, kind="system", text=f"[ref] {r}")
    
    # 3. Log narrative + broadcast
    state.append_narration(actor_id=action.actor_id, kind="action", text=action.text)
    state.append_narration(actor_id=None, kind="narration", text=response.narrative)
    await event_bus.publish(state.snapshot_diff())
    
    return {"narrative": response.narrative, "revision": state.current.revision}
```

**`src/storyforge/api/ws_session.py`**

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from storyforge.events.bus import event_bus

router = APIRouter()
_connections: set[WebSocket] = set()


@router.websocket("/ws/session/{room_id}")
async def session_ws(websocket: WebSocket, room_id: str):
    await websocket.accept()
    _connections.add(websocket)
    
    # Subscribe to internal event bus
    queue = event_bus.subscribe()
    try:
        while True:
            diff = await queue.get()
            await websocket.send_json(diff)
    except WebSocketDisconnect:
        _connections.discard(websocket)
        event_bus.unsubscribe(queue)
```

---

## 4. Initialization Script

### 4.1 `src/storyforge/main.py`

```python
"""StoryForge FastAPI entrypoint.

Run:
    uv run uvicorn storyforge.main:app --reload --host 127.0.0.1 --port 8765
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from storyforge.config import settings
from storyforge.api import routes_state, routes_action, ws_session
from storyforge.core.state_manager import StateManager
from storyforge.persistence import snapshot


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load campaign state on boot, persist on shutdown."""
    state = snapshot.load(settings.campaign_path) or snapshot.load_seed()
    app.state.state_manager = StateManager(state)
    print(f"[storyforge] loaded campaign: {state.campaign_id}")
    print(f"[storyforge] room: {state.current_room_id}")
    print(f"[storyforge] characters: {list(state.characters.keys())}")
    
    yield
    
    snapshot.save(settings.campaign_path, app.state.state_manager.current)
    print("[storyforge] state persisted to disk")


app = FastAPI(
    title="StoryForge",
    version="0.1.0",
    description="Hybrid VTT + AI Dungeon Master",
    lifespan=lifespan,
)

# API routes
app.include_router(routes_state.router)
app.include_router(routes_action.router)
app.include_router(ws_session.router)

# Frontend static
FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
app.mount("/static", StaticFiles(directory=FRONTEND), name="static")


@app.get("/")
async def root():
    return FileResponse(FRONTEND / "index.html")


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "version": app.version}
```

### 4.2 `src/storyforge/config.py`

```python
"""Environment + path resolution. No secrets in code."""
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="STORYFORGE_",
        extra="ignore",
    )
    
    gemini_api_key: str = Field(..., description="Google AI Studio API key")
    gemini_model: str = "gemini-2.0-flash-exp"
    
    campaign_id: str = "family_campaign_01"
    
    @property
    def campaign_path(self) -> Path:
        return PROJECT_ROOT / "data" / "campaigns" / self.campaign_id
    
    @property
    def prompts_path(self) -> Path:
        return PROJECT_ROOT / "src" / "storyforge" / "ai" / "prompts"


settings = Settings()
```

### 4.3 `scripts/bootstrap.fish`

```fish
#!/usr/bin/env fish
# StoryForge environment bootstrap.
# Run from project root: ./scripts/bootstrap.fish

set -l PROJECT_ROOT (status dirname)/..
cd $PROJECT_ROOT

echo "─── StoryForge Bootstrap ───"

# 1. Verify uv is installed (preferred over pip+venv for speed)
if not command -v uv >/dev/null
    echo "uv not found. Installing via official script..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # uv installs to ~/.local/bin; ensure on PATH for this session
    set -gx PATH ~/.local/bin $PATH
end

# 2. Pin Python 3.14 (uv will download if needed)
echo "→ pinning Python 3.14..."
uv python pin 3.14

# 3. Create project venv and install deps
echo "→ syncing dependencies..."
uv sync

# 4. Seed campaign state if absent
set -l CAMPAIGN_DIR data/campaigns/family_campaign_01
if not test -d $CAMPAIGN_DIR
    echo "→ no campaign state found, seeding from data/seeds/..."
    mkdir -p $CAMPAIGN_DIR
    cp data/seeds/default_campaign.json $CAMPAIGN_DIR/state.json
end

# 5. Verify Gemini API key
if not test -f .env
    echo "⚠  .env missing. Create it with:"
    echo "   STORYFORGE_GEMINI_API_KEY=your_key_here"
    echo ""
    echo "Get a key: https://aistudio.google.com/apikey"
    exit 1
end

# 6. Health check
echo "→ running schema validation..."
uv run python -c "from storyforge.core.models import GameState; print('✓ models OK')"

echo ""
echo "✓ Bootstrap complete."
echo ""
echo "Next: ./scripts/dev.fish    (launches the dev server)"
```

### 4.4 `scripts/dev.fish`

```fish
#!/usr/bin/env fish
# Launch the StoryForge dev server with auto-reload.

set -l PROJECT_ROOT (status dirname)/..
cd $PROJECT_ROOT

# Honor your Wayland axiom for any future Qt overlays
set -gx QT_QPA_PLATFORM wayland

echo "─── StoryForge Dev Server ───"
echo "Frontend: http://127.0.0.1:8765"
echo "API docs: http://127.0.0.1:8765/docs"
echo "Press Ctrl-C to stop."
echo ""

uv run uvicorn storyforge.main:app \
    --reload \
    --host 127.0.0.1 \
    --port 8765 \
    --reload-dir src \
    --reload-dir frontend
```

### 4.5 `pyproject.toml`

```toml
[project]
name = "storyforge"
version = "0.1.0"
description = "Hybrid VTT + AI Dungeon Master for family D&D 5e"
requires-python = ">=3.14"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "pydantic>=2.9",
    "pydantic-settings>=2.6",
    "google-genai>=0.3",
    "websockets>=13",
    "python-multipart>=0.0.12",
]

[dependency-groups]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.24",
    "httpx>=0.28",
    "ruff>=0.7",
]

[tool.uv]
package = true

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/storyforge"]
```

---

## 5. Bootstrap Sequence (Today, Right Now)

Execute in order from a fresh directory:

```fish
# 1. Create project skeleton
mkdir -p ~/projects/storyforge && cd ~/projects/storyforge
mkdir -p src/storyforge/{api,core,ai/prompts/schemas,persistence,events}
mkdir -p frontend/{css,js} data/{campaigns,seeds} scripts tests

# 2. Drop the files above into place
#    (pyproject.toml, main.py, config.py, models.py, scripts/*.fish, etc.)

# 3. Make scripts executable
chmod +x scripts/bootstrap.fish scripts/dev.fish

# 4. Create the .env
echo "STORYFORGE_GEMINI_API_KEY=YOUR_KEY_HERE" > .env

# 5. Initialize Git with your dual-remote setup
git init
git remote add origin git@github.com:DaRipper91/storyforge.git
git remote add gitlab git@gitlab.your-instance.tld:cody/storyforge.git
git add . && git commit -m "feat: StoryForge MVP scaffold"

# 6. Bootstrap and run
./scripts/bootstrap.fish
./scripts/dev.fish
```

Open `http://127.0.0.1:8765/docs` — you'll get the FastAPI Swagger UI, which is your **immediate first verification step** that routing is alive. You can POST to `/api/action/grid` from there before the frontend exists.

---

## 6. Aether Integration Note

Three explicit hooks so future-you doesn't paint into a corner:

| Hook | Where | What it enables |
|---|---|---|
| **`core/` is import-pure** | `src/storyforge/core/*.py` | Aether can `from storyforge.core.models import GameState` and inspect state without spinning up FastAPI. |
| **State snapshots are filesystem JSON** | `data/campaigns/<id>/state.json` | Aether's file watcher can render live campaign state in a dashboard panel without IPC. |
| **`events/bus.py` is the only mutation broadcast** | internal pub/sub | Wire it to your existing IPCBus (`view_changed` signal pattern) and Aether gets real-time game updates for free. |

When you're ready to mount StoryForge into Aether, the pattern is:

```python
# in aether/widgets/storyforge_panel.py
from storyforge.core.state_manager import StateManager
from storyforge.persistence import snapshot

state = snapshot.load(Path("~/projects/storyforge/data/campaigns/family_campaign_01"))
# render state.characters / state.rooms in a NodeGraphQt or QTreeView panel
```

---

## 7. Deferred to v0.2 (deliberately out of MVP)

I'm calling these out so you can sanity-check the cut line:

- **Dice math + combat resolution** (attack rolls, damage, saves)
- **Initiative tracker UI**
- **Fog of war / line-of-sight rendering on the canvas**
- **Spell slot management**
- **Multiple rooms + transitions**
- **Save/load slot UI** (snapshots exist; UI for them doesn't)
- **Voice input** (the Aether Whisper integration is a natural next step)
- **DM override mode** (a Cody-only panel to forcibly inject state diffs)

If any of these belong in MVP, say which and I'll fold the schema/route changes in.

---

# 🛠️ StoryForge — Pass 2: Core Engine + AI Integration

> **Decisions locked, plumbing committed.** Moving from architecture to working code. By end of this pass you have a runnable backend that loads campaign state, validates D&D 5e movement, calls Gemini, sanitizes its output, persists every mutation, and broadcasts diffs over WebSocket. Frontend is the third pass.

---

## 1. Decision Manifest (locked)

| # | Decision | Implementation impact |
|---|---|---|
| 1 | **Gemini Flash** (`gemini-2.0-flash`) | `response_schema=` structured output works; async client; ~800ms p50 latency |
| 2 | **Save on every mutation** | Atomic write (`.tmp` → rename) in `StateManager.commit()`; called by every public mutator |
| 3 | **No auth (trusted LAN)** | FastAPI middleware skipped; CORS opened to `127.0.0.1` + LAN range only |
| 4 | **Konva.js** | Deferred to Pass 3 frontend, but the API contracts in this pass are tuned to Konva's event shape (target Coord, not pixel deltas) |
| 5 | **Exploration-only MVP** | `CombatState` modeled but unused; `phase` defaults to `EXPLORATION`; combat routes return `409 Conflict` if invoked |

These are now baked into every file below — if any drift later, the persistence and validation layers break loudly. That's intentional.

---

## 2. This Pass — Delivery Manifest

```
src/storyforge/
├── core/
│   ├── grid.py              ← 2D math (distance, traversal, bounds)
│   ├── rules.py             ← 5e legality checks (movement, occupancy)
│   ├── state_manager.py     ← the keystone: state + autosave + mutations
│   └── validators.py        ← AI diff sanitizer (the bouncer)
│
├── persistence/
│   └── snapshot.py          ← atomic JSON read/write
│
├── events/
│   └── bus.py               ← in-process async pub/sub
│
├── ai/
│   ├── client.py            ← google-genai async wrapper
│   ├── narrator.py          ← flavor text for deterministic actions
│   ├── interpreter.py       ← freeform text → AINarrationResponse
│   └── prompts/
│       ├── system_dm.md
│       ├── narrate_movement.md
│       ├── interpret_freeform.md
│       └── schemas/
│           └── state_diff.schema.json
│
└── api/
    └── deps.py              ← FastAPI dependency injection wiring
```

---

## 3. How It All Threads Together (read this first)

Before the code, the **mental model** of what a single freeform turn looks like end-to-end. This is the loop you'll be debugging for the next week of development, so it pays to internalize it now.

```
Player types: "I sneak behind the bard and pickpocket his coin pouch"
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│ frontend/js/api.js                                              │
│   POST /api/action/freeform                                     │
│   body: { actor_id: "bray", text: "I sneak behind..." }         │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│ api/routes_action.py :: handle_freeform()                       │
│   ↓ pulls StateManager from deps                                │
│   ↓ calls ai.interpreter.interpret(state, action)               │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│ ai/interpreter.py :: interpret()                                │
│   1. Renders prompts/system_dm.md      (persona/rules)          │
│   2. Renders prompts/interpret_freeform.md with:                │
│      - current GameState JSON                                   │
│      - actor info                                               │
│      - player's text                                            │
│   3. Calls ai.client.generate_structured(prompt, AINarrationResponse)│
│   4. Returns parsed AINarrationResponse                         │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│ Back in routes_action.py:                                       │
│   ↓ response.state_diff exists?                                 │
│   ↓ validators.sanitize(current_state, response.state_diff)     │
│     → returns (safe_diff, rejections)                           │
│   ↓ state.apply_diff(safe_diff)                                 │
│     ↓ which calls state.commit()                                │
│       ↓ which calls snapshot.save() ← DISK WRITE                │
│       ↓ which calls event_bus.publish(diff_message) ← WS PUSH   │
│   ↓ append narrative log entries                                │
│   ↓ return { narrative, revision } to player                    │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
All connected WebSocket clients receive the diff and re-render.
```

Three properties this gives you for free:

| Property | Why it matters |
|---|---|
| **Single mutation point** | `state.commit()` is the only place state hits disk and the bus. No "did I forget to save?" bugs. |
| **AI output is provisional** | Validator stands between Gemini and reality. Hallucinations land as `system` log entries, never as silent state corruption. |
| **Revision counter** | Every mutation bumps `state.revision`. Frontend can detect stale state; tests can assert mutation counts. |

---

## 4. `src/storyforge/persistence/snapshot.py`

The disk layer. **Atomic writes** are non-negotiable — a half-written `state.json` during a crash would wreck a campaign.

```python
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
from storyforge.config import PROJECT_ROOT


STATE_FILENAME = "state.json"
SEED_PATH = PROJECT_ROOT / "data" / "seeds" / "default_campaign.json"


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
    if not SEED_PATH.exists():
        raise FileNotFoundError(
            f"Seed campaign missing at {SEED_PATH}. "
            "Run scripts/bootstrap.fish to provision it."
        )
    with SEED_PATH.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return GameState.model_validate(raw)
```

**Teaching note on `os.replace`:** This is the lowest-friction cross-platform atomic rename in the stdlib. POSIX `rename(2)` is atomic by spec; Windows `MoveFileEx` with `MOVEFILE_REPLACE_EXISTING` matches. `os.replace` picks the right one for you. Never use `shutil.move` here — it's not atomic across filesystems.

---

## 5. `src/storyforge/events/bus.py`

An in-process async pub/sub. **No Redis, no broker** — this is a single-process FastAPI app on a family LAN. asyncio queues are perfect.

```python
"""
In-process publish/subscribe over asyncio.Queue.

Each subscriber gets their own queue. publish() fans out to every queue
without blocking the publisher. Slow subscribers don't block fast ones —
queues are unbounded by default; if you ever need backpressure, swap to
asyncio.Queue(maxsize=N) and decide on a drop policy.

Aether integration point: subscribe a queue here to feed StoryForge
events into the IPCBus.
"""
from __future__ import annotations
import asyncio
from typing import Any


class EventBus:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self._lock = asyncio.Lock()
    
    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        """Register a new subscriber and return its receive queue."""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._subscribers.add(queue)
        return queue
    
    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        self._subscribers.discard(queue)
    
    async def publish(self, message: dict[str, Any]) -> None:
        """Fan out a message to every subscriber. Non-blocking per consumer."""
        async with self._lock:
            targets = list(self._subscribers)
        for q in targets:
            # put_nowait would raise QueueFull on bounded queues; we use
            # unbounded queues so this never blocks.
            q.put_nowait(message)


# Module-level singleton — one bus per process.
event_bus = EventBus()
```

**Why a singleton:** FastAPI lifespan owns the StateManager (per-app instance), but the EventBus is conceptually process-global — it's just a message router. Keeping it as a module-level instance avoids threading it through every Depends() chain.

---

## 6. `src/storyforge/core/grid.py`

The 2D math primitives. Pure functions, no I/O, no state. Easy to test in isolation.

```python
"""
2D grid math primitives.

D&D 5e Player's Handbook uses 5ft per square. Diagonal movement: simple
rule (PHB) is 5ft per diagonal. Variant rule (DMG): alternates 5/10/5/10.
We use the simple rule — Chebyshev distance — to match how "Arcane Quest"
and most digital VTTs behave. Family game, fast turns.
"""
from __future__ import annotations

from storyforge.core.models import Cell, Coord, Room, TerrainKind


FEET_PER_CELL = 5


# ─────────────────────── Cell accessors ───────────────────────

def cell_index(room: Room, coord: Coord) -> int:
    """Convert (x, y) into the row-major index for room.cells."""
    return coord.y * room.width + coord.x


def get_cell(room: Room, coord: Coord) -> Cell:
    """Fetch the Cell at coord. Raises IndexError if out of bounds."""
    if not in_bounds(room, coord):
        raise IndexError(f"Coord {coord} out of bounds for room {room.id}")
    return room.cells[cell_index(room, coord)]


def set_cell(room: Room, coord: Coord, cell: Cell) -> None:
    """In-place cell replacement. Caller responsible for state.commit()."""
    room.cells[cell_index(room, coord)] = cell


def in_bounds(room: Room, coord: Coord) -> bool:
    return 0 <= coord.x < room.width and 0 <= coord.y < room.height


# ─────────────────────── Distance + traversal ───────────────────────

def chebyshev_distance(a: Coord, b: Coord) -> int:
    """
    Number of grid cells between two coords using the simple 5e rule
    (diagonal counts as one square). Multiply by FEET_PER_CELL for feet.
    """
    return max(abs(a.x - b.x), abs(a.y - b.y))


def feet_between(a: Coord, b: Coord) -> int:
    return chebyshev_distance(a, b) * FEET_PER_CELL


def is_traversable(cell: Cell) -> bool:
    """A cell a character can stand in (or pass through)."""
    if cell.terrain in (TerrainKind.WALL,):
        return False
    if cell.occupant_id is not None:
        return False
    return True


def movement_cost_feet(cell: Cell) -> int:
    """How many feet a single cell costs to enter."""
    if cell.terrain == TerrainKind.DIFFICULT:
        return FEET_PER_CELL * 2
    return FEET_PER_CELL


# ─────────────────────── Pathfinding (MVP: line check) ───────────────────────

def line_coords(a: Coord, b: Coord) -> list[Coord]:
    """
    Bresenham-ish line from a to b inclusive. Used for line-of-sight
    and simple "can I walk straight there?" checks in MVP.
    """
    x0, y0, x1, y1 = a.x, a.y, b.x, b.y
    coords: list[Coord] = []
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        coords.append(Coord(x=x0, y=y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy
    return coords


def path_is_clear(room: Room, start: Coord, end: Coord) -> bool:
    """
    True if a straight line from start to end traverses only traversable
    cells (excluding the start, including the end). MVP-grade — replace
    with A* when v0.2 introduces obstacle-rich rooms.
    """
    line = line_coords(start, end)[1:]  # exclude start (self)
    return all(is_traversable(get_cell(room, c)) for c in line)
```

**Teaching note on Chebyshev:** Manhattan distance would forbid diagonal moves; Euclidean would let you move 4.2 cells which doesn't make sense on a grid. Chebyshev treats the 8 surrounding cells as equidistant, which is how the simple 5e PHB rule plays. If you ever switch to DMG variant diagonals, only `chebyshev_distance` needs to change — every caller treats distance as feet.

---

## 7. `src/storyforge/core/rules.py`

D&D 5e legality. Movement only in MVP; the function signature accommodates combat actions for v0.2.

```python
"""
D&D 5e legality checks.

Pure functions: take a snapshot of state + an action, return a Legality
verdict. Never mutates. The state_manager calls these before applying
any structured (grid-click) action.
"""
from __future__ import annotations
from dataclasses import dataclass

from storyforge.core import grid
from storyforge.core.models import (
    CharacterSheet, Coord, GameState, GridAction, Room,
)


@dataclass(frozen=True)
class Legality:
    ok: bool
    reason: str = ""
    
    @classmethod
    def allow(cls) -> "Legality":
        return cls(ok=True)
    
    @classmethod
    def deny(cls, reason: str) -> "Legality":
        return cls(ok=False, reason=reason)


def check_grid_action(
    state: GameState,
    char: CharacterSheet,
    action: GridAction,
) -> Legality:
    """Top-level dispatcher for structured grid actions."""
    room = state.rooms[state.current_room_id]
    
    if not grid.in_bounds(room, action.target):
        return Legality.deny(f"target {action.target} is outside the room")
    
    match action.type:
        case "move":
            return _check_move(room, char, action.target)
        case "attack":
            return Legality.deny("attacks are v0.2; freeform-narrate it for now")
        case "interact":
            return _check_interact(room, char, action.target)
        case _:
            return Legality.deny(f"unknown action type: {action.type}")


def _check_move(room: Room, char: CharacterSheet, target: Coord) -> Legality:
    target_cell = grid.get_cell(room, target)
    
    if not grid.is_traversable(target_cell):
        return Legality.deny(
            f"target cell is {target_cell.terrain.value}"
            + (f" (occupied by {target_cell.occupant_id})"
               if target_cell.occupant_id else "")
        )
    
    feet_needed = grid.feet_between(char.position, target)
    if feet_needed > char.movement_remaining:
        return Legality.deny(
            f"need {feet_needed}ft, only {char.movement_remaining}ft remaining"
        )
    
    if not grid.path_is_clear(room, char.position, target):
        return Legality.deny("path is blocked between start and target")
    
    return Legality.allow()


def _check_interact(room: Room, char: CharacterSheet, target: Coord) -> Legality:
    # Must be adjacent (within 5ft) to interact
    if grid.feet_between(char.position, target) > grid.FEET_PER_CELL:
        return Legality.deny("interact target must be adjacent")
    return Legality.allow()
```

**Teaching note on `@dataclass(frozen=True)`:** Immutable verdict objects mean callers can't mutate a "yes" into a "no" partway through a request. `ok` is the only thing you branch on; `reason` is purely for logs and the player-facing 400 response.

---

## 8. `src/storyforge/core/state_manager.py`

The **keystone**. Owns the live `GameState`, mediates all mutations, autosaves, broadcasts. Every other module talks to state through this class.

```python
"""
The single mutation point for GameState.

Public mutators must call self._commit() at the end so that:
    1. revision increments
    2. state is persisted to disk atomically
    3. an event is published to subscribers

Concurrency model: FastAPI runs handlers in async tasks on a single event
loop. We use an asyncio.Lock to serialize mutations so two near-simultaneous
WebSocket-driven changes can't interleave. Reads do not require the lock —
they snapshot via .model_copy(deep=True) if the caller needs isolation.
"""
from __future__ import annotations
import asyncio
import datetime as dt
from pathlib import Path
from typing import Literal

from storyforge.core import grid, rules
from storyforge.core.models import (
    CharacterSheet, Coord, GameState, GridAction,
    NarrativeEntry, StateDiff, TurnPhase,
)
from storyforge.events.bus import event_bus
from storyforge.persistence import snapshot


# ─────────────────────── Errors ───────────────────────

class StateError(Exception):
    """Generic state-layer error."""


class IllegalActionError(StateError):
    """A grid action failed rules.check_grid_action."""


# ─────────────────────── Manager ───────────────────────

class StateManager:
    def __init__(self, initial: GameState, campaign_dir: Path) -> None:
        self._state = initial
        self._campaign_dir = campaign_dir
        self._lock = asyncio.Lock()
    
    @property
    def current(self) -> GameState:
        """Read-only handle to the live state. Don't mutate this directly."""
        return self._state
    
    def get_character(self, char_id: str) -> CharacterSheet:
        char = self._state.characters.get(char_id)
        if char is None:
            raise StateError(f"unknown character: {char_id}")
        return char
    
    # ─────────────────── Public Mutators ───────────────────
    
    async def apply_grid_action(
        self,
        char: CharacterSheet,
        action: GridAction,
    ) -> dict:
        """Apply a structured grid action. Raises IllegalActionError on failure."""
        async with self._lock:
            verdict = rules.check_grid_action(self._state, char, action)
            if not verdict.ok:
                raise IllegalActionError(verdict.reason)
            
            diff_summary: dict = {}
            
            match action.type:
                case "move":
                    diff_summary = self._do_move(char, action.target)
                case "interact":
                    diff_summary = {"type": "interact", "target": action.target.model_dump()}
                case _:
                    raise IllegalActionError(f"unhandled action: {action.type}")
            
            await self._commit(diff_summary)
            return diff_summary
    
    async def apply_diff(self, diff: StateDiff) -> dict:
        """
        Apply an AI-proposed (and validator-sanitized) diff.
        
        IMPORTANT: this assumes diff has already been through
        validators.sanitize(). Calling this with a raw Gemini response
        bypasses every safety check.
        """
        async with self._lock:
            applied: dict = {"character_updates": {}, "cell_updates": [],
                             "add_inventory": {}, "remove_inventory": {},
                             "phase_change": None}
            
            for char_id, updates in diff.character_updates.items():
                char = self._state.characters.get(char_id)
                if char is None:
                    continue
                for field, value in updates.items():
                    if hasattr(char, field):
                        setattr(char, field, value)
                applied["character_updates"][char_id] = updates
            
            for room_id, coord, new_cell in diff.cell_updates:
                room = self._state.rooms.get(room_id)
                if room is None:
                    continue
                grid.set_cell(room, coord, new_cell)
                applied["cell_updates"].append([room_id, coord.model_dump(),
                                                new_cell.model_dump()])
            
            for char_id, items in diff.add_inventory.items():
                char = self._state.characters.get(char_id)
                if char is None:
                    continue
                char.inventory.extend(items)
                applied["add_inventory"][char_id] = [i.model_dump() for i in items]
            
            for char_id, item_ids in diff.remove_inventory.items():
                char = self._state.characters.get(char_id)
                if char is None:
                    continue
                char.inventory = [i for i in char.inventory if i.id not in item_ids]
                applied["remove_inventory"][char_id] = item_ids
            
            if diff.phase_change is not None:
                self._state.phase = diff.phase_change
                applied["phase_change"] = diff.phase_change.value
            
            await self._commit(applied)
            return applied
    
    async def append_narration(
        self,
        actor_id: str | None,
        kind: Literal["action", "narration", "system"],
        text: str,
    ) -> None:
        """Append a narrative log entry. Does NOT bump revision."""
        async with self._lock:
            self._state.narrative_log.append(
                NarrativeEntry(
                    revision=self._state.revision,
                    actor_id=actor_id,
                    kind=kind,
                    text=text,
                    timestamp=dt.datetime.now(dt.timezone.utc).isoformat(),
                )
            )
            # Narration is part of state, so persist — but skip event bus
            # to avoid double-broadcast (the caller will publish the diff).
            snapshot.save(self._campaign_dir, self._state)
    
    # ─────────────────── Internal Helpers ───────────────────
    
    def _do_move(self, char: CharacterSheet, target: Coord) -> dict:
        """Pure mutation: vacate old cell, occupy new, decrement movement."""
        room = self._state.rooms[self._state.current_room_id]
        feet_spent = grid.feet_between(char.position, target)
        
        # Vacate old cell
        old_cell = grid.get_cell(room, char.position)
        old_cell.occupant_id = None
        
        # Occupy new cell
        new_cell = grid.get_cell(room, target)
        new_cell.occupant_id = char.id
        
        # Update character
        previous = char.position
        char.position = target
        char.movement_remaining -= feet_spent
        
        return {
            "type": "move",
            "actor_id": char.id,
            "from": previous.model_dump(),
            "to": target.model_dump(),
            "feet_spent": feet_spent,
            "movement_remaining": char.movement_remaining,
        }
    
    async def _commit(self, diff_summary: dict) -> None:
        """
        Single point of write-out + broadcast. ALWAYS called inside the lock.
        
        Order matters:
            1. Bump revision (so subscribers see the new number)
            2. Persist to disk (so crashes after publish still recover)
            3. Publish to bus (subscribers fire after disk is durable)
        """
        self._state.revision += 1
        snapshot.save(self._campaign_dir, self._state)
        await event_bus.publish({
            "type": "state_diff",
            "revision": self._state.revision,
            "diff": diff_summary,
        })
```

**Teaching note on the commit order:** Disk first, then broadcast. Why? If the process crashes between persist and broadcast, the next boot still has the new state and clients will sync on reconnect. The opposite order — broadcast first — risks clients seeing a state that doesn't survive a restart, producing a phantom "did that even happen?" bug. Boring but important.

---

## 9. `src/storyforge/core/validators.py`

The **bouncer**. Gemini will absolutely try to give characters +50 HP, conjure items, and teleport across rooms. This module says no.

```python
"""
Sanitize AI-proposed StateDiffs before they touch live state.

Philosophy: REJECT, don't repair. If the AI proposes something illegal,
drop it and log a system message. Repairing (clamping HP to max,
rounding teleports to nearest legal cell) creates magic the AI then
learns to exploit. Hard NO is teachable; soft maybe is gameable.

Returns a tuple of (sanitized_diff, rejections) where rejections is a
list of human-readable strings to append to the narrative log.
"""
from __future__ import annotations
from copy import deepcopy

from storyforge.core import grid
from storyforge.core.models import (
    Cell, Coord, GameState, InventoryItem, StateDiff, TurnPhase,
)


# Fields the AI is permitted to mutate on a CharacterSheet.
_ALLOWED_CHAR_FIELDS = {
    "hp_current",
    "conditions",
    "movement_remaining",
    "position",          # only via cell_updates, not direct write; see below
}

# Max delta the AI may apply to HP in a single turn without an explicit
# combat phase. Prevents "you find a healing fountain" giving +∞ HP.
_MAX_HP_DELTA_PER_TURN = 8


def sanitize(
    state: GameState,
    proposed: StateDiff,
) -> tuple[StateDiff, list[str]]:
    """Return (safe_diff, rejection_messages). The safe_diff is always
    a fresh StateDiff — never the input object."""
    rejections: list[str] = []
    safe = StateDiff()
    
    safe.character_updates = _filter_char_updates(
        state, proposed.character_updates, rejections,
    )
    safe.cell_updates = _filter_cell_updates(
        state, proposed.cell_updates, rejections,
    )
    safe.add_inventory = _filter_add_inventory(
        state, proposed.add_inventory, rejections,
    )
    safe.remove_inventory = _filter_remove_inventory(
        state, proposed.remove_inventory, rejections,
    )
    safe.phase_change = _filter_phase_change(
        state, proposed.phase_change, rejections,
    )
    
    return safe, rejections


# ─────────────────────── Per-section filters ───────────────────────

def _filter_char_updates(
    state: GameState,
    updates: dict[str, dict],
    rejections: list[str],
) -> dict[str, dict]:
    safe: dict[str, dict] = {}
    for char_id, fields in updates.items():
        if char_id not in state.characters:
            rejections.append(f"unknown character '{char_id}'")
            continue
        char = state.characters[char_id]
        safe_fields: dict = {}
        for field, value in fields.items():
            if field not in _ALLOWED_CHAR_FIELDS:
                rejections.append(
                    f"AI tried to modify forbidden field '{field}' on {char_id}"
                )
                continue
            
            # Field-specific guards
            if field == "hp_current":
                if not isinstance(value, int):
                    rejections.append(f"hp_current must be int, got {type(value).__name__}")
                    continue
                if value < 0:
                    rejections.append(f"hp_current cannot be negative ({char_id})")
                    continue
                if value > char.hp_max:
                    rejections.append(
                        f"hp_current {value} > max {char.hp_max} for {char_id}"
                    )
                    continue
                if abs(value - char.hp_current) > _MAX_HP_DELTA_PER_TURN:
                    rejections.append(
                        f"HP delta too large for {char_id}: "
                        f"{char.hp_current} → {value}"
                    )
                    continue
            
            if field == "movement_remaining":
                if not isinstance(value, int) or value < 0:
                    rejections.append(f"movement_remaining invalid for {char_id}")
                    continue
                if value > char.speed:
                    rejections.append(
                        f"movement_remaining {value} > speed {char.speed} for {char_id}"
                    )
                    continue
            
            if field == "conditions":
                if not isinstance(value, list):
                    rejections.append(f"conditions must be list for {char_id}")
                    continue
            
            if field == "position":
                # Disallow direct position writes — must go through cell_updates
                # so the cell occupancy is also updated.
                rejections.append(
                    f"position must be set via cell_updates, not character_updates ({char_id})"
                )
                continue
            
            safe_fields[field] = value
        
        if safe_fields:
            safe[char_id] = safe_fields
    return safe


def _filter_cell_updates(
    state: GameState,
    updates: list[tuple[str, Coord, Cell]],
    rejections: list[str],
) -> list[tuple[str, Coord, Cell]]:
    safe: list[tuple[str, Coord, Cell]] = []
    current_room_id = state.current_room_id
    
    for room_id, coord, new_cell in updates:
        if room_id != current_room_id:
            rejections.append(
                f"AI tried to modify room '{room_id}' but party is in '{current_room_id}'"
            )
            continue
        
        room = state.rooms.get(room_id)
        if room is None:
            rejections.append(f"unknown room '{room_id}'")
            continue
        
        if not grid.in_bounds(room, coord):
            rejections.append(f"cell {coord} out of bounds in {room_id}")
            continue
        
        safe.append((room_id, coord, new_cell))
    return safe


def _filter_add_inventory(
    state: GameState,
    additions: dict[str, list[InventoryItem]],
    rejections: list[str],
) -> dict[str, list[InventoryItem]]:
    safe: dict[str, list[InventoryItem]] = {}
    for char_id, items in additions.items():
        if char_id not in state.characters:
            rejections.append(f"unknown character '{char_id}' in inventory add")
            continue
        # For MVP, allow inventory additions but cap quantity to prevent
        # "AI gives you 999 healing potions"
        safe_items = []
        for item in items:
            if item.quantity > 10:
                rejections.append(
                    f"refused inventory add: quantity {item.quantity} > 10 ({item.name})"
                )
                continue
            safe_items.append(item)
        if safe_items:
            safe[char_id] = safe_items
    return safe


def _filter_remove_inventory(
    state: GameState,
    removals: dict[str, list[str]],
    rejections: list[str],
) -> dict[str, list[str]]:
    safe: dict[str, list[str]] = {}
    for char_id, item_ids in removals.items():
        char = state.characters.get(char_id)
        if char is None:
            rejections.append(f"unknown character '{char_id}' in inventory remove")
            continue
        owned_ids = {i.id for i in char.inventory}
        valid = [iid for iid in item_ids if iid in owned_ids]
        invalid = [iid for iid in item_ids if iid not in owned_ids]
        for iid in invalid:
            rejections.append(f"{char_id} does not own item '{iid}'")
        if valid:
            safe[char_id] = valid
    return safe


def _filter_phase_change(
    state: GameState,
    proposed: TurnPhase | None,
    rejections: list[str],
) -> TurnPhase | None:
    if proposed is None:
        return None
    # MVP: AI can suggest moving to COMBAT, but we reject — combat is v0.2.
    if proposed == TurnPhase.COMBAT:
        rejections.append("phase change to combat is deferred to v0.2")
        return None
    return proposed
```

**Teaching note on the "reject, don't repair" stance:** This is the same principle as input validation in any security-sensitive system. If you silently clamp `hp_current=999` to `hp_max`, Gemini's next prompt will see `hp_current=hp_max` and conclude its proposal worked. It'll keep proposing absurdities. If you reject and log "HP delta too large," Gemini sees in subsequent turns that the field is unchanged and recalibrates. Loud failures are training signal.

---

## 10. `src/storyforge/ai/client.py`

The thin wrapper around `google-genai`. Async, structured-output-capable, retry-aware.

```python
"""
Async Gemini client wrapper.

Wraps google-genai with:
    - Async generation via the .aio namespace
    - Structured output via response_schema
    - Simple exponential backoff on transient errors
    - Prompt template loading from disk

The rest of the codebase imports `client` from here and never touches
google-genai directly.
"""
from __future__ import annotations
import asyncio
from pathlib import Path
from typing import TypeVar

from google import genai
from google.genai import types as genai_types
from pydantic import BaseModel

from storyforge.config import settings


T = TypeVar("T", bound=BaseModel)


class GeminiClient:
    def __init__(self, api_key: str, model: str) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model
    
    async def generate_text(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.7,
    ) -> str:
        """Plain text generation. Used by narrator.flavor_for()."""
        config = genai_types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_instruction,
        )
        response = await self._retry(
            lambda: self._client.aio.models.generate_content(
                model=self._model, contents=prompt, config=config,
            )
        )
        return (response.text or "").strip()
    
    async def generate_structured(
        self,
        prompt: str,
        response_model: type[T],
        system_instruction: str | None = None,
        temperature: float = 0.4,
    ) -> T:
        """JSON-structured generation against a Pydantic schema."""
        config = genai_types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=response_model,
        )
        response = await self._retry(
            lambda: self._client.aio.models.generate_content(
                model=self._model, contents=prompt, config=config,
            )
        )
        # The SDK can populate .parsed when response_schema is a Pydantic model,
        # but we validate ourselves for defense in depth.
        raw = response.text or "{}"
        return response_model.model_validate_json(raw)
    
    async def _retry(self, call, *, max_attempts: int = 3) -> object:
        """Exponential backoff for transient API errors."""
        delay = 0.5
        last_exc: Exception | None = None
        for attempt in range(max_attempts):
            try:
                return await call()
            except Exception as exc:  # google-genai raises a tree of exception types
                last_exc = exc
                if attempt == max_attempts - 1:
                    break
                await asyncio.sleep(delay)
                delay *= 2
        raise RuntimeError(f"Gemini call failed after {max_attempts} attempts") from last_exc


# ─────────────────────── Prompt template loader ───────────────────────

def load_prompt(name: str) -> str:
    """Read a prompt file from src/storyforge/ai/prompts/<name>.md."""
    path = settings.prompts_path / name
    if not path.exists():
        raise FileNotFoundError(f"prompt template not found: {path}")
    return path.read_text(encoding="utf-8")


# Module-level singleton — one client per process.
client = GeminiClient(
    api_key=settings.gemini_api_key,
    model=settings.gemini_model,
)
```

**Teaching note on the retry shape:** Gemini Flash p99 latency spikes occasionally — usually transient. Three attempts with 0.5s → 1s → 2s backoff caps your worst-case at ~4s before a hard failure. Anything beyond that, you want the player to see an error and resend rather than wait silently.

---

## 11. Prompt Templates

These are **on-disk Markdown** so you can iterate on them without touching Python. Treat them like source code: they belong in Git, they get code-reviewed, they get tested.

### 11.1 `src/storyforge/ai/prompts/system_dm.md`

This is the AI's *persona contract*. Loaded as `system_instruction` on every call.

```markdown
# StoryForge Dungeon Master — System Prompt

You are the Dungeon Master for a family D&D 5e campaign. The players are:
Cody, Dee, Nate, and Bray. Their characters are Kael (Fighter), Lyra
(Wizard), Thorne (Ranger), and Whisper (Rogue).

## Your Role

You produce two outputs per turn:

1. **Narrative text** — descriptive, sensory, second-person ("you smell pipe
   smoke," "the bard stops mid-chord"). Match the tone of classic
   text-adventure D&D: vivid but tight. Aim for 2-5 sentences per response,
   not paragraphs.

2. **A state diff** — a JSON object describing what changed mechanically.
   This is OPTIONAL. If the player's action does not change game state
   (looking around, asking the bard a question), set `state_diff` to null.

## The Iron Rules

You are NOT the source of truth. The Python engine validates every diff
you propose. If you propose something illegal, your diff is silently
dropped and a system note is logged. The player still sees your narrative
but the world does not change.

Things you may NEVER do:
- Give a character HP above their `hp_max`
- Award more than 8 HP of healing in a single turn outside combat
- Add inventory items with quantity > 10
- Modify rooms the party is not currently in
- Set positions directly — use cell_updates so occupancy stays consistent
- Modify character `hp_max`, `armor_class`, `abilities`, or `level`
- Initiate combat (phase_change to "combat") — combat is not yet implemented

Things you SHOULD do:
- Describe failure as vividly as success
- Make NPCs have opinions, accents, agendas
- Let small actions have small consequences ("the bard glances at you")
- Respect player creativity — if they want to climb the chandelier, let
  them, even if it's not optimal
- Keep tone family-friendly: violence is implied, never graphic; no
  romance content; no real-world political references

## Tone Reference

Closer to *The Hobbit* than *Game of Thrones*. Closer to *Critical Role*'s
warmer moments than its grimdark ones. Closer to a Pixar film than a
Cormac McCarthy novel.
```

### 11.2 `src/storyforge/ai/prompts/interpret_freeform.md`

The heavy-lifter. Loaded once per freeform turn and templated with current state.

```markdown
# Freeform Action Interpretation

A player has typed a freeform action. Your job is to:

1. Decide what happens narratively.
2. Decide what (if anything) changes mechanically.
3. Return both as a single JSON response matching the AINarrationResponse schema.

## Current Game State

```json
{game_state_json}
```

## Acting Character

- Character ID: `{actor_id}`
- Name: {actor_name}
- Class: {actor_class}
- Current position: {actor_position}
- HP: {actor_hp_current} / {actor_hp_max}
- Conditions: {actor_conditions}

## Current Room

- Room: {current_room_name}
- Description: {current_room_description}
- Dimensions: {room_width} × {room_height}

## Player's Action

> "{player_text}"

## Your Response

Return a JSON object with this shape:

```json
{{
  "narrative": "2-5 sentences of vivid description.",
  "state_diff": {{
    "character_updates": {{ "<char_id>": {{ "<field>": <new_value> }} }},
    "cell_updates": [["<room_id>", {{"x": <int>, "y": <int>}}, {{"terrain": "...", "occupant_id": null}}]],
    "add_inventory": {{ "<char_id>": [{{"id": "...", "name": "...", "quantity": 1, "equipped": false}}] }},
    "remove_inventory": {{ "<char_id>": ["<item_id>"] }},
    "phase_change": null
  }}
}}
```

If nothing changes mechanically, set `state_diff` to `null`:

```json
{{ "narrative": "...", "state_diff": null }}
```

## Reasoning Hints

- If the action is a question ("What does the room smell like?"), narrative only, no diff.
- If the action moves the character, propose `character_updates.{actor_id}.position`... wait, NO — positions go through `cell_updates`. Vacate the old cell (set occupant_id to null) AND occupy the new cell (set occupant_id to "{actor_id}"). Both updates in the cell_updates array.
- If the action acquires an item, use `add_inventory`. Generate a stable `id` like "coin_pouch_01".
- If the action damages the character, lower `hp_current` in `character_updates`.
- Never invent items the world hasn't established. The bard's coin pouch is fine. A laser rifle is not.
```

### 11.3 `src/storyforge/ai/prompts/narrate_movement.md`

Flavor text for **already-validated** structured moves. The Python referee has done the math; Gemini only writes the prose.

```markdown
# Movement Narration

A character has moved across the grid. The mechanics are already resolved
by the Python engine — you only describe the action vividly.

## Context

- Character: {actor_name} ({actor_class})
- Moved from cell ({from_x}, {from_y}) to ({to_x}, {to_y})
- Distance: {feet_spent}ft
- Movement remaining this turn: {movement_remaining}ft
- Room: {current_room_name} — {current_room_description}

## Your Task

Return a single sentence (max two) describing the movement. No JSON, no
metadata — just the sentence. Examples:

- "Kael strides across the tavern floor, boots scuffing the sawdust."
- "Whisper slips along the shadowed wall, three paces closer to the bar."
- "Lyra pads cautiously toward the hearth, her robe trailing."

Match the action: a Fighter strides, a Rogue slips, a Wizard glides. Keep
it tight and sensory.
```

### 11.4 `src/storyforge/ai/prompts/schemas/state_diff.schema.json`

Generated from the Pydantic model. Commit the generated artifact so reviewers can diff it. Regenerate via a make target or pre-commit hook:

```bash
uv run python -c "
import json
from storyforge.core.models import AINarrationResponse
print(json.dumps(AINarrationResponse.model_json_schema(), indent=2))
" > src/storyforge/ai/prompts/schemas/state_diff.schema.json
```

You don't need to hand-write this file — it's a build artifact. But check it into Git so prompt-engineering work doesn't require running Python to inspect what the AI is being asked for.

---

## 12. `src/storyforge/ai/narrator.py`

Used by **structured** routes. The math is already done; Gemini only narrates.

```python
"""
Flavor-text generator for deterministic, already-resolved actions.

The Python engine has moved the character, decremented movement, applied
all mechanics. We hand Gemini just enough context to produce one or two
sentences of color.
"""
from __future__ import annotations

from storyforge.ai.client import client, load_prompt
from storyforge.core.models import GameState, GridAction


_SYSTEM = load_prompt("system_dm.md")
_TEMPLATE = load_prompt("narrate_movement.md")


async def flavor_for(
    state: GameState,
    action: GridAction,
    diff_summary: dict,
) -> str:
    """Generate one-to-two sentences describing a completed grid action."""
    char = state.characters[action.actor_id]
    room = state.rooms[state.current_room_id]
    
    rendered = _TEMPLATE.format(
        actor_name=char.name,
        actor_class=char.char_class,
        from_x=diff_summary["from"]["x"],
        from_y=diff_summary["from"]["y"],
        to_x=diff_summary["to"]["x"],
        to_y=diff_summary["to"]["y"],
        feet_spent=diff_summary["feet_spent"],
        movement_remaining=diff_summary["movement_remaining"],
        current_room_name=room.name,
        current_room_description=room.description,
    )
    
    return await client.generate_text(
        prompt=rendered,
        system_instruction=_SYSTEM,
        temperature=0.8,  # higher temp for flavor
    )
```

---

## 13. `src/storyforge/ai/interpreter.py`

The **freeform** entrypoint. Gemini gets the full state, returns narrative + proposed diff.

```python
"""
Freeform action interpreter.

Renders interpret_freeform.md with current state + player text, calls
Gemini for structured output, returns the parsed AINarrationResponse.
The CALLER must run validators.sanitize() on the returned state_diff
before applying it. This module does not sanitize — separation of
concerns: interpret here, sanitize in core.
"""
from __future__ import annotations

from storyforge.ai.client import client, load_prompt
from storyforge.core.models import (
    AINarrationResponse, FreeformAction, GameState,
)


_SYSTEM = load_prompt("system_dm.md")
_TEMPLATE = load_prompt("interpret_freeform.md")


async def interpret(
    game_state: GameState,
    action: FreeformAction,
) -> AINarrationResponse:
    """Ask Gemini to interpret a freeform action and propose a state diff."""
    actor = game_state.characters[action.actor_id]
    room = game_state.rooms[game_state.current_room_id]
    
    rendered = _TEMPLATE.format(
        game_state_json=game_state.model_dump_json(indent=2),
        actor_id=action.actor_id,
        actor_name=actor.name,
        actor_class=actor.char_class,
        actor_position=f"({actor.position.x}, {actor.position.y})",
        actor_hp_current=actor.hp_current,
        actor_hp_max=actor.hp_max,
        actor_conditions=", ".join(actor.conditions) or "none",
        current_room_name=room.name,
        current_room_description=room.description,
        room_width=room.width,
        room_height=room.height,
        player_text=action.text,
    )
    
    return await client.generate_structured(
        prompt=rendered,
        response_model=AINarrationResponse,
        system_instruction=_SYSTEM,
        temperature=0.6,
    )
```

---

## 14. `src/storyforge/api/deps.py`

FastAPI dependency injection. One-liner functions that pull the StateManager out of `app.state` for handlers to consume.

```python
"""FastAPI dependency providers."""
from __future__ import annotations
from fastapi import Request

from storyforge.core.state_manager import StateManager


def get_state_manager(request: Request) -> StateManager:
    """Pull the StateManager that lifespan stashed on app.state."""
    return request.app.state.state_manager
```

And the previously sketched `routes_action.py` needs a small update to use the async mutators correctly:

```python
# Inside handle_grid:
diff = await state.apply_grid_action(char, action)   # was: state.apply_grid_action

# Inside handle_freeform, after sanitize:
await state.apply_diff(safe_diff)
await state.append_narration(actor_id=action.actor_id, kind="action", text=action.text)
await state.append_narration(actor_id=None, kind="narration", text=response.narrative)
```

Also update `main.py`'s lifespan to pass the campaign_dir into StateManager:

```python
state = snapshot.load(settings.campaign_path) or snapshot.load_seed()
app.state.state_manager = StateManager(state, settings.campaign_path)
```

---

## 15. Verification Checklist (run this end-of-pass)

Five checks. Each one isolates a failure mode so when something breaks tomorrow you know which layer to look at.

```fish
# ─── 1. Schema integrity ───────────────────────────────────────
# Confirms Pydantic models load cleanly and the seed validates.
uv run python -c "
from storyforge.persistence.snapshot import load_seed
s = load_seed()
print(f'✓ seed loaded: campaign={s.campaign_id}, chars={len(s.characters)}')
"

# ─── 2. Persistence roundtrip ──────────────────────────────────
# Save, load, compare. Catches schema-vs-disk drift.
uv run python -c "
from pathlib import Path
from storyforge.persistence.snapshot import load_seed, save, load
import tempfile

with tempfile.TemporaryDirectory() as d:
    s1 = load_seed()
    save(Path(d), s1)
    s2 = load(Path(d))
    assert s1.model_dump() == s2.model_dump(), 'roundtrip mismatch!'
    print('✓ persistence roundtrip clean')
"

# ─── 3. Rules engine ───────────────────────────────────────────
uv run python -c "
from storyforge.persistence.snapshot import load_seed
from storyforge.core import rules
from storyforge.core.models import GridAction, Coord

s = load_seed()
cody = s.characters['cody']
# Try a legal 1-cell move
action = GridAction(type='move', actor_id='cody', target=Coord(x=cody.position.x+1, y=cody.position.y))
v = rules.check_grid_action(s, cody, action)
print(f'✓ legal move verdict: ok={v.ok}, reason={v.reason!r}')
"

# ─── 4. Gemini connectivity (requires .env populated) ──────────
uv run python -c "
import asyncio
from storyforge.ai.client import client

async def go():
    out = await client.generate_text('Reply with exactly: OK')
    print(f'✓ gemini reachable, response: {out!r}')

asyncio.run(go())
"

# ─── 5. Full server boot ───────────────────────────────────────
./scripts/dev.fish
# In another shell:
#   curl http://127.0.0.1:8765/healthz
#   curl http://127.0.0.1:8765/api/state | head -40
```

If all five pass, the backend is structurally sound.

---

## 16. Outstanding Wiring (intentional gaps)

A few thin connector files I haven't written but you'll need before the server boots cleanly. They're trivial — call them out so you don't hit `ImportError` and assume something's wrong:

| File | Purpose | LOC estimate |
|---|---|---|
| `src/storyforge/api/routes_state.py` | GET handlers for state, character, room | ~25 |
| `src/storyforge/api/__init__.py`, `core/__init__.py`, etc. | Empty package markers | 0 |
| `tests/test_state_manager.py` | Move + diff + persistence tests | ~80 |
| `data/seeds/default_campaign.json` | Full 10×8 tavern, four characters | ~200 (data, not code) |

I'll fold all of these into Pass 3 alongside the Konva frontend. Or if you want any of them ahead of Pass 3, say which and I'll splice it in.

---

## 17. What Pass 3 Delivers

Frontend + the connector files above. Specifically:

```
frontend/
├── index.html              ← split-pane layout (canvas | narrative log)
├── css/styles.css          ← dark theme, matches Aether palette
└── js/
    ├── main.js             ← bootstrap, WS connection, state sync
    ├── canvas.js           ← Konva stage, grid layer, token layer, click handlers
    ├── api.js              ← fetch wrappers for /api/action/{grid,freeform}
    └── log.js              ← narrative scroll feed with autoscroll
```

Plus the seed campaign JSON (a 10×8 tavern with the four PCs pre-placed) and a `routes_state.py` so the frontend can do an initial sync on page load.

---

# 🎮 StoryForge — Pass 3: 10-Foot UI Frontend + Xbox Controllers + Backend Closure

> **Final MVP pass.** This delivers a couch-playable, controller-driven, parchment-themed VTT rendered at 4K, plus the remaining backend connector files so the whole thing boots clean. By end of this response: launch the dev server, plug in four Series X controllers, and play.

---

## 1. Pass 3 Manifest

| Layer | File | Purpose | LOC |
|---|---|---|---|
| Backend | `api/routes_state.py` | GET endpoints (state, character, room) | ~40 |
| Backend | `data/seeds/default_campaign.json` | 10×8 tavern, 4 PCs pre-placed | ~250 (data) |
| Backend | `__init__.py` markers | Package wiring | 0 |
| Frontend | `index.html` | Split-pane TV layout | ~100 |
| Frontend | `css/styles.css` | 10-foot UI base + layout | ~280 |
| Frontend | `css/parchment.css` | Paper texture themes | ~110 |
| Frontend | `css/ink-effects.css` | Gradient/glitter ink | ~90 |
| Frontend | `js/main.js` | Bootstrap, WS sync, app state | ~180 |
| Frontend | `js/api.js` | REST + freeform action wrappers | ~50 |
| Frontend | `js/canvas.js` | Konva stage, HiDPI, grid, tokens | ~290 |
| Frontend | `js/gamepad.js` | Xbox controller polling + dispatch | ~230 |
| Frontend | `js/log.js` | Narrative feed + TTS hook | ~100 |
| Frontend | `js/audio.js` | Web Audio engine, generated SFX | ~140 |
| Frontend | `js/characters.js` | Portrait strip + active-player UI | ~160 |

---

## 2. Architectural Decisions (Pass 3 Lock-In)

Five frontend-specific axioms before any code. If any of these are wrong, push back now.

| # | Axiom | Consequence |
|---|---|---|
| **F1** | **Konva runs at device pixel ratio, layout at CSS pixels.** | Stage internal dimensions = `cssWidth * devicePixelRatio`. Tokens stay crisp at 4K (DPR ≈ 1.5–2.0 on a TV after browser scaling). |
| **F2** | **Gamepad index 0–3 = character slot 0–3.** No "claim" ceremony. | Controller 1 → Cody/Kael, Controller 2 → Dee/Lyra, etc. Pick up any controller, press A, your character acts. |
| **F3** | **One global "active character" — hot seat.** | LB/RB cycle. Any controller can override. Grid cursor and action buttons always apply to the active character only. |
| **F4** | **Freeform text input requires a hardware keyboard.** | On-screen keyboards over a Gamepad API are a 400-LOC rabbit hole. Y opens the modal, you type on the wireless keyboard. |
| **F5** | **Audio is procedural for MVP — Web Audio oscillators, no asset files.** | Click, confirm, deny, narration-chime all synthesized. Drop in WAV/OGG later by swapping one factory function. |

---

## 3. Backend Gap-Closure

Three files to wire before the frontend has anything to talk to.

### 3.1 `src/storyforge/api/routes_state.py`

```python
"""Read-only state endpoints. Frontend uses /api/state on boot."""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException

from storyforge.api.deps import get_state_manager
from storyforge.core.state_manager import StateManager, StateError


router = APIRouter(prefix="/api", tags=["state"])


@router.get("/state")
async def get_full_state(state: StateManager = Depends(get_state_manager)) -> dict:
    """Initial sync payload. Frontend calls this once on page load."""
    return state.current.model_dump(mode="json")


@router.get("/character/{char_id}")
async def get_character(
    char_id: str,
    state: StateManager = Depends(get_state_manager),
) -> dict:
    try:
        return state.get_character(char_id).model_dump(mode="json")
    except StateError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/room/{room_id}")
async def get_room(
    room_id: str,
    state: StateManager = Depends(get_state_manager),
) -> dict:
    room = state.current.rooms.get(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail=f"unknown room: {room_id}")
    return room.model_dump(mode="json")


@router.get("/revision")
async def get_revision(state: StateManager = Depends(get_state_manager)) -> dict:
    """Lightweight poll endpoint — frontend can compare against its cached
    revision number before deciding to re-sync."""
    return {"revision": state.current.revision}
```

### 3.2 `__init__.py` Markers

All empty. Just create them so Python recognizes the packages.

```fish
# Run from project root
touch src/storyforge/__init__.py
touch src/storyforge/api/__init__.py
touch src/storyforge/core/__init__.py
touch src/storyforge/ai/__init__.py
touch src/storyforge/persistence/__init__.py
touch src/storyforge/events/__init__.py
```

### 3.3 `data/seeds/default_campaign.json`

The starter campaign: the **Crooked Tankard tavern**, 10×8 grid, walls around the perimeter, a hearth, two tables, four PCs lined up at the southern side ready to explore. Save as-is.

```json
{
  "campaign_id": "family_campaign_01",
  "current_room_id": "tavern_01",
  "phase": "exploration",
  "revision": 0,
  "narrative_log": [
    {
      "revision": 0,
      "actor_id": null,
      "kind": "narration",
      "text": "The Crooked Tankard's door swings shut behind you with a groan of warped oak. Pipe smoke hangs in the rafters, and a bard by the hearth tunes a battered lute. Four faces turn briefly toward you, then back to their cups.",
      "timestamp": "2026-01-01T00:00:00+00:00"
    }
  ],
  "characters": {
    "cody": {
      "id": "cody", "name": "Kael", "player": "Cody",
      "char_class": "Fighter", "level": 1,
      "hp_current": 12, "hp_max": 12, "armor_class": 16, "speed": 30,
      "abilities": {"STR": 16, "DEX": 12, "CON": 14, "INT": 10, "WIS": 12, "CHA": 8},
      "proficiency_bonus": 2,
      "inventory": [
        {"id": "longsword_01", "name": "Longsword", "quantity": 1, "equipped": true, "notes": null},
        {"id": "shield_01", "name": "Shield", "quantity": 1, "equipped": true, "notes": null}
      ],
      "position": {"x": 3, "y": 6},
      "movement_remaining": 30,
      "conditions": []
    },
    "dee": {
      "id": "dee", "name": "Lyra", "player": "Dee",
      "char_class": "Wizard", "level": 1,
      "hp_current": 7, "hp_max": 7, "armor_class": 11, "speed": 30,
      "abilities": {"STR": 8, "DEX": 14, "CON": 12, "INT": 16, "WIS": 13, "CHA": 10},
      "proficiency_bonus": 2,
      "inventory": [
        {"id": "quarterstaff_01", "name": "Quarterstaff", "quantity": 1, "equipped": true, "notes": null},
        {"id": "spellbook_01", "name": "Spellbook", "quantity": 1, "equipped": false, "notes": "bound in violet leather"}
      ],
      "position": {"x": 4, "y": 6},
      "movement_remaining": 30,
      "conditions": []
    },
    "nate": {
      "id": "nate", "name": "Thorne", "player": "Nate",
      "char_class": "Ranger", "level": 1,
      "hp_current": 11, "hp_max": 11, "armor_class": 14, "speed": 30,
      "abilities": {"STR": 13, "DEX": 16, "CON": 14, "INT": 10, "WIS": 14, "CHA": 9},
      "proficiency_bonus": 2,
      "inventory": [
        {"id": "longbow_01", "name": "Longbow", "quantity": 1, "equipped": true, "notes": null},
        {"id": "arrows_20", "name": "Arrows", "quantity": 20, "equipped": false, "notes": null}
      ],
      "position": {"x": 5, "y": 6},
      "movement_remaining": 30,
      "conditions": []
    },
    "bray": {
      "id": "bray", "name": "Whisper", "player": "Bray",
      "char_class": "Rogue", "level": 1,
      "hp_current": 9, "hp_max": 9, "armor_class": 13, "speed": 30,
      "abilities": {"STR": 10, "DEX": 16, "CON": 12, "INT": 12, "WIS": 13, "CHA": 14},
      "proficiency_bonus": 2,
      "inventory": [
        {"id": "shortsword_01", "name": "Shortsword", "quantity": 1, "equipped": true, "notes": null},
        {"id": "thieves_tools_01", "name": "Thieves' Tools", "quantity": 1, "equipped": false, "notes": null}
      ],
      "position": {"x": 6, "y": 6},
      "movement_remaining": 30,
      "conditions": []
    }
  },
  "rooms": {
    "tavern_01": {
      "id": "tavern_01",
      "name": "The Crooked Tankard",
      "width": 10,
      "height": 8,
      "description": "A cramped common room with low oak beams smoke-stained nearly black. A stone hearth dominates the back wall. Two round tables sit askew between you and the bar. A bard tunes a lute in the far corner.",
      "cells": [
        {"terrain":"wall","occupant_id":null},{"terrain":"wall","occupant_id":null},{"terrain":"wall","occupant_id":null},{"terrain":"wall","occupant_id":null},{"terrain":"wall","occupant_id":null},{"terrain":"wall","occupant_id":null},{"terrain":"wall","occupant_id":null},{"terrain":"wall","occupant_id":null},{"terrain":"wall","occupant_id":null},{"terrain":"wall","occupant_id":null},
        {"terrain":"wall","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"hazard","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":"bard"},{"terrain":"floor","occupant_id":null},{"terrain":"wall","occupant_id":null},
        {"terrain":"wall","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"wall","occupant_id":null},
        {"terrain":"wall","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"difficult","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"difficult","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"wall","occupant_id":null},
        {"terrain":"wall","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"difficult","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"difficult","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"wall","occupant_id":null},
        {"terrain":"wall","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"wall","occupant_id":null},
        {"terrain":"wall","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":"cody"},{"terrain":"floor","occupant_id":"dee"},{"terrain":"floor","occupant_id":"nate"},{"terrain":"floor","occupant_id":"bray"},{"terrain":"floor","occupant_id":null},{"terrain":"floor","occupant_id":null},{"terrain":"wall","occupant_id":null},
        {"terrain":"wall","occupant_id":null},{"terrain":"wall","occupant_id":null},{"terrain":"wall","occupant_id":null},{"terrain":"wall","occupant_id":null},{"terrain":"wall","occupant_id":null},{"terrain":"door","occupant_id":null},{"terrain":"wall","occupant_id":null},{"terrain":"wall","occupant_id":null},{"terrain":"wall","occupant_id":null},{"terrain":"wall","occupant_id":null}
      ]
    }
  },
  "combat": null
}
```

**Teaching note on the cell layout:** Row-major, so `cells[y * width + x]`. Walls form the perimeter; a **hazard** cell at `(3,1)` is the hearth fire; two **difficult terrain** clusters at `(2-7, 3-4)` are the tables and chairs (slow to push through). The southern wall has a single **door** at `(5,7)` — the way out into the rest of the dungeon.

---

## 4. Frontend Architecture Briefing

### 4.1 Screen Layout (1920×1080 reference; scales 1:1 to 4K)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ╔═══╗ ╔═══╗ ╔═══╗ ╔═══╗                          ⌨ KBD  🎮 1 2 3 4    │  ← 8% (top bar)
│  ║ K ║ ║ L ║ ║ T ║ ║ W ║   ← active glows gold                          │
│  ╚═══╝ ╚═══╝ ╚═══╝ ╚═══╝                                                │
├──────────────────────────────────────────┬──────────────────────────────┤
│                                          │                              │
│                                          │  ▓▓▓ NARRATIVE LOG ▓▓▓       │
│                                          │                              │
│           KONVA CANVAS                   │  Kael strides toward the     │
│           (10×8 grid)                    │  hearth, boots scuffing      │
│                                          │  sawdust...                  │
│           Cursor: D-pad                  │                              │
│           Confirm:    A                  │  > "I want to flip the       │
│           Cancel:     B                  │     table"                   │
│                                          │                              │
│                                          │  The oak table groans as     │
│                                          │  Kael's shoulder slams...    │
│                                          │                              │
│                                          │  [autoscroll bottom]         │
│              60% width                   │            40% width         │
│                                          │                              │
├──────────────────────────────────────────┴──────────────────────────────┤
│  ACTIVE: Kael (Fighter)  HP 12/12  AC 16  MOVE 30/30  POS (3,6)         │  ← 12% (bottom bar)
│  [A] Confirm   [B] Cancel   [Y] Speak   [LB/RB] Switch Char             │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Xbox Controller Mapping (Standard Layout)

| Button | Index | Action |
|---|---|---|
| **A** | 0 | Confirm move to highlighted cell |
| **B** | 1 | Cancel cursor / close modal |
| **X** | 2 | Inspect highlighted cell |
| **Y** | 3 | Open freeform text modal (keyboard input) |
| **LB** | 4 | Previous character (cycle active) |
| **RB** | 5 | Next character |
| **D-pad ↑↓←→** | 12–15 | Move cursor 1 cell (debounced) |
| **Left stick** | axes 0,1 | Same as D-pad with deadzone |
| **Start** | 9 | Open menu (reserved for v0.2) |
| **Back/View** | 8 | Toggle character sheet detail |

Any of the 4 controllers can drive the cursor and confirm. Controller index doesn't lock to a character — pick up whichever's nearest.

### 4.3 Data Flow Per Frame

```
60Hz requestAnimationFrame
        │
        ▼
gamepad.poll()         ← navigator.getGamepads()
        │
        ▼
emits events           ← "cursor_move", "confirm", "switch_char", etc.
        │
        ▼
main.js handlers       ← updates app state (cursor pos, active char id)
        │
        ▼
canvas.render()        ← Konva layer .draw() only on state change
        │
        ▼
Konva stage commits to GPU
```

WebSocket pushes from server happen **outside** this loop — they fire whenever, and dispatch to `main.applyDiff(diff)` which updates app state and triggers the next render.

---

## 5. Frontend Files

### 5.1 `frontend/index.html`

```html
<!DOCTYPE html>
<html lang="en" data-paper="vellum" data-ink="midnight">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>StoryForge — The Crooked Tankard</title>

  <!-- Konva.js: thin Canvas wrapper. v9 supports devicePixelRatio out of the box. -->
  <script src="https://unpkg.com/konva@9.3.16/konva.min.js"></script>

  <link rel="stylesheet" href="/static/css/styles.css" />
  <link rel="stylesheet" href="/static/css/parchment.css" />
  <link rel="stylesheet" href="/static/css/ink-effects.css" />
</head>
<body>

  <!-- ─────── TOP BAR: Party Portraits + Connection Status ─────── -->
  <header id="party-bar" class="party-bar parchment-strip">
    <div class="portrait-row" id="portrait-row">
      <!-- Populated by characters.js -->
    </div>
    <div class="status-cluster">
      <span id="kbd-indicator" class="indicator">⌨ <span>KBD</span></span>
      <span id="gamepad-indicator" class="indicator">
        🎮 <span id="gp-slot-0">·</span><span id="gp-slot-1">·</span><span id="gp-slot-2">·</span><span id="gp-slot-3">·</span>
      </span>
    </div>
  </header>

  <!-- ─────── MAIN STAGE: Canvas + Log ─────── -->
  <main id="stage">
    <section id="canvas-pane" class="parchment-surface">
      <div id="konva-mount"></div>
    </section>

    <aside id="log-pane" class="parchment-surface ink-midnight">
      <h2 class="log-title">Chronicle</h2>
      <ol id="narrative-log" class="narrative-log"></ol>
    </aside>
  </main>

  <!-- ─────── BOTTOM BAR: Active Character + Hints ─────── -->
  <footer id="action-bar" class="action-bar parchment-strip">
    <div id="active-summary" class="active-summary">
      <span class="label">Active:</span>
      <span id="active-name" class="active-name ink-gilded">—</span>
      <span id="active-class" class="active-class">—</span>
      <span class="stat">HP <span id="active-hp">—</span></span>
      <span class="stat">AC <span id="active-ac">—</span></span>
      <span class="stat">MOVE <span id="active-move">—</span></span>
      <span class="stat">POS <span id="active-pos">—</span></span>
    </div>
    <div class="hints">
      <span class="hint"><kbd>A</kbd> Confirm</span>
      <span class="hint"><kbd>B</kbd> Cancel</span>
      <span class="hint"><kbd>Y</kbd> Speak</span>
      <span class="hint"><kbd>LB</kbd>/<kbd>RB</kbd> Cycle</span>
    </div>
  </footer>

  <!-- ─────── FREEFORM MODAL ─────── -->
  <div id="freeform-modal" class="modal hidden" role="dialog" aria-modal="true">
    <div class="modal-card parchment-surface">
      <h2 class="ink-crimson">Speak Your Action</h2>
      <p class="hint-small">Press <kbd>Esc</kbd> or <kbd>B</kbd> to cancel · <kbd>Enter</kbd> to commit</p>
      <textarea id="freeform-input"
                rows="4"
                maxlength="500"
                placeholder="I creep along the shadowed wall toward the bard..."></textarea>
      <div class="modal-actions">
        <button id="freeform-cancel" class="btn">Cancel</button>
        <button id="freeform-commit" class="btn btn-primary">Commit</button>
      </div>
    </div>
  </div>

  <!-- ─────── ENTRY POINT ─────── -->
  <script type="module" src="/static/js/main.js"></script>
</body>
</html>
```

### 5.2 `frontend/css/styles.css`

```css
/* ═══════════════════════════════════════════════════════════════════════
   StoryForge — 10-Foot UI Base Stylesheet
   Target: 50"+ TV at viewing distance ~10ft. Base font 1.5rem = 24px.
   Layout uses CSS Grid for predictable scaling at 1080p AND 4K.
   ═══════════════════════════════════════════════════════════════════════ */

:root {
  /* ─── Type scale ─── */
  --fs-base: 1.5rem;       /* 24px */
  --fs-sm:   1.25rem;      /* 20px */
  --fs-lg:   2rem;         /* 32px */
  --fs-xl:   2.75rem;      /* 44px */
  --fs-display: 4rem;      /* 64px */

  /* ─── Spacing (TV-scale) ─── */
  --space-1: 0.5rem;
  --space-2: 1rem;
  --space-3: 1.5rem;
  --space-4: 2rem;
  --space-5: 3rem;

  /* ─── Ink palette ─── */
  --ink-midnight:  #1a1428;
  --ink-burgundy:  #5a1622;
  --ink-gilded:    #c9a14a;
  --ink-emerald:   #1e5a3a;
  --ink-crimson:   #8b1a2b;
  --ink-violet:    #4a1a6b;

  /* ─── Glow / accent ─── */
  --glow-gold:   0 0 1.5rem rgba(201, 161, 74, 0.55);
  --glow-active: 0 0 2rem rgba(255, 215, 0, 0.7);

  /* ─── Grid contrast (for canvas overlays) ─── */
  --grid-line:   rgba(40, 24, 12, 0.7);
  --grid-major:  rgba(40, 24, 12, 0.9);
  --token-border-w: 4px;     /* thick strokes for TV legibility */

  /* ─── Layout ─── */
  --top-h:    8vh;
  --bottom-h: 12vh;
  --pane-gap: var(--space-2);
}

* { box-sizing: border-box; }

html, body {
  margin: 0;
  padding: 0;
  height: 100%;
  font-family: "Cardo", "Bookerly", Georgia, serif;
  font-size: var(--fs-base);
  color: var(--ink-midnight);
  overflow: hidden;
  /* Disable text selection — this is a kiosk, not a webpage */
  user-select: none;
  -webkit-user-select: none;
}

body {
  display: grid;
  grid-template-rows: var(--top-h) 1fr var(--bottom-h);
  background: #2a1f10;  /* deep walnut beneath any parchment failure */
}

/* ─────────────────────────── TOP BAR ─────────────────────────── */
.party-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--space-3);
  gap: var(--space-3);
  border-bottom: 3px solid var(--ink-midnight);
  box-shadow: 0 4px 12px rgba(0,0,0,0.25);
}

.portrait-row {
  display: flex;
  gap: var(--space-3);
  height: 100%;
  align-items: center;
}

.portrait {
  width: calc(var(--top-h) - 1rem);
  height: calc(var(--top-h) - 1rem);
  border: 4px solid var(--ink-midnight);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--fs-xl);
  font-weight: 700;
  background: rgba(255, 245, 220, 0.7);
  transition: box-shadow 0.18s ease, transform 0.18s ease, border-color 0.18s ease;
  cursor: pointer;
  position: relative;
}

.portrait.active {
  border-color: var(--ink-gilded);
  box-shadow: var(--glow-active);
  transform: scale(1.08);
}

.portrait .player-tag {
  position: absolute;
  bottom: -1.6rem;
  left: 50%;
  transform: translateX(-50%);
  font-size: var(--fs-sm);
  white-space: nowrap;
  color: var(--ink-burgundy);
}

.status-cluster {
  display: flex;
  gap: var(--space-3);
  font-size: var(--fs-sm);
}

.indicator {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-2);
  border: 2px solid var(--ink-midnight);
  border-radius: 6px;
  background: rgba(255, 245, 220, 0.5);
}

.indicator.connected { color: var(--ink-emerald); }
.indicator.disconnected { color: var(--ink-crimson); }

#gamepad-indicator span span { margin: 0 2px; font-weight: 700; }
#gamepad-indicator span span.live { color: var(--ink-emerald); }

/* ─────────────────────────── MAIN STAGE ─────────────────────────── */
#stage {
  display: grid;
  grid-template-columns: 60% 40%;
  gap: var(--pane-gap);
  padding: var(--pane-gap);
  overflow: hidden;
  min-height: 0;
}

#canvas-pane {
  position: relative;
  border: 4px solid var(--ink-midnight);
  border-radius: 12px;
  overflow: hidden;
  min-height: 0;
}

#konva-mount {
  width: 100%;
  height: 100%;
}

#log-pane {
  border: 4px solid var(--ink-midnight);
  border-radius: 12px;
  padding: var(--space-3);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.log-title {
  margin: 0 0 var(--space-2) 0;
  font-size: var(--fs-lg);
  border-bottom: 2px solid var(--ink-midnight);
  padding-bottom: var(--space-1);
}

.narrative-log {
  list-style: none;
  margin: 0;
  padding: 0 var(--space-2) 0 0;
  flex: 1;
  overflow-y: auto;
  scroll-behavior: smooth;
  font-size: var(--fs-base);
  line-height: 1.55;
}

.narrative-log li {
  margin: var(--space-2) 0;
  padding: var(--space-2);
  border-left: 4px solid transparent;
}

.narrative-log li.kind-narration { border-left-color: var(--ink-midnight); }
.narrative-log li.kind-action    { border-left-color: var(--ink-gilded); font-style: italic; }
.narrative-log li.kind-system    {
  border-left-color: var(--ink-crimson);
  font-size: var(--fs-sm);
  opacity: 0.75;
  font-family: "JetBrains Mono", monospace;
}

/* TV-friendly scrollbar */
.narrative-log::-webkit-scrollbar { width: 14px; }
.narrative-log::-webkit-scrollbar-track { background: rgba(0,0,0,0.06); }
.narrative-log::-webkit-scrollbar-thumb {
  background: var(--ink-midnight);
  border-radius: 7px;
}

/* ─────────────────────────── BOTTOM BAR ─────────────────────────── */
.action-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--space-3);
  gap: var(--space-3);
  border-top: 3px solid var(--ink-midnight);
  box-shadow: 0 -4px 12px rgba(0,0,0,0.25);
}

.active-summary {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
  font-size: var(--fs-base);
}

.active-summary .label { opacity: 0.7; }
.active-name { font-size: var(--fs-lg); font-weight: 700; }
.active-class { font-style: italic; opacity: 0.85; }
.stat { display: inline-flex; gap: 0.4rem; align-items: baseline; }
.stat > span { font-weight: 700; color: var(--ink-burgundy); }

.hints { display: flex; gap: var(--space-3); font-size: var(--fs-sm); }
.hint kbd {
  background: var(--ink-midnight);
  color: #f4ead4;
  padding: 2px 0.6rem;
  border-radius: 6px;
  font-family: "JetBrains Mono", monospace;
  margin-right: 0.4rem;
}

/* ─────────────────────────── MODAL ─────────────────────────── */
.modal {
  position: fixed;
  inset: 0;
  display: grid;
  place-items: center;
  background: rgba(0,0,0,0.6);
  z-index: 100;
}

.modal.hidden { display: none; }

.modal-card {
  width: min(80vw, 1100px);
  padding: var(--space-4);
  border: 6px solid var(--ink-midnight);
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.modal-card h2 { font-size: var(--fs-xl); margin: 0; }
.hint-small { font-size: var(--fs-sm); opacity: 0.75; margin: 0; }
.hint-small kbd { background: var(--ink-midnight); color: #f4ead4; padding: 1px 0.5rem; border-radius: 4px; }

#freeform-input {
  font-family: "Cardo", Georgia, serif;
  font-size: var(--fs-lg);
  padding: var(--space-3);
  border: 3px solid var(--ink-midnight);
  border-radius: 8px;
  background: rgba(255,245,220,0.9);
  color: var(--ink-midnight);
  resize: vertical;
  min-height: 8rem;
  user-select: text;     /* re-enable for input only */
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
}

.btn {
  font-family: inherit;
  font-size: var(--fs-base);
  padding: var(--space-2) var(--space-4);
  border: 3px solid var(--ink-midnight);
  border-radius: 8px;
  background: rgba(255,245,220,0.7);
  color: var(--ink-midnight);
  cursor: pointer;
  transition: transform 0.12s ease, box-shadow 0.12s ease;
}

.btn:hover, .btn:focus { transform: translateY(-2px); box-shadow: var(--glow-gold); }
.btn-primary { background: var(--ink-gilded); color: #1a1428; }

/* ─────────────────────────── 4K scaling tweaks ─────────────────────────── */
@media (min-width: 3000px) {
  :root {
    --fs-base: 2rem;        /* 32px at 4K */
    --fs-sm: 1.6rem;
    --fs-lg: 2.75rem;
    --fs-xl: 3.5rem;
    --token-border-w: 6px;
  }
}
```

**Teaching note on the type scale at 4K:** Most browsers render a 4K TV at the native resolution, but the OS-level `--scale` defaults to ~150% on many smart TVs and Chromecast devices. The `@media (min-width: 3000px)` rule kicks in only when the browser actually has 3000+ CSS pixels — i.e. you've forced 1:1 scaling. At default scaling on a 4K TV (which behaves like ~2560×1440 in CSS pixels), the base rule of 1.5rem still produces a comfortable 24px.

### 5.3 `frontend/css/parchment.css`

```css
/* ═══════════════════════════════════════════════════════════════════════
   Parchment Themes
   Three paper variants, switchable via [data-paper] on <html>.
   All pure CSS — no image assets needed for MVP. Drop in real textures
   later by replacing the background-image rules.
   ═══════════════════════════════════════════════════════════════════════ */

/* Base parchment surface — applied to log, modal, etc. */
.parchment-surface,
.parchment-strip {
  background-color: #f4ead4;
  background-image:
    radial-gradient(ellipse at top left,    rgba(180,140,90,0.18), transparent 60%),
    radial-gradient(ellipse at bottom right, rgba(160,120,70,0.22), transparent 65%),
    radial-gradient(circle  at 30% 60%,     rgba(120, 80,50,0.10), transparent 40%),
    radial-gradient(circle  at 70% 30%,     rgba(120, 80,50,0.12), transparent 35%);
  /* Subtle fibrous noise via stacked tiny gradients */
  background-blend-mode: multiply, multiply, normal, normal;
  position: relative;
}

.parchment-surface::before,
.parchment-strip::before {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.45;
  /* SVG turbulence for fiber detail. Inlined so we ship no assets. */
  background-image: url("data:image/svg+xml;utf8,\
<svg xmlns='http://www.w3.org/2000/svg' width='400' height='400'>\
<filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' seed='3'/>\
<feColorMatrix values='0 0 0 0 0.3   0 0 0 0 0.2   0 0 0 0 0.1   0 0 0 0.15 0'/></filter>\
<rect width='100%' height='100%' filter='url(%23n)'/></svg>");
  mix-blend-mode: multiply;
  border-radius: inherit;
}

/* ─── Theme: standard vellum (default) ─── */
html[data-paper="vellum"] .parchment-surface,
html[data-paper="vellum"] .parchment-strip {
  background-color: #f4ead4;
}

/* ─── Theme: ancient scroll (warmer, more aged) ─── */
html[data-paper="ancient"] .parchment-surface,
html[data-paper="ancient"] .parchment-strip {
  background-color: #e3c896;
  background-image:
    radial-gradient(ellipse at top left,    rgba(120, 70, 30,0.30), transparent 55%),
    radial-gradient(ellipse at bottom right, rgba( 90, 50, 20,0.40), transparent 60%),
    radial-gradient(circle  at 50% 50%,     rgba(140, 90, 40,0.18), transparent 70%);
}

/* ─── Theme: dark scroll (charcoal vellum for the gloomy chapters) ─── */
html[data-paper="dark"] {
  color-scheme: dark;
}
html[data-paper="dark"] .parchment-surface,
html[data-paper="dark"] .parchment-strip {
  background-color: #1f1810;
  background-image:
    radial-gradient(ellipse at top left,    rgba(80, 50, 20,0.35), transparent 55%),
    radial-gradient(ellipse at bottom right, rgba(50, 30, 10,0.45), transparent 60%);
}
html[data-paper="dark"] body {
  color: #d9c89a;
}
html[data-paper="dark"] {
  --ink-midnight: #d9c89a;
  --grid-line:   rgba(230, 210, 160, 0.5);
  --grid-major:  rgba(230, 210, 160, 0.8);
}
```

### 5.4 `frontend/css/ink-effects.css`

```css
/* ═══════════════════════════════════════════════════════════════════════
   Ink Effects
   Used for character names, magical items, ability flourishes.
   All effects use background-clip:text so they remain text (a11y +
   selectable in modal). The "gilded" and "glitter" effects animate.
   ═══════════════════════════════════════════════════════════════════════ */

/* ─── Solid inks ─── */
.ink-midnight { color: var(--ink-midnight); }
.ink-burgundy { color: var(--ink-burgundy); }
.ink-emerald  { color: var(--ink-emerald); }
.ink-crimson  { color: var(--ink-crimson); }
.ink-violet   { color: var(--ink-violet); }

/* ─── Gilded: gold gradient, gentle shimmer ─── */
.ink-gilded {
  background: linear-gradient(
    100deg,
    #8a6918 0%,
    #c9a14a 25%,
    #f5d97a 50%,
    #c9a14a 75%,
    #8a6918 100%
  );
  background-size: 200% 100%;
  -webkit-background-clip: text;
          background-clip: text;
  -webkit-text-fill-color: transparent;
          color: transparent;
  animation: gilded-shimmer 6s ease-in-out infinite;
  text-shadow: 0 0 1px rgba(201, 161, 74, 0.25);
}

@keyframes gilded-shimmer {
  0%, 100% { background-position: 0% 50%; }
  50%      { background-position: 100% 50%; }
}

/* ─── Arcane: violet → cyan, slow drift, for spells/wizards ─── */
.ink-arcane {
  background: linear-gradient(
    100deg,
    #4a1a6b 0%,
    #7a3cb8 30%,
    #3cc9d4 60%,
    #7a3cb8 80%,
    #4a1a6b 100%
  );
  background-size: 250% 100%;
  -webkit-background-clip: text;
          background-clip: text;
  -webkit-text-fill-color: transparent;
          color: transparent;
  animation: arcane-drift 9s linear infinite;
}

@keyframes arcane-drift {
  0%   { background-position: 0% 50%; }
  100% { background-position: 200% 50%; }
}

/* ─── Glitter: rapid hue shimmer, for magical items / crits ─── */
.ink-glitter {
  background: linear-gradient(
    90deg,
    #f5d97a, #ffffff, #b78cff, #ffffff, #f5d97a
  );
  background-size: 300% 100%;
  -webkit-background-clip: text;
          background-clip: text;
  -webkit-text-fill-color: transparent;
          color: transparent;
  animation: glitter-pulse 2.5s linear infinite;
  filter: drop-shadow(0 0 6px rgba(255, 220, 130, 0.45));
}

@keyframes glitter-pulse {
  0%   { background-position: 0% 50%; }
  100% { background-position: 300% 50%; }
}

/* ─── Bloodied: throbbing red for low HP / wounded states ─── */
.ink-bloodied {
  color: var(--ink-crimson);
  animation: bloodied-throb 1.4s ease-in-out infinite;
}

@keyframes bloodied-throb {
  0%, 100% { opacity: 1.0; }
  50%      { opacity: 0.65; }
}

/* Respect users who don't want motion */
@media (prefers-reduced-motion: reduce) {
  .ink-gilded, .ink-arcane, .ink-glitter, .ink-bloodied {
    animation: none;
  }
}
```

### 5.5 `frontend/js/api.js`

```javascript
/**
 * REST + WebSocket wrappers for the StoryForge backend.
 * All endpoints are relative — works in dev and any future reverse proxy.
 */

const API_BASE = "";  // same-origin

async function jsonOrThrow(res) {
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}${text ? ` — ${text}` : ""}`);
  }
  return res.json();
}

export async function fetchState() {
  const res = await fetch(`${API_BASE}/api/state`);
  return jsonOrThrow(res);
}

export async function fetchRevision() {
  const res = await fetch(`${API_BASE}/api/revision`);
  return jsonOrThrow(res);
}

export async function postGridAction({ actorId, type, target }) {
  const res = await fetch(`${API_BASE}/api/action/grid`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ actor_id: actorId, type, target }),
  });
  return jsonOrThrow(res);
}

export async function postFreeformAction({ actorId, text }) {
  const res = await fetch(`${API_BASE}/api/action/freeform`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ actor_id: actorId, text }),
  });
  return jsonOrThrow(res);
}

/**
 * Open a WebSocket and call onMessage for every state_diff event.
 * Auto-reconnects with backoff on disconnect.
 */
export function openSession({ roomId, onMessage, onConnect, onDisconnect }) {
  let ws = null;
  let backoff = 500;
  const MAX_BACKOFF = 8000;
  let alive = true;

  function connect() {
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    ws = new WebSocket(`${proto}://${window.location.host}/ws/session/${roomId}`);
    ws.addEventListener("open", () => {
      backoff = 500;
      onConnect?.();
    });
    ws.addEventListener("message", (e) => {
      try {
        onMessage(JSON.parse(e.data));
      } catch (err) {
        console.error("[ws] bad message", err, e.data);
      }
    });
    ws.addEventListener("close", () => {
      onDisconnect?.();
      if (!alive) return;
      setTimeout(connect, backoff);
      backoff = Math.min(backoff * 2, MAX_BACKOFF);
    });
    ws.addEventListener("error", () => ws?.close());
  }

  connect();
  return {
    close() { alive = false; ws?.close(); },
  };
}
```

### 5.6 `frontend/js/canvas.js`

The heaviest frontend module. Konva stage with three layers, HiDPI handling, cursor that follows gamepad input, click-to-act.

```javascript
/**
 * Konva-based 10x8 grid renderer with HiDPI awareness.
 *
 * Layers (bottom → top):
 *   1. gridLayer    — parchment-tinted cells with terrain colors and borders
 *   2. tokenLayer   — character + NPC tokens
 *   3. cursorLayer  — gamepad-controlled selection cursor + targeting reticle
 *
 * The stage is sized in CSS pixels but Konva.pixelRatio is set to
 * window.devicePixelRatio so the underlying canvas is rendered at native
 * resolution — crisp at 4K.
 */

const TERRAIN_COLORS = {
  floor:     "rgba(244, 234, 212, 0.0)",       // transparent over parchment
  wall:      "rgba(40, 24, 12, 0.92)",
  door:      "rgba(120, 70, 30, 0.85)",
  difficult: "rgba(140, 100, 60, 0.35)",
  hazard:    "rgba(180, 50, 30, 0.55)",
};

const CHARACTER_COLORS = {
  cody: "#5a1622",  // burgundy — Fighter
  dee:  "#4a1a6b",  // violet   — Wizard
  nate: "#1e5a3a",  // emerald  — Ranger
  bray: "#1a1428",  // midnight — Rogue
};

const TERRAIN_LABEL = {
  floor: "·", wall: "▓", door: "Ɖ", difficult: "≋", hazard: "✷",
};

export class GridCanvas {
  constructor({ mountEl, onCellConfirmed, onCellInspected }) {
    this.mountEl = mountEl;
    this.onCellConfirmed = onCellConfirmed;
    this.onCellInspected = onCellInspected;

    this.state = null;
    this.cursor = { x: 0, y: 0 };
    this.cellSize = 64;  // recalculated on resize

    this._initStage();
    this._observeResize();
  }

  _initStage() {
    // HiDPI: ensure Konva renders at native pixel density.
    Konva.pixelRatio = window.devicePixelRatio || 1;

    this.stage = new Konva.Stage({
      container: this.mountEl,
      width: this.mountEl.clientWidth,
      height: this.mountEl.clientHeight,
    });

    this.gridLayer   = new Konva.Layer({ listening: false });
    this.tokenLayer  = new Konva.Layer({ listening: true });
    this.cursorLayer = new Konva.Layer({ listening: false });

    this.stage.add(this.gridLayer);
    this.stage.add(this.tokenLayer);
    this.stage.add(this.cursorLayer);
  }

  _observeResize() {
    const ro = new ResizeObserver(() => this._fitAndRedraw());
    ro.observe(this.mountEl);
  }

  _fitAndRedraw() {
    if (!this.state) return;
    const w = this.mountEl.clientWidth;
    const h = this.mountEl.clientHeight;
    this.stage.size({ width: w, height: h });

    const room = this._currentRoom();
    // Cell size: fit the longer of the two axes with a small padding.
    const padding = 32;
    const cellW = (w - padding * 2) / room.width;
    const cellH = (h - padding * 2) / room.height;
    this.cellSize = Math.floor(Math.min(cellW, cellH));

    // Recompute offset so the grid is centered.
    this.offsetX = Math.floor((w - this.cellSize * room.width) / 2);
    this.offsetY = Math.floor((h - this.cellSize * room.height) / 2);

    this.renderAll();
  }

  setState(state) {
    this.state = state;
    this._fitAndRedraw();
  }

  applyDiff(_diff) {
    // For MVP, just re-render everything on any diff. Cheap at 10x8.
    this.renderAll();
  }

  setCursor({ x, y }) {
    const room = this._currentRoom();
    this.cursor.x = Math.max(0, Math.min(room.width  - 1, x));
    this.cursor.y = Math.max(0, Math.min(room.height - 1, y));
    this._renderCursor();
  }

  moveCursor(dx, dy) {
    this.setCursor({ x: this.cursor.x + dx, y: this.cursor.y + dy });
  }

  confirmCursor() {
    this.onCellConfirmed?.({ x: this.cursor.x, y: this.cursor.y });
  }

  inspectCursor() {
    const cell = this._cellAt(this.cursor.x, this.cursor.y);
    this.onCellInspected?.({ coord: { ...this.cursor }, cell });
  }

  // ─────────────────────── Internal renderers ───────────────────────

  _currentRoom() {
    return this.state.rooms[this.state.current_room_id];
  }

  _cellAt(x, y) {
    const room = this._currentRoom();
    return room.cells[y * room.width + x];
  }

  renderAll() {
    if (!this.state) return;
    this._renderGrid();
    this._renderTokens();
    this._renderCursor();
  }

  _renderGrid() {
    this.gridLayer.destroyChildren();
    const room = this._currentRoom();
    const cs = this.cellSize;
    const ox = this.offsetX, oy = this.offsetY;

    for (let y = 0; y < room.height; y++) {
      for (let x = 0; x < room.width; x++) {
        const cell = room.cells[y * room.width + x];
        const fill = TERRAIN_COLORS[cell.terrain] ?? TERRAIN_COLORS.floor;

        const rect = new Konva.Rect({
          x: ox + x * cs,
          y: oy + y * cs,
          width: cs,
          height: cs,
          fill: fill,
          stroke: "rgba(40, 24, 12, 0.75)",
          strokeWidth: 2,
          perfectDrawEnabled: false,
        });
        this.gridLayer.add(rect);
      }
    }

    // Major gridlines every 5 cells (10ft increments in 5e)
    const major = new Konva.Group();
    for (let i = 0; i <= room.width; i += 5) {
      major.add(new Konva.Line({
        points: [ox + i * cs, oy, ox + i * cs, oy + room.height * cs],
        stroke: "rgba(40, 24, 12, 0.95)",
        strokeWidth: 3,
      }));
    }
    for (let j = 0; j <= room.height; j += 5) {
      major.add(new Konva.Line({
        points: [ox, oy + j * cs, ox + room.width * cs, oy + j * cs],
        stroke: "rgba(40, 24, 12, 0.95)",
        strokeWidth: 3,
      }));
    }
    this.gridLayer.add(major);
    this.gridLayer.batchDraw();
  }

  _renderTokens() {
    this.tokenLayer.destroyChildren();
    const cs = this.cellSize;
    const ox = this.offsetX, oy = this.offsetY;

    for (const char of Object.values(this.state.characters)) {
      const { x, y } = char.position;
      const cx = ox + x * cs + cs / 2;
      const cy = oy + y * cs + cs / 2;

      const ring = new Konva.Circle({
        x: cx, y: cy,
        radius: cs * 0.4,
        fill: CHARACTER_COLORS[char.id] ?? "#444",
        stroke: "#f4ead4",
        strokeWidth: 5,   // thick stroke for TV
        shadowColor: "black",
        shadowBlur: 8,
        shadowOpacity: 0.45,
      });

      const initial = new Konva.Text({
        x: cx - cs / 2,
        y: cy - cs / 2,
        width: cs,
        height: cs,
        text: char.name[0],
        fontFamily: "Cardo, Georgia, serif",
        fontSize: Math.floor(cs * 0.5),
        fontStyle: "bold",
        fill: "#f4ead4",
        align: "center",
        verticalAlign: "middle",
        listening: false,
      });

      const group = new Konva.Group({ id: `token-${char.id}` });
      group.add(ring);
      group.add(initial);
      this.tokenLayer.add(group);
    }
    this.tokenLayer.batchDraw();
  }

  _renderCursor() {
    this.cursorLayer.destroyChildren();
    if (!this.state) return;

    const cs = this.cellSize;
    const ox = this.offsetX, oy = this.offsetY;
    const { x, y } = this.cursor;

    // Outer reticle — bright gold
    const reticle = new Konva.Rect({
      x: ox + x * cs + 3,
      y: oy + y * cs + 3,
      width: cs - 6,
      height: cs - 6,
      stroke: "#c9a14a",
      strokeWidth: 5,
      dash: [12, 6],
      cornerRadius: 6,
      shadowColor: "#c9a14a",
      shadowBlur: 18,
      shadowOpacity: 0.7,
    });
    this.cursorLayer.add(reticle);

    // Animated dash offset — gives a "marching ants" effect
    const anim = new Konva.Animation((frame) => {
      reticle.dashOffset(-(frame.time / 60) % 18);
    }, this.cursorLayer);
    // Stop previous animation if any
    this._cursorAnim?.stop();
    this._cursorAnim = anim;
    anim.start();
  }
}
```

**Teaching note on the marching-ants cursor:** Konva.Animation only burns CPU on the cursor layer (the other layers don't re-rasterize). At 60Hz on a 4K canvas with one rect that's negligible — ~0.4% of one core. If you ever profile a CPU spike, look at gridLayer/tokenLayer redraws first.

### 5.7 `frontend/js/gamepad.js`

The Xbox controller polling engine. Edge-detected button events, axis deadzone, repeat-delay for held directions.

```javascript
/**
 * Gamepad API integration with edge-detected button events and
 * D-pad / stick navigation with repeat delay.
 *
 * Supports up to 4 simultaneous controllers (indices 0-3).
 *
 * Public API: new GamepadManager().on(event, handler).start();
 *
 * Events:
 *   "controller_connected"    { index }
 *   "controller_disconnected" { index }
 *   "button_pressed"          { index, button }    edge: just-pressed
 *   "button_released"         { index, button }
 *   "dpad_repeat"             { index, dx, dy }    on tap AND held-repeat
 */

const XBOX = {
  A: 0, B: 1, X: 2, Y: 3,
  LB: 4, RB: 5, LT: 6, RT: 7,
  BACK: 8, START: 9,
  LS: 10, RS: 11,
  DPAD_UP: 12, DPAD_DOWN: 13, DPAD_LEFT: 14, DPAD_RIGHT: 15,
};

const DEADZONE = 0.45;
const INITIAL_REPEAT_MS = 350;
const REPEAT_INTERVAL_MS = 120;

export class GamepadManager {
  constructor() {
    this._handlers = new Map();           // event -> Set<handler>
    this._prevButtons = [[], [], [], []];  // per controller, per button (bool)
    this._dirHold = [null, null, null, null]; // { dx, dy, sinceMs, lastRepeatMs }
    this._connected = new Set();
    this._running = false;

    window.addEventListener("gamepadconnected", (e) => {
      this._connected.add(e.gamepad.index);
      this._emit("controller_connected", { index: e.gamepad.index });
    });
    window.addEventListener("gamepaddisconnected", (e) => {
      this._connected.delete(e.gamepad.index);
      this._dirHold[e.gamepad.index] = null;
      this._emit("controller_disconnected", { index: e.gamepad.index });
    });
  }

  on(event, handler) {
    if (!this._handlers.has(event)) this._handlers.set(event, new Set());
    this._handlers.get(event).add(handler);
    return this;
  }

  off(event, handler) {
    this._handlers.get(event)?.delete(handler);
    return this;
  }

  start() {
    if (this._running) return;
    this._running = true;
    const loop = () => {
      if (!this._running) return;
      this._poll(performance.now());
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }

  stop() { this._running = false; }

  // ─────────────────────── Internals ───────────────────────

  _emit(event, payload) {
    const set = this._handlers.get(event);
    if (!set) return;
    for (const h of set) {
      try { h(payload); } catch (err) { console.error("[gp]", event, err); }
    }
  }

  _poll(nowMs) {
    const pads = navigator.getGamepads?.() ?? [];
    for (let i = 0; i < 4; i++) {
      const pad = pads[i];
      if (!pad) {
        if (this._connected.has(i)) {
          // Spec says we should already have received gamepaddisconnected,
          // but some browsers miss it. Clean up manually.
          this._connected.delete(i);
          this._dirHold[i] = null;
        }
        continue;
      }

      if (!this._connected.has(i)) {
        this._connected.add(i);
        this._emit("controller_connected", { index: i });
      }

      this._pollButtons(i, pad);
      this._pollDirection(i, pad, nowMs);
    }
  }

  _pollButtons(i, pad) {
    const prev = this._prevButtons[i];
    for (let b = 0; b < pad.buttons.length; b++) {
      const pressed = pad.buttons[b].pressed;
      const wasPressed = prev[b] ?? false;
      if (pressed && !wasPressed) {
        this._emit("button_pressed", { index: i, button: b });
      } else if (!pressed && wasPressed) {
        this._emit("button_released", { index: i, button: b });
      }
      prev[b] = pressed;
    }
  }

  _pollDirection(i, pad, nowMs) {
    // Combine D-pad and left stick into a single dx/dy intent.
    let dx = 0, dy = 0;

    if (pad.buttons[XBOX.DPAD_LEFT]?.pressed)  dx -= 1;
    if (pad.buttons[XBOX.DPAD_RIGHT]?.pressed) dx += 1;
    if (pad.buttons[XBOX.DPAD_UP]?.pressed)    dy -= 1;
    if (pad.buttons[XBOX.DPAD_DOWN]?.pressed)  dy += 1;

    const ax = pad.axes[0] ?? 0;
    const ay = pad.axes[1] ?? 0;
    if (dx === 0 && Math.abs(ax) > DEADZONE) dx = Math.sign(ax);
    if (dy === 0 && Math.abs(ay) > DEADZONE) dy = Math.sign(ay);

    const hold = this._dirHold[i];
    if (dx === 0 && dy === 0) {
      this._dirHold[i] = null;
      return;
    }

    // First press: emit immediately.
    if (!hold || hold.dx !== dx || hold.dy !== dy) {
      this._dirHold[i] = { dx, dy, sinceMs: nowMs, lastRepeatMs: nowMs };
      this._emit("dpad_repeat", { index: i, dx, dy });
      return;
    }

    // Held: wait for initial delay, then repeat at interval.
    const heldFor = nowMs - hold.sinceMs;
    const sinceLast = nowMs - hold.lastRepeatMs;
    if (heldFor >= INITIAL_REPEAT_MS && sinceLast >= REPEAT_INTERVAL_MS) {
      hold.lastRepeatMs = nowMs;
      this._emit("dpad_repeat", { index: i, dx, dy });
    }
  }
}

export { XBOX };
```

**Teaching note on repeat-delay:** Without `INITIAL_REPEAT_MS` and `REPEAT_INTERVAL_MS`, holding D-pad-right would fire 60 times per second and the cursor would teleport across the room. The first press is immediate (snappy), then there's a 350ms hesitation, then 120ms repeats — matches OS-level key-repeat conventions so it feels natural.

### 5.8 `frontend/js/audio.js`

Procedural sound effects via Web Audio API. No asset files needed for MVP.

```javascript
/**
 * Procedural audio engine.
 *
 * Generates short SFX via oscillators + envelopes. AudioContext is
 * resumed on the first user gesture (browsers require this).
 *
 * To swap in real assets later: replace each play* method with
 * a buffer-loaded sample played through the same masterGain.
 */

export class AudioEngine {
  constructor({ enabled = true } = {}) {
    this.enabled = enabled;
    this.ctx = null;
    this.masterGain = null;
    this._initOnGesture = this._initOnGesture.bind(this);
    window.addEventListener("pointerdown", this._initOnGesture, { once: true });
    window.addEventListener("keydown", this._initOnGesture, { once: true });
    window.addEventListener("gamepadconnected", this._initOnGesture, { once: true });
  }

  _initOnGesture() {
    if (this.ctx) return;
    const Ctx = window.AudioContext || window.webkitAudioContext;
    this.ctx = new Ctx({ latencyHint: "interactive" });
    this.masterGain = this.ctx.createGain();
    this.masterGain.gain.value = 0.55;
    this.masterGain.connect(this.ctx.destination);
  }

  setVolume(v) {
    if (this.masterGain) this.masterGain.gain.value = Math.max(0, Math.min(1, v));
  }

  // ─────────────────────── Public SFX API ───────────────────────

  playCursor() { this._tone({ freq: 880, dur: 0.04, type: "triangle", gain: 0.18 }); }

  playConfirm() {
    this._chord([523, 659, 784], { dur: 0.22, type: "sine", gain: 0.30 });
  }

  playDeny() {
    this._tone({ freq: 220, dur: 0.18, type: "sawtooth", gain: 0.28, sweepTo: 160 });
  }

  playPageTurn() {
    // Filtered noise burst
    if (!this.ctx) return;
    const noise = this._noiseBuffer(0.35);
    const src = this.ctx.createBufferSource();
    src.buffer = noise;
    const filter = this.ctx.createBiquadFilter();
    filter.type = "bandpass";
    filter.frequency.value = 1800;
    filter.Q.value = 3;
    const gain = this.ctx.createGain();
    gain.gain.setValueAtTime(0.0, this.ctx.currentTime);
    gain.gain.linearRampToValueAtTime(0.30, this.ctx.currentTime + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.34);
    src.connect(filter).connect(gain).connect(this.masterGain);
    src.start();
    src.stop(this.ctx.currentTime + 0.36);
  }

  playNarrationChime() {
    this._chord([392, 587, 880], { dur: 0.55, type: "sine", gain: 0.22, attack: 0.04 });
  }

  // ─────────────────────── Internals ───────────────────────

  _tone({ freq, dur, type = "sine", gain = 0.3, sweepTo = null }) {
    if (!this.ctx || !this.enabled) return;
    const now = this.ctx.currentTime;
    const osc = this.ctx.createOscillator();
    const g = this.ctx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, now);
    if (sweepTo != null) {
      osc.frequency.exponentialRampToValueAtTime(sweepTo, now + dur);
    }
    g.gain.setValueAtTime(0.0001, now);
    g.gain.exponentialRampToValueAtTime(gain, now + 0.005);
    g.gain.exponentialRampToValueAtTime(0.0001, now + dur);
    osc.connect(g).connect(this.masterGain);
    osc.start(now);
    osc.stop(now + dur + 0.02);
  }

  _chord(freqs, opts) {
    for (const f of freqs) this._tone({ freq: f, ...opts });
  }

  _noiseBuffer(seconds) {
    const sr = this.ctx.sampleRate;
    const buf = this.ctx.createBuffer(1, sr * seconds, sr);
    const ch = buf.getChannelData(0);
    for (let i = 0; i < ch.length; i++) ch[i] = (Math.random() * 2 - 1) * 0.5;
    return buf;
  }
}
```

### 5.9 `frontend/js/characters.js`

Portrait strip rendering and active-character indicator.

```javascript
/**
 * Renders the party portrait strip and the active-character summary in
 * the bottom bar. Click/select a portrait to switch the active character.
 */

const CHAR_INK_CLASS = {
  cody: "ink-burgundy",
  dee:  "ink-arcane",
  nate: "ink-emerald",
  bray: "ink-midnight",
};

export class CharacterPanel {
  constructor({ portraitRowEl, summaryEls, onActiveChanged }) {
    this.row = portraitRowEl;
    this.summary = summaryEls;  // { name, klass, hp, ac, move, pos }
    this.onActiveChanged = onActiveChanged;
    this.state = null;
    this.activeId = null;
  }

  setState(state) {
    this.state = state;
    if (!this.activeId) this.activeId = Object.keys(state.characters)[0];
    this.render();
  }

  setActive(charId) {
    if (!this.state?.characters[charId]) return;
    if (this.activeId === charId) return;
    this.activeId = charId;
    this.render();
    this.onActiveChanged?.(charId);
  }

  cycleActive(direction = 1) {
    const ids = Object.keys(this.state.characters);
    const idx = ids.indexOf(this.activeId);
    const next = (idx + direction + ids.length) % ids.length;
    this.setActive(ids[next]);
  }

  setActiveByControllerIndex(controllerIdx) {
    const ids = Object.keys(this.state.characters);
    if (controllerIdx >= 0 && controllerIdx < ids.length) {
      this.setActive(ids[controllerIdx]);
    }
  }

  render() {
    if (!this.state) return;
    this._renderPortraits();
    this._renderSummary();
  }

  _renderPortraits() {
    this.row.innerHTML = "";
    for (const [id, char] of Object.entries(this.state.characters)) {
      const portrait = document.createElement("button");
      portrait.className = "portrait";
      if (id === this.activeId) portrait.classList.add("active");
      portrait.dataset.charId = id;

      const initial = document.createElement("span");
      initial.className = CHAR_INK_CLASS[id] ?? "ink-midnight";
      initial.textContent = char.name[0];
      portrait.appendChild(initial);

      const tag = document.createElement("span");
      tag.className = "player-tag";
      tag.textContent = `${char.player} · ${char.name}`;
      portrait.appendChild(tag);

      portrait.addEventListener("click", () => this.setActive(id));
      this.row.appendChild(portrait);
    }
  }

  _renderSummary() {
    const char = this.state.characters[this.activeId];
    if (!char) return;
    this.summary.name.textContent  = char.name;
    this.summary.klass.textContent = char.char_class;
    this.summary.hp.textContent    = `${char.hp_current}/${char.hp_max}`;
    this.summary.ac.textContent    = String(char.armor_class);
    this.summary.move.textContent  = `${char.movement_remaining}/${char.speed}`;
    this.summary.pos.textContent   = `(${char.position.x}, ${char.position.y})`;

    // Bloodied check — under half HP throbs red
    this.summary.hp.parentElement.classList.toggle(
      "ink-bloodied",
      char.hp_current <= char.hp_max / 2,
    );
  }

  get activeCharacter() {
    return this.state?.characters[this.activeId] ?? null;
  }
}
```

### 5.10 `frontend/js/log.js`

```javascript
/**
 * Narrative log feed with autoscroll and TTS hook.
 *
 * Future: tts.speak(entry.text) when a speech engine is wired in.
 */

export class NarrativeLog {
  constructor({ listEl, audio }) {
    this.listEl = listEl;
    this.audio = audio;
    this._seen = new Set();
  }

  setInitial(entries) {
    this.listEl.innerHTML = "";
    this._seen.clear();
    for (const entry of entries) this.append(entry, { silent: true });
    this._scrollToBottom();
  }

  append(entry, { silent = false } = {}) {
    const key = `${entry.revision}::${entry.timestamp}::${entry.kind}`;
    if (this._seen.has(key)) return;
    this._seen.add(key);

    const li = document.createElement("li");
    li.className = `kind-${entry.kind}`;

    if (entry.actor_id) {
      const who = document.createElement("strong");
      who.textContent = `${entry.actor_id}: `;
      who.className = "ink-burgundy";
      li.appendChild(who);
    }

    const text = document.createElement("span");
    text.textContent = entry.text;
    li.appendChild(text);

    this.listEl.appendChild(li);
    this._scrollToBottom();

    if (!silent && entry.kind === "narration") {
      this.audio?.playNarrationChime();
    }
  }

  _scrollToBottom() {
    this.listEl.scrollTop = this.listEl.scrollHeight;
  }
}
```

### 5.11 `frontend/js/main.js`

The conductor. Wires everything together.

```javascript
/**
 * StoryForge — Application Entry Point
 *
 * Responsibilities:
 *   - Fetch initial state, render canvas + portraits + log
 *   - Open WebSocket, route state_diff events
 *   - Wire gamepad events → cursor / actions / character switching
 *   - Wire keyboard events as fallback
 *   - Manage freeform input modal
 */

import { fetchState, openSession, postGridAction, postFreeformAction } from "./api.js";
import { GridCanvas } from "./canvas.js";
import { GamepadManager, XBOX } from "./gamepad.js";
import { CharacterPanel } from "./characters.js";
import { NarrativeLog } from "./log.js";
import { AudioEngine } from "./audio.js";

const els = {
  konvaMount:    document.getElementById("konva-mount"),
  portraitRow:   document.getElementById("portrait-row"),
  narrativeLog:  document.getElementById("narrative-log"),
  freeformModal: document.getElementById("freeform-modal"),
  freeformInput: document.getElementById("freeform-input"),
  freeformCommit:document.getElementById("freeform-commit"),
  freeformCancel:document.getElementById("freeform-cancel"),
  kbdIndicator:  document.getElementById("kbd-indicator"),
  gpIndicators:  [0, 1, 2, 3].map(i => document.getElementById(`gp-slot-${i}`)),
  summary: {
    name:  document.getElementById("active-name"),
    klass: document.getElementById("active-class"),
    hp:    document.getElementById("active-hp"),
    ac:    document.getElementById("active-ac"),
    move:  document.getElementById("active-move"),
    pos:   document.getElementById("active-pos"),
  },
};

const audio  = new AudioEngine();
const canvas = new GridCanvas({
  mountEl: els.konvaMount,
  onCellConfirmed: handleGridConfirm,
});
const characters = new CharacterPanel({
  portraitRowEl: els.portraitRow,
  summaryEls:    els.summary,
  onActiveChanged: () => audio.playCursor(),
});
const log = new NarrativeLog({ listEl: els.narrativeLog, audio });
const gp  = new GamepadManager();

let appState = null;
let session  = null;

// ─────────────────────── Boot ───────────────────────

(async function boot() {
  appState = await fetchState();
  canvas.setState(appState);
  characters.setState(appState);
  log.setInitial(appState.narrative_log);

  // Start cursor on the active character's position
  const active = characters.activeCharacter;
  if (active) canvas.setCursor(active.position);

  session = openSession({
    roomId: appState.current_room_id,
    onConnect:    () => console.log("[ws] connected"),
    onDisconnect: () => console.log("[ws] disconnected"),
    onMessage: handleServerEvent,
  });

  wireGamepad();
  wireKeyboard();
  wireFreeformModal();

  gp.start();
})();

// ─────────────────────── Server events ───────────────────────

async function handleServerEvent(msg) {
  if (msg.type !== "state_diff") return;
  // Cheapest correct approach: re-fetch the canonical state on every diff.
  // Diffs are advisory for triggering re-renders + audio cues.
  appState = await fetchState();
  canvas.setState(appState);
  characters.setState(appState);

  // Append only the latest log entry (or however many we don't have yet)
  for (const entry of appState.narrative_log.slice(-3)) {
    log.append(entry);
  }
}

// ─────────────────────── Action handlers ───────────────────────

async function handleGridConfirm(target) {
  const active = characters.activeCharacter;
  if (!active) return;
  try {
    await postGridAction({
      actorId: active.id,
      type: "move",
      target,
    });
    audio.playConfirm();
  } catch (err) {
    console.warn("[grid] rejected:", err.message);
    audio.playDeny();
    log.append({
      revision: appState?.revision ?? 0,
      actor_id: null,
      kind: "system",
      text: `[ref] illegal action: ${err.message}`,
      timestamp: new Date().toISOString(),
    });
  }
}

async function commitFreeform() {
  const text = els.freeformInput.value.trim();
  if (!text) return;
  const active = characters.activeCharacter;
  if (!active) return;
  closeFreeformModal();
  audio.playPageTurn();
  try {
    await postFreeformAction({ actorId: active.id, text });
  } catch (err) {
    console.error("[freeform] failed", err);
    audio.playDeny();
  }
}

// ─────────────────────── Gamepad wiring ───────────────────────

function wireGamepad() {
  gp.on("controller_connected", ({ index }) => {
    els.gpIndicators[index]?.classList.add("live");
    els.gpIndicators[index].textContent = String(index + 1);
  });
  gp.on("controller_disconnected", ({ index }) => {
    els.gpIndicators[index]?.classList.remove("live");
    els.gpIndicators[index].textContent = "·";
  });

  gp.on("dpad_repeat", ({ dx, dy }) => {
    canvas.moveCursor(dx, dy);
    audio.playCursor();
  });

  gp.on("button_pressed", ({ index, button }) => {
    switch (button) {
      case XBOX.A:
        canvas.confirmCursor();
        break;
      case XBOX.B:
        if (!els.freeformModal.classList.contains("hidden")) {
          closeFreeformModal();
        }
        break;
      case XBOX.X:
        canvas.inspectCursor();
        break;
      case XBOX.Y:
        openFreeformModal();
        break;
      case XBOX.LB:
        characters.cycleActive(-1);
        recenterCursorOnActive();
        break;
      case XBOX.RB:
        characters.cycleActive(+1);
        recenterCursorOnActive();
        break;
      default:
        // Controller-index → character-slot binding on any A press
        if (button === XBOX.A) {
          characters.setActiveByControllerIndex(index);
        }
        break;
    }
  });
}

function recenterCursorOnActive() {
  const active = characters.activeCharacter;
  if (active) canvas.setCursor(active.position);
}

// ─────────────────────── Keyboard fallback ───────────────────────

function wireKeyboard() {
  window.addEventListener("keydown", (e) => {
    // Skip when typing in the freeform modal
    if (document.activeElement === els.freeformInput) return;

    switch (e.key) {
      case "ArrowLeft":  canvas.moveCursor(-1, 0); audio.playCursor(); break;
      case "ArrowRight": canvas.moveCursor(+1, 0); audio.playCursor(); break;
      case "ArrowUp":    canvas.moveCursor(0, -1); audio.playCursor(); break;
      case "ArrowDown":  canvas.moveCursor(0, +1); audio.playCursor(); break;
      case "Enter":      canvas.confirmCursor(); break;
      case "Escape":     closeFreeformModal(); break;
      case "Tab":
        e.preventDefault();
        characters.cycleActive(e.shiftKey ? -1 : +1);
        recenterCursorOnActive();
        break;
      case "/":
      case "t":
        e.preventDefault();
        openFreeformModal();
        break;
    }
  });
  els.kbdIndicator.classList.add("connected");
}

// ─────────────────────── Freeform modal ───────────────────────

function wireFreeformModal() {
  els.freeformCommit.addEventListener("click", commitFreeform);
  els.freeformCancel.addEventListener("click", closeFreeformModal);
  els.freeformInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      commitFreeform();
    } else if (e.key === "Escape") {
      closeFreeformModal();
    }
  });
}

function openFreeformModal() {
  els.freeformModal.classList.remove("hidden");
  els.freeformInput.value = "";
  setTimeout(() => els.freeformInput.focus(), 50);
  audio.playPageTurn();
}

function closeFreeformModal() {
  els.freeformModal.classList.add("hidden");
}
```

**Teaching note on `handleServerEvent`:** I'm refetching the full state on every diff rather than applying the diff payload directly. For a 10×8 grid with 4 characters, the full state is ~3KB and refetch is ~5ms over loopback. Applying diffs locally is faster but introduces a divergence class of bugs (client-side state drifts from server). For MVP, **trust the server, refetch on every change**. Optimize when you have a profiler telling you to.

---

## 6. Verification Checklist (Pass 3)

Run these in order. Each one isolates a failure mode in the new code.

```fish
# ─── 1. Backend boots with new routes ──────────────────────────
./scripts/dev.fish &
sleep 2
curl -sf http://127.0.0.1:8765/api/state | jq '.campaign_id, .current_room_id'
# Expected: "family_campaign_01" and "tavern_01"

curl -sf http://127.0.0.1:8765/api/character/cody | jq '.name, .position'
# Expected: "Kael" and {"x":3,"y":6}

curl -sf http://127.0.0.1:8765/api/revision | jq '.revision'
# Expected: 0

# ─── 2. Static assets serve ────────────────────────────────────
curl -sf http://127.0.0.1:8765/ | head -20
# Expected: <!DOCTYPE html> ... StoryForge — The Crooked Tankard

curl -sf http://127.0.0.1:8765/static/css/styles.css | head -5
# Expected: CSS comment block

# ─── 3. Open the browser ───────────────────────────────────────
xdg-open http://127.0.0.1:8765
# You should see: parchment background, 4 character portraits at top,
# 10x8 grid in center with 4 colored tokens at row 6, narrative log
# at right with the opening tavern description, action bar at bottom.

# ─── 4. Gamepad smoke test (with controller plugged in) ────────
# In browser DevTools console:
#   navigator.getGamepads().filter(p => p).map(p => p.id)
# Expected: an array containing your Xbox controller's ID string.

# ─── 5. Move attempt (any controller, or arrow keys + Enter) ──
# D-pad the cursor to (4,5). Press A (or Enter on keyboard).
# Watch:
#   - Token visibly moves
#   - Narrative log gets a new italic "action" entry
#   - Bottom bar's MOVE counter decrements
#   - Audio "confirm" chord plays
```

If all five pass, **MVP is live** and your family can play.

---

## 7. Known Limitations (Honest Inventory)

Calling these out so you can sanity-check the cut line and prioritize v0.2.

| Limitation | Workaround | Fix in |
|---|---|---|
| Freeform requires keyboard | Wireless KB on coffee table; voice-to-text via Whisper is the real fix | v0.3 |
| No combat / dice rolls | Narrate fights as freeform; AI improvises outcomes (validator caps HP damage at 8/turn) | v0.2 |
| Single room | The party can't actually leave The Crooked Tankard yet | v0.2 |
| Movement budget doesn't reset | After spending all 30ft, the character is frozen until you manually edit `state.json` and reload | v0.2 (turn-end logic) |
| No save slots | One campaign, one timeline. Restore-from-backup = `cp state.json.bak state.json` | v0.3 |
| LAN trust assumed | Anyone on your WiFi can hit the API. Fine for family; not fine for streaming | v0.4 |
| No Aether panel yet | StoryForge state is filesystem-accessible; panel is a Pass 4 task in the Aether repo | Aether-side |

---

## 8. Cleanup Commit Sequence

For your dual-remote workflow, here's the recommended commit cadence to land Pass 3:

```fish
cd ~/projects/storyforge

# Backend closures
git add src/storyforge/api/routes_state.py \
        src/storyforge/**/__init__.py \
        data/seeds/default_campaign.json
git commit -m "feat(backend): close routing gaps + seed Crooked Tankard campaign

- Add GET /api/state, /api/character/{id}, /api/room/{id}, /api/revision
- Seed 10x8 tavern with 4 PCs (Kael/Lyra/Thorne/Whisper) pre-placed
- Add package __init__.py markers"

# Frontend HTML + CSS
git add frontend/index.html frontend/css/
git commit -m "feat(frontend): 10-foot UI shell with parchment theme

- HTML layout: portrait strip / canvas / log / action bar
- CSS: 1.5rem base scaling to 4K, three parchment themes,
  ink effects (gilded/arcane/glitter/bloodied)"

# Frontend JS
git add frontend/js/
git commit -m "feat(frontend): Konva canvas + Xbox gamepad + procedural audio

- canvas.js: HiDPI Konva stage, marching-ants cursor, 3-layer grid
- gamepad.js: 4-controller polling with edge detection and dpad repeat
- audio.js: Web Audio procedural SFX (cursor/confirm/deny/chime/page)
- main.js: WS-driven state sync, gamepad → action wiring
- characters.js + log.js: portrait switcher and chronicle feed"

# Push to both remotes (your dual-remote insurance pattern)
git push origin main
git push gitlab main
```

---

## 9. What's Next (v0.2 Targets)

When you're ready to keep building:

1. **Combat loop.** Initiative roll, turn order, attack actions on the grid (click an enemy token instead of an empty cell), damage application going through the validator.
2. **Room transitions.** The door at `(5,7)` actually leads somewhere. Add a `room_transitions` table to GameState; `interact` on a door swaps `current_room_id` and repositions all PCs.
3. **Movement reset.** End-of-turn button or auto-detection that restores `movement_remaining` to `speed`.
4. **Aether panel.** A NodeGraphQt or QTreeView widget that mounts the live state via the `event_bus` subscription pattern.
5. **Voice-to-text.** Hook `speech_recognition` (browser native) or local Whisper into the freeform modal — Y to open mic, hold to dictate, release to commit.

---

## 10. One Final Sanity Check

Before you run the bootstrap and dev scripts, verify the final directory structure looks like this:

```
storyforge/
├── .env                              ← STORYFORGE_GEMINI_API_KEY=...
├── pyproject.toml
├── scripts/
│   ├── bootstrap.fish
│   └── dev.fish
├── src/storyforge/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py
│   │   ├── routes_state.py
│   │   ├── routes_action.py
│   │   └── ws_session.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── state_manager.py
│   │   ├── grid.py
│   │   ├── rules.py
│   │   └── validators.py
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── client.py
│   │   ├── narrator.py
│   │   ├── interpreter.py
│   │   └── prompts/
│   │       ├── system_dm.md
│   │       ├── narrate_movement.md
│   │       ├── interpret_freeform.md
│   │       └── schemas/state_diff.schema.json
│   ├── persistence/
│   │   ├── __init__.py
│   │   └── snapshot.py
│   └── events/
│       ├── __init__.py
│       └── bus.py
├── frontend/
│   ├── index.html
│   ├── css/
│   │   ├── styles.css
│   │   ├── parchment.css
│   │   └── ink-effects.css
│   └── js/
│       ├── main.js
│       ├── api.js
│       ├── canvas.js
│       ├── gamepad.js
│       ├── audio.js
│       ├── log.js
│       └── characters.js
└── data/
    ├── seeds/default_campaign.json
    └── campaigns/family_campaign_01/state.json   ← populated by bootstrap
```

Run `./scripts/bootstrap.fish` then `./scripts/dev.fish`, plug the TV into the EliteDesk via HDMI, kick on the four controllers, and the Crooked Tankard is open for business.

---

**The MVP is shipped. Pass on what you've heard.** 🎲

If anything breaks on first run, the verification checklist in Section 6 is your triage flow — each step isolates one layer. Most likely failure: Konva not loading from CDN if the TV is on a captive-portal WiFi. Fallback is downloading `konva.min.js` to `frontend/js/vendor/` and updating the script tag.
