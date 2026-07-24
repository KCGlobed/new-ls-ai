import os
import shutil

import structlog
import structlog.contextvars
from fastapi import APIRouter, Depends, File, Request, UploadFile, BackgroundTasks
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.audit import AuditEvent, write_audit
from app.database.dependencies import get_db
from app.database.models.document import Document
from app.database.models.users import Users
from app.storage.gcs import GoogleCloudStorage

router = APIRouter(prefix="/upload", tags=["upload"])
logger = structlog.get_logger(__name__)


@router.post("/")
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    # Bind user to all log calls within this request
    structlog.contextvars.bind_contextvars(
        user_id=str(current_user.id),
        filename=file.filename,
    )

    logger.info("upload_started", mime_type=file.content_type)
    write_audit(
        db,
        AuditEvent.DOCUMENT_UPLOAD_STARTED,
        status="success",
        user_id=str(current_user.id),
        user_email=current_user.email,
        resource_type="document",
        details={"filename": file.filename, "mime_type": file.content_type},
    )

    temp_file_path = f"/tmp/{file.filename}"
    try:
        # Save to temp location
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_size = os.path.getsize(temp_file_path)

        # Upload to Google Cloud Storage
        storage_provider = GoogleCloudStorage()
        destination_path = f"users/{current_user.id}/documents/{file.filename}"
        await storage_provider.upload_file(temp_file_path, destination_path)

        # Persist document record in the database
        document = Document(
            title=file.filename,
            original_filename=file.filename,
            storage_path=destination_path,
            mime_type=file.content_type,
            file_size=file_size,
            upload_by=current_user.id,
        )
        db.add(document)
        db.commit()
        db.refresh(document)

        logger.info(
            "upload_success",
            document_id=str(document.id),
            file_size_bytes=file_size,
        )
        write_audit(
            db,
            AuditEvent.DOCUMENT_UPLOAD_SUCCESS,
            status="success",
            user_id=str(current_user.id),
            user_email=current_user.email,
            resource_id=str(document.id),
            resource_type="document",
            details={
                "filename": file.filename,
                "mime_type": file.content_type,
                "file_size_bytes": file_size,
                "storage_path": destination_path,
            },
        )

        from app.upload.service import DocumentIngestionService
        
        async def process_document_background():
            service = DocumentIngestionService()
            await service.ingest(
                document_id=str(document.id),
                storage_path=destination_path,
                mime_type=file.content_type,
                user_id=str(current_user.id)
            )

        # Trigger background task within the FastAPI process
        background_tasks.add_task(process_document_background)

        return {
            "status": "uploaded",
            "document_id": document.id,
            "message": "File uploaded successfully. Background processing will begin shortly.",
        }

    except Exception as exc:
        logger.error(
            "upload_failed",
            exc_info=True,
            error=str(exc),
        )
        write_audit(
            db,
            AuditEvent.DOCUMENT_UPLOAD_FAILURE,
            status="failure",
            user_id=str(current_user.id),
            user_email=current_user.email,
            resource_type="document",
            details={"filename": file.filename, "mime_type": file.content_type},
            error_message=str(exc),
        )
        raise

    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
