from app.database.session import SessionLocal, LMSSessionLocal
from sqlalchemy.orm import Session
from collections.abc import Generator


def get_db() -> Generator[Session, None, None]:
    """Yields a session to THIS PROJECT's database (documents, audit, history)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_lms_db() -> Generator[Session, None, None]:
    """
    Yields a read-only session to the LMS database.
    Only raw SELECT queries via text() should be used with this session.
    The LMS DB is managed by Django — we never create/alter tables here.
    """
    db = LMSSessionLocal()
    try:
        yield db
    finally:
        db.close()