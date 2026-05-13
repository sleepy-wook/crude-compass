"""EventBus → Slack notification subscriber.

write→broadcast 디커플 패턴:
- API hook 직접 호출 X. EventBus.publish 만 발생시킴.
- 이 subscriber 가 별도 task로 큐를 watch하며 Slack push/update 발사.
- Slack 다운/지연이 API 응답시간에 영향 X.

Lifecycle: app.main.lifespan 의 startup → asyncio.create_task. shutdown → cancel.
"""
from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from app.schemas.mission import Mission
from app.services.slack_notify import SlackNotifier
from app.store import EventBus, MissionStore

logger = logging.getLogger(__name__)


# event['type'] → SlackNotifier 메소드 매핑
_ACTION_STATE_MAP = {
    "mission.proposed": "proposed",
    "mission.confirmed": "confirmed",
    "mission.updated": None,   # generic update — modify or pause 등 별도 분기
    "mission.pivoted": "pivoted",
}


def _parse_mission(event: dict) -> Mission | None:
    """Event payload에서 Mission 복원."""
    raw = event.get("mission")
    if not raw:
        return None
    try:
        return Mission.model_validate(raw)
    except Exception as e:
        logger.error("slack subscriber — failed to parse mission: %s", e)
        return None


async def _handle_event(event: dict, notifier: SlackNotifier, store: MissionStore) -> None:
    et = event.get("type")
    mission = _parse_mission(event)
    if mission is None:
        return

    if et == "mission.proposed":
        # 신규 post → ts map 자동 저장
        try:
            await notifier.post_mission_card(mission)
        except Exception as e:
            logger.exception("slack subscriber post failed: %s", e)
        return

    # update 계열: action_state 결정 후 update_mission_card
    if et == "mission.confirmed":
        await notifier.update_mission_card(mission, action_state="confirmed")
        return
    if et == "mission.pivoted":
        await notifier.update_mission_card(mission, action_state="pivoted")
        return
    if et == "mission.updated":
        # status별 분기 — aborted / paused / proposed (modify) etc
        status = mission.status.value
        state: str
        if status == "aborted":
            state = "aborted"
        elif status == "paused":
            state = "paused"
        else:
            # modify 또는 기타 — 카드 자체 데이터 새로 그림 (proposed 상태로 다시)
            state = "proposed" if status == "proposed" else "confirmed"
        await notifier.update_mission_card(mission, action_state=state)  # type: ignore[arg-type]
        return

    # 미지의 type — 로그만
    logger.debug("slack subscriber — unknown event type: %s", et)


async def run_slack_subscriber(
    bus: EventBus, notifier: SlackNotifier, store: MissionStore
) -> None:
    """무한 루프 — bus.subscribe() 큐에서 event 받아 _handle_event 호출.

    Cancel 시 정리 후 종료.
    """
    queue = await bus.subscribe()
    logger.info("slack subscriber started (enabled=%s)", notifier.enabled)
    try:
        while True:
            event = await queue.get()
            try:
                await _handle_event(event, notifier, store)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.exception("slack subscriber handler error: %s", e)
    except asyncio.CancelledError:
        logger.info("slack subscriber cancelled")
        raise
    finally:
        await bus.unsubscribe(queue)
