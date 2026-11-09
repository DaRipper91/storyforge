@tool
extends CharacterBody3D
class_name RaceMini

@export var editor_race_id: String = "ashenborn":
	set(val):
		editor_race_id = val
		if Engine.is_editor_hint():
			setup(val, "", editor_is_enemy)

@export var editor_is_enemy: bool = false:
	set(val):
		editor_is_enemy = val
		if Engine.is_editor_hint():
			setup(editor_race_id, "", val)

## Player species render as a rigged CharacterModel when its base GLB loads; the primitive
## RACE_RECIPES below stay as the fallback (and as the look of anything that is not a race).
@export var use_character_models: bool = true

@onready var mesh_instance: MeshInstance3D = $MeshInstance3D
@onready var nav_agent: NavigationAgent3D = $NavigationAgent3D

const FlexibleToonShader = preload("res://addons/flexible_toon_shader/flexible_toon.gdshader")

var _material: ShaderMaterial
var move_speed: float = 5.0
var rotation_speed: float = 10.0
var _is_walking: bool = false
var _pulse_time: float = 0.0
var _selected: bool = false
var _phantom_cam: Node3D = null
var _model: Node3D = null            # GLB from ModelLibrary; null = primitive recipe
var _anim: AnimationPlayer = null
var _character: CharacterModel = null  # rigged species body; null = primitive recipe or ModelLibrary GLB
var _ring_mat: StandardMaterial3D = null

func _process(delta: float) -> void:
	if _selected and _material:
		_pulse_time += delta * 4.0
		var pulse = (sin(_pulse_time) + 1.0) * 0.5
		_material.set_shader_parameter("rim_width", lerp(4.0, 12.0, pulse))

# ─── DATA-DRIVEN SILHOUETTES ───
const RACE_RECIPES: Dictionary = {
	# COSMIC
	"voidwraith": [
		{"type": "sphere", "pos": Vector3(0, 1.2, 0), "scale": Vector3(0.6, 1.2, 0.6)},
		{"type": "box", "pos": Vector3(0.5, 1.0, 0.5), "rot": Vector3(0.7, 0.7, 0), "scale": Vector3(0.3, 0.3, 0.3)},
		{"type": "box", "pos": Vector3(-0.5, 1.4, -0.5), "rot": Vector3(-0.7, 0.4, 0.5), "scale": Vector3(0.25, 0.25, 0.25)},
		{"type": "box", "pos": Vector3(0, 0.6, 0), "rot": Vector3(PI/2, 0, 0), "scale": Vector3(0.5, 0.5, 0.5)}
	],
	"nullshade": [
		{"type": "cylinder", "pos": Vector3(0, 1.2, 0), "scale": Vector3(0.1, 2.4, 0.1)},
		{"type": "torus", "pos": Vector3(0, 2.2, 0), "rot": Vector3(PI/2, 0, 0), "scale": Vector3(0.4, 0.4, 0.4)}
	],
	"ironlocust": [
		{"type": "box", "pos": Vector3(0, 0.4, 0), "scale": Vector3(0.8, 0.4, 1.0)},
		{"type": "prism", "pos": Vector3(0.4, 0.6, 0.4), "rot": Vector3(1.2, 0.8, 0), "scale": Vector3(0.2, 1.2, 0.2)},
		{"type": "prism", "pos": Vector3(-0.4, 0.6, 0.4), "rot": Vector3(1.2, -0.8, 0), "scale": Vector3(0.2, 1.2, 0.2)},
		{"type": "prism", "pos": Vector3(0.4, 0.6, -0.4), "rot": Vector3(-1.2, 0.8, 0), "scale": Vector3(0.2, 1.2, 0.2)},
		{"type": "prism", "pos": Vector3(-0.4, 0.6, -0.4), "rot": Vector3(-1.2, -0.8, 0), "scale": Vector3(0.2, 1.2, 0.2)}
	],
	"embervein": [
		{"type": "box", "pos": Vector3(0, 0.6, 0), "scale": Vector3(1.0, 1.2, 0.8)},
		{"type": "box", "pos": Vector3(0.2, 1.2, 0.2), "rot": Vector3(0.4, 0.5, 0.2), "scale": Vector3(0.5, 0.5, 0.5)},
		{"type": "sphere", "pos": Vector3(-0.4, 1.4, -0.2), "scale": Vector3(0.2, 0.2, 0.2)}
	],
	"riftwalker": [
		{"type": "capsule", "pos": Vector3(0.3, 0.8, 0), "scale": Vector3(0.2, 1.6, 0.2)},
		{"type": "capsule", "pos": Vector3(-0.3, 0.8, 0), "scale": Vector3(0.2, 1.6, 0.2)},
		{"type": "cylinder", "pos": Vector3(0, 1.4, 0), "rot": Vector3(0, 0, PI/2), "scale": Vector3(0.02, 0.6, 0.02)}
	],
	# PRIMAL
	"solarlord": [
		{"type": "capsule", "pos": Vector3(0, 0.7, 0), "scale": Vector3(0.7, 1.4, 0.7)},
		{"type": "torus", "pos": Vector3(0, 1.5, -0.3), "rot": Vector3(PI/2, 0, 0), "scale": Vector3(0.8, 0.8, 0.8)},
		{"type": "prism", "pos": Vector3(0.6, 1.2, -0.2), "rot": Vector3(0.5, 0, 0.5), "scale": Vector3(0.2, 1.0, 0.1)},
		{"type": "prism", "pos": Vector3(-0.6, 1.2, -0.2), "rot": Vector3(0.5, 0, -0.5), "scale": Vector3(0.2, 1.0, 0.1)}
	],
	"thornmimic": [
		{"type": "prism", "pos": Vector3(0, 0.75, 0.3), "scale": Vector3(0.4, 1.5, 0.4)},
		{"type": "prism", "pos": Vector3(0.3, 0.75, -0.2), "rot": Vector3(0, 2.1, 0), "scale": Vector3(0.3, 1.2, 0.3)},
		{"type": "prism", "pos": Vector3(-0.3, 0.75, -0.2), "rot": Vector3(0, -2.1, 0), "scale": Vector3(0.3, 1.2, 0.3)}
	],
	"cinderkin": [
		{"type": "capsule", "pos": Vector3(0, 0.4, 0), "scale": Vector3(0.8, 0.8, 0.8)},
		{"type": "cone", "pos": Vector3(0, 1.2, 0), "scale": Vector3(0.6, 1.2, 0.6)}
	],
	"deeptyrant": [
		{"type": "sphere", "pos": Vector3(0, 1.2, 0), "scale": Vector3(0.8, 1.2, 1.2)},
		{"type": "cylinder", "pos": Vector3(0.4, 0.4, 0.4), "rot": Vector3(0.5, 0.8, 0), "scale": Vector3(0.1, 1.0, 0.1)},
		{"type": "cylinder", "pos": Vector3(-0.4, 0.4, 0.4), "rot": Vector3(0.5, -0.8, 0), "scale": Vector3(0.1, 1.0, 0.1)},
		{"type": "cylinder", "pos": Vector3(0, 0.4, -0.5), "rot": Vector3(-0.5, 0, 0), "scale": Vector3(0.1, 1.0, 0.1)}
	],
	"grimcrow": [
		{"type": "capsule", "pos": Vector3(0, 0.5, 0), "rot": Vector3(0.5, 0, 0), "scale": Vector3(0.6, 1.0, 0.6)},
		{"type": "cone", "pos": Vector3(0, 1.0, 0.4), "rot": Vector3(1.5, 0, 0), "scale": Vector3(0.1, 0.6, 0.1)},
		{"type": "prism", "pos": Vector3(0, 0.7, -0.2), "rot": Vector3(0.2, 0, 0), "scale": Vector3(1.2, 1.4, 0.1)}
	],
	# ELDRITCH
	"bloodweaver": [
		{"type": "sphere", "pos": Vector3(0, 1.6, 0), "scale": Vector3(0.6, 0.8, 0.6)},
		{"type": "cylinder", "pos": Vector3(0.4, 0.8, 0.4), "rot": Vector3(0.2, 0.8, 0), "scale": Vector3(0.05, 1.6, 0.05)},
		{"type": "cylinder", "pos": Vector3(-0.4, 0.8, 0.4), "rot": Vector3(0.2, -0.8, 0), "scale": Vector3(0.05, 1.6, 0.05)},
		{"type": "cylinder", "pos": Vector3(0, 0.8, -0.5), "rot": Vector3(-0.2, 0, 0), "scale": Vector3(0.05, 1.6, 0.05)}
	],
	"dreamhusk": [
		{"type": "cone", "pos": Vector3(0, 1.0, 0), "scale": Vector3(0.6, 1.8, 0.6)},
		{"type": "sphere", "pos": Vector3(0, 1.5, 0.2), "scale": Vector3(0.3, 0.1, 0.1)}
	],
	"bonedrifter": [
		{"type": "box", "pos": Vector3(0, 0.4, 0), "scale": Vector3(0.4, 0.2, 0.4)},
		{"type": "box", "pos": Vector3(0, 0.8, 0), "rot": Vector3(0, 0.4, 0), "scale": Vector3(0.4, 0.2, 0.4)},
		{"type": "box", "pos": Vector3(0, 1.2, 0), "rot": Vector3(0, 0.8, 0), "scale": Vector3(0.4, 0.2, 0.4)},
		{"type": "box", "pos": Vector3(0, 1.6, 0), "rot": Vector3(0, 1.2, 0), "scale": Vector3(0.4, 0.2, 0.4)},
		{"type": "box", "pos": Vector3(0, 2.2, 0), "scale": Vector3(0.5, 0.5, 0.5)}
	],
	"mindspider": [
		{"type": "sphere", "pos": Vector3(0, 1.4, 0), "scale": Vector3(1.2, 0.9, 1.2)},
		{"type": "cylinder", "pos": Vector3(0.3, 0.6, 0.3), "rot": Vector3(-0.3, 0.8, 0), "scale": Vector3(0.03, 1.2, 0.03)},
		{"type": "cylinder", "pos": Vector3(-0.3, 0.6, 0.3), "rot": Vector3(-0.3, -0.8, 0), "scale": Vector3(0.03, 1.2, 0.03)},
		{"type": "cylinder", "pos": Vector3(0, 0.6, -0.4), "rot": Vector3(0.3, 0, 0), "scale": Vector3(0.03, 1.2, 0.03)}
	],
	"chaosling": [
		{"type": "box", "pos": Vector3(0.2, 0.5, 0), "rot": Vector3(0.4, 0.2, 0.8), "scale": Vector3(0.4, 0.4, 0.4)},
		{"type": "sphere", "pos": Vector3(-0.2, 1.0, 0.2), "rot": Vector3(0.7, -0.5, 0), "scale": Vector3(0.5, 0.5, 0.5)},
		{"type": "prism", "pos": Vector3(0.1, 1.4, -0.2), "rot": Vector3(-0.2, 1.2, 0.4), "scale": Vector3(0.3, 0.6, 0.3)}
	],
	# MECHANICAL
	"ironveil": [
		{"type": "box", "pos": Vector3(0, 0.6, 0), "scale": Vector3(1.0, 1.2, 0.6)},
		{"type": "box", "pos": Vector3(0.65, 0.6, 0), "scale": Vector3(0.3, 0.8, 0.3)},
		{"type": "box", "pos": Vector3(-0.65, 0.6, 0), "scale": Vector3(0.3, 0.8, 0.3)}
	],
	"forgespawn": [
		{"type": "box", "pos": Vector3(0, 0.5, 0), "rot": Vector3(0.4, 0, 0), "scale": Vector3(0.7, 0.9, 0.7)},
		{"type": "box", "pos": Vector3(0.6, 0.6, 0.2), "scale": Vector3(0.5, 1.2, 0.5)},
		{"type": "box", "pos": Vector3(-0.5, 0.4, 0), "scale": Vector3(0.2, 0.6, 0.2)}
	],
	"cinderplate": [
		{"type": "cylinder", "pos": Vector3(0, 0.6, 0), "scale": Vector3(1.0, 1.2, 1.0)},
		{"type": "cylinder", "pos": Vector3(0.2, 1.5, -0.2), "scale": Vector3(0.2, 0.6, 0.2)},
		{"type": "cylinder", "pos": Vector3(-0.2, 1.5, -0.2), "scale": Vector3(0.2, 0.6, 0.2)}
	],
	"hexgear": [
		{"type": "torus", "pos": Vector3(0, 1.0, 0), "rot": Vector3(PI/2, 0, 0), "scale": Vector3(1.2, 1.2, 1.2)},
		{"type": "sphere", "pos": Vector3(0, 1.0, 0), "scale": Vector3(0.6, 0.6, 0.6)}
	],
	"wirewraith": [
		{"type": "cylinder", "pos": Vector3(0.1, 0.9, 0.1), "rot": Vector3(0, 0.4, 0.2), "scale": Vector3(0.04, 1.8, 0.04)},
		{"type": "cylinder", "pos": Vector3(-0.2, 0.9, 0.1), "rot": Vector3(0, 1.2, 0.2), "scale": Vector3(0.04, 1.8, 0.04)},
		{"type": "cylinder", "pos": Vector3(0.1, 0.9, -0.2), "rot": Vector3(0, 2.0, 0.2), "scale": Vector3(0.04, 1.8, 0.04)}
	],
	# HUMANOID VARIANTS
	"ashenborn": [
		{"type": "capsule", "pos": Vector3(0, 0.65, 0), "scale": Vector3(0.7, 1.3, 0.7)},
		{"type": "sphere", "pos": Vector3(0, 1.4, 0), "scale": Vector3(0.5, 0.5, 0.5)}
	],
	"hollowsong": [
		{"type": "capsule", "pos": Vector3(0, 0.75, 0), "scale": Vector3(0.5, 1.5, 0.5)},
		{"type": "prism", "pos": Vector3(0.3, 1.6, 0), "rot": Vector3(0, 0, -0.6), "scale": Vector3(0.1, 0.5, 0.3)},
		{"type": "prism", "pos": Vector3(-0.3, 1.6, 0), "rot": Vector3(0, 0, 0.6), "scale": Vector3(0.1, 0.5, 0.3)}
	],
	"veilborn": [
		{"type": "cone", "pos": Vector3(0, 0.8, 0), "scale": Vector3(1.0, 1.6, 1.0)}
	],
	"thornweft": [
		{"type": "capsule", "pos": Vector3(0, 0.65, 0), "scale": Vector3(0.7, 1.3, 0.7)},
		{"type": "torus", "pos": Vector3(0, 0.4, 0), "scale": Vector3(0.8, 0.1, 0.8)},
		{"type": "torus", "pos": Vector3(0, 0.8, 0), "scale": Vector3(0.8, 0.1, 0.8)},
		{"type": "torus", "pos": Vector3(0, 1.2, 0), "scale": Vector3(0.8, 0.1, 0.8)}
	],
	"ashcrown": [
		{"type": "capsule", "pos": Vector3(0, 0.65, 0), "scale": Vector3(0.7, 1.3, 0.7)},
		{"type": "cone", "pos": Vector3(0.2, 1.6, 0), "rot": Vector3(0, 0, -0.4), "scale": Vector3(0.05, 0.4, 0.05)},
		{"type": "cone", "pos": Vector3(-0.2, 1.6, 0), "rot": Vector3(0, 0, 0.4), "scale": Vector3(0.05, 0.4, 0.05)},
		{"type": "cone", "pos": Vector3(0, 1.6, 0.2), "rot": Vector3(0.4, 0, 0), "scale": Vector3(0.05, 0.4, 0.05)},
		{"type": "cone", "pos": Vector3(0, 1.6, -0.2), "rot": Vector3(-0.4, 0, 0), "scale": Vector3(0.05, 0.4, 0.05)}
	],
	"ironfast": [
		{"type": "box", "pos": Vector3(0, 0.5, 0), "scale": Vector3(0.7, 1.0, 0.3)},
		{"type": "box", "pos": Vector3(0, 1.2, 0), "scale": Vector3(0.5, 0.2, 0.2)}
	],
	"coreborn": [
		{"type": "capsule", "pos": Vector3(0, 0.65, 0), "scale": Vector3(0.7, 1.3, 0.7)},
		{"type": "box", "pos": Vector3(0, 0.9, 0), "rot": Vector3(0.7, 0.7, 0), "scale": Vector3(0.2, 0.2, 0.2)}
	],
	"warpbred": [
		{"type": "capsule", "pos": Vector3(0.1, 0.7, 0), "rot": Vector3(0, 0, 0.3), "scale": Vector3(0.6, 1.4, 0.6)},
		{"type": "box", "pos": Vector3(0.6, 0.8, 0), "rot": Vector3(0, 0, -0.2), "scale": Vector3(0.2, 1.0, 0.2)}
	],
	"splitblood": [
		{"type": "capsule", "pos": Vector3(0.2, 0.7, 0), "rot": Vector3(0, 0, -0.1), "scale": Vector3(0.4, 1.4, 0.4)},
		{"type": "capsule", "pos": Vector3(-0.2, 0.7, 0), "rot": Vector3(0, 0, 0.1), "scale": Vector3(0.4, 1.4, 0.4)}
	],
	"duskweft": [
		{"type": "capsule", "pos": Vector3(0, 0.65, 0), "scale": Vector3(0.7, 1.3, 0.7)},
		{"type": "prism", "pos": Vector3(0, 0.8, -0.3), "rot": Vector3(0.1, 0, 0), "scale": Vector3(1.0, 1.6, 0.1)}
	],
	"glitchkin": [
		{"type": "box", "pos": Vector3(0, 0.3, 0), "scale": Vector3(0.4, 0.4, 0.4)},
		{"type": "box", "pos": Vector3(0.1, 0.7, 0.1), "scale": Vector3(0.4, 0.4, 0.4)},
		{"type": "box", "pos": Vector3(-0.1, 1.1, -0.1), "scale": Vector3(0.4, 0.4, 0.4)},
		{"type": "box", "pos": Vector3(0.1, 1.5, 0), "scale": Vector3(0.4, 0.4, 0.4)}
	],
	"fractureline": [
		{"type": "box", "pos": Vector3(0, 0.3, 0), "scale": Vector3(0.7, 0.7, 0.7)},
		{"type": "box", "pos": Vector3(0.2, 0.9, 0.1), "rot": Vector3(0, 0.5, 0), "scale": Vector3(0.6, 0.6, 0.6)},
		{"type": "box", "pos": Vector3(-0.1, 1.5, -0.2), "rot": Vector3(0.3, 0, 0.3), "scale": Vector3(0.5, 0.5, 0.5)}
	],
	"emberpact": [
		{"type": "capsule", "pos": Vector3(0, 0.65, 0), "scale": Vector3(0.7, 1.3, 0.7)},
		{"type": "cylinder", "pos": Vector3(0, 0.4, -0.5), "rot": Vector3(-1.2, 0, 0), "scale": Vector3(0.1, 1.0, 0.1)},
		{"type": "cone", "pos": Vector3(0, 1.6, 0.1), "rot": Vector3(0.5, 0, 0), "scale": Vector3(0.1, 0.6, 0.1)}
	],
	"fallenlight": [
		{"type": "capsule", "pos": Vector3(0, 0.65, 0), "scale": Vector3(0.7, 1.3, 0.7)},
		{"type": "box", "pos": Vector3(0.4, 1.0, -0.2), "rot": Vector3(0, -0.3, 0.2), "scale": Vector3(0.1, 1.8, 0.6)},
		{"type": "box", "pos": Vector3(-0.4, 1.0, -0.2), "rot": Vector3(0, 0.3, -0.2), "scale": Vector3(0.1, 1.8, 0.6)}
	],
	"scaleworn": [
		{"type": "capsule", "pos": Vector3(0, 0.5, 0), "rot": Vector3(0.5, 0, 0), "scale": Vector3(0.8, 1.0, 0.8)},
		{"type": "cylinder", "pos": Vector3(0, 0.2, -0.8), "rot": Vector3(-1.0, 0, 0), "scale": Vector3(0.2, 1.2, 0.2)}
	],
	"humanoid_default": [
		{"type": "capsule", "pos": Vector3(0, 0.65, 0), "scale": Vector3(0.7, 1.3, 0.7)},
		{"type": "sphere", "pos": Vector3(0, 1.4, 0), "scale": Vector3(0.5, 0.5, 0.5)}
	]
}

const RACE_COLORS: Dictionary = {
	"voidwraith":  Color(0.1, 0.05, 0.4), "nullshade":   Color(0.05, 0.05, 0.05),
	"ironlocust":  Color(0.3, 0.3, 0.4), "embervein":   Color(0.9, 0.2, 0.0),
	"riftwalker":  Color(0.5, 0.0, 0.8), "solarlord":   Color(1.0, 0.8, 0.2),
	"thornmimic":  Color(0.1, 0.4, 0.1), "cinderkin":   Color(1.0, 0.4, 0.0),
	"deeptyrant":  Color(0.0, 0.2, 0.5), "grimcrow":    Color(0.1, 0.1, 0.15),
	"bloodweaver": Color(0.7, 0.0, 0.1), "dreamhusk":   Color(0.6, 0.4, 0.9),
	"bonedrifter": Color(0.95, 0.9, 0.8), "mindspider":  Color(0.4, 0.1, 0.6),
	"chaosling":   Color(0.2, 0.9, 1.0), "ironveil":    Color(0.5, 0.5, 0.6),
	"forgespawn":  Color(0.6, 0.3, 0.1), "cinderplate": Color(0.2, 0.2, 0.2),
	"hexgear":     Color(0.8, 0.6, 0.0), "wirewraith":  Color(0.0, 0.9, 0.7),
	"ashenborn":   Color(0.5, 0.5, 0.6), "hollowsong":  Color(0.4, 0.6, 1.0),
	"veilborn":    Color(0.3, 0.0, 0.4), "thornweft":   Color(0.4, 0.6, 0.2),
	"ashcrown":    Color(0.9, 0.8, 0.4), "ironfast":    Color(0.6, 0.6, 0.7),
	"coreborn":    Color(0.3, 0.8, 1.0), "warpbred":    Color(0.7, 0.3, 0.8),
	"splitblood":  Color(0.8, 0.1, 0.2), "duskweft":    Color(0.3, 0.2, 0.5),
	"glitchkin":   Color(0.0, 1.0, 0.6), "fractureline":Color(0.8, 0.8, 0.9),
	"emberpact":   Color(1.0, 0.6, 0.0), "fallenlight": Color(0.95, 0.95, 1.0),
	"scaleworn":   Color(0.4, 0.7, 0.1)
}

func _ready() -> void:
	_init_material()
	_setup_phantom_camera()
	if Engine.is_editor_hint():
		setup(editor_race_id, "", editor_is_enemy)

func _setup_phantom_camera() -> void:
	if Engine.is_editor_hint(): return
	# Create a PhantomCamera3D node
	_phantom_cam = Node3D.new()
	_phantom_cam.set_script(load("res://addons/phantom_camera/scripts/phantom_camera/phantom_camera_3d.gd"))
	_phantom_cam.name = "SelectionPhantomCamera"
	add_child(_phantom_cam)

	# Configure it
	_phantom_cam.set("priority", 0)
	_phantom_cam.set("follow_mode", 2) # Third Person
	_phantom_cam.set("look_at_mode", 1) # Simple
	_phantom_cam.set("follow_target", self)
	_phantom_cam.set("look_at_target", self)

	# Nice cinematic offset
	_phantom_cam.set("third_person_distance", 4.0)
	_phantom_cam.set("third_person_tilt", -20.0)
func _init_material() -> void:
	if _material: return
	_material = ShaderMaterial.new()
	_material.shader = FlexibleToonShader
	_material.set_shader_parameter("albedo", Color(1.0, 1.0, 1.0))
	_material.set_shader_parameter("rim_color", Color(1.0, 1.0, 1.0))
	_material.set_shader_parameter("rim_width", 2.0)
	_material.set_shader_parameter("cuts", 3)
	_material.set_shader_parameter("steepness", 1.5)
	_material.set_shader_parameter("use_rim", true)
	if mesh_instance:
		mesh_instance.material_override = _material
func setup(race_id: String, entity_name: String = "", is_enemy: bool = false) -> void:
	if not mesh_instance: 
		mesh_instance = get_node_or_null("MeshInstance3D")
	if not mesh_instance: return

	_init_material()
	
	race_id = race_id.to_lower().replace(" ", "_")
	if _character != null and is_instance_valid(_character) and _character.race_id == race_id \
			and _character.get_parent() == mesh_instance:
		return  # same species already showing (the creation preview re-selects on every hover)
	mesh_instance.mesh = null
	for child in mesh_instance.get_children(): child.queue_free()
	_model = null
	_anim = null
	_character = null
	var old_ring := get_node_or_null("IdentityRing")
	if old_ring:
		old_ring.queue_free()
		_ring_mat = null
	
	var color: Color = RACE_COLORS.get(race_id, Color(0.3, 0.5, 0.8))
	if is_enemy and not race_id in RACE_COLORS: color = Color(0.8, 0.2, 0.2)

	if _try_character(race_id, color, is_enemy):
		return
	if _try_creature(race_id, is_enemy):
		return

	var recipe: Array = RACE_RECIPES.get(race_id, RACE_RECIPES["humanoid_default"])
	for part in recipe: _add_recipe_part(part)
	
	if _material:
		_material.set_shader_parameter("albedo", color)
		_material.set_shader_parameter("rim_color", color * 1.2)
		_material.set_shader_parameter("rim_width", 2.0)

## Swaps in the rigged species body. Returns false (primitives stay) for ids that are not
## player species, in the editor, or when the base GLB cannot be loaded.
func _try_character(race_id: String, color: Color, is_enemy: bool) -> bool:
	if not use_character_models or Engine.is_editor_hint():
		return false
	if not CharacterModel.is_known_race(race_id):
		return false
	var cm := CharacterModel.new()
	cm.name = "Character"
	if not cm.setup(race_id):
		cm.free()
		return false
	mesh_instance.add_child(cm)
	_character = cm
	_model = cm
	if not is_enemy:
		# The group glow colour (blended with the race colour): bright enough to read on a dark floor.
		_add_identity_ring(CharacterModel.colours_for(race_id)["accent"])
	# RaceMini's own movement code looks along -Z; a fresh token faces the default camera (+Z side).
	if transform.basis.is_equal_approx(Basis.IDENTITY):
		rotation.y = PI
	return true

## Standing height of non-humanoid heroes (length is whatever the model's proportions give).
const CREATURE_HEIGHTS := {
	"ironlocust": 0.62,
	"mindspider": 0.62,
}

## Swaps in a hand-modelled creature that brings its own skeleton and Idle/Walk/Hit/Death clips.
func _try_creature(race_id: String, is_enemy: bool) -> bool:
	if not use_character_models or Engine.is_editor_hint():
		return false
	if not CharacterModel.is_known_race(race_id) or CharacterModel.hero_path(race_id).is_empty():
		return false
	var model := ModelLibrary.instantiate_hero(race_id, CREATURE_HEIGHTS.get(race_id, 0.9))
	if model == null:
		return false
	use_model(model, CharacterModel.colours_for(race_id)["accent"], not is_enemy)
	if transform.basis.is_equal_approx(Basis.IDENTITY):
		rotation.y = PI
	return true

func has_character() -> bool:
	return _character != null

## Turns a character-model token to face `dir` (ground-plane direction). No-op for primitives.
func face_direction(dir: Vector3) -> void:
	if _character == null:
		return
	dir.y = 0.0
	if dir.length_squared() < 0.0001:
		return
	quaternion = Quaternion(Basis.looking_at(dir.normalized()))

## Bounds of the visible token in this node's local space (feet at y = 0 for characters),
## used to auto-frame previews. Characters report a standing-body box, not the T-pose mesh box.
func get_visual_aabb() -> AABB:
	if _character != null:
		return _character.get_body_aabb()
	var acc := {"found": false, "box": AABB()}
	if mesh_instance:
		_accumulate_aabb(mesh_instance, Transform3D.IDENTITY, acc)
	if not acc["found"]:
		return AABB(Vector3(-0.4, 0.0, -0.4), Vector3(0.8, 1.6, 0.8))
	return acc["box"]

static func _accumulate_aabb(node: Node, parent_xform: Transform3D, acc: Dictionary) -> void:
	for child in node.get_children():
		var xform := parent_xform
		if child is Node3D:
			xform = parent_xform * (child as Node3D).transform
		if child is VisualInstance3D:
			var b: AABB = xform * (child as VisualInstance3D).get_aabb()
			if acc["found"]:
				acc["box"] = (acc["box"] as AABB).merge(b)
			else:
				acc["box"] = b
				acc["found"] = true
		_accumulate_aabb(child, xform, acc)

## Recolors the primitive recipe (used for NPCs, whose sprite_key isn't a race).
func set_tint(color: Color) -> void:
	if _character:
		_character.tint = color
	if _material:
		_material.set_shader_parameter("albedo", color)
		_material.set_shader_parameter("rim_color", color * 1.2)
	if _ring_mat:
		_ring_mat.emission = color

## Swaps the primitive recipe for a GLB from ModelLibrary. The token keeps its
## collision, navigation, Interactable and camera; only the visuals change.
## A thin ring in `identity_color` stands in for the toon rim, which GLBs lack.
func use_model(model: Node3D, identity_color: Color, show_ring: bool = true) -> void:
	if not mesh_instance or model == null:
		return
	for child in mesh_instance.get_children(): child.queue_free()
	mesh_instance.add_child(model)
	_model = model
	_character = null
	_anim = ModelLibrary.find_anim_player(model)
	if show_ring:
		_add_identity_ring(identity_color)
	play_idle()

func has_model() -> bool:
	return _model != null

func play_idle() -> void:
	if _character:
		_character.set_walking(false)
		return
	if _anim:
		ModelLibrary.play_role(_anim, "idle")

func play_talk() -> void:
	if _character:
		_character.play(HumanoidAnimLibrary.CLIP_INTERACT)
		return
	if _anim and not ModelLibrary.play_role(_anim, "talk"):
		play_idle()

func play_hit() -> void:
	if _character:
		_character.play(HumanoidAnimLibrary.CLIP_HIT)
	elif _anim and ModelLibrary.play_role(_anim, "hit"):
		var idle := ModelLibrary.find_clip(_anim, "idle")
		if not idle.is_empty():
			_anim.queue(idle)   # flinch once, then back to breathing

func play_death() -> void:
	if _character:
		_character.play(HumanoidAnimLibrary.CLIP_DEATH)
	elif _anim:
		ModelLibrary.play_role(_anim, "death")

func _add_identity_ring(color: Color) -> void:
	var old := get_node_or_null("IdentityRing")
	if old:
		old.queue_free()
	var ring := MeshInstance3D.new()
	ring.name = "IdentityRing"
	var torus := TorusMesh.new()
	torus.inner_radius = 0.30
	torus.outer_radius = 0.34
	ring.mesh = torus
	_ring_mat = StandardMaterial3D.new()
	_ring_mat.albedo_color = color
	_ring_mat.emission_enabled = true
	_ring_mat.emission = color
	_ring_mat.emission_energy_multiplier = 0.6
	ring.material_override = _ring_mat
	ring.position = Vector3(0, 0.02, 0)
	ring.scale = Vector3(1, 0.25, 1)
	add_child(ring)

func _add_recipe_part(data: Dictionary) -> void:
	var mesh: Mesh
	match data.get("type", "box"):
		"box":      mesh = BoxMesh.new()
		"sphere":   mesh = SphereMesh.new()
		"capsule":  mesh = CapsuleMesh.new()
		"cylinder": mesh = CylinderMesh.new()
		"cone":     
			mesh = CylinderMesh.new()
			mesh.top_radius = 0.0
		"torus":    mesh = TorusMesh.new()
		"prism":    mesh = PrismMesh.new()
	if mesh:
		var mi := MeshInstance3D.new()
		mi.mesh = mesh
		mi.material_override = _material
		mi.position = data.get("pos", Vector3.ZERO)
		mi.rotation = data.get("rot", Vector3.ZERO)
		mi.scale    = data.get("scale", Vector3.ONE)
		mesh_instance.add_child(mi)

func select() -> void:
	_selected = true
	if _character:
		_character.highlighted = true
	if _phantom_cam:
		_phantom_cam.set("priority", 20)
	if _material:
		_material.set_shader_parameter("rim_color", Color(1.0, 0.9, 0.3))
		_material.set_shader_parameter("rim_width", 8.0)
	if _ring_mat:
		_ring_mat.emission_energy_multiplier = 2.5

func deselect() -> void:
	_selected = false
	if _character:
		_character.highlighted = false
	if _phantom_cam:
		_phantom_cam.set("priority", 0)
	if _material:
		_material.set_shader_parameter("rim_width", 2.0)
		var base_color = _material.get_shader_parameter("albedo")
		if base_color:
			_material.set_shader_parameter("rim_color", base_color * 1.2)
	if _ring_mat:
		_ring_mat.emission_energy_multiplier = 0.6

func play_walk() -> void:
	if _character:
		_character.set_walking(true)
		return
	if _anim and ModelLibrary.play_role(_anim, "walk"):
		return
	if _is_walking: return
	_is_walking = true
	var tw := create_tween()
	tw.tween_property(mesh_instance, "position:y", 0.15, 0.1).set_trans(Tween.TRANS_SINE)
	tw.tween_property(mesh_instance, "position:y", 0.0, 0.1).set_trans(Tween.TRANS_SINE)
	tw.finished.connect(func(): _is_walking = false)

func move_with_input(input_dir: Vector3, delta: float, look_at_pos: Vector3 = Vector3.ZERO) -> void:
	if input_dir.length() > 0.1:
		velocity = input_dir * move_speed
		var target_quat: Quaternion
		if look_at_pos != Vector3.ZERO:
			var dir_to_target = global_position.direction_to(look_at_pos)
			dir_to_target.y = 0
			if dir_to_target.length_squared() > 0.01:
				target_quat = Quaternion(Basis.looking_at(dir_to_target))
			else:
				target_quat = Quaternion(Basis.looking_at(input_dir))
		else:
			target_quat = Quaternion(Basis.looking_at(input_dir))
		quaternion = quaternion.slerp(target_quat, rotation_speed * delta)
		play_walk()
	else:
		velocity = velocity.move_toward(Vector3.ZERO, move_speed * 10.0 * delta)
		play_idle()
		if look_at_pos != Vector3.ZERO:
			var dir_to_target = global_position.direction_to(look_at_pos)
			dir_to_target.y = 0
			if dir_to_target.length_squared() > 0.01:
				var target_quat = Quaternion(Basis.looking_at(dir_to_target))
				quaternion = quaternion.slerp(target_quat, rotation_speed * delta)
	move_and_slide()

func move_towards_target(delta: float) -> void:
	if nav_agent.is_navigation_finished():
		velocity = velocity.move_toward(Vector3.ZERO, move_speed * 10.0 * delta)
		play_idle()
		move_and_slide()
		return
	var next_path_pos = nav_agent.get_next_path_position()
	var dir = global_position.direction_to(next_path_pos)
	dir.y = 0
	dir = dir.normalized()
	velocity = dir * move_speed
	if dir.length() > 0.1:
		var target_quat = Quaternion(Basis.looking_at(dir))
		quaternion = quaternion.slerp(target_quat, rotation_speed * delta)
		play_walk()
	move_and_slide()
