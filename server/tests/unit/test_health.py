"""Smoke tests — verify the app factory boots and /health responds."""


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert "version" in data


def test_api_v1_ping(client):
    response = client.get("/api/v1/ping")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["api_version"] == "v1"