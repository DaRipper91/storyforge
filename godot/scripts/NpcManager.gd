extends Node
# NpcManager.gd - Handles AI routines and NavMesh pathing for NPCs

var _npc_agents: Dictionary = {} # npc_id -> RaceMini instance

func _ready() -> void:
	var pc = get_node_or_null("/root/PythonClient")
	if pc:
		pc.state_updated.connect(_on_state_updated)

func register_npc(npc_id: String, instance: Node3D) -> void:
	if instance.has_node("NavigationAgent3D"):
		_npc_agents[npc_id] = instance

func clear_npcs() -> void:
	_npc_agents.clear()

func _on_state_updated(state: Dictionary) -> void:
	var npcs = state.get("npcs", {})
	for npc_id in npcs:
		var npc_data = npcs[npc_id]
		if npc_id in _npc_agents:
			var mini = _npc_agents[npc_id]
			if not is_instance_valid(mini):
				continue
			
			# If the NPC has a target_position in their state data
			if npc_data.has("target_position") and npc_data["target_position"] != null:
				var tpos = npc_data["target_position"]
				var world_pos = Vector3(tpos.get("x", 0), 0.05, tpos.get("y", 0))
				
				# Give them a new target
				if mini.has_method("move_towards_target"):
					mini.nav_agent.target_position = world_pos

func _physics_process(delta: float) -> void:
	for npc_id in _npc_agents:
		var mini = _npc_agents[npc_id]
		if not is_instance_valid(mini):
			continue
		# Tell the NPC to move along its path if it has one
		if mini.has_method("move_towards_target") and not mini.nav_agent.is_navigation_finished():
			mini.move_towards_target(delta)
