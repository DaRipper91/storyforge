extends SceneTree
## Regression test for the export-only bug: "Loaded 0 base items" in packaged builds.
##
## In an export Godot stores text resources as "<name>.tres.remap", so a loader that filters
## DirAccess names with ends_with(".tres") finds nothing. ResourceListing strips the suffix.
## This test cannot run an export, so it builds a directory whose FILE NAMES mimic one and lists
## it with the real DirAccess, then checks the real item folder and the InventorySystem autoload.
##
##   godot --headless --path godot -s res://tests/golden/resource_listing_test.gd
## Last line: RESULT: OK | RESULT: FAILED

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


func _naive_list(dir_path: String) -> PackedStringArray:
	# The OLD loader logic, kept here only to prove the test can fail.
	var out := PackedStringArray()
	var dir := DirAccess.open(dir_path)
	for f in dir.get_files():
		if f.ends_with(".tres") or f.ends_with(".res"):
			out.append(f)
	return out


func _write(path: String) -> void:
	var f := FileAccess.open(path, FileAccess.WRITE)
	f.store_string("x")
	f.close()


func _run() -> void:
	print("-- loadable_name mapping")
	var table := {
		"armor.tres": "armor.tres",
		"armor.tres.remap": "armor.tres",
		"affix.res.remap": "affix.res",
		"affix.res": "affix.res",
		"scene.tscn.remap": "scene.tscn",
		"scene.scn": "scene.scn",
		"UPPER.TRES": "UPPER.TRES",
		"icon.png.import": "",
		"model.glb.import": "",
		"I_Sword.png": "",
		"notes.md": "",
		"noextension": "",
		"": "",
	}
	for k in table:
		_ok(ResourceListing.loadable_name(k) == table[k],
			"loadable_name(\"%s\") == \"%s\"" % [k, table[k]])

	print("-- real DirAccess on an export-like directory")
	var base := "user://listing_test_%d/" % Time.get_ticks_usec()
	DirAccess.make_dir_recursive_absolute(base)
	var names := ["a.tres.remap", "b.tres", "c.png.import", "d.res.remap", "e.png",
		"dup.tres", "dup.tres.remap"]
	for n in names:
		_write(base + n)
	DirAccess.make_dir_recursive_absolute(base + "sub")
	var listed := ResourceListing.list_resources(base)
	var want := PackedStringArray(["a.tres", "b.tres", "d.res", "dup.tres"])
	_ok(listed == want, "listing == %s (got %s)" % [want, listed])
	var dup_count := 0
	for n in listed:
		if n == "dup.tres":
			dup_count += 1
	_ok(dup_count == 1, "dup.tres + dup.tres.remap appear once (got %d)" % dup_count)

	print("-- negative control: the old ends_with filter misses the remapped files")
	var naive := _naive_list(base)
	_ok(naive.size() < listed.size(),
		"naive filter finds %d of %d (reproduces the bug)" % [naive.size(), listed.size()])
	_ok(not naive.has("a.tres") and not naive.has("d.res"),
		"naive filter misses a.tres.remap and d.res.remap")

	for n in names:
		DirAccess.remove_absolute(base + n)
	DirAccess.remove_absolute(base + "sub")
	DirAccess.remove_absolute(base)

	print("-- the real item folder")
	var items := ResourceListing.list_resources("res://assets/items/")
	_ok(items.size() == 5, "res://assets/items/ lists 5 resources (got %d: %s)" % [items.size(), items])
	_ok(items.has("health_potion.tres"), "includes health_potion.tres")

	print("-- InventorySystem autoload actually loaded them")
	var inv := root.get_node_or_null("InventorySystem")
	_ok(inv != null, "InventorySystem autoload present")
	if inv != null:
		var loaded = inv.get("_items")
		_ok(loaded is Dictionary and (loaded as Dictionary).size() == 5,
			"InventorySystem holds 5 base items")

	print("resource_listing_test: %d checks, %d failed" % [_checks, _failed])
	print("RESULT: OK" if _failed == 0 else "RESULT: FAILED")
	quit(0 if _failed == 0 else 1)
