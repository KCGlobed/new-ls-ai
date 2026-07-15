from app.database.models.enums import DocumentType
from datetime import datetime
import uuid
from sqlalchemy import Boolean, DateTime, Enum, String, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base
from app.database.models.enums import DocumentStatus


class Document(Base):
    __tablename__="documents"
    id:Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    title:Mapped[str]=mapped_column(String(255))
    original_filename:Mapped[str]=mapped_column(String(255))
    storage_path:Mapped[str]=mapped_column(String(512))
    mime_type: Mapped[str] = mapped_column(String(100))
    file_size: Mapped[int] = mapped_column(Integer)
    status:Mapped[DocumentStatus]=mapped_column(Enum(DocumentStatus),default=DocumentStatus.PENDING)
    course:Mapped[str]=mapped_column(String(255),nullable=True)
    subject:Mapped[str]=mapped_column(String(255),nullable=True)
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    document_type:Mapped[DocumentType]=mapped_column(Enum(DocumentType),nullable=True,default=DocumentType.OTHER)
    upload_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    uploader: Mapped["Users"] = relationship("Users", back_populates="documents")
    # Ingestion tracking
    is_indexed: Mapped[bool] = mapped_column(Boolean, default=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    page_count: Mapped[int] = mapped_column(Integer, nullable=True)
    indexed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    chunks: Mapped[list["Chunk"]] = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")