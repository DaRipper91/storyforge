extends Area3D

signal interacted(interactable: Area3D, actor: Node3D)

@export var interact_prompt: String = "Interact"
@export var entity_id: String = ""

var _player_in_range: Node3D = null

func _ready() -> void:
	body_entered.connect(_on_body_entered)
	body_exited.connect(_on_body_exited)

func _on_body_entered(body: Node3D) -> void:
	if body.has_method("move_with_input") and body.name.begins_with("Mini_"):
		_player_in_range = body

func _on_body_exited(body: Node3D) -> void:
	if body == _player_in_range:
		_player_in_range = null

func _process(_delta: float) -> void:
	if _player_in_range and Input.is_action_just_pressed("action"):
		interacted.emit(self, _player_in_range)
