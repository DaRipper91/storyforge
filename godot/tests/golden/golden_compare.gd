extends RefCounted
## Numeric-tolerant deep compare shared by the golden runners (same rules as
## run_golden.gd::_diff): integral float == same int (Godot parses every JSON
## number as float); bool is NOT interchangeable with numbers.


static func is_num(v: Variant) -> bool:
	return typeof(v) == TYPE_INT or typeof(v) == TYPE_FLOAT


static func short(v: Variant) -> String:
	var s := JSON.stringify(v)
	return s if s.length() <= 200 else s.substr(0, 200) + "..."


## "" when equal, else a readable description of the first difference.
static func diff(exp: Variant, got: Variant, path: String) -> String:
	if is_num(exp) and is_num(got):
		if is_equal_approx(float(exp), float(got)) and (float(exp) == float(got) or absf(float(exp) - float(got)) < 1e-9):
			return ""
		return "%s: expected %s, got %s" % [path, str(exp), str(got)]
	if typeof(exp) != typeof(got):
		return "%s: type expected %s (%s), got %s (%s)" % [path, type_string(typeof(exp)), short(exp), type_string(typeof(got)), short(got)]
	if exp is Dictionary:
		for k in exp:
			if not got.has(k):
				return "%s: missing key '%s'" % [path, k]
		for k in got:
			if not exp.has(k):
				return "%s: unexpected key '%s'" % [path, k]
		for k in exp:
			var d := diff(exp[k], got[k], path + "." + str(k))
			if d != "":
				return d
		return ""
	if exp is Array:
		if exp.size() != got.size():
			return "%s: array length expected %d, got %d" % [path, exp.size(), got.size()]
		for n in exp.size():
			var d := diff(exp[n], got[n], "%s[%d]" % [path, n])
			if d != "":
				return d
		return ""
	if exp != got:
		return "%s: expected %s, got %s" % [path, short(exp), short(got)]
	return ""
