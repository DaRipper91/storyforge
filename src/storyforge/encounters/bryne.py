"""
Bryne — encounter logic for Bryne (The Warden's Apprentice).

Mechanics:
  1. The Shadow  — he appears in the background of other encounters.
  2. Silent Help — he provides a critical observation when the party is stuck.
  3. Cole's Lean — a passive effect that makes interactions feel more grounded.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from pydantic import BaseModel


class BryneEncounterState(BaseModel):
    active: bool = False
    observations_shared: int = 0
    cole_is_leaning: bool = False


@dataclass(frozen=True)
class ObservationResult:
    text: str
    impact: str
    flavor: str


_OBSERVATIONS: list[str] = [
    "The tracks by the door don't match the ones on the road. Something changed its weight halfway through.",
    "The air in this room is moving toward the fireplace, but there's no draft from the window. The chimney is larger than it looks.",
    "The silver on the table is old world. High purity. The kind they don't mint anymore.",
]

_COLE_LEAN_FLAVOR: list[str] = [
    "Cole leans his entire weight against your leg. It feels like being pinned by a very soft, very warm mountain.",
    "The massive black dog rests his head on your knee. You feel suddenly, inexplicably safe.",
    "Cole settles in next to you. His presence makes the room's tension feel like a distant problem.",
]


class WardenApprenticeBryne:
    def __init__(self, state: BryneEncounterState | None = None) -> None:
        self.encounter = state or BryneEncounterState()

    def get_observation(self) -> ObservationResult:
        """Share a silent observation."""
        self.encounter.observations_shared += 1
        return ObservationResult(
            text=random.choice(_OBSERVATIONS),
            impact="Investigation Advantage",
            flavor="Bryne points a stocky finger toward a detail you missed. He doesn't wait for a thank you."
        )

    def trigger_cole_lean(self) -> str:
        """Narrate Cole's lean passive effect."""
        self.encounter.cole_is_leaning = True
        return random.choice(_COLE_LEAN_FLAVOR)
