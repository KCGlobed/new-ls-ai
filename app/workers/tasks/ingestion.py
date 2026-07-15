import asyncio

import structlog

from app.workers.celery_app import celery_app
from app.upload.service import DocumentIngestionService

logger = structlog.get_logger(__name__)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,  # wait 30 seconds between retries
    name="app.workers.tasks.ingestion.ingest_document",
)
def ingest_document(
    self, document_id: str, storage_path: str, mime_type: str, user_id: str
) -> None:
    """
    Celery task: called immediately after a file is uploaded to GCS.
    Performs the heavy lifting of extracting, chunking, and embedding.
    """
    logger.info("celery_ingest_task_started", document_id=document_id)
    
    # Run the async ingestion service synchronously in the Celery worker
    service = DocumentIngestionService()
    try:
        asyncio.run(
            service.ingest(
                document_id=document_id,
                storage_path=storage_path,
                mime_type=mime_type,
                user_id=user_id,
            )
        )
    except Exception as exc:
        logger.error(
            "celery_ingest_task_failed",
            document_id=document_id,
            exc_info=True,
            error=str(exc),
        )
        # Retry the task for transient errors (e.g., API limits, DB locks)
        raise self.retry(exc=exc)
