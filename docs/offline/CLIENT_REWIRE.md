# Client rewire (Step D2b)

The Godot client can talk to the in-process `LocalBackend` instead of the FastAPI server. Default (`remote`) behaviour is unchanged.

## Mode switch (first match wins)

1. user arg `--backend=local|remote` (after `--`, e.g. `godot --path godot -- --backend=local`)
2. env `STORYFORGE_BACKEND`
3. `user://backend.cfg`: `[backend]` / `mode="local"`
4. default `remote`

`PythonClient.backend_mode`, `PythonClient.is_local()`, `PythonClient.get_local_backend()`.
Local save dir: `user://campaigns/`; override with `--save-dir=<dir>` or env `STORYFORGE_SAVE_DIR` (tests use this).
Offline game: `scripts/launch_offline.sh` (needs a display; not run by the test suite).

## What changed

| File | Change |
|---|---|
| `godot/scripts/backend/backend_http.gd` (new) | `BackendHttp`: HTTPRequest look-alike (`request()`, `request_completed(result, code, headers, body)`); strips origin, parses query/JSON body, calls `GameBackend.request`, emits next frame (String bodies as raw utf8, others `JSON.stringify`), then frees itself |
| `godot/scripts/PythonClient.gd` | mode resolution, `new_http()` factory (only remaining `HTTPRequest.new()`), LocalBackend creation, local boot signal, `state_changed` wiring, ws polling skipped when local; 8 `HTTPRequest.new()` sites -> `new_http()`; `post_request/get_request` return `Node` |
| `godot/scripts/Tabletop.gd` | `var http: HTTPRequest` -> `Node`; freeform handler shows the backend's `detail` on non-2xx; `_update_narrative` null guard (see below) |
| `tools/golden/run_gd_smoke.sh`, `godot/tests/golden/smoke_local.gd` | smoke test A (real autoload, local mode, throwaway save dir) |
| `tools/golden/run_gd_scene_smoke.sh`, `godot/tests/golden/scene_smoke.gd` | scene smoke B: error-set diff local vs remote vs pre-change |
| `scripts/launch_offline.sh` | offline launcher |

Every other script already goes through `PythonClient.post_request/get_request/fetch_*`, so no other call site needed edits.

## Boot and state wiring (local mode)

- No `/healthz` loop, no websocket. On the first frame `PythonClient` sets `is_connected` and emits `connection_status_changed(true)` (once; `start_connection()` just triggers the same guarded signal).
- Boot campaign: `LocalBackend` ctor loads `family_campaign_01` from the save dir if present, else the bundled seed (same as `main.lifespan`). `campaigns/load|new` swap the live campaign for the session only.
- `LocalBackend.state_changed` is handled exactly like the ws `state_diff`: `fetch_full_state()` -> GET /state through the shim -> `state_updated`. Chosen over emitting `state_updated` directly so the downstream path (and its one-frame latency) is identical to remote. Difference: `campaigns/new|load` also fire `state_changed` (no bus event in Python), giving one extra `state_updated`.
- Auth: `desktop_login` is answered by the backend stub (200, offline user).

## 503/501 handling

- `/npc/**` -> 503, `action/freeform` -> 501. Existing call sites already gate on `code >= 200 and < 300` (NPC interact, combat) or flatten the `detail` string into the NPC dialog (`_npc_do_action`); Jon inventory/buy handlers in `PythonClient` already map non-200 to `[]` / failure message.
- Guard added: `Tabletop._on_freeform_submitted` appends the backend `detail` (or a generic line) to the narrative box on non-2xx (the box may not exist, so it is null-checked).
- Unrelated pre-existing bug fixed minimally: `Tabletop._update_narrative` assigned `.text` on `_narrative_box`, which is only built in `_load_level()` (never called). A real `/state` with `narrative_log` entries made it throw; now returns early.

## Known gaps

- NPC encounters, Jon shop (inventory/buy) and freeform text do nothing useful offline.
- No display available when this was written: scenes were only loaded headless for a few frames; interactive play-through (clicking, camera, audio) is unverified.
- `JonShopPanel` Array-vs-Dictionary typing issue from the contract doc is untouched.
- Saves live under Godot's `user://campaigns/`; New Game ids use the UTC clock.

## Tests

    bash tools/golden/run_gd_smoke.sh         # 36 checks, RESULT: OK
    bash tools/golden/run_gd_scene_smoke.sh   # error-set diff, RESULT: OK when local is a subset of remote U pre-change
    bash tools/golden/run_gd_tests.sh; bash tools/golden/run_gd_routes.sh; uv run pytest -q
