from fastapi import APIRouter, Depends, HTTPException
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
