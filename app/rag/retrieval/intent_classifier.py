import structlog
from openai import AsyncOpenAI

from app.core.config import settings
from app.rag.prompts.query_prompts import INTENT_PROMPT

logger = structlog.get_logger(__name__)

INTENTS = {"factual_lookup", "conceptual_explain", "comparison", "summarization", "unknown"}


class IntentClassifier:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def classify(self, query: str) -> str:
        """Classify the user's query into one of the predefined intents."""
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": INTENT_PROMPT},
                    {"role": "user", "content": query},
                ],
                max_tokens=20,
                temperature=0.0,
            )
            intent = response.choices[0].message.content.strip().lower()
            if intent not in INTENTS:
                intent = "unknown"
            
            logger.info("intent_classified", original_query=query, intent=intent)
            return intent
        except Exception as exc:
            logger.error("intent_classification_failed", exc_info=True, error=str(exc))
            return "unknown"
