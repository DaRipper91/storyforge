# Touch controls

On-screen controls for phones: `godot/scripts/ui/touch_controls.gd` (`class_name TouchControls`, a `CanvasLayer`
built entirely in code, no assets). Tabletop creates it in `_ready` only when `TouchControls.should_show()`.

## When it shows

`should_show()` is true when the `android` or `ios` feature is set, the user arg `--touch` is passed
(`godot --path godot -- --touch`), or env `STORYFORGE_TOUCH=1`. Otherwise desktop behaviour is unchanged.
To eyeball it on a desktop: `STORYFORGE_TOUCH=1 godot --path godot -- --backend=local` (or `-- --touch`).
Real multi-touch needs a touchscreen. With a mouse, the engine does not emit ScreenTouch events (touch-from-mouse is off), so the
on-screen controls will draw but only react to a touchscreen. Forcing it on also hides the "connect a controller" overlay
(a phone has no pad), so it is the quickest way to check layout.

## Action map

| Control | Where | Drives (InputMap action) | What Tabletop does with it |
|---|---|---|---|
| Joystick (floating) | left 40 % of safe area, below the top strip | `move_left/right/up/down` via `Input.action_press(name, strength)` | `Input.get_vector` -> leader movement (camera-relative) |
| Camera drag (1 finger) | right of joystick | `look_left/right/up/down` | right-stick orbit (`yaw -= x*2.5`, `pitch -= y*2.0` per physics frame) |
| Pinch (2 fingers in camera area) | same | synthetic `MOUSE_BUTTON_WHEEL_UP/DOWN` | existing mouse-wheel branch of `Tabletop._input` (`_cam_distance` +-1.2) |
| USE (big, bottom-right) | | `action` | `Interactable` polls it |
| `<` / `>` (top-left) | | `cycle_prev` / `cycle_next` | `_cycle_character` |
| MAP, CAM, SAY (top-right) | | `map` / `reset_cam` / `freeform` | world map, reset camera, freeform text bar |
| Short tap in a zone | joystick/camera zones | replayed as a left mouse click (device 0) | token/NPC selection, UI under the zones |

Buttons send `InputEventAction` through `Input.parse_input_event` (so `Tabletop._input`, which polls
`Input.is_action_just_pressed`, sees the press) and hold the press for at least 60 ms (so `_process` pollers such as
`Interactable` do not miss a quick tap). Analog axes use `action_press` with a strength pre-compensated for the
action dead zone, so `Input.get_vector` returns exactly the intended vector. `RaceMini`/`Tabletop` are unmodified
consumers. Not mapped: `lock_on`, number keys, `I`.

## Mouse-from-touch (what is relied on)

`input_devices/pointing/emulate_mouse_from_touch` is left at its default (true): the first finger also yields
`InputEventMouse*` with `device == InputEvent.DEVICE_ID_EMULATION`, delivered BEFORE the matching `InputEventScreenTouch`
(observed in the headless test). Viewport order is every `_input` (children first), GUI Controls, then unhandled input,
and `Tabletop._input` reads mouse clicks, so `mouse_filter = STOP` alone is too late. TouchControls therefore
(1) consumes its own touches with `set_input_as_handled()`, (2) consumes an emulated mouse press that lands inside any region, plus
the motion and release that follow, (3) keeps a STOP `Control` under every region as a second line of defence,
(4) replays a short, small tap (< 350 ms, < 2.5 mm) in the zones as a synthetic left click through `Viewport.push_input(ev, true)`.
Verified headless with `Input.parse_input_event`: a button touch reaches the world node as nothing; a free-spot touch
still produces the emulated click; a camera-zone tap yields exactly one click; a drag yields none.

## Constants to tune (top of the file)

`BUTTON_MM` 11, `BIG_BUTTON_MM` 15, `MIN_BUTTON_MM` 9 (hard floor, plus `MIN_BUTTON_PX` 48), `GAP_MM` 3, `JOY_RADIUS_MM` 10,
`JOY_DEADZONE` 0.18 (of radius, output re-mapped to 0..1), `JOY_ZONE_FRAC` 0.40, `OPACITY` 0.55,
`CAM_YAW_DEG_PER_PX` 0.30, `CAM_PITCH_DEG_PER_PX` 0.22 (mouse orbit uses 0.25/0.2; full speed is capped by the stick rate, ~150 deg/s
yaw), `LOOK_MIN_LEN` 0.06, `CAM_BACKLOG_PX` 400, `PINCH_STEP_MM` 5, `TAP_MAX_MS` 350, `TAP_SLOP_MM` 2.5,
`BUTTON_MIN_HOLD_MS` 60, `FALLBACK_DPI` 420. Sizes come from `DisplayServer.screen_get_dpi()` divided by the stretch scale.

## Layout and safe area

`compute_layout()` is pure: it takes viewport size, px per mm and the safe rect. The safe rect is
`DisplayServer.get_display_safe_area()` mapped through the stretch scale/letterbox. Note `project.godot` keeps
`aspect=keep`, so a 20:9 phone letterboxes a 16:9 viewport; if you want the extra width, set `window/stretch/aspect="expand"`
(layout already handles any aspect; the test covers 1920x864).

## Menus

Title/lobby/creation screens are untouched Control scenes. Creation uses buttons with minimum heights 28-60 px at 1280x720
(e.g. clear 28 px, pool 44x36, value 48 wide), i.e. below 9 mm on a ~420 dpi phone at scale 1.78 for several of them. Tappable, cramped.
While a dialog, shop, combat overlay or freeform bar is open the controls hide; with the world map open only MAP stays.

## Unverified without a real device

Real multi-touch order of events and `canceled` delivery; that `DisplayServer.screen_get_dpi()` and `get_display_safe_area()`
give sane values on Pixel 10 Pro / Pixel 9 / Galaxy S25 (cutout, gesture bars); mouse-emulation suppression on Android;
thumb comfort of the layout; joystick/camera sensitivity; virtual keyboard behaviour for the freeform bar; frame cost.
