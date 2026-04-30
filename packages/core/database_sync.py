"""Synchronous database engine for RQ workers and scripts."""

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from packages.core.config import get_settings

_sync_engine = None
_sync_session_factory = None


def get_sync_engine():
    """Create or return cached sync engine (psycopg2)."""
    global _sync_engine
    if _sync_engine is None:
        settings = get_settings()
        _sync_engine = create_engine(
            settings.database_url_sync,
            echo=settings.debug,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
    return _sync_engine


def get_sync_session_factory() -> sessionmaker[Session]:
    """Return cached session factory for sync operations."""
    global _sync_session_factory
    if _sync_session_factory is None:
        _sync_session_factory = sessionmaker(
            bind=get_sync_engine(),
            class_=Session,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _sync_session_factory


@contextmanager
def sync_session_scope() -> Generator[Session, None, None]:
    """Context manager that commits on success and rolls back on error."""
    factory = get_sync_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
