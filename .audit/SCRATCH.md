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

### Findings

1. **CLAUDE.md's "tests/ is empty" claim is stale — all 88 tests pass.** Ran `uv run pytest -q`
   after `uv sync --group dev`: `88 passed in 3.53s`, covering `test_character_factory.py`,
   `test_routes_lobby.py`, `test_routes_npc.py`, `test_validators.py`. The documentation is simply
   out of date, not a red flag about test health. Severity: low (docs drift). [VERIFIED]

2. **`core/` violates its own documented "no I/O, never imports ai/api/persistence" invariant** —
   `src/storyforge/core/state_manager.py:31` does `from storyforge.persistence import snapshot`
   and calls `snapshot.save(self._campaign_dir, self._state)` directly at
   `state_manager.py:233` and `:652` (disk I/O inside `core/`, the exact thing CLAUDE.md says
   never happens). It also imports `storyforge.encounters.enemies` (`state_manager.py:29`) and
   `storyforge.events.bus` (`:30`) — both outside `core/`. Verified by
   `grep -n "^from storyforge\.\|^import storyforge\." src/storyforge/core/*.py`: every other file
   in `core/` (`grid.py`, `rules.py`, `validators.py`, `character_factory.py`) only imports from
   `storyforge.core.*`; `state_manager.py` is the sole offender. This is a real, checkable
   contradiction between CLAUDE.md's architecture doc and the actual dependency graph — not
   catastrophic (it's the designated single mutation/persistence choke point, so the coupling is
   arguably intentional), but it directly falsifies invariant #4 as literally written. Severity:
   medium (docs/architecture-invariant violation, not a functional bug). [VERIFIED]

3. **`StateDiff` validator whitelist in `core/validators.py` fully matches CLAUDE.md's documented
   invariants, with no drift against `core/models.py`.** Read `validators.py` in full and
   cross-checked against `StateDiff` in `models.py:354-363` (5 fields:
   `character_updates`, `cell_updates`, `add_inventory`, `remove_inventory`, `phase_change` — all
   5 have a corresponding `_filter_*` function, no missing/extra fields).
   - LOBBY/CREATION phase → returns empty diff + rejection message (`validators.py:44-48`).
   - `character_updates` allowed fields = `hp_current`, `conditions`, `movement_remaining`,
     `position` — but `position` is explicitly rejected inside its own branch
     (`validators.py:125-131`, "must go through cell_updates"), matching CLAUDE.md exactly.
   - `add_inventory` quantity cap of 10 enforced per-item (`validators.py:182-186`).
   - `phase_change == COMBAT` rejected (`validators.py:222-224`), matching "COMBAT deferred to v0.2."
   - Confirmed `apply_diff()` in `state_manager.py:163-169` is *not* self-sanitizing — its own
     docstring warns "assumes diff has already been through validators.sanitize()... Calling this
     with a raw Gemini response bypasses every safety check." Traced all 3 call sites of
     `apply_diff()`: `routes_action.py:87` (calls `validators.sanitize()` first at line 84 — the
     only call site fed by real Gemini/AI output), and two call sites in `routes_npc.py:181,256`
     that pass diffs built deterministically by Python NPC service classes
     (`jon.buy_item()`, `jon.roll_escape_check()`) — never raw Gemini output, so skipping
     `sanitize()` there is consistent with the documented model rather than a bypass. No call site
     was found passing an unsanitized AI diff into `apply_diff`. Severity: none (invariant holds).
     [VERIFIED]

4. **`get_current_user` auth dependency (`api/deps.py:12`) is dead code — never wired into any
   route.** `grep -rn "get_current_user" src/` returns exactly one hit: its own definition. None
   of `routes_action.py` (`/api/action/grid`, `/freeform`, `/interact_entity`, `/travel`),
   `routes_lobby.py` (`/api/lobby/*`, `/api/character/create`), or `routes_npc.py` (all 26
   endpoints) depend on it, and `main.py` has no global auth middleware — only a security-headers
   middleware and CORS. The only place that actually enforces the session JWT is
   `ws_session.py` (manual `jwt.decode` before `websocket.accept()`) and `routes_lobby.py:147-158`
   (`join_lobby`, which does its own inline cookie parse with a fallback to a client-supplied
   `controller_id` for guest/local-controller play — by design, not broken, confirmed by
   `tests/test_routes_lobby.py::test_join_requires_controller_id` which only expects 401 when
   *both* the cookie and `controller_id` are absent). Net effect: every actual gameplay
   mutation endpoint (grid/freeform actions, all NPC encounters, character creation) is reachable
   with **no authentication check at all** — the Google OAuth / JWT session system exists and is
   internally correct, but isn't applied to REST endpoints, only informally consulted by lobby
   join and enforced only on the websocket. For a local family app on 127.0.0.1 this may be an
   accepted risk, but it contradicts CLAUDE.md's description of `get_current_user` as the thing
   that "raises 401 if missing or invalid" (true of the function in isolation, false of its
   effect on the API surface — it's never invoked at runtime). Severity: high (auth exists but
   isn't enforced anywhere it would matter). [VERIFIED]

5. **NPC prompt/encounter split (17 prompts vs 8 encounter classes) is legitimately intentional
   for 7 of the 9 "extra" prompts, but 2 (`npc_mykael.md`, `npc_yeldarb.md`) are dead/orphaned
   files, not wired to anything.**
   - `npc_keeva`, `npc_teddy`, `npc_cyrus`, `npc_binkbink`, `npc_cole`, `npc_coco`, `npc_tyty`,
     `npc_snowie` are all reachable via a single unified flavor-only endpoint,
     `POST /api/pet/{pet_id}/interact` (`routes_npc.py:929-939`), which maps each to
     `narrate_npc(name, situation)` with a hardcoded pool fallback and **no state/StateDiff** —
     matches GEMINI.md's "never stat a beast" rule exactly and is a real, working feature, not a
     bug. Verified by reading `routes_npc.py:841-939` in full and confirming `_PET_PROMPT`,
     `_PET_SITUATION`, `_PET_FALLBACK` dicts cover all 8 names.
   - `npc_mykael.md` and `npc_yeldarb.md`, by contrast, describe named human(-ish) characters with
     actual mechanics ("The 4-Second Peak" strength surge for Mykael; "appears without warning"
     for Yeldarb) per `STORYFORGE_CODEX.md:87-95,128-136` — these are not beasts, so the
     "never stat a beast" exemption doesn't apply. Verified there is **no call site anywhere**
     invoking `narrate_npc("mykael", ...)` or `narrate_npc("yeldarb", ...)`
     (`grep -rn "mykael|yeldarb" src/` only matches the prompt files themselves, plus a passing
     mention in `npc_kodrik.md` flavor text and two bullet points in `ai/prompts/system_dm.md:48,55`
     — the latter is the base system prompt loaded by both `interpreter.py:77` and
     `narrator.py:16` for *all* general narration, so the *characters* are reachable ambiently
     through the main DM's system prompt, but the dedicated `npc_mykael.md`/`npc_yeldarb.md` files
     with their detailed mechanics are never loaded by `load_prompt()` anywhere — orphaned content,
     not a functioning encounter). Severity: low (unused/dead prompt content, not a broken
     player-facing feature — the characters still function via ambient DM narration).
     [VERIFIED]

6. **Security-remediation commits from other bots are all still intact and consistent in current
   code** — checked each of the 5 security commits recon flagged:
   - `cd3879c` (HTTP security headers middleware): present verbatim in
     `main.py:48-55` (`X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`,
     `Content-Security-Policy`).
   - `fb64750` (XSS fix in `_esc`): current `frontend/js/main.js:67-71` uses the regex-based
     `/[&<>"']/g` replace escaping `&<>"'` exactly as the commit message describes (not the old
     `textContent`-to-`innerHTML` trick). Spot-checked 3 call sites
     (`main.js:753` shop inventory render, `inventory.js:45`, `lobby.js:677-680` save-card render)
     — all route user/AI-derived strings through `_esc()`/`this._escape()` before `innerHTML`
     interpolation. Did not exhaustively check all ~30 `innerHTML` sites in `lobby.js`/`main.js`
     (out of scope for this stage — flagging for stage 3 bug hunt if it wants full coverage).
   - `681dd38`/`245b4c6` (secure cookie flag): `routes_auth.py:41-46,93-98` sets
     `secure=request.url.scheme == "https"` dynamically on both cookie-setting call sites (desktop
     and web login) — matches commit intent.
   - `1d4ea36` (websocket auth): `ws_session.py:13-22` — closes with code 1008 if no
     `storyforge_session` cookie, and again if `jwt.decode` raises `PyJWTError`, before ever
     calling `websocket.accept()`. Verified there is only one `@router.websocket` in the whole
     codebase (`grep -rn "@router.websocket\|@app.websocket" src/storyforge`), so there's no
     second unguarded WS endpoint.
   - `fefa047` (CORS wildcard / shop XSS / token file permissions): `main.py:58-64` uses
     `settings.cors_origins` (explicit origin list from `STORYFORGE_ALLOWED_ORIGINS`, default
     `localhost` only) rather than `"*"`; `auth.py:71` does
     `token_file.chmod(stat.S_IRUSR | stat.S_IWUSR)` (0600) after writing, and `token.json` is
     stored under `~/.local/share/storyforge/` per `auth.py:12` rather than the project root.
     Confirmed no `token.json` is tracked in git (`git ls-files | grep token.json` → empty).
   All 5 fixes verified present and consistent, not partial. Severity: none (all confirmed intact).
   [VERIFIED]

7. **`jwt_secret` defaults to a fresh random value per process (`secrets.token_urlsafe(32)`,
   `config.py:28`), not a static "dev secret" as CLAUDE.md's env var comment implies.** This is
   more secure than documented (unguessable per-boot secret rather than a shared default string),
   but it does mean every server restart invalidates all previously issued session cookies —
   worth knowing operationally (e.g. under `uvicorn --reload`, a source-file save triggers a
   subprocess restart and silently logs everyone out). Severity: low (docs inaccuracy /
   minor operational surprise, not a vulnerability — if anything the current behavior is safer
   than what's documented). [VERIFIED]

8. **No secrets found in git-tracked files** — ran `uvx trufflehog3 -f json --no-history` (v3.0.10)
   over the working tree (excluding `godot/`, `standalone/`, `current_backup/`), then filtered the
   15,989 raw findings down to the 2,385 that fall on `git ls-files`-tracked paths, then further
   filtered by pattern-rule (excluding the `high-entropy` heuristic, which fires on legitimate
   sha256 hashes in `uv.lock`/`standalone/uv.lock` and Godot `.import` asset hashes): **0
   pattern-based hits (API keys, private keys, tokens) in any tracked file.** All `private.key`
   (HIGH severity) hits were confined to `.venv/lib/...` third-party library source/docstrings
   (google-auth, cryptography), not the repo itself, and `.venv/` is not tracked by git
   (confirmed no `.venv` paths in `git ls-files`). Also ran `uvx pip-audit --local` against the
   synced environment: **"No known vulnerabilities found."** Severity: none. [VERIFIED]

9. **Stray tracked artifacts confirmed but benign** — `PXL_20260525_011843405.jpg` (2.6MB) and
   `uvicorn_output.log` are both tracked (`git ls-files | grep` confirms). `git log --oneline --
   uvicorn_output.log` shows it entered via `c804762` ("chore: apply remaining Jules sessions").
   Read the full 13-line log content: only startup banner + one 400 Bad Request line, no secrets,
   no stack traces. Severity: low (repo hygiene only). [VERIFIED]

### Checks run
- `uv sync --group dev` — installed dev deps cleanly.
- `uv run pytest -q` — **88 passed** in 3.53s, no failures/errors/skips.
- `grep -n "^from storyforge\.\|^import storyforge\."` over every file in `src/storyforge/core/`
  — found the one `core/state_manager.py` → `persistence`/`encounters`/`events` violation; all
  other `core/` files clean.
- Read `core/validators.py` in full (226 lines) and cross-referenced every `_filter_*` function
  against `StateDiff`'s 5 fields in `core/models.py` — no whitelist drift.
- Traced all 3 call sites of `StateManager.apply_diff()` (`routes_action.py:87`,
  `routes_npc.py:181`, `routes_npc.py:256`) to confirm sanitize-before-apply discipline holds for
  the one AI-fed call site and is N/A (Python-generated diffs) for the other two.
- `grep -rn "get_current_user" src/` — confirmed dependency is defined once, never consumed;
  cross-checked every router file's `Depends(...)` usage to confirm no route requires auth.
- `grep -rn "@router.websocket\|@app.websocket" src/storyforge` — exactly one WS endpoint, and
  it's the auth-gated one.
- Read `ws_session.py`, `routes_auth.py` (cookie-setting + `/me` + `/logout`), `main.py`
  (middleware stack) in full.
- `git log --oneline -i --grep="XSS|security header|secure cookie|websocket auth" --all` plus
  manual `git show <hash> --stat` on `fb64750` and `fefa047` to see exact diffs, then re-read the
  current versions of every file each commit touched to confirm the fix is still present and not
  since regressed.
- `git ls-files | grep -iE "token\.json|\.env$|credentials|\.pem$|\.key$|id_rsa|\.db$|\.sqlite"` —
  no hits.
- `uvx trufflehog3 -f json --no-history -e "godot/.*" -e "standalone/.*" -e "current_backup/.*"
  -s HIGH .` (v3.0.10, via `uvx`) — ran full scan, then Python-filtered results against
  `git ls-files` and by rule-id to separate real secret patterns from lockfile-hash noise; 0 real
  hits in tracked files.
- `uvx pip-audit --local` (v2.10.1) — "No known vulnerabilities found."
- `git ls-files | grep -iE "\.jpg$|\.jpeg$|uvicorn_output\.log"` + `git log --oneline --
  <file>` + full read of `uvicorn_output.log` — confirmed tracked, benign content.
- Spot-checked 3 `innerHTML` call sites across `main.js`/`inventory.js`/`lobby.js` for `_esc`/
  `_escape` usage post-XSS-fix.

### Checks skipped
- **`gitleaks`** — not installed and no Go toolchain readily available in this sandbox to build
  it; substituted `trufflehog3` (installable via `uvx`) as an equivalent secret scanner instead of
  skipping entirely.
- **Exhaustive line-by-line audit of all ~30 `innerHTML` interpolation sites in
  `frontend/js/lobby.js`/`main.js`** — spot-checked 3 representative sites (all clean); a full
  sweep for any interpolation that bypasses `_esc()`/`_escape()` is left for the stage 3 bug hunt
  since it's a frontend-presentation-layer concern this stage's brief says to mostly skip.
- **`npm audit`/frontend dependency scanning** — N/A, project has no `package.json` /npm
  dependencies per CLAUDE.md ("No npm, no build step for the frontend").
- **`cargo audit`** — N/A, no Rust code in the repo.
- **Godot/GDScript client (`godot/scripts/*.gd`) and `standalone/`/`current_backup/` duplicate
  trees** — excluded from this stage per recon's guidance that CLAUDE.md's FastAPI+vanilla-JS
  description is ground truth; not exercised with tests since Godot isn't part of the Python test
  suite and there's no headless way to run it in this sandbox.
- **Live GitHub Actions/CI run status** — `gh` CLI not available in this sandbox (consistent with
  recon's note); could not cross-check whether CI actually passes on the current HEAD vs. relying
  on the local `pytest` run only.

## 03 — Bug Hunt
(pending)

## 04 — Strengths
(pending)

## 05 — Critic Pass
(pending)
