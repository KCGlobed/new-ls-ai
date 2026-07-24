# pyrefly: ignore [missing-import]
import structlog
from openai import AsyncOpenAI

from app.core.config import settings
from app.rag.prompts.query_prompts import REWRITE_PROMPT

logger = structlog.get_logger(__name__)


class QueryRewriter:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def rewrite(self, query: str, history: list[dict]) -> str:
        """
        Rewrites a query to be self-contained by resolving pronouns and context
        from the last few conversation turns.
        """
        if not history:
            return query

        messages = [{"role": "system", "content": REWRITE_PROMPT}]
        # Take the last 6 messages (3 turns)
        messages.extend(history[-6:])
        messages.append({"role": "user", "content": f"Rewrite this question: {query}"})

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=100,
                temperature=0.0,
            )
            rewritten = response.choices[0].message.content.strip()
            logger.info("query_rewritten", original=query, rewritten=rewritten)
            return rewritten
        except Exception as exc:
            logger.error("query_rewrite_failed", exc_info=True, error=str(exc))
            return query
