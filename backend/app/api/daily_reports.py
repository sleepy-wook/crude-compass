"""Daily Reports REST API — 06:30 KST cron 종합 보고서 (2026-05-21).

Endpoints:
  GET /api/daily-reports/today        → 오늘 daily_report (KST 기준)
  GET /api/daily-reports/recent       → 최근 N개 (default 7)
  GET /api/daily-reports/{date}       → 특정 날짜 (ISO YYYY-MM-DD)

Lakebase 미연결 시 graceful empty.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Path, Query

from app.db.lakebase import acquire
from app.db.repositories import daily_reports as daily_repo
from app.schemas.report import DailyReport

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/daily-reports", tags=["daily_reports"])


def _today_kst() -> date:
    """KST 기준 오늘 날짜."""
    return (datetime.now(timezone.utc) + timedelta(hours=9)).date()


def _serialize(d: DailyReport) -> dict[str, Any]:
    return {
        "daily_id": str(d.daily_id),
        "report_date": d.report_date.isoformat() if d.report_date else None,
        "prev_daily_id": str(d.prev_daily_id) if d.prev_daily_id else None,
        "kept_report_ids": [str(r) for r in d.kept_report_ids],
        "kept_count": d.kept_count,
        "kept_summary": d.kept_summary,
        "prev_daily_summary": d.prev_daily_summary,
        "market_context": d.market_context,
        "ratio_suggestion": d.ratio_suggestion,
        "reasoning": d.reasoning,
        "confidence": d.confidence,
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }


@router.get("/today")
async def get_today() -> dict[str, Any]:
    """오늘 (KST) daily_report. 없으면 `{"daily_report": null}` graceful."""
    try:
        with acquire() as conn:
            d = daily_repo.get_for_date(conn, _today_kst())
        return {"daily_report": _serialize(d) if d else None}
    except Exception as e:
        logger.warning("get_today daily_report failed: %s", e)
        return {"daily_report": None}


@router.get("/recent")
async def get_recent(limit: int = Query(default=7, ge=1, le=30)) -> dict[str, Any]:
    """최근 N일 daily_reports (DESC)."""
    try:
        with acquire() as conn:
            items = daily_repo.list_recent(conn, limit=limit)
        return {"count": len(items), "items": [_serialize(d) for d in items]}
    except Exception as e:
        logger.warning("get_recent daily_reports failed: %s", e)
        return {"count": 0, "items": []}


@router.get("/{report_date}")
async def get_by_date(report_date: date = Path(...)) -> dict[str, Any]:
    """특정 날짜 daily_report. 404 if missing."""
    try:
        with acquire() as conn:
            d = daily_repo.get_for_date(conn, report_date)
        if d is None:
            raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "date": report_date.isoformat()})
        return {"daily_report": _serialize(d)}
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("get_by_date daily_report failed (%s): %s", report_date, e)
        raise HTTPException(status_code=500, detail={"code": "FETCH_FAILED", "message": str(e)})
