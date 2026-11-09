"""Generate divider.svg, section-*.svg, pipeline.svg and architecture.svg."""
from __future__ import annotations

import math
import random

from common import ASSETS, esc, svg_open, text, write

MARKER = ('<defs>\n<marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
          'orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" class="f-accent"/></marker>\n'
          '<marker id="ahr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
          'orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" class="f-highlight"/></marker>\n'
          '<pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
          '<line x1="0" y1="0" x2="0" y2="6" class="s-border" stroke-width="1" opacity=".55"/></pattern>\n'
          '<pattern id="dots" width="8" height="8" patternUnits="userSpaceOnUse">'
          '<circle cx="2" cy="2" r=".9" class="f-muted" opacity=".3"/></pattern>\n</defs>\n')


def bg(w, h, inset=4):
    return (f'<rect width="{w}" height="{h}" class="f-bg"/>\n'
            f'<rect x="{inset}" y="{inset}" width="{w-2*inset}" height="{h-2*inset}" class="nofill s-border" stroke-width="1.2"/>\n')


def box(x, y, w, h, head, lines=(), dashed=False, gate=False, size=10.5):
    st = "s-highlight" if gate else "s-border"
    dash = ' stroke-dasharray="5 4"' if dashed else ""
    o = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" class="f-surface {st}" stroke-width="{2 if gate else 1.2}"{dash}/>']
    o.append(text(x + 12, y + 22, head, 12, "f-highlight", extra='font-weight="bold"'))
    for i, ln in enumerate(lines):
        cls = "f-text" if not ln.startswith("~") else "f-muted"
        o.append(text(x + 12, y + 41 + i * 15, ln.lstrip("~"), size, cls))
    return "".join(o) + "\n"


def arrow(d, hi=False, dashed=False):
    cls = "s-highlight" if hi else "s-accent"
    dash = ' stroke-dasharray="5 4"' if dashed else ""
    return (f'<path d="{d}" class="nofill {cls}" stroke-width="1.6"{dash} '
            f'marker-end="url(#{"ahr" if hi else "ah"})"/>\n')


# ───────────────────────── divider + sections ─────────────────────────

def divider():
    W, H = 960, 28
    s = svg_open(W, H, "Divider", "Survey-line divider with a centre mark.")
    c = W / 2
    s += f'<line x1="30" y1="14" x2="{c-30}" y2="14" class="s-border" stroke-width="1"/>\n'
    s += f'<line x1="{c+30}" y1="14" x2="{W-30}" y2="14" class="s-border" stroke-width="1"/>\n'
    for i in range(1, 9):
        for sign in (-1, 1):
            x = c + sign * (30 + i * 52)
            if 30 < x < W - 30:
                h = 6 if i % 2 == 0 else 3.5
                s += f'<line x1="{x:g}" y1="{14-h}" x2="{x:g}" y2="{14+h}" class="s-border" stroke-width="1"/>\n'
    # centre mark: eight-point star inside a ring (a survey benchmark, not a compass copy)
    pts = []
    for i in range(16):
        a = math.radians(i * 22.5)
        r = 11 if i % 2 == 0 else 4.2
        pts.append(f"{c + r*math.sin(a):.1f},{14 - r*math.cos(a):.1f}")
    s += f'<circle cx="{c}" cy="14" r="13" class="nofill s-border" stroke-width=".8"/>\n'
    s += f'<polygon points="{" ".join(pts)}" class="f-accent"/>\n'
    s += f'<circle cx="{c}" cy="14" r="2" class="f-bg"/>\n'
    return s + "</svg>\n"


def section(num, title, coord):
    W, H = 960, 56
    s = svg_open(W, H, f"{num}: {title}", f"Section header: {num}, {title}.")
    s += bg(W, H, 2)
    s += f'<rect x="2" y="2" width="150" height="{H-4}" class="f-surface s-border" stroke-width="1.2"/>\n'
    s += text(77 + 2, 35, num, 19, "f-highlight", "disp", "middle", 'font-weight="bold" letter-spacing="3"')
    s += text(178, 36, title, 24, "f-text", "disp", extra='style="font-variant:small-caps" letter-spacing="3"')
    s += text(W - 16, 33, coord, 10, "f-muted", anchor="end", extra='letter-spacing="1.5"')
    for x in range(160, W - 8, 24):
        s += f'<line x1="{x}" y1="{H-2}" x2="{x}" y2="{H-6}" class="s-border" stroke-width=".8"/>\n'
    return s + "</svg>\n"


SECTIONS = [
    ("quickstart", "PLATE II", "Quickstart", "SURVEY 01 / FIELD KIT"),
    ("species", "PLATE III", "The Species", "SURVEY 02 / 35 CARDS"),
    ("turn", "PLATE IV", "How a Turn Works", "SURVEY 03 / ACTION PATH"),
    ("engine", "PLATE V", "The Engine", "SURVEY 04 / TERRITORIES"),
    ("status", "PLATE VI", "Status and Roadmap", "SURVEY 05 / OPEN GROUND"),
]


# ───────────────────────── pipeline ─────────────────────────

def pipeline():
    W, H = 1280, 560
    s = svg_open(W, H, "StoryForge action pipeline",
                 "How a player action becomes validated state: grid actions pass rules.check_grid_action; "
                 "freeform actions pass a Gemini proposal then validators.sanitize; both commit through "
                 "StateManager._commit and fan out over the WebSocket.", motion=True)
    s += MARKER + bg(W, H)
    s += text(40, 40, "A  GRID ACTION  (deterministic, Python decides)", 11, "f-accent", extra='letter-spacing="2"')
    s += box(40, 52, 210, 82, "Player picks a cell", ["POST /api/action/grid"])
    s += box(290, 52, 240, 82, "rules.check_grid_action()", ["legal move / interact?", "~illegal: HTTP 400 + reason"])
    s += box(570, 52, 250, 82, "apply_grid_action()", ["move / interact / room", "transition via StateManager"])
    s += arrow("M250 93 H286") + arrow("M530 93 H566")
    s += box(570, 160, 250, 62, "narrator (Gemini)", ["flavor text only, no StateDiff"], dashed=True)
    s += arrow("M695 134 V156", dashed=True)
    s += text(40, 262, "B  FREEFORM ACTION  (Gemini proposes, Python disposes)", 11, "f-accent", extra='letter-spacing="2"')
    s += box(40, 274, 210, 82, "Player types text", ["POST /api/action/freeform"])
    s += box(290, 274, 240, 82, "interpret_freeform()", ["Gemini returns narrative", "+ a proposed StateDiff"])
    s += box(570, 274, 250, 82, "validators.sanitize()", ["reject, don't repair", "returns (safe_diff, rejections)"], gate=True)
    s += box(880, 274, 120, 82, "apply_diff()", ["safe_diff only"])
    s += arrow("M250 315 H286") + arrow("M530 315 H566")
    s += arrow("M820 315 H876", hi=True)
    s += text(848, 306, "accept", 10, "f-highlight", anchor="middle")
    s += arrow("M695 356 V392", hi=True)
    s += text(703, 378, "reject", 10, "f-highlight")
    # rejection band
    s += (f'<rect x="40" y="394" width="960" height="140" rx="4" class="f-surface s-border" stroke-width="1.2" '
          f'stroke-dasharray="5 4"/>\n')
    s += text(54, 416, "REJECTED, NOT REPAIRED. Each rejection is logged as [ref] <reason>. Real strings from validators.py:", 11, "f-highlight", extra='font-weight="bold"')
    quotes = [
        "AI tried to modify forbidden field 'hp_max' on <char_id>",
        "refused inventory add: quantity 999 > 10 (Healing Potion)",
        "phase change to combat is deferred to v0.2",
        "AI diffs are not accepted during lobby phase",
    ]
    for i, q in enumerate(quotes):
        s += text(66, 442 + i * 20, '"' + q + '"', 11, "f-text")
    s += text(54, 524, "values in <> and the potion name are placeholders; the sentence templates are verbatim.", 9.5, "f-muted")
    # commit column
    s += box(1040, 52, 210, 304, "StateManager._commit()", [
        "1. revision += 1", "2. snapshot.save()", "~   temp file + os.replace", "3. event_bus.publish()", "~   one queue per subscriber",
        "", "~All mutations pass here,", "~serialized by asyncio.Lock."], size=10.5)
    s += arrow("M820 93 H1036", hi=False)
    s += arrow("M1000 315 H1036")
    s += arrow("M1145 356 V390")
    s += box(1040, 394, 210, 56, "WebSocket fan-out", ["/ws/session/{room_id}"])
    s += arrow("M1145 450 V478")
    s += box(1040, 482, 210, 56, "Godot client", ["PythonClient.gd signals"], size=10.5)
    return s + "</svg>\n"


# ───────────────────────── architecture ─────────────────────────

def ripples(rects, seed=3, n=26):
    rnd = random.Random(seed)
    o = ['<g class="ink">\n']
    c = 0
    while c < n:
        x, y = rnd.uniform(20, 1260), rnd.uniform(20, 500)
        if any(a <= x <= b and cc <= y <= d for a, cc, b, d in rects):
            continue
        o.append(f'<path d="M{x:.0f} {y:.0f} q6 -5 12 0 t12 0" class="nofill s-muted" stroke-width=".9" opacity=".5"/>')
        c += 1
    return "".join(o) + "\n</g>\n"


def architecture():
    W, H = 1280, 520
    s = svg_open(W, H, "StoryForge architecture plate",
                 "Territories: Godot client, FastAPI server (api, ai, encounters, pure-logic core behind a "
                 "validator gate), remote Gemini, and on-disk snapshots.", motion=True)
    s += MARKER + bg(W, H)
    taken = [(20, 60, 300, 450), (370, 40, 960, 510), (1010, 60, 1260, 400)]
    s += ripples(taken)
    # client
    s += '<polygon points="34,100 274,72 292,210 274,392 70,420 30,268" class="f-surface s-border" fill-opacity=".55" stroke-width="1.6" stroke-linejoin="round"/>\n'
    s += text(54, 112, "GODOT 4.6 CLIENT", 13, "f-highlight", "disp", extra='font-weight="bold" letter-spacing="2"')
    s += text(54, 130, "godot/  (GDScript)", 10, "f-muted")
    for i, ln in enumerate(["Tabletop.gd: board + camera", "PythonClient.gd: HTTP + WS", "UI, NPC dialogs, audio", "", "Renders state. Owns no rules."]):
        s += text(54, 168 + i * 20, ln, 10.5, "f-text" if i < 3 else "f-muted")
    s += text(54, 300, "--backend=local swaps the", 10, "f-accent")
    s += text(54, 316, "server for an in-process", 10, "f-accent")
    s += text(54, 332, "GDScript LocalBackend.", 10, "f-accent")
    s += text(54, 348, "Default: remote (this plate).", 10, "f-muted")
    # server
    s += '<polygon points="384,70 944,56 966,290 936,430 396,444 372,250" class="f-surface s-border" fill-opacity=".45" stroke-width="1.6" stroke-linejoin="round"/>\n'
    s += text(404, 90, "FASTAPI SERVER", 13, "f-highlight", "disp", extra='font-weight="bold" letter-spacing="2"')
    s += text(404, 106, "src/storyforge/  (Python 3.12)", 10, "f-muted")
    s += '<rect x="404" y="120" width="526" height="36" rx="3" class="f-surface s-accent" stroke-width="1"/>\n'
    s += text(417, 143, "api/  action - lobby - npc - state - auth - ws_session", 10.5, "f-text")
    # core keep
    s += '<rect x="404" y="190" width="236" height="190" class="f-surface s-border" stroke-width="3"/>\n'
    s += '<rect x="404" y="190" width="236" height="190" fill="url(#hatch)" opacity=".6"/>\n'
    s += '<rect x="418" y="204" width="208" height="162" class="f-bg s-border" stroke-width="1"/>\n'
    s += text(428, 226, "core/  THE KEEP", 12, "f-highlight", "disp", extra='font-weight="bold" letter-spacing="1.5"')
    for i, ln in enumerate(["pure logic, no I/O", "models  rules  grid", "character_factory", "state_manager (Lock)", "-> _commit()", "source of truth"]):
        s += text(428, 248 + i * 18, ln, 10.5, "f-text" if i not in (0, 5) else "f-muted")
    # validator gate
    s += '<rect x="656" y="250" width="40" height="64" rx="3" class="f-surface s-highlight" stroke-width="2.4"/>\n'
    s += '<path d="M660 250 v-8 h8 v8 M672 250 v-8 h8 v8 M684 250 v-8 h8 v8" class="nofill s-highlight" stroke-width="1.6"/>\n'
    s += text(676, 330, "validators.", 9.5, "f-highlight", anchor="middle", extra='font-weight="bold"')
    s += text(676, 342, "sanitize()", 9.5, "f-highlight", anchor="middle", extra='font-weight="bold"')
    s += text(676, 358, "reject,", 9, "f-muted", anchor="middle")
    s += text(676, 369, "don't repair", 9, "f-muted", anchor="middle")
    # ai + encounters
    s += '<rect x="716" y="190" width="214" height="100" rx="3" class="f-surface s-accent" stroke-width="1"/>\n'
    s += text(728, 212, "ai/  narrator + proposer", 11, "f-highlight", extra='font-weight="bold"')
    for i, ln in enumerate(["client.py  interpreter.py", "narrator.py", "prompts/*.md (Markdown)"]):
        s += text(728, 234 + i * 17, ln, 10.5, "f-text")
    s += '<rect x="716" y="308" width="214" height="72" rx="3" class="f-surface s-accent" stroke-width="1"/>\n'
    s += text(728, 330, "encounters/  NPC services", 11, "f-highlight", extra='font-weight="bold"')
    s += text(728, 350, "pure logic, session state,", 10.5, "f-text")
    s += text(728, 366, "return StateDiff to caller", 10.5, "f-text")
    # gemini
    s += '<polygon points="1034,90 1246,76 1256,250 1236,390 1040,404 1020,240" class="f-surface s-border" fill-opacity=".55" stroke-width="1.6" stroke-linejoin="round" stroke-dasharray="6 4"/>\n'
    s += text(1050, 112, "GEMINI (remote)", 13, "f-highlight", "disp", extra='font-weight="bold" letter-spacing="2"')
    for i, ln in enumerate(["narrative renderer", "", "gemini-3.5-flash", "gemini-3.1-pro-preview", "", "needs STORYFORGE_", "GEMINI_API_KEY"]):
        s += text(1050, 150 + i * 18, ln, 10.5, "f-text" if i in (2, 3) else "f-muted")
    # disk
    s += '<rect x="404" y="446" width="526" height="58" rx="3" class="f-surface s-border" stroke-width="1.2"/>\n'
    s += '<rect x="404" y="446" width="526" height="58" rx="3" fill="url(#dots)"/>\n'
    s += text(418, 468, "DISK  data/campaigns/<id>/state.json", 11, "f-highlight", extra='font-weight="bold"')
    s += text(418, 488, "atomic JSON snapshot, local-first.  Seed: data/seeds/default_campaign.json", 10, "f-text")
    # roads
    s += arrow("M290 128 H400") + text(345, 120, "HTTP /api/*", 10, "f-accent", anchor="middle")
    s += arrow("M400 168 H290", dashed=True) + text(345, 183, "WS", 9.5, "f-accent", anchor="middle") + text(345, 194, "/ws/session/{room_id}", 8.5, "f-accent", anchor="middle")
    s += arrow("M520 156 V188")
    s += arrow("M820 156 V188")
    s += arrow("M716 282 H700", hi=True)
    s += arrow("M652 282 H642", hi=True)
    s += arrow("M930 240 H1030", dashed=True) + text(980, 232, "google-genai", 9.5, "f-accent", anchor="middle")
    s += arrow("M520 380 V442") + text(530, 416, "snapshot.save()", 10, "f-accent")
    return s + "</svg>\n"


if __name__ == "__main__":
    write(ASSETS / "divider.svg", divider())
    for slug, num, title, coord in SECTIONS:
        write(ASSETS / f"section-{slug}.svg", section(num, title, coord))
    write(ASSETS / "pipeline.svg", pipeline())
    write(ASSETS / "architecture.svg", architecture())
