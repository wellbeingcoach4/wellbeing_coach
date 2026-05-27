# test_feedback_service.py

import pytest
from unittest.mock import MagicMock, patch

from app.service.feedback_service import FeedbackService


class TestFeedbackService:

    @patch("app.services.feedback_service.repository.save_feedback")
    def test_save_feedback_success(self, mock_save_feedback):
        # Arrange
        mock_db = MagicMock()

        mock_saved_feedback = MagicMock()
        mock_saved_feedback.id = 123

        mock_save_feedback.return_value = mock_saved_feedback

        service = FeedbackService(db=mock_db)

        # Act
        result = service.save_feedback(
            user_id="user_1",
            feedback_text="Great service!",
            rating=5
        )

        # Assert
        mock_save_feedback.assert_called_once_with(
            db=mock_db,
            user_id="user_1",
            feedback_text="Great service!",
            rating=5
        )

        assert result == {
            "message": "Feedback saved successfully",
            "database_id": 123,
            "thanks_note": "Thanks for your feedback!"
        }

    @patch("app.services.feedback_service.repository.save_feedback")
    def test_save_feedback_failure(self, mock_save_feedback):
        # Arrange
        mock_db = MagicMock()

        mock_save_feedback.return_value = None

        service = FeedbackService(db=mock_db)

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            service.save_feedback(
                user_id="user_1",
                feedback_text="Bad experience",
                rating=1
            )

        assert str(exc_info.value) == "Failed to save feedback"

        mock_save_feedback.assert_called_once_with(
            db=mock_db,
            user_id="user_1",
            feedback_text="Bad experience",
            rating=1
        )

    @patch("app.services.feedback_service.repository.save_feedback")
    def test_save_feedback_without_rating(self, mock_save_feedback):
        # Arrange
        mock_db = MagicMock()

        mock_saved_feedback = MagicMock()
        mock_saved_feedback.id = 456

        mock_save_feedback.return_value = mock_saved_feedback

        service = FeedbackService(db=mock_db)

        # Act
        result = service.save_feedback(
            user_id="user_2",
            feedback_text="Average experience"
        )

        # Assert
        mock_save_feedback.assert_called_once_with(
            db=mock_db,
            user_id="user_2",
            feedback_text="Average experience",
            rating=None
        )

        assert result["database_id"] == 456
        assert result["message"] == "Feedback saved successfully"