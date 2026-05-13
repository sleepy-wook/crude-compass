"""Slack Events + Interactive endpoints (Bolt AsyncApp + FastAPI adapter).

핵심:
- POST /api/slack/events   — Events API (URL verification + message events)
- POST /api/slack/interactive — Block Kit button click payload

Action 분기:
- mission_confirm  → missions.confirm
- mission_reject   → missions.reject
- mission_pivot    → modal open (D-3 deferred → 우선 ephemeral '곧 Apps에서')
- mission_modify   → ephemeral '곧 Apps에서' (D-3 deferred)
- mission_open_apps → url 버튼 (ack만)

Idempotency:
- action_ts + action_id + mission_id + version 조합 60s TTL in-memory dict로 dedupe.
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
from app.schemas.mission import Mission, MissionStatus, MissionType, PivotEntry
from app.services.slack_notify import get_notifier
from app.store import get_bus, get_store

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
def _parse_value(raw: str) -> tuple[UUID, int] | None:
    try:
        data = json.loads(raw)
        return UUID(data["mid"]), int(data["v"])
    except Exception as e:
        logger.error("slack action value parse failed: %s — raw=%s", e, raw)
        return None


def _slack_actor(body: dict[str, Any]) -> str:
    """Slack body에서 user identifier 추출."""
    user = body.get("user") or {}
    uid = user.get("id") or "?"
    name = user.get("username") or user.get("name") or "slack_user"
    return f"slack:{name}@{uid}"


async def _do_mission_action(
    action_id: str,
    body: dict[str, Any],
    mission_id: UUID,
    version: int,
    actor: str,
) -> tuple[Mission | None, str | None]:
    """missions.* 핸들러 직접 호출. Returns (new_mission, ephemeral_message)."""
    from datetime import datetime, timezone
    store = get_store()
    bus = get_bus()

    if action_id == "mission_confirm":
        def _do(m: Mission) -> Mission:
            m.status = MissionStatus.ACTIVE
            m.confirmed_at = datetime.now(timezone.utc)
            m.confirmed_by = actor
            m.confirmed_via = "slack"
            return m

        new = await store.update(mission_id, version, _do)
        if new is None:
            existing = await store.get(mission_id)
            if existing is None:
                return None, "이미 삭제된 미션입니다."
            return None, (
                f"이미 다른 채널에서 처리되었습니다 (status={existing.status.value}). "
                f"Apps에서 최신 상태 확인하세요."
            )
        await bus.publish({"type": "mission.confirmed", "mission": new.model_dump(mode="json")})
        return new, None

    if action_id == "mission_reject":
        def _do(m: Mission) -> Mission:
            m.status = MissionStatus.ABORTED
            m.completed_at = datetime.now(timezone.utc)
            m.confirmed_by = actor
            m.confirmed_via = "slack"
            return m

        new = await store.update(mission_id, version, _do)
        if new is None:
            existing = await store.get(mission_id)
            if existing is None:
                return None, "이미 삭제된 미션입니다."
            return None, f"이미 처리됨 (status={existing.status.value})"
        await bus.publish({"type": "mission.updated", "mission": new.model_dump(mode="json")})
        return new, None

    if action_id == "mission_pivot":
        # Sprint 4: Pivot은 Slack에서 HEDGE↔OPP 토글로 처리 (modal D-3 deferred).
        current = await store.get(mission_id)
        if current is None:
            return None, "미션을 찾을 수 없습니다."
        to_type = (
            MissionType.OPPORTUNITY
            if current.mission_type == MissionType.HEDGE
            else MissionType.HEDGE
        )

        def _do(m: Mission) -> Mission:
            entry = PivotEntry(
                from_type=m.mission_type,
                to_type=to_type,
                occurred_at=datetime.now(timezone.utc),
                reason=f"Slack 단일클릭 토글 (by {actor})",
                pattern_score_at=m.pattern_score,
            )
            m.pivot_history = [*m.pivot_history, entry]
            m.mission_type = to_type
            m.status = MissionStatus.PIVOTED
            m.confirmed_via = "slack"
            return m

        new = await store.update(mission_id, version, _do)
        if new is None:
            existing = await store.get(mission_id)
            if existing is None:
                return None, "이미 삭제된 미션입니다."
            return None, f"이미 처리됨 (status={existing.status.value})"
        event = {"type": "mission.pivoted", "mission": new.model_dump(mode="json")}
        if new.pivot_history:
            event["pivot"] = new.pivot_history[-1].model_dump(mode="json")
        await bus.publish(event)
        return new, None

    if action_id == "mission_modify":
        return None, "Modify는 Apps에서 가능 — 'Open in Apps' 버튼을 눌러주세요."

    if action_id == "mission_open_apps":
        # url button — Slack이 자동 redirect. ack 만.
        return None, None

    return None, f"알 수 없는 action: {action_id}"


def _register_handlers(app: AsyncApp) -> None:
    """모든 mission_* action_id 를 한 핸들러로 묶음."""

    @app.action({"action_id": "mission_confirm"})
    @app.action({"action_id": "mission_reject"})
    @app.action({"action_id": "mission_pivot"})
    @app.action({"action_id": "mission_modify"})
    @app.action({"action_id": "mission_open_apps"})
    async def handle_mission_action(ack, body, client, action, respond):
        await ack()
        action_id = action.get("action_id")
        value_raw = action.get("value") or "{}"
        parsed = _parse_value(value_raw)
        if parsed is None:
            await respond(text="잘못된 버튼 데이터 — 카드를 새로 받아주세요.", response_type="ephemeral")
            return
        mid, version = parsed

        # Idempotency: Slack retry 시 동일 action_ts 보존. 원본 그대로 사용 (secondary 정밀도 손실 회피).
        action_ts = str(action.get("action_ts") or "0")
        ikey = _idem_key(action_ts, action_id, str(mid), version)
        if _idem_check(ikey):
            logger.info("slack idem dedupe — key=%s", ikey)
            return

        actor = _slack_actor(body)
        try:
            new_mission, err = await _do_mission_action(action_id, body, mid, version, actor)
        except Exception as e:
            logger.exception("slack action error: %s", e)
            await respond(text=f"처리 실패: {e}", response_type="ephemeral")
            return

        if err:
            await respond(text=f":warning: {err}", response_type="ephemeral")
            return
        # 성공 — subscriber 가 카드 update 처리. 별도 응답 X.


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
