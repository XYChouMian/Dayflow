"""Database setup and session management."""

import logging
from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# Base class for all models
Base = declarative_base()


def get_database_path() -> Path:
    """Get the path to the SQLite database file."""
    data_dir = Path.home() / "AppData" / "Local" / "Dayflow" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "dayflow.db"


def create_db_engine(db_path: Path = None) -> Engine:
    """
    Create SQLAlchemy engine for database connection.

    Args:
        db_path: Optional custom database path

    Returns:
        SQLAlchemy Engine instance
    """
    if db_path is None:
        db_path = get_database_path()

    connection_string = f"sqlite:///{db_path}"
    engine = create_engine(
        connection_string,
        echo=False,  # Set to True for SQL debugging
        pool_pre_ping=True,
        connect_args={"check_same_thread": False},  # Needed for SQLite
    )

    # Enable foreign key support for SQLite
    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


# Global session factory
_SessionFactory = None


def init_db(engine: Engine = None) -> None:
    """
    Initialize the database schema.

    Args:
        engine: Optional SQLAlchemy engine (creates default if not provided)
    """
    global _SessionFactory

    if engine is None:
        engine = create_db_engine()

    # Create all tables
    Base.metadata.create_all(engine)

    # Create session factory
    _SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)

    logger.info(f"Database initialized at: {get_database_path()}")


def get_session() -> Generator[Session, None, None]:
    """
    Get a database session (context manager).

    Yields:
        SQLAlchemy Session
    """
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


def get_session_direct() -> Session:
    """
    Get a database session directly (without context manager).

    Returns:
        SQLAlchemy Session
    """
    if _SessionFactory is None:
        init_db()

    return _SessionFactory()
