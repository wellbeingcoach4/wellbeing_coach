"""Unit tests for repository exception/rollback branches.

These tests use a minimal FakeSession to exercise the `except Exception`
paths in save_* and query helpers that the integration tests cannot
easily reach without forcing a real DB error.
"""

from datetime import datetime, timedelta

import pytest

from app.database import repository


class _FailingSession:
    """Session stub whose every meaningful op raises."""

    def __init__(self):
        self.rollback_called = False

    def add(self, _obj):
        raise RuntimeError("add failed")

    def commit(self):
        raise RuntimeError("commit failed")

    def refresh(self, _obj):
        raise RuntimeError("refresh failed")

    def rollback(self):
        self.rollback_called = True

    def query(self, *_args, **_kwargs):
        raise RuntimeError("query failed")


# ---------------------------------------------------------------------------
# save_* rollback branches
# ---------------------------------------------------------------------------

def test_save_mood_analysis_returns_none_and_rolls_back_on_failure():
    db = _FailingSession()
    result = repository.save_mood_analysis(
        db=db,
        user_id="u1",
        input_text="hi",
        mood_analysed="happy",
        reason_for_mood="reason",
        confidence_score=0.9,
        llm_provider="ollama",
    )
    assert result is None
    assert db.rollback_called is True


def test_save_user_activity_selection_returns_none_and_rolls_back_on_failure():
    db = _FailingSession()
    result = repository.save_user_activity_selection(
        db=db,
        user_id="u1",
        activity_id=1,
        activity_name="Breathing",
        available_time_minutes=5,
        ai_session_title="t",
        ai_session_steps=["a"],
        ai_estimated_duration="5m",
        llm_provider="ollama",
    )
    assert result is None
    assert db.rollback_called is True


def test_save_feedback_returns_none_and_rolls_back_on_failure():
    db = _FailingSession()
    result = repository.save_feedback(
        db=db,
        user_id="u1",
        feedback_text="bad",
        activity_selection="Meditation",
        user_activity_selection_id=1,
        rating=1,
    )
    assert result is None
    assert db.rollback_called is True


# ---------------------------------------------------------------------------
# query helper except branches
# ---------------------------------------------------------------------------

def test_get_user_moods_propagates_query_error():
    with pytest.raises(RuntimeError, match="query failed"):
        repository.get_user_moods(db=_FailingSession(), user_id="u1")


def test_get_user_feedback_propagates_query_error():
    with pytest.raises(RuntimeError, match="query failed"):
        repository.get_user_feedback(db=_FailingSession(), user_id="u1")


def test_get_user_activities_propagates_query_error():
    with pytest.raises(RuntimeError, match="query failed"):
        repository.get_user_activities(db=_FailingSession(), user_id="u1")


def test_get_user_moods_in_period_raises_on_invalid_range():
    now = datetime.utcnow()
    with pytest.raises(ValueError, match="from_date must be before or equal"):
        repository.get_user_moods_in_period(
            db=_FailingSession(),
            user_id="u1",
            from_date=now,
            to_date=now - timedelta(days=1),
        )


def test_get_user_moods_in_period_propagates_query_error():
    now = datetime.utcnow()
    with pytest.raises(RuntimeError, match="query failed"):
        repository.get_user_moods_in_period(
            db=_FailingSession(),
            user_id="u1",
            from_date=now - timedelta(days=1),
            to_date=now,
        )


def test_get_recent_feedback_for_prompt_returns_empty_on_query_error():
    """Helper swallows exceptions and returns an empty list."""
    result = repository.get_recent_feedback_for_prompt(
        db=_FailingSession(), user_id="u1", limit=3
    )
    assert result == []
