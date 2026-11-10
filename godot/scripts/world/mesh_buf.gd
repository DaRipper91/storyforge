class_name MeshBuf
extends RefCounted
## Tiny CPU mesh builder for the procedural world props: flat/smooth triangles with vertex colours,
## no UVs (the world shaders map textures in world space). Godot front faces are clockwise, so a
## triangle's outward normal is (c - a) x (b - a).

var verts := PackedVector3Array()
var norms := PackedVector3Array()
var cols := PackedColorArray()
var idx := PackedInt32Array()


func tri(a: Vector3, b: Vector3, c: Vector3, col: Color) -> void:
	var n := (c - a).cross(b - a).normalized()
	tri_n(a, b, c, n, n, n, col, col, col)


func tri_n(a: Vector3, b: Vector3, c: Vector3, na: Vector3, nb: Vector3, nc: Vector3,
		ca: Color, cb: Color, cc: Color) -> void:
	var base := verts.size()
	verts.append_array(PackedVector3Array([a, b, c]))
	norms.append_array(PackedVector3Array([na, nb, nc]))
	cols.append_array(PackedColorArray([ca, cb, cc]))
	idx.append_array(PackedInt32Array([base, base + 1, base + 2]))


## Quad given clockwise from the front: a, b, c, d.
func quad(a: Vector3, b: Vector3, c: Vector3, d: Vector3, col: Color) -> void:
	tri(a, b, c, col)
	tri(a, c, d, col)


func box(centre: Vector3, size: Vector3, col: Color, top_scale: float = 1.0, bottom: bool = true) -> void:
	var h := size * 0.5
	var t := Vector2(h.x, h.z) * top_scale
	var p000 := centre + Vector3(-h.x, -h.y, -h.z)
	var p100 := centre + Vector3(h.x, -h.y, -h.z)
	var p101 := centre + Vector3(h.x, -h.y, h.z)
	var p001 := centre + Vector3(-h.x, -h.y, h.z)
	var q000 := centre + Vector3(-t.x, h.y, -t.y)
	var q100 := centre + Vector3(t.x, h.y, -t.y)
	var q101 := centre + Vector3(t.x, h.y, t.y)
	var q001 := centre + Vector3(-t.x, h.y, t.y)
	quad(q000, q100, q101, q001, col)               # top
	quad(p001, p101, q101, q001, col * 0.0 + col)   # +z
	quad(p101, p100, q100, q101, col)               # +x
	quad(p100, p000, q000, q100, col)               # -z
	quad(p000, p001, q001, q000, col)               # -x
	if bottom:
		quad(p000, p100, p101, p001, col)


## Vertical cylinder / cone / frustum standing on `base`.
func cyl(base: Vector3, r0: float, r1: float, height: float, sides: int, col: Color,
		cap_top: bool = true, col_top: Color = Color(0, 0, 0, 0)) -> void:
	var ct := col if col_top.a == 0.0 else col_top
	var slope := (r0 - r1) / maxf(height, 0.0001)
	for i in sides:
		var a0 := TAU * float(i) / sides
		var a1 := TAU * float(i + 1) / sides
		var d0 := Vector3(cos(a0), 0, sin(a0))
		var d1 := Vector3(cos(a1), 0, sin(a1))
		var b0 := base + d0 * r0
		var b1 := base + d1 * r0
		var t0 := base + Vector3(0, height, 0) + d0 * r1
		var t1 := base + Vector3(0, height, 0) + d1 * r1
		var n0 := (d0 + Vector3(0, slope, 0)).normalized()
		var n1 := (d1 + Vector3(0, slope, 0)).normalized()
		# clockwise from outside: b1, b0, t0 then b1, t0, t1 (angle increases counter-clockwise from above)
		tri_n(b0, b1, t0, n0, n1, n0, col, col, ct)
		tri_n(b1, t1, t0, n1, n1, n0, col, ct, ct)
		if cap_top and r1 > 0.001:
			tri(base + Vector3(0, height, 0), t0, t1, ct)
		if r0 > 0.001:
			tri(base, b1, b0, col)


## Lumpy flat-shaded ellipsoid (tree crowns, bushes, haystacks, boulders).
func blob(centre: Vector3, radii: Vector3, rings: int, segs: int, col: Color, jitter: float,
		rng: RandomNumberGenerator, col_var: float = 0.12) -> void:
	var grid: Array = []
	for r in range(rings + 1):
		var row: Array = []
		var phi := PI * float(r) / rings
		for s in segs:
			var th := TAU * float(s) / segs
			var j := 1.0 + (rng.randf() - 0.5) * jitter
			if r == 0 or r == rings:
				j = 1.0
			var dir := Vector3(sin(phi) * cos(th), cos(phi), sin(phi) * sin(th))
			row.append(centre + dir * radii * j)
		grid.append(row)
	for r in rings:
		for s in segs:
			var s2 := (s + 1) % segs
			var a: Vector3 = grid[r][s]
			var b: Vector3 = grid[r][s2]
			var c: Vector3 = grid[r + 1][s2]
			var d: Vector3 = grid[r + 1][s]
			var shade := 1.0 + (rng.randf() - 0.5) * col_var + ((a.y - centre.y) / maxf(radii.y, 0.01)) * 0.12
			var cc := Color(col.r * shade, col.g * shade, col.b * shade, col.a)
			if r == 0:
				tri(a, c, d, cc)
			elif r == rings - 1:
				tri(a, b, d, cc)
			else:
				tri(a, b, c, cc)
				tri(a, c, d, cc)


## Gable roof over a rectangle (ridge along local X). Overhang extends all round.
func gable_roof(centre: Vector3, size: Vector3, overhang: float, col: Color, col_edge: Color) -> void:
	var hx := size.x * 0.5 + overhang
	var hz := size.z * 0.5 + overhang
	var y0 := centre.y
	var y1 := centre.y + size.y
	var rl := Vector3(centre.x - hx, y1, centre.z)
	var rr := Vector3(centre.x + hx, y1, centre.z)
	var fl := Vector3(centre.x - hx, y0, centre.z + hz)
	var fr := Vector3(centre.x + hx, y0, centre.z + hz)
	var bl := Vector3(centre.x - hx, y0, centre.z - hz)
	var br := Vector3(centre.x + hx, y0, centre.z - hz)
	quad(fl, rl, rr, fr, col)    # front slope (+z)
	quad(br, rr, rl, bl, col)    # back slope
	# thickness: undersides and gable ends
	quad(fl, fr, rr, rl, col_edge * 0.55)
	quad(br, bl, rl, rr, col_edge * 0.55)
	tri(fl, bl, rl, col_edge)    # -x gable
	tri(fr, rr, br, col_edge)    # +x gable


func to_mesh(into: ArrayMesh = null, material: Material = null) -> ArrayMesh:
	var m := into if into != null else ArrayMesh.new()
	if verts.is_empty():
		return m
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = verts
	arr[Mesh.ARRAY_NORMAL] = norms
	arr[Mesh.ARRAY_COLOR] = cols
	arr[Mesh.ARRAY_INDEX] = idx
	m.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	if material != null:
		m.surface_set_material(m.get_surface_count() - 1, material)
	return m


func triangle_count() -> int:
	return idx.size() / 3
