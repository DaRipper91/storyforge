# Model provenance

Last reviewed: 2026-11-08.

## Player species bases and NPC humanoids

Files: `player/{cosmic,eldritch,humanoid,mechanical,primal}.glb`, `humanoid/npc_*.glb`.

- Source: Quaternius low-poly character packs (the "Ultimate Modular Men/Women" style rig:
  `CharacterArmature` > `Skeleton3D`, 49 bones, meshes `*_Body`, `*_Legs`, `*_Feet`, `*_Head`).
- License: CC0 1.0 (public domain dedication), https://quaternius.com. No attribution required;
  credit is given here anyway.
- All ten files share one skeleton: identical bone names, order and hierarchy (checked by
  `godot/tests/golden/character_test.gd`).
- The files ship with no animation clips.

## Animations

There are no authored or downloaded animation assets. All motion is procedural and written in this
repository: `godot/scripts/characters/humanoid_anim_library.gd` builds one `AnimationLibrary`
(Idle, Walk, Run, Interact, Hit, Death) at runtime from the skeleton's rest pose, so it is original
work covered by the repository licence.

## Runtime changes to the models (nothing on disk was edited)

- Only the left leg and left foot meshes exist in the shipped GLBs (the mirror modifier was not
  applied on export). `godot/scripts/characters/character_model.gd` builds the missing right halves
  at load time by mirroring those meshes in X (winding flipped) and re-binding them to the opposite
  limb's bones. Re-exporting the GLBs with the modifier applied would make this a no-op (symmetric
  meshes are skipped).
- Per-race colour, emissive accent and proportions are applied through material overrides and node
  scale; no meshes are added.

## Other model folders

`animals/`, `dragons/`, `enemies/` are untouched by this change and are not covered by this note.
