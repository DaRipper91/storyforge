class_name LocalBackend
extends "res://scripts/backend/game_backend.gd"
## In-process replacement for the FastAPI app (CORE routes only).
##
## Behaviour is pinned by tests/golden/routes/*.json (status + JSON body of
## every step), parity first: Python quirks and the documented 500 responses
## are reproduced on purpose. See docs/offline/LOCAL_BACKEND.md.
##
## Wraps CoreStateManager (mutators), CoreRules, CoreEnemies, the generated
## race/state/role tables and SeedCampaignData. Persistence mirrors
## persistence/snapshot.py: <save_dir>/<campaign_id>/state.json written
## atomically (temp file + rename) from the state manager's commit/snapshot
## hooks. JSON numbers are normalized on save and load: integral floats become
## ints (5.0 -> 5) because Godot parses every JSON number as float.

const _Seed := preload("res://scripts/core/data/seed_campaign_data.gd")
const _Schema := preload("res://scripts/backend/request_schema.gd")
const _Manager := preload("res://scripts/core/state_manager.gd")
const _Roll := preload("res://scripts/core/roll_provider.gd")
const _Rules := preload("res://scripts/core/rules.gd")
const _Races := preload("res://scripts/core/data/races_data.gd")
const _States := preload("res://scripts/core/data/states_data.gd")
const _Roles := preload("res://scripts/core/data/roles_data.gd")
const _Backgrounds := preload("res://scripts/core/data/backgrounds_data.gd")
const _Lists := preload("res://scripts/core/data/creation_lists_data.gd")

const MAIN_CAMPAIGN_ID := "family_campaign_01"
const STATE_FILENAME := "state.json"
const API_VERSION := "0.1.0"
const PHASES := ["title", "menu", "mode_select", "lobby", "creation", "exploration", "combat"]
const AUTH_REQUIRED := "Authentication or controller_id required"

## [method, path pattern, handler]. Patterns have no leading slash.
const ROUTES := [
	["GET", "api/healthz", "_h_healthz"],
	["GET", "healthz", "_h_healthz"],
	["GET", "api/state", "_h_state"],
	["GET", "api/revision", "_h_revision"],
	["POST", "api/state/trigger_paradox", "_h_trigger_paradox"],
	["POST", "api/time/sync", "_h_time_sync"],
	["GET", "api/lobby/catalog", "_h_catalog"],
	["GET", "api/campaigns", "_h_campaigns_list"],
	["POST", "api/campaigns/new", "_h_campaigns_new"],
	["POST", "api/campaigns/load", "_h_campaigns_load"],
	["POST", "api/lobby/join", "_h_join"],
	["POST", "api/lobby/leave", "_h_leave"],
	["POST", "api/lobby/update_name", "_h_update_name"],
	["POST", "api/lobby/save_draft", "_h_save_draft"],
	["POST", "api/lobby/set_phase", "_h_set_phase"],
	["POST", "api/lobby/start", "_h_start"],
	["POST", "api/character/create", "_h_create_character"],
	["POST", "api/action/grid", "_h_grid"],
	["POST", "api/action/interact_entity", "_h_interact_entity"],
	["POST", "api/action/travel", "_h_travel"],
	["POST", "api/action/freeform", "_h_freeform_stub"],
	["GET", "api/enemy/room/{room_id}", "_h_enemy_room"],
	["POST", "api/enemy/{enemy_id}/attack", "_h_enemy_attack"],
	["POST", "api/auth/desktop_login", "_h_desktop_login_stub"],
]

# ─────────────────────── Request models (pydantic mirrors) ───────────────────────

const _CTRL_OPT := {"name": "controller_id", "kind": "str", "nullable": true, "min": 1, "max": 200}
const JOIN_MODEL := [_CTRL_OPT]
const UPDATE_NAME_MODEL := [
	{"name": "slot_index", "kind": "int", "required": true, "ge": 0, "le": 3},
	{"name": "name", "kind": "str", "required": true, "min": 0, "max": 24},
	_CTRL_OPT,
]
const SET_PHASE_MODEL := [
	{"name": "phase", "kind": "enum", "required": true, "values": PHASES},
]
const COORD_MODEL := [
	{"name": "x", "kind": "int", "required": true, "ge": 0},
	{"name": "y", "kind": "int", "required": true, "ge": 0},
]
const GRID_MODEL := [
	{"name": "type", "kind": "enum", "required": true, "values": ["move", "attack", "interact"], "literal": true},
	{"name": "actor_id", "kind": "str", "required": true},
	{"name": "target", "kind": "model", "required": true, "fields": COORD_MODEL},
]
const ENTITY_MODEL := [
	{"name": "actor_id", "kind": "str", "required": true},
	{"name": "target_id", "kind": "str", "required": true},
]
const TRAVEL_MODEL := [{"name": "room_id", "kind": "str", "required": true}]
const ATTACK_MODEL := [{"name": "actor_id", "kind": "str", "required": true}]
const LOAD_MODEL := [{"name": "campaign_id", "kind": "str", "required": true}]
const TIME_MODEL := [
	{"name": "day", "kind": "int", "required": true},
	{"name": "hour", "kind": "int", "required": true},
	{"name": "minute", "kind": "int", "required": true},
]
const ABILITY_MODEL := [
	{"name": "STR", "kind": "int", "required": true, "ge": 1, "le": 30},
	{"name": "DEX", "kind": "int", "required": true, "ge": 1, "le": 30},
	{"name": "CON", "kind": "int", "required": true, "ge": 1, "le": 30},
	{"name": "INT", "kind": "int", "required": true, "ge": 1, "le": 30},
	{"name": "WIS", "kind": "int", "required": true, "ge": 1, "le": 30},
	{"name": "CHA", "kind": "int", "required": true, "ge": 1, "le": 30},
]
const SAVE_DRAFT_MODEL := [
	{"name": "controller_id", "kind": "str", "required": true, "min": 1, "max": 200},
	{"name": "creation_step", "kind": "str", "nullable": true},
	{"name": "race", "kind": "str", "nullable": true},
	{"name": "evolution_state", "kind": "str", "nullable": true},
	{"name": "predator_role", "kind": "str", "nullable": true},
	{"name": "starting_era", "kind": "str", "nullable": true},
	{"name": "assigned_abilities", "kind": "dict", "nullable": true},
	{"name": "equipment_choice_id", "kind": "str", "nullable": true},
	{"name": "background", "kind": "str", "nullable": true},
	{"name": "skill_proficiencies", "kind": "list_str", "nullable": true},
	{"name": "feat", "kind": "str", "nullable": true},
	{"name": "cantrips", "kind": "list_str", "nullable": true},
	{"name": "alignment", "kind": "str", "nullable": true},
	{"name": "pronouns", "kind": "str", "nullable": true},
	{"name": "title", "kind": "str", "nullable": true},
	{"name": "dialogue_style", "kind": "str", "nullable": true},
	{"name": "physical_description", "kind": "str", "nullable": true},
	{"name": "backstory", "kind": "str", "nullable": true},
	{"name": "personality_traits", "kind": "str", "nullable": true},
	{"name": "flaws", "kind": "str", "nullable": true},
	{"name": "bonds", "kind": "str", "nullable": true},
	{"name": "ideals", "kind": "str", "nullable": true},
	{"name": "keepsake_name", "kind": "str", "nullable": true},
]

# ─────────────────────── Configuration / state ───────────────────────

var save_dir: String
## Callable() -> ISO-8601 UTC String (also used for the new-campaign id).
var clock: Callable
## Callable(dir_name: String, state_file_path: String) -> float (last_modified).
var mtime_provider: Callable
var rolls: CoreRollProvider
var seed_state: Dictionary

var _manager: CoreStateManager
var _dir_name: String = MAIN_CAMPAIGN_ID
var _dirty := false
var _ready_flag := false


func _init(p_save_dir: String = "user://campaigns/", p_clock: Callable = Callable(),
		p_rolls: CoreRollProvider = null, p_seed_state: Dictionary = {},
		p_mtime_provider: Callable = Callable()) -> void:
	save_dir = p_save_dir
	clock = p_clock
	rolls = p_rolls if p_rolls != null else _Roll.live()
	seed_state = normalize_numbers(p_seed_state) if not p_seed_state.is_empty() else {}
	mtime_provider = p_mtime_provider if p_mtime_provider.is_valid() else Callable(self, "_default_mtime")
	# Mirrors main.lifespan: saved main campaign, else the seed.
	var loaded: Variant = _load_dir(MAIN_CAMPAIGN_ID)
	if loaded is Dictionary:
		_install(loaded, MAIN_CAMPAIGN_ID)
	else:
		var s := _seed()
		_install(s, MAIN_CAMPAIGN_ID)
	_ready_flag = true


func is_ready() -> bool:
	return _ready_flag


func get_state() -> Dictionary:
	return _manager.state.duplicate(true)


## Swap the roll source (the route test scripts rolls per step).
func set_roll_provider(p: CoreRollProvider) -> void:
	rolls = p
	_manager.rolls = p


func _seed() -> Dictionary:
	if not seed_state.is_empty():
		return seed_state.duplicate(true)
	return normalize_numbers(_Seed.get_state())


func _install(state: Dictionary, dir_name: String) -> void:
	_dir_name = dir_name
	_manager = _Manager.new(state, rolls, clock)
	_manager.commit_hook = Callable(self, "_on_commit")
	_manager.snapshot_hook = Callable(self, "_on_snapshot")


func _on_commit(_state: Dictionary, _summary: Dictionary) -> void:
	_save()
	_dirty = true


func _on_snapshot(_state: Dictionary) -> void:
	_save()


func _clock_str() -> String:
	return str(clock.call()) if clock.is_valid() else _Manager.default_clock()


# ─────────────────────── Number normalization ───────────────────────

## Deep copy where integral floats become ints (5.0 -> 5).
static func normalize_numbers(v: Variant) -> Variant:
	match typeof(v):
		TYPE_FLOAT:
			if is_finite(v) and v == floorf(v) and absf(v) < 9.0e15:
				return int(v)
			return v
		TYPE_DICTIONARY:
			var d := {}
			for k in v:
				d[k] = normalize_numbers(v[k])
			return d
		TYPE_ARRAY:
			var a := []
			for x in v:
				a.append(normalize_numbers(x))
			return a
	return v


# ─────────────────────── Persistence ───────────────────────

static func _abs(path: String) -> String:
	return ProjectSettings.globalize_path(path) if path.begins_with("res://") or path.begins_with("user://") else path


func _base_dir() -> String:
	return _abs(save_dir).simplify_path().rstrip("/")


func _state_path(dir_name: String) -> String:
	return _base_dir().path_join(dir_name).path_join(STATE_FILENAME)


func _default_mtime(_dir_name_arg: String, state_path: String) -> float:
	return float(FileAccess.get_modified_time(state_path))


func _save() -> int:
	return write_state(_base_dir().path_join(_dir_name), _manager.state)


## Atomic save: temp file in the same directory, flush, rename over the target.
static func write_state(campaign_dir: String, state: Dictionary) -> int:
	var err := DirAccess.make_dir_recursive_absolute(campaign_dir)
	if err != OK and not DirAccess.dir_exists_absolute(campaign_dir):
		return err
	var target := campaign_dir.path_join(STATE_FILENAME)
	var tmp := campaign_dir.path_join(".state-%d.tmp" % Time.get_ticks_usec())
	var payload := JSON.stringify(normalize_numbers(state), "  ", false)
	var f := FileAccess.open(tmp, FileAccess.WRITE)
	if f == null:
		return FileAccess.get_open_error()
	f.store_string(payload)
	f.flush()
	f.close()
	err = DirAccess.rename_absolute(tmp, target)
	if err != OK and FileAccess.file_exists(target):
		# Platforms where rename does not overwrite.
		DirAccess.remove_absolute(target)
		err = DirAccess.rename_absolute(tmp, target)
	if err != OK:
		DirAccess.remove_absolute(tmp)
	return err


## Parsed + number-normalized state, null when absent, CoreError when corrupt.
func _load_dir(dir_name: String) -> Variant:
	var path := _state_path(dir_name)
	if not FileAccess.file_exists(path):
		return null
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	if not (parsed is Dictionary):
		return CoreError.make("JSONDecodeError", "corrupt state file: %s" % dir_name)
	return normalize_numbers(parsed)


# ─────────────────────── Response helpers ───────────────────────

static func _ok(body: Variant) -> Dictionary:
	return {"status": 200, "body": body}


static func _http_err(status: int, detail: Variant) -> Dictionary:
	return {"status": status, "body": {"detail": detail}}


static func _server_error() -> Dictionary:
	return {"status": 500, "body": "Internal Server Error"}


## CoreError -> HTTP. StateError/ValueError map to `status`, anything else is
## an unhandled Python exception (500 text) exactly like FastAPI.
static func _core_failure(err: Dictionary, status: int) -> Dictionary:
	var kind := str(err["__error__"])
	if kind == "StateError" or kind == "ValueError":
		return _http_err(status, str(err["message"]))
	return _server_error()


func _validate(model: Array, body: Variant) -> Dictionary:
	return _Schema.validate(model, body)


func _invalid(v: Dictionary) -> Dictionary:
	return {"status": 422, "body": {"detail": v["errors"]}}


func _current() -> Dictionary:
	return _manager.state


# ─────────────────────── Dispatch ───────────────────────

func request(method: String, path: String, body: Dictionary = {}, query: Dictionary = {}) -> Dictionary:
	_dirty = false
	var p := path
	var q := query.duplicate()
	var qi := p.find("?")
	if qi >= 0:
		for pair in p.substr(qi + 1).split("&", false):
			var kv := pair.split("=", true, 1)
			q[kv[0]] = kv[1] if kv.size() > 1 else ""
		p = p.substr(0, qi)
	if p.length() > 1:
		p = p.rstrip("/")
	var resp := _dispatch(method.to_upper(), p, normalize_numbers(body), q)
	if _dirty and state_changed.get_connections().size() > 0:
		state_changed.emit(_manager.state.duplicate(true))
	return resp


func _dispatch(method: String, path: String, body: Dictionary, query: Dictionary) -> Dictionary:
	var segs := path.trim_prefix("/").split("/")
	# ENCOUNTER routes (routes_npc.py) are not ported yet.
	if path.begins_with("/api/npc/"):
		return _http_err(503, "Not available offline yet")
	var path_known := false
	for r in ROUTES:
		var params: Variant = _match(str(r[1]).split("/"), segs)
		if params == null:
			continue
		path_known = true
		if r[0] != method:
			continue
		return call(r[2], {"body": body, "query": query, "params": params})
	if path_known:
		return _http_err(405, "Method Not Allowed")
	return _http_err(404, "Not Found")


## Pattern segments vs request segments -> params Dictionary, or null.
static func _match(pattern: PackedStringArray, segs: PackedStringArray) -> Variant:
	if pattern.size() != segs.size():
		return null
	var params := {}
	for i in pattern.size():
		var ps := pattern[i]
		if ps.begins_with("{") and ps.ends_with("}"):
			if segs[i] == "":
				return null
			params[ps.substr(1, ps.length() - 2)] = segs[i].uri_decode()
		elif ps != segs[i]:
			return null
	return params


# ─────────────────────── Stubs ───────────────────────

func _h_healthz(_ctx: Dictionary) -> Dictionary:
	return _ok({"status": "ok", "version": API_VERSION})


func _h_freeform_stub(_ctx: Dictionary) -> Dictionary:
	return _http_err(501, "Freeform actions need the AI narrator, which is not available offline")


## Real route runs a Google OAuth flow. Offline we pretend: same shape as the
## Python payload ("status", "user": session payload minus the JWT expiry).
func _h_desktop_login_stub(_ctx: Dictionary) -> Dictionary:
	return _ok({"status": "ok", "user": {
		"sub": "offline", "email": "offline@localhost", "name": "Offline Player",
		"picture": "", "offline": true,
	}})


# ─────────────────────── State routes ───────────────────────

func _h_state(_ctx: Dictionary) -> Dictionary:
	return _ok(_current().duplicate(true))


func _h_revision(_ctx: Dictionary) -> Dictionary:
	return _ok({"revision": _current()["revision"]})


func _h_trigger_paradox(_ctx: Dictionary) -> Dictionary:
	var r: Variant = _manager.trigger_paradox()
	if CoreError.is_error(r):
		return _server_error()
	return _ok(r)


func _h_time_sync(ctx: Dictionary) -> Dictionary:
	var v := _validate(TIME_MODEL, ctx["body"])
	if not (v["errors"] as Array).is_empty():
		return _invalid(v)
	var hour_s := str(int(v["value"]["hour"]))
	var dirty := false
	var npcs: Dictionary = _current()["npcs"]
	for npc_id in npcs:
		var npc: Dictionary = npcs[npc_id]
		var sched: Variant = npc.get("schedule", null)
		if sched is Dictionary and not (sched as Dictionary).is_empty() and (sched as Dictionary).has(hour_s):
			var pos: Dictionary = sched[hour_s]
			var nx := int(pos.get("x", 0))
			var ny := int(pos.get("y", 0))
			if nx < 0 or ny < 0:
				return _server_error()  # pydantic Coord(ge=0) ValidationError in Python
			var cur: Variant = npc.get("target_position", null)
			if not (cur is Dictionary) or int(cur["x"]) != nx or int(cur["y"]) != ny:
				npc["target_position"] = {"x": nx, "y": ny}
				dirty = true
	if dirty:
		_current()["revision"] = int(_current()["revision"]) + 1
		_dirty = true  # state_updated event; NOT persisted (as in Python)
	return _ok({"status": "ok"})


# ─────────────────────── Catalog ───────────────────────

func _h_catalog(_ctx: Dictionary) -> Dictionary:
	var races := {}
	for k in _Races.RACES:
		var r: Dictionary = _Races.RACES[k]
		races[k] = {"name": r["name"], "speed": r["speed"], "ability_bonuses": r["ability_bonuses"].duplicate(true),
			"flavor": r["flavor"], "group": r["group"], "before": r["before"]}
	var states := {}
	for k in _States.STATES:
		var s: Dictionary = _States.STATES[k]
		states[k] = {"name": s["name"], "hit_die": s["hit_die"], "base_armor_class": s["base_armor_class"], "flavor": s["flavor"]}
	var roles := {}
	for k in _Roles.ROLES:
		var p: Dictionary = _Roles.ROLES[k]
		roles[k] = {"name": p["name"], "primary_item": p["primary_item"].duplicate(true),
			"equipment_choices": p["equipment_choices"].duplicate(true), "flavor": p["flavor"]}
	var bgs := {}
	for k in _Backgrounds.BACKGROUNDS:
		var b: Dictionary = _Backgrounds.BACKGROUNDS[k]
		bgs[k] = {"name": b["name"], "flavor": b["flavor"], "perk_name": b["perk_name"],
			"perk_description": b["perk_description"], "bonus_skills": b["bonus_skills"].duplicate(),
			"skill_pool": b["skill_pool"].duplicate()}
	var feats := {}
	for k in _Backgrounds.FEATS:
		var f: Dictionary = _Backgrounds.FEATS[k]
		feats[k] = {"name": f["name"], "flavor": f["flavor"], "mechanical_effect": f["mechanical_effect"]}
	return _ok({
		"races": races, "states": states, "roles": roles, "backgrounds": bgs, "feats": feats,
		"skills": _Lists.SKILLS.duplicate(), "cantrips": _Lists.CANTRIPS.duplicate(),
		"alignments": _Lists.ALIGNMENTS.duplicate(), "dialogue_styles": _Lists.DIALOGUE_STYLES.duplicate(true),
		"standard_array": _Lists.STANDARD_ARRAY.duplicate(),
	})


# ─────────────────────── Campaigns ───────────────────────

func _h_campaigns_list(_ctx: Dictionary) -> Dictionary:
	var base := _base_dir()
	var out: Array = []
	if DirAccess.dir_exists_absolute(base):
		var dirs := Array(DirAccess.get_directories_at(base))
		dirs.sort()
		for d in dirs:
			var path := _state_path(d)
			if not FileAccess.file_exists(path):
				continue
			var raw: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
			if not (raw is Dictionary):
				continue  # Python: except Exception: continue
			var names: Array = []
			var chars: Variant = raw.get("characters", {})
			if chars is Dictionary:
				for c in (chars as Dictionary).values():
					names.append(c.get("name", "?") if c is Dictionary else "?")
			out.append({
				"campaign_id": raw.get("campaign_id", d), "phase": raw.get("phase", "unknown"),
				"characters": names, "revision": raw.get("revision", 0),
				"last_modified": float(mtime_provider.call(d, path)),
			})
	out.sort_custom(func(a, b): return a["last_modified"] > b["last_modified"])
	return _ok({"campaigns": out})


## "2026-01-01T12:00:00+00:00" -> "20260101_120000"
func _campaign_stamp() -> String:
	var s := _clock_str().substr(0, 19)
	return s.replace("-", "").replace(":", "").replace("T", "_")


func _h_campaigns_new(_ctx: Dictionary) -> Dictionary:
	var cid := "campaign_" + _campaign_stamp()
	var state := _seed()
	state["campaign_id"] = cid
	var err := write_state(_base_dir().path_join(cid), state)
	if err != OK:
		return _server_error()
	_install(state, cid)
	_dirty = true
	return _ok(state.duplicate(true))


func _h_campaigns_load(ctx: Dictionary) -> Dictionary:
	var v := _validate(LOAD_MODEL, ctx["body"])
	if not (v["errors"] as Array).is_empty():
		return _invalid(v)
	var cid: String = v["value"]["campaign_id"]
	var base := _base_dir()
	var traversal := _http_err(400, "Invalid campaign_id: potential path traversal detected.")
	if cid.is_absolute_path() or cid.contains("\\") or cid.get_slice(":", 0) != cid:
		return traversal
	var target := base.path_join(cid).simplify_path().rstrip("/")
	if target == base or not target.begins_with(base + "/"):
		return traversal
	var rel := target.substr(base.length() + 1)
	var loaded: Variant = _load_dir(rel)
	if loaded == null:
		return _http_err(404, "campaign '%s' not found" % cid)
	if CoreError.is_error(loaded):
		return _server_error()
	_install(loaded, rel)
	_dirty = true
	return _ok((loaded as Dictionary).duplicate(true))


# ─────────────────────── Lobby routes ───────────────────────

## Cookie auth does not exist offline, so the body's controller_id is always used.
func _controller_id(value: Dictionary) -> Variant:
	var c: Variant = value["value"].get("controller_id", null)
	if c == null or str(c) == "":
		return null
	return str(c)


func _h_join(ctx: Dictionary) -> Dictionary:
	var v := _validate(JOIN_MODEL, ctx["body"])
	if not (v["errors"] as Array).is_empty():
		return _invalid(v)
	var cid: Variant = _controller_id(v)
	if cid == null:
		return _http_err(401, AUTH_REQUIRED)
	var r: Variant = _manager.claim_slot(cid)
	if CoreError.is_error(r):
		return _core_failure(r, 409)
	return _ok(r)


func _h_leave(ctx: Dictionary) -> Dictionary:
	var v := _validate(JOIN_MODEL, ctx["body"])
	if not (v["errors"] as Array).is_empty():
		return _invalid(v)
	var cid: Variant = _controller_id(v)
	if cid == null:
		return _http_err(401, AUTH_REQUIRED)
	var r: Variant = _manager.release_slot(cid)
	if CoreError.is_error(r):
		return _core_failure(r, 404)
	return _ok(r)


func _h_update_name(ctx: Dictionary) -> Dictionary:
	var v := _validate(UPDATE_NAME_MODEL, ctx["body"])
	if not (v["errors"] as Array).is_empty():
		return _invalid(v)
	var cid: Variant = _controller_id(v)
	if cid == null:
		return _http_err(401, AUTH_REQUIRED)
	var r: Variant = _manager.update_slot_name(int(v["value"]["slot_index"]), str(v["value"]["name"]), cid)
	if CoreError.is_error(r):
		return _core_failure(r, 400)
	return _ok(r)


func _h_save_draft(ctx: Dictionary) -> Dictionary:
	var v := _validate(SAVE_DRAFT_MODEL, ctx["body"])
	if not (v["errors"] as Array).is_empty():
		return _invalid(v)
	var patch := {}
	for k in v["value"]:
		if k != "controller_id" and v["value"][k] != null:
			patch[k] = v["value"][k]
	var r: Variant = _manager.save_draft(str(v["value"]["controller_id"]), patch)
	if CoreError.is_error(r):
		return _core_failure(r, 400)
	return _ok(r)


func _h_set_phase(ctx: Dictionary) -> Dictionary:
	var v := _validate(SET_PHASE_MODEL, ctx["body"])
	if not (v["errors"] as Array).is_empty():
		return _invalid(v)
	var r: Variant = _manager.set_phase(str(v["value"]["phase"]))
	if CoreError.is_error(r):
		return _core_failure(r, 400)
	return _ok(r)


func _h_start(_ctx: Dictionary) -> Dictionary:
	var r: Variant = _manager.start_exploration()
	if CoreError.is_error(r):
		return _core_failure(r, 409)
	return _ok(r)


func _creation_model() -> Array:
	return [
		{"name": "slot_index", "kind": "int", "required": true, "ge": 0, "le": 3},
		{"name": "name", "kind": "str", "required": true, "min": 1, "max": 24},
		{"name": "race", "kind": "enum", "required": true, "values": _Races.RACES.keys()},
		{"name": "evolution_state", "kind": "enum", "required": true, "values": _States.STATES.keys()},
		{"name": "predator_role", "kind": "enum", "required": true, "values": _Roles.ROLES.keys()},
		{"name": "starting_era", "kind": "enum", "literal": true, "values": ["before", "after"], "default": "after"},
		{"name": "abilities", "kind": "model", "required": true, "fields": ABILITY_MODEL},
		{"name": "equipment_choice_id", "kind": "str", "nullable": true},
		{"name": "background", "kind": "str", "nullable": true},
		{"name": "skill_proficiencies", "kind": "list_str", "default": []},
		{"name": "feat", "kind": "str", "nullable": true},
		{"name": "cantrips", "kind": "list_str", "default": []},
		{"name": "alignment", "kind": "str", "nullable": true},
		{"name": "pronouns", "kind": "str", "default": "they/them"},
		{"name": "title", "kind": "str", "nullable": true},
		{"name": "dialogue_style", "kind": "str", "nullable": true},
		{"name": "physical_description", "kind": "str", "default": "", "max": 1000},
		{"name": "backstory", "kind": "str", "default": "", "max": 2000},
		{"name": "personality_traits", "kind": "str", "default": "", "max": 500},
		{"name": "flaws", "kind": "str", "default": "", "max": 500},
		{"name": "bonds", "kind": "str", "default": "", "max": 500},
		{"name": "ideals", "kind": "str", "default": "", "max": 500},
		{"name": "keepsake_name", "kind": "str", "nullable": true, "max": 100},
	]


func _h_create_character(ctx: Dictionary) -> Dictionary:
	var v := _validate(_creation_model(), ctx["body"])
	if not (v["errors"] as Array).is_empty():
		return _invalid(v)
	var r: Variant = _manager.create_character(v["value"])
	if CoreError.is_error(r):
		return _core_failure(r, 400)
	return _ok(r)


# ─────────────────────── Action routes ───────────────────────

func _h_grid(ctx: Dictionary) -> Dictionary:
	var v := _validate(GRID_MODEL, ctx["body"])
	if not (v["errors"] as Array).is_empty():
		return _invalid(v)
	var action: Dictionary = v["value"]
	var st := _current()
	if str(st["phase"]) != "exploration":
		return _http_err(409, "grid actions require EXPLORATION phase, currently %s" % str(st["phase"]))
	var ch: Variant = _manager.get_character(str(action["actor_id"]))
	if CoreError.is_error(ch):
		return _server_error()  # StateError is not mapped by this route
	var legality := _Rules.check_grid_action(st, ch, action)
	if not legality["ok"]:
		return _http_err(400, legality["reason"])
	var diff: Variant = _manager.apply_grid_action(ch, action)
	if CoreError.is_error(diff):
		return _server_error()

	var dtype := str(diff.get("type", ""))
	if dtype == "npc_encounter":
		return _ok({"encounter": diff, "revision": st["revision"]})
	if dtype == "room_transition":
		var narrative := "%s steps into %s." % [ch["name"], diff["room_name"]]
		_manager.append_narration(ch["id"], "narration", narrative)
		return _ok({"narrative": narrative, "room_transition": diff, "revision": st["revision"]})
	if dtype != "move":
		# Python: diff["from"] raises KeyError inside the try, the except
		# fallback then reads diff["to"] -> KeyError -> HTTP 500 (after the commit).
		return _server_error()
	# The AI narrator is unavailable offline: always the built-in fallback text.
	var narrative2 := "%s moves to (%d, %d)." % [ch["name"], int(diff["to"]["x"]), int(diff["to"]["y"])]
	_manager.append_narration(ch["id"], "action", narrative2)
	return _ok({"narrative": narrative2, "revision": st["revision"]})


func _h_interact_entity(ctx: Dictionary) -> Dictionary:
	var v := _validate(ENTITY_MODEL, ctx["body"])
	if not (v["errors"] as Array).is_empty():
		return _invalid(v)
	var st := _current()
	if str(st["phase"]) != "exploration":
		return _http_err(409, "actions require EXPLORATION phase, currently %s" % str(st["phase"]))
	var ch: Variant = _manager.get_character(str(v["value"]["actor_id"]))
	if CoreError.is_error(ch):
		return _server_error()
	var target_id := str(v["value"]["target_id"])
	var npcs: Dictionary = st["npcs"]
	if npcs.has(target_id):
		var npc: Dictionary = npcs[target_id]
		return _ok({"encounter": {
			"type": "npc_encounter", "npc_id": npc["id"], "npc_name": npc["name"],
			"encounter_id": npc["encounter_id"], "history": (npc["dialog_history"] as Array).duplicate(true),
		}, "revision": st["revision"]})
	return _http_err(404, "Target not found or not interactable")


func _h_travel(ctx: Dictionary) -> Dictionary:
	var v := _validate(TRAVEL_MODEL, ctx["body"])
	if not (v["errors"] as Array).is_empty():
		return _invalid(v)
	var room_id := str(v["value"]["room_id"])
	var st := _current()
	if not (st["rooms"] as Dictionary).has(room_id):
		return _http_err(404, "unknown room: %s" % room_id)
	var diff: Variant = _manager.fast_travel(room_id)
	if CoreError.is_error(diff):
		return _server_error()
	_manager.append_narration(null, "narration", "The party arrives at %s." % str(st["rooms"][room_id]["name"]))
	return _ok({"room_transition": diff, "revision": st["revision"]})


# ─────────────────────── Enemy routes ───────────────────────

func _h_enemy_room(ctx: Dictionary) -> Dictionary:
	var room_id := str(ctx["params"]["room_id"])
	var out := {}
	var enemies: Dictionary = _current()["enemies"]
	for eid in enemies:
		if str(enemies[eid]["room_id"]) == room_id:
			out[eid] = (enemies[eid] as Dictionary).duplicate(true)
	return _ok({"room_id": room_id, "enemies": out})


func _h_enemy_attack(ctx: Dictionary) -> Dictionary:
	var v := _validate(ATTACK_MODEL, ctx["body"])
	if not (v["errors"] as Array).is_empty():
		return _invalid(v)
	var enemy_id := str(ctx["params"]["enemy_id"])
	var actor_id := str(v["value"]["actor_id"])
	var st := _current()
	var enemies: Dictionary = st["enemies"]
	if not enemies.has(enemy_id):
		return _http_err(404, "unknown enemy: %s" % enemy_id)
	var enemy: Dictionary = enemies[enemy_id]
	if not enemy["alive"]:
		return _http_err(409, "%s is already dead" % str(enemy["name"]))
	var result: Variant = _manager.attack_enemy(actor_id, enemy_id)
	if CoreError.is_error(result):
		return _core_failure(result, 400)
	var lines: Array[String] = [str(result["player_attack"]["hint"])]
	if result.has("enemy_attack"):
		lines.append(str(result["enemy_attack"]["hint"]))
	if result.get("enemy_died", false):
		lines.append("%s collapses. +%d XP." % [str(enemies[enemy_id]["name"]), int(result["xp_reward"])])
	var narrative := " ".join(lines)
	_manager.append_narration(actor_id, "action", narrative)
	result["narrative"] = narrative
	result["revision"] = st["revision"]
	return _ok(result)
