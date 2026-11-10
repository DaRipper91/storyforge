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

The Godot project contains 35 bespoke, rigged hero models across the five species groups. Each species has a Blender-authored GLB with its own silhouette, clothing or armor, equipment, and surface palette. The hero system uses the shared procedural humanoid animation set, and the humanoid models share the game's 49-bone rig.

The 12 humanoid species that had been using generic group bodies now have bespoke Blender models. These three front-view catalogs show all 15 humanoid species with their in-game clothing, armor, and equipment.

| Humanoid A | Humanoid B | Humanoid C |
|---|---|---|
| <img src="docs/assets/heroes/model_catalog_humanoid_a.png" alt="Front-view Blender catalog of five bespoke humanoid hero models" width="100%"> | <img src="docs/assets/heroes/model_catalog_humanoid_b.png" alt="Front-view Blender catalog of five bespoke humanoid hero models" width="100%"> | <img src="docs/assets/heroes/model_catalog_humanoid_c.png" alt="Front-view Blender catalog of five bespoke humanoid hero models" width="100%"> |

| Ashenborn | Ironfast | Glitchkin |
|---|---|---|
| <a href="docs/assets/heroes/ashenborn.webp"><img src="docs/assets/heroes/ashenborn.webp" alt="Ashenborn bespoke 3D hero, front, side and back Blender renders" width="100%"></a> | <a href="docs/assets/heroes/ironfast.webp"><img src="docs/assets/heroes/ironfast.webp" alt="Ironfast bespoke 3D hero, front, side and back Blender renders" width="100%"></a> | <a href="docs/assets/heroes/glitchkin.webp"><img src="docs/assets/heroes/glitchkin.webp" alt="Glitchkin bespoke 3D hero, front, side and back Blender renders" width="100%"></a> |

| Forgespawn | Ironveil | All species concepts |
|---|---|---|
| <a href="docs/assets/heroes/forgespawn.webp"><img src="docs/assets/heroes/forgespawn.webp" alt="Forgespawn bespoke 3D hero, front, side and back Blender renders" width="100%"></a> | <a href="docs/assets/heroes/ironveil.webp"><img src="docs/assets/heroes/ironveil.webp" alt="Ironveil bespoke 3D hero, front, side and back Blender renders" width="100%"></a> | <img src="docs/assets/concept-reel.webp" alt="Animated concept reel for all 35 species" width="100%"> |

### Feral World NPC turnarounds

These five realistic front, side, and back character studies follow the roles, equipment, and palettes in the November 10 Gemini design export. In that roster, **Dee is Queen D.Anna**; **The Mother is Bryttan Wolfholt**, paired with Evangeline. The PDF export preserves the written specifications but not the original uploaded concept sheets, so these images are new visual interpretations rather than copies of those sheets or finished in-game models.

| D.Anna (Dee) | Vyra Larkholt | Bryttan Wolfholt (The Mother) |
|---|---|---|
| <a href="docs/assets/npcs/danna-dee-feral-vanguard.png"><img src="docs/assets/npcs/danna-dee-feral-vanguard.png" alt="Queen D.Anna, called Dee in the Gemini roster, in front, side and back views with amber wolf gear and paired axes" width="100%"></a> | <a href="docs/assets/npcs/vyra-larkholt-freeblade.png"><img src="docs/assets/npcs/vyra-larkholt-freeblade.png" alt="Vyra Larkholt in front, side and back views with a blue Weave battle axe, scout gear and lantern" width="100%"></a> | <a href="docs/assets/npcs/bryttan-wolfholt-the-mother.png"><img src="docs/assets/npcs/bryttan-wolfholt-the-mother.png" alt="Bryttan Wolfholt in front, side and back views with a cobalt wolf crest, blue core pack and survival gear" width="100%"></a> |

| Evangeline Wolfholt | Caelyn Riven |
|---|---|
| <a href="docs/assets/npcs/evangeline-wolfholt-spark-scholar.png"><img src="docs/assets/npcs/evangeline-wolfholt-spark-scholar.png" alt="Young Evangeline in front, side and back views with her Spark codex, lantern and patchwork bunny" width="100%"></a> | <a href="docs/assets/npcs/caelyn-riven-wayfarer.png"><img src="docs/assets/npcs/caelyn-riven-wayfarer.png" alt="Caelyn Riven in front, side and back views in slate travel gear with a relic pouch, talisman and rune-touched hand axe" width="100%"></a> |

### More cast concepts

These additional turnarounds extend the seeded cast beyond the five characters in the Gemini export. Where the prompt files leave visual details open, the concept art uses restrained, practical designs that fit each character's role.

| Jon | Samael | Haylie |
|---|---|---|
| <a href="docs/assets/npcs/jon-multiversal-bodega.png"><img src="docs/assets/npcs/jon-multiversal-bodega.png" alt="Jon in front, side and back views as a warm, practical shopkeeper with a ledger and apron" width="100%"></a> | <a href="docs/assets/npcs/samael-ascended.png"><img src="docs/assets/npcs/samael-ascended.png" alt="Samael in front, side and back views in understated dark clothing, with a quietly otherworldly presence" width="100%"></a> | <a href="docs/assets/npcs/haylie-store-manager.png"><img src="docs/assets/npcs/haylie-store-manager.png" alt="Haylie in front, side and back views as a decisive store manager carrying her ledger" width="100%"></a> |

| Coco | Cinder | Mykael |
|---|---|---|
| <a href="docs/assets/npcs/coco-ember-hound.png"><img src="docs/assets/npcs/coco-ember-hound.png" alt="Coco, a chocolate Labrador companion, shown from front, side and back" width="100%"></a> | <a href="docs/assets/npcs/cinder-vale-performer.png"><img src="docs/assets/npcs/cinder-vale-performer.png" alt="Cinder Vale in front, side and back views wearing practical fire-performer clothes and carrying an unlit torch" width="100%"></a> | <a href="docs/assets/npcs/mykael-greenwood-hauler.png"><img src="docs/assets/npcs/mykael-greenwood-hauler.png" alt="Mykael Greenwood in front, side and back views as a broad, warm-hearted hauler with a dark shoulder tattoo" width="100%"></a> |

| Nathis | Tyty |
|---|---|
| <a href="docs/assets/npcs/nathis-front-man.png"><img src="docs/assets/npcs/nathis-front-man.png" alt="Nathis in front, side and back views in age-appropriate scout clothing" width="100%"></a> | <a href="docs/assets/npcs/tyty-wandering-herald.png"><img src="docs/assets/npcs/tyty-wandering-herald.png" alt="Tyty, a shaggy long-eared hound companion, shown from front, side and back" width="100%"></a> |

### Queen D.Anna model reference

This separate rendering follows the Gemini reference for Queen D.Anna as an ascended Bloodweaver / Solar-Lord sovereign in crimson and gold, carrying a light-focusing scepter. It is concept art for the in-game model pass, not a replacement for the written character brief.

<p align="center"><a href="docs/assets/npcs/danna-dee-sovereign-v2.png"><img src="docs/assets/npcs/danna-dee-sovereign-v2.png" alt="Queen D.Anna in crimson and gold sovereign regalia, shown in front, side and back views holding a light-focused scepter" width="100%"></a></p>

### New NPC: Bryttan Wolfholt

Bryttan is the Wolfguard, a vigilant shieldwarden at Ironhold Keep. Her seeded look is built from the shared rigged warrior model with cobalt wolf insignia, a power-core pack, a blue shard pendant, and a rune-etched survival dagger. She is an interactable named NPC, paired in the setting with Evangeline Wolfholt.

Her Godot appearance is assembled from mesh details and material overrides without modifying the shared source model. It interprets the PDF's text description; it is not presented as a recreation of missing reference art.

### First playable quest: The Quiet Watch

In Ironhold's Keep Courtyard, Evangeline Wolfholt asks the party to investigate an echo near the signal bell. Defeat the seeded Echo Hound, then return to Bryttan at the keep to receive 75 XP and the Wolfguard Watch Mark. Quest progress, completion, XP, and the item reward are saved with the campaign snapshot. This slice uses StoryForge's existing player attack and enemy counterattack flow; initiative and a full turn-based combat system remain in progress.

The courtyard now uses textured stone and timber surfaces, with a bronze signal bell, wall lantern, supply crates, and training dummy placed along the yard's edges. These props are decorative and leave the grid movement rules unchanged. Named NPCs use role-specific material palettes; D.Anna, Evangeline, and Bryttan also receive per-instance equipment details on the shared rig. See the [NPC visual bible](docs/NPC_VISUAL_BIBLE.md).

### Iron Ledge equipment and wilds

Five low-poly weapon concepts have been modelled and rendered in Blender. Editable sources and GLB exports are linked in the [weapon concept sheet](docs/WEAPON_CONCEPTS.md). Proposed damage and prices are design notes; the assets are not yet connected to inventory or combat.

| Gateward sword | Wolfguard Reach spear | Greenwood Longbow |
|---|---|---|
| <img src="docs/assets/weapons/gateward_sword.png" alt="Blender render of the Gateward arming sword" width="100%"> | <img src="docs/assets/weapons/wolfguard_reach_spear.png" alt="Blender render of the Wolfguard Reach patrol spear" width="100%"> | <img src="docs/assets/weapons/greenwood_longbow.png" alt="Blender render of the Greenwood field longbow" width="100%"> |

| Briarhook field knife | Bellfound Maul | Forest edge prop kit |
|---|---|---|
| <img src="docs/assets/weapons/briarhook_field_knife.png" alt="Blender render of the Briarhook brush knife" width="100%"> | <img src="docs/assets/weapons/bellfound_maul.png" alt="Blender render of the Bellfound two-handed maul" width="100%"> | <img src="docs/assets/world/forest_edge_kit.png" alt="Blender render of a low-poly oak, spruce, stump, fallen log and woodland rocks" width="100%"> |

The [forest kit's editable Blender file](godot/assets/models/props/forest_edge_kit/forest_edge_kit.blend) and [Godot GLB export](godot/assets/models/props/forest_edge_kit/forest_edge_kit.glb) contain reusable oak, spruce, stump, fallen log, and boulder meshes. The repository also includes [deer](godot/assets/models/animals/deer.glb), [fox](godot/assets/models/animals/fox.glb), and [stag](godot/assets/models/animals/stag.glb) models for ambient wildlife; ordinary animals remain outside the combat roster, in keeping with the world rules. These assets are previews and building blocks; the forest kit and wildlife are not yet placed in a playable forest encounter.

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

- **Available:** 35-species character creation with 35 bespoke hero models, tabletop exploration, Python API, local snapshot saves, validator-gated Gemini proposals, NPC encounters, and the first authored quest loop in Ironhold.
- **NPC update:** Bryttan Wolfholt is seeded in Ironhold Keep and uses the existing rigged character pipeline with a composed appearance.
- **In progress:** real-device verification for the offline Android build and touch controls, and a complete turn-based combat system. The current quest uses a basic attack/counterattack encounter.
- **Offline limits:** NPC encounter routes return 503 and freeform text returns 501 because those features require the AI narrator.

Read the [project docs](docs/README.md) and [roadmap](ROADMAP.md) for more detail.

## Acknowledgments

StoryForge's setting and NPCs grew from Deanna's stories, ideas, and guidance. Thanks to Haley, John, Jason, and Brad for their support, and to Google Gemini for helping shape the narrator.

<p align="center"><i>“The dice determine the fate, but the Forge shapes the story.”</i></p>
