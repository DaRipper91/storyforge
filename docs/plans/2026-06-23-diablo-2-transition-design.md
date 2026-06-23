# StoryForge — Diablo 2 Transition Design Spec

## Overview
This document specifies the architectural transition of *StoryForge* from a turn-based tabletop grid simulator to a real-time Action RPG inspired by *Diablo 2*.

## 1. High-Level Architecture (Hybrid Client-Authoritative)
We will employ a **Hybrid Client-Authoritative** model:
* **Godot (C++ / GDScript)**: Serves as the authoritative physics, movement, and combat loop runner. It executes local collision detection, real-time pathfinding, and calculations (via the `D2CombatEngine` extension).
* **Python Backend**: Acts as a state persistent save-game manager, shopkeeper database, and lore teller.

## 2. Movement & Collision
* **Grid to Freeform**: Deactivate cell-by-cell path restrictions. Movement is continuous analog WASD/Gamepad input.
* **Physics Bounds**: Attach `StaticBody3D` and `CollisionShape3D` objects to procedural room meshes (walls, pillars, tables) to block the player character body (`CharacterBody3D`) from passing.
* **Isometric Camera**: Camera focus continuously lerps to the player's 3D coordinates, maintaining a constant 3/4 isometric viewpoint.
* **Trigger Exits**: Spawns `Area3D` nodes at exit points. Entering these trigger zones auto-submits a `/action/travel` packet to transition rooms.

## 3. Combat, Skill Trees & Itemization
* **Active Combat**: Attacks are mapped to mouse clicks / gamepad face buttons.
* **Combat Engine (C++)**: Calculations for accuracy vs. defense, critical hits, speed, and active skill tree resource depletion are performed locally in GDExtension real-time.
* **Real-time AI**: Enemy nodes continuously calculate distance to the player and chase using `NavigationAgent3D` when within aggro range.
* **Diablo Ground Loot**: Defeated enemies prompt loot rolls. Drops appear on the ground as colored text labels representing normal (white), magic (blue), rare (yellow), or unique (gold) items.

## 4. Backend State Sync & Narration
* **Liveness Heartbeat**: Introduce a `POST /api/d2/sync` endpoint for periodic updates (e.g. every 5 seconds) to save player health, level, and position coordinates.
* **Event-driven Narration**: Remove step-by-step narration. Gemini only narrates significant events (zone changes, waypoint activation, boss defeats) to keep narration atmospheric and low-frequency.
