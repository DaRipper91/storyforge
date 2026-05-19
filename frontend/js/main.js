/**
 * StoryForge — Application Entry Point
 *
 * Responsibilities:
 *   - Phase routing (Lobby → Creation → Exploration)
 *   - WebSocket event distribution
 *   - Lazy-init of game-phase modules
 */

import { fetchState, openSession, postGridAction, postFreeformAction } from "./api.js";
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
  kbdIndicator:  document.getElementById("kbd-indicator"),
  gpIndicators:  [0, 1, 2, 3].map(i => document.getElementById(`gp-slot-${i}`)),
  initTracker:   document.getElementById("initiative-tracker"),
  initSlots:     document.querySelector(".init-slots"),
  summary: {
    name:  document.getElementById("active-name"),
    klass: document.getElementById("active-class"),
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
    document.body.dataset.phase = appState.phase;
    
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
  });
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

async function handleServerEvent(msg) {
  if (msg.type !== "state_diff") return;
  const oldPhase = appState?.phase;
  const oldChars = appState?.characters ?? {};
  appState = await fetchState();
  
  document.body.dataset.phase = appState.phase;
  
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
  try {
    await postGridAction({
      actorId: active.id,
      type: "move",
      target,
    });
    audio.playConfirm();
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
      case XBOX.LT: inventory?.toggle(); break;
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

// ─────────────────────── Keyboard fallback ───────────────────────

function wireKeyboard() {
  window.addEventListener("keydown", (e) => {
    if (document.activeElement === els.freeformInput) return;
    
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
      case "v":
        inventory?.toggle(); break;
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
