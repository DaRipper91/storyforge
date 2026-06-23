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

@onready var mesh_instance: MeshInstance3D = $MeshInstance3D
@onready var nav_agent: NavigationAgent3D = $NavigationAgent3D

const FlexibleToonShader = preload("res://addons/flexible_toon_shader/flexible_toon.gdshader")
const NeonOutlineShader = preload("res://shaders/neon_outline.gdshader")

static var use_true_3d: bool = false

const NEON_COLORS: Dictionary = {
	"cosmic": Color(0.0, 1.0, 1.0),
	"primal": Color(0.2, 1.0, 0.2),
	"eldritch": Color(1.0, 0.1, 0.1),
	"mechanical": Color(1.0, 0.6, 0.0),
	"humanoid": Color(0.0, 0.5, 1.0)
}

var _material: ShaderMaterial
var move_speed: float = 5.0
var rotation_speed: float = 10.0
var _is_walking: bool = false
var _pulse_time: float = 0.0
var _selected: bool = false
var _race_id: String = ""
var _is_enemy: bool = false
var _phantom_cam: Node3D = null
var _anim_player: AnimationPlayer = null

func _process(delta: float) -> void:
	if _selected and _material:
		_pulse_time += delta * 4.0
		var pulse = (sin(_pulse_time) + 1.0) * 0.5
		if _material.shader == FlexibleToonShader:
			_material.set_shader_parameter("rim_width", lerp(4.0, 12.0, pulse))
		else:
			_material.set_shader_parameter("outline_width", lerp(1.5, 4.0, pulse))
			_material.set_shader_parameter("glow_intensity", lerp(2.0, 6.0, pulse))

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

func _get_faction_group(clean_id: String) -> String:
	if clean_id in ["voidwraith", "nullshade", "ironlocust", "embervein", "riftwalker"]:
		return "cosmic"
	elif clean_id in ["solarlord", "thornmimic", "cinderkin", "deeptyrant", "grimcrow"]:
		return "primal"
	elif clean_id in ["bloodweaver", "dreamhusk", "bonedrifter", "mindspider", "chaosling"]:
		return "eldritch"
	elif clean_id in ["ironveil", "forgespawn", "cinderplate", "hexgear", "wirewraith"]:
		return "mechanical"
	return "humanoid"

func _create_miniature_base(clean_race_id: String) -> void:
	var old_base = get_node_or_null("MiniatureBase")
	if old_base:
		old_base.name = "OldBase"
		old_base.queue_free()
		
	var faction = _get_faction_group(clean_race_id)
	var base_mi := MeshInstance3D.new()
	base_mi.name = "MiniatureBase"
	
	# Base mesh configuration based on faction
	var base_mesh: Mesh
	var base_mat := StandardMaterial3D.new()
	
	# Default dimensions
	var height = 0.08
	var radius = 0.5
	
	match faction:
		"cosmic":
			# Cosmic: Ethereal runic disk
			var cyl = CylinderMesh.new()
			cyl.height = height
			cyl.top_radius = radius
			cyl.bottom_radius = radius
			cyl.radial_segments = 32
			base_mesh = cyl
			
			base_mat.albedo_color = Color(0.05, 0.02, 0.15) # Deep cosmic void
			base_mat.roughness = 0.2
			base_mat.metallic = 0.5
			base_mat.emission_enabled = true
			base_mat.emission = Color(0.0, 0.8, 1.0) # Glowing neon cyan runic ring glow
			base_mat.emission_energy_multiplier = 2.0
			
		"primal":
			# Primal: Wooden/vine organic decagon
			var cyl = CylinderMesh.new()
			cyl.height = height
			cyl.top_radius = radius
			cyl.bottom_radius = radius * 1.1 # Bevelled
			cyl.radial_segments = 10 # Rough decagon
			base_mesh = cyl
			
			base_mat.albedo_color = Color(0.3, 0.2, 0.1) # Dark wood
			base_mat.roughness = 0.95
			base_mat.metallic = 0.0
			base_mat.emission_enabled = true
			base_mat.emission = Color(0.1, 0.6, 0.1)
			base_mat.emission_energy_multiplier = 0.5
			
		"eldritch":
			# Eldritch: Parasitic bone ring (torus)
			var tor = TorusMesh.new()
			tor.outer_radius = radius
			tor.inner_radius = radius * 0.75
			tor.ring_segments = 12
			tor.radial_segments = 16
			base_mesh = tor
			base_mi.scale = Vector3(1.0, 0.12 / 2.0, 1.0)
			height = 0.06
			
			base_mat.albedo_color = Color(0.85, 0.8, 0.7) # Bone white
			base_mat.roughness = 0.8
			base_mat.metallic = 0.0
			base_mat.emission_enabled = true
			base_mat.emission = Color(0.7, 0.0, 0.5)
			base_mat.emission_energy_multiplier = 1.0
			
		"mechanical":
			# Mechanical: Metallic gear
			var cyl = CylinderMesh.new()
			cyl.height = height
			cyl.top_radius = radius
			cyl.bottom_radius = radius
			cyl.radial_segments = 16
			base_mesh = cyl
			
			base_mat.albedo_color = Color(0.55, 0.45, 0.35) # Brass/copper
			base_mat.roughness = 0.4
			base_mat.metallic = 1.0
			base_mat.emission_enabled = true
			base_mat.emission = Color(1.0, 0.4, 0.0)
			base_mat.emission_energy_multiplier = 1.2
			
			# Procedural gear teeth
			var teeth_count = 8
			for i in range(teeth_count):
				var tooth := MeshInstance3D.new()
				var tooth_mesh := BoxMesh.new()
				tooth_mesh.size = Vector3(0.12, height, 0.1)
				tooth.mesh = tooth_mesh
				tooth.material_override = base_mat
				
				var angle = i * (2.0 * PI / teeth_count)
				tooth.position = Vector3(cos(angle) * (radius - 0.02), 0, sin(angle) * (radius - 0.02))
				tooth.rotation.y = -angle
				base_mi.add_child(tooth)
				
		_:
			# Humanoid / Default: Matte black bevelled plastic cylinder
			var cyl = CylinderMesh.new()
			cyl.height = height
			cyl.top_radius = radius
			cyl.bottom_radius = radius * 1.08
			cyl.radial_segments = 32
			base_mesh = cyl
			
			base_mat.albedo_color = Color(0.15, 0.15, 0.18)
			base_mat.roughness = 0.6
			base_mat.metallic = 0.1
			base_mat.emission_enabled = true
			base_mat.emission = Color(0.8, 0.6, 0.2)
			base_mat.emission_energy_multiplier = 0.4
			
	base_mi.mesh = base_mesh
	base_mi.material_override = base_mat
	
	base_mi.position = Vector3(0, height / 2.0, 0)
	add_child(base_mi)
	
	mesh_instance.position = Vector3(0, height, 0)

func setup(race_id: String, entity_name: String = "", is_enemy: bool = false) -> void:
	if not mesh_instance: 
		mesh_instance = get_node_or_null("MeshInstance3D")
	if not mesh_instance: return

	_init_material()
	
	_race_id = race_id
	_is_enemy = is_enemy
	
	var clean_race_id = race_id.to_lower().replace(" ", "").replace("_", "").replace("-", "")
	mesh_instance.mesh = null
	for child in mesh_instance.get_children(): child.queue_free()
	_anim_player = null

	# Create miniature base
	_create_miniature_base(clean_race_id)

	# Clear/Hide Sprite3D since we are using 3D meshes
	var sprite = get_node_or_null("Sprite3D") as Sprite3D
	if sprite:
		sprite.visible = false

	var model_loaded = false

	if use_true_3d:
		# Try GLB first, then fall back to OBJ
		model_loaded = _load_glb_model(clean_race_id, race_id)
		if not model_loaded:
			model_loaded = _load_obj_standee(clean_race_id)
	else:
		# Try OBJ first, then fall back to GLB
		model_loaded = _load_obj_standee(clean_race_id)
		if not model_loaded:
			model_loaded = _load_glb_model(clean_race_id, race_id)

	# 3. Fallback: Data-driven Recipe shapes
	if not model_loaded:
		mesh_instance.visible = true
		var recipe: Array = RACE_RECIPES.get(clean_race_id, RACE_RECIPES["humanoid_default"])
		for part in recipe: _add_recipe_part(part)
		
		var color: Color = RACE_COLORS.get(clean_race_id, Color(0.3, 0.5, 0.8))
		if is_enemy and not clean_race_id in RACE_COLORS: color = Color(0.8, 0.2, 0.2)
		
		if _material:
			mesh_instance.material_override = _material
			_material.set_shader_parameter("albedo", color)
			_material.set_shader_parameter("rim_color", color * 1.2)
			_material.set_shader_parameter("rim_width", 2.0)

func _load_obj_standee(clean_race_id: String) -> bool:
	var obj_path = "res://assets/models/player/" + clean_race_id + ".obj"
	if FileAccess.file_exists(obj_path):
		var mesh = ResourceLoader.load(obj_path, "Mesh", ResourceLoader.CACHE_MODE_IGNORE) as Mesh
		if mesh:
			mesh_instance.mesh = mesh
			mesh_instance.visible = true
			
			var tex: Texture2D = null
			var active_mat = mesh_instance.get_active_material(0)
			if active_mat is StandardMaterial3D:
				tex = active_mat.albedo_texture
			if not tex and mesh.get_surface_count() > 0:
				var surf_mat = mesh.surface_get_material(0)
				if surf_mat is StandardMaterial3D:
					tex = surf_mat.albedo_texture
			
			if not tex:
				var png_path = "res://assets/characters/" + clean_race_id + ".png"
				if FileAccess.file_exists(png_path):
					tex = ResourceLoader.load(png_path, "Texture2D", ResourceLoader.CACHE_MODE_IGNORE)
			
			if tex:
				_material = ShaderMaterial.new()
				_material.shader = NeonOutlineShader
				_material.set_shader_parameter("albedo_texture", tex)
				
				var faction = _get_faction_group(clean_race_id)
				var neon_col = NEON_COLORS.get(faction, Color(0.0, 1.0, 1.0))
				_material.set_shader_parameter("outline_color", neon_col)
				_material.set_shader_parameter("outline_width", 2.0)
				_material.set_shader_parameter("glow_intensity", 2.0)
				_material.set_shader_parameter("alpha_threshold", 0.1)
				_material.set_shader_parameter("flash_ratio", 0.0)
				mesh_instance.material_override = _material
			else:
				mesh_instance.material_override = null
			
			mesh_instance.scale = Vector3(1.0, 1.0, 1.0)
			mesh_instance.rotation = Vector3.ZERO
			return true
	return false

func _load_glb_model(clean_race_id: String, race_id: String) -> bool:
	var group = _get_faction_group(clean_race_id)

	var registry_path = "res://assets/models/races/asset_registry.json"
	var registry = {}
	if FileAccess.file_exists(registry_path):
		var file = FileAccess.open(registry_path, FileAccess.READ)
		var json_str = file.get_as_text()
		var parsed = JSON.parse_string(json_str)
		if parsed is Dictionary:
			registry = parsed

	var model_path = "res://assets/models/player/" + race_id.to_lower().replace(" ", "_") + ".glb"
	var custom_scale = Vector3(1.0, 1.0, 1.0)
	var custom_rotation = Vector3.ZERO

	if not registry.is_empty() and registry.has(clean_race_id):
		var race_entry = registry[clean_race_id]
		if race_entry is Dictionary:
			if race_entry.has("model_path"):
				model_path = race_entry["model_path"]
			if race_entry.has("scale"):
				var sc = race_entry["scale"]
				if sc is Array and sc.size() == 3:
					custom_scale = Vector3(sc[0], sc[1], sc[2])
				elif sc is float or sc is int:
					custom_scale = Vector3(sc, sc, sc)
			if race_entry.has("rotation"):
				var rot = race_entry["rotation"]
				if rot is Array and rot.size() == 3:
					custom_rotation = Vector3(deg_to_rad(rot[0]), deg_to_rad(rot[1]), deg_to_rad(rot[2]))

	if not FileAccess.file_exists(model_path):
		model_path = "res://assets/models/player/" + group + ".glb"

	if FileAccess.file_exists(model_path):
		var model_scene = load(model_path)
		if model_scene:
			mesh_instance.material_override = null
			var model_instance = model_scene.instantiate()
			mesh_instance.add_child(model_instance)
			
			model_instance.scale = custom_scale
			model_instance.rotation = custom_rotation
			
			var anim_player = model_instance.get_node_or_null("AnimationPlayer")
			if anim_player:
				_anim_player = anim_player
				_play_anim("Idle")
			return true
	return false

func _play_anim(anim_name: String) -> void:
	if not _anim_player: return
	
	var variations = []
	if anim_name == "Idle":
		variations = ["Idle", "Idle_A", "Standing", "idle", "standing"]
	elif anim_name == "Walk":
		variations = ["Walking", "Walk", "Walk_A", "walk", "walking"]
		
	for var_name in variations:
		if _anim_player.has_animation(var_name):
			if _anim_player.current_animation != var_name:
				_anim_player.play(var_name)
			return

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
	if _phantom_cam:
		_phantom_cam.set("priority", 20)
	if _material:
		if _material.shader == FlexibleToonShader:
			_material.set_shader_parameter("rim_color", Color(1.0, 0.9, 0.3))
			_material.set_shader_parameter("rim_width", 8.0)
		else:
			_material.set_shader_parameter("glow_intensity", 5.0)

func deselect() -> void:
	_selected = false
	if _phantom_cam:
		_phantom_cam.set("priority", 0)
	if _material:
		if _material.shader == FlexibleToonShader:
			_material.set_shader_parameter("rim_width", 2.0)
			var base_color = _material.get_shader_parameter("albedo")
			if base_color:
				_material.set_shader_parameter("rim_color", base_color * 1.2)
		else:
			_material.set_shader_parameter("glow_intensity", 2.0)
			_material.set_shader_parameter("outline_width", 2.0)

func play_walk() -> void:
	if _anim_player:
		_play_anim("Walk")
		return
	if _is_walking: return
	_is_walking = true
	var visual = mesh_instance
	var base_y = mesh_instance.position.y
	var tw := create_tween()
	tw.tween_property(visual, "position:y", base_y + 0.15, 0.1).set_trans(Tween.TRANS_SINE)
	tw.tween_property(visual, "position:y", base_y, 0.1).set_trans(Tween.TRANS_SINE)
	tw.finished.connect(func(): _is_walking = false)

func play_idle() -> void:
	if _anim_player:
		_play_anim("Idle")

func play_attack() -> void:
	if _anim_player:
		_play_anim("Walk") # Or attack if we map it
		return
	
	var forward_dir = -global_transform.basis.z.normalized()
	forward_dir.y = 0
	forward_dir = forward_dir.normalized()
	
	var original_pos = mesh_instance.position
	var original_rot = mesh_instance.rotation
	
	var tween = create_tween()
	# Slide forward fast
	tween.tween_property(mesh_instance, "position", original_pos + forward_dir * 0.6 + Vector3(0, 0.1, 0), 0.1).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	tween.parallel().tween_property(mesh_instance, "rotation:x", original_rot.x - 0.15, 0.1)
	
	# Slam back
	tween.tween_property(mesh_instance, "position", original_pos, 0.12).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN)
	tween.parallel().tween_property(mesh_instance, "rotation:x", original_rot.x, 0.12)

func play_damage() -> void:
	# Damage wiggle
	var original_pos = mesh_instance.position
	var original_rot = mesh_instance.rotation
	
	var tween = create_tween()
	# Fast wiggle and shake
	tween.tween_property(mesh_instance, "position:x", original_pos.x + 0.12, 0.04).set_trans(Tween.TRANS_SINE)
	tween.parallel().tween_property(mesh_instance, "rotation:z", original_rot.z - 0.1, 0.04)
	
	tween.tween_property(mesh_instance, "position:x", original_pos.x - 0.12, 0.04).set_trans(Tween.TRANS_SINE)
	tween.parallel().tween_property(mesh_instance, "rotation:z", original_rot.z + 0.1, 0.04)
	
	tween.tween_property(mesh_instance, "position:x", original_pos.x, 0.04).set_trans(Tween.TRANS_SINE)
	tween.parallel().tween_property(mesh_instance, "rotation:z", original_rot.z, 0.04)
	
	_flash_red()

func _flash_red() -> void:
	if not _material: return
	
	var tween = create_tween()
	if _material.shader == FlexibleToonShader:
		var orig_albedo = _material.get_shader_parameter("albedo")
		if orig_albedo == null: orig_albedo = Color(1.0, 1.0, 1.0)
		_material.set_shader_parameter("albedo", Color(1.0, 0.0, 0.0))
		tween.tween_method(func(c): _material.set_shader_parameter("albedo", c), Color(1.0, 0.0, 0.0), orig_albedo, 0.2)
	else:
		_material.set_shader_parameter("flash_ratio", 1.0)
		tween.tween_method(func(v): _material.set_shader_parameter("flash_ratio", v), 1.0, 0.0, 0.25)

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
		if look_at_pos != Vector3.ZERO:
			var dir_to_target = global_position.direction_to(look_at_pos)
			dir_to_target.y = 0
			if dir_to_target.length_squared() > 0.01:
				var target_quat = Quaternion(Basis.looking_at(dir_to_target))
				quaternion = quaternion.slerp(target_quat, rotation_speed * delta)
		play_idle()
	move_and_slide()

func move_towards_target(delta: float) -> void:
	if nav_agent.is_navigation_finished():
		velocity = velocity.move_toward(Vector3.ZERO, move_speed * 10.0 * delta)
		move_and_slide()
		play_idle()
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
