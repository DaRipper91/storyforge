# 🗡️ StoryForge

<p align="center">
  <img src="https://img.shields.io/badge/System-D%26D_5e-red?style=for-the-badge&logo=dungeons-and-dragons" alt="D&D 5e">
  <img src="https://img.shields.io/badge/Engine-Python_3.14-blue?style=for-the-badge&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/AI-Gemini_Flash-orange?style=for-the-badge&logo=google-gemini" alt="Gemini">
  <img src="https://img.shields.io/badge/Platform-Arch%20%2F%20Asahi%20%2F%20Termux-lightgrey?style=for-the-badge&logo=arch-linux" alt="Platform">
</p>

---

## 📜 The Prophecy
**StoryForge** is a hybrid Virtual Tabletop (VTT) and AI-driven Dungeon Master designed for a private family campaign. It bridges the gap between the strict, tactical grid combat of digital board games and the limitless narrative freedom of classic pen-and-paper roleplaying.

Built to run locally on an **Arch/Asahi Linux or Termux** environment, it serves as a specialized node within the **Project Aether** ecosystem.

---

## ⚔️ The Hybrid Logic Loop
StoryForge operates on a dual-engine architecture:

1.  **The Python Referee (The Logic):** The absolute source of truth. Manages character sheets, grid coordinates, and D&D 5e rules math.
2.  **The Gemini Narrator (The Soul):** Provides sensory descriptions, roleplays NPCs, and interprets creative player actions ("I swing from the chandelier!") into validated state changes.

---

## 🏰 Project Structure

```text
storyforge/
├── 📂 src/storyforge/     # The "Referee" (Python Logic)
│   ├── 📂 core/           # Rules, Models, & Validators
│   ├── 📂 ai/             # Gemini AI Integration & Prompts
│   └── 📂 api/            # FastAPI & WebSockets
├── 📂 static/             # The "Arena" (HTML5 Canvas UI)
├── 📂 data/               # Persistent Campaign JSON
└── 📂 scripts/            # Bootstrap & Launch Utilities
```

---

## 🕯️ Quick Start

### 1. Light the Forge
Ensure you have `uv` installed, then run the bootstrap script to prepare the environment and campaign seeds.

```fish
chmod +x bootstrap.fish
./bootstrap.fish
```

### 2. Attune your API Key
Add your Google AI Studio key to the `.env` file:
```env
STORYFORGE_GEMINI_API_KEY=your_secret_key_here
```

### 3. Enter the Realm
Launch the development server and open your browser to `http://127.0.0.1:8765`.

```fish
./scripts/dev.fish
```

---

## 🛡️ The Party
- **Kael** (Cody) — *The Indomitable Fighter*
- **Lyra** (Dee) — *The Arcane Weaver*
- **Thorne** (Nate) — *The Shadow Stalker*
- **Whisper** (Bray) — *The Silent Blade*

---

<p align="center">
  <i>"The dice determine the fate, but the Forge shapes the story."</i>
</p>
