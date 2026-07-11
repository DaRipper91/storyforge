# Audit Scratch — storyforge — started 2026-07-11

## 01 — Recon

**Project:** StoryForge — "hybrid Virtual Tabletop (VTT) + AI Dungeon Master for family D&D 5e" (CLAUDE.md). Also described as "a hybrid Virtual Tabletop (VTT) and AI-driven Dungeon Master built specifically for the *Weaver's Paradox* campaign setting" combining a "cinematic 3D Godot 4 tabletop client" with a headless Python/FastAPI brain (README.md). A third, older doc (docs/README.md) describes it as a Python 3.14 / Termux-Arch project with a static HTML5 Canvas UI as part of a "Project Aether ecosystem." These three descriptions do not agree on what the live client is (see below).
**Stack:** Python 3.12+ / FastAPI / Pydantic v2 / pydantic-settings, `google-genai` SDK (Gemini), vanilla JS + HTML5 Canvas frontend (`frontend/`), a separate Godot 4 (GDScript, ~16k lines) 3D client (`godot/`), `pywebview` + PyQt6 desktop wrapper (`gui.py`), `uv` for dependency/venv management, PyInstaller for Windows packaging.
**Repo state:** has `.git`: yes · remote: `https://github.com/DaRipper91/storyforge` (fetch+push, origin) · appears public: unconfirmed (no `gh` CLI available in sandbox; GitHub API access blocked for this session — "GitHub access is not enabled"). Should be manually confirmed before treating any exposed data/secrets findings as lower-severity.

### Structure notes
- **Two competing frontends, and it matters which is "live."** `src/storyforge/main.py` mounts `/static` directly from the top-level `frontend/` directory (vanilla JS + Canvas, ~5.9k lines JS across `frontend/js/*.js`) — this is the frontend actually wired to the FastAPI backend, and matches CLAUDE.md's architecture description. Separately, `godot/` contains a full ~16k-line GDScript 3D client (scenes, shaders, particle systems, `PythonClient.gd` HTTP/WebSocket bridge) that talks to the same backend over HTTP/WS but is launched independently via the top-level `main.py` orchestrator (`start_backend()` + `start_godot()`, spawns `godot --path godot/`). README.md and ROADMAP.md describe the Godot client as the primary/complete product ("The Godot 4 3D tabletop client is complete... Active work is on audio assets, balance validation, and CI distribution"), while CLAUDE.md — the file governing this audit's own instructions — never mentions Godot at all. Later stages should treat CLAUDE.md's description (FastAPI + vanilla JS + pywebview) as the ground truth for backend behavior, but flag the Godot client as a large, separately-maintained parallel implementation that is easy to lose track of.
- **`standalone/` is a near-complete, older/smaller duplicate of the whole project** (own `src/storyforge`, `frontend/`, `docs/`, `pyproject.toml`, `uv.lock`, build scripts). Its `src/storyforge` (152K) is roughly a third the size of the live `src/storyforge` (504K) and diffs show it's missing newer modules (`auth.py`, `routes_auth.py`, `routes_npc.py`, `routes_enemy.py`, most NPC prompts) — looks like a frozen pre-auth/pre-NPC-encounters snapshot, possibly kept for a different packaging target (it has its own `storyforge.iss` Inno Setup script and `build_windows.py`). Treat as legacy; don't confuse with the live `src/`.
- **`current_backup/` (top level) is a partial backup of `src/storyforge`** (only `config.py`, `main.py`, `core/`, `events/`, `persistence/` — no `api/`, no `ai/`, no `encounters/`). `standalone/current_backup/` duplicates this same partial backup a second time nested inside `standalone/`. Config diff shows the backup predates the hardcoded model-version constants and the JWT/CORS/auth settings in `config.py` — another frozen-in-time artifact, not the live config.
- **Documentation claims contradicted by repo contents, worth flagging for the verification stage:** CLAUDE.md states "note: no tests exist yet — tests/ is empty," but `tests/` actually contains 5 files / ~1,257 lines (`test_character_factory.py`, `test_routes_lobby.py`, `test_routes_npc.py`, `test_validators.py`, `conftest.py`). Either the tests were added after CLAUDE.md was last updated, or CLAUDE.md is stale — worth confirming whether they currently pass.
- **NPC prompt/implementation mismatch:** `src/storyforge/ai/prompts/` has 17 `npc_*.md` files, but `src/storyforge/encounters/` only implements 8 NPC service classes (`shopkeeper_jon`, `samael`, `haylie`, `queen_danna`, `redvelvet`, `kodrik`, `bryne`, `nathis` — matching CLAUDE.md's documented list exactly). The extra prompt files (`npc_binkbink`, `npc_coco`, `npc_cole`, `npc_cyrus`, `npc_danna`(?), `npc_keeva`, `npc_mykael`, `npc_snowie`, `npc_teddy`, `npc_tyty`, `npc_yeldarb`) appear to correspond to the "beasts"/divine characters GEMINI.md explicitly forbids giving mechanics to ("NEVER stat a beast... NEVER roll for a beast"), so this split may be intentional (flavor-only narration via `ai/npc_narrator.py` rather than a stateful encounter class) — worth confirming in stage 2 rather than assuming a bug.
- **Lore/persona-governance files layered on top of the engineering docs:** `GEMINI.md` and `STORYFORGE_CODEX.md` at the repo root are hard-rule canon documents for the AI DM's narrative behavior (e.g. "Kodrik is never King," "never stat a beast," named NPCs' relationships are fixed and unchallengeable). These aren't architecture docs but do constrain what "correct" AI output looks like — relevant if later stages review `ai/prompts/*.md` content for internal consistency.
- **`.jules/` and `.Jules/` (two separately-cased directories)** contain `bolt.md`, `palette.md`, `sentinel.md` — persona/skill files for other automated agents (git log shows commits attributed to "🎨 Palette," "⚡ Bolt," "🛡️ Sentinel" bots). Confirms this repo has been worked on by multiple automated agents already, some fixing security issues (e.g. "Fix XSS vulnerability in frontend escaping," "Add HTTP security headers middleware," "Dynamically set secure flag for session cookies," "add authentication to websocket endpoint") — good context for stage 3/4: check whether these fixes are complete/consistent rather than assuming the area is untouched.
- **Miscellaneous top-level clutter:** a 2.6MB JPEG (`PXL_20260525_011843405.jpg`) sitting at repo root (not obviously referenced by code — likely an accidental commit), `uvicorn_output.log` (a runtime log file checked into the repo root), `extract.py` and `fix_seed.py` (one-off utility scripts, not part of the package), `Profiles/`, `res/`, `plans/active_campaigns/` (campaign-planning docs, not code).
- `.env.example` matches CLAUDE.md's documented env vars (`STORYFORGE_GEMINI_API_KEY`, `STORYFORGE_GOOGLE_CLIENT_ID`, `STORYFORGE_JWT_SECRET`) plus an undocumented `STORYFORGE_GOOGLE_CLIENT_SECRET` and `STORYFORGE_ALLOWED_ORIGINS` (CORS) not mentioned in CLAUDE.md's env list.

### Documented feature/capability list
From README.md / ROADMAP.md / CLAUDE.md, in the authors' own words:
- Hybrid VTT + AI Dungeon Master; "Gemini acts as a narrative renderer (not a state machine)."
- Custom species system: 35 "Feral Successor" races across 5 groups (Cosmic, Primal, Eldritch, Mechanical, Humanoid), 4 Evolutionary States (Behemoth/Phantom/Swarm-Host/Mimic), 4 Predator Roles (Stalker/Vanguard/Catalyst/Siphoner).
- Phase state machine: `TITLE → MENU → MODE_SELECT → LOBBY → CREATION → EXPLORATION`; COMBAT explicitly "deferred to v0.2" and blocked by validators.
- 12-step Character Forge: era, race, evolutionary state, predator role, equipment, background, skills, feats (Apex Predator, Hive Mind, Regenerator, Phase Shift, Pack Tactics, Void Touched, Echo Memory), alignment, lore entry, keepsake, name.
- Local-first, JSON-snapshotted state; atomic save via temp-file + `os.replace`.
- Real-time WebSocket session updates (`/ws/session/{room_id}`) fanning out via an in-process `EventBus`.
- Google OAuth2 identity: two flows — web (Google GIS ID token) and desktop (`InstalledAppFlow`, caches `token.json`).
- 8 implemented NPC encounters with individual state machines: ShopkeeperJon, SamaelTheDemigod, MadameHaylie, QueenDAnna, FireyRedVelvet, GuildmasterKodrik, WardenApprenticeBryne, FrontManNathis — including a documented cross-NPC dependency (Jon's failed "Haylie bailout" escape sets a flag Haylie's encounter checks).
- ROADMAP.md claims (as "COMPLETE"): Godot 4 3D tabletop client, `PythonClient.gd` bridge, dual-process launch orchestration, full 3D dungeon geometry, 3D character minis, gimbal camera, 12-step Character Forge UI in Godot, 35 race portrait cards, dynamic lighting/particles/audio infrastructure, Windows executable via PyInstaller.
- Desktop wrapper: `gui.py` — pywebview + PyQt6 native window, spawns uvicorn in a background thread.
- Core invariant claims (CLAUDE.md, to be checked in stage 2): Python is sole source of truth over Gemini's proposed `StateDiff`s; all mutations serialize through `StateManager`'s `asyncio.Lock` and `_commit()`; prompts live as Markdown files, not f-strings; `core/` has zero I/O and never imports `ai/`, `api/`, or `persistence/`.

### Complexity hotspots
| File | Lines | Note |
|---|---|---|
| `src/storyforge/api/routes_npc.py` | 941 | Largest file in the live backend — all 8 NPC encounter HTTP endpoints in one module; likely repetitive per-NPC branching, prime spot for copy-paste bugs and inconsistent validation across NPCs. |
| `src/storyforge/core/character_factory.py` | 865 | Single source of truth for 35 races × 4 states × 4 roles; CLAUDE.md calls this out explicitly — large combinatorial data tables are error-prone (typos in stat bonuses, missing combos). |
| `src/storyforge/core/state_manager.py` | 657 | The one mutation choke point for `GameState` (asyncio.Lock + `_commit()`); correctness here is load-bearing for every other feature — worth the deepest read in stage 2. |
| `src/storyforge/encounters/shopkeeper_jon.py` | 445 | Most complex single NPC (has the cross-NPC "Haylie bailout" dependency noted in CLAUDE.md) — good candidate for state-machine edge-case bugs. |
| `src/storyforge/core/models.py` | 369 | Root Pydantic schemas (`GameState`, `StateDiff`) — the contract every layer depends on; also worth checking against the validator whitelist in `validators.py` (225 lines) for drift. |

Godot client (`godot/scripts/*.gd`, ~16,113 lines total) and `frontend/js/*.js` (~5,939 lines total) were sized but not individually profiled — out of scope for a Python-backend-focused hotspot list, but note their existence for any stage that decides to review the frontend/client layers directly.

## 02 — Core Verification
(pending)

## 03 — Bug Hunt
(pending)

## 04 — Strengths
(pending)

## 05 — Critic Pass
(pending)
