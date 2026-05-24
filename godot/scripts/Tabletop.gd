extends Node3D

@onready var ground_mesh     = $Ground
@onready var camera          = $Camera3D
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
var _mat_wall:      StandardMaterial3D = null
var _mat_floor:     StandardMaterial3D = null
var _mat_door:      StandardMaterial3D = null
var _mat_hazard:    StandardMaterial3D = null
var _mat_pillar:    StandardMaterial3D = null
var _mat_table:     StandardMaterial3D = null
var _mat_difficult: StandardMaterial3D = null

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


# ─── Lifecycle ──────────────────────────────────────────────────────

func _ready():
	_build_materials()
	_setup_ui()

	_dungeon_root = Node3D.new()
	_dungeon_root.name = "DungeonRoot"
	add_child(_dungeon_root)

	# Hide flat ground until we have room data; show it as fallback
	ground_mesh.visible = true

	var pc = get_node_or_null("/root/PythonClient")
	if pc:
		pc.state_updated.connect(_on_state_updated)
		pc.paradox_triggered.connect(_on_paradox_triggered)
		pc.phase_changed.connect(_on_phase_changed)
		pc.npc_event_received.connect(_on_npc_event)
		pc.particle_event_received.connect(_on_particle_event)

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

	# M-key hint (top-right)
	var hint_label := Label.new()
	hint_label.text = "[M] Map"
	hint_label.set_anchors_and_offsets_preset(Control.PRESET_TOP_RIGHT)
	hint_label.offset_left   = -90
	hint_label.offset_top    = 20
	hint_label.offset_right  = -20
	hint_label.offset_bottom = 50
	hint_label.add_theme_font_size_override("font_size", 16)
	hint_label.add_theme_color_override("font_color", Color(0.8, 0.8, 0.8, 0.7))
	_ui_layer.add_child(hint_label)

	_setup_world_map()


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
		var rid_copy := room_id
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
	_mat_wall = StandardMaterial3D.new()
	_mat_wall.albedo_color = Color(0.28, 0.25, 0.22)
	_mat_wall.roughness = 0.9
	_mat_wall.metallic = 0.0

	_mat_floor = StandardMaterial3D.new()
	_mat_floor.albedo_color = Color(0.22, 0.20, 0.18)
	_mat_floor.roughness = 0.85
	_mat_floor.metallic = 0.0

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


# ─── Camera input ───────────────────────────────────────────────────

func _input(event: InputEvent):
	if event is InputEventMouseButton:
		match event.button_index:
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
		match event.keycode:
			KEY_R:
				_cam_yaw      = 0.0
				_cam_pitch    = -45.0
				_cam_distance = 14.14
				_cam_target   = Vector3.ZERO
				_update_camera()
			KEY_M:
				_toggle_world_map()
			KEY_ESCAPE:
				if _world_map_visible:
					_toggle_world_map()


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


# ─── State / miniatures ─────────────────────────────────────────────

func _on_state_updated(new_state: Dictionary):
	var old_room := _current_room_id
	_rebuild_room(new_state)
	# On room transition, clear all minis so they respawn at new positions
	if _current_room_id != old_room and old_room != "":
		for mini in _miniatures.values():
			mini.queue_free()
		_miniatures.clear()
		_selected_cid = ""
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
	var mini: Node3D = _miniatures[character_id]
	var target = _grid_to_world(grid_pos)
	var tween  = create_tween()
	tween.tween_property(mini, "position", target, 0.3).set_trans(Tween.TRANS_SINE)
	spawn_magic_burst(target)
	AudioManager.play_sfx("res://assets/audio/sfx_move.wav")


func _grid_to_world(grid_pos: Vector2) -> Vector3:
	return Vector3(grid_pos.x * CELL_SIZE, MINI_Y, grid_pos.y * CELL_SIZE)


# ─── Click-to-select ────────────────────────────────────────────────

func _input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		_try_select_mini(event.position)


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
	var terrain := cell.get("terrain", "floor")

	# ── 3. Door cell — interact (room transition) ─────────────────────
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

	# ── 4. Floor/difficult cell — move selected character ─────────────
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
