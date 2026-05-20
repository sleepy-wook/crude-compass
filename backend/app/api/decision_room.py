"""Decision Room — multi-case queue + delta strip endpoints.

GET  /api/decision-room/last-seen  → 사용자 last_seen_at (delta 기준점)
POST /api/decision-room/touch      → last_seen_at = NOW() (사용자 "모두 확인")
GET  /api/decision-room/queue      → needs_you + monitoring case grouping
GET  /api/decision-room/delta      → last_seen 이후 case 변화 events

graceful: Lakebase 미연결 시 빈 list / null / 0 반환.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Query

from app.store import get_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/decision-room", tags=["decision-room"])

# 우선순위 sort keys
_URGENCY_ORDER = {"urgent": 0, "default": 1, "optional": 2}
_NEEDS_YOU_STATUS_ORDER = {"proposed": 0, "at_risk": 1}
_MONITORING_STATUS_ORDER = {"on_track": 0, "active": 1, "paused": 2}
_NEEDS_YOU_STATUSES = {"proposed", "at_risk"}
_MONITORING_STATUSES = {"active", "on_track", "paused"}


@router.get("/last-seen")
async def get_last_seen_endpoint(user_key: str = Query(default="default")) -> dict[str, Any]:
    """사용자 last_seen_at — delta 기준점. Lakebase 미연결 시 null."""
    try:
        from app.db.lakebase import acquire
        from app.db.repositories import last_seen as _repo

        with acquire() as conn:
            ts = _repo.get_last_seen(conn, user_key)
        return {
            "last_seen_at": ts.isoformat() if ts else None,
            "user_key": user_key,
        }
    except Exception as e:
        logger.warning("last-seen GET failed: %s", e)
        return {"last_seen_at": None, "user_key": user_key}


@router.post("/touch")
async def touch_endpoint(user_key: str = Query(default="default")) -> dict[str, Any]:
    """last_seen_at = NOW(). 사용자가 '모두 확인' 누르면 호출."""
    try:
        from app.db.lakebase import acquire
        from app.db.repositories import last_seen as _repo

        with acquire() as conn:
            ts = _repo.touch_last_seen(conn, user_key)
        return {
            "last_seen_at": ts.isoformat() if ts else None,
            "user_key": user_key,
        }
    except Exception as e:
        logger.warning("touch POST failed: %s", e)
        return {"last_seen_at": None, "user_key": user_key}


@router.get("/queue")
async def get_queue() -> dict[str, Any]:
    """multi-case queue — needs_you (proposed/at_risk) + monitoring (active/on_track/paused).

    Status별 group + 우선순위 sort:
      needs_you: urgency DESC > status (proposed first) > created_at ASC
      monitoring: status (on_track first) > confirmed_at|created_at ASC
    """
    store = get_store()
    all_active = await store.get_active()

    needs_you = [m for m in all_active if m.status.value in _NEEDS_YOU_STATUSES]
    monitoring = [m for m in all_active if m.status.value in _MONITORING_STATUSES]

    needs_you.sort(key=lambda m: (
        _URGENCY_ORDER.get(m.urgency.value, 99),
        _NEEDS_YOU_STATUS_ORDER.get(m.status.value, 99),
        m.created_at,
    ))
    monitoring.sort(key=lambda m: (
        _MONITORING_STATUS_ORDER.get(m.status.value, 99),
        m.confirmed_at or m.created_at,
    ))

    counts = {
        "needs_you": len(needs_you),
        "monitoring": len(monitoring),
        "proposed": sum(1 for m in all_active if m.status.value == "proposed"),
        "at_risk": sum(1 for m in all_active if m.status.value == "at_risk"),
        "active": sum(1 for m in all_active if m.status.value == "active"),
        "on_track": sum(1 for m in all_active if m.status.value == "on_track"),
        "paused": sum(1 for m in all_active if m.status.value == "paused"),
    }

    return {
        "needs_you": [m.model_dump(mode="json") for m in needs_you],
        "monitoring": [m.model_dump(mode="json") for m in monitoring],
        "counts": counts,
    }


@router.get("/delta")
async def get_delta(user_key: str = Query(default="default")) -> dict[str, Any]:
    """last_seen 이후 case 변화 events — new_proposed / status_change / pivot.

    3 tables join: missions (new_proposed) + decisions (status_change) + pivot_history (pivot).
    Lakebase 미연결 시 graceful: since=None, events=[], counts=0.
    """
    empty = {
        "since": None,
        "events": [],
        "counts": {"new_proposed": 0, "status_change": 0, "pivot": 0, "total": 0},
    }
    try:
        from app.db.lakebase import acquire
        from app.db.repositories import last_seen as _ls_repo

        with acquire() as conn:
            since = _ls_repo.get_last_seen(conn, user_key)
            if since is None:
                # 기준점 없으면 최근 3일 fallback
                since = datetime.now(timezone.utc) - timedelta(days=3)

            events: list[dict[str, Any]] = []

            # 1) new_proposed — missions.created_at > since
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT mission_id, created_at, goal_text, mission_type
                      FROM missions
                     WHERE created_at > %s AND status NOT IN ('aborted', 'completed')
                     ORDER BY created_at DESC
                    """,
                    (since,),
                )
                for row in cur.fetchall():
                    events.append({
                        "type": "new_proposed",
                        "case_id": str(row[0]),
                        "occurred_at": row[1].isoformat(),
                        "summary": f"신규 {row[3]} 제안 — {(row[2] or '')[:40]}",
                    })

            # 2) status_change — decisions table
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT d.mission_id, d.action, d.occurred_at, m.goal_text
                      FROM decisions d
                      JOIN missions m ON m.mission_id = d.mission_id
                     WHERE d.occurred_at > %s
                     ORDER BY d.occurred_at DESC
                    """,
                    (since,),
                )
                for row in cur.fetchall():
                    events.append({
                        "type": "status_change",
                        "case_id": str(row[0]),
                        "from": None,
                        "to": row[1],
                        "occurred_at": row[2].isoformat(),
                        "summary": f"{row[1]} — {(row[3] or '')[:40]}",
                    })

            # 3) pivot — pivot_history table
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT mission_id, from_type, to_type, reason, occurred_at
                      FROM pivot_history
                     WHERE occurred_at > %s
                     ORDER BY occurred_at DESC
                    """,
                    (since,),
                )
                for row in cur.fetchall():
                    events.append({
                        "type": "pivot",
                        "case_id": str(row[0]),
                        "from_type": row[1],
                        "to_type": row[2],
                        "occurred_at": row[4].isoformat(),
                        "summary": f"{row[1]} → {row[2]} — {(row[3] or '')[:40]}",
                    })

        events.sort(key=lambda e: e["occurred_at"], reverse=True)
        counts = {
            "new_proposed": sum(1 for e in events if e["type"] == "new_proposed"),
            "status_change": sum(1 for e in events if e["type"] == "status_change"),
            "pivot": sum(1 for e in events if e["type"] == "pivot"),
            "total": len(events),
        }
        return {
            "since": since.isoformat(),
            "events": events,
            "counts": counts,
        }
    except Exception as e:
        logger.warning("delta GET failed: %s", e)
        return empty
