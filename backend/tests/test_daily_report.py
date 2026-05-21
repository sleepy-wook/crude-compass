"""daily_report service + API smoke tests.

LAKEBASE_HOST + Databricks SQL Warehouse + Haiku endpoint 필요. 없으면 skip.
"""
from __future__ import annotations

import os
from datetime import date, timedelta

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


# ─────────────────────────────────────────────────────────────────────
# Service layer
# ─────────────────────────────────────────────────────────────────────
def test_generate_daily_report_creates_row():
    """generate_daily_report overwrite=True → daily_reports에 INSERT."""
    from app.db.lakebase import acquire
    from app.db.repositories import daily_reports as dr
    from app.services.daily_report import generate_daily_report

    # 다른 테스트랑 충돌 안 나게 fake epoch-based date
    base = date(1993, 1, 1)
    from datetime import datetime, timezone
    offset = int(datetime.now(timezone.utc).timestamp() * 1000) % 9000
    test_date = base + timedelta(days=offset)

    daily_id = generate_daily_report(target_date=test_date, overwrite=True)
    assert daily_id is not None

    with acquire() as conn:
        got = dr.get_for_date(conn, test_date)
    assert got is not None
    assert got.daily_id == daily_id
    assert got.report_date == test_date
    # ratio_suggestion 필수 키들
    rs = got.ratio_suggestion
    assert "direction" in rs
    assert rs["direction"] in {"lean_hedge", "neutral", "lean_opportunity"}
    assert "term_delta_pct" in rs
    assert "spot_delta_pct" in rs
    # confidence 범위
    assert got.confidence is not None
    assert 0 <= got.confidence <= 100


def test_generate_daily_report_skip_if_exists():
    """overwrite=False + 이미 존재 → 기존 daily_id 반환 (skip)."""
    from app.services.daily_report import generate_daily_report

    base = date(1994, 1, 1)
    from datetime import datetime, timezone
    offset = int(datetime.now(timezone.utc).timestamp() * 1000) % 9000
    test_date = base + timedelta(days=offset)

    # 1번째 — 생성
    daily_id_1 = generate_daily_report(target_date=test_date, overwrite=False)
    assert daily_id_1 is not None

    # 2번째 — overwrite=False → 같은 daily_id 반환
    daily_id_2 = generate_daily_report(target_date=test_date, overwrite=False)
    assert daily_id_2 == daily_id_1


def test_generate_daily_report_overwrite_replaces():
    """overwrite=True → 기존 row delete + 새 row insert (다른 daily_id)."""
    from app.services.daily_report import generate_daily_report

    base = date(1995, 1, 1)
    from datetime import datetime, timezone
    offset = int(datetime.now(timezone.utc).timestamp() * 1000) % 9000
    test_date = base + timedelta(days=offset)

    daily_id_1 = generate_daily_report(target_date=test_date, overwrite=True)
    daily_id_2 = generate_daily_report(target_date=test_date, overwrite=True)
    assert daily_id_1 != daily_id_2


# ─────────────────────────────────────────────────────────────────────
# API layer
# ─────────────────────────────────────────────────────────────────────
def test_api_today_graceful_when_missing(client):
    """오늘 daily_report 있으면 반환, 없으면 null (graceful)."""
    r = client.get("/api/daily-reports/today")
    assert r.status_code == 200
    body = r.json()
    # daily_report 키 존재 (값은 dict 또는 None)
    assert "daily_report" in body


def test_api_recent_returns_list(client):
    r = client.get("/api/daily-reports/recent", params={"limit": 3})
    assert r.status_code == 200
    body = r.json()
    assert "count" in body
    assert "items" in body
    # DESC 정렬
    items = body["items"]
    if len(items) >= 2:
        for i in range(len(items) - 1):
            assert items[i]["report_date"] >= items[i + 1]["report_date"]


def test_api_get_by_date_404(client):
    r = client.get("/api/daily-reports/1850-01-01")
    assert r.status_code == 404


def test_api_admin_generate_now_idempotent(client):
    """generate-now overwrite=false → 기존 ok=True + 같은 daily_id."""
    r1 = client.post(
        "/api/admin/daily-report/generate-now",
        params={"target_date": "2026-05-21", "overwrite": "false"},
    )
    assert r1.status_code == 200
    body1 = r1.json()
    if body1.get("ok"):
        # 두번째 호출도 같은 daily_id
        r2 = client.post(
            "/api/admin/daily-report/generate-now",
            params={"target_date": "2026-05-21", "overwrite": "false"},
        )
        body2 = r2.json()
        if body2.get("ok"):
            assert body1["daily_id"] == body2["daily_id"]


def test_api_admin_generate_now_invalid_date(client):
    r = client.post(
        "/api/admin/daily-report/generate-now",
        params={"target_date": "not-a-date"},
    )
    assert r.status_code == 400
