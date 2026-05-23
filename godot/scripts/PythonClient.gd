extends Node

# The technical bridge between Godot and the Python Brain.
# Connects via HTTP for requests and WebSockets for real-time state updates.
#
# server_url is set by BootManager before _start_connection() is called.
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
		# https → wss, http → ws
		if base.begins_with("https://"):
			base = "wss://" + base.substr(8)
		elif base.begins_with("http://"):
			base = "ws://" + base.substr(7)
		return base + "/ws/session/main"

signal state_updated(new_state)
signal narration_received(text)
signal connection_status_changed(connected)

var ws_client: WebSocketPeer = WebSocketPeer.new()
var is_connected: bool = false

# ─── Called by BootManager once the URL is confirmed ───────────────

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
	cfg.load(CONFIG_PATH)  # load existing so we don't wipe other keys
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

func fetch_catalog():
	var http = HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(_on_catalog_fetched)
	http.request(_base_url + "/lobby/catalog")
	return http

signal catalog_received(catalog_data: Dictionary)

func _on_catalog_fetched(_result, response_code, _headers, body):
	if response_code == 200:
		var json = JSON.parse_string(body.get_string_from_utf8())
		if json:
			catalog_received.emit(json)

func post_request(endpoint: String, data: Dictionary):
	var http = HTTPRequest.new()
	add_child(http)
	var json_data = JSON.stringify(data)
	var headers = ["Content-Type: application/json"]
	http.request(_base_url + endpoint, headers, HTTPClient.METHOD_POST, json_data)
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
