# StoryForge Roadmap

This document tracks the high-level progress and future milestones of StoryForge.

## 🏁 Current Status: The Great Godot Pivot
We are currently transitioning from a web-based (HTML/JS/Konva.js) frontend to a high-fidelity **2.5D Godot Engine** client. The Python backend remains the authoritative "Brain."

---

## 🗺️ Milestones

### ✅ Milestone 1: Foundations (Web MVP) - COMPLETE
- [x] Python FastAPI Backend with D&D 5e logic.
- [x] Gemini 3.5 Flash AI DM integration.
- [x] HTML5 Canvas renderer with 8-bit sprites.
- [x] Google OAuth2 Desktop Authentication.
- [x] Persistence (Campaign Saves).
- [x] Standalone Windows executable via PyInstaller.

### 🏗️ Milestone 2: The Godot Overhaul - IN PROGRESS
- [x] Formalized 2.5D "Living Lorebook" Design.
- [x] Scaffolding Godot project structure.
- [x] `PythonClient.gd` communication bridge (HTTP/WebSockets).
- [x] Update `main.py` to orchestrate dual-process launch.
- [x] Implement 3D Tabletop scene with parchment shader.
- [x] Integrate 2.5D Billboard sprites (Foundations).
- [ ] **Next Task**: Recreate Character Forge UI in Godot (Focus: 'Before' vs 'After' Transition).
- [x] Implement Google OAuth2 login flow within Godot UI.

### 🔮 Milestone 3: Cinematic Polish - PLANNED
- [ ] Dynamic 3D lighting and shadows.
- [ ] Godot Particle effects for magic and Paradox glitches.
- [ ] Gimbal Camera with depth-of-field.
- [ ] Integrated audio engine (FMOD/Godot Audio).

### 🚀 Milestone 4: Final Release - PLANNED
- [ ] Unified Windows Release packaging (Godot + Python).
- [ ] Steam/Itch.io distribution preparation.
- [ ] Final lorebook & asset optimization.

---

## 🛠️ Instructions for Agents
When picking up this project:
1.  **Backend**: Located in `src/`. Do not break the API contract used by the frontend.
2.  **Frontend**: The legacy web frontend is in `frontend/`. All new visual work must happen in `godot/`.
3.  **Communication**: Godot talks to Python on `localhost:8765`.
4.  **Verification**: Always ensure the Python server is running before testing the Godot client.
