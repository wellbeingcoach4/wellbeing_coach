"""Integration tests for feedback submission API."""


def _select_activity(client, mock_chat_completion):
    mock_chat_completion(
        '{"session_title":"Calm Breathing","session_steps":["Inhale","Hold","Exhale"],'
        '"estimated_duration":"10 minutes","mood_addressed":"Stress relief"}'
    )
    response = client.post(
        "/wellbeing/select-activity",
        json={
            "user_id": "user01",
            "activity_id": 1,
            "available_time_minutes": 10,
        },
    )
    assert response.status_code == 200
    return response.json()["database_id"]


def test_submit_feedback_success(client, mock_chat_completion):
    """Valid feedback with rating should be accepted and persisted."""
    selection_id = _select_activity(client, mock_chat_completion)
    response = client.post(
        "/feedback/",
        json={
            "user_id": "user01",
            "feedback_text": "Very helpful session",
            "rating": 5,
            "activity_selection": "Meditation",
            "user_activity_selection_id": selection_id,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Feedback saved successfully"
    assert body["database_id"] is not None
    assert body["thanks_note"] == "Thanks for your feedback!"


def test_submit_feedback_without_rating(client, mock_chat_completion):
    """Rating is optional and should default to null in storage."""
    selection_id = _select_activity(client, mock_chat_completion)
    response = client.post(
        "/feedback/",
        json={
            "user_id": "user01",
            "feedback_text": "Decent experience",
            "activity_selection": "Meditation",
            "user_activity_selection_id": selection_id,
        },
    )

    assert response.status_code == 200
    assert response.json()["database_id"] is not None
