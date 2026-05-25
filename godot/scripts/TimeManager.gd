extends Node
# TimeManager.gd - Autoloaded global time system

signal time_changed(day: int, hour: int, minute: int)
signal period_changed(is_day: bool)

var day: int = 1
var hour: int = 6 # Start at 6 AM
var minute: int = 0

var time_scale: float = 12.0 # 1 real minute = 12 in-game minutes (1 hour = 5 mins)
var is_day: bool = true

func _process(delta: float) -> void:
	var total_minutes = minute + (delta * time_scale)
	
	if total_minutes >= 60:
		minute = int(total_minutes) % 60
		_increment_hour()
	else:
		minute = int(total_minutes)
	
	time_changed.emit(day, hour, minute)

func _increment_hour():
	hour += 1
	if hour >= 24:
		hour = 0
		day += 1
	
	# Transition lighting periods
	var was_day = is_day
	is_day = (hour >= 6 and hour < 20)
	if was_day != is_day:
		period_changed.emit(is_day)

func get_time_string() -> String:
	var ampm = "AM" if hour < 12 else "PM"
	var display_hour = hour % 12
	if display_hour == 0: display_hour = 12
	return "Day %d - %d:%02d %s" % [day, display_hour, minute, ampm]
