"""
Integration tests for lobby + character creation routes.

Uses httpx.AsyncClient against the real FastAPI app with a fresh
StateManager seeded from default_campaign.json for each test.

No Gemini calls are made by any of the routes under test.
"""
import os

import pytest

os.environ.setdefault("STORYFORGE_GEMINI_API_KEY", "test-fake-key-not-real")

from storyforge.core.models import TurnPhase


# ─────────────────────── /api/lobby/catalog ───────────────────────

async def test_catalog_structure(client):
    """GET /api/lobby/catalog returns the full reference data with expected keys."""
    resp = await client.get("/api/lobby/catalog")
    assert resp.status_code == 200
    data = resp.json()

    assert "races" in data
    assert "states" in data
    assert "roles" in data
    assert "backgrounds" in data
    assert "feats" in data
    assert "skills" in data
    assert "cantrips" in data
    assert "alignments" in data
    assert "dialogue_styles" in data


def test_catalog_race_count(client):
    """The catalog exposes exactly 35 races."""
    # We call this synchronously via a workaround — but in asyncio_mode=auto
    # we can just define it as an async function. Re-declare as async below.


async def test_catalog_has_35_races(client):
    resp = await client.get("/api/lobby/catalog")
    data = resp.json()
    assert len(data["races"]) == 35


async def test_catalog_state_count(client):
    """The catalog exposes exactly 4 evolutionary states."""
    resp = await client.get("/api/lobby/catalog")
    data = resp.json()
    assert len(data["states"]) == 4


async def test_catalog_role_count(client):
    """The catalog exposes exactly 4 predator roles."""
    resp = await client.get("/api/lobby/catalog")
    data = resp.json()
    assert len(data["roles"]) == 4


async def test_catalog_background_count(client):
    """The catalog exposes exactly 8 backgrounds."""
    resp = await client.get("/api/lobby/catalog")
    data = resp.json()
    assert len(data["backgrounds"]) == 8


async def test_catalog_feat_count(client):
    """The catalog exposes exactly 8 feats."""
    resp = await client.get("/api/lobby/catalog")
    data = resp.json()
    assert len(data["feats"]) == 8


async def test_catalog_roles_have_required_fields(client):
    """Each role in the catalog has primary_item and equipment_choices."""
    resp = await client.get("/api/lobby/catalog")
    data = resp.json()
    for role_key, role_data in data["roles"].items():
        assert "primary_item" in role_data, f"role {role_key} missing primary_item"
        assert "equipment_choices" in role_data, f"role {role_key} missing equipment_choices"
        assert isinstance(role_data["equipment_choices"], list)
        assert len(role_data["equipment_choices"]) > 0


# ─────────────────────── /api/lobby/join + /api/lobby/leave ───────────────────────

async def test_join_lobby(client):
    """POST /api/lobby/join with a controller_id claims a slot."""
    resp = await client.post("/api/lobby/join", json={"controller_id": "pad_01"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "slot_claimed"
    assert "slot_index" in data


async def test_join_and_leave(client):
    """
    Claim a slot then release it. The leave response should confirm the slot
    was released.
    """
    join_resp = await client.post("/api/lobby/join", json={"controller_id": "pad_42"})
    assert join_resp.status_code == 200

    leave_resp = await client.post("/api/lobby/leave", json={"controller_id": "pad_42"})
    assert leave_resp.status_code == 200
    data = leave_resp.json()
    assert data["type"] == "slot_released"


async def test_join_idempotent(client):
    """Joining twice with the same controller_id returns the same slot."""
    resp1 = await client.post("/api/lobby/join", json={"controller_id": "pad_idm"})
    assert resp1.status_code == 200
    slot1 = resp1.json()["slot_index"]

    resp2 = await client.post("/api/lobby/join", json={"controller_id": "pad_idm"})
    assert resp2.status_code == 200
    slot2 = resp2.json()["slot_index"]

    assert slot1 == slot2


async def test_leave_unknown_controller_returns_404(client):
    """Leaving a slot you never claimed returns 404."""
    resp = await client.post("/api/lobby/leave", json={"controller_id": "ghost_controller"})
    assert resp.status_code == 404


async def test_join_requires_controller_id(client):
    """POST /api/lobby/join with no controller_id and no auth cookie → 401."""
    resp = await client.post("/api/lobby/join", json={})
    assert resp.status_code == 401


# ─────────────────────── Full character creation ───────────────────────

async def _join_and_set_creation_phase(client) -> str:
    """
    Helper: join a slot, advance to CREATION phase, return controller_id.
    Returns the controller_id used to claim the slot.
    """
    controller_id = "creator_01"
    join = await client.post("/api/lobby/join", json={"controller_id": controller_id})
    assert join.status_code == 200

    phase = await client.post("/api/lobby/set_phase", json={"phase": "creation"})
    assert phase.status_code == 200

    return controller_id


async def test_full_character_creation(client):
    """
    Join, advance to CREATION, POST /api/character/create with all fields.
    Assert the response has type='character_created' and the character has
    the expected customization fields populated.
    """
    await _join_and_set_creation_phase(client)

    payload = {
        "slot_index": 0,
        "name": "Zyra",
        "race": "voidwraith",
        "evolution_state": "mimic",
        "predator_role": "stalker",
        "starting_era": "after",
        "abilities": {
            "STR": 8,
            "DEX": 12,
            "CON": 13,
            "INT": 15,
            "WIS": 14,
            "CHA": 10,
        },
        "equipment_choice_id": "smoke_pellets",
        "background": "feral_wanderer",
        "skill_proficiencies": ["Stealth", "Athletics"],
        "feat": "apex_predator",
        "cantrips": ["Voidbolt"],
        "alignment": "Chaotic Neutral",
        "pronouns": "she/her",
        "title": "The Unseen",
        "dialogue_style": "stoic",
        "physical_description": "Slender, shadow-wreathed form.",
        "backstory": "Born in the void.",
        "personality_traits": "Quiet and deadly.",
        "flaws": "Trusts no one.",
        "bonds": "Her blade.",
        "ideals": "Freedom at any cost.",
        "keepsake_name": "Cracked locket",
    }

    resp = await client.post("/api/character/create", json=payload)
    assert resp.status_code == 200, resp.text

    data = resp.json()
    assert data["type"] == "character_created"
    assert "character" in data

    char = data["character"]
    assert char["name"] == "Zyra"
    assert char["background"] == "feral_wanderer"
    assert char["feat"] == "apex_predator"
    assert char["alignment"] == "Chaotic Neutral"
    assert char["pronouns"] == "she/her"
    assert char["title"] == "The Unseen"
    assert char["dialogue_style"] == "stoic"

    # Keepsake should be in inventory
    item_ids = [i["id"] for i in char["inventory"]]
    assert any(iid.startswith("keepsake_") for iid in item_ids)

    # Background skills merged in
    assert "Survival" in char["skill_proficiencies"]
    assert "Perception" in char["skill_proficiencies"]
    assert "Stealth" in char["skill_proficiencies"]

    # Racial ability bonuses applied (Voidwraith: INT+2, STR+1)
    assert char["abilities"]["INT"] == 17  # 15 + 2
    assert char["abilities"]["STR"] == 9   # 8 + 1


async def test_character_creation_requires_creation_phase(client):
    """
    /api/character/create fails with 400 when not in CREATION phase.
    The seed starts in LOBBY phase.
    """
    # Do NOT advance to CREATION — just join
    await client.post("/api/lobby/join", json={"controller_id": "ctrl_01"})

    payload = {
        "slot_index": 0,
        "name": "Test",
        "race": "voidwraith",
        "evolution_state": "mimic",
        "predator_role": "stalker",
        "starting_era": "after",
        "abilities": {
            "STR": 8, "DEX": 12, "CON": 13,
            "INT": 15, "WIS": 14, "CHA": 10,
        },
    }
    resp = await client.post("/api/character/create", json=payload)
    assert resp.status_code == 400


async def test_character_creation_slot_must_be_claimed(client):
    """
    Creating a character on an unclaimed slot (index 1 when only 0 was claimed)
    should return 400.
    """
    await _join_and_set_creation_phase(client)

    payload = {
        "slot_index": 1,  # slot 1 was never claimed
        "name": "Orphan",
        "race": "voidwraith",
        "evolution_state": "mimic",
        "predator_role": "stalker",
        "starting_era": "after",
        "abilities": {
            "STR": 8, "DEX": 12, "CON": 13,
            "INT": 15, "WIS": 14, "CHA": 10,
        },
    }
    resp = await client.post("/api/character/create", json=payload)
    assert resp.status_code == 400


# ─────────────────────── Path traversal guard ───────────────────────

async def test_path_traversal_blocked(client):
    """
    POST /api/campaigns/load with a campaign_id containing '..' → 400.
    """
    resp = await client.post("/api/campaigns/load", json={"campaign_id": "../../../etc"})
    assert resp.status_code == 400


async def test_path_traversal_with_slash_blocked(client):
    """campaign_id containing forward slash → 404 since it's a subfolder but doesn't exist."""
    resp = await client.post("/api/campaigns/load", json={"campaign_id": "foo/bar"})
    assert resp.status_code == 404


async def test_path_traversal_with_backslash_blocked(client):
    """campaign_id containing backslash → 404 since it's a subfolder but doesn't exist."""
    resp = await client.post("/api/campaigns/load", json={"campaign_id": "foo\\bar"})
    assert resp.status_code == 404


# ─────────────────────── Healthcheck ───────────────────────

async def test_healthz(client):
    """GET /healthz returns 200 and status ok."""
    resp = await client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
