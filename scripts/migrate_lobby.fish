# ─── 1. Schema accepts the new phases ──────────────────────────
uv run python -c "
from storyforge.core.models import GameState, TurnPhase
from storyforge.persistence.snapshot import load_seed
s = load_seed()
assert s.phase == TurnPhase.LOBBY, f'expected LOBBY, got {s.phase}'
assert len(s.lobby_slots) == 4, f'expected 4 slots, got {len(s.lobby_slots)}'
assert len(s.characters) == 0, f'expected no characters, got {len(s.characters)}'
print(f'✓ schema accepts new phases, 4 slots seeded, 0 characters')
"

# ─── 2. Character factory builds a sheet ───────────────────────
uv run python -c "
from storyforge.core.character_factory import build_character
from storyforge.core.models import AbilityScores, Coord, Race, CharClass

sheet = build_character(
    char_id='test_01', player='test', name='Testarossa',
    race=Race.ELF, char_class=CharClass.WIZARD,
    base_abilities=AbilityScores(STR=8, DEX=14, CON=12, INT=15, WIS=13, CHA=10),
    starting_position=Coord(x=3, y=6),
)
print(f'✓ built {sheet.name}: {sheet.char_class} (DEX={sheet.abilities.DEX}, INT={sheet.abilities.INT}, HP={sheet.hp_max})')
# Expected: DEX 16 (14+2 elf), INT 16 (15+1 elf), HP 7 (d6=6 + CON mod 1)
"

# ─── 3. Boot the dev server, hit the catalog ───────────────────
./scripts/dev.fish &
sleep 2
curl -sf http://127.0.0.1:8765/api/lobby/catalog | jq '.races | keys, .classes | keys'
# Expected: arrays containing race and class keys

# ─── 4. Full lobby-join → create → start round-trip ────────────
# Join:
curl -sf -X POST http://127.0.0.1:8765/api/lobby/join \
    -H "Content-Type: application/json" \
    -d '{"controller_id": "test::1"}' | jq
# Expected: slot_index 0, phase "creation"

# Create:
curl -sf -X POST http://127.0.0.1:8765/api/character/create \
    -H "Content-Type: application/json" \
    -d '{"slot_index": 0, "name": "Testarossa", "race": "elf",
         "char_class": "wizard",
         "abilities": {"STR": 8, "DEX": 14, "CON": 12, "INT": 15, "WIS": 13, "CHA": 10}}' | jq
# Expected: character_id, character object

# Start:
curl -sf -X POST http://127.0.0.1:8765/api/lobby/start | jq
# Expected: phase "exploration", character_count 1

# Verify final state:
curl -sf http://127.0.0.1:8765/api/state | jq '.phase, (.characters | length)'
# Expected: "exploration", 1

# ─── 5. Action routes reject when not in exploration ───────────
# (Reset the seed first: rm data/campaigns/family_campaign_01/state.json && restart)
curl -i -X POST http://127.0.0.1:8765/api/action/grid \
    -H "Content-Type: application/json" \
    -d '{"actor_id": "test", "type": "move", "target": {"x": 1, "y": 1}}'
# Expected: 409 Conflict, detail about phase

# ─── 6. Open the browser ───────────────────────────────────────
xdg-open http://127.0.0.1:8765
# You should see: parchment Lobby screen with 4 dashed slot cards.
# Plug in a controller, press A → first slot lights gold.
# UI transitions to creation screen with 4 step pills at top.
# Walk through race → class → abilities → name with D-pad + A.
# Press Start → exploration view with your character on the grid.
