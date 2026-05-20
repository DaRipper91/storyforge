"""
ShopkeeperJon — encounter logic for Jon (The Boss / Store Owner).

Architecture:
  - ShopkeeperJon is a pure service class. It never touches GameState directly.
  - Every mutation is returned as a StateDiff for state_manager.apply_diff().
  - JonEncounterState is the persisted encounter record (session-level, stored
    on app.state.jon_encounter — it resets when a campaign is loaded/created,
    not on every turn).

Mechanics implemented here:
  1. Multiversal Bodega      — genre-adaptive inventory, Jon never notices
  2. Cactus Defense Protocol — offense tracking + sales embargo on repeated jokes
  3. Escape Check            — d20 ability check to leave; penalty scales with margin
  4. Haylie Bailout Flag     — set on critical fail so MadameHaylie can intervene
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from enum import StrEnum
from pydantic import BaseModel, Field

from storyforge.core.models import (
    Ability, CharacterSheet, InventoryItem, StateDiff,
)


# ─────────────────────── Genre enum ───────────────────────

class SceneGenre(StrEnum):
    FANTASY          = "fantasy"
    SCI_FI           = "sci_fi"
    CYBERPUNK        = "cyberpunk"
    HORROR           = "horror"
    WESTERN          = "western"
    POST_APOCALYPTIC = "post_apocalyptic"


# ─────────────────────── Escape methods ───────────────────────

class EscapeMethod(StrEnum):
    """How the party attempts to leave Jon's store."""
    SMOOTH_TALK         = "smooth_talk"
    STEALTH             = "stealth"
    FABRICATE_EMERGENCY = "fabricate"
    SHEER_WILLPOWER     = "willpower"
    BULLDOZE            = "bulldoze"


_ESCAPE_ABILITY: dict[EscapeMethod, Ability] = {
    EscapeMethod.SMOOTH_TALK:         Ability.CHA,
    EscapeMethod.STEALTH:             Ability.DEX,
    EscapeMethod.FABRICATE_EMERGENCY: Ability.INT,
    EscapeMethod.SHEER_WILLPOWER:     Ability.WIS,
    EscapeMethod.BULLDOZE:            Ability.STR,
}


# ─────────────────────── Result dataclass ───────────────────────

@dataclass(frozen=True)
class EscapeResult:
    success: bool
    roll: int
    modifier: int
    total: int
    dc: int
    margin: int
    psychic_damage: int
    turns_lost: int
    method: EscapeMethod
    ability_used: Ability
    flavor: str


# ─────────────────────── Encounter state ───────────────────────

class JonEncounterState(BaseModel):
    """
    Session-level state for an active Jon encounter.
    Stored on app.state.jon_encounter; reset on new/load campaign.
    """
    active: bool = False
    cactus_offense_count: int = 0
    jon_currently_offended: bool = False
    refused_sale_turns_remaining: int = 0
    story_trap_active: bool = False
    story_trap_turns_remaining: int = 0
    escape_attempts: int = 0
    total_psychic_damage_dealt: int = 0
    bailout_available: bool = False  # set True on critical fail; Haylie can clear it


# ─────────────────────── Inventory tables ───────────────────────

def _item(item_id: str, name: str, value: int, notes: str) -> InventoryItem:
    return InventoryItem(id=item_id, name=name, quantity=1,
                         equipped=False, value=value, notes=notes)


_INVENTORY_TABLES: dict[SceneGenre, list[InventoryItem]] = {
    SceneGenre.FANTASY: [
        _item("longsword_jon",    "Longsword",                 150, "Slightly notched. 'Character,' Jon says."),
        _item("healing_potion",   "Healing Potion (2d4+2)",     50, "Store brand. Tastes like cherry cough syrup."),
        _item("rope_50ft",        "Hempen Rope, 50ft",          10, "'You'd be surprised how often people need this.'"),
        _item("torches_x5",       "Torch Bundle (×5)",           5, "Come back when you need more. He'll be here."),
        _item("lockpick_set",     "Thieves' Tools",             25, "'For the locks in your own home. Wink.'"),
        _item("trail_rations",    "Trail Rations (7 days)",     35, "'The jerky is the good stuff. My wife's recipe.'"),
        _item("light_crossbow",   "Light Crossbow",             25, "Bolts sold separately. Of course they are."),
        _item("lantern_hooded",   "Hooded Lantern",              5, "Oil not included. Also sold separately."),
    ],
    SceneGenre.SCI_FI: [
        _item("plasma_rifle_mk2",  "Plasma Rifle Mk.II",        800, "'Had these since Tuesday. Very popular this week.'"),
        _item("medkit_standard",   "Standard Med-Kit",          120, "Patches cellular damage. Smells like ozone."),
        _item("nano_stimpack",     "Nano-Stimpack (×3)",         60, "Inject, wait six seconds, feel 40% better."),
        _item("energy_cells_x10",  "Energy Cells (×10)",         40, "'These work in most brands. Mostly.'"),
        _item("vac_suit_patch",    "Vacuum Suit Patch Kit",      15, "For the small holes. Big ones, you're on your own."),
        _item("holo_decoy",        "Holographic Decoy Unit",    200, "'Bink Bink keeps batting mine off the shelf.'"),
        _item("grav_boots",        "Magnetic Grav-Boots",       350, "Rated to 1.2G. 'Don't test that.'"),
        _item("scrambler_grenade", "Signal Scrambler Grenade (×2)", 90, "Disables sensors. And apparently, toasters."),
    ],
    SceneGenre.CYBERPUNK: [
        _item("neural_jack_v3",    "Neural Interface Jack v3",  1200, "'The v4 has a recall. Stick with v3.'"),
        _item("emp_grenade",       "EMP Grenade (×2)",           150, "Takes out drones AND pacemakers. Read the label."),
        _item("mono_wire_spool",   "Monofilament Wire, 10m",     80, "Handle with the included gloves. Seriously."),
        _item("credchip_reader",   "Credchip Reader/Cloner",    600, "'For reading your OWN chips. Obviously.'"),
        _item("synthskin_patch",   "Synthskin Dermal Patches (×5)", 45, "Covers wounds and port scarring."),
        _item("ice_breaker",       "ICE-Breaker Dongle",        400, "'I don't ask what people use these for anymore.'"),
        _item("smartgun_link",     "Smartgun Link Module",      300, "Compatible with 80% of firearms. 'The other 20%: not my problem.'"),
        _item("ghost_cloak_gen1",  "Ghost Cloak Gen.1",        2500, "35-second battery life. 'It's a work in progress.'"),
    ],
    SceneGenre.HORROR: [
        _item("silver_bullets_x6", "Silver Bullets (×6)",        90, "'Don't ask why I have these.' (He has been asked.)"),
        _item("holy_water_vial",   "Holy Water (×3 vials)",       25, "Genuine. 'Father Mike owes me a favor.'"),
        _item("wolfsbane_bundle",  "Wolfsbane Bundle",            15, "Keep away from dogs. He had to learn this."),
        _item("iron_salt_pouch",   "Iron Filings + Salt Mix",     10, "'Sprinkle at doorways. Don't ask.'"),
        _item("crucifix_blessed",  "Blessed Crucifix",            30, "May or may not work. Depends on your faith."),
        _item("mirror_hand",       "Hand Mirror (unbroken)",       5, "'Keep it unbroken. For the love of...'"),
        _item("journal_blank",     "Blank Journal",                8, "Do NOT write anything that comes to you at 3am."),
        _item("flare_gun",         "Flare Gun + 4 Rounds",        40, "Works on things. Also doubles as a distress signal."),
    ],
    SceneGenre.WESTERN: [
        _item("sixshooter_colt",   ".45 Revolver",               120, "'Came off a man who didn't need it anymore.'"),
        _item("ammo_box_45",       ".45 Rounds (×24)",            12, "Factory loads. Clean burns."),
        _item("lasso_rope",        "Lasso (40ft)",                 8, "'Teddy keeps dragging mine around. Hence the surplus.'"),
        _item("whiskey_flask",     "Whiskey Flask (full)",         4, "The good kind. Don't water it down."),
        _item("dynamite_x2",       "Dynamite Sticks (×2)",        25, "'I don't ask, you don't tell.'"),
        _item("wanted_poster",     "Blank Wanted Poster",          2, "Fill in your own name. Could save time later."),
        _item("duster_coat",       "Duster Coat (leather)",       35, "Stops wind, rain, and minor knife attacks."),
        _item("bowie_knife",       "Bowie Knife",                 18, "Still has an edge. Unlike some customers."),
    ],
    SceneGenre.POST_APOCALYPTIC: [
        _item("duct_tape_roll",    "Duct Tape (full roll)",       20, "'Fix anything. Literally. Fixed Teddy's collar with this.'"),
        _item("canned_beans_x6",   "Canned Beans (×6)",           30, "No expiry date visible. Probably fine."),
        _item("rad_pills_x10",     "Radiation Blocker Pills (×10)", 50, "Reduces exposure. Does NOT cure. Read the label."),
        _item("shotgun_shells_x8", "12-Gauge Shells (×8)",        16, "'Standard load. The fancy stuff I keep out back.'"),
        _item("water_purifier",    "Hand-Pump Water Purifier",    80, "'Bink Bink knocked the last one off the shelf. Hence the sale.'"),
        _item("gas_mask",          "Gas Mask + 2 Filters",       110, "Seal checks out. Tested it on myself."),
        _item("stun_baton",        "Jury-Rigged Stun Baton",      65, "'Cyrus bumped it on once. We don't talk about that.'"),
        _item("scavenger_toolkit", "Scavenger Toolkit",           45, "Wire, pliers, fuses. The holy trinity."),
    ],
}

THE_CACTUS = _item(
    "cactus_jons",
    "Remarkably Distinctive Desert Succulent",
    value=0,
    notes=(
        "NOT FOR SALE. A rare botanical specimen, purchased for Jon's sister. "
        "Jon is extremely proud of it and is entirely unaware why people keep "
        "smirking at it. Shape noted as 'very architectural' by the specialist grower."
    ),
)


# ─────────────────────── Flavor text pools ───────────────────────

_SUCCESS_FLAVOR: dict[EscapeMethod, list[str]] = {
    EscapeMethod.SMOOTH_TALK: [
        "You compliment the cactus, praise Teddy's coat, and back toward the door with practiced grace. Jon beams. You're gone before he can remember what he was about to say about his brother-in-law.",
        "A firm handshake, a 'we'll do this again soon,' and a smile that doesn't reach your eyes. Jon watches you go, genuinely touched. He's already planning what he'll tell you next time.",
    ],
    EscapeMethod.STEALTH: [
        "Bink Bink leaps onto the display case. Jon spins around. By the time the cat has knocked three items to the floor and Jon has apologized to all of them individually, you are gone. Bink Bink winks. You think.",
        "You time your exit to the exact moment Teddy demands ear scratches. The bell above the door barely makes a sound.",
    ],
    EscapeMethod.FABRICATE_EMERGENCY: [
        "You inform Jon that something is on fire approximately two blocks away. He says, 'Oh, is it the Hendersons again?' and turns to look out the window. You are a distant memory.",
        "A mumbled 'I think I left the stove on' and a rising sense of urgency does the trick. Jon calls after you to 'be safe out there.' You will not be coming back anytime soon.",
    ],
    EscapeMethod.SHEER_WILLPOWER: [
        "You nod through four unrelated anecdotes, maintain eye contact, smile at all the right moments, and slowly, imperceptibly drift toward the exit like a leaf on a river. Jon never noticed you leave.",
        "Twenty years of politely surviving holidays with extended family have prepared you for this exact moment. You are free.",
    ],
    EscapeMethod.BULLDOZE: [
        "You pat Jon firmly on the shoulder, say 'Good talk, buddy,' and walk out. He's a little surprised but genuinely not offended. 'Come back any time!' You will absolutely not.",
        "A bear hug you didn't consent to initiates. You endure it. You leave. Jon wipes his eye. Everyone's fine.",
    ],
}

_FAIL_MILD_FLAVOR: dict[EscapeMethod, list[str]] = {
    EscapeMethod.SMOOTH_TALK: [
        "You make your move, but Jon's face lights up. 'Oh! That reminds me—' You sink back. Seventeen minutes about his cousin's second wedding. The details are extraordinary in their mundanity.",
        "You're almost out the door when Jon asks if you've met Bink Bink. You have. He introduces you anyway. At length.",
    ],
    EscapeMethod.STEALTH: [
        "You miscalculate Bink Bink's trajectory. The cat knocks something toward you instead of away. Jon turns. Sees you near the door. 'Oh, were you heading out? Actually—'",
        "The bell above the door is louder than you remembered. Jon spins around with the enthusiasm of a man who has been alone with a cat and two dogs all day.",
    ],
    EscapeMethod.FABRICATE_EMERGENCY: [
        "Jon immediately offers to come help with your fictional emergency. He knows a guy. He's going to call the guy. He's telling you about the guy first.",
        "Your excuse is plausible, but Jon has a relevant story. It starts in 1987. By the time he finishes, your fake emergency has had time to resolve itself.",
    ],
    EscapeMethod.SHEER_WILLPOWER: [
        "Your resolve falters on anecdote three. You make a polite noise of interest. This is interpreted as an invitation to continue. It was not an invitation.",
        "You blink at the wrong moment. Jon takes it as a question. It was not a question.",
    ],
    EscapeMethod.BULLDOZE: [
        "Jon reciprocates the hug with significantly more force than expected. By the time you've extracted yourself, the moment has passed and he's already mid-sentence.",
        "You push for the door. Teddy has sat down in front of it and will not move until acknowledged. Jon laughs and launches into Teddy's origin story.",
    ],
}

_FAIL_SEVERE_FLAVOR: dict[EscapeMethod, list[str]] = {
    EscapeMethod.SMOOTH_TALK: [
        "Your charm backfires. Jon thinks you're his new best friend. He shows you photos — physical, printed photos. There are many. Your mind retreats to a soft, gray place.",
        "You complimented his hat. There is a story about the hat. The hat story leads to a boat story. The boat story leads to a fishing story. You briefly cease to be a person and become instead a pair of eyes, floating.",
    ],
    EscapeMethod.STEALTH: [
        "Bink Bink lands on your shoulder and yowls directly into your ear. Jon is delighted. Bink Bink has *chosen* you. There is extensive commentary on this. Your sanity absorbs the impact.",
        "You slip on something Bink Bink knocked over. Jon helps you up. At length. With a story about a similar fall in 2003. The cognitive erosion begins immediately.",
    ],
    EscapeMethod.FABRICATE_EMERGENCY: [
        "Jon has a cousin who went through EXACTLY that. He is going to call them. You listen to both sides of the conversation. By the end, you are no longer certain of your own name.",
        "Your emergency was too interesting. Jon is invested. He asks clarifying questions. You must maintain the lie in real time while he builds on it. Your mind files the experience under 'formative trauma.'",
    ],
    EscapeMethod.SHEER_WILLPOWER: [
        "Your wall breaks at minute thirty-two. Jon says something tangentially related to something you once cared about. You engage. You don't know why you engage. The damage is done.",
        "The anecdote has no ending. Jon has circled back to the beginning with new details. You stare into the middle distance. Cyrus makes eye contact with you. He has seen this before. He is very sorry.",
    ],
    EscapeMethod.BULLDOZE: [
        "Jon, apparently raised by huggers, follows you to the door for a goodbye that lasts eleven minutes. Cyrus sits on your foot. You cannot leave without disturbing the dog. Jon takes this as a sign you want to stay.",
        "You push through but Jon follows, continuing the story onto the front stoop. He doesn't notice he is now outside. You are standing in the sun together. This is somehow worse. His rambling erodes something essential in you.",
    ],
}


# ─────────────────────── Service class ───────────────────────

class ShopkeeperJon:
    """
    Pure service layer for the Jon encounter.
    Instantiate with the current JonEncounterState, call methods,
    pass returned StateDiff objects to state_manager.apply_diff().
    """

    ESCAPE_DC = 15
    PSYCHIC_DAMAGE_DIE = 4
    CACTUS_OFFENSE_THRESHOLD = 3
    CACTUS_SALES_BLOCK_TURNS = 2

    def __init__(self, state: JonEncounterState | None = None) -> None:
        self.encounter = state or JonEncounterState()

    # ── Inventory ────────────────────────────────────────────────

    def get_inventory(self, genre: SceneGenre) -> list[InventoryItem]:
        return list(_INVENTORY_TABLES[genre])

    def get_item(self, genre: SceneGenre, item_id: str) -> InventoryItem | None:
        return next(
            (i for i in _INVENTORY_TABLES[genre] if i.id == item_id),
            None,
        )

    def buy_item(
        self,
        character: CharacterSheet,
        genre: SceneGenre,
        item_id: str,
    ) -> tuple[StateDiff | None, str]:
        if self.encounter.refused_sale_turns_remaining > 0:
            return (
                None,
                "Jon has turned away from the counter. 'I need a moment,' he says, "
                "staring pointedly at the cactus. 'Some people have no respect for "
                "horticulture.' He will not be selling anything for a while."
            )

        item = self.get_item(genre, item_id)
        if item is None:
            return None, "Jon squints. 'Don't carry that. Try me next week.'"

        if character.silver < item.value:
            shortage = item.value - character.silver
            return (
                None,
                f"Jon does the math. You're {shortage} silver short. "
                f"'Come back when you're less broke. No offense.' He means all of it.",
            )

        diff = StateDiff(
            character_updates={character.id: {"silver": character.silver - item.value}},
            add_inventory={character.id: [item]},
        )
        return (
            diff,
            f"Jon wraps the {item.name} with practiced efficiency. "
            f"'Anything else? No rush. I'm here all day. And tomorrow. "
            f"The day after, actually. Did I mention the—'",
        )

    # ── Cactus Defense Protocol ───────────────────────────────────

    def handle_cactus_comment(self, is_lewd_or_mocking: bool) -> str:
        if not is_lewd_or_mocking:
            return (
                "Jon brightens. 'Gorgeous, isn't she? Sister's going to love it. "
                "Found a specialist grower three towns over. Very rare specimen. "
                "The shape is quite distinctive — very *architectural*, they said.'"
            )

        self.encounter.cactus_offense_count += 1
        self.encounter.jon_currently_offended = True

        if self.encounter.cactus_offense_count >= self.CACTUS_OFFENSE_THRESHOLD:
            self.encounter.refused_sale_turns_remaining = self.CACTUS_SALES_BLOCK_TURNS
            return (
                "Jon's face cycles through several colors. He sets down what he was "
                "holding. 'I don't know what you think you're implying, but that is a "
                "*plant*. A rare, carefully cultivated *succulent*. For my *sister*. "
                "She has a collection. It is a *hobby*. Now I'm going to need you to "
                "step back from the counter until you can conduct yourselves with some "
                "basic human decency. Unbelievable. In front of Teddy, even.'"
            )

        early_responses = [
            (
                "Jon stares at you for a long moment. 'I beg your pardon? That is a "
                "*botanical specimen*. Imported. For my sister. Who collects them. "
                "There is nothing funny about succulent horticulture.' He turns the "
                "cactus slightly away from you, as if protecting it."
            ),
            (
                "'What is *wrong* with you people?' Jon positions himself between you "
                "and the cactus. 'That is a gift. For family. The shape is *distinctive* "
                "because it is a rare *species*. The specialist was very clear. Very. "
                "Clear.' His eye twitches."
            ),
        ]
        idx = min(self.encounter.cactus_offense_count - 1, len(early_responses) - 1)
        return early_responses[idx]

    # ── Escape mechanics ─────────────────────────────────────────

    @staticmethod
    def _modifier(score: int) -> int:
        return (score - 10) // 2

    def roll_escape_check(
        self,
        character: CharacterSheet,
        method: EscapeMethod,
        advantage: bool = False,
        disadvantage: bool = False,
    ) -> tuple[EscapeResult, StateDiff | None]:
        """
        Penalty ladder (margin = total − DC):
          ≥  0      : success — clean exit
          −1 to −4  : mild fail — 1 turn lost
          ≤ −5      : bad fail  — 2 turns lost + 1d4 psychic, bailout_available=True
        """
        ability = _ESCAPE_ABILITY[method]
        score = getattr(character.abilities, ability.value)
        modifier = self._modifier(score)

        rolls = [random.randint(1, 20), random.randint(1, 20)]
        if advantage and not disadvantage:
            raw = max(rolls)
        elif disadvantage and not advantage:
            raw = min(rolls)
        else:
            raw = rolls[0]

        total = raw + modifier
        margin = total - self.ESCAPE_DC
        self.encounter.escape_attempts += 1

        if margin >= 0:
            flavor = random.choice(_SUCCESS_FLAVOR[method])
            turns_lost, psychic = 0, 0
            self.encounter.bailout_available = False
            diff = None

        elif margin >= -4:
            flavor = random.choice(_FAIL_MILD_FLAVOR[method])
            turns_lost, psychic = 1, 0
            self.encounter.story_trap_active = True
            self.encounter.story_trap_turns_remaining = turns_lost
            self.encounter.bailout_available = False
            diff = None

        else:
            flavor = random.choice(_FAIL_SEVERE_FLAVOR[method])
            turns_lost = 2
            psychic = random.randint(1, self.PSYCHIC_DAMAGE_DIE)
            self.encounter.story_trap_active = True
            self.encounter.story_trap_turns_remaining = turns_lost
            self.encounter.total_psychic_damage_dealt += psychic
            self.encounter.bailout_available = True
            new_hp = max(0, character.hp_current - psychic)
            diff = StateDiff(character_updates={character.id: {"hp_current": new_hp}})

        return (
            EscapeResult(
                success=(margin >= 0),
                roll=raw, modifier=modifier, total=total,
                dc=self.ESCAPE_DC, margin=margin,
                psychic_damage=psychic, turns_lost=turns_lost,
                method=method, ability_used=ability, flavor=flavor,
            ),
            diff,
        )

    # ── Turn clock ────────────────────────────────────────────────

    def tick_turn(self) -> None:
        if self.encounter.story_trap_turns_remaining > 0:
            self.encounter.story_trap_turns_remaining -= 1
            if self.encounter.story_trap_turns_remaining == 0:
                self.encounter.story_trap_active = False

        if self.encounter.refused_sale_turns_remaining > 0:
            self.encounter.refused_sale_turns_remaining -= 1
            if self.encounter.refused_sale_turns_remaining == 0:
                self.encounter.jon_currently_offended = False

    @property
    def party_can_leave(self) -> bool:
        return not self.encounter.story_trap_active

    @property
    def jon_will_sell(self) -> bool:
        return self.encounter.refused_sale_turns_remaining == 0
