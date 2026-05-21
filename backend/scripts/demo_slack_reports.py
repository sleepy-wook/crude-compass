"""데모용 — 트리거 보고서 2건을 Slack으로 발송 (reports model Slack 알림 검증).

LLM 호출 없이 사전 작성된 Report 2건을 SlackNotifier.post_report_card로 push.
settings.slack_enabled (backend/.env의 SLACK_* 3종) True여야 실제 발송.

실행:
  cd backend
  .venv/Scripts/python.exe scripts/demo_slack_reports.py
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.schemas.report import Recommendation, Report, ReportStatus, TriggerType
from app.services.slack_notify import get_notifier

NOW = datetime.now(timezone.utc)

DEMO_REPORTS = [
    Report(
        report_id=uuid4(),
        trigger_type=TriggerType.PRICE_SPIKE,
        status=ReportStatus.PENDING,
        headline="두바이유 24시간 +2.8% 급등 — 호르무즈 해협 긴장 고조",
        summary=(
            "지난 24시간 두바이유가 $104.2 → $107.1로 +2.8% 급등했습니다. "
            "호르무즈 해협 인근 군사 활동 보도가 누적되며 공급 차질 우려가 가격에 반영되는 중입니다. "
            "단기 변동성 확대 국면으로, 스팟 비중을 줄이고 장기계약 비중을 높이는 방어적 조정을 권고합니다."
        ),
        recommendation=Recommendation.HEDGE,
        created_at=NOW,
    ),
    Report(
        report_id=uuid4(),
        trigger_type=TriggerType.GDELT_SIGNAL,
        status=ReportStatus.PENDING,
        headline="OPEC+ 추가 감산 합의 불발 — 공급 과잉 우려",
        summary=(
            "OPEC+ 회의에서 추가 감산 합의가 불발되며 공급 과잉 시그널이 강해지고 있습니다. "
            "사우디 생산량이 5개월 연속 증가 추세인 점과 맞물려 단기 가격 하방 압력이 예상됩니다. "
            "지금 시점의 스팟 매입을 연기하고 가격 추가 하락을 기다리는 전략을 권고합니다."
        ),
        recommendation=Recommendation.DEFER_SPOT,
        created_at=NOW,
    ),
]


async def main() -> None:
    notifier = get_notifier()
    print(f"slack_enabled = {notifier.enabled} (False면 dry-run, 실제 발송 안 됨)")
    for r in DEMO_REPORTS:
        ts = await notifier.post_report_card(r)
        print(f"  발송: {r.headline[:40]}... → ts={ts}")
    print("완료")


if __name__ == "__main__":
    asyncio.run(main())
