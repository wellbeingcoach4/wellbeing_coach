"""
Database package initialization module.

Exports database connection utilities, session management,
database engine configuration, and helper functions used
throughout the Wellbeing Coach application.
"""

from app.database.models import (
    Base,
    MoodAnalysis,
    UserFeedback,
    UserActivitySelection,
)

from app.database.connection import (
    engine,
    SessionLocal,
    get_db,
    init_db,
    close_db,
    DATABASE_URL,
)

_all_ = [
    "Base",
    "MoodAnalysis",
    "UserFeedback",
    "UserActivitySelection",
    "engine",
    "SessionLocal",
    "get_db",
    "init_db",
    "close_db",
    "DATABASE_URL",
]
