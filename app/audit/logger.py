"""
Audit writer — writes to the DB and emits a structured log line simultaneously.
Use write_audit() in every endpoint that needs accountability tracking.
"""
import structlog
import structlog.contextvars
from sqlalchemy.orm import Session

from app.database.models.audit_log import AuditLog
from app.audit.events import AuditEvent

log = structlog.get_logger(__name__)


def write_audit(
    db: Session,
    event: AuditEvent,
    status: str,                        # "success" | "failure"
    user_id: str | None = None,
    user_email: str | None = None,
    resource_id: str | None = None,
    resource_type: str | None = None,
    details: dict | None = None,
    error_message: str | None = None,
    ip_address: str | None = None,
) -> None:
    """
    Write an audit event to the database AND emit a structured log line.

    The request_id and client_ip are pulled automatically from the current
    request context (set by RequestLoggerMiddleware), so you never need to
    pass them explicitly.
    """
    ctx = structlog.contextvars.get_contextvars()
    request_id = ctx.get("request_id")
    client_ip = ip_address or ctx.get("client_ip")

    # 1. Persist to database
    record = AuditLog(
        event=event,
        user_id=user_id,
        user_email=user_email,
        ip_address=client_ip,
        request_id=request_id,
        resource_id=resource_id,
        resource_type=resource_type,
        status=status,
        details=details,
        error_message=error_message,
    )
    db.add(record)
    db.commit()

    # 2. Emit structured log line (warning level for failures)
    log_fn = log.info if status == "success" else log.warning
    log_fn(
        event,
        status=status,
        user_id=user_id,
        user_email=user_email,
        resource_id=resource_id,
        resource_type=resource_type,
        **({"details": details} if details else {}),
        **({"error": error_message} if error_message else {}),
    )
