"""Deterministic authored quest actions."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from storyforge.api.deps import get_state_manager
from storyforge.core.state_manager import StateError, StateManager

router = APIRouter(prefix="/api/quests", tags=["quests"])


class QuestInteraction(BaseModel):
    actor_id: str
    npc_id: str


@router.post("/{quest_id}/interact")
async def interact_with_quest_npc(
    quest_id: str,
    body: QuestInteraction,
    state: StateManager = Depends(get_state_manager),
) -> JSONResponse:
    """Accept, review, or turn in a quest through its authored NPCs."""
    try:
        result = await state.interact_quest(body.actor_id, quest_id, body.npc_id)
    except StateError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await state.append_narration(
        actor_id=body.actor_id,
        kind="action",
        text=result["message"],
    )
    result["revision"] = state.current.revision
    return JSONResponse(content=result)
