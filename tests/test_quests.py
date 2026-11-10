from __future__ import annotations

import asyncio
import json
from unittest.mock import patch

from storyforge.api.routes_enemy import AttackRequest, attack_enemy
from storyforge.api.routes_quests import QuestInteraction, interact_with_quest_npc
from storyforge.core.models import (
    AbilityScores, CharacterSheet, Coord, EvolutionaryState, PredatorRole,
    Race, TurnPhase,
)
from storyforge.core.state_manager import StateError
from storyforge.encounters.enemies import AttackResult
from storyforge.main import app
from storyforge.persistence import snapshot


def _add_test_character(state_manager, position: Coord) -> CharacterSheet:
    character = CharacterSheet(
        id="rook",
        name="Rook",
        player="Test",
        race=Race.VEILBORN,
        evolution_state=EvolutionaryState.PHANTOM,
        predator_role=PredatorRole.STALKER,
        hp_current=12,
        hp_max=12,
        abilities=AbilityScores(STR=15, DEX=14, CON=13, INT=12, WIS=10, CHA=8),
        position=position,
    )
    state_manager.current.characters[character.id] = character
    room = state_manager.current.rooms[state_manager.current.current_room_id]
    room.cells[position.y * room.width + position.x].occupant_id = character.id
    return character


def test_wolfguard_watch_accepts_fights_turns_in_and_persists(fresh_state_manager):
    manager = fresh_state_manager
    manager.current.phase = TurnPhase.EXPLORATION
    manager.current.current_room_id = "keep_courtyard"
    character = _add_test_character(manager, Coord(x=8, y=3))

    async def run_slice():
        accepted = await interact_with_quest_npc(
            "wolfguard_watch",
            QuestInteraction(actor_id=character.id, npc_id="evangeline_wolfholt"),
            manager,
        )
        accepted = json.loads(accepted.body)
        assert accepted["status"] == "active"
        assert "echo hound" in accepted["objective"].lower()

        guaranteed_hit = AttackResult(
            hit=True, roll=15, total=20, damage=8,
            attacker_name="Rook", target_name="Echo Hound", hint="Rook fells the Echo Hound.",
        )
        with patch("storyforge.core.state_manager.resolve_player_attack", return_value=guaranteed_hit):
            defeated = await attack_enemy(
                "echo_hound_01", AttackRequest(actor_id=character.id), manager,
            )
        assert defeated["enemy_died"] is True
        assert defeated["quest_update"]["status"] == "ready_to_turn_in"

        keep = manager.current.rooms["ironhold_keep"]
        manager.current.current_room_id = "ironhold_keep"
        character.position = Coord(x=7, y=3)
        keep.cells[3 * keep.width + 7].occupant_id = character.id
        turned_in = await interact_with_quest_npc(
            "wolfguard_watch",
            QuestInteraction(actor_id=character.id, npc_id="bryttan_wolfholt"),
            manager,
        )
        turned_in = json.loads(turned_in.body)
        assert turned_in["status"] == "completed"
        assert turned_in["reward_xp"] == 75
        assert any(item.id == "wolfguard_watch_mark" for item in character.inventory)

        xp_after_turn_in = character.evolution_points
        repeated = await interact_with_quest_npc(
            "wolfguard_watch",
            QuestInteraction(actor_id=character.id, npc_id="bryttan_wolfholt"),
            manager,
        )
        repeated = json.loads(repeated.body)
        assert repeated["status"] == "completed"
        assert character.evolution_points == xp_after_turn_in
        assert sum(item.id == "wolfguard_watch_mark" for item in character.inventory) == 1

    asyncio.run(run_slice())

    saved = snapshot.load(manager._campaign_dir)
    assert saved.quest_progress["wolfguard_watch"].status.value == "completed"
    assert any(item.id == "wolfguard_watch_mark" for item in saved.characters[character.id].inventory)


def test_quest_requires_nearby_npc_and_correct_quest_giver(fresh_state_manager):
    manager = fresh_state_manager
    manager.current.phase = TurnPhase.EXPLORATION
    manager.current.current_room_id = "keep_courtyard"
    character = _add_test_character(manager, Coord(x=1, y=1))

    async def check_rules():
        try:
            await manager.interact_quest(character.id, "wolfguard_watch", "evangeline_wolfholt")
        except StateError as exc:
            assert "too far" in str(exc)
        else:
            raise AssertionError("distant quest NPC interaction was accepted")

        manager.current.current_room_id = "ironhold_keep"
        keep = manager.current.rooms["ironhold_keep"]
        character.position = Coord(x=7, y=3)
        keep.cells[3 * keep.width + 7].occupant_id = character.id
        before_acceptance = await manager.interact_quest(
            character.id, "wolfguard_watch", "bryttan_wolfholt",
        )
        assert before_acceptance["status"] == "available"
        assert "Evangeline" in before_acceptance["message"]

    asyncio.run(check_rules())


def test_quest_route_is_in_openapi():
    assert "/api/quests/{quest_id}/interact" in app.openapi()["paths"]
