"""api/reports.py + admin trigger-now smoke tests.

LAKEBASE_HOST + Databricks SQL Warehouse access 필요. 없으면 skip.
"""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.skipif(
    not os.getenv("LAKEBASE_HOST"),
    reason="LAKEBASE_HOST not set — Lakebase + Warehouse integration test skipped",
)


@pytest.fixture(scope="module")
def client():
    from app.main import create_app
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_admin_trigger_now_force_creates_report(client):
    """force=true → trigger 없어도 dummy event 1건으로 LLM call + insert."""
    r = client.post("/api/admin/reports/trigger-now", params={"force": "true"})
    assert r.status_code == 200
    data = r.json()
    assert data["events_detected"] >= 1
    # 최소 1건 success (LLM 가용 가정)
    any_ok = any(res.get("ok") for res in data["results"])
    assert any_ok
    ok_res = next(res for res in data["results"] if res.get("ok"))
    assert "report_id" in ok_res
    assert ok_res["headline"]


def test_inbox_returns_pending(client):
    r = client.get("/api/reports/inbox", params={"limit": 50})
    assert r.status_code == 200
    data = r.json()
    assert "count" in data
    assert "items" in data
    # 위 test 후이므로 최소 1건
    assert data["count"] >= 1
    # 모두 pending
    for item in data["items"]:
        assert item["status"] == "pending"


def test_get_report_404_for_unknown(client):
    r = client.get("/api/reports/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "NOT_FOUND"


def test_keep_then_idempotent_replay(client):
    # 보관 가능한 pending report 1건 확보
    inbox = client.get("/api/reports/inbox").json()
    if inbox["count"] == 0:
        # trigger force로 1건 만듦
        client.post("/api/admin/reports/trigger-now", params={"force": "true"})
        inbox = client.get("/api/reports/inbox").json()
    assert inbox["count"] >= 1
    rid = inbox["items"][0]["report_id"]

    r1 = client.post(f"/api/reports/{rid}/keep")
    assert r1.status_code == 200
    assert r1.json()["new_status"] == "kept"

    # 같은 보고서 재호출 → no_change idempotent
    r2 = client.post(f"/api/reports/{rid}/keep")
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2.get("no_change") is True
    assert body2["current_status"] == "kept"


def test_drop_endpoint(client):
    # 새 pending 1건 trigger
    client.post("/api/admin/reports/trigger-now", params={"force": "true"})
    inbox = client.get("/api/reports/inbox").json()
    if inbox["count"] == 0:
        pytest.skip("no pending report available to drop")
    rid = inbox["items"][0]["report_id"]

    r = client.post(f"/api/reports/{rid}/drop")
    assert r.status_code == 200
    assert r.json()["new_status"] == "dropped"


def test_archive_filter_by_status(client):
    r = client.get("/api/reports/archive", params={"status": "kept", "limit": 50})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "kept"
    for item in data["items"]:
        assert item["status"] == "kept"

    # invalid status → 422 (Pydantic validation)
    r = client.get("/api/reports/archive", params={"status": "invalid"})
    assert r.status_code == 422


def test_investigate_stub(client):
    inbox = client.get("/api/reports/inbox").json()
    if inbox["count"] == 0:
        client.post("/api/admin/reports/trigger-now", params={"force": "true"})
        inbox = client.get("/api/reports/inbox").json()
    if inbox["count"] == 0:
        pytest.skip("no report available")
    rid = inbox["items"][0]["report_id"]

    r = client.post(f"/api/reports/{rid}/investigate")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert r.json()["status"] == "queued"


def test_trigger_now_invalid_trigger_type(client):
    r = client.post("/api/admin/reports/trigger-now", params={"trigger_type": "wrong"})
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "INVALID_TRIGGER_TYPE"


def test_trigger_now_selective_force(client):
    """trigger_type=gdelt_signal + force → gdelt dummy 1건만 생성 (price/pattern 안 함)."""
    r = client.post(
        "/api/admin/reports/trigger-now",
        params={"trigger_type": "gdelt_signal", "force": "true"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["events_detected"] == 1
    res = data["results"][0]
    assert res["ok"] is True
    # fingerprint가 manual:... (forced dummy)
    assert res["fingerprint"].startswith("manual:")


def test_get_report_with_thread(client):
    """단건 + thread (parent_id chain) round-trip."""
    inbox = client.get("/api/reports/inbox").json()
    if inbox["count"] == 0:
        client.post("/api/admin/reports/trigger-now", params={"force": "true"})
        inbox = client.get("/api/reports/inbox").json()
    if inbox["count"] == 0:
        pytest.skip("no report")
    rid = inbox["items"][0]["report_id"]
    r = client.get(f"/api/reports/{rid}")
    assert r.status_code == 200
    body = r.json()
    # rid가 root이거나 root의 thread에 있어야 함
    assert body["root"]["parent_id"] is None  # root는 항상 parent_id 없음
    assert body["thread_length"] >= 1
    assert any(item["report_id"] == rid for item in body["thread"])
