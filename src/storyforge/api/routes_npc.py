"""
NPC interaction endpoints.

All NPC encounter state lives on app.state (session-level) so it resets
automatically when a new campaign is loaded — encounters aren't persisted
to the campaign snapshot.

NPCs:
  /api/npc/jon/*     — Jon the shopkeeper (Multiversal Bodega, Cactus, Escape)
  /api/npc/samael/*  — Samael the Ascended (cryptic lore hints)
  /api/npc/haylie/*  — Madame Haylie (bailout from Jon's conversational trap)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from storyforge.api.deps import get_state_manager
from storyforge.core.state_manager import StateManager
from storyforge.encounters.shopkeeper_jon import (
    EscapeMethod,
    JonEncounterState,
    SceneGenre,
    ShopkeeperJon,
)
from storyforge.encounters.samael import (
    LoreCategory,
    SamaelEncounterState,
    SamaelTheDemigod,
)
from storyforge.encounters.haylie import (
    HaylieEncounterState,
    MadameHaylie,
)

router = APIRouter(prefix="/api/npc", tags=["npc"])


# ── Jon helpers ───────────────────────────────────────────────────

def _get_jon(request: Request) -> ShopkeeperJon:
    if not hasattr(request.app.state, "jon_encounter"):
        request.app.state.jon_encounter = JonEncounterState(active=True)
    return ShopkeeperJon(request.app.state.jon_encounter)


def _save_jon(request: Request, jon: ShopkeeperJon) -> None:
    request.app.state.jon_encounter = jon.encounter


# ── Samael helpers ────────────────────────────────────────────────

def _get_samael(request: Request) -> SamaelTheDemigod:
    if not hasattr(request.app.state, "samael_encounter"):
        request.app.state.samael_encounter = SamaelEncounterState(active=True)
    return SamaelTheDemigod(request.app.state.samael_encounter)


def _save_samael(request: Request, samael: SamaelTheDemigod) -> None:
    request.app.state.samael_encounter = samael.encounter


# ── Haylie helpers ────────────────────────────────────────────────

def _get_haylie(request: Request) -> MadameHaylie:
    if not hasattr(request.app.state, "haylie_encounter"):
        request.app.state.haylie_encounter = HaylieEncounterState(active=True)
    return MadameHaylie(request.app.state.haylie_encounter)


def _save_haylie(request: Request, haylie: MadameHaylie) -> None:
    request.app.state.haylie_encounter = haylie.encounter


# ═══════════════════════════════════════════════════════════════════
# JON endpoints
# ═══════════════════════════════════════════════════════════════════

@router.get("/jon/inventory")
async def jon_inventory(genre: SceneGenre = SceneGenre.FANTASY):
    """Return Jon's current stock for the given genre."""
    jon = ShopkeeperJon()
    items = jon.get_inventory(genre)
    return {
        "genre": genre,
        "items": [i.model_dump() for i in items],
        "note": "Jon has not commented on the genre change. He never does.",
    }


class BuyRequest(BaseModel):
    actor_id: str
    item_id: str
    genre: SceneGenre = SceneGenre.FANTASY


@router.post("/jon/buy")
async def jon_buy(
    body: BuyRequest,
    request: Request,
    state: StateManager = Depends(get_state_manager),
):
    """Attempt to purchase an item from Jon."""
    character = state.current.characters.get(body.actor_id)
    if character is None:
        raise HTTPException(status_code=404, detail=f"character '{body.actor_id}' not found")

    jon = _get_jon(request)
    diff, message = jon.buy_item(character, body.genre, body.item_id)
    _save_jon(request, jon)

    if diff is None:
        return {"success": False, "message": message}

    await state.apply_diff(diff)
    return {"success": True, "message": message}


class CactusRequest(BaseModel):
    is_lewd_or_mocking: bool = False


@router.post("/jon/cactus")
async def jon_cactus(body: CactusRequest, request: Request):
    """Player makes a comment about the cactus."""
    jon = _get_jon(request)
    response = jon.handle_cactus_comment(body.is_lewd_or_mocking)
    _save_jon(request, jon)
    return {
        "jon_response": response,
        "cactus_offense_count": jon.encounter.cactus_offense_count,
        "jon_will_sell": jon.jon_will_sell,
    }


class EscapeRequest(BaseModel):
    actor_id: str
    method: EscapeMethod = EscapeMethod.SMOOTH_TALK
    advantage: bool = False
    disadvantage: bool = False


@router.post("/jon/escape")
async def jon_escape(
    body: EscapeRequest,
    request: Request,
    state: StateManager = Depends(get_state_manager),
):
    """
    Attempt to leave Jon's store.
    On a bad fail (margin ≤ −5) sets bailout_available=True so Haylie can intervene.
    """
    jon = _get_jon(request)

    if not jon.party_can_leave:
        return {
            "success": False,
            "blocked": True,
            "bailout_available": jon.encounter.bailout_available,
            "message": (
                "Jon is mid-sentence. You literally cannot get a word in. "
                "Wait for him to finish. Or don't. He won't notice either way."
            ),
        }

    character = state.current.characters.get(body.actor_id)
    if character is None:
        raise HTTPException(status_code=404, detail=f"character '{body.actor_id}' not found")

    result, diff = jon.roll_escape_check(
        character, body.method, body.advantage, body.disadvantage
    )
    _save_jon(request, jon)

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
        "party_can_leave": jon.party_can_leave,
        "bailout_available": jon.encounter.bailout_available,
        "flavor": result.flavor,
    }


@router.post("/jon/tick")
async def jon_tick(request: Request):
    """Advance Jon's encounter by one turn."""
    jon = _get_jon(request)
    jon.tick_turn()
    _save_jon(request, jon)
    return {
        "story_trap_active": jon.encounter.story_trap_active,
        "story_trap_turns_remaining": jon.encounter.story_trap_turns_remaining,
        "jon_will_sell": jon.jon_will_sell,
        "party_can_leave": jon.party_can_leave,
        "bailout_available": jon.encounter.bailout_available,
    }


@router.get("/jon/state")
async def jon_state(request: Request):
    """Return the full current Jon encounter state."""
    jon = _get_jon(request)
    return {
        **jon.encounter.model_dump(),
        "party_can_leave": jon.party_can_leave,
        "jon_will_sell": jon.jon_will_sell,
    }


# ═══════════════════════════════════════════════════════════════════
# SAMAEL endpoints
# ═══════════════════════════════════════════════════════════════════

class ConsultRequest(BaseModel):
    category: LoreCategory = LoreCategory.GENERAL_LORE


@router.post("/samael/consult")
async def samael_consult(body: ConsultRequest, request: Request):
    """
    Ask Samael for a lore hint.
    Returns cryptic but valid guidance + what mundane thing he's doing right now.
    """
    samael = _get_samael(request)
    result = samael.consult(body.category)
    _save_samael(request, samael)
    return {
        "category": result.category,
        "cryptic_hint": result.cryptic_hint,
        "mundane_activity": result.mundane_activity,
        "mundane_description": result.mundane_description,
        "apathy_intro": result.apathy_intro,
        "apathy_outro": result.apathy_outro,
        "apathy_level": result.apathy_level,
        "consultation_number": result.consultation_number,
        "llm_context": samael.get_llm_context(body.category),
    }


@router.get("/samael/state")
async def samael_state(request: Request):
    """Return Samael's current encounter state."""
    samael = _get_samael(request)
    activity, desc = samael.get_current_activity()
    return {
        **samael.encounter.model_dump(),
        "current_activity_description": desc,
    }


# ═══════════════════════════════════════════════════════════════════
# HAYLIE endpoints
# ═══════════════════════════════════════════════════════════════════

class BailoutRequest(BaseModel):
    genre: SceneGenre = SceneGenre.FANTASY


@router.post("/haylie/bailout")
async def haylie_bailout(body: BailoutRequest, request: Request):
    """
    Madame Haylie intervenes to rescue the party from Jon's conversational trap.
    Requires jon.encounter.bailout_available == True (set after a critical escape fail).
    Always succeeds. Clears Jon's story trap.
    """
    jon = _get_jon(request)
    haylie = _get_haylie(request)

    result = haylie.trigger_bailout(jon.encounter, body.genre)

    if result is None:
        return {
            "triggered": False,
            "message": (
                "Haylie glances through the door but doesn't intervene. "
                "Jon isn't *that* far gone yet. Try the exit yourself first."
            ),
        }

    _save_jon(request, jon)
    _save_haylie(request, haylie)

    return {
        "triggered": True,
        "scolding": result.scolding,
        "jon_response": result.jon_response,
        "haylie_sign_off": result.haylie_sign_off,
        "inn_note": result.inn_note,
        "bailouts_delivered": result.bailouts_delivered,
        "party_can_leave": jon.party_can_leave,
    }


@router.get("/haylie/inn")
async def haylie_inn(genre: SceneGenre = SceneGenre.FANTASY, request: Request = None):
    """Return Haylie's genre-adaptive inn description."""
    haylie = _get_haylie(request) if request else MadameHaylie()
    return {
        "genre": genre,
        "description": haylie.get_inn_description(genre),
    }


@router.get("/haylie/state")
async def haylie_state(request: Request):
    """Return Haylie's current encounter state."""
    haylie = _get_haylie(request)
    jon = _get_jon(request)
    return {
        **haylie.encounter.model_dump(),
        "bailout_available": jon.encounter.bailout_available,
    }
