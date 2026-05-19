from fastapi import APIRouter, Depends
from storyforge.core.state_manager import StateManager
from storyforge.api.deps import get_state_manager

router = APIRouter(prefix="/api", tags=["state"])

@router.get("/state")
async def get_state(state: StateManager = Depends(get_state_manager)):
    return state.current

@router.get("/revision")
async def get_revision(state: StateManager = Depends(get_state_manager)):
    return {"revision": state.current.revision}
