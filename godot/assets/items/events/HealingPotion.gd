class_name HealingPotion
extends ItemEvent
## Health Potion effect: restores a rolled amount of Life when used.
##
## HP is owned by the Python backend, so this does not touch a hit-point
## property directly. The user node must expose `heal(amount: int) -> void`
## (and may expose `needs_healing() -> bool` to refuse use at full health).
## If the user has no `heal` method the potion is NOT consumed (returns false).

@export var min_heal: int = 1
@export var max_heal: int = 6

func can_use(_item: Item, user: Node) -> bool:
	if user == null or not user.has_method("heal"):
		return false
	if user.has_method("needs_healing"):
		return user.needs_healing()
	return true

func on_use(item: Item, user: Node) -> bool:
	if not can_use(item, user):
		return false
	var amount := randi_range(min_heal, max_heal)
	user.heal(amount)
	return true
