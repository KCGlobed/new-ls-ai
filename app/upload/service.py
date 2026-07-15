"""
Document Ingestion Service.

Called by the Celery worker after a file is uploaded to GCS.
Orchestrates: Load → Chunk → Embed → Index (ChromaDB + BM25) → Save to DB.
"""
import uuid
from datetime import datetime

import structlog
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.database.models.document import Document
from app.database.models.chunk import Chunk
from app.database.models.enums import DocumentStatus
from app.rag.loaders import get_loader
from app.rag.chunking import ParentChildChunker
from app.rag.embeddings import OpenAIEmbedder
from app.vectorstore.chroma import ChromaStore
from app.vectorstore.bm25_store import BM25Store

logger = structlog.get_logger(__name__)


class DocumentIngestionService:
    def __init__(self) -> None:
        self.chunker = ParentChildChunker()
        self.embedder = OpenAIEmbedder()
        self.chroma = ChromaStore()
        self.bm25 = BM25Store()

    async def ingest(
        self, document_id: str, storage_path: str, mime_type: str, user_id: str
    ) -> None:
        """
        Full ingestion pipeline for one document.
        1. Download file from GCS to a temp location
        2. Load file → pages
        3. Chunk pages → parent + child chunks
        4. Embed child chunks (OpenAI)
        5. Upsert child chunks into ChromaDB
        6. Build BM25 index from child chunk texts
        7. Save all chunks to PostgreSQL
        8. Mark document as indexed
        """
        import os
        from app.storage.gcs import GoogleCloudStorage
        
        db: Session = SessionLocal()
        temp_file_path = f"/tmp/ingest_{document_id}"
        
        try:
            logger.info(
                "ingestion_started",
                document_id=document_id,
                mime_type=mime_type,
            )
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                raise ValueError(f"Document {document_id} not found in database")

            # Mark as processing
            document.status = DocumentStatus.PROCESSING
            db.commit()

            # ── 0. Download from GCS ───────────────────────────────────────
            storage_provider = GoogleCloudStorage()
            await storage_provider.download_file(storage_path, temp_file_path)

            # ── 1. Load ────────────────────────────────────────────────────
            loader = get_loader(mime_type)
            pages = loader.load(temp_file_path)
            document.page_count = len(pages)

            # ── 2. Chunk ───────────────────────────────────────────────────
            parent_chunks = self.chunker.chunk(pages)
            if not parent_chunks:
                raise ValueError("No content extracted from document")

            # ── 3. Embed child chunks ──────────────────────────────────────
            all_child_texts = [
                child.text
                for parent in parent_chunks
                for child in parent.children
            ]
            child_embeddings = await self.embedder.embed_batch(all_child_texts)

            # ── 4. Upsert into ChromaDB ────────────────────────────────────
            chroma_ids, chroma_docs, chroma_metas, chroma_embeds = [], [], [], []
            db_chunks: list[Chunk] = []
            child_embed_idx = 0
            parent_db_ids: dict[int, uuid.UUID] = {}

            for parent in parent_chunks:
                parent_db_id = uuid.uuid4()
                parent_db_ids[parent.parent_index] = parent_db_id

                # Save parent chunk to DB
                db_chunks.append(
                    Chunk(
                        id=parent_db_id,
                        document_id=uuid.UUID(document_id),
                        parent_id=None,
                        text=parent.text,
                        chunk_index=parent.parent_index,
                        page_number=parent.page_number,
                        token_count=parent.token_count,
                        is_parent=True,
                    )
                )

                for child in parent.children:
                    child_db_id = uuid.uuid4()
                    embedding_id = str(child_db_id)

                    chroma_ids.append(embedding_id)
                    chroma_docs.append(child.text)
                    chroma_embeds.append(child_embeddings[child_embed_idx])
                    chroma_metas.append(
                        {
                            "user_id": user_id,
                            "document_id": document_id,
                            "parent_id": str(parent_db_id),
                            "chunk_index": child.chunk_index,
                            "page_number": child.page_number,
                            "file_name": document.original_filename,
                            "mime_type": mime_type,
                        }
                    )
                    db_chunks.append(
                        Chunk(
                            id=child_db_id,
                            document_id=uuid.UUID(document_id),
                            parent_id=parent_db_id,
                            text=child.text,
                            chunk_index=child.chunk_index,
                            page_number=child.page_number,
                            token_count=child.token_count,
                            embedding_id=embedding_id,
                            is_parent=False,
                        )
                    )
                    child_embed_idx += 1

            self.chroma.upsert_chunks(
                ids=chroma_ids,
                embeddings=chroma_embeds,
                documents=chroma_docs,
                metadatas=chroma_metas,
            )

            # ── 5. Build BM25 index ────────────────────────────────────────
            self.bm25.build_index(document_id, all_child_texts)

            # ── 6. Save chunks to PostgreSQL ───────────────────────────────
            db.bulk_save_objects(db_chunks)

            # ── 7. Mark document as indexed ────────────────────────────────
            document.is_indexed = True
            document.status = DocumentStatus.COMPLETED
            document.chunk_count = len(all_child_texts)
            document.indexed_at = datetime.utcnow()
            db.commit()

            logger.info(
                "ingestion_success",
                document_id=document_id,
                parent_count=len(parent_chunks),
                child_count=len(all_child_texts),
            )

        except Exception as exc:
            logger.error(
                "ingestion_failed",
                document_id=document_id,
                exc_info=True,
                error=str(exc),
            )
            if db:
                doc = db.query(Document).filter(Document.id == document_id).first()
                if doc:
                    doc.status = DocumentStatus.FAILED
                    db.commit()
            raise
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            db.close()
