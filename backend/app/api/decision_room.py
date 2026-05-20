"""Decision Room — multi-case queue + delta strip endpoints.

GET  /api/decision-room/last-seen  → 사용자 last_seen_at (delta 기준점)
POST /api/decision-room/touch      → last_seen_at = NOW() (사용자 "모두 확인")
GET  /api/decision-room/queue      → needs_you + monitoring case grouping
GET  /api/decision-room/delta      → last_seen 이후 case 변화 events

graceful: Lakebase 미연결 시 빈 list / null / 0 반환.
"""
from __future__ import annotations

import logging
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
