# Golden fixtures (Python backend -> GDScript port)

Deterministic recordings of the Python implementation. A GDScript test runner
replays the same files against the port; `tests/test_golden.py` replays them
against Python so the fixtures can never drift from the code.

## Regenerate / verify

```
uv run python tools/golden/record_fixtures.py   # rewrite tests/golden/fixtures/**
uv run pytest -q tests/test_golden.py            # replay + determinism check
```

Output is byte-identical across runs: keys sorted, fixed layout (2-space
indent; any object/array whose compact form is <= 640 chars is collapsed onto
one line, long arrays of tiny items such as grid cells are packed ~120 cols),
trailing newline, no timestamps/uuids/absolute paths. `test_golden.py` also
re-runs the recorder in memory and asserts it equals the committed files, so a
stale or hand-edited fixture fails CI. The shared runner is
`tools/golden/golden_lib.py` (dispatch + RNG/clock/persistence patching).

## File layout and format

`tests/golden/fixtures/<module>/<function>__<case>.json`, one case per file:

```json
{
  "module": "enemies",
  "function": "resolve_player_attack",
  "case": "resolve_player_attack__hit_d8_mid_roll",
  "inputs": { ... },
  "rng_script": {"random": [], "randint": [10, 4], "choice_index": [],
                 "token_hex": [], "randint_bounds": [[1, 20], [1, 8]]},
  "expected": { ... }  |  {"raises": "IndexError", "message_contains": "out of bounds"}
}
```

- `expected` is whatever the function returned, as JSON. Pydantic models are
  `model_dump(mode="json")` (enums as their string values, tuples as arrays,
  e.g. `cell_updates` entries are `[room_id, {x,y}, {terrain,occupant_id}]`).
  `AttackResult` (dataclass) is `asdict`. A function that returns `None`
  records only what the test harness observes (see state_manager below).
- An error fixture has exactly the keys `raises` (exception class name) and
  `message_contains` (substring of `str(exc)`; not the full message).
  A port should raise/return an error of the equivalent kind; the message
  substring is the stable part of the contract.
- `rules` and `validators` never raise for bad actions: denials/rejections are
  ordinary `expected` values (`{"ok": false, "reason": ...}`,
  `{"diff": ..., "rejections": [...]}`).

### Per-module `inputs` / `expected`

| module | inputs | expected |
|---|---|---|
| grid | `room`, `coord` / `a`,`b` / `cell` / `start`,`end` (as the function's args, models as JSON) | return value; `set_cell` returns `{"room": <room after>}` |
| rules | `state` (full GameState JSON), `char_id`, `action` (GridAction) | `{"ok": bool, "reason": str}` |
| validators | `state`, `diff` (StateDiff JSON) | `{"diff": <safe StateDiff>, "rejections": [str]}` |
| character_factory | kwargs of the function (`build_character` takes `game_state` = full GameState JSON; enum args as strings; `abilities` as `{STR,..}`) | CharacterSheet / bool / str / Coord / EnemySheet JSON |
| enemies | `attacker`+`target` (CharacterSheet / EnemySheet JSON), `enemy`+`target`, `notation`, `score`, `char` | AttackResult dict, int, or str |
| state_manager | `state` (full GameState JSON before) + `args` (method kwargs: ids, action, diff, request, ...) | `{"result": <dict returned by the method>, "state": <full GameState JSON after>}` |

For state_manager the manager is built from `state`; the replay calls the
method (async methods are run to completion) and compares the returned dict
and the entire resulting state, including `revision`.

## RNG-script convention

Python's `random` (in `storyforge.encounters.enemies`) and `secrets.token_hex`
(in `character_factory`) are replaced by a scripted stand-in that pops the
next value from the list for the call it receives:

- `randint`: values for successive `random.randint(a, b)` calls, in call
  order. `randint_bounds` records the `[a, b]` actually passed to each call
  (the port must make the same calls with the same bounds in the same order:
  this pins the number of dice rolled, e.g. crit = two extra weapon dice).
  The runner asserts each scripted value lies within its bounds.
- `token_hex`: strings returned by successive `secrets.token_hex(2)` calls.
- `random` (floats) and `choice_index` (index into the sequence given to
  `random.choice`) are supported by the harness but no covered function
  currently calls them; they are always `[]`.
- The script must be consumed **exactly**; leftover or exhausted values fail.
  A fixture whose function takes no randomness has all-empty lists.

## Time, persistence, events

Only the recorder/replay patches these (src/ is untouched):
`state_manager.dt` -> fixed clock `2026-01-01T12:00:00+00:00` (all
`NarrativeEntry.timestamp` values), `state_manager.snapshot` -> no-op save,
`state_manager.event_bus` -> no-op publish. `_commit()` still runs, so
`revision` increments are part of the expected state.

## State fixtures: what was trimmed

The seed (`data/seeds/default_campaign.json`, 187 KB) is cut to a *trimmed
base state*: rooms `back_alley` (current, 12x8) and, only when a case needs
a transition, `market_square` (14x10); enemies `bandit_01`, `thug_01`; no
NPCs (cases add one where needed); empty narrative log; `revision` 1; phase
`exploration`; era `after`. Two characters (`alpha` ironfast/behemoth/vanguard,
`beta` veilborn/phantom/stalker) are made with `build_character` and `beta` is
parked at (9,1). Long flavour text (room/enemy descriptions, item `notes`) is
blanked purely to save space. Lobby/creation cases clear the characters. The
largest state fixture is ~27 KB; whole tree ~3.3 MB.
Character-factory cases use an 8x8 walled room (`mini`).

## Functions covered

| module | function | cases | notes |
|---|---|---|---|
| grid | cell_index, get_cell, set_cell, in_bounds | 4, 8, 4, 6 | out-of-bounds IndexError |
| grid | chebyshev_distance, feet_between | 6, 6 | |
| grid | is_traversable, movement_cost_feet | 9, 9 | every TerrainKind, occupied cells |
| grid | line_coords, path_is_clear | 8, 9 | `FEET_PER_CELL`=5 constant implicit |
| rules | check_grid_action (+ `_check_move`, `_check_interact`) | 26 | move legal/OOB/wall/table/pillar/occupied/self/budget/path; phases lobby/creation/exploration/combat; attack denied; interact adjacency |
| validators | sanitize (+ all `_filter_*` helpers) | 53 | every rejection message and acceptance path |
| character_factory | build_character | 30 | 25 valid (all 5 race groups, all 4 states and 4 roles >= 2x, customisation variants) + bad array x3, unknown race, odd start cell |
| character_factory | is_valid_standard_array, generate_char_id, find_starting_position, build_race_enemy | 4, 7, 9, 10 | `secrets.token_hex` scripted |
| enemies | resolve_player_attack, resolve_enemy_attack | 17, 11 | hit/miss/exact AC/nat 20/nat 1/default d6/dead target/dice forms |
| enemies | `_roll_dice`, `_mod`, `_weapon_dice` (private helpers) | 14, 9, 2 | dice parsing edge cases |
| state_manager | set_phase, get_character | 5, 2 | |
| state_manager | attack_enemy | 12 | hit/miss/crit/kill+xp/cell vacate/counter/clamp/errors |
| state_manager | apply_grid_action | 19 | move (explore vs combat), interact (enemy/NPC/legacy `npc_` prefix/door exit/generic), denials |
| state_manager | apply_diff | 17 | each section, unknown ids, unsanitized quirks |
| state_manager | fast_travel, transition_room | 4, 4 | spawn placement, unknown room |
| state_manager | append_narration | 5 | fixed timestamp; no revision bump |
| state_manager | claim_slot, update_slot_name, save_draft, release_slot | 6, 3, 3, 4 | lobby |
| state_manager | create_character, start_exploration, trigger_paradox | 6, 4, 3 | creation flow, token-hex id collision |

Total 358 fixtures: character_factory 60, enemies 53, grid 69, rules 26,
state_manager 97, validators 53.

## Not covered / nondeterministic / out of scope

- Persistence (`persistence/snapshot.py`) and `EventBus` fan-out: stubbed, not recorded.
- `StateManager.__init__`, `current`, `_commit` are exercised only indirectly.
- Real `random`/`secrets` values: only scripted values are ever recorded;
  production nondeterminism is therefore not tested (by design).
- `datetime.now()` in `append_narration`, `start_exploration`,
  `trigger_paradox`: frozen to the fixed clock above.
- Other encounters (`queen_danna.py`, NPC/shop handlers, routes, Gemini
  client/prompts) are not part of this step.
- `build_character` for the other ~535 race/state/role combinations (sampled).
- Pydantic input validation errors (e.g. negative `Coord`) are model-layer
  behaviour, not the functions under test, so none are recorded.
