/**
 * Gamepad API integration with edge-detected button events and
 * D-pad / stick navigation with repeat delay.
 */

const XBOX = {
  A: 0, B: 1, X: 2, Y: 3,
  LB: 4, RB: 5, LT: 6, RT: 7,
  BACK: 8, START: 9,
  LS: 10, RS: 11,
  DPAD_UP: 12, DPAD_DOWN: 13, DPAD_LEFT: 14, DPAD_RIGHT: 15,
};

const DEADZONE = 0.45;
const INITIAL_REPEAT_MS = 350;
const REPEAT_INTERVAL_MS = 120;

/**
 * Stable identifier for a connected controller.
 */
export function makeControllerId(pad) {
  return `${pad.id}::${pad.index}`;
}

export class GamepadManager {
  constructor() {
    this._handlers = new Map();
    this._prevButtons = [[], [], [], []];
    this._dirHold = [null, null, null, null];
    this._connected = new Set();
    this._running = false;

    window.addEventListener("gamepadconnected", (e) => {
      this._connected.add(e.gamepad.index);
      this._emit("controller_connected", {
        index: e.gamepad.index,
        controllerId: makeControllerId(e.gamepad),
      });
    });
    window.addEventListener("gamepaddisconnected", (e) => {
      this._connected.delete(e.gamepad.index);
      this._dirHold[e.gamepad.index] = null;
      this._emit("controller_disconnected", { index: e.gamepad.index });
    });
  }

  on(event, handler) {
    if (!this._handlers.has(event)) this._handlers.set(event, new Set());
    this._handlers.get(event).add(handler);
    return this;
  }

  off(event, handler) {
    this._handlers.get(event)?.delete(handler);
    return this;
  }

  start() {
    if (this._running) return;
    this._running = true;
    const loop = () => {
      if (!this._running) return;
      this._poll(performance.now());
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }

  stop() { this._running = false; }

  controllerIdFor(index) {
    const pads = navigator.getGamepads?.() ?? [];
    const pad = pads[index];
    return pad ? makeControllerId(pad) : null;
  }

  _emit(event, payload) {
    const set = this._handlers.get(event);
    if (!set) return;
    for (const h of set) {
      try { h(payload); } catch (err) { console.error("[gp]", event, err); }
    }
  }

  _poll(nowMs) {
    const pads = navigator.getGamepads?.() ?? [];
    for (let i = 0; i < 4; i++) {
      const pad = pads[i];
      if (!pad) {
        if (this._connected.has(i)) {
          this._connected.delete(i);
          this._dirHold[i] = null;
        }
        continue;
      }

      if (!this._connected.has(i)) {
        this._connected.add(i);
        this._emit("controller_connected", {
          index: i,
          controllerId: makeControllerId(pad),
        });
      }

      this._pollButtons(i, pad);
      this._pollDirection(i, pad, nowMs);
    }
  }

  _pollButtons(i, pad) {
    const prev = this._prevButtons[i];
    const controllerId = makeControllerId(pad);
    for (let b = 0; b < pad.buttons.length; b++) {
      const pressed = pad.buttons[b].pressed;
      const wasPressed = prev[b] ?? false;
      if (pressed && !wasPressed) {
        this._emit("button_pressed", { index: i, button: b, controllerId });
      } else if (!pressed && wasPressed) {
        this._emit("button_released", { index: i, button: b, controllerId });
      }
      prev[b] = pressed;
    }
  }

  _pollDirection(i, pad, nowMs) {
    let dx = 0, dy = 0;

    if (pad.buttons[XBOX.DPAD_LEFT]?.pressed)  dx -= 1;
    if (pad.buttons[XBOX.DPAD_RIGHT]?.pressed) dx += 1;
    if (pad.buttons[XBOX.DPAD_UP]?.pressed)    dy -= 1;
    if (pad.buttons[XBOX.DPAD_DOWN]?.pressed)  dy += 1;

    const ax = pad.axes[0] ?? 0;
    const ay = pad.axes[1] ?? 0;
    if (dx === 0 && Math.abs(ax) > DEADZONE) dx = Math.sign(ax);
    if (dy === 0 && Math.abs(ay) > DEADZONE) dy = Math.sign(ay);

    const controllerId = makeControllerId(pad);
    const hold = this._dirHold[i];
    if (dx === 0 && dy === 0) {
      this._dirHold[i] = null;
      return;
    }

    if (!hold || hold.dx !== dx || hold.dy !== dy) {
      this._dirHold[i] = { dx, dy, sinceMs: nowMs, lastRepeatMs: nowMs };
      this._emit("dpad_repeat", { index: i, dx, dy, controllerId });
      return;
    }

    const heldFor = nowMs - hold.sinceMs;
    const sinceLast = nowMs - hold.lastRepeatMs;
    if (heldFor >= INITIAL_REPEAT_MS && sinceLast >= REPEAT_INTERVAL_MS) {
      hold.lastRepeatMs = nowMs;
      this._emit("dpad_repeat", { index: i, dx, dy, controllerId });
    }
  }
}

export { XBOX };
