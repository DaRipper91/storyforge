# StoryForge: Feral Successors

<p align="center">
  <img src="https://img.shields.io/badge/System-D%26D_5e-red?style=for-the-badge&logo=dungeons-and-dragons" alt="D&D 5e">
  <img src="https://img.shields.io/badge/Engine-Python_3.14-blue?style=for-the-badge&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/AI-Gemini_2.0_Flash-orange?style=for-the-badge&logo=google-gemini" alt="Gemini">
  <img src="https://img.shields.io/badge/Platform-Linux_%2F_Windows_%2F_Android-lightgrey?style=for-the-badge" alt="Platform">
</p>

A hybrid Virtual Tabletop (VTT) and AI Dungeon Master for family D&D 5e — built desktop-first with a native window, gamepad support, and a custom species system built around the Weaver's Paradox setting.

---

## Setting: The Weaver's Paradox

The "civilized" races have fallen. The world has been reorganized by the Paradox. 

### The Era System
Players now choose their starting point in history:
- **Era: BEFORE (The Civilized World)**: Start as the race you were (Human, Elf, Security Drone). The world is polite but brittle, with "glitches" in reality hinting at the coming end.
- **Era: AFTER (The Feral World)**: The Paradox has already hit. You start as a **Feral Successor** — one of 20 unique species spanning Cosmic, Primal, Mechanical, and Eldritch themes.

**The Race Switch:** In "Before" campaigns, the DM can trigger the Paradox mid-game. The air screams, reality is rewritten, and all characters instantly transform into their Feral Successor forms.

---

## Authentication & Persistence

Integrated **Google OAuth2** allows players to sign in and bind their characters to their Google ID.
- **Cross-Device ownership:** Your heroes follow you across browser refreshes and different devices.
- **Secure Sessions:** JWT-based session management using HttpOnly cookies.

---

## Character System

Characters are built from four orthogonal choices:

| Choice | Options |
|--------|---------|
| **Era** | Before (Civilized) · After (Feral) |
| **Race** (20 total) | Ironveil, Ashenborn, Voidwraith, Hollowsong, and 16 more |
| **Evolutionary State** | Behemoth · Phantom · Swarm-Host · Mimic |
| **Predator Role** | Stalker · Vanguard · Catalyst · Siphoner |

Ability scores use the standard D&D array `[15, 14, 13, 12, 10, 8]` with racial bonuses applied on top.

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

Copy `.env` and set your keys:

```env
STORYFORGE_GEMINI_API_KEY=your_google_ai_studio_key
STORYFORGE_GEMINI_MODEL=gemini-2.0-flash-exp
STORYFORGE_GOOGLE_CLIENT_ID=your_google_client_id
STORYFORGE_JWT_SECRET=your_random_secret
STORYFORGE_CAMPAIGN_ID=family_campaign_01
```

All settings use the `STORYFORGE_` prefix via `pydantic-settings`.

---

## Architecture

**FastAPI** backend → **vanilla JS** frontend → **Konva.js** grid renderer. State is local-first and JSON-snapshotted to disk. The desktop app wraps everything in a native window via **pywebview + PyQt6**.

AI outputs are validated and sanitized by `core/validators.py` before being applied to the game state.

---

## NPC Encounters

The world is populated by reactive NPCs, each with unique mechanics:

| NPC | Role | Encounter |
|-----|------|-----------|
| **Jon (The Boss)** | Shopkeeper | Multiversal Bodega — buy gear, avoid his "Cousin Dale" stories. |
| **Madame Haylie** | Innkeeper | The Real Boss — managing the books, the inn, and Jon's monologues. |
| **Samael the Ascended** | Demigod | Lore Oracle — provides cryptic hints and opens jars with cosmic power. |
| **Queen D.Anna** | Sovereign | Formal Address Protocol — petition her for divine boons and mercy. |
| **Firey RedVelvet** | Bard | Tavern Performer — tip, heckle, or request songs. |
| **The Pets** | Companions | **Bink Bink** (Black Cat), **Cole** (Shadow Guardian), **Teddy** (Heavenly Protector of D.Anna), **Keeva** (Queen D.Anna's Angelic Hound). |

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

Gamepad (Xbox layout) is fully supported. UI scale (default 120%) and game zoom are adjustable in **View → Settings**.

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
- **Gemini 2.0 Flash** — the DM

---

<p align="center"><i>"The dice determine the fate, but the Forge shapes the story."</i></p>
