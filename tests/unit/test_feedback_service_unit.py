from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from app.service.feedback_service import FeedbackService


def test_save_feedback_success():
    service = FeedbackService(db=Mock())
    saved_feedback = SimpleNamespace(id=42)
    selection = SimpleNamespace(user_id="u1")

    with patch(
        "app.service.feedback_service.repository.get_user_activity_selection_by_id",
        return_value=selection,
    ), patch(
        "app.service.feedback_service.repository.save_feedback",
        return_value=saved_feedback,
    ) as mock_save:
        result = service.save_feedback(
            user_id="u1",
            feedback_text="Very helpful",
            activity_selection="Meditation",
            user_activity_selection_id=10,
            rating=5,
        )

    mock_save.assert_called_once()
    assert result["database_id"] == 42
    assert result["message"] == "Feedback saved successfully"


def test_save_feedback_without_rating():
    service = FeedbackService(db=Mock())
    saved_feedback = SimpleNamespace(id=99)
    selection = SimpleNamespace(user_id="u1")

    with patch(
        "app.service.feedback_service.repository.get_user_activity_selection_by_id",
        return_value=selection,
    ), patch(
        "app.service.feedback_service.repository.save_feedback",
        return_value=saved_feedback,
    ) as mock_save:
        result = service.save_feedback(
            user_id="u1",
            feedback_text="OK experience",
            activity_selection="Journaling",
            user_activity_selection_id=3,
        )

    assert mock_save.call_args.kwargs["rating"] is None
    assert result["database_id"] == 99


def test_save_feedback_raises_when_repository_fails():
    service = FeedbackService(db=Mock())
    selection = SimpleNamespace(user_id="u1")

    with patch(
        "app.service.feedback_service.repository.get_user_activity_selection_by_id",
        return_value=selection,
    ), patch(
        "app.service.feedback_service.repository.save_feedback",
        return_value=None,
    ):
        with pytest.raises(ValueError, match="Failed to save feedback"):
            service.save_feedback(
                user_id="u1",
                feedback_text="Bad",
                activity_selection="Meditation",
                user_activity_selection_id=1,
                rating=1,
            )


def test_save_feedback_rejects_unknown_session():
    service = FeedbackService(db=Mock())

    with patch(
        "app.service.feedback_service.repository.get_user_activity_selection_by_id",
        return_value=None,
    ):
        with pytest.raises(ValueError, match="Invalid user_activity_selection_id"):
            service.save_feedback(
                user_id="u1",
                feedback_text="Bad",
                activity_selection="Meditation",
                user_activity_selection_id=999,
            )
