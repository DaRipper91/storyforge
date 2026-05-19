/**
 * Procedural audio engine.
 */

export class AudioEngine {
  constructor({ enabled = true } = {}) {
    this.enabled = enabled;
    this.ctx = null;
    this.masterGain = null;
    
    // BGM management
    this.bgm = {
      current: null,
      tracks: {
        lobby:       "https://opengameart.org/sites/default/files/mystical%20world.ogg",
        exploration: "https://opengameart.org/sites/default/files/rpg_ambience_-_exploration.ogg",
        fight:       "https://opengameart.org/sites/default/files/rbl.mp3",
        death:       "https://opengameart.org/sites/default/files/The%20World%20Stood%20Still.mp3",
        heartbeat:   "https://freesound.org/data/previews/48/48492_321967-lq.mp3" // Placeholder heartbeat
      },
      elements: {} // id -> HTMLAudioElement
    };

    this._initOnGesture = this._initOnGesture.bind(this);
    window.addEventListener("pointerdown", this._initOnGesture, { once: true });
    window.addEventListener("keydown", this._initOnGesture, { once: true });
    window.addEventListener("gamepadconnected", this._initOnGesture, { once: true });
  }

  _initOnGesture() {
    if (this.ctx) return;
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return;
    this.ctx = new Ctx({ latencyHint: "interactive" });
    this.masterGain = this.ctx.createGain();
    this.masterGain.gain.value = 0.55;
    this.masterGain.connect(this.ctx.destination);
    
    console.log("[audio] Engine initialized on gesture");
    // Pre-warm BGM elements (don't play yet)
    for (const [id, url] of Object.entries(this.bgm.tracks)) {
      const el = new Audio(url);
      el.loop = id !== 'death'; // Loop everything except death jingle
      el.crossOrigin = "anonymous";
      this.bgm.elements[id] = el;
    }
  }

  setVolume(v) {
    if (this.masterGain) this.masterGain.gain.value = Math.max(0, Math.min(1, v));
  }

  // ─────────────────────── BGM Control ───────────────────────

  playBGM(id, { fadeTime = 2.0 } = {}) {
    if (!this.bgm.elements[id] || !this.enabled) return;
    if (this.bgm.current === id) return;

    console.log(`[audio] Switching BGM to: ${id}`);
    const next = this.bgm.elements[id];
    const prev = this.bgm.current ? this.bgm.elements[this.bgm.current] : null;

    // Fade out previous
    if (prev) {
      this._fadeAudio(prev, 0, fadeTime, () => {
        prev.pause();
        prev.currentTime = 0;
      });
    }

    // Fade in next
    next.volume = 0;
    next.play().catch(e => console.warn("[audio] play blocked:", e));
    this._fadeAudio(next, 0.4, fadeTime);
    this.bgm.current = id;
  }

  stopBGM(fadeTime = 1.5) {
    if (!this.bgm.current) return;
    const el = this.bgm.elements[this.bgm.current];
    this._fadeAudio(el, 0, fadeTime, () => {
      el.pause();
      el.currentTime = 0;
    });
    this.bgm.current = null;
  }

  _fadeAudio(el, targetVolume, time, onComplete) {
    const steps = 20;
    const interval = (time * 1000) / steps;
    const startVolume = el.volume;
    const delta = (targetVolume - startVolume) / steps;
    let currentStep = 0;

    const timer = setInterval(() => {
      currentStep++;
      el.volume = Math.max(0, Math.min(1, startVolume + delta * currentStep));
      if (currentStep >= steps) {
        clearInterval(timer);
        el.volume = targetVolume;
        onComplete?.();
      }
    }, interval);
  }

  // ─────────────────────── SFX ───────────────────────

  playCursor() { this._tone({ freq: 880, dur: 0.04, type: "triangle", gain: 0.18 }); }

  playConfirm() {
    this._chord([523, 659, 784], { dur: 0.22, type: "sine", gain: 0.30 });
  }

  playDeny() {
    this._tone({ freq: 220, dur: 0.18, type: "sawtooth", gain: 0.28, sweepTo: 160 });
  }

  playPageTurn() {
    if (!this.ctx) return;
    const noise = this._noiseBuffer(0.35);
    const src = this.ctx.createBufferSource();
    src.buffer = noise;
    const filter = this.ctx.createBiquadFilter();
    filter.type = "bandpass";
    filter.frequency.value = 1800;
    filter.Q.value = 3;
    const gain = this.ctx.createGain();
    gain.gain.setValueAtTime(0.0, this.ctx.currentTime);
    gain.gain.linearRampToValueAtTime(0.30, this.ctx.currentTime + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.34);
    src.connect(filter).connect(gain).connect(this.masterGain);
    src.start();
    src.stop(this.ctx.currentTime + 0.36);
  }

  playNarrationChime() {
    this._chord([392, 587, 880], { dur: 0.55, type: "sine", gain: 0.22, attack: 0.04 });
  }

  _tone({ freq, dur, type = "sine", gain = 0.3, sweepTo = null }) {
    if (!this.ctx || !this.enabled) return;
    const now = this.ctx.currentTime;
    const osc = this.ctx.createOscillator();
    const g = this.ctx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, now);
    if (sweepTo != null) {
      osc.frequency.exponentialRampToValueAtTime(sweepTo, now + dur);
    }
    g.gain.setValueAtTime(0.0001, now);
    g.gain.exponentialRampToValueAtTime(gain, now + 0.005);
    g.gain.exponentialRampToValueAtTime(0.0001, now + dur);
    osc.connect(g).connect(this.masterGain);
    osc.start(now);
    osc.stop(now + dur + 0.02);
  }

  _chord(freqs, opts) {
    for (const f of freqs) this._tone({ freq: f, ...opts });
  }

  _noiseBuffer(seconds) {
    const sr = this.ctx.sampleRate;
    const buf = this.ctx.createBuffer(1, sr * seconds, sr);
    const ch = buf.getChannelData(0);
    for (let i = 0; i < ch.length; i++) ch[i] = (Math.random() * 2 - 1) * 0.5;
    return buf;
  }
}
