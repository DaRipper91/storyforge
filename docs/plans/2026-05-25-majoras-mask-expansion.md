# Majora's Mask Style World Expansion

> **For Gemini:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transition StoryForge from a disconnected, grid-based "tabletop simulator" into a highly atmospheric, real-time action-adventure world inspired by *The Legend of Zelda: Majora's Mask*. This means prioritizing direct character control, a persistent world hub, scheduled NPC routines, and a looming time system.

**Architecture Shift:**
- **Navigation & Control:** Replace point-and-click/rigid grid movement with direct, fluid WASD/Analog control for the active character. Unselected party members trail behind dynamically, or wait at a hub.
- **World State (The Clock):** Implement a global Time System (e.g., 3-Day cycle). The Python backend tracks time, and the Godot client syncs visually (Day/Night cycle, NPC positioning).
- **Level Design:** A persistent Central Hub (like Clock Town) surrounded by themed regions.
- **Backend Sync:** The Python AI acts as the "Scheduler" and "Director," dictating where NPCs should be at what time and generating dialogue based on the current hour/day.

---

## Phase 1: Fluid Direct Control & The Follower AI

**Goal:** Break free from the grid. Allow the player to directly pilot the active character via controller, making the game feel like a 3D adventure rather than a tabletop board.

### Task 1.1: Direct Analog Movement & Camera (Xbox Support)
- **Files:** `godot/scripts/Tabletop.gd`, `godot/scripts/RaceMini.gd`, `godot/scripts/PythonClient.gd`
- **Action:** Setup Godot's Input Map for Xbox Gamepad controls:
  - **Left Stick:** Player movement (`move_up`, `move_down`, `move_left`, `move_right`).
  - **Right Stick:** Camera orbit (`look_up`, `look_down`, `look_left`, `look_right`).
- **Action:** Ensure mappings are robust for **Bluetooth Xbox Controllers** (handling standard JoyAxis/JoyButton IDs).
- **Action:** Add a "Controller Connected" / "Controller Disconnected" notification to the UI to verify Bluetooth pairing status in-game.
- **Action:** Convert the current arrow key grid logic in `Tabletop.gd` into continuous `_physics_process` movement.
- **Action:** Update `_physics_process` to handle Right Stick camera rotation (updating `_cam_yaw` and `_cam_pitch`).
- **Action:** Add a `CharacterBody3D` to `RaceMini.tscn` for smooth collision.
- **Action:** Implement smooth rotation (lerping `rotation.y`) so the character physically turns to face their movement direction.

### Task 1.2: Follower AI (The NavMesh Trailing)
- **Files:** `godot/scenes/Tabletop.tscn`
- **Action:** Bake a `NavigationRegion3D` into the floor.
- **Action:** For the 3 unselected characters, assign them a `NavigationAgent3D`.
- **Action:** In `_process`, constantly update the followers' target position to trail slightly behind the active player character, maintaining a loose formation.

---

## Phase 2: The Global Clock & Dynamic Lighting

**Goal:** Implement the defining feature of Majora's Mask: Time.

### Task 2.1: The Time Manager (Godot UI & Sync)
- **Files:** `godot/scripts/TimeManager.gd` (New Autoload)
- **Action:** Create a UI element at the bottom center of the screen displaying the "Current Day" and a clock face.
- **Action:** Tick time forward continuously (e.g., 1 real minute = 1 in-game hour).

### Task 2.2: Day/Night Cycle
- **Files:** `godot/scenes/Tabletop.tscn`
- **Action:** Create a `DirectionalLight3D` tied to the `TimeManager`.
- **Action:** Rotate the sun and change its color temperature based on the time of day (warm dawns, bright noons, dark purple nights).
- **Action:** Toggle point lights (torches/lanterns) on when night falls.

---

## Phase 3: Persistent Hub World & Scheduled NPCs

**Goal:** Build a central town where NPCs live out their lives based on the clock.

### Task 3.1: The Hub Level Scene
- **Files:** Create `godot/scenes/levels/CentralHub.tscn`
- **Action:** Build a static town square level with terrain, buildings, and a clear center point. Ensure the floor is baked into a `NavigationRegion3D`.

### Task 3.2: AI Scheduled NPCs
- **Files:** `Python Backend` (API) & `godot/scripts/NpcManager.gd`
- **Action:** Update the backend to assign "schedules" to NPCs (e.g., 8AM - Market, 6PM - Inn).
- **Action:** The Godot client polls the backend (or receives WebSocket events) for NPC locations.
- **Action:** NPCs use their `NavigationAgent3D` to physically walk to their scheduled locations as time passes.

---

## Phase 4: Real-Time Action Interactions

**Goal:** Swap turn-based grid combat for real-time swinging, talking, and interacting.

### Task 4.1: The Action Button & Z-Targeting
- **Files:** `godot/scripts/Interactable.gd`, `godot/scripts/Tabletop.gd`
- **Action:** Setup Input Map for Xbox Gamepad (Left Trigger / `LT` for `z_target`, Bottom Face Button / `A Button` for `action`).
- **Action:** Add a proximity trigger to interactables (NPCs, chests).
- **Action:** When the player is close and facing an interactable, show a UI prompt (e.g., "[A] Talk").
- **Action:** Pressing the `LT` trigger locks the camera focus onto the nearest interactable/enemy, allowing strafing.
- **Action:** Pressing the `A Button` triggers the dialogue/action via the AI backend.