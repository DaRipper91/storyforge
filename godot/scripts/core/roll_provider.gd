class_name CoreRollProvider
extends RefCounted
## Randomness source for the ported core logic.
##
## Two modes:
##  * live     - backed by a RandomNumberGenerator (production).
##  * scripted - constructed from a golden fixture's `rng_script`; values are
##               consumed IN ORDER and every requested (lo, hi) is checked
##               against the recorded `randint_bounds`.
## Problems never throw (GDScript has no exceptions); they are accumulated and
## returned by finish() so the test runner can fail the case.

var is_scripted: bool = false
var _rng: RandomNumberGenerator = null

var _randint: Array = []
var _random: Array = []
var _choice_index: Array = []
var _token_hex: Array = []
var _expected_bounds: Array = []
var _has_expected_bounds: bool = false

var observed_bounds: Array = []
var problems: Array[String] = []


static func live(seed_value: int = -1) -> CoreRollProvider:
	var p := CoreRollProvider.new()
	p._rng = RandomNumberGenerator.new()
	if seed_value >= 0:
		p._rng.seed = seed_value
	else:
		p._rng.randomize()
	return p


static func scripted(script: Dictionary) -> CoreRollProvider:
	var p := CoreRollProvider.new()
	p.is_scripted = true
	p._randint = (script.get("randint", []) as Array).duplicate()
	p._random = (script.get("random", []) as Array).duplicate()
	p._choice_index = (script.get("choice_index", []) as Array).duplicate()
	p._token_hex = (script.get("token_hex", []) as Array).duplicate()
	if script.has("randint_bounds"):
		p._has_expected_bounds = true
		p._expected_bounds = (script["randint_bounds"] as Array).duplicate()
	return p


## Python random.randint(lo, hi): inclusive on both ends.
func randint(lo: int, hi: int) -> int:
	if not is_scripted:
		return _rng.randi_range(lo, hi)
	var call_no := observed_bounds.size()
	observed_bounds.append([lo, hi])
	if _has_expected_bounds:
		if call_no >= _expected_bounds.size():
			problems.append("randint call #%d bounds [%d,%d] but fixture recorded only %d calls" % [call_no, lo, hi, _expected_bounds.size()])
		else:
			var eb: Array = _expected_bounds[call_no]
			if int(eb[0]) != lo or int(eb[1]) != hi:
				problems.append("randint call #%d bounds [%d,%d] != recorded [%d,%d]" % [call_no, lo, hi, int(eb[0]), int(eb[1])])
	if _randint.is_empty():
		problems.append("rng script exhausted for 'randint' (call #%d)" % call_no)
		return lo
	var v := int(_randint.pop_front())
	if v < lo or v > hi:
		problems.append("scripted randint %d outside [%d,%d]" % [v, lo, hi])
	return v


## Python random.random(): float in [0, 1).
func random() -> float:
	if not is_scripted:
		return _rng.randf()
	if _random.is_empty():
		problems.append("rng script exhausted for 'random'")
		return 0.0
	return float(_random.pop_front())


## Index that Python's random.choice(seq) would pick from a sequence of `length`.
func choice_index(length: int) -> int:
	if not is_scripted:
		return _rng.randi_range(0, length - 1)
	if _choice_index.is_empty():
		problems.append("rng script exhausted for 'choice_index'")
		return 0
	return int(_choice_index.pop_front())


## Python secrets.token_hex(nbytes): 2*nbytes lowercase hex chars.
func token_hex(nbytes: int = 32) -> String:
	if not is_scripted:
		var s := ""
		for i in nbytes:
			s += "%02x" % _rng.randi_range(0, 255)
		return s
	if _token_hex.is_empty():
		problems.append("rng script exhausted for 'token_hex'")
		return ""
	return str(_token_hex.pop_front())


## Scripted mode: returns every problem seen, including unconsumed values.
## Live mode: always empty.
func finish() -> Array[String]:
	var out: Array[String] = problems.duplicate()
	if is_scripted:
		for pair in [["randint", _randint], ["random", _random], ["choice_index", _choice_index], ["token_hex", _token_hex]]:
			if not (pair[1] as Array).is_empty():
				out.append("rng script has %d unconsumed '%s' value(s): %s" % [(pair[1] as Array).size(), pair[0], str(pair[1])])
		if _has_expected_bounds and observed_bounds.size() < _expected_bounds.size():
			out.append("port made %d randint call(s), fixture recorded %d" % [observed_bounds.size(), _expected_bounds.size()])
	return out
