"""reports + daily_reports repository smoke tests (2026-05-21 reports model).

LAKEBASE_HOST env 없으면 skip (CI 안전).
실제 Lakebase에 INSERT/UPDATE/SELECT round-trip 검증.
"""
from __future__ import annotations

import os
from datetime import date, datetime, timezone
from uuid import uuid4

import pytest

from app.db.repositories import reports as reports_repo
from app.db.repositories import daily_reports as daily_repo
from app.schemas.report import (
    DailyReportCreate,
    Recommendation,
    ReportCreate,
    ReportStatus,
    StatusActor,
    TriggerType,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("LAKEBASE_HOST"),
    reason="LAKEBASE_HOST not set — Lakebase integration test skipped",
)


# ─────────────────────────────────────────────────────────────────────
# reports
# ─────────────────────────────────────────────────────────────────────
def test_insert_and_get_report():
    from app.db.lakebase import acquire

    payload = ReportCreate(
        trigger_type=TriggerType.PRICE_SPIKE,
        trigger_meta={"dubai_pct": 2.4, "snapshot": "test"},
        headline="테스트 헤드라인",
        summary="테스트 요약 3줄.",
        reasoning={"key_signals": ["s1"], "logic": "test logic"},
        recommendation=Recommendation.DEFER_SPOT,
        related_signals=[{"type": "price", "id": "x"}],
    )
    with acquire() as conn:
        rid = reports_repo.insert_report(conn, payload)
        conn.commit()

    assert rid is not None

    with acquire() as conn:
        got = reports_repo.get_by_id(conn, rid)
    assert got is not None
    assert got.headline == "테스트 헤드라인"
    assert got.trigger_type == TriggerType.PRICE_SPIKE.value
    assert got.recommendation == Recommendation.DEFER_SPOT.value
    assert got.status == ReportStatus.PENDING.value


def test_update_status_keep():
    from app.db.lakebase import acquire

    payload = ReportCreate(
        trigger_type=TriggerType.GDELT_SIGNAL,
        trigger_meta={},
        headline="keep test",
        summary="x",
    )
    with acquire() as conn:
        rid = reports_repo.insert_report(conn, payload)
        conn.commit()
        ok = reports_repo.update_status(conn, rid, ReportStatus.KEPT, StatusActor.MANAGER)
        conn.commit()

    assert ok is True

    with acquire() as conn:
        got = reports_repo.get_by_id(conn, rid)
    assert got.status == ReportStatus.KEPT.value
    assert got.status_changed_by == StatusActor.MANAGER.value
    assert got.status_changed_at is not None


def test_update_status_ai_drop_carries_reason():
    from app.db.lakebase import acquire

    payload = ReportCreate(
        trigger_type=TriggerType.PATTERN_DRIFT,
        trigger_meta={},
        headline="ai drop test",
        summary="x",
    )
    with acquire() as conn:
        rid = reports_repo.insert_report(conn, payload)
        conn.commit()
        ok = reports_repo.update_status(
            conn, rid, ReportStatus.AI_DROPPED, StatusActor.AI,
            ai_drop_reason="시그널 약화됨",
        )
        conn.commit()

    assert ok is True

    with acquire() as conn:
        got = reports_repo.get_by_id(conn, rid)
    assert got.status == ReportStatus.AI_DROPPED.value
    assert got.ai_drop_reason == "시그널 약화됨"


def test_list_pending_returns_only_pending():
    from app.db.lakebase import acquire

    # 하나는 pending 유지, 하나는 drop
    p_pending = ReportCreate(
        trigger_type=TriggerType.GDELT_SIGNAL, headline="p1", summary="x",
    )
    p_dropped = ReportCreate(
        trigger_type=TriggerType.GDELT_SIGNAL, headline="p2", summary="x",
    )

    with acquire() as conn:
        rid_pending = reports_repo.insert_report(conn, p_pending)
        rid_dropped = reports_repo.insert_report(conn, p_dropped)
        conn.commit()
        reports_repo.update_status(conn, rid_dropped, ReportStatus.DROPPED, StatusActor.MANAGER)
        conn.commit()

    with acquire() as conn:
        pendings = reports_repo.list_pending(conn, limit=50)

    ids = [str(r.report_id) for r in pendings]
    assert str(rid_pending) in ids
    assert str(rid_dropped) not in ids


def test_thread_via_parent_id():
    from app.db.lakebase import acquire

    # parent (root) + 1 continuation
    root_payload = ReportCreate(
        trigger_type=TriggerType.GDELT_SIGNAL, headline="root", summary="x",
    )
    with acquire() as conn:
        root_id = reports_repo.insert_report(conn, root_payload)
        conn.commit()

        cont_payload = ReportCreate(
            parent_id=root_id,
            trigger_type=TriggerType.GDELT_SIGNAL,
            headline="continuation",
            summary="follow-up",
        )
        cont_id = reports_repo.insert_report(conn, cont_payload)
        conn.commit()

    # get_with_thread on root OR on continuation must both return same thread
    with acquire() as conn:
        thread_from_root = reports_repo.get_with_thread(conn, root_id)
        thread_from_cont = reports_repo.get_with_thread(conn, cont_id)

    assert thread_from_root is not None
    assert thread_from_cont is not None
    assert thread_from_root.root.report_id == root_id
    assert thread_from_cont.root.report_id == root_id  # same root
    # 최소 2개 (root + continuation)
    assert len(thread_from_root.thread) >= 2
    ids = [str(r.report_id) for r in thread_from_root.thread]
    assert str(root_id) in ids
    assert str(cont_id) in ids


def test_fingerprint_dedup_returns_existing_within_24h():
    """같은 fingerprint 2번째 insert는 기존 report_id 반환 (dedup)."""
    from app.db.lakebase import acquire
    from datetime import datetime, timezone

    fp = f"test:dedup:{datetime.now(timezone.utc).isoformat()}"
    payload = ReportCreate(
        trigger_type=TriggerType.GDELT_SIGNAL,
        trigger_meta={"fingerprint": fp},
        headline="dedup test 첫번째",
        summary="x",
    )
    with acquire() as conn:
        rid1 = reports_repo.insert_report(conn, payload)
        conn.commit()
        # 2번째 호출 — 다른 headline이라도 dedup 작동
        payload2 = ReportCreate(
            trigger_type=TriggerType.GDELT_SIGNAL,
            trigger_meta={"fingerprint": fp},
            headline="dedup test 두번째 — 무시되어야",
            summary="x",
        )
        rid2 = reports_repo.insert_report(conn, payload2)
        conn.commit()

    assert rid1 == rid2  # 같은 ID 반환


def test_fingerprint_dedup_no_fingerprint_always_inserts():
    """fingerprint 없으면 dedup 안 함 — 매번 새 row."""
    from app.db.lakebase import acquire

    payload = ReportCreate(
        trigger_type=TriggerType.GDELT_SIGNAL,
        trigger_meta={},
        headline="no fingerprint 첫번째 (10자 이상)",
        summary="x",
    )
    with acquire() as conn:
        rid1 = reports_repo.insert_report(conn, payload)
        conn.commit()
        rid2 = reports_repo.insert_report(conn, payload)
        conn.commit()

    assert rid1 != rid2  # 다른 ID


def test_find_similar_in_archive_filters_by_trigger_type():
    from app.db.lakebase import acquire

    p = ReportCreate(
        trigger_type=TriggerType.PRICE_SPIKE, headline="archived spike", summary="x",
    )
    with acquire() as conn:
        rid = reports_repo.insert_report(conn, p)
        conn.commit()
        reports_repo.update_status(conn, rid, ReportStatus.DROPPED, StatusActor.MANAGER)
        conn.commit()

    with acquire() as conn:
        # price_spike trigger인 dropped reports 검색 — rid가 결과에 포함되어야
        results = reports_repo.find_similar_in_archive(
            conn, trigger_type=TriggerType.PRICE_SPIKE, days=90, limit=20,
        )
        # gdelt trigger 검색 — rid 제외 (다른 type)
        results_other = reports_repo.find_similar_in_archive(
            conn, trigger_type=TriggerType.GDELT_SIGNAL, days=90, limit=20,
        )

    rid_str = str(rid)
    assert rid_str in [str(r.report_id) for r in results]
    assert rid_str not in [str(r.report_id) for r in results_other]


# ─────────────────────────────────────────────────────────────────────
# daily_reports
# ─────────────────────────────────────────────────────────────────────
def test_insert_and_get_daily_report():
    """report_date UNIQUE 때문에 매 테스트마다 다른 epoch 기반 date 필요.

    실제 사용은 어제 날짜이지만 테스트는 충돌 방지 위해 1990년대 fake date 사용.
    fake date도 epoch ms 기반으로 매 run 다르게.
    """
    from app.db.lakebase import acquire

    # 1990-01-01 + (now epoch ms % 1000)일  → 거의 확실히 한 번도 안 쓴 date
    base = date(1990, 1, 1)
    from datetime import timedelta as td
    offset_days = int(datetime.now(timezone.utc).timestamp() * 1000) % 9999
    test_date = base + td(days=offset_days)

    payload = DailyReportCreate(
        report_date=test_date,
        kept_report_ids=[uuid4(), uuid4()],
        kept_count=2,
        kept_summary="kept 요약",
        prev_daily_summary="어제 요약",
        market_context="시장 컨텍스트",
        ratio_suggestion={
            "direction": "lean_hedge",
            "term_delta_pct": "+5",
            "spot_delta_pct": "-5",
            "qualitative": "단기 위험 누적",
            "scenarios": [
                {"name": "base", "expected_saving_pct": 0.3},
                {"name": "bull", "expected_saving_pct": -1.1},
                {"name": "bear", "expected_saving_pct": 1.5},
            ],
        },
        reasoning="종합 분석 결과...",
        confidence=72.5,
    )

    with acquire() as conn:
        did = daily_repo.insert_daily(conn, payload)
        conn.commit()

    assert did is not None

    with acquire() as conn:
        got = daily_repo.get_for_date(conn, test_date)
    assert got is not None
    assert got.kept_count == 2
    assert got.ratio_suggestion["direction"] == "lean_hedge"
    assert got.confidence == 72.5
    assert len(got.kept_report_ids) == 2


def test_get_prev_returns_most_recent_before_date():
    from app.db.lakebase import acquire
    from datetime import timedelta as td

    # 두 개 date 삽입
    base = date(1991, 1, 1)
    offset = int(datetime.now(timezone.utc).timestamp() * 1000) % 9000
    d1 = base + td(days=offset)
    d2 = d1 + td(days=1)

    p1 = DailyReportCreate(report_date=d1, kept_count=1)
    p2 = DailyReportCreate(report_date=d2, kept_count=2)
    with acquire() as conn:
        daily_repo.insert_daily(conn, p1)
        conn.commit()
        daily_repo.insert_daily(conn, p2)
        conn.commit()

    # d2+1 직전 = d2
    with acquire() as conn:
        prev = daily_repo.get_prev(conn, d2 + td(days=1))
    assert prev is not None
    assert prev.report_date == d2

    # d2의 직전 = d1
    with acquire() as conn:
        prev = daily_repo.get_prev(conn, d2)
    assert prev is not None
    assert prev.report_date == d1


def test_list_recent_orders_desc():
    from app.db.lakebase import acquire

    with acquire() as conn:
        recent = daily_repo.list_recent(conn, limit=5)

    if len(recent) >= 2:
        for i in range(len(recent) - 1):
            assert recent[i].report_date >= recent[i + 1].report_date
