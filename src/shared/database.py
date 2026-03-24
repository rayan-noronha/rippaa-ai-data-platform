"""Database connection management for PostgreSQL + pgvector."""

import structlog
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from src.shared.config import get_settings

logger = structlog.get_logger(__name__)


def get_engine() -> "Engine":
    """Create and return a SQLAlchemy engine."""
    settings = get_settings()
    engine = create_engine(
        settings.database_url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        echo=settings.debug,
    )
    return engine


def get_session_factory() -> sessionmaker[Session]:
    """Return a session factory bound to the engine."""
    engine = get_engine()
    return sessionmaker(bind=engine, expire_on_commit=False)


def check_database_health() -> bool:
    """Verify database connectivity and pgvector extension."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            result = conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'"))
            has_pgvector = result.fetchone() is not None
            if not has_pgvector:
                logger.warning("pgvector extension not found in database")
                return False
            return True
    except Exception:
        logger.exception("Database health check failed")
        return False
