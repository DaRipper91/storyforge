extends SceneTree
## Headless replay of the route-level golden flows (tests/golden/routes/*.json)
## against a fresh LocalBackend per flow.
##
## godot --headless --path <scratch copy of godot/> -s res://tests/golden/run_routes.gd -- \
##       --routes=<abs path to tests/golden/routes> [--flow=name] [--verbose]
##
## Per step it checks: status + JSON body (numeric-tolerant deep compare), the
## trimmed post-step state where the flow records it, exact RNG consumption
## (values AND bounds), and that state_changed fired iff the real app published
## bus events (campaigns/new|load swap the live state without a bus event; the
## backend emits there on purpose and the check is skipped).
## Exit 0 only when every step of every flow passes or is listed in
## res://tests/golden/route_divergences.json ({flow, step, reason}).

const Compare := preload("res://tests/golden/golden_compare.gd")
const Backend := preload("res://scripts/backend/local_backend.gd")
const Roll := preload("res://scripts/core/roll_provider.gd")
const Seed := preload("res://scripts/core/data/seed_campaign_data.gd")
const DIVERGENCES_PATH := "res://tests/golden/route_divergences.json"
const FROZEN_CLOCK := "2026-01-01T12:00:00+00:00"
const FROZEN_MTIME := 1700000000
const MAX_FAILURE_REPORTS := 10

var _verbose := false
var _frozen: Dictionary = {}
var _emitted := 0
var _seed_state: Dictionary = {}


func _initialize() -> void:
	var routes_dir := ""
	var only_flow := ""
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--routes="):
			routes_dir = arg.substr(9)
		elif arg.begins_with("--flow="):
			only_flow = arg.substr(7)
		elif arg == "--verbose":
			_verbose = true
	if routes_dir == "":
		printerr("usage: -- --routes=<dir> [--flow=<name>] [--verbose]")
		quit(2)
		return

	_seed_state = Seed.get_state()
	var divergences := _load_divergences()
	var files := Array(DirAccess.get_files_at(routes_dir))
	files.sort()
	var lines: Array[String] = []
	var failures: Array[String] = []
	var total_fail := 0
	var total_steps := 0
	var total_pass := 0
	var flows_run := 0
	var used := {}
	for f in files:
		if not (f as String).ends_with(".json"):
			continue
		var doc: Variant = JSON.parse_string(FileAccess.get_file_as_string(routes_dir.path_join(f)))
		if not (doc is Dictionary):
			failures.append("[%s] fixture failed to parse as JSON object" % f)
			total_fail += 1
			continue
		var flow := str(doc["flow"])
		if only_flow != "" and flow != only_flow:
			continue
		flows_run += 1
		var st := _run_flow(doc, divergences, used, failures)
		total_steps += st["total"]
		total_pass += st["pass"]
		total_fail += st["fail"]
		lines.append("%s: %d/%d steps passed, %d failed, %d allowlisted" % [flow, st["pass"], st["total"], st["fail"], st["allow"]])
	if only_flow == "":
		for k in divergences:
			if not used.has(k):
				lines.append("WARNING: divergence entry matches no step: " + k)

	await process_frame
	await process_frame
	var shown := 0
	for fl in failures:
		if shown >= MAX_FAILURE_REPORTS:
			print("... %d more failure(s) not shown" % (failures.size() - shown))
			break
		print(fl)
		shown += 1
	print("---- route golden summary ----")
	for l in lines:
		print(l)
	print("total: %d/%d steps passed across %d flows" % [total_pass, total_steps, flows_run])
	var ok := total_fail == 0 and flows_run > 0
	print("RESULT: %s" % ("OK" if ok else "FAILED"))
	quit(0 if ok else 1)


func _load_divergences() -> Dictionary:
	var out := {}
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(DIVERGENCES_PATH))
	if parsed is Array:
		for e in parsed:
			out["%s#%d" % [str(e["flow"]), int(e["step"])]] = str(e.get("reason", ""))
	return out


func _clock() -> String:
	return FROZEN_CLOCK


func _mtime(dir_name: String, state_path: String) -> float:
	if _frozen.has(dir_name):
		return float(_frozen[dir_name])
	return float(FileAccess.get_modified_time(state_path))


func _on_changed(_state: Dictionary) -> void:
	_emitted += 1


func _rm_rf(path: String) -> void:
	if not DirAccess.dir_exists_absolute(path):
		return
	for d in DirAccess.get_directories_at(path):
		_rm_rf(path.path_join(d))
	for f in DirAccess.get_files_at(path):
		DirAccess.remove_absolute(path.path_join(f))
	DirAccess.remove_absolute(path)


func _freeze_mtimes(save_dir: String) -> void:
	var dirs := Array(DirAccess.get_directories_at(save_dir))
	dirs.sort()
	var i := 0
	for d in dirs:
		if FileAccess.file_exists(save_dir.path_join(d).path_join("state.json")):
			_frozen[d] = FROZEN_MTIME + i
			i += 1


## Same trimming as tools/golden/record_routes.py::_trim.
func _trim(state: Dictionary) -> Dictionary:
	var out := {}
	for k in state:
		if k != "rooms":
			out[k] = state[k]
	var rooms := {}
	var unchanged: Array = []
	var seed_rooms: Dictionary = _seed_state["rooms"]
	for rid in state["rooms"]:
		if seed_rooms.has(rid) and Compare.diff(seed_rooms[rid], state["rooms"][rid], "") == "":
			unchanged.append(rid)
		else:
			rooms[rid] = state["rooms"][rid]
	unchanged.sort()
	out["rooms"] = rooms
	out["unchanged_rooms"] = unchanged
	return out


func _run_flow(doc: Dictionary, divergences: Dictionary, used: Dictionary, failures: Array[String]) -> Dictionary:
	var flow := str(doc["flow"])
	var save_dir := ProjectSettings.globalize_path("res://").path_join(".route_saves").path_join(flow)
	_rm_rf(save_dir)
	DirAccess.make_dir_recursive_absolute(save_dir)
	_frozen = {}
	_emitted = 0
	var backend = Backend.new(save_dir, Callable(self, "_clock"), Roll.scripted({}), {}, Callable(self, "_mtime"))
	backend.state_changed.connect(Callable(self, "_on_changed"))
	var prev := _trim(backend.get_state())
	var st := {"total": 0, "pass": 0, "fail": 0, "allow": 0}

	for step in doc["steps"]:
		st["total"] += 1
		var n := int(step["n"])
		var problems: Array[String] = []
		for pre in step.get("pre", []):
			if pre == "freeze_mtimes":
				_freeze_mtimes(save_dir)
			else:
				problems.append("unknown pre action " + str(pre))
		var req: Dictionary = step["request"]
		var rs: Dictionary = step.get("rng_script", {})
		var script := rs.duplicate(true)
		script["randint_bounds"] = step.get("rng_bounds", [])
		var rolls: CoreRollProvider = Roll.scripted(script)
		backend.set_roll_provider(rolls)
		var body: Dictionary = req["json"] if req["json"] is Dictionary else {}
		_emitted = 0
		var resp: Dictionary = backend.request(str(req["method"]), str(req["path"]), body, req.get("query", {}))

		var exp: Dictionary = step["response"]
		if int(resp["status"]) != int(exp["status"]):
			problems.append("status expected %d, got %d (body %s)" % [int(exp["status"]), int(resp["status"]), Compare.short(resp["body"])])
		elif exp.has("json"):
			var d: String = Compare.diff(exp["json"], resp["body"], "$")
			if d != "":
				problems.append("body: " + d)
		elif exp.has("text"):
			if resp["body"] != exp["text"]:
				problems.append("text body expected %s, got %s" % [Compare.short(exp["text"]), Compare.short(resp["body"])])
		for p in rolls.finish():
			problems.append("RNG: " + p)

		var expects_event: bool = not (step.get("events", []) as Array).is_empty()
		var is_campaign_swap: bool = str(req["path"]).begins_with("/api/campaigns/")
		if expects_event and _emitted == 0:
			problems.append("state_changed not emitted but the app published %d bus event(s)" % (step["events"] as Array).size())
		elif not expects_event and _emitted > 0 and not is_campaign_swap:
			problems.append("state_changed emitted %d time(s) but the app published no bus event" % _emitted)

		if step.has("state_after"):
			var cur := _trim(backend.get_state())
			var sa: Dictionary = step["state_after"]
			var want: Dictionary = prev if sa.has("same_as_previous") else sa
			var sd: String = Compare.diff(want, cur, "$state")
			if sd != "":
				problems.append(("state_after (same_as_previous): " if sa.has("same_as_previous") else "state_after: ") + sd)
			prev = cur

		var key := "%s#%d" % [flow, n]
		var allowed := divergences.has(key)
		if allowed:
			used[key] = true
		if problems.is_empty():
			if allowed:
				st["fail"] += 1
				failures.append("[%s] step %d (%s): in divergence list but PASSES (stale entry)" % [flow, n, step["name"]])
			else:
				st["pass"] += 1
			if _verbose:
				print("PASS  %s #%d %s" % [flow, n, step["name"]])
		else:
			if allowed:
				st["allow"] += 1
				if _verbose:
					print("ALLOW %s #%d: %s (%s)" % [flow, n, problems[0], divergences[key]])
			else:
				st["fail"] += 1
				failures.append("[%s] step %d (%s) %s %s\n    %s" % [flow, n, step["name"], req["method"], req["path"], "\n    ".join(problems)])
				if _verbose:
					print("FAIL  %s #%d %s" % [flow, n, step["name"]])
	_rm_rf(save_dir)
	return st
