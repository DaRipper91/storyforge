/**
 * Manages the "Stolen Goods" (Inventory) UI.
 */

export class InventoryPanel {
  constructor({ containerEl, listEl, audio }) {
    this.container = containerEl;
    this.list = listEl;
    this.audio = audio;
    this.activeCharacter = null;
  }

  toggle() {
    const isHidden = this.container.classList.toggle("hidden");
    if (!isHidden) {
      this.audio?.playPageTurn();
      this.render();
    }
  }

  setCharacter(char) {
    this.activeCharacter = char;
    if (!this.container.classList.contains("hidden")) {
      this.render();
    }
  }

  render() {
    if (!this.activeCharacter) return;
    this.list.innerHTML = "";
    
    if (this.activeCharacter.inventory.length === 0) {
      const empty = document.createElement("li");
      empty.className = "inventory-empty";
      empty.textContent = "Your pockets are as empty as your promises.";
      this.list.appendChild(empty);
      return;
    }

    for (const item of this.activeCharacter.inventory) {
      const li = document.createElement("li");
      li.className = "inventory-item";
      if (item.equipped) li.classList.add("equipped");

      li.innerHTML = `
        <div class="item-header">
          <span class="item-name">${this._escape(item.name)}</span>
          <span class="item-qty">x${item.quantity}</span>
        </div>
        <div class="item-meta">
          <span class="item-value">${item.value > 0 ? `${item.value}s` : "Worthless"}</span>
          ${item.equipped ? '<span class="item-tag">Equipped</span>' : ""}
        </div>
        ${item.notes ? `<div class="item-notes">${this._escape(item.notes)}</div>` : ""}
      `;
      this.list.appendChild(li);
    }
  }

  _escape(s) {
    return String(s).replace(/[&<>"']/g, c =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[c])
    );
  }
}
