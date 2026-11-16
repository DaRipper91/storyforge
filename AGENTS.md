# StoryForge Agent Guide & Invariants

Hybrid Virtual Tabletop (VTT) + AI Dungeon Master for family D&D 5e. Built with a FastAPI backend, vanilla JS and Godot 4 clients, local-first JSON snapshot state, and Gemini narrative renderer.

## Architecture & Invariants
1. **Python is the source of truth.** Gemini outputs are proposals — `validators.sanitize()` must gate every AI-proposed `StateDiff` before `state_manager.apply_diff()` is called. Never pass raw Gemini responses directly to `apply_diff`.
2. **All mutations go through `StateManager`.** Holds an `asyncio.Lock` that serializes concurrent writes. Every public mutator calls `_commit()`, which increments `revision`, atomically saves to disk, and fans out to the `EventBus`.
3. **Prompts are Markdown files on disk**, not f-strings (`src/storyforge/ai/prompts/*.md`).
4. **`core/` is pure logic — no I/O.** Never import from `ai/`, `api/`, or `persistence/` inside `core/`.
5. **Single Source of Truth:** `AGENTS.md` is canonical; `CLAUDE.md`, `GEMINI.md`, and `.cursorrules` are symlinks pointing directly to it.

## Verification & Development Commands
```bash
cd /home/daripper/Projects/storyforge

# Run test suite
.venv/bin/pytest tests/test_character_factory.py tests/test_quests.py tests/test_routes_lobby.py tests/test_routes_npc.py tests/test_validators.py

# Dev server
uv run uvicorn storyforge.main:app --reload --host 127.0.0.1 --port 8765 --reload-dir src

# Linting and formatting
uv run ruff check src/
uv run ruff format src/
```
