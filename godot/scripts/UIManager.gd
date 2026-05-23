extends Control

@onready var title_screen  = $TitleScreen
@onready var main_menu     = $MainMenu
@onready var new_game_btn  = $MainMenu/VBoxContainer/NewGameBtn
@onready var load_game_btn = $MainMenu/VBoxContainer/LoadGameBtn
@onready var save_game_menu = $SaveGameMenu
@onready var save_list     = $SaveGameMenu/MarginContainer/VBoxContainer/ScrollContainer/SaveList

var is_authenticating = false

func _ready():
	title_screen.show()
	main_menu.hide()
	save_game_menu.hide()

	var pc = get_node_or_null("/root/PythonClient")
	if pc:
		pc.auth_completed.connect(_on_auth_completed)
		pc.campaigns_received.connect(_on_campaigns_received)
		pc.new_campaign_ready.connect(_on_new_campaign_ready)
		pc.campaign_loaded.connect(_on_campaign_loaded)

func _input(event):
	if title_screen.visible and not is_authenticating \
			and (event.is_action_pressed("ui_accept") \
			or (event is InputEventMouseButton and event.pressed)):
		is_authenticating = true
		$TitleScreen/PressStart.text = "Authenticating..."
		get_node("/root/PythonClient").trigger_desktop_login()

func _on_auth_completed(success: bool, _user_info: Dictionary):
	is_authenticating = false
	if success:
		transition_to_menu()
	else:
		$TitleScreen/PressStart.text = "Auth Failed. Press ANY KEY to Retry"

func transition_to_menu():
	title_screen.hide()
	main_menu.show()
	new_game_btn.grab_focus()

# ─── New game ──────────────────────────────────────────────────────

func _on_new_game_btn_pressed():
	new_game_btn.disabled = true
	new_game_btn.text = "Creating..."
	get_node("/root/PythonClient").new_campaign()

func _on_new_campaign_ready(_state: Dictionary):
	# Campaign created — join as the local player and go to character creation.
	var pc = get_node("/root/PythonClient")
	pc.lobby_joined.connect(_on_lobby_joined_for_creation, CONNECT_ONE_SHOT)
	pc.join_lobby("godot_player")

func _on_lobby_joined_for_creation(_slot_index: int):
	get_node("/root/PythonClient").set_phase("creation")
	get_tree().change_scene_to_file("res://scenes/Creation.tscn")

# ─── Load game ─────────────────────────────────────────────────────

func _on_load_game_btn_pressed():
	main_menu.hide()
	save_game_menu.show()
	_clear_save_list()
	var label = Label.new()
	label.text = "Loading saved chronicles..."
	save_list.add_child(label)
	get_node("/root/PythonClient").fetch_campaigns()

func _on_save_back_btn_pressed():
	save_game_menu.hide()
	main_menu.show()
	load_game_btn.grab_focus()

func _clear_save_list():
	for child in save_list.get_children():
		child.queue_free()

func _on_campaigns_received(campaigns: Array):
	_clear_save_list()

	if campaigns.is_empty():
		var label = Label.new()
		label.text = "No saved chronicles found."
		save_list.add_child(label)
		return

	for save in campaigns:
		var campaign_id: String = save.get("campaign_id", "unknown")
		var char_names: Array  = save.get("characters", [])
		var phase: String      = save.get("phase", "")

		var btn = Button.new()
		var label_text = campaign_id
		if not char_names.is_empty():
			label_text += "  [" + ", ".join(char_names) + "]"
		if not phase.is_empty():
			label_text += "  (" + phase + ")"
		btn.text = label_text
		btn.pressed.connect(func(): _on_save_selected(campaign_id))
		save_list.add_child(btn)

func _on_save_selected(campaign_id: String):
	_clear_save_list()
	var label = Label.new()
	label.text = "Loading %s..." % campaign_id
	save_list.add_child(label)
	get_node("/root/PythonClient").load_campaign(campaign_id)

func _on_campaign_loaded(state: Dictionary):
	var phase = state.get("phase", "lobby")
	if phase == "exploration":
		get_tree().change_scene_to_file("res://scenes/Tabletop.tscn")
	else:
		# Campaign is mid-creation or lobby — send to creation screen.
		get_tree().change_scene_to_file("res://scenes/Creation.tscn")
