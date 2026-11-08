class_name RequestSchema
extends RefCounted
## Tiny pydantic-v2 / FastAPI request validator.
##
## A schema is an Array of field specs (declaration order == error order):
##   {"name": String, "kind": "str"|"int"|"enum"|"dict"|"list_str"|"model",
##    "required": bool, "nullable": bool, "default": Variant,
##    "min": int, "max": int            # str length (chars)
##    "ge": int, "le": int              # int bounds
##    "values": Array                   # enum / literal members
##    "literal": bool                   # enum error type "literal_error" instead of "enum"
##    "fields": Array}                  # nested model
## validate() returns {"value": Dictionary, "errors": Array}. `errors` has the
## exact shape of a FastAPI 422 body's `detail` list (type/loc/msg/input/ctx).
## Extra keys in the input are ignored (pydantic default). Lax coercions that
## the client never triggers (e.g. "5" -> 5) are limited to numeric strings for
## int fields and bool -> int.


static func validate(fields: Array, data: Variant) -> Dictionary:
	var errors: Array = []
	var out := _model(fields, data, ["body"], errors)
	return {"value": out, "errors": errors}


static func _err(type: String, loc: Array, msg: String, input: Variant, ctx: Variant = null) -> Dictionary:
	var e := {"type": type, "loc": loc.duplicate(), "msg": msg, "input": input}
	if ctx != null:
		e["ctx"] = ctx
	return e


static func _model(fields: Array, data: Variant, loc: Array, errors: Array) -> Dictionary:
	var out := {}
	if typeof(data) != TYPE_DICTIONARY:
		errors.append(_err("model_attributes_type", loc, "Input should be a valid dictionary or object to extract fields from", data))
		return out
	var d: Dictionary = data
	for f in fields:
		var fname: String = f["name"]
		var floc: Array = loc + [fname]
		if not d.has(fname):
			if f.get("required", false):
				errors.append(_err("missing", floc, "Field required", d))
			elif f.has("default"):
				out[fname] = _copy(f["default"])
			else:
				out[fname] = null
			continue
		var v: Variant = d[fname]
		if typeof(v) == TYPE_NIL and f.get("nullable", false):
			out[fname] = null
			continue
		out[fname] = _value(f, v, floc, errors)
	return out


static func _copy(v: Variant) -> Variant:
	if v is Dictionary or v is Array:
		return v.duplicate(true)
	return v


static func _plural(n: int) -> String:
	return "" if n == 1 else "s"


static func _expected(values: Array) -> String:
	var q: Array[String] = []
	for v in values:
		q.append("'%s'" % str(v))
	if q.size() == 1:
		return q[0]
	return ", ".join(q.slice(0, q.size() - 1)) + " or " + q[q.size() - 1]


static func _value(f: Dictionary, v: Variant, loc: Array, errors: Array) -> Variant:
	match str(f["kind"]):
		"str":
			if typeof(v) != TYPE_STRING:
				errors.append(_err("string_type", loc, "Input should be a valid string", v))
				return v
			var s: String = v
			if f.has("min") and s.length() < int(f["min"]):
				errors.append(_err("string_too_short", loc, "String should have at least %d character%s" % [int(f["min"]), _plural(int(f["min"]))], v, {"min_length": int(f["min"])}))
			elif f.has("max") and s.length() > int(f["max"]):
				errors.append(_err("string_too_long", loc, "String should have at most %d character%s" % [int(f["max"]), _plural(int(f["max"]))], v, {"max_length": int(f["max"])}))
			return v
		"int":
			var n: int = 0
			match typeof(v):
				TYPE_INT:
					n = v
				TYPE_BOOL:
					n = 1 if v else 0
				TYPE_FLOAT:
					if is_finite(v) and v == floorf(v):
						n = int(v)
					else:
						errors.append(_err("int_from_float", loc, "Input should be a valid integer, got a number with a fractional part", v))
						return v
				TYPE_STRING:
					if (v as String).strip_edges().is_valid_int():
						n = int((v as String).strip_edges())
					else:
						errors.append(_err("int_parsing", loc, "Input should be a valid integer, unable to parse string as an integer", v))
						return v
				_:
					errors.append(_err("int_type", loc, "Input should be a valid integer", v))
					return v
			if f.has("ge") and n < int(f["ge"]):
				errors.append(_err("greater_than_equal", loc, "Input should be greater than or equal to %d" % int(f["ge"]), v, {"ge": int(f["ge"])}))
			elif f.has("le") and n > int(f["le"]):
				errors.append(_err("less_than_equal", loc, "Input should be less than or equal to %d" % int(f["le"]), v, {"le": int(f["le"])}))
			return n
		"enum":
			if typeof(v) == TYPE_STRING and (v in (f["values"] as Array)):
				return v
			var exp := _expected(f["values"])
			errors.append(_err("literal_error" if f.get("literal", false) else "enum", loc, "Input should be " + exp, v, {"expected": exp}))
			return v
		"dict":
			if typeof(v) != TYPE_DICTIONARY:
				errors.append(_err("dict_type", loc, "Input should be a valid dictionary", v))
			return v
		"list_str":
			if typeof(v) != TYPE_ARRAY:
				errors.append(_err("list_type", loc, "Input should be a valid list", v))
				return v
			var items: Array = v
			for i in items.size():
				if typeof(items[i]) != TYPE_STRING:
					errors.append(_err("string_type", loc + [i], "Input should be a valid string", items[i]))
			return v
		"model":
			return _model(f["fields"], v, loc, errors)
	return v
