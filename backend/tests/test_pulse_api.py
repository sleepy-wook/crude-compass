"""Pulse REST endpoint tests — graceful degradation when Lakebase unavailable."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_pulse_recent_returns_list_shape():
    response = client.get("/api/pulse/recent?limit=20")
    assert response.status_code == 200
    body = response.json()
    assert "events" in body
    assert isinstance(body["events"], list)
    assert "count" in body
    assert isinstance(body["count"], int)


def test_pulse_recent_respects_limit_validation():
    """limit > 200은 422 (Query validation)."""
    response = client.get("/api/pulse/recent?limit=500")
    assert response.status_code == 422


def test_pulse_stats_returns_24h_aggregation():
    response = client.get("/api/pulse/stats")
    assert response.status_code == 200
    body = response.json()
    assert "total_24h" in body and isinstance(body["total_24h"], int)
    assert "by_actor" in body and isinstance(body["by_actor"], dict)
    assert "by_action" in body and isinstance(body["by_action"], dict)
    assert "active_cases" in body and isinstance(body["active_cases"], int)
