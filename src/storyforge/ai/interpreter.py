"""
The Interpreter connects the StateManager to the GeminiClient.

It takes player actions, builds the prompt context, calls Gemini,
and passes the resulting StateDiff back to the StateManager.
"""
import logging
from storyforge.core.models import GameState, CharacterSheet, FreeformAction, AINarrationResponse
from storyforge.ai.client import gemini_client
from storyforge.ai.prompts import load_prompt

logger = logging.getLogger(__name__)


def _build_actor_context(actor: CharacterSheet) -> str:
    """Build a markdown character-context block for the AI prompt."""
    from storyforge.core.character_factory import BACKGROUNDS, FEATS, DIALOGUE_STYLES

    lines: list[str] = []

    # Identity line
    title = f"{actor.title} " if actor.title else ""
    lines.append(f"**Name:** {title}{actor.name} ({actor.pronouns})")
    lines.append(f"**Form:** {actor.race} · {actor.evolution_state} · {actor.predator_role}")
    if actor.alignment:
        lines.append(f"**Alignment:** {actor.alignment}")

    # Background
    if actor.background and actor.background in BACKGROUNDS:
        bg = BACKGROUNDS[actor.background]
        lines.append(f"**Background:** {bg.name} — *{bg.perk_name}*")

    # Feat
    if actor.feat and actor.feat in FEATS:
        feat = FEATS[actor.feat]
        lines.append(f"**Feat:** {feat.name} — {feat.mechanical_effect}")

    # Dialogue voice
    if actor.dialogue_style:
        style = next((s for s in DIALOGUE_STYLES if s["id"] == actor.dialogue_style), None)
        if style:
            lines.append(f"**Dialogue Voice:** {style['name']} — *{style['flavor']}*")

    # Story fields — only include non-empty ones
    if actor.physical_description:
        lines.append(f"**Appearance:** {actor.physical_description}")
    if actor.personality_traits:
        lines.append(f"**Personality:** {actor.personality_traits}")
    if actor.backstory:
        lines.append(f"**Backstory:** {actor.backstory}")
    if actor.ideals:
        lines.append(f"**Ideal:** {actor.ideals}")
    if actor.bonds:
        lines.append(f"**Bond:** {actor.bonds}")
    if actor.flaws:
        lines.append(f"**Flaw:** {actor.flaws}")

    # Keepsake — look it up in inventory
    keepsake = next(
        (item for item in actor.inventory if item.id.startswith("keepsake_")), None
    )
    if keepsake:
        lines.append(f"**Keepsake:** {keepsake.name}")

    if actor.cantrips:
        lines.append(f"**Cantrips:** {', '.join(actor.cantrips)}")

    return "\n".join(lines)


async def interpret_freeform(
    state: GameState,
    actor: CharacterSheet,
    action: FreeformAction,
) -> AINarrationResponse:
    """Handle a freeform text action."""
    system_instruction = load_prompt("system_dm.md")
    template = load_prompt("interpret_freeform.md")

    prompt = template.replace("{{ state_json }}", state.model_dump_json(exclude={"rooms", "narrative_log"}, indent=2))
    prompt = prompt.replace("{{ current_era }}", state.era.value)
    prompt = prompt.replace("{{ actor_id }}", actor.id)
    prompt = prompt.replace("{{ actor_name }}", actor.name)
    prompt = prompt.replace("{{ is_transformed }}", str(actor.is_transformed))
    prompt = prompt.replace("{{ actor_context }}", _build_actor_context(actor))
    prompt = prompt.replace("{{ action_text }}", action.text)

    logger.info(f"Interpreting freeform action from {actor.name}: {action.text}")

    ai_response = await gemini_client.generate_structured(
        system_instruction=system_instruction,
        prompt=prompt,
    )

    return ai_response
