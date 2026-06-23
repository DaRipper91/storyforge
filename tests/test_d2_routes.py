import pytest
from unittest.mock import patch
from fastapi import HTTPException
from pathlib import Path

from storyforge.core.models import GameState, CharacterSheet, EnemySheet, Race, EvolutionaryState, PredatorRole, AbilityScores, Coord, TurnPhase
from storyforge.core.state_manager import StateManager
from storyforge.api.routes_d2 import learn_skill, roll_loot, LearnSkillRequest

@pytest.fixture
def state_manager(tmp_path):
    # Set up dummy state
    state = GameState(
        campaign_id="test_campaign",
        current_room_id="room_1",
        phase=TurnPhase.EXPLORATION,
        rooms={
            "room_1": {
                "id": "room_1",
                "name": "Room 1",
                "width": 5,
                "height": 5,
                "cells": [{"terrain": "floor", "occupant_id": None} for _ in range(25)],
                "description": "A testing room."
            }
        },
        characters={
            "test_char": CharacterSheet(
                id="test_char",
                name="Hero",
                player="Player",
                race=Race.ASHENBORN,
                evolution_state=EvolutionaryState.BEHEMOTH,
                predator_role=PredatorRole.STALKER,
                hp_current=50,
                hp_max=50,
                armor_class=10,
                speed=30,
                abilities=AbilityScores(STR=15, DEX=14, CON=13, INT=12, WIS=10, CHA=8),
                position=Coord(x=0, y=0),
                inventory=[]
            )
        },
        enemies={
            "test_enemy": EnemySheet(
                id="test_enemy",
                name="Minion",
                room_id="room_1",
                position=Coord(x=1, y=1),
                hp_current=1, # low hp to guarantee a kill in one hit
                hp_max=10,
                xp_reward=1000, # Large reward to trigger level up
                alive=True
            )
        }
    )
    
    return StateManager(state, Path(tmp_path))

@pytest.mark.asyncio
async def test_roll_loot(state_manager):
    # Call roll_loot route function directly
    data = await roll_loot(char_id="test_char", rarity_tier="magic", state=state_manager)
    assert data["type"] == "loot_rolled"
    assert "item" in data
    assert data["item"]["rarity"] == "magic"
    assert len(data["item"]["affixes"]) == 1

@pytest.mark.asyncio
async def test_learn_skill_validation(state_manager):
    # Try learning with 0 skill points
    with pytest.raises(HTTPException) as exc_info:
        await learn_skill(char_id="test_char", req=LearnSkillRequest(skill_id="shadow_strike"), state=state_manager)
    assert exc_info.value.status_code == 400
    assert "No unspent skill points" in exc_info.value.detail

@pytest.mark.asyncio
async def test_enemy_defeat_and_level_up(state_manager):
    # Patch random.randint to always return 20 (guaranteed crit/hit/kill)
    with patch("random.randint", return_value=20):
        result = await state_manager.attack_enemy("test_char", "test_enemy")
        assert result["enemy_died"] is True
    
    # Verify character stats after level up
    char_data = state_manager.current.characters["test_char"]
    assert char_data.level == 2
    assert char_data.unspent_skill_points == 1
    
    # Learn skill now that we have a point
    response = await learn_skill(char_id="test_char", req=LearnSkillRequest(skill_id="shadow_strike"), state=state_manager)
    assert response["points_spent"] == 1
    assert response["unspent_skill_points"] == 0
