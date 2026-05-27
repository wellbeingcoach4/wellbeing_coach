"""Integration tests for wellbeing activity endpoints."""


def test_get_activities(client):
    """Verify the seeded wellbeing activity catalog is returned."""
    response = client.get("/wellbeing/activities")

    assert response.status_code == 200
    body = response.json()
    assert len(body["activities"]) >= 1
    assert "activity_id" in body["activities"][0]


def test_select_activity_success(client, mock_chat_completion):
    """Verify selecting a predefined activity returns an AI-generated session."""
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
            "mood": "stressed",
            "user_reason_for_mood": "Busy workday",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["activity_name"] == "Meditation"
    assert body["session_plan"]["session_title"] == "Calm Breathing"
    assert body["database_id"] is not None


def test_select_custom_activity(client, mock_chat_completion):
    """Verify activity_id=0 accepts and stores a custom activity name."""
    mock_chat_completion(
        '{"session_title":"Custom Yoga","session_steps":["Warm up","Stretch"],'
        '"estimated_duration":"20 minutes","mood_addressed":"Anxiety support"}'
    )

    response = client.post(
        "/wellbeing/select-activity",
        json={
            "user_id": "user01",
            "activity_id": 0,
            "available_time_minutes": 20,
            "custom_activity": "Morning yoga flow",
            "mood": "anxious",
        },
    )

    assert response.status_code == 200
    assert response.json()["activity_name"] == "Morning yoga flow"


def test_select_activity_invalid_id(client):
    """Invalid activity IDs should surface as a 400 from the route layer."""
    response = client.post(
        "/wellbeing/select-activity",
        json={
            "user_id": "user01",
            "activity_id": 999,
            "available_time_minutes": 10,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid activity_id"


def test_select_activity_missing_custom_activity(client):
    """Schema validation should reject activity_id=0 without custom_activity."""
    response = client.post(
        "/wellbeing/select-activity",
        json={
            "user_id": "user01",
            "activity_id": 0,
            "available_time_minutes": 10,
        },
    )

    assert response.status_code == 422
