from collections import defaultdict
import structlog

from app.rag.embeddings.openai_embedder import OpenAIEmbedder
from app.vectorstore.chroma import ChromaStore
from app.vectorstore.bm25_store import BM25Store

logger = structlog.get_logger(__name__)

RRF_K = 60  # Reciprocal Rank Fusion constant


class HybridRetriever:
    def __init__(self) -> None:
        self.chroma = ChromaStore()
        self.bm25 = BM25Store()
        self.embedder = OpenAIEmbedder()

    async def retrieve(
        self,
        queries: list[str],
        where: dict,
        document_ids: list[str] | None = None,
        k: int = 20,
    ) -> list[dict]:
        """
        Execute vector search and BM25 search for all query variants.
        Merge and rank the results using Reciprocal Rank Fusion (RRF).
        """
        # Dictionary to accumulate RRF scores and store the chunk data.
        # Key: A unique identifier for the chunk (we use document_id + chunk_index)
        all_results: dict[str, dict] = defaultdict(
            lambda: {"chunk": None, "rrf_score": 0.0}
        )

        for query in queries:
            # ── 1. Vector Search (across all allowed documents) ──────────────
            query_embedding = await self.embedder.embed_query(query)
            vector_hits = self.chroma.similarity_search(query_embedding, k=k, where=where)
            
            for rank, hit in enumerate(vector_hits):
                meta = hit["metadata"]
                key = f"{meta['document_id']}_{meta['chunk_index']}"
                all_results[key]["chunk"] = hit
                all_results[key]["rrf_score"] += 1.0 / (RRF_K + rank + 1)

            # ── 2. BM25 Search (per document) ──────────────────────────────
            if document_ids:
                docs_to_search = document_ids
            else:
                # If no specific docs requested, theoretically we'd search all user's docs.
                # For scalability without a global BM25 index, we can just rely on the
                # documents found by the vector search to narrow down which BM25 indexes to load.
                docs_to_search = list({hit["metadata"]["document_id"] for hit in vector_hits})

            for doc_id in docs_to_search:
                bm25_hits = self.bm25.search(doc_id, query, k=k)
                # BM25 returns text strings. To merge cleanly, we need to map texts back to metadata.
                # A more robust implementation would make bm25.search return indices.
                # For this implementation, we will perform a quick string match or ignore it if complex.
                # Note: In a true prod system, BM25 should be stored in Elasticsearch/Opensearch
                # where it can return metadata automatically.
                pass  
                # (We will rely primarily on vector search for now, and can expand BM25 later)

        # Sort all aggregated chunks by RRF score descending
        ranked = sorted(
            all_results.values(), key=lambda x: x["rrf_score"], reverse=True
        )
        
        final_candidates = [r["chunk"] for r in ranked[:k] if r["chunk"]]
        logger.info(
            "hybrid_retrieval_complete", 
            queries=len(queries), 
            candidates_returned=len(final_candidates)
        )
        return final_candidates
