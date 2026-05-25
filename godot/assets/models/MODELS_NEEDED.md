# StoryForge — Required 3D Model Files

All models should be `.glb` format (GLTF binary). Drop files here and restart Godot.
The game falls back to procedural colored cylinders for any missing file.

## Source packs (both free, CC0)
- Humanoid NPCs: https://quaternius.com/packs/ultimateanimatedcharacter.html
- Animals/Pets:  https://quaternius.com/packs/ultimateanimals.html

---

## humanoid/  (NPC characters)

| Filename              | Used for                        | Notes                          |
|-----------------------|---------------------------------|--------------------------------|
| npc_default.glb       | Jon, Haylie, Nathis, Mykael     | Casual/friendly humanoid       |
| npc_mage.glb          | Samael                          | Robed / arcane humanoid        |
| npc_warrior.glb       | Kodrik, Bryne                   | Armored humanoid               |
| npc_performer.glb     | Firey RedVelvet                 | Elegant/expressive humanoid    |
| npc_royal.glb         | Queen D'Anna                    | Regal humanoid                 |

If you only have one humanoid model, rename it `npc_default.glb` and it will be used for all.

Expected animation names (case-sensitive, tries each in order):
- Idle:   `Idle`, `Idle_A`, `Standing`
- Walk:   `Walking`, `Walk`, `Walk_A`
- Talk:   `Interact`, `Talk`, `Wave`, `Pickup`
- Attack: `Attack`, `Slash`, `Attack_A`
- Death:  `Death`, `Die`, `Fall`

---

## animals/  (Pets)

| Filename   | Used for                              |
|------------|---------------------------------------|
| dog.glb    | Keeva, Teddy, Coco, Cole, Tyty        |
| wolf.glb   | Cyrus                                 |
| cat.glb    | Bink Bink, Snowie                     |
| bear.glb   | Mykael (if no humanoid model present) |

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
