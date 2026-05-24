"""
StoryForge placeholder audio generator.
Produces 27 synthesized .wav files in godot/assets/audio/.
All files are real, playable audio — swap in final assets by replacing the files.

Run:  uv run python scripts/generate_audio.py
"""
import wave
import struct
import os
import math
import numpy as np
from pathlib import Path

SR = 44100
OUT = Path(__file__).resolve().parents[1] / "godot" / "assets" / "audio"
OUT.mkdir(parents=True, exist_ok=True)


# ─── Core synthesis primitives ────────────────────────────────────────────────

def t(dur):
    return np.linspace(0, dur, int(SR * dur), endpoint=False)


def sine(freq, dur, phase=0.0):
    return np.sin(2 * np.pi * freq * t(dur) + phase)


def harmony(freqs_amps, dur):
    """Mix multiple (freq, amplitude) sines."""
    out = np.zeros(int(SR * dur))
    for freq, amp in freqs_amps:
        out += amp * sine(freq, dur)
    return out


def noise(dur):
    return np.random.default_rng(42).uniform(-1, 1, int(SR * dur))


def lpf(sig, cutoff):
    """FFT low-pass filter."""
    f = np.fft.rfft(sig)
    freqs = np.fft.rfftfreq(len(sig), 1 / SR)
    f[freqs > cutoff] = 0
    return np.fft.irfft(f, len(sig))


def hpf(sig, cutoff):
    f = np.fft.rfft(sig)
    freqs = np.fft.rfftfreq(len(sig), 1 / SR)
    f[freqs < cutoff] = 0
    return np.fft.irfft(f, len(sig))


def bandpass(sig, lo, hi):
    return hpf(lpf(sig, hi), lo)


def env(sig, a=0.01, d=0.05, s=0.8, r=0.1):
    """ADSR envelope."""
    n = len(sig)
    e = np.ones(n) * s
    ai = int(a * SR);  di = int(d * SR);  ri = int(r * SR)
    if ai > 0:   e[:ai]       = np.linspace(0,   1,   ai)
    if di > 0:   e[ai:ai+di]  = np.linspace(1,   s,   di)
    if ri > 0:   e[max(0, n - ri):] = np.linspace(s, 0, ri)
    return sig * e


def vibrato(sig, rate=5.0, depth=0.003):
    n = len(sig)
    lfo = depth * np.sin(2 * np.pi * rate * np.arange(n) / SR)
    idx = np.arange(n) + (lfo * SR).astype(int)
    idx = np.clip(idx, 0, n - 1)
    return sig[idx]


def tremolo(sig, rate=4.0, depth=0.15):
    lfo = 1.0 - depth * (0.5 + 0.5 * np.sin(2 * np.pi * rate * t(len(sig) / SR)))
    return sig * lfo


def sweep(f1, f2, dur):
    """Linear frequency sweep (glissando)."""
    ph = 2 * np.pi * np.cumsum(np.linspace(f1, f2, int(SR * dur))) / SR
    return np.sin(ph)


def fade(sig, in_dur=0.02, out_dur=0.05):
    sig = sig.copy()
    fi = int(in_dur * SR);  fo = int(out_dur * SR)
    if fi > 0: sig[:fi]    *= np.linspace(0, 1, fi)
    if fo > 0: sig[-fo:]   *= np.linspace(1, 0, fo)
    return sig


def loop_seamless(sig):
    """Cross-fade the tail into the head so the loop clicks disappear."""
    x = int(0.05 * SR)
    sig = sig.copy()
    xf = np.linspace(1, 0, x)
    sig[:x] = sig[:x] * np.linspace(0, 1, x) + sig[-x:] * xf
    return sig[:-x]


def stereo(left, right=None, width=0.3):
    if right is None:
        right = left * (1 - width) + np.roll(left, int(0.001 * SR)) * width
    return np.stack([left, right], axis=1)


def norm(sig, peak=0.72):
    m = np.max(np.abs(sig))
    return sig * (peak / m) if m > 0 else sig


def save(name, samples, peak=0.72):
    if samples.ndim == 1:
        samples = stereo(samples)
    samples = norm(samples, peak)
    samples = np.clip(samples, -1.0, 1.0)
    data = (samples * 32767).astype(np.int16)
    path = str(OUT / name)
    with wave.open(path, 'w') as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(data.tobytes())
    kb = os.path.getsize(path) // 1024
    print(f"  ✓  {name:<36} {kb:>4} KB")


# ─── 1. ambient_keep.wav ─────────────────────────────────────────────────────
def gen_ambient_keep():
    dur = 6.0
    base  = harmony([(55, 0.5), (110, 0.25), (82.4, 0.18), (165, 0.1)], dur)
    base  = vibrato(base, rate=0.4, depth=0.002)
    base  = tremolo(base, rate=0.12, depth=0.08)
    atmos = lpf(noise(dur), 180) * 0.06
    sig   = loop_seamless(base + atmos)
    r     = vibrato(base, rate=0.38, depth=0.0015)
    r     = loop_seamless(tremolo(r + atmos, rate=0.11, depth=0.07))
    # pad lengths
    n = min(len(sig), len(r))
    save("ambient_keep.wav", stereo(sig[:n], r[:n], width=0.25))


# ─── 2. ambient_throne_room.wav ───────────────────────────────────────────────
def gen_ambient_throne_room():
    dur = 6.0
    base = harmony([(73.4, 0.4), (110, 0.3), (146.8, 0.2), (220, 0.1), (293.7, 0.06)], dur)
    base = vibrato(base, rate=0.25, depth=0.0015)
    echo = np.roll(base, int(0.35 * SR)) * 0.25
    sig  = loop_seamless(base + echo)
    r    = loop_seamless(vibrato(base + np.roll(echo, int(0.02 * SR)) * 0.9, rate=0.22, depth=0.001))
    n = min(len(sig), len(r))
    save("ambient_throne_room.wav", stereo(sig[:n], r[:n], width=0.35))


# ─── 3. ambient_store.wav ────────────────────────────────────────────────────
def gen_ambient_store():
    dur = 6.0
    # C major warmth: C3 E3 G3
    base = harmony([(130.8, 0.4), (164.8, 0.28), (196, 0.2), (261.6, 0.12)], dur)
    base = vibrato(base, rate=0.3, depth=0.001)
    hum  = lpf(noise(dur), 250) * 0.05
    sig  = loop_seamless(tremolo(base + hum, rate=0.18, depth=0.06))
    save("ambient_store.wav", sig)


# ─── 4. ambient_inn.wav ──────────────────────────────────────────────────────
def gen_ambient_inn():
    dur = 6.0
    # G major: G3 B3 D4 — social, warm
    base  = harmony([(196, 0.38), (246.9, 0.28), (293.7, 0.22), (392, 0.1)], dur)
    cheer = lpf(noise(dur), 400) * 0.04 + harmony([(523.3, 0.04)], dur)
    base  = vibrato(base + cheer, rate=0.5, depth=0.0012)
    sig   = loop_seamless(tremolo(base, rate=0.22, depth=0.07))
    save("ambient_inn.wav", sig)


# ─── 5. ambient_wilderness.wav ───────────────────────────────────────────────
def gen_ambient_wilderness():
    dur = 6.0
    wind_l = bandpass(noise(dur), 80, 600)
    wind_r = bandpass(noise(dur), 90, 580)
    mod    = 0.7 + 0.3 * np.sin(2 * np.pi * 0.07 * t(dur))
    l      = loop_seamless(wind_l * mod)
    r      = loop_seamless(wind_r * mod * 0.9)
    n = min(len(l), len(r))
    save("ambient_wilderness.wav", stereo(l[:n], r[:n], width=0.5))


# ─── 6. ambient_paradox.wav ──────────────────────────────────────────────────
def gen_ambient_paradox():
    dur = 6.0
    # Tritone dissonance: C3 + F#3 — maximum tension
    base    = harmony([(130.8, 0.35), (185.0, 0.35), (92.5, 0.2)], dur)
    glitch  = bandpass(noise(dur), 300, 3000) * 0.08
    beating = np.sin(2 * np.pi * 7.3 * t(dur)) * 0.12
    sig     = vibrato(base + glitch + beating, rate=1.8, depth=0.006)
    sig     = loop_seamless(sig)
    save("ambient_paradox.wav", sig)


# ─── 7–11. Firey RedVelvet performance tracks ─────────────────────────────────

def _perf_base(fund, harmonics, dur, vib_rate, vib_depth, trem_rate, trem_depth):
    freqs_amps = [(fund * h, a) for h, a in harmonics]
    sig = harmony(freqs_amps, dur)
    sig = vibrato(sig, rate=vib_rate, depth=vib_depth)
    sig = tremolo(sig, rate=trem_rate, depth=trem_depth)
    return fade(sig, in_dur=0.4, out_dur=0.8)


def gen_perf_cold():
    # Sparse, technically correct, going through the motions
    dur = 8.0
    sig = _perf_base(220, [(1, 0.6), (2, 0.12), (3, 0.05)], dur,
                     vib_rate=3.5, vib_depth=0.002, trem_rate=0.8, trem_depth=0.04)
    sig = env(sig, a=0.6, d=0.3, s=0.55, r=1.2)
    save("performance_cold.wav", sig, peak=0.45)


def gen_perf_warm():
    # Locked in — genuinely good
    dur = 8.0
    sig = _perf_base(220, [(1, 0.5), (2, 0.3), (3, 0.18), (4, 0.08), (5, 0.04)], dur,
                     vib_rate=5.2, vib_depth=0.004, trem_rate=1.2, trem_depth=0.06)
    chord = harmony([(261.6, 0.12), (329.6, 0.1), (392, 0.08)], dur)
    sig   = env(sig + chord, a=0.3, d=0.2, s=0.72, r=0.9)
    save("performance_warm.wav", sig, peak=0.58)


def gen_perf_hot():
    # Something real is happening — the room feels it
    dur = 8.0
    sig = _perf_base(220, [(1, 0.45), (2, 0.32), (3, 0.22), (4, 0.15), (5, 0.08), (6, 0.04)], dur,
                     vib_rate=6.5, vib_depth=0.006, trem_rate=2.0, trem_depth=0.09)
    upper = harmony([(440, 0.1), (550, 0.06), (660, 0.04)], dur)
    sweep_in = sweep(200, 220, dur) * 0.08
    sig = env(sig + upper + sweep_in, a=0.2, d=0.15, s=0.82, r=0.6)
    save("performance_hot.wav", sig, peak=0.68)


def gen_perf_blazing():
    # Transcendent — the fire performs with her. The room goes quiet.
    dur = 8.0
    fund = 220
    harmonics = [(h, a) for h, a in zip(
        range(1, 12),
        [0.4, 0.3, 0.22, 0.18, 0.14, 0.10, 0.07, 0.05, 0.04, 0.03, 0.02]
    )]
    sig  = harmony([(fund * h, a) for h, a in harmonics], dur)
    sig  = vibrato(sig, rate=7.0, depth=0.007)
    sig  = tremolo(sig, rate=3.0, depth=0.10)
    glow = harmony([(880, 0.06), (1100, 0.04), (1320, 0.03)], dur)
    sig  = env(sig + glow, a=0.1, d=0.1, s=0.92, r=0.4)
    # Stereo: slight width difference for "fills the room" feel
    l    = sig
    r    = vibrato(sig, rate=6.8, depth=0.006)
    n    = min(len(l), len(r))
    save("performance_blazing.wav", stereo(l[:n], r[:n], width=0.4), peak=0.75)


def gen_perf_mystery():
    # Haunting — let her decide what the room needs
    dur = 8.0
    # Dorian feel: minor with raised 6th
    sig = _perf_base(196, [(1, 0.5), (2, 0.22), (3, 0.15), (4, 0.07)], dur,
                     vib_rate=3.8, vib_depth=0.003, trem_rate=0.6, trem_depth=0.05)
    echo = np.roll(sig, int(0.42 * SR)) * 0.2
    sig  = env(sig + echo, a=0.5, d=0.3, s=0.62, r=1.5)
    save("performance_mystery.wav", sig, peak=0.52)


# ─── 12. sfx_move.wav ────────────────────────────────────────────────────────
def gen_sfx_move():
    dur = 0.25
    thump = lpf(noise(dur), 120) * 1.5
    thump = env(thump, a=0.005, d=0.04, s=0.0, r=0.18)
    cloth = bandpass(noise(dur), 800, 2500) * 0.3
    cloth = env(cloth, a=0.002, d=0.03, s=0.0, r=0.1)
    save("sfx_move.wav", fade(thump + cloth))


# ─── 13. sfx_paradox_glitch.wav ──────────────────────────────────────────────
def gen_sfx_paradox():
    dur = 0.9
    dn  = sweep(1800, 120, dur) * 0.5
    dn  = env(dn, a=0.005, d=0.1, s=0.2, r=0.6)
    burst = bandpass(noise(dur), 400, 8000) * 0.4
    burst = env(burst, a=0.002, d=0.05, s=0.0, r=0.3)
    glitch = harmony([(185, 0.15), (277, 0.12), (370, 0.08)], dur)
    glitch = env(glitch, a=0.01, d=0.15, s=0.0, r=0.5)
    sig = fade(dn + burst + glitch, out_dur=0.2)
    save("sfx_paradox_glitch.wav", sig)


# ─── 14. sfx_magic_burst.wav ─────────────────────────────────────────────────
def gen_sfx_magic_burst():
    dur = 0.6
    sparkle = harmony([(2093, 0.3), (2637, 0.25), (3136, 0.2), (4186, 0.15)], dur)
    sparkle = env(sparkle, a=0.01, d=0.08, s=0.0, r=0.4)
    shimmer = bandpass(noise(dur), 3000, 8000) * 0.2
    shimmer = env(shimmer, a=0.005, d=0.05, s=0.0, r=0.3)
    rise    = sweep(800, 2400, dur) * 0.15
    rise    = env(rise, a=0.005, d=0.06, s=0.0, r=0.35)
    save("sfx_magic_burst.wav", fade(sparkle + shimmer + rise))


# ─── 15. sfx_cactus.wav ──────────────────────────────────────────────────────
def gen_sfx_cactus():
    dur = 0.35
    thunk = lpf(noise(dur), 300) * 0.8
    thunk = env(thunk, a=0.003, d=0.06, s=0.0, r=0.2)
    ring  = sine(420, dur) * 0.25
    ring  = env(ring,  a=0.002, d=0.04, s=0.0, r=0.25)
    save("sfx_cactus.wav", fade(thunk + ring))


# ─── 16. sfx_tip_silver.wav ──────────────────────────────────────────────────
def gen_sfx_tip_silver():
    dur = 0.45
    coin = sine(880, dur) * 0.6 + sine(1046, dur) * 0.3 + sine(1320, dur) * 0.15
    coin = env(coin, a=0.003, d=0.05, s=0.0, r=0.35)
    tap  = lpf(noise(dur), 500) * 0.2
    tap  = env(tap, a=0.002, d=0.02, s=0.0, r=0.05)
    save("sfx_tip_silver.wav", fade(coin + tap))


# ─── 17. sfx_heckle.wav ──────────────────────────────────────────────────────
def gen_sfx_heckle():
    dur = 0.5
    # Harsh descending buzz — she handles it
    buzz = harmony([(185, 0.4), (278, 0.3), (370, 0.2)], dur)
    buzz = vibrato(buzz, rate=12.0, depth=0.02)
    buzz = env(buzz, a=0.005, d=0.1, s=0.3, r=0.3)
    down = sweep(400, 180, dur) * 0.25
    down = env(down, a=0.01, d=0.08, s=0.0, r=0.35)
    save("sfx_heckle.wav", fade(buzz + down))


# ─── 18. sfx_boon_granted.wav ────────────────────────────────────────────────
def gen_sfx_boon():
    dur = 1.2
    # Ascending D major arpeggio then hold
    def note(f, start, length):
        n_start = int(start * SR); n_len = int(length * SR)
        s = sine(f, length)
        s = env(s, a=0.02, d=0.05, s=0.75, r=0.2)
        out = np.zeros(int(SR * dur))
        out[n_start:n_start + n_len] = s[:min(n_len, int(SR * dur) - n_start)]
        return out
    sig  = note(293.7, 0.0,  0.3)   # D4
    sig += note(370.0, 0.15, 0.3)   # F#4
    sig += note(440.0, 0.30, 0.3)   # A4
    sig += note(587.3, 0.45, 0.7)   # D5 hold
    glow = harmony([(293.7, 0.1), (370, 0.08), (440, 0.06)], dur)
    glow = env(glow, a=0.4, d=0.1, s=0.5, r=0.4)
    save("sfx_boon_granted.wav", fade(sig + glow, out_dur=0.15))


# ─── 19. sfx_haylie_entrance.wav ─────────────────────────────────────────────
def gen_sfx_haylie():
    dur = 0.85
    # Energetic upward sweep — she arrives
    up   = sweep(300, 900, dur) * 0.45
    up   = env(up, a=0.01, d=0.05, s=0.3, r=0.4)
    boom = lpf(noise(dur), 200) * 0.3
    boom = env(boom, a=0.005, d=0.08, s=0.0, r=0.15)
    bright = harmony([(880, 0.15), (1100, 0.1)], dur)
    bright = env(bright, a=0.01, d=0.06, s=0.0, r=0.5)
    save("sfx_haylie_entrance.wav", fade(up + boom + bright))


# ─── 20. sfx_ui_confirm.wav ──────────────────────────────────────────────────
def gen_sfx_ui_confirm():
    dur = 0.28
    a = sine(523.3, dur); b = sine(659.3, dur)
    mid = int(0.12 * SR)
    sig = np.zeros(int(SR * dur))
    sig[:mid] = env(a[:mid], a=0.005, d=0.03, s=0.0, r=0.08)
    sig[mid:] = env(b[mid:], a=0.005, d=0.03, s=0.0, r=0.1)
    save("sfx_ui_confirm.wav", fade(sig))


# ─── 21. sfx_ui_back.wav ─────────────────────────────────────────────────────
def gen_sfx_ui_back():
    dur = 0.28
    a = sine(659.3, dur); b = sine(523.3, dur)
    mid = int(0.12 * SR)
    sig = np.zeros(int(SR * dur))
    sig[:mid] = env(a[:mid], a=0.005, d=0.03, s=0.0, r=0.08)
    sig[mid:] = env(b[mid:], a=0.005, d=0.03, s=0.0, r=0.1)
    save("sfx_ui_back.wav", fade(sig))


# ─── 22. sfx_ui_hover.wav ────────────────────────────────────────────────────
def gen_sfx_ui_hover():
    dur = 0.1
    sig = sine(880, dur) * 0.4
    sig = env(sig, a=0.003, d=0.01, s=0.0, r=0.07)
    save("sfx_ui_hover.wav", fade(sig), peak=0.35)


# ─── 23. sfx_character_created.wav ───────────────────────────────────────────
def gen_sfx_char_created():
    dur = 1.6
    def note(f, start, length, amp=0.5):
        n0 = int(start * SR); nl = int(length * SR)
        s = sine(f, length) * amp + sine(f * 2, length) * amp * 0.2
        s = env(s, a=0.015, d=0.04, s=0.7, r=0.25)
        out = np.zeros(int(SR * dur))
        end = min(n0 + nl, int(SR * dur))
        out[n0:end] = s[:end - n0]
        return out
    # C major fanfare: C E G C(oct)
    sig  = note(261.6, 0.0,  0.25)
    sig += note(329.6, 0.18, 0.25)
    sig += note(392.0, 0.36, 0.25)
    sig += note(523.3, 0.52, 0.9)
    # Final chord
    chord = harmony([(261.6, 0.12), (329.6, 0.1), (392, 0.09), (523.3, 0.08)], dur)
    chord = env(chord, a=0.55, d=0.1, s=0.5, r=0.5)
    save("sfx_character_created.wav", fade(sig + chord, out_dur=0.2))


# ─── 24. sfx_era_before.wav ──────────────────────────────────────────────────
def gen_sfx_era_before():
    dur = 0.55
    # Warm, golden — the civilized world
    sig = harmony([(392, 0.45), (494, 0.3), (587.3, 0.2)], dur)  # G B D — G major
    sig = env(sig, a=0.04, d=0.08, s=0.6, r=0.3)
    glow = lpf(noise(dur), 400) * 0.06
    save("sfx_era_before.wav", fade(sig + glow))


# ─── 25. sfx_era_after.wav ───────────────────────────────────────────────────
def gen_sfx_era_after():
    dur = 0.55
    # Darker — the Paradox already found you
    sig = harmony([(196, 0.45), (233.1, 0.3), (293.7, 0.2)], dur)  # G Bb D — G minor
    sig = vibrato(sig, rate=4.0, depth=0.005)
    sig = env(sig, a=0.02, d=0.1, s=0.5, r=0.35)
    edge = bandpass(noise(dur), 400, 2000) * 0.06
    save("sfx_era_after.wav", fade(sig + edge))


# ─── 26. sfx_tyty_bark.wav ───────────────────────────────────────────────────
def gen_sfx_tyty_bark():
    dur = 0.75
    def bark(start, length=0.12):
        n0 = int(start * SR); nl = int(length * SR)
        b  = bandpass(noise(length), 400, 3200) * 1.8
        b  = env(b, a=0.004, d=0.04, s=0.0, r=0.07)
        out = np.zeros(int(SR * dur))
        out[n0:n0 + nl] = b[:nl]
        return out
    # Three sharp barks — the element of surprise is gone
    sig = bark(0.0) + bark(0.22) + bark(0.44)
    save("sfx_tyty_bark.wav", fade(sig), peak=0.85)


# ─── 27. sfx_cyrus_deterrent.wav ─────────────────────────────────────────────
def gen_sfx_cyrus():
    dur = 1.4
    # Deep, slow rising tone — the room de-escalates
    deep = harmony([(36.7, 0.5), (55, 0.35), (73.4, 0.2)], dur)  # D1 A1 D2
    deep = vibrato(deep, rate=0.5, depth=0.001)
    rise = sweep(55, 65, dur) * 0.15
    rumble = lpf(noise(dur), 90) * 0.18
    sig = env(deep + rise + rumble, a=0.6, d=0.2, s=0.65, r=0.5)
    save("sfx_cyrus_deterrent.wav", fade(sig, in_dur=0.6, out_dur=0.3), peak=0.65)


# ─── Runner ───────────────────────────────────────────────────────────────────

GENERATORS = [
    ("Ambient (6)",          [gen_ambient_keep, gen_ambient_throne_room, gen_ambient_store,
                               gen_ambient_inn, gen_ambient_wilderness, gen_ambient_paradox]),
    ("RedVelvet Performance (5)", [gen_perf_cold, gen_perf_warm, gen_perf_hot,
                                    gen_perf_blazing, gen_perf_mystery]),
    ("Game SFX (8)",         [gen_sfx_move, gen_sfx_paradox, gen_sfx_magic_burst,
                               gen_sfx_cactus, gen_sfx_tip_silver, gen_sfx_heckle,
                               gen_sfx_boon, gen_sfx_haylie]),
    ("UI SFX (5)",           [gen_sfx_ui_confirm, gen_sfx_ui_back, gen_sfx_ui_hover,
                               gen_sfx_char_created, gen_sfx_era_before]),
    ("Era + Creatures (3)",  [gen_sfx_era_after, gen_sfx_tyty_bark, gen_sfx_cyrus]),
]

if __name__ == "__main__":
    np.random.seed(42)
    total = 0
    for group, fns in GENERATORS:
        print(f"\n{group}")
        for fn in fns:
            fn()
            total += 1
    print(f"\n✓ {total} audio files written to {OUT}")
