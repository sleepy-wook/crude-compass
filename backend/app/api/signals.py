"""Signal Lifecycle API — bronze.news_articles + silver.signal_events_decayed + gold.signal_contribution_30d.

GET /api/signals/{signal_id}/lifecycle  → 4-stage forensic view

Stage 1: detected — bronze.news_articles row
Stage 2: scored — LLM scoring (importance/direction/horizon/confidence)
Stage 3: decay — silver.signal_events_decayed (시간 감쇠 곡선)
Stage 4: contribution — gold.signal_contribution_30d (30일 누적)

SQL-injection 방어:
1. path param 정규식 validation (영숫자/하이픈/언더스코어만 허용) → 400
2. Databricks SDK parameterized query (:signal_id) — f-string interpolation X
"""
from __future__ import annotations

import logging
import re
from typing import Any

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/signals", tags=["signals"])

# article_id 형식: 영숫자 + 하이픈 + 언더스코어만 허용 (GDELT id / UUID 모두 만족)
_SIGNAL_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


@router.get("/{signal_id}/lifecycle")
async def get_lifecycle(signal_id: str) -> dict[str, Any]:
    """한 signal (news_article)의 4-stage lifecycle."""
    if not _SIGNAL_ID_RE.match(signal_id):
        raise HTTPException(status_code=400, detail={"code": "BAD_SIGNAL_ID"})

    try:
        from databricks.sdk import WorkspaceClient
        from databricks.sdk.service.sql import StatementParameterListItem

        from app.core.config import get_settings

        settings = get_settings()
        w = WorkspaceClient()
        warehouse_id = settings.databricks_warehouse_id

        def _query(sql: str) -> list[dict[str, Any]]:
            result = w.statement_execution.execute_statement(
                warehouse_id=warehouse_id,
                statement=sql,
                parameters=[StatementParameterListItem(name="signal_id", value=signal_id)],
                wait_timeout="30s",
            )
            if not result.result or not result.result.data_array:
                return []
            cols = [c.name for c in (result.manifest.schema.columns or [])]
            return [dict(zip(cols, row)) for row in result.result.data_array]

        # Stage 1+2 — detected + scored (단일 query)
        detected = _query(
            """
            SELECT article_id, title, source, published_at, importance,
                   direction, category, horizon, confidence
              FROM crude_compass.bronze.news_articles
             WHERE article_id = :signal_id
             LIMIT 1
            """
        )
        if not detected:
            raise HTTPException(status_code=404, detail={"code": "NOT_FOUND"})

        # Stage 3 — decay curve
        decay = _query(
            """
            SELECT as_of_date, weight, lambda, days_since_event
              FROM crude_compass.silver.signal_events_decayed
             WHERE article_id = :signal_id
             ORDER BY as_of_date ASC
            """
        )

        # Stage 4 — contribution (30일 누적 + referenced cases)
        contribution = _query(
            """
            SELECT total_contribution, peak_contribution, peak_date,
                   referenced_case_ids
              FROM crude_compass.gold.signal_contribution_30d
             WHERE article_id = :signal_id
             LIMIT 1
            """
        )

        return {
            "signal_id": signal_id,
            "stages": {
                "detected": detected[0],
                "scored": {
                    "importance": detected[0].get("importance"),
                    "direction": detected[0].get("direction"),
                    "horizon": detected[0].get("horizon"),
                    "confidence": detected[0].get("confidence"),
                },
                "decay": decay,
                "contribution": contribution[0] if contribution else None,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("signal lifecycle failed for %s: %s", signal_id, e)
        # graceful: 빈 stages (Lakebase/Warehouse 미연결 등)
        return {
            "signal_id": signal_id,
            "stages": {"detected": None, "scored": None, "decay": [], "contribution": None},
        }
