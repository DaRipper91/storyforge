"""
NPC narrator — generates Gemini responses for NPC encounters.

Uses the NPC's npc_<name>.md as the system instruction (character bible +
rules). The caller builds the situation string describing what just happened;
this module handles the Gemini call and returns the narrative text.

Falls back gracefully: callers should always have a Python-pool fallback.
"""
import logging
from storyforge.ai.client import gemini_client
from storyforge.ai.prompts import load_prompt

logger = logging.getLogger(__name__)


async def narrate_npc(npc_name: str, situation: str) -> str:
    """
    Generate an NPC response using their character prompt as the system
    instruction. Returns only the narrative string — NPCs do not mutate
    GameState (no StateDiff).

    Args:
        npc_name:  Lowercase name matching the prompt file, e.g. "samael"
                   → loads npc_samael.md.
        situation: Natural-language description of the interaction context
                   sent as the user turn to Gemini.

    Raises:
        RuntimeError: If Gemini fails after all retries (caller should catch
                      and fall back to pool text).
    """
    system_instruction = load_prompt(f"npc_{npc_name}.md")
    result = await gemini_client.generate_structured(
        system_instruction=system_instruction,
        prompt=situation,
    )
    return result.narrative
