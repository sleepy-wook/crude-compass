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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/decision-room", tags=["decision-room"])


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
