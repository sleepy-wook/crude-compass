"""AI 자율 판단 — pending report stale 여부 / archive 매칭.

시나리오 (reports model 2026-05-21):
- 새 trigger 발생 시 pending reports 검토 → stale 판정 → ai_drop
- 새 trigger의 시그널이 archive에 있던 dropped/ai_dropped report와 동일 → revisits_id 채워서 새 report

Phase 9 전용 — Phase 2 시점에서는 인터페이스만 + 단순 fallback ('unrelated' 항상 반환).
"""
from __future__ import annotations

import logging
from enum import Enum

from app.schemas.report import Report
from app.services.trigger_detector import TriggerEvent

logger = logging.getLogger(__name__)


class Verdict(str, Enum):
    STALE = "stale"
    CONTINUATION = "continuation"
    UNRELATED = "unrelated"


def judge_pending(prev_report: Report, new_event: TriggerEvent) -> Verdict:
    """기존 pending report가 새 trigger 대비 stale인지 / continuation인지 판정.

    Phase 2 stub: 항상 UNRELATED 반환 (AI 자율 판단 비활성).
    Phase 9에서 Haiku 1-shot judge로 본격 발동.
    """
    return Verdict.UNRELATED


def find_archive_match(new_event: TriggerEvent, candidates: list[Report]) -> Report | None:
    """archive(dropped/ai_dropped) 중 새 trigger와 가장 유사한 1건.

    Phase 2 stub: 항상 None.
    Phase 9에서 LLM embedding / fingerprint 매칭으로 본격 발동.
    """
    return None
