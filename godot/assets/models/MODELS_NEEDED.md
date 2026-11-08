# StoryForge — Required 3D Model Files

All models should be `.glb` format (GLTF binary). Drop files here and restart Godot.
`godot/scripts/ModelLibrary.gd` resolves every token. First usable hit wins:

1. `characters/<id>.glb` — bespoke model for one entity (`kodrik.glb`, `ghoul_01.glb`)
2. `SPRITE_MODELS[sprite_key]` in ModelLibrary.gd — archetype (humanoid/, animals/, enemies/, dragons/)
3. `player/<race_id>.glb` — per-race override (players only)
4. `player/<group>.glb` — race group body (players only)
5. RaceMini primitive recipe — never fails

**A rigged model is only used if it has an idle clip.** Rigged files without clips
(today: everything in `humanoid/` and `player/`) would stand in a T-pose, so they
are skipped until animated versions land. Models are scaled to the height set in
`SPRITE_MODELS` and grounded automatically — no manual scale needed.

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

## player/  (Player race characters)

| Filename            | Race groups it covers                           |
|---------------------|-------------------------------------------------|
| humanoid.glb        | All 12 Humanoid races (ashenborn, veilborn, etc)|
| primal.glb          | All 5 Primal races (solarlord, grimcrow, etc)   |
| eldritch.glb        | All 5 Eldritch races (bloodweaver, etc)         |
| mechanical.glb      | All 5 Mechanical races (forgespawn, etc)        |
| cosmic.glb          | All 5 Cosmic races (voidwraith, etc)            |

Per-race override: place `<race_id>.glb` (e.g. `grimcrow.glb`) for a fully custom model.
Falls back to group model, then to procedural generation.
