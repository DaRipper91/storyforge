"""
MadameHaylie — encounter logic for Madame Haylie (The Innkeeper / Jon's wife).

Architecture:
  - MadameHaylie is a pure service class. No direct GameState mutations.
  - Primary mechanic: trigger_bailout() — guaranteed escape from Jon's conversational
    trap after a critical escape fail (jon.encounter.bailout_available == True).
  - Her inn environment inherits the same SceneGenre as Jon's shop.
  - HaylieEncounterState tracks bailouts used and scoldings delivered.

Mechanics:
  1. Bailout Protocol — interrupts Jon, scolds him, guarantees party exit
  2. Genre-Adaptive Inn — inn stock/atmosphere mirrors the scene genre
  3. Running the Numbers — she knows exactly how much revenue Jon has cost them today
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from pydantic import BaseModel

from storyforge.encounters.shopkeeper_jon import JonEncounterState, SceneGenre


# ─────────────────────── Flavor text pools ───────────────────────

_SCOLDING_LINES: list[str] = [
    "A woman appears from the back room with the energy of someone who has been listening to this exact story for eleven years. 'JON.' He stops mid-syllable.",
    "The back door opens. Madame Haylie does not raise her voice, which is somehow more frightening than if she had. 'Jon. These people need to leave.' There is a silence. Jon closes his mouth.",
    "From somewhere behind the shelves: 'Jonathan.' One word. Jon goes very still, like a dog that has just heard a tone it recognizes. 'Are you holding customers again?' He is not going to answer that.",
    "A hand appears around the doorframe holding a ledger. The ledger is slapped onto the counter with surgical precision. 'Jon. I have done the math. You have talked this party out of two additional purchases in the time you have been telling that story. I need you to let them go.' He begins to apologize to the ledger.",
    "She comes in from the inn side carrying linens with the posture of a woman who runs this entire operation and is aware of it. 'Jon, sweetheart, what did we talk about?' He knows what they talked about. The party is free to leave.",
]

_JON_CHASTENED_LINES: list[str] = [
    "'Right, right — sorry, Haylie, I just — yes. Okay.' He waves you toward the door with genuine warmth and only mild disappointment. 'Come back when you've got time for the rest of the story.'",
    "Jon looks at his shoes. 'She's right. I do this. Okay. You go ahead.' He gestures broadly toward freedom. 'Safe travels. Tell Dale I said hi.' You still don't know who Dale is.",
    "'I was just finishing up!' He isn't. He knows he isn't. His wife knows he isn't. Everybody knows he isn't. You are free. Go.",
    "Jon raises both hands in mild surrender. 'Alright, alright. Haylie's the boss.' This is clearly true in every possible sense. He holds the door open himself. He is still talking as you leave but it's receding now.",
    "'That's — yeah, fair.' He nods at you with genuine friendliness. 'No hard feelings. Come by for dinner sometime. Haylie makes a thing.' Madame Haylie, from the back: 'I do not make a *thing*.' 'She makes a *thing*.'"
]

_HAYLIE_SIGN_OFFS: list[str] = [
    "She gives you a nod that says *go, quickly, before he remembers the boat story* and disappears back through the door.",
    "She turns to you with the brief, efficient smile of a woman who has rescued approximately four hundred customers from this exact situation. 'Sorry about that. Safe travels.' She is gone before you can thank her.",
    "She is already back through the door, which closes with the decisive click of a woman who has places to be.",
    "She looks at you with something like solidarity, then at Jon with something like affection, then back to her work. The exit is right there.",
    "She doesn't wait for a response. She has an inn to run. You have a door to use. The universe is in alignment.",
]

# Genre-adaptive inn offerings (what Haylie is running out back)
_INN_DESCRIPTIONS: dict[SceneGenre, str] = {
    SceneGenre.FANTASY:
        "Warm rooms upstairs, a hearth that hasn't gone out in years, and a stew that Jon is not allowed to describe because every time he does, people leave.",
    SceneGenre.SCI_FI:
        "Pressurized quarters with functional recycled-air systems. She's installed a signal booster on the roof. Jon tried to explain it to a customer once. She disconnected him.",
    SceneGenre.CYBERPUNK:
        "Clean bunks, no surveillance, and a faraday cage option for those with neural implants who need to sleep without interference. Jon has never once understood what faraday means but is very proud of it.",
    SceneGenre.HORROR:
        "She keeps all the lights on. Full spectrum. There's salt at every threshold and she checks the mirrors every morning. Jon thinks she's 'a little particular.' She is keeping everyone alive.",
    SceneGenre.WESTERN:
        "Rooms, hot water, and a strict policy of no shooting indoors that she enforces personally. Jon tried to make exceptions. There are no exceptions.",
    SceneGenre.POST_APOCALYPTIC:
        "Filtered air, reinforced walls, and a rotation schedule she manages personally. She has the only copy of the supply manifest. This is intentional.",
}


# ─────────────────────── Encounter state ───────────────────────

class HaylieEncounterState(BaseModel):
    """
    Session-level state for Haylie's presence in the inn/shop.
    """
    active: bool = True
    bailouts_delivered: int = 0
    total_revenue_saved: int = 0   # tracked for flavor
    jon_scoldings: int = 0


# ─────────────────────── Result dataclass ───────────────────────

@dataclass(frozen=True)
class BailoutResult:
    triggered: bool
    scolding: str         # Haylie interrupting Jon
    jon_response: str     # Jon's chastened reply
    haylie_sign_off: str  # Her exit line
    inn_note: str         # Brief note about the inn (genre-adaptive)
    bailouts_delivered: int


# ─────────────────────── Service class ───────────────────────

class MadameHaylie:
    """
    Pure service layer for Madame Haylie.

    trigger_bailout() is the core mechanic. It:
      1. Requires jon_encounter.bailout_available == True
      2. Clears the story trap from JonEncounterState
      3. Returns deterministic flavor text — no LLM call needed
      4. Never fails
    """

    def __init__(self, state: HaylieEncounterState | None = None) -> None:
        self.encounter = state or HaylieEncounterState()

    def trigger_bailout(
        self,
        jon_encounter: JonEncounterState,
        genre: SceneGenre = SceneGenre.FANTASY,
    ) -> BailoutResult | None:
        """
        Interrupt Jon's conversational trap and guarantee party escape.

        Returns None if bailout is not available (no critical fail pending).
        Mutates jon_encounter in place — caller must persist both states.
        """
        if not jon_encounter.bailout_available:
            return None

        # Clear Jon's trap
        jon_encounter.story_trap_active = False
        jon_encounter.story_trap_turns_remaining = 0
        jon_encounter.bailout_available = False

        self.encounter.bailouts_delivered += 1
        self.encounter.jon_scoldings += 1

        return BailoutResult(
            triggered=True,
            scolding=random.choice(_SCOLDING_LINES),
            jon_response=random.choice(_JON_CHASTENED_LINES),
            haylie_sign_off=random.choice(_HAYLIE_SIGN_OFFS),
            inn_note=_INN_DESCRIPTIONS[genre],
            bailouts_delivered=self.encounter.bailouts_delivered,
        )

    def get_inn_description(self, genre: SceneGenre) -> str:
        """Return the genre-adaptive inn description."""
        return _INN_DESCRIPTIONS[genre]

    @property
    def can_bailout(self) -> bool:
        """Always True — Haylie is always available to intervene if needed."""
        return True
