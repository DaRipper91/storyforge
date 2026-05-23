extends Control

# This script manages the transition from the Title Screen to the Main Menu
# and the new Save Game selection menu.

@onready var title_screen = $TitleScreen
@onready var main_menu = $MainMenu
@onready var new_game_btn = $MainMenu/VBoxContainer/NewGameBtn
@onready var load_game_btn = $MainMenu/VBoxContainer/LoadGameBtn
@onready var save_game_menu = $SaveGameMenu
@onready var save_list = $SaveGameMenu/MarginContainer/VBoxContainer/ScrollContainer/SaveList

var is_authenticating = false

func _ready():
	# Start on the title screen
	title_screen.show()
	main_menu.hide()
	save_game_menu.hide()
	
	# Connect to auth signal
	var python_client = get_node_or_null("/root/PythonClient")
	if python_client:
		python_client.auth_completed.connect(_on_auth_completed)

func _input(event):
	if title_screen.visible and not is_authenticating and (event.is_action_pressed("ui_accept") or (event is InputEventMouseButton and event.pressed)):
		is_authenticating = true
		$TitleScreen/PressStart.text = "Authenticating..."
		var python_client = get_node("/root/PythonClient")
		python_client.trigger_desktop_login()

func _on_auth_completed(success: bool, user_info: Dictionary):
	is_authenticating = false
	if success:
		transition_to_menu()
	else:
		$TitleScreen/PressStart.text = "Auth Failed. Press ANY KEY to Retry"

func transition_to_menu():
	title_screen.hide()
	main_menu.show()
	new_game_btn.grab_focus()

func _on_new_game_btn_pressed():
	print("Starting New Game sequence...")
	# This should eventually transition to the character creation scene
	get_tree().change_scene_to_file("res://scenes/Creation.tscn")


func _on_load_game_btn_pressed():
	print("Opening Saves List...")
	main_menu.hide()
	save_game_menu.show()
	_populate_save_games()

func _on_save_back_btn_pressed():
	save_game_menu.hide()
	main_menu.show()
	load_game_btn.grab_focus()

func _populate_save_games():
	# Clear existing save entries
	for child in save_list.get_children():
		child.queue_free()
	
	# TODO: Replace with actual data from PythonClient
	var mock_saves = ["Family_Campaign_01", "Solo_Run_Ashenborn", "The_Ironfast_Chronicles"]
	
	if mock_saves.is_empty():
		var label = Label.new()
		label.text = "No saved chronicles found."
		save_list.add_child(label)
		return
	
	for save_name in mock_saves:
		var btn = Button.new()
		btn.text = save_name
		btn.pressed.connect(func(): _on_save_selected(save_name))
		save_list.add_child(btn)

func _on_save_selected(save_name: String):
	print("Loading save game: ", save_name)
	# TODO: Call PythonClient to load the selected campaign
	# For now, just print the action
