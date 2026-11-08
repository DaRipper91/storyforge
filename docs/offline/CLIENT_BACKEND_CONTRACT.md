# Godot client <-> backend contract (Step D1)

Scope: everything `godot/scripts/**` sends to / expects from the FastAPI backend (`src/storyforge/api/**`),
as of branch `offline-port` (rebased on origin/main af02835). Written to let a GDScript `LocalBackend` (step D2)
answer the client's requests in-process.

Conventions: `file:line` references are to the worktree. "UNVERIFIED" marks claims derived from reading code
only (Godot was never run). Route-level golden fixtures for every CORE route live in `tests/golden/routes/`
(format: `tests/golden/ROUTES_README.md`); `[fx: flow]` below names the flow that exercises a route.

Embedded scripts: `godot/scenes/**` contain no script code that talks to the backend. The only scene hit is
`godot/scenes/Boot.tscn:55` (placeholder text `http://127.0.0.1:8765`). All traffic goes through the
`PythonClient` autoload (`godot/project.godot:24`), plus `TimeManager` (autoload, `project.godot:26`).

Class legend: CORE = implementable with the ported core modules; ENCOUNTER = needs unported
`encounters/*` + `routes_npc.py`; AI = calls Gemini; AUTH = to be dropped offline; INFRA = healthz/ws/static.

## 1. Client transport facts (apply to every row)

- **Base URL.** `server_url` + `/api` (`PythonClient.gd:16-17`); default `http://127.0.0.1:8765` (`:12`).
- **Request helpers.** `post_request(endpoint, dict)` JSON-encodes the dict, header `Content-Type: application/json`
  (`PythonClient.gd:173-179`); `get_request` (`:181-185`); both return the `HTTPRequest` node and the caller
  connects `request_completed`. A few calls bypass the helper and send an empty-string POST body with no header:
  `desktop_login` (`:196`), `campaigns/new` (`:248`).
- **No auth is ever sent.** There is no `Cookie`/`Authorization` header or cookie jar anywhere in `godot/scripts`
  (grep "cookie" -> no hits). Lobby routes therefore fall back to the body's `controller_id`
  (`routes_lobby.py:140-163`). Godot 4's `HTTPRequest` has no cookie jar (UNVERIFIED at runtime), so the
  `storyforge_session` cookie from `desktop_login` is, in practice, dropped.
- **Status handling is sparse.** Most callbacks ignore the status code and only free the node; errors are surfaced only
  by `character/create`, `lobby/start`, `jon/*`, and `healthz`.
- **Response `revision` is never read** by the client (grep: no `revision` in `godot/scripts`). Only the full-state
  refetch matters.

## 2. Route table: routes the client calls

Columns: method+path | caller file:line | request body keys the client sends | response keys the client READS |
status/error handling the client relies on | CLASS | fixture flow.

### 2.1 CORE (14)

| Route | Caller | Body sent | Response keys read | Status / errors | Class | Fixtures |
|---|---|---|---|---|---|---|
| GET `/api/state` | `PythonClient.gd:162-171` (`fetch_full_state`); callers: `Tabletop.gd:183`, `:509`, `:1302`, `:1357`, `:1998`; `CreationManager.gd:84`; ws `state_diff` (`:137-138`) | - | whole object passed to `state_updated`; consumers read: `current_room_id`, `rooms[id].{name,width,height,cells[].terrain,exits}` (`Tabletop.gd:773-788,824-`), `characters` (dict) each `{id,position{x,y},race,name,abilities,inventory,hp_current,hp_max,armor_class,speed,evolution_state,predator_role}` (`:981-995,1596-1640`), `enemies` each `{room_id,position,alive,hp_current,hp_max,sprite_key,kind,name}` (`:1003-1025,1060`), `npcs` each `{room_id,position,interactable,target_position,description,sprite_key,...}` (`:1090-1110`, `NpcManager.gd:18-30`), `narrative_log[].{kind,text}` (`:1176-1192`), `lobby_slots[].{status,slot_index}` (`CreationManager.gd:89-93`), `phase` is NOT read here | status code ignored; body parsed with `JSON.parse_string`, falsy -> silently dropped (`PythonClient.gd:168-171`) | CORE | boot_reads, all |
| POST `/api/time/sync` | `TimeManager.gd:39-44` (called from `_increment_hour`, `:37`, i.e. once per in-game hour) | `day,hour,minute` | none (`http.queue_free` only, `:44`) | ignored | CORE | paradox_time |
| GET `/api/lobby/catalog` | `PythonClient.gd:211-222`; caller `CreationManager.gd:83` | - | `races{key:{name,before,group,flavor,speed,ability_bonuses}}`, `states{key:{name,flavor}}`, `roles{key:{name,flavor}}` (`CreationManager.gd:164-221,260-279,322-323,403-420`). Other catalog keys (backgrounds, feats, skills, cantrips, alignments, dialogue_styles, standard_array) are not read | only `== 200` emits `catalog_received` (`:219`); non-200 -> silence, creation screen stays blank (`CreationManager.gd:101-102`) | CORE | boot_reads |
| GET `/api/campaigns` | `PythonClient.gd:230-242`; `UIManager.gd:70` | - | `campaigns[].{campaign_id,characters[],phase}` (`UIManager.gd:80-90`); `revision`/`last_modified` unread | `== 200` only (`:237`); else nothing | CORE | boot_reads, campaigns |
| POST `/api/campaigns/new` | `PythonClient.gd:244-254`; `UIManager.gd:49` | none (empty string) | body parsed and emitted, but `UIManager._on_new_campaign_ready` ignores it (`:51`) | `== 200` only; on failure the "Creating..." button stays disabled forever (`UIManager.gd:46-48`) | CORE | campaigns |
| POST `/api/campaigns/load` | `PythonClient.gd:256-264`; `UIManager.gd:110` | `campaign_id` | `phase` (`UIManager.gd:112-118`): `"exploration"` -> Tabletop else Creation | `== 200` only; 404/400 -> nothing happens (UI stuck on "Loading ...") | CORE | campaigns |
| POST `/api/lobby/join` | `PythonClient.gd:270-278`; `UIManager.gd:55` (`"godot_player"`) | `controller_id` | `slot_index` (default 0) | `== 200` only (409 "all 4 slots claimed" -> silent; flow stalls) | CORE | lobby_slots, character_creation |
| POST `/api/lobby/set_phase` | `PythonClient.gd:280-281` (`post_request` result discarded, so the `HTTPRequest` is never freed or checked); `UIManager.gd:58` | `phase` (`"creation"` only) | none | not checked (fire-and-forget; Creation scene loads immediately, `UIManager.gd:59`, racing the request) | CORE | lobby_slots, exploration |
| POST `/api/character/create` | `PythonClient.gd:288-298`; `CreationManager.gd:476-484` | `slot_index,name,race,evolution_state,predator_role,starting_era,abilities{STR..CHA}` | on success whole dict emitted, `_result` unused (`CreationManager.gd:486`); on failure `detail` read as a **string** (`PythonClient.gd:297`) | `== 200 and json` = success; anything else shows `detail` or "Unknown error". 422 bodies have `detail` as a **list**; it is formatted into a label with `%s` (UNVERIFIED rendering) | CORE | character_creation |
| POST `/api/lobby/start` | `PythonClient.gd:303-313`; `CreationManager.gd:488-489` | `{}` | none (`game_started` has no payload) | 200 -> Tabletop scene; else `detail` string shown (409 body has string `detail`) | CORE | character_creation, lobby_slots |
| POST `/api/action/grid` (move) | `Tabletop.gd:1309-1315` | `actor_id,type:"move",target{x,y}` | **none** - response ignored, node freed (`:1315`) | ignored. The move becomes visible only through a ws `state_diff` -> refetch (see 4a) | CORE (plain move uses AI narration with built-in fallback `routes_action.py:51-54`) | exploration |
| POST `/api/action/grid` (interact door) | `Tabletop.gd:1293-1304`, `:1991-2000` | `actor_id,type:"interact",target{x,y}` | presence of key `room_transition` (`:1301`, `:1996`) | status ignored; refetches `/state` if the key exists | CORE | world_travel |
| POST `/api/action/grid` (interact NPC) | `Tabletop.gd:1362-1377` | same | `encounter` dict; requires `encounter.type == "npc_encounter"` then `npc_id,npc_name,encounter_id` (`:1373-1376`, `_show_npc_dialog` `:1405-1420`) | 2xx only | CORE (returns encounter *descriptor*; the encounter itself is ENCOUNTER) | exploration |
| POST `/api/action/interact_entity` | `Tabletop.gd:1384-1401` | `actor_id,target_id` | `encounter.{type,npc_id,npc_name,encounter_id}` | 2xx only | CORE | exploration |
| POST `/api/action/travel` | `Tabletop.gd:502-511` (`_travel_to`) | `room_id` | none | status ignored; always refetches `/state` (`:509`) | CORE | world_travel, enemy_combat |
| POST `/api/enemy/{enemy_id}/attack` | `Tabletop.gd:1321-1359` | `actor_id` | `player_attack.{hit,hint}`, `enemy_died`, `xp_reward`, `enemy_attack.{hit,hint}`, `enemy_hp` (`:1332-1356`, `_show_combat_result` `:1551-1576`) | 2xx only; 404/409/400 are swallowed silently (no UI feedback) | CORE | enemy_combat |

(`grid` counts once in the totals; it appears as three rows because the client uses three response contracts.)

### 2.2 ENCOUNTER (17; all sit on `routes_npc.py`, prefix `/api/npc`)

NPC actions are hard-coded in `Tabletop.gd:1446-1505` (`_npc_actions_for`) and executed by `_npc_do_action`
(`:1508-1545`). The client reads, in order, the first non-empty string among `narrative, flavor, result, observation,
report, address, performance` (`:1527-1542`), else the first string value in the dict. Shared handling: status code is
never checked in this path (`:1524-1545`), so a 422 prints `...`.

| Route | Caller | Body sent | Server model (mismatch?) | Reads | Notes |
|---|---|---|---|---|---|
| GET `/npc/jon/inventory?genre=` | `PythonClient.gd:320-329` | query `genre` | `routes_npc.py:145` | `items[]` (id,name,...) | non-200 -> empty shop; no AI |
| POST `/npc/jon/buy` | `PythonClient.gd:331-341` | `actor_id,item_id,genre` | `BuyRequest` `:157` | `success`/`message` is NOT used: client treats `response_code == 200` as success and reads `message` (`:337-338`) | **200 with `success:false` (`:179`) shows "Purchased!"-style success** - client bug; also needs `apply_diff` on the real state |
| POST `/npc/jon/cactus` | `Tabletop.gd:1451` | `is_lewd_or_mocking` | `CactusRequest` ok | `jon_response` is not in the client's key list -> falls back to first string value | AI-optional (pool fallback) |
| POST `/npc/samael/consult` | `:1455` | `category:"general"`, `question` | `ConsultRequest.category` enum (`general_lore`,...) | -> 422 (UNVERIFIED, from code) | AI-optional |
| GET `/npc/haylie/inn` | `:1459` | - | `:424` | `description` via first-string fallback | no AI |
| POST `/npc/danna/address` | `:1463` | `form:"formal"` | `AddressForm` = proper/friendly/casual/wrong -> 422 | | AI-optional |
| POST `/npc/danna/petition` | `:1464` | `type:"request"` | field is `petition_type`; `type` ignored (default blessing) | | AI-optional |
| POST `/npc/cinder/perform` | `:1468` | none | `:552`; also publishes `npc_event` (`:573`) | | AI-optional |
| POST `/npc/cinder/tip` | `:1469` | `amount:5` | field is `silver`; `amount` ignored (default 5) | | |
| POST `/npc/cinder/request-song` | `:1470` | `song:"..."` | field is `song_type`; `song` ignored | | AI-optional |
| POST `/npc/kodrik/dispatch` | `:1474` | none (`dispatch_type` is a query param) | `:700` | | AI-optional |
| POST `/npc/kodrik/repair` | `:1475` | `item:"armor"` | `RepairRequest` needs `item_name`, `silver_available` -> 422 (UNVERIFIED) | | |
| GET `/npc/bryne/observation` | `:1479` | - | `:747` | `observation`/`flavor` | AI-optional |
| POST `/npc/bryne/cole-lean` | `:1480` | none | `:770` | `flavor` | AI-optional |
| GET `/npc/nathis/report` | `:1484` | - | `:795` | `flavor` | AI-optional |
| POST `/npc/nathis/tyty-bark` | `:1485` | none | `:819` | `flavor` | AI-optional |
| POST `/npc/pet/{keeva,teddy,cyrus,bink_bink,cole,coco,tyty,snowie}/interact` | `:1489-1503` | none | `:929` | `flavor` | AI-optional (per-pet fallback text) |

### 2.3 AI (1)

| Route | Caller | Body | Reads | Handling | Class |
|---|---|---|---|---|---|
| POST `/api/action/freeform` | `Tabletop.gd:2024-2035` (`_on_freeform_submitted`) | `actor_id,text` | `narrative` | 2xx only; input is disabled until the response (`:2023`, re-enabled `:2028`) - an offline backend must always answer or the box stays disabled | AI (`routes_action.py:61`, `interpreter.interpret_freeform`). Needs a stub reply offline |

### 2.4 AUTH (1)

| Route | Caller | Body | Reads | Handling | Class |
|---|---|---|---|---|---|
| POST `/api/auth/desktop_login` | `PythonClient.gd:191-205`; `UIManager.gd:24-30` (any key / click on the title screen) | none | `status == "ok"`, `user.name` (print only) | the **title screen only proceeds on success** (`UIManager.gd:32-37`); otherwise "Auth Failed. Press ANY KEY to Retry". The OAuth flow blocks for the browser round trip (`routes_auth.py:21`) | AUTH. Offline: stub must return `{"status":"ok","user":{}}` (or the client must skip the title gate) |

### 2.5 INFRA (2)

| Route | Caller | Notes |
|---|---|---|
| GET `/api/healthz` | `PythonClient.gd:103-118` (`_base_url + "/healthz"`, i.e. `/api/healthz`; `main.py:89-90` serves both `/healthz` and `/api/healthz`) | 200 -> `is_connected`, `connection_status_changed(true)`, opens the websocket. Anything else: emits `false`, waits 2 s, retries forever (`:117-118`). Only the status code is read; `{"status":"ok","version":"0.1.0"}` body unread |
| WS `/ws/session/main` | `PythonClient.gd:19-26,120-158` | see 4a. Server requires the `storyforge_session` cookie, else closes 1008 (`ws_session.py:15-26`) |

### Totals for client-used routes
CORE 14 (counting `action/grid` once), ENCOUNTER 17, AI 1, AUTH 1, INFRA 2 -> 35.

## 3. Backend routes the client never calls

| Route | Class | Note |
|---|---|---|
| GET `/healthz`, GET `/`, mount `/static` | INFRA | `main.py:84-90`; `/` serves `frontend/index.html` (web client only) |
| GET `/api/revision` (`routes_state.py:56`) | CORE | unused; the client never polls |
| POST `/api/state/trigger_paradox` (`:50`) | CORE | unused. The client has handlers for ws `paradox_triggered` (`PythonClient.gd:141`), but nothing publishes that top-level type (see 4a) |
| GET `/api/enemy/room/{room_id}` (`routes_enemy.py:17`) | CORE | unused; the client derives enemies from `/state` |
| POST `/api/lobby/leave`, `/update_name`, `/save_draft` (`routes_lobby.py:166,191,220`) | CORE | web client only |
| GET `/api/auth/config`, `/me`, POST `/google`, `/logout` | AUTH | web client only |
| POST `/api/npc/jon/escape`, `/jon/tick`, GET `/jon/state`, `/samael/state`, POST `/haylie/bailout`, GET `/haylie/state`, `/danna/state`, POST `/cinder/heckle`, GET `/cinder/state` | ENCOUNTER | |

## 4. Required sections

### 4a. Websocket messages -> state

- Connect: after a 200 from healthz (`PythonClient.gd:111-113`) `connect_websocket()` (`:120-121`) opens
  `ws://host/ws/session/main`. `_process` polls every frame (`:123-131`); on `STATE_CLOSED` it does nothing
  (`:130-131`): **no reconnect, no error signal**.
- Dispatch (`_handle_ws_message`, `:133-149`) switches on `json["type"]`:
  - `state_diff` -> `fetch_full_state()` (GET `/api/state`) -> `state_updated(full_state)`. **The diff payload is
    discarded**; the client never applies diffs. `revision` is not compared either.
  - `narration` -> signal `narration_received(json["text"])` (`:139-140`); `paradox_triggered` -> signal with
    `transformed_ids` (`:141-142`); `phase_changed` -> signal with `phase` (`:143-144`); `npc_event` -> audio for
    cinder/perform + signal (`:145-147`, `:152-158`); `particle_event` -> signal (`:148-149`).
  - `state_updated` is **not handled** (no match arm): the `{"type":"state_updated"}` message that `time/sync`
    publishes (`routes_state.py:39-42`) is ignored.
- What the backend actually publishes (`grep event_bus.publish`): `state_diff` from `_commit` for every mutator
  (`state_manager.py:642-657`; the mutation summary is nested under `diff`); `state_updated` from `time/sync`
  (`routes_state.py:38-42`); `npc_event` from NPC routes; `particle_event` from freeform (`routes_action.py:96-101`).
  **Nothing publishes top-level `narration`, `paradox_triggered` or `phase_changed`** - those client handlers are dead
  (the same words occur only inside `state_diff.diff.type`, see fixtures). Tabletop's `open_shop` npc_event branch
  (`Tabletop.gd:1653`) is likewise never produced.
- Auth gate: the server closes the socket with code 1008 when `storyforge_session` is missing/invalid
  (`ws_session.py:15-26`). Because the client never sends a cookie, the websocket most likely never delivers any message
  in the current client (UNVERIFIED at runtime). Evidence of how it still works: the only refreshes that do not depend
  on the ws are the explicit `fetch_full_state()` after travel/door/attack (`Tabletop.gd:509,1302,1357,1998`) and on
  scene load (`:183`, `CreationManager.gd:84`). A plain move click discards its response (`:1315`) and therefore
  would not update the screen without a ws `state_diff`. **An offline backend must emit `state_updated` itself after
  every mutating request (the in-process equivalent of `state_diff`).**
- Recorded bus events per step are in the fixtures (`events` key), so D2 can assert exactly which mutations emit
  a `state_diff` (all `_commit` callers: join/leave/update_name/save_draft/set_phase/create/start/move/interact/attack/
  travel/trigger_paradox/apply_diff/append_narration) and which do not (failed requests, repeated `join`).

### 4b. Boot sequence and what blocks on `/healthz`

1. Godot starts the main scene `Boot.tscn` (`project.godot:18`); autoloads
   `PythonClient`, `TimeManager` (`project.godot:22-26`) already run. `TimeManager._process` ticks the in-game clock
   from the first frame and POSTs `/time/sync` every in-game hour (5 real minutes) **even before any connection or
   campaign exists** (`TimeManager.gd:14-44`).
2. `BootManager._ready` (`BootManager.gd:10-28`): env `STORYFORGE_SERVER_URL` or arg `--local-server` -> auto-connect to
   `DEFAULT_URL`; else shows a URL box prefilled from `user://settings.cfg` (`PythonClient.gd:89-99`).
3. `start_connection(url)` saves the URL and calls `check_python_server()` (`PythonClient.gd:84-87,103-107`) -
   GET `/api/healthz`. **Everything blocks on this**: the scene change to `UI_Overlay.tscn` happens only when
   `connection_status_changed(true)` fires (`BootManager.gd:46-48`); on failure it retries every 2 s without limit.
4. After 200: websocket connect (see 4a; its failure is invisible).
5. `UI_Overlay` -> title screen waits for a key/click, then `trigger_desktop_login` (AUTH) gates the main menu
   (`UIManager.gd:24-37`).
6. New game: `POST /campaigns/new` -> `POST /lobby/join {"controller_id":"godot_player"}` -> `POST /lobby/set_phase
   {"phase":"creation"}` -> `Creation.tscn` (`UIManager.gd:46-59`). Creation fetches catalog + state
   (`CreationManager.gd:83-84`), user steps, `POST /character/create`, then `POST /lobby/start`, then `Tabletop.tscn`
   (`CreationManager.gd:486-499`). Tabletop fetches state on `_ready` (`Tabletop.gd:183`).
7. Load game: `GET /campaigns` -> `POST /campaigns/load` -> scene by `phase` (`UIManager.gd:70,110,112-118`).
   Note: loading a campaign swaps `app.state.state_manager` server-side (`routes_state.py:81-92`) but no
   `state_updated` is fired; the Tabletop's first `fetch_full_state` covers it.

### 4c. Where the client keeps its own copy of state

All derived from the last `/state` payload unless noted. None is persisted; none is reconciled against `revision`.

| Cache | File:line | Content / risk |
|---|---|---|
| `_character_data` | `Tabletop.gd:115,993` | cid -> character dict; used for selection, stat panel, gold, "any player id" (`:1579-1584`) |
| `_room_width/_room_height/_room_cells/_room_exits` | `Tabletop.gd:118-121,785-788` | cached at every state update for click-to-move; terrain is read from `_room_cells[].terrain` client-side (`:1991-2000` area) so click classification (floor/door) is done **client side** before choosing which route to call |
| `_current_room_id` | `Tabletop.gd:16,790-792` | geometry rebuilt only when this changes; room *contents* (cells) are not re-read after the first build, so occupant changes are not rendered from cells |
| `_enemy_data`, `_enemy_cells`, `_enemy_tokens` | `Tabletop.gd:124-126,1003-1025` | enemy_id -> dict, "x,y" -> id (alive only), scene nodes. Attack HP bar uses cached `hp_max` (`:1356`) |
| `_npc_data`, `_npc_cells`, `_npc_tokens`, `_npc_active_data` | `Tabletop.gd:129-131,149,1090-1119` | NPC occupancy is client-derived from `npcs[].position`/`interactable` (not from `cells[].occupant_id`) |
| `_miniatures`, `_selected_cid` | `Tabletop.gd:9,114` | scene nodes + selection |
| `WORLD_MAP_NODES` + `CONNECTIONS` | `Tabletop.gd:98-` and world map block | hard-coded room ids/positions of the world map; the client can request `travel` to ids the server may not have (server 404 is ignored, `:507-511`) |
| `catalog`, `selection`, `slot_index` | `CreationManager.gd:38-47,89-93` | catalog cached for the scene's life; `slot_index` taken from `lobby_slots` with status claimed/creating, defaulting to 0 |
| `_items`, `_gold`, `_actor_id` | `JonShopPanel.gd:23-29,135-148` | gold recomputed from `inventory` entries whose id/name contain "gold" (`quantity*value`). `state.get("characters", [])` is typed `Array` but the server sends a **dict keyed by id** (`:139`) - runtime type error on the first state update while the panel is visible (UNVERIFIED) |
| `_npc_agents` | `NpcManager.gd:3,18-30` | nav agents; uses `npcs[].target_position` set by `time/sync` |
| In-game clock `day/hour/minute/is_day` | `TimeManager.gd:6-12` | **client-owned**: never read back from the server; reset to day 1, 06:00 on every launch; the server only receives it via `time/sync` (and stores nothing but NPC `target_position`) |
| `server_url`, `is_connected` | `PythonClient.gd:14,37`; `user://settings.cfg` | |

### 4d. Proposed minimal interface for D2

```
LocalBackend.request(method: String, path: String, body: Dictionary = {}, query: Dictionary = {}) -> Dictionary
    # returns {"status": int, "body": Variant}   # body = parsed JSON, or {"__text__": "..."} for non-JSON (500)
    # signal state_changed(revision)             # LocalBackend emits after every successful mutation
```

- `path` is the full API path including `/api` (as in the fixtures), so the same strings work for HTTP and local.
- A thin shim in `PythonClient.gd` would replace `HTTPRequest` with `LocalBackend.request` and complete
  `request_completed(result, status, headers, body_bytes)` with `JSON.stringify(body)`; `fetch_full_state` and the
  `state_updated` signal stay untouched. `state_changed` replaces the ws `state_diff` -> `fetch_full_state` hop.
- Dispatch table covering all 14 client CORE routes plus the unused CORE ones (`leave`, `update_name`, `save_draft`,
  `revision`, `trigger_paradox`, `enemy/room/{id}`):

| (method, path) | Handler (ported module) | Status codes to reproduce (see fixtures) |
|---|---|---|
| GET /api/state | `CoreStateManager` state dict | 200 |
| GET /api/revision | `state.revision` | 200 |
| GET /api/lobby/catalog | `*_data.gd` consts + `standard_array [15,14,13,12,10,8]` | 200 |
| POST /api/time/sync | schedule scan, bump revision only on change, emit `state_updated` | 200, 422 |
| GET /api/campaigns, POST /api/campaigns/new, POST /api/campaigns/load | file store under `user://campaigns/`; `new` id `campaign_%Y%m%d_%H%M%S`; `last_modified` = file mtime | 200, 400 (traversal/`.`), 404, 422 |
| POST /api/lobby/join, leave, update_name, save_draft, set_phase, start | `claim_slot`, `release_slot`, `update_slot_name`, `save_draft`, `set_phase`, `start_exploration` | 200, 401 (no id), 404 (leave), 409 (join/start), 400 (name/draft), 422 |
| POST /api/character/create | `create_character` (+`validators`) | 200, 400, 422 |
| POST /api/action/grid | `rules.check_grid_action` + `apply_grid_action`; narration = fallback text only | 200, 400, 409 (phase), 422, **500** (unknown actor; generic interact, see surprises) |
| POST /api/action/interact_entity, /travel | NPC descriptor lookup; `fast_travel` | 200, 404, 409, 500, 422 |
| POST /api/enemy/{id}/attack, GET /api/enemy/room/{id} | `enemies.resolve_*`, `attack_enemy` | 200, 400, 404, 409, 422 |
| POST /api/state/trigger_paradox | `trigger_paradox` | 200 |

- Non-JSON 500: FastAPI returns text `Internal Server Error`; fixtures store it as `{"status":500,"text":...}`.
- Out of the interface (ENCOUNTER/AI/AUTH): D2 needs explicit stubs - `auth/desktop_login` -> 200 `{"status":"ok"}`,
  `action/freeform` -> 200 `{"narrative": "..."}`, `/npc/**` -> either unported-501 or a canned `{"flavor": ...}`.

## 5. Behaviours that would make an offline backend differ (summary; see also the notes file)

1. Plain `move` response is discarded by the client; visibility depends on a state push that, with cookie-less ws,
   likely never arrives in the HTTP build. Local backend must push `state_changed` itself.
2. Generic `interact` (empty floor/enemy cell) and unknown `actor_id` produce HTTP **500** after/without a commit
   (`routes_action.py:28,52-54`); see `exploration.json` steps 14, 20, 23. A faithful port replays the 500 and, for
   generic interact, the state mutation (revision bump + `state_diff`) that happened before it.
3. 422 bodies carry `detail` as a list; client code expects a string (`PythonClient.gd:297,312`).
4. `jon/buy` returns 200 for a failed purchase.
5. Title screen requires AUTH success; healthz loop never gives up.
6. `time/sync` is called from an autoload before any campaign exists; the server must tolerate it at any phase.
