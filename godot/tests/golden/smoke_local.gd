extends SceneTree
## Headless smoke test of the client's local-backend path (Step D2b).
##
## Drives the REAL PythonClient autoload (mode `--backend=local`) through its public helpers
## (post_request / get_request / new_http / fetch_* / join_lobby ...), i.e. the same code
## paths the scenes use, against a throwaway save dir (never the human's user:// data).
##
## godot --headless --path <scratch copy of godot/> -s res://tests/golden/smoke_local.gd -- \
##       --backend=local --save-dir=<throwaway dir>
## Exit 0 only when every check passes.

var _fails := 0
var _checks := 0
var _pc: Node = null
var _counts := {"state_updated": 0, "conn": 0, "conn_true": 0, "catalog": 0, "campaigns": 0, "joined": 0,
	"created": 0, "create_failed": 0, "started": 0, "auth": 0, "auth_ok": 0, "jon_inv": 0, "state_changed": 0}
var _jon_items: Array = []


func _check(label: String, cond: bool, detail: String = "") -> void:
	_checks += 1
	if cond:
		print("  ok   ", label)
	else:
		_fails += 1
		printerr("  FAIL ", label, "  ", detail)


## Await a node's request_completed -> [result, code, headers, body].
func _wait(http: Node) -> Array:
	return await http.request_completed


func _json(r: Array) -> Variant:
	return JSON.parse_string((r[3] as PackedByteArray).get_string_from_utf8())


func _settle(frames: int = 4) -> void:
	for i in frames:
		await process_frame


func _api_post(path: String, body: Dictionary) -> Array:
	return await _wait(_pc.post_request(path, body))


func _api_get(path: String) -> Array:
	return await _wait(_pc.get_request(path))


func _initialize() -> void:
	_run()


func _run() -> void:
	_pc = root.get_node_or_null("PythonClient")
	if _pc == null:
		printerr("FAIL: PythonClient autoload missing")
		quit(2)
		return
	_pc.state_updated.connect(func(_s): _counts["state_updated"] += 1)
	_pc.connection_status_changed.connect(func(c):
		_counts["conn"] += 1
		if c:
			_counts["conn_true"] += 1)
	_pc.catalog_received.connect(func(_c): _counts["catalog"] += 1)
	_pc.campaigns_received.connect(func(_c): _counts["campaigns"] += 1)
	_pc.lobby_joined.connect(func(_i): _counts["joined"] += 1)
	_pc.character_created.connect(func(_r): _counts["created"] += 1)
	_pc.character_create_failed.connect(func(_e): _counts["create_failed"] += 1)
	_pc.game_started.connect(func(): _counts["started"] += 1)
	_pc.auth_completed.connect(func(ok, _u):
		_counts["auth"] += 1
		if ok:
			_counts["auth_ok"] += 1)
	_pc.jon_inventory_received.connect(func(items):
		_counts["jon_inv"] += 1
		_jon_items = items)

	# Autoload _ready (mode resolution, backend creation) runs on the first frame of a -s script.
	await process_frame
	print("== mode / boot")
	_check("backend_mode == local", _pc.backend_mode == "local", str(_pc.backend_mode))
	_check("is_local()", _pc.is_local())
	var be = _pc.get_local_backend()
	_check("LocalBackend created and ready", be != null and be.is_ready())
	if be == null:
		quit(1)
		return
	be.state_changed.connect(func(_s): _counts["state_changed"] += 1)
	_check("save dir is the throwaway one", not str(be.save_dir).begins_with("user://"), str(be.save_dir))
	await _settle(3)
	_check("connection_status_changed(true) fired exactly once", _counts["conn"] == 1 and _counts["conn_true"] == 1,
		str(_counts))
	var h = _pc.new_http()
	_check("new_http() is a BackendHttp, not HTTPRequest", not (h is HTTPRequest) and h.has_signal("request_completed"))
	h.free()

	print("== auth stub / health / state")
	_pc.trigger_desktop_login()
	await _settle(3)
	_check("auth_completed(true)", _counts["auth"] == 1 and _counts["auth_ok"] == 1, str(_counts))
	var r := await _api_get("/healthz")
	_check("GET /healthz 200", r[1] == 200 and _json(r).get("status") == "ok")
	r = await _api_get("/state")
	var st: Dictionary = _json(r)
	_check("GET /state 200, seed loaded", r[1] == 200 and st.get("phase") != null and st.has("rooms"),
		str(r[1]))
	var rev0: int = int(st.get("revision", -1))
	_pc.fetch_full_state()
	await _settle(3)
	_check("fetch_full_state -> state_updated once", _counts["state_updated"] == 1, str(_counts["state_updated"]))

	print("== catalog / campaigns")
	_pc.fetch_catalog()
	await _settle(3)
	_check("catalog_received once", _counts["catalog"] == 1)
	_pc.fetch_campaigns()
	await _settle(3)
	_check("campaigns_received once", _counts["campaigns"] == 1)
	r = await _api_get("/campaigns")
	_check("GET /campaigns 200 with list", r[1] == 200 and _json(r).get("campaigns") is Array)

	print("== lobby -> creation -> start")
	var su0: int = _counts["state_updated"]
	var sc0: int = _counts["state_changed"]
	_pc.join_lobby("smoke_player")
	await _settle(4)
	_check("lobby_joined once", _counts["joined"] == 1)
	_check("join committed -> state_changed -> one state_updated",
		_counts["state_changed"] == sc0 + 1 and _counts["state_updated"] == su0 + 1,
		str(_counts))
	r = await _api_post("/lobby/update_name", {"controller_id": "smoke_player", "name": "Rook", "slot_index": 0})
	_check("update_name 200", r[1] == 200, str(r[1]))
	_pc.set_phase("creation")
	await _settle(4)
	_pc.create_character({
		"slot_index": 0, "name": "Rook", "race": "veilborn", "evolution_state": "mimic",
		"predator_role": "stalker", "starting_era": "after",
		"abilities": {"CHA": 13, "CON": 14, "DEX": 15, "INT": 10, "STR": 8, "WIS": 12}})
	await _settle(4)
	_check("character_created once, no failure", _counts["created"] == 1 and _counts["create_failed"] == 0,
		str(_counts))
	_pc.start_game()
	await _settle(4)
	_check("game_started once", _counts["started"] == 1)
	r = await _api_get("/state")
	st = _json(r)
	_check("phase exploration, actor 'rook' exists", str(st.get("phase")) == "exploration" and st["characters"].has("rook"),
		str(st.get("phase")))
	_check("revision advanced", int(st["revision"]) > rev0)

	print("== grid move")
	su0 = _counts["state_updated"]
	r = await _api_post("/action/grid", {"actor_id": "rook", "type": "move", "target": {"x": 1, "y": 6}})
	_check("move 200", r[1] == 200, str(r[1]))
	await _settle(4)
	_check("move -> exactly one state_updated", _counts["state_updated"] == su0 + 1, str(_counts["state_updated"] - su0))
	r = await _api_post("/action/grid", {"actor_id": "rook", "type": "move", "target": {"x": 99, "y": 99}})
	_check("out-of-bounds move 400 (handled error)", r[1] == 400, str(r[1]))
	r = await _api_post("/action/grid", {"actor_id": "nobody", "type": "move", "target": {"x": 1, "y": 6}})
	_check("unknown actor -> 500 plain text, body not JSON-crashing",
		r[1] == 500 and (r[3] as PackedByteArray).get_string_from_utf8() == "Internal Server Error", str(r[1]))

	print("== travel / enemy attack")
	r = await _api_post("/action/travel", {"room_id": "back_alley"})
	_check("travel back_alley 200", r[1] == 200, str(r[1]))
	r = await _api_get("/enemy/room/back_alley")
	_check("enemy/room 200", r[1] == 200, str(r[1]))
	r = await _api_post("/enemy/bandit_01/attack", {"actor_id": "rook"})
	_check("enemy attack 200 with player_attack", r[1] == 200 and _json(r) is Dictionary and _json(r).has("player_attack"),
		str(r[1]))
	r = await _api_post("/action/travel", {"room_id": "crossroads"})
	_check("travel crossroads 200", r[1] == 200, str(r[1]))
	r = await _api_post("/action/travel", {"room_id": "atlantis"})
	_check("travel atlantis 404", r[1] == 404, str(r[1]))
	r = await _api_post("/time/sync", {"day": 1, "hour": 7, "minute": 0})
	_check("time/sync 200 (TimeManager path)", r[1] == 200, str(r[1]))

	print("== unsupported-in-local routes are handled, not crashes")
	r = await _api_post("/npc/jon/escape", {})
	_check("npc route -> 503 with detail", r[1] == 503 and _json(r).get("detail") != null, str(r[1]))
	r = await _api_post("/action/interact_entity", {"actor_id": "rook", "target_id": "nobody_here"})
	_check("interact_entity unknown target is a clean error status", r[1] >= 400 and r[1] < 600, str(r[1]))
	r = await _api_post("/action/freeform", {"actor_id": "rook", "text": "look around"})
	_check("freeform -> 501 with detail", r[1] == 501 and _json(r).get("detail") != null, str(r[1]))
	_pc.fetch_jon_inventory("fantasy")
	await _settle(3)
	_check("jon inventory 503 -> jon_inventory_received([])", _counts["jon_inv"] == 1 and _jon_items.is_empty())
	var msgs: Array = []
	_pc.jon_buy_result.connect(func(ok, m): msgs.append([ok, m]))
	_pc.buy_jon_item("rook", "x")
	await _settle(3)
	_check("jon buy 503 -> jon_buy_result(false, message)", msgs.size() == 1 and msgs[0][0] == false and msgs[0][1] is String,
		str(msgs))

	print("== persistence into the throwaway dir")
	var dir := str(be.save_dir)
	_check("state.json written under throwaway dir",
		FileAccess.file_exists(dir.path_join("family_campaign_01").path_join("state.json")), dir)

	print("RESULT: %s (%d checks, %d failed)" % ["OK" if _fails == 0 else "FAILED", _checks, _fails])
	quit(0 if _fails == 0 else 1)
