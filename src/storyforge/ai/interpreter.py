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

async def interpret_freeform(
    state: GameState,
    actor: CharacterSheet,
    action: FreeformAction,
) -> AINarrationResponse:
    """
    Handle a freeform text action.
    """
    system_instruction = load_prompt("system_dm.md")
    template = load_prompt("interpret_freeform.md")
    
    # Simple template rendering (string replace)
    prompt = template.replace("{{ state_json }}", state.model_dump_json(exclude={"rooms", "narrative_log"}, indent=2))
    prompt = prompt.replace("{{ current_era }}", state.era.value)
    prompt = prompt.replace("{{ actor_id }}", actor.id)
    prompt = prompt.replace("{{ actor_name }}", actor.name)
    prompt = prompt.replace("{{ is_transformed }}", str(actor.is_transformed))
    prompt = prompt.replace("{{ action_text }}", action.text)
    
    logger.info(f"Interpreting freeform action from {actor.name}: {action.text}")
    
    # Call Gemini enforcing our JSON schema
    ai_response = await gemini_client.generate_structured(
        system_instruction=system_instruction,
        prompt=prompt,
    )
    
    return ai_response
