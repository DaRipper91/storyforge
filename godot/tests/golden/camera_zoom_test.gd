extends SceneTree
## Regression test: Tabletop zoom did nothing.
##
## The Tabletop camera is orthographic. Wheel / pinch changed `_cam_distance`, which has no visible
## effect on an orthographic camera (only Camera3D.size does), and the size was a constant 20, so
## zoom never worked. `_update_camera()` now converts the zoom value into the camera's ortho size.
## This test drives the real input path (mouse-wheel events, which is what the touch layer's pinch
## sends) and measures the camera.
##
##   godot --headless --path godot -s res://tests/golden/camera_zoom_test.gd -- --backend=local --save-dir=<dir>
## Last line: RESULT: OK | RESULT: FAILED

var _checks := 0
var _failed := 0


func _initialize() -> void:
	_run()


func _ok(cond: bool, label: String) -> void:
	_checks += 1
	if cond:
		print("  ok   %s" % label)
	else:
		_failed += 1
		print("  FAIL %s" % label)


func _wheel(tabletop: Node, up: bool) -> void:
	var ev := InputEventMouseButton.new()
	ev.button_index = MOUSE_BUTTON_WHEEL_UP if up else MOUSE_BUTTON_WHEEL_DOWN
	ev.pressed = true
	ev.position = Vector2(640, 360)
	tabletop._input(ev)


func _run() -> void:
	await process_frame
	var tabletop := (load("res://scenes/Tabletop.tscn") as PackedScene).instantiate()
	root.add_child(tabletop)
	for _i in 12:
		await process_frame
	var cam: Camera3D = tabletop.camera

	print("-- camera facts")
	_ok(cam.projection == Camera3D.PROJECTION_ORTHOGONAL, "Tabletop camera is orthographic")
	var k: float = tabletop.CAM_SIZE_PER_DISTANCE
	_ok(is_equal_approx(cam.size, tabletop._cam_distance * k),
		"camera.size (%.2f) == zoom distance %.2f * %.4f" % [cam.size, tabletop._cam_distance, k])
	var default_size: float = tabletop.CAM_DISTANCE_DEFAULT * k
	_ok(default_size < 12.0, "default ortho size %.2f is closer than the old fixed 20" % default_size)

	print("-- wheel zoom changes the camera size")
	var s0 := cam.size
	_wheel(tabletop, true)
	var s1 := cam.size
	_wheel(tabletop, true)
	var s2 := cam.size
	_ok(s1 < s0 and s2 < s1, "zooming in shrinks the ortho size (%.2f > %.2f > %.2f)" % [s0, s1, s2])
	_wheel(tabletop, false)
	_wheel(tabletop, false)
	_wheel(tabletop, false)
	_ok(cam.size > s0, "zooming out grows it past the start (%.2f > %.2f)" % [cam.size, s0])

	print("-- clamped at both ends")
	for _i in 60:
		_wheel(tabletop, true)
	var smin := cam.size
	_ok(is_equal_approx(smin, tabletop.CAM_DISTANCE_MIN * k), "min ortho size %.2f" % smin)
	for _i in 60:
		_wheel(tabletop, false)
	var smax := cam.size
	_ok(is_equal_approx(smax, tabletop.CAM_DISTANCE_MAX * k), "max ortho size %.2f" % smax)
	_ok(smin < default_size and default_size < smax, "default lies between the limits")

	print("-- negative control: the old behaviour (distance changes, size does not) is detectable")
	cam.size = 20.0
	var before := cam.size
	tabletop._cam_distance = 9.0
	cam.projection = Camera3D.PROJECTION_PERSPECTIVE   # the conversion only applies to ortho
	tabletop._update_camera()
	_ok(cam.size == before, "with a non-orthographic camera size is left alone (control)")
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	tabletop._update_camera()
	_ok(not is_equal_approx(cam.size, before), "back in ortho the size follows the zoom again")

	print("camera_zoom_test: %d checks, %d failed" % [_checks, _failed])
	print("RESULT: OK" if _failed == 0 else "RESULT: FAILED")
	quit(0 if _failed == 0 else 1)
