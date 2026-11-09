extends SceneTree
## Deterministic generator for res://assets/ui/storyforge_theme.tres (the one project theme).
## Palette: docs/assets/palette.json ("dark" = dark vellum). Regenerate with:
##   godot --headless --path godot -s res://tools/ui/gen_theme.gd
## Output goes to res://assets/ui/storyforge_theme.tres, or to --out=<path> when given.

const BG := Color("#14100d")
const SURFACE := Color("#2b211a")
const BORDER := Color("#8a6a3b")
const ACCENT := Color("#dca331")
const HIGHLIGHT := Color("#ffe699")
const TEXT := Color("#f1e4c3")
const MUTED := Color("#8d7f6a")
const DARK_TEXT := Color("#14100d")

const FONT_SIZE := 28
const TITLE_SIZE := 56
const SMALL_SIZE := 24
const RADIUS := 10
const SCROLL_THICKNESS := 24


func _init() -> void:
	var out := "res://assets/ui/storyforge_theme.tres"
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--out="):
			out = a.substr(6)
	var err := ResourceSaver.save(build(), out)
	if err == OK:
		_stabilise_ids(out)
	print("gen_theme: saved %s err=%d" % [out, err])
	quit(0 if err == OK else 1)


## ResourceSaver names sub-resources with random suffixes; renumber them in file order so the
## .tres is byte-identical between runs.
func _stabilise_ids(path: String) -> void:
	var f := FileAccess.open(path, FileAccess.READ)
	var text := f.get_as_text()
	f.close()
	var rx := RegEx.new()
	rx.compile("(?:id=|SubResource\\()\"([A-Za-z0-9]+)_([a-z0-9]{5})\"")
	var map := {}
	var n := 0
	for m in rx.search_all(text):
		var old := m.get_string(1) + "_" + m.get_string(2)
		if not map.has(old):
			map[old] = "%s_%03d" % [m.get_string(1), n]
			n += 1
	for old in map:
		text = text.replace("\"%s\"" % old, "\"%s\"" % map[old])
	var w := FileAccess.open(path, FileAccess.WRITE)
	w.store_string(text)
	w.close()


func _box(fill: Color, border: Color, border_w := 2, radius := RADIUS, pad := 14) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = fill
	sb.border_color = border
	sb.set_border_width_all(border_w)
	sb.set_corner_radius_all(radius)
	sb.content_margin_left = pad
	sb.content_margin_right = pad
	sb.content_margin_top = pad * 0.5
	sb.content_margin_bottom = pad * 0.5
	return sb


func _focus_ring() -> StyleBoxFlat:
	# Transparent fill + a thick highlight outline: stays visible on top of any state.
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0, 0, 0, 0)
	sb.draw_center = false
	sb.border_color = HIGHLIGHT
	sb.set_border_width_all(4)
	sb.set_corner_radius_all(RADIUS + 2)
	sb.expand_margin_left = 2
	sb.expand_margin_right = 2
	sb.expand_margin_top = 2
	sb.expand_margin_bottom = 2
	return sb


func build() -> Theme:
	var t := Theme.new()
	t.default_font_size = FONT_SIZE

	# Buttons (Button, CheckBox-less): surface + border; hover/focus accent; pressed accent fill.
	for type in ["Button", "OptionButton", "MenuButton"]:
		t.set_stylebox("normal", type, _box(SURFACE, BORDER))
		t.set_stylebox("hover", type, _box(SURFACE.lightened(0.08), ACCENT))
		t.set_stylebox("pressed", type, _box(ACCENT, HIGHLIGHT))
		t.set_stylebox("hover_pressed", type, _box(ACCENT.lightened(0.1), HIGHLIGHT))
		t.set_stylebox("disabled", type, _box(BG.lightened(0.04), MUTED.darkened(0.45)))
		t.set_stylebox("focus", type, _focus_ring())
		t.set_color("font_color", type, TEXT)
		t.set_color("font_hover_color", type, HIGHLIGHT)
		t.set_color("font_focus_color", type, HIGHLIGHT)
		t.set_color("font_pressed_color", type, DARK_TEXT)
		t.set_color("font_hover_pressed_color", type, DARK_TEXT)
		t.set_color("font_disabled_color", type, MUTED.darkened(0.3))
		t.set_font_size("font_size", type, FONT_SIZE)
		t.set_constant("h_separation", type, 10)

	# Small variant used for chips and captions.
	t.set_type_variation("ChipButton", "Button")
	t.set_font_size("font_size", "ChipButton", SMALL_SIZE)

	# Labels
	t.set_color("font_color", "Label", TEXT)
	t.set_color("font_shadow_color", "Label", Color(0, 0, 0, 0.5))
	t.set_font_size("font_size", "Label", FONT_SIZE)
	t.set_type_variation("TitleLabel", "Label")
	t.set_font_size("font_size", "TitleLabel", TITLE_SIZE)
	t.set_color("font_color", "TitleLabel", HIGHLIGHT)
	t.set_type_variation("MutedLabel", "Label")
	t.set_font_size("font_size", "MutedLabel", SMALL_SIZE)
	t.set_color("font_color", "MutedLabel", MUTED)
	t.set_type_variation("AccentLabel", "Label")
	t.set_color("font_color", "AccentLabel", ACCENT)

	t.set_color("default_color", "RichTextLabel", TEXT)
	t.set_font_size("normal_font_size", "RichTextLabel", FONT_SIZE)
	t.set_font_size("bold_font_size", "RichTextLabel", FONT_SIZE)
	t.set_font_size("italics_font_size", "RichTextLabel", FONT_SIZE)
	t.set_font_size("bold_italics_font_size", "RichTextLabel", FONT_SIZE)
	t.set_font_size("mono_font_size", "RichTextLabel", FONT_SIZE)

	# Panels
	var panel := _box(SURFACE, BORDER, 2, RADIUS, 12)
	t.set_stylebox("panel", "Panel", panel)
	t.set_stylebox("panel", "PanelContainer", panel)
	t.set_type_variation("DarkPanel", "PanelContainer")
	t.set_stylebox("panel", "DarkPanel", _box(BG.lightened(0.03), BORDER.darkened(0.3), 2, RADIUS, 12))
	t.set_type_variation("CardPanel", "PanelContainer")
	t.set_stylebox("panel", "CardPanel", _box(SURFACE, ACCENT, 3, RADIUS + 4, 12))
	t.set_stylebox("panel", "TooltipPanel", _box(SURFACE, ACCENT, 2, 8, 10))
	t.set_color("font_color", "TooltipLabel", TEXT)
	t.set_font_size("font_size", "TooltipLabel", SMALL_SIZE)

	# Text input
	var le_normal := _box(BG, BORDER, 2, RADIUS, 14)
	t.set_stylebox("normal", "LineEdit", le_normal)
	t.set_stylebox("focus", "LineEdit", _box(BG, ACCENT, 3, RADIUS, 14))
	t.set_stylebox("read_only", "LineEdit", _box(BG, MUTED.darkened(0.4), 2, RADIUS, 14))
	t.set_color("font_color", "LineEdit", TEXT)
	t.set_color("font_placeholder_color", "LineEdit", MUTED)
	t.set_color("caret_color", "LineEdit", HIGHLIGHT)
	t.set_color("selection_color", "LineEdit", ACCENT.darkened(0.4))
	t.set_font_size("font_size", "LineEdit", FONT_SIZE)
	t.set_stylebox("normal", "TextEdit", le_normal)
	t.set_stylebox("focus", "TextEdit", _box(BG, ACCENT, 3, RADIUS, 14))
	t.set_color("font_color", "TextEdit", TEXT)
	t.set_font_size("font_size", "TextEdit", FONT_SIZE)

	# Scrollbars (touch thick), grabber in the accent family
	var track := StyleBoxFlat.new()
	track.bg_color = BG.lightened(0.04)
	track.set_corner_radius_all(SCROLL_THICKNESS / 2)
	track.content_margin_left = SCROLL_THICKNESS / 2.0
	track.content_margin_right = SCROLL_THICKNESS / 2.0
	track.content_margin_top = SCROLL_THICKNESS / 2.0
	track.content_margin_bottom = SCROLL_THICKNESS / 2.0
	var grab := StyleBoxFlat.new()
	grab.bg_color = BORDER
	grab.set_corner_radius_all(SCROLL_THICKNESS / 2)
	grab.content_margin_left = SCROLL_THICKNESS / 2.0
	grab.content_margin_right = SCROLL_THICKNESS / 2.0
	grab.content_margin_top = SCROLL_THICKNESS / 2.0
	grab.content_margin_bottom = SCROLL_THICKNESS / 2.0
	var grab_hi := grab.duplicate() as StyleBoxFlat
	grab_hi.bg_color = ACCENT
	for type in ["VScrollBar", "HScrollBar"]:
		t.set_stylebox("scroll", type, track)
		t.set_stylebox("scroll_focus", type, track)
		t.set_stylebox("grabber", type, grab)
		t.set_stylebox("grabber_highlight", type, grab_hi)
		t.set_stylebox("grabber_pressed", type, grab_hi)
	t.set_stylebox("panel", "ScrollContainer", StyleBoxEmpty.new())
	t.set_constant("scrollbar_h_separation", "ScrollContainer", 6)
	t.set_constant("scrollbar_v_separation", "ScrollContainer", 6)

	# ItemList / ProgressBar (HP) / Slider
	t.set_stylebox("panel", "ItemList", _box(BG, BORDER, 2, RADIUS, 8))
	t.set_stylebox("focus", "ItemList", _focus_ring())
	t.set_stylebox("selected", "ItemList", _box(ACCENT.darkened(0.35), ACCENT, 2, 6, 8))
	t.set_stylebox("selected_focus", "ItemList", _box(ACCENT.darkened(0.2), HIGHLIGHT, 2, 6, 8))
	t.set_color("font_color", "ItemList", TEXT)
	t.set_color("font_selected_color", "ItemList", HIGHLIGHT)
	t.set_font_size("font_size", "ItemList", FONT_SIZE)
	t.set_stylebox("background", "ProgressBar", _box(BG, BORDER, 2, 6, 4))
	t.set_stylebox("fill", "ProgressBar", _box(ACCENT, ACCENT, 0, 6, 4))
	t.set_color("font_color", "ProgressBar", TEXT)
	t.set_font_size("font_size", "ProgressBar", SMALL_SIZE)

	# Popups (OptionButton lists, menus)
	t.set_stylebox("panel", "PopupMenu", _box(SURFACE, BORDER, 2, 8, 8))
	t.set_stylebox("hover", "PopupMenu", _box(ACCENT.darkened(0.35), ACCENT, 0, 6, 8))
	t.set_color("font_color", "PopupMenu", TEXT)
	t.set_color("font_hover_color", "PopupMenu", HIGHLIGHT)
	t.set_font_size("font_size", "PopupMenu", FONT_SIZE)
	t.set_constant("v_separation", "PopupMenu", 14)
	return t
