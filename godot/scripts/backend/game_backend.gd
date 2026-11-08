class_name GameBackend
extends RefCounted
## Abstract transport-agnostic game backend.
##
## A GameBackend answers the same requests the Godot client sends to the FastAPI
## server (see docs/offline/CLIENT_BACKEND_CONTRACT.md), without any network.
## Subclasses: LocalBackend (in-process, offline).
##
## There is NO websocket: `state_changed` replaces the ws `state_diff` hop. It is
## emitted after every request that mutated state (even when the request ends in
## an error status after having committed, e.g. the documented 500s) with a deep
## copy of the FULL state, so listeners can re-render without a follow-up GET.

signal state_changed(state: Dictionary)


## Returns {"status": int, "body": Variant}, exactly the HTTP response the
## Python route would give. `path` is the full API path including "/api".
## Non-JSON bodies (FastAPI's 500 page) are returned as a plain String.
func request(_method: String, _path: String, _body: Dictionary = {}, _query: Dictionary = {}) -> Dictionary:
	return {"status": 501, "body": {"detail": "Not implemented"}}


func is_ready() -> bool:
	return false


## Deep copy of the current full state.
func get_state() -> Dictionary:
	return {}
