"""
Lobby + character creation routes.

Endpoints:
    POST /api/lobby/join      — claim a slot with a controller ID
    POST /api/lobby/leave     — release a slot
    POST /api/character/create — finalize a slot into a CharacterSheet
    POST /api/lobby/start     — transition to EXPLORATION
    GET  /api/lobby/catalog   — race + class definitions for the UI
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
import jwt

from storyforge.config import settings
from storyforge.api.deps import get_state_manager
from storyforge.core.character_factory import RACES, STATES, ROLES
from storyforge.core.models import CharacterCreationRequest, TurnPhase
from storyforge.core.state_manager import StateError, StateManager


router = APIRouter(prefix="/api", tags=["lobby"])


# ───────────────────────── Request models ─────────────────────────

class SetPhaseRequest(BaseModel):
    phase: TurnPhase


class JoinRequest(BaseModel):
    # If authenticated, this is ignored and the Google ID is used.
    controller_id: str | None = Field(default=None, min_length=1, max_length=200)


class LeaveRequest(BaseModel):
    controller_id: str | None = Field(default=None, min_length=1, max_length=200)


class UpdateNameRequest(BaseModel):
    slot_index: int = Field(ge=0, le=3)
    name: str = Field(min_length=0, max_length=24)
    controller_id: str | None = Field(default=None, min_length=1, max_length=200)


# ───────────────────────── Endpoints ─────────────────────────

@router.get("/lobby/catalog")
async def get_catalog() -> dict:
    """Static reference data for the creation UI. Cached client-side."""
    return {
        "races": {
            race.value: {
                "name": rdef.name,
                "speed": rdef.speed,
                "ability_bonuses": rdef.ability_bonuses,
                "flavor": rdef.flavor,
                "group": rdef.group,
                "before": rdef.before,
            }
            for race, rdef in RACES.items()
        },
        "states": {
            state.value: {
                "name": sdef.name,
                "hit_die": sdef.hit_die,
                "base_armor_class": sdef.base_armor_class,
                "flavor": sdef.flavor,
            }
            for state, sdef in STATES.items()
        },
        "roles": {
            role.value: {
                "name": pdef.name,
                "starting_inventory": [
                    item.model_dump(mode="json") for item in pdef.starting_inventory
                ],
                "flavor": pdef.flavor,
            }
            for role, pdef in ROLES.items()
        },
        "standard_array": [15, 14, 13, 12, 10, 8],
    }


@router.post("/lobby/join")
async def join_lobby(
    req: JoinRequest,
    state: StateManager = Depends(get_state_manager),
    request: Request = None,
) -> dict:
    # Use Google ID if available, else fallback to provided controller_id (e.g. guest/local)
    token = request.cookies.get("storyforge_session")
    controller_id = req.controller_id
    
    if token:
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
            controller_id = f"google::{payload['sub']}"
        except Exception:
            pass

    if not controller_id:
        raise HTTPException(status_code=401, detail="Authentication or controller_id required")

    try:
        return await state.claim_slot(controller_id=controller_id)
    except StateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/lobby/leave")
async def leave_lobby(
    req: LeaveRequest,
    state: StateManager = Depends(get_state_manager),
    request: Request = None,
) -> dict:
    token = request.cookies.get("storyforge_session")
    controller_id = req.controller_id

    if token:
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
            controller_id = f"google::{payload['sub']}"
        except Exception:
            pass

    if not controller_id:
        raise HTTPException(status_code=401, detail="Authentication or controller_id required")

    try:
        return await state.release_slot(controller_id=controller_id)
    except StateError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/lobby/update_name")
async def update_name(
    req: UpdateNameRequest,
    state: StateManager = Depends(get_state_manager),
    request: Request = None,
) -> dict:
    token = request.cookies.get("storyforge_session")
    controller_id = req.controller_id

    if token:
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
            controller_id = f"google::{payload['sub']}"
        except Exception:
            pass

    if not controller_id:
        raise HTTPException(status_code=401, detail="Authentication or controller_id required")

    try:
        return await state.update_slot_name(
            slot_index=req.slot_index,
            name=req.name,
            controller_id=controller_id,
        )
    except StateError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/lobby/set_phase")
async def set_phase(
    req: SetPhaseRequest,
    state: StateManager = Depends(get_state_manager),
) -> dict:
    try:
        return await state.set_phase(req.phase)
    except StateError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/character/create")
async def create_character(
    req: CharacterCreationRequest,
    state: StateManager = Depends(get_state_manager),
) -> dict:
    try:
        return await state.create_character(req)
    except (StateError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/lobby/start")
async def start_game(
    state: StateManager = Depends(get_state_manager),
) -> dict:
    try:
        return await state.start_exploration()
    except StateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
