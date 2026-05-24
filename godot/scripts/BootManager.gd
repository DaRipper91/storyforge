extends Control

# Shown before any connection attempt.
# Lets testers paste an ngrok URL; remembers it via ConfigFile.

@onready var status_label: Label = $CenterContainer/VBoxContainer/Label
@onready var url_input: LineEdit = $CenterContainer/VBoxContainer/URLBox/URLInput
@onready var connect_btn: Button = $CenterContainer/VBoxContainer/URLBox/ConnectBtn

func _ready():
	PythonClient.connection_status_changed.connect(_on_connection_status)
	url_input.text_submitted.connect(_on_connect_pressed)
	connect_btn.pressed.connect(_on_connect_pressed)

	# When launched from the StoryForge.exe launcher the server is already
	# running locally — skip the URL prompt and connect immediately.
	var auto_url = OS.get_environment("STORYFORGE_SERVER_URL")
	if auto_url.is_empty() and _has_local_server_arg():
		auto_url = PythonClient.DEFAULT_URL

	if not auto_url.is_empty():
		status_label.text = "Starting…"
		url_input.text = auto_url
		PythonClient.start_connection(auto_url)
		return

	var saved = PythonClient.load_saved_url()
	url_input.text = saved
	url_input.placeholder_text = "http://127.0.0.1:8765"
	status_label.text = "Enter server URL and press Connect."


func _has_local_server_arg() -> bool:
	return "--local-server" in OS.get_cmdline_args()

func _on_connect_pressed(_text = "") -> void:
	var url = url_input.text.strip_edges()
	if url.is_empty():
		url = PythonClient.DEFAULT_URL

	connect_btn.disabled = true
	url_input.editable = false
	status_label.text = "Connecting to %s …" % url
	PythonClient.start_connection(url)

func _on_connection_status(connected: bool):
	if connected:
		get_tree().change_scene_to_file("res://scenes/UI_Overlay.tscn")
	else:
		status_label.text = "Could not reach server. Check the URL and try again."
		connect_btn.disabled = false
		url_input.editable = true
