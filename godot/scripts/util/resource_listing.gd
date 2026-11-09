class_name ResourceListing
extends RefCounted
## Lists loadable resource files in a res:// directory, in the editor AND in exported builds.
##
## Why this exists: in an export Godot converts text resources and stores them as
## "<name>.tres.remap" (imported assets as "<name>.png.import"). DirAccess lists those stored
## names, so a plain `file_name.ends_with(".tres")` filter matches nothing and the directory looks
## empty. The editor lists the real names, which is why the bug only appears in packaged builds.
## ResourceLoader.load() wants the ORIGINAL path ("armor.tres"), so strip the ".remap" suffix.

const RESOURCE_EXTENSIONS: PackedStringArray = ["tres", "res", "scn", "tscn"]


## Maps a name as returned by DirAccess to the loadable resource name, or "" when the entry is
## not a loadable resource (images, models, notes, ".import" sidecars).
static func loadable_name(file_name: String) -> String:
	var n := file_name
	if n.ends_with(".remap"):
		n = n.trim_suffix(".remap")
	if n.ends_with(".import"):
		return ""
	if RESOURCE_EXTENSIONS.has(n.get_extension().to_lower()):
		return n
	return ""


## Sorted, de-duplicated resource file names (not full paths) directly inside dir_path.
static func list_resources(dir_path: String) -> PackedStringArray:
	var out := PackedStringArray()
	var dir := DirAccess.open(dir_path)
	if dir == null:
		push_error("Failed to open directory %s" % dir_path)
		return out
	var seen := {}
	for f in dir.get_files():
		var n := loadable_name(f)
		if n != "" and not seen.has(n):
			seen[n] = true
			out.append(n)
	out.sort()
	return out
