"""Database session management for Violence Detection System (SQLite)."""
import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base
from ..utils.logging import get_logger

logger = get_logger(__name__)

_engine = None
_SessionFactory = None


def init_db(db_url: str = None):
    """Initialize database engine and create tables."""
    global _engine, _SessionFactory

    if db_url is None:
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
        os.makedirs(db_path, exist_ok=True)
        db_url = f'sqlite:///{os.path.join(db_path, "violence_detection.db")}'

    _engine = create_engine(db_url, echo=False, connect_args={'check_same_thread': False})
    _SessionFactory = sessionmaker(bind=_engine)

    Base.metadata.create_all(_engine)
    logger.info(f"Database initialized: {db_url}")


@contextmanager
def get_db_session():
    """Context manager for database sessions."""
    global _SessionFactory
    if _SessionFactory is None:
        init_db()

    session = _SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
