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

import dataclasses

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from storyforge.ai.npc_narrator import narrate_npc
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
    pool_response = jon.handle_cactus_comment(body.is_lewd_or_mocking)
    _save_jon(request, jon)

    situation = (
        f"A player {'made a lewd or mocking comment about' if body.is_lewd_or_mocking else 'casually noticed'} "
        f"the cactus on the counter. This is cactus offense #{jon.encounter.cactus_offense_count}. "
        f"Jon does not register the offense — he responds with genuine warmth and treats the cactus with dignity. "
        f"{'Jon is still not selling to them right now.' if not jon.jon_will_sell else ''} "
        f"Respond as Jon only. One short reply."
    )
    try:
        jon_response = await narrate_npc("jon", situation)
    except Exception:
        jon_response = pool_response

    return {
        "jon_response": jon_response,
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
    Calls Gemini with npc_samael.md as the system instruction for a unique
    cryptic response. Falls back to the Python pool hint if Gemini fails.
    """
    samael = _get_samael(request)
    result = samael.consult(body.category)
    ctx = samael.get_llm_context(body.category)
    _save_samael(request, samael)

    category_label = body.category.value.replace("_", " ")
    again_prefix = "Again. " if ctx["consultation_number"] > 1 else ""
    situation = (
        f"{again_prefix}The party has approached Samael for guidance. "
        f"He is currently: {ctx['mundane_description']} "
        f"They are asking about: {category_label}. "
        f"This is consultation #{ctx['consultation_number']}. "
        f"Apathy level: {ctx['apathy_level']} out of 5 — let this shape how theatrical your sighing is. "
        f"Respond in character. Use the Cryptic Delivery Format from your prompt. "
        f"Return the full interaction: atmospheric intro, acknowledgment, cryptic hint, mundane return."
    )

    try:
        cryptic_hint = await narrate_npc("samael", situation)
    except Exception:
        cryptic_hint = result.cryptic_hint  # pool fallback

    return {
        "category": result.category,
        "cryptic_hint": cryptic_hint,
        "mundane_activity": result.mundane_activity,
        "mundane_description": result.mundane_description,
        "apathy_intro": result.apathy_intro,
        "apathy_outro": result.apathy_outro,
        "apathy_level": result.apathy_level,
        "consultation_number": result.consultation_number,
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

    situation = (
        f"Haylie has walked into The Store. She is in motion — not rescuing anyone, just arriving. "
        f"Jon has been deep in a story trap. This is bailout #{result.bailouts_delivered}. "
        f"The room's energy shifts when she enters. Players find it easier to leave — not because she "
        f"intervened, but because the room reorganized around her. "
        f"Genre context: {body.genre.value}. "
        f"Write three short beats: Haylie's casual remark as she moves through (loud, warm, chaotic), "
        f"Jon's quiet chastened murmur, Haylie's sign-off as she reaches the door. "
        f"Keep it light — Haylie is noise and forward motion, Jon is fond of her exactly as she is."
    )
    try:
        scolding = await narrate_npc("haylie", situation)
        jon_response = result.jon_response
        haylie_sign_off = result.haylie_sign_off
    except Exception:
        scolding = result.scolding
        jon_response = result.jon_response
        haylie_sign_off = result.haylie_sign_off

    return {
        "triggered": True,
        "scolding": scolding,
        "jon_response": jon_response,
        "haylie_sign_off": haylie_sign_off,
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

    situation = (
        f"A player addressed Queen D.Anna using form: '{body.form.value}'. "
        f"Address was {'correct' if result.correct else 'incorrect — she does not raise her voice, she simply clarifies'}. "
        f"Favor delta: {result.favor_delta:+d}. Current favor: {result.new_favor}. Standing: {danna.standing_label}. "
        f"D.Anna is measured, precise, warm but never soft. She holds space without announcing it. "
        f"Deliver her response in one or two sentences."
    )
    try:
        response_text = await narrate_npc("danna", situation)
    except Exception:
        response_text = result.response

    return {
        "form": result.form,
        "correct": result.correct,
        "response": response_text,
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

    situation = (
        f"A player petitioned Queen D.Anna for: {body.petition_type.value}. "
        f"Petition {'granted' if result.granted else 'declined'}. "
        f"Favor cost: {result.favor_cost}. Remaining favor: {result.new_favor}. Standing: {danna.standing_label}. "
        f"{'Grant it with weight — this costs something, politically.' if result.granted else 'Decline with clarity — no apology, just a closed door and a path forward.'} "
        f"One or two sentences as D.Anna."
    )
    try:
        response_text = await narrate_npc("danna", situation)
    except Exception:
        response_text = result.response

    return {
        "granted": result.granted,
        "petition_type": result.petition_type,
        "response": response_text,
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

    situation = (
        f"Firey RedVelvet is performing at {result.mood.name} mood (performance #{rv.encounter.performances_given}). "
        f"COLD = technically perfect but going through motions; WARM = locked in, genuinely good; "
        f"HOT = something real is happening here, the room feels it; "
        f"BLAZING = transcendent — the fire performs with her, it is finished and perfect, the room goes quiet. "
        f"{'BLAZING: this moment is complete. Write it that way.' if result.grants_boon else ''} "
        f"Write her performance text for exactly this mood. Match the energy precisely. No hedging."
    )
    try:
        perf_text = await narrate_npc("redvelvet", situation)
    except Exception:
        perf_text = result.performance_text

    return {
        "performance_text": perf_text,
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

    situation = (
        f"Someone tipped Firey RedVelvet {body.silver} silver. "
        f"Mood moved from {result.mood_before.name} to {result.mood_after.name}. "
        f"{'Mood improved one step.' if result.mood_changed else 'Already at peak mood — she acknowledges it anyway.'} "
        f"She never stops the performance for a tip — she acknowledges it in character, mid-movement. "
        f"Write her response in one sentence. Stylish. In character."
    )
    try:
        response_text = await narrate_npc("redvelvet", situation)
    except Exception:
        response_text = result.response

    return {
        "response": response_text,
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

    situation = (
        f"Someone heckled Firey RedVelvet. Heckle #{rv.encounter.heckles_received}. "
        f"Mood dropped from {result.mood_before.name} to {result.mood_after.name}. "
        f"She finishes the phrase first. Then she addresses it — with the calm of someone who has "
        f"already composed the response and is deciding whether to use the polite version. "
        f"She is never rattled. The fire does not agree with the heckler. "
        f"Two sentences max: finish the phrase, then the address."
    )
    try:
        response_text = await narrate_npc("redvelvet", situation)
    except Exception:
        response_text = result.response

    return {
        "response": response_text,
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

    situation = (
        f"Someone requested a {body.song_type.value} song from Firey RedVelvet. "
        f"Her current mood is {result.mood.name}. "
        f"Song types: MYSTERY=haunting/atmospheric, BATTLE=driving/fierce, BALLAD=slow/emotional, "
        f"COMEDY=light/crowd-pleasing, EPIC=sweeping/legendary. "
        f"She does not announce the song — she just begins it. Write the performance for this song type, "
        f"colored by her current mood. Two to four sentences."
    )
    try:
        perf_text = await narrate_npc("redvelvet", situation)
    except Exception:
        perf_text = result.performance_text

    return {
        "song_type": result.song_type,
        "performance_text": perf_text,
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

    situation = (
        f"Guildmaster Kodrik is assigning a {dispatch_type.value} dispatch to the party. "
        f"Location: {result.location_name}. Breadcrumb: {result.breadcrumb}. "
        f"Dispatch #{kodrik.encounter.dispatches_given}. "
        f"Kodrik is direct, professional, no wasted words. He probably does not look up from the map. "
        f"Write his delivery of this dispatch — one or two sentences. No pleasantries."
    )
    try:
        flavor = await narrate_npc("kodrik", situation)
    except Exception:
        flavor = result.flavor

    return {**dataclasses.asdict(result), "flavor": flavor}


@router.post("/kodrik/repair")
async def kodrik_repair(request: Request, body: RepairRequest):
    """Request a gear repair from Kodrik."""
    kodrik = _get_kodrik(request)
    result = kodrik.repair_gear(body.item_name, body.silver_available)
    _save_kodrik(request, kodrik)

    situation = (
        f"Kodrik is {'repairing' if result.success else 'declining to repair'} {body.item_name}. "
        f"{'Cost: ' + str(result.cost) + ' silver. Work is done.' if result.success else 'Not enough silver — he does not touch it.'} "
        f"He speaks in the language of craft and coin. Brief. No sentiment. "
        f"Write his response in one sentence."
    )
    try:
        flavor = await narrate_npc("kodrik", situation)
    except Exception:
        flavor = result.flavor

    return {**dataclasses.asdict(result), "flavor": flavor}

# ═══════════════════════════════════════════════════════════════════
# BRYNE endpoints
# ═══════════════════════════════════════════════════════════════════

@router.get("/bryne/observation")
async def bryne_observation(request: Request):
    """Get a silent observation from Bryne."""
    bryne = _get_bryne(request)
    result = bryne.get_observation()
    _save_bryne(request, bryne)

    situation = (
        f"Bryne has noticed something the party missed: \"{result.text}\". "
        f"He points at it without explanation. He does not wait for acknowledgment. "
        f"He and Nathis are always together — Nathis is nearby. "
        f"Write the behavioral flavor: how Bryne gestures, what the silence feels like, "
        f"what it is like to receive information from someone who considers speaking a last resort. "
        f"One or two sentences. No dialogue from Bryne."
    )
    try:
        flavor = await narrate_npc("bryne", situation)
    except Exception:
        flavor = result.flavor

    return {**dataclasses.asdict(result), "flavor": flavor}


@router.post("/bryne/cole-lean")
async def bryne_cole_lean(request: Request):
    """Trigger Cole's lean effect."""
    bryne = _get_bryne(request)
    pool_flavor = bryne.trigger_cole_lean()
    _save_bryne(request, bryne)

    situation = (
        "Cole (Bryne's massive black dog, not yet in the realm) is doing The Lean — "
        "the passive effect where he settles his full weight against someone and the room's tension "
        "becomes a distant problem. Write one sentence describing the lean. "
        "Weight. Warmth. Inexplicable safety."
    )
    try:
        flavor = await narrate_npc("bryne", situation)
    except Exception:
        flavor = pool_flavor

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

    situation = (
        f"Nathis is delivering an intelligence report at speed. "
        f"Intel: \"{result.intel}\". Urgency: {result.urgency}. "
        f"Report #{nathis.encounter.reports_given}. "
        f"He speaks in volleys — no filter between thought and mouth, "
        f"already half-out the door before he finishes the sentence. "
        f"Tyty may be nearby, already announcing the situation to the surrounding half mile. "
        f"Write the flavor of how Nathis delivers this. One or two sentences. Fast."
    )
    try:
        flavor = await narrate_npc("nathis", situation)
    except Exception:
        flavor = result.flavor

    return {**dataclasses.asdict(result), "flavor": flavor}


@router.post("/nathis/tyty-bark")
async def nathis_tyty_bark(request: Request):
    """Trigger Tyty's barking."""
    nathis = _get_nathis(request)
    pool_flavor = nathis.trigger_tyty_bark()
    _save_nathis(request, nathis)

    situation = (
        "Tyty (Nathis's dog, The Wandering Herald) has detected a threat and begun his announcement. "
        "Full volume. The element of surprise is over for everyone within half a mile. "
        "He has relocated to a better position to continue heraldry — this is not fleeing, "
        "this is operational repositioning. "
        "Write one sentence: the announcement, its range, and Tyty's strategic relocation."
    )
    try:
        flavor = await narrate_npc("nathis", situation)
    except Exception:
        flavor = pool_flavor

    return {"flavor": flavor}
