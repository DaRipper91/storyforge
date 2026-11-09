class_name RaceCarousel
extends Control
## Horizontally swipeable carousel of cards. The centre slot is a caller-supplied live card
## (set_center), neighbours show dimmed card art (res://assets/characters/<id>.jpg) and peek in
## from the sides. Mouse/touch drag with inertia + snap, wheel, ui_left/ui_right, tap a peeking
## card to select it. Mouse events only: Android emulates them from touch.
## Emits index_changed(i) whenever the centred item changes (live, also while dragging).

signal index_changed(index: int)

const ART_PATH := "res://assets/characters/%s.jpg"
const ART_ASPECT := 800.0 / 1120.0
const DRAG_THRESHOLD := 18.0
const PEEK_GAP := 16.0
const KEEP_LOADED := 3.5   # cards within this distance keep their texture

var ids: Array = []
var index := 0              # centred item (round(pos))
var pos := 0.0              # fractional position while dragging / animating
var _target := 0.0

var _center: Control = null
var _cards: Array = []      # TextureRect per id
var _pressed := false
var _dragging := false
var _press_x := 0.0
var _press_pos := 0.0
var _last_x := 0.0
var _last_t := 0
var _vel := 0.0             # items / second


func _init() -> void:
	clip_contents = true
	focus_mode = Control.FOCUS_ALL
	mouse_filter = Control.MOUSE_FILTER_STOP


## Takes ownership of `card` as the live centre card.
func set_center(card: Control) -> void:
	_center = card
	card.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(card)
	_layout()


func set_items(new_ids: Array, start_index := 0) -> void:
	for c in _cards:
		c.queue_free()
	_cards.clear()
	ids = new_ids.duplicate()
	for id in ids:
		var tr := TextureRect.new()
		tr.name = "Card_%s" % id
		tr.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		tr.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
		tr.mouse_filter = Control.MOUSE_FILTER_IGNORE
		tr.clip_contents = true
		add_child(tr)
		_cards.append(tr)
	if _center:
		move_child(_center, get_child_count() - 1)   # centre card draws above the peeks
	index = clampi(start_index, 0, maxi(ids.size() - 1, 0))
	pos = float(index)
	_target = pos
	_layout()


func select_index(i: int, animate := true) -> void:
	if ids.is_empty():
		return
	_target = float(clampi(i, 0, ids.size() - 1))
	if not animate:
		settle()


func step_by(n: int) -> void:
	select_index(roundi(_target) + n)


## Jump straight to the target (used by tests and non-animated selection).
func settle() -> void:
	pos = _target
	_update_index()
	_layout()


func is_moving() -> bool:
	return _dragging or absf(pos - _target) > 0.002


# ─── geometry ──────────────────────────────────────────────────────

func center_width() -> float:
	return clampf(size.x * 0.56, minf(480.0, size.x), 760.0)


func peek_size() -> Vector2:
	var h := size.y * 0.86
	return Vector2(h * ART_ASPECT, h)


func _offset(d: float) -> float:
	var cw := center_width()
	var pw := peek_size().x
	var s1 := cw * 0.5 + PEEK_GAP + pw * 0.5
	if absf(d) <= 1.0:
		return d * s1
	return signf(d) * (s1 + (absf(d) - 1.0) * (pw + PEEK_GAP))


func _layout() -> void:
	if size.x <= 0.0 or size.y <= 0.0:
		return
	var ps := peek_size()
	var cw := center_width()
	if _center:
		var d := float(index) - pos
		_center.size = Vector2(cw, size.y)
		_center.position = Vector2(size.x * 0.5 + _offset(d) - cw * 0.5, 0.0)
	for i in _cards.size():
		var card: TextureRect = _cards[i]
		var d2 := float(i) - pos
		var ad := absf(d2)
		var onscreen := ad < 6.0 and i != index
		if onscreen:
			var x := size.x * 0.5 + _offset(d2) - ps.x * 0.5
			onscreen = x < size.x and x + ps.x > 0.0
			card.size = ps
			card.position = Vector2(x, (size.y - ps.y) * 0.5)
		card.visible = onscreen
		card.modulate = Color(1, 1, 1, 0.55 if ad < 1.5 else 0.32)
		if ad <= KEEP_LOADED:
			if card.texture == null:
				var p: String = ART_PATH % ids[i]
				if ResourceLoader.exists(p):
					card.texture = load(p) as Texture2D
		elif card.texture != null:
			card.texture = null


func _update_index() -> void:
	if ids.is_empty():
		return
	var ni := clampi(roundi(pos), 0, ids.size() - 1)
	if ni != index:
		index = ni
		index_changed.emit(index)


func _notification(what: int) -> void:
	if what == NOTIFICATION_RESIZED:
		_layout()


func _process(delta: float) -> void:
	if _dragging or ids.is_empty():
		return
	if absf(pos - _target) > 0.0005:
		pos = lerpf(pos, _target, 1.0 - exp(-14.0 * delta))
		if absf(pos - _target) < 0.002:
			pos = _target
		_update_index()
		_layout()


# ─── input ─────────────────────────────────────────────────────────

func _gui_input(event: InputEvent) -> void:
	if ids.is_empty():
		return
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_LEFT:
			if mb.pressed:
				_pressed = true
				_dragging = false
				_press_x = mb.position.x
				_press_pos = pos
				_last_x = mb.position.x
				_last_t = Time.get_ticks_msec()
				_vel = 0.0
				grab_focus()
			elif _pressed:
				_pressed = false
				_release(mb.position)
			accept_event()
		elif mb.pressed and mb.button_index == MOUSE_BUTTON_WHEEL_UP:
			step_by(-1)
			accept_event()
		elif mb.pressed and mb.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			step_by(1)
			accept_event()
	elif event is InputEventMouseMotion and _pressed:
		var mm := event as InputEventMouseMotion
		var dx := mm.position.x - _press_x
		if not _dragging and absf(dx) > DRAG_THRESHOLD:
			_dragging = true
		if _dragging:
			var s1 := _offset(1.0)
			var now := Time.get_ticks_msec()
			var dt := maxf(float(now - _last_t) / 1000.0, 0.001)
			var np := clampf(_press_pos - dx / maxf(s1, 1.0), -0.35, float(ids.size() - 1) + 0.35)
			var v := (np - pos) / dt
			_vel = lerpf(_vel, v, 0.5)
			pos = np
			_last_t = now
			_last_x = mm.position.x
			_update_index()
			_layout()
		accept_event()
	elif event.is_action_pressed("ui_left"):
		step_by(-1)
		accept_event()
	elif event.is_action_pressed("ui_right"):
		step_by(1)
		accept_event()


func _release(at: Vector2) -> void:
	if _dragging:
		_dragging = false
		# Inertia: project the release velocity a little ahead, then snap to an item.
		_target = clampf(roundf(pos + clampf(_vel * 0.16, -3.0, 3.0)), 0.0, float(ids.size() - 1))
		return
	# Tap: a peeking card selects itself.
	for i in _cards.size():
		var card: TextureRect = _cards[i]
		if card.visible and i != index and Rect2(card.position, card.size).has_point(at):
			_target = float(i)
			return
	_target = float(index)
