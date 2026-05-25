# 3D Race Miniatures & Portraits Implementation Plan

> **For Gemini:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace 2D PNG race portraits and generic 3D capsule miniatures with a unified 3D RaceMiniature system that provides unique visual identities for all 35 races.

**Architecture:**
- Create a `RaceMini` scene in Godot that dynamically builds a 3D avatar based on `race_id`.
- Use `SubViewport` in the character creation menu to render the 3D avatar as a portrait.
- Refactor `Tabletop.gd` to use the new `RaceMini` instead of hardcoded primitives.

**Tech Stack:**
- Godot 4.6 (Forward Plus)
- GDScript
- Built-in 3D Primitives and Shaders

---

### Task 1: Create RaceMini Base Scene and Script

**Files:**
- Create: `godot/scenes/RaceMini.tscn`
- Create: `godot/scripts/RaceMini.gd`

**Step 1: Create the RaceMini.tscn scene**
A simple Node3D with a child MeshInstance3D.

**Step 2: Create the RaceMini.gd script**
Implement a `setup(race_id: String)` method that configures the mesh and material based on the race.

---

### Task 2: Define Race Visual Profiles

**Files:**
- Modify: `godot/scripts/RaceMini.gd`

**Step 1: Implement basic group-based geometry**
- Humanoid: Capsule + Sphere head.
- Cosmic: Sphere + Particle trail.
- Mechanical: Boxy/Angular.
- Eldritch: Spindly/Multiple parts.
- Primal: Organic/Nature-themed.

**Step 2: Add race-specific customizations**
- `voidwraith`: Ethereal blue wisp (Sphere + Shader).
- `ironlocust`: Insectoid (Long body + 6 small legs).
- `emberpact`: Humanoid + Horns (Cylinders).
- etc.

---

### Task 3: Refactor Tabletop Miniature Spawning

**Files:**
- Modify: `godot/scripts/Tabletop.gd`

**Step 1: Replace hardcoded miniature building**
In `spawn_miniature`, instantiate `RaceMini.tscn` instead of building meshes manually.

**Step 2: Update move animation**
Ensure the new mini works with existing movement tweens.

---

### Task 4: Implement 3D Portrait in Creation Menu

**Files:**
- Modify: `godot/scenes/Creation.tscn`
- Modify: `godot/scripts/CreationManager.gd`

**Step 1: Add SubViewport to Creation.tscn**
Replace `PortraitRect` (TextureRect) with a `SubViewportContainer` + `SubViewport` + `Camera3D` + `RaceMini`.

**Step 2: Update CreationManager.gd**
Update the `RaceMini` inside the viewport whenever the user selects a race.

---

### Task 5: Polishing and Shaders

**Files:**
- Create: `godot/assets/shaders/miniature_glow.gdshader`
- Modify: `godot/scripts/RaceMini.gd`

**Step 1: Add rim lighting and glow shaders**
Make the minis feel "alive" and atmospheric.

**Step 2: Final validation**
Ensure all 35 races have a distinct look.
