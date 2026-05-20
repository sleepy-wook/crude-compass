"""Pulse REST — Live AI Pulse + 24h stats.

GET /api/pulse/recent  → 최근 N개 agent_activity events (cross-mission)
GET /api/pulse/stats   → 24h 누적 by_actor / by_action 통계
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pulse", tags=["pulse"])


@router.get("/recent")
async def get_recent(limit: int = Query(default=50, ge=1, le=200)) -> dict[str, Any]:
    """Cross-mission 최근 events."""
    try:
        from app.db.lakebase import acquire
        from app.db.repositories import agent_activity

        with acquire() as conn:
            events = agent_activity.list_recent_all(conn, limit=limit)
        return {"events": events, "count": len(events)}
    except Exception as e:
        logger.warning("pulse recent failed: %s", e)
        return {"events": [], "count": 0}


@router.get("/stats")
async def get_stats() -> dict[str, Any]:
    """24h 누적 통계 — Daily Loop / Pulse Strip 상단 bar."""
    try:
        from app.db.lakebase import acquire

        since = datetime.now(timezone.utc) - timedelta(hours=24)

        with acquire() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT actor, COUNT(*) as c FROM agent_activity_events
                 WHERE occurred_at > %s GROUP BY actor
                """,
                (since,),
            )
            by_actor = {r[0]: r[1] for r in cur.fetchall()}

            cur.execute(
                """
                SELECT action, COUNT(*) as c FROM agent_activity_events
                 WHERE occurred_at > %s GROUP BY action
                """,
                (since,),
            )
            by_action = {r[0]: r[1] for r in cur.fetchall()}

            cur.execute(
                """
                SELECT COUNT(DISTINCT mission_id) FROM agent_activity_events
                 WHERE occurred_at > %s AND mission_id IS NOT NULL
                """,
                (since,),
            )
            active_cases = cur.fetchone()[0] or 0

        total = sum(by_actor.values())
        return {
            "total_24h": total,
            "by_actor": by_actor,
            "by_action": by_action,
            "active_cases": active_cases,
        }
    except Exception as e:
        logger.warning("pulse stats failed: %s", e)
        return {"total_24h": 0, "by_actor": {}, "by_action": {}, "active_cases": 0}
