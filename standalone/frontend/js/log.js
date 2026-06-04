/**
 * Narrative log feed with autoscroll and audio cues.
 */

export class NarrativeLog {
  constructor({ listEl, audio }) {
    this.listEl = listEl;
    this.audio = audio;
    this._seen = new Set();
  }

  setInitial(entries) {
    this.listEl.innerHTML = "";
    this._seen.clear();
    for (const entry of entries) this.append(entry, { silent: true });
    this._scrollToBottom();
  }

  append(entry, { silent = false } = {}) {
    const key = `${entry.revision}::${entry.timestamp}::${entry.kind}`;
    if (this._seen.has(key)) return;
    this._seen.add(key);

    const li = document.createElement("li");
    li.className = `kind-${entry.kind}`;

    if (entry.actor_id) {
      const who = document.createElement("strong");
      who.textContent = `${entry.actor_id}: `;
      who.className = "ink-burgundy";
      li.appendChild(who);
    }

    const text = document.createElement("span");
    text.textContent = entry.text;
    li.appendChild(text);

    this.listEl.appendChild(li);
    this._scrollToBottom();

    if (!silent && entry.kind === "narration") {
      this.audio?.playNarrationChime();
    }
  }

  _scrollToBottom() {
    this.listEl.scrollTop = this.listEl.scrollHeight;
  }
}
