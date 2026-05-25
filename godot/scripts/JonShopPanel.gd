extends Control
## Jon's Multiversal Bodega — dynamic shop panel driven by /api/npc/jon/inventory.
##
## Open: JonShopPanel.open(actor_id, genre)
## Close: Escape or X button.
## Buy: left-click an item slot → confirm dialog → POST /api/npc/jon/buy.

signal shop_closed

const SLOT_SCENE := preload("res://scenes/ui/inventory_slot.tscn")
const COLS := 4
const SLOT_SIZE := Vector2(72, 72)
const SLOT_GAP := 6

@onready var _title_label: Label = $PanelContainer/VBox/Header/TitleLabel
@onready var _close_btn: Button = $PanelContainer/VBox/Header/CloseBtn
@onready var _grid: GridContainer = $PanelContainer/VBox/Body/ScrollContainer/Grid
@onready var _status_label: Label = $PanelContainer/VBox/Footer/StatusLabel
@onready var _gold_label: Label = $PanelContainer/VBox/Footer/GoldLabel
@onready var _confirm_panel: PanelContainer = $ConfirmPanel
@onready var _confirm_label: Label = $ConfirmPanel/VBox/ItemLabel
@onready var _buy_btn: Button = $ConfirmPanel/VBox/Buttons/BuyBtn
@onready var _cancel_btn: Button = $ConfirmPanel/VBox/Buttons/CancelBtn

var _actor_id: String = ""
var _genre: String = "fantasy"
var _items: Array = []
var _selected_item: Dictionary = {}
var _slots: Array = []
var _gold: int = 0

func _ready() -> void:
	_close_btn.pressed.connect(_close)
	_buy_btn.pressed.connect(_confirm_buy)
	_cancel_btn.pressed.connect(func(): _confirm_panel.hide())
	PythonClient.jon_inventory_received.connect(_on_inventory)
	PythonClient.jon_buy_result.connect(_on_buy_result)
	PythonClient.state_updated.connect(_on_state_updated)
	_confirm_panel.hide()
	hide()

func open(actor_id: String, genre: String = "fantasy", gold: int = 0) -> void:
	_actor_id = actor_id
	_genre = genre
	_gold = gold
	_gold_label.text = "Gold: %d" % _gold
	_status_label.text = "Fetching inventory…"
	_clear_slots()
	show()
	PythonClient.fetch_jon_inventory(_genre)

func _close() -> void:
	hide()
	_confirm_panel.hide()
	shop_closed.emit()

func _input(event: InputEvent) -> void:
	if visible and event.is_action_pressed("ui_cancel"):
		if _confirm_panel.visible:
			_confirm_panel.hide()
		else:
			_close()
		accept_event()

# ─── Inventory population ─────────────────────────────────────────

func _on_inventory(items: Array) -> void:
	_items = items
	_clear_slots()
	_status_label.text = "%d items in stock" % items.size()
	for item in items:
		_add_slot(item)

func _clear_slots() -> void:
	for slot in _slots:
		slot.queue_free()
	_slots.clear()

func _add_slot(item: Dictionary) -> void:
	var slot: Panel = SLOT_SCENE.instantiate()
	_grid.add_child(slot)
	_slots.append(slot)

	# Build a minimal label overlay showing name + price
	var label := Label.new()
	label.text = "%s\n%dg" % [item.get("name", "?"), item.get("value", 0)]
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	label.add_theme_font_size_override("font_size", 9)
	label.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	slot.add_child(label)

	# Tooltip on hover
	slot.mouse_entered.connect(_show_tooltip.bind(item))
	slot.mouse_exited.connect(_hide_tooltip)
	slot.gui_input.connect(_on_slot_input.bind(item))

func _show_tooltip(item: Dictionary) -> void:
	_status_label.text = "[%s]  %s" % [item.get("name", ""), item.get("notes", "")]

func _hide_tooltip() -> void:
	_status_label.text = "%d items in stock" % _items.size()

func _on_slot_input(event: InputEvent, item: Dictionary) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		_selected_item = item
		_confirm_label.text = "Buy %s\nfor %d gold?" % [item.get("name", "?"), item.get("value", 0)]
		_confirm_panel.show()

# ─── Buy flow ─────────────────────────────────────────────────────

func _confirm_buy() -> void:
	_confirm_panel.hide()
	if _selected_item.is_empty():
		return
	var cost: int = _selected_item.get("value", 0)
	if _gold < cost:
		_status_label.text = "Not enough gold! (%dg needed)" % cost
		return
	_status_label.text = "Buying…"
	PythonClient.buy_jon_item(_actor_id, _selected_item.get("id", ""), _genre)

func _on_buy_result(success: bool, message: String) -> void:
	if not visible:
		return
	if success:
		_status_label.text = "✓ " + message
		# Refresh inventory after purchase
		PythonClient.fetch_jon_inventory(_genre)
	else:
		_status_label.text = "✗ " + message

func _on_state_updated(state: Dictionary) -> void:
	if not visible:
		return
	# Update gold from current character
	var chars: Array = state.get("characters", [])
	for ch in chars:
		if ch.get("id", "") == _actor_id:
			var inv: Array = ch.get("inventory", [])
			var gold := 0
			for it in inv:
				if it.get("id", "").contains("gold") or it.get("name", "").to_lower().contains("gold"):
					gold += it.get("quantity", 1) * it.get("value", 1)
			_gold = gold
			_gold_label.text = "Gold: %d" % _gold
			break
