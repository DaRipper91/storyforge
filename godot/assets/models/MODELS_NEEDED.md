# StoryForge — Required 3D Model Files

All runtime models use `.glb` (GLTF binary). `godot/scripts/ModelLibrary.gd` resolves NPCs and enemies; `godot/scripts/characters/character_model.gd` resolves player species. First usable NPC hit wins:

1. `characters/<id>.glb` — bespoke model for one entity (`kodrik.glb`, `ghoul_01.glb`)
2. `SPRITE_MODELS[sprite_key]` in ModelLibrary.gd — archetype (humanoid/, animals/, enemies/, dragons/)
3. RaceMini primitive recipe — never fails

Player species load `heroes/<race_id>.glb` when present, then fall back to `player/<group>.glb`.
All 35 species now have bespoke Blender-authored hero GLBs; their shared 49-bone humanoid
rig is animated by the procedural animation library. The five group models remain fallback
bases. Models are scaled and grounded by the runtime character model.

## Source packs (both free, CC0)
- Humanoid NPCs: https://quaternius.com/packs/ultimateanimatedcharacter.html
- Animals/Pets:  https://quaternius.com/packs/ultimateanimals.html

---

## humanoid/  (NPC characters)

| Filename              | Used for                        | Notes                          |
|-----------------------|---------------------------------|--------------------------------|
| npc_default.glb       | Jon, Haylie, Nathis, Bryne      | Casual/friendly humanoid       |
| npc_mage.glb          | Samael                          | Robed / arcane humanoid        |
| npc_warrior.glb       | Kodrik, Mykael (npc_bear)       | Armored humanoid               |
| npc_performer.glb     | Cinder Vale                 | Elegant/expressive humanoid    |
| npc_royal.glb         | Queen D'Anna                    | Regal humanoid                 |

If you only have one humanoid model, rename it `npc_default.glb` and it will be used for all.

Animation names (case-insensitive; see `CLIP_ALIASES` in ModelLibrary.gd).
Blender duplicate suffixes (`Idle.021` → `Idle_021` after import) and pack
prefixes (`Skeleton_Idle`) are handled:
- Idle:   `Idle`, `Idle_A`, `Standing`
- Walk:   `Walk`, `Walking`, `Walk_A`, `Running`, `Run`, `Flying`, `Fly`, `Gallop`
- Talk:   `Interact`, `Talk`, `Wave`, `Pickup`, `Idle_2`
- Attack: `Attack`, `Slash`, `Attack_A`, `Attack_Headbutt`
- Death:  `Death`, `Die`, `Fall`

---

## animals/  (Pets)

| Filename   | Used for                              |
|------------|---------------------------------------|
| dog.glb    | Keeva, Teddy, Coco, Cole, Tyty        |
| wolf.glb   | Cyrus                                 |
| cat.glb    | Bink Bink, Snowie                     |

---

## player/  (Player race fallback bases)

| Filename            | Race groups it covers                           |
|---------------------|-------------------------------------------------|
| humanoid.glb        | All 15 Humanoid races (fallback only)           |
| primal.glb          | All 5 Primal races (solarlord, grimcrow, etc)   |
| eldritch.glb        | All 5 Eldritch races (bloodweaver, etc)         |
| mechanical.glb      | All 5 Mechanical races (forgespawn, etc)        |
| cosmic.glb          | All 5 Cosmic races (voidwraith, etc)            |

## heroes/  (Bespoke playable species)

There is one named GLB for each of the 35 species. The complete roster and Blender source
builders are shown in the root README and `tools/blender/build_<race_id>.py`.
