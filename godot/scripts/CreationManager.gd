extends Control

# Steps: 0=race, 1=state, 2=role, 3=name+era
const STEPS = ["Race", "Evolutionary State", "Predator Role", "Name & Era"]
# Standard array auto-assigned STR→DEX→CON→INT→WIS→CHA
const STANDARD_ARRAY = [15, 14, 13, 12, 10, 8]

@onready var step_label      = $MarginContainer/VBoxContainer/StepLabel
@onready var race_list       = $MarginContainer/VBoxContainer/HSplitContainer/LeftPanel/RaceList
@onready var description_label = $MarginContainer/VBoxContainer/HSplitContainer/RightPanel/MarginContainer/VBoxContainer/DescriptionLabel
@onready var portrait_rect   = $MarginContainer/VBoxContainer/HSplitContainer/RightPanel/MarginContainer/VBoxContainer/PortraitRect
@onready var next_btn        = $MarginContainer/VBoxContainer/Footer/NextBtn
@onready var back_btn        = $MarginContainer/VBoxContainer/Footer/BackBtn

var catalog: Dictionary = {}
var current_step: int = 0
var slot_index: int = 0
var selection: Dictionary = {
	"race": null,
	"evolution_state": null,
	"predator_role": null,
	"name": "",
	"starting_era": "after",
}
var button_group = ButtonGroup.new()
var _submitting: bool = false

func _ready():
	button_group.set("allow_unpress", true)
	back_btn.pressed.connect(_on_back_btn_pressed)
	next_btn.pressed.connect(_on_next_btn_pressed)
	next_btn.disabled = true

	var pc = get_node_or_null("/root/PythonClient")
	if pc:
		pc.catalog_received.connect(_on_catalog_received)
		pc.character_created.connect(_on_character_created)
		pc.character_create_failed.connect(_on_character_create_failed)
		pc.game_started.connect(_on_game_started)
		# Try to read slot_index from state
		pc.state_updated.connect(_on_state_updated, CONNECT_ONE_SHOT)
		pc.fetch_catalog()
		pc.fetch_full_state()
	else:
		_setup_mock_catalog()
		_render_step()

func _on_state_updated(state: Dictionary):
	# Find our slot — first claimed/creating slot.
	for slot in state.get("lobby_slots", []):
		if slot.get("status") in ["claimed", "creating"]:
			slot_index = slot.get("slot_index", 0)
			break

func _on_catalog_received(new_catalog: Dictionary):
	catalog = new_catalog
	_render_step()

func _setup_mock_catalog():
	catalog = {
		"races": {
			"voidwraith": {"name": "Voidwraith", "before": "Astral Spirit", "flavor": "Stellar scavengers that feast on dying magic."},
		},
		"states": {
			"behemoth":   {"name": "Behemoth",   "flavor": "Unstoppable bulk. High HP, solid AC."},
			"phantom":    {"name": "Phantom",    "flavor": "Evasive and swift. Low HP but hard to hit."},
			"swarm_host": {"name": "Swarm-Host", "flavor": "Adaptive colony. Balanced all-rounder."},
			"mimic":      {"name": "Mimic",      "flavor": "Flexible predator. Copies strengths."},
		},
		"roles": {
			"stalker":  {"name": "Stalker",  "flavor": "Ambush predator. Starts with stealth gear."},
			"vanguard": {"name": "Vanguard", "flavor": "Front-line crusher. Starts with heavy weapons."},
			"catalyst": {"name": "Catalyst", "flavor": "Arcane disruptor. Starts with volatile reagents."},
			"siphoner": {"name": "Siphoner", "flavor": "Life-drain specialist. Starts with drain tools."},
		},
	}

# ─── Rendering ─────────────────────────────────────────────────────

func _render_step():
	if catalog.is_empty():
		return

	# Clear the list panel
	for child in race_list.get_children():
		child.queue_free()
	description_label.text = ""
	portrait_rect.texture = null
	next_btn.disabled = true

	step_label.text = "Step %d / %d — %s" % [current_step + 1, STEPS.size(), STEPS[current_step]]

	match current_step:
		0: _render_choice_step(catalog.get("races", {}), "race",           "Select an ancestry...")
		1: _render_choice_step(catalog.get("states", {}), "evolution_state", "Choose your evolutionary form...")
		2: _render_choice_step(catalog.get("roles", {}), "predator_role",  "Choose your predator role...")
		3: _render_name_step()

func _render_choice_step(options: Dictionary, field: String, placeholder: String):
	description_label.text = placeholder
	var new_group = ButtonGroup.new()
	new_group.set("allow_unpress", true)

	for key in options:
		var data = options[key]
		var btn = Button.new()
		btn.text = data.get("name", key)
		btn.toggle_mode = true
		btn.button_group = new_group
		if selection[field] == key:
			btn.set_pressed_no_signal(true)
			next_btn.disabled = false
			_preview_item(options, key)
		btn.mouse_entered.connect(func(): _preview_item(options, key))
		btn.focus_entered.connect(func(): _preview_item(options, key))
		btn.pressed.connect(func():
			selection[field] = key
			next_btn.disabled = false
			_preview_item(options, key)
		)
		race_list.add_child(btn)

func _preview_item(options: Dictionary, key: String):
	var data = options.get(key, {})
	var name_str   = data.get("name", key)
	var before_str = data.get("before", "")
	var flavor     = data.get("flavor", "")
	var text = "[b]%s[/b]" % name_str
	if before_str:
		text += "\n[i](Formerly %s)[/i]" % before_str
	if flavor:
		text += "\n\n%s" % flavor
	description_label.text = text

	var path = "res://assets/characters/" + key + ".png"
	portrait_rect.texture = load(path) if ResourceLoader.exists(path) else null

func _render_name_step():
	# Name input
	var name_input = LineEdit.new()
	name_input.placeholder_text = "Enter your hero's name..."
	name_input.text = selection["name"]
	name_input.text_changed.connect(func(val):
		selection["name"] = val.strip_edges()
		next_btn.disabled = selection["name"].is_empty()
	)
	name_input.text_submitted.connect(func(_val): _on_next_btn_pressed())
	race_list.add_child(name_input)
	name_input.grab_focus()

	# Era choice
	var era_label = Label.new()
	era_label.text = "\nStarting Era:"
	race_list.add_child(era_label)

	for era_id in ["after", "before"]:
		var btn = Button.new()
		btn.text = "After (Feral form)" if era_id == "after" else "Before (Civilized form, transforms mid-game)"
		btn.toggle_mode = true
		if selection["starting_era"] == era_id:
			btn.set_pressed_no_signal(true)
		btn.pressed.connect(func(): selection["starting_era"] = era_id)
		race_list.add_child(btn)

	if not selection["name"].is_empty():
		next_btn.disabled = false

	description_label.text = "Name your hero and choose when your story begins.\n\n[b]After[/b]: Start in full feral form.\n[b]Before[/b]: Start humanoid — your beast form awakens mid-game."

# ─── Navigation ────────────────────────────────────────────────────

func _on_next_btn_pressed():
	if _submitting:
		return
	if current_step < STEPS.size() - 1:
		current_step += 1
		_render_step()
	else:
		_submit_creation()

func _on_back_btn_pressed():
	if current_step > 0:
		current_step -= 1
		_render_step()
	else:
		get_tree().change_scene_to_file("res://scenes/UI_Overlay.tscn")

# ─── Submission ────────────────────────────────────────────────────

func _submit_creation():
	_submitting = true
	next_btn.disabled = true
	next_btn.text = "Forging..."

	var abilities = {
		"STR": STANDARD_ARRAY[0],
		"DEX": STANDARD_ARRAY[1],
		"CON": STANDARD_ARRAY[2],
		"INT": STANDARD_ARRAY[3],
		"WIS": STANDARD_ARRAY[4],
		"CHA": STANDARD_ARRAY[5],
	}

	get_node("/root/PythonClient").create_character({
		"slot_index":      slot_index,
		"name":            selection["name"],
		"race":            selection["race"],
		"evolution_state": selection["evolution_state"],
		"predator_role":   selection["predator_role"],
		"starting_era":    selection["starting_era"],
		"abilities":       abilities,
	})

func _on_character_created(_result: Dictionary):
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
