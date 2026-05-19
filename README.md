# 🗡️ StoryForge: Feral Successors

<p align="center">
  <img src="https://img.shields.io/badge/System-D%26D_5e-red?style=for-the-badge&logo=dungeons-and-dragons" alt="D&D 5e">
  <img src="https://img.shields.io/badge/Engine-Python_3.14-blue?style=for-the-badge&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/AI-Gemini_3.5_Flash-orange?style=for-the-badge&logo=google-gemini" alt="Gemini">
  <img src="https://img.shields.io/badge/Platform-Desktop_/_Android_/_Linux-lightgrey?style=for-the-badge&logo=appveyor" alt="Platform">
</p>

---

## 📜 The Prophecy: The Weaver's Paradox
**StoryForge** has evolved. The world has been shattered by the Weaver's Paradox, and the "civilized" races have fallen. You play as the **Feral Successors**—15 unique, wild, and cunning races (from the digital *Signal-Shades* to the celestial *Sun-Sovereigns*) surviving in a multiverse that has "refused" its original design.

This is a hybrid Virtual Tabletop (VTT) and AI-driven Dungeon Master that bridges tactical grid combat with the snarky, reactive narration of a world-weary DM.

---

## ⚔️ The "Specimen" Architecture
Instead of static classes, StoryForge uses an evolutionary hybrid system:
1.  **Evolutionary State (The Body):** Choose your physical chassis (*Behemoth, Phantom, Swarm-Host, or Mimic*).
2.  **Predator Role (The Mind):** Choose your tactical hunting style (*Stalker, Vanguard, Catalyst, or Siphoner*).
3.  **Point-Buy Evolution:** Spend Evolution Points (EP) across four trees to mutate your abilities as you level up.

---

## 🏰 Cross-Platform Support
StoryForge is now a standalone application available for:
*   **Windows:** Standalone `.exe`
*   **Android:** Fully functional `.apk`
*   **Linux:** `.deb`, `.rpm`, `.pkg.tar.zst`, and `.AppImage`

All builds are managed automatically via GitHub Actions.

---

## 🕯️ Quick Start

### 1. Light the Forge
Ensure you have `uv` installed, then run the bootstrap script to prepare the environment.

```fish
chmod +x bootstrap.fish
./bootstrap.fish
```

### 2. Attune your AI
Add your Google AI Studio key to the `.env` file. StoryForge is optimized for **Gemini 3.5 Flash**.
```env
STORYFORGE_GEMINI_API_KEY=your_secret_key_here
```

### 3. Launch the Specimen
To run the desktop GUI:
```bash
uv run python src/storyforge/gui.py
```

---

## 🛡️ Special Thanks & Credits

*   **Jason:** For the indispensable fire-safety protocol. Without him, we wouldn't know to "kill it with fire!" whenever a Wizard (or a Cinder-Kin) gets too enthusiastic.
*   **RedVelvet:** A special thanks for the inspiration.
*   **Gemini 3.5 Flash:** For being the snarkiest DM in the multiverse.

---

<p align="center">
  <i>"The dice determine the fate, but the Forge shapes the story."</i>
</p>
