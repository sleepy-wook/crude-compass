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

from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from app.core.config import get_settings

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

        blocks = build_report_card(report, report_id=report_id, apps_url=get_settings().apps_url)
        text = build_report_text_fallback(report)
        resp = await self._call_with_retry(
            "chat_postMessage", channel=channel, blocks=blocks, text=text
        )
        ts = str(resp["ts"])
        logger.info("slack post_report_card report=%s channel=%s ts=%s",
                    getattr(report, "report_id", "?"), channel, ts)
        return ts

    async def post_daily_card(self, daily, channel: str | None = None) -> str:
        """일일 종합 보고서 카드 push. daily 전용 채널 우선, 없으면 default."""
        from app.services.slack_blocks import build_daily_card, build_daily_text_fallback

        s = get_settings()
        channel = channel or s.slack_daily_channel or self.default_channel
        if not self.enabled:
            fake_ts = f"dryrun-{uuid.uuid4()}"
            logger.info("slack[dry-run] post_daily_card date=%s", getattr(daily, "report_date", "?"))
            return fake_ts

        blocks = build_daily_card(daily, apps_url=get_settings().apps_url)
        text = build_daily_text_fallback(daily)
        resp = await self._call_with_retry(
            "chat_postMessage", channel=channel, blocks=blocks, text=text
        )
        ts = str(resp["ts"])
        logger.info("slack post_daily_card date=%s channel=%s ts=%s",
                    getattr(daily, "report_date", "?"), channel, ts)
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
