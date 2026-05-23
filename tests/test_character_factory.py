"""
Tests for storyforge.core.character_factory.

Each test builds a CharacterSheet using build_character() and asserts
specific invariants about the resulting sheet. No I/O is performed —
the GameState is loaded in-memory from the seed file.
"""
import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("STORYFORGE_GEMINI_API_KEY", "test-fake-key-not-real")

from storyforge.core.character_factory import (
    RACES,
    ROLES,
    build_character,
    is_valid_standard_array,
)
from storyforge.core.models import (
    AbilityScores,
    EvolutionaryState,
    GameState,
    PredatorRole,
    Race,
    TurnPhase,
)

_SEED_PATH = Path(__file__).resolve().parents[1] / "data" / "seeds" / "default_campaign.json"


def _seed() -> GameState:
    return GameState.model_validate(json.loads(_SEED_PATH.read_text()))


def _standard_abilities(
    *,
    STR: int = 10,
    DEX: int = 12,
    CON: int = 13,
    INT: int = 14,
    WIS: int = 15,
    CHA: int = 8,
) -> AbilityScores:
    """Return a valid standard-array AbilityScores, with overrides."""
    return AbilityScores(STR=STR, DEX=DEX, CON=CON, INT=INT, WIS=WIS, CHA=CHA)


def _build(
    *,
    race: Race = Race.VOIDWRAITH,
    state: EvolutionaryState = EvolutionaryState.MIMIC,
    role: PredatorRole = PredatorRole.STALKER,
    abilities: AbilityScores | None = None,
    **kwargs,
) -> "storyforge.core.models.CharacterSheet":  # noqa: F821 (forward ref in annotation)
    if abilities is None:
        abilities = _standard_abilities()
    return build_character(
        char_id="test_char",
        name="Tester",
        player="pytest",
        race=race,
        state=state,
        role=role,
        abilities=abilities,
        game_state=_seed(),
        **kwargs,
    )


# ─────────────────────── Racial Ability Bonuses ───────────────────────

def test_racial_ability_bonuses():
    """Voidwraith: INT+2, STR+1. Starting STR=8, INT=14 → STR=9, INT=16."""
    sheet = _build(
        race=Race.VOIDWRAITH,
        abilities=AbilityScores(STR=8, DEX=12, CON=13, INT=14, WIS=15, CHA=10),
    )
    assert sheet.abilities.STR == 9
    assert sheet.abilities.INT == 16


def test_racial_bonus_does_not_affect_other_stats():
    """No unintended spillover to DEX or WIS when building Voidwraith."""
    base = AbilityScores(STR=8, DEX=12, CON=13, INT=14, WIS=15, CHA=10)
    sheet = _build(race=Race.VOIDWRAITH, abilities=base)
    # Only STR and INT should change.
    assert sheet.abilities.DEX == 12
    assert sheet.abilities.CON == 13
    assert sheet.abilities.WIS == 15
    assert sheet.abilities.CHA == 10


# ─────────────────────── Equipment Choice ───────────────────────

def test_equipment_choice_selected():
    """Stalker with equipment_choice_id='smoke_pellets' → Razor Claws + Smoke Pellets."""
    sheet = _build(role=PredatorRole.STALKER, equipment_choice_id="smoke_pellets")
    item_ids = {item.id for item in sheet.inventory}
    assert "razor_claws" in item_ids
    assert "smoke_pellets" in item_ids


def test_equipment_choice_default():
    """Stalker with no equipment_choice_id gets primary + first choice (smoke_pellets)."""
    sheet = _build(role=PredatorRole.STALKER, equipment_choice_id=None)
    item_ids = {item.id for item in sheet.inventory}
    assert "razor_claws" in item_ids
    # First item in STALKER equipment_choices is smoke_pellets.
    first_choice_id = ROLES[PredatorRole.STALKER].equipment_choices[0].id
    assert first_choice_id in item_ids


def test_equipment_choice_grappling_hook():
    """Stalker explicitly choosing grappling_hook gets it instead of smoke_pellets."""
    sheet = _build(role=PredatorRole.STALKER, equipment_choice_id="grappling_hook")
    item_ids = {item.id for item in sheet.inventory}
    assert "grappling_hook" in item_ids
    assert "smoke_pellets" not in item_ids


# ─────────────────────── Background Auto-Skills ───────────────────────

def test_background_auto_skills_merged():
    """
    feral_wanderer grants bonus_skills ("Survival", "Perception").
    If the player also picks "Stealth", all three appear in skill_proficiencies.
    """
    sheet = _build(
        background="feral_wanderer",
        skill_proficiencies=["Stealth"],
    )
    assert "Stealth" in sheet.skill_proficiencies
    assert "Survival" in sheet.skill_proficiencies
    assert "Perception" in sheet.skill_proficiencies


def test_no_duplicate_skills():
    """
    If the player manually picks "Survival" and feral_wanderer also grants
    "Survival", it should appear exactly once.
    """
    sheet = _build(
        background="feral_wanderer",
        skill_proficiencies=["Survival", "Stealth"],
    )
    assert sheet.skill_proficiencies.count("Survival") == 1


def test_no_duplicate_skills_perception():
    """
    Same deduplication check for "Perception" — the other feral_wanderer bonus.
    """
    sheet = _build(
        background="feral_wanderer",
        skill_proficiencies=["Perception", "Athletics"],
    )
    assert sheet.skill_proficiencies.count("Perception") == 1


# ─────────────────────── Keepsake ───────────────────────

def test_keepsake_in_inventory():
    """keepsake_name='Cracked locket' → an item with id starting 'keepsake_' and that name."""
    sheet = _build(keepsake_name="Cracked locket")
    keepsake_items = [i for i in sheet.inventory if i.id.startswith("keepsake_")]
    assert len(keepsake_items) == 1
    assert keepsake_items[0].name == "Cracked locket"


def test_no_keepsake_when_not_provided():
    """When keepsake_name is None, no keepsake item is added."""
    sheet = _build(keepsake_name=None)
    keepsake_items = [i for i in sheet.inventory if i.id.startswith("keepsake_")]
    assert len(keepsake_items) == 0


# ─────────────────────── is_valid_standard_array ───────────────────────

def test_is_valid_standard_array_passes():
    """The canonical standard array [15,14,13,12,10,8] is valid."""
    scores = AbilityScores(STR=15, DEX=14, CON=13, INT=12, WIS=10, CHA=8)
    assert is_valid_standard_array(scores) is True


def test_is_valid_standard_array_any_permutation():
    """Any permutation of [15,14,13,12,10,8] should be valid."""
    scores = AbilityScores(STR=8, DEX=10, CON=12, INT=13, WIS=14, CHA=15)
    assert is_valid_standard_array(scores) is True


def test_is_valid_standard_array_rejects_wrong_values():
    """[15,14,13,12,10,9] is NOT a valid standard array (9 instead of 8)."""
    scores = AbilityScores(STR=15, DEX=14, CON=13, INT=12, WIS=10, CHA=9)
    assert is_valid_standard_array(scores) is False


def test_is_valid_standard_array_rejects_duplicates():
    """[15,14,13,12,10,10] has a duplicate 10, not valid."""
    scores = AbilityScores(STR=15, DEX=14, CON=13, INT=12, WIS=10, CHA=10)
    assert is_valid_standard_array(scores) is False
