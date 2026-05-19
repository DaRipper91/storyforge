/**
 * Renders the party portrait strip and the active-character summary in
 * the bottom bar.
 */

const CHAR_INK_CLASS = {
  cody: "ink-burgundy",
  dee:  "ink-arcane",
  nate: "ink-emerald",
  bray: "ink-midnight",
};

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
  }

  _renderPortraits() {
    this.row.innerHTML = "";
    for (const [id, char] of Object.entries(this.state.characters)) {
      const portrait = document.createElement("button");
      portrait.className = "portrait";
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
    this.summary.name.textContent  = char.name;
    this.summary.klass.textContent = char.char_class;
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

  get activeCharacter() {
    return this.state?.characters[this.activeId] ?? null;
  }
}
