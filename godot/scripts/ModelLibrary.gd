class_name ModelLibrary
extends RefCounted
## Resolves tokens (players, NPCs, enemies) to GLB models and normalises
## animation clip names across the asset packs in res://assets/models/.
##
## Lookup order for every token — first usable hit wins:
##   1. characters/<id>.glb            bespoke model for one named entity
##   2. SPRITE_MODELS[key]             archetype (humanoid/, animals/, enemies/, dragons/)
##   3. player/<race_id>.glb           per-race override
##   4. player/<race group>.glb        group body
##   5. (none)                         caller keeps the RaceMini primitive recipe
##
## A rigged model is only "usable" if it ships an idle clip. The humanoid/ and
## player/ packs are rigged but have no clips yet, so they rest in a T-pose;
## they are skipped until animated versions are dropped in.

const MODEL_ROOT := "res://assets/models/"

## Standing height (metres, on a 1 m grid cell) used when nothing else says.
const DEFAULT_HEIGHT := 0.9

## Archetype table. "path" is relative to MODEL_ROOT without ".glb".
## "height" is the mini's standing height after normalisation.
const SPRITE_MODELS := {
	# Named NPCs
	"npc_kodrik":     {"path": "humanoid/npc_warrior",   "height": 0.95},
	"npc_danna":      {"path": "humanoid/npc_royal",     "height": 0.90},
	"npc_jon":        {"path": "humanoid/npc_default",   "height": 0.90},
	"npc_haylie":     {"path": "humanoid/npc_default",   "height": 0.88},
	"npc_samael":     {"path": "humanoid/npc_mage",      "height": 0.95},
	"npc_cinder":     {"path": "humanoid/npc_performer", "height": 0.90},
	"npc_bryne":      {"path": "humanoid/npc_default",   "height": 0.90},
	"npc_nathis":     {"path": "humanoid/npc_default",   "height": 0.90},
	# Mykael: the codex describes a large man, so a wide warrior, not a bear.
	"npc_bear":       {"path": "humanoid/npc_warrior",   "height": 1.00},
	"npc_mykael":     {"path": "humanoid/npc_warrior",   "height": 1.00},
	# Beasts
	"npc_dog":        {"path": "animals/dog",  "height": 0.45},
	"npc_dog_black":  {"path": "animals/dog",  "height": 0.50},
	"npc_teddy":      {"path": "animals/dog",  "height": 0.35},
	"npc_wolf":       {"path": "animals/wolf", "height": 0.80},
	"npc_cat":        {"path": "animals/cat",  "height": 0.30},
	"npc_cat_white":  {"path": "animals/cat",  "height": 0.30},
	"npc_cat_black":  {"path": "animals/cat",  "height": 0.30},
	# Enemies by kind (matched from the enemy id stem, e.g. "ghoul_01" → "ghoul")
	"skeleton":       {"path": "enemies/skeleton",       "height": 0.90},
	"ghoul":          {"path": "enemies/ghoul",          "height": 0.90},
	"bandit":         {"path": "enemies/bandit",         "height": 0.90},
	"thug":           {"path": "enemies/thug",           "height": 0.95},
	"animated_armor": {"path": "enemies/animated_armor", "height": 1.00},
	"shadow":         {"path": "enemies/shadow",         "height": 0.90},
	"race_enemy":     {"path": "enemies/race_enemy",     "height": 0.90},
	# Enemies by sprite_key, as the seed and character_factory emit them
	"enemy_humanoid":  {"path": "enemies/bandit",         "height": 0.90},
	"enemy_undead":    {"path": "enemies/skeleton",       "height": 0.90},
	"enemy_construct": {"path": "enemies/animated_armor", "height": 1.00},
	"enemy_race":      {"path": "enemies/race_enemy",     "height": 0.90},
	# Dragons
	"dragon_red":     {"path": "dragons/dragon_red",   "height": 1.60},
	"dragon_green":   {"path": "dragons/dragon_green", "height": 1.60},
	"dragon_blue":    {"path": "dragons/dragon_blue",  "height": 1.60},
	"dragon_black":   {"path": "dragons/dragon_black", "height": 1.60},
	"dragon_white":   {"path": "dragons/dragon_white", "height": 1.60},
	"dragon_gold":    {"path": "dragons/dragon_gold",  "height": 1.60},
	"dragon_whelp":   {"path": "dragons/dragon_whelp", "height": 0.90},
}

const RACE_GROUPS := {
	"cosmic":     ["voidwraith", "nullshade", "ironlocust", "embervein", "riftwalker"],
	"primal":     ["solarlord", "thornmimic", "cinderkin", "deeptyrant", "grimcrow"],
	"eldritch":   ["bloodweaver", "dreamhusk", "bonedrifter", "mindspider", "chaosling"],
	"mechanical": ["ironveil", "forgespawn", "cinderplate", "hexgear", "wirewraith"],
	"humanoid":   ["ashenborn", "hollowsong", "veilborn", "thornweft", "ashcrown",
		"ironfast", "coreborn", "warpbred", "splitblood", "duskweft", "glitchkin",
		"fractureline", "emberpact", "fallenlight", "scaleworn"],
}

## Clip roles → accepted names, in priority order. Names are compared after
## normalise_clip(), so "Idle.021" and "Skeleton_Idle" both match "idle".
const CLIP_ALIASES := {
	"idle":   ["idle", "idle_a", "standing"],
	"walk":   ["walk", "walking", "walk_a", "running", "run", "flying", "fly", "gallop"],
	"talk":   ["interact", "talk", "wave", "pickup", "idle_2"],
	"attack": ["attack", "slash", "attack_a", "attack_headbutt"],
	"death":  ["death", "die", "fall"],
}

const LOOPING_ROLES := ["idle", "walk", "talk"]


# ─── Public API ───────────────────────────────────────────────────────────────

## Model for a named NPC or enemy token. `entity_id` is the seed id
## ("kodrik", "ghoul_01"); `sprite_key` is its sprite_key field.
static func instantiate_for_key(sprite_key: String, entity_id: String = "") -> Node3D:
	var candidates: Array = []
	if not entity_id.is_empty():
		candidates.append({"path": "characters/" + entity_id, "height": _height_for(sprite_key)})
		var stem := _id_stem(entity_id)
		if stem in SPRITE_MODELS:
			candidates.append(SPRITE_MODELS[stem])
	if sprite_key in SPRITE_MODELS:
		candidates.append(SPRITE_MODELS[sprite_key])
	return _first_usable(candidates)


## Model for a player character of the given race.
static func instantiate_for_race(character_id: String, race_id: String) -> Node3D:
	race_id = race_id.to_lower().replace(" ", "_").replace("-", "")
	var candidates: Array = []
	if not character_id.is_empty():
		candidates.append({"path": "characters/" + character_id, "height": DEFAULT_HEIGHT})
	candidates.append({"path": "player/" + race_id, "height": DEFAULT_HEIGHT})
	var group := race_group(race_id)
	if not group.is_empty():
		candidates.append({"path": "player/" + group, "height": DEFAULT_HEIGHT})
	return _first_usable(candidates)


static func race_group(race_id: String) -> String:
	for group in RACE_GROUPS:
		if race_id in RACE_GROUPS[group]:
			return group
	return ""


static func find_anim_player(node: Node) -> AnimationPlayer:
	if node is AnimationPlayer:
		return node as AnimationPlayer
	for child in node.get_children():
		var found := find_anim_player(child)
		if found:
			return found
	return null


## Returns the clip name that fills `role` ("idle", "walk", "talk", "attack",
## "death"), or "" if the player has none.
static func find_clip(ap: AnimationPlayer, role: String) -> String:
	if ap == null:
		return ""
	var clips := ap.get_animation_list()
	for alias in CLIP_ALIASES.get(role, [role]):
		for clip in clips:
			var n := normalise_clip(clip)
			if n == alias or n.ends_with("_" + alias):
				return clip
	return ""


## Plays the clip for `role` if it exists and isn't already playing.
## Returns false when the model has no such clip.
static func play_role(ap: AnimationPlayer, role: String) -> bool:
	var clip := find_clip(ap, role)
	if clip.is_empty():
		return false
	if ap.current_animation != clip:
		ap.play(clip)
	return true


## "Idle.021" / "Idle_021" → "idle", "Skeleton_Idle" → "skeleton_idle",
## "lib/Walk" → "walk". Blender writes duplicate clips as "Name.001"; Godot's
## importer turns the dot into "_". Only 3+ digit suffixes are stripped, so
## real variants like the animals' "Idle_2" survive.
static func normalise_clip(clip_name: String) -> String:
	var n := clip_name.to_lower()
	var slash := n.rfind("/")
	if slash != -1:
		n = n.substr(slash + 1)
	var cut := maxi(n.rfind("."), n.rfind("_"))
	if cut != -1:
		var suffix := n.substr(cut + 1)
		if suffix.length() >= 3 and suffix.is_valid_int():
			n = n.substr(0, cut)
	return n


# ─── Internals ────────────────────────────────────────────────────────────────

static func _first_usable(candidates: Array) -> Node3D:
	for c in candidates:
		var inst := _instantiate(c.get("path", ""), c.get("height", DEFAULT_HEIGHT))
		if inst:
			return inst
	return null


static func _instantiate(rel_path: String, height: float) -> Node3D:
	if rel_path.is_empty():
		return null
	var res_path := MODEL_ROOT + rel_path + ".glb"
	if not ResourceLoader.exists(res_path):
		return null
	var scene := load(res_path) as PackedScene
	if scene == null:
		return null
	var inst := scene.instantiate() as Node3D
	if inst == null:
		return null

	var ap := find_anim_player(inst)
	if _has_skeleton(inst) and find_clip(ap, "idle").is_empty():
		# Rigged but unanimated: it would stand in its T-pose. Skip it.
		inst.free()
		return null

	_normalise_height(inst, height)
	if ap:
		_set_looping(ap)
		play_role(ap, "idle")
	return inst


static func _height_for(sprite_key: String) -> float:
	if sprite_key in SPRITE_MODELS:
		return SPRITE_MODELS[sprite_key].get("height", DEFAULT_HEIGHT)
	return DEFAULT_HEIGHT


## "ghoul_01" → "ghoul", "animated_armor_01" → "animated_armor".
static func _id_stem(entity_id: String) -> String:
	var parts := entity_id.to_lower().split("_")
	if parts.size() > 1 and parts[parts.size() - 1].is_valid_int():
		parts.remove_at(parts.size() - 1)
	return "_".join(parts)


static func _has_skeleton(node: Node) -> bool:
	if node is Skeleton3D:
		return true
	for child in node.get_children():
		if _has_skeleton(child):
			return true
	return false


static func _set_looping(ap: AnimationPlayer) -> void:
	for role in LOOPING_ROLES:
		var clip := find_clip(ap, role)
		if not clip.is_empty():
			var anim := ap.get_animation(clip)
			if anim:
				anim.loop_mode = Animation.LOOP_LINEAR


## Scales `inst` so its visible height equals `height` and its feet sit on y = 0.
static func _normalise_height(inst: Node3D, height: float) -> void:
	var acc := {"found": false, "box": AABB()}
	_accumulate_aabb(inst, Transform3D.IDENTITY, acc)
	if not acc["found"]:
		return
	var box: AABB = acc["box"]
	if box.size.y <= 0.001:
		return
	var s := height / box.size.y
	inst.scale = inst.scale * s
	inst.position.y -= box.position.y * s


static func _accumulate_aabb(node: Node, parent_xform: Transform3D, acc: Dictionary) -> void:
	var xform := parent_xform
	if node is Node3D:
		xform = parent_xform * (node as Node3D).transform
	if node is VisualInstance3D:
		var box: AABB = xform * (node as VisualInstance3D).get_aabb()
		if acc["found"]:
			acc["box"] = (acc["box"] as AABB).merge(box)
		else:
			acc["box"] = box
			acc["found"] = true
	for child in node.get_children():
		_accumulate_aabb(child, xform, acc)
