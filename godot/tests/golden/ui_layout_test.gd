extends SceneTree
## Headless layout test of the character-creation screen (phone-first navigation redesign).
##   godot --headless --path <scratch copy of godot/> -s res://tests/golden/ui_layout_test.gd -- --backend=local
## For every step, at 1280x720, 1600x720 (20:9 under stretch=expand), 960x720 and 1280x720 with
## OS safe-area insets, it asserts (base units): every visible interactive control is >= 96x96,
## no two interactive rects overlap, nothing lies outside the viewport / safe area, Back/Continue
## rects never move when an option is selected or the carousel is swiped, and the header matches
## the step. It also drives the carousel by swipe, tap, chip and keyboard.
## Final stdout line: `RESULT: OK|FAILED`. Includes NEGATIVE controls: the same checkers run
## against deliberately broken layouts must report violations.

const _Races := preload("res://scripts/core/data/races_data.gd")
const MIN_TOUCH := 96.0
const SIZES := [Vector2i(1280, 720), Vector2i(1600, 720), Vector2i(960, 720)]
const SAFE := Vector4(40, 24, 40, 30)   # left, top, right, bottom inset used for the safe-area run
const STEPS := ["Era", "Race", "Evolutionary State", "Predator Role", "Abilities", "Name"]

var _fails := 0
var _checks := 0


func _check(label: String, cond: bool, detail: String = "") -> void:
	_checks += 1
	if cond:
		print("  ok   ", label)
	else:
		_fails += 1
		printerr("  FAIL ", label, "  ", detail)


func _initialize() -> void:
	_run()


func _frames(n := 3) -> void:
	for _i in n:
		await process_frame


# ─── layout checkers (also used by the negative controls) ───────────

func _is_interactive(c: Control) -> bool:
	return c is BaseButton or c is LineEdit or c is RaceCarousel


## Rect of `c` clipped by every clipping ancestor (ScrollContainer, clip_contents).
func _clipped_rect(c: Control) -> Rect2:
	var r := c.get_global_rect()
	var p := c.get_parent()
	while p != null:
		if p is Control and (p is ScrollContainer or (p as Control).clip_contents):
			r = r.intersection((p as Control).get_global_rect())
		p = p.get_parent()
	return r


func _collect(node: Node, out: Array) -> void:
	for ch in node.get_children():
		if ch is Control:
			var c := ch as Control
			if c.is_visible_in_tree() and _is_interactive(c) and c.size.x > 0.0 and c.size.y > 0.0:
				out.append(c)
		_collect(ch, out)


## Returns a list of human-readable violations (empty = layout is fine).
func layout_violations(root: Node, vp_rect: Rect2, inner: Rect2) -> Array:
	var bad: Array = []
	var items: Array = []
	_collect(root, items)
	for c: Control in items:
		var r := c.get_global_rect()
		if r.size.x < MIN_TOUCH - 0.5 or r.size.y < MIN_TOUCH - 0.5:
			bad.append("too small %s %s" % [c.name, r.size])
		var cr := _clipped_rect(c)
		if cr.size.x <= 0.0 or cr.size.y <= 0.0:
			continue
		if not inner.grow(0.5).encloses(cr):
			bad.append("outside safe area %s %s (inner %s)" % [c.name, cr, inner])
	for i in items.size():
		for j in range(i + 1, items.size()):
			var a: Control = items[i]
			var b: Control = items[j]
			if a.is_ancestor_of(b) or b.is_ancestor_of(a):
				continue
			var ia := _clipped_rect(a).intersection(_clipped_rect(b))
			if ia.size.x > 1.0 and ia.size.y > 1.0:
				bad.append("overlap %s / %s" % [a.name, b.name])
	# Non-interactive furniture (labels, panels) must also stay on screen unless it is clipped.
	_check_visible_inside(root, vp_rect, bad)
	return bad


func _check_visible_inside(node: Node, vp_rect: Rect2, bad: Array) -> void:
	for ch in node.get_children():
		if ch is Control:
			var c := ch as Control
			if not c.is_visible_in_tree():
				continue
			if c is RaceCarousel or c is ScrollContainer or c is SubViewportContainer:
				continue   # their content is clipped / lives in its own viewport
			if c.size.x > 0.0 and c.size.y > 0.0 and not vp_rect.grow(0.5).encloses(c.get_global_rect()):
				if not (c is Container) or c.get_child_count() == 0:
					bad.append("furniture off screen %s %s" % [c.name, c.get_global_rect()])
		if not (ch is RaceCarousel or ch is ScrollContainer):
			_check_visible_inside(ch, vp_rect, bad)


# ─── scene helpers ───────────────────────────────────────────────────

func _make_scene(size: Vector2i, safe := Vector4.ZERO) -> Array:
	var vp := SubViewport.new()
	vp.size = size
	vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(vp)
	var scene: Control = (load("res://scenes/Creation.tscn") as PackedScene).instantiate()
	vp.add_child(scene)
	await _frames(12)
	scene._setup_mock_catalog()
	scene.catalog["races"] = _Races.RACES.duplicate(true)
	scene.set_safe_margins(safe.x, safe.y, safe.z, safe.w)
	scene.current_step = 0
	scene._render_step()
	await _frames(4)
	return [vp, scene]


func _rects(scene) -> Array:
	return [scene.back_btn.get_global_rect(), scene.next_btn.get_global_rect()]


func _options(scene) -> Array:
	var out: Array = []
	_find_toggles(scene.race_list, out)
	return out


func _find_toggles(node: Node, out: Array) -> void:
	for ch in node.get_children():
		if ch is Button and (ch as Button).toggle_mode and ch.is_visible_in_tree():
			out.append(ch)
		_find_toggles(ch, out)


func _click(btn: BaseButton) -> void:
	if btn.toggle_mode:
		btn.set_pressed_no_signal(true)
	btn.pressed.emit()


func _fire(carousel: RaceCarousel, ev: InputEvent) -> void:
	carousel._gui_input(ev)


func _mouse(pos: Vector2, pressed: bool) -> InputEventMouseButton:
	var e := InputEventMouseButton.new()
	e.button_index = MOUSE_BUTTON_LEFT
	e.pressed = pressed
	e.position = pos
	return e


func _motion(pos: Vector2) -> InputEventMouseMotion:
	var e := InputEventMouseMotion.new()
	e.position = pos
	e.button_mask = MOUSE_BUTTON_MASK_LEFT
	return e


func _swipe(carousel: RaceCarousel, dx: float) -> void:
	var y := carousel.size.y * 0.5
	var x0 := carousel.size.x * 0.5 - dx * 0.5
	_fire(carousel, _mouse(Vector2(x0, y), true))
	for k in 1:
		pass
	var steps := 8
	for s in range(1, steps + 1):
		_fire(carousel, _motion(Vector2(x0 + dx * float(s) / float(steps), y)))
		await create_timer(0.016).timeout
	_fire(carousel, _mouse(Vector2(x0 + dx, y), false))


func _key(code: Key) -> InputEventKey:
	var e := InputEventKey.new()
	e.keycode = code
	e.physical_keycode = code
	e.pressed = true
	return e


func _same_rects(a: Array, b: Array) -> bool:
	return a[0].is_equal_approx(b[0]) and a[1].is_equal_approx(b[1])


# ─── main ────────────────────────────────────────────────────────────

func _run() -> void:
	await _negative_controls()

	var configs: Array = []
	for s in SIZES:
		configs.append([s, Vector4.ZERO])
	configs.append([Vector2i(1280, 720), SAFE])
	for cfg in configs:
		var size: Vector2i = cfg[0]
		var safe: Vector4 = cfg[1]
		var tag := "%dx%d%s" % [size.x, size.y, " safe" if safe != Vector4.ZERO else ""]
		print("== ", tag)
		var made: Array = await _make_scene(size, safe)
		var vp: SubViewport = made[0]
		var scene = made[1]
		var vp_rect := Rect2(Vector2.ZERO, Vector2(size))
		var inner := Rect2(Vector2(safe.x, safe.y), Vector2(size) - Vector2(safe.x + safe.z, safe.y + safe.w))
		await _walk(scene, tag, vp_rect, inner)
		vp.queue_free()
		await _frames(2)

	print("checks=%d failed=%d" % [_checks, _fails])
	if _fails == 0:
		print("RESULT: OK")
	else:
		print("RESULT: FAILED")
	quit(0 if _fails == 0 else 1)


func _step_checks(scene, tag: String, vp_rect: Rect2, inner: Rect2) -> void:
	var step: int = scene.current_step
	var lab := "%s step %d (%s)" % [tag, step, STEPS[step]]
	_check("%s header matches" % lab, scene.title_label.text == STEPS[step], scene.title_label.text)
	_check("%s no stale ancestry header" % lab, step == 1 or scene.title_label.text != "Choose Your Ancestry:")
	var bad := layout_violations(scene, vp_rect, inner)
	_check("%s layout (%d violations)" % [lab, bad.size()], bad.is_empty(), str(bad.slice(0, 4)))
	var back_r: Rect2 = scene.back_btn.get_global_rect()
	var next_r: Rect2 = scene.next_btn.get_global_rect()
	_check("%s footer >= 96 and pinned to bottom" % lab,
		back_r.size.y >= MIN_TOUCH and next_r.size.y >= MIN_TOUCH and back_r.size.x >= MIN_TOUCH
		and next_r.size.x >= MIN_TOUCH and absf(next_r.end.y - inner.end.y) <= 16.0 + 0.5,
		"%s %s" % [back_r, next_r])


func _walk(scene, tag: String, vp_rect: Rect2, inner: Rect2) -> void:
	# Step 0: Era
	await _step_checks(scene, tag, vp_rect, inner)
	_check("%s step0 Back is Menu" % tag, scene.back_btn.text == "Menu")
	var before := _rects(scene)
	for opt in _options(scene):
		_click(opt)
		await _frames(2)
		_check("%s era option keeps footer still" % tag, _same_rects(before, _rects(scene)))
	_check("%s era Continue enabled" % tag, not scene.next_btn.disabled)
	await _step_checks(scene, tag, vp_rect, inner)

	# Step 1: Race carousel
	scene._on_next_btn_pressed()
	await _frames(4)
	await _step_checks(scene, tag, vp_rect, inner)
	var car: RaceCarousel = scene.carousel
	_check("%s carousel holds 35 races" % tag, car.ids.size() == 35, str(car.ids.size()))
	_check("%s Back reads Back" % tag, scene.back_btn.text == "Back")
	var groups := []
	for id in car.ids:
		var g: String = scene.catalog["races"][id]["group"]
		if groups.is_empty() or groups[-1] != g:
			groups.append(g)
	_check("%s ordered by group" % tag, groups == ["Cosmic", "Primal", "Eldritch", "Mechanical", "Humanoid"], str(groups))
	var rects0 := _rects(scene)
	var race0 = scene.selection["race"]
	var idx0: int = car.index
	_check("%s race pre-selected = first" % tag, race0 == car.ids[0] and idx0 == 0)
	await _swipe(car, -420.0)
	await _frames(2)
	car.settle()
	await _frames(2)
	_check("%s swipe left advances" % tag, car.index > idx0, "index=%d" % car.index)
	_check("%s selection follows swipe" % tag, scene.selection["race"] == car.ids[car.index] and scene.selection["race"] != race0)
	_check("%s footer still after swipe" % tag, _same_rects(rects0, _rects(scene)))
	var idx1: int = car.index
	await _swipe(car, -420.0)
	await _swipe(car, -420.0)
	car.settle()
	await _frames(2)
	_check("%s N swipes move further" % tag, car.index > idx1, "index=%d" % car.index)
	await _swipe(car, 420.0)
	car.settle()
	await _frames(2)
	_check("%s swipe right goes back" % tag, car.index < idx1 + 3 + 40)
	# keyboard
	var k0: int = car.index
	_fire(car, _key(KEY_RIGHT))
	car.settle()
	_check("%s keyboard right" % tag, car.index == k0 + 1 and scene.selection["race"] == car.ids[car.index])
	_fire(car, _key(KEY_LEFT))
	car.settle()
	_check("%s keyboard left" % tag, car.index == k0)
	# tap a peeking card
	var peek_i := -1
	for i in car._cards.size():
		var c: TextureRect = car._cards[i]
		if i == k0 + 1 and c.visible:
			peek_i = i
	if peek_i >= 0:
		var pc: TextureRect = car._cards[peek_i]
		var at := pc.position + pc.size * 0.5
		_fire(car, _mouse(at, true))
		_fire(car, _mouse(at, false))
		car.settle()
		await _frames(2)
		_check("%s tap on peeking card selects it" % tag, car.index == peek_i and scene.selection["race"] == car.ids[peek_i], "idx=%d" % car.index)
	else:
		_check("%s peeking neighbour visible" % tag, false)
	# group chips
	var primal_btn: Button = scene._chips["Primal"]
	primal_btn.pressed.emit()
	car.settle()
	await _frames(2)
	var first_primal := -1
	for i in car.ids.size():
		if scene.catalog["races"][car.ids[i]]["group"] == "Primal":
			first_primal = i
			break
	_check("%s chip jumps to first Primal" % tag, car.index == first_primal, "idx=%d want=%d" % [car.index, first_primal])
	_check("%s chip highlights group" % tag, primal_btn.button_pressed and not (scene._chips["Cosmic"] as Button).button_pressed)
	_check("%s indicator text" % tag, scene.index_label.text.begins_with("%d / 35" % (first_primal + 1)), scene.index_label.text)
	_check("%s footer still after chip" % tag, _same_rects(rects0, _rects(scene)))
	_check("%s race Continue enabled" % tag, not scene.next_btn.disabled)
	await _step_checks(scene, tag, vp_rect, inner)

	# Steps 2 / 3: state and role cards
	for st in [2, 3]:
		scene._on_next_btn_pressed()
		await _frames(4)
		await _step_checks(scene, tag, vp_rect, inner)
		_check("%s step%d Continue disabled until chosen" % [tag, st], scene.next_btn.disabled)
		var r_before := _rects(scene)
		var opts := _options(scene)
		_check("%s step%d has cards" % [tag, st], opts.size() >= 2 and opts.size() <= 4, str(opts.size()))
		for opt in opts:
			_click(opt)
			await _frames(2)
			_check("%s step%d option keeps footer still" % [tag, st], _same_rects(r_before, _rects(scene)))
		_check("%s step%d Continue enabled" % [tag, st], not scene.next_btn.disabled)

	# Step 4: abilities
	scene._on_next_btn_pressed()
	await _frames(4)
	await _step_checks(scene, tag, vp_rect, inner)
	var ab_before := _rects(scene)
	_check("%s abilities Continue disabled" % tag, scene.next_btn.disabled)
	for n in 6:
		# The first enabled pool button assigns to the focused ability.
		var pool: Button = null
		var pool_row := _find_pool(scene.race_list)
		for b in pool_row.get_children():
			if not (b as Button).disabled:
				pool = b
				break
		_check("%s abilities pool button %d available" % [tag, n], pool != null)
		if pool == null:
			break
		pool.pressed.emit()
		await _frames(2)
		_check("%s abilities footer still (%d)" % [tag, n], _same_rects(ab_before, _rects(scene)))
	_check("%s all abilities assigned" % tag, scene._pool_remaining.is_empty() and not scene.next_btn.disabled)
	await _step_checks(scene, tag, vp_rect, inner)
	var sel_ab: Dictionary = scene.selection["abilities"]
	var uniq := {}
	for k in sel_ab:
		uniq[sel_ab[k]] = true
	_check("%s abilities hold 6 distinct standard-array values" % tag, uniq.size() == 6)

	# Step 5: name
	scene._on_next_btn_pressed()
	await _frames(4)
	await _step_checks(scene, tag, vp_rect, inner)
	var name_rects := _rects(scene)
	_check("%s name Continue disabled until typed" % tag, scene.next_btn.disabled)
	var le: LineEdit = _find_line_edit(scene.race_list)
	_check("%s name LineEdit >= 96 high" % tag, le != null and le.size.y >= MIN_TOUCH)
	le.text = "Rook"
	le.text_changed.emit("Rook")
	await _frames(2)
	_check("%s name enables Continue" % tag, not scene.next_btn.disabled and scene.selection["name"] == "Rook")
	_check("%s name keeps footer still" % tag, _same_rects(name_rects, _rects(scene)))

	# Back walks one step at a time.
	for want in [4, 3, 2, 1, 0]:
		scene._on_back_btn_pressed()
		await _frames(3)
		_check("%s Back goes to step %d" % [tag, want], scene.current_step == want, str(scene.current_step))
	# Selections survive the round trip (race kept).
	_check("%s selection kept after Back" % tag, scene.selection["race"] != null and scene.selection["name"] == "Rook")


func _find_pool(node: Node) -> Node:
	for ch in node.get_children():
		if ch is HBoxContainer and ch.get_child_count() == 6 and ch.get_child(0) is Button \
				and (ch.get_child(0) as Button).text.is_valid_int():
			return ch
		var r := _find_pool(ch)
		if r != null:
			return r
	return null


func _find_line_edit(node: Node) -> LineEdit:
	for ch in node.get_children():
		if ch is LineEdit:
			return ch
		var r := _find_line_edit(ch)
		if r != null:
			return r
	return null


# ─── negative controls ───────────────────────────────────────────────

func _negative_controls() -> void:
	print("== negative controls")
	var host := Control.new()
	host.size = Vector2(1280, 720)
	root.add_child(host)
	var small := Button.new()
	small.name = "TinyBtn"
	small.position = Vector2(20, 20)
	small.size = Vector2(60, 40)
	small.custom_minimum_size = Vector2(60, 40)
	host.add_child(small)
	var a := Button.new()
	a.name = "OverlapA"
	a.custom_minimum_size = Vector2(200, 100)
	a.position = Vector2(300, 300)
	a.size = Vector2(200, 100)
	host.add_child(a)
	var b := Button.new()
	b.name = "OverlapB"
	b.custom_minimum_size = Vector2(200, 100)
	b.position = Vector2(400, 320)
	b.size = Vector2(200, 100)
	host.add_child(b)
	var off := Button.new()
	off.name = "OffScreen"
	off.custom_minimum_size = Vector2(200, 100)
	off.position = Vector2(1200, 650)
	off.size = Vector2(200, 100)
	host.add_child(off)
	await _frames(2)
	var bad := layout_violations(host, Rect2(0, 0, 1280, 720), Rect2(0, 0, 1280, 720))
	var joined := "\n".join(bad)
	_check("NEG tiny button is detected", joined.contains("too small TinyBtn"), joined)
	_check("NEG overlap is detected", joined.contains("overlap OverlapA / OverlapB"), joined)
	_check("NEG off-screen is detected", joined.contains("outside safe area OffScreen"), joined)
	var clean := Control.new()
	clean.size = Vector2(1280, 720)
	root.add_child(clean)
	var ok := Button.new()
	ok.name = "Fine"
	ok.custom_minimum_size = Vector2(200, 100)
	ok.position = Vector2(100, 100)
	ok.size = Vector2(200, 100)
	clean.add_child(ok)
	await _frames(2)
	_check("NEG control passes a clean layout", layout_violations(clean, Rect2(0, 0, 1280, 720), Rect2(0, 0, 1280, 720)).is_empty())
	# The "footer did not move" comparison must notice a moved button.
	var moved := [Rect2(0, 600, 240, 96), Rect2(900, 600, 320, 96)]
	var moved2 := [Rect2(0, 600, 240, 96), Rect2(900, 668, 320, 96)]
	_check("NEG moved Continue is detected", not _same_rects(moved, moved2))
	host.queue_free()
	clean.queue_free()
