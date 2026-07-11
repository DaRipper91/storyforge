# StoryForge: Rip-it-apart audit fix pass

> **Implement task-by-task, in order.** Start with **Task 1 — Kodrik gear-repair economy
> exploit**: it's the only finding in this pass that lets any client fabricate a "successful"
> outcome and silently avoid a real state mutation (free repairs, no silver ever deducted,
> success gated entirely on a number the client made up). Everything else is either a
> not-yet-exploited auth gap, a missing safety net, or cleanup.

**Context:** StoryForge is a hybrid VTT + AI Dungeon Master (FastAPI backend, vanilla JS/Canvas
frontend, Gemini as narrative renderer, local-first JSON-snapshotted state) per CLAUDE.md, which
this pass treats as ground truth over the README's Godot-client framing. This audit covered the
live `src/storyforge` backend, its test suite, CI workflows, and repo hygiene — the Godot client,
`standalone/`, and `current_backup/` were explicitly out of scope throughout and remain so. What's
already solid and should **not** be touched while fixing the items below: `core/validators.py`'s
"reject, don't repair" `StateDiff` sanitization (including the deliberate `_MAX_HP_DELTA_PER_TURN`
cap), `character_factory.py`'s server-side standard-array enforcement, `shopkeeper_jon.py`'s
`buy_item()` (the correct pattern Task 1 should copy), `state_manager.py`'s `_commit()` write
ordering (revision bump → disk save → event publish) and its legacy `npc_`-prefix tolerance, and
`ai/client.py`'s retry/backoff/raise-on-exhaustion behavior. All five were independently confirmed
as deliberate, well-reasoned design, not accidental correctness.

---

## Task 1 — Fix Kodrik's gear-repair endpoint to use authoritative server-side silver

**Problem:** `POST /api/kodrik/repair` (`src/storyforge/api/routes_npc.py:697-741`) accepts a
client-supplied `silver_available: int` in the `RepairRequest` body instead of reading the
character's real `CharacterSheet.silver` field (`core/models.py:59`). `encounters/kodrik.py:103-119`
(`repair_gear`) only compares `silver_available < cost` against that client-claimed number, and on
success increments `repaired_items_count` but never returns or applies a `StateDiff` to deduct the
10-silver cost — the route doesn't even take a `StateManager` dependency, so it is structurally
incapable of touching real state. Net effect: any client can repair gear for free by POSTing
`silver_available: 999999` regardless of actual balance, and even a "successful" repair costs
nothing. `tests/test_routes_npc.py:321-346` (`test_kodrik_repair_success`,
`test_kodrik_repair_insufficient_silver`) only assert against the client-supplied value and never
assert any change to a character's real silver balance — the test suite currently encodes the bug
rather than catching it. Severity: high (game-economy integrity bug / server trusting
client-supplied state instead of authoritative data).

**Steps:**
1. Change `kodrik_repair`'s route signature to take a `StateManager` dependency and look up the
   acting character's real `CharacterSheet.silver`, mirroring `jon_buy`
   (`routes_npc.py:167-181`) and `ShopkeeperJon.buy_item()` (`encounters/shopkeeper_jon.py:277-312`).
2. Update `Kodrik.repair_gear()` (`encounters/kodrik.py:103-119`) to accept the authoritative
   silver amount (not a client-supplied field), reject on insufficient funds server-side, and on
   success return a real `StateDiff` that deducts the repair cost.
3. Have the route call `StateManager.apply_diff()` with that `StateDiff` on success.
4. Remove `silver_available` from `RepairRequest` (or ignore/deprecate it) so the client can no
   longer supply the value the server should be computing.
5. Rewrite `test_kodrik_repair_success` / `test_kodrik_repair_insufficient_silver` to assert
   against the character's actual persisted silver balance before and after the call, not the
   client-supplied number.

---

## Task 2 — Enforce authentication on gameplay REST endpoints; stop silently swallowing JWT failures

**Problem:** Two related auth gaps, both in the same subsystem:
- `get_current_user` (`api/deps.py:12`) is dead code — never wired into any route via `Depends`.
  None of `routes_action.py` (`/api/action/grid`, `/freeform`, `/interact_entity`, `/travel`),
  `routes_lobby.py` (`/api/lobby/*`, `/api/character/create`), or all 26 `routes_npc.py` endpoints
  require it, and `main.py` has no global auth middleware — only security headers and CORS. Every
  actual gameplay mutation endpoint (grid/freeform actions, all NPC encounters, character
  creation) is reachable with no authentication check at all, contradicting CLAUDE.md's
  description of `get_current_user` as the thing that "raises 401 if missing or invalid" (true in
  isolation, false of its effect on the API surface since it's never invoked at runtime).
- `routes_lobby.py:151-155, 176-180, 201-205` (`join_lobby`, `leave_lobby`, `update_name`) each
  independently try `jwt.decode()` on the session cookie and overwrite `controller_id` with
  `google::{sub}` on success, but wrap the attempt in a bare `except Exception: pass` — any decode
  failure (expired, tampered, malformed, or an unrelated bug) silently falls back to trusting the
  client-supplied `controller_id` from the request body, with zero logging. A corrupted/expired
  cookie plus a spoofed `controller_id` is indistinguishable from an intentional guest player.

The only endpoint that actually enforces the session JWT today is `ws_session.py` (which,
notably, uses a narrowly-scoped `except PyJWTError` — the correct pattern the lobby routes should
copy). Severity: high (auth exists but isn't enforced anywhere it would matter for gameplay
mutation; the silent broad catch removes any signal that a real token is being rejected).

**Steps:**
1. Decide, explicitly, which endpoints are meant to require a logged-in user (grid/freeform
   actions, NPC encounters, character creation) versus which are meant to support guest/
   local-controller play by design (lobby join, matching `tests/test_routes_lobby.py::
   test_join_requires_controller_id`'s documented behavior) — do not remove guest play, just make
   the split intentional and enforced rather than accidental.
2. Add `Depends(get_current_user)` (or an equivalent, explicitly-scoped dependency) to the
   gameplay-mutation routes identified in step 1.
3. In `routes_lobby.py`'s three JWT-decode sites, replace `except Exception: pass` with a
   narrowly-scoped `except jwt.PyJWTError` (matching `ws_session.py`'s pattern) and add a
   `logger.warning`/`debug` line when a presented cookie fails to decode, so a rejected token is
   distinguishable from an absent one in logs.
4. Add or update tests confirming: (a) gameplay-mutation endpoints reject unauthenticated
   requests where intended, and (b) a malformed/expired cookie in the lobby routes now logs a
   rejection rather than silently falling through unnoticed.

---

## Task 3 — Add a test-gate step to CI

**Problem:** `.github/workflows/build.yml` (7 jobs: Godot export ×2, Python launcher build ×2,
package, GitHub release, itch.io publish) and `.github/workflows/windows-build.yml` both run
`uv sync --group dev` and then go straight to build/export steps — neither workflow contains a
`pytest` invocation anywhere (confirmed via `grep -n "pytest" .github/workflows/*.yml` → zero
matches, twice, independently). Every push to `main` and every PR triggers a full build+release
pipeline with no test gate: a commit that breaks `test_validators.py` or `test_routes_npc.py`
would still produce and, on a tag push, publish a release artifact. The 88 tests confirmed passing
locally (`uv run pytest -q` → `88 passed in 3.53s`) have zero CI enforcement. Severity: high (no
regression safety net on the only branch that ships releases).

**Steps:**
1. Add a `pytest` job/step to `.github/workflows/build.yml`, running before the build/package/
   release jobs, gated so those downstream jobs only run on success.
2. Add the same test-gate step to `.github/workflows/windows-build.yml`.
3. Confirm the release/publish jobs in both workflows have an explicit `needs:` dependency on the
   new test job so a red test run actually blocks the pipeline rather than merely reporting
   red alongside a green release.

---

## Task 4 — Fix `core/state_manager.py`'s violation of the "core has no I/O" invariant

**Problem:** CLAUDE.md states `core/` is "pure logic — no I/O" and "don't import from `ai/`,
`api/`, or `persistence/` inside `core/`." `src/storyforge/core/state_manager.py:31` does
`from storyforge.persistence import snapshot` and calls `snapshot.save(...)` directly at
`state_manager.py:233` and `:652` — disk I/O inside `core/`, the exact thing the invariant
forbids. It also imports `storyforge.encounters.enemies` (`state_manager.py:29`) and
`storyforge.events.bus` (`:30`), both outside `core/`. Every other file in `core/` (`grid.py`,
`rules.py`, `validators.py`, `character_factory.py`) has zero such imports — `state_manager.py` is
the sole offender. Severity: medium (documented architecture invariant is falsified as literally
written; the coupling is arguably intentional given `state_manager.py` is the designated single
mutation/persistence choke point, but the doc and the code currently disagree).

**Steps:**
1. Decide the intended architecture: either (a) update CLAUDE.md's invariant #4 to carve out
   `state_manager.py` explicitly as the one sanctioned exception (the "single mutation/persistence
   choke point"), or (b) extract the `snapshot.save()` / event-publish / enemies-lookup calls
   behind an interface that lives outside `core/` and is injected into `state_manager.py`.
2. If choosing (b), keep the `asyncio.Lock` + `_commit()` ordering (revision bump → disk save →
   event publish) intact exactly as-is — this write ordering was independently identified as
   correct and deliberate; do not change its sequencing while relocating the I/O calls.
3. If choosing (a), update CLAUDE.md's "Core invariants" section so the documented rule matches
   reality, and note the exception is scoped to `state_manager.py` only (the other four `core/`
   files should remain I/O-free, and any new violation elsewhere should still be treated as a bug).

---

## Task 5 — Remove or wire up orphaned NPC prompt files (`npc_mykael.md`, `npc_yeldarb.md`)

**Problem:** Of the 9 "extra" NPC prompt files beyond the 8 implemented encounter classes, 7 are
legitimately wired to the unified flavor-only `POST /api/pet/{pet_id}/interact` endpoint
(`routes_npc.py:929-939`) and are working as intended. `npc_mykael.md` and `npc_yeldarb.md`,
however, describe named characters with actual mechanics (Mykael's "4-Second Peak" strength surge;
Yeldarb's "appears without warning") per `STORYFORGE_CODEX.md:87-95,128-136` — not beasts, so the
"never stat a beast" exemption doesn't apply — yet there is no call site anywhere invoking
`narrate_npc("mykael", ...)` or `narrate_npc("yeldarb", ...)`; `load_prompt()` never loads either
file. The characters are still reachable ambiently via the base `system_dm.md` prompt used by all
general narration, but the dedicated prompt files with their detailed mechanics are dead content.
Severity: low (unused/dead prompt content, not a broken player-facing feature).

**Steps:**
1. Decide whether Mykael and Yeldarb are meant to become real, dedicated encounters (with their
   own service class, matching the pattern of the 8 implemented NPCs) or are intentionally
   ambient-only characters.
2. If dedicated encounters are intended: wire `npc_mykael.md`/`npc_yeldarb.md` into a real
   endpoint/service class, following the same pattern as the 8 existing NPC encounters.
3. If ambient-only is intended: delete the two orphaned prompt files (or explicitly document, in
   `STORYFORGE_CODEX.md` or a code comment, that they're intentionally unused reference material)
   so a future contributor doesn't waste time looking for a call site that doesn't exist.

---

## Task 6 — Fix hardcoded personal machine path in `scripts/launch.sh`

**Problem:** `scripts/launch.sh:4` hardcodes
`PROJECT_ROOT="/home/daripper/Projects/storyforge"` followed by `cd "$PROJECT_ROOT"`. This only
works on the original author's exact machine/username; any other contributor running this script
gets `cd: no such file or directory` with no error handling afterward, so the subsequent
`uv run python src/storyforge/gui.py` runs from whatever directory the failed `cd` left the shell
in. The sibling script `scripts/dev.fish:4` correctly derives its root via
`set -l PROJECT_ROOT (status dirname)/..`. Note: `dev.fish`, not `launch.sh`, is the documented
entry point per CLAUDE.md's Commands section, and nothing in CI/`gui.py`/`scripts/build.py`
invokes `launch.sh` — this is a personal convenience script, not a documented or CI-exercised path.
Severity: low (portability/onboarding paper cut for anyone besides the original author using this
specific, undocumented script).

**Steps:**
1. Replace the hardcoded path in `scripts/launch.sh:4` with a relative derivation matching
   `dev.fish`'s pattern (e.g. resolve `PROJECT_ROOT` from the script's own location).
2. Add a `cd` failure check (`|| exit 1`) so a bad path fails loudly instead of silently running
   subsequent commands from the wrong directory.

---

## Task 7 — Clean up stale documentation and dead/duplicate repo artifacts

**Problem:** Several small, independent hygiene issues, none functionally breaking, all
misleading to a new contributor:
- CLAUDE.md's "note: no tests exist yet — tests/ is empty" is stale; `tests/` actually contains 5
  files / ~1,257 lines and 88 passing tests (confirmed via `uv run pytest -q`).
- `config.py:28`'s `jwt_secret` default is `secrets.token_urlsafe(32)` (a fresh random value per
  process), not the static "dev secret" CLAUDE.md's env var comment implies — worth documenting
  accurately, including the operational note that every server restart invalidates all existing
  session cookies (e.g. `uvicorn --reload` logs everyone out on every file save).
- `docs/README.md:1-15` advertises "Python 3.14," "Platform: Arch / Asahi / Termux," and "a
  specialized node within the Project Aether ecosystem" — none of which match `pyproject.toml`'s
  `python_requires = ">=3.12"`, both CI workflows' `python-version: '3.12'` pin, or anything else
  in `src/`. A new contributor reading this file first is misdirected onto a nonexistent stack.
- `buildozer.spec` is tracked despite matching the `*.spec` gitignore pattern (`.gitignore:8-9`
  only negates `!StoryForge.spec`) and describes a Kivy/Android build with zero other references
  anywhere in the repo — dead tooling from an abandoned approach.
- `.jules/palette.md` and `.Jules/palette.md` are both tracked, case-divergent paths with
  genuinely different accumulated content (a case-insensitive-filesystem fork) — any tooling that
  only reads one casing silently loses whatever was appended to the other.
- `PXL_20260525_011843405.jpg` (2.6MB) and `uvicorn_output.log` are tracked at the repo root;
  both are benign in content but shouldn't be checked in.

Severity: low across all items (docs drift / repo hygiene only).

**Steps:**
1. Update CLAUDE.md's Commands section to remove the stale "tests/ is empty" note and mention the
   real test suite (88 tests, `pytest`).
2. Update CLAUDE.md's Environment section to accurately describe `jwt_secret`'s actual default
   behavior (random per-process, not a static string) and the restart/logout implication.
3. Rewrite or retire `docs/README.md` so it doesn't contradict `pyproject.toml`/CI on Python
   version, platform, or the "Project Aether" framing — align it with CLAUDE.md's description or
   remove it if it's fully superseded.
4. Delete `buildozer.spec` (or, if Android packaging is genuinely still a future goal, move it
   somewhere clearly marked as aspirational/unused and note that in a comment).
5. Reconcile `.jules/palette.md` and `.Jules/palette.md` — merge their distinct content into one
   canonical file and delete the duplicate, or rename one to avoid case-collision entirely.
6. Remove `PXL_20260525_011843405.jpg` and `uvicorn_output.log` from git tracking (`git rm
   --cached`) and add them to `.gitignore` if they're expected to reappear locally.

---

## Known coverage gaps

- **Frontend `innerHTML` interpolation sites were only spot-checked, not exhaustively swept.**
  Stage 2 of this audit checked 3 representative call sites (`frontend/js/main.js:753`,
  `inventory.js:45`, `lobby.js:677-680`) out of roughly 30 `innerHTML` interpolation sites across
  `frontend/js/lobby.js`/`main.js`, confirming all 3 correctly route user/AI-derived strings
  through `_esc()`/`this._escape()` before interpolation (consistent with the real, verified XSS
  fix commit `fb64750`). This was explicitly handed off to the bug-hunt stage for full coverage,
  but the bug-hunt stage never picked it up — the remaining ~27 sites have not been checked. Given
  the 3 spot-checked sites and the underlying fix are genuinely clean, risk is likely low, but this
  is a disclosed, open gap, not a "checked, clean" result — a full sweep of `frontend/js/lobby.js`
  and `frontend/js/main.js` for any `innerHTML` interpolation that bypasses the escape helpers is
  still owed.
- **Live CI run status was never obtained** (no `gh` CLI / GitHub API access during this audit).
  Task 3 above is based on static analysis of the workflow YAML (confirmed zero `pytest`
  invocations), which is sufficient to support "no test gate exists," but nobody has confirmed
  whether the current HEAD's *build* steps (as opposed to test steps) actually succeed in CI —
  only that no test step exists to fail one.
- **Godot client (`godot/scripts/*.gd`, ~16k lines), `standalone/`, and `current_backup/`** remain
  out of scope by design across this entire audit (consistently disclosed at every stage) and are
  not covered by anything in this plan.

## Definition of done

- Task 1: Kodrik repair route takes a `StateManager` dependency, reads real
  `CharacterSheet.silver`, applies a `StateDiff` deducting the repair cost on success, and
  `RepairRequest` no longer trusts a client-supplied silver amount; tests assert against actual
  persisted silver balance.
- Task 2: gameplay-mutation endpoints require authentication where intended; lobby routes' JWT
  decode failures are caught narrowly (`PyJWTError`) and logged rather than silently swallowed;
  tests cover both.
- Task 3: both GitHub Actions workflows run `pytest` before any build/release job, and release
  jobs are gated on that test job passing.
- Task 4: either CLAUDE.md's invariant #4 explicitly documents `state_manager.py` as the sanctioned
  I/O exception, or the I/O calls have been moved out of `core/` — `_commit()`'s write ordering is
  unchanged either way.
- Task 5: `npc_mykael.md`/`npc_yeldarb.md` are either wired to a real encounter or removed/
  explicitly documented as intentionally unused.
- Task 6: `scripts/launch.sh` derives its project root relative to the script location and fails
  loudly if `cd` fails.
- Task 7: CLAUDE.md's test and jwt_secret claims are accurate; `docs/README.md` no longer
  contradicts the real stack; `buildozer.spec` is removed or clearly marked aspirational; the
  `.jules`/`.Jules` duplicate is reconciled; the stray JPEG and log file are untracked.
