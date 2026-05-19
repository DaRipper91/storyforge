/**
 * Lobby + Creation state machine.
 *
 * Two phases this module owns:
 *   LOBBY    — show 4 slot cards; press A on any controller to claim a slot.
 *   CREATION — selected controller walks through race → class → abilities → name.
 *
 * Per-controller creation state is held in `_drafts` keyed by controller_id.
 * Only one draft is "active" (rendering in the creation stage) at a time;
 * we cycle between drafts with LB/RB so multiple players can take turns.
 */

import {
  fetchCatalog, joinLobby, leaveLobby, createCharacter, startGame,
} from "./api.js";

const STANDARD_ARRAY = [15, 14, 13, 12, 10, 8];
const ABILITIES = ["STR", "DEX", "CON", "INT", "WIS", "CHA"];

export class Lobby {
  constructor({ state, audio, onExplorationStarted, onStateRefetch }) {
    this.state = state;
    this.audio = audio;
    this.onExplorationStarted = onExplorationStarted;
    this.onStateRefetch = onStateRefetch;
    
    this.catalog = null;
    this._drafts = new Map();       // controllerId -> draft object
    this._activeControllerId = null; // whose creation flow is on screen
    this._focusIndex = 0;            // for keyboard navigation within a step
    
    this._dom = {
      lobbyView:     document.getElementById("lobby-view"),
      lobbySlots:    document.getElementById("lobby-slots"),
      startBtn:      document.getElementById("start-game-btn"),
      creationView:  document.getElementById("creation-view"),
      stage:         document.getElementById("creation-stage"),
      stepPills:     document.querySelectorAll(".step-pill"),
      slotLabel:     document.getElementById("creation-slot-label"),
      backBtn:       document.getElementById("creation-back"),
      nextBtn:       document.getElementById("creation-next"),
    };
    
    this._dom.startBtn.addEventListener("click", () => this.handleStartGame());
    this._dom.backBtn.addEventListener("click", () => this.handleBack());
    this._dom.nextBtn.addEventListener("click", () => this.handleNext());
  }
  
  async init(currentState) {
    this.catalog = await fetchCatalog();
    this.setState(currentState);
  }
  
  setState(state) {
    this.state = state;
    document.body.dataset.phase = state.phase;
    
    // Hydrate drafts from server-persisted lobby_slots.
    for (const slot of state.lobby_slots) {
      if (slot.status === "creating" || slot.status === "claimed") {
        if (slot.controller_id && !this._drafts.has(slot.controller_id)) {
          this._drafts.set(slot.controller_id, this._draftFromSlot(slot));
        }
      }
    }
    
    if (state.phase === "lobby" || state.phase === "creation") {
      this._renderLobby();
    }
    if (state.phase === "creation") {
      // Auto-focus the first claiming controller if none is active.
      if (!this._activeControllerId) {
        const firstClaiming = state.lobby_slots.find(
          s => s.status === "claimed" || s.status === "creating"
        );
        if (firstClaiming) {
          this._activeControllerId = firstClaiming.controller_id;
        }
      }
      this._renderCreation();
    }
  }
  
  // ─────────────────────── Gamepad / Keyboard input ───────────────────────
  
  handleControllerButton({ controllerId, button }) {
    if (this.state.phase === "lobby" || this.state.phase === "creation") {
      // A = claim slot (if no slot held) or confirm in creation
      if (button === 0) {  // A
        this._handleConfirm(controllerId);
      } else if (button === 1) {  // B
        this._handleBButton(controllerId);
      } else if (button === 4 || button === 5) {  // LB/RB
        this._cycleActiveDraft(button === 5 ? +1 : -1);
      } else if (button === 9) {  // Start
        this.handleStartGame();
      }
    }
  }

  handleControllerDpad({ controllerId, dx, dy }) {
    if (this.state.phase !== "creation") return;
    if (controllerId !== this._activeControllerId) return;
    this._moveFocus(dx, dy);
  }

  handleKeyboard(e) {
    if (this.state.phase === "lobby") {
      if (e.key === "Enter") this.handleStartGame();
      // Allow keyboard player to join with 'A' (mapped to Space or A)
      if (e.key.toLowerCase() === "a" || e.key === " ") {
        this._handleAButton("keyboard");
      }
      return;
    }
    if (this.state.phase !== "creation") return;

    if (e.key === "ArrowLeft")  this._moveFocus(-1, 0);
    if (e.key === "ArrowRight") this._moveFocus(+1, 0);
    if (e.key === "ArrowUp")    this._moveFocus(0, -1);
    if (e.key === "ArrowDown")  this._moveFocus(0, +1);
    if (e.key === "Enter")      this._handleConfirm(this._activeControllerId || "keyboard");
    if (e.key === "Escape")     this.handleBack();
    if (e.key === "Tab") {
      e.preventDefault();
      this._cycleActiveDraft(e.shiftKey ? -1 : +1);
    }
  }

  // ─────────────────────── Slot claim / release ───────────────────────

  async _handleConfirm(controllerId) {
    // If not in creation, just try to claim.
    if (this.state.phase !== "creation") {
      return this._handleAButton(controllerId);
    }

    const draft = this._drafts.get(controllerId);
    if (!draft) return this._handleAButton(controllerId);

    // If this is the active draft, use Enter/A to select or advance.
    if (controllerId === this._activeControllerId) {
      if (draft.step === "race") {
        const keys = Object.keys(this.catalog.races);
        draft.race = keys[this._focusIndex];
      } else if (draft.step === "state") {
        const keys = Object.keys(this.catalog.states);
        draft.evolutionState = keys[this._focusIndex];
      } else if (draft.step === "role") {
        const keys = Object.keys(this.catalog.roles);
        draft.predatorRole = keys[this._focusIndex];
      }
      // "abilities" and "name" use their own internal focus/enter logic,
      // but we still want Enter to advance once they are valid.

      await this.handleNext();
    } else {
      // Take focus.
      this._activeControllerId = controllerId;
      this._renderCreation();
      this.audio?.playCursor();
    }
  }

  async _handleAButton(controllerId) {
    // If already has a draft, we don't need to do anything here anymore
    // as _handleConfirm handles the creation-phase logic.
    if (this._drafts.has(controllerId)) return;
    
    // Brand-new claim.
    try {
      const result = await joinLobby(controllerId);
      this.audio?.playConfirm();
      // Initialize an empty draft.
      this._drafts.set(controllerId, {
        controllerId,
        slotIndex: result.slot_index,
        step: "race",
        race: null,
        evolutionState: null,
        predatorRole: null,
        abilities: { STR: null, DEX: null, CON: null, INT: null, WIS: null, CHA: null },
        name: "",
      });
      if (!this._activeControllerId) {
        this._activeControllerId = controllerId;
      }
      await this.onStateRefetch?.();
    } catch (err) {
      console.warn("[lobby] join failed:", err.message);
      this.audio?.playDeny();
    }
  }
  
  async _handleBButton(controllerId) {
    if (!this._drafts.has(controllerId)) return;
    
    if (this.state.phase === "creation") {
      // Back in creation flow first.
      const draft = this._drafts.get(controllerId);
      if (draft.step !== "race") {
        this.handleBack();
        return;
      }
    }
    
    // From race step or lobby: release the slot.
    try {
      await leaveLobby(controllerId);
      this._drafts.delete(controllerId);
      if (this._activeControllerId === controllerId) {
        this._activeControllerId = this._drafts.keys().next().value ?? null;
      }
      this.audio?.playDeny();
      await this.onStateRefetch?.();
    } catch (err) {
      console.warn("[lobby] leave failed:", err.message);
    }
  }
  
  _cycleActiveDraft(direction) {
    const ids = [...this._drafts.keys()];
    if (ids.length === 0) return;
    const currentIdx = ids.indexOf(this._activeControllerId);
    const nextIdx = (currentIdx + direction + ids.length) % ids.length;
    this._activeControllerId = ids[nextIdx];
    this._focusIndex = 0;
    this._renderCreation();
    this.audio?.playCursor();
  }
  
  // ─────────────────────── Step navigation ───────────────────────
  
  async handleNext() {
    if (!this._activeControllerId) return;
    const draft = this._drafts.get(this._activeControllerId);
    if (!draft) return;
    
    const order = ["race", "state", "role", "abilities", "name"];
    const idx = order.indexOf(draft.step);
    
    // Validate current step before advancing.
    if (!this._isStepComplete(draft, draft.step)) {
      this.audio?.playDeny();
      return;
    }
    
    if (idx === order.length - 1) {
      // Final step — commit to server.
      await this._commitDraft(draft);
    } else {
      draft.step = order[idx + 1];
      this._focusIndex = 0;
      this._renderCreation();
      this.audio?.playPageTurn();
    }
  }
  
  handleBack() {
    if (!this._activeControllerId) return;
    const draft = this._drafts.get(this._activeControllerId);
    if (!draft) return;
    
    const order = ["race", "state", "role", "abilities", "name"];
    const idx = order.indexOf(draft.step);
    if (idx === 0) return;  // Can't go back from first step
    
    draft.step = order[idx - 1];
    this._focusIndex = 0;
    this._renderCreation();
    this.audio?.playPageTurn();
  }
  
  async _commitDraft(draft) {
    try {
      await createCharacter({
        slotIndex: draft.slotIndex,
        name: draft.name.trim(),
        race: draft.race,
        evolution_state: draft.evolutionState,
        predator_role: draft.predatorRole,
        abilities: draft.abilities,
      });
      this.audio?.playConfirm();
      this._drafts.delete(draft.controllerId);
      
      // Move focus to next unfinished draft.
      const ids = [...this._drafts.keys()];
      this._activeControllerId = ids[0] ?? null;
      
      await this.onStateRefetch?.();
    } catch (err) {
      console.error("[creation] commit failed:", err.message);
      this.audio?.playDeny();
    }
  }
  
  async handleStartGame() {
    if (this._dom.startBtn.disabled) return;
    try {
      await startGame();
      this.audio?.playConfirm();
      await this.onStateRefetch?.();
      this.onExplorationStarted?.();
    } catch (err) {
      console.error("[lobby] start failed:", err.message);
      this.audio?.playDeny();
    }
  }
  
  // ─────────────────────── Rendering: lobby ───────────────────────
  
  _renderLobby() {
    this._dom.lobbySlots.innerHTML = "";
    for (const slot of this.state.lobby_slots) {
      const card = document.createElement("div");
      card.className = "lobby-slot";
      card.dataset.status = slot.status;
      
      const idx = document.createElement("div");
      idx.className = "slot-index";
      idx.textContent = `Slot ${slot.slot_index + 1}`;
      card.appendChild(idx);
      
      const status = document.createElement("div");
      status.className = "slot-status-text";
      status.textContent = this._slotStatusText(slot);
      card.appendChild(status);
      
      if (slot.status === "ready" && slot.character_id) {
        const char = this.state.characters[slot.character_id];
        if (char) {
          const preview = document.createElement("div");
          preview.className = "slot-character-preview";
          preview.innerHTML = `
            <div class="char-name ink-gilded">${this._escape(char.name)}</div>
            <div>${this._escape(char.race)} · ${this._escape(char.evolution_state)}</div>
            <div>${this._escape(char.predator_role)}</div>
            <div>HP ${char.hp_max} · AC ${char.armor_class}</div>
          `;
          card.appendChild(preview);
        }
      }
      
      this._dom.lobbySlots.appendChild(card);

      card.addEventListener("click", () => {
        if (slot.status === "empty") {
          this._handleAButton("mouse");
        } else if (slot.status === "claimed" || slot.status === "creating") {
          // If already claimed, clicking it makes it the active draft.
          this._activeControllerId = slot.controller_id;
          this._renderCreation();
          this.audio?.playCursor();
        }
      });
    }
    
    // Update Start button.
    const readyCount = this.state.lobby_slots.filter(s => s.status === "ready").length;
    this._dom.startBtn.disabled = readyCount < 1;
    this._dom.startBtn.textContent = readyCount > 0
      ? `Begin Adventure (${readyCount} ${readyCount === 1 ? "hero" : "heroes"})`
      : "Begin Adventure";
  }
  
  _slotStatusText(slot) {
    switch (slot.status) {
      case "empty":    return "Press A to join";
      case "claimed":  return "Choosing race...";
      case "creating": return "Forging...";
      case "ready":    return "Ready";
      default:         return slot.status;
    }
  }
  
  // ─────────────────────── Rendering: creation ───────────────────────
  
  _renderCreation() {
    if (!this._activeControllerId) {
      this._dom.stage.innerHTML = "<p>Waiting for players...</p>";
      return;
    }
    const draft = this._drafts.get(this._activeControllerId);
    if (!draft) return;
    
    // Update step pills.
    const stepOrder = ["race", "state", "role", "abilities", "name"];
    const currentIdx = stepOrder.indexOf(draft.step);
    this._dom.stepPills.forEach((pill, i) => {
      pill.classList.remove("active", "done");
      if (i === currentIdx) pill.classList.add("active");
      if (i < currentIdx)  pill.classList.add("done");
    });
    
    this._dom.slotLabel.textContent =
      `Slot ${draft.slotIndex + 1} of ${this._drafts.size}`;
    
    // Render the current step.
    this._dom.stage.innerHTML = "";
    switch (draft.step) {
      case "race":      this._renderRaceStep(draft); break;
      case "state":     this._renderStateStep(draft); break;
      case "role":      this._renderRoleStep(draft); break;
      case "abilities": this._renderAbilitiesStep(draft); break;
      case "name":      this._renderNameStep(draft); break;
    }
  }
  
  _renderRaceStep(draft) {
    const grid = document.createElement("div");
    grid.className = "option-grid";
    
    const entries = Object.entries(this.catalog.races);
    entries.forEach(([raceKey, rdef], idx) => {
      const card = document.createElement("div");
      card.className = "option-card";
      if (draft.race === raceKey) card.classList.add("selected");
      if (idx === this._focusIndex) card.classList.add("focused");
      
      card.innerHTML = `
        <h3>${this._escape(rdef.name)}</h3>
        <p class="flavor">${this._escape(rdef.flavor)}</p>
        <div class="stats">
          Speed: ${rdef.speed}ft · 
          ${Object.entries(rdef.ability_bonuses).map(([a, b]) => `${a} +${b}`).join(", ")}
        </div>
      `;
      
      card.addEventListener("click", () => {
        draft.race = raceKey;
        this._renderCreation();
        this.audio?.playCursor();
      });
      card.addEventListener("mouseenter", () => {
        this._focusIndex = idx;
        this._renderCreation();
      });
      grid.appendChild(card);
    });
    
    this._dom.stage.appendChild(grid);
  }

  _renderStateStep(draft) {
    const grid = document.createElement("div");
    grid.className = "option-grid";
    
    const entries = Object.entries(this.catalog.states);
    entries.forEach(([stateKey, sdef], idx) => {
      const card = document.createElement("div");
      card.className = "option-card";
      if (draft.evolutionState === stateKey) card.classList.add("selected");
      if (idx === this._focusIndex) card.classList.add("focused");
      
      card.innerHTML = `
        <h3>${this._escape(sdef.name)}</h3>
        <p class="flavor">${this._escape(sdef.flavor)}</p>
        <div class="stats">
          Hit Die: d${sdef.hit_die} · Base AC: ${sdef.base_armor_class}
        </div>
      `;
      
      card.addEventListener("click", () => {
        draft.evolutionState = stateKey;
        this._renderCreation();
        this.audio?.playCursor();
      });
      card.addEventListener("mouseenter", () => {
        this._focusIndex = idx;
        this._renderCreation();
      });
      grid.appendChild(card);
    });
    
    this._dom.stage.appendChild(grid);
  }
  
  _renderRoleStep(draft) {
    const grid = document.createElement("div");
    grid.className = "option-grid";
    
    const entries = Object.entries(this.catalog.roles);
    entries.forEach(([roleKey, pdef], idx) => {
      const card = document.createElement("div");
      card.className = "option-card";
      if (draft.predatorRole === roleKey) card.classList.add("selected");
      if (idx === this._focusIndex) card.classList.add("focused");
      
      const inv = pdef.starting_inventory.map(i => i.name).join(", ");
      card.innerHTML = `
        <h3>${this._escape(pdef.name)}</h3>
        <p class="flavor">${this._escape(pdef.flavor)}</p>
        <div class="stats">
          Gear: ${this._escape(inv)}
        </div>
      `;
      
      card.addEventListener("click", () => {
        draft.predatorRole = roleKey;
        this._renderCreation();
        this.audio?.playCursor();
      });
      card.addEventListener("mouseenter", () => {
        this._focusIndex = idx;
        this._renderCreation();
      });
      grid.appendChild(card);
    });
    
    this._dom.stage.appendChild(grid);
  }
  
  _renderAbilitiesStep(draft) {
    const stage = document.createElement("div");
    
    const help = document.createElement("p");
    help.style.textAlign = "center";
    help.innerHTML = `Assign the standard array to each ability. Click an unused value, then click an ability to set it.`;
    stage.appendChild(help);
    
    const grid = document.createElement("div");
    grid.className = "ability-grid";
    
    ABILITIES.forEach((abil, i) => {
      const row = document.createElement("div");
      row.className = "ability-row";
      if (i === this._focusIndex) row.classList.add("focused");
      
      const name = document.createElement("span");
      name.className = "ability-name";
      name.textContent = abil;
      
      const val = document.createElement("span");
      val.className = "ability-value";
      val.textContent = draft.abilities[abil] ?? "—";
      
      row.appendChild(val);
      
      row.addEventListener("mouseenter", () => {
        this._focusIndex = i;
        this._renderCreation();
      });

      row.addEventListener("click", () => {
        if (this._pendingValue != null) {
          // Place the pending value.
          if (draft.abilities[abil] != null) {
            // Restore the displaced value to the pool.
            this._pool.push(draft.abilities[abil]);
          }
          draft.abilities[abil] = this._pendingValue;
          this._pool = this._pool.filter(v => v !== this._pendingValue);
          this._pendingValue = null;
          this._renderCreation();
          this.audio?.playConfirm();
        } else if (draft.abilities[abil] != null) {
          // Take this value back.
          this._pendingValue = draft.abilities[abil];
          this._pool.push(this._pendingValue);
          draft.abilities[abil] = null;
          this._renderCreation();
          this.audio?.playCursor();
        }
      });
      grid.appendChild(row);
    });
    
    stage.appendChild(grid);
    
    // Pool of available values.
    if (!this._pool) {
      const assigned = Object.values(draft.abilities).filter(v => v != null);
      this._pool = STANDARD_ARRAY.filter(v => !assigned.includes(v));
    }
    
    const pool = document.createElement("div");
    pool.className = "ability-pool";
    STANDARD_ARRAY.forEach(v => {
      const chip = document.createElement("div");
      chip.className = "ability-chip";
      if (!this._pool.includes(v)) chip.classList.add("used");
      if (this._pendingValue === v) chip.classList.add("selected-flame");
      chip.textContent = String(v);
      chip.addEventListener("click", () => {
        if (this._pool.includes(v)) {
          this._pendingValue = v;
          this._renderCreation();
          this.audio?.playCursor();
        }
      });
      pool.appendChild(chip);
    });
    stage.appendChild(pool);
    this._dom.stage.appendChild(stage);
  }
  
  _renderNameStep(draft) {
    const wrap = document.createElement("div");
    wrap.className = "name-stage";
    
    const label = document.createElement("p");
    label.style.fontSize = "var(--fs-lg)";
    label.textContent = "What is your hero called?";
    wrap.appendChild(label);
    
    const input = document.createElement("input");
    input.type = "text";
    input.className = "name-input";
    input.maxLength = 24;
    input.placeholder = "Kael, Lyra, Whisper...";
    input.value = draft.name;
    input.addEventListener("input", (e) => { draft.name = e.target.value; });
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && draft.name.trim()) this.handleNext();
    });
    wrap.appendChild(input);
    
    const preview = document.createElement("p");
    preview.style.opacity = "0.7";
    preview.style.fontStyle = "italic";
    preview.textContent =
      `${draft.race ? this.catalog.races[draft.race].name : "—"} ` +
      `${draft.charClass ? this.catalog.classes[draft.charClass].name : "—"}`;
    wrap.appendChild(preview);
    
    this._dom.stage.appendChild(wrap);
    setTimeout(() => input.focus(), 50);
  }
  
  // ─────────────────────── Helpers ───────────────────────
  
  _isStepComplete(draft, step) {
    switch (step) {
      case "race":      return draft.race != null;
      case "state":     return draft.evolutionState != null;
      case "role":      return draft.predatorRole != null;
      case "abilities": return ABILITIES.every(a => draft.abilities[a] != null);
      case "name":      return draft.name.trim().length >= 1;
      default:          return false;
    }
  }
  
  _moveFocus(dx, dy) {
    // Step-specific focus model. For race/state/role grids, dx/dy moves through
    // the cards in row-major order assuming ~3 columns.
    const draft = this._drafts.get(this._activeControllerId);
    if (!draft) return;
    
    const stepSizes = {
      race: Object.keys(this.catalog.races).length,
      state: Object.keys(this.catalog.states).length,
      role: Object.keys(this.catalog.roles).length,
      abilities: ABILITIES.length,
      name: 1,
    };
    const max = stepSizes[draft.step] ?? 0;
    if (max === 0) return;
    
    const columns = (draft.step === "race" || draft.step === "state" || draft.step === "role") ? 3 : 1;
    let next = this._focusIndex + dx + dy * columns;
    next = Math.max(0, Math.min(max - 1, next));
    this._focusIndex = next;
    this._renderCreation();
    this.audio?.playCursor();
  }
  
  _draftFromSlot(slot) {
    return {
      controllerId: slot.controller_id,
      slotIndex: slot.slot_index,
      step: slot.race ? (slot.evolution_state ? (slot.predator_role ? "abilities" : "role") : "state") : "race",
      race: slot.race,
      evolutionState: slot.evolution_state,
      predatorRole: slot.predator_role,
      abilities: slot.assigned_abilities ??
        { STR: null, DEX: null, CON: null, INT: null, WIS: null, CHA: null },
      name: slot.name_draft ?? "",
    };
  }
  
  _escape(s) {
    return String(s).replace(/[&<>"']/g, c =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[c])
    );
  }
}
