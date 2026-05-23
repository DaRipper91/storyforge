extends Control

func _ready():
	# Since PythonClient is now an Autoload, we can access it directly
	if PythonClient.is_connected:
		_transition()
	else:
		PythonClient.connection_status_changed.connect(_on_connection_status)
		$Label.text = "StoryForge: Initializing Brain..."

func _on_connection_status(connected: bool):
	if connected:
		_transition()
	else:
		$Label.text = "StoryForge: Brain Offline. Retrying..."

func _transition():
	get_tree().change_scene_to_file("res://scenes/UI_Overlay.tscn")
