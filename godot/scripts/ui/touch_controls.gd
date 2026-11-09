class_name TouchControls
extends CanvasLayer
## On-screen touch controls for phones (offline Android build).
##
## Left zone  : floating virtual joystick -> move_left/right/up/down (same actions as WASD / left stick).
## Right zone : one-finger drag orbits the camera (look_* actions, same effect as the right stick),
##              two-finger pinch zooms (synthetic mouse-wheel steps, the existing zoom hook in Tabletop).
## Buttons    : action (interact), cycle_prev, cycle_next, map, reset_cam, freeform.
##
## Whole UI is built in code, drawn with _draw(); no binary assets.
##
## Mouse-from-touch (Godot's `emulate_mouse_from_touch`, default true): the engine turns the first
## finger into InputEventMouse* events (device == InputEvent.DEVICE_ID_EMULATION) in addition to the
## InputEventScreenTouch/Drag. Viewport order is: every node's _input() (children before parents),
## then GUI Controls, then _unhandled_input. Tabletop._input() reads mouse clicks, so a Control with
## mouse_filter = STOP alone would be too late. This node therefore (a) consumes the touches it owns
## with set_input_as_handled(), (b) consumes emulated mouse events that start inside any of its
## regions, and (c) also keeps a STOP Control under every region as a second line of defence for the
## GUI phase. A short, small tap in a joystick/camera zone is re-played as a normal left click
## (push_input, device 0) so selecting tokens and tapping UI under the zones still works.
## While a dialog/shop/freeform box/combat overlay is open (overlay_provider) the controls step aside.

const GOLD := Color("#dca331")
const HIGHLIGHT := Color("#ffe699")
const DARK := Color("#3a2e28")
const DARKER := Color("#0f0c0a")

# ─── Sizing (physical units, converted with the screen DPI) ─────────
const MIN_BUTTON_MM := 9.0          # hard floor for every tappable button (about 48 dp)
const BUTTON_MM := 11.0
const BIG_BUTTON_MM := 15.0
const GAP_MM := 3.0
const JOY_RADIUS_MM := 10.0
const TAP_SLOP_MM := 2.5
const PINCH_STEP_MM := 5.0
const MIN_BUTTON_PX := 48.0         # floor in viewport pixels (desktop --touch with a low reported DPI)
const FALLBACK_DPI := 420.0         # typical target phone; used when the OS reports nothing usable

# ─── Tuning ─────────────────────────────────────────────────────────
const OPACITY := 0.55
const JOY_DEADZONE := 0.18          # fraction of the radius; output is re-mapped so it leaves 0 smoothly
const JOY_ZONE_FRAC := 0.40         # joystick zone = left 40 % of the safe area
const TAP_MAX_MS := 350
const BUTTON_MIN_HOLD_MS := 60      # keeps `is_action_just_pressed` pollers (_process) from missing a quick tap
# Camera drag -> degrees. Tabletop mouse orbit uses 0.25 / 0.2 deg per px.
const CAM_YAW_DEG_PER_PX := 0.30
const CAM_PITCH_DEG_PER_PX := 0.22
# Tabletop._physics_process applies look_vec * these many degrees per physics frame (right stick).
const LOOK_YAW_DEG_PER_FRAME := 2.5
const LOOK_PITCH_DEG_PER_FRAME := 2.0
const LOOK_MIN_LEN := 0.06          # Tabletop ignores look vectors <= 0.05; keep accumulating below this
const CAM_BACKLOG_PX := 400.0

const OVERLAY_NONE := 0
const OVERLAY_MAP_ONLY := 1         # world map open: only the map button stays (to close it)
const OVERLAY_HIDDEN := 2           # dialog / shop / freeform / combat overlay: controls step aside

const MOVE_ACTIONS := ["move_left", "move_right", "move_up", "move_down"]
const LOOK_ACTIONS := ["look_left", "look_right", "look_up", "look_down"]
## name -> [action, label, big]
const BUTTONS := {
	"interact": ["action", "USE", true],
	"prev": ["cycle_prev", "<", false],
	"next": ["cycle_next", ">", false],
	"map": ["map", "MAP", false],
	"reset": ["reset_cam", "CAM", false],
	"say": ["freeform", "SAY", false],
}

## Instance toggle (tests / settings). should_show() decides whether Tabletop creates the node at all.
var enabled: bool = true
## Callable() -> int (OVERLAY_*). Optional.
var overlay_provider: Callable = Callable()

var _vp_override: Vector2 = Vector2.ZERO
var _ppm_override: float = 0.0
var _safe_override: Rect2 = Rect2()
var _layout: Dictionary = {}
var _regions: Array = []                 # [{role, name, rect}]
var _host: Control = null
var _region_ctrls: Array = []

var _touches: Dictionary = {}            # touch index -> {role, name, start, last, t0, moved, pinched}
var _joy_index: int = -1
var _joy_origin: Vector2 = Vector2.ZERO
var _joy_pos: Vector2 = Vector2.ZERO
var _cam_accum: Vector2 = Vector2.ZERO
var _pinch_last: float = 0.0
var _pinch_acc: float = 0.0
var _held: Dictionary = {}               # analog action -> strength currently pressed
var _buttons_down: Dictionary = {}       # button name -> true while its action is pressed
var _release_due: Dictionary = {}        # button name -> tick (ms) after which the action is released
var _emu_swallow: bool = false
var _synth: bool = false


# ─── Visibility rule ────────────────────────────────────────────────

## Pure form of the rule, for tests.
static func should_show_for(android: bool, ios: bool, user_args: PackedStringArray, env_value: String) -> bool:
	if android or ios:
		return true
	if "--touch" in user_args:
		return true
	return env_value == "1"


static func should_show() -> bool:
	return should_show_for(OS.has_feature("android"), OS.has_feature("ios"),
			OS.get_cmdline_user_args(), OS.get_environment("STORYFORGE_TOUCH"))


# ─── Pure helpers (static so tests can call them) ───────────────────

static func joy_strength(deflection: float) -> float:
	## deflection = distance / radius (0..inf) -> 0..1, with dead zone re-mapped.
	return clampf((deflection - JOY_DEADZONE) / (1.0 - JOY_DEADZONE), 0.0, 1.0)


## All geometry in viewport pixels. `px_per_mm` is viewport px per physical millimetre.
static func compute_layout(vp: Vector2, px_per_mm: float, safe: Rect2) -> Dictionary:
	var mm := maxf(px_per_mm, 0.1)
	var btn := maxf(maxf(BUTTON_MM * mm, MIN_BUTTON_MM * mm), MIN_BUTTON_PX)
	var big := maxf(BIG_BUTTON_MM * mm, btn * 1.35)
	var gap := maxf(GAP_MM * mm, 8.0)
	var full := Rect2(Vector2.ZERO, vp)
	var s := safe.intersection(full) if safe.has_area() else full
	s = s.grow(-gap)
	var top := s.position.y
	var top_h := top + btn + gap
	var rects := {}
	rects["prev"] = Rect2(s.position.x, top, btn, btn)
	rects["next"] = Rect2(s.position.x + btn + gap, top, btn, btn)
	rects["say"] = Rect2(s.end.x - btn, top, btn, btn)
	rects["reset"] = Rect2(s.end.x - 2.0 * btn - gap, top, btn, btn)
	rects["map"] = Rect2(s.end.x - 3.0 * btn - 2.0 * gap, top, btn, btn)
	rects["interact"] = Rect2(s.end.x - big, s.end.y - big, big, big)
	var joy := Rect2(s.position.x, top_h, s.size.x * JOY_ZONE_FRAC, s.end.y - top_h)
	var cam_a := Rect2(joy.end.x, top_h, s.end.x - big - gap - joy.end.x, s.end.y - top_h)
	var cam_b := Rect2(s.end.x - big, top_h, big, s.end.y - big - gap - top_h)
	return {
		"btn": btn, "big": big, "gap": gap, "mm": mm, "safe": s,
		"rects": rects, "joy": joy, "cam_a": cam_a, "cam_b": cam_b,
		"joy_radius": minf(JOY_RADIUS_MM * mm, minf(joy.size.x, joy.size.y) * 0.5),
	}


## Viewport-space safe area from a screen-space one, undoing the stretch scale + letterbox offset.
static func map_safe_area(screen_safe: Rect2, window: Vector2, vp: Vector2) -> Rect2:
	if screen_safe.size.x <= 0.0 or screen_safe.size.y <= 0.0 or window.x <= 0.0 or window.y <= 0.0:
		return Rect2(Vector2.ZERO, vp)
	var scale := minf(window.x / vp.x, window.y / vp.y)
	var off := (window - vp * scale) * 0.5
	var r := Rect2((screen_safe.position - off) / scale, screen_safe.size / scale)
	return r.intersection(Rect2(Vector2.ZERO, vp))


# ─── Lifecycle ──────────────────────────────────────────────────────

func _ready() -> void:
	layer = 3
	process_mode = Node.PROCESS_MODE_ALWAYS
	_host = Control.new()
	_host.name = "TouchHost"
	_host.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_host.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_host.draw.connect(_draw_host)
	add_child(_host)
	visibility_changed.connect(_on_visibility_changed)
	var vp := get_viewport()
	if vp:
		vp.size_changed.connect(relayout)
	relayout()


func _exit_tree() -> void:
	release_all()


func _notification(what: int) -> void:
	match what:
		NOTIFICATION_APPLICATION_FOCUS_OUT, NOTIFICATION_WM_WINDOW_FOCUS_OUT, \
		NOTIFICATION_APPLICATION_PAUSED, NOTIFICATION_PREDELETE:
			release_all()


func _on_visibility_changed() -> void:
	if not visible:
		release_all()


## Test hook: pin viewport size, physical scale and safe area (viewport px) instead of querying the OS.
func configure(vp: Vector2, px_per_mm: float, safe: Rect2 = Rect2()) -> void:
	_vp_override = vp
	_ppm_override = px_per_mm
	_safe_override = safe
	relayout()


func relayout() -> void:
	var vp := _vp_override
	if vp == Vector2.ZERO:
		vp = get_viewport().get_visible_rect().size if is_inside_tree() else Vector2(1280, 720)
	var ppm := _ppm_override
	var safe := _safe_override
	if ppm <= 0.0 or not safe.has_area():
		var win := Vector2(DisplayServer.window_get_size())
		var scale := 1.0
		if win.x > 0.0 and win.y > 0.0:
			scale = minf(win.x / vp.x, win.y / vp.y)
		if ppm <= 0.0:
			var dpi := float(DisplayServer.screen_get_dpi())
			if dpi < 60.0 or dpi > 1000.0:
				dpi = FALLBACK_DPI
			ppm = dpi / 25.4 / maxf(scale, 0.01)
		if not safe.has_area():
			var sa := DisplayServer.get_display_safe_area()
			safe = map_safe_area(Rect2(sa), win, vp)
	_layout = compute_layout(vp, ppm, safe)
	_regions.clear()
	for n in BUTTONS:
		_regions.append({"role": "button", "name": n, "rect": _layout["rects"][n]})
	_regions.append({"role": "joy", "name": "joy", "rect": _layout["joy"]})
	_regions.append({"role": "cam", "name": "cam_a", "rect": _layout["cam_a"]})
	_regions.append({"role": "cam", "name": "cam_b", "rect": _layout["cam_b"]})
	_rebuild_region_controls()
	if _host:
		_host.queue_redraw()


func get_regions() -> Array:
	return _regions


func get_layout() -> Dictionary:
	return _layout


func _rebuild_region_controls() -> void:
	for c in _region_ctrls:
		if is_instance_valid(c):
			c.queue_free()
	_region_ctrls.clear()
	for r in _regions:
		var c := Control.new()
		c.name = "Region_" + String(r["name"])
		c.mouse_filter = Control.MOUSE_FILTER_STOP
		c.focus_mode = Control.FOCUS_NONE
		c.position = (r["rect"] as Rect2).position
		c.size = (r["rect"] as Rect2).size
		c.set_meta("region_name", r["name"])
		add_child(c)
		_region_ctrls.append(c)
	_sync_region_controls()


func _sync_region_controls() -> void:
	var state := _overlay_state()
	var on := enabled and visible and state != OVERLAY_HIDDEN
	for c in _region_ctrls:
		if not is_instance_valid(c):
			continue
		var nm := String(c.get_meta("region_name", ""))
		c.visible = on and (state == OVERLAY_NONE or nm == "map")


# ─── State ──────────────────────────────────────────────────────────

func _overlay_state() -> int:
	if overlay_provider.is_valid():
		return int(overlay_provider.call())
	return OVERLAY_NONE


func is_active() -> bool:
	return enabled and visible and _overlay_state() != OVERLAY_HIDDEN


func _visible_regions() -> Array:
	var state := _overlay_state()
	if not (enabled and visible) or state == OVERLAY_HIDDEN:
		return []
	if state == OVERLAY_MAP_ONLY:
		return _regions.filter(func(r): return r["name"] == "map")
	return _regions


func _hit_test(pos: Vector2) -> Dictionary:
	for r in _visible_regions():
		if (r["rect"] as Rect2).has_point(pos):
			return r
	return {}


func _handled() -> void:
	var vp := get_viewport()
	if vp:
		vp.set_input_as_handled()


# ─── Input ──────────────────────────────────────────────────────────

func _input(event: InputEvent) -> void:
	if event is InputEventScreenTouch:
		_on_touch(event)
	elif event is InputEventScreenDrag:
		_on_drag(event)
	elif event is InputEventMouse:
		_on_emulated_mouse(event)


func _on_touch(ev: InputEventScreenTouch) -> void:
	if ev.pressed and not ev.canceled:
		if _touches.has(ev.index):
			return
		var hit := _hit_test(ev.position)
		if hit.is_empty():
			return
		_begin(ev.index, hit, ev.position)
		_handled()
	elif _touches.has(ev.index):
		_end(ev.index, ev.canceled)
		_handled()


func _on_drag(ev: InputEventScreenDrag) -> void:
	if not _touches.has(ev.index):
		return
	var t: Dictionary = _touches[ev.index]
	if not is_active():
		return
	var prev: Vector2 = t["last"]
	t["last"] = ev.position
	if ev.position.distance_to(t["start"]) > TAP_SLOP_MM * float(_layout.get("mm", 8.0)):
		t["moved"] = true
	match t["role"]:
		"joy":
			_joy_pos = ev.position
			_apply_joystick()
		"cam":
			if _cam_touch_count() >= 2:
				_pinch_update()
			else:
				_cam_accum += ev.position - prev
				_cam_accum = _cam_accum.limit_length(CAM_BACKLOG_PX)
	_host.queue_redraw()
	_handled()


func _on_emulated_mouse(ev: InputEventMouse) -> void:
	if _synth or ev.device != InputEvent.DEVICE_ID_EMULATION:
		return
	if ev is InputEventMouseButton:
		if ev.pressed:
			if not _hit_test(ev.position).is_empty():
				_emu_swallow = true
				_handled()
		elif _emu_swallow:
			_emu_swallow = false
			_handled()
	elif _emu_swallow:
		_handled()


func _begin(index: int, hit: Dictionary, pos: Vector2) -> void:
	var t := {"role": hit["role"], "name": hit["name"], "start": pos, "last": pos,
			"t0": Time.get_ticks_msec(), "moved": false, "pinched": false}
	_touches[index] = t
	match hit["role"]:
		"button":
			_press_button(String(hit["name"]))
		"joy":
			if _joy_index != -1:
				# Only one joystick finger; the extra one is ignored but still consumed.
				t["role"] = "none"
				return
			var rad: float = _layout["joy_radius"]
			var zone: Rect2 = _layout["joy"]
			var lim := zone.grow(-rad)
			_joy_origin = pos if not lim.has_area() else Vector2(
					clampf(pos.x, lim.position.x, lim.end.x), clampf(pos.y, lim.position.y, lim.end.y))
			_joy_pos = pos
			_joy_index = index
			_apply_joystick()
		"cam":
			if _cam_touch_count() >= 2:
				_pinch_start()
	_host.queue_redraw()


func _end(index: int, canceled: bool) -> void:
	var t: Dictionary = _touches[index]
	_touches.erase(index)
	match t["role"]:
		"button":
			_release_button(String(t["name"]), canceled)
		"joy":
			if index == _joy_index:
				_joy_index = -1
				_apply_vector(MOVE_ACTIONS, Vector2.ZERO)
		"cam":
			if _cam_touch_count() < 2:
				_pinch_acc = 0.0
			if _cam_touch_count() == 0:
				_cam_accum = Vector2.ZERO
	if t["role"] in ["joy", "cam"] and not canceled and not t["moved"] and not t["pinched"] \
			and Time.get_ticks_msec() - int(t["t0"]) <= TAP_MAX_MS:
		_replay_click(t["start"])
	_host.queue_redraw()


# ─── Buttons ────────────────────────────────────────────────────────

func _press_button(name: String) -> void:
	if _buttons_down.has(name):
		return
	_buttons_down[name] = true
	_release_due.erase(name)
	_send_action(BUTTONS[name][0], true)


func _release_button(name: String, immediate: bool) -> void:
	if not _buttons_down.has(name):
		return
	_release_due[name] = 0 if immediate else Time.get_ticks_msec() + BUTTON_MIN_HOLD_MS
	if immediate:
		_flush_button_releases(true)


func _flush_button_releases(force: bool = false) -> void:
	var now := Time.get_ticks_msec()
	for name in _release_due.keys():
		if force or now >= int(_release_due[name]):
			_release_due.erase(name)
			_buttons_down.erase(name)
			_send_action(BUTTONS[name][0], false)
	if _host:
		_host.queue_redraw()


## Goes through the normal input pipeline so Tabletop._input() sees the press (it polls
## Input.is_action_just_pressed from inside _input) and so Input.is_action_* state is updated.
func _send_action(action: String, pressed: bool) -> void:
	var ev := InputEventAction.new()
	ev.action = action
	ev.pressed = pressed
	ev.strength = 1.0 if pressed else 0.0
	Input.parse_input_event(ev)


# ─── Joystick / analog ──────────────────────────────────────────────

func _apply_joystick() -> void:
	var rad: float = maxf(_layout["joy_radius"], 1.0)
	var d := _joy_pos - _joy_origin
	var s := joy_strength(d.length() / rad)
	_apply_vector(MOVE_ACTIONS, d.normalized() * s if s > 0.0 else Vector2.ZERO)


## `v` is the vector Input.get_vector() should return (screen axes: +y = down). Input.get_vector
## applies the actions' dead zone (length re-mapped from [dz,1] to [0,1]); pre-compensate so the
## consumer sees exactly `v`.
func _apply_vector(actions: Array, v: Vector2) -> void:
	var len := v.length()
	if len <= 0.0001:
		for a in actions:
			_set_analog(a, 0.0)
		return
	var dz := _deadzone(actions)
	var out := v / len * (dz + minf(len, 1.0) * (1.0 - dz))
	# actions = [left, right, up, down]
	_set_analog(actions[0], maxf(-out.x, 0.0))
	_set_analog(actions[1], maxf(out.x, 0.0))
	_set_analog(actions[2], maxf(-out.y, 0.0))
	_set_analog(actions[3], maxf(out.y, 0.0))


func _deadzone(actions: Array) -> float:
	var sum := 0.0
	for a in actions:
		sum += InputMap.action_get_deadzone(a) if InputMap.has_action(a) else 0.2
	return sum / float(actions.size())


func _set_analog(action: String, strength: float) -> void:
	if not InputMap.has_action(action):
		return
	if strength <= 0.0001:
		if _held.has(action):
			Input.action_release(action)
			_held.erase(action)
		return
	if _held.has(action) and absf(float(_held[action]) - strength) < 0.001:
		return
	Input.action_press(action, strength)
	_held[action] = strength


# ─── Camera ─────────────────────────────────────────────────────────

func _cam_touch_count() -> int:
	var n := 0
	for k in _touches:
		if _touches[k]["role"] == "cam":
			n += 1
	return n


func _cam_points() -> Array:
	var pts := []
	for k in _touches:
		if _touches[k]["role"] == "cam":
			pts.append(k)
	return pts


func _pinch_start() -> void:
	var pts := _cam_points()
	if pts.size() < 2:
		return
	_cam_accum = Vector2.ZERO
	_pinch_acc = 0.0
	_pinch_last = (_touches[pts[0]]["last"] as Vector2).distance_to(_touches[pts[1]]["last"])
	for k in pts:
		_touches[k]["pinched"] = true


func _pinch_update() -> void:
	var pts := _cam_points()
	if pts.size() < 2:
		return
	var a: Vector2 = _touches[pts[0]]["last"]
	var b: Vector2 = _touches[pts[1]]["last"]
	var dist := a.distance_to(b)
	_pinch_acc += dist - _pinch_last
	_pinch_last = dist
	var step := PINCH_STEP_MM * float(_layout.get("mm", 8.0))
	var centre := (a + b) * 0.5
	while absf(_pinch_acc) >= step:
		# Spreading fingers zooms in (wheel up), same as Tabletop's mouse wheel branch.
		_emit_wheel(MOUSE_BUTTON_WHEEL_UP if _pinch_acc > 0.0 else MOUSE_BUTTON_WHEEL_DOWN, centre)
		_pinch_acc -= step * signf(_pinch_acc)


func _emit_wheel(button: int, pos: Vector2) -> void:
	var ev := InputEventMouseButton.new()
	ev.button_index = button
	ev.pressed = true
	ev.position = pos
	ev.global_position = pos
	_push_local(ev)


func _push_local(ev: InputEvent) -> void:
	var vp := get_viewport()
	if vp == null:
		return
	_synth = true
	vp.push_input(ev, true)
	_synth = false


func _replay_click(pos: Vector2) -> void:
	var down := InputEventMouseButton.new()
	down.button_index = MOUSE_BUTTON_LEFT
	down.pressed = true
	down.position = pos
	down.global_position = pos
	down.button_mask = MOUSE_BUTTON_MASK_LEFT
	_push_local(down)
	var up := InputEventMouseButton.new()
	up.button_index = MOUSE_BUTTON_LEFT
	up.pressed = false
	up.position = pos
	up.global_position = pos
	_push_local(up)


func _physics_process(_delta: float) -> void:
	if not is_active():
		return
	if _cam_accum != Vector2.ZERO:
		var want := Vector2(_cam_accum.x * CAM_YAW_DEG_PER_PX / LOOK_YAW_DEG_PER_FRAME,
				_cam_accum.y * CAM_PITCH_DEG_PER_PX / LOOK_PITCH_DEG_PER_FRAME)
		if want.length() >= LOOK_MIN_LEN:
			var frac := 1.0
			if want.length() > 1.0:
				frac = 1.0 / want.length()
				want *= frac
			_cam_accum *= (1.0 - frac)
			if _cam_accum.length() < 0.01:
				_cam_accum = Vector2.ZERO
			_apply_vector(LOOK_ACTIONS, want)
			return
	_apply_vector(LOOK_ACTIONS, Vector2.ZERO)


func _process(_delta: float) -> void:
	_sync_region_controls()
	if not is_active():
		if not _touches.is_empty() or not _held.is_empty() or not _buttons_down.is_empty():
			release_all()
		return
	if _overlay_state() == OVERLAY_MAP_ONLY:
		for k in _touches.keys():
			if _touches[k]["name"] != "map":
				_end(k, true)
	_flush_button_releases()


## Releases every action this node pressed and forgets all touches. Safe to call any time.
func release_all() -> void:
	_touches.clear()
	_joy_index = -1
	_cam_accum = Vector2.ZERO
	_pinch_acc = 0.0
	_emu_swallow = false
	for a in _held.keys():
		Input.action_release(a)
	_held.clear()
	for name in _buttons_down.keys():
		_send_action(BUTTONS[name][0], false)
	_buttons_down.clear()
	_release_due.clear()
	if _host and is_instance_valid(_host):
		_host.queue_redraw()


# ─── Drawing ────────────────────────────────────────────────────────

func _draw_host() -> void:
	if not is_active():
		return
	var only_map := _overlay_state() == OVERLAY_MAP_ONLY
	var font := ThemeDB.fallback_font
	for n in BUTTONS:
		if only_map and n != "map":
			continue
		var r: Rect2 = _layout["rects"][n]
		var down := _buttons_down.has(n)
		var c := r.get_center()
		var rad := minf(r.size.x, r.size.y) * 0.5
		var fill := Color(GOLD, OPACITY * 0.8) if down else Color(DARKER, OPACITY)
		_host.draw_circle(c, rad, fill)
		_host.draw_arc(c, rad - 1.5, 0.0, TAU, 40, Color(HIGHLIGHT if down else GOLD, OPACITY + 0.2), 3.0, true)
		var fs := int(rad * 0.62)
		var txt: String = BUTTONS[n][1]
		var sz := font.get_string_size(txt, HORIZONTAL_ALIGNMENT_CENTER, -1, fs)
		_host.draw_string(font, c + Vector2(-sz.x * 0.5, sz.y * 0.3), txt,
				HORIZONTAL_ALIGNMENT_LEFT, -1, fs, Color(HIGHLIGHT, OPACITY + 0.3))
	if only_map:
		return
	var jr: float = _layout["joy_radius"]
	if _joy_index != -1:
		_host.draw_circle(_joy_origin, jr, Color(DARK, OPACITY * 0.7))
		_host.draw_arc(_joy_origin, jr, 0.0, TAU, 48, Color(GOLD, OPACITY + 0.15), 3.0, true)
		var knob := _joy_origin + (_joy_pos - _joy_origin).limit_length(jr)
		_host.draw_circle(knob, jr * 0.45, Color(HIGHLIGHT, OPACITY))
	else:
		var z: Rect2 = _layout["joy"]
		var idle := Vector2(z.position.x + jr * 1.6, z.end.y - jr * 1.6)
		_host.draw_arc(idle, jr, 0.0, TAU, 48, Color(GOLD, OPACITY * 0.4), 2.0, true)
