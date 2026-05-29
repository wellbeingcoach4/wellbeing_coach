"""
Unit tests for Wellbeing Service module.

This test suite validates:
- wellbeing session generation
- database interactions
- validation handling
- AI response processing
- service integration logic
"""


import asyncio
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from pydantic import ValidationError

from app.database.models import Base
from app.database import repository
from app.schema.wellbeing_schema import ActivitySelectionRequest
from app.service.wellbeing_service import WellbeingService


@pytest.fixture
def test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    yield db

    db.close()


def test_activity_selection_request_requires_custom_activity_for_zero_id():
    with pytest.raises(ValidationError):
        ActivitySelectionRequest(
            user_id="user_1",
            activity_id=0,
            available_time_minutes=20,
            mood="stressed",
            user_reason_for_mood="I have a lot on my plate",
        )


def test_activity_selection_zero_id_uses_custom_activity(test_db, monkeypatch):
    service = WellbeingService(db=test_db)

    async def mock_try_llm_request(
        self,
        provider,
        activity_name,
        available_time,
        mood=None,
        user_reason_for_mood=None,
        custom_activity=None,
    ):
        assert activity_name == "Morning yoga flow"
        assert custom_activity == "Morning yoga flow"
        return {
            "session_title": "Custom Yoga Session",
            "session_steps": ["Warm up", "Stretch", "Breathe deeply"],
            "estimated_duration": "20 minutes",
            "mood_addressed": "Stress relief for a busy day",
        }

    def mock_save_user_activity_selection(
        db,
        user_id,
        activity_id,
        activity_name,
        available_time_minutes,
        ai_session_title,
        ai_session_steps,
        ai_estimated_duration,
        llm_provider,
        user_reason_for_mood=None,
        custom_activity=None,
    ):
        assert activity_id == 0
        assert activity_name == "Morning yoga flow"
        assert custom_activity == "Morning yoga flow"
        return SimpleNamespace(id=123)

    monkeypatch.setattr(
        WellbeingService, "_try_llm_request", mock_try_llm_request)
    monkeypatch.setattr(repository, "save_user_activity_selection",
                        mock_save_user_activity_selection)

    result = asyncio.run(
        service.select_activity(
            user_id="user_1",
            activity_id=0,
            available_time_minutes=20,
            mood="stressed",
            user_reason_for_mood="I need a reset",
            custom_activity="Morning yoga flow",
        )
    )

    assert result["activity_name"] == "Morning yoga flow"
    assert result["database_id"] == 123
    assert result["session_plan"]["session_title"] == "Custom Yoga Session"
