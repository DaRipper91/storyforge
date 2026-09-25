class_name HealingPotion
extends ItemEvent

func can_use(_item: Item, _user: Node) -> bool:
	return true

func on_use(_item: Item, _user: Node) -> bool:
	# Add logic for use, e.g. heal user or send a command
	print("Health Potion used!")
	return true
