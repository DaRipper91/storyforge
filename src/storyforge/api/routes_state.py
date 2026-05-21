import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from storyforge.config import settings
from storyforge.core.state_manager import StateManager
from storyforge.api.deps import get_state_manager
from storyforge.persistence import snapshot

router = APIRouter(prefix="/api", tags=["state"])


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
    campaign_dir = settings.campaign_path.parent / body.campaign_id
    state = snapshot.load(campaign_dir)
    if state is None:
        raise HTTPException(status_code=404, detail=f"campaign '{body.campaign_id}' not found")
    request.app.state.state_manager = StateManager(state, campaign_dir)
    return state
