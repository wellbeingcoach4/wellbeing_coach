"""Integration tests for feedback submission API."""


def test_submit_feedback_success(client):
    """Valid feedback with rating should be accepted and persisted."""
    response = client.post(
        "/feedback/",
        json={
            "user_id": "user01",
            "feedback_text": "Very helpful session",
            "rating": 5,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Feedback saved successfully"
    assert body["database_id"] is not None
    assert body["thanks_note"] == "Thanks for your feedback!"


def test_submit_feedback_without_rating(client):
    """Rating is optional and should default to null in storage."""
    response = client.post(
        "/feedback/",
        json={
            "user_id": "user01",
            "feedback_text": "Decent experience",
        },
    )

    assert response.status_code == 200
    assert response.json()["database_id"] is not None
