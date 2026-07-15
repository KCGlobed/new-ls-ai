"""
BM25 keyword index — one pickled index file per document_id.
Used alongside ChromaDB vector search for hybrid retrieval.
"""
import os
import pickle
import structlog
from rank_bm25 import BM25Okapi

logger = structlog.get_logger(__name__)

BM25_INDEX_DIR = "/tmp/bm25_indexes"


class BM25Store:
    def build_index(self, document_id: str, texts: list[str]) -> None:
        """Tokenize chunk texts and build a BM25 index for the document."""
        tokenized = [text.lower().split() for text in texts]
        index = BM25Okapi(tokenized)
        os.makedirs(BM25_INDEX_DIR, exist_ok=True)
        index_path = self._path(document_id)
        with open(index_path, "wb") as f:
            pickle.dump({"index": index, "texts": texts}, f)
        logger.info("bm25_index_built", document_id=document_id, chunk_count=len(texts))

    def search(self, document_id: str, query: str, k: int = 20) -> list[str]:
        """Return top-k matching text chunks for the given query."""
        index_path = self._path(document_id)
        if not os.path.exists(index_path):
            logger.warning("bm25_index_not_found", document_id=document_id)
            return []
        with open(index_path, "rb") as f:
            data = pickle.load(f)
        scores = data["index"].get_scores(query.lower().split())
        top_k_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        return [data["texts"][i] for i in top_k_indices]

    def delete_index(self, document_id: str) -> None:
        """Remove the BM25 index for a document."""
        index_path = self._path(document_id)
        if os.path.exists(index_path):
            os.remove(index_path)
            logger.info("bm25_index_deleted", document_id=document_id)

    def _path(self, document_id: str) -> str:
        return os.path.join(BM25_INDEX_DIR, f"{document_id}.pkl")
