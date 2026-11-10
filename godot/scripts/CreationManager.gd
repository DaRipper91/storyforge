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
const ABILITY_NAMES = {
	"STR": "Strength",
	"DEX": "Dexterity",
	"CON": "Constitution",
	"INT": "Intelligence",
	"WIS": "Wisdom",
	"CHA": "Charisma"
}
const ABILITY_HELP = {
	"STR": "Power. Increases physical damage and carrying capacity.",
	"DEX": "Agility. Increases accuracy, defense (AC), and initiative.",
	"CON": "Fortitude. Increases total Health (HP) and stamina.",
	"INT": "Logic. Power for cosmic/tech abilities and investigation.",
	"WIS": "Instinct. Power for primal/eldritch abilities and perception.",
	"CHA": "Presence. Power for social influence and leadership."
}
const STANDARD_ARRAY = [15, 14, 13, 12, 10, 8]

@onready var title_label      = $Safe/Root/HeaderRow/TitleLabel
@onready var step_label       = $Safe/Root/HeaderRow/StepLabel
@onready var step_dots        = $Safe/Root/HeaderRow/StepDots
@onready var chip_row         = $Safe/Root/ChipRow
@onready var content          = $Safe/Root/Content
@onready var preview_slot     = $Safe/Root/Content/PreviewSlot
@onready var preview_panel    = $Safe/Root/Content/PreviewPanel
@onready var main_col         = $Safe/Root/Content/Main
@onready var race_list        = $Safe/Root/Content/Main/OptionHost
@onready var desc_panel       = $Safe/Root/Content/Main/DescPanel
@onready var description_label = $Safe/Root/Content/Main/DescPanel/DescScroll/DescriptionLabel
@onready var index_label      = $Safe/Root/IndexLabel
@onready var race_mini        = $Safe/Root/Content/PreviewPanel/PortraitViewport/SubViewport/RaceMini
@onready var next_btn         = $Safe/Root/Footer/NextBtn
@onready var back_btn         = $Safe/Root/Footer/BackBtn
@onready var safe_box         = $Safe

## Layout constants, in base units of the 1280x720 viewport (see storyforge-ui-spec).
const MIN_TOUCH := 96
const BASE_MARGIN := Vector4(24, 12, 24, 12)   # left, top, right, bottom
const WIDE_PREVIEW_MIN_W := 1100.0             # below this the side preview is dropped
const GROUP_ORDER := ["Cosmic", "Primal", "Eldritch", "Mechanical", "Humanoid"]
const PREVIEW_DEBOUNCE := 0.14

## Preview framing: the whole body plus this much slack, seen from a slight downward angle.
const PREVIEW_MARGIN := 1.22
const PREVIEW_PITCH_DEG := 9.0
const PREVIEW_TURN_SPEED := 0.55   # rad/s turntable

var catalog:      Dictionary = {}
var current_step: int        = 0
var slot_index:   int        = 0
var _submitting:  bool       = false
var _preview_cam: Camera3D       = null
var _preview_vp:  SubViewport    = null

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

# Race carousel state
var carousel: RaceCarousel = null
var _race_ids: Array = []
var _chips: Dictionary = {}          # group name -> Button
var _card_name: Label = null
var _card_was: Label = null
var _card_flavor: Label = null
var _card_bonus: Label = null
var _preview_timer: Timer = null
var _safe_margins := Vector4.ZERO    # extra insets from the OS safe area
var _kb_extra := 0.0
var _typing := false

# ─── Lifecycle ─────────────────────────────────────────────────────

func _ready():
	next_btn.disabled = true
	_setup_preview()
	_build_carousel()
	_preview_timer = Timer.new()
	_preview_timer.one_shot = true
	_preview_timer.wait_time = PREVIEW_DEBOUNCE
	_preview_timer.timeout.connect(func(): _show_preview(selection["race"]))
	add_child(_preview_timer)

	# Android back button must step back through the wizard, not close the app.
	if "quit_on_go_back" in get_tree():
		get_tree().quit_on_go_back = false
	get_viewport().size_changed.connect(_on_viewport_resized)
	apply_os_safe_area()
	_on_viewport_resized()

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

func _exit_tree() -> void:
	if is_inside_tree() and "quit_on_go_back" in get_tree():
		get_tree().quit_on_go_back = true

func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_GO_BACK_REQUEST:
		_on_back_btn_pressed()

func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_cancel") and not _submitting:
		get_viewport().set_input_as_handled()
		_on_back_btn_pressed()

# ── Safe area / keyboard ───────────────────────────────────────────

## Extra insets (base units) from a notch / gesture bar: left, top, right, bottom.
func set_safe_margins(left: float, top: float, right: float, bottom: float) -> void:
	_safe_margins = Vector4(left, top, right, bottom)
	_apply_margins()

func _apply_margins() -> void:
	safe_box.add_theme_constant_override("margin_left", int(ceil(BASE_MARGIN.x + _safe_margins.x)))
	safe_box.add_theme_constant_override("margin_top", int(ceil(BASE_MARGIN.y + _safe_margins.y)))
	safe_box.add_theme_constant_override("margin_right", int(ceil(BASE_MARGIN.z + _safe_margins.z)))
	safe_box.add_theme_constant_override("margin_bottom", int(ceil(BASE_MARGIN.w + _safe_margins.w + _kb_extra)))

## Converts the OS safe area (pixels) to viewport units. Only meaningful on phones.
func apply_os_safe_area() -> void:
	if not (OS.has_feature("android") or OS.has_feature("ios")):
		return
	var safe: Rect2i = DisplayServer.get_display_safe_area()
	var screen: Vector2i = DisplayServer.screen_get_size()
	var vis: Vector2 = get_viewport().get_visible_rect().size
	if screen.x <= 0 or screen.y <= 0 or safe.size.x <= 0:
		return
	var sx := vis.x / float(screen.x)
	var sy := vis.y / float(screen.y)
	set_safe_margins(
		maxf(safe.position.x * sx, 0.0),
		maxf(safe.position.y * sy, 0.0),
		maxf((screen.x - safe.end.x) * sx, 0.0),
		maxf((screen.y - safe.end.y) * sy, 0.0))

func _on_viewport_resized() -> void:
	apply_os_safe_area()
	_apply_margins()
	_apply_layout_mode()

func _update_keyboard() -> void:
	if not OS.has_feature("mobile"):
		return
	var kb_px := float(DisplayServer.virtual_keyboard_get_height())
	var win_h := float(maxi(DisplayServer.window_get_size().y, 1))
	var extra := kb_px * get_viewport().get_visible_rect().size.y / win_h
	if absf(extra - _kb_extra) > 1.0:
		_kb_extra = extra
		_apply_margins()
		_typing = extra > 0.0 and current_step == STEPS.size() - 1
		desc_panel.visible = _desc_wanted() and not _typing
		_apply_layout_mode()

## The preview is framed from the model's own bounds (see _frame_preview), so the mini
## keeps scale 1 and the camera moves instead.
func _setup_preview() -> void:
	if race_mini == null:
		return
	_preview_vp = race_mini.get_parent() as SubViewport
	if _preview_vp == null:
		return
	_preview_cam = _preview_vp.get_node_or_null("Camera3D") as Camera3D
	if _preview_cam:
		_preview_cam.fov = 40.0
		_preview_cam.current = true
	_preview_vp.size_changed.connect(_frame_preview)
	# The preview shares the main world, which has no ambient light: add a soft fill.
	var fill := DirectionalLight3D.new()
	fill.name = "FillLight"
	fill.light_energy = 0.55
	fill.rotation_degrees = Vector3(-15.0, 165.0, 0.0)
	_preview_vp.add_child(fill)

func _process(delta: float) -> void:
	_update_keyboard()
	_sync_preview_panel()
	if race_mini and race_mini.is_visible_in_tree():
		race_mini.rotation.y = wrapf(race_mini.rotation.y + delta * PREVIEW_TURN_SPEED, -PI, PI)

## Shows `race_key` (or a neutral humanoid when empty / unknown) and frames it.
func _show_preview(race_key) -> void:
	if race_mini == null:
		return
	var key: String = race_key if race_key is String and not (race_key as String).is_empty() else CharacterModel.NEUTRAL_ID
	race_mini.visible = true
	race_mini.setup(key)
	_frame_preview()

## Places the preview camera so the whole body, from the AABB, fits with a margin.
func _frame_preview() -> void:
	if race_mini == null or _preview_cam == null or _preview_vp == null:
		return
	var box: AABB = race_mini.get_visual_aabb()
	var aspect := float(maxi(_preview_vp.size.x, 1)) / float(maxi(_preview_vp.size.y, 1))
	var tan_half := tan(deg_to_rad(_preview_cam.fov) * 0.5)
	var radius := maxf(box.size.x, box.size.z) * 0.5
	var half_h := box.size.y * 0.5 * PREVIEW_MARGIN
	var half_w := radius * PREVIEW_MARGIN
	var dist := maxf(half_h / tan_half, half_w / (tan_half * aspect)) + radius
	var centre: Vector3 = race_mini.position + box.get_center()
	var pitch := deg_to_rad(PREVIEW_PITCH_DEG)
	_preview_cam.position = centre + Vector3(0.0, sin(pitch) * dist, cos(pitch) * dist)
	_preview_cam.look_at(centre, Vector3.UP)

func _on_state_updated(state: Dictionary):
	for slot in state.get("lobby_slots", []):
		if slot.get("status") in ["claimed", "creating"]:
			slot_index = slot.get("slot_index", 0)
			break

func _on_catalog_received(new_catalog: Dictionary):
	catalog = new_catalog
	_render_step()

# ─── Rendering ─────────────────────────────────────────────────────

func _preview_wanted() -> bool:
	if current_step == 1:
		return false   # the race preview lives inside the carousel's centre card
	if current_step == 0 or current_step == 4:
		return false
	return get_viewport().get_visible_rect().size.x >= WIDE_PREVIEW_MIN_W

func _desc_wanted() -> bool:
	return current_step != 1 and current_step != 4

func _apply_layout_mode() -> void:
	if preview_slot == null:
		return
	preview_slot.visible = _preview_wanted()
	_sync_preview_panel()

func _render_step():
	if catalog.is_empty():
		return
	_clear_list()
	next_btn.disabled = true
	title_label.text = STEPS[current_step]
	step_label.text = "Step %d / %d" % [current_step + 1, STEPS.size()]
	step_dots.count = STEPS.size()
	step_dots.current = current_step
	back_btn.text = "Menu" if current_step == 0 else "Back"
	next_btn.text = "Create" if current_step == STEPS.size() - 1 else "Continue"

	var race_step := current_step == 1
	chip_row.visible = race_step
	index_label.visible = race_step
	carousel.visible = race_step
	main_col.visible = not race_step
	desc_panel.visible = _desc_wanted()
	_apply_layout_mode()

	match current_step:
		0: _render_era_step()
		1: _render_race_step()
		2: _render_choice_step(catalog.get("states", {}), "evolution_state", "Choose your evolutionary form…")
		3: _render_choice_step(catalog.get("roles",  {}), "predator_role",   "Choose your predator role…")
		4: _render_abilities_step()
		5: _render_name_step()
	if current_step != 1 or selection["race"] == null:
		_show_preview(selection["race"])

## Frees children immediately (not queue_free alone) so stale nodes never share the tree with
## the new ones: layout and the UI test only ever see the current step.
func _clear_list():
	for child in race_list.get_children():
		race_list.remove_child(child)
		child.queue_free()
	description_label.text = ""

## The preview panel is a top-level control that follows the active slot (the carousel's centre
## card on the race step, the side slot otherwise). It is never reparented: RaceMini and its
## SubViewport stay in the tree, so no exit/enter cycle per step.
func _active_preview_slot() -> Control:
	if current_step == 1:
		return carousel.get_meta("preview_slot")
	return preview_slot

func _sync_preview_panel() -> void:
	var slot := _active_preview_slot()
	var show := slot != null and slot.is_visible_in_tree() and not _typing
	preview_panel.visible = show
	if show:
		var gr := slot.get_global_rect()
		if preview_panel.global_position != gr.position:
			preview_panel.global_position = gr.position
		if preview_panel.size != gr.size:
			preview_panel.size = gr.size

## One big touch card: bold title + muted caption, toggle-able. Child labels pass the touch through.
func _make_card(title: String, sub: String, group: ButtonGroup) -> Button:
	var btn := Button.new()
	btn.toggle_mode = true
	btn.button_group = group
	btn.custom_minimum_size = Vector2(0, 180)
	btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	btn.size_flags_vertical = Control.SIZE_EXPAND_FILL
	var box := VBoxContainer.new()
	box.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	box.offset_left = 14
	box.offset_right = -14
	box.offset_top = 10
	box.offset_bottom = -10
	box.alignment = BoxContainer.ALIGNMENT_CENTER
	box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var t := Label.new()
	t.text = title
	t.theme_type_variation = &"AccentLabel"
	t.add_theme_font_size_override("font_size", 36)
	t.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	t.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	t.mouse_filter = Control.MOUSE_FILTER_IGNORE
	box.add_child(t)
	if not sub.is_empty():
		var l := Label.new()
		l.text = sub
		l.theme_type_variation = &"MutedLabel"
		l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		l.max_lines_visible = 3
		l.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0))
		l.mouse_filter = Control.MOUSE_FILTER_IGNORE
		box.add_child(l)
	btn.add_child(box)
	btn.toggled.connect(func(on: bool):
		t.add_theme_color_override("font_color", Color("#14100d") if on else Color("#dca331"))
		for ch in box.get_children():
			if ch != t:
				ch.add_theme_color_override("font_color", Color("#2b211a") if on else Color("#8d7f6a")))
	return btn

func _card_row() -> HBoxContainer:
	var row := HBoxContainer.new()
	row.size_flags_vertical = Control.SIZE_EXPAND_FILL
	row.add_theme_constant_override("separation", 12)
	race_list.add_child(row)
	return row

func _first_sentence(text: String) -> String:
	var i := text.find(". ")
	return text.substr(0, i + 1) if i > 0 else text

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
		{ "id": "after",  "label": "After",  "sub": "The Feral World. The Paradox already found you." },
		{ "id": "before", "label": "Before", "sub": "The Civilized World. You are what you were." },
	]

	var group = ButtonGroup.new()
	group.set("allow_unpress", false)
	var row := _card_row()
	var first: Button = null

	for era in eras:
		var btn := _make_card(era["label"], era["sub"], group)
		if selection["starting_era"] == era["id"]:
			btn.set_pressed_no_signal(true)
			btn.toggled.emit(true)
			next_btn.disabled = false
		btn.mouse_entered.connect(func(): AudioManager.play_sfx("res://assets/audio/sfx_ui_hover.wav"))
		btn.pressed.connect(func():
			selection["starting_era"] = era["id"]
			next_btn.disabled = false
			# Reset race if era changed — before-only humanoid display may differ
			selection["race"] = null
		)
		row.add_child(btn)
		if first == null:
			first = btn
	if first:
		first.grab_focus.call_deferred()

# ── Step 1: Race (era-aware swipe carousel) ────────────────────────

func _race_order() -> Array:
	var races: Dictionary = catalog.get("races", {})
	var out: Array = []
	for g in GROUP_ORDER:
		for key in races:
			if races[key].get("group", "Other") == g:
				out.append(key)
	for key in races:
		if not out.has(key):
			out.append(key)
	return out

func _build_carousel() -> void:
	carousel = RaceCarousel.new()
	carousel.name = "RaceCarousel"
	carousel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	carousel.size_flags_vertical = Control.SIZE_EXPAND_FILL
	carousel.custom_minimum_size = Vector2(0, 240)
	content.add_child(carousel)
	content.move_child(carousel, 0)

	var card := PanelContainer.new()
	card.theme_type_variation = &"CardPanel"
	var hb := HBoxContainer.new()
	hb.add_theme_constant_override("separation", 12)
	card.add_child(hb)
	var slot := Control.new()      # the (top-level) preview panel follows this slot on the race step
	slot.name = "PreviewSlot"
	slot.custom_minimum_size = Vector2(150, 0)
	slot.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	slot.size_flags_vertical = Control.SIZE_EXPAND_FILL
	slot.size_flags_stretch_ratio = 0.9
	slot.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hb.add_child(slot)
	carousel.set_meta("preview_slot", slot)
	var info := VBoxContainer.new()
	info.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	info.size_flags_stretch_ratio = 1.1
	info.add_theme_constant_override("separation", 4)
	info.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hb.add_child(info)
	# Autowrap labels report ~0 minimum height, so give each a floor or the VBox squashes them.
	_card_name = _info_label(info, &"AccentLabel", 40)
	_card_name.custom_minimum_size = Vector2(0, 52)
	_card_name.autowrap_mode = TextServer.AUTOWRAP_OFF
	_card_was = _info_label(info, &"MutedLabel", 0)
	_card_was.custom_minimum_size = Vector2(0, 32)
	_card_was.autowrap_mode = TextServer.AUTOWRAP_OFF
	_card_flavor = _info_label(info, &"Label", 26)
	_card_flavor.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_card_flavor.custom_minimum_size = Vector2(0, 100)
	_card_bonus = _info_label(info, &"AccentLabel", 26)
	_card_bonus.custom_minimum_size = Vector2(0, 76)
	carousel.set_center(card)
	carousel.index_changed.connect(_on_carousel_index_changed)
	carousel.visible = false

func _info_label(parent: Control, variation: StringName, font_size: int) -> Label:
	var l := Label.new()
	l.theme_type_variation = variation
	if font_size > 0:
		l.add_theme_font_size_override("font_size", font_size)
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.clip_text = true
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(l)
	return l

func _render_race_step():
	description_label.text = ""
	var races: Dictionary = catalog.get("races", {})
	_race_order_refresh()
	# Group chips: jump to the first race of a group, highlight the current one.
	for c in chip_row.get_children():
		chip_row.remove_child(c)
		c.queue_free()
	_chips.clear()
	for g in GROUP_ORDER:
		var chip := Button.new()
		chip.theme_type_variation = &"ChipButton"
		chip.text = g
		chip.toggle_mode = true
		chip.clip_text = true
		chip.custom_minimum_size = Vector2(MIN_TOUCH, MIN_TOUCH)
		chip.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		var first_idx := _first_index_of_group(g)
		chip.disabled = first_idx < 0
		chip.pressed.connect(func():
			if first_idx >= 0:
				carousel.select_index(first_idx)
			_sync_chips())
		chip_row.add_child(chip)
		_chips[g] = chip

	var start := 0
	if selection["race"] != null and _race_ids.has(selection["race"]):
		start = _race_ids.find(selection["race"])
	carousel.set_items(_race_ids, start)
	carousel.settle()
	selection["race"] = _race_ids[start] if not _race_ids.is_empty() else null
	next_btn.disabled = _race_ids.is_empty()
	_update_race_card()
	if not races.is_empty():
		carousel.grab_focus.call_deferred()

func _race_order_refresh() -> void:
	_race_ids = _race_order()

func _first_index_of_group(g: String) -> int:
	var races: Dictionary = catalog.get("races", {})
	for i in _race_ids.size():
		if races[_race_ids[i]].get("group", "Other") == g:
			return i
	return -1

func _sync_chips() -> void:
	if _race_ids.is_empty():
		return
	var races: Dictionary = catalog.get("races", {})
	var cur_group: String = races[_race_ids[carousel.index]].get("group", "Other")
	for g in _chips:
		(_chips[g] as Button).set_pressed_no_signal(g == cur_group)

func _on_carousel_index_changed(i: int) -> void:
	if i < 0 or i >= _race_ids.size():
		return
	selection["race"] = _race_ids[i]
	next_btn.disabled = false
	_update_race_card()
	if is_inside_tree() and _preview_timer:
		_preview_timer.start()

## Fills the centre card, the position indicator and the chips from the centred race.
func _update_race_card() -> void:
	if _race_ids.is_empty():
		return
	var races: Dictionary = catalog.get("races", {})
	var key: String = _race_ids[carousel.index]
	var data: Dictionary = races[key]
	var is_before: bool = selection["starting_era"] == "before"
	var before_str: String = data.get("before", "")
	var name_str: String = data.get("name", key)
	_card_name.text = name_str
	if before_str:
		_card_was.text = ("Civilized form: %s" % before_str) if is_before else ("(was %s)" % before_str)
	else:
		_card_was.text = ""
	_card_was.visible = not _card_was.text.is_empty()
	_card_flavor.text = data.get("flavor", "")
	var bonus_parts = []
	var bonuses = data.get("ability_bonuses", {})
	for ab in bonuses:
		bonus_parts.append("%s +%d" % [ab, bonuses[ab]])
	_card_bonus.text = "%s\nSpeed %d ft" % ["  ".join(bonus_parts), data.get("speed", 30)]
	index_label.text = "%d / %d  ·  %s" % [carousel.index + 1, _race_ids.size(), data.get("group", "")]
	_sync_chips()

# ── Step 2/3: Generic choice (state / role) ────────────────────────

func _render_choice_step(options: Dictionary, field: String, placeholder: String):
	description_label.text = placeholder
	var group = ButtonGroup.new()
	group.set("allow_unpress", false)
	var row := _card_row()
	var focus_btn: Button = null

	for key in options:
		var data = options[key]
		var btn := _make_card(data.get("name", key), _first_sentence(data.get("flavor", "")), group)
		if selection[field] == key:
			btn.set_pressed_no_signal(true)
			btn.toggled.emit(true)
			next_btn.disabled = false
			_preview_item(data)
			focus_btn = btn
		btn.mouse_entered.connect(func(): AudioManager.play_sfx("res://assets/audio/sfx_ui_hover.wav"))
		btn.pressed.connect(func():
			selection[field] = key
			next_btn.disabled = false
			_preview_item(data)
		)
		row.add_child(btn)
		if focus_btn == null and row.get_child_count() == 1:
			focus_btn = btn
	if focus_btn:
		focus_btn.grab_focus.call_deferred()

func _preview_item(data: Dictionary):
	var name_str = data.get("name", "")
	var flavor   = data.get("flavor", "")
	var text = "[b]%s[/b]" % name_str
	if flavor:
		text += "\n\n%s" % flavor
	description_label.text = text

# ── Step 4: Abilities ──────────────────────────────────────────────

func _next_unassigned() -> String:
	for ab in ABILITY_KEYS:
		if selection["abilities"][ab] == null:
			return ab
	return ""

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
	if _focused_ability == "" and not all_assigned:
		_focused_ability = _next_unassigned()

	var race_id = selection.get("race")
	var race_data = catalog.get("races", {}).get(race_id, {})
	var bonuses = race_data.get("ability_bonuses", {})

	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	race_list.add_child(scroll)
	var col := VBoxContainer.new()
	col.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	col.add_theme_constant_override("separation", 8)
	scroll.add_child(col)

	# Six ability tiles, two columns. Tap a tile to aim at it, then tap a value below.
	var grid := GridContainer.new()
	grid.columns = 2
	grid.add_theme_constant_override("h_separation", 12)
	grid.add_theme_constant_override("v_separation", 12)
	grid.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	col.add_child(grid)
	for ab in ABILITY_KEYS:
		grid.add_child(_make_ability_tile(ab, bonuses.get(ab, 0)))

	# Hint line: fixed height so nothing below it shifts.
	var hint := Label.new()
	hint.theme_type_variation = &"MutedLabel"
	hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	hint.custom_minimum_size = Vector2(0, 64)
	hint.max_lines_visible = 2
	if all_assigned:
		hint.text = "All assigned. Racial bonuses are applied on creation."
	elif _focused_ability != "":
		hint.text = "%s: %s" % [ABILITY_NAMES[_focused_ability], ABILITY_HELP[_focused_ability]]
	else:
		hint.text = "Pick an ability, then a value."
	col.add_child(hint)

	# Value pool: always six slots, used ones disabled, so the row never changes size.
	var pool_row := HBoxContainer.new()
	pool_row.add_theme_constant_override("separation", 12)
	for v in STANDARD_ARRAY:
		var pool_btn := Button.new()
		pool_btn.text = str(v)
		pool_btn.custom_minimum_size = Vector2(MIN_TOUCH, MIN_TOUCH)
		pool_btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		pool_btn.add_theme_font_size_override("font_size", 40)
		pool_btn.disabled = not _pool_remaining.has(v) or _focused_ability == ""
		pool_btn.pressed.connect(func():
			selection["abilities"][_focused_ability] = v
			_focused_ability = ""
			_render_step()
		)
		pool_row.add_child(pool_btn)
	col.add_child(pool_row)

func _make_ability_tile(ab: String, bonus: int) -> Control:
	var current_val = selection["abilities"][ab]
	var row := HBoxContainer.new()
	row.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_theme_constant_override("separation", 8)

	var tile := Button.new()
	tile.toggle_mode = true
	tile.custom_minimum_size = Vector2(0, MIN_TOUCH)
	tile.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	if _focused_ability == ab:
		tile.set_pressed_no_signal(true)
	var hb := HBoxContainer.new()
	hb.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	hb.offset_left = 14
	hb.offset_right = -14
	hb.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hb.add_theme_constant_override("separation", 10)
	tile.add_child(hb)
	var dark := Color("#14100d")
	var on: bool = _focused_ability == ab

	var names := VBoxContainer.new()
	names.alignment = BoxContainer.ALIGNMENT_CENTER
	names.mouse_filter = Control.MOUSE_FILTER_IGNORE
	names.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var abbr := Label.new()
	abbr.text = ab
	abbr.add_theme_font_size_override("font_size", 36)
	abbr.add_theme_color_override("font_color", dark if on else Color("#dca331"))
	abbr.mouse_filter = Control.MOUSE_FILTER_IGNORE
	names.add_child(abbr)
	var full := Label.new()
	full.text = ABILITY_NAMES[ab] + ("  +%d" % bonus if bonus > 0 else "")
	full.add_theme_font_size_override("font_size", 24)
	full.add_theme_color_override("font_color", dark if on else Color("#8d7f6a"))
	full.clip_text = true
	full.mouse_filter = Control.MOUSE_FILTER_IGNORE
	names.add_child(full)
	hb.add_child(names)

	var val := Label.new()
	val.text = str(current_val) if current_val != null else "—"
	val.add_theme_font_size_override("font_size", 52)
	val.add_theme_color_override("font_color", dark if on else Color("#ffe699"))
	val.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	val.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	val.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hb.add_child(val)
	if current_val != null and bonus > 0:
		var total := Label.new()
		total.text = "= %d" % (current_val + bonus)
		total.add_theme_color_override("font_color", dark if on else Color("#8dd17a"))
		total.size_flags_vertical = Control.SIZE_SHRINK_CENTER
		total.mouse_filter = Control.MOUSE_FILTER_IGNORE
		hb.add_child(total)

	tile.pressed.connect(func():
		_focused_ability = ab
		_render_step()
	)
	row.add_child(tile)

	var clear_btn := Button.new()
	clear_btn.text = "Clear"
	clear_btn.theme_type_variation = &"ChipButton"
	clear_btn.custom_minimum_size = Vector2(MIN_TOUCH, MIN_TOUCH)
	clear_btn.disabled = current_val == null
	clear_btn.pressed.connect(func():
		selection["abilities"][ab] = null
		_focused_ability = ab
		_render_step()
	)
	row.add_child(clear_btn)
	return row

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
	name_input.custom_minimum_size = Vector2(0, MIN_TOUCH)
	name_input.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	name_input.add_theme_font_size_override("font_size", 36)
	name_input.text_changed.connect(func(val: String):
		selection["name"] = val.strip_edges()
		next_btn.disabled = selection["name"].is_empty()
	)
	name_input.text_submitted.connect(func(_v):
		if not next_btn.disabled:
			_on_next_btn_pressed()
	)
	race_list.add_child(name_input)
	# Desktop: type straight away. On a phone this would pop the keyboard before the player
	# has seen the summary, so wait for a tap.
	if not OS.has_feature("mobile"):
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
	if _submitting:
		return
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
	next_btn.text = "Create"
	description_label.text = "[color=red]Creation failed: %s[/color]" % error

func _on_game_started():
	get_tree().change_scene_to_file("res://scenes/Tabletop.tscn")

func _on_game_start_failed(error: String):
	_submitting = false
	next_btn.disabled = false
	next_btn.text = "Create"
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
