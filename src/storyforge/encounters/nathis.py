"""
Nathis — encounter logic for Nathis (The Front Man).

Mechanics:
  1. The Herald  — Tyty's barking removes the element of surprise.
  2. Fast Talk   — Nathis provides rapid-fire local intelligence.
  3. Relocation  — He disappears and reappears in a more advantageous spot.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from pydantic import BaseModel


class NathisEncounterState(BaseModel):
    active: bool = False
    reports_given: int = 0
    tyty_barking: bool = False


@dataclass(frozen=True)
class ReportResult:
    intel: str
    urgency: str
    flavor: str


_REPORTS: list[str] = [
    "The bridge is out. Or it's there but it's not holding weight. Either way, don't walk on it. I checked.",
    "There's a group of people at the crossroads who are pretending they don't have weapons. They have weapons. Mostly knives.",
    "The Store just got a delivery of something that glows. Jon thinks it's cheese. It's definitely not cheese.",
]

_TYTY_FLAVOR: list[str] = [
    "Tyty lets out a series of sharp, high-volume barks. The element of surprise has been officially revoked for everyone within three miles.",
    "The Wandering Herald begins his announcement. It is loud. It is persistent. It is Tyty.",
    "Tyty barks at a shadow. The shadow, clearly embarrassed by the attention, retreats into the brush.",
]


class FrontManNathis:
    def __init__(self, state: NathisEncounterState | None = None) -> None:
        self.encounter = state or NathisEncounterState()

    def get_report(self) -> ReportResult:
        """Get a fast-paced intelligence report."""
        self.encounter.reports_given += 1
        return ReportResult(
            intel=random.choice(_REPORTS),
            urgency="Immediate",
            flavor="Nathis delivers the information at a speed that suggests he has somewhere else to be. He usually does."
        )

    def trigger_tyty_bark(self) -> str:
        """Narrate Tyty's announcement."""
        self.encounter.tyty_barking = True
        return random.choice(_TYTY_FLAVOR)
