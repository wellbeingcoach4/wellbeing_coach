"""Integration tests for feedback route error handling."""

from types import SimpleNamespace
from unittest.mock import patch


def test_submit_feedback_failure_returns_400(client):
    """Service-level save failure should map to a client-facing 400 error."""
    selection = SimpleNamespace(user_id="user01")
    with patch(
        "app.service.feedback_service.repository.get_user_activity_selection_by_id",
        return_value=selection,
    ), patch(
        "app.service.feedback_service.repository.save_feedback",
        return_value=None,
    ):
        response = client.post(
            "/feedback/",
            json={
                "user_id": "user01",
                "feedback_text": "Could not save",
                "rating": 2,
                "activity_selection": "Meditation",
                "user_activity_selection_id": 1,
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Failed to save feedback"


def test_submit_feedback_internal_error_returns_500(client):
    """Unexpected repository exceptions should map to HTTP 500."""
    selection = SimpleNamespace(user_id="user01")
    with patch(
        "app.service.feedback_service.repository.get_user_activity_selection_by_id",
        return_value=selection,
    ), patch(
        "app.service.feedback_service.repository.save_feedback",
        side_effect=RuntimeError("database unavailable"),
    ):
        response = client.post(
            "/feedback/",
            json={
                "user_id": "user01",
                "feedback_text": "Server error path",
                "activity_selection": "Meditation",
                "user_activity_selection_id": 1,
            },
        )

    assert response.status_code == 500
    assert response.json()["detail"] == "database unavailable"
