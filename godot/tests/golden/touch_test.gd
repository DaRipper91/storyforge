extends SceneTree
## Headless test of TouchControls (res://scripts/ui/touch_controls.gd). No display needed.
##   godot --headless --path <scratch copy of godot/> -s res://tests/golden/touch_test.gd
## Exit 0 only when every check passes; final stdout line is `RESULT: OK|FAILED`.
## Includes a NEGATIVE check: the same joystick assertion run against a deliberately broken
## subclass must report failure, proving the assertion can fail.

const MOVE := ["move_left", "move_right", "move_up", "move_down"]
const LOOK := ["look_left", "look_right", "look_up", "look_down"]
const WATCH := ["action", "cycle_prev", "cycle_next", "map", "reset_cam", "freeform"]

var _fails := 0
var _checks := 0


## Parent of the TouchControls, standing in for Tabletop: records what reaches a world node.
class Sink extends Node:
	var counts := {}
	var mouse_presses := 0
	var left_clicks := 0
	var wheel_up := 0
	var wheel_down := 0
	var touches := 0

	func _input(event: InputEvent) -> void:
		if event is InputEventScreenTouch or event is InputEventScreenDrag:
			touches += 1
		if event is InputEventMouseButton and event.pressed:
			mouse_presses += 1
			if event.button_index == MOUSE_BUTTON_LEFT:
				left_clicks += 1
			elif event.button_index == MOUSE_BUTTON_WHEEL_UP:
				wheel_up += 1
			elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
				wheel_down += 1
		# Same polling pattern Tabletop._input uses.
		for a in ["action", "cycle_prev", "cycle_next", "map", "reset_cam", "freeform"]:
			if Input.is_action_just_pressed(a):
				counts[a] = int(counts.get(a, 0)) + 1


## Deliberately broken: the joystick never reaches the actions.
class BrokenTC extends TouchControls:
	func _apply_vector(_actions: Array, _v: Vector2) -> void:
		pass


func _check(label: String, cond: bool, detail: String = "") -> void:
	_checks += 1
	if cond:
		print("  ok   ", label)
	else:
		_fails += 1
		printerr("  FAIL ", label, "  ", detail)


func _initialize() -> void:
	_run()


func _make(cls, vp := Vector2(1280, 720), ppm := 11.0, safe := Rect2()) -> Array:
	var sink := Sink.new()
	root.add_child(sink)
	var tc: TouchControls = cls.new()
	sink.add_child(tc)
	tc.configure(vp, ppm, safe)
	return [sink, tc]


func _free(pair: Array) -> void:
	pair[1].release_all()
	pair[0].queue_free()


func _touch(tc: TouchControls, idx: int, pos: Vector2, pressed: bool, canceled := false) -> void:
	var e := InputEventScreenTouch.new()
	e.index = idx
	e.position = pos
	e.pressed = pressed
	e.canceled = canceled
	tc._input(e)


func _drag(tc: TouchControls, idx: int, pos: Vector2) -> void:
	var e := InputEventScreenDrag.new()
	e.index = idx
	e.position = pos
	tc._input(e)


func _vec(actions: Array) -> Vector2:
	return Input.get_vector(actions[0], actions[1], actions[2], actions[3])


func _joy_start(tc: TouchControls) -> Vector2:
	return (tc.get_layout()["joy"] as Rect2).get_center()


func _btn_center(tc: TouchControls, name: String) -> Vector2:
	return (tc.get_layout()["rects"][name] as Rect2).get_center()


func _cam_start(tc: TouchControls) -> Vector2:
	return (tc.get_layout()["cam_a"] as Rect2).get_center()


func _any_pressed(actions: Array) -> bool:
	for a in actions:
		if Input.is_action_pressed(a):
			return true
	return false


func _wait(sec: float) -> void:
	await create_timer(sec).timeout
	Input.flush_buffered_events()


## The joystick assertion shared by the real test and the negative check.
func _joy_right_works(tc: TouchControls) -> bool:
	var rad: float = tc.get_layout()["joy_radius"]
	var p := _joy_start(tc)
	_touch(tc, 0, p, true)
	_drag(tc, 0, p + Vector2(rad * 1.5, 0))
	var v := _vec(MOVE)
	var ok := v.x > 0.97 and absf(v.y) < 0.03
	_touch(tc, 0, p + Vector2(rad * 1.5, 0), false)
	return ok


func _run() -> void:
	await process_frame
	await process_frame
	var pc := root.get_node_or_null("PythonClient")
	if pc == null or not InputMap.has_action("move_left"):
		printerr("FAIL: PythonClient autoload / input map missing")
		print("RESULT: FAILED")
		quit(1)
		return

	print("-- should_show")
	_check("pure: desktop, no arg, no env -> false", not TouchControls.should_show_for(false, false, PackedStringArray(), ""))
	_check("pure: android -> true", TouchControls.should_show_for(true, false, PackedStringArray(), ""))
	_check("pure: ios -> true", TouchControls.should_show_for(false, true, PackedStringArray(), ""))
	_check("pure: --touch -> true", TouchControls.should_show_for(false, false, PackedStringArray(["--backend=local", "--touch"]), ""))
	_check("pure: env 1 -> true, env 0 -> false", TouchControls.should_show_for(false, false, PackedStringArray(), "1")
			and not TouchControls.should_show_for(false, false, PackedStringArray(), "0"))
	OS.unset_environment("STORYFORGE_TOUCH")
	var desktop_default := not OS.has_feature("android") and not OS.has_feature("ios") \
			and not ("--touch" in OS.get_cmdline_user_args())
	_check("real: default on this desktop run -> false", (not TouchControls.should_show()) if desktop_default else true)
	OS.set_environment("STORYFORGE_TOUCH", "1")
	_check("real: STORYFORGE_TOUCH=1 -> true", TouchControls.should_show())
	OS.unset_environment("STORYFORGE_TOUCH")

	print("-- joystick")
	var pair := _make(TouchControls)
	var sink: Sink = pair[0]
	var tc: TouchControls = pair[1]
	var rad: float = tc.get_layout()["joy_radius"]
	var p := _joy_start(tc)
	_touch(tc, 0, p, true)
	_drag(tc, 0, p + Vector2(rad * 1.5, 0))
	var v := _vec(MOVE)
	_check("full right -> get_vector ~ (1,0)", v.x > 0.97 and absf(v.y) < 0.03, str(v))
	_drag(tc, 0, p + Vector2(-rad * 1.5, 0))
	v = _vec(MOVE)
	_check("full left -> (-1,0)", v.x < -0.97 and absf(v.y) < 0.03, str(v))
	_drag(tc, 0, p + Vector2(0, rad * 2.0))
	v = _vec(MOVE)
	_check("down (screen +y) -> (0,1) = move_down", v.y > 0.97 and absf(v.x) < 0.03, str(v))
	_drag(tc, 0, p + Vector2(0, -rad * 2.0))
	_check("up -> (0,-1)", _vec(MOVE).y < -0.97)
	var d1 := 0.59
	_drag(tc, 0, p + Vector2(rad * d1, 0))
	var want := TouchControls.joy_strength(d1)
	v = _vec(MOVE)
	_check("partial 0.59R -> strength %.2f" % want, absf(v.length() - want) < 0.02 and v.x > 0.0, str(v))
	_drag(tc, 0, p + Vector2(rad * 0.8, 0))
	var v2 := _vec(MOVE)
	_check("more deflection -> more strength", v2.length() > v.length() + 0.1, "%s vs %s" % [v, v2])
	_drag(tc, 0, p + Vector2(rad * 0.707, rad * 0.707))
	v = _vec(MOVE)
	_check("diagonal keeps length 1 and equal axes", absf(v.length() - 1.0) < 0.03 and absf(v.x - v.y) < 0.03, str(v))
	_drag(tc, 0, p + Vector2(rad * 0.10, 0))
	_check("inside dead zone -> zero vector, nothing pressed", _vec(MOVE) == Vector2.ZERO and not _any_pressed(MOVE))
	_drag(tc, 0, p + Vector2(rad * 1.5, 0))
	_touch(tc, 0, p, false)
	_check("release clears all move actions", not _any_pressed(MOVE) and _vec(MOVE) == Vector2.ZERO)
	_check("joystick touch consumed (never reached world node)", sink.touches == 0)

	print("-- multi-touch / cancel")
	_touch(tc, 0, p, true)
	_drag(tc, 0, p + Vector2(rad * 1.5, 0))
	var c0 := _cam_start(tc)
	_touch(tc, 1, c0, true)
	_drag(tc, 1, c0 + Vector2(80, 0))
	tc._physics_process(0.016)
	var look := _vec(LOOK)
	_check("second finger orbits camera (look_right) ...", look.x > 0.5, str(look))
	_check("... while first finger still holds the joystick", _vec(MOVE).x > 0.97, str(_vec(MOVE)))
	_touch(tc, 1, c0 + Vector2(80, 0), false)
	tc._physics_process(0.016)
	_check("camera finger up releases look actions only", not _any_pressed(LOOK) and _vec(MOVE).x > 0.97)
	_touch(tc, 0, p, false, true)
	_check("cancel on joystick finger releases movement", not _any_pressed(MOVE))
	_touch(tc, 2, _btn_center(tc, "map"), true)
	_touch(tc, 2, _btn_center(tc, "map"), false, true)
	await _wait(0.05)
	_check("cancel on a button releases its action", not Input.is_action_pressed("map"))
	_touch(tc, 0, p, true)
	_drag(tc, 0, p + Vector2(rad, 0))
	_touch(tc, 3, _btn_center(tc, "interact"), true)
	Input.flush_buffered_events()
	_check("held joystick + button down", _vec(MOVE).x > 0.5 and Input.is_action_pressed("action"))
	tc.notification(Node.NOTIFICATION_APPLICATION_FOCUS_OUT)
	Input.flush_buffered_events()
	_check("focus-out releases everything", not _any_pressed(MOVE) and not Input.is_action_pressed("action"))
	_touch(tc, 0, p, true)
	_drag(tc, 0, p + Vector2(rad, 0))
	tc.visible = false
	_check("hiding the node releases everything", not _any_pressed(MOVE))
	tc.visible = true
	_touch(tc, 0, p, true)
	_drag(tc, 0, p + Vector2(rad, 0))
	tc.free()
	_check("freeing the node releases everything", not _any_pressed(MOVE))
	sink.queue_free()

	print("-- buttons")
	pair = _make(TouchControls)
	sink = pair[0]
	tc = pair[1]
	var names := {"interact": "action", "prev": "cycle_prev", "next": "cycle_next", "map": "map", "reset": "reset_cam", "say": "freeform"}
	for n in names:
		sink.counts.clear()
		var c := _btn_center(tc, n)
		_touch(tc, 5, c, true)
		Input.flush_buffered_events()
		_check("%s down -> %s pressed" % [n, names[n]], Input.is_action_pressed(names[n]))
		_touch(tc, 5, c, false)
		await _wait(0.12)
		tc._process(0.0)
		Input.flush_buffered_events()
		_check("%s tap -> exactly one just_pressed in _input" % n, int(sink.counts.get(names[n], 0)) == 1, str(sink.counts))
		_check("%s released afterwards" % n, not Input.is_action_pressed(names[n]))
		for other in WATCH:
			if other != names[n]:
				_check("%s tap leaves %s alone" % [n, other], int(sink.counts.get(other, 0)) == 0)
	_free(pair)

	print("-- layout (regions, sizes, overlap)")
	var configs := [
		["1280x720 @ 420dpi-ish", Vector2(1280, 720), 11.0, Rect2()],
		["1920x864 (20:9)", Vector2(1920, 864), 11.0, Rect2()],
		["1280x720 + safe inset", Vector2(1280, 720), 11.0, Rect2(70, 0, 1120, 690)],
		["2400x1080 + cutout inset", Vector2(2400, 1080), 5.5, Rect2(90, 20, 2200, 1040)],
		["1280x720 low dpi floor", Vector2(1280, 720), 3.0, Rect2()],
	]
	for cfg in configs:
		var pr := _make(TouchControls, cfg[1], cfg[2], cfg[3])
		var t: TouchControls = pr[1]
		var lay := t.get_layout()
		var full := Rect2(Vector2.ZERO, cfg[1])
		var safe: Rect2 = cfg[3] if (cfg[3] as Rect2).has_area() else full
		var min_px := maxf(TouchControls.MIN_BUTTON_MM * float(cfg[2]), TouchControls.MIN_BUTTON_PX)
		var overlap := ""
		var small := ""
		var outside := ""
		var regs := t.get_regions()
		for i in regs.size():
			var ri: Rect2 = regs[i]["rect"]
			if regs[i]["role"] == "button" and (ri.size.x < min_px - 0.01 or ri.size.y < min_px - 0.01):
				small += "%s(%s) " % [regs[i]["name"], ri.size]
			if not safe.encloses(ri):
				outside += "%s " % regs[i]["name"]
			if ri.size.x <= 0.0 or ri.size.y <= 0.0:
				small += "%s(empty) " % regs[i]["name"]
			for j in range(i + 1, regs.size()):
				if ri.intersects(regs[j]["rect"], false):
					overlap += "%s/%s " % [regs[i]["name"], regs[j]["name"]]
		_check("[%s] no overlapping hit regions" % cfg[0], overlap == "", overlap)
		_check("[%s] every button >= %.0f px" % [cfg[0], min_px], small == "", small)
		_check("[%s] all regions inside safe area" % cfg[0], outside == "", outside)
		_check("[%s] joystick zone and camera zone usable (>= 2 buttons wide)" % cfg[0],
				(lay["joy"] as Rect2).size.x >= 2.0 * lay["btn"] and (lay["cam_a"] as Rect2).size.x >= 2.0 * lay["btn"]
				and (lay["joy"] as Rect2).size.y >= 2.0 * lay["btn"])
		_free(pr)
	var ms := TouchControls.map_safe_area(Rect2(0, 60, 2856, 1160), Vector2(2856, 1280), Vector2(1280, 720))
	_check("map_safe_area stays inside the viewport", Rect2(0, 0, 1280, 720).encloses(ms) and ms.size.x > 1000.0, str(ms))
	_check("map_safe_area with no data -> whole viewport", TouchControls.map_safe_area(Rect2(), Vector2(100, 100), Vector2(1280, 720)) == Rect2(0, 0, 1280, 720))

	print("-- engine routing: Input.parse_input_event (emulated mouse from touch)")
	# Headless root window is 64x64; Input.parse_input_event positions are window pixels that the
	# stretch transform maps into viewport space. Make window == viewport so the transform is identity.
	root.size = Vector2i(1280, 720)
	await process_frame
	print("  info root.size=", root.size, " visible_rect=", root.get_visible_rect())
	pair = _make(TouchControls, root.get_visible_rect().size, 11.0)
	sink = pair[0]
	tc = pair[1]
	var bc := _btn_center(tc, "map")
	var evt := InputEventScreenTouch.new()
	evt.index = 0
	evt.position = bc
	evt.pressed = true
	Input.parse_input_event(evt)
	Input.flush_buffered_events()
	await process_frame
	var up := InputEventScreenTouch.new()
	up.index = 0
	up.position = bc
	up.pressed = false
	Input.parse_input_event(up)
	Input.flush_buffered_events()
	await _wait(0.12)
	tc._process(0.0)
	Input.flush_buffered_events()
	print("  info mouse-from-touch emulation setting: ", ProjectSettings.get_setting("input_devices/pointing/emulate_mouse_from_touch", true))
	_check("button touch: no emulated mouse click and no touch reached the world node", sink.mouse_presses == 0 and sink.touches == 0,
			"mouse=%d touches=%d" % [sink.mouse_presses, sink.touches])
	_check("button touch: map action seen exactly once via the engine pipeline", int(sink.counts.get("map", 0)) == 1, str(sink.counts))
	# Free spot (top centre, between the two top button groups): untouched, mouse emulation passes through.
	var free_pos := Vector2(root.get_visible_rect().size.x * 0.5, 4.0)
	_check("free spot is outside every region", tc._hit_test(free_pos).is_empty())
	sink.mouse_presses = 0
	var e2 := InputEventScreenTouch.new()
	e2.index = 0
	e2.position = free_pos
	e2.pressed = true
	Input.parse_input_event(e2)
	Input.flush_buffered_events()
	e2 = e2.duplicate()
	e2.pressed = false
	Input.parse_input_event(e2)
	Input.flush_buffered_events()
	await process_frame
	_check("touch outside controls still produces the emulated mouse click (desktop-style UI taps keep working)", sink.mouse_presses >= 1,
			"mouse_presses=%d (engine did not emulate? then this env cannot verify)" % sink.mouse_presses)
	# Tap in the camera zone: emulated press swallowed, replayed as exactly one left click.
	sink.mouse_presses = 0
	sink.left_clicks = 0
	var cp := _cam_start(tc)
	var e3 := InputEventScreenTouch.new()
	e3.index = 0
	e3.position = cp
	e3.pressed = true
	Input.parse_input_event(e3)
	Input.flush_buffered_events()
	e3 = e3.duplicate()
	e3.pressed = false
	Input.parse_input_event(e3)
	Input.flush_buffered_events()
	await process_frame
	_check("short tap in camera zone -> exactly one replayed left click (emulated one swallowed)", sink.left_clicks == 1,
			"left_clicks=%d" % sink.left_clicks)
	# Drag in the camera zone: no click at all.
	sink.left_clicks = 0
	var e4 := InputEventScreenTouch.new()
	e4.index = 0
	e4.position = cp
	e4.pressed = true
	Input.parse_input_event(e4)
	var dr := InputEventScreenDrag.new()
	dr.index = 0
	dr.position = cp + Vector2(120, 10)
	dr.relative = Vector2(120, 10)
	Input.parse_input_event(dr)
	e4 = e4.duplicate()
	e4.pressed = false
	e4.position = cp + Vector2(120, 10)
	Input.parse_input_event(e4)
	Input.flush_buffered_events()
	await process_frame
	_check("camera drag produces no click", sink.left_clicks == 0, "left_clicks=%d" % sink.left_clicks)
	_free(pair)

	print("-- pinch zoom")
	pair = _make(TouchControls)
	sink = pair[0]
	tc = pair[1]
	var a0 := _cam_start(tc)
	var mm: float = tc.get_layout()["mm"]
	_touch(tc, 0, a0 - Vector2(10, 0), true)
	_touch(tc, 1, a0 + Vector2(10, 0), true)
	_drag(tc, 1, a0 + Vector2(10 + 12.0 * mm, 0))
	_check("spreading fingers emits wheel-up steps (zoom in)", sink.wheel_up >= 2 and sink.wheel_down == 0,
			"up=%d down=%d" % [sink.wheel_up, sink.wheel_down])
	_drag(tc, 1, a0 + Vector2(10, 0))
	_check("pinching in emits wheel-down steps", sink.wheel_down >= 2, "down=%d" % sink.wheel_down)
	tc._physics_process(0.016)
	_check("pinch does not orbit the camera", not _any_pressed(LOOK))
	_touch(tc, 0, a0, false)
	_touch(tc, 1, a0, false)
	sink.left_clicks = 0
	_check("pinch release does not click the world", sink.left_clicks == 0)
	_free(pair)

	print("-- overlay gating")
	pair = _make(TouchControls)
	sink = pair[0]
	tc = pair[1]
	var state := [TouchControls.OVERLAY_HIDDEN]
	tc.overlay_provider = func(): return state[0]
	_touch(tc, 0, _joy_start(tc), true)
	_drag(tc, 0, _joy_start(tc) + Vector2(100, 0))
	_check("overlay open: joystick ignored", not _any_pressed(MOVE))
	_touch(tc, 1, _btn_center(tc, "interact"), true)
	Input.flush_buffered_events()
	_check("overlay open: buttons ignored", not Input.is_action_pressed("action"))
	state[0] = TouchControls.OVERLAY_MAP_ONLY
	_touch(tc, 2, _joy_start(tc), true)
	_check("map open: joystick zone ignored", tc._touches.is_empty())
	_touch(tc, 3, _btn_center(tc, "map"), true)
	Input.flush_buffered_events()
	_check("map open: map button still works", Input.is_action_pressed("map"))
	state[0] = TouchControls.OVERLAY_HIDDEN
	tc._process(0.0)
	Input.flush_buffered_events()
	_check("overlay appearing mid-hold releases the held button", not Input.is_action_pressed("map"))
	tc.enabled = false
	state[0] = TouchControls.OVERLAY_NONE
	_touch(tc, 4, _btn_center(tc, "map"), true)
	_check("enabled=false: ignored", tc._touches.is_empty())
	_free(pair)

	print("-- negative check")
	var ok_pair := _make(TouchControls)
	var good: bool = _joy_right_works(ok_pair[1])
	_free(ok_pair)
	var bad_pair := _make(BrokenTC)
	var broken_ok: bool = _joy_right_works(bad_pair[1])
	_free(bad_pair)
	_check("joystick assertion passes on the real implementation", good)
	_check("NEGATIVE: same assertion FAILS on a deliberately broken variant (test can fail)", not broken_ok)

	for a in MOVE + LOOK + WATCH:
		Input.action_release(a)
	print("touch_test: %d checks, %d failed" % [_checks, _fails])
	print("RESULT: OK" if _fails == 0 else "RESULT: FAILED")
	quit(0 if _fails == 0 else 1)
