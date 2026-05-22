# StoryForge: The Feral World — D&D 5e AI Dungeon Master

<p align="center">
  <img src="https://img.shields.io/badge/System-D%26D_5e-red?style=for-the-badge&logo=dungeons-and-dragons" alt="D&D 5e">
  <img src="https://img.shields.io/badge/Engine-Python_3.12-blue?style=for-the-badge&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/AI-Gemini_3.5_Flash-orange?style=for-the-badge&logo=google-gemini" alt="Gemini">
  <img src="https://img.shields.io/badge/Platform-Windows_10_Exec-lightgrey?style=for-the-badge" alt="Platform">
</p>

**StoryForge** is a hybrid Virtual Tabletop (VTT) and AI-driven Dungeon Master built specifically for the *Weaver's Paradox* campaign setting. It combines a structured 2D grid engine with the creative power of **Gemini 3.5 Flash** to deliver a reactive, persistent, and voice-enabled D&D 5e experience.

---

## 🎭 The Setting: The Feral World

The "Civilized World" is a memory. Reality was unraveled by the Weaver's Paradox—a cosmic glitch that rewrote the laws of magic and biology. 

### Core Lore Elements
- **The Paradox**: A reality-shattering event that transformed the humanoid races into **Feral Successors**.
- **Ironhold Keep**: The last bastion of stability, ruled by **Queen D.Anna** and anchored by **Guildmaster Kodrik**.
- **The Multiversal Bodega**: A shop that exists across all genres, managed by **Jon** (the talkative owner) and **Madame Haylie** (the actual manager).
- **The Pantheon of the Mundane**: Beings like **Samael the Ascended**, who use omnipotence to perform household chores while offering cryptic lore.

---

## 🛠️ Project Architecture

StoryForge is a full-stack Python application designed for zero-config deployment:

- **Backend**: **FastAPI** provides the core engine, managing the state machine, grid rules, and AI orchestration.
- **Frontend**: A high-performance **Vanilla JS** application utilizing **Konva.js** for the grid renderer.
- **Desktop Wrapper**: Uses **pywebview** and **PyQt6** to provide a native Windows experience with gamepad support.
- **AI Brain**: Integrated with **google-generativeai**, pinned to **Gemini 3.5 Flash** for high-speed agentic responses.
- **Identity**: **Google OAuth2 (Desktop App Flow)** for character persistence and player mapping.

### Lobby-to-Exploration Flow
The game operates on a robust state machine:
1. **Lobby Phase**: Players join, authenticate via Google, and claim controller slots.
2. **Creation Phase**: Players build their Feral Successors (Race, Evolutionary State, Predator Role).
3. **Exploration Phase**: The AI DM narrates movements, handles freeform actions, and manages NPC encounters.

---

## 🚀 Tester Installation Guide (Windows)

Welcome to the StoryForge alpha! Follow these steps to join the Feral World:

### 1. Download the Release
Go to the [Releases](https://github.com/your-repo/storyforge/releases) page and download `StoryForge.exe`.

### 2. Launch the Application
Double-click `StoryForge.exe`. Windows may show a "SmartScreen" warning—click **"More Info"** -> **"Run Anyway"**.

### 3. Authentication (Critical Step)
During the lobby phase, you will be prompted to log in with Google. 
- A browser window will open automatically.
- Because this is an alpha application, Google will show an **"Unverified App"** screen.
- **ACTION**: Click **"Advanced"** and then click **"Go to StoryForge (unsafe)"**.
- This is required for the local Desktop App Flow to capture your identity and save your `token.json` for future sessions.

### 4. Gameplay
Once logged in, you can create your character and begin exploring. Use a keyboard or an Xbox-style gamepad.

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

## 📜 Credits
- **Haley, John, & Jason**: For the constant support and testing.
- **RedVelvet**: The inspiration for the bardic fire.
- **Brad**: Our primary alpha tester.
- **Google Gemini**: The silicon voice behind the Weaver's Paradox.

<p align="center"><i>"The dice determine the fate, but the Forge shapes the story."</i></p>
