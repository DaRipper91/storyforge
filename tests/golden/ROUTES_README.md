# Route-level golden fixtures

Recorded from the real FastAPI app (`storyforge.main.app`) by `tools/golden/record_routes.py`, replayed by
`tests/test_golden_routes.py`. Where the function-level fixtures (`tests/golden/README.md`) pin the core modules,
these pin the **HTTP behaviour the Godot client sees** so a GDScript `LocalBackend` can replay them. Contract
and route classification: `docs/offline/CLIENT_BACKEND_CONTRACT.md`.

    uv run python tools/golden/record_routes.py     # rewrites tests/golden/routes/*.json
    uv run pytest tests/test_golden_routes.py -q    # replay + byte-identical re-record

Only CORE routes are covered. Gemini is stubbed (see `ai_stubs` in each file); no network, no `data/campaigns/`
(the app runs against a temp dir that is deleted afterwards; the lifespan hook is NOT run).

## Flow file shape (`format: "storyforge-route-flow/1"`)

```json
{
  "format": "storyforge-route-flow/1",
  "flow": "enemy_combat",
  "description": "...",
  "covers": ["POST /api/enemy/{enemy_id}/attack", "..."],
  "ai_stubs": ["narrator.narrate_movement -> raises; grid move uses fallback text", "..."],
  "initial": {"seed": "data/seeds/default_campaign.json",
              "main_campaign_dir": "family_campaign_01", "saved_campaigns": []},
  "steps": [
    {
      "n": 7,
      "name": "attack: hit, enemy hits back",
      "pre": [],                                    // environment actions before the request; only "freeze_mtimes"
      "request":  {"method": "POST", "path": "/api/enemy/bandit_01/attack",
                   "query": {}, "json": {"actor_id": "rook"}},
      "rng_script": {"randint": [15, 3, 18, 2]},    // input: values handed out in call order
      "rng_bounds": [[1, 20], [1, 6], [1, 20], [1, 6]],   // output: [lo, hi] of each randint actually made
      "response": {"status": 200, "json": {"...": "..."}},   // or {"status": 500, "text": "Internal Server Error"}
      "events":   [{"type": "state_diff", "revision": 8, "diff": {"...": "..."}}],  // event-bus messages published during the request
      "state_after": {...}                          // present on POST steps (and steps flagged snap); see below
    }
  ]
}
```

- A flow starts from a **fresh** `StateManager` built from the seed; nothing is saved on disk until the first
  mutating request commits (mirrors `main.lifespan` on a first boot). Steps run strictly in order and share state.
- `request.json` is `null` when no body is sent. `query` is `{}` for every CORE route today.
- `response.json` is the parsed body; non-JSON bodies (FastAPI's 500 page) are `{"status", "text"}`.
- `events` are the exact messages the real `event_bus` fanned out (what the websocket would have sent):
  `state_diff` (`revision`, nested `diff` = the mutator's summary) or `state_updated` (`time/sync`).
- `state_after` is `GET /api/state` taken right after the step, trimmed: `rooms` holds only rooms that differ from
  the seed's, and `unchanged_rooms` lists the ids omitted. `{"same_as_previous": true}` means the (trimmed) state
  equals the previous snapshot (failed requests must not mutate). The first comparison base is the seed state.
  Full-state *responses* (`GET /api/state`, `campaigns/new|load`) are stored untrimmed.

## Determinism

- **RNG** - `golden_lib.ScriptedRandom` replaces `random` in `encounters.enemies` and `secrets` in
  `character_factory`. Each step gets its own script `rng_script = {"randint": [...], "token_hex": [...]}` (same
  keys as the function-level fixtures). Every `randint` value must lie inside the bounds the code asks for; the
  actual bounds are recorded in `rng_bounds`. A step fails (recorder and test) if the script is exhausted, a value is
  out of range, or values are left over - so a port must consume **exactly** the recorded sequence.
  Typical sequences: attack = `[d20, weapon die (hit only), (second die on 20)] + [enemy d20, enemy die (hit)]` unless
  the enemy dies; character-id collisions consume one `token_hex`.
- **Clock** - `datetime` in `state_manager` and `routes_state` is frozen at `2026-01-01T12:00:00+00:00`
  (so `campaign_20260101_120000`, narrative timestamps). One `campaigns/new` per flow (id would collide).
- **File mtimes** - `GET /api/campaigns` reports `last_modified` (= `state.json` mtime) and sorts by it. Steps with
  `"pre": ["freeze_mtimes"]` set every saved campaign's mtime to `1700000000 + index` (campaign dirs sorted by name)
  before the request. A GDScript store must mimic that or ignore `last_modified`/ordering for this step.
- **Paths** - temp dirs never appear in fixtures; error messages only carry campaign ids.

## Flows and covered routes

| Flow | Routes covered | Notable behaviours pinned |
|---|---|---|
| `boot_reads` | GET `/api/state`, `/api/revision`, `/api/lobby/catalog`, `/api/campaigns`, `/api/enemy/room/{id}` | catalog shape, empty campaign list, unknown room -> 200 with empty enemies |
| `lobby_slots` | POST `/api/lobby/join`, `leave`, `update_name`, `save_draft`, `set_phase`, `start` | idempotent join, 5th join 409, missing id 401, leave 404, 422 shapes, draft stores unvalidated values, phase reverts when lobby empties |
| `character_creation` | join, set_phase, POST `/api/character/create`, `/api/lobby/start`, leave, GET `/api/state` | bad array 400, range/enum/length 422, wrong phase 400, unclaimed/READY slot 400, duplicate name -> `rook_<token_hex>`, start 409 twice, leave READY removes character |
| `exploration` | POST `/api/action/grid`, `/api/action/interact_entity`, `/api/action/travel`, set_phase | legal near/far moves, self/NPC/wall/table/path blocked 400, OOB 400, negative 422, wrong phase 409, **500** for unknown actor and for generic interact (after committing), NPC encounter descriptor, adjacency rule |
| `enemy_combat` | POST `/api/enemy/{id}/attack`, GET `/api/enemy/room/{id}`, travel | miss/hit/counter, no room or range check, kill (+XP, cell cleared), dead 409, unknown enemy 404, unknown actor 400 |
| `world_travel` | POST `/api/action/travel`, `/api/action/grid` (door interact), GET state | travel works in LOBBY with no characters, unknown room 404, same-room re-spawn, door transition response |
| `campaigns` | GET `/api/campaigns`, POST `/api/campaigns/new`, `/api/campaigns/load`, join, GET state | real persistence round trip, traversal/`.` 400, unknown 404, 422 |
| `paradox_time` | POST `/api/time/sync`, `/api/state/trigger_paradox`, GET `/api/revision` | schedule-driven `target_position`, revision bump only on change, `state_updated` event, paradox on `before`-era characters |

Not recorded (not CORE): `/api/healthz` (INFRA), websocket (INFRA), `/api/auth/*` (AUTH),
`/api/action/freeform` (AI), `/api/npc/**` (ENCOUNTER, partly AI-optional).
