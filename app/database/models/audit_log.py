import uuid
from datetime import datetime
from sqlalchemy import DateTime, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # e.g. "user.login.success", "document.upload.failure"
    event: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=True, index=True)
    user_email: Mapped[str] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str] = mapped_column(String(50), nullable=True)
    # Ties audit record back to the HTTP request log line
    request_id: Mapped[str] = mapped_column(String(255), nullable=True)
    # ID of the entity being acted on (document_id, etc.)
    resource_id: Mapped[str] = mapped_column(String(255), nullable=True)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=True)
    # "success" | "failure"
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    # Extra structured data (file size, query preview, etc.)
    details: Mapped[dict] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
