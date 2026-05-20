/**
 * StoryForge — Application Entry Point
 *
 * Responsibilities:
 *   - Phase routing (Lobby → Creation → Exploration)
 *   - WebSocket event distribution
 *   - Lazy-init of game-phase modules
 */

import { fetchState, openSession, postGridAction, postFreeformAction,
         jonGetInventory, jonBuy, jonEscape, jonCactus, jonTick, jonGetState,
         dannaAddress, dannaPetition, dannaGetState,
         rvPerform, rvTip, rvHeckle, rvRequestSong,
} from "./api.js";
import { GridCanvas } from "./canvas.js";
import { GamepadManager, XBOX } from "./gamepad.js";
import { CharacterPanel } from "./characters.js";
import { NarrativeLog } from "./log.js";
import { InventoryPanel } from "./inventory.js";
import { AudioEngine } from "./audio.js";
import { Lobby } from "./lobby.js";

const els = {
  konvaMount:    document.getElementById("konva-mount"),
  portraitRow:   document.getElementById("portrait-row"),
  narrativeLog:  document.getElementById("narrative-log"),
  inventoryPane: document.getElementById("inventory-pane"),
  inventoryList: document.getElementById("inventory-list"),
  freeformModal: document.getElementById("freeform-modal"),
  freeformInput: document.getElementById("freeform-input"),
  freeformCommit:document.getElementById("freeform-commit"),
  freeformCancel:document.getElementById("freeform-cancel"),
  keymapModal:   document.getElementById("keymap-modal"),
  kbdIndicator:  document.getElementById("kbd-indicator"),
  gpIndicators:  [0, 1, 2, 3].map(i => document.getElementById(`gp-slot-${i}`)),
  initTracker:   document.getElementById("initiative-tracker"),
  initSlots:     document.querySelector(".init-slots"),
  summary: {
    name:  document.getElementById("active-name"),
    state: document.getElementById("active-state"),
    role:  document.getElementById("active-role"),
    hp:    document.getElementById("active-hp"),
    ac:    document.getElementById("active-ac"),
    move:  document.getElementById("active-move"),
    pos:   document.getElementById("active-pos"),
    silver:document.getElementById("active-silver"),
  },
};

const audio = new AudioEngine();
const gp    = new GamepadManager();

// Modules
let canvas = null;
let characters = null;
let log = null;
let lobby = null;
let inventory = null;

let appState = null;
let session  = null;

// ─────────────────────── Boot ───────────────────────

(async function boot() {
  try {
    appState = await fetchState();
    // Only skip the title screen if the server is already mid-game (exploration).
    // For lobby/creation the user navigates there via the menu flow.
    if (appState.phase === "exploration") {
      document.body.dataset.phase = "exploration";
    }
    // else: keep body[data-phase="title"] that was set in HTML

    lobby = new Lobby({
      state: appState,
      audio,
      onExplorationStarted: () => initExplorationView(),
      onStateRefetch: async () => {
        appState = await fetchState();
        lobby.setState(appState);
        if (appState.phase === "exploration" && !canvas) {
          initExplorationView();
        }
      },
    });
    await lobby.init(appState);
    
    // Initial BGM
    if (appState.phase === "lobby" || appState.phase === "creation") {
      audio.playBGM("lobby");
    } else if (appState.phase === "exploration") {
      audio.playBGM("exploration");
    }
    
    session = openSession({
      roomId: appState.current_room_id,
      onConnect:    () => console.log("[ws] connected"),
      onDisconnect: () => console.log("[ws] disconnected"),
      onMessage: handleServerEvent,
    });
    
    wireGamepad();
    wireKeyboard();
    wireFreeformModal();
    
    if (appState.phase === "exploration") {
      initExplorationView();
    }
    
    gp.start();
  } catch (err) {
    console.error("Boot failed:", err);
  }
})();

function renderInitiative(state) {
  if (!state || state.phase !== "exploration") {
    els.initTracker.classList.add("hidden");
    return;
  }
  
  els.initTracker.classList.remove("hidden");
  els.initSlots.innerHTML = "";
  
  // Use combat initiative order if available, else just show the party
  let order = [];
  let activeIdx = -1;
  
  if (state.combat && state.combat.initiative_order.length > 0) {
    order = state.combat.initiative_order;
    activeIdx = state.combat.active_index;
  } else {
    order = Object.keys(state.characters);
  }

  order.forEach((id, idx) => {
    const char = state.characters[id];
    const portrait = document.createElement("div");
    portrait.className = "init-portrait";
    
    // Is it a player or enemy? For now, we assume all in state.characters are players.
    // If it was an enemy, we could add 'enemy' class.
    if (idx === activeIdx) {
      portrait.classList.add("active-turn");
    }
    
    portrait.textContent = char ? char.name[0] : "?";
    // Color code if known
    if (char && char.hp_current <= 0) {
      portrait.style.opacity = "0.3";
      portrait.style.filter = "grayscale(1)";
    }
    
    els.initSlots.appendChild(portrait);
  });
}

function initExplorationView() {

  if (canvas) return;
  
  canvas = new GridCanvas({
    mountEl: els.konvaMount,
    onCellConfirmed: handleGridConfirm,
    onZoomChanged: (z) => {
      const s = _loadSettings();
      s.gameZoom = z;
      _saveSettings(s);
      _syncSliderUI(s);
    },
  });
  // Apply saved game zoom before the first setState (which triggers _fitAndRedraw)
  canvas.zoomLevel = _loadSettings().gameZoom;
  characters = new CharacterPanel({
    portraitRowEl: els.portraitRow,
    summaryEls:    els.summary,
    onActiveChanged: (id) => {
      audio.playCursor();
      recenterCursorOnActive();
      const char = appState.characters[id];
      if (char) inventory?.setCharacter(char);
    },
  });
  log = new NarrativeLog({ listEl: els.narrativeLog, audio });
  inventory = new InventoryPanel({
    containerEl: els.inventoryPane,
    listEl:      els.inventoryList,
    audio
  });
  
  canvas.setState(appState);
  characters.setState(appState);
  renderInitiative(appState);
  log.setInitial(appState.narrative_log);
  
  const active = characters.activeCharacter;
  if (active) {
    canvas.setCursor(active.position);
    inventory.setCharacter(active);
  }
}

// ─────────────────────── Server events ───────────────────────

const CLIENT_ONLY_PHASES = ["title", "menu", "mode_select", "saves"];

async function handleServerEvent(msg) {
  if (msg.type !== "state_diff") return;
  const oldPhase = appState?.phase;
  const oldChars = appState?.characters ?? {};
  appState = await fetchState();

  // Don't let server events clobber client-only navigation phases (title/menu/etc.)
  // unless the server has already moved to exploration.
  const clientPhase = document.body.dataset.phase;
  if (!CLIENT_ONLY_PHASES.includes(clientPhase) || appState.phase === "exploration") {
    document.body.dataset.phase = appState.phase;
  }
  
  // Detect damage for screen shake and floating text
  if (canvas) {
    for (const [id, char] of Object.entries(appState.characters)) {
      if (oldChars[id] && char.hp_current < oldChars[id].hp_current) {
        const damage = oldChars[id].hp_current - char.hp_current;
        canvas.shake(15, 400);
        canvas.spawnFloatingText(char.position, `-${damage}`, "#ff4444");
      } else if (oldChars[id] && char.hp_current > oldChars[id].hp_current) {
        const heal = char.hp_current - oldChars[id].hp_current;
        canvas.spawnFloatingText(char.position, `+${heal}`, "#44ff44");
      }
    }
  }

  // Phase-based BGM transition
  if (appState.phase !== oldPhase) {
    if (appState.phase === "lobby" || appState.phase === "creation") {
      audio.playBGM("lobby");
    } else if (appState.phase === "exploration") {
      audio.playBGM("exploration");
    }
  }

  // Combat / Death BGM logic
  if (appState.phase === "exploration") {
    const chars = Object.values(appState.characters);
    const allDead = chars.length > 0 && chars.every(c => c.hp_current <= 0);
    const anyNearDeath = chars.some(c => c.hp_current > 0 && c.hp_current <= c.hp_max * 0.25);
    
    // Check if there are enemies nearby to trigger "fight" music
    // For now, we'll use a simple heuristic: if any character is bloodied or in combat state
    const inCombat = chars.some(c => c.hp_current < c.hp_max); 

    if (allDead) {
      audio.playBGM("death", { fadeTime: 0.5 });
      document.body.classList.add("party-dead");
    } else if (anyNearDeath) {
      audio.playBGM("heartbeat", { fadeTime: 1.0 });
      document.body.classList.add("near-death");
    } else if (inCombat) {
      audio.playBGM("fight");
      document.body.classList.remove("near-death", "party-dead");
    } else {
      audio.playBGM("exploration");
      document.body.classList.remove("near-death", "party-dead");
    }
  }
  
  if (appState.phase === "lobby" || appState.phase === "creation") {
    lobby?.setState(appState);
    return;
  }
  
  if (appState.phase === "exploration" && !canvas) {
    initExplorationView();
    return;
  }
  
  if (canvas) {
    canvas.setState(appState);
    characters.setState(appState);
    renderInitiative(appState);
    const active = characters.activeCharacter;
    if (active) inventory?.setCharacter(active);
    
    // Calculate new log entries
    const previousLogLength = document.querySelectorAll("#narrative-log li").length;
    const newEntries = appState.narrative_log.slice(previousLogLength);
    
    for (const entry of newEntries) {
      log.append(entry);
      // Spawn floating text for actions
      if (entry.kind === "action" && entry.actor_id && appState.characters[entry.actor_id]) {
        const actor = appState.characters[entry.actor_id];
        // Extract just a short preview of the text for the bubble
        const shortText = entry.text.length > 20 ? entry.text.substring(0, 18) + "..." : entry.text;
        canvas.spawnFloatingText(actor.position, shortText, "#f4ead4");
      }
    }
  }
}

// ─────────────────────── Action handlers ───────────────────────

async function handleGridConfirm(target) {
  if (appState.phase !== "exploration") return;
  const active = characters.activeCharacter;
  if (!active) return;

  // Confirming your own cell is a no-op — don't send to the server
  if (target.x === active.position.x && target.y === active.position.y) return;

  // Decide action type: interact if the target is an NPC cell or a door
  const room = appState.rooms?.[appState.current_room_id];
  const cell = room?.cells?.[target.y * room.width + target.x];
  const isNpcCell  = cell?.occupant_id && appState.npcs?.[cell.occupant_id];
  const isDoorCell = cell?.terrain === "door";
  const actionType = (isNpcCell || isDoorCell) ? "interact" : "move";

  try {
    const result = await postGridAction({ actorId: active.id, type: actionType, target });
    audio.playConfirm();

    if (result.encounter?.type === "npc_encounter") {
      openNpcOverlay(result.encounter);
      return;
    }
    if (result.room_transition) {
      // State refreshes via WS; force immediate canvas update
      appState = await fetchState();
      canvas.setState(appState);
      log.append({
        revision: appState.revision,
        actor_id: active.id,
        kind: "narration",
        text: result.narrative ?? `Entered ${result.room_transition.room_name}.`,
        timestamp: new Date().toISOString(),
      });
    }
  } catch (err) {
    console.warn("[grid] rejected:", err.message);
    audio.playDeny();
    log.append({
      revision: appState?.revision ?? 0,
      actor_id: null,
      kind: "system",
      text: `[ref] illegal action: ${err.message}`,
      timestamp: new Date().toISOString(),
    });
  }
}

async function commitFreeform() {
  if (appState.phase !== "exploration") return;
  const text = els.freeformInput.value.trim();
  if (!text) return;
  const active = characters.activeCharacter;
  if (!active) return;
  closeFreeformModal();
  audio.playPageTurn();
  try {
    await postFreeformAction({ actorId: active.id, text });
  } catch (err) {
    console.error("[freeform] failed", err);
    audio.playDeny();
  }
}

// ─────────────────────── Gamepad wiring ───────────────────────

function wireGamepad() {
  gp.on("controller_connected", ({ index, controllerId }) => {
    els.gpIndicators[index]?.classList.add("live");
    els.gpIndicators[index].textContent = String(index + 1);
  });
  gp.on("controller_disconnected", ({ index }) => {
    els.gpIndicators[index]?.classList.remove("live");
    els.gpIndicators[index].textContent = "·";
  });
  
  gp.on("dpad_repeat", (e) => {
    if (appState?.phase === "exploration") {
      canvas?.moveCursor(e.dx, e.dy);
      audio.playCursor();
    } else {
      lobby?.handleControllerDpad(e);
    }
  });
  
  gp.on("button_pressed", (e) => {
    if (appState?.phase === "lobby" || appState?.phase === "creation") {
      lobby?.handleControllerButton(e);
      return;
    }
    
    switch (e.button) {
      case XBOX.A:  canvas?.confirmCursor(); break;
      case XBOX.B:
        if (!els.freeformModal.classList.contains("hidden")) closeFreeformModal();
        break;
      case XBOX.X:  canvas?.inspectCursor(); break;
      case XBOX.Y:  openFreeformModal(); break;
      case XBOX.LT: canvas?.adjustZoom(-0.25); break;
      case XBOX.RT: canvas?.adjustZoom(0.25); break;
      case XBOX.LB:
        characters?.cycleActive(-1);
        recenterCursorOnActive();
        break;
      case XBOX.RB:
        characters?.cycleActive(+1);
        recenterCursorOnActive();
        break;
    }
  });
}

function recenterCursorOnActive() {
  const active = characters?.activeCharacter;
  if (active && canvas) canvas.setCursor(active.position);
}

function toggleKeymap() {
  els.keymapModal.classList.toggle("hidden");
  if (!els.keymapModal.classList.contains("hidden")) {
    audio.playCursor();
  }
}
window.toggleKeymap = toggleKeymap;

// ─────────────────────── Settings ────────────────────────────────

const _settingsModal   = document.getElementById("settings-modal");
const _uiScaleSlider   = document.getElementById("ui-scale-slider");
const _gameZoomSlider  = document.getElementById("game-zoom-slider");
const _uiScaleValue    = document.getElementById("ui-scale-value");
const _gameZoomValue   = document.getElementById("game-zoom-value");

const _DEFAULT_SETTINGS = { uiScale: 1.0, gameZoom: 0.7 };

function _loadSettings() {
  try {
    return { ..._DEFAULT_SETTINGS, ...JSON.parse(localStorage.getItem("sf_settings") || "{}") };
  } catch { return { ..._DEFAULT_SETTINGS }; }
}

function _saveSettings(s) {
  localStorage.setItem("sf_settings", JSON.stringify(s));
}

function _applySettings({ uiScale, gameZoom }) {
  document.documentElement.style.zoom = uiScale;
  if (canvas) {
    canvas.zoomLevel = gameZoom;
    // Wait one frame so the zoom reflow settles before measuring clientWidth/Height
    requestAnimationFrame(() => canvas._fitAndRedraw());
  }
}

function _syncSliderUI({ uiScale, gameZoom }) {
  const uiPct   = Math.round(uiScale  * 100);
  const gamePct = Math.round(gameZoom * 100);
  _uiScaleSlider.value   = uiPct;
  _gameZoomSlider.value  = gamePct;
  _uiScaleValue.textContent  = `${uiPct}%`;
  _gameZoomValue.textContent = `${gamePct}%`;
}

function openSettings() {
  const s = _loadSettings();
  _syncSliderUI(s);
  _settingsModal.classList.remove("hidden");
  audio.playCursor();
}
window.openSettings = openSettings;

function closeSettings() {
  _settingsModal.classList.add("hidden");
}
window.closeSettings = closeSettings;

function resetSettings() {
  _saveSettings(_DEFAULT_SETTINGS);
  _syncSliderUI(_DEFAULT_SETTINGS);
  _applySettings(_DEFAULT_SETTINGS);
}
window.resetSettings = resetSettings;

// Live preview as sliders move
_uiScaleSlider.addEventListener("input", () => {
  const uiScale  = _uiScaleSlider.value / 100;
  const gameZoom = _gameZoomSlider.value / 100;
  _uiScaleValue.textContent = `${_uiScaleSlider.value}%`;
  const s = { uiScale, gameZoom };
  _applySettings(s);
  _saveSettings(s);
});

_gameZoomSlider.addEventListener("input", () => {
  const uiScale  = _uiScaleSlider.value / 100;
  const gameZoom = _gameZoomSlider.value / 100;
  _gameZoomValue.textContent = `${_gameZoomSlider.value}%`;
  const s = { uiScale, gameZoom };
  _applySettings(s);
  _saveSettings(s);
});

// Close on backdrop click or Esc
_settingsModal.addEventListener("click", (e) => {
  if (e.target === _settingsModal) closeSettings();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !_settingsModal.classList.contains("hidden")) {
    closeSettings();
  }
});

// Apply saved settings on load
(function initSettings() {
  const s = _loadSettings();
  _applySettings(s);
})();

// ─────────────────────── Keyboard fallback ───────────────────────

function wireKeyboard() {
  window.addEventListener("keydown", (e) => {
    if (document.activeElement === els.freeformInput) return;
    
    // Toggle keymap
    if (e.key.toLowerCase() === "k" || e.key === "?") {
      toggleKeymap();
      return;
    }

    if (!els.keymapModal.classList.contains("hidden")) {
      if (e.key === "Escape") toggleKeymap();
      return;
    }

    if (appState?.phase === "lobby" || appState?.phase === "creation") {
      if (document.activeElement?.tagName === "INPUT") return;
      lobby?.handleKeyboard(e);
      return;
    }
    // Exploration: existing keymap.
    switch (e.key) {
      case "w":
      case "ArrowUp":    canvas?.moveCursor(0, -1); audio.playCursor(); break;
      case "s":
      case "ArrowDown":  canvas?.moveCursor(0, +1); audio.playCursor(); break;
      case "a":
      case "ArrowLeft":  canvas?.moveCursor(-1, 0); audio.playCursor(); break;
      case "d":
      case "ArrowRight": canvas?.moveCursor(+1, 0); audio.playCursor(); break;
      case "1":
      case "2":
      case "3":
      case "4":
        const idx = parseInt(e.key) - 1;
        const ids = Object.keys(appState.characters);
        if (idx < ids.length) {
          characters?.setActive(ids[idx]);
          recenterCursorOnActive();
        }
        break;
      case "Enter":
      case "f":
      case " ":
      case "e":
        canvas?.confirmCursor(); break;
      case "i":
      case "x":
        canvas?.inspectCursor(); break;
      case "-":
        canvas?.adjustZoom(-0.25); break;
      case "=":
      case "+":
        canvas?.adjustZoom(0.25); break;
      case "v":
        inventory?.toggle(); break;
      case "r":
        location.reload(); break;
      case "Escape":     closeFreeformModal(); break;
      case "Tab":
        e.preventDefault();
        characters?.cycleActive(e.shiftKey ? -1 : +1);
        recenterCursorOnActive();
        break;
      case "/":
      case "t":
        e.preventDefault();
        openFreeformModal();
        break;
    }

  });
  els.kbdIndicator.classList.add("connected");
}

function wireFreeformModal() {
  els.freeformCommit.addEventListener("click", commitFreeform);
  els.freeformCancel.addEventListener("click", closeFreeformModal);
  els.freeformInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      commitFreeform();
    } else if (e.key === "Escape") {
      closeFreeformModal();
    }
  });
}

function openFreeformModal() {
  if (appState?.phase !== "exploration") return;
  els.freeformModal.classList.remove("hidden");
  els.freeformInput.value = "";
  setTimeout(() => els.freeformInput.focus(), 50);
  audio.playPageTurn();
}

function closeFreeformModal() {
  els.freeformModal.classList.add("hidden");
}

// ─────────────────────── NPC overlay dispatcher ───────────────────

function openNpcOverlay(encounterData) {
  const id = encounterData.encounter_id;
  if      (id === "jon_shop")              openShopOverlay(encounterData);
  else if (id === "danna_audience")        openDannaOverlay();
  else if (id === "redvelvet_performance") openRedVelvetOverlay();
  // samael_lore / haylie_inn: no overlay yet — fall through silently
}

// ─────────────────────── Jon Shop Encounter ───────────────────────

const shopEls = {
  overlay:       document.getElementById("jon-shop-overlay"),
  tagline:       document.getElementById("jon-shop-tagline"),
  message:       document.getElementById("jon-shop-message"),
  inventoryList: document.getElementById("jon-inventory-list"),
  escapeResult:  document.getElementById("escape-result"),
  cactusAdmire:  document.getElementById("cactus-admire-btn"),
  cactusSnicker: document.getElementById("cactus-snicker-btn"),
};

let _shopGenre = "fantasy";
let _shopActorId = null;

async function openShopOverlay(encounterData) {
  _shopActorId = characters?.activeCharacter?.id ?? null;
  shopEls.overlay.classList.remove("hidden");
  shopEls.message.classList.add("hidden");
  shopEls.escapeResult.classList.add("hidden");

  // Derive genre from current_room_id (extend later if GameState gets a genre field)
  _shopGenre = "fantasy";

  await refreshShopInventory();
  wireShopButtons();
  audio.playPageTurn();
}

function closeShopOverlay() {
  shopEls.overlay.classList.add("hidden");
  shopEls.message.classList.add("hidden");
  shopEls.escapeResult.classList.add("hidden");
  jonTick().catch(() => {});  // advance Jon's turn clock on departure
}

async function refreshShopInventory() {
  shopEls.inventoryList.innerHTML = "<li style='opacity:.5;font-style:italic'>Loading stock…</li>";
  try {
    const data = await jonGetInventory(_shopGenre);
    renderShopInventory(data.items);
  } catch (e) {
    shopEls.inventoryList.innerHTML = "<li style='opacity:.5'>Couldn't reach the back room.</li>";
  }
}

function renderShopInventory(items) {
  shopEls.inventoryList.innerHTML = "";
  for (const item of items) {
    const li = document.createElement("li");
    li.className = "jon-item";
    li.innerHTML = `
      <span class="jon-item-name">${item.name}</span>
      <span class="jon-item-notes">${item.notes ?? ""}</span>
      <span class="jon-item-price">${item.value}s</span>
      <button class="jon-item-buy" data-item-id="${item.id}">Buy</button>
    `;
    li.querySelector(".jon-item-buy").addEventListener("click", () => buyItem(item.id, item.name));
    shopEls.inventoryList.appendChild(li);
  }
}

async function buyItem(itemId, itemName) {
  if (!_shopActorId) return;
  try {
    const res = await jonBuy({ actorId: _shopActorId, itemId, genre: _shopGenre });
    showShopMessage(res.message, res.success ? "" : "is-offended");
    if (res.success) {
      appState = await fetchState();
      canvas?.setState(appState);
      characters?.setState(appState);
      audio.playConfirm();
    } else {
      audio.playDeny();
    }
  } catch (e) {
    showShopMessage("Something went wrong.", "is-offended");
  }
}

function wireShopButtons() {
  // Escape method buttons
  document.querySelectorAll(".escape-btn").forEach(btn => {
    btn.onclick = () => attemptEscape(btn.dataset.method);
  });

  shopEls.cactusAdmire.onclick  = () => handleCactus(false);
  shopEls.cactusSnicker.onclick = () => handleCactus(true);

  // Close on backdrop click
  shopEls.overlay.addEventListener("click", (e) => {
    if (e.target === shopEls.overlay) closeShopOverlay();
  });

  // Esc to close (only if escape check succeeded)
  document.addEventListener("keydown", function shopEsc(e) {
    if (e.key === "Escape" && !shopEls.overlay.classList.contains("hidden")) {
      closeShopOverlay();
      document.removeEventListener("keydown", shopEsc);
    }
  });
}

async function attemptEscape(method) {
  if (!_shopActorId) return;

  const jonState = await jonGetState().catch(() => null);
  if (jonState && !jonState.party_can_leave) {
    showEscapeResult(
      "Jon is mid-sentence. He hasn't noticed you trying to leave. " +
      "You literally cannot get a word in. Wait for him to finish.",
      false,
    );
    return;
  }

  try {
    const res = await jonEscape({ actorId: _shopActorId, method });

    const rollLine = `d20(${res.roll}) + ${res.modifier} = **${res.total}** vs DC ${res.dc}`;
    const result = `${res.flavor}\n\n*${rollLine}*`;
    showEscapeResult(result, res.success);

    if (res.psychic_damage > 0) {
      appState = await fetchState();
      canvas?.setState(appState);
      characters?.setState(appState);
      canvas?.shake(12, 300);
      const char = appState.characters[_shopActorId];
      if (char) canvas?.spawnFloatingText(char.position, `-${res.psychic_damage} ψ`, "#9966cc");
      showShopMessage(`The rambling carves a small psychic notch in your soul. −${res.psychic_damage} HP.`, "is-offended");
    }

    if (res.success) {
      setTimeout(closeShopOverlay, 2200);
    }
  } catch (e) {
    showEscapeResult("Something went wrong with the escape check.", false);
  }
}

async function handleCactus(isLewd) {
  try {
    const res = await jonCactus(isLewd);
    showShopMessage(res.jon_response, isLewd ? "is-offended" : "");
    if (!res.jon_will_sell) {
      audio.playDeny();
      document.querySelectorAll(".jon-item-buy").forEach(b => b.disabled = true);
    }
  } catch (e) {
    showShopMessage("Jon looks at you. You look at Jon.", "");
  }
}

function showShopMessage(text, extraClass = "") {
  shopEls.message.className = `jon-message${extraClass ? " " + extraClass : ""}`;
  shopEls.message.textContent = text;
  shopEls.message.classList.remove("hidden");
  shopEls.tagline.textContent = text.slice(0, 80) + (text.length > 80 ? "…" : "");
}

function showEscapeResult(text, success) {
  shopEls.escapeResult.className = `escape-result${success ? " is-success" : " is-fail"}`;
  // Render simple markdown bold
  shopEls.escapeResult.innerHTML = text.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/\n/g, "<br>");
  shopEls.escapeResult.classList.remove("hidden");
}

// ─────────────────────── Queen D.Anna Encounter ───────────────────

const dannaEls = {
  overlay:       document.getElementById("danna-overlay"),
  tagline:       document.getElementById("danna-tagline"),
  message:       document.getElementById("danna-message"),
  standingLabel: document.getElementById("danna-standing-label"),
  favorDisplay:  document.getElementById("danna-favor"),
  leaveBtn:      document.getElementById("danna-leave-btn"),
};

function openDannaOverlay() {
  dannaEls.overlay.classList.remove("hidden");
  dannaEls.message.classList.add("hidden");
  _refreshDannaState();
  wireDannaButtons();
  audio.playPageTurn();
}

function closeDannaOverlay() {
  dannaEls.overlay.classList.add("hidden");
  dannaEls.message.classList.add("hidden");
}

async function _refreshDannaState() {
  try {
    const s = await dannaGetState();
    dannaEls.standingLabel.textContent = s.standing;
    dannaEls.favorDisplay.textContent  = s.favor;
    dannaEls.tagline.textContent = _dannaTagline(s.favor, s.is_offended);
  } catch (_) {}
}

function _dannaTagline(favor, offended) {
  if (offended)  return '"We will try this again. From the beginning."';
  if (favor >= 3) return '"You have conducted yourself well. Remarkably well."';
  if (favor >= 1) return '"You may approach."';
  if (favor < 0)  return '"I am choosing, deliberately, not to elaborate."';
  return '"State your business. Correctly."';
}

function _showDannaMessage(text, cls = "") {
  dannaEls.message.className = `jon-message${cls ? " " + cls : ""}`;
  dannaEls.message.textContent = text;
  dannaEls.message.classList.remove("hidden");
  dannaEls.tagline.textContent = text.slice(0, 80) + (text.length > 80 ? "…" : "");
}

function wireDannaButtons() {
  document.querySelectorAll(".danna-address-btn").forEach(btn => {
    btn.onclick = async () => {
      try {
        const res = await dannaAddress(btn.dataset.form);
        _showDannaMessage(res.response, res.correct ? "" : "is-offended");
        dannaEls.standingLabel.textContent = res.standing;
        dannaEls.favorDisplay.textContent  = res.new_favor;
        dannaEls.tagline.textContent = _dannaTagline(res.new_favor, res.is_offended);
      } catch (e) {
        _showDannaMessage("She looks at you. The situation is unclear.", "");
      }
    };
  });

  document.querySelectorAll(".danna-petition-btn").forEach(btn => {
    btn.onclick = async () => {
      try {
        const res = await dannaPetition(btn.dataset.petition);
        _showDannaMessage(res.response, res.granted ? "" : "is-offended");
        dannaEls.standingLabel.textContent = res.standing;
        dannaEls.favorDisplay.textContent  = res.new_favor;
      } catch (e) {
        _showDannaMessage("The petition went unheard.", "is-offended");
      }
    };
  });

  dannaEls.leaveBtn.onclick = closeDannaOverlay;

  dannaEls.overlay.addEventListener("click", (e) => {
    if (e.target === dannaEls.overlay) closeDannaOverlay();
  });

  document.addEventListener("keydown", function dannaEsc(e) {
    if (e.key === "Escape" && !dannaEls.overlay.classList.contains("hidden")) {
      closeDannaOverlay();
      document.removeEventListener("keydown", dannaEsc);
    }
  });
}

// ─────────────────────── Firey RedVelvet Encounter ────────────────

const rvEls = {
  overlay:    document.getElementById("redvelvet-overlay"),
  tagline:    document.getElementById("rv-tagline"),
  message:    document.getElementById("rv-message"),
  moodLabel:  document.getElementById("rv-mood-label"),
  moodPips:   document.getElementById("rv-mood-pips"),
  performBtn: document.getElementById("rv-perform-btn"),
  heckleBtn:  document.getElementById("rv-heckle-btn"),
  leaveBtn:   document.getElementById("rv-leave-btn"),
};

const _MOOD_NAMES  = ["Cold", "Warm", "Hot", "Blazing"];
const _MOOD_COLORS = ["#aaa", "#e8a040", "#ff6820", "#ff2200"];

function openRedVelvetOverlay() {
  rvEls.overlay.classList.remove("hidden");
  rvEls.message.classList.add("hidden");
  _refreshRvState();
  wireRvButtons();
  audio.playPageTurn();
}

function closeRedVelvetOverlay() {
  rvEls.overlay.classList.add("hidden");
  rvEls.message.classList.add("hidden");
}

async function _refreshRvState() {
  try {
    const s = await (await fetch("/api/npc/redvelvet/state")).json();
    _updateRvMood(s.current_mood);
  } catch (_) {}
}

function _updateRvMood(moodValue) {
  const label = _MOOD_NAMES[moodValue] ?? "Warm";
  const color  = _MOOD_COLORS[moodValue] ?? _MOOD_COLORS[1];
  rvEls.moodLabel.textContent = label;
  rvEls.moodLabel.style.color = color;
  rvEls.moodPips?.querySelectorAll(".rv-pip").forEach((pip, i) => {
    pip.classList.toggle("active", i <= moodValue);
    pip.style.background = i <= moodValue ? color : "";
  });

  const taglines = [
    '"The fire performs whether you deserve it or not."',
    '"You\'re watching, or you\'re in the way."',
    '"Now we\'re getting somewhere."',
    '"This one\'s the real one. Pay attention."',
  ];
  rvEls.tagline.textContent = taglines[moodValue] ?? taglines[1];

  const btn = rvEls.performBtn;
  btn.textContent = moodValue >= 3 ? "★ Watch Her Perform ★" : "Watch Her Perform";
  btn.style.borderColor = moodValue >= 2 ? color : "";
}

function _showRvMessage(text, cls = "") {
  rvEls.message.className = `jon-message${cls ? " " + cls : ""}`;
  rvEls.message.textContent = text;
  rvEls.message.classList.remove("hidden");
}

function wireRvButtons() {
  rvEls.performBtn.onclick = async () => {
    try {
      const res = await rvPerform();
      _showRvMessage(res.performance_text, res.grants_boon ? "" : "");
      _updateRvMood(res.mood_value);
      if (res.grants_boon) {
        audio.playConfirm();
        canvas?.spawnFloatingText(
          characters?.activeCharacter?.position ?? { x: 0, y: 0 },
          "✦ Inspired", "#ff6820"
        );
      } else {
        audio.playPageTurn();
      }
    } catch (e) {
      _showRvMessage("The performance continues regardless.", "");
    }
  };

  document.querySelectorAll(".rv-tip-btn").forEach(btn => {
    btn.onclick = async () => {
      try {
        const res = await rvTip(Number(btn.dataset.tip));
        _showRvMessage(res.response, "");
        if (res.mood_changed) _updateRvMood(_MOOD_NAMES.indexOf(res.mood_after));
        audio.playConfirm();
      } catch (e) {
        _showRvMessage("The silver landed somewhere. Probably fine.", "");
      }
    };
  });

  document.querySelectorAll(".rv-song-btn").forEach(btn => {
    btn.onclick = async () => {
      try {
        const res = await rvRequestSong(btn.dataset.song);
        _showRvMessage(res.performance_text, "");
        audio.playPageTurn();
      } catch (e) {
        _showRvMessage("She starts playing something. The request may not have registered.", "");
      }
    };
  });

  rvEls.heckleBtn.onclick = async () => {
    try {
      const res = await rvHeckle();
      _showRvMessage(res.response, "is-offended");
      _updateRvMood(_MOOD_NAMES.indexOf(res.mood_after));
      audio.playDeny();
    } catch (e) {
      _showRvMessage("She heard you. Everyone heard you.", "is-offended");
    }
  };

  rvEls.leaveBtn.onclick = closeRedVelvetOverlay;

  rvEls.overlay.addEventListener("click", (e) => {
    if (e.target === rvEls.overlay) closeRedVelvetOverlay();
  });

  document.addEventListener("keydown", function rvEsc(e) {
    if (e.key === "Escape" && !rvEls.overlay.classList.contains("hidden")) {
      closeRedVelvetOverlay();
      document.removeEventListener("keydown", rvEsc);
    }
  });
}
