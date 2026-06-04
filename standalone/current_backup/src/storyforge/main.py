from fastapi import FastAPI, Depends
from pydantic import BaseModel
from typing import Dict, Any, List
from contextlib import asynccontextmanager

# --- Lifecycle Management ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load state from JSON on startup
    print("[storyforge] Initializing Campaign State...")
    yield
    # Save state to JSON on shutdown
    print("[storyforge] Persisting State to Disk...")

app = FastAPI(title="StoryForge", lifespan=lifespan)

# --- State Model (Internal) ---
class GameState(BaseModel):
    revision: int = 0
    characters: Dict[str, Any] = {}
    current_room: str = "Tavern"

# --- API Routes ---
@app.get("/api/state")
async def get_state():
    return {"status": "ok", "revision": 0}

@app.post("/api/action/grid")
async def grid_action(action: Dict[str, Any]):
    """
    Python Referee Route:
    Validates move, updates state, calls Gemini for flavor.
    """
    return {"narrative": "The hero moves.", "state_diff": {}}

@app.post("/api/action/freeform")
async def freeform_action(action: Dict[str, Any]):
    """
    AI Narrator Route:
    Gemini interprets text, proposes state diff, Python validates.
    """
    return {"narrative": "The world responds to your words.", "state_diff": {}}

@app.get("/")
async def root():
    return {"message": "StoryForge API is running. Access the frontend at /static/index.html"}
