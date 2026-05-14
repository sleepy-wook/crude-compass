"""Missions REST endpoints.

API contract: docs/api_contract.md §2.
- GET /api/missions/active
- GET /api/missions/{id}
- POST /api/missions/{id}/confirm
- POST /api/missions/{id}/reject
- POST /api/missions/{id}/pivot
- POST /api/missions/{id}/modify
- POST /api/missions/recommend  (LLM Mission Plan Agent)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.schemas.mission import (
    Mission,
    MissionPlanInput,
    MissionStatus,
    MissionType,
    MissionUrgency,
    PivotEntry,
)
from app.services.mission_plan import call_mission_plan_agent
from app.store import get_bus, get_store

router = APIRouter(prefix="/api/missions", tags=["missions"])


# ────────────────────────────────────────────────────────────────────────
# Request schemas
# ────────────────────────────────────────────────────────────────────────
class ConfirmRequest(BaseModel):
    version: int
    via: Literal["slack", "apps"] = "apps"


class RejectRequest(BaseModel):
    version: int
    via: Literal["slack", "apps"] = "apps"
    reason: str | None = None


class PivotRequest(BaseModel):
    version: int
    via: Literal["slack", "apps"] = "apps"
    pivot_action: Literal["pivot", "pause", "abort", "continue"]
    to_type: MissionType | None = None  # pivot_action='pivot' 시만
    reason: str


class ModifyRequest(BaseModel):
    version: int
    target_pct: int | None = None
    duration_days: int | None = None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _actor(request: Request) -> str:
    """Apps OAuth: X-Forwarded-User 헤더 (production). Local dev: anonymous."""
    return request.headers.get("X-Forwarded-User", "dev_user")


# ────────────────────────────────────────────────────────────────────────
# Read endpoints
# ────────────────────────────────────────────────────────────────────────
@router.get("/active")
async def list_active() -> dict:
    store = get_store()
    missions = await store.get_active()
    return {"missions": [m.model_dump(mode="json") for m in missions]}


@router.get("/all")
async def list_all() -> dict:
    """All missions (active + completed/aborted) — for history page."""
    store = get_store()
    missions = await store.all()
    return {"missions": [m.model_dump(mode="json") for m in missions]}


@router.get("/{mission_id}")
async def get_mission(mission_id: UUID) -> dict:
    store = get_store()
    m = await store.get(mission_id)
    if m is None:
        raise HTTPException(status_code=404, detail={"code": "MISSION_NOT_FOUND"})
    return m.model_dump(mode="json")


# ────────────────────────────────────────────────────────────────────────
# Confirm / Reject / Pivot / Modify (write — with optimistic concurrency)
# ────────────────────────────────────────────────────────────────────────
@router.post("/{mission_id}/confirm")
async def confirm(mission_id: UUID, body: ConfirmRequest, request: Request) -> dict:
    actor = _actor(request)
    store = get_store()
    bus = get_bus()

    def _do(m: Mission) -> Mission:
        m.status = MissionStatus.ACTIVE
        m.confirmed_at = _now()
        m.confirmed_by = actor
        m.confirmed_via = body.via
        return m

    new = await store.update(mission_id, body.version, _do)
    if new is None:
        existing = await store.get(mission_id)
        if existing is None:
            raise HTTPException(status_code=404, detail={"code": "MISSION_NOT_FOUND"})
        raise HTTPException(
            status_code=409,
            detail={"code": "MISSION_VERSION_CONFLICT", "current": existing.model_dump(mode="json")},
        )

    await bus.publish({"type": "mission.confirmed", "mission": new.model_dump(mode="json")})
    return new.model_dump(mode="json")


@router.post("/{mission_id}/reject")
async def reject(mission_id: UUID, body: RejectRequest, request: Request) -> dict:
    actor = _actor(request)
    store = get_store()
    bus = get_bus()

    def _do(m: Mission) -> Mission:
        m.status = MissionStatus.ABORTED
        m.completed_at = _now()
        m.confirmed_by = actor
        m.confirmed_via = body.via
        return m

    new = await store.update(mission_id, body.version, _do)
    if new is None:
        existing = await store.get(mission_id)
        if existing is None:
            raise HTTPException(status_code=404, detail={"code": "MISSION_NOT_FOUND"})
        raise HTTPException(
            status_code=409,
            detail={"code": "MISSION_VERSION_CONFLICT", "current": existing.model_dump(mode="json")},
        )

    await bus.publish({"type": "mission.updated", "mission": new.model_dump(mode="json")})
    return new.model_dump(mode="json")


@router.post("/{mission_id}/pivot")
async def pivot(mission_id: UUID, body: PivotRequest, request: Request) -> dict:
    actor = _actor(request)
    store = get_store()
    bus = get_bus()

    def _do(m: Mission) -> Mission:
        # pivot_history entry 추가
        if body.pivot_action == "pivot" and body.to_type:
            entry = PivotEntry(
                from_type=m.mission_type,
                to_type=body.to_type,
                occurred_at=_now(),
                reason=body.reason,
                pattern_score_at=m.pattern_score,
            )
            m.pivot_history = [*m.pivot_history, entry]
            m.mission_type = body.to_type
            m.status = MissionStatus.PIVOTED
        elif body.pivot_action == "pause":
            m.status = MissionStatus.PAUSED
        elif body.pivot_action == "abort":
            m.status = MissionStatus.ABORTED
            m.completed_at = _now()
        # 'continue' = no status change but record event
        return m

    new = await store.update(mission_id, body.version, _do)
    if new is None:
        existing = await store.get(mission_id)
        if existing is None:
            raise HTTPException(status_code=404, detail={"code": "MISSION_NOT_FOUND"})
        raise HTTPException(
            status_code=409,
            detail={"code": "MISSION_VERSION_CONFLICT", "current": existing.model_dump(mode="json")},
        )

    event = {"type": "mission.pivoted", "mission": new.model_dump(mode="json")}
    if new.pivot_history:
        event["pivot"] = new.pivot_history[-1].model_dump(mode="json")
    await bus.publish(event)
    return new.model_dump(mode="json")


@router.post("/{mission_id}/modify")
async def modify(mission_id: UUID, body: ModifyRequest) -> dict:
    store = get_store()
    bus = get_bus()

    def _do(m: Mission) -> Mission:
        if body.target_pct is not None:
            m.target_pct = body.target_pct
        if body.duration_days is not None:
            m.duration_days = body.duration_days
        return m

    new = await store.update(mission_id, body.version, _do)
    if new is None:
        existing = await store.get(mission_id)
        if existing is None:
            raise HTTPException(status_code=404, detail={"code": "MISSION_NOT_FOUND"})
        raise HTTPException(
            status_code=409,
            detail={"code": "MISSION_VERSION_CONFLICT", "current": existing.model_dump(mode="json")},
        )

    await bus.publish({"type": "mission.updated", "mission": new.model_dump(mode="json")})
    return new.model_dump(mode="json")


# ────────────────────────────────────────────────────────────────────────
# Mission Plan Agent — LLM recommend endpoint
# ────────────────────────────────────────────────────────────────────────
@router.post("/recommend")
async def recommend(payload: MissionPlanInput) -> dict:
    """LLM Mission Plan Agent — Pattern Score + signals → recommend mission.

    Sprint 4: 직접 call_mission_plan_agent (services/mission_plan.py)
    Sprint 5: Agent Bricks Custom Agent endpoint으로 swap (형욱님 manual 등록)
    """
    result = call_mission_plan_agent(payload)
    if result is None:
        raise HTTPException(status_code=500, detail={"code": "LLM_CALL_FAILED"})

    # action_type이 new_mission이면 store에 proposed로 저장 + broadcast
    if result.action_type == "new_mission":
        store = get_store()
        bus = get_bus()
        mission = Mission(
            mission_id=uuid4(),
            mission_type=result.mission_type,
            status=MissionStatus.PROPOSED,
            goal_text=result.goal_text,
            pattern_score=result.pattern_score,
            reasoning=result.reasoning,
            simulation_roi=result.simulation_roi,
            urgency=result.urgency,
            target_pct=result.target_pct,
            duration_days=result.duration_days,
            created_at=_now(),
            version=1,
        )
        await store.create(mission)
        await bus.publish({"type": "mission.proposed", "mission": mission.model_dump(mode="json")})
        return {"action": "new_mission", "mission": mission.model_dump(mode="json"),
                "confidence_score": result.confidence_score}

    return {"action": result.action_type, "output": result.model_dump(mode="json")}


# ────────────────────────────────────────────────────────────────────────
# Demo-friendly: no-body wrapper (자동 demo signals + active mission 추론)
# ────────────────────────────────────────────────────────────────────────
class RecommendNowRequest(BaseModel):
    """Discovery '지금 새 추천 생성' 버튼이 호출. 모두 optional override."""
    pattern_score: float | None = None
    bullish_score: float | None = None
    bearish_score: float | None = None
    use_demo_signals: bool = True  # False면 빈 signals → LLM 추론에 의존


# 데모 narrative anchor signals (시나리오 §14 Phase 4 핵심 시그널)
_DEMO_SIGNALS = [
    {
        "signal_id": "demo_hormuz_001",
        "source": "GDELT_hormuz",
        "direction": "bullish",
        "importance": 88,
        "category": "geopolitical",
        "title": "Iran 제재 추가 + UK Maritime alerts 호르무즈 통과 우려 (멘션 +280%)",
    },
    {
        "signal_id": "demo_eia_001",
        "source": "EIA_inventory",
        "direction": "bullish",
        "importance": 72,
        "category": "supply",
        "title": "EIA 주간 재고 -5.2M bbl surprise (예상 -1.5M)",
    },
    {
        "signal_id": "demo_opec_001",
        "source": "OPEC_momr",
        "direction": "bullish",
        "importance": 75,
        "category": "demand",
        "title": "OPEC MOMR 5월호 — 사우디 추가 감산 시그널 + 글로벌 수요 +1.8mb/d 상향",
    },
    {
        "signal_id": "demo_russia_001",
        "source": "GDELT_russia",
        "direction": "bullish",
        "importance": 68,
        "category": "geopolitical",
        "title": "Russia-Ukraine 휴전 협상 결렬 시그널",
    },
]


@router.post("/recommend_now")
async def recommend_now(body: RecommendNowRequest = RecommendNowRequest()) -> dict:
    """No-body wrapper for demo '지금 새 추천 생성' button.

    내부에서 (a) demo signals seed (b) active mission (있으면) (c) Pattern Score override
    → MissionPlanInput 구성 → LLM 호출 → 결과 반환.

    LLM cold start ~5-10s 예상. frontend는 mutation pending spinner.
    """
    from datetime import datetime
    from app.schemas.mission import SignalContext

    # default values for demo (Phase 4 narrative와 일치 — Pattern Score 82 = HEDGE zone)
    pattern_score = body.pattern_score if body.pattern_score is not None else 82.0
    bullish_score = body.bullish_score if body.bullish_score is not None else 78.0
    bearish_score = body.bearish_score if body.bearish_score is not None else 22.0

    # active mission 있으면 Pivot 검토 candidate
    store = get_store()
    actives = await store.get_active()
    active_mission = actives[0] if actives else None

    # top_signals — demo 모드 시 hardcoded narrative anchor
    top_signals = []
    if body.use_demo_signals:
        now = datetime.now(timezone.utc)
        top_signals = [
            SignalContext(
                signal_id=s["signal_id"],
                published_at=now,
                source=s["source"],
                direction=s["direction"],
                importance=s["importance"],
                category=s["category"],
                title=s["title"],
            )
            for s in _DEMO_SIGNALS
        ]

    payload = MissionPlanInput(
        pattern_score=pattern_score,
        bullish_score=bullish_score,
        bearish_score=bearish_score,
        cross_val_bonus=15.0 if body.use_demo_signals else 0.0,
        signal_count_90d=len(top_signals),
        top_signals=top_signals,
        active_mission=active_mission,
    )

    # 기존 recommend logic 재사용
    result = call_mission_plan_agent(payload)
    if result is None:
        raise HTTPException(status_code=500, detail={"code": "LLM_CALL_FAILED"})

    if result.action_type == "new_mission":
        bus = get_bus()
        mission = Mission(
            mission_id=uuid4(),
            mission_type=result.mission_type,
            status=MissionStatus.PROPOSED,
            goal_text=result.goal_text,
            pattern_score=result.pattern_score,
            reasoning=result.reasoning,
            simulation_roi=result.simulation_roi,
            urgency=result.urgency,
            target_pct=result.target_pct,
            duration_days=result.duration_days,
            created_at=_now(),
            version=1,
            source="agent",  # provenance: LLM-generated (vs demo_inject)
        )
        await store.create(mission)
        await bus.publish({"type": "mission.proposed", "mission": mission.model_dump(mode="json")})
        return {
            "action": "new_mission",
            "mission": mission.model_dump(mode="json"),
            "confidence_score": result.confidence_score,
            "llm_endpoint": "databricks-claude-haiku-4-5",
        }

    return {
        "action": result.action_type,
        "output": result.model_dump(mode="json"),
        "llm_endpoint": "databricks-claude-haiku-4-5",
    }
