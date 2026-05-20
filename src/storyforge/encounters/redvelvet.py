"""
FireyRedVelvet — encounter logic for Firey RedVelvet (The Tavern Performer).

Architecture:
  - FireyRedVelvet is a pure service class. No direct GameState mutations.
  - Primary mechanic: perform() — she puts on a show; party can watch, tip, or heckle.
  - Mood escalates with tips and craters with heckles.
  - At BLAZING mood, her performance grants a real mechanical boon.
  - At COLD mood, she performs anyway. It's just not for you.

Mechanics:
  1. Performance     — she performs; flavor text scales with current mood
  2. Tip (silver)    — spend silver → mood goes up → better performances
  3. Heckle          — she responds; mood goes down; she is not rattled, merely disappointed
  4. Request a Song  — she picks one appropriate to the party's current situation
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from enum import IntEnum, StrEnum
from pydantic import BaseModel


# ─────────────────────── Enums ───────────────────────

class Mood(IntEnum):
    COLD    = 0   # baseline; polished but impersonal
    WARM    = 1   # engaged; she's enjoying herself
    HOT     = 2   # she's in it; the whole tavern knows it
    BLAZING = 3   # full power; sparks may be literal


class SongRequest(StrEnum):
    """What kind of song the party requests."""
    BATTLE_HYMN  = "battle_hymn"   # morale for combat
    LULLABY      = "lullaby"       # rest and recovery
    DRINKING_SONG = "drinking_song" # social lubrication
    DIRGE        = "dirge"         # someone had a bad day
    MYSTERY      = "mystery"       # let her decide


# ─────────────────────── Flavor text pools ───────────────────────

_PERFORMANCE_COLD: list[str] = [
    "She performs. There is no other word for it. The technique is perfect, the fire goes where it's supposed to go, and when it's over she catches the torch in one hand without looking. A small scatter of applause. She acknowledges it with a single nod. She has performed for kings. She has performed for empty rooms. The fire doesn't care either way, and neither does she.",
    "The performance is technically flawless. The fire describes a tight arc, she walks through the space with the economy of someone who has calculated exactly how much energy this audience deserves, and lands it clean. It's like watching someone maintain machinery that happens to be on fire. Impressive. Formal. Not warm.",
    "She opens with a flourish that is more statement than invitation: *I am performing now. You may watch.* The fire moves correctly. Her expression is professional. She has been doing this long enough to do it well on autopilot, and that is precisely what you are watching.",
]

_PERFORMANCE_WARM: list[str] = [
    "Something shifts partway through. A small choice — the arc goes wider, she holds a beat longer than the routine calls for, she glances at the audience with something that isn't quite a smile but is adjacent to one. The fire breathes. People put down their drinks. This is better than it was a moment ago.",
    "She decides, somewhere in the middle of the performance, that this crowd is worth showing off for. The fire responds to the decision. She's doing things the routine doesn't include now — an improvised beat, a pause that makes three people hold their breath. When she finishes, the applause is real.",
    "The performance warms by degrees. She starts where she always starts, technical and controlled, but the crowd gives something back and she takes it, and after that the fire is doing things it wasn't planning to do. The room comes with her. This is what it's supposed to feel like.",
]

_PERFORMANCE_HOT: list[str] = [
    "The whole tavern knows it now. She's not performing *at* the room; she's performing *with* it, and the fire knows the difference. It moves like it has opinions. People have set down their drinks. One person has stopped a conversation mid-sentence and not resumed it. This is the performance she came to give. You're watching it.",
    "At this level, the performance becomes something else entirely — not a show but an event. The fire behaves as though it is glad to be here. She is moving through the space the way water moves through a river, all of it going in the same direction at the same speed for the same reason. The applause when she finishes lasts longer than it should. Nobody minds.",
    "The room is hers. There's no other way to say it. The fire goes places it doesn't usually go, she extends the finale until it is nearly past bearing and then pulls it back just in time, and when she's done she doesn't take a bow so much as simply stop, which is more effective. The tavern takes a moment to remember it is a tavern.",
]

_PERFORMANCE_BLAZING: list[str] = [
    "This is the one she saves. Not for occasions — she doesn't believe in saving things for occasions — but for moments. This is a moment. The fire does not behave like fire. It behaves like fire that has made a decision. She moves through it without looking at it because she doesn't have to. When she's done, the silence lasts three full seconds before anyone remembers to breathe. The applause that follows is the honest kind. She stands in it, and she lets herself.",
    "Something happens during this performance that doesn't have a clean technical explanation. The fire moves ahead of her — not out of control, but anticipating. The room is absolutely still. She takes it somewhere it didn't know it could go and brings it back, and when it's over there's a moment where everyone present understands, for just a second, that they watched something that won't happen exactly this way again. She catches the last torch. She exhales. She looks at the room like she knew it would happen. She did.",
    "BLAZING. That's the only word for it and she probably invented it. The fire doesn't just perform with her — it performs *for* her. She is not working. She is moving through something she built for herself a long time ago and has been refining ever since, and tonight it is finished. When it ends, nobody talks for a moment. Then everybody talks at once. She accepts a drink from the bar without asking for it. This is the correct response.",
]

_TIP_RESPONSES: list[str] = [
    "She looks at the silver. She looks at you. 'Generous.' She doesn't say it like a compliment exactly. She says it like an acknowledgment of a fact that she finds interesting. The silver disappears. Something in the temperature of the room goes up half a degree.",
    "She takes the silver without looking away from you. 'You have taste.' Whether she means taste in performance or taste in tipping is unclear. Possibly both. The evening gets easier.",
    "'Appreciated.' One word. She means it. The next time she performs, you'll see where the silver went.",
    "She pockets the tip with the practiced ease of someone who has received tips for a long time and still receives each one as though it confirms something she already knew. 'Thank you.' The fire in the next performance goes a little further than it planned to.",
]

_HECKLE_RESPONSES: list[str] = [
    "She finishes what she was doing first. This is important — she doesn't react, she *finishes*. Then she looks at you with an expression that has no heat in it at all, which is somehow worse than if it did. 'I've performed for people who've tried harder than that to put me off and I've performed for empty rooms and I've performed in weather that wanted me dead, and I'm still here. Try something harder or don't bother.' She goes back to it.",
    "A pause. Not a rattled pause — a *deliberate* one. She turns to look at you with the calm of someone who has had approximately this exact heckle before and has already composed the response. 'You're going to want to reconsider the next one.' She turns back. The fire doesn't seem to agree with you either.",
    "She doesn't stop. She doesn't look. 'Next one's for free,' she says to the room, meaning you, 'after that you're paying for my time and I charge more than the drink you're holding.' The room finds this funnier than you'd like. She was counting on that.",
    "'Heard it,' she says. Not to you specifically. Just into the air. Informational. She continues the performance. It is somehow better than it was a moment ago. This is deliberate. You have done her a favor and she will not thank you for it.",
]

_SONG_BATTLE_HYMN: list[str] = [
    "She picks the tempo up. The song she chooses is old — old enough that the words don't matter anymore, just the forward motion of it. By the third verse the room is doing something approximating rhythm. You leave with it still going, and you notice that your shoulders are back further than they were when you walked in.",
    "The battle hymn she selects isn't one you know, but your feet do. Something ancient moves through it. She doesn't perform it for the room; she performs it *at* whatever you're about to walk into. When it ends, you feel ready. You weren't before.",
]

_SONG_LULLABY: list[str] = [
    "She finds the one that doesn't ask anything of you. The fire lowers. The room quiets. When it's over several people don't move for a moment, and the ones who needed rest most get it without trying. Something unclenches. You'll sleep better than you should.",
    "The lullaby she chooses isn't soft exactly — it's *still*. There's a difference. The still kind of song that settles around you like something that has been waiting. The room breathes slower. You'll rest tonight.",
]

_SONG_DRINKING_SONG: list[str] = [
    "It's the one everyone knows. Nobody knows why they know it or where it came from but everyone in the room knows it, including people who have never heard it before tonight, and by the chorus the whole tavern is contributing something. The evening improves by exactly the amount a good drinking song can improve an evening, which is more than it has any right to.",
    "She makes a choice you wouldn't have made and it's the right choice. The song is technically a drinking song but it's doing something else underneath — it's making the room feel like the room is on your side. It is. For now. Enjoy it.",
]

_SONG_DIRGE: list[str] = [
    "She doesn't ask who it's for. She picks one that has space in it for whatever you've lost, and she performs it without embellishment, and when it's done she doesn't look at you, which is the right choice. The grief gets somewhere it needed to go. That's what the song was for.",
    "It's the correct song. Not the prettiest one. The one that makes room. She holds the end longer than you expect, and then it's over, and you're still here, and that's enough.",
]


# ─────────────────────── Encounter state ───────────────────────

class RedVelvetEncounterState(BaseModel):
    """Session-level state for Firey RedVelvet's presence in the tavern."""
    active: bool = True
    current_mood: int = Mood.WARM          # starts at WARM — she's already been here a while
    performances_given: int = 0
    total_tips_silver: int = 0
    heckles_received: int = 0


# ─────────────────────── Result dataclasses ───────────────────────

@dataclass(frozen=True)
class PerformanceResult:
    performance_text: str
    mood: Mood
    grants_boon: bool           # True at BLAZING — party gets inspiration
    boon_description: str | None


@dataclass(frozen=True)
class TipResult:
    response: str
    silver_spent: int
    mood_before: Mood
    mood_after: Mood
    mood_changed: bool


@dataclass(frozen=True)
class HeckleResult:
    response: str
    mood_before: Mood
    mood_after: Mood


@dataclass(frozen=True)
class SongResult:
    song_type: SongRequest
    performance_text: str
    mood: Mood


# ─────────────────────── Service class ───────────────────────

class FireyRedVelvet:
    """
    Pure service layer for Firey RedVelvet.

    perform() → watch her show.
    tip(silver) → improve her mood.
    heckle() → worsen her mood (she handles it).
    request_song(type) → she picks the right one.
    """

    def __init__(self, state: RedVelvetEncounterState | None = None) -> None:
        self.encounter = state or RedVelvetEncounterState()

    @property
    def mood(self) -> Mood:
        return Mood(self.encounter.current_mood)

    def perform(self) -> PerformanceResult:
        """She performs. Flavor and boon scale with mood."""
        self.encounter.performances_given += 1
        m = self.mood

        text_pool = {
            Mood.COLD:    _PERFORMANCE_COLD,
            Mood.WARM:    _PERFORMANCE_WARM,
            Mood.HOT:     _PERFORMANCE_HOT,
            Mood.BLAZING: _PERFORMANCE_BLAZING,
        }
        text = random.choice(text_pool[m])

        grants_boon = m == Mood.BLAZING
        boon_desc = (
            "The party is Inspired. Each member has advantage on their next ability check or attack roll."
            if grants_boon else None
        )

        # After a BLAZING performance, mood settles back to HOT
        if m == Mood.BLAZING:
            self.encounter.current_mood = Mood.HOT

        return PerformanceResult(
            performance_text=text,
            mood=m,
            grants_boon=grants_boon,
            boon_description=boon_desc,
        )

    def tip(self, silver: int) -> TipResult:
        """Tip her in silver. Each 5s raises mood by one step (max BLAZING)."""
        e = self.encounter
        before = self.mood
        e.total_tips_silver += silver

        steps = silver // 5
        new_raw = min(int(Mood.BLAZING), e.current_mood + steps)
        e.current_mood = new_raw
        after = self.mood

        return TipResult(
            response=random.choice(_TIP_RESPONSES),
            silver_spent=silver,
            mood_before=before,
            mood_after=after,
            mood_changed=after != before,
        )

    def heckle(self) -> HeckleResult:
        """Heckle her. Mood drops by one step (min COLD). She responds."""
        e = self.encounter
        before = self.mood
        e.current_mood = max(int(Mood.COLD), e.current_mood - 1)
        e.heckles_received += 1
        after = self.mood

        return HeckleResult(
            response=random.choice(_HECKLE_RESPONSES),
            mood_before=before,
            mood_after=after,
        )

    def request_song(self, song_type: SongRequest) -> SongResult:
        """Request a specific kind of song. She picks the right one."""
        if song_type == SongRequest.MYSTERY:
            song_type = random.choice([
                SongRequest.BATTLE_HYMN,
                SongRequest.DRINKING_SONG,
                SongRequest.LULLABY,
            ])

        text_pool = {
            SongRequest.BATTLE_HYMN:   _SONG_BATTLE_HYMN,
            SongRequest.LULLABY:       _SONG_LULLABY,
            SongRequest.DRINKING_SONG: _SONG_DRINKING_SONG,
            SongRequest.DIRGE:         _SONG_DIRGE,
        }
        text = random.choice(text_pool[song_type])
        self.encounter.performances_given += 1

        return SongResult(
            song_type=song_type,
            performance_text=text,
            mood=self.mood,
        )

    @property
    def mood_label(self) -> str:
        return self.mood.name.title()
