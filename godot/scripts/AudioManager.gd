## AudioManager — autoload singleton for all StoryForge audio.
##
## Bus layout (configured in AudioServer at runtime if not set via editor):
##   Master
##   ├── Music   (reverb, low-pass when paused)
##   └── SFX     (slight spatial warmth)
##
## Usage:
##   AudioManager.play_ambient("res://assets/audio/ambient_keep.ogg")
##   AudioManager.play_sfx("res://assets/audio/sfx_move.wav")
##   AudioManager.play_npc_performance()   # triggers Firey RedVelvet audio
##   AudioManager.stop_ambient()
##   AudioManager.set_music_volume(0.8)    # 0.0 – 1.0

extends Node

# ─── Bus indices ────────────────────────────────────────────────────
const _BUS_MUSIC = "Music"
const _BUS_SFX   = "SFX"

# ─── Players ────────────────────────────────────────────────────────
var _ambient_player:     AudioStreamPlayer
var _performance_player: AudioStreamPlayer
var _sfx_pool: Array[AudioStreamPlayer] = []
const _SFX_POOL_SIZE = 6

# ─── State ──────────────────────────────────────────────────────────
var _ambient_volume:  float = 0.8
var _sfx_volume:      float = 1.0
var _is_paused:       bool  = false

# ─── Lifecycle ──────────────────────────────────────────────────────

func _ready():
	_ensure_buses()

	_ambient_player = _make_player(_BUS_MUSIC)
	_performance_player = _make_player(_BUS_MUSIC)

	for i in _SFX_POOL_SIZE:
		_sfx_pool.append(_make_player(_BUS_SFX))


func _make_player(bus: String) -> AudioStreamPlayer:
	var p = AudioStreamPlayer.new()
	p.bus = bus
	add_child(p)
	return p


func _ensure_buses():
	# Create Music and SFX buses if they don't exist in the project
	if AudioServer.get_bus_index(_BUS_MUSIC) == -1:
		AudioServer.add_bus()
		var idx = AudioServer.get_bus_count() - 1
		AudioServer.set_bus_name(idx, _BUS_MUSIC)
		AudioServer.set_bus_send(idx, "Master")
		# Subtle reverb on music bus
		var reverb = AudioEffectReverb.new()
		reverb.room_size = 0.6
		reverb.damping = 0.5
		reverb.wet = 0.25
		AudioServer.add_bus_effect(idx, reverb)

	if AudioServer.get_bus_index(_BUS_SFX) == -1:
		AudioServer.add_bus()
		var idx = AudioServer.get_bus_count() - 1
		AudioServer.set_bus_name(idx, _BUS_SFX)
		AudioServer.set_bus_send(idx, "Master")
		# Warm low-shelf EQ for SFX
		var eq = AudioEffectEQ.new()
		AudioServer.add_bus_effect(idx, eq)


# ─── Ambient / music ────────────────────────────────────────────────

func play_ambient(path: String, fade_in: float = 1.5):
	if not ResourceLoader.exists(path):
		return
	_ambient_player.stream = load(path)
	_ambient_player.volume_db = linear_to_db(0.0)
	_ambient_player.play()
	var tween = create_tween()
	tween.tween_property(
		_ambient_player, "volume_db",
		linear_to_db(_ambient_volume),
		fade_in
	).set_trans(Tween.TRANS_SINE)


func stop_ambient(fade_out: float = 2.0):
	if not _ambient_player.playing:
		return
	var tween = create_tween()
	tween.tween_property(
		_ambient_player, "volume_db",
		linear_to_db(0.0),
		fade_out
	).set_trans(Tween.TRANS_SINE)
	tween.tween_callback(_ambient_player.stop)


# ─── NPC performance (Firey RedVelvet) ──────────────────────────────

func play_npc_performance(path: String = "", mood: String = "warm"):
	# Mood adjusts volume and pitch to match RedVelvet's state
	var pitch_scale = { "cold": 0.95, "warm": 1.0, "hot": 1.02, "blazing": 1.05 }
	var vol_scale   = { "cold": 0.6,  "warm": 0.75, "hot": 0.85, "blazing": 1.0  }

	if path.is_empty() or not ResourceLoader.exists(path):
		return

	_performance_player.stream = load(path)
	_performance_player.pitch_scale = pitch_scale.get(mood, 1.0)
	_performance_player.volume_db   = linear_to_db(vol_scale.get(mood, 0.75))
	_performance_player.play()


func stop_npc_performance():
	_performance_player.stop()


# ─── SFX (pooled) ───────────────────────────────────────────────────

func play_sfx(path: String, volume: float = 1.0):
	if not ResourceLoader.exists(path):
		return
	var player = _get_free_sfx_player()
	if player == null:
		return
	player.stream = load(path)
	player.volume_db = linear_to_db(volume * _sfx_volume)
	player.play()


func _get_free_sfx_player() -> AudioStreamPlayer:
	for p in _sfx_pool:
		if not p.playing:
			return p
	return null


# ─── Volume controls ────────────────────────────────────────────────

func set_music_volume(vol: float):
	_ambient_volume = clamp(vol, 0.0, 1.0)
	if _ambient_player.playing:
		_ambient_player.volume_db = linear_to_db(_ambient_volume)


func set_sfx_volume(vol: float):
	_sfx_volume = clamp(vol, 0.0, 1.0)


# ─── Pause integration ──────────────────────────────────────────────

func set_paused(paused: bool):
	_is_paused = paused
	var bus_idx = AudioServer.get_bus_index(_BUS_MUSIC)
	if bus_idx != -1:
		# Low-pass filter on pause gives a "muffled" effect
		AudioServer.set_bus_volume_db(bus_idx, -6.0 if paused else 0.0)
