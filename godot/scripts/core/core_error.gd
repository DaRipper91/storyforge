class_name CoreError
extends RefCounted
## Error-return convention for the ported core modules.
##
## GDScript has no exceptions, so a function that raises in Python returns a
## Dictionary {"__error__": "<PythonExceptionClassName>", "message": "<str(exc)>"}.
## Callers that can see such a value must check CoreError.is_error() first.


static func make(kind: String, message: String) -> Dictionary:
	return {"__error__": kind, "message": message}


static func is_error(value: Variant) -> bool:
	return value is Dictionary and (value as Dictionary).has("__error__")
