"""
QueenDAnnа — encounter logic for Queen D.Anna (The Traveling Sovereign).

Architecture:
  - QueenDAnna is a pure service class. No direct GameState mutations.
  - Primary mechanic: address() — how you greet her determines her mood.
  - Secondary mechanic: petition() — ask her for a boon; she grants or declines.
  - QueenDAnnaEncounterState tracks addresses, petitions, and whether she is currently
    offended.

Companions:
  - Keeva (Angelic Hound): Holds divine authority over the space.
  - Bink Bink (Black Cat): Holds quality control authority over the shelves.
  - D.Anna's relationship to both is simply "correct." She does not explain them.
  - Neither pet acknowledges the other's domain; both acknowledge D.Anna's.

Mechanics:
  1. Royal Address    — correct address earns Favor; wrong address earns a lesson
  2. Royal Petition   — party can request a Decree; she grants boons on good standing
  3. Royal Dismissal  — she will leave when she is ready, not before
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import StrEnum
from pydantic import BaseModel


# ─────────────────────── Enums ───────────────────────


class AddressForm(StrEnum):
    """How the party chooses to address the Queen."""

    PROPER = "proper"  # "Your Majesty" — correct
    FRIENDLY = "friendly"  # "Your Grace" — acceptable, mildly noted
    CASUAL = "casual"  # first name — incorrect, earns a correction
    WRONG = "wrong"  # "Hey you" / completely off — earns an incident


class PetitionType(StrEnum):
    """What the party petitions the Queen for."""

    BLESSING = "blessing"  # morale boon — party advantage on next check
    INTELLIGENCE = "intelligence"  # she shares what she knows of the road ahead
    ENDORSEMENT = "endorsement"  # her seal opens doors (better NPC relations)
    MERCY = "mercy"  # she intervenes on a party member's behalf


# ─────────────────────── Flavor text pools ───────────────────────

_ADDRESS_PROPER: list[str] = [
    "She looks up from whatever she was reading with the precise attention of someone who is always aware of exactly who enters a room. 'Well. Someone has manners.' She gestures for you to approach. This is not an invitation. This is a concession.",
    "A slight incline of her head. Not quite a nod. More the acknowledgment that a correct thing has occurred. 'Your Majesty.' She repeats your address back to you as confirmation that it was, in fact, correct. You feel as if you have passed an exam you did not know you were taking.",
    "She sets down her cup with the deliberate patience of a woman who has been greeted incorrectly by heads of state and chooses not to revisit the experience. 'Better.' This is, from Queen D.Anna, nearly a compliment.",
]

_ADDRESS_FRIENDLY: list[str] = [
    "Her expression does not change. This is, somehow, expressive. 'Your Grace is the address for a duchess. I am a queen. However, I will allow it, as the distinction appears to require more geography than you may have studied.' She waits.",
    "'Your Grace.' She considers this. 'Technically incorrect. Diplomatically adequate. We will proceed.' She makes a small note in her ledger. You are not sure what the note says. You are sure you don't want to be on the wrong side of it.",
    "A pause. Not an uncomfortable one. A calibrating one. 'I see you have some education. Enough to attempt the proper form, not quite enough to land it. We'll call it a reasonable effort.' This is, apparently, high praise.",
]

_ADDRESS_CASUAL: list[str] = [
    "She turns to face you fully. This is more alarming than you expected. 'My name,' she says, with the patience of someone who has corrected this error across seventeen kingdoms, 'is Queen D.Anna. I am addressed as Your Majesty, or as Queen D.Anna if we are to be informal, which we are not.' She waits. 'Try again.'",
    "'I will give you,' she says pleasantly, 'one opportunity to rephrase that.' The pleasantness is entirely real. So is the opportunity being singular.",
    "She does not raise her voice. This is somehow more alarming than if she had. 'In the interest of efficiency: I am a queen. Queens have titles. Titles exist because someone thought very hard about the most effective way to organize social order and this is what they arrived at. Your Majesty. Say it once for practice.' She waits.",
]

_ADDRESS_WRONG: list[str] = [
    "There is a silence of the kind that occurs when something has gone badly wrong but has not yet begun to visibly collapse. 'I,' she says, 'am going to say something, and I want you to listen carefully, because I will say it once.' She does. It takes four minutes. You understand the full history of the concept of sovereignty by the end of it. You will address her correctly from now on.",
    "She puts down whatever she was holding. She folds her hands. She looks at you with the specific calm of a woman who has had people executed for this and has since adopted a more measured approach to the same stimulus. What follows is the most comprehensive explanation of proper address you have ever received. When it is over, you feel educated.",
    "'Fascinating,' she says, and nothing in her face suggests fascination. What follows is a lesson. The lesson is thorough. By the end of it several people in nearby seats have also learned something and didn't ask to.",
]

_PETITION_BLESSING: list[str] = [
    "She considers this. 'A blessing. You want a *blessing*.' She says the word as if testing its weight. Then: 'Very well. Come here.' She speaks three words in a language that is old enough to predate the concept of writing it down. You feel something settle into your bones. Something like certainty. 'Go do something useful with it.'",
    "'You are asking me to bless you.' A beat. 'I'll do it. But understand that a royal blessing is a contract. It does not simply help you. It commits you to a standard. If you embarrass me with what you do next, I will find out.' You believe her completely. The blessing settles around your shoulders like something that has expectations.",
    "She does not hesitate. 'Kneel.' You kneel. The blessing is brief and absolute. When you stand, something is different about the air around you. She is already back to her reading. 'Don't waste it.'",
]

_PETITION_INTELLIGENCE: list[str] = [
    "She closes her ledger. This is, apparently, the action that precedes sharing information. 'I stopped at the eastern crossroads three days ago. There were signs — and I am using *signs* in the technical sense, not the vague one — that the road past the mill is being watched. By whom, I cannot confirm. By something with patience, I can.' She opens her ledger again. 'That is what I know. I hope you use it more carefully than the last group who asked me for intelligence.'",
    "She tells you, concisely and without embellishment, what she has observed since arriving: the comings and goings, the ones who watched the exits, the conversation she overheard at the bar that the two participants believed was private. She has excellent recall. She has used it. 'The information is yours. The conclusions are yours to earn.'",
    "'Intelligence.' She looks at you. 'You want to know what I've seen.' She does not phrase this as a question. 'I'll tell you what I know. I'll tell you what I suspect. I'll tell you which one is which. That distinction,' she adds, 'is more important than most people realize, and most people do not realize it at all.'",
]

_PETITION_ENDORSEMENT: list[str] = [
    "She withdraws a small seal from somewhere in her coat. Not her pocket — somewhere with more gravity than a pocket. She presses it to a square of paper with the authority of someone who has been doing this for decades and means it every time. 'Present this. If anyone fails to honor it, send word.' She puts the seal away. 'I enjoy hearing that people have been sensible.'",
    "'An endorsement.' She seems to find this reasonable. 'You have conducted yourself adequately. I will endorse you.' The letter she writes takes approximately thirty seconds. The handwriting is extraordinary. The language is formal, precise, and sounds, if read aloud, like a promise that it would be unwise to test. 'This should open some doors. Mind the ones it closes.'",
    "She nods once. 'I'll write it.' The resulting letter is a single paragraph. It is the most efficient and thorough endorsement that has ever been put to paper. She hands it over without reading it back. She does not need to. She wrote it right the first time.",
]

_PETITION_MERCY: list[str] = [
    "She looks at you. Then at the one you're asking on behalf of. Then back at you. 'They've put themselves in a situation.' This is not a question. 'And you're asking me to intervene.' Also not a question. A pause. Then she stands up, which is, apparently, the answer. 'Show me the situation. I'll decide if it merits mercy. Mercy is not a reflex. It's a judgment.'",
    "'You want me to intervene.' A breath. 'Tell me everything. Accurately. If I find out later that you left something out, the mercy I'm about to exercise will become a lesson instead, and lessons from me are significantly less comfortable.' You tell her everything. She listens with the full attention of someone who will remember all of it. 'I see,' she says. Then she handles it.",
    "She does not sigh. She does not express frustration. She looks at the situation with the efficiency of a woman who has seen considerably worse and still acted correctly. 'Fine. I'll handle this.' She handles it. It is, objectively, handled.",
]

_DECLINE_WRONG_ADDRESS: list[str] = [
    "She raises one finger. 'Before we discuss what you want: address me correctly. Then we'll see.' She waits.",
    "'I don't conduct petitions with people who have not yet demonstrated they know who they're talking to.' She picks up her cup. 'Come back when you've remembered the form.'",
]

_DECLINE_LOW_FAVOR: list[str] = [
    "'You are asking for something before establishing any reason I should grant it.' Not accusatory. Accurate. 'Address me properly. Behave as though this interaction has standards. Then petition me.' She returns to her book. This is not dismissal. This is instruction.",
    "'I grant petitions based on standing. You have not established standing.' She looks at you with the patience of someone who has all day and is perfectly comfortable using it. 'Start over. Correctly.'",
]


# ─────────────────────── Encounter state ───────────────────────


class QueenDAnnaEncounterState(BaseModel):
    """Session-level state for Queen D.Anna's presence in the tavern."""

    active: bool = True
    correct_addresses: int = 0
    incorrect_addresses: int = 0
    petitions_granted: int = 0
    petitions_declined: int = 0
    is_offended: bool = False
    favor: int = 0  # −2 to +3; gates petitions


# ─────────────────────── Result dataclasses ───────────────────────


@dataclass(frozen=True)
class AddressResult:
    form: AddressForm
    correct: bool
    response: str
    favor_delta: int
    new_favor: int
    is_offended: bool


@dataclass(frozen=True)
class PetitionResult:
    granted: bool
    petition_type: PetitionType | None
    response: str
    favor_cost: int
    new_favor: int


# ─────────────────────── Service class ───────────────────────


class QueenDAnna:
    """
    Pure service layer for Queen D.Anna.

    address() determines standing.
    petition() spends standing for a boon.
    """

    _FAVOR_THRESHOLDS = {
        PetitionType.BLESSING: 1,
        PetitionType.INTELLIGENCE: 1,
        PetitionType.ENDORSEMENT: 2,
        PetitionType.MERCY: 3,
    }
    _FAVOR_COSTS = {
        PetitionType.BLESSING: 1,
        PetitionType.INTELLIGENCE: 1,
        PetitionType.ENDORSEMENT: 2,
        PetitionType.MERCY: 2,
    }

    def __init__(self, state: QueenDAnnaEncounterState | None = None) -> None:
        self.encounter = state or QueenDAnnaEncounterState()

    def address(self, form: AddressForm) -> AddressResult:
        """Greet the Queen. Returns favor delta and her response."""
        e = self.encounter

        if form == AddressForm.PROPER:
            delta = 1
            e.correct_addresses += 1
            e.is_offended = False
            response = random.choice(_ADDRESS_PROPER)
        elif form == AddressForm.FRIENDLY:
            delta = 0
            e.correct_addresses += 1
            response = random.choice(_ADDRESS_FRIENDLY)
        elif form == AddressForm.CASUAL:
            delta = -1
            e.incorrect_addresses += 1
            response = random.choice(_ADDRESS_CASUAL)
        else:  # WRONG
            delta = -2
            e.incorrect_addresses += 1
            e.is_offended = True
            response = random.choice(_ADDRESS_WRONG)

        e.favor = max(-3, min(3, e.favor + delta))

        return AddressResult(
            form=form,
            correct=form in (AddressForm.PROPER, AddressForm.FRIENDLY),
            response=response,
            favor_delta=delta,
            new_favor=e.favor,
            is_offended=e.is_offended,
        )

    def petition(self, petition_type: PetitionType) -> PetitionResult:
        """Request a boon from the Queen. Requires sufficient favor."""
        e = self.encounter

        if e.is_offended:
            e.petitions_declined += 1
            return PetitionResult(
                granted=False,
                petition_type=None,
                response=random.choice(_DECLINE_WRONG_ADDRESS),
                favor_cost=0,
                new_favor=e.favor,
            )

        threshold = self._FAVOR_THRESHOLDS[petition_type]
        if e.favor < threshold:
            e.petitions_declined += 1
            return PetitionResult(
                granted=False,
                petition_type=None,
                response=random.choice(_DECLINE_LOW_FAVOR),
                favor_cost=0,
                new_favor=e.favor,
            )

        cost = self._FAVOR_COSTS[petition_type]
        e.favor = max(-3, e.favor - cost)
        e.petitions_granted += 1

        text_pool = {
            PetitionType.BLESSING: _PETITION_BLESSING,
            PetitionType.INTELLIGENCE: _PETITION_INTELLIGENCE,
            PetitionType.ENDORSEMENT: _PETITION_ENDORSEMENT,
            PetitionType.MERCY: _PETITION_MERCY,
        }
        response = random.choice(text_pool[petition_type])

        return PetitionResult(
            granted=True,
            petition_type=petition_type,
            response=response,
            favor_cost=cost,
            new_favor=e.favor,
        )

    @property
    def standing_label(self) -> str:
        f = self.encounter.favor
        if f >= 3:
            return "Esteemed"
        if f >= 1:
            return "Acknowledged"
        if f == 0:
            return "Neutral"
        if f >= -1:
            return "Noted (Unfavorably)"
        return "In Poor Standing"
