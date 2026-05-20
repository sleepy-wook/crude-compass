"""Decision Room API tests — graceful when Lakebase unavailable.

last-seen GET/POST + queue + delta endpoints.
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ────────────────────────────────────────────────────────────────────
# /last-seen + /touch
# ────────────────────────────────────────────────────────────────────
def test_last_seen_returns_shape():
    response = client.get("/api/decision-room/last-seen")
    assert response.status_code == 200
    body = response.json()
    assert "last_seen_at" in body  # None on Lakebase 미연결
    assert "user_key" in body
    assert body["user_key"] == "default"


def test_touch_returns_timestamp_shape():
    response = client.post("/api/decision-room/touch")
    assert response.status_code == 200
    body = response.json()
    assert "last_seen_at" in body  # None on Lakebase 미연결
    assert body["user_key"] == "default"


def test_touch_then_get_consistent_shape():
    """touch 후 GET — graceful 환경에서도 shape 일관."""
    touch_resp = client.post("/api/decision-room/touch")
    get_resp = client.get("/api/decision-room/last-seen")
    assert touch_resp.status_code == 200
    assert get_resp.status_code == 200
    # Lakebase 연결되면 동일 timestamp 기대. 미연결 시 둘 다 None.
    assert set(touch_resp.json().keys()) == {"last_seen_at", "user_key"}
    assert set(get_resp.json().keys()) == {"last_seen_at", "user_key"}


# ────────────────────────────────────────────────────────────────────
# /queue
# ────────────────────────────────────────────────────────────────────
def test_queue_returns_grouped_shape():
    response = client.get("/api/decision-room/queue")
    assert response.status_code == 200
    body = response.json()
    assert "needs_you" in body and isinstance(body["needs_you"], list)
    assert "monitoring" in body and isinstance(body["monitoring"], list)
    assert "counts" in body
    counts = body["counts"]
    for k in ("needs_you", "monitoring", "proposed", "at_risk", "active", "on_track", "paused"):
        assert k in counts and isinstance(counts[k], int)


def test_queue_needs_you_proposed_only_in_needs_you():
    """proposed/at_risk만 needs_you, active/on_track/paused만 monitoring."""
    response = client.get("/api/decision-room/queue")
    body = response.json()
    for m in body["needs_you"]:
        assert m["status"] in ("proposed", "at_risk")
    for m in body["monitoring"]:
        assert m["status"] in ("active", "on_track", "paused")


# ────────────────────────────────────────────────────────────────────
# /delta
# ────────────────────────────────────────────────────────────────────
def test_delta_returns_expected_shape():
    response = client.get("/api/decision-room/delta")
    assert response.status_code == 200
    body = response.json()
    assert "since" in body  # ISO str | None
    assert "events" in body and isinstance(body["events"], list)
    assert "counts" in body
    counts = body["counts"]
    for k in ("new_proposed", "status_change", "pivot", "total"):
        assert k in counts and isinstance(counts[k], int)


def test_delta_event_types_constrained():
    """각 event는 알려진 type 중 하나."""
    response = client.get("/api/decision-room/delta")
    body = response.json()
    for ev in body["events"]:
        assert ev["type"] in ("new_proposed", "status_change", "pivot")
        assert "case_id" in ev
        assert "occurred_at" in ev
