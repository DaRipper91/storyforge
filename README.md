# StoryForge: Feral Successors

<p align="center">
  <img src="https://img.shields.io/badge/System-D%26D_5e-red?style=for-the-badge&logo=dungeons-and-dragons" alt="D&D 5e">
  <img src="https://img.shields.io/badge/Engine-Python_3.14-blue?style=for-the-badge&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/AI-Gemini_3.5-orange?style=for-the-badge&logo=google-gemini" alt="Gemini">
  <img src="https://img.shields.io/badge/Platform-Linux_%2F_Windows_%2F_Android-lightgrey?style=for-the-badge" alt="Platform">
</p>

A hybrid Virtual Tabletop (VTT) and AI Dungeon Master for family D&D 5e — built desktop-first with a native window, gamepad support, and a custom species system built around the Weaver's Paradox setting.

---

## Setting

The "civilized" races have fallen. The **Feral Successors** — 15 unique species spanning Sci-Fi, Mythic, and Eldritch themes — survive in a multiverse that refused its own design. The AI (Gemini) narrates the world reactively; the Python referee enforces the rules deterministically.

---

## Character System

Characters are built from three orthogonal choices — not classes:

| Choice | Options |
|--------|---------|
| **Race** (15 total) | Signal-Shade, Sun-Sovereign, Cinder-Kin, and 12 more |
| **Evolutionary State** | Behemoth · Phantom · Swarm-Host · Mimic |
| **Predator Role** | Stalker · Vanguard · Catalyst · Siphoner |

Ability scores use the standard D&D array `[15, 14, 13, 12, 10, 8]` distributed across STR/DEX/CON/INT/WIS/CHA with racial bonuses applied on top.

---

## Running Locally

All commands use `uv`. No npm, no build step.

```bash
# Install dependencies
uv sync

# Dev server (hot-reload)
uv run uvicorn storyforge.main:app --reload --host 127.0.0.1 --port 8765 --reload-dir src
# or
fish scripts/dev.fish

# Desktop app (native window)
uv run storyforge
```

App served at `http://127.0.0.1:8765`. Swagger UI at `/docs`.

---

## Configuration

Copy `.env` and set your key:

```env
STORYFORGE_GEMINI_API_KEY=your_google_ai_studio_key
STORYFORGE_GEMINI_MODEL=gemini-2.0-flash-exp
STORYFORGE_CAMPAIGN_ID=family_campaign_01
```

All settings use the `STORYFORGE_` prefix via `pydantic-settings`. Campaign state is saved automatically to `data/campaigns/<campaign_id>/state.json`.

---

## Architecture

**FastAPI** backend → **vanilla JS** frontend → **Konva.js** grid renderer. State is local-first and JSON-snapshotted to disk. The desktop app wraps everything in a native window via **pywebview + PyQt6**.

```
Player action
  → POST /api/action/grid or /api/action/freeform
  → rules.check_grid_action()        # deterministic legality
  → state_manager.apply_*()          # locked mutation + disk snapshot
  → Gemini narration                 # flavor text only, never state
  → EventBus → WebSocket broadcast
```

AI outputs are proposals only — `validators.sanitize()` gates every `StateDiff` before it touches state. Prompts are Markdown files in `src/storyforge/ai/prompts/`, not f-strings.

---

## NPC Encounters

Five interactive NPCs in The Crooked Tankard:

| NPC | Encounter |
|-----|-----------|
| **Jon** | Travelling merchant — buy gear, attempt to escape his monologues |
| **Samael the Ascended** | Lore oracle — consult on setting history and mysteries |
| **Madame Haylie** | Inn keeper — room, rest, and rumor |
| **Queen D.Anna** | Court official — formal address protocol, petition for boons |
| **Firey RedVelvet** | Bard — tip, heckle, or request songs; mood affects the performance |

---

## Controls

| Input | Action |
|-------|--------|
| WASD / Arrow keys | Move cursor |
| Enter / F / Space | Confirm / interact |
| I / X | Inspect cell |
| Y / T | Speak (freeform) |
| - / = | Zoom out / in |
| Tab / Shift-Tab | Cycle active character |
| V | Toggle inventory |
| K / ? | Toggle keymap |
| LT / RT (gamepad) | Zoom out / in |

Gamepad (Xbox layout) is fully supported. UI scale and game zoom are adjustable in **View → Settings**.

---

## Builds

Cross-platform builds are automated via GitHub Actions:

- **Linux** — `.deb`, `.rpm`, `.pkg.tar.zst`, `.AppImage`
- **Windows** — standalone `.exe`
- **Android** — `.apk`

---

## Credits

- **Haley** — the most awesome cuz ever, and for all the laughs
- **John** — for everything he's taught me, and for never giving up, even when I made it ever so difficult
- **Jason** — for being the brother I never had, and a friend when I needed one the most
- **RedVelvet** — inspiration
- **Gemini 3.5** — the DM

---

<p align="center"><i>"The dice determine the fate, but the Forge shapes the story."</i></p>
