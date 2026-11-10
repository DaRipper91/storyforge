<p align="center">
  <img src="docs/assets/banner.svg" alt="StoryForge survey plate: Ironhold Keep and its seeded NPCs" width="100%">
</p>

<p align="center">
  <b>A tabletop and AI dungeon master for a family D&amp;D 5e campaign.</b><br>
  <i>Gemini narrates. Python decides.</i>
</p>

StoryForge is a virtual tabletop for *Weaver's Paradox: The Feral World*. The Godot client presents the campaign; a Python service owns game state, validates actions, and saves local snapshots. Gemini can narrate and suggest outcomes, but its proposals pass through the rules before they can change the game.

> **Preview note:** Race and species sheets are concept art; hero turnarounds are Blender asset renders, not gameplay screenshots. The banner is drawn from the campaign seed data. Bryttan's appearance below interprets a text brief because the PDF export had no usable character image.

## Latest visual direction

The setting has 35 custom species across five groups. These realistic race-card sheets are the latest group previews. The animated reel links the full concept-sheet set, with turnarounds and material studies for all 35 species.

| Cosmic | Primal | Eldritch |
|---|---|---|
| <img src="docs/assets/races-cosmic.png" alt="Latest realistic race cards: Voidwraith, Nullshade, Iron-Locust, Embervein and Riftwalker" width="100%"> | <img src="docs/assets/races-primal.png" alt="Latest realistic race cards: Solar-Lord, Thornmimic, Cinderkin, Deep-Tyrant and Grimcrow" width="100%"> | <img src="docs/assets/races-eldritch.png" alt="Latest realistic race cards: Bloodweaver, Dreamhusk, Bonedrifter, Mindspider and Chaosling" width="100%"> |

| Mechanical | Humanoid | All 35 concepts |
|---|---|---|
| <img src="docs/assets/races-mechanical.png" alt="Latest realistic race cards: Ironveil, Forgespawn, Cinderplate, Hexgear and Wirewraith" width="100%"> | <img src="docs/assets/races-humanoid.png" alt="Latest realistic race cards for 15 humanoid species" width="100%"> | <img src="docs/assets/concept-reel.webp" alt="Animated reel cycling through concept sheets for all 35 species" width="100%"> |

### Bespoke 3D heroes

The Godot project contains 23 bespoke, rigged hero models across the five species groups. These five sheets show Blender turnarounds; twelve species still use the shared character-card art while their bespoke models are pending. The hero system also uses a shared procedural humanoid animation set.

| Ashenborn | Ironfast | Glitchkin |
|---|---|---|
| <a href="docs/assets/heroes/ashenborn.webp"><img src="docs/assets/heroes/ashenborn.webp" alt="Ashenborn bespoke 3D hero, front, side and back Blender renders" width="100%"></a> | <a href="docs/assets/heroes/ironfast.webp"><img src="docs/assets/heroes/ironfast.webp" alt="Ironfast bespoke 3D hero, front, side and back Blender renders" width="100%"></a> | <a href="docs/assets/heroes/glitchkin.webp"><img src="docs/assets/heroes/glitchkin.webp" alt="Glitchkin bespoke 3D hero, front, side and back Blender renders" width="100%"></a> |

| Forgespawn | Ironveil | All species concepts |
|---|---|---|
| <a href="docs/assets/heroes/forgespawn.webp"><img src="docs/assets/heroes/forgespawn.webp" alt="Forgespawn bespoke 3D hero, front, side and back Blender renders" width="100%"></a> | <a href="docs/assets/heroes/ironveil.webp"><img src="docs/assets/heroes/ironveil.webp" alt="Ironveil bespoke 3D hero, front, side and back Blender renders" width="100%"></a> | <img src="docs/assets/concept-reel.webp" alt="Animated concept reel for all 35 species" width="100%"> |

### New NPC: Bryttan Wolfholt

Bryttan is the Wolfguard, a vigilant shieldwarden at Ironhold Keep. Her seeded look is built from the shared rigged warrior model with cobalt wolf insignia, a power-core pack, a blue shard pendant, and a rune-etched survival dagger. She is an interactable named NPC, paired in the setting with Evangeline Wolfholt.

Her Godot appearance is assembled from mesh details and material overrides without modifying the shared source model. It interprets the PDF's text description; it is not presented as a recreation of missing reference art.

## Play locally

### Requirements

- Python 3.12+ and [uv](https://github.com/astral-sh/uv)
- Godot 4.6 (CI pins 4.6.2)
- A Google AI Studio key for the default remote backend; no key is needed for local mode

### Remote backend

```bash
git clone https://github.com/DaRipper91/storyforge.git
cd storyforge
uv sync
cp .env.example .env  # set STORYFORGE_GEMINI_API_KEY
uv run python main.py
```

`main.py` starts the API server and launches Godot when it is available on `PATH`. To run the components separately, use `uv run uvicorn storyforge.main:app --host 127.0.0.1 --port 8765` and `godot --path godot` in separate terminals.

### Local backend

```bash
./scripts/launch_offline.sh
# or: godot --path godot -- --backend=local
```

The local backend stores campaign snapshots under Godot's `user://campaigns/`. AI NPC encounters and freeform text require the remote narrator and are unavailable offline. See [offline mode](docs/offline/LOCAL_BACKEND.md).

## How the game protects state

Grid actions are checked by deterministic Python rules. Freeform play asks Gemini for a narrative and an optional `StateDiff`; `validators.sanitize()` rejects disallowed fields and values before anything reaches `StateManager`. Both paths commit through the same serialized write path, which increments the revision, writes an atomic snapshot, and publishes state updates to Godot over a WebSocket.

```text
Godot client → FastAPI action route → rules or Gemini proposal
                                     → validation → StateManager commit
                                     → snapshot + event bus → Godot update
```

Core rules do not import AI, API, or persistence modules. NPC encounter services return proposals to the caller and do not mutate game state directly.

## Development

```bash
uv sync --dev
uv run pytest -q
```

The Python suite covers character creation, validators, routes, and golden behavior. Godot suites are separate; see [tests/golden/README.md](tests/golden/README.md). The seed campaign lives in [data/seeds/default_campaign.json](data/seeds/default_campaign.json).

### Current status

- **Available:** 35-species character creation, 23 bespoke hero models, tabletop exploration, Python API, local snapshot saves, validator-gated Gemini proposals, and NPC encounters.
- **NPC update:** Bryttan Wolfholt is seeded in Ironhold Keep and uses the existing rigged character pipeline with a composed appearance.
- **In progress:** bespoke models for the remaining 12 species, real-device verification for the offline Android build and touch controls; combat remains deferred.
- **Offline limits:** NPC encounter routes return 503 and freeform text returns 501 because those features require the AI narrator.

Read the [project docs](docs/README.md) and [roadmap](ROADMAP.md) for more detail.

## Acknowledgments

StoryForge's setting and NPCs grew from Deanna's stories, ideas, and guidance. Thanks to Haley, John, Jason, and Brad for their support, and to Google Gemini for helping shape the narrator.

<p align="center"><i>“The dice determine the fate, but the Forge shapes the story.”</i></p>
