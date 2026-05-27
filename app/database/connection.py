"""
Database connection and session management for PostgreSQL
"""
import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.database.models import Base

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:passShubhi@localhost:5432/wellbeing_coach"
).strip()

# Create database engine
engine = create_engine(
    DATABASE_URL,
    echo=os.getenv("SQL_ECHO", "False").strip().lower() == "true",
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """
    Dependency function to get database session
    Usage in FastAPI: 
        @app.get("/")
        def read_root(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        logger.debug("Opened database session")
        yield db
    except Exception:
        logger.exception("Database session yielded an exception")
        raise
    finally:
        db.close()
        logger.debug("Closed database session")


def init_db():
    """
    Initialize database by creating all tables
    Call this on application startup
    """
    logger.info("Creating database tables if they do not exist")
    Base.metadata.create_all(bind=engine)


def close_db():
    """
    Close all database connections
    Call this on application shutdown
    """
    logger.info("Disposing database engine")
    engine.dispose()
