extends Node

# The technical bridge between Godot and the Python Brain.
# Connects via HTTP for requests and WebSockets for real-time state updates.

const BASE_URL = "http://localhost:8765/api"
const WS_URL = "ws://localhost:8765/ws"

signal state_updated(new_state)
signal narration_received(text)
signal connection_status_changed(connected)

var ws_client: WebSocketPeer = WebSocketPeer.new()
var is_connected: bool = false

func _ready():
	# Initial connection attempt
	check_python_server()

func check_python_server():
	var http = HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(_on_health_check_completed)
	http.request(BASE_URL + "/healthz")

func _on_health_check_completed(_result, response_code, _headers, _body):
	if response_code == 200:
		is_connected = true
		connection_status_changed.emit(true)
		connect_websocket()
	else:
		is_connected = false
		connection_status_changed.emit(false)
		# Retry in 2 seconds
		await get_tree().create_timer(2.0).timeout
		check_python_server()

func connect_websocket():
	ws_client.connect_to_url(WS_URL)

func _process(_delta):
	ws_client.poll()
	var state = ws_client.get_ready_state()
	if state == WebSocketPeer.STATE_OPEN:
		while ws_client.get_available_packet_count() > 0:
			var packet = ws_client.get_packet()
			_handle_ws_message(packet.get_string_from_utf8())
	elif state == WebSocketPeer.STATE_CLOSED:
		# Handle reconnection logic
		pass

func _handle_ws_message(json_str: String):
	var json = JSON.parse_string(json_str)
	if json and json.has("type"):
		match json["type"]:
			"state_diff":
				# In a real implementation, we might fetch the full state or apply diff
				fetch_full_state()
			"narration":
				narration_received.emit(json["text"])

func fetch_full_state():
	var http = HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(_on_state_fetched)
	http.request(BASE_URL + "/state")

func _on_state_fetched(_result, _response_code, _headers, body):
	var json = JSON.parse_string(body.get_string_from_utf8())
	if json:
		state_updated.emit(json)

func fetch_catalog():
	var http = HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(_on_catalog_fetched)
	http.request(BASE_URL + "/lobby/catalog")
	return http

signal catalog_received(catalog_data: Dictionary)

func _on_catalog_fetched(_result, response_code, _headers, body):
	if response_code == 200:
		var json = JSON.parse_string(body.get_string_from_utf8())
		if json:
			catalog_received.emit(json)

# Helper for generic POST requests (Join Lobby, Create Character, etc.)
func post_request(endpoint: String, data: Dictionary):
	var http = HTTPRequest.new()
	add_child(http)
	var json_data = JSON.stringify(data)
	var headers = ["Content-Type: application/json"]
	http.request(BASE_URL + endpoint, headers, HTTPClient.METHOD_POST, json_data)
	return http

# ───────────────── Auth ─────────────────

signal auth_completed(success: bool, user_info: Dictionary)

func trigger_desktop_login():
	print("Triggering Desktop Auth flow...")
	var http = HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(_on_auth_completed)
	http.request(BASE_URL + "/auth/desktop_login", [], HTTPClient.METHOD_POST, "")

func _on_auth_completed(_result, response_code, _headers, body):
	var json = JSON.parse_string(body.get_string_from_utf8())
	if response_code == 200 and json and json.get("status") == "ok":
		print("Auth successful! User: ", json.get("user", {}).get("name"))
		auth_completed.emit(true, json.get("user", {}))
	else:
		print("Auth failed or was cancelled.")
		auth_completed.emit(false, {})
