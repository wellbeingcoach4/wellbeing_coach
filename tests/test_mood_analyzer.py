"""
Sample tests for mood analyzer service.

Run with:
    pytest tests/test_mood_analyzer.py -v
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.models import Base
from app.service.mood_analyser import MoodAnalyzerService


@pytest.fixture
def test_db():
    """Create an in-memory SQLite database for testing."""

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(bind=engine)

    testing_session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    db = testing_session_local()

    yield db

    db.close()


def test_parse_llm_response_valid_json(test_db):
    """Test parsing valid JSON response."""

    service = MoodAnalyzerService(db=test_db)

    response_text = """
    {
        "mood_analysed": "happy",
        "reason_for_mood": "Positive language detected"
    }
    """

    result = service._parse_llm_response(response_text)

    assert result is not None
    assert result["mood_analysed"] == "happy"
    assert (
        result["reason_for_mood"]
        == "Positive language detected"
    )


def test_parse_llm_response_with_markdown(test_db):
    """Test parsing JSON response wrapped in markdown."""

    service = MoodAnalyzerService(db=test_db)

    response_text = """
    json
    {
        "mood_analysed": "sad",
        "reason_for_mood":
        "Negative expressions and sadness indicators"
    }
    
    """

    result = service._parse_llm_response(response_text)

    assert result is not None
    assert result["mood_analysed"] == "sad"


def test_parse_llm_response_invalid_json(test_db):
    """Test parsing invalid JSON response."""

    service = MoodAnalyzerService(db=test_db)

    response_text = "This is not valid JSON"

    result = service._parse_llm_response(response_text)

    assert result is None


def test_parse_llm_response_missing_fields(test_db):
    """Test parsing JSON with missing required fields."""

    service = MoodAnalyzerService(db=test_db)

    response_text = '{"mood_analysed": "happy"}'

    result = service._parse_llm_response(response_text)

    assert result is None


def test_default_response(test_db):
    """Test default fallback response."""

    service = MoodAnalyzerService(db=test_db)

    default = service._get_default_response()

    assert default["mood_analysed"] == "neutral"
    assert default["provider_used"] == "default"
    assert default["confidence_score"] == 0.0


def test_store_mood_analysis(test_db):
    """Test storing mood analysis in database."""

    service = MoodAnalyzerService(db=test_db)

    record = service._store_mood_analysis(
        user_id="test_user",
        input_text="I am happy",
        mood_analysed="happy",
        reason_for_mood="Positive expression",
        confidence_score=0.95,
        llm_provider="ollama",
    )

    assert record is not None
    assert record.user_id == "test_user"
    assert record.mood_analysed == "happy"
    assert record.llm_provider == "ollama"


def test_get_mood_history(test_db):
    """Test retrieving mood history."""

    service = MoodAnalyzerService(db=test_db)

    for index in range(3):
        service._store_mood_analysis(
            user_id="test_user",
            input_text=f"Text {index}",
            mood_analysed="happy",
            reason_for_mood=f"Reason {index}",
            confidence_score=0.9,
            llm_provider="ollama",
        )

    history = service.get_mood_history(
        user_id="test_user",
        limit=10,
    )

    assert len(history) == 3

    assert all(
        record.user_id == "test_user"
        for record in history
    )


def test_get_mood_history_empty(test_db):
    """Test retrieving empty mood history."""

    service = MoodAnalyzerService(db=test_db)

    history = service.get_mood_history(
        user_id="nonexistent_user",
        limit=10,
    )

    assert len(history) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
