def test_analyze_mood_success(client, mock_chat_completion):
    mock_chat_completion(
        '{"mood_analysed":"happy","reason_for_mood":"Positive language detected"}'
    )

    response = client.post(
        "/mood/analyze_mood",
        json={"user_id": "user01", "text": "I am feeling great today"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["mood_analysed"] == "happy"
    assert body["reason_for_mood"] == "Positive language detected"
    assert body["database_id"] is not None
    assert body["llm_provider"] in {"ollama", "groq", "gemini", "default"}


def test_analyze_mood_validation_error(client):
    response = client.post(
        "/mood/analyze_mood",
        json={"user_id": "", "text": "invalid user"},
    )

    assert response.status_code == 422
