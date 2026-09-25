# Diablo Camera Overhaul Implementation Plan

> **For Gemini:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Overhaul the Godot isometric camera to support smooth frame-rate independent follow, smooth target-based zoom and orbits, auto-selection and snapping on transitions, and raycast-based fading of blocking walls/pillars.

**Architecture:** Update the camera calculations from `_physics_process` to `_process` to run at the screen's refresh rate without jitter. Maintain target values for yaw, pitch, and distance to interpolate smoothly. Cast up to 6 rays from the camera to the player's position to identify and fade blocking meshes individually using duplicated materials.

**Tech Stack:** Godot Engine 4 (GDScript, Shaders, 3D Physics).

---

### Task 1: Shader and Material Transparency Configuration

**Files:**
- Modify: `godot/scripts/Tabletop.gd` (under `_build_materials`)

**Step 1: Specify material configuration modifications**
Modify `_build_materials` so that:
- `_mat_wall` shader code includes `render_mode depth_draw_always;`, `uniform float alpha = 1.0;`, and maps `ALPHA = alpha;` in fragment.
- `_mat_pillar`, `_mat_table`, and `_mat_door` have `transparency = BaseMaterial3D.TRANSPARENCY_ALPHA` and `depth_draw_mode = BaseMaterial3D.DEPTH_DRAW_ALWAYS` set.

**Step 2: Run verification**
Ensure no GDScript parse errors in material configuration.

**Step 3: Commit**
```bash
git add godot/scripts/Tabletop.gd
git commit -m "feat: enable depth draw and transparency in tabletop materials"
```

---

### Task 2: Duplicate Materials during Procedural Generation

**Files:**
- Modify: `godot/scripts/Tabletop.gd` (inside `_rebuild_room` matches)

**Step 1: Implement material duplication**
For `wall`, `door`, `pillar`, and `table` terrain matches, call `.duplicate()` on their respective materials (e.g. `inst.material_override = _mat_wall.duplicate()`) so that fading applies per-mesh rather than globally.

**Step 2: Run verification**
Verify geometry still spawns and renders normally without shader errors.

**Step 3: Commit**
```bash
git add godot/scripts/Tabletop.gd
git commit -m "feat: duplicate materials for procedural obstacles to allow individual fading"
```

---

### Task 3: Camera State and Input Updates

**Files:**
- Modify: `godot/scripts/Tabletop.gd` (declarations, `_ready`, `_input`, `_physics_process`)

**Step 1: Declare smooth camera target properties**
Add `_target_yaw`, `_target_pitch`, `_target_distance` (as floats) and `_faded_meshes: Dictionary` to class-level declarations. Initialize them in `_ready()` using the starting values of `_cam_yaw`, `_cam_pitch`, and `_cam_distance`.

**Step 2: Update inputs to set target variables**
- Modify `_input()` so mouse wheel adjusts `_target_distance` rather than `_cam_distance`.
- Modify `_input()` mouse motion right-drag to adjust `_target_yaw` and `_target_pitch`. Remove the immediate `_update_camera()` calls from these mouse events.
- Modify `_physics_process()` gamepad/Xbox look vector checks to adjust `_target_yaw` and `_target_pitch` instead of `_cam_yaw`/`_cam_pitch`. Remove `_update_camera()` call from look vector handling.
- Modify `reset_cam` action to reset `_target_yaw`, `_target_pitch`, and `_target_distance`.
- Modify lock-on rotation handling to update `_target_yaw` instead of `_cam_yaw`.
- Remove the camera follow block at the end of `_physics_process()` entirely.

**Step 3: Run verification**
Confirm Godot project builds without warnings.

**Step 4: Commit**
```bash
git add godot/scripts/Tabletop.gd
git commit -m "feat: rewrite camera inputs to set target interpolation variables and clean up physics updates"
```

---

### Task 4: Smooth Follow, Orbit, and Obstacle Fading in `_process`

**Files:**
- Modify: `godot/scripts/Tabletop.gd` (inside `_process` and `_update_camera`)

**Step 1: Implement updates and raycast wall fading**
In `_process(delta)`, implement:
- Camera yaw/pitch wrap-around handling and smooth interpolation towards targets.
- Zoom distance interpolation: `_cam_distance = lerp(_cam_distance, _target_distance, delta * 8.0)`.
- Player camera targeting with midpoint support.
- Direct raycast queries to detect up to 6 blocking wall/pillar meshes between the camera and the player character torso.
- Interpolation of mesh alphas (using `alpha` uniform for ShaderMaterial and `albedo_color.a` for StandardMaterial3D) towards their target fade state (`0.25` if blocked, `1.0` if clear).
- Invocation of `_update_camera()`.

**Step 2: Update `_update_camera()` zoom scale**
If `camera.projection == Camera3D.PROJECTION_ORTHOGONAL`, set `camera.size = _cam_distance`.

**Step 3: Run verification**
Verify the camera follows smoothly in the client without jitter, zoom works, and obstacles fade out when standing behind them.

**Step 4: Commit**
```bash
git add godot/scripts/Tabletop.gd
git commit -m "feat: implement smooth tracking, camera updates, and wall fading in _process"
```

---

### Task 5: Snap Camera and Auto-Select on Room Transition

**Files:**
- Modify: `godot/scripts/Tabletop.gd` (inside `_on_state_updated`)

**Step 1: Implement selection/snapping logic**
- In `_on_state_updated()`, check if `_selected_cid` is empty after spawning/syncing characters. If empty, auto-select the first character by calling `_select_mini(cid)`.
- If a leader character was spawned during the transition, immediately snap `_cam_target = leader.position` and call `_update_camera()` to prevent camera sliding across empty rooms.

**Step 2: Run verification**
Transition between rooms using exit doors and verify the leader is automatically selected and camera immediately snaps to the new position.

**Step 3: Commit**
```bash
git add godot/scripts/Tabletop.gd
git commit -m "feat: auto-select character and snap camera on room transition"
```
