import structlog
from openai import AsyncOpenAI

from app.core.config import settings
from app.rag.prompts.query_prompts import COMPRESS_PROMPT

logger = structlog.get_logger(__name__)


class ContextCompressor:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def compress(self, query: str, chunks: list[dict]) -> list[dict]:
        """
        Extracts only the sentences from each chunk that are relevant to the query.
        This reduces the context window size and limits distraction for the final LLM response.
        """
        if not chunks:
            return []

        import asyncio

        async def _compress_chunk(chunk: dict) -> dict:
            passage_text = chunk.get("text", "")
            try:
                response = await self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "user",
                            "content": COMPRESS_PROMPT.format(query=query, passage=passage_text)
                        }
                    ],
                    max_tokens=500,
                    temperature=0.0,
                )
                
                compressed_text = response.choices[0].message.content.strip()
                
                if compressed_text and not compressed_text.lower().startswith("no relevant"):
                    return {**chunk, "text": compressed_text}
                return None
                
            except Exception as exc:
                logger.error("compression_failed_for_chunk", exc_info=True, error=str(exc))
                # Fallback to the original text if compression fails
                return chunk

        results = await asyncio.gather(
            *[_compress_chunk(c) for c in chunks]
        )
        
        # Filter out chunks that were completely irrelevant (None)
        compressed_chunks = [r for r in results if r is not None]
        
        logger.info(
            "context_compressed", 
            chunks_in=len(chunks), 
            chunks_out=len(compressed_chunks)
        )
        return compressed_chunks
