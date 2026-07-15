from enum import StrEnum


class AuditEvent(StrEnum):
    # ─── Auth ────────────────────────────────────────────────────────────────
    USER_REGISTER_SUCCESS = "user.register.success"
    USER_REGISTER_FAILURE = "user.register.failure"
    USER_LOGIN_SUCCESS    = "user.login.success"
    USER_LOGIN_FAILURE    = "user.login.failure"

    # ─── Upload ──────────────────────────────────────────────────────────────
    DOCUMENT_UPLOAD_STARTED    = "document.upload.started"
    DOCUMENT_UPLOAD_SUCCESS    = "document.upload.success"
    DOCUMENT_UPLOAD_FAILURE    = "document.upload.failure"
    DOCUMENT_INGESTION_STARTED = "document.ingestion.started"
    DOCUMENT_INGESTION_SUCCESS = "document.ingestion.success"
    DOCUMENT_INGESTION_FAILURE = "document.ingestion.failure"
    DOCUMENT_DELETE            = "document.delete"

    # ─── RAG / Search ────────────────────────────────────────────────────────
    RAG_QUERY_STARTED = "rag.query.started"
    RAG_QUERY_SUCCESS = "rag.query.success"
    RAG_QUERY_FAILURE = "rag.query.failure"

    # ─── System ──────────────────────────────────────────────────────────────
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_ERROR   = "system.error"
