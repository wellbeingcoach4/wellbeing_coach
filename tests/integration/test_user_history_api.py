"""Integration tests for user history and periodic mood endpoints."""

from unittest.mock import patch


def _seed_user_data(client, mock_chat_completion):
    """Create one mood, feedback, and activity record for a user."""
    mock_chat_completion(
        '{"mood_analysed":"happy","reason_for_mood":"Positive day"}'
    )
    client.post(
        "/mood/analyze_mood",
        json={"user_id": "user01", "text": "Great day"},
    )

    mock_chat_completion(
        '{"session_title":"Focus Session","session_steps":["Plan","Execute"],'
        '"estimated_duration":"15 minutes","mood_addressed":"Productivity"}'
    )
    activity_response = client.post(
        "/wellbeing/select-activity",
        json={
            "user_id": "user01",
            "activity_id": 2,
            "available_time_minutes": 15,
        },
    )
    selection_id = activity_response.json()["database_id"]

    client.post(
        "/feedback/",
        json={
            "user_id": "user01",
            "feedback_text": "Helpful",
            "rating": 4,
            "activity_selection": "Breathing Exercise",
            "user_activity_selection_id": selection_id,
        },
    )


def test_get_user_history(client, mock_chat_completion):
    """The history endpoint should aggregate mood, feedback, and activity data."""
    _seed_user_data(client, mock_chat_completion)

    response = client.get("/user/user01/history")

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == "user01"
    assert body["total_moods"] == 1
    assert body["total_feedback"] == 1
    assert body["total_activities"] == 1
    assert body["mood_history"][0]["mood_analysed"] == "happy"


def test_get_periodic_mood(client, mock_chat_completion):
    """Periodic mood endpoint should return stats plus LLM analysis."""
    _seed_user_data(client, mock_chat_completion)

    mock_chat_completion(
        '{"period_analysis":"Mostly positive mood","recommendation":"Keep daily walks"}'
    )

    response = client.get(
        "/user/user01/mood/periodic",
        params={"from_date": "2020-01-01", "to_date": "2099-12-31"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == "user01"
    assert body["mood_statistics"]["total_moods"] >= 1
    assert body["period_analysis"] == "Mostly positive mood"
    assert body["recommendation"] == "Keep daily walks"


def test_get_periodic_mood_invalid_date_range(client):
    """Invalid date ranges should return a 400 validation-style response."""
    response = client.get(
        "/user/user01/mood/periodic",
        params={"from_date": "2024-02-01", "to_date": "2024-01-01"},
    )

    assert response.status_code == 400
    assert "from_date must be before or equal to to_date" in response.json()["detail"]


def test_get_user_history_empty(client):
    """A user without records should return an empty history payload."""
    response = client.get("/user/newusr/history")

    assert response.status_code == 200
    body = response.json()
    assert body["total_moods"] == 0
    assert body["total_feedback"] == 0
    assert body["total_activities"] == 0


def test_get_user_history_internal_error(client):
    """Repository errors should be wrapped into a 500 API response."""
    with patch(
        "app.service.user_history_service.db_repository.get_user_moods",
        side_effect=RuntimeError("history query failed"),
    ):
        response = client.get("/user/user01/history")

    assert response.status_code == 500
    assert "Failed to fetch user history" in response.json()["detail"]
