from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any

app = FastAPI(title="StoryForge Engine")

# --- Routes ---
@app.get("/api/state")
async def get_state():
    """Returns the current structured JSON state of the grid and characters."""
    return {
        "status": "ok", 
        "state": {
            "grid": {"width": 20, "height": 20}, 
            "characters": {"cody": {"hp": 10, "x": 5, "y": 5}}
        }
    }

@app.post("/api/action/grid")
async def grid_action(payload: Dict[str, Any]):
    """
    Handles strict tactical moves (clicks).
    1. Python calculates new state.
    2. Passes result to Gemini.
    3. Returns State + Flavor Text.
    """
    # TODO: Implement strict math logic here
    # 1. engine.combat validates move
    # 2. engine.state_manager updates JSON
    # 3. ai.gemini_client generates narrative
    flavor_text = "The hero maneuvers tactically across the battlefield."
    return {"status": "success", "narrative": flavor_text, "state": payload}

@app.post("/api/action/freeform")
async def freeform_action(payload: Dict[str, Any]):
    """
    Handles narrative actions (text).
    1. Passes intent + current state to Gemini.
    2. Gemini returns narrative AND a JSON state diff.
    3. Python applies diff to state.
    """
    # TODO: Implement Gemini Structured Outputs here
    # 1. ai.gemini_client processes text + schema
    # 2. engine.state_manager applies AI's JSON diff
    flavor_text = f"You attempt to: {payload.get('text', 'something')}. The AI determines the outcome."
    return {"status": "success", "narrative": flavor_text, "state_diff": {"hp_change": 0}}

@app.get("/")
async def root():
    return {"message": "StoryForge VTT API is alive. Check /docs for endpoints."}
