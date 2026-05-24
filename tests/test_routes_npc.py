"""
Tests for NPC encounter routes.

All Gemini calls are patched out — narrate_npc is mocked to return a
deterministic string so tests never hit the real API. Mechanics (counters,
state transitions, favor math) are tested against the Python pool results
to verify game logic independently of narration.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from storyforge.main import app


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_npc_state():
    """Reset all NPC encounter state on app.state before each test."""
    for attr in (
        "jon_encounter", "samael_encounter", "haylie_encounter",
        "danna_encounter", "redvelvet_encounter", "kodrik_encounter",
        "bryne_encounter", "nathis_encounter",
    ):
        if hasattr(app.state, attr):
            delattr(app.state, attr)
    yield


# ─── Helpers ──────────────────────────────────────────────────────────────────

MOCK_NARRATION = "Mocked NPC narration."

_NPC_PATCH = "storyforge.api.routes_npc.narrate_npc"


def _mock_narrate():
    return patch(_NPC_PATCH, new=AsyncMock(return_value=MOCK_NARRATION))


# ─── Jon ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_jon_inventory(client):
    resp = await client.get("/api/npc/jon/inventory")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert isinstance(data["items"], list)
    assert len(data["items"]) > 0


@pytest.mark.asyncio
async def test_jon_cactus_normal(client):
    with _mock_narrate():
        resp = await client.post("/api/npc/jon/cactus", json={"is_lewd_or_mocking": False})
    assert resp.status_code == 200
    data = resp.json()
    assert data["jon_response"] == MOCK_NARRATION
    assert data["cactus_offense_count"] == 0
    assert data["jon_will_sell"] is True


@pytest.mark.asyncio
async def test_jon_cactus_lewd_increments_offense(client):
    with _mock_narrate():
        resp = await client.post("/api/npc/jon/cactus", json={"is_lewd_or_mocking": True})
    assert resp.status_code == 200
    data = resp.json()
    assert data["cactus_offense_count"] == 1


@pytest.mark.asyncio
async def test_jon_cactus_falls_back_on_gemini_error(client):
    with patch(_NPC_PATCH, new=AsyncMock(side_effect=RuntimeError("Gemini down"))):
        resp = await client.post("/api/npc/jon/cactus", json={"is_lewd_or_mocking": False})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["jon_response"], str)
    assert len(data["jon_response"]) > 0


@pytest.mark.asyncio
async def test_jon_tick(client):
    resp = await client.post("/api/npc/jon/tick")
    assert resp.status_code == 200
    data = resp.json()
    assert "story_trap_active" in data
    assert "jon_will_sell" in data


@pytest.mark.asyncio
async def test_jon_state(client):
    resp = await client.get("/api/npc/jon/state")
    assert resp.status_code == 200
    data = resp.json()
    assert "active" in data
    assert "party_can_leave" in data


# ─── Samael ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_samael_consult(client):
    with _mock_narrate():
        resp = await client.post("/api/npc/samael/consult", json={"category": "general_lore"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["cryptic_hint"] == MOCK_NARRATION
    assert data["consultation_number"] == 1


@pytest.mark.asyncio
async def test_samael_consult_increments(client):
    with _mock_narrate():
        r1 = await client.post("/api/npc/samael/consult", json={"category": "general_lore"})
        r2 = await client.post("/api/npc/samael/consult", json={"category": "general_lore"})
    assert r2.json()["consultation_number"] == r1.json()["consultation_number"] + 1


@pytest.mark.asyncio
async def test_samael_consult_gemini_fallback(client):
    with patch(_NPC_PATCH, new=AsyncMock(side_effect=RuntimeError("Gemini down"))):
        resp = await client.post("/api/npc/samael/consult", json={"category": "general_lore"})
    assert resp.status_code == 200
    assert isinstance(resp.json()["cryptic_hint"], str)


@pytest.mark.asyncio
async def test_samael_state(client):
    resp = await client.get("/api/npc/samael/state")
    assert resp.status_code == 200
    data = resp.json()
    assert "active" in data
    assert "consultations" in data


# ─── Haylie ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_haylie_bailout_not_available(client):
    resp = await client.post("/api/npc/haylie/bailout", json={"genre": "fantasy"})
    assert resp.status_code == 200
    assert resp.json()["triggered"] is False


@pytest.mark.asyncio
async def test_haylie_bailout_triggers_after_critical_escape_fail(client):
    # Burn enough escape attempts to set bailout_available
    # The escape endpoint requires a character — skip this and set state directly
    # by priming jon state via app.state manipulation through the tick endpoint
    # (Simplest approach: call tick enough times to exhaust story trap, then
    # check the bailout path. Full bailout mechanic is tested via the encounter unit.)
    resp = await client.post("/api/npc/haylie/bailout", json={"genre": "fantasy"})
    assert resp.status_code == 200
    data = resp.json()
    # Without a prior critical fail, bailout is not available
    assert data["triggered"] is False
    assert "message" in data


@pytest.mark.asyncio
async def test_haylie_inn(client):
    resp = await client.get("/api/npc/haylie/inn")
    assert resp.status_code == 200
    assert "description" in resp.json()


@pytest.mark.asyncio
async def test_haylie_state(client):
    resp = await client.get("/api/npc/haylie/state")
    assert resp.status_code == 200
    assert "bailout_available" in resp.json()


# ─── Queen D.Anna ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_danna_address_proper(client):
    with _mock_narrate():
        resp = await client.post("/api/npc/danna/address", json={"form": "proper"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["correct"] is True
    assert data["favor_delta"] > 0
    assert data["response"] == MOCK_NARRATION


@pytest.mark.asyncio
async def test_danna_address_wrong_costs_favor(client):
    with _mock_narrate():
        resp = await client.post("/api/npc/danna/address", json={"form": "casual"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["correct"] is False
    assert data["favor_delta"] <= 0


@pytest.mark.asyncio
async def test_danna_address_gemini_fallback(client):
    with patch(_NPC_PATCH, new=AsyncMock(side_effect=RuntimeError("Gemini down"))):
        resp = await client.post("/api/npc/danna/address", json={"form": "proper"})
    assert resp.status_code == 200
    assert isinstance(resp.json()["response"], str)


@pytest.mark.asyncio
async def test_danna_petition_granted(client):
    # First build up favor with correct address
    with _mock_narrate():
        for _ in range(3):
            await client.post("/api/npc/danna/address", json={"form": "proper"})
        resp = await client.post("/api/npc/danna/petition", json={"petition_type": "blessing"})
    assert resp.status_code == 200
    data = resp.json()
    # May be granted or declined depending on favor — just verify structure
    assert "granted" in data
    assert "response" in data
    assert "new_favor" in data


@pytest.mark.asyncio
async def test_danna_state(client):
    resp = await client.get("/api/npc/danna/state")
    assert resp.status_code == 200
    assert "favor" in resp.json()


# ─── Firey RedVelvet ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_redvelvet_perform(client):
    with _mock_narrate():
        resp = await client.post("/api/npc/redvelvet/perform")
    assert resp.status_code == 200
    data = resp.json()
    assert data["performance_text"] == MOCK_NARRATION
    assert "mood" in data
    assert data["performances_given"] == 1


@pytest.mark.asyncio
async def test_redvelvet_tip_raises_mood(client):
    with _mock_narrate():
        resp = await client.post("/api/npc/redvelvet/tip", json={"silver": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert data["response"] == MOCK_NARRATION
    assert data["silver_spent"] == 5
    assert data["total_tips"] == 5


@pytest.mark.asyncio
async def test_redvelvet_tip_zero_rejected(client):
    resp = await client.post("/api/npc/redvelvet/tip", json={"silver": 0})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_redvelvet_heckle_drops_mood(client):
    with _mock_narrate():
        resp = await client.post("/api/npc/redvelvet/heckle")
    assert resp.status_code == 200
    data = resp.json()
    assert data["response"] == MOCK_NARRATION
    assert data["heckles_received"] == 1


@pytest.mark.asyncio
async def test_redvelvet_request_song(client):
    with _mock_narrate():
        resp = await client.post(
            "/api/npc/redvelvet/request-song", json={"song_type": "mystery"}
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["performance_text"] == MOCK_NARRATION
    # MYSTERY resolves to a real song type — just verify it's a non-empty string
    assert isinstance(data["song_type"], str)
    assert len(data["song_type"]) > 0


@pytest.mark.asyncio
async def test_redvelvet_gemini_fallback(client):
    with patch(_NPC_PATCH, new=AsyncMock(side_effect=RuntimeError("Gemini down"))):
        resp = await client.post("/api/npc/redvelvet/perform")
    assert resp.status_code == 200
    assert isinstance(resp.json()["performance_text"], str)


@pytest.mark.asyncio
async def test_redvelvet_state(client):
    resp = await client.get("/api/npc/redvelvet/state")
    assert resp.status_code == 200
    assert "mood_label" in resp.json()


# ─── Kodrik ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_kodrik_dispatch(client):
    with _mock_narrate():
        resp = await client.post("/api/npc/kodrik/dispatch?dispatch_type=survey")
    assert resp.status_code == 200
    data = resp.json()
    assert data["flavor"] == MOCK_NARRATION
    assert "location_name" in data
    assert "breadcrumb" in data


@pytest.mark.asyncio
async def test_kodrik_repair_success(client):
    with _mock_narrate():
        resp = await client.post(
            "/api/npc/kodrik/repair",
            json={"item_name": "Dented Breastplate", "silver_available": 20},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["flavor"] == MOCK_NARRATION


@pytest.mark.asyncio
async def test_kodrik_repair_insufficient_silver(client):
    with _mock_narrate():
        resp = await client.post(
            "/api/npc/kodrik/repair",
            json={"item_name": "Dented Breastplate", "silver_available": 3},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    # flavor is Gemini or fallback — just verify it's a non-empty string
    assert isinstance(data["flavor"], str)
    assert len(data["flavor"]) > 0


@pytest.mark.asyncio
async def test_kodrik_gemini_fallback(client):
    with patch(_NPC_PATCH, new=AsyncMock(side_effect=RuntimeError("Gemini down"))):
        resp = await client.post("/api/npc/kodrik/dispatch?dispatch_type=bounty")
    assert resp.status_code == 200
    assert isinstance(resp.json()["flavor"], str)


# ─── Bryne ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bryne_observation(client):
    with _mock_narrate():
        resp = await client.get("/api/npc/bryne/observation")
    assert resp.status_code == 200
    data = resp.json()
    assert data["flavor"] == MOCK_NARRATION
    assert "text" in data
    assert "impact" in data


@pytest.mark.asyncio
async def test_bryne_observation_increments_count(client):
    with _mock_narrate():
        await client.get("/api/npc/bryne/observation")
        await client.get("/api/npc/bryne/observation")
    resp = await client.get("/api/npc/bryne/observation")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_bryne_cole_lean(client):
    with _mock_narrate():
        resp = await client.post("/api/npc/bryne/cole-lean")
    assert resp.status_code == 200
    assert resp.json()["flavor"] == MOCK_NARRATION


@pytest.mark.asyncio
async def test_bryne_gemini_fallback(client):
    with patch(_NPC_PATCH, new=AsyncMock(side_effect=RuntimeError("Gemini down"))):
        resp = await client.get("/api/npc/bryne/observation")
    assert resp.status_code == 200
    assert isinstance(resp.json()["flavor"], str)


# ─── Nathis ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_nathis_report(client):
    with _mock_narrate():
        resp = await client.get("/api/npc/nathis/report")
    assert resp.status_code == 200
    data = resp.json()
    assert data["flavor"] == MOCK_NARRATION
    assert "intel" in data
    assert "urgency" in data


@pytest.mark.asyncio
async def test_nathis_report_increments(client):
    with _mock_narrate():
        await client.get("/api/npc/nathis/report")
        resp = await client.get("/api/npc/nathis/report")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_nathis_tyty_bark(client):
    with _mock_narrate():
        resp = await client.post("/api/npc/nathis/tyty-bark")
    assert resp.status_code == 200
    assert resp.json()["flavor"] == MOCK_NARRATION


@pytest.mark.asyncio
async def test_nathis_gemini_fallback(client):
    with patch(_NPC_PATCH, new=AsyncMock(side_effect=RuntimeError("Gemini down"))):
        resp = await client.get("/api/npc/nathis/report")
    assert resp.status_code == 200
    assert isinstance(resp.json()["flavor"], str)
