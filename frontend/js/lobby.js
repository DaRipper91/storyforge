/**
 * Lobby + Creation state machine.
 *
 * Phases this module owns (client-side virtual phases in CAPS):
 *   TITLE       — press-start splash
 *   MENU        — New Adventure / Saved Games
 *   MODE_SELECT — Solo / Multiplayer
 *   SAVES       — list of saved campaigns
 *   lobby       — 4 slot cards; press A on any controller to claim a slot
 *   creation    — per-controller: race → state → role → abilities → name
 */

import {
  fetchCatalog, joinLobby, leaveLobby, createCharacter, startGame,
  updateLobbyName, setPhase, saveDraft,
  fetchCampaigns, newCampaign, loadCampaign,
} from "./api.js";

const STANDARD_ARRAY = [15, 14, 13, 12, 10, 8];
const ABILITIES = ["STR", "DEX", "CON", "INT", "WIS", "CHA"];
const CREATION_ORDER = ["era", "race", "state", "role", "equipment", "background", "abilities", "skills", "feat", "identity", "story", "name"];

// Phases that exist only client-side — server state must not override them
// (unless server reaches "exploration", which always wins).
const CLIENT_ONLY_PHASES = ["title", "intro", "menu", "mode_select", "saves"];

export class Lobby {
  constructor({ state, audio, onExplorationStarted, onStateRefetch }) {
    this.state = state;
    this.audio = audio;
    this.onExplorationStarted = onExplorationStarted;
    this.onStateRefetch = onStateRefetch;

    this.catalog = null;
    this._drafts = new Map();        // controllerId → draft object
    this._activeControllerId = null; // whose creation flow is on screen
    this._focusIndex = 0;            // focused card in the current creation step
    this._pool = null;               // remaining ability values to assign
    this._pendingValue = null;       // ability chip picked, waiting for a slot
    this._submitting = false;        // guard against double-submit on final step

    // Attract mode
    this._attractTimer   = null;
    this._attractSlide   = 0;
    this._attractTimeout = null;
    this._attractEl      = document.getElementById("attract-overlay");
    this._attractVideo   = document.getElementById("attract-video");
    this._attractText    = document.getElementById("attract-text");
    this._attractVisible = false;

    // Pre-menu / saves navigation
    this._menuFocus = 0;   // 0 = New Adventure, 1 = Saved Games
    this._modeFocus = 0;   // 0 = Solo, 1 = Multiplayer
    this._saves = [];
    this._saveFocus = 0;

    this._dom = {
      titleView:    document.getElementById("title-view"),
      menuView:     document.getElementById("menu-view"),
      modeView:     document.getElementById("mode-view"),
      savesView:    document.getElementById("saves-view"),
      savesList:    document.getElementById("saves-list"),
      savesBackBtn: document.getElementById("saves-back-btn"),
      modeBackBtn:  document.getElementById("mode-back-btn"),
      newGameBtn:   document.getElementById("new-game-btn"),
      loadGameBtn:  document.getElementById("load-game-btn"),
      soloBtn:      document.getElementById("solo-btn"),
      multiBtn:     document.getElementById("multi-btn"),
      lobbyView:    document.getElementById("lobby-view"),
      lobbySlots:   document.getElementById("lobby-slots"),
      startBtn:     document.getElementById("start-game-btn"),
      creationView: document.getElementById("creation-view"),
      stage:        document.getElementById("creation-stage"),
      stepPills:    document.querySelectorAll(".step-pill"),
      slotLabel:    document.getElementById("creation-slot-label"),
      backBtn:      document.getElementById("creation-back"),
      nextBtn:      document.getElementById("creation-next"),
    };

    // Title
    this._dom.titleView?.addEventListener("click", () => this._exitTitlePhase());

    // Menu buttons
    this._dom.newGameBtn?.addEventListener("click", () => {
      document.body.dataset.phase = "mode_select";
      this._modeFocus = 0;
      this._renderMode();
      this.audio?.playPageTurn();
    });
    this._dom.loadGameBtn?.addEventListener("click", () => this._showSaves());

    // Mode buttons
    this._dom.soloBtn?.addEventListener("click",  () => this._startNewCampaign(true));
    this._dom.multiBtn?.addEventListener("click", () => this._startNewCampaign(false));

    // Back buttons
    this._dom.modeBackBtn?.addEventListener("click",  () => this._goToMenu());
    this._dom.savesBackBtn?.addEventListener("click", () => this._goToMenu());

    // Creation controls
    this._dom.startBtn?.addEventListener("click", () => this.handleStartGame());
    this._dom.backBtn?.addEventListener("click",  () => this.handleBack());
    this._dom.nextBtn?.addEventListener("click",  () => this.handleNext());

    // Always start on title (boot sets body[data-phase="title"])
    if (document.body.dataset.phase === "title") {
      this._renderTitle();
    }

    // Attract mode — reset idle timer on any input
    let lastMouseMove = 0;
    const resetIdle = (e) => {
      // Throttle mousemove events to at most once per second
      // unless attract mode is currently visible (to ensure instant cancellation)
      if (e && e.type === "mousemove" && !this._attractVisible) {
        const now = Date.now();
        if (now - lastMouseMove < 1000) return;
        lastMouseMove = now;
      }
      this._resetAttractTimer();
    };
    window.addEventListener("keydown",    resetIdle, { passive: true });
    window.addEventListener("mousemove",  resetIdle, { passive: true });
    window.addEventListener("mousedown",  resetIdle, { passive: true });
    window.addEventListener("touchstart", resetIdle, { passive: true });
    this._resetAttractTimer();
  }

  // ─────────────────────── Attract Mode ───────────────────────

  _resetAttractTimer() {
    if (this._attractVisible) { this._hideAttract(); return; }
    clearTimeout(this._attractTimer);
    const phase = document.body.dataset.phase;
    if (phase === "title" || phase === "menu") {
      this._attractTimer = setTimeout(() => this._showAttract(), 45_000);
    }
  }

  _showAttract() {
    if (!this._attractEl || !this.catalog) return;
    this._attractVisible = true;
    this._attractEl.setAttribute("aria-hidden", "false");
    this._attractEl.classList.add("visible");
    this._attractVideo?.play().catch(() => {});
    this._attractSlide = 0;
    this._buildAttractSlides();
    this._runAttractSlides();
  }

  _hideAttract() {
    if (!this._attractEl) return;
    this._attractVisible = false;
    this._attractEl.setAttribute("aria-hidden", "true");
    this._attractEl.classList.remove("visible");
    this._attractVideo?.pause();
    clearTimeout(this._attractTimeout);
    this._resetAttractTimer();
  }

  _buildAttractSlides() {
    if (!this._attractText || !this.catalog) return;
    const races = this.catalog.races ?? {};

    // Group races by their group field
    const groups = {};
    for (const [, def] of Object.entries(races)) {
      if (!groups[def.group]) groups[def.group] = [];
      groups[def.group].push(def);
    }

    const slides = [
      {
        eyebrow: "Before the Paradox",
        headline: "They had names you would recognize.",
        body: "Elves. Humans. Dwarves. Orcs. The familiar peoples of a thousand worlds.",
      },
      {
        eyebrow: "Then it came",
        headline: "The Paradox did not destroy them.",
        body: "It remembered them — then rewrote what they could become.",
      },
      ...Object.entries(groups).map(([group, defs]) => ({
        eyebrow: `The ${group} Lineage`,
        headline: null,
        body: null,
        pairs: defs.map(d => ({ before: d.before, after: d.name })),
      })),
      {
        eyebrow: "Your story",
        headline: "Which will you become?",
        body: "Press any button to begin.",
      },
    ];

    this._attractSlides = slides;
  }

  _runAttractSlides() {
    if (!this._attractVisible || !this._attractSlides) return;
    const slides = this._attractSlides;
    const el = this._attractText;
    el.innerHTML = "";

    const slide = slides[this._attractSlide];
    const div = document.createElement("div");
    div.className = "attract-slide active";

    if (slide.eyebrow) {
      const ey = document.createElement("p");
      ey.className = "attract-eyebrow";
      ey.textContent = slide.eyebrow;
      div.appendChild(ey);
    }
    if (slide.headline) {
      const h = document.createElement("h2");
      h.className = "attract-headline";
      h.textContent = slide.headline;
      div.appendChild(h);
    }
    if (slide.body) {
      const b = document.createElement("p");
      b.className = "attract-body";
      b.textContent = slide.body;
      div.appendChild(b);
    }
    if (slide.pairs) {
      const grid = document.createElement("div");
      grid.className = "attract-race-grid";
      slide.pairs.forEach(({ before, after }) => {
        const pair = document.createElement("span");
        pair.className = "attract-race-pair";
        pair.innerHTML =
          `<span class="before">${this._escape(before)}</span>` +
          `<span class="arrow">→</span>` +
          `<span class="after">${this._escape(after)}</span>`;
        grid.appendChild(pair);
      });
      div.appendChild(grid);
    }

    el.appendChild(div);

    const duration = slide.pairs ? 5000 : 4000;
    this._attractTimeout = setTimeout(() => {
      this._attractSlide = (this._attractSlide + 1) % slides.length;
      this._runAttractSlides();
    }, duration);
  }

  _renderTitle() {
    if (!this._dom.titleView) return;
    this._dom.titleView.innerHTML = `
      <div class="flame-container">
        <div class="flame"></div><div class="flame"></div><div class="flame"></div>
      </div>
      <h1 class="title-logo ink-gilded">StoryForge</h1>
      <p class="title-press-start">Press <kbd>Enter</kbd> or <kbd>A</kbd> to Begin</p>
    `;
  }

  async init(currentState) {
    this.catalog = await fetchCatalog();
    this.setState(currentState);
  }

  setState(state) {
    const clientPhase = document.body.dataset.phase;

    // Client-only phases: don't let a server state_diff override navigation,
    // unless the server has already progressed to exploration.
    if (CLIENT_ONLY_PHASES.includes(clientPhase) && state.phase !== "exploration") {
      this.state = state;
      return;
    }

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
      clearTimeout(this._attractTimer); // no attract mode once players are in
      this._renderLobby();
    }
    if (state.phase === "creation") {
      if (!this._activeControllerId) {
        const first = state.lobby_slots.find(
          s => s.status === "claimed" || s.status === "creating"
        );
        if (first) this._activeControllerId = first.controller_id;
      }
      this._renderCreation();
    }
  }

  // ─────────────────────── Gamepad / Keyboard input ───────────────────────

  handleControllerButton({ controllerId, button }) {
    if (this._attractVisible) { this._hideAttract(); return; }

    const clientPhase = document.body.dataset.phase;

    if (clientPhase === "intro") return; // intro handles its own skip via document events

    if (clientPhase === "title") {
      if (button === 0 || button === 9) this._exitTitlePhase(); // A or Start
      return;
    }

    if (clientPhase === "menu") {
      if (button === 0) this._handleMenuConfirm();              // A
      return;
    }

    if (clientPhase === "mode_select") {
      if (button === 0) this._handleModeConfirm();              // A
      if (button === 1) this._goToMenu();                       // B
      return;
    }

    if (clientPhase === "saves") {
      if (button === 0 && this._saves.length)
        this._loadSave(this._saves[this._saveFocus].campaign_id); // A
      if (button === 1) this._goToMenu();                          // B
      return;
    }

    // lobby / creation
    if (this.state.phase === "lobby" || this.state.phase === "creation") {
      if (button === 0) {
        // In creation with no active draft → everyone is done → start the game
        if (this.state.phase === "creation" && !this._activeControllerId) {
          this.handleStartGame();
        } else {
          this._handleConfirm(controllerId);
        }
      } else if (button === 1)   this._handleBButton(controllerId);
      else if (button === 4 || button === 5) this._cycleActiveDraft(button === 5 ? +1 : -1);
      else if (button === 9)     this.handleStartGame();
    }
  }

  handleControllerDpad({ controllerId, dx, dy }) {
    const clientPhase = document.body.dataset.phase;

    if (clientPhase === "menu") {
      this._menuFocus = Math.max(0, Math.min(1, this._menuFocus + (dy > 0 ? 1 : dy < 0 ? -1 : 0)));
      this._renderMenu();
      this.audio?.playCursor();
      return;
    }

    if (clientPhase === "mode_select") {
      this._modeFocus = Math.max(0, Math.min(1, this._modeFocus + (dy > 0 ? 1 : dy < 0 ? -1 : 0)));
      this._renderMode();
      this.audio?.playCursor();
      return;
    }

    if (clientPhase === "saves") {
      this._saveFocus = Math.max(0, Math.min(this._saves.length - 1,
        this._saveFocus + (dy > 0 ? 1 : dy < 0 ? -1 : 0)));
      this._renderSaves();
      this.audio?.playCursor();
      return;
    }

    if (this.state.phase !== "creation") return;
    if (controllerId !== this._activeControllerId) return;
    this._moveFocus(dx, dy);
  }

  handleKeyboard(e) {
    const clientPhase = document.body.dataset.phase;

    if (clientPhase === "title") {
      if (e.key === "Enter") this._exitTitlePhase();
      return;
    }

    if (clientPhase === "menu") {
      if (e.key === "ArrowUp")   { this._menuFocus = 0; this._renderMenu(); this.audio?.playCursor(); }
      if (e.key === "ArrowDown") { this._menuFocus = 1; this._renderMenu(); this.audio?.playCursor(); }
      if (e.key === "Enter")     this._handleMenuConfirm();
      return;
    }

    if (clientPhase === "mode_select") {
      if (e.key === "ArrowUp")   { this._modeFocus = 0; this._renderMode(); this.audio?.playCursor(); }
      if (e.key === "ArrowDown") { this._modeFocus = 1; this._renderMode(); this.audio?.playCursor(); }
      if (e.key === "Enter")     this._handleModeConfirm();
      if (e.key === "Escape")    this._goToMenu();
      return;
    }

    if (clientPhase === "saves") {
      if (e.key === "ArrowUp")   { this._saveFocus = Math.max(0, this._saveFocus - 1); this._renderSaves(); this.audio?.playCursor(); }
      if (e.key === "ArrowDown") { this._saveFocus = Math.min(this._saves.length - 1, this._saveFocus + 1); this._renderSaves(); this.audio?.playCursor(); }
      if (e.key === "Enter" && this._saves.length) this._loadSave(this._saves[this._saveFocus].campaign_id);
      if (e.key === "Escape")    this._goToMenu();
      return;
    }

    if (this.state.phase === "lobby") {
      if (e.key === "Enter") this.handleStartGame();
      if (e.key.toLowerCase() === "a" || e.key === " ") this._handleAButton("keyboard");
      return;
    }
    if (this.state.phase !== "creation") return;

    // When all players have finished creation, Enter/Space starts the adventure
    if (!this._activeControllerId) {
      if (e.key === "Enter" || e.key === " ") this.handleStartGame();
      return;
    }

    if (document.activeElement?.tagName === "INPUT") return;
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

  // ─────────────────────── Pre-lobby navigation ───────────────────────

  _exitTitlePhase() {
    if (document.body.dataset.phase !== "title") return;
    this.audio?.playConfirm();
    document.body.dataset.phase = "menu";
    this._menuFocus = 0;
    this._renderMenu();
  }

  _goToMenu() {
    document.body.dataset.phase = "menu";
    this._menuFocus = 0;
    this._renderMenu();
    this.audio?.playCursor();
  }

  _handleMenuConfirm() {
    if (this._menuFocus === 0) {
      this._showIntroCrawl(() => {
        this._modeFocus = 0;
        this._renderMode();
      });
      this.audio?.playPageTurn();
    } else {
      this._showSaves();
    }
  }

  _showIntroCrawl(onComplete) {
    const LINES = [
      "The world did not end.",
      "",
      "It refused to.",
      "",
      "The Weaver's Paradox did not arrive as war, or plague, or fire from the sky. It arrived as a silence — three seconds where every living thing forgot what it was.",
      "",
      "Most remembered wrong.",
      "",
      "The civilized races — their cities, their gods, their carefully arranged hierarchies of who mattered and who didn't — dissolved inside those three seconds. Not destroyed. Reorganized. The Paradox looked at what had been built and decided it was a first draft.",
      "",
      "What came after was not apocalypse.",
      "",
      "It was revision.",
      "",
      "The Cosmic wanderers had always known the world was temporary. The Primal things had roots deep enough to survive the silence. The Eldritch had never belonged to the old order at all.",
      "",
      "But the ones who called themselves civilized — the ones with names for everything, borders for everything, rules for everything —",
      "",
      "They held on.",
      "",
      "They changed.",
      "",
      "They are still here.",
      "",
      "And they are very difficult to kill.",
      "",
      "Welcome to what comes next.",
    ];

    document.body.dataset.phase = "intro";
    const content = document.getElementById("intro-content");
    content.innerHTML = "";

    let delay = 0.4;
    const WORD_GAP = 0.11;

    LINES.forEach(line => {
      const p = document.createElement("p");
      p.className = "intro-para";
      if (!line) {
        p.innerHTML = "&nbsp;";
        delay += 0.35;
      } else {
        line.split(" ").forEach((word, i, arr) => {
          const span = document.createElement("span");
          span.className = "burn-word";
          span.textContent = word + (i < arr.length - 1 ? " " : "");
          span.style.animationDelay = `${delay.toFixed(2)}s`;
          delay += WORD_GAP;
          p.appendChild(span);
        });
      }
      content.appendChild(p);
    });

    const totalMs = (delay + 1.8) * 1000;
    let autoTimer = setTimeout(finish, totalMs);
    let skipTimer = null;

    function startSkip() {
      if (skipTimer) return;
      const bar = document.getElementById("skip-bar");
      if (bar) { bar.style.transition = "width 3s linear"; bar.style.width = "100%"; }
      skipTimer = setTimeout(() => { clearTimeout(autoTimer); finish(); }, 3000);
    }

    function cancelSkip() {
      clearTimeout(skipTimer);
      skipTimer = null;
      const bar = document.getElementById("skip-bar");
      if (bar) { bar.style.transition = "none"; bar.style.width = "0%"; }
    }

    function finish() {
      clearTimeout(autoTimer);
      clearTimeout(skipTimer);
      document.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("keyup", onKeyUp);
      document.body.dataset.phase = "mode_select";
      onComplete();
    }

    const onKeyDown = (e) => {
      if (e.key === "Enter" || e.key === "a" || e.key === "A") startSkip();
    };
    const onKeyUp = (e) => {
      if (e.key === "Enter" || e.key === "a" || e.key === "A") cancelSkip();
    };

    document.addEventListener("keydown", onKeyDown);
    document.addEventListener("keyup", onKeyUp);
  }

  _handleModeConfirm() {
    this._startNewCampaign(this._modeFocus === 0); // 0 = solo
  }

  async _startNewCampaign(isSolo = false) {
    try {
      await newCampaign();
      this._drafts.clear();
      this._activeControllerId = null;
      this._focusIndex = 0;
      this._pool = null;
      this._pendingValue = null;

      if (isSolo) {
        // Skip the lobby entirely: claim one keyboard slot and go straight to creation.
        await joinLobby("keyboard");
        await setPhase("creation");
        document.body.dataset.phase = "creation";
      } else {
        document.body.dataset.phase = "lobby";
      }

      this.audio?.playConfirm();
      await this.onStateRefetch?.();
    } catch (err) {
      console.error("[lobby] new campaign failed:", err.message);
      this.audio?.playDeny();
    }
  }

  async _showSaves() {
    try {
      const data = await fetchCampaigns();
      this._saves = data.campaigns || [];
      this._saveFocus = 0;
      document.body.dataset.phase = "saves";
      this._renderSaves();
    } catch (err) {
      console.error("[lobby] fetch campaigns failed:", err.message);
      this.audio?.playDeny();
    }
  }

  async _loadSave(campaignId) {
    try {
      const state = await loadCampaign(campaignId);
      this._drafts.clear();
      this._activeControllerId = null;
      this._focusIndex = 0;
      this._pool = null;
      this._pendingValue = null;
      document.body.dataset.phase = state.phase;
      this.audio?.playConfirm();
      await this.onStateRefetch?.();
    } catch (err) {
      console.error("[lobby] load campaign failed:", err.message);
      this.audio?.playDeny();
    }
  }

  _renderAllReady() {
    // Reset step pills to all-done
    this._dom.stepPills.forEach(p => { p.classList.remove("active"); p.classList.add("done"); });
    this._dom.slotLabel.textContent = "";

    const readySlots = this.state.lobby_slots.filter(s => s.status === "ready");
    const names = readySlots.map(s => {
      const char = this.state.characters[s.character_id];
      return char?.name ?? "Hero";
    }).join(", ");

    this._dom.stage.innerHTML = `
      <div class="creation-all-ready">
        <p class="all-ready-names ink-gilded">${this._escape(names)}</p>
        <p class="all-ready-msg">${readySlots.length === 1 ? "Your hero is" : "All heroes are"} forged and ready.</p>
        <button class="btn btn-primary all-ready-begin">Begin Adventure <kbd>Enter</kbd></button>
      </div>
    `;
    this._dom.stage.querySelector(".all-ready-begin")
      ?.addEventListener("click", () => this.handleStartGame());
  }

  _renderMenu() {
    [this._dom.newGameBtn, this._dom.loadGameBtn].forEach((btn, i) => {
      btn?.classList.toggle("focused", i === this._menuFocus);
    });
  }

  _renderMode() {
    [this._dom.soloBtn, this._dom.multiBtn].forEach((btn, i) => {
      btn?.classList.toggle("focused", i === this._modeFocus);
    });
  }

  _renderSaves() {
    const container = this._dom.savesList;
    if (!container) return;
    container.innerHTML = "";

    if (this._saves.length === 0) {
      container.innerHTML = '<p class="saves-empty">No saved adventures found.</p>';
      return;
    }

    this._saves.forEach((save, idx) => {
      const card = document.createElement("div");
      card.className = "save-card";
      if (idx === this._saveFocus) card.classList.add("focused");

      const date = new Date(save.last_modified * 1000);
      const dateStr = date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })
        + " · " + date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      const chars = save.characters.length ? save.characters.join(", ") : "No heroes yet";
      const phaseLabel = { lobby: "At the Tavern", creation: "Forging Heroes", exploration: "On Adventure", combat: "In Combat" }[save.phase] ?? save.phase;

      card.innerHTML = `
        <div class="save-title ink-gilded">${this._escape(save.campaign_id)}</div>
        <div class="save-meta">
          <span class="save-phase">${this._escape(phaseLabel)}</span>
          <span class="save-chars">${this._escape(chars)}</span>
          <span class="save-date">${dateStr}</span>
        </div>
      `;
      card.addEventListener("click",      () => this._loadSave(save.campaign_id));
      card.addEventListener("mouseenter", () => { this._saveFocus = idx; this._renderSaves(); });
      container.appendChild(card);
    });
  }

  // ─────────────────────── Slot claim / release ───────────────────────

  async _handleConfirm(controllerId) {
    if (this.state.phase !== "creation") {
      return this._handleAButton(controllerId);
    }

    const draft = this._drafts.get(controllerId);
    if (!draft) return this._handleAButton(controllerId);

    if (controllerId === this._activeControllerId) {
      if (draft.step === "era") {
        const eras = ["before", "after"];
        draft.startingEra = eras[this._focusIndex];
      } else if (draft.step === "race") {
        const keys = Object.keys(this.catalog.races);
        draft.race = keys[this._focusIndex];
      } else if (draft.step === "state") {
        const keys = Object.keys(this.catalog.states);
        draft.evolutionState = keys[this._focusIndex];
      } else if (draft.step === "role") {
        const keys = Object.keys(this.catalog.roles);
        draft.predatorRole = keys[this._focusIndex];
      } else if (draft.step === "equipment") {
        if (draft.predatorRole) {
          const choices = this.catalog.roles[draft.predatorRole]?.equipment_choices ?? [];
          if (choices[this._focusIndex]) draft.equipmentChoiceId = choices[this._focusIndex].id;
        }
      } else if (draft.step === "background") {
        const keys = Object.keys(this.catalog.backgrounds);
        const chosen = keys[this._focusIndex];
        if (draft.background !== chosen) {
          draft.background = chosen;
          draft.skillProficiencies = [];
        }
      } else if (draft.step === "skills") {
        const allSkills = this.catalog.skills ?? [];
        const bgDef = draft.background ? (this.catalog.backgrounds ?? {})[draft.background] : null;
        const autoSkills = bgDef ? bgDef.bonus_skills : [];
        const skill = allSkills[this._focusIndex];
        if (skill && !autoSkills.includes(skill)) {
          if (draft.skillProficiencies.includes(skill)) {
            draft.skillProficiencies = draft.skillProficiencies.filter(s => s !== skill);
          } else if (draft.skillProficiencies.length < this._skillPicksNeeded(draft)) {
            draft.skillProficiencies = [...draft.skillProficiencies, skill];
          } else {
            this.audio?.playDeny();
          }
          this._renderCreation();
          this.audio?.playCursor();
          return;
        }
        return;
      } else if (draft.step === "feat") {
        const keys = Object.keys(this.catalog.feats);
        draft.feat = keys[this._focusIndex];
      } else if (draft.step === "abilities") {
        const abil = ABILITIES[this._focusIndex];
        if (!this._pool) {
          const assigned = Object.values(draft.abilities).filter(v => v != null);
          this._pool = STANDARD_ARRAY.filter(v => !assigned.includes(v));
        }
        if (draft.abilities[abil] != null) {
          this._pool.push(draft.abilities[abil]);
          draft.abilities[abil] = null;
          this._renderCreation();
          this.audio?.playCursor();
          return;
        } else if (this._pool.length > 0) {
          this._pool.sort((a, b) => b - a);
          draft.abilities[abil] = this._pool.shift();
          this._renderCreation();
          this.audio?.playConfirm();
          if (this._pool.length > 0) return;
        }
      }
      // name step confirm is handled inside _renderNameStep via Enter key
      await this.handleNext();
    } else {
      this._activeControllerId = controllerId;
      this._renderCreation();
      this.audio?.playCursor();
    }
  }

  async _handleAButton(controllerId) {
    if (this._drafts.has(controllerId)) return;
    try {
      const result = await joinLobby(controllerId);
      this.audio?.playConfirm();
      this._drafts.set(controllerId, this._emptyDraft(controllerId, result.slot_index));
      if (!this._activeControllerId) this._activeControllerId = controllerId;
      await this.onStateRefetch?.();
    } catch (err) {
      console.warn("[lobby] join failed:", err.message);
      this.audio?.playDeny();
    }
  }

  async _handleBButton(controllerId) {
    if (!this._drafts.has(controllerId)) return;
    if (this.state.phase === "creation") {
      const draft = this._drafts.get(controllerId);
      if (draft.step !== CREATION_ORDER[0]) { this.handleBack(); return; }
    }
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
    if (!ids.length) return;
    const cur = ids.indexOf(this._activeControllerId);
    this._activeControllerId = ids[(cur + direction + ids.length) % ids.length];
    this._focusIndex = 0;
    this._renderCreation();
    this.audio?.playCursor();
  }

  // ─────────────────────── Step navigation ───────────────────────

  async handleNext() {
    if (!this._activeControllerId) return;
    if (this._submitting) return;
    const draft = this._drafts.get(this._activeControllerId);
    if (!draft) return;

    const idx = CREATION_ORDER.indexOf(draft.step);

    if (!this._isStepComplete(draft, draft.step)) {
      this.audio?.playDeny();
      return;
    }

    if (idx === CREATION_ORDER.length - 1) {
      this._submitting = true;
      await this._commitDraft(draft);
      this._submitting = false;
    } else {
      draft.step = CREATION_ORDER[idx + 1];
      this._focusIndex = 0;
      this._pool = null;
      this._pendingValue = null;
      this._renderCreation();
      this.audio?.playPageTurn();
      // Persist draft so a page refresh can restore this step
      saveDraft(this._draftToServerPatch(draft)).catch(() => {});
    }
  }

  handleBack() {
    if (!this._activeControllerId) return;
    const draft = this._drafts.get(this._activeControllerId);
    if (!draft) return;

    const idx = CREATION_ORDER.indexOf(draft.step);
    if (idx === 0) return;

    draft.step = CREATION_ORDER[idx - 1];
    this._focusIndex = 0;
    this._pool = null;
    this._pendingValue = null;
    this._renderCreation();
    this.audio?.playPageTurn();
  }

  async _commitDraft(draft) {
    try {
      await createCharacter({
        slotIndex:           draft.slotIndex,
        name:                draft.name,
        race:                draft.race,
        evolutionState:      draft.evolutionState,
        predatorRole:        draft.predatorRole,
        abilities:           draft.abilities,
        startingEra:         draft.startingEra,
        equipmentChoiceId:   draft.equipmentChoiceId,
        background:          draft.background,
        skillProficiencies:  draft.skillProficiencies,
        feat:                draft.feat,
        cantrips:            draft.cantrips,
        alignment:           draft.alignment,
        pronouns:            draft.pronouns,
        title:               draft.title,
        dialogueStyle:       draft.dialogueStyle,
        physicalDescription: draft.physicalDescription,
        backstory:           draft.backstory,
        personalityTraits:   draft.personalityTraits,
        flaws:               draft.flaws,
        bonds:               draft.bonds,
        ideals:              draft.ideals,
        keepsakeName:        draft.keepsakeName,
      });
      this.audio?.playConfirm();
      this._drafts.delete(draft.controllerId);
      this._activeControllerId = [...this._drafts.keys()][0] ?? null;
      await this.onStateRefetch?.();
    } catch (err) {
      console.error("[creation] commit failed:", err.message);
      this.audio?.playDeny();
    }
  }

  async handleStartGame() {
    if (this._dom.startBtn?.disabled) return;
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

      const nameContainer = document.createElement("div");
      nameContainer.className = "slot-name-container";

      const nameInput = document.createElement("input");
      nameInput.type = "text";
      nameInput.placeholder = "Enter name...";
      nameInput.className = "slot-name-input";
      nameInput.value = slot.name_draft || "";
      nameInput.disabled = slot.status === "ready";

      nameInput.addEventListener("change", async (e) => {
        const val = e.target.value.trim();
        if (val) {
          try {
            await updateLobbyName({
              slotIndex:    slot.slot_index,
              name:         val,
              controllerId: slot.controller_id || `mouse_${slot.slot_index}`,
            });
            this.audio?.playConfirm();
          } catch (err) {
            console.error("[lobby] name update failed:", err);
            this.audio?.playDeny();
          }
        }
      });

      nameContainer.appendChild(nameInput);
      card.appendChild(nameContainer);

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
    }

    // Start button
    const claimedSlots = this.state.lobby_slots.filter(s => s.status !== "empty");
    const readyCount   = this.state.lobby_slots.filter(s => s.status === "ready").length;

    if (this.state.phase === "lobby") {
      this._dom.startBtn.disabled = claimedSlots.length === 0;
      this._dom.startBtn.textContent = claimedSlots.length > 0
        ? `Start Hero Creation (${claimedSlots.length} ${claimedSlots.length === 1 ? "player" : "players"})`
        : "Join a slot to start";
      this._dom.startBtn.onclick = async () => {
        try {
          await setPhase("creation");
          await this.onStateRefetch?.();
          this.audio?.playPageTurn();
        } catch (err) {
          console.error("[lobby] phase transition failed:", err);
          this.audio?.playDeny();
        }
      };
    } else {
      this._dom.startBtn.disabled = readyCount < 1;
      this._dom.startBtn.textContent = readyCount > 0
        ? `Begin Adventure (${readyCount} ${readyCount === 1 ? "hero" : "heroes"})`
        : "Finish creating heroes";
      this._dom.startBtn.onclick = () => this.handleStartGame();
    }
  }

  _slotStatusText(slot) {
    return { empty: "Available", claimed: "Joined", creating: "Forging…", ready: "Ready" }[slot.status] ?? slot.status;
  }

  // ─────────────────────── Rendering: creation ───────────────────────

  _renderCreation() {
    if (!this._activeControllerId) {
      const next = this.state.lobby_slots.find(s => s.status !== "ready" && s.controller_id);
      if (next) {
        this._activeControllerId = next.controller_id;
        if (!this._drafts.has(this._activeControllerId))
          this._drafts.set(this._activeControllerId, this._draftFromSlot(next));
      } else {
        // All players finished — show the launch screen
        this._renderAllReady();
        return;
      }
    }

    const draft = this._drafts.get(this._activeControllerId);
    if (!draft) { this._renderAllReady(); return; }

    const currentIdx = CREATION_ORDER.indexOf(draft.step);

    this._dom.stepPills.forEach((pill, i) => {
      pill.classList.remove("active", "done");
      if (i === currentIdx) pill.classList.add("active");
      if (i < currentIdx)  pill.classList.add("done");
    });

    // Multi-player progress strip
    const activePlayers = this.state.lobby_slots.filter(s => s.status !== "empty");
    if (activePlayers.length > 1) {
      const existing = this._dom.creationView?.querySelector(".player-progress");
      if (existing) existing.remove();
      const strip = document.createElement("div");
      strip.className = "player-progress";
      activePlayers.forEach(slot => {
        const pip = document.createElement("div");
        pip.className = "player-pip";
        const isActive = slot.controller_id === this._activeControllerId;
        const isDone   = slot.status === "ready";
        if (isDone)   pip.classList.add("done");
        if (isActive) pip.classList.add("active");
        const char = this.state.characters[slot.character_id];
        pip.textContent = isDone
          ? `${char?.name ?? slot.name_draft ?? `P${slot.slot_index + 1}`} ✓`
          : (slot.name_draft?.trim() || `Player ${slot.slot_index + 1}`);
        strip.appendChild(pip);
      });
      if (activePlayers.length > 1) {
        const hint = document.createElement("span");
        hint.className = "player-pip-hint";
        hint.textContent = "Tab / LB·RB to switch";
        strip.appendChild(hint);
      }
      this._dom.creationView?.insertBefore(strip, this._dom.creationView.querySelector(".creation-steps"));
    }

    this._dom.slotLabel.textContent = `Forging: ${draft.name.trim() || `Slot ${draft.slotIndex + 1}`}`;

    this._dom.stage.innerHTML = "";
    switch (draft.step) {
      case "era":        this._renderEraStep(draft);        break;
      case "race":       this._renderRaceStep(draft);       break;
      case "state":      this._renderStateStep(draft);      break;
      case "role":       this._renderRoleStep(draft);       break;
      case "equipment":  this._renderEquipmentStep(draft);  break;
      case "background": this._renderBackgroundStep(draft); break;
      case "abilities":  this._renderAbilitiesStep(draft);  break;
      case "skills":     this._renderSkillsStep(draft);     break;
      case "feat":       this._renderFeatStep(draft);       break;
      case "identity":   this._renderIdentityStep(draft);   break;
      case "story":      this._renderStoryStep(draft);      break;
      case "name":       this._renderNameStep(draft);       break;
    }

    this._scrollFocusedIntoView();
  }

  _scrollFocusedIntoView() {
    this._dom.stage.querySelector(".focused")?.scrollIntoView({ block: "nearest" });
  }

  _renderEraStep(draft) {
    const eras = [
      {
        id: "before", glyph: "☀",
        name: "Before — The Civilized World",
        subtitle: "You are what you were",
        flavor: "Start as the race you were before the Paradox. Your Feral transformation will hit mid-game.",
        detail: "Human · Elf · Dwarf · the old names still hold"
      },
      {
        id: "after", glyph: "🜏",
        name: "After — The Feral World",
        subtitle: "The Paradox already found you",
        flavor: "You start in your evolved Feral Successor form. The Civilized World is a memory.",
        detail: "Voidwraith · Ashenborn · Ironveil · what you became"
      },
    ];
    const grid = document.createElement("div");
    grid.className = "option-grid era-grid";
    eras.forEach((era, idx) => {
      const selected = draft.startingEra === era.id;
      const focused  = idx === this._focusIndex;
      const card = document.createElement("div");
      card.className = `option-card era-card era-card--${era.id}${selected ? " selected" : ""}${focused ? " focused" : ""}`;
      card.innerHTML = `
        <div class="era-glyph">${era.glyph}</div>
        <h3>${this._escape(era.name)}</h3>
        <p class="era-subtitle">${this._escape(era.subtitle)}</p>
        <p class="flavor">${this._escape(era.flavor)}</p>
        <p class="era-detail">${this._escape(era.detail)}</p>
      `;
      card.addEventListener("click",      () => { draft.startingEra = era.id; this._renderCreation(); this.audio?.playCursor(); });
      card.addEventListener("mouseenter", () => { this._focusIndex = idx; this._renderCreation(); });
      grid.appendChild(card);
    });
    this._dom.stage.appendChild(grid);
  }

  _renderRaceStep(draft) {
    const entries = Object.entries(this.catalog.races);
    const groups = ["Cosmic", "Primal", "Eldritch", "Mechanical", "Humanoid"];
    let globalIdx = 0;
    const container = document.createElement("div");
    container.className = "race-groups";

    groups.forEach(group => {
      const groupEntries = entries.filter(([, def]) => def.group === group);
      if (!groupEntries.length) return;

      const section = document.createElement("div");
      section.className = group === "Humanoid" ? "race-group humanoid-group" : "race-group";

      const heading = document.createElement("h3");
      heading.className = "race-group-heading";
      heading.textContent = group;
      section.appendChild(heading);

      if (group === "Humanoid") {
        const hint = document.createElement("p");
        hint.className = "humanoid-hint";
        hint.textContent = "What you were — and what the Paradox made you.";
        section.appendChild(hint);
      }

      const grid = document.createElement("div");
      grid.className = group === "Humanoid" ? "option-grid humanoid-grid" : "option-grid";

      groupEntries.forEach(([key, def]) => {
        const idx = globalIdx++;
        let card;
        
        const isBeforeEra = draft.startingEra === "before";

        if (def.before) {
          // Humanoid race — has a civilized "before" form and a feral "after" form
          card = document.createElement("div");
          card.className = "option-card humanoid-card";
          if (draft.race === key) card.classList.add("selected");
          if (idx === this._focusIndex) card.classList.add("focused");

          if (isBeforeEra) {
            card.innerHTML = `
              <div class="humanoid-before-label">Start as: <span>${this._escape(def.before)}</span></div>
              <div class="humanoid-arrow">↓ Paradox</div>
              <h3>${this._escape(def.name)}</h3>
              <p class="flavor">${this._escape(def.flavor)}</p>
              <div class="stats">Speed: ${def.speed}ft · ${Object.entries(def.ability_bonuses).map(([a, b]) => `${a} +${b}`).join(", ")}</div>
            `;
          } else {
            card.innerHTML = `
              <div class="humanoid-before-label">Before: <span>${this._escape(def.before)}</span></div>
              <div class="humanoid-arrow">↓ Paradox</div>
              <h3>${this._escape(def.name)}</h3>
              <p class="flavor">${this._escape(def.flavor)}</p>
              <div class="stats">Speed: ${def.speed}ft · ${Object.entries(def.ability_bonuses).map(([a, b]) => `${a} +${b}`).join(", ")}</div>
            `;
          }
        } else {
          // Non-humanoid race (Cosmic / Primal / Eldritch / Mechanical) — no before form
          card = this._optionCard(def.name, def.flavor,
            `Speed: ${def.speed}ft · ${Object.entries(def.ability_bonuses).map(([a, b]) => `${a} +${b}`).join(", ")}`,
            draft.race === key, idx === this._focusIndex);
        }
        card.addEventListener("click",      () => { draft.race = key; this._renderCreation(); this.audio?.playCursor(); });
        card.addEventListener("mouseenter", () => { this._focusIndex = idx; this._renderCreation(); });
        grid.appendChild(card);
      });

      section.appendChild(grid);
      container.appendChild(section);
    });

    this._dom.stage.appendChild(container);
  }

  _renderStateStep(draft) {
    const grid = document.createElement("div");
    grid.className = "option-grid";
    Object.entries(this.catalog.states).forEach(([key, def], idx) => {
      const card = this._optionCard(def.name, def.flavor,
        `Hit Die: d${def.hit_die} · Base AC: ${def.base_armor_class}`,
        draft.evolutionState === key, idx === this._focusIndex);
      card.addEventListener("click",      () => { draft.evolutionState = key; this._renderCreation(); this.audio?.playCursor(); });
      card.addEventListener("mouseenter", () => { this._focusIndex = idx; this._renderCreation(); });
      grid.appendChild(card);
    });
    this._dom.stage.appendChild(grid);
  }

  _renderRoleStep(draft) {
    const grid = document.createElement("div");
    grid.className = "option-grid";
    Object.entries(this.catalog.roles).forEach(([key, def], idx) => {
      const inv = def.starting_inventory.map(i => i.name).join(", ");
      const card = this._optionCard(def.name, def.flavor,
        `Gear: ${inv}`,
        draft.predatorRole === key, idx === this._focusIndex);
      card.addEventListener("click",      () => { draft.predatorRole = key; this._renderCreation(); this.audio?.playCursor(); });
      card.addEventListener("mouseenter", () => { this._focusIndex = idx; this._renderCreation(); });
      grid.appendChild(card);
    });
    this._dom.stage.appendChild(grid);
  }

  _renderEquipmentStep(draft) {
    const role = draft.predatorRole ? this.catalog.roles[draft.predatorRole] : null;
    if (!role) { this._dom.stage.innerHTML = "<p>Select a role first.</p>"; return; }

    const wrap = document.createElement("div");
    wrap.className = "equipment-stage";

    const primary = document.createElement("div");
    primary.className = "equipment-primary";
    primary.innerHTML = `
      <h3 class="equipment-heading">Always Equipped</h3>
      <div class="equipment-item-card fixed">
        <span class="item-name">${this._escape(role.primary_item.name)}</span>
        ${role.primary_item.notes ? `<span class="item-notes">${this._escape(role.primary_item.notes)}</span>` : ""}
      </div>
    `;
    wrap.appendChild(primary);

    const secondary = document.createElement("div");
    secondary.className = "equipment-choices";
    const heading = document.createElement("h3");
    heading.className = "equipment-heading";
    heading.textContent = "Choose Your Secondary Gear";
    secondary.appendChild(heading);

    const grid = document.createElement("div");
    grid.className = "option-grid";
    (role.equipment_choices ?? []).forEach((item, idx) => {
      const card = document.createElement("div");
      card.className = "option-card equipment-choice-card";
      if (draft.equipmentChoiceId === item.id) card.classList.add("selected");
      if (idx === this._focusIndex) card.classList.add("focused");
      card.innerHTML = `
        <h3>${this._escape(item.name)}</h3>
        ${item.notes ? `<p class="flavor">${this._escape(item.notes)}</p>` : ""}
        ${item.quantity > 1 ? `<div class="stats">Qty: ${item.quantity}</div>` : ""}
      `;
      card.addEventListener("click", () => {
        draft.equipmentChoiceId = item.id;
        this._renderCreation();
        this.audio?.playCursor();
      });
      card.addEventListener("mouseenter", () => { this._focusIndex = idx; this._renderCreation(); });
      grid.appendChild(card);
    });
    secondary.appendChild(grid);
    wrap.appendChild(secondary);
    this._dom.stage.appendChild(wrap);
  }

  _renderBackgroundStep(draft) {
    const entries = Object.entries(this.catalog.backgrounds ?? {});
    const grid = document.createElement("div");
    grid.className = "option-grid";

    entries.forEach(([key, def], idx) => {
      const card = document.createElement("div");
      card.className = "option-card background-card";
      if (draft.background === key) card.classList.add("selected");
      if (idx === this._focusIndex) card.classList.add("focused");
      card.innerHTML = `
        <h3>${this._escape(def.name)}</h3>
        <p class="flavor">${this._escape(def.flavor)}</p>
        <div class="background-perk">
          <span class="perk-name">${this._escape(def.perk_name)}</span>
          <span class="perk-desc">${this._escape(def.perk_description)}</span>
        </div>
        <div class="stats">Auto-skills: ${def.bonus_skills.join(", ")}</div>
      `;
      card.addEventListener("click", () => {
        draft.background = key;
        // Reset skill picks if background changes
        draft.skillProficiencies = [];
        this._renderCreation();
        this.audio?.playCursor();
      });
      card.addEventListener("mouseenter", () => { this._focusIndex = idx; this._renderCreation(); });
      grid.appendChild(card);
    });
    this._dom.stage.appendChild(grid);
  }

  _renderSkillsStep(draft) {
    const allSkills = this.catalog.skills ?? [];
    const bgDef = draft.background ? (this.catalog.backgrounds ?? {})[draft.background] : null;
    const autoSkills  = bgDef ? bgDef.bonus_skills  : [];
    const poolSkills  = bgDef ? bgDef.skill_pool     : [];
    const needed = this._skillPicksNeeded(draft);

    const wrap = document.createElement("div");
    wrap.className = "skills-stage";

    if (autoSkills.length > 0) {
      const autoSection = document.createElement("div");
      autoSection.className = "skills-auto";
      autoSection.innerHTML = `<p class="skills-auto-label">Granted by background:</p>
        <div class="skills-auto-chips">${autoSkills.map(s =>
          `<span class="skill-chip auto">${this._escape(s)}</span>`
        ).join("")}</div>`;
      wrap.appendChild(autoSection);
    }

    if (poolSkills.length > 0) {
      const hint = document.createElement("p");
      hint.className = "skills-pool-hint";
      hint.textContent = "★ Suggested by your background — pick any 2 you like:";
      wrap.appendChild(hint);
    }

    const pickLabel = document.createElement("p");
    const remaining = Math.max(0, needed - draft.skillProficiencies.length);
    pickLabel.className = "skills-pick-label";
    pickLabel.textContent = remaining > 0
      ? `Choose ${remaining} more skill proficien${remaining === 1 ? "cy" : "cies"}:`
      : "Skills chosen! Click Next to continue.";
    wrap.appendChild(pickLabel);

    const grid = document.createElement("div");
    grid.className = "skills-grid";
    allSkills.forEach((skill, idx) => {
      const isAuto     = autoSkills.includes(skill);
      const isSuggested = poolSkills.includes(skill) && !isAuto;
      const isPicked   = draft.skillProficiencies.includes(skill);
      const isFocused  = idx === this._focusIndex;
      const canPick    = !isAuto && !isPicked && draft.skillProficiencies.length < needed;

      const chip = document.createElement("div");
      chip.className = "skill-option-chip";
      if (isAuto)      chip.classList.add("auto");
      if (isSuggested) chip.classList.add("suggested");
      if (isPicked)    chip.classList.add("selected");
      if (isFocused)   chip.classList.add("focused");
      chip.textContent = isSuggested ? `★ ${skill}` : skill;

      if (!isAuto) {
        chip.addEventListener("click", () => {
          if (isPicked) {
            draft.skillProficiencies = draft.skillProficiencies.filter(s => s !== skill);
          } else if (canPick) {
            draft.skillProficiencies = [...draft.skillProficiencies, skill];
          }
          this._renderCreation();
          this.audio?.playCursor();
        });
        chip.addEventListener("mouseenter", () => { this._focusIndex = idx; this._renderCreation(); });
      }
      grid.appendChild(chip);
    });
    wrap.appendChild(grid);

    // Optional cantrips section
    const cantrips = this.catalog.cantrips ?? [];
    if (cantrips.length > 0) {
      const cantripSection = document.createElement("div");
      cantripSection.className = "cantrip-section";
      cantripSection.innerHTML = `<p class="cantrip-label">Optional — Pick up to 2 cantrips (narrative flavor for the AI narrator):</p>`;
      const cantripGrid = document.createElement("div");
      cantripGrid.className = "skills-grid";
      cantrips.forEach(c => {
        const chip = document.createElement("div");
        chip.className = "skill-option-chip cantrip";
        if (draft.cantrips.includes(c)) chip.classList.add("selected");
        chip.textContent = c;
        chip.addEventListener("click", () => {
          if (draft.cantrips.includes(c)) {
            draft.cantrips = draft.cantrips.filter(x => x !== c);
          } else if (draft.cantrips.length < 2) {
            draft.cantrips = [...draft.cantrips, c];
          }
          this._renderCreation();
          this.audio?.playCursor();
        });
        cantripGrid.appendChild(chip);
      });
      cantripSection.appendChild(cantripGrid);
      wrap.appendChild(cantripSection);
    }

    this._dom.stage.appendChild(wrap);
  }

  _renderFeatStep(draft) {
    const entries = Object.entries(this.catalog.feats ?? {});
    const grid = document.createElement("div");
    grid.className = "option-grid";
    entries.forEach(([key, def], idx) => {
      const card = this._optionCard(def.name, def.flavor, def.mechanical_effect,
        draft.feat === key, idx === this._focusIndex);
      card.addEventListener("click", () => { draft.feat = key; this._renderCreation(); this.audio?.playCursor(); });
      card.addEventListener("mouseenter", () => { this._focusIndex = idx; this._renderCreation(); });
      grid.appendChild(card);
    });
    this._dom.stage.appendChild(grid);
  }

  _renderIdentityStep(draft) {
    const wrap = document.createElement("div");
    wrap.className = "identity-stage";

    // Pronouns
    const pronounOptions = ["he/him", "she/her", "they/them", "xe/xem"];
    wrap.appendChild(this._identitySection("Pronouns", `
      <div class="identity-chips">
        ${pronounOptions.map(p => `
          <div class="identity-chip ${draft.pronouns === p ? "selected" : ""}" data-value="${p}">${p}</div>
        `).join("")}
      </div>
      <input type="text" class="identity-text-input" id="pronouns-custom" placeholder="Custom pronouns…"
        value="${!pronounOptions.includes(draft.pronouns) ? this._escape(draft.pronouns) : ""}"
        style="margin-top:0.5rem;width:100%">
    `));

    // Title
    const titleOptions = ["None", "Sir", "Dame", "Captain", "Scholar", "Warden", "Huntmaster", "Vessel", "Ghost"];
    wrap.appendChild(this._identitySection("Title", `
      <div class="identity-chips">
        ${titleOptions.map(t => `
          <div class="identity-chip ${(draft.title ?? "None") === t ? "selected" : ""}" data-title="${t}">${t}</div>
        `).join("")}
      </div>
      <input type="text" class="identity-text-input" id="title-custom" placeholder="Custom title…"
        value="${(draft.title && !titleOptions.includes(draft.title)) ? this._escape(draft.title) : ""}"
        style="margin-top:0.5rem;width:100%">
    `));

    // Alignment (3×3 grid)
    const alignments = this.catalog.alignments ?? [];
    wrap.appendChild(this._identitySection("Alignment", `
      <div class="alignment-grid">
        ${alignments.map(a => `
          <div class="alignment-chip ${draft.alignment === a ? "selected" : ""}" data-align="${this._escape(a)}">${this._escape(a)}</div>
        `).join("")}
      </div>
    `));

    // Dialogue Style
    const styles = this.catalog.dialogue_styles ?? [];
    wrap.appendChild(this._identitySection("Dialogue Voice", `
      <div class="identity-chips style-chips">
        ${styles.map(s => `
          <div class="identity-chip style-chip ${draft.dialogueStyle === s.id ? "selected" : ""}" data-style="${s.id}" title="${this._escape(s.flavor)}">
            ${this._escape(s.name)}
          </div>
        `).join("")}
      </div>
    `));

    this._dom.stage.appendChild(wrap);

    // Wire up events after insertion
    wrap.querySelectorAll(".identity-chip[data-value]").forEach(el => {
      el.addEventListener("click", () => {
        draft.pronouns = el.dataset.value;
        wrap.querySelectorAll(".identity-chip[data-value]").forEach(c => c.classList.remove("selected"));
        el.classList.add("selected");
        wrap.querySelector("#pronouns-custom").value = "";
        this.audio?.playCursor();
      });
    });
    wrap.querySelector("#pronouns-custom")?.addEventListener("input", e => {
      if (e.target.value) {
        draft.pronouns = e.target.value;
        wrap.querySelectorAll(".identity-chip[data-value]").forEach(c => c.classList.remove("selected"));
      }
    });

    wrap.querySelectorAll(".identity-chip[data-title]").forEach(el => {
      el.addEventListener("click", () => {
        const t = el.dataset.title;
        draft.title = t === "None" ? null : t;
        wrap.querySelectorAll(".identity-chip[data-title]").forEach(c => c.classList.remove("selected"));
        el.classList.add("selected");
        wrap.querySelector("#title-custom").value = "";
        this.audio?.playCursor();
      });
    });
    wrap.querySelector("#title-custom")?.addEventListener("input", e => {
      if (e.target.value) {
        draft.title = e.target.value;
        wrap.querySelectorAll(".identity-chip[data-title]").forEach(c => c.classList.remove("selected"));
      }
    });

    wrap.querySelectorAll(".alignment-chip").forEach(el => {
      el.addEventListener("click", () => {
        draft.alignment = el.dataset.align;
        wrap.querySelectorAll(".alignment-chip").forEach(c => c.classList.remove("selected"));
        el.classList.add("selected");
        this.audio?.playCursor();
      });
    });

    wrap.querySelectorAll(".style-chip").forEach(el => {
      el.addEventListener("click", () => {
        draft.dialogueStyle = el.dataset.style;
        wrap.querySelectorAll(".style-chip").forEach(c => c.classList.remove("selected"));
        el.classList.add("selected");
        this.audio?.playCursor();
      });
    });
  }

  _identitySection(label, innerHtml) {
    const section = document.createElement("div");
    section.className = "identity-section";
    section.innerHTML = `<h4 class="identity-section-label">${this._escape(label)}</h4>${innerHtml}`;
    return section;
  }

  _renderStoryStep(draft) {
    const wrap = document.createElement("div");
    wrap.className = "story-stage";

    const fields = [
      { key: "physicalDescription", label: "Physical Description",  placeholder: "Describe how your character looks, moves, or sounds…", rows: 3 },
      { key: "personalityTraits",   label: "Personality Traits",    placeholder: "What makes this character tick?", rows: 2 },
      { key: "backstory",           label: "Backstory",             placeholder: "Where did they come from? What shaped them?", rows: 3 },
      { key: "ideals",              label: "Ideals",                placeholder: "What do they believe in above all else?", rows: 2 },
      { key: "bonds",               label: "Bonds",                 placeholder: "Who or what do they care about most?", rows: 2 },
      { key: "flaws",               label: "Flaws",                 placeholder: "What's their weakness, vice, or blind spot?", rows: 2 },
    ];

    fields.forEach(f => {
      const group = document.createElement("div");
      group.className = "story-field-group";
      const label = document.createElement("label");
      label.className = "story-label";
      label.textContent = f.label;
      const ta = document.createElement("textarea");
      ta.className = "story-textarea";
      ta.rows = f.rows;
      ta.placeholder = f.placeholder;
      ta.value = draft[f.key] ?? "";
      ta.addEventListener("input", e => { draft[f.key] = e.target.value; });
      group.appendChild(label);
      group.appendChild(ta);
      wrap.appendChild(group);
    });

    // Keepsake / Trinket
    const keepsakeGroup = document.createElement("div");
    keepsakeGroup.className = "story-field-group";
    const keepsakeLabel = document.createElement("label");
    keepsakeLabel.className = "story-label";
    keepsakeLabel.textContent = "Keepsake / Trinket";
    const keepsakeInput = document.createElement("input");
    keepsakeInput.type = "text";
    keepsakeInput.className = "story-text-input";
    keepsakeInput.placeholder = "A glowing coin, a letter from a dead relative, a broken locket…";
    keepsakeInput.maxLength = 100;
    keepsakeInput.value = draft.keepsakeName ?? "";
    keepsakeInput.addEventListener("input", e => { draft.keepsakeName = e.target.value || null; });

    const keepsakeHint = document.createElement("p");
    keepsakeHint.className = "story-hint";
    keepsakeHint.textContent = "No mechanical value — pure flavor. The AI narrator will remember it.";

    keepsakeGroup.appendChild(keepsakeLabel);
    keepsakeGroup.appendChild(keepsakeInput);
    keepsakeGroup.appendChild(keepsakeHint);
    wrap.appendChild(keepsakeGroup);

    this._dom.stage.appendChild(wrap);
  }

  _optionCard(name, flavor, stats, selected, focused) {
    const card = document.createElement("div");
    card.className = "option-card";
    if (selected) card.classList.add("selected");
    if (focused)  card.classList.add("focused");
    card.innerHTML = `
      <h3>${this._escape(name)}</h3>
      <p class="flavor">${this._escape(flavor)}</p>
      <div class="stats">${this._escape(stats)}</div>
    `;
    return card;
  }

  _renderAbilitiesStep(draft) {
    const stage = document.createElement("div");

    const help = document.createElement("p");
    help.style.cssText = "text-align:center;margin-bottom:var(--space-2)";
    help.textContent = "Assign the standard array to each ability.";
    stage.appendChild(help);

    if (!this._pool) {
      const assigned = Object.values(draft.abilities).filter(v => v != null);
      this._pool = STANDARD_ARRAY.filter(v => !assigned.includes(v));
    }

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

      row.appendChild(name);
      row.appendChild(val);
      row.addEventListener("mouseenter", () => { this._focusIndex = i; this._renderCreation(); });
      row.addEventListener("click", () => {
        if (this._pendingValue != null) {
          if (draft.abilities[abil] != null) this._pool.push(draft.abilities[abil]);
          draft.abilities[abil] = this._pendingValue;
          this._pool = this._pool.filter(v => v !== this._pendingValue);
          this._pendingValue = null;
          this._renderCreation();
          this.audio?.playConfirm();
        } else if (draft.abilities[abil] != null) {
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
    label.className = "name-prompt";
    label.textContent = "What is your hero called?";
    wrap.appendChild(label);

    const input = document.createElement("input");
    input.type = "text";
    input.className = "name-input";
    input.maxLength = 24;
    input.placeholder = "Kael, Lyra, Whisper…";
    input.value = draft.name;

    input.addEventListener("input", (e) => { draft.name = e.target.value; });
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.stopPropagation();
        if (draft.name.trim()) this.handleNext();
      }
    });
    wrap.appendChild(input);

    // Preview line showing race · state · role
    if (draft.race && draft.evolutionState && draft.predatorRole) {
      const preview = document.createElement("p");
      preview.className = "name-preview";
      preview.textContent =
        `${this.catalog.races[draft.race]?.name ?? "—"} · ` +
        `${this.catalog.states[draft.evolutionState]?.name ?? "—"} · ` +
        `${this.catalog.roles[draft.predatorRole]?.name ?? "—"}`;
      wrap.appendChild(preview);
    }

    this._dom.stage.appendChild(wrap);
    setTimeout(() => input.focus(), 50);
  }

  // ─────────────────────── Helpers ───────────────────────

  _isStepComplete(draft, step) {
    switch (step) {
      case "era":        return draft.startingEra != null;
      case "race":       return draft.race != null;
      case "state":      return draft.evolutionState != null;
      case "role":       return draft.predatorRole != null;
      case "equipment":  return draft.equipmentChoiceId != null;
      case "background": return draft.background != null;
      case "abilities":  return ABILITIES.every(a => draft.abilities[a] != null);
      case "skills": {
        const needed = this._skillPicksNeeded(draft);
        return draft.skillProficiencies.length >= needed;
      }
      case "feat":       return draft.feat != null;
      case "identity":   return true;  // all optional
      case "story":      return true;  // all optional
      case "name":       return draft.name.trim().length > 0;
      default:           return false;
    }
  }

  _skillPicksNeeded(draft) {
    // Players pick 2 skills freely; background auto-adds its bonus_skills on the server.
    return 2;
  }

  _moveFocus(dx, dy) {
    const draft = this._drafts.get(this._activeControllerId);
    if (!draft) return;
    const stepSizes = {
      era:        2,
      race:       Object.keys(this.catalog.races).length,
      state:      Object.keys(this.catalog.states).length,
      role:       Object.keys(this.catalog.roles).length,
      equipment:  draft.predatorRole ? (this.catalog.roles[draft.predatorRole]?.equipment_choices?.length ?? 1) : 1,
      background: Object.keys(this.catalog.backgrounds ?? {}).length,
      abilities:  ABILITIES.length,
      skills:     (this.catalog.skills ?? []).length,
      feat:       Object.keys(this.catalog.feats ?? {}).length,
      identity:   1,
      story:      1,
      name:       1,
    };
    const max     = stepSizes[draft.step] ?? 0;
    if (!max) return;
    const columns = ["era", "race", "state", "role", "equipment", "background", "feat"].includes(draft.step)
      ? Math.max(1, Math.floor((this._dom.stage.clientWidth || 900) / 300))
      : 1;
    let next = this._focusIndex + dx + dy * columns;
    next = Math.max(0, Math.min(max - 1, next));
    this._focusIndex = next;
    this._renderCreation();
    this.audio?.playCursor();
  }

  _emptyDraft(controllerId, slotIndex) {
    return {
      controllerId,
      slotIndex,
      step: "era",
      startingEra: "after",
      race: null,
      evolutionState: null,
      predatorRole: null,
      equipmentChoiceId: null,
      background: null,
      abilities: { STR: null, DEX: null, CON: null, INT: null, WIS: null, CHA: null },
      skillProficiencies: [],
      feat: null,
      cantrips: [],
      alignment: null,
      pronouns: "they/them",
      title: null,
      dialogueStyle: null,
      physicalDescription: "",
      backstory: "",
      personalityTraits: "",
      flaws: "",
      bonds: "",
      ideals: "",
      keepsakeName: null,
      name: "",
    };
  }

  _draftFromSlot(slot) {
    const draft = this._emptyDraft(slot.controller_id, slot.slot_index);
    // Core fields
    draft.race              = slot.race ?? null;
    draft.evolutionState    = slot.evolution_state ?? null;
    draft.predatorRole      = slot.predator_role ?? null;
    draft.startingEra       = slot.starting_era ?? "after";
    draft.abilities         = slot.assigned_abilities
      ?? { STR: null, DEX: null, CON: null, INT: null, WIS: null, CHA: null };
    draft.name              = slot.name_draft ?? "";
    // Extended customisation fields
    draft.equipmentChoiceId  = slot.equipment_choice_id ?? null;
    draft.background         = slot.background ?? null;
    draft.skillProficiencies = slot.skill_proficiencies ?? [];
    draft.feat               = slot.feat ?? null;
    draft.cantrips           = slot.cantrips ?? [];
    draft.alignment          = slot.alignment ?? null;
    draft.pronouns           = slot.pronouns ?? "they/them";
    draft.title              = slot.title ?? null;
    draft.dialogueStyle      = slot.dialogue_style ?? null;
    draft.physicalDescription = slot.physical_description ?? "";
    draft.backstory          = slot.backstory ?? "";
    draft.personalityTraits  = slot.personality_traits ?? "";
    draft.flaws              = slot.flaws ?? "";
    draft.bonds              = slot.bonds ?? "";
    draft.ideals             = slot.ideals ?? "";
    draft.keepsakeName       = slot.keepsake_name ?? null;
    // Restore the step the player was on
    draft.step = slot.creation_step ?? "era";
    return draft;
  }

  _draftToServerPatch(draft) {
    return {
      controller_id:        draft.controllerId,
      creation_step:        draft.step,
      race:                 draft.race,
      evolution_state:      draft.evolutionState,
      predator_role:        draft.predatorRole,
      starting_era:         draft.startingEra,
      assigned_abilities:   Object.values(draft.abilities).every(v => v != null) ? draft.abilities : null,
      equipment_choice_id:  draft.equipmentChoiceId,
      background:           draft.background,
      skill_proficiencies:  draft.skillProficiencies,
      feat:                 draft.feat,
      cantrips:             draft.cantrips,
      alignment:            draft.alignment,
      pronouns:             draft.pronouns,
      title:                draft.title,
      dialogue_style:       draft.dialogueStyle,
      physical_description: draft.physicalDescription,
      backstory:            draft.backstory,
      personality_traits:   draft.personalityTraits,
      flaws:                draft.flaws,
      bonds:                draft.bonds,
      ideals:               draft.ideals,
      keepsake_name:        draft.keepsakeName,
    };
  }

  _escape(s) {
    return String(s).replace(/[&<>"']/g, c =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
    );
  }
}
