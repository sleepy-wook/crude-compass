"""Slack Events + Interactive endpoints (Bolt AsyncApp + FastAPI adapter).

핵심:
- POST /api/slack/events   — Events API (URL verification + message events)
- POST /api/slack/interactive — Block Kit button click payload

Action 분기 (reports model):
- report_keep      → reports.update_status(KEPT)
- report_drop      → reports.update_status(DROPPED)
- report_open_apps → url 버튼 (ack만)
- daily_open_apps  → url 버튼 (ack만)

Idempotency:
- action_ts + action_id + report_id 조합 60s TTL in-memory dict로 dedupe.
- Slack retry 시 동일 action_ts 보존 → 중복 처리 방지. 단일 worker 가정 (multi-replica 시 Redis 필요).

Dry-run:
- settings.slack_enabled False → 503 응답 (Bolt mount 자체는 skip).
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler
from slack_bolt.async_app import AsyncApp

from app.core.config import get_settings
from app.services.slack_notify import get_notifier

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/slack", tags=["slack"])


# ════════════════════════════════════════════════════════════════════════
# Lazy AsyncApp + handler (dry-run safe)
# ════════════════════════════════════════════════════════════════════════
_app: AsyncApp | None = None
_handler: AsyncSlackRequestHandler | None = None


def _build_app() -> AsyncApp | None:
    """settings.slack_enabled True 일 때만 AsyncApp 인스턴스 생성."""
    s = get_settings()
    if not s.slack_enabled:
        return None
    app = AsyncApp(
        token=s.slack_bot_token,
        signing_secret=s.slack_signing_secret,
        # FastAPI 호출이라 ack-first 권장 — process_before_response=True 로 동기적 처리도 가능하나
        # missions.* 핸들러가 await chain이라 process_before_response=False (Bolt default async) 유지
    )
    _register_handlers(app)
    return app


def get_app() -> AsyncApp | None:
    global _app
    if _app is None:
        _app = _build_app()
    return _app


def get_handler() -> AsyncSlackRequestHandler | None:
    global _handler
    if _handler is None:
        app = get_app()
        if app is None:
            return None
        _handler = AsyncSlackRequestHandler(app)
    return _handler


# ════════════════════════════════════════════════════════════════════════
# Idempotency cache — (action_ts, action_id, mission_id, version) 60s TTL
# Slack retry 시 동일 action_ts 보존 → 두 번째 요청 dedupe.
# ════════════════════════════════════════════════════════════════════════
_IDEM_TTL = 60.0
_idem_cache: dict[str, float] = {}


def _idem_key(action_ts: str, action_id: str, mid: str, version: int) -> str:
    return f"{action_ts}:{action_id}:{mid}:{version}"


def _idem_check(key: str) -> bool:
    """True if already seen (dedupe). Side-effect: TTL eviction + key insert."""
    now = time.time()
    # evict
    for k in list(_idem_cache.keys()):
        if _idem_cache[k] + _IDEM_TTL < now:
            _idem_cache.pop(k, None)
    if key in _idem_cache:
        return True
    _idem_cache[key] = now
    return False


# ════════════════════════════════════════════════════════════════════════
# Action handlers — Bolt @app.action(action_id)
# ════════════════════════════════════════════════════════════════════════
def _slack_actor(body: dict[str, Any]) -> str:
    """Slack body에서 user identifier 추출."""
    user = body.get("user") or {}
    uid = user.get("id") or "?"
    name = user.get("username") or user.get("name") or "slack_user"
    return f"slack:{name}@{uid}"


# ════════════════════════════════════════════════════════════════════════
# Reports model action handler (2026-05-21) — 활성화/기각 from Slack
# ════════════════════════════════════════════════════════════════════════
def _parse_report_value(raw: str) -> str | None:
    try:
        return json.loads(raw).get("rid") or None
    except Exception:
        return None


async def _do_report_action(action_id: str, rid_str: str, actor: str):
    """report_keep/report_drop → Lakebase status 업데이트. Returns (ok, label, report)."""
    from app.db.lakebase import acquire
    from app.db.repositories import reports as reports_repo
    from app.schemas.report import ReportStatus, StatusActor

    rid = UUID(rid_str)
    status = ReportStatus.KEPT if action_id == "report_keep" else ReportStatus.DROPPED
    label = "활성화됨" if action_id == "report_keep" else "기각됨"
    with acquire() as conn:
        ok = reports_repo.update_status(conn, rid, status, StatusActor.MANAGER)
        conn.commit()
        report = reports_repo.get_by_id(conn, rid) if ok else None
    logger.info("slack report action %s rid=%s by=%s ok=%s", action_id, rid_str, actor, ok)
    return ok, label, report


def _register_handlers(app: AsyncApp) -> None:
    """mission_* + report_* action_id 핸들러 등록."""

    @app.action({"action_id": "report_keep"})
    @app.action({"action_id": "report_drop"})
    @app.action({"action_id": "report_open_apps"})
    @app.action({"action_id": "daily_open_apps"})
    async def handle_report_action(ack, body, action, respond):
        await ack()
        action_id = action.get("action_id")
        if action_id in ("report_open_apps", "daily_open_apps"):
            return  # url 버튼 — Slack 자동 redirect
        rid = _parse_report_value(action.get("value") or "{}")
        if not rid:
            await respond(text="잘못된 버튼 데이터 — 카드를 새로 받아주세요.", response_type="ephemeral")
            return
        # Idempotency
        action_ts = str(action.get("action_ts") or "0")
        ikey = _idem_key(action_ts, action_id, rid, 0)
        if _idem_check(ikey):
            logger.info("slack report idem dedupe — key=%s", ikey)
            return
        actor = _slack_actor(body)
        try:
            ok, label, report = await _do_report_action(action_id, rid, actor)
        except Exception as e:
            logger.exception("slack report action error: %s", e)
            await respond(text=f"처리 실패: {e}", response_type="ephemeral")
            return
        if not ok:
            await respond(text="이미 처리되었거나 보고서를 찾을 수 없습니다.", response_type="ephemeral")
            return
        from app.services.slack_blocks import build_report_resolved_card
        if report is not None:
            await respond(blocks=build_report_resolved_card(report, label), replace_original=True)
        else:
            await respond(text=f"보고서 {label}", replace_original=True)


# ════════════════════════════════════════════════════════════════════════
# FastAPI endpoints
# ════════════════════════════════════════════════════════════════════════
@router.post("/events")
async def slack_events(req: Request) -> Response:
    handler = get_handler()
    if handler is None:
        raise HTTPException(
            status_code=503,
            detail={"code": "SLACK_DRY_RUN", "message": "Slack disabled (token/secret/channel missing)"},
        )
    return await handler.handle(req)


@router.post("/interactive")
async def slack_interactive(req: Request) -> Response:
    handler = get_handler()
    if handler is None:
        raise HTTPException(
            status_code=503,
            detail={"code": "SLACK_DRY_RUN", "message": "Slack disabled (token/secret/channel missing)"},
        )
    return await handler.handle(req)


@router.get("/health")
async def slack_health() -> dict:
    """Quick health probe — config 상태만 (실제 Slack 호출 X)."""
    s = get_settings()
    return {
        "enabled": s.slack_enabled,
        "has_bot_token": bool(s.slack_bot_token),
        "has_signing_secret": bool(s.slack_signing_secret),
        "default_channel": s.slack_default_channel or "(missing)",
    }
