# StoryForge Roadmap

This document tracks the high-level progress and future milestones of StoryForge.

## 🏁 Current Status: Final Release Polish
The Godot 4 3D tabletop client is complete. The Python backend remains the authoritative "Brain." Active work is on audio assets, balance validation, and CI distribution.

---

## 🗺️ Milestones

### ✅ Milestone 1: Foundations (Web MVP) - COMPLETE
- [x] Python FastAPI Backend with D&D 5e logic.
- [x] Gemini 3.5 Flash AI DM integration.
- [x] HTML5 Canvas renderer with 8-bit sprites.
- [x] Google OAuth2 Desktop Authentication.
- [x] Persistence (Campaign Saves).
- [x] Standalone Windows executable via PyInstaller.

### ✅ Milestone 2: The Godot Overhaul - COMPLETE
- [x] Formalized 2.5D "Living Lorebook" Design.
- [x] Scaffolding Godot project structure.
- [x] `PythonClient.gd` communication bridge (HTTP/WebSockets).
- [x] Update `main.py` to orchestrate dual-process launch.
- [x] Implement 3D Tabletop scene with parchment shader.
- [x] Integrate 2.5D Billboard sprites (Foundations).
- [x] Implement Google OAuth2 login flow within Godot UI.
- [x] Godot 4 3D dungeon geometry (BoxMesh walls/floors/doors/hazards).
- [x] 3D character minis with race-group glow colors.
- [x] Gimbal camera (orbit/zoom/R to reset).
- [x] Full Character Forge UI (12-step creation: era, race, state, role, equipment, background, skills, feats, alignment, lore, keepsake, name).
- [x] 35 Feral Successor portrait cards (atmospheric PIL generator).

### ✅ Milestone 3: Cinematic Polish - COMPLETE
- [x] Dynamic 3D lighting — WorldEnvironment, candlelit OmniLight with flicker, bloom + SSAO.
- [x] Godot Particle effects — ParadoxParticles (chromatic burst) + MagicBurst (golden sparkle).
- [x] Gimbal Camera — orbit (right-drag), zoom (scroll), DoF (CameraAttributesPractical), R to reset.
- [x] Audio infrastructure — AudioManager autoload, Music/SFX buses, play_ambient/sfx/npc_performance.
- [x] Synthesized placeholder audio assets — 27 .wav files (6 ambient, 5 RedVelvet performances, 16 SFX).
- [x] Particle triggers wired to all game events (freeform actions, Paradox phase change, NPC entrances, 8 NPC event SFX).

### 🚀 Milestone 4: Final Release - IN PROGRESS
- [x] Unified Windows Release packaging (Godot + Python).
  - `src/storyforge/launcher.py` — PyInstaller entry point (FastAPI thread + Godot subprocess).
  - `StoryForge.spec` — updated spec (removed pywebview, targets launcher.py).
  - `godot/export_presets.cfg` — Windows Desktop + Linux/X11 headless export presets.
  - `scripts/build.py` + `scripts/package_release.py` — build and zip pipeline.
- [x] Steam/Itch.io distribution preparation.
  - `.github/workflows/build.yml` — Godot export + Python build + release zip + itch.io butler push.
  - `.itch.toml` — itch.io manifest (entry point: StoryForge.exe).
  - Required GitHub secrets: `BUTLER_API_KEY`, `OAUTH_CLIENT_SECRET`.
  - Required GitHub vars: `ITCH_USER`, `ITCH_GAME`.
- [x] Final lorebook & asset optimization (portraits done).
  - [x] Sprite sheets for all 35 races (portrait cards done).
  - [ ] Replace synthesized .wav placeholders with real audio assets.
  - [ ] Final balance pass on ability score bonuses + NPC encounter state.

### 🎵 Milestone 5: Audio & Polish - PENDING
- [ ] Replace synthesized .wav placeholders with real audio assets.
- [ ] Final balance pass on ability score bonuses.
- [ ] Duplicate ability score server validation (`is_valid_standard_array` not yet called in creation route).
- [ ] CI itch.io publishing (needs `BUTLER_API_KEY` + `ITCH_USER`/`ITCH_GAME` GitHub secrets).

---

## 🛠️ Instructions for Agents
When picking up this project:
1.  **Backend**: Located in `src/`. Do not break the API contract used by the frontend.
2.  **Frontend**: The legacy web frontend is in `frontend/`. All new visual work must happen in `godot/`.
3.  **Communication**: Godot talks to Python on `localhost:8765`.
4.  **Verification**: Always ensure the Python server is running before testing the Godot client.
