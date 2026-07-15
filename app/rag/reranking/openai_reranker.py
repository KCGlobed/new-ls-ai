import structlog
from openai import AsyncOpenAI

from app.core.config import settings
from app.rag.prompts.query_prompts import RERANK_PROMPT

logger = structlog.get_logger(__name__)


class OpenAIReranker:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def rerank(self, query: str, candidates: list[dict], top_n: int = 5) -> list[dict]:
        """
        Uses gpt-4o-mini to score the relevance of candidates 0-10.
        Note: Candidates is a list of dictionaries with at least a 'text' field.
        """
        if not candidates:
            return []

        scored_candidates = []
        
        # In a high-traffic production system, we'd use Cohere Rerank API to batch this.
        # Here we use asyncio.gather for parallel OpenAI scoring.
        import asyncio

        async def _score_candidate(candidate: dict) -> dict:
            passage_text = candidate.get("text", "")[:1000]  # Limit context length per chunk
            try:
                response = await self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "user",
                            "content": RERANK_PROMPT.format(query=query, passage=passage_text)
                        }
                    ],
                    max_tokens=5,
                    temperature=0.0,
                )
                
                content = response.choices[0].message.content.strip()
                try:
                    score = float(content)
                except ValueError:
                    score = 0.0
                    
                return {**candidate, "rerank_score": score}
                
            except Exception as exc:
                logger.error("rerank_failed_for_candidate", exc_info=True, error=str(exc))
                return {**candidate, "rerank_score": 0.0}

        scored_candidates = await asyncio.gather(
            *[_score_candidate(c) for c in candidates]
        )

        # Sort by rerank score descending
        scored_candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
        
        logger.info(
            "rerank_complete", 
            candidates_in=len(candidates), 
            candidates_out=min(len(scored_candidates), top_n)
        )
        return scored_candidates[:top_n]
