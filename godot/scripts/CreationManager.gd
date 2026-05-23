extends Control

# Manages the new two-panel Character Creation flow.
# Still transitions: Race -> State -> Role -> Abilities -> Name.

@onready var race_list = $MarginContainer/VBoxContainer/HSplitContainer/LeftPanel/RaceList
@onready var description_label = $MarginContainer/VBoxContainer/HSplitContainer/RightPanel/MarginContainer/DescriptionLabel
@onready var next_btn = $MarginContainer/VBoxContainer/Footer/NextBtn
@onready var back_btn = $MarginContainer/VBoxContainer/Footer/BackBtn

var catalog: Dictionary = {}
var current_step: int = 0
var selection: Dictionary = {
	"race": null,
	"state": null,
	"role": null,
	"abilities": {},
	"name": ""
}
var button_group = ButtonGroup.new()

func _ready():
	back_btn.grab_focus()
	button_group.set("allow_unpress", true)
	
	var python_client = get_node_or_null("/root/PythonClient")
	if python_client:
		python_client.catalog_received.connect(_on_catalog_received)
		python_client.fetch_catalog()
	else:
		_setup_mock_catalog()
		_render_race_step()

func _on_catalog_received(new_catalog: Dictionary):
	catalog = new_catalog
	_render_race_step()

func _setup_mock_catalog():
	catalog = {
		"races": {
			"ashenborn": {"name": "Ashenborn", "before": "Human", "flavor": "Charred survivors of the Paradox, they are defined by their resilience and grim determination. They rise from the ashes of the old world, their humanity both a memory and a curse."},
			"ashcrown": {"name": "Ashcrown", "before": "High Elf", "flavor": "Once regal, now brittle. The Ashcrown carry the sorrow of a lost age in their very bones. Their grace is a ghost, their beauty a fading ember."},
			"ironfast": {"name": "Ironfast", "before": "Dwarf", "flavor": "Calcified and dense, the Ironfast are as unyielding as the mountains they once carved. The Paradox turned their stubbornness into physical reality."}
		}
	}

func _render_race_step():
	description_label.text = "Select an ancestry to learn its story..."
	next_btn.disabled = true
	
	for child in race_list.get_children():
		child.queue_free()
	
	for race_id in catalog.races:
		var race_data = catalog.races[race_id]
		var btn = Button.new()
		btn.text = race_data.get("before", race_data.name)
		btn.toggle_mode = true
		btn.button_group = button_group
		
		btn.mouse_entered.connect(func(): _on_race_hover(race_id))
		btn.pressed.connect(func(): _on_race_selected(race_id))
		race_list.add_child(btn)

func _on_race_hover(race_id: String):
	var race_data = catalog.races[race_id]
	var feral_name = race_data.name
	var before_name = race_data.get("before", "")
	var flavor = race_data.get("flavor", "No description available.")
	
	description_label.text = "[b]{feral}[/b]\n(Formerly [i]{before}[/i])\n\n{desc}".format({
		"feral": feral_name,
		"before": before_name,
		"desc": flavor
	})

func _on_race_selected(race_id: String):
	selection.race = race_id
	next_btn.disabled = false
	print("Selected Race: ", race_id)
	# TODO: Proceed to next step...

func _on_back_btn_pressed():
	get_tree().change_scene_to_file("res://scenes/UI_Overlay.tscn")
