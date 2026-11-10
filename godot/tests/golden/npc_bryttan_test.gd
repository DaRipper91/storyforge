extends SceneTree
## End-to-end check for Bryttan's seeded NPC data, shared rig, visual variant and token hookup.

const NPC_ID := "bryttan_wolfholt"
const NPC_KEY := "npc_bryttan_wolfholt"
const RACE_MINI := preload("res://scenes/RaceMini.tscn")

var _checks := 0
var _fails := 0


func _initialize() -> void:
	call_deferred("_run")


func _check(label: String, ok: bool, detail: String = "") -> void:
	_checks += 1
	if ok:
		print("  ok   ", label)
	else:
		_fails += 1
		printerr("  FAIL ", label, " ", detail)


func _run() -> void:
	await process_frame
	var state := SeedCampaignData.get_state()
	var npc: Dictionary = state.get("npcs", {}).get(NPC_ID, {})
	_check("seed contains Bryttan Wolfholt", npc.get("name", "") == "Bryttan Wolfholt")
	_check("seed routes her through the NPC visual key", npc.get("sprite_key", "") == NPC_KEY)
	_check("NPC is placed in Ironhold Keep", npc.get("room_id", "") == "ironhold_keep")
	_check("NPC remains interactable", npc.get("interactable", false))

	var mini := RACE_MINI.instantiate() as RaceMini
	root.add_child(mini)
	mini.setup(NPC_KEY, npc.get("name", "Bryttan Wolfholt"), false)
	var model := ModelLibrary.instantiate_for_key(NPC_KEY, NPC_ID)
	_check("ModelLibrary resolves the bespoke NPC appearance", model != null)
	if model == null:
		_finish()
		return
	mini.use_model(model, Color("#1b4f9c"), false)
	await process_frame
	_check("RaceMini accepts the model", mini.has_model())
	var skeletons := model.find_children("*", "Skeleton3D", true, false)
	_check("NPC model keeps its shared humanoid skeleton", not skeletons.is_empty())
	if not skeletons.is_empty():
		var skeleton := skeletons[0] as Skeleton3D
		_check("procedural humanoid animation supports this skeleton",
			HumanoidAnimLibrary.is_compatible(skeleton) and skeleton.get_bone_count() == 49)
	var anim := ModelLibrary.find_anim_player(model)
	_check("NPC model receives an idle clip", ModelLibrary.find_clip(anim, "idle") != "")
	_check("NPC model receives an interaction clip", ModelLibrary.find_clip(anim, "talk") != "")
	_check("model includes the signature wolf crest",
		model.find_child("WolfCrest", true, false) != null)
	_check("model includes the cobalt pack core",
		model.find_child("CobaltPowerCore", true, false) != null)
	_check("model includes the rune dagger", model.find_child("RunedBlade", true, false) != null)
	mini.play_talk()
	_check("NPC token plays its interaction animation", anim != null and anim.is_playing())

	_finish()


func _finish() -> void:
	print("%d checks, %d failed" % [_checks, _fails])
	print("RESULT: %s" % ("OK" if _fails == 0 else "FAILED"))
	quit(0 if _fails == 0 else 1)
