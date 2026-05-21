"""daily_reports table repo — 06:30 KST cron 종합 보고서 (2026-05-21).

Schema: databricks/schemas/lakebase.sql §7.
Migration: app/db/lakebase.py migrate_reports().

Write path:
- job_daily_report.py (06:30 cron) → insert_daily

Read paths:
- GET /api/daily-reports/today → get_for_date
- GET /api/daily-reports/recent → list_recent

Constraint: report_date UNIQUE. 같은 날 재실행 INSERT 충돌 (caller가 사전 get_for_date 확인).
"""
from __future__ import annotations

import json
import logging
from datetime import date as date_type, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row

from app.schemas.report import DailyReport, DailyReportCreate

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────
# Row → Pydantic
# ──────────────────────────────────────────────────────────────────────
def _row_to_daily(row: dict[str, Any]) -> DailyReport:
    return DailyReport(
        daily_id=row["daily_id"],
        report_date=row["report_date"],
        prev_daily_id=row.get("prev_daily_id"),
        kept_report_ids=row.get("kept_report_ids") or [],
        kept_count=row.get("kept_count", 0),
        kept_summary=row.get("kept_summary"),
        prev_daily_summary=row.get("prev_daily_summary"),
        market_context=row.get("market_context"),
        ratio_suggestion=row.get("ratio_suggestion") or {},
        reasoning=row.get("reasoning"),
        confidence=float(row["confidence"]) if row.get("confidence") is not None else None,
        created_at=row["created_at"],
    )


# ──────────────────────────────────────────────────────────────────────
# Write
# ──────────────────────────────────────────────────────────────────────
def insert_daily(conn: psycopg.Connection, payload: DailyReportCreate) -> UUID:
    """INSERT 1 daily_report. Returns daily_id.

    report_date UNIQUE — 같은 날 중복이면 UniqueViolation raise.
    Caller가 conn.commit() 책임.
    """
    daily_id = uuid4()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO daily_reports (
                daily_id, report_date, prev_daily_id,
                kept_report_ids, kept_count, kept_summary,
                prev_daily_summary, market_context,
                ratio_suggestion, reasoning, confidence
            ) VALUES (
                %s, %s, %s,
                %s, %s, %s,
                %s, %s,
                %s::jsonb, %s, %s
            )
            """,
            (
                daily_id,
                payload.report_date,
                payload.prev_daily_id,
                payload.kept_report_ids,  # psycopg3 list → uuid[]
                payload.kept_count,
                payload.kept_summary,
                payload.prev_daily_summary,
                payload.market_context,
                json.dumps(payload.ratio_suggestion),
                payload.reasoning,
                payload.confidence,
            ),
        )
    return daily_id


# ──────────────────────────────────────────────────────────────────────
# Read
# ──────────────────────────────────────────────────────────────────────
def get_for_date(conn: psycopg.Connection, target_date: date_type) -> DailyReport | None:
    """특정 날짜 daily_report 1건. None if missing."""
    try:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT * FROM daily_reports WHERE report_date = %s",
                (target_date,),
            )
            row = cur.fetchone()
        return _row_to_daily(row) if row else None
    except Exception as e:
        logger.warning("get_for_date failed (date=%s): %s", target_date, e)
        return None


def get_prev(conn: psycopg.Connection, target_date: date_type) -> DailyReport | None:
    """target_date 이전 가장 최근 daily_report.

    daily report 생성 시 prev_daily_summary 채우기용.
    """
    try:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT * FROM daily_reports
                 WHERE report_date < %s
                 ORDER BY report_date DESC
                 LIMIT 1
                """,
                (target_date,),
            )
            row = cur.fetchone()
        return _row_to_daily(row) if row else None
    except Exception as e:
        logger.warning("get_prev failed (date=%s): %s", target_date, e)
        return None


def list_recent(conn: psycopg.Connection, *, limit: int = 7) -> list[DailyReport]:
    """최근 N일 daily reports. report_date DESC."""
    try:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT * FROM daily_reports
                 ORDER BY report_date DESC
                 LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
        return [_row_to_daily(r) for r in rows]
    except Exception as e:
        logger.warning("list_recent failed: %s", e)
        return []
