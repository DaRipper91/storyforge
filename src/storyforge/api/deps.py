from fastapi import Request
from storyforge.core.state_manager import StateManager

def get_state_manager(request: Request) -> StateManager:
    return request.app.state.state_manager
