extends SceneTree
## Regression test: the "Continue Journey" save list rendered nothing ("no buttons in the menu").
##
## UI_Overlay.tscn used `size_hint_vertical = 3`, a property Godot 4 does not have (it is
## `size_flags_vertical`), so the ScrollContainer collapsed to height 0 and clipped every row.
## This test lays the menu out headless and measures it: the list must have real height, every row
## must be touch-sized, and the main-menu buttons too. The negative control puts the bug condition
## back (default size flags) and checks the same measurement now FAILS, so the check can tell.
##
##   godot --headless --path godot -s res://tests/golden/save_menu_test.gd
## Last line: RESULT: OK | RESULT: FAILED

const MIN_TOUCH_HEIGHT := 96.0
const FAKE_SAVES := [
	{"campaign_id": "family_campaign_01", "characters": ["Rook", "Mira"], "phase": "exploration"},
	{"campaign_id": "campaign_b", "characters": ["Dax"], "phase": "creation"},
	{"campaign_id": "campaign_c", "characters": [], "phase": "lobby"},
]

var _checks := 0
var _failed := 0


func _init() -> void:
	call_deferred("_run")


func _ok(cond: bool, label: String) -> void:
	_checks += 1
	if cond:
		print("  ok   %s" % label)
	else:
		_failed += 1
		print("  FAIL %s" % label)


func _settle() -> void:
	for _i in 5:
		await process_frame


func _scroll_of(ui: Node) -> ScrollContainer:
	return ui.get_node("SaveGameMenu/MarginContainer/VBoxContainer/ScrollContainer") as ScrollContainer


func _run() -> void:
	var packed := load("res://scenes/UI_Overlay.tscn") as PackedScene
	var ui := packed.instantiate()
	get_root().add_child(ui)
	await _settle()

	print("-- main menu buttons are touch-sized")
	ui.title_screen.hide()
	ui.main_menu.show()
	await _settle()
	for b in [ui.new_game_btn, ui.load_game_btn]:
		_ok((b as Control).size.y >= MIN_TOUCH_HEIGHT,
			"%s height %.0f >= %.0f" % [(b as Button).text, (b as Control).size.y, MIN_TOUCH_HEIGHT])

	print("-- save list with 3 saves")
	ui.main_menu.hide()
	ui.save_game_menu.show()
	ui._on_campaigns_received(FAKE_SAVES)
	await _settle()
	var sc := _scroll_of(ui)
	_ok(sc.size.y > 120.0, "ScrollContainer has real height (%.0f > 120)" % sc.size.y)
	var rows: Array = ui.save_list.get_children()
	_ok(rows.size() == 3, "3 rows created (got %d)" % rows.size())
	var all_big := true
	var all_inside := true
	var sc_rect := sc.get_global_rect()
	for r in rows:
		var c := r as Control
		if c.size.y < MIN_TOUCH_HEIGHT:
			all_big = false
		if not sc_rect.encloses(c.get_global_rect()):
			all_inside = false
	_ok(all_big, "every row >= %.0f units tall" % MIN_TOUCH_HEIGHT)
	_ok(all_inside, "every row lies inside the ScrollContainer (visible, not clipped)")
	_ok((rows[0] as Button).text.begins_with("family_campaign_01"), "first row names the campaign")

	print("-- empty list shows its message")
	ui._on_campaigns_received([])
	await _settle()
	var kids: Array = ui.save_list.get_children()
	var live := kids.filter(func(n): return not n.is_queued_for_deletion())
	_ok(live.size() == 1 and live[0] is Label, "one Label ('No saved chronicles found.')")
	_ok(sc.get_global_rect().encloses((live[0] as Control).get_global_rect()),
		"the message is inside the visible ScrollContainer")

	print("-- negative control: restoring the bug (default size flags) collapses the list")
	ui._on_campaigns_received(FAKE_SAVES)
	sc.size_flags_vertical = Control.SIZE_FILL
	await _settle()
	_ok(sc.size.y < 10.0, "with the bug restored the ScrollContainer is %.0f tall (< 10)" % sc.size.y)

	print("save_menu_test: %d checks, %d failed" % [_checks, _failed])
	print("RESULT: OK" if _failed == 0 else "RESULT: FAILED")
	quit(0 if _failed == 0 else 1)
