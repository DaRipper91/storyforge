import logging
from storyforge.core.models import GameState, CharacterSheet
from storyforge.ai.client import gemini_client
from storyforge.ai.prompts import load_prompt
from storyforge.ai.interpreter import _build_actor_context

logger = logging.getLogger(__name__)

async def narrate_movement(
    state: GameState,
    actor: CharacterSheet,
    from_coord: dict,
    to_coord: dict,
) -> str:
    """Generate flavor text for a validated grid move."""
    system_instruction = load_prompt("system_dm.md")
    template = load_prompt("narrate_movement.md")

    prompt = template.replace("{{ actor_name }}", actor.name)
    prompt = prompt.replace("{{ from_coord }}", str(from_coord))
    prompt = prompt.replace("{{ to_coord }}", str(to_coord))
    prompt = prompt.replace("{{ current_era }}", state.era.value)
    prompt = prompt.replace("{{ is_transformed }}", str(actor.is_transformed))
    prompt = prompt.replace("{{ actor_context }}", _build_actor_context(actor))

    ai_response = await gemini_client.generate_structured(
        system_instruction=system_instruction,
        prompt=prompt,
    )

    return ai_response.narrative
