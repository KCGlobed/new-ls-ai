"""
OpenAI Embedder using text-embedding-3-small.
Batches requests in groups of 100 to stay safely within rate limits.
"""
import structlog
from openai import AsyncOpenAI

from app.core.config import settings

logger = structlog.get_logger(__name__)

EMBEDDING_MODEL = "text-embedding-3-small"
BATCH_SIZE = 100


class OpenAIEmbedder:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts, processed in batches of BATCH_SIZE."""
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i : i + BATCH_SIZE]
            response = await self.client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=batch,
            )
            all_embeddings.extend([e.embedding for e in response.data])
            logger.info(
                "embed_batch_done",
                batch_start=i,
                batch_size=len(batch),
                total=len(texts),
            )
        return all_embeddings

    async def embed_query(self, text: str) -> list[float]:
        """Embed a single query string."""
        response = await self.client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=[text],
        )
        return response.data[0].embedding
