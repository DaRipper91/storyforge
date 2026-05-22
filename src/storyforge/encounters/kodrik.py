"""
Kodrik — encounter logic for Guildmaster Kodrik (Iron Ledge Company).

Architecture:
  - Kodrik is a pure service class.
  - Mechanics:
    1. Mechanic's Bench — repairs broken gear for silver or favors.
    2. Dispatch       — provides lore breadcrumbs/hints for the map.
    3. Arbitration    — settles party disputes or issues guild contracts.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from enum import StrEnum
from pydantic import BaseModel, Field


# ─────────────────────── Enums ───────────────────────

class DispatchType(StrEnum):
    BOUNTY      = "bounty"       # combat/hunt focused
    SURVEY      = "survey"       # exploration focused
    LOGISTICS   = "logistics"    # delivery/hauling focused
    RECON       = "recon"        # intelligence focused


class RepairStatus(StrEnum):
    PRISTINE    = "pristine"
    WORN        = "worn"
    SHATTERED   = "shattered"


# ─────────────────────── State ───────────────────────

class KodrikEncounterState(BaseModel):
    active: bool = False
    repaired_items_count: int = 0
    dispatches_given: int = 0
    trust_level: int = 0  # -3 to 3
    is_busy: bool = False # if busy, he's at the desk and won't look up


# ─────────────────────── Results ───────────────────────

@dataclass(frozen=True)
class DispatchResult:
    dispatch_type: DispatchType
    location_name: str
    breadcrumb: str
    reward_hint: str
    flavor: str


@dataclass(frozen=True)
class RepairResult:
    item_name: str
    cost: int
    success: bool
    flavor: str


# ─────────────────────── Flavor Text ───────────────────────

_DISPATCH_FLAVOR: list[str] = [
    "Kodrik doesn't look up from the map. He taps a scarred finger on a blank space. 'I need clean data here. Go. Come back when the lines match the ground.'",
    "He slides a wax-sealed scroll across the table. 'The contract is clear. The reward is fixed. Don't make me update the casualty ledger.'",
    "A heavy sigh. 'The Ledge is shifting again. I need someone fast to check the northern pass. Are you fast, or are you just loud?'",
]

_REPAIR_FLAVOR: list[str] = [
    "He takes the armor with a look of genuine offense. 'Who did this to a decent plate? Sit. Don't touch anything on the bench.'",
    "Kodrik works in silence for several minutes. The sound of a hammer on steel is the only conversation you'll get. 'Fixed. Don't break it the same way twice.'",
    "He inspects the gear with ink-stained hands. 'Functional. Not pretty, but it'll hold. That's ten silver for the guild fund.'",
]


# ─────────────────────── Logic ───────────────────────

class GuildmasterKodrik:
    def __init__(self, state: KodrikEncounterState | None = None) -> None:
        self.encounter = state or KodrikEncounterState()

    def get_dispatch(self, dispatch_type: DispatchType) -> DispatchResult:
        """Assign a new task/lore breadcrumb to the party."""
        self.encounter.dispatches_given += 1
        
        locations = ["Whispering Woods", "Iron Ledge Pass", "The Sunken Vault", "The Feral Outpost"]
        breadcrumbs = [
            "Something is moving in the canopy that doesn't have a shadow.",
            "The altitude is causing reality glitches in the compasses.",
            "The old world foundations are leaking something blue.",
            "The supply line has been quiet for too long. Check the gates.",
        ]
        
        return DispatchResult(
            dispatch_type=dispatch_type,
            location_name=random.choice(locations),
            breadcrumb=random.choice(breadcrumbs),
            reward_hint="Guild Favor and Silver",
            flavor=random.choice(_DISPATCH_FLAVOR)
        )

    def repair_gear(self, item_name: str, silver_available: int) -> RepairResult:
        """Repair a piece of equipment."""
        cost = 10
        if silver_available < cost:
            return RepairResult(
                item_name=item_name,
                cost=cost,
                success=False,
                flavor="'I run a guild, not a charity. Come back when you can pay the bench fee.'"
            )
        
        self.encounter.repaired_items_count += 1
        return RepairResult(
            item_name=item_name,
            cost=cost,
            success=True,
            flavor=random.choice(_REPAIR_FLAVOR)
        )
