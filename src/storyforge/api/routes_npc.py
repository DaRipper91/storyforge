"""
NPC interaction endpoints.

All NPC encounter state lives on app.state (session-level) so it resets
automatically when a new campaign is loaded — encounters aren't persisted
to the campaign snapshot.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from storyforge.api.deps import get_state_manager
from storyforge.core.state_manager import StateManager
from storyforge.encounters.shopkeeper_john import (
    EscapeMethod,
    JohnEncounterState,
    SceneGenre,
    ShopkeeperJohn,
)

router = APIRouter(prefix="/api/npc", tags=["npc"])


# ── Helpers ──────────────────────────────────────────────────────

def _get_john(request: Request) -> ShopkeeperJohn:
    if not hasattr(request.app.state, "john_encounter"):
        request.app.state.john_encounter = JohnEncounterState(active=True)
    return ShopkeeperJohn(request.app.state.john_encounter)


def _save_john(request: Request, john: ShopkeeperJohn) -> None:
    request.app.state.john_encounter = john.encounter


# ── Inventory ─────────────────────────────────────────────────────

@router.get("/john/inventory")
async def john_inventory(genre: SceneGenre = SceneGenre.FANTASY):
    """Return John's current stock for the given genre."""
    john = ShopkeeperJohn()
    items = john.get_inventory(genre)
    return {
        "genre": genre,
        "items": [i.model_dump() for i in items],
        "note": "John has not commented on the genre change. He never does.",
    }


# ── Purchase ─────────────────────────────────────────────────────

class BuyRequest(BaseModel):
    actor_id: str
    item_id: str
    genre: SceneGenre = SceneGenre.FANTASY


@router.post("/john/buy")
async def john_buy(
    body: BuyRequest,
    request: Request,
    state: StateManager = Depends(get_state_manager),
):
    """Attempt to purchase an item from John."""
    character = state.current.characters.get(body.actor_id)
    if character is None:
        raise HTTPException(status_code=404, detail=f"character '{body.actor_id}' not found")

    john = _get_john(request)
    diff, message = john.buy_item(character, body.genre, body.item_id)
    _save_john(request, john)

    if diff is None:
        return {"success": False, "message": message}

    await state.apply_diff(diff)
    return {"success": True, "message": message}


# ── Cactus ────────────────────────────────────────────────────────

class CactusRequest(BaseModel):
    is_lewd_or_mocking: bool = False


@router.post("/john/cactus")
async def john_cactus(body: CactusRequest, request: Request):
    """
    Player makes a comment about the cactus.
    Set is_lewd_or_mocking=true if the comment is sexual or mocking in nature.
    """
    john = _get_john(request)
    response = john.handle_cactus_comment(body.is_lewd_or_mocking)
    _save_john(request, john)
    return {
        "john_response": response,
        "cactus_offense_count": john.encounter.cactus_offense_count,
        "john_will_sell": john.john_will_sell,
    }


# ── Escape ────────────────────────────────────────────────────────

class EscapeRequest(BaseModel):
    actor_id: str
    method: EscapeMethod = EscapeMethod.SMOOTH_TALK
    advantage: bool = False
    disadvantage: bool = False


@router.post("/john/escape")
async def john_escape(
    body: EscapeRequest,
    request: Request,
    state: StateManager = Depends(get_state_manager),
):
    """
    Attempt to leave John's store.

    On a bad fail (margin ≤ −5) the response includes psychic damage
    already applied via StateDiff. The party_can_leave flag tells you
    whether further escape attempts are currently gated by the story trap.
    """
    if not _get_john(request).party_can_leave:
        return {
            "success": False,
            "blocked": True,
            "message": (
                "John is mid-sentence. You literally cannot get a word in. "
                "Wait for him to finish. Or don't. He won't notice either way."
            ),
        }

    character = state.current.characters.get(body.actor_id)
    if character is None:
        raise HTTPException(status_code=404, detail=f"character '{body.actor_id}' not found")

    john = _get_john(request)
    result, diff = john.roll_escape_check(
        character, body.method, body.advantage, body.disadvantage
    )
    _save_john(request, john)

    if diff is not None:
        await state.apply_diff(diff)

    return {
        "success": result.success,
        "roll": result.roll,
        "modifier": result.modifier,
        "total": result.total,
        "dc": result.dc,
        "margin": result.margin,
        "method": result.method,
        "ability_used": result.ability_used,
        "psychic_damage": result.psychic_damage,
        "turns_lost": result.turns_lost,
        "party_can_leave": john.party_can_leave,
        "flavor": result.flavor,
    }


# ── Turn tick ─────────────────────────────────────────────────────

@router.post("/john/tick")
async def john_tick(request: Request):
    """Advance John's encounter by one turn (decrements all time-based counters)."""
    john = _get_john(request)
    john.tick_turn()
    _save_john(request, john)
    return {
        "story_trap_active": john.encounter.story_trap_active,
        "story_trap_turns_remaining": john.encounter.story_trap_turns_remaining,
        "john_will_sell": john.john_will_sell,
        "party_can_leave": john.party_can_leave,
    }


# ── State introspection ───────────────────────────────────────────

@router.get("/john/state")
async def john_state(request: Request):
    """Return the full current encounter state (useful for the frontend)."""
    john = _get_john(request)
    return {
        **john.encounter.model_dump(),
        "party_can_leave": john.party_can_leave,
        "john_will_sell": john.john_will_sell,
    }
