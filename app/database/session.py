"""
Database session factory — lazy initialization.

The engine is created on first use, NOT at import time.
This prevents SQLAlchemy from crashing on startup if DATABASE_URL
is injected via Cloud Run environment variables (which arrive after
the module is first imported by Uvicorn).
"""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

_engine = None
_SessionLocal = None


def _get_engine():
    global _engine
    if _engine is None:
        from app.core.config import settings
        if not settings.database_url:
            raise RuntimeError("DATABASE_URL environment variable is not set.")
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,       # auto-reconnect on dropped connections
            pool_size=5,
            max_overflow=10,
        )
    return _engine


def SessionLocal() -> Session:  # type: ignore[override]
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=_get_engine(),
            autoflush=False,
            autocommit=False,
        )
    return _SessionLocal()