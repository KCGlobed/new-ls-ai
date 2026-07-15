import asyncio

import structlog

from app.upload.service import DocumentIngestionService

logger = structlog.get_logger(__name__)


async def ingest_document(
    document_id: str, storage_path: str, mime_type: str, user_id: str
) -> None:
    """
    Background task: called immediately after a file is uploaded to GCS.
    Performs the heavy lifting of extracting, chunking, and embedding.
    """
    logger.info("background_ingest_task_started", document_id=document_id)
    
    # Run the async ingestion service
    service = DocumentIngestionService()
    try:
        await service.ingest(
            document_id=document_id,
            storage_path=storage_path,
            mime_type=mime_type,
            user_id=user_id,
        )
    except Exception as exc:
        logger.error(
            "background_ingest_task_failed",
            document_id=document_id,
            exc_info=True,
            error=str(exc),
        )
        # Note: No automatic retry for BackgroundTasks out of the box
        # We just log the failure.
