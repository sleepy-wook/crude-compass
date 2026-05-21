"""reports table repo — event-driven AI report inbox (2026-05-21).

Schema: databricks/schemas/lakebase.sql §6.
Migration: app/db/lakebase.py migrate_reports().

Write paths:
- trigger_detector + report_generator → insert_report (Phase 2)
- manager UI/Slack [보관]/[Drop] → update_status (by='manager')
- AI judge stale/continuation → update_status (by='ai') / insert thread row

Read paths:
- GET /api/reports/inbox → list_pending
- GET /api/reports/{id} → get_with_thread
- GET /api/reports/archive → list_by_status
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row

from app.schemas.report import (
    Recommendation,
    Report,
    ReportCreate,
    ReportStatus,
    ReportThread,
    StatusActor,
    TriggerType,
)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────
# Row → Pydantic
# ──────────────────────────────────────────────────────────────────────
def _row_to_report(row: dict[str, Any]) -> Report:
    """psycopg3 dict_row → Report. JSONB는 이미 decoded."""
    return Report(
        report_id=row["report_id"],
        parent_id=row.get("parent_id"),
        trigger_type=row["trigger_type"],
        trigger_meta=row.get("trigger_meta") or {},
        status=row["status"],
        status_changed_at=row.get("status_changed_at"),
        status_changed_by=row.get("status_changed_by"),
        headline=row["headline"],
        summary=row["summary"],
        reasoning=row.get("reasoning") or {},
        recommendation=row.get("recommendation"),
        related_signals=row.get("related_signals") or [],
        revisits_id=row.get("revisits_id"),
        ai_drop_reason=row.get("ai_drop_reason"),
        version=row.get("version", 1),
        created_at=row["created_at"],
    )


# ──────────────────────────────────────────────────────────────────────
# Write
# ──────────────────────────────────────────────────────────────────────
def insert_report(conn: psycopg.Connection, payload: ReportCreate) -> UUID:
    """INSERT 1 report. Returns report_id.

    Dedup: trigger_meta.fingerprint가 있고 최근 24h 같은 fingerprint 존재하면
    새 row 안 만들고 기존 report_id 반환 (idempotent).

    Caller가 conn.commit() 책임. raise on failure (caller가 rollback).
    """
    fingerprint = (payload.trigger_meta or {}).get("fingerprint")

    # Dedup check — 최근 24h 같은 fingerprint
    if fingerprint:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT report_id FROM reports
                 WHERE trigger_meta->>'fingerprint' = %s
                   AND created_at > NOW() - INTERVAL '24 hours'
                 ORDER BY created_at DESC LIMIT 1
                """,
                (fingerprint,),
            )
            existing = cur.fetchone()
            if existing:
                logger.info(
                    "insert_report dedup hit (fingerprint=%s) → existing report_id=%s",
                    fingerprint, existing[0],
                )
                return existing[0]

    report_id = uuid4()
    rec_value = payload.recommendation.value if payload.recommendation else None
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO reports (
                report_id, parent_id, trigger_type, trigger_meta,
                headline, summary, reasoning, recommendation,
                related_signals, revisits_id
            ) VALUES (
                %s, %s, %s, %s::jsonb,
                %s, %s, %s::jsonb, %s,
                %s::jsonb, %s
            )
            """,
            (
                report_id,
                payload.parent_id,
                payload.trigger_type.value,
                json.dumps(payload.trigger_meta),
                payload.headline,
                payload.summary,
                json.dumps(payload.reasoning),
                rec_value,
                json.dumps(payload.related_signals),
                payload.revisits_id,
            ),
        )
    return report_id


def update_status(
    conn: psycopg.Connection,
    report_id: UUID,
    status: ReportStatus,
    by: StatusActor,
    *,
    ai_drop_reason: str | None = None,
) -> bool:
    """status 변경 + status_changed_at = NOW() + status_changed_by 기록.

    status='ai_dropped'일 때만 ai_drop_reason 사용.
    Returns True if 1 row updated.
    """
    by_value = by.value
    new_status = status.value
    try:
        with conn.cursor() as cur:
            if status == ReportStatus.AI_DROPPED and ai_drop_reason:
                cur.execute(
                    """
                    UPDATE reports
                       SET status = %s,
                           status_changed_at = NOW(),
                           status_changed_by = %s,
                           ai_drop_reason = %s,
                           version = version + 1
                     WHERE report_id = %s
                    """,
                    (new_status, by_value, ai_drop_reason, report_id),
                )
            else:
                cur.execute(
                    """
                    UPDATE reports
                       SET status = %s,
                           status_changed_at = NOW(),
                           status_changed_by = %s,
                           version = version + 1
                     WHERE report_id = %s
                    """,
                    (new_status, by_value, report_id),
                )
            return cur.rowcount == 1
    except Exception as e:
        logger.warning("update_status FAIL (report_id=%s): %s", report_id, e)
        try:
            conn.rollback()
        except Exception:
            pass
        return False


# ──────────────────────────────────────────────────────────────────────
# Read
# ──────────────────────────────────────────────────────────────────────
def list_pending(conn: psycopg.Connection, *, limit: int = 10) -> list[Report]:
    """status='pending' inbox. created_at DESC.

    idx_reports_pending (partial WHERE status='pending') 활용.
    """
    try:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT * FROM reports
                 WHERE status = 'pending'
                 ORDER BY created_at DESC
                 LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
        return [_row_to_report(r) for r in rows]
    except Exception as e:
        logger.warning("list_pending failed: %s", e)
        return []


def list_by_status(
    conn: psycopg.Connection,
    status: ReportStatus,
    *,
    limit: int = 50,
    since: datetime | None = None,
) -> list[Report]:
    """archive view — status별 filter. created_at DESC.

    since 주어지면 그 시점 이후만 (incremental polling).
    """
    try:
        with conn.cursor(row_factory=dict_row) as cur:
            if since is not None:
                cur.execute(
                    """
                    SELECT * FROM reports
                     WHERE status = %s AND created_at > %s
                     ORDER BY created_at DESC
                     LIMIT %s
                    """,
                    (status.value, since, limit),
                )
            else:
                cur.execute(
                    """
                    SELECT * FROM reports
                     WHERE status = %s
                     ORDER BY created_at DESC
                     LIMIT %s
                    """,
                    (status.value, limit),
                )
            rows = cur.fetchall()
        return [_row_to_report(r) for r in rows]
    except Exception as e:
        logger.warning("list_by_status failed (status=%s): %s", status, e)
        return []


def get_by_id(conn: psycopg.Connection, report_id: UUID) -> Report | None:
    """단일 report fetch (thread 없이)."""
    try:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM reports WHERE report_id = %s", (report_id,))
            row = cur.fetchone()
        return _row_to_report(row) if row else None
    except Exception as e:
        logger.warning("get_by_id failed (report_id=%s): %s", report_id, e)
        return None


def get_with_thread(conn: psycopg.Connection, report_id: UUID) -> ReportThread | None:
    """report + 모든 자손 (parent_id 체인) chronological.

    Recursive CTE로 root까지 거슬러 올라간 뒤 root 자손 전체.
    한 thread는 보통 1-3개 row이므로 비용 미미.
    """
    try:
        with conn.cursor(row_factory=dict_row) as cur:
            # Step 1: root 찾기 (parent_id 체인 끝까지)
            cur.execute(
                """
                WITH RECURSIVE ancestors AS (
                    SELECT * FROM reports WHERE report_id = %s
                    UNION ALL
                    SELECT r.* FROM reports r
                    JOIN ancestors a ON r.report_id = a.parent_id
                )
                SELECT * FROM ancestors WHERE parent_id IS NULL LIMIT 1
                """,
                (report_id,),
            )
            root_row = cur.fetchone()
            if not root_row:
                return None
            root = _row_to_report(root_row)

            # Step 2: root의 모든 자손 (root 포함) chronological
            cur.execute(
                """
                WITH RECURSIVE descendants AS (
                    SELECT * FROM reports WHERE report_id = %s
                    UNION ALL
                    SELECT r.* FROM reports r
                    JOIN descendants d ON r.parent_id = d.report_id
                )
                SELECT * FROM descendants ORDER BY created_at ASC
                """,
                (root.report_id,),
            )
            rows = cur.fetchall()
        thread = [_row_to_report(r) for r in rows]
        return ReportThread(root=root, thread=thread)
    except Exception as e:
        logger.warning("get_with_thread failed (report_id=%s): %s", report_id, e)
        return None


def find_similar_in_archive(
    conn: psycopg.Connection,
    *,
    trigger_type: TriggerType,
    days: int = 90,
    limit: int = 5,
) -> list[Report]:
    """동일 trigger_type + 최근 N일 dropped/ai_dropped reports.

    Phase 9 (AI revisit detection)에서 사용 — 새 trigger 발생 시 archive 검색,
    동일 시그널이 archive에 있으면 revisits_id 채워서 새 report.

    실제 유사도 판정은 caller가 LLM judge로 처리; 여기서는 후보만 fetch.
    """
    try:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT * FROM reports
                 WHERE trigger_type = %s
                   AND status IN ('dropped', 'ai_dropped')
                   AND created_at > NOW() - (%s::int * INTERVAL '1 day')
                 ORDER BY created_at DESC
                 LIMIT %s
                """,
                (trigger_type.value, days, limit),
            )
            rows = cur.fetchall()
        return [_row_to_report(r) for r in rows]
    except Exception as e:
        logger.warning("find_similar_in_archive failed: %s", e)
        return []


def list_kept_for_date(
    conn: psycopg.Connection,
    target_date,
    *,
    limit: int = 50,
) -> list[Report]:
    """target_date에 status='kept'로 전환된 reports.

    daily_report 06:30 cron이 어제 분 모을 때 사용.
    """
    try:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT * FROM reports
                 WHERE status = 'kept'
                   AND DATE(status_changed_at) = %s
                 ORDER BY status_changed_at ASC
                 LIMIT %s
                """,
                (target_date, limit),
            )
            rows = cur.fetchall()
        return [_row_to_report(r) for r in rows]
    except Exception as e:
        logger.warning("list_kept_for_date failed (date=%s): %s", target_date, e)
        return []
