extends Control

# ─── Steps ─────────────────────────────────────────────────────────
# 0 = Era        (Before vs After — the Paradox question)
# 1 = Race       (era-aware: humanoid races show civilized → feral pair)
# 2 = State      (Behemoth / Phantom / Swarm-Host / Mimic)
# 3 = Role       (Stalker / Vanguard / Catalyst / Siphoner)
# 4 = Abilities  (player distributes standard array [15,14,13,12,10,8])
# 5 = Name       (final confirmation)

const STEPS        = ["Era", "Race", "Evolutionary State", "Predator Role", "Abilities", "Name"]
const ABILITY_KEYS = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
const STANDARD_ARRAY = [15, 14, 13, 12, 10, 8]

@onready var step_label       = $MarginContainer/VBoxContainer/StepLabel
@onready var race_list        = $MarginContainer/VBoxContainer/HSplitContainer/LeftPanel/RaceList
@onready var description_label = $MarginContainer/VBoxContainer/HSplitContainer/RightPanel/MarginContainer/VBoxContainer/DescriptionLabel
@onready var portrait_rect    = $MarginContainer/VBoxContainer/HSplitContainer/RightPanel/MarginContainer/VBoxContainer/PortraitRect
@onready var next_btn         = $MarginContainer/VBoxContainer/Footer/NextBtn
@onready var back_btn         = $MarginContainer/VBoxContainer/Footer/BackBtn

var catalog:      Dictionary = {}
var current_step: int        = 0
var slot_index:   int        = 0
var _submitting:  bool       = false

var selection: Dictionary = {
	"starting_era":    "after",
	"race":            null,
	"evolution_state": null,
	"predator_role":   null,
	"abilities":       { "STR": null, "DEX": null, "CON": null, "INT": null, "WIS": null, "CHA": null },
	"name":            "",
}

# Ability assignment state
var _pool_remaining: Array = []     # standard array values not yet assigned
var _focused_ability: String = ""   # which ability row is selected for assignment

# ─── Lifecycle ─────────────────────────────────────────────────────

func _ready():
	back_btn.pressed.connect(_on_back_btn_pressed)
	next_btn.pressed.connect(_on_next_btn_pressed)
	next_btn.disabled = true

	var pc = get_node_or_null("/root/PythonClient")
	if pc:
		pc.catalog_received.connect(_on_catalog_received)
		pc.character_created.connect(_on_character_created)
		pc.character_create_failed.connect(_on_character_create_failed)
		pc.game_started.connect(_on_game_started)
		pc.state_updated.connect(_on_state_updated, CONNECT_ONE_SHOT)
		pc.fetch_catalog()
		pc.fetch_full_state()
	else:
		_setup_mock_catalog()
		_render_step()

func _on_state_updated(state: Dictionary):
	for slot in state.get("lobby_slots", []):
		if slot.get("status") in ["claimed", "creating"]:
			slot_index = slot.get("slot_index", 0)
			break

func _on_catalog_received(new_catalog: Dictionary):
	catalog = new_catalog
	_render_step()

# ─── Rendering ─────────────────────────────────────────────────────

func _render_step():
	if catalog.is_empty():
		return
	_clear_list()
	next_btn.disabled = true
	step_label.text = "Step %d / %d  —  %s" % [current_step + 1, STEPS.size(), STEPS[current_step]]

	match current_step:
		0: _render_era_step()
		1: _render_race_step()
		2: _render_choice_step(catalog.get("states", {}), "evolution_state", "Choose your evolutionary form…")
		3: _render_choice_step(catalog.get("roles",  {}), "predator_role",   "Choose your predator role…")
		4: _render_abilities_step()
		5: _render_name_step()

func _clear_list():
	for child in race_list.get_children():
		child.queue_free()
	description_label.text = ""
	portrait_rect.texture = null

# ── Step 0: Era ────────────────────────────────────────────────────

func _render_era_step():
	description_label.text = (
		"The Weaver's Paradox rewrote reality in three seconds.\n\n" +
		"[b]Before[/b]: You begin as the person you were — the old names still hold. " +
		"Your feral transformation arrives mid-game.\n\n" +
		"[b]After[/b]: The Paradox already found you. You start in your Feral Successor form. " +
		"The Civilized World is a memory."
	)

	var eras = [
		{ "id": "after",  "label": "After — The Feral World",    "sub": "The Paradox already found you" },
		{ "id": "before", "label": "Before — The Civilized World","sub": "You are what you were" },
	]

	var group = ButtonGroup.new()
	group.set("allow_unpress", true)

	for era in eras:
		var btn = Button.new()
		btn.text = "%s\n%s" % [era["label"], era["sub"]]
		btn.toggle_mode = true
		btn.button_group = group
		btn.custom_minimum_size = Vector2(0, 60)
		if selection["starting_era"] == era["id"]:
			btn.set_pressed_no_signal(true)
			next_btn.disabled = false
		btn.pressed.connect(func():
			selection["starting_era"] = era["id"]
			next_btn.disabled = false
			# Reset race if era changed — before-only humanoid display may differ
			selection["race"] = null
		)
		race_list.add_child(btn)

# ── Step 1: Race (era-aware) ───────────────────────────────────────

func _render_race_step():
	description_label.text = "Select your ancestry…"
	var races = catalog.get("races", {})
	var is_before = selection["starting_era"] == "before"

	# Group ordering: Cosmic, Primal, Eldritch, Mechanical, Humanoid
	var group_order = ["Cosmic", "Primal", "Eldritch", "Mechanical", "Humanoid"]
	var grouped: Dictionary = {}
	for key in races:
		var g = races[key].get("group", "Other")
		if not grouped.has(g):
			grouped[g] = []
		grouped[g].append(key)

	var new_group = ButtonGroup.new()
	new_group.set("allow_unpress", true)

	for group_name in group_order:
		if not grouped.has(group_name):
			continue
		var header = Label.new()
		header.text = "── %s ──" % group_name
		header.add_theme_color_override("font_color", Color(0.6, 0.5, 0.3))
		race_list.add_child(header)

		for key in grouped[group_name]:
			var data = races[key]
			var before_name = data.get("before", "")
			var display_name: String

			if before_name and is_before:
				display_name = "%s  →  %s" % [before_name, data["name"]]
			elif before_name:
				display_name = "%s  (was %s)" % [data["name"], before_name]
			else:
				display_name = data["name"]

			var btn = Button.new()
			btn.text = display_name
			btn.toggle_mode = true
			btn.button_group = new_group
			if selection["race"] == key:
				btn.set_pressed_no_signal(true)
				next_btn.disabled = false
				_preview_race(data, is_before)
			btn.mouse_entered.connect(func(): _preview_race(data, is_before))
			btn.focus_entered.connect(func(): _preview_race(data, is_before))
			btn.pressed.connect(func():
				selection["race"] = key
				next_btn.disabled = false
				_preview_race(data, is_before)
			)
			race_list.add_child(btn)

func _preview_race(data: Dictionary, is_before: bool):
	var name_str   = data.get("name", "")
	var before_str = data.get("before", "")
	var flavor     = data.get("flavor", "")
	var speed      = data.get("speed", 30)
	var bonuses    = data.get("ability_bonuses", {})

	var lines = []
	if before_str:
		if is_before:
			lines.append("[b]Civilized Form:[/b] %s" % before_str)
			lines.append("[b]Feral Successor:[/b] %s" % name_str)
		else:
			lines.append("[b]%s[/b]" % name_str)
			lines.append("[i](Formerly %s)[/i]" % before_str)
	else:
		lines.append("[b]%s[/b]" % name_str)

	if flavor:
		lines.append("\n%s" % flavor)

	var bonus_parts = []
	for ab in bonuses:
		bonus_parts.append("%s +%d" % [ab, bonuses[ab]])
	if bonus_parts.size() > 0:
		lines.append("\nSpeed: %dft   %s" % [speed, "   ".join(bonus_parts)])

	description_label.text = "\n".join(lines)

# ── Step 2/3: Generic choice (state / role) ────────────────────────

func _render_choice_step(options: Dictionary, field: String, placeholder: String):
	description_label.text = placeholder
	var group = ButtonGroup.new()
	group.set("allow_unpress", true)

	for key in options:
		var data = options[key]
		var btn = Button.new()
		btn.text = data.get("name", key)
		btn.toggle_mode = true
		btn.button_group = group
		if selection[field] == key:
			btn.set_pressed_no_signal(true)
			next_btn.disabled = false
			_preview_item(data)
		btn.mouse_entered.connect(func(): _preview_item(data))
		btn.focus_entered.connect(func(): _preview_item(data))
		btn.pressed.connect(func():
			selection[field] = key
			next_btn.disabled = false
			_preview_item(data)
		)
		race_list.add_child(btn)

func _preview_item(data: Dictionary):
	var name_str = data.get("name", "")
	var flavor   = data.get("flavor", "")
	var text = "[b]%s[/b]" % name_str
	if flavor:
		text += "\n\n%s" % flavor
	description_label.text = text

	var portrait_key = name_str.to_lower().replace(" ", "_").replace("-", "_")
	var path = "res://assets/characters/%s.png" % portrait_key
	portrait_rect.texture = load(path) if ResourceLoader.exists(path) else null

# ── Step 4: Abilities ──────────────────────────────────────────────

func _render_abilities_step():
	# Rebuild remaining pool from what hasn't been assigned yet
	_pool_remaining = []
	for v in STANDARD_ARRAY:
		var already_used = false
		for ab in ABILITY_KEYS:
			if selection["abilities"][ab] == v:
				already_used = true
				break
		if not already_used:
			_pool_remaining.append(v)

	var all_assigned = _pool_remaining.is_empty()
	next_btn.disabled = not all_assigned

	description_label.text = (
		"Distribute the standard array across your six abilities.\n\n" +
		"[b]15  14  13  12  10  8[/b]\n\n" +
		"Select an ability, then select a value to assign.\n\n" +
		"Racial bonuses are applied automatically on character creation."
	)

	# Pool of unassigned values at the top
	var pool_label = Label.new()
	pool_label.text = "Available: %s" % (str(_pool_remaining) if not _pool_remaining.is_empty() else "— all assigned —")
	race_list.add_child(pool_label)

	# One row per ability
	for ab in ABILITY_KEYS:
		var current_val = selection["abilities"][ab]
		var row = HBoxContainer.new()
		row.custom_minimum_size = Vector2(0, 32)

		var ab_label = Label.new()
		ab_label.text = ab
		ab_label.custom_minimum_size = Vector2(44, 0)
		row.add_child(ab_label)

		# Assigned value button (shows current or "—")
		var val_btn = Button.new()
		val_btn.text = str(current_val) if current_val != null else "—"
		val_btn.custom_minimum_size = Vector2(48, 0)
		val_btn.toggle_mode = true
		if _focused_ability == ab:
			val_btn.set_pressed_no_signal(true)
		val_btn.pressed.connect(func():
			_focused_ability = ab
			_render_step()
		)
		row.add_child(val_btn)

		# If a value is assigned, show a clear button
		if current_val != null:
			var clear_btn = Button.new()
			clear_btn.text = "✕"
			clear_btn.custom_minimum_size = Vector2(28, 0)
			clear_btn.pressed.connect(func():
				selection["abilities"][ab] = null
				_focused_ability = ab
				_render_step()
			)
			row.add_child(clear_btn)

		race_list.add_child(row)

	# Pool value buttons — only shown when an ability is focused
	if _focused_ability != "" and not _pool_remaining.is_empty():
		var spacer = Label.new()
		spacer.text = ""
		race_list.add_child(spacer)

		var assign_label = Label.new()
		assign_label.text = "Assign to %s:" % _focused_ability
		race_list.add_child(assign_label)

		var pool_row = HBoxContainer.new()
		for v in _pool_remaining:
			var pool_btn = Button.new()
			pool_btn.text = str(v)
			pool_btn.custom_minimum_size = Vector2(44, 36)
			pool_btn.pressed.connect(func():
				selection["abilities"][_focused_ability] = v
				_focused_ability = ""
				_render_step()
			)
			pool_row.add_child(pool_btn)
		race_list.add_child(pool_row)

# ── Step 5: Name ───────────────────────────────────────────────────

func _render_name_step():
	var race_key  = selection.get("race", "")
	var race_data = catalog.get("races", {}).get(race_key, {})
	var is_before = selection["starting_era"] == "before"
	var before_name = race_data.get("before", "")

	var summary = []
	summary.append("[b]Era:[/b] %s" % ("Before — Civilized" if is_before else "After — Feral"))
	var race_label = race_data.get("name", race_key)
	if before_name and is_before:
		race_label = "%s → %s" % [before_name, race_label]
	summary.append("[b]Race:[/b] %s" % race_label)

	var state_key  = selection.get("evolution_state", "")
	var state_data = catalog.get("states", {}).get(state_key, {})
	summary.append("[b]Form:[/b] %s" % state_data.get("name", state_key))

	var role_key  = selection.get("predator_role", "")
	var role_data = catalog.get("roles", {}).get(role_key, {})
	summary.append("[b]Role:[/b] %s" % role_data.get("name", role_key))

	var ab_parts = []
	for ab in ABILITY_KEYS:
		var v = selection["abilities"].get(ab)
		if v != null:
			ab_parts.append("%s %d" % [ab, v])
	if ab_parts.size() > 0:
		summary.append("[b]Abilities:[/b] %s" % "  ".join(ab_parts))

	description_label.text = "\n".join(summary)

	var name_input = LineEdit.new()
	name_input.placeholder_text = "Enter your hero's name…"
	name_input.text = selection["name"]
	name_input.text_changed.connect(func(val: String):
		selection["name"] = val.strip_edges()
		next_btn.disabled = selection["name"].is_empty()
	)
	name_input.text_submitted.connect(func(_v): _on_next_btn_pressed())
	race_list.add_child(name_input)
	name_input.grab_focus()

	if not selection["name"].is_empty():
		next_btn.disabled = false

# ─── Navigation ────────────────────────────────────────────────────

func _on_next_btn_pressed():
	if _submitting:
		return
	AudioManager.play_sfx("res://assets/audio/sfx_ui_confirm.wav")
	if current_step < STEPS.size() - 1:
		current_step += 1
		_render_step()
	else:
		_submit_creation()

func _on_back_btn_pressed():
	AudioManager.play_sfx("res://assets/audio/sfx_ui_back.wav")
	if current_step > 0:
		current_step -= 1
		_render_step()
	else:
		get_tree().change_scene_to_file("res://scenes/UI_Overlay.tscn")

# ─── Submission ────────────────────────────────────────────────────

func _submit_creation():
	_submitting = true
	next_btn.disabled = true
	next_btn.text = "Forging…"

	get_node("/root/PythonClient").create_character({
		"slot_index":      slot_index,
		"name":            selection["name"],
		"race":            selection["race"],
		"evolution_state": selection["evolution_state"],
		"predator_role":   selection["predator_role"],
		"starting_era":    selection["starting_era"],
		"abilities":       selection["abilities"],
	})

func _on_character_created(_result: Dictionary):
	AudioManager.play_sfx("res://assets/audio/sfx_character_created.wav")
	get_node("/root/PythonClient").game_start_failed.connect(_on_game_start_failed, CONNECT_ONE_SHOT)
	get_node("/root/PythonClient").start_game()

func _on_character_create_failed(error: String):
	_submitting = false
	next_btn.disabled = false
	next_btn.text = "Next"
	description_label.text = "[color=red]Creation failed: %s[/color]" % error

func _on_game_started():
	get_tree().change_scene_to_file("res://scenes/Tabletop.tscn")

func _on_game_start_failed(error: String):
	_submitting = false
	next_btn.disabled = false
	next_btn.text = "Next"
	description_label.text = "[color=red]Could not start game: %s[/color]" % error

# ─── Mock catalog (dev fallback) ───────────────────────────────────

func _setup_mock_catalog():
	catalog = {
		"races": {
			"voidwraith":  { "name": "Voidwraith",  "group": "Cosmic",   "before": "",       "flavor": "Stellar scavengers that feast on dying magic.", "speed": 30, "ability_bonuses": {"INT": 2, "DEX": 1} },
			"ashenborn":   { "name": "Ashenborn",   "group": "Humanoid", "before": "Human",  "flavor": "What humanity became after the Paradox.",       "speed": 30, "ability_bonuses": {"STR": 1, "CON": 1} },
			"hollowsong":  { "name": "Hollowsong",  "group": "Humanoid", "before": "Elf",    "flavor": "Resonant voids that carry the old melodies.",   "speed": 35, "ability_bonuses": {"DEX": 2, "WIS": 1} },
		},
		"states": {
			"behemoth":    { "name": "Behemoth",    "flavor": "Unstoppable bulk. High HP, solid AC." },
			"phantom":     { "name": "Phantom",     "flavor": "Evasive and swift. Low HP but hard to hit." },
			"swarm_host":  { "name": "Swarm-Host",  "flavor": "Adaptive colony. Balanced all-rounder." },
			"mimic":       { "name": "Mimic",       "flavor": "Flexible predator. Copies strengths." },
		},
		"roles": {
			"stalker":     { "name": "Stalker",     "flavor": "Ambush predator. Starts with stealth gear." },
			"vanguard":    { "name": "Vanguard",    "flavor": "Front-line crusher. Starts with heavy weapons." },
			"catalyst":    { "name": "Catalyst",    "flavor": "Arcane disruptor. Starts with volatile reagents." },
			"siphoner":    { "name": "Siphoner",    "flavor": "Life-drain specialist. Starts with drain tools." },
		},
	}
	_render_step()
