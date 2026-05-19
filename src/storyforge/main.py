"""StoryForge FastAPI entrypoint.

Run:
    uv run uvicorn storyforge.main:app --reload --host 127.0.0.1 --port 8765
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from storyforge.config import settings
from storyforge.api import routes_state, routes_action, routes_lobby, ws_session
from storyforge.core.state_manager import StateManager
from storyforge.persistence import snapshot


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load campaign state on boot, persist on shutdown."""
    state = snapshot.load(settings.campaign_path) or snapshot.load_seed()
    app.state.state_manager = StateManager(state, settings.campaign_path)
    print(f"[storyforge] loaded campaign: {state.campaign_id}")
    print(f"[storyforge] phase: {state.phase}")
    print(f"[storyforge] room: {state.current_room_id}")
    print(f"[storyforge] characters: {list(state.characters.keys())}")
    
    yield
    
    snapshot.save(settings.campaign_path, app.state.state_manager.current)
    print("[storyforge] state persisted to disk")


app = FastAPI(
    title="StoryForge",
    version="0.1.0",
    description="Hybrid VTT + AI Dungeon Master",
    lifespan=lifespan,
)

# CORS: open to local network for family devices
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Open for MVP on local LAN
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(routes_state.router)
app.include_router(routes_action.router)
app.include_router(routes_lobby.router)
app.include_router(ws_session.router)

# Frontend static
app.mount("/static", StaticFiles(directory=settings.frontend_path), name="static")


@app.get("/")
async def root():
    return FileResponse(settings.frontend_path / "index.html")


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "version": app.version}
