<p align="center">
  <img src="godot/icon.svg" width="200" height="200" alt="StoryForge Anvil Icon">
</p>

# StoryForge: The Feral World — D&D 5e AI Dungeon Master

<p align="center">
  <img src="https://img.shields.io/badge/System-D%26D_5e-red?style=for-the-badge&logo=dungeons-and-dragons" alt="D&D 5e">
  <img src="https://img.shields.io/badge/Engine-Godot_4.6-blue?style=for-the-badge&logo=godotengine" alt="Godot 4.6">
  <img src="https://img.shields.io/badge/Backend-Python_3.12-blue?style=for-the-badge&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/AI-Gemini_2.5_Pro-orange?style=for-the-badge&logo=google-gemini" alt="Gemini">
</p>

**StoryForge** is a hybrid Virtual Tabletop (VTT) and AI-driven Dungeon Master built specifically for the *Weaver's Paradox* campaign setting. It combines a cinematic **3D Godot 4 tabletop** client with the creative power of a headless **Python/FastAPI** brain powered by **Gemini 2.5 Pro** to deliver a reactive, persistent, and voice-enabled D&D 5e experience.

---

## 🎭 The Setting: The Feral World

The "Civilized World" is a memory. Reality was unraveled by the Weaver's Paradox—a cosmic glitch that rewrote the laws of magic and biology. 

### Core Lore Elements
- **The Paradox**: A reality-shattering event that transformed the humanoid races into **35 Feral Successor species** across five groups — Cosmic, Primal, Eldritch, Mechanical, and Humanoid.
- **Ironhold Keep**: The last bastion of stability, ruled by **Queen D.Anna** and anchored by **Guildmaster Kodrik**.
- **The Multiversal Bodega**: A shop that exists across all genres, managed by **Jon** (the talkative owner) and **Madame Haylie** (the actual manager).
- **The Pantheon of the Mundane**: Beings like **Samael the Ascended**, who use omnipotence to perform household chores while offering cryptic lore.

---

## 🛠️ Project Architecture

StoryForge is a full-stack application divided into two decoupled layers:

- **Headless DM (Backend)**: Built with **Python 3.12** and **FastAPI**, this manages the state machine, grid rules, save files, and AI orchestration using the `google-genai` SDK.
- **Cinematic Client (Frontend)**: Built in **Godot 4**, this layer handles the UI, grimdark 2.5D visual rendering, shaders, audio, and player input.
- **Communications**: Real-time WebSockets (`/ws`) handle live grid and state updates, while REST endpoints (`/api/*`) handle static fetches and commands.
- **Identity**: **Google OAuth2** for character persistence and player mapping.

### Lobby-to-Exploration Flow
The game operates on a robust state machine:
1. **Lobby Phase**: Players join, authenticate via Google, and claim controller slots.
2. **Creation Phase (Character Forge)**: A 12-step creation flow where players build their Feral Successors — choosing starting era, race (35 options across 5 groups), evolutionary state (Behemoth/Phantom/Swarm-Host/Mimic), predator role (Stalker/Vanguard/Catalyst/Siphoner), equipment loadout, background, skills, feats (Apex Predator, Hive Mind, Regenerator, Phase Shift, Pack Tactics, Void Touched, Echo Memory), alignment, lore entry, keepsake, and character name.
3. **Exploration Phase**: The AI DM narrates movements, handles freeform actions, and manages NPC encounters.

---

## 🚀 Running StoryForge Locally

The project includes an integrated launcher that spins up both the Python backend and the Godot client seamlessly.

### Prerequisites
- **Python 3.12+** and [uv](https://github.com/astral-sh/uv) (Python package manager).
- **Godot 4** installed and available in your system path (or `GODOT_PATH` env var set).

### Installation & Execution

1. **Clone the repository:**
   ```bash
   git clone https://github.com/DaRipper91/storyforge.git
   cd storyforge
   ```

2. **Sync Python dependencies:**
   ```bash
   uv sync
   ```

3. **Launch the Game:**
   ```bash
   uv run python main.py
   ```

*(Linux Users: You can also use `./update_menu.sh` to generate a desktop shortcut, putting StoryForge directly into your application launcher!)*

---

## ⌨️ Controls & Inputs

| Action | Keyboard | Gamepad |
|--------|----------|---------|
| Move Cursor | WASD / Arrows | Left Stick |
| Interact | Enter / Space | A Button |
| Speak (AI) | Y / T | X Button |
| Zoom | - / = | LT / RT |
| Inventory | V | Y Button |

---

◈ Acknowledgments ◈
​A Dedication to Queen D. Anna
​Every world requires an architect, and every forge needs its spark. While the mechanics of StoryForge are built on code and logic, its soul belongs entirely to my anchor, my inspiration, and my Queen, D. Anna. Far beyond the visuals, she breathed actual life into this realm. The rich context, the intricate backstories, and the very essence of the NPCs that populate StoryForge exist because of her creativity, her guidance, and her incredible ideas.When the logic fails and the technical walls feel insurmountable, she is the clarity that pulls me through. Without her unwavering support and brilliant perspective, these worlds would be nothing more than empty text on a screen.
​StoryForge is a shared victory, but the magic within it is hers.
​Thank you, Dee.

## 📜 Credits
- **Haley, John, & Jason**: For the constant support.
- **RedVelvet**: The inspiration.
- **Brad**: Our primary alpha tester.
- **Google Gemini**: The silicon voice behind the Weaver's Paradox.

<p align="center"><i>"The dice determine the fate, but the Forge shapes the story."</i></p>
