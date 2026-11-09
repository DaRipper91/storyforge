class_name StepDots
extends Control
## Progress strip for a wizard: one dot per step (done = filled gold, current = big highlight
## ring, upcoming = muted outline). Purely visual, never interactive.

const COL_DONE := Color("#dca331")
const COL_CURRENT := Color("#ffe699")
const COL_TODO := Color("#8d7f6a")

var count := 6:
	set(v):
		count = maxi(v, 1)
		queue_redraw()
var current := 0:
	set(v):
		current = v
		queue_redraw()


func _init() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	custom_minimum_size = Vector2(240, 40)


func _draw() -> void:
	var n := count
	var step := size.x / float(n)
	var cy := size.y * 0.5
	var r := minf(step * 0.28, size.y * 0.3)
	for i in n:
		var c := Vector2(step * (i + 0.5), cy)
		if i < current:
			draw_circle(c, r, COL_DONE)
		elif i == current:
			draw_circle(c, r * 1.35, COL_CURRENT)
			draw_arc(c, r * 1.35 + 4.0, 0.0, TAU, 32, COL_DONE, 3.0, true)
		else:
			draw_arc(c, r, 0.0, TAU, 24, COL_TODO, 3.0, true)
