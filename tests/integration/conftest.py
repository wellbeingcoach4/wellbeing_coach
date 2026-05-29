"""Shared fixtures for API integration tests."""

import os
import sys
from pathlib import Path

import pytest
import sqlalchemy
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# SQLite + import path setup before app modules load.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_real_create_engine = sqlalchemy.create_engine


def _patched_create_engine(url, *args, **kwargs):
    """Drop unsupported pool args when tests run against SQLite."""
    if str(url).startswith("sqlite"):
        kwargs.pop("pool_size", None)
        kwargs.pop("max_overflow", None)
    return _real_create_engine(url, *args, **kwargs)


sqlalchemy.create_engine = _patched_create_engine

from app.database.models import Base  # noqa: E402
from app.database.connection import get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def db_engine():
    """Create an isolated in-memory database per test function."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def client(db_engine):
    """Provide a FastAPI TestClient bound to the test database session."""
    session_factory = sessionmaker(
        autocommit=False, autoflush=False, bind=db_engine
    )

    def override_get_db():
        """Dependency override that yields a short-lived DB session."""
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def mock_chat_completion(monkeypatch):
    """Mock OpenAI-compatible chat completion responses across services."""

    def _install(response_text: str):
        class _Response:
            status_code = 200
            text = ""

            def raise_for_status(self):
                if self.status_code >= 400:
                    raise RuntimeError(f"HTTP {self.status_code}")

            def json(self):
                return {
                    "choices": [
                        {"message": {"content": response_text}}
                    ]
                }

        class _AsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

            async def post(self, *args, **kwargs):
                return _Response()

        monkeypatch.setattr(
            "app.service.mood_analyser.httpx.AsyncClient",
            _AsyncClient,
        )
        monkeypatch.setattr(
            "app.service.wellbeing_service.httpx.AsyncClient",
            _AsyncClient,
        )
        monkeypatch.setattr(
            "app.service.user_history_service.httpx.AsyncClient",
            _AsyncClient,
        )

    return _install
