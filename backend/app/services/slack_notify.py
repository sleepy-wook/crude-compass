"""Slack notification service — chat.postMessage + chat.update wrapper.

핵심:
- settings.slack_enabled False → dry-run 모드 (log only, 실제 API 호출 X)
- in-process dict로 mission_id → message_ts 매핑 (schema 변경 없이 chat.update 지원)
- 429/5xx retry 3회 (100ms → 500ms → 2s exp backoff)
- Singleton via lru_cache

NOTE: 단일 프로세스 데모 가정. multi-instance production 시 Redis 또는 DB로 ts 보관.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any
from uuid import UUID

from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from app.core.config import get_settings
from app.schemas.mission import Mission
from app.services.slack_blocks import ActionState, build_mission_card, build_text_fallback

logger = logging.getLogger(__name__)


class SlackNotifier:
    """Slack chat API client + in-process ts map.

    dry-run 모드: settings.slack_enabled False → 실제 API 호출 안 함. ts='dryrun-{uuid}' 반환.
    """

    def __init__(self):
        s = get_settings()
        self.enabled = s.slack_enabled
        self.default_channel = s.slack_default_channel
        self._client: AsyncWebClient | None = (
            AsyncWebClient(token=s.slack_bot_token) if self.enabled else None
        )
        # mission_id (UUID) → message_ts (str). chat.update 시 lookup.
        self._ts_map: dict[UUID, str] = {}
        # 채널도 카드별로 보관 (DM 채널은 mission_id마다 다를 수 있음).
        self._channel_map: dict[UUID, str] = {}

    # ────────────────────────────────────────────────────────────────────
    # ts map (subscriber + interactive handler에서 양쪽 사용)
    # ────────────────────────────────────────────────────────────────────
    def get_ts(self, mission_id: UUID) -> tuple[str, str] | None:
        """Returns (channel, ts) tuple or None."""
        ts = self._ts_map.get(mission_id)
        ch = self._channel_map.get(mission_id)
        if ts and ch:
            return ch, ts
        return None

    def set_ts(self, mission_id: UUID, channel: str, ts: str) -> None:
        self._ts_map[mission_id] = ts
        self._channel_map[mission_id] = channel

    # ────────────────────────────────────────────────────────────────────
    # Post + update with retry
    # ────────────────────────────────────────────────────────────────────
    async def _call_with_retry(self, method_name: str, **kwargs) -> dict[str, Any]:
        """Slack API 호출 + 429/5xx 3회 재시도 (exp backoff)."""
        if self._client is None:
            raise RuntimeError("SlackNotifier dry-run mode — _call_with_retry should not be reached")

        delays = [0.1, 0.5, 2.0]
        last_exc: Exception | None = None
        for i, delay in enumerate([0.0, *delays]):
            if delay > 0:
                await asyncio.sleep(delay)
            try:
                method = getattr(self._client, method_name)
                resp = await method(**kwargs)
                # AsyncSlackResponse.data
                return resp.data  # type: ignore[return-value]
            except SlackApiError as e:
                # 429 retry-after 존중 + 5xx 재시도. 4xx 즉시 raise.
                code = e.response.status_code if e.response else None
                if code == 429 or (code and 500 <= code < 600):
                    last_exc = e
                    logger.warning(
                        "slack.%s retry %d/3 — code=%s body=%s",
                        method_name, i + 1, code, e.response.data if e.response else "?",
                    )
                    continue
                raise
            except Exception as e:
                # 네트워크 일시 오류도 재시도
                last_exc = e
                logger.warning("slack.%s retry %d/3 — exc=%s", method_name, i + 1, e)
                continue
        assert last_exc is not None
        raise last_exc

    async def post_mission_card(
        self,
        mission: Mission,
        channel: str | None = None,
    ) -> str:
        """Mission 카드 신규 push. Returns message ts.

        dry-run 모드: 가짜 ts 반환 + log only.
        """
        channel = channel or self.default_channel
        if not self.enabled:
            fake_ts = f"dryrun-{uuid.uuid4()}"
            logger.info(
                "slack[dry-run] post_mission_card mission=%s urgency=%s → ts=%s",
                mission.mission_id, mission.urgency.value, fake_ts,
            )
            self.set_ts(mission.mission_id, channel or "dry-run-channel", fake_ts)
            return fake_ts

        blocks = build_mission_card(mission, action_state="proposed")
        text = build_text_fallback(mission, "proposed")
        resp = await self._call_with_retry(
            "chat_postMessage", channel=channel, blocks=blocks, text=text
        )
        ts = str(resp["ts"])
        self.set_ts(mission.mission_id, channel, ts)
        logger.info(
            "slack post_mission_card mission=%s channel=%s ts=%s",
            mission.mission_id, channel, ts,
        )
        return ts

    async def update_mission_card(
        self,
        mission: Mission,
        action_state: ActionState,
    ) -> None:
        """기존 message 를 새 상태로 갱신. ts map 에 없으면 silent skip + WARN."""
        loc = self.get_ts(mission.mission_id)
        if loc is None:
            logger.warning(
                "slack update_mission_card — no ts for mission=%s (skip)",
                mission.mission_id,
            )
            return
        channel, ts = loc

        if not self.enabled:
            logger.info(
                "slack[dry-run] update_mission_card mission=%s state=%s ts=%s",
                mission.mission_id, action_state, ts,
            )
            return

        blocks = build_mission_card(mission, action_state=action_state)
        text = build_text_fallback(mission, action_state)
        await self._call_with_retry(
            "chat_update", channel=channel, ts=ts, blocks=blocks, text=text
        )
        logger.info(
            "slack update_mission_card mission=%s state=%s ts=%s",
            mission.mission_id, action_state, ts,
        )

    async def post_report_card(self, report, report_id: str | None = None, channel: str | None = None) -> str:
        """트리거 보고서 발행 알림 카드 push (reports model, 2026-05-21).

        report: Report 객체. report_id: 버튼 value용 (admin은 insert 후 rid 전달).
        dry-run 모드면 log only + 가짜 ts.
        """
        from app.services.slack_blocks import build_report_card, build_report_text_fallback

        channel = channel or self.default_channel
        if not self.enabled:
            fake_ts = f"dryrun-{uuid.uuid4()}"
            logger.info("slack[dry-run] post_report_card report=%s headline=%s",
                        report_id or getattr(report, "report_id", "?"), report.headline)
            return fake_ts

        blocks = build_report_card(report, report_id=report_id)
        text = build_report_text_fallback(report)
        resp = await self._call_with_retry(
            "chat_postMessage", channel=channel, blocks=blocks, text=text
        )
        ts = str(resp["ts"])
        logger.info("slack post_report_card report=%s channel=%s ts=%s",
                    getattr(report, "report_id", "?"), channel, ts)
        return ts

    async def post_ephemeral(self, channel: str, user: str, text: str) -> None:
        """ephemeral 메시지 (interactive 핸들러에서 409 conflict 등 즉시 피드백)."""
        if not self.enabled:
            logger.info("slack[dry-run] ephemeral channel=%s user=%s text=%s", channel, user, text)
            return
        try:
            await self._call_with_retry(
                "chat_postEphemeral", channel=channel, user=user, text=text
            )
        except Exception as e:
            logger.error("slack ephemeral failed: %s", e)


# ────────────────────────────────────────────────────────────────────────
# Singleton accessor
# ────────────────────────────────────────────────────────────────────────
_notifier: SlackNotifier | None = None


def get_notifier() -> SlackNotifier:
    global _notifier
    if _notifier is None:
        _notifier = SlackNotifier()
    return _notifier


def reset_notifier_for_testing() -> None:
    global _notifier
    _notifier = None
