"""
ChromaDB vector store — single global collection "lms_documents".
User isolation is achieved via the user_id metadata filter.
"""
import structlog
import chromadb
from chromadb import Collection

from app.core.config import settings

logger = structlog.get_logger(__name__)

COLLECTION_NAME = "lms_documents"


class ChromaStore:
    def __init__(self) -> None:
        if settings.chroma_host:
            self.client = chromadb.HttpClient(
                host=settings.chroma_host, 
                port=settings.chroma_port
            )
            logger.info(
                "chroma_initialized",
                mode="http",
                host=settings.chroma_host,
                port=settings.chroma_port,
                collection=COLLECTION_NAME
            )
        else:
            self.client = chromadb.PersistentClient(path=settings.chroma_persist_directory)
            logger.info(
                "chroma_initialized",
                mode="persistent",
                path=settings.chroma_persist_directory,
                collection=COLLECTION_NAME
            )

        self.collection: Collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert_chunks(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> None:
        """Insert or update chunks in the vector store."""
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        logger.info("chroma_upsert", count=len(ids))

    def similarity_search(
        self,
        query_embedding: list[float],
        k: int = 20,
        where: dict | None = None,
    ) -> list[dict]:
        """Return top-k chunks ranked by cosine similarity."""
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        hits = [
            {
                "text": doc,
                "metadata": meta,
                "score": round(1 - dist, 4),   # Convert distance → similarity
            }
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            )
        ]
        logger.info("chroma_search", results=len(hits))
        return hits

    def delete_document_chunks(self, document_id: str) -> None:
        """Remove all chunks belonging to a specific document."""
        self.collection.delete(where={"document_id": document_id})
        logger.info("chroma_delete", document_id=document_id)
