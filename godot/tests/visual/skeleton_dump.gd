extends SceneTree
## Dev tool: dump node layout, bone names, parents and rest rotations of rigged GLBs.
##   godot --headless --path godot -s res://tests/visual/skeleton_dump.gd -- --models=res://a.glb,res://b.glb [--verbose]

func _init() -> void:
	call_deferred("_run")

func _arg(arg_name: String, default_value := "") -> String:
	var prefix := "--%s=" % arg_name
	for a in OS.get_cmdline_user_args():
		if a.begins_with(prefix):
			return a.substr(prefix.length())
	return default_value

func _tree(n: Node, depth: int) -> void:
	var extra := ""
	if n is Node3D:
		extra = " pos=%s scale=%s rot=%s" % [(n as Node3D).position, (n as Node3D).scale, (n as Node3D).rotation_degrees]
	if n is MeshInstance3D:
		var mi := n as MeshInstance3D
		extra += " skin=%s skel=%s verts_aabb=%s" % [mi.skin != null, mi.skeleton, mi.get_aabb().size]
	print("%s%s [%s]%s" % ["  ".repeat(depth), n.name, n.get_class(), extra])
	for c in n.get_children():
		_tree(c, depth + 1)

func _run() -> void:
	var verbose := _arg("verbose", "0") != "0" or OS.get_cmdline_user_args().has("--verbose")
	var first_names := PackedStringArray()
	for path in _arg("models").split(",", false):
		var inst := (load(path) as PackedScene).instantiate() as Node3D
		print("== ", path)
		_tree(inst, 0)
		var sk := inst.find_children("*", "Skeleton3D", true, false)[0] as Skeleton3D
		var names := PackedStringArray()
		for i in sk.get_bone_count():
			names.append(sk.get_bone_name(i))
		if first_names.is_empty():
			first_names = names
			print("bones=", names.size())
			if verbose:
				for i in sk.get_bone_count():
					var q := sk.get_bone_rest(i).basis.get_rotation_quaternion()
					print("  %2d %-24s parent=%-3d rest_euler=%s pos=%s" % [i, names[i], sk.get_bone_parent(i), q.get_euler() * 180.0 / PI, sk.get_bone_rest(i).origin])
		else:
			print("same bone names/order as first: ", names == first_names)
		inst.free()
	quit(0)
