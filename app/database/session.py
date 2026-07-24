"""
Database session factories — lazy initialization.

- SessionLocal()    → This project's DB (DATABASE_URL): documents, chunks, audit, history
- LMSSessionLocal() → LMS DB (LMS_DATABASE_URL): read-only, raw SQL SELECT only
"""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

_engine = None
_SessionLocal = None

_lms_engine = None
_LMSSessionLocal = None


def _get_engine():
    global _engine
    if _engine is None:
        from app.core.config import settings
        if not settings.database_url:
            raise RuntimeError("DATABASE_URL environment variable is not set.")
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
    return _engine


def _get_lms_engine():
    global _lms_engine
    if _lms_engine is None:
        from app.core.config import settings
        if not settings.lms_database_url:
            raise RuntimeError("LMS_DATABASE_URL environment variable is not set.")
        _lms_engine = create_engine(
            settings.lms_database_url,
            pool_pre_ping=True,
            pool_size=3,
            max_overflow=5,
            # Execution options to enforce read-only behaviour
            execution_options={"no_parameters": False},
        )
    return _lms_engine


def SessionLocal() -> Session:  # type: ignore[override]
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=_get_engine(),
            autoflush=False,
            autocommit=False,
        )
    return _SessionLocal()


def LMSSessionLocal() -> Session:  # type: ignore[override]
    global _LMSSessionLocal
    if _LMSSessionLocal is None:
        _LMSSessionLocal = sessionmaker(
            bind=_get_lms_engine(),
            autoflush=False,
            autocommit=False,
        )
    return _LMSSessionLocal()