# Fix Character Creator Abilities Allocation and Finish 3D Models

> **For Gemini:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the layout and behavior of the Abilities allocation step in character creation, update the LeftPanel titles dynamically for improved UX, and fix 3D character model matching/animations in `RaceMini.gd`.

**Architecture:**
- Update `_clear_list()` in `CreationManager.gd` to remove child nodes immediately before queueing them for deletion to prevent a one-frame layout/flicker glitch.
- Modify `_render_abilities_step()` in `CreationManager.gd` to allow toggling off (unfocusing) an ability row button when clicked again.
- Set the LeftPanel header label dynamically in `_render_step()` based on the current step.
- Update `RaceMini.gd`'s `setup` to sanitize the race ID (removing spaces, underscores, and hyphens) so it matches the lowercase visual recipes, colors, and groups accurately (e.g. matching "Iron-Locust" to "ironlocust" in the Cosmic group).
- Add lowercase fallbacks for animation names in `RaceMini.gd` to support various model file structures.

**Tech Stack:**
- Godot 4.6 (GDScript)

---

### Task 1: Fix Abilities Step Layout and UI UX in CreationManager.gd

**Files:**
- Modify: `godot/scripts/CreationManager.gd`

**Step 1: Fix `_clear_list()` node removal**
Modify `_clear_list()` to call `race_list.remove_child(child)` before calling `child.queue_free()`.

**Step 2: Add dynamic LeftPanel title updates**
Update the LeftPanel label text dynamically at the top of `_render_step()`.
Retrieve the LeftPanel Label node:
`@onready var left_panel_label = $MarginContainer/VBoxContainer/HSplitContainer/LeftPanel/Label`
Then in `_render_step()`:
```gdscript
	if left_panel_label:
		match current_step:
			0: left_panel_label.text = "Select Starting Era:"
			1: left_panel_label.text = "Choose Your Ancestry:"
			2: left_panel_label.text = "Select Evolutionary State:"
			3: left_panel_label.text = "Select Predator Role:"
			4: left_panel_label.text = "Allocate Ability Scores:"
			5: left_panel_label.text = "Enter Character Name:"
```

**Step 3: Enable toggling off the focused ability**
In `_render_abilities_step()`, modify the `val_btn` pressed connection:
```gdscript
		val_btn.pressed.connect(func():
			if _focused_ability == ab:
				_focused_ability = ""
			else:
				_focused_ability = ab
			_render_step()
		)
```

**Step 4: Verify the Abilities screen functionality**
Re-run compilation/headless validation or test locally if possible.

---

### Task 2: Finish and Fix 3D Character Models in RaceMini.gd

**Files:**
- Modify: `godot/scripts/RaceMini.gd`

**Step 1: Sanitize race_id in setup()**
Modify `setup(race_id, entity_name, is_enemy)` in `RaceMini.gd` to clean the input ID:
```gdscript
	var clean_race_id = race_id.to_lower().replace(" ", "").replace("_", "").replace("-", "")
```
Update group classifications, `RACE_RECIPES`, and `RACE_COLORS` lookups to use `clean_race_id` instead of the raw `race_id`.

**Step 2: Add lowercase animation fallbacks**
Update `_play_anim(anim_name)` to include lowercase versions (`idle`, `standing`, `walk`, `walking`) for the animation player checks to ensure embedded animations load and play cleanly:
```gdscript
	var variations = []
	if anim_name == "Idle":
		variations = ["Idle", "Idle_A", "Standing", "idle", "standing"]
	elif anim_name == "Walk":
		variations = ["Walking", "Walk", "Walk_A", "walk", "walking"]
```

**Step 3: Commit and Verify**
Confirm that all 3D models load correctly and do not collapse mesh vertices.
