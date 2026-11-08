class_name CoreGrid
extends RefCounted
## Port of src/storyforge/core/grid.py. 2D grid math primitives.
##
## Models are plain JSON-compatible Dictionaries (same keys as pydantic
## model_dump(mode="json")): Room {id,width,height,cells[]}, Cell {terrain,
## occupant_id}, Coord {x,y}. Godot parses all JSON numbers as float, so every
## numeric read goes through int().
## Python exceptions are returned as CoreError dictionaries (see core_error.gd).

const FEET_PER_CELL := 5


## str(Coord) in pydantic v2 is "x=1 y=2"; rejection/error strings embed it.
static func coord_str(coord: Dictionary) -> String:
	return "x=%d y=%d" % [int(coord["x"]), int(coord["y"])]


# ─────────────────────── Cell accessors ───────────────────────

static func cell_index(room: Dictionary, coord: Dictionary) -> int:
	return int(coord["y"]) * int(room["width"]) + int(coord["x"])


## Returns the Cell Dictionary, or a CoreError("IndexError") when out of bounds.
static func get_cell(room: Dictionary, coord: Dictionary) -> Variant:
	if not in_bounds(room, coord):
		return CoreError.make("IndexError", "Coord %s out of bounds for room %s" % [coord_str(coord), str(room["id"])])
	return (room["cells"] as Array)[cell_index(room, coord)]


## In-place replacement. Python list assignment: negative indexes wrap, an
## index past the end raises IndexError (returned here as a CoreError).
## Returns null on success.
static func set_cell(room: Dictionary, coord: Dictionary, cell: Dictionary) -> Variant:
	var cells: Array = room["cells"]
	var idx := cell_index(room, coord)
	if idx >= cells.size() or idx < -cells.size():
		return CoreError.make("IndexError", "list assignment index out of range")
	if idx < 0:
		idx += cells.size()
	cells[idx] = cell
	return null


static func in_bounds(room: Dictionary, coord: Dictionary) -> bool:
	var x := int(coord["x"])
	var y := int(coord["y"])
	return 0 <= x and x < int(room["width"]) and 0 <= y and y < int(room["height"])


# ─────────────────────── Distance + traversal ───────────────────────

static func chebyshev_distance(a: Dictionary, b: Dictionary) -> int:
	return maxi(absi(int(a["x"]) - int(b["x"])), absi(int(a["y"]) - int(b["y"])))


static func feet_between(a: Dictionary, b: Dictionary) -> int:
	return chebyshev_distance(a, b) * FEET_PER_CELL


static func is_traversable(cell: Dictionary) -> bool:
	var terrain: String = str(cell.get("terrain", "floor"))
	if terrain == "wall" or terrain == "pillar" or terrain == "table":
		return false
	# Python: `occupant_id is not None` - an empty string still counts as occupied.
	if cell.get("occupant_id", null) != null:
		return false
	return true


static func movement_cost_feet(cell: Dictionary) -> int:
	if str(cell.get("terrain", "floor")) == "difficult":
		return FEET_PER_CELL * 2
	return FEET_PER_CELL


# ─────────────────────── Pathfinding (MVP: line check) ───────────────────────

## Bresenham-ish line from a to b inclusive; array of {x,y}.
static func line_coords(a: Dictionary, b: Dictionary) -> Array:
	var x0 := int(a["x"])
	var y0 := int(a["y"])
	var x1 := int(b["x"])
	var y1 := int(b["y"])
	var coords: Array = []
	var dx := absi(x1 - x0)
	var dy := -absi(y1 - y0)
	var sx := 1 if x0 < x1 else -1
	var sy := 1 if y0 < y1 else -1
	var err := dx + dy
	while true:
		coords.append({"x": x0, "y": y0})
		if x0 == x1 and y0 == y1:
			break
		var e2 := 2 * err
		if e2 >= dy:
			err += dy
			x0 += sx
		if e2 <= dx:
			err += dx
			y0 += sy
	return coords


## Python's all(generator) short-circuits: the first non-traversable cell ends
## the walk with False, but an out-of-bounds cell reached BEFORE that raises
## IndexError (returned as a CoreError). Order matters, so walk in sequence.
static func path_is_clear(room: Dictionary, start: Dictionary, end: Dictionary) -> Variant:
	var line := line_coords(start, end)
	for i in range(1, line.size()):
		var cell: Variant = get_cell(room, line[i])
		if CoreError.is_error(cell):
			return cell
		if not is_traversable(cell):
			return false
	return true
