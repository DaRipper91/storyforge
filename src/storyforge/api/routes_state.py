import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from storyforge.config import settings
from storyforge.core.state_manager import StateManager
from storyforge.core.models import Coord
from storyforge.api.deps import get_state_manager
from storyforge.persistence import snapshot
from storyforge.events.bus import event_bus

router = APIRouter(prefix="/api", tags=["state"])

class TimeSyncRequest(BaseModel):
    day: int
    hour: int
    minute: int

@router.post("/time/sync")
async def sync_time(req: TimeSyncRequest, state: StateManager = Depends(get_state_manager)):
    """Godot sends the current time. Update NPC schedules if hour changes."""
    # We can store the global time in state if we want, but for now just use it to evaluate schedules
    current_hour_str = str(req.hour)
    
    dirty = False
    for npc_id, npc in state.current.npcs.items():
        if npc.schedule and current_hour_str in npc.schedule:
            sched_pos = npc.schedule[current_hour_str]
            # Convert dictionary back to Coord
            new_target = Coord(x=int(sched_pos.get("x", 0)), y=int(sched_pos.get("y", 0)))
            
            if npc.target_position != new_target:
                npc.target_position = new_target
                dirty = True
                
    if dirty:
        state.current.revision += 1
        await event_bus.publish({
            "type": "state_updated",
            "revision": state.current.revision
        })
    return {"status": "ok"}

@router.get("/state")
async def get_state(state: StateManager = Depends(get_state_manager)):
    return state.current


@router.post("/state/trigger_paradox")
async def trigger_paradox(state: StateManager = Depends(get_state_manager)):
    """Manual trigger for the Race Switch."""
    return await state.trigger_paradox()


@router.get("/revision")
async def get_revision(state: StateManager = Depends(get_state_manager)):
    return {"revision": state.current.revision}


@router.get("/campaigns")
async def list_campaigns():
    base_dir = settings.campaign_path.parent
    return {"campaigns": snapshot.list_campaigns(base_dir)}


class LoadCampaignRequest(BaseModel):
    campaign_id: str


@router.post("/campaigns/new")
async def new_campaign(request: Request):
    campaign_id = f"campaign_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    campaign_dir = settings.campaign_path.parent / campaign_id
    state = snapshot.load_seed().model_copy(deep=True, update={"campaign_id": campaign_id})
    snapshot.save(campaign_dir, state)
    request.app.state.state_manager = StateManager(state, campaign_dir)
    return state


@router.post("/campaigns/load")
async def load_campaign(body: LoadCampaignRequest, request: Request):
    if "/" in body.campaign_id or "\\" in body.campaign_id or ".." in body.campaign_id:
        raise HTTPException(status_code=400, detail="Invalid campaign_id: cannot contain path traversal characters.")

    campaign_dir = settings.campaign_path.parent / body.campaign_id
    state = snapshot.load(campaign_dir)
    if state is None:
        raise HTTPException(status_code=404, detail=f"campaign '{body.campaign_id}' not found")
    request.app.state.state_manager = StateManager(state, campaign_dir)
    return state
