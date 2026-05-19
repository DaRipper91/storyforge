from fastapi import APIRouter, Depends, HTTPException
from storyforge.core.models import (
    GridAction, FreeformAction, AINarrationResponse, TurnPhase,
)
from storyforge.core.state_manager import StateManager
from storyforge.core import rules, validators
from storyforge.ai import narrator, interpreter
from storyforge.events.bus import event_bus
from storyforge.api.deps import get_state_manager

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
    
    # 3. Ask Gemini for flavor text (text-only, no state diff allowed)
    narrative = await narrator.narrate_movement(state.current, char, diff["from"], diff["to"])
    
    # 4. Log and broadcast
    await state.append_narration(actor_id=char.id, kind="action", text=narrative)
    # Broadcast is handled by state.commit() called inside apply_grid_action
    
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
    # Broadcast is handled by state.commit() called inside apply_diff
    
    return {"narrative": response.narrative, "revision": state.current.revision}
