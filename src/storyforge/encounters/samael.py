"""
SamaelTheAscended — encounter logic for Samael (The Bored Demigod).

Architecture:
  - SamaelTheDemigod is a pure service class. No GameState mutations.
  - Samael provides cryptic lore/hints when the party asks for guidance.
  - He uses divine cosmic power for completely mundane tasks while talking.
  - SamaelEncounterState tracks consultation history and apathy escalation.

Mechanics:
  1. Lore Oracle      — cryptic but valid campaign hints by category
  2. Mundane Divinity — he is always doing something absurd with omnipotence
  3. Apathy Escalation — more consultations = more theatrical sighing
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from enum import StrEnum
from pydantic import BaseModel


# ─────────────────────── Enums ───────────────────────

class MundaneActivity(StrEnum):
    """What Samael is doing with the full power of creation right now."""
    OPENING_JAR           = "opening_jar"
    PETTING_BINK_BINK     = "petting_bink_bink"
    MAKING_COFFEE         = "making_coffee"
    ALPHABETIZING_SHELF   = "alphabetizing_shelf"
    UNTANGLING_EARBUDS    = "untangling_earbuds"
    RIPENING_AVOCADO      = "ripening_avocado"
    DRYING_WET_SOCKS      = "drying_wet_socks"
    PARALLEL_PARKING      = "parallel_parking"
    SKIPPING_AD           = "skipping_ad"
    FINDING_TV_REMOTE     = "finding_tv_remote"
    COOLING_SOUP          = "cooling_soup"
    FOLDING_FITTED_SHEET  = "folding_fitted_sheet"


_MUNDANE_DESCRIPTIONS: dict[MundaneActivity, str] = {
    MundaneActivity.OPENING_JAR:          "He is using the fundamental force that shapes galaxies to open a jar of pickles.",
    MundaneActivity.PETTING_BINK_BINK:    "He is devoting the omniscient focus of a divine mind to ensuring Bink Bink is scratched at precisely the right pressure behind the left ear.",
    MundaneActivity.MAKING_COFFEE:        "He is willing the Maillard reaction into perfection at the molecular level, one bean at a time, for a cup of coffee.",
    MundaneActivity.ALPHABETIZING_SHELF:  "He is using precognition to determine the correct alphabetical order of Jon's inventory, which Jon will immediately destroy.",
    MundaneActivity.UNTANGLING_EARBUDS:   "He is applying the same omnipotent will that parted dimensional rifts to a set of tangled earbuds.",
    MundaneActivity.RIPENING_AVOCADO:     "He is accelerating the entropy of a single avocado to achieve peak ripeness, a task he describes as 'more satisfying than the last war.'",
    MundaneActivity.DRYING_WET_SOCKS:     "He is using his command over thermodynamic laws to dry a pair of socks. He looks completely at peace.",
    MundaneActivity.PARALLEL_PARKING:     "He is using divine spatial awareness to parallel park Jon's delivery cart into a gap that is, by his own admission, 'technically impossible.'",
    MundaneActivity.SKIPPING_AD:          "He is reaching through the fabric of time to skip a pre-roll advertisement five seconds early.",
    MundaneActivity.FINDING_TV_REMOTE:    "He is scanning across all possible timelines to locate a television remote that Jon sat on.",
    MundaneActivity.COOLING_SOUP:         "He is carefully redistributing thermal energy from a bowl of soup, which is 'too hot,' at the speed of light.",
    MundaneActivity.FOLDING_FITTED_SHEET: "He is applying the geometry of a higher dimension to fold a fitted bedsheet. He has been at this for forty minutes.",
}


class LoreCategory(StrEnum):
    ENEMY_WEAKNESS  = "enemy_weakness"
    LOCATION_SECRET = "location_secret"
    NPC_BACKSTORY   = "npc_backstory"
    ITEM_ORIGIN     = "item_origin"
    GENERAL_LORE    = "general_lore"
    TACTICAL_HINT   = "tactical_hint"


# ─────────────────────── Cryptic hint fallbacks ───────────────────────
# Used when no LLM is available. One per category.

_FALLBACK_HINTS: dict[LoreCategory, list[str]] = {
    LoreCategory.ENEMY_WEAKNESS: [
        "The thing that cannot be broken can still be moved. Movement is, when you consider it, a kind of breaking. Consider it.",
        "Every armor has a seam. Every seam is where two decisions met and disagreed. Find where they disagreed.",
        "What it fears most is what it once was. What it once was, it cannot name. Name it anyway.",
    ],
    LoreCategory.LOCATION_SECRET: [
        "The door that isn't there opens inward. Everything opens inward, if you press on the part that looks solid.",
        "What the map says ends is where the cartographer stopped paying attention. Cartographers get bored. I understand this.",
        "Underneath the underneath, there is a third underneath that everyone forgot to mention. This is typical.",
    ],
    LoreCategory.NPC_BACKSTORY: [
        "They were someone else first. Most people are. The question is which self they kept.",
        "The thing they never speak of is the thing that explains everything else. You already know what they never speak of. You've seen it in their eyes when they think no one is watching. I am always watching.",
        "Ask them about before. Before is where all the relevant information lives. After is just consequences.",
    ],
    LoreCategory.ITEM_ORIGIN: [
        "It was made in anger. Most of the useful things were. The question is whose anger and whether it's finished.",
        "Something was put into it that was never meant to come out. Whether that is a blessing depends entirely on what you need.",
        "It has been many things. What it is now is only its most recent opinion of itself.",
    ],
    LoreCategory.GENERAL_LORE: [
        "The event everyone agrees happened did not happen the way everyone agrees. This is true of every event. I was present for most of them. I was not always paying attention.",
        "The thing that seems like a coincidence is the universe being sloppy. The universe is frequently sloppy. It does not appreciate me pointing this out.",
        "What you are looking for and what you think you are looking for are adjacent but not identical. This is, in my experience, always the case.",
    ],
    LoreCategory.TACTICAL_HINT: [
        "The obvious approach will work. It will simply cost something you didn't expect to spend. Budget accordingly.",
        "There are three ways to solve this. Two of them will work. The third is more interesting. I recommend the third.",
        "The thing standing between you and the answer is not as large as it appears from here. Most things aren't. Distance is deceptive. I say this from a position of significant altitude.",
    ],
}

_APATHY_INTROS: list[str] = [
    "He glances over without turning his head.",
    "He pauses what he is doing for approximately one second.",
    "He does not look up. A response arrives nonetheless.",
    "He exhales in a way that suggests the heat death of the universe cannot come soon enough.",
    "He sets down what he is doing with the resigned grace of someone who has answered this question across seventeen timelines.",
]

_APATHY_OUTROS: list[str] = [
    "He returns to what he was doing.",
    "He appears to already have forgotten this conversation.",
    "He has resumed the activity. The activity is, apparently, more urgent.",
    "He has closed his eyes. He may be meditating. He may be simply done.",
    "Bink Bink jumps into his lap. He addresses the cat with more enthusiasm than he addressed you.",
]


# ─────────────────────── Encounter state ───────────────────────

class SamaelEncounterState(BaseModel):
    """
    Session-level state for Samael's presence in the shop.
    Samael is always present but engagement is optional.
    """
    active: bool = True
    consultations: int = 0
    total_useful_responses: int = 0
    current_mundane_activity: str = MundaneActivity.PETTING_BINK_BINK


# ─────────────────────── Result dataclass ───────────────────────

@dataclass(frozen=True)
class LoreResult:
    category: LoreCategory
    cryptic_hint: str
    mundane_activity: MundaneActivity
    mundane_description: str
    apathy_intro: str
    apathy_outro: str
    apathy_level: int        # 1–5
    consultation_number: int


# ─────────────────────── Service class ───────────────────────

class SamaelTheDemigod:
    """
    Pure service layer for Samael encounters.
    Returns LoreResult objects; no state mutations to GameState.
    """

    APATHY_ESCALATION_RATE = 2  # every N consultations bumps apathy level

    def __init__(self, state: SamaelEncounterState | None = None) -> None:
        self.encounter = state or SamaelEncounterState()

    def get_current_activity(self) -> tuple[MundaneActivity, str]:
        """Return what Samael is currently doing and a description of it."""
        activity = MundaneActivity(self.encounter.current_mundane_activity)
        return activity, _MUNDANE_DESCRIPTIONS[activity]

    def consult(self, category: LoreCategory) -> LoreResult:
        """
        The party asks Samael for guidance.
        Returns a LoreResult with context for the LLM prompt + fallback hint text.
        """
        self.encounter.consultations += 1
        apathy = min(5, 1 + (self.encounter.consultations // self.APATHY_ESCALATION_RATE))

        # Rotate to a new mundane activity
        activities = list(MundaneActivity)
        new_activity = activities[self.encounter.consultations % len(activities)]
        self.encounter.current_mundane_activity = new_activity

        hints = _FALLBACK_HINTS[category]
        hint = hints[self.encounter.consultations % len(hints)]

        intro = _APATHY_INTROS[min(apathy - 1, len(_APATHY_INTROS) - 1)]
        outro = _APATHY_OUTROS[min(apathy - 1, len(_APATHY_OUTROS) - 1)]

        self.encounter.total_useful_responses += 1

        return LoreResult(
            category=category,
            cryptic_hint=hint,
            mundane_activity=new_activity,
            mundane_description=_MUNDANE_DESCRIPTIONS[new_activity],
            apathy_intro=intro,
            apathy_outro=outro,
            apathy_level=apathy,
            consultation_number=self.encounter.consultations,
        )

    def get_llm_context(self, category: LoreCategory) -> dict:
        """
        Build the context dict to pass alongside the npc_samael.md system prompt
        when calling the Gemini LLM for a richer response.
        """
        activity, desc = self.get_current_activity()
        return {
            "mundane_activity": activity.value,
            "mundane_description": desc,
            "lore_category": category.value,
            "consultation_number": self.encounter.consultations,
            "apathy_level": min(5, 1 + (self.encounter.consultations // self.APATHY_ESCALATION_RATE)),
        }
