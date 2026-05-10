"""Sprint 1 smoke test — import 가능 + health endpoint 응답 검증."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_app_imports() -> None:
    assert app.title == "Crude Compass"


def test_health_endpoint() -> None:
    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data
