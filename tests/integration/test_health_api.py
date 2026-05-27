"""Integration test for application health endpoint."""


def test_health_check(client):
    """Health endpoint should expose service readiness metadata."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "wellbeing-coach"}
