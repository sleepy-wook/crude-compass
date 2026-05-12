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
