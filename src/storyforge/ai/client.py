"""
Async Gemini client wrapper.

Responsible for the actual network call to Google GenAI. Handles retries
for transient 500s/rate limits.
"""
import asyncio
import json
import logging

from google import genai
from google.genai import types

from storyforge.config import settings, STORYFORGE_PRIMARY_MODEL, STORYFORGE_PRO_MODEL
from storyforge.core.models import AINarrationResponse

logger = logging.getLogger(__name__)


class GeminiClient:
    def __init__(self, api_key: str, model: str) -> None:
        if not api_key or api_key == "your_key_here":
            raise ValueError("STORYFORGE_GEMINI_API_KEY is missing or invalid.")
        self.client = genai.Client(api_key=api_key)
        self.model = model

    async def generate_structured(
        self,
        system_instruction: str,
        prompt: str,
        max_attempts: int = 3,
    ) -> AINarrationResponse:
        """
        Call Gemini enforcing the AINarrationResponse JSON schema.
        Includes simple backoff for transient failures.
        """
        schema = AINarrationResponse.model_json_schema()
        
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.7, # Slightly creative but bounded
        )

        last_exc = None
        # Backoff: 0.5s, 1s, 2s
        delays = [0.5, 1.0, 2.0]

        for attempt in range(max_attempts):
            try:
                # Run the sync genai client in a threadpool so we don't block the async event loop.
                # google-genai 0.3+ does have async clients, but using asyncio.to_thread is robust
                # if the specific async signatures aren't perfectly stable yet.
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model,
                    contents=prompt,
                    config=config,
                )
                if not response.text:
                    raise ValueError("Gemini returned empty text")
                
                # Parse the JSON string Gemini returned into our Pydantic model
                raw_dict = json.loads(response.text)
                return AINarrationResponse.model_validate(raw_dict)
                
            except Exception as e:
                last_exc = e
                if attempt < max_attempts - 1:
                    logger.warning(f"Gemini call failed (attempt {attempt+1}/{max_attempts}): {e}")
                    await asyncio.sleep(delays[attempt])
                else:
                    logger.error(f"Gemini call failed permanently: {e}")

        raise RuntimeError(f"Gemini call failed after {max_attempts} attempts") from last_exc


# Primary client for high-speed, agentic workflows (lobby, exploration, combat, NPCs)
gemini_client = GeminiClient(
    api_key=settings.gemini_api_key,
    model=STORYFORGE_PRIMARY_MODEL,
)

# Pro client for heavy world-building and codex generation (if needed)
gemini_pro_client = GeminiClient(
    api_key=settings.gemini_api_key,
    model=STORYFORGE_PRO_MODEL,
)
