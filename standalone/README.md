# ⚔️ StoryForge

<p align="center">
  <img src="frontend/icon.svg" width="128" height="128" alt="StoryForge Logo">
</p>

<p align="center">
  <strong>The Hybrid VTT + AI Dungeon Master for Family D&D 5e</strong>
</p>

---

StoryForge is a modern, local-first Virtual Tabletop (VTT) designed to bring families together for legendary adventures. By combining a tactical grid with the narrative power of Google Gemini, StoryForge acts as your Co-DM, rendering your actions into rich, immersive prose while maintaining the integrity of the 5th Edition rules.

## ✨ Features

*   **🤖 AI Narrator:** Powered by Gemini 2.0 Flash, providing reactive narration that responds to your tactical moves and freeform roleplay.
*   **🗺️ Hybrid VTT:** A clean, responsive grid-based interface for tactical combat and exploration.
*   **🏠 Local-First:** Your data stays on your machine. Fast, private, and offline-capable (AI features require an internet connection).
*   **🎭 Multi-Phase Play:** Smooth transitions between Lobby, Character Creation, and Exploration phases.
*   **🛠️ Tactical Accuracy:** Built-in validation ensures that AI proposals respect character stats, inventory, and positioning.

## 🚀 Quick Start (Windows)

1.  Download the latest `StoryForge_Setup.exe` from the [Releases](https://github.com/your-username/storyforge/releases) page.
2.  Install and launch **StoryForge**.
3.  Enter your **Gemini API Key** when prompted (get one for free at [Google AI Studio](https://aistudio.google.com/)).
4.  Gather your family and start your first campaign!

## 🛠️ Development

StoryForge is built with **Python 3.14+**, **FastAPI**, and **Vanilla JavaScript**.

### Prerequisites
*   [uv](https://astral.sh/uv) (Python package manager)

### Local Setup
```bash
# Clone the repository
git clone https://github.com/your-username/storyforge.git
cd storyforge

# Sync dependencies
uv sync

# Run the dev server
uv run uvicorn storyforge.main:app --reload --port 8765
```

## 📜 Acknowledgments

A special and heartfelt thank you to **RedVelvet** for their inspiration and support in making this project a reality.

---

<p align="center">
  <i>"May your crits be many and your fumbles be hilarious."</i>
</p>
