"""Enemy encounter endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from storyforge.api.deps import get_state_manager
from storyforge.core.state_manager import StateError, StateManager

router = APIRouter(prefix="/api/enemy", tags=["enemy"])


class AttackRequest(BaseModel):
    actor_id: str


@router.get("/room/{room_id}")
async def list_room_enemies(
    room_id: str,
    state: StateManager = Depends(get_state_manager),
) -> dict:
    """Return all alive enemies in a given room."""
    enemies = {
        eid: e.model_dump(mode="json")
        for eid, e in state.current.enemies.items()
        if e.room_id == room_id
    }
    return {"room_id": room_id, "enemies": enemies}


@router.post("/{enemy_id}/attack")
async def attack_enemy(
    enemy_id: str,
    req: AttackRequest,
    state: StateManager = Depends(get_state_manager),
) -> dict:
    """Resolve a player attack against an enemy. Enemy counterattacks if alive."""
    enemy = state.current.enemies.get(enemy_id)
    if enemy is None:
        raise HTTPException(status_code=404, detail=f"unknown enemy: {enemy_id}")
    if not enemy.alive:
        raise HTTPException(status_code=409, detail=f"{enemy.name} is already dead")

    try:
        result = await state.attack_enemy(req.actor_id, enemy_id)
    except StateError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Build a single narrative line from the round results
    lines = [result["player_attack"]["hint"]]
    if "enemy_attack" in result:
        lines.append(result["enemy_attack"]["hint"])
    if result.get("enemy_died"):
        dead_name = state.current.enemies[enemy_id].name
        lines.append(f"{dead_name} collapses. +{result['xp_reward']} XP.")

    narrative = " ".join(lines)
    await state.append_narration(actor_id=req.actor_id, kind="action", text=narrative)

    result["narrative"] = narrative
    result["revision"] = state.current.revision
    return result
