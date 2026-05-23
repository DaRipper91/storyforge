"""
NPC interaction endpoints.

All NPC encounter state lives on app.state (session-level) so it resets
automatically when a new campaign is loaded — encounters aren't persisted
to the campaign snapshot.

NPCs:
  /api/npc/jon/*       — Jon the shopkeeper (Multiversal Bodega, Cactus, Escape)
  /api/npc/samael/*    — Samael the Ascended (cryptic lore hints)
  /api/npc/haylie/*    — Madame Haylie (bailout from Jon's conversational trap)
  /api/npc/danna/*     — Queen D.Anna (Royal Address, Petitions, Boons)
  /api/npc/redvelvet/* — Firey RedVelvet (Performances, Tips, Song Requests)
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
from storyforge.encounters.queen_danna import (
    AddressForm,
    PetitionType,
    QueenDAnna,
    QueenDAnnaEncounterState,
)
from storyforge.encounters.kodrik import (
    DispatchType,
    GuildmasterKodrik,
    KodrikEncounterState,
)
from storyforge.encounters.bryne import (
    BryneEncounterState,
    WardenApprenticeBryne,
)
from storyforge.encounters.nathis import (
    NathisEncounterState,
    FrontManNathis,
)
from storyforge.encounters.redvelvet import (
    FireyRedVelvet,
    RedVelvetEncounterState,
    SongRequest,
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


# ── Kodrik helpers ────────────────────────────────────────────────

def _get_kodrik(request: Request) -> GuildmasterKodrik:
    if not hasattr(request.app.state, "kodrik_encounter"):
        request.app.state.kodrik_encounter = KodrikEncounterState(active=True)
    return GuildmasterKodrik(request.app.state.kodrik_encounter)


def _save_kodrik(request: Request, kodrik: GuildmasterKodrik) -> None:
    request.app.state.kodrik_encounter = kodrik.encounter


# ── Bryne helpers ─────────────────────────────────────────────────

def _get_bryne(request: Request) -> WardenApprenticeBryne:
    if not hasattr(request.app.state, "bryne_encounter"):
        request.app.state.bryne_encounter = BryneEncounterState(active=True)
    return WardenApprenticeBryne(request.app.state.bryne_encounter)


def _save_bryne(request: Request, bryne: WardenApprenticeBryne) -> None:
    request.app.state.bryne_encounter = bryne.encounter


# ── Nathis helpers ────────────────────────────────────────────────

def _get_nathis(request: Request) -> FrontManNathis:
    if not hasattr(request.app.state, "nathis_encounter"):
        request.app.state.nathis_encounter = NathisEncounterState(active=True)
    return FrontManNathis(request.app.state.nathis_encounter)


def _save_nathis(request: Request, nathis: FrontManNathis) -> None:
    request.app.state.nathis_encounter = nathis.encounter


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


# ═══════════════════════════════════════════════════════════════════
# QUEEN D.ANNA helpers & endpoints
# ═══════════════════════════════════════════════════════════════════

def _get_danna(request: Request) -> QueenDAnna:
    if not hasattr(request.app.state, "danna_encounter"):
        request.app.state.danna_encounter = QueenDAnnaEncounterState(active=True)
    return QueenDAnna(request.app.state.danna_encounter)


def _save_danna(request: Request, danna: QueenDAnna) -> None:
    request.app.state.danna_encounter = danna.encounter


class AddressRequest(BaseModel):
    form: AddressForm = AddressForm.PROPER


@router.post("/danna/address")
async def danna_address(body: AddressRequest, request: Request):
    """Address Queen D.Anna. Correct address earns Favor; wrong address earns a lesson."""
    danna = _get_danna(request)
    result = danna.address(body.form)
    _save_danna(request, danna)
    return {
        "form": result.form,
        "correct": result.correct,
        "response": result.response,
        "favor_delta": result.favor_delta,
        "new_favor": result.new_favor,
        "standing": danna.standing_label,
        "is_offended": result.is_offended,
    }


class PetitionRequest(BaseModel):
    petition_type: PetitionType = PetitionType.BLESSING


@router.post("/danna/petition")
async def danna_petition(body: PetitionRequest, request: Request):
    """Petition Queen D.Anna for a boon. Requires Favor; costs Favor on grant."""
    danna = _get_danna(request)
    result = danna.petition(body.petition_type)
    _save_danna(request, danna)
    return {
        "granted": result.granted,
        "petition_type": result.petition_type,
        "response": result.response,
        "favor_cost": result.favor_cost,
        "new_favor": result.new_favor,
        "standing": danna.standing_label,
    }


@router.get("/danna/state")
async def danna_state(request: Request):
    """Return Queen D.Anna's current encounter state."""
    danna = _get_danna(request)
    return {
        **danna.encounter.model_dump(),
        "standing": danna.standing_label,
    }


# ═══════════════════════════════════════════════════════════════════
# FIREY REDVELVET helpers & endpoints
# ═══════════════════════════════════════════════════════════════════

def _get_redvelvet(request: Request) -> FireyRedVelvet:
    if not hasattr(request.app.state, "redvelvet_encounter"):
        request.app.state.redvelvet_encounter = RedVelvetEncounterState(active=True)
    return FireyRedVelvet(request.app.state.redvelvet_encounter)


def _save_redvelvet(request: Request, rv: FireyRedVelvet) -> None:
    request.app.state.redvelvet_encounter = rv.encounter


@router.post("/redvelvet/perform")
async def redvelvet_perform(request: Request):
    """Watch Firey RedVelvet perform. At BLAZING mood, the party gains Inspiration."""
    rv = _get_redvelvet(request)
    result = rv.perform()
    _save_redvelvet(request, rv)
    return {
        "performance_text": result.performance_text,
        "mood": result.mood.name,
        "mood_value": int(result.mood),
        "grants_boon": result.grants_boon,
        "boon_description": result.boon_description,
        "performances_given": rv.encounter.performances_given,
    }


class TipRequest(BaseModel):
    silver: int = 5


@router.post("/redvelvet/tip")
async def redvelvet_tip(body: TipRequest, request: Request):
    """Tip Firey RedVelvet. Every 5 silver raises her mood by one step."""
    if body.silver <= 0:
        raise HTTPException(status_code=400, detail="silver must be positive")
    rv = _get_redvelvet(request)
    result = rv.tip(body.silver)
    _save_redvelvet(request, rv)
    return {
        "response": result.response,
        "silver_spent": result.silver_spent,
        "mood_before": result.mood_before.name,
        "mood_after": result.mood_after.name,
        "mood_changed": result.mood_changed,
        "total_tips": rv.encounter.total_tips_silver,
    }


@router.post("/redvelvet/heckle")
async def redvelvet_heckle(request: Request):
    """Heckle Firey RedVelvet. She handles it. Mood drops one step."""
    rv = _get_redvelvet(request)
    result = rv.heckle()
    _save_redvelvet(request, rv)
    return {
        "response": result.response,
        "mood_before": result.mood_before.name,
        "mood_after": result.mood_after.name,
        "heckles_received": rv.encounter.heckles_received,
    }


class SongRequestBody(BaseModel):
    song_type: SongRequest = SongRequest.MYSTERY


@router.post("/redvelvet/request-song")
async def redvelvet_request_song(body: SongRequestBody, request: Request):
    """Request a song from Firey RedVelvet. She picks the right one."""
    rv = _get_redvelvet(request)
    result = rv.request_song(body.song_type)
    _save_redvelvet(request, rv)
    return {
        "song_type": result.song_type,
        "performance_text": result.performance_text,
        "mood": result.mood.name,
    }


@router.get("/redvelvet/state")
async def redvelvet_state(request: Request):
    """Return Firey RedVelvet's current encounter state."""
    rv = _get_redvelvet(request)
    return {
        **rv.encounter.model_dump(),
        "mood_label": rv.mood_label,
    }

# ═══════════════════════════════════════════════════════════════════
# KODRIK endpoints
# ═══════════════════════════════════════════════════════════════════

class RepairRequest(BaseModel):
    item_name: str
    silver_available: int

@router.post("/kodrik/dispatch")
async def kodrik_dispatch(request: Request, dispatch_type: DispatchType = DispatchType.SURVEY):
    """Request a new dispatch/task from Kodrik."""
    kodrik = _get_kodrik(request)
    result = kodrik.get_dispatch(dispatch_type)
    _save_kodrik(request, kodrik)
    return result

@router.post("/kodrik/repair")
async def kodrik_repair(request: Request, body: RepairRequest):
    """Request a gear repair from Kodrik."""
    kodrik = _get_kodrik(request)
    result = kodrik.repair_gear(body.item_name, body.silver_available)
    _save_kodrik(request, kodrik)
    return result

# ═══════════════════════════════════════════════════════════════════
# BRYNE endpoints
# ═══════════════════════════════════════════════════════════════════

@router.get("/bryne/observation")
async def bryne_observation(request: Request):
    """Get a silent observation from Bryne."""
    bryne = _get_bryne(request)
    result = bryne.get_observation()
    _save_bryne(request, bryne)
    return result

@router.post("/bryne/cole-lean")
async def bryne_cole_lean(request: Request):
    """Trigger Cole's lean effect."""
    bryne = _get_bryne(request)
    flavor = bryne.trigger_cole_lean()
    _save_bryne(request, bryne)
    return {"flavor": flavor}


# ═══════════════════════════════════════════════════════════════════
# NATHIS endpoints
# ═══════════════════════════════════════════════════════════════════

@router.get("/nathis/report")
async def nathis_report(request: Request):
    """Get a rapid-fire intelligence report from Nathis."""
    nathis = _get_nathis(request)
    result = nathis.get_report()
    _save_nathis(request, nathis)
    return result

@router.post("/nathis/tyty-bark")
async def nathis_tyty_bark(request: Request):
    """Trigger Tyty's barking."""
    nathis = _get_nathis(request)
    flavor = nathis.trigger_tyty_bark()
    _save_nathis(request, nathis)
    return {"flavor": flavor}
