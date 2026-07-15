import structlog
from openai import AsyncOpenAI

from app.core.config import settings
from app.rag.prompts.query_prompts import MULTI_QUERY_PROMPT

logger = structlog.get_logger(__name__)


class MultiQueryGenerator:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def generate(self, query: str, n: int = 4) -> list[str]:
        """
        Generates n alternative phrasing/perspectives for the given query.
        Returns the original query plus the variants.
        """
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": MULTI_QUERY_PROMPT.format(n=n)},
                    {"role": "user", "content": query},
                ],
                max_tokens=300,
                temperature=0.7,
            )
            content = response.choices[0].message.content.strip()
            # Split by lines and clean up any stray numbers or bullets if the LLM ignored instructions
            queries = []
            for line in content.split("\n"):
                clean = line.strip(" -*1234567890.")
                if clean:
                    queries.append(clean)
            
            # Always include the original
            final_queries = [query] + queries[:n]
            logger.info("multi_query_generated", original=query, variants=len(final_queries)-1)
            return final_queries
        except Exception as exc:
            logger.error("multi_query_failed", exc_info=True, error=str(exc))
            return [query]
