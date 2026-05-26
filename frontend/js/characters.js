/**
 * Renders the party portrait strip, the active-character summary in
 * the bottom bar, and the character card sidebar.
 */

const CHAR_INK_CLASS = {
  cody: "ink-burgundy",
  dee:  "ink-arcane",
  nate: "ink-emerald",
  bray: "ink-midnight",
};

// Portrait background gradients keyed by race group (derived from race name)
const RACE_GROUP_GRADIENTS = {
  cosmic:     "radial-gradient(circle at 40% 35%, #1a0a4a 0%, #0d0020 70%)",
  primal:     "radial-gradient(circle at 40% 35%, #2a4a0a 0%, #0a2000 70%)",
  eldritch:   "radial-gradient(circle at 40% 35%, #4a0a2a 0%, #200010 70%)",
  mechanical: "radial-gradient(circle at 40% 35%, #1a2a3a 0%, #050f18 70%)",
  humanoid:   "radial-gradient(circle at 40% 35%, #2a1a0a 0%, #100800 70%)",
  default:    "radial-gradient(circle at 40% 35%, #4a3070 0%, #1a1428 70%)",
};

const COSMIC_RACES    = new Set(["voidwraith","nullshade","ironlocust","embervein","riftwalker"]);
const PRIMAL_RACES    = new Set(["solarlord","thornmimic","cinderkin","deeptyrant","grimcrow"]);
const ELDRITCH_RACES  = new Set(["bloodweaver","dreamhusk","bonedrifter","mindspider","chaosling"]);
const MECHANICAL_RACES = new Set(["ironveil","forgespawn","cinderplate","hexgear","wirewraith"]);

function _raceGradient(race) {
  if (COSMIC_RACES.has(race))     return RACE_GROUP_GRADIENTS.cosmic;
  if (PRIMAL_RACES.has(race))     return RACE_GROUP_GRADIENTS.primal;
  if (ELDRITCH_RACES.has(race))   return RACE_GROUP_GRADIENTS.eldritch;
  if (MECHANICAL_RACES.has(race)) return RACE_GROUP_GRADIENTS.mechanical;
  return RACE_GROUP_GRADIENTS.humanoid;
}

// Card DOM refs (grabbed lazily on first render)
let _card = null;
function _getCardEls() {
  if (_card) return _card;
  _card = {
    portrait:    document.getElementById("char-card-portrait"),
    initial:     document.getElementById("char-card-initial"),
    name:        document.getElementById("char-card-name"),
    race:        document.getElementById("char-card-race"),
    hpText:      document.getElementById("char-card-hp-text"),
    hpFill:      document.getElementById("char-card-hp-fill"),
    ac:          document.getElementById("char-card-ac"),
    mv:          document.getElementById("char-card-mv"),
    pos:         document.getElementById("char-card-pos"),
    silver:      document.getElementById("char-card-silver"),
    state:       document.getElementById("char-card-state"),
    role:        document.getElementById("char-card-role"),
    conditions:  document.getElementById("char-card-conditions"),
    room:        document.getElementById("char-card-room"),
  };
  return _card;
}

export class CharacterPanel {
  constructor({ portraitRowEl, summaryEls, onActiveChanged }) {
    this.row = portraitRowEl;
    this.summary = summaryEls;
    this.onActiveChanged = onActiveChanged;
    this.state = null;
    this.activeId = null;
  }

  setState(state) {
    this.state = state;
    if (!this.activeId && Object.keys(state.characters).length > 0) {
      this.activeId = Object.keys(state.characters)[0];
    }
    this.render();
  }

  setActive(charId) {
    if (!this.state?.characters[charId]) return;
    if (this.activeId === charId) return;
    this.activeId = charId;
    this.render();
    this.onActiveChanged?.(charId);
  }

  cycleActive(direction = 1) {
    const ids = Object.keys(this.state.characters);
    if (ids.length === 0) return;
    const idx = ids.indexOf(this.activeId);
    const next = (idx + direction + ids.length) % ids.length;
    this.setActive(ids[next]);
  }

  setActiveByControllerIndex(controllerIdx) {
    const ids = Object.keys(this.state.characters);
    if (controllerIdx >= 0 && controllerIdx < ids.length) {
      this.setActive(ids[controllerIdx]);
    }
  }

  render() {
    if (!this.state) return;
    this._renderPortraits();
    this._renderSummary();
    this._renderCard();
  }

  _renderPortraits() {
    this.row.innerHTML = "";
    for (const [id, char] of Object.entries(this.state.characters)) {
      const portrait = document.createElement("button");
      portrait.className = "portrait";
      portrait.setAttribute("aria-label", `Select character ${char.name}`);
      portrait.setAttribute("title", `Select ${char.name}`);
      if (id === this.activeId) portrait.classList.add("active");
      
      const isBloodied = char.hp_current > 0 && char.hp_current <= char.hp_max / 2;
      const isDead = char.hp_current <= 0;
      
      if (isBloodied) portrait.classList.add("bloodied");
      if (isDead) portrait.classList.add("dead");
      
      portrait.dataset.charId = id;

      const initial = document.createElement("span");
      initial.className = CHAR_INK_CLASS[id] ?? "ink-midnight";
      initial.textContent = char.name[0];
      portrait.appendChild(initial);

      // Status overlay
      if (isDead) {
        const skull = document.createElement("span");
        skull.className = "status-icon";
        skull.textContent = "💀";
        portrait.appendChild(skull);
      } else if (isBloodied) {
        const drop = document.createElement("span");
        drop.className = "status-icon";
        drop.textContent = "🩸";
        portrait.appendChild(drop);
      }

      const tag = document.createElement("span");
      tag.className = "player-tag";
      tag.textContent = `${char.player} · ${char.name}`;
      portrait.appendChild(tag);

      portrait.addEventListener("click", () => this.setActive(id));
      this.row.appendChild(portrait);
    }
  }

  _renderSummary() {
    const char = this.state.characters[this.activeId];
    if (!char) return;

    const catalog = window.lobby?.catalog?.races?.[char.race];
    const raceName = (!char.is_transformed && catalog?.before) 
      ? catalog.before 
      : char.race.replace(/_/g, " ");

    this.summary.name.textContent  = char.name;
    this.summary.state.textContent = char.evolution_state;
    this.summary.role.textContent  = char.predator_role;
    this.summary.hp.textContent    = `${char.hp_current}/${char.hp_max}`;
    this.summary.ac.textContent    = String(char.armor_class);
    this.summary.move.textContent  = `${char.movement_remaining}/${char.speed}`;
    this.summary.pos.textContent   = `(${char.position.x}, ${char.position.y})`;
    this.summary.silver.textContent = `${char.silver}s`;

    this.summary.hp.parentElement.classList.toggle(
      "ink-bloodied",
      char.hp_current <= char.hp_max / 2,
    );
  }

  _renderCard() {
    const char = this.state?.characters[this.activeId];
    const els = _getCardEls();
    if (!char || !els.name) return;

    const catalog = window.lobby?.catalog?.races?.[char.race];
    const raceName = (!char.is_transformed && catalog?.before) 
      ? catalog.before 
      : char.race.replace(/_/g, " ");

    const hpPct = char.hp_max > 0 ? char.hp_current / char.hp_max : 0;

    // Portrait gradient and initial
    els.portrait.style.background = _raceGradient(char.race);
    els.initial.textContent = char.name[0]?.toUpperCase() ?? "?";

    // Text fields
    els.name.textContent = char.name;
    els.race.textContent = raceName;
    els.hpText.textContent = `${char.hp_current} / ${char.hp_max}`;
    els.ac.textContent    = char.armor_class;
    els.mv.textContent    = `${char.movement_remaining}/${char.speed}ft`;
    els.pos.textContent   = `${char.position.x},${char.position.y}`;
    els.silver.textContent = `${char.silver} silver`;
    els.state.textContent = char.evolution_state.replace(/_/g, " ");
    els.role.textContent  = char.predator_role;

    // HP bar
    const fillPct = Math.max(0, Math.min(1, hpPct)) * 100;
    els.hpFill.style.width = `${fillPct}%`;
    els.hpFill.classList.remove("bloodied", "critical");
    if (hpPct <= 0.25) els.hpFill.classList.add("critical");
    else if (hpPct <= 0.5) els.hpFill.classList.add("bloodied");

    // Conditions
    els.conditions.innerHTML = "";
    for (const cond of (char.conditions ?? [])) {
      const pip = document.createElement("span");
      pip.className = "char-card-condition-pip";
      pip.textContent = cond;
      els.conditions.appendChild(pip);
    }

    // Room
    if (this.state.rooms && this.state.current_room_id) {
      const room = this.state.rooms[this.state.current_room_id];
      els.room.textContent = room?.name ?? "";
    }
  }

  get activeCharacter() {
    return this.state?.characters[this.activeId] ?? null;
  }
}
