extends Node3D

@onready var ground_mesh     = $Ground
@onready var camera: Camera3D = $Camera3D
@onready var table_lantern   = $TableLantern
@onready var particles_root  = $ParticlesRoot

# ─── Miniatures ─────────────────────────────────────────────────────
var _miniatures: Dictionary = {}
const CELL_SIZE   = 1.0
const MINI_Y      = 0.05   # sits on top of floor tile

# ─── Dungeon geometry ───────────────────────────────────────────────
var _dungeon_root: Node3D = null
var _current_room_id: String = ""

# Shared materials (created once, reused)
var _mat_wall:      Material = null   # ShaderMaterial — stone blocks
var _mat_floor:     Material = null   # ShaderMaterial — stone flags
var _mat_door:      StandardMaterial3D = null
var _mat_hazard:    StandardMaterial3D = null
var _mat_pillar:    StandardMaterial3D = null
var _mat_table:     StandardMaterial3D = null
var _mat_difficult: StandardMaterial3D = null

# ─── Environment / lighting ─────────────────────────────────────────
var _world_env: WorldEnvironment  = null
var _env:       Environment       = null
var _key_light: DirectionalLight3D = null

# Per-room atmosphere (fog color, density, ambient, key light)
const ROOM_ATMOSPHERE: Dictionary = {
	"tavern_01":        {"fog": Color(0.10, 0.07, 0.03), "fog_d": 0.020, "ambient": Color(0.15, 0.10, 0.05), "key": Color(1.00, 0.78, 0.50), "key_e": 1.4},
	"cellar_depths":    {"fog": Color(0.02, 0.02, 0.05), "fog_d": 0.060, "ambient": Color(0.04, 0.04, 0.08), "key": Color(0.50, 0.60, 1.00), "key_e": 0.6},
	"forest_edge":      {"fog": Color(0.04, 0.08, 0.03), "fog_d": 0.018, "ambient": Color(0.08, 0.14, 0.06), "key": Color(0.90, 1.00, 0.80), "key_e": 1.6},
	"ancient_ruins":    {"fog": Color(0.04, 0.03, 0.06), "fog_d": 0.050, "ambient": Color(0.06, 0.05, 0.08), "key": Color(0.70, 0.65, 1.00), "key_e": 0.85},
	"market_square":    {"fog": Color(0.08, 0.07, 0.06), "fog_d": 0.015, "ambient": Color(0.12, 0.11, 0.10), "key": Color(1.00, 0.95, 0.85), "key_e": 1.3},
	"nightside_square": {"fog": Color(0.02, 0.02, 0.04), "fog_d": 0.055, "ambient": Color(0.05, 0.05, 0.10), "key": Color(0.60, 0.65, 1.00), "key_e": 0.7},
}
const _ATMO_DEFAULT: Dictionary = {"fog": Color(0.04, 0.04, 0.06), "fog_d": 0.040, "ambient": Color(0.08, 0.09, 0.12), "key": Color(1.00, 0.88, 0.70), "key_e": 1.1}

# Race group → emissive color for miniature glow
const RACE_COLORS: Dictionary = {
	"Cosmic":    Color(0.2, 0.4, 1.0),
	"Primal":    Color(0.1, 0.8, 0.2),
	"Eldritch":  Color(0.7, 0.1, 0.9),
	"Mechanical":Color(1.0, 0.5, 0.1),
	"Humanoid":  Color(1.0, 0.85, 0.6),
}
const RACE_GROUP: Dictionary = {
	"voidwraith":   "Cosmic",    "nullshade":    "Cosmic",    "ironlocust":   "Cosmic",
	"embervein":    "Cosmic",    "riftwalker":   "Cosmic",
	"solarlord":    "Primal",    "thornmimic":   "Primal",    "cinderkin":    "Primal",
	"deeptyrant":   "Primal",    "grimcrow":     "Primal",
	"bloodweaver":  "Eldritch",  "dreamhusk":    "Eldritch",  "bonedrifter":  "Eldritch",
	"mindspider":   "Eldritch",  "chaosling":    "Eldritch",
	"ironveil":     "Mechanical","forgespawn":   "Mechanical","cinderplate":  "Mechanical",
	"hexgear":      "Mechanical","wirewraith":   "Mechanical",
	"ashenborn":    "Humanoid",  "hollowsong":   "Humanoid",  "veilborn":     "Humanoid",
	"thornweft":    "Humanoid",  "ashcrown":     "Humanoid",  "ironfast":     "Humanoid",
	"coreborn":     "Humanoid",  "warpbred":     "Humanoid",  "splitblood":   "Humanoid",
	"duskweft":     "Humanoid",  "glitchkin":    "Humanoid",  "fractureline": "Humanoid",
	"emberpact":    "Humanoid",  "fallenlight":  "Humanoid",  "scaleworn":    "Humanoid",
}

# ─── Camera gimbal ──────────────────────────────────────────────────
var _cam_yaw:      float = 0.0
var _cam_pitch:    float = -45.0
var _cam_distance: float = 14.14
var _cam_target:   Vector3 = Vector3.ZERO
var _is_orbiting:  bool = false
var _last_mouse:   Vector2 = Vector2.ZERO

# ─── Lantern flicker ────────────────────────────────────────────────
const _LANTERN_BASE  = 2.5
var _flicker_t: float = 0.0

# ─── Particle scenes ────────────────────────────────────────────────
var _paradox_scene:     PackedScene = null
var _magic_burst_scene: PackedScene = null


# ─── UI Overlay ─────────────────────────────────────────────────────
var _ui_layer:      CanvasLayer    = null
var _room_label:    Label          = null
var _narrative_box: RichTextLabel  = null
var _stat_panel:    PanelContainer = null
var _stat_label:    RichTextLabel  = null
var _controller_label: Label = null
var _waiting_screen: ColorRect = null
var _world_map:     Control        = null
var _world_map_visible: bool       = false

# World map layout: room_id → {label, pos (pixels), connections}
const WORLD_MAP_NODES: Dictionary = {
    "crossroads":       {"label": "The Crossroads",    "pos": Vector2(340, 280)},
    "ironhold_keep":    {"label": "Ironhold Keep",     "pos": Vector2(340, 100)},
    "keep_courtyard":   {"label": "Keep Courtyard",    "pos": Vector2(340, 180)},
    "keep_barracks":    {"label": "Keep Barracks",     "pos": Vector2(220, 100)},
    "market_square":    {"label": "Market Square",     "pos": Vector2(530, 200)},
    "store_01":         {"label": "The Store",         "pos": Vector2(530, 100)},
    "back_alley":       {"label": "Back Alley",        "pos": Vector2(650, 200)},
    "nightside_square": {"label": "Nightside Square",  "pos": Vector2(340, 380)},
    "tavern_01":        {"label": "Crooked Tankard",   "pos": Vector2(530, 380)},
    "cellar_depths":    {"label": "Cellar Depths",     "pos": Vector2(180, 380)},
    "forest_edge":      {"label": "The Wild Reaches",  "pos": Vector2(140, 280)},
    "ancient_ruins":    {"label": "Ancient Ruins",     "pos": Vector2(30,  280)},
}

# ─── Selection ───────────────────────────────────────────────────────
var _selected_cid:   String = ""
var _character_data: Dictionary = {}  # cid → full char dict from last state

# ─── Room state cache (for click-to-move) ────────────────────────────
var _room_width:  int = 10
var _room_height: int = 8
var _room_cells:  Array = []   # flat cell dicts, row-major
var _room_exits:  Dictionary = {}  # "x,y" → room_id

# ─── Enemy tokens ────────────────────────────────────────────────────
var _enemy_data:   Dictionary = {}  # enemy_id → data dict
var _enemy_tokens: Dictionary = {}  # enemy_id → Node3D
var _enemy_cells:  Dictionary = {}  # "x,y" → enemy_id (current room)

# ─── NPC tokens ──────────────────────────────────────────────────────
var _npc_data:   Dictionary = {}  # npc_id → data dict
var _npc_tokens: Dictionary = {}  # npc_id → RaceMini instance
var _npc_cells:  Dictionary = {}  # "x,y" → npc_id (current room)

# ─── Freeform text input ─────────────────────────────────────────────
var _freeform_bar:   PanelContainer = null
var _freeform_input: LineEdit       = null

# ─── Combat overlay ──────────────────────────────────────────────────
var _combat_overlay: Control = null
var _combat_label: RichTextLabel = null
var _combat_timer: float = 0.0
const COMBAT_OVERLAY_DURATION := 4.0

# ─── NPC dialog ──────────────────────────────────────────────────────
var _npc_dialog:       Control       = null
var _npc_dialog_title: Label         = null
var _npc_dialog_desc:  RichTextLabel = null
var _npc_dialog_resp:  RichTextLabel = null
var _npc_dialog_btns:  HBoxContainer = null
var _npc_active_data:  Dictionary    = {}  # encounter data from server


# ─── Lifecycle ──────────────────────────────────────────────────────

func _ready():
	_build_materials()
	_setup_ui()
	_setup_environment()

	Input.joy_connection_changed.connect(_on_joy_connection_changed)
	_update_controller_status()

	_dungeon_root = NavigationRegion3D.new()
	_dungeon_root.name = "DungeonRoot"
	_dungeon_root.navigation_mesh = NavigationMesh.new()
	_dungeon_root.navigation_mesh.agent_radius = 0.35
	_dungeon_root.navigation_mesh.agent_height = 1.6
	add_child(_dungeon_root)

	# Keep ground hidden — _render_room shows it only when room_id not found
	ground_mesh.visible = false

	var pc = get_node_or_null("/root/PythonClient")
	if pc:
		pc.state_updated.connect(_on_state_updated)
		pc.paradox_triggered.connect(_on_paradox_triggered)
		pc.phase_changed.connect(_on_phase_changed)
		pc.npc_event_received.connect(_on_npc_event)
		pc.particle_event_received.connect(_on_particle_event)
		pc.fetch_full_state()

	_update_camera()

	if ResourceLoader.exists("res://scenes/ParadoxParticles.tscn"):
		_paradox_scene = load("res://scenes/ParadoxParticles.tscn")
	if ResourceLoader.exists("res://scenes/MagicBurst.tscn"):
		_magic_burst_scene = load("res://scenes/MagicBurst.tscn")

	AudioManager.play_ambient("res://assets/audio/ambient_keep.wav")


func _setup_ui():
	_ui_layer = CanvasLayer.new()
	add_child(_ui_layer)

	# Room Name (top-center)
	var margin = MarginContainer.new()
	margin.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	margin.add_theme_constant_override("margin_top", 20)
	_ui_layer.add_child(margin)

	_room_label = Label.new()
	_room_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_room_label.add_theme_font_size_override("font_size", 28)
	_room_label.add_theme_color_override("font_shadow_color", Color.BLACK)
	_room_label.add_theme_constant_override("shadow_offset_x", 2)
	_room_label.add_theme_constant_override("shadow_offset_y", 2)
	margin.add_child(_room_label)

	# Narrative Box (bottom-left)
	var log_margin = MarginContainer.new()
	log_margin.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	log_margin.add_theme_constant_override("margin_left", 20)
	log_margin.add_theme_constant_override("margin_bottom", 20)
	log_margin.add_theme_constant_override("margin_right", 400) # Keep it on the left half
	_ui_layer.add_child(log_margin)

	var panel = PanelContainer.new()
	log_margin.add_child(panel)

	_narrative_box = RichTextLabel.new()
	_narrative_box.bbcode_enabled = true
	_narrative_box.scroll_following = true
	_narrative_box.custom_minimum_size = Vector2(0, 120)
	_narrative_box.fit_content = true
	_narrative_box.add_theme_font_size_override("normal_font_size", 18)
	panel.add_child(_narrative_box)

	# Stat panel (bottom-right, hidden until a mini is selected)
	var stat_margin := MarginContainer.new()
	stat_margin.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_RIGHT)
	stat_margin.add_theme_constant_override("margin_right",  20)
	stat_margin.add_theme_constant_override("margin_bottom", 20)
	_ui_layer.add_child(stat_margin)

	_stat_panel = PanelContainer.new()
	_stat_panel.custom_minimum_size = Vector2(260, 0)
	_stat_panel.visible = false
	stat_margin.add_child(_stat_panel)

	_stat_label = RichTextLabel.new()
	_stat_label.bbcode_enabled = true
	_stat_label.fit_content = true
	_stat_label.add_theme_font_size_override("normal_font_size", 15)
	_stat_panel.add_child(_stat_label)

	_setup_combat_overlay()
	_setup_npc_dialog()
	_setup_world_map()
	_setup_freeform_bar()
	_setup_keyhints()

	# Waiting for Controller Screen
	_waiting_screen = ColorRect.new()
	_waiting_screen.color = Color(0, 0, 0, 0.85)
	_waiting_screen.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_ui_layer.add_child(_waiting_screen)

	var center = CenterContainer.new()
	center.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_waiting_screen.add_child(center)

	_controller_label = Label.new()
	_controller_label.text = "WAITING FOR XBOX CONTROLLER...\n(PLEASE CONNECT VIA BLUETOOTH OR USB)"
	_controller_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_controller_label.add_theme_font_size_override("font_size", 24)
	center.add_child(_controller_label)


func _on_joy_connection_changed(_device: int, _connected: bool):
	_update_controller_status()

func _update_controller_status():
	var connected = Input.get_connected_joypads().size() > 0
	if _waiting_screen:
		_waiting_screen.visible = not connected
	print("[Tabletop] Controller connected: ", connected)

func _setup_combat_overlay() -> void:
	_combat_overlay = PanelContainer.new()
	_combat_overlay.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	_combat_overlay.custom_minimum_size = Vector2(480, 0)
	_combat_overlay.offset_left  = -240
	_combat_overlay.offset_right =  240
	_combat_overlay.offset_top   = -120
	_combat_overlay.offset_bottom = 120
	_combat_overlay.visible = false
	_ui_layer.add_child(_combat_overlay)

	_combat_label = RichTextLabel.new()
	_combat_label.bbcode_enabled = true
	_combat_label.fit_content = true
	_combat_label.add_theme_font_size_override("normal_font_size", 17)
	_combat_overlay.add_child(_combat_label)


func _setup_npc_dialog() -> void:
	_npc_dialog = PanelContainer.new()
	_npc_dialog.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	_npc_dialog.custom_minimum_size = Vector2(520, 0)
	_npc_dialog.offset_left   = -260
	_npc_dialog.offset_right  =  260
	_npc_dialog.offset_top    = -200
	_npc_dialog.offset_bottom =  200
	_npc_dialog.visible = false
	_ui_layer.add_child(_npc_dialog)

	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 10)
	_npc_dialog.add_child(vbox)

	# Header row: name + close button
	var header := HBoxContainer.new()
	vbox.add_child(header)

	_npc_dialog_title = Label.new()
	_npc_dialog_title.add_theme_font_size_override("font_size", 22)
	_npc_dialog_title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	header.add_child(_npc_dialog_title)

	var close_btn := Button.new()
	close_btn.text = "✕"
	close_btn.flat = true
	close_btn.pressed.connect(func(): _npc_dialog.visible = false)
	header.add_child(close_btn)

	# Separator
	var sep := HSeparator.new()
	vbox.add_child(sep)

	# Description
	_npc_dialog_desc = RichTextLabel.new()
	_npc_dialog_desc.bbcode_enabled = true
	_npc_dialog_desc.fit_content = true
	_npc_dialog_desc.custom_minimum_size = Vector2(0, 50)
	_npc_dialog_desc.add_theme_font_size_override("normal_font_size", 15)
	vbox.add_child(_npc_dialog_desc)

	# Response area
	_npc_dialog_resp = RichTextLabel.new()
	_npc_dialog_resp.bbcode_enabled = true
	_npc_dialog_resp.fit_content = true
	_npc_dialog_resp.scroll_following = true
	_npc_dialog_resp.custom_minimum_size = Vector2(0, 60)
	_npc_dialog_resp.add_theme_font_size_override("normal_font_size", 14)
	vbox.add_child(_npc_dialog_resp)

	# Action buttons
	_npc_dialog_btns = HBoxContainer.new()
	_npc_dialog_btns.add_theme_constant_override("separation", 8)
	vbox.add_child(_npc_dialog_btns)


func _setup_world_map() -> void:
	# Full-screen darkened overlay
	_world_map = Control.new()
	_world_map.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_world_map.visible = false
	_ui_layer.add_child(_world_map)

	# Dark backdrop
	var backdrop := ColorRect.new()
	backdrop.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	backdrop.color = Color(0.04, 0.03, 0.06, 0.88)
	_world_map.add_child(backdrop)

	# Title
	var title := Label.new()
	title.text = "THE FERAL WORLD — Fast Travel"
	title.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	title.offset_top = 30
	title.offset_bottom = 70
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_font_size_override("font_size", 32)
	title.add_theme_color_override("font_color", Color(0.9, 0.82, 0.6))
	_world_map.add_child(title)

	var hint := Label.new()
	hint.text = "Click a location to travel there  •  [M] or [Esc] to close"
	hint.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	hint.offset_top    = -50
	hint.offset_bottom = -16
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	hint.add_theme_font_size_override("font_size", 16)
	hint.add_theme_color_override("font_color", Color(0.6, 0.6, 0.6, 0.8))
	_world_map.add_child(hint)

	# Map canvas centered in screen
	var map_container := Control.new()
	map_container.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	map_container.custom_minimum_size = Vector2(720, 500)
	map_container.offset_left   = -360
	map_container.offset_top    = -210
	map_container.offset_right  =  360
	map_container.offset_bottom =  290
	_world_map.add_child(map_container)

	# Draw connection lines as ColorRects
	const CONNECTIONS: Array = [
		["crossroads", "keep_courtyard"], ["keep_courtyard", "ironhold_keep"],
		["ironhold_keep", "keep_barracks"],
		["crossroads", "market_square"], ["market_square", "store_01"],
		["market_square", "back_alley"],
		["crossroads", "nightside_square"], ["nightside_square", "tavern_01"],
		["nightside_square", "cellar_depths"],
		["crossroads", "forest_edge"], ["forest_edge", "ancient_ruins"],
	]
	for conn in CONNECTIONS:
		var a_pos: Vector2 = WORLD_MAP_NODES[conn[0]]["pos"]
		var b_pos: Vector2 = WORLD_MAP_NODES[conn[1]]["pos"]
		var line := ColorRect.new()
		var mid  := (a_pos + b_pos) * 0.5
		var diff := b_pos - a_pos
		var length := diff.length()
		line.size = Vector2(length, 2)
		line.position = mid - Vector2(length * 0.5, 1)
		line.rotation = diff.angle()
		line.pivot_offset = Vector2(length * 0.5, 1)
		line.color = Color(0.5, 0.45, 0.35, 0.55)
		map_container.add_child(line)

	# Room buttons
	for room_id in WORLD_MAP_NODES:
		var data: Dictionary = WORLD_MAP_NODES[room_id]
		var btn := Button.new()
		btn.text = data["label"]
		btn.custom_minimum_size = Vector2(130, 36)
		btn.position = data["pos"] - Vector2(65, 18)
		btn.add_theme_font_size_override("font_size", 13)
		var rid_copy: String = room_id
		btn.pressed.connect(func():
			_travel_to(rid_copy)
		)
		map_container.add_child(btn)


func _travel_to(room_id: String) -> void:
	var pc = get_node_or_null("/root/PythonClient")
	if not pc:
		return
	_world_map.visible = false
	_world_map_visible = false
	var http = pc.post_request("/action/travel", {"room_id": room_id})
	http.request_completed.connect(func(_r, _c, _h, _b):
		pc.fetch_full_state()
		http.queue_free()
	)


func _toggle_world_map() -> void:
	_world_map_visible = not _world_map_visible
	_world_map.visible = _world_map_visible


func _build_materials():
	# Stone-block wall: hash-varied tiles with grout lines
	var wall_sm := ShaderMaterial.new()
	wall_sm.shader = Shader.new()
	wall_sm.shader.code = """
shader_type spatial;
void fragment() {
	vec2 uv = UV * 2.5;
	vec2 tile = floor(uv);
	vec2 frc  = fract(uv);
	float n   = fract(sin(dot(tile, vec2(127.1, 311.7))) * 43758.5453);
	float grout = step(0.93, max(frc.x, frc.y));
	vec3 base = vec3(0.27, 0.24, 0.21) * (0.78 + n * 0.44);
	ALBEDO    = mix(base, vec3(0.11, 0.10, 0.09), grout);
	ROUGHNESS = 0.93 - n * 0.08;
	METALLIC  = 0.0;
	float ex  = (frc.x - 0.5) * grout * 0.5;
	float ey  = (frc.y - 0.5) * grout * 0.5;
	NORMAL_MAP       = normalize(vec3(ex, ey, 1.0));
	NORMAL_MAP_DEPTH = 1.1;
}
"""
	_mat_wall = wall_sm

	# Stone-flag floor: larger slabs with grout and wear variation
	var floor_sm := ShaderMaterial.new()
	floor_sm.shader = Shader.new()
	floor_sm.shader.code = """
shader_type spatial;
void fragment() {
	vec2 uv   = UV * 3.0;
	vec2 tile = floor(uv);
	vec2 frc  = fract(uv);
	float n   = fract(sin(dot(tile, vec2(311.7, 127.1))) * 43758.5453);
	float grout = step(0.94, max(frc.x, frc.y));
	vec3 base = vec3(0.21, 0.19, 0.17) * (0.80 + n * 0.40);
	ALBEDO    = mix(base, vec3(0.09, 0.08, 0.07), grout);
	ROUGHNESS = 0.88 - n * 0.10;
	METALLIC  = 0.0;
	float ex  = (frc.x - 0.5) * grout * 0.35;
	float ey  = (frc.y - 0.5) * grout * 0.35;
	NORMAL_MAP       = normalize(vec3(ex, ey, 1.0));
	NORMAL_MAP_DEPTH = 0.85;
}
"""
	_mat_floor = floor_sm

	_mat_door = StandardMaterial3D.new()
	_mat_door.albedo_color = Color(0.35, 0.25, 0.15)
	_mat_door.roughness = 0.7
	_mat_door.metallic = 0.1

	_mat_hazard = StandardMaterial3D.new()
	_mat_hazard.albedo_color = Color(0.4, 0.1, 0.05)
	_mat_hazard.roughness = 0.5
	_mat_hazard.metallic = 0.0
	_mat_hazard.emission_enabled = true
	_mat_hazard.emission = Color(0.4, 0.1, 0.0)

	_mat_pillar = StandardMaterial3D.new()
	_mat_pillar.albedo_color = Color(0.52, 0.48, 0.42)
	_mat_pillar.roughness = 0.78
	_mat_pillar.metallic = 0.04

	_mat_table = StandardMaterial3D.new()
	_mat_table.albedo_color = Color(0.32, 0.20, 0.11)
	_mat_table.roughness = 0.88
	_mat_table.metallic = 0.0

	_mat_difficult = StandardMaterial3D.new()
	_mat_difficult.albedo_color = Color(0.30, 0.24, 0.18)
	_mat_difficult.roughness = 0.92
	_mat_difficult.metallic = 0.0


func _process(delta):
	_flicker_t += delta
	var flicker = sin(_flicker_t * 7.3) * 0.09 + sin(_flicker_t * 13.7) * 0.05
	table_lantern.light_energy = _LANTERN_BASE + flicker
	if _combat_overlay and _combat_overlay.visible:
		_combat_timer -= delta
		if _combat_timer <= 0.0:
			_combat_overlay.visible = false


# ─── Camera input ───────────────────────────────────────────────────

func _input(event: InputEvent):
	if event is InputEventMouseButton:
		match event.button_index:
			MOUSE_BUTTON_LEFT:
				if event.pressed:
					if _combat_overlay and _combat_overlay.visible:
						_combat_overlay.visible = false
					elif not _world_map_visible:
						_try_select_mini(event.position)
			MOUSE_BUTTON_RIGHT:
				_is_orbiting = event.pressed
				if event.pressed:
					_last_mouse = event.position
			MOUSE_BUTTON_WHEEL_UP:
				_cam_distance = max(5.0, _cam_distance - 1.2)
				_update_camera()
			MOUSE_BUTTON_WHEEL_DOWN:
				_cam_distance = min(30.0, _cam_distance + 1.2)
				_update_camera()

	if event is InputEventMouseMotion and _is_orbiting:
		var d = event.position - _last_mouse
		_cam_yaw   -= d.x * 0.25
		_cam_pitch  = clamp(_cam_pitch - d.y * 0.2, -82.0, -8.0)
		_last_mouse = event.position
		_update_camera()

	if event is InputEventKey and event.pressed:
		# Escape always closes overlays/freeform regardless of focus
		if event.keycode == KEY_ESCAPE:
			if _freeform_bar and _freeform_bar.visible:
				_freeform_bar.visible = false
			elif _combat_overlay and _combat_overlay.visible:
				_combat_overlay.visible = false
			elif _npc_dialog and _npc_dialog.visible:
				_npc_dialog.visible = false
			elif _world_map_visible:
				_toggle_world_map()
			return

		# Block all other shortcuts while freeform input is open
		if _freeform_bar and _freeform_bar.visible:
			return

		match event.keycode:
			KEY_R:
				_cam_yaw      = 0.0
				_cam_pitch    = -45.0
				_cam_distance = 14.14
				_cam_target   = Vector3.ZERO
				_update_camera()
			KEY_M:
				_toggle_world_map()
			KEY_TAB:
				_cycle_character(not event.shift_pressed)
			KEY_1: _select_character_by_slot(0)
			KEY_2: _select_character_by_slot(1)
			KEY_3: _select_character_by_slot(2)
			KEY_4: _select_character_by_slot(3)
			KEY_E:
				_interact_adjacent()
			KEY_F:
				_open_freeform()
			KEY_I:
				if _stat_panel:
					if not _stat_panel.visible and not _selected_cid.is_empty():
						_show_stat_panel(_selected_cid)
					else:
						_stat_panel.visible = not _stat_panel.visible


func _physics_process(delta: float) -> void:
	if _selected_cid.is_empty() or not _selected_cid in _miniatures:
		return
	
	# Block movement while typing or in dialog
	if (_freeform_bar and _freeform_bar.visible) or (_npc_dialog and _npc_dialog.visible):
		return

	# 1. Camera Control (Right Stick / Bluetooth Xbox)
	var look_vec = Input.get_vector("look_left", "look_right", "look_up", "look_down")
	if look_vec.length() > 0.05:
		_cam_yaw -= look_vec.x * 2.5
		_cam_pitch = clamp(_cam_pitch - look_vec.y * 2.0, -82.0, -8.0)
		_update_camera()

	# 2. Leader Movement (Left Stick / WASD)
	var leader = _miniatures[_selected_cid]
	var input_vec = Input.get_vector("move_left", "move_right", "move_up", "move_down")
	
	if input_vec.length() > 0.05:
		var yaw := deg_to_rad(_cam_yaw)
		var forward = Vector3(-sin(yaw), 0, -cos(yaw))
		var right   = Vector3(cos(yaw), 0, -sin(yaw))
		
		# In Godot get_vector, Y is positive for down, so -input_vec.y is forward
		var move_dir = (right * input_vec.x + forward * (-input_vec.y)).normalized()
		
		if leader.has_method("move_with_input"):
			leader.move_with_input(move_dir, delta)
			_cam_target = leader.position
			_update_camera()
	
	# 3. Party Follower Logic
	for cid in _miniatures:
		if cid == _selected_cid:
			continue
		
		var mini = _miniatures[cid]
		# Only move player characters (mini name starts with "Mini_")
		if not mini.name.begins_with("Mini_"):
			continue
			
		if mini.has_method("move_towards_target"):
			# Followers target the leader
			mini.nav_agent.target_position = leader.position
			mini.move_towards_target(delta)

func _update_camera():
	var yaw   = deg_to_rad(_cam_yaw)
	var pitch = deg_to_rad(_cam_pitch)
	var cp    = cos(pitch)
	var offset = Vector3(
		_cam_distance * cp * sin(yaw),
		_cam_distance * -sin(pitch),
		_cam_distance * cp * cos(yaw)
	)
	camera.position = _cam_target + offset
	camera.look_at(_cam_target, Vector3.UP)


# ─── Dungeon geometry ───────────────────────────────────────────────

func _rebuild_room(state: Dictionary):
	var room_id: String = state.get("current_room_id", "")

	# Update room name UI
	var rooms = state.get("rooms", {})
	if room_id in rooms:
		_room_label.text = rooms[room_id].get("name", room_id).to_upper()
	else:
		_room_label.text = ""

	# Cache room data for click-to-move
	if room_id in rooms:
		var room_dict: Dictionary = rooms[room_id]
		_room_width  = room_dict.get("width",  10)
		_room_height = room_dict.get("height", 8)
		_room_cells  = room_dict.get("cells",  [])
		_room_exits  = room_dict.get("exits",  {})

	if room_id == _current_room_id:
		return
	_current_room_id = room_id

	# Clear previous geometry
	for child in _dungeon_root.get_children():
		child.queue_free()

	if not room_id in rooms:
		ground_mesh.visible = true
		return

	ground_mesh.visible = false

	var room: Dictionary = rooms[room_id]
	var w: int = room.get("width", 10)
	var h: int = room.get("height", 10)
	var cells: Array = room.get("cells", [])

	var wall_mesh   = BoxMesh.new()
	wall_mesh.size  = Vector3(CELL_SIZE, 2.5, CELL_SIZE)

	var floor_mesh  = BoxMesh.new()
	floor_mesh.size = Vector3(CELL_SIZE, 0.12, CELL_SIZE)

	var door_mesh   = BoxMesh.new()
	door_mesh.size  = Vector3(CELL_SIZE * 0.6, 2.2, 0.12)

	var hazard_mesh = BoxMesh.new()
	hazard_mesh.size = Vector3(CELL_SIZE, 0.12, CELL_SIZE)

	var pillar_mesh = CylinderMesh.new()
	pillar_mesh.top_radius    = CELL_SIZE * 0.18
	pillar_mesh.bottom_radius = CELL_SIZE * 0.22
	pillar_mesh.height        = 2.0
	pillar_mesh.radial_segments = 8

	var table_top_mesh = BoxMesh.new()
	table_top_mesh.size = Vector3(CELL_SIZE * 0.88, 0.09, CELL_SIZE * 0.88)

	var table_leg_mesh = CylinderMesh.new()
	table_leg_mesh.top_radius    = CELL_SIZE * 0.04
	table_leg_mesh.bottom_radius = CELL_SIZE * 0.04
	table_leg_mesh.height        = 0.56
	table_leg_mesh.radial_segments = 6

	for y in range(h):
		for x in range(w):
			var idx = y * w + x
			var cell: Dictionary = cells[idx] if idx < cells.size() else {}
			var terrain: String = cell.get("terrain", "floor")
			var wx: float = x * CELL_SIZE
			var wz: float = y * CELL_SIZE

			var inst = MeshInstance3D.new()
			match terrain:
				"wall":
					inst.mesh = wall_mesh
					inst.material_override = _mat_wall
					inst.position = Vector3(wx, 1.25, wz)

				"door":
					var floor_inst = MeshInstance3D.new()
					floor_inst.mesh = floor_mesh
					floor_inst.material_override = _mat_floor
					floor_inst.position = Vector3(wx, -0.06, wz)
					_dungeon_root.add_child(floor_inst)
					inst.mesh = door_mesh
					inst.material_override = _mat_door
					inst.position = Vector3(wx, 1.1, wz)

				"hazard":
					inst.mesh = hazard_mesh
					inst.material_override = _mat_hazard
					inst.position = Vector3(wx, -0.06, wz)

				"difficult":
					inst.mesh = floor_mesh
					inst.material_override = _mat_difficult
					inst.position = Vector3(wx, -0.06, wz)

				"pillar":
					# Floor slab beneath
					var floor_inst = MeshInstance3D.new()
					floor_inst.mesh = floor_mesh
					floor_inst.material_override = _mat_floor
					floor_inst.position = Vector3(wx, -0.06, wz)
					_dungeon_root.add_child(floor_inst)
					# Base cap
					var base_mesh = BoxMesh.new()
					base_mesh.size = Vector3(CELL_SIZE * 0.5, 0.12, CELL_SIZE * 0.5)
					var base_inst = MeshInstance3D.new()
					base_inst.mesh = base_mesh
					base_inst.material_override = _mat_pillar
					base_inst.position = Vector3(wx, 0.06, wz)
					_dungeon_root.add_child(base_inst)
					# Shaft
					inst.mesh = pillar_mesh
					inst.material_override = _mat_pillar
					inst.position = Vector3(wx, 1.0, wz)

				"table":
					# Floor slab beneath
					var floor_inst = MeshInstance3D.new()
					floor_inst.mesh = floor_mesh
					floor_inst.material_override = _mat_floor
					floor_inst.position = Vector3(wx, -0.06, wz)
					_dungeon_root.add_child(floor_inst)
					# Four legs
					var leg_offsets = [
						Vector3( CELL_SIZE * 0.32, 0.28,  CELL_SIZE * 0.32),
						Vector3(-CELL_SIZE * 0.32, 0.28,  CELL_SIZE * 0.32),
						Vector3( CELL_SIZE * 0.32, 0.28, -CELL_SIZE * 0.32),
						Vector3(-CELL_SIZE * 0.32, 0.28, -CELL_SIZE * 0.32),
					]
					for lo in leg_offsets:
						var leg_inst = MeshInstance3D.new()
						leg_inst.mesh = table_leg_mesh
						leg_inst.material_override = _mat_table
						leg_inst.position = Vector3(wx, 0, wz) + lo
						_dungeon_root.add_child(leg_inst)
					# Tabletop
					inst.mesh = table_top_mesh
					inst.material_override = _mat_table
					inst.position = Vector3(wx, 0.60, wz)

				_:
					inst.mesh = floor_mesh
					inst.material_override = _mat_floor
					inst.position = Vector3(wx, -0.06, wz)

			_dungeon_root.add_child(inst)

	# Center camera on room
	_cam_target = Vector3((w - 1) * CELL_SIZE * 0.5, 0.0, (h - 1) * CELL_SIZE * 0.5)
	_cam_distance = max(w, h) * 0.9 + 4.0
	_update_camera()

	_build_void_floor(w, h)
	_add_room_torches(cells, w, h)
	_set_room_atmosphere(room_id)
	
	# Bake navigation mesh so party followers can pathfind
	if _dungeon_root:
		_dungeon_root.bake_navigation_mesh()


# ─── State / miniatures ─────────────────────────────────────────────

func _on_state_updated(new_state: Dictionary):
	var old_room := _current_room_id
	_rebuild_room(new_state)
	# On room transition, clear minis and enemy tokens so they respawn
	if _current_room_id != old_room and old_room != "":
		for mini in _miniatures.values():
			mini.queue_free()
		_miniatures.clear()
		for tok in _enemy_tokens.values():
			tok.queue_free()
		_enemy_tokens.clear()
		_enemy_cells.clear()
		for tok in _npc_tokens.values():
			tok.queue_free()
		_npc_tokens.clear()
		_npc_cells.clear()
		_selected_cid = ""
		_npc_dialog.visible = false
	_update_narrative(new_state)

	# characters is dict[str, CharacterSheet] — iterate over key→value pairs
	var characters = new_state.get("characters", {})
	var char_items: Array = characters.values() if characters is Dictionary else characters
	for char_data in char_items:
		if char_data is String:
			continue
		var cid:       String = char_data.get("id", "")
		var pos               = char_data.get("position", {"x": 0, "y": 0})
		var race_id:   String = char_data.get("race", "ashenborn")
		var char_name: String = char_data.get("name", cid)

		if cid.is_empty():
			continue
		_character_data[cid] = char_data  # store for stat panel
		if cid in _miniatures:
			_move_miniature(cid, Vector2(pos.x, pos.y))
		else:
			spawn_miniature(cid, Vector2(pos.x, pos.y), race_id, char_name)

	_update_enemy_tokens(new_state)
	_update_npc_tokens(new_state)


func _update_enemy_tokens(state: Dictionary) -> void:
	_enemy_data.clear()
	_enemy_cells.clear()
	var current_room: String = state.get("current_room_id", "")
	var all_enemies = state.get("enemies", {})
	if not all_enemies is Dictionary:
		return

	for eid in all_enemies:
		var e = all_enemies[eid]
		if not e is Dictionary:
			continue
		if e.get("room_id", "") != current_room:
			continue
		_enemy_data[eid] = e
		var pos = e.get("position", {"x": 0, "y": 0})
		var cell_key := "%d,%d" % [int(pos.get("x", 0)), int(pos.get("y", 0))]
		if e.get("alive", true):
			_enemy_cells[cell_key] = eid
		# Spawn or remove token
		if e.get("alive", true):
			if not eid in _enemy_tokens:
				_spawn_enemy_token(eid, e)
		else:
			if eid in _enemy_tokens:
				_enemy_tokens[eid].queue_free()
				_enemy_tokens.erase(eid)


const _ENEMY_MODEL_DIR := "res://assets/models/enemies/"
const _DRAGON_MODEL_DIR := "res://assets/models/dragons/"

# sprite_key → model file (without dir prefix and .glb)
const _ENEMY_SPRITE_MAP: Dictionary = {
	"skeleton":       "enemies/skeleton",
	"ghoul":          "enemies/ghoul",
	"bandit":         "enemies/bandit",
	"thug":           "enemies/thug",
	"animated_armor": "enemies/animated_armor",
	"shadow":         "enemies/shadow",
	"race_enemy":     "enemies/race_enemy",
	"dragon_red":     "dragons/dragon_red",
	"dragon_green":   "dragons/dragon_green",
	"dragon_blue":    "dragons/dragon_blue",
	"dragon_black":   "dragons/dragon_black",
	"dragon_white":   "dragons/dragon_white",
	"dragon_gold":    "dragons/dragon_gold",
	"dragon_whelp":   "dragons/dragon_whelp",
}

func _spawn_enemy_token(enemy_id: String, data: Dictionary) -> void:
	var pos = data.get("position", {"x": 0, "y": 0})
	var root := Node3D.new()
	root.name = "Enemy_" + enemy_id
	root.position = _grid_to_world(Vector2(pos.get("x", 0), pos.get("y", 0)))

	# Try to load a .glb model based on sprite_key
	var sprite_key: String = data.get("sprite_key", "")
	var model_loaded := false
	if not sprite_key.is_empty() and sprite_key in _ENEMY_SPRITE_MAP:
		var rel_path: String = _ENEMY_SPRITE_MAP[sprite_key]
		var glb_path: String = "res://assets/models/" + rel_path + ".glb"
		if ResourceLoader.exists(glb_path):
			var scene := load(glb_path) as PackedScene
			if scene:
				var inst := scene.instantiate()
				var is_dragon := rel_path.begins_with("dragons/")
				inst.scale = Vector3(0.9, 0.9, 0.9) if is_dragon else Vector3(0.55, 0.55, 0.55)
				# Animate idle if AnimationPlayer present
				var ap := _find_anim_player_in(inst)
				if ap:
					for n in ["Idle", "Idle_A", "idle"]:
						if ap.has_animation(n):
							ap.play(n)
							break
				root.add_child(inst)
				model_loaded = true

	if not model_loaded:
		# Use RaceMini for dynamic 3D shapes based on enemy type
		var mini = RaceMiniScene.instantiate()
		mini.name = "RaceMini"
		root.add_child(mini)
		var kind: String = data.get("kind", sprite_key)
		if kind.is_empty(): kind = "goblin"
		mini.setup(kind, data.get("name", "Enemy"), true)

	# Red glow ring regardless of model
	var ring_mesh := CylinderMesh.new()
	ring_mesh.top_radius    = CELL_SIZE * 0.30
	ring_mesh.bottom_radius = CELL_SIZE * 0.30
	ring_mesh.height        = 0.04
	ring_mesh.radial_segments = 16
	var ring_mat := StandardMaterial3D.new()
	ring_mat.albedo_color      = Color(1.0, 0.15, 0.15, 0.7)
	ring_mat.emission_enabled  = true
	ring_mat.emission          = Color(1.2, 0.0, 0.0)
	ring_mat.transparency      = BaseMaterial3D.TRANSPARENCY_ALPHA
	var ring_inst := MeshInstance3D.new()
	ring_inst.mesh = ring_mesh
	ring_inst.material_override = ring_mat
	ring_inst.position = Vector3(0, 0.02, 0)
	root.add_child(ring_inst)

	# HP bar floating above token
	_add_enemy_hp_bar(root, data.get("hp_current", 1), data.get("hp_max", 1))

	add_child(root)
	_enemy_tokens[enemy_id] = root


func _find_anim_player_in(node: Node) -> AnimationPlayer:
	if node is AnimationPlayer:
		return node as AnimationPlayer
	for child in node.get_children():
		var found := _find_anim_player_in(child)
		if found:
			return found
	return null


func _update_npc_tokens(state: Dictionary) -> void:
	var current_room: String = state.get("current_room_id", "")
	var all_npcs = state.get("npcs", {})
	if not all_npcs is Dictionary:
		return

	var seen_ids: Dictionary = {}
	for nid in all_npcs:
		var n = all_npcs[nid]
		if not n is Dictionary:
			continue
		if n.get("room_id", "") != current_room:
			continue
		_npc_data[nid] = n
		seen_ids[nid] = true
		var pos = n.get("position", {"x": 0, "y": 0})
		var cell_key := "%d,%d" % [int(pos.get("x", 0)), int(pos.get("y", 0))]
		if n.get("interactable", false):
			_npc_cells[cell_key] = nid
		if not nid in _npc_tokens:
			_spawn_npc_token(nid, n)

	# Remove tokens for NPCs no longer in this room
	for nid in _npc_tokens.keys():
		if not nid in seen_ids:
			_npc_tokens[nid].queue_free()
			_npc_tokens.erase(nid)
	for k in _npc_cells.keys():
		if not _npc_cells[k] in seen_ids:
			_npc_cells.erase(k)


# NPC token color palette keyed by sprite_key prefix
const NPC_COLORS: Dictionary = {
	"npc_jon":      Color(1.0,  0.82, 0.35),   # warm gold — shopkeeper
	"npc_samael":   Color(0.55, 0.20, 0.90),   # deep violet — demigod
	"npc_haylie":   Color(0.85, 0.45, 0.75),   # rose pink — innkeeper
	"npc_danna":    Color(0.90, 0.85, 0.30),   # royal gold — queen
	"npc_redvelvet":Color(0.95, 0.20, 0.30),   # red — performer
	"npc_kodrik":   Color(0.30, 0.65, 0.95),   # steel blue — guildmaster
	"npc_bryne":    Color(0.45, 0.75, 0.55),   # muted green — warden
	"npc_nathis":   Color(0.85, 0.55, 0.20),   # amber — front man
	"npc_keeva":    Color(1.0,  1.0,  1.0),    # white — divine
	"npc_bear":     Color(0.70, 0.45, 0.20),   # brown — bear
	"npc_wolf":     Color(0.75, 0.75, 0.80),   # silver — wolf
	"npc_cat":      Color(0.85, 0.65, 0.40),   # tan — cat
	"npc_cat_white":Color(0.95, 0.95, 1.0),    # white — cat
	"npc_dog":      Color(0.70, 0.55, 0.35),   # brown — dog
	"npc_dog_black":Color(0.20, 0.18, 0.22),   # dark — black dog
}

func _npc_color(sprite_key: String) -> Color:
	if sprite_key in NPC_COLORS:
		return NPC_COLORS[sprite_key]
	return Color(0.7, 0.9, 0.7)  # default soft green

func _spawn_npc_token(npc_id: String, data: Dictionary) -> void:
	var pos = data.get("position", {"x": 0, "y": 0})
	var sprite_key: String = data.get("sprite_key", "npc_default")
	var display_name: String = data.get("name", npc_id)

	var mini = RaceMiniScene.instantiate()
	mini.name = "NPC_" + npc_id
	mini.position = _grid_to_world(Vector2(pos.get("x", 0), pos.get("y", 0)))
	add_child(mini)
	mini.setup(sprite_key, display_name, false)
	_npc_tokens[npc_id] = mini


func _update_narrative(state: Dictionary):
	var log_entries = state.get("narrative_log", [])
	if log_entries.is_empty():
		return
	
	var text = ""
	# Show last 3 entries
	var start = max(0, log_entries.size() - 3)
	for i in range(start, log_entries.size()):
		var entry = log_entries[i]
		var entry_text = entry.get("text", "")
		if entry.get("kind") == "narration":
			text += "[i]%s[/i]\n\n" % entry_text
		else:
			text += "%s\n\n" % entry_text
	
	_narrative_box.text = text.strip_edges()


const RaceMiniScene = preload("res://scenes/RaceMini.tscn")

func spawn_miniature(character_id: String, grid_pos: Vector2, race_id: String, char_name: String = "") -> Node3D:
	var root = RaceMiniScene.instantiate()
	root.name     = "Mini_" + character_id
	root.position = _grid_to_world(grid_pos)
	add_child(root)          # add first so @onready vars resolve before setup()
	root.setup(race_id, char_name)
	_miniatures[character_id] = root
	return root


func _move_miniature(character_id: String, grid_pos: Vector2):
	var mini = _miniatures[character_id]
	var target = _grid_to_world(grid_pos)
	# Start walk animation
	if mini.has_method("play_walk"):
		mini.play_walk()
	var tween = create_tween()
	tween.tween_property(mini, "position", target, 0.3).set_trans(Tween.TRANS_SINE)
	tween.tween_callback(func():
		if mini.has_method("play_idle"):
			mini.play_idle()
	)
	spawn_magic_burst(target)
	AudioManager.play_sfx("res://assets/audio/sfx_move.wav")


func _grid_to_world(grid_pos: Vector2) -> Vector3:
	return Vector3(grid_pos.x * CELL_SIZE, MINI_Y, grid_pos.y * CELL_SIZE)


# ─── Click-to-select ────────────────────────────────────────────────

func _try_select_mini(screen_pos: Vector2) -> void:
	var ray_origin := camera.project_ray_origin(screen_pos)
	var ray_dir    := camera.project_ray_normal(screen_pos)

	# ── 1. Try to hit a miniature ─────────────────────────────────────
	var closest_cid  := ""
	var closest_dist := INF
	for cid in _miniatures:
		var mini: Node3D = _miniatures[cid]
		var to_ray := mini.global_position - ray_origin
		var proj   := to_ray.dot(ray_dir)
		if proj < 0:
			continue
		var closest_pt := ray_origin + ray_dir * proj
		if mini.global_position.distance_to(closest_pt) < 0.55 and proj < closest_dist:
			closest_dist = proj
			closest_cid  = cid

	if closest_cid != "":
		_select_mini(closest_cid)
		return

	# ── 2. No mini hit — ray-cast onto the floor plane (y = 0) ────────
	if ray_dir.y >= 0.0:
		_deselect_mini()
		return
	var t := -ray_origin.y / ray_dir.y
	var world_x := ray_origin.x + t * ray_dir.x
	var world_z := ray_origin.z + t * ray_dir.z
	var gx := int(round(world_x / CELL_SIZE))
	var gy := int(round(world_z / CELL_SIZE))

	if gx < 0 or gy < 0 or gx >= _room_width or gy >= _room_height:
		_deselect_mini()
		return

	var cell_idx := gy * _room_width + gx
	var cell: Dictionary = _room_cells[cell_idx] if cell_idx < _room_cells.size() else {}
	var terrain: String = cell.get("terrain", "floor")

	# ── 3. Enemy cell — attack ───────────────────────────────────────
	var cell_key := "%d,%d" % [gx, gy]
	if cell_key in _enemy_cells:
		var eid: String = _enemy_cells[cell_key]
		if _enemy_data.get(eid, {}).get("alive", false):
			var actor_id := _get_any_player_id()
			if not actor_id.is_empty():
				_do_attack_enemy(eid, actor_id)
			return

	# ── 3b. NPC cell — open dialog ───────────────────────────────────
	if cell_key in _npc_cells:
		var nid: String = _npc_cells[cell_key]
		var actor_id := _get_any_player_id()
		if not actor_id.is_empty():
			_do_interact_npc(nid, gx, gy, actor_id)
		return

	# ── 4. Door cell — interact (room transition) ─────────────────────
	if terrain == "door":
		var actor_id := _get_any_player_id()
		if actor_id.is_empty():
			return
		var pc = get_node_or_null("/root/PythonClient")
		if pc:
			var http = pc.post_request("/action/grid", {
				"actor_id": actor_id, "type": "interact",
				"target": {"x": gx, "y": gy}
			})
			http.request_completed.connect(func(_r, _c, _h, body):
				var resp = JSON.parse_string(body.get_string_from_utf8())
				if resp and resp.has("room_transition"):
					pc.fetch_full_state()
				http.queue_free()
			)
		return

	# ── 5. Floor/difficult cell — move selected character ─────────────
	if (terrain == "floor" or terrain == "difficult") and _selected_cid != "":
		var pc = get_node_or_null("/root/PythonClient")
		if pc:
			var http = pc.post_request("/action/grid", {
				"actor_id": _selected_cid, "type": "move",
				"target": {"x": gx, "y": gy}
			})
			http.request_completed.connect(func(_r, _c, _h, _b): http.queue_free())
		return

	_deselect_mini()


func _do_attack_enemy(enemy_id: String, actor_id: String) -> void:
	var pc = get_node_or_null("/root/PythonClient")
	if not pc:
		return
	# Attacker swings
	if actor_id in _miniatures:
		var mini = _miniatures[actor_id]
		if mini.has_method("play_attack"):
			mini.play_attack()
	var http = pc.post_request("/enemy/" + enemy_id + "/attack", {"actor_id": actor_id})
	http.request_completed.connect(func(_r, code, _h, body):
		if code >= 200 and code < 300:
			var resp = JSON.parse_string(body.get_string_from_utf8())
			if resp is Dictionary:
				_show_combat_result(resp)
				if enemy_id in _enemy_tokens:
					var etok: Node3D = _enemy_tokens[enemy_id]
					# Sparks on any hit
					var pa: Dictionary = resp.get("player_attack", {})
					if pa.get("hit", false):
						_spawn_hit_sparks(etok.position)
					# Death animation + bar hide on kill
					if resp.get("enemy_died", false):
						var ap := _find_anim_player_in(etok)
						if ap:
							for n in ["Death", "Die", "Fall", "death"]:
								if ap.has_animation(n):
									ap.play(n)
									break
						var bar := etok.get_node_or_null("HPBar")
						if bar:
							bar.visible = false
					else:
						# Refresh HP bar to show new HP
						var bar := etok.get_node_or_null("HPBar")
						if bar:
							bar.queue_free()
						_add_enemy_hp_bar(etok, resp.get("enemy_hp", 1),
							_enemy_data.get(enemy_id, {}).get("hp_max", 1))
				pc.fetch_full_state()
		http.queue_free()
	)


func _do_interact_npc(npc_id: String, gx: int, gy: int, actor_id: String) -> void:
	var pc = get_node_or_null("/root/PythonClient")
	if not pc:
		return
	var http = pc.post_request("/action/grid", {
		"actor_id": actor_id, "type": "interact",
		"target": {"x": gx, "y": gy}
	})
	http.request_completed.connect(func(_r, code, _h, body):
		if code >= 200 and code < 300:
			var resp = JSON.parse_string(body.get_string_from_utf8())
			if resp is Dictionary and resp.has("encounter"):
				var enc: Dictionary = resp["encounter"]
				if enc.get("type", "") == "npc_encounter":
					_show_npc_dialog(enc)
		http.queue_free()
	)


func _show_npc_dialog(enc: Dictionary) -> void:
	_npc_active_data = enc
	var npc_id: String = enc.get("npc_id", "")
	var npc_name: String = enc.get("npc_name", "Unknown")
	var encounter_id: String = enc.get("encounter_id", "")

	# Play talk animation on the NPC token
	if npc_id in _npc_tokens:
		var tok = _npc_tokens[npc_id]
		if tok.has_method("play_talk"):
			tok.play_talk()

	# Get description from cached npc_data
	var desc: String = ""
	if npc_id in _npc_data:
		desc = _npc_data[npc_id].get("description", "")

	_npc_dialog_title.text = npc_name
	_npc_dialog_desc.text = "[color=#cccccc]%s[/color]" % desc
	_npc_dialog_resp.text = ""

	# Rebuild action buttons
	for child in _npc_dialog_btns.get_children():
		child.queue_free()

	var actions := _npc_actions_for(encounter_id)
	for act in actions:
		var btn := Button.new()
		btn.text = act["label"]
		var act_copy: Dictionary = act
		btn.pressed.connect(func(): _npc_do_action(act_copy))
		_npc_dialog_btns.add_child(btn)

	var leave_btn := Button.new()
	leave_btn.text = "Leave"
	leave_btn.pressed.connect(func(): _npc_dialog.visible = false)
	_npc_dialog_btns.add_child(leave_btn)

	_npc_dialog.visible = true


func _npc_actions_for(encounter_id: String) -> Array:
	match encounter_id:
		"jon_shop":
			return [
				{"label": "Browse Shop",  "method": "GET",  "path": "/npc/jon/inventory"},
				{"label": "Buy Cactus",   "method": "POST", "path": "/npc/jon/cactus",  "body": {"item": "cactus"}},
			]
		"samael_lore":
			return [
				{"label": "Consult Oracle", "method": "POST", "path": "/npc/samael/consult", "body": {"category": "general", "question": "What should we know?"}},
			]
		"haylie_inn":
			return [
				{"label": "Visit Inn", "method": "GET", "path": "/npc/haylie/inn"},
			]
		"danna_audience":
			return [
				{"label": "Address Queen",  "method": "POST", "path": "/npc/danna/address",  "body": {"form": "formal"}},
				{"label": "File Petition",  "method": "POST", "path": "/npc/danna/petition", "body": {"type": "request"}},
			]
		"redvelvet_performance":
			return [
				{"label": "Watch Performance", "method": "POST", "path": "/npc/redvelvet/perform"},
				{"label": "Tip RedVelvet",      "method": "POST", "path": "/npc/redvelvet/tip", "body": {"amount": 5}},
				{"label": "Request Song",       "method": "POST", "path": "/npc/redvelvet/request-song", "body": {"song": "something haunting"}},
			]
		"kodrik_guild":
			return [
				{"label": "Guild Dispatch", "method": "POST", "path": "/npc/kodrik/dispatch"},
				{"label": "Request Repair", "method": "POST", "path": "/npc/kodrik/repair", "body": {"item": "armor"}},
			]
		"bryne_warden":
			return [
				{"label": "Seek Report",  "method": "GET",  "path": "/npc/bryne/observation"},
				{"label": "Call Cole",    "method": "POST", "path": "/npc/bryne/cole-lean"},
			]
		"nathis_frontman":
			return [
				{"label": "Get Report",  "method": "GET",  "path": "/npc/nathis/report"},
				{"label": "Tyty Speaks", "method": "POST", "path": "/npc/nathis/tyty-bark"},
			]
		# ── Pets ────────────────────────────────────────────────────
		"pet_keeva":
			return [{"label": "Rest in Her Light", "method": "POST", "path": "/npc/pet/keeva/interact"}]
		"pet_teddy":
			return [{"label": "Play with Teddy",   "method": "POST", "path": "/npc/pet/teddy/interact"}]
		"pet_cyrus":
			return [{"label": "Approach Cyrus",    "method": "POST", "path": "/npc/pet/cyrus/interact"}]
		"pet_bink_bink":
			return [{"label": "Observe the Interval", "method": "POST", "path": "/npc/pet/bink_bink/interact"}]
		"pet_cole":
			return [{"label": "Receive the Lean",  "method": "POST", "path": "/npc/pet/cole/interact"}]
		"pet_coco":
			return [{"label": "Pet Coco",          "method": "POST", "path": "/npc/pet/coco/interact"}]
		"pet_tyty":
			return [{"label": "Greet the Herald",  "method": "POST", "path": "/npc/pet/tyty/interact"}]
		"pet_snowie":
			return [{"label": "Meet the Sentinel", "method": "POST", "path": "/npc/pet/snowie/interact"}]
		_:
			return []


func _npc_do_action(act: Dictionary) -> void:
	var pc = get_node_or_null("/root/PythonClient")
	if not pc:
		return
	_npc_dialog_resp.text = "[color=#888888][i]...[/i][/color]"

	var http: HTTPRequest
	if act.get("method", "GET") == "GET":
		http = pc.get_request(act["path"])
	else:
		http = pc.post_request(act["path"], act.get("body", {}))

	http.request_completed.connect(func(_r, code, _h, body):
		var resp = JSON.parse_string(body.get_string_from_utf8())
		if resp is Dictionary:
			var narrative: String = (
				resp.get("narrative", "") or
				resp.get("flavor", "") or
				resp.get("result", "") or
				resp.get("observation", "") or
				resp.get("report", "") or
				resp.get("address", "") or
				resp.get("performance", "") or
				""
			)
			if narrative.is_empty():
				# Flatten any string value from the response
				for v in resp.values():
					if v is String and not v.is_empty():
						narrative = v
						break
			if not narrative.is_empty():
				_npc_dialog_resp.text = "[color=#e8d9b0]%s[/color]" % narrative
			else:
				_npc_dialog_resp.text = "[color=#888888]...[/color]"
		http.queue_free()
	)


func _show_combat_result(data: Dictionary) -> void:
	if not _combat_overlay or not _combat_label:
		return

	var txt := "[center][b]⚔  COMBAT  ⚔[/b][/center]\n\n"

	var pa: Dictionary = data.get("player_attack", {})
	if not pa.is_empty():
		var color := "#ff9966" if pa.get("hit", false) else "#888888"
		txt += "[color=%s]%s[/color]\n" % [color, pa.get("hint", "")]

	if data.get("enemy_died", false):
		txt += "\n[color=#ffdd44][b]Enemy defeated! +%d XP[/b][/color]\n" % data.get("xp_reward", 0)
	else:
		var ea: Dictionary = data.get("enemy_attack", {})
		if not ea.is_empty():
			var color := "#ff5555" if ea.get("hit", false) else "#888888"
			txt += "[color=%s]%s[/color]\n" % [color, ea.get("hint", "")]
		var enemy_hp: int = data.get("enemy_hp", 0)
		txt += "\n[color=#888888]Enemy HP remaining: %d[/color]" % enemy_hp

	txt += "\n\n[color=#555555][i]Click or wait to dismiss[/i][/color]"

	_combat_label.text = txt
	_combat_overlay.visible = true
	_combat_timer = COMBAT_OVERLAY_DURATION


func _get_any_player_id() -> String:
	if _selected_cid != "":
		return _selected_cid
	if not _character_data.is_empty():
		return _character_data.keys()[0]
	return ""


func _select_mini(cid: String) -> void:
	if _selected_cid != "" and _selected_cid in _miniatures:
		_miniatures[_selected_cid].deselect()
	_selected_cid = cid
	_miniatures[cid].select()
	_show_stat_panel(cid)


func _deselect_mini() -> void:
	if _selected_cid != "" and _selected_cid in _miniatures:
		_miniatures[_selected_cid].deselect()
	_selected_cid = ""
	if _stat_panel:
		_stat_panel.visible = false


func _show_stat_panel(cid: String) -> void:
	if not _stat_panel or not _stat_label:
		return
	var d: Dictionary = _character_data.get(cid, {})
	if d.is_empty():
		return

	var ab: Dictionary = d.get("abilities", {})
	var inv: Array     = d.get("inventory", [])

	var txt := ""
	txt += "[b]%s[/b]\n" % d.get("name", cid)
	txt += "[color=#888888]%s — %s — %s[/color]\n\n" % [
		str(d.get("race", "?")).replace("_", " ").capitalize(),
		str(d.get("evolution_state", "?")).replace("_", " ").capitalize(),
		str(d.get("predator_role",  "?")).replace("_", " ").capitalize(),
	]
	txt += "[b]HP[/b]  %d / %d    [b]AC[/b]  %d    [b]Spd[/b]  %dft\n\n" % [
		d.get("hp_current", 0), d.get("hp_max", 0),
		d.get("armor_class", 10), d.get("speed", 30),
	]
	txt += "[b]STR[/b] %2d   [b]DEX[/b] %2d   [b]CON[/b] %2d\n" % [
		ab.get("STR", 10), ab.get("DEX", 10), ab.get("CON", 10),
	]
	txt += "[b]INT[/b] %2d   [b]WIS[/b] %2d   [b]CHA[/b] %2d\n\n" % [
		ab.get("INT", 10), ab.get("WIS", 10), ab.get("CHA", 10),
	]
	if inv.size() > 0:
		txt += "[b]Inventory:[/b]\n"
		for item in inv.slice(0, 6):
			txt += "  • %s\n" % str(item.get("name", item) if item is Dictionary else item)

	_stat_label.text = txt
	_stat_panel.visible = true


# ─── Particles ──────────────────────────────────────────────────────

func _on_paradox_triggered():
	if _paradox_scene:
		var inst = _paradox_scene.instantiate()
		particles_root.add_child(inst)
		inst.position = _cam_target
		AudioManager.play_sfx("res://assets/audio/sfx_paradox.wav")

func _on_phase_changed(new_phase: String):
	print("[Tabletop] Phase changed to: ", new_phase)

func _on_npc_event(event: Dictionary):
	print("[Tabletop] NPC event: ", event)

func _on_particle_event(event: Dictionary):
	var type = event.get("type", "magic_burst")
	var pos  = event.get("position", {"x":0, "y":0})
	var world_pos = _grid_to_world(Vector2(pos.x, pos.y))
	
	if type == "magic_burst":
		spawn_magic_burst(world_pos)

func spawn_magic_burst(world_pos: Vector3):
	if _magic_burst_scene:
		var inst = _magic_burst_scene.instantiate()
		particles_root.add_child(inst)
		inst.position = world_pos + Vector3(0, 0.5, 0)


# ─── Environment setup ──────────────────────────────────────────────

func _setup_environment() -> void:
	_env = Environment.new()
	_env.background_mode        = Environment.BG_COLOR
	_env.background_color       = Color(0.02, 0.02, 0.03)
	_env.ambient_light_source   = Environment.AMBIENT_SOURCE_COLOR
	_env.ambient_light_color    = Color(0.08, 0.09, 0.12)
	_env.ambient_light_energy   = 0.8

	# Distance fog — makes the void outside rooms fade to near-black
	_env.fog_enabled            = true
	_env.fog_light_color        = Color(0.04, 0.04, 0.06)
	_env.fog_light_energy       = 1.0
	_env.fog_density            = 0.040

	# Bloom — only emissive surfaces glow; threshold kept high to avoid blowout
	_env.glow_enabled           = true
	_env.glow_intensity         = 0.45
	_env.glow_bloom             = 0.05
	_env.glow_hdr_threshold     = 1.0
	_env.glow_hdr_scale         = 2.0

	# SSAO — adds depth to wall/floor crevices
	_env.ssao_enabled           = true
	_env.ssao_radius            = 1.0
	_env.ssao_intensity         = 1.8
	_env.ssao_power             = 1.5

	# Filmic tone mapping — prevents over-bright washed-out look
	_env.tonemap_mode           = Environment.TONE_MAPPER_FILMIC
	_env.tonemap_exposure       = 0.9

	_world_env = WorldEnvironment.new()
	_world_env.name = "WorldEnvironment"
	_world_env.environment = _env
	add_child(_world_env)

	# Key light — warm directional from upper-front-right, casts shadows
	_key_light = DirectionalLight3D.new()
	_key_light.name = "KeyLight"
	_key_light.rotation_degrees = Vector3(-55.0, 30.0, 0.0)
	_key_light.light_color      = Color(1.0, 0.88, 0.70)
	_key_light.light_energy     = 1.1
	_key_light.shadow_enabled   = true
	add_child(_key_light)

	# Fill light — cool bounce from below-back, no shadow
	var fill := DirectionalLight3D.new()
	fill.name = "FillLight"
	fill.rotation_degrees = Vector3(25.0, -160.0, 0.0)
	fill.light_color      = Color(0.40, 0.50, 0.80)
	fill.light_energy     = 0.20
	fill.shadow_enabled   = false
	add_child(fill)


func _set_room_atmosphere(room_id: String) -> void:
	if not _env or not _key_light:
		return
	var atmo: Dictionary = ROOM_ATMOSPHERE.get(room_id, _ATMO_DEFAULT)
	var tw := create_tween().set_parallel(true)
	tw.tween_property(_env,       "fog_light_color",    atmo["fog"],     1.5)
	tw.tween_property(_env,       "fog_density",        atmo["fog_d"],   1.5)
	tw.tween_property(_env,       "ambient_light_color", atmo["ambient"], 1.5)
	tw.tween_property(_key_light, "light_color",        atmo["key"],     1.5)
	tw.tween_property(_key_light, "light_energy",       atmo["key_e"],   1.5)


# ─── Cave void outside rooms ─────────────────────────────────────────

func _build_void_floor(w: int, h: int) -> void:
	var cx := (w - 1) * CELL_SIZE * 0.5
	var cz := (h - 1) * CELL_SIZE * 0.5
	var size: float = float(maxi(w, h)) * CELL_SIZE * 6.0

	# Large dark cavern floor extending beyond room bounds
	var void_sm := ShaderMaterial.new()
	void_sm.shader = Shader.new()
	void_sm.shader.code = """
shader_type spatial;
void fragment() {
	vec2 uv   = UV * 10.0;
	vec2 tile = floor(uv);
	float n   = fract(sin(dot(tile, vec2(127.1, 311.7))) * 43758.5453);
	ALBEDO    = vec3(0.06, 0.055, 0.05) * (0.65 + n * 0.35);
	ROUGHNESS = 0.96;
	METALLIC  = 0.0;
}
"""
	var plane := PlaneMesh.new()
	plane.size = Vector2(size, size)
	var void_inst := MeshInstance3D.new()
	void_inst.mesh = plane
	void_inst.material_override = void_sm
	void_inst.position = Vector3(cx, -0.14, cz)
	_dungeon_root.add_child(void_inst)

	# Scatter cave boulders and rubble around the perimeter
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(w * 1000 + h)
	var min_d: float = float(maxi(w, h)) * 0.55 * CELL_SIZE
	var max_d: float = float(maxi(w, h)) * 1.8 * CELL_SIZE

	for _i in range(45):
		var angle := rng.randf() * TAU
		var dist  := rng.randf_range(min_d, max_d)
		var rx := cx + cos(angle) * dist
		var rz2 := cz + sin(angle) * dist
		var rh   := rng.randf_range(0.2, 2.4)
		var rw2  := rng.randf_range(0.3, 1.6)
		var rd   := rng.randf_range(0.3, 1.6)
		var rock_mesh := BoxMesh.new()
		rock_mesh.size = Vector3(rw2, rh, rd)
		var sv := rng.randf_range(0.07, 0.19)
		var rock_mat := StandardMaterial3D.new()
		rock_mat.albedo_color = Color(sv, sv * 0.94, sv * 0.86)
		rock_mat.roughness    = rng.randf_range(0.85, 0.97)
		var rock_inst := MeshInstance3D.new()
		rock_inst.mesh = rock_mesh
		rock_inst.material_override = rock_mat
		rock_inst.position = Vector3(rx, rh * 0.5 - 0.13, rz2)
		rock_inst.rotation_euler.y = rng.randf() * TAU
		_dungeon_root.add_child(rock_inst)

	# Stalactites hanging from ceiling
	for _j in range(22):
		var angle := rng.randf() * TAU
		var dist  := rng.randf_range(min_d * 0.65, max_d)
		var sx := cx + cos(angle) * dist
		var sz2 := cz + sin(angle) * dist
		var sh   := rng.randf_range(0.25, 1.6)
		var sr   := rng.randf_range(0.05, 0.20)
		var stala := CylinderMesh.new()
		stala.top_radius    = 0.0
		stala.bottom_radius = sr
		stala.height        = sh
		stala.radial_segments = 5
		var sv2 := rng.randf_range(0.10, 0.24)
		var sm2 := StandardMaterial3D.new()
		sm2.albedo_color = Color(sv2, sv2 * 0.92, sv2 * 0.84)
		sm2.roughness    = 0.90
		var si := MeshInstance3D.new()
		si.mesh = stala
		si.material_override = sm2
		si.position = Vector3(sx, 2.5 - sh * 0.5, sz2)
		_dungeon_root.add_child(si)


# ─── Wall torches ────────────────────────────────────────────────────

func _add_room_torches(cells: Array, w: int, h: int) -> void:
	var torch_pos: Array[Vector3] = []

	# Room corners (if floor)
	for corner in [[1, 1], [w - 2, 1], [1, h - 2], [w - 2, h - 2]]:
		var tx: int = corner[0]
		var ty: int = corner[1]
		var idx := ty * w + tx
		if idx < cells.size():
			var t: String = cells[idx].get("terrain", "floor")
			if t in ["floor", "difficult", "table"]:
				torch_pos.append(Vector3(tx * CELL_SIZE, 1.5, ty * CELL_SIZE))

	# Wall cells adjacent to floor — thin-out to avoid saturation
	for y in range(h):
		for x in range(w):
			if torch_pos.size() >= 14:
				break
			var idx := y * w + x
			if idx >= cells.size():
				continue
			if cells[idx].get("terrain", "floor") != "wall":
				continue
			if (x + y) % 5 != 0:
				continue
			for off in [[0,1],[0,-1],[1,0],[-1,0]]:
				var nx2: int = x + int(off[0])
				var ny2: int = y + int(off[1])
				var ni: int  = ny2 * w + nx2
				if nx2 >= 0 and nx2 < w and ny2 >= 0 and ny2 < h and ni < cells.size():
					if cells[ni].get("terrain", "floor") in ["floor", "door"]:
						torch_pos.append(Vector3(x * CELL_SIZE, 1.4, y * CELL_SIZE))
						break

	for tp in torch_pos:
		# Warm flickering OmniLight
		var light := OmniLight3D.new()
		light.light_color  = Color(1.0, 0.60, 0.20)
		light.light_energy = 1.6
		light.omni_range   = 3.8
		light.shadow_enabled = false
		light.position = tp
		_dungeon_root.add_child(light)

		# Small CPU flame particle — no scene file needed
		var flame := CPUParticles3D.new()
		flame.emitting           = true
		flame.amount             = 14
		flame.lifetime           = 0.45
		flame.explosiveness      = 0.0
		flame.randomness         = 0.65
		flame.direction          = Vector3(0, 1, 0)
		flame.spread             = 22.0
		flame.gravity            = Vector3(0, 0.4, 0)
		flame.initial_velocity_min = 0.4
		flame.initial_velocity_max = 1.0
		flame.scale_amount_min   = 0.04
		flame.scale_amount_max   = 0.09
		flame.color              = Color(1.0, 0.50, 0.10, 0.85)
		flame.position           = tp + Vector3(0, 0.12, 0)
		_dungeon_root.add_child(flame)


# ─── Hit sparks ──────────────────────────────────────────────────────

func _spawn_hit_sparks(world_pos: Vector3) -> void:
	var sparks := CPUParticles3D.new()
	sparks.position          = world_pos + Vector3(0, 0.55, 0)
	sparks.emitting          = true
	sparks.one_shot          = true
	sparks.amount            = 22
	sparks.lifetime          = 0.55
	sparks.explosiveness     = 0.88
	sparks.direction         = Vector3(0, 1, 0)
	sparks.spread            = 75.0
	sparks.gravity           = Vector3(0, -9.8, 0)
	sparks.initial_velocity_min = 2.5
	sparks.initial_velocity_max = 5.5
	sparks.scale_amount_min  = 0.03
	sparks.scale_amount_max  = 0.07
	sparks.color             = Color(1.0, 0.70, 0.15)
	add_child(sparks)
	get_tree().create_timer(1.5).timeout.connect(sparks.queue_free)


# ─── Enemy HP bar ────────────────────────────────────────────────────

# ─── Key binding helpers ─────────────────────────────────────────────

func _cycle_character(forward: bool) -> void:
	if _character_data.is_empty():
		return
	var keys := _character_data.keys()
	if _selected_cid.is_empty():
		_select_mini(keys[0])
		return
	var idx: int = keys.find(_selected_cid)
	if idx == -1:
		_select_mini(keys[0])
		return
	idx = (idx + (1 if forward else keys.size() - 1)) % keys.size()
	_select_mini(keys[idx])


func _select_character_by_slot(slot: int) -> void:
	var keys := _character_data.keys()
	if slot < keys.size():
		_select_mini(keys[slot])


func _interact_adjacent() -> void:
	if _selected_cid.is_empty():
		return
	var cdata: Dictionary = _character_data.get(_selected_cid, {})
	var pos = cdata.get("position", null)
	if pos == null:
		return
	var cx: int = int(pos.get("x", 0))
	var cy: int = int(pos.get("y", 0))
	var pc = get_node_or_null("/root/PythonClient")
	if not pc:
		return

	for off in [[0, -1], [0, 1], [-1, 0], [1, 0]]:
		var nx: int = cx + int(off[0])
		var ny: int = cy + int(off[1])
		if nx < 0 or ny < 0 or nx >= _room_width or ny >= _room_height:
			continue
		var cell_key := "%d,%d" % [nx, ny]

		if cell_key in _npc_cells:
			_do_interact_npc(_npc_cells[cell_key], nx, ny, _selected_cid)
			return

		var tidx: int = ny * _room_width + nx
		if tidx < _room_cells.size():
			var t: String = _room_cells[tidx].get("terrain", "floor")
			if t == "door":
				var http = pc.post_request("/action/grid", {
					"actor_id": _selected_cid, "type": "interact",
					"target": {"x": nx, "y": ny}
				})
				http.request_completed.connect(func(_r, _c, _h, body):
					var resp = JSON.parse_string(body.get_string_from_utf8())
					if resp and resp.has("room_transition"):
						pc.fetch_full_state()
					http.queue_free()
				)
				return


func _open_freeform() -> void:
	if _selected_cid.is_empty():
		if not _character_data.is_empty():
			_select_mini(_character_data.keys()[0])
		else:
			return
	if _freeform_bar:
		_freeform_bar.visible = true
		_freeform_input.clear()
		_freeform_input.grab_focus()


func _on_freeform_submitted(text: String) -> void:
	_freeform_bar.visible = false
	if text.strip_edges().is_empty() or _selected_cid.is_empty():
		return
	var pc = get_node_or_null("/root/PythonClient")
	if not pc:
		return
	_freeform_input.editable = false
	var http = pc.post_request("/action/freeform", {
		"actor_id": _selected_cid, "text": text.strip_edges()
	})
	http.request_completed.connect(func(_r, code, _h, body):
		_freeform_input.editable = true
		if code >= 200 and code < 300:
			var resp = JSON.parse_string(body.get_string_from_utf8())
			if resp is Dictionary and _narrative_box:
				var nar: String = resp.get("narrative", "")
				if not nar.is_empty():
					_narrative_box.append_text("\n[color=#e8d9b0]%s[/color]" % nar)
		http.queue_free()
	)


func _setup_freeform_bar() -> void:
	_freeform_bar = PanelContainer.new()
	_freeform_bar.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	_freeform_bar.offset_top    = -58
	_freeform_bar.offset_bottom = -8
	_freeform_bar.offset_left   = 80
	_freeform_bar.offset_right  = -80
	_freeform_bar.visible = false

	var bg := StyleBoxFlat.new()
	bg.bg_color = Color(0.08, 0.07, 0.06, 0.92)
	bg.border_color = Color(0.5, 0.4, 0.25)
	bg.set_border_width_all(1)
	bg.set_corner_radius_all(4)
	_freeform_bar.add_theme_stylebox_override("panel", bg)

	var hbox := HBoxContainer.new()
	hbox.add_theme_constant_override("separation", 10)
	var lbl := Label.new()
	lbl.text = "Action:"
	lbl.add_theme_font_size_override("font_size", 18)
	lbl.add_theme_color_override("font_color", Color(0.9, 0.75, 0.4))
	hbox.add_child(lbl)

	_freeform_input = LineEdit.new()
	_freeform_input.placeholder_text = "Describe what you do…  (Enter to send, Esc to cancel)"
	_freeform_input.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_freeform_input.add_theme_font_size_override("font_size", 18)
	_freeform_input.text_submitted.connect(_on_freeform_submitted)
	hbox.add_child(_freeform_input)

	_freeform_bar.add_child(hbox)
	_ui_layer.add_child(_freeform_bar)


func _setup_keyhints() -> void:
	var strip := Label.new()
	strip.text = "Arrows: Move   E: Interact   F: Freeform action   Tab: Next character   1-4: Select   I: Stats   M: Map   R: Reset camera"
	strip.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	strip.offset_top    = -28
	strip.offset_bottom = -6
	strip.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	strip.add_theme_font_size_override("font_size", 13)
	strip.add_theme_color_override("font_color", Color(0.7, 0.65, 0.55, 0.60))
	_ui_layer.add_child(strip)


func _add_enemy_hp_bar(root: Node3D, hp: int, hp_max: int) -> void:
	var bar := Node3D.new()
	bar.name = "HPBar"
	bar.position = Vector3(0.0, 1.35, 0.0)

	var frac: float = clamp(float(hp) / float(maxi(1, hp_max)), 0.0, 1.0)
	var bar_w := 0.62

	# Background (dark maroon)
	var bg := MeshInstance3D.new()
	var bg_mesh := QuadMesh.new()
	bg_mesh.size = Vector2(bar_w + 0.04, 0.085)
	bg.mesh = bg_mesh
	var bg_mat := StandardMaterial3D.new()
	bg_mat.albedo_color  = Color(0.22, 0.02, 0.02, 0.92)
	bg_mat.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
	bg_mat.no_depth_test  = true
	bg_mat.shading_mode   = BaseMaterial3D.SHADING_MODE_UNSHADED
	bg_mat.transparency   = BaseMaterial3D.TRANSPARENCY_ALPHA
	bg.material_override  = bg_mat
	bar.add_child(bg)

	# Foreground fill (green → red by remaining HP)
	if frac > 0.0:
		var fg := MeshInstance3D.new()
		var fg_mesh := QuadMesh.new()
		fg_mesh.size = Vector2(bar_w * frac, 0.075)
		fg.mesh = fg_mesh
		var c := Color(1.0 - frac, frac * 0.85, 0.05, 1.0)
		var fg_mat := StandardMaterial3D.new()
		fg_mat.albedo_color   = c
		fg_mat.emission_enabled = true
		fg_mat.emission        = c * 0.5
		fg_mat.billboard_mode  = BaseMaterial3D.BILLBOARD_ENABLED
		fg_mat.no_depth_test   = true
		fg_mat.shading_mode    = BaseMaterial3D.SHADING_MODE_UNSHADED
		fg.material_override   = fg_mat
		# Offset so it fills from the left edge
		fg.position.x = -(bar_w * (1.0 - frac)) * 0.5
		bar.add_child(fg)

	root.add_child(bar)
