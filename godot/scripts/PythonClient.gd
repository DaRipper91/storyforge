extends Node

# The technical bridge between Godot and the Python Brain.
# Connects via HTTP for requests and WebSockets for real-time state updates.
#
# server_url is set by BootManager before start_connection() is called.
# Default is localhost for solo play; paste an ngrok URL for remote testing.

const CONFIG_PATH = "user://settings.cfg"
const CONFIG_SECTION = "network"
const CONFIG_KEY_URL = "server_url"
const DEFAULT_URL = "http://127.0.0.1:8765"

var server_url: String = DEFAULT_URL  # set by BootManager; no trailing slash

var _base_url: String:
	get: return server_url.rstrip("/") + "/api"

var _ws_url: String:
	get:
		var base = server_url.rstrip("/")
		if base.begins_with("https://"):
			base = "wss://" + base.substr(8)
		elif base.begins_with("http://"):
			base = "ws://" + base.substr(7)
		return base + "/ws/session/main"

signal state_updated(new_state)
signal narration_received(text)
signal connection_status_changed(connected)
signal paradox_triggered(transformed_ids: Array)
signal phase_changed(phase: String)
signal npc_event_received(ev: Dictionary)
signal particle_event_received(ev: Dictionary)

var ws_client: WebSocketPeer = WebSocketPeer.new()
var is_connected: bool = false

# ─── Called by BootManager once the URL is confirmed ───────────────

func _ready() -> void:
	_setup_input_map()

func _setup_input_map() -> void:
	var actions = {
		"move_up":    [KEY_W, KEY_UP, [JOY_AXIS_LEFT_Y, -1.0]],
		"move_down":  [KEY_S, KEY_DOWN, [JOY_AXIS_LEFT_Y, 1.0]],
		"move_left":  [KEY_A, KEY_LEFT, [JOY_AXIS_LEFT_X, -1.0]],
		"move_right": [KEY_D, KEY_RIGHT, [JOY_AXIS_LEFT_X, 1.0]],
		"action":     [KEY_E, KEY_ENTER, JOY_BUTTON_A],
		"z_target":   [KEY_Q, [JOY_AXIS_LEFT_TRIGGER, 1.0]],
		"look_up":    [[JOY_AXIS_RIGHT_Y, -1.0]],
		"look_down":  [[JOY_AXIS_RIGHT_Y, 1.0]],
		"look_left":  [[JOY_AXIS_RIGHT_X, -1.0]],
		"look_right": [[JOY_AXIS_RIGHT_X, 1.0]]
	}

	for action in actions:
		if not InputMap.has_action(action):
			InputMap.add_action(action)
		
		for event_data in actions[action]:
			var event: InputEvent
			if event_data is int: # KeyCode or JoyButton
				if event_data < 500: # Simple heuristic for JoyButton vs KeyCode
					event = InputEventJoypadButton.new()
					event.button_index = event_data
				else:
					event = InputEventKey.new()
					event.physical_keycode = event_data
			elif event_data is Array: # JoyAxis [axis, value]
				event = InputEventJoypadMotion.new()
				event.axis = event_data[0]
				event.axis_value = event_data[1]
			
			if event:
				InputMap.action_add_event(action, event)

func start_connection(url: String) -> void:
	server_url = url.rstrip("/")
	_save_url(server_url)
	check_python_server()

func load_saved_url() -> String:
	var cfg = ConfigFile.new()
	if cfg.load(CONFIG_PATH) == OK:
		return cfg.get_value(CONFIG_SECTION, CONFIG_KEY_URL, DEFAULT_URL)
	return DEFAULT_URL

func _save_url(url: String) -> void:
	var cfg = ConfigFile.new()
	cfg.load(CONFIG_PATH)
	cfg.set_value(CONFIG_SECTION, CONFIG_KEY_URL, url)
	cfg.save(CONFIG_PATH)

# ─── Connection ────────────────────────────────────────────────────

func check_python_server():
	var http = HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(_on_health_check_completed)
	http.request(_base_url + "/healthz")

func _on_health_check_completed(_result, response_code, _headers, _body):
	if response_code == 200:
		is_connected = true
		connection_status_changed.emit(true)
		connect_websocket()
	else:
		is_connected = false
		connection_status_changed.emit(false)
		await get_tree().create_timer(2.0).timeout
		check_python_server()

func connect_websocket():
	ws_client.connect_to_url(_ws_url)

func _process(_delta):
	ws_client.poll()
	var state = ws_client.get_ready_state()
	if state == WebSocketPeer.STATE_OPEN:
		while ws_client.get_available_packet_count() > 0:
			var packet = ws_client.get_packet()
			_handle_ws_message(packet.get_string_from_utf8())
	elif state == WebSocketPeer.STATE_CLOSED:
		pass

func _handle_ws_message(json_str: String):
	var json = JSON.parse_string(json_str)
	if json and json.has("type"):
		match json["type"]:
			"state_diff":
				fetch_full_state()
			"narration":
				narration_received.emit(json["text"])
			"paradox_triggered":
				paradox_triggered.emit(json.get("transformed_ids", []))
			"phase_changed":
				phase_changed.emit(json.get("phase", ""))
			"npc_event":
				_handle_npc_event(json)
				npc_event_received.emit(json)
			"particle_event":
				particle_event_received.emit(json)


func _handle_npc_event(ev: Dictionary):
	var npc    = ev.get("npc", "")
	var action = ev.get("action", "")
	var mood   = ev.get("mood", "warm")
	if npc == "redvelvet" and action == "perform":
		var path = "res://assets/audio/performance_%s.wav" % mood
		AudioManager.play_npc_performance(path, mood)

# ─── REST helpers ──────────────────────────────────────────────────

func fetch_full_state():
	var http = HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(_on_state_fetched)
	http.request(_base_url + "/state")

func _on_state_fetched(_result, _response_code, _headers, body):
	var json = JSON.parse_string(body.get_string_from_utf8())
	if json:
		state_updated.emit(json)

func post_request(endpoint: String, data: Dictionary) -> HTTPRequest:
	var http = HTTPRequest.new()
	add_child(http)
	var json_data = JSON.stringify(data)
	var headers = ["Content-Type: application/json"]
	http.request(_base_url + endpoint, headers, HTTPClient.METHOD_POST, json_data)
	return http

func get_request(endpoint: String) -> HTTPRequest:
	var http = HTTPRequest.new()
	add_child(http)
	http.request(_base_url + endpoint)
	return http

# ─── Auth ──────────────────────────────────────────────────────────

signal auth_completed(success: bool, user_info: Dictionary)

func trigger_desktop_login():
	print("Triggering Desktop Auth flow...")
	var http = HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(_on_auth_completed)
	http.request(_base_url + "/auth/desktop_login", [], HTTPClient.METHOD_POST, "")

func _on_auth_completed(_result, response_code, _headers, body):
	var json = JSON.parse_string(body.get_string_from_utf8())
	if response_code == 200 and json and json.get("status") == "ok":
		print("Auth successful! User: ", json.get("user", {}).get("name"))
		auth_completed.emit(true, json.get("user", {}))
	else:
		print("Auth failed or was cancelled.")
		auth_completed.emit(false, {})

# ─── Catalog ───────────────────────────────────────────────────────

signal catalog_received(catalog_data: Dictionary)

func fetch_catalog():
	var http = HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(_on_catalog_fetched)
	http.request(_base_url + "/lobby/catalog")
	return http

func _on_catalog_fetched(_result, response_code, _headers, body):
	if response_code == 200:
		var json = JSON.parse_string(body.get_string_from_utf8())
		if json:
			catalog_received.emit(json)

# ─── Campaign management ───────────────────────────────────────────

signal campaigns_received(campaigns: Array)
signal new_campaign_ready(state: Dictionary)
signal campaign_loaded(state: Dictionary)

func fetch_campaigns() -> void:
	var http = HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(_on_campaigns_fetched)
	http.request(_base_url + "/campaigns")

func _on_campaigns_fetched(_result, response_code, _headers, body):
	if response_code == 200:
		var json = JSON.parse_string(body.get_string_from_utf8())
		if json:
			campaigns_received.emit(json.get("campaigns", []))
		else:
			campaigns_received.emit([])

func new_campaign() -> void:
	var http = HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(_on_new_campaign_ready)
	http.request(_base_url + "/campaigns/new", [], HTTPClient.METHOD_POST, "")

func _on_new_campaign_ready(_result, response_code, _headers, body):
	if response_code == 200:
		var json = JSON.parse_string(body.get_string_from_utf8())
		if json:
			new_campaign_ready.emit(json)

func load_campaign(campaign_id: String) -> void:
	var http = post_request("/campaigns/load", {"campaign_id": campaign_id})
	http.request_completed.connect(_on_campaign_loaded)

func _on_campaign_loaded(_result, response_code, _headers, body):
	if response_code == 200:
		var json = JSON.parse_string(body.get_string_from_utf8())
		if json:
			campaign_loaded.emit(json)

# ─── Lobby ─────────────────────────────────────────────────────────

signal lobby_joined(slot_index: int)

func join_lobby(controller_id: String) -> void:
	var http = post_request("/lobby/join", {"controller_id": controller_id})
	http.request_completed.connect(_on_lobby_joined)

func _on_lobby_joined(_result, response_code, _headers, body):
	if response_code == 200:
		var json = JSON.parse_string(body.get_string_from_utf8())
		if json:
			lobby_joined.emit(json.get("slot_index", 0))

func set_phase(phase: String) -> void:
	post_request("/lobby/set_phase", {"phase": phase})

# ─── Character creation ────────────────────────────────────────────

signal character_created(result: Dictionary)
signal character_create_failed(error: String)

func create_character(data: Dictionary) -> void:
	var http = post_request("/character/create", data)
	http.request_completed.connect(_on_character_created)

func _on_character_created(_result, response_code, _headers, body):
	var json = JSON.parse_string(body.get_string_from_utf8())
	if response_code == 200 and json:
		character_created.emit(json)
	else:
		var msg = json.get("detail", "Unknown error") if json else "Unknown error"
		character_create_failed.emit(msg)

signal game_started()
signal game_start_failed(error: String)

func start_game() -> void:
	var http = post_request("/lobby/start", {})
	http.request_completed.connect(_on_game_started)

func _on_game_started(_result, response_code, _headers, body):
	if response_code == 200:
		game_started.emit()
	else:
		var json = JSON.parse_string(body.get_string_from_utf8())
		var msg = json.get("detail", "Unknown error") if json else "Unknown error"
		game_start_failed.emit(msg)
