"""Integration tests for feedback route error handling."""

from unittest.mock import patch


def test_submit_feedback_failure_returns_400(client):
    """Service-level save failure should map to a client-facing 400 error."""
    with patch(
        "app.service.feedback_service.repository.save_feedback",
        return_value=None,
    ):
        response = client.post(
            "/feedback/",
            json={
                "user_id": "user01",
                "feedback_text": "Could not save",
                "rating": 2,
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Failed to save feedback"


def test_submit_feedback_internal_error_returns_500(client):
    """Unexpected repository exceptions should map to HTTP 500."""
    with patch(
        "app.service.feedback_service.repository.save_feedback",
        side_effect=RuntimeError("database unavailable"),
    ):
        response = client.post(
            "/feedback/",
            json={
                "user_id": "user01",
                "feedback_text": "Server error path",
            },
        )

    assert response.status_code == 500
    assert response.json()["detail"] == "database unavailable"
