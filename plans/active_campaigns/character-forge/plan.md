# Technical Plan: Character Forge (Creation UI)

## 🔍 Analysis & Context
*   **Objective:** Design and implement the Character Forge UI for the Godot 2.5D client, highlighting the Ancestral/Successor relationship and making "Feral" a special ability for each race.
*   **Affected Files:**
    *   `godot/scenes/Creation.tscn` (New)
    *   `godot/scripts/CreationManager.gd` (New)
    *   `godot/scripts/UIManager.gd` (Modify)
    *   `ROADMAP.md` (Modify)
*   **Key Dependencies:** `PythonClient.gd` (for `/api/lobby/catalog` and `/api/character/create`), Godot UI framework.
*   **Risks/Edge Cases:** Replicating the web flow seamlessly in Godot UI; properly parsing standard array logic; properly handling the user steering to make "Feral" a special ability.

## 📋 Task Execution (Parallel Groups)

### Group 1 (Parallel Execution - Independent Tasks)
- [ ] Task 1.A: Implement `godot/scenes/Creation.tscn`
- [ ] Task 1.B: Implement `godot/scripts/CreationManager.gd`

### Group 2 (Sequential Execution - Depends on Group 1)
- [ ] Task 2.A: Connect `UIManager.gd` to trigger Character Forge.
- [ ] Task 2.B: Update `ROADMAP.md` to reflect new Feral Ability design and Godot progress.

## 📝 Step-by-Step Implementation Details

### Prerequisites
Godot 4.x running, Python backend accessible at `:8765`.

#### Task 1.A
1.  **Step 1 (The Unit Test Harness):** Define verification for UI loading.
    *   *Target File:* `tests/test_creation_ui.py` (Mock / Manual verify)
    *   *Test Cases to Write:* Verify the scene parses without errors.
2.  **Step 2 (The Implementation):** Create the Godot scene for Character Forge.
    *   *Target File:* `godot/scenes/Creation.tscn`
    *   *Exact Change:* Create a `Control` root with a parchment `TextureRect` background. Add a `VBoxContainer` for the main layout. Include a header for steps (Race -> State -> Role -> Abilities -> Name). Add an `HBoxContainer` splitting the screen: Left for the character preview/silhouette, Right for a `ScrollContainer` holding dynamic options. Include a footer with Back/Next buttons.

#### Task 1.B
1.  **Step 1 (The Unit Test Harness):** Define verification for CreationManager state.
    *   *Target File:* `tests/test_creation_manager.py` (Mock / Manual verify)
    *   *Test Cases to Write:* Verify state machine moves correctly through steps.
2.  **Step 2 (The Implementation):** Script the Creation Manager logic.
    *   *Target File:* `godot/scripts/CreationManager.gd`
    *   *Exact Change:* Implement fetching from `/api/lobby/catalog`. Modify the race rendering logic to skip the "Era" step. Iterate through catalog races, displaying the "Before" (Ancestral) and "Name" (Successor) along with a newly designated "Feral Ability" (mapped from flavor or a new `feral_ability` key).

#### Task 2.A
1.  **Step 1 (The Unit Test Harness):** Verify UI transition.
    *   *Target File:* `tests/test_ui_manager.py` (Mock / Manual verify)
    *   *Test Cases to Write:* Verify New Game triggers scene switch.
2.  **Step 2 (The Implementation):** Route Main Menu to Creation.
    *   *Target File:* `godot/scripts/UIManager.gd`
    *   *Exact Change:* In `_on_new_game_btn_pressed()`, transition the scene to `res://scenes/Creation.tscn`.

#### Task 2.B
1.  **Step 1 (The Unit Test Harness):** Verify Roadmap update.
    *   *Target File:* `ROADMAP.md`
    *   *Test Cases to Write:* Ensure Godot Character Forge is checked off or updated.
2.  **Step 2 (The Implementation):** Update Roadmap.
    *   *Target File:* `ROADMAP.md`
    *   *Exact Change:* Update Milestone 2 to reflect the Godot Character Forge implementation, and note the change from Era selection to "Feral Ability" integration.

### 🧪 Global Testing Strategy
*   **Unit Tests:** Verify `PythonClient.gd` handles `/api/character/create` correctly.
*   **Integration Tests:** Run Godot client, hit "New Game", verify catalog loads, verify "Feral Ability" is displayed for races without an Era prompt, verify standard array selection works, verify final submission payload to `/api/character/create` matches the schema.

## 🎯 Success Criteria
*   The Godot client can seamlessly transition to the Creation scene.
*   The Era step is gone; Feral is treated as a special ability per race.
*   The standard array dragging/clicking works in Godot UI.
