extends SceneTree
## Headless golden-fixture replay for the ported core modules.
##
## godot --headless --path <scratch copy of godot/> -s res://tests/golden/run_golden.gd -- \
##       --fixtures=<abs path to tests/golden/fixtures> [--module=grid] [--verbose]
##
## Error convention: a Python exception is a CoreError dictionary
## {"__error__": <ExceptionClass>, "message": ...}. A fixture whose expected
## value is {"raises", "message_contains"} must produce a matching CoreError.
## Modules without a port yet (character_factory, state_manager) are reported
## as NOT PORTED and do not count as failures.
##
## Exit code 0 only if every non-allowlisted, ported fixture passes.

const Grid := preload("res://scripts/core/grid.gd")
const Rules := preload("res://scripts/core/rules.gd")
const Validators := preload("res://scripts/core/validators.gd")
const Enemies := preload("res://scripts/core/enemies.gd")
const Roll := preload("res://scripts/core/roll_provider.gd")
const ALLOWLIST_PATH := "res://tests/golden/known_divergences.json"
const PORTED := ["grid", "rules", "validators", "enemies"]
const MAX_FAILURE_REPORTS := 10

var _verbose := false


func _initialize() -> void:
	var fixtures_dir := ""
	var only_module := ""
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--fixtures="):
			fixtures_dir = arg.substr(11)
		elif arg.begins_with("--module="):
			only_module = arg.substr(9)
		elif arg == "--verbose":
			_verbose = true
	if fixtures_dir == "":
		printerr("usage: -- --fixtures=<dir> [--module=<name>] [--verbose]")
		quit(2)
		return

	var allow := _load_allowlist()
	var stats := {}  # module -> {pass, fail, allow_fail, allow_pass, total}
	var failures: Array[String] = []
	var not_ported: Array[String] = []
	var allow_used := {}
	var bad_fixtures := 0

	var modules := DirAccess.get_directories_at(fixtures_dir)
	modules.sort()
	for module in modules:
		if only_module != "" and module != only_module:
			continue
		var files := Array(DirAccess.get_files_at(fixtures_dir.path_join(module)))
		files.sort()
		if not (module in PORTED):
			not_ported.append("%s (%d fixtures)" % [module, files.size()])
			continue
		var st := {"pass": 0, "fail": 0, "allow_fail": 0, "allow_pass": 0, "total": 0}
		stats[module] = st
		for f in files:
			if not (f as String).ends_with(".json"):
				continue
			st["total"] += 1
			var text := FileAccess.get_file_as_string(fixtures_dir.path_join(module).path_join(f))
			var fx: Variant = JSON.parse_string(text)
			var problems: Array[String] = []
			var case_id := str(f).get_basename()
			if not (fx is Dictionary):
				problems.append("fixture failed to parse as JSON object")
				bad_fixtures += 1
			else:
				case_id = str(fx.get("case", case_id))
				problems = _run_case(fx)
			var allowed: bool = allow.has(case_id)
			if allowed:
				allow_used[case_id] = true
			if problems.is_empty():
				if allowed:
					st["allow_pass"] += 1
					failures.append("[%s] %s: in allowlist but PASSES (stale entry)" % [module, case_id])
				else:
					st["pass"] += 1
				if _verbose:
					print("PASS  %s/%s" % [module, case_id])
			else:
				if allowed:
					st["allow_fail"] += 1
					if _verbose:
						print("ALLOW %s/%s: %s (%s)" % [module, case_id, problems[0], allow[case_id]])
				else:
					st["fail"] += 1
					failures.append("[%s] %s\n    %s" % [module, case_id, "\n    ".join(problems)])
					if _verbose:
						print("FAIL  %s/%s" % [module, case_id])

	var lines: Array[String] = []
	var total_fail := 0
	for module in stats:
		var s: Dictionary = stats[module]
		total_fail += s["fail"]
		lines.append("%s: %d/%d passed, %d failed, %d allowlisted-failing%s" % [
			module, s["pass"], s["total"], s["fail"], s["allow_fail"],
			(", %d allowlisted-but-passing" % s["allow_pass"]) if s["allow_pass"] > 0 else ""])
		total_fail += s["allow_pass"]  # stale allowlist entries must be cleaned up
	for nm in not_ported:
		lines.append("NOT PORTED (not counted): " + nm)
	for k in allow:
		if not allow_used.has(k) and only_module == "":
			lines.append("WARNING: allowlist entry matches no fixture: " + k)

	# Let the project's autoloads finish their (noisy) startup so the summary
	# is genuinely the last thing on stdout.
	await process_frame
	await process_frame
	var shown := 0
	for fl in failures:
		if shown >= MAX_FAILURE_REPORTS:
			print("... %d more failure(s) not shown" % (failures.size() - shown))
			break
		print(fl)
		shown += 1
	print("---- golden summary ----")
	for l in lines:
		print(l)
	var ok := total_fail == 0 and bad_fixtures == 0 and not stats.is_empty()
	print("RESULT: %s" % ("OK" if ok else "FAILED"))
	quit(0 if ok else 1)


func _load_allowlist() -> Dictionary:
	var out := {}
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(ALLOWLIST_PATH))
	if parsed is Array:
		for e in parsed:
			out[str(e["fixture"])] = str(e.get("reason", ""))
	return out


## Returns a list of problems; empty means the case passed.
func _run_case(fx: Dictionary) -> Array[String]:
	var problems: Array[String] = []
	var rolls: CoreRollProvider = Roll.scripted(fx.get("rng_script", {}))
	var inputs: Dictionary = fx["inputs"]
	var result: Variant = _dispatch(str(fx["module"]), str(fx["function"]), inputs, rolls)
	if result is String and (result as String).begins_with("__nodispatch__"):
		problems.append(result)
		return problems

	var expected: Variant = fx["expected"]
	if expected is Dictionary and expected.has("raises"):
		if not CoreError.is_error(result):
			problems.append("expected %s(%s) but got value %s" % [expected["raises"], expected.get("message_contains", ""), _short(result)])
		else:
			if str(result["__error__"]) != str(expected["raises"]):
				problems.append("error class %s != expected %s" % [result["__error__"], expected["raises"]])
			if not str(result["message"]).contains(str(expected.get("message_contains", ""))):
				problems.append("error message '%s' lacks '%s'" % [result["message"], expected.get("message_contains", "")])
	else:
		if CoreError.is_error(result):
			problems.append("unexpected error %s: %s" % [result["__error__"], result["message"]])
		else:
			var d := _diff(expected, result, "$")
			if d != "":
				problems.append("value mismatch: " + d)
	for p in rolls.finish():
		problems.append("RNG: " + p)
	return problems


func _dispatch(module: String, fn: String, i: Dictionary, rolls: CoreRollProvider) -> Variant:
	match module:
		"grid":
			match fn:
				"cell_index": return Grid.cell_index(i["room"], i["coord"])
				"get_cell": return Grid.get_cell(i["room"], i["coord"])
				"set_cell":
					var room: Dictionary = i["room"]
					var r: Variant = Grid.set_cell(room, i["coord"], i["cell"])
					if CoreError.is_error(r):
						return r
					return {"room": room}
				"in_bounds": return Grid.in_bounds(i["room"], i["coord"])
				"chebyshev_distance": return Grid.chebyshev_distance(i["a"], i["b"])
				"feet_between": return Grid.feet_between(i["a"], i["b"])
				"is_traversable": return Grid.is_traversable(i["cell"])
				"movement_cost_feet": return Grid.movement_cost_feet(i["cell"])
				"line_coords": return Grid.line_coords(i["a"], i["b"])
				"path_is_clear": return Grid.path_is_clear(i["room"], i["start"], i["end"])
		"rules":
			if fn == "check_grid_action":
				var st: Dictionary = i["state"]
				return Rules.check_grid_action(st, st["characters"][i["char_id"]], i["action"])
		"validators":
			if fn == "sanitize":
				return Validators.sanitize(i["state"], i["diff"])
		"enemies":
			match fn:
				"resolve_player_attack": return Enemies.resolve_player_attack(i["attacker"], i["target"], rolls)
				"resolve_enemy_attack": return Enemies.resolve_enemy_attack(i["enemy"], i["target"], rolls)
				"_roll_dice": return Enemies._roll_dice(i["notation"], rolls)
				"_mod": return Enemies._mod(int(i["score"]))
				"_weapon_dice": return Enemies._weapon_dice(i["char"])
	return "__nodispatch__ no handler for %s.%s" % [module, fn]


# ─────────────────────── Comparison ───────────────────────

func _is_num(v: Variant) -> bool:
	return typeof(v) == TYPE_INT or typeof(v) == TYPE_FLOAT


## "" when equal. Integral float == same int (Godot parses every JSON number as
## float); bool is NOT interchangeable with numbers.
func _diff(exp: Variant, got: Variant, path: String) -> String:
	if _is_num(exp) and _is_num(got):
		if is_equal_approx(float(exp), float(got)) and (float(exp) == float(got) or absf(float(exp) - float(got)) < 1e-9):
			return ""
		return "%s: expected %s, got %s" % [path, str(exp), str(got)]
	if typeof(exp) != typeof(got):
		return "%s: type expected %s (%s), got %s (%s)" % [path, type_string(typeof(exp)), _short(exp), type_string(typeof(got)), _short(got)]
	if exp is Dictionary:
		for k in exp:
			if not got.has(k):
				return "%s: missing key '%s'" % [path, k]
		for k in got:
			if not exp.has(k):
				return "%s: unexpected key '%s'" % [path, k]
		for k in exp:
			var d := _diff(exp[k], got[k], path + "." + str(k))
			if d != "":
				return d
		return ""
	if exp is Array:
		if exp.size() != got.size():
			return "%s: array length expected %d, got %d" % [path, exp.size(), got.size()]
		for n in exp.size():
			var d := _diff(exp[n], got[n], "%s[%d]" % [path, n])
			if d != "":
				return d
		return ""
	if exp != got:
		return "%s: expected %s, got %s" % [path, _short(exp), _short(got)]
	return ""


func _short(v: Variant) -> String:
	var s := JSON.stringify(v)
	return s if s.length() <= 200 else s.substr(0, 200) + "..."
