from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from storyforge.core.models import (
    GridAction, FreeformAction, TurnPhase,
)
from storyforge.core.state_manager import StateManager
from storyforge.core import rules, validators
from storyforge.ai import narrator, interpreter
from storyforge.api.deps import get_state_manager
from storyforge.events.bus import event_bus

router = APIRouter(prefix="/api/action", tags=["action"])


@router.post("/grid")
async def handle_grid(
    action: GridAction,
    state: StateManager = Depends(get_state_manager),
) -> dict:
    """Structured click → deterministic mutation → flavor narration."""
    if state.current.phase != TurnPhase.EXPLORATION:
        raise HTTPException(
            status_code=409,
            detail=f"grid actions require EXPLORATION phase, "
                   f"currently {state.current.phase.value}",
        )
    
    char = state.get_character(action.actor_id)
    
    # 1. Python referee validates the move
    legality = rules.check_grid_action(state.current, char, action)
    if not legality.ok:
        raise HTTPException(status_code=400, detail=legality.reason)
    
    # 2. Apply the deterministic mutation
    diff = await state.apply_grid_action(char, action)

    # 3. Handle each diff type differently
    diff_type = diff.get("type", "")

    if diff_type == "npc_encounter":
        # No narration — let the frontend open the encounter overlay
        return {"encounter": diff, "revision": state.current.revision}

    if diff_type == "room_transition":
        narrative = f"{char.name} steps into {diff['room_name']}."
        await state.append_narration(actor_id=char.id, kind="narration", text=narrative)
        return {"narrative": narrative, "room_transition": diff, "revision": state.current.revision}

    # Normal move — ask Gemini for flavor text (non-fatal if Gemini is unavailable)
    try:
        narrative = await narrator.narrate_movement(state.current, char, diff["from"], diff["to"])
    except Exception:
        narrative = f"{char.name} moves to ({diff['to']['x']}, {diff['to']['y']})."

    # 4. Log and broadcast
    await state.append_narration(actor_id=char.id, kind="action", text=narrative)
    return {"narrative": narrative, "revision": state.current.revision}


@router.post("/freeform")
async def handle_freeform(
    action: FreeformAction,
    state: StateManager = Depends(get_state_manager),
) -> dict:
    """Freeform text → AI interprets → validated mutation → broadcast."""
    if state.current.phase != TurnPhase.EXPLORATION:
        raise HTTPException(
            status_code=409,
            detail=f"freeform actions require EXPLORATION phase, "
                   f"currently {state.current.phase.value}",
        )
    
    # 1. Build prompt + call Gemini for structured output
    char = state.get_character(action.actor_id)
    response = await interpreter.interpret_freeform(
        state=state.current,
        actor=char,
        action=action,
    )
    
    # 2. Sanitize the proposed diff (drop illegal mutations)
    if response.state_diff is not None:
        safe_diff, rejections = validators.sanitize(
            state.current, response.state_diff,
        )
        await state.apply_diff(safe_diff)
        for r in rejections:
            await state.append_narration(actor_id=None, kind="system", text=f"[ref] {r}")
    
    # 3. Log narrative + broadcast
    await state.append_narration(actor_id=action.actor_id, kind="action", text=action.text)
    await state.append_narration(actor_id=None, kind="narration", text=response.narrative)

    pos = char.position
    await event_bus.publish({
        "type": "particle_event",
        "actor_id": action.actor_id,
        "position": {"x": pos.x, "y": pos.y},
        "effect": "magic_burst",
    })

    return {"narrative": response.narrative, "revision": state.current.revision}


class EntityAction(BaseModel):
    actor_id: str
    target_id: str

@router.post("/interact_entity")
async def interact_entity(
    action: EntityAction,
    state: StateManager = Depends(get_state_manager),
) -> dict:
    """Directly interact with an entity (NPC, chest, etc.) by ID."""
    if state.current.phase != TurnPhase.EXPLORATION:
        raise HTTPException(
            status_code=409,
            detail=f"actions require EXPLORATION phase, currently {state.current.phase.value}",
        )
    
    char = state.get_character(action.actor_id)
    target_id = action.target_id
    
    # Check if target is an NPC
    if target_id in state.current.npcs:
        npc = state.current.npcs[target_id]
        diff = {
            "type": "npc_encounter",
            "npc_id": npc.id,
            "npc_name": npc.name,
            "encounter_id": npc.encounter_id,
            "history": npc.dialog_history,
        }
        return {"encounter": diff, "revision": state.current.revision}
    
    raise HTTPException(status_code=404, detail="Target not found or not interactable")


class TravelRequest(BaseModel):
    room_id: str


@router.post("/travel")
async def fast_travel(
    req: TravelRequest,
    state: StateManager = Depends(get_state_manager),
) -> dict:
    """World-map fast travel: teleport the party to any known room."""
    if req.room_id not in state.current.rooms:
        raise HTTPException(status_code=404, detail=f"unknown room: {req.room_id}")
    diff = await state.fast_travel(req.room_id)
    room_name = state.current.rooms[req.room_id].name
    await state.append_narration(
        actor_id=None, kind="narration",
        text=f"The party arrives at {room_name}."
    )
    return {"room_transition": diff, "revision": state.current.revision}
