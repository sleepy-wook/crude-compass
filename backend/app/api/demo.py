"""Demo-only endpoints — `/api/demo/inject_signal`.

데모 시연 중 평가위원 앞에서 Mission 카드를 강제 trigger.
- settings.demo_mode True일 때만 main.py에서 conditional mount.
- production deploy 시 DEMO_MODE=false → 자동 404.

흐름:
1. POST {scenario, ...overrides} → preset payload 생성
2. Mission(source='demo_inject') 생성 + store.create
3. bus.publish('mission.proposed') → slack_bus_subscriber가 Slack 카드 push + WS broadcast
4. 응답: mission + slack_status

NOTE: LLM Pattern Score 엔진(/api/missions/recommend)과 별도 endpoint. source='demo_inject' 로 구분.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.schemas.mission import (
    Mission,
    MissionStatus,
    MissionType,
    MissionUrgency,
)
from app.services.demo_scenarios import (
    CustomScenarioIncomplete,
    VALID_SCENARIOS,
    build_preset,
)
from app.store import get_bus, get_store

router = APIRouter(prefix="/api/demo", tags=["demo"])


class InjectSignalRequest(BaseModel):
    """Demo inject endpoint request body.

    scenario는 필수. 나머지는 preset override (None이 아닌 값만 적용).
    """

    scenario: str = Field(..., description=f"Preset name. Valid: {VALID_SCENARIOS}")
    mission_type: MissionType | None = None
    pattern_score: float | None = Field(None, ge=0, le=100)
    urgency: MissionUrgency | None = None
    goal_text: str | None = None
    reasoning: str | None = None
    target_pct: int | None = Field(None, ge=0, le=100)
    duration_days: int | None = Field(None, ge=1, le=365)
    simulation_roi: dict[str, float] | None = None


@router.post("/inject_signal")
async def inject_signal(body: InjectSignalRequest) -> dict[str, Any]:
    """Demo 시연 trigger — Mission 생성 + Slack DM 카드 발송."""
    if body.scenario not in VALID_SCENARIOS:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_SCENARIO",
                "valid": VALID_SCENARIOS,
            },
        )

    try:
        preset = build_preset(
            body.scenario,
            overrides=body.model_dump(exclude={"scenario"}, exclude_none=True),
        )
    except CustomScenarioIncomplete as e:
        raise HTTPException(
            status_code=422,
            detail={"code": "CUSTOM_REQUIRES_FIELDS", "message": str(e)},
        )

    mission = Mission(
        mission_id=uuid4(),
        status=MissionStatus.PROPOSED,
        created_at=datetime.now(timezone.utc),
        version=1,
        source="demo_inject",
        **preset,
    )

    store = get_store()
    bus = get_bus()
    await store.create(mission)
    await bus.publish(
        {"type": "mission.proposed", "mission": mission.model_dump(mode="json")}
    )

    settings = get_settings()
    return {
        "mission": mission.model_dump(mode="json"),
        "slack_status": "live" if settings.slack_enabled else "dry-run",
        "channel": settings.slack_default_channel or None,
        "source": "demo_inject",
    }
