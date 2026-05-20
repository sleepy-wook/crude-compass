"""Agent Bricks Supervisor Agent endpoint.

POST /api/supervisor/query — 자연어 질의 → Supervisor가 3 sub-agent 자동 라우팅 →
종합 답변 + tools_used trace 반환.

settings.supervisor_enabled False 또는 호출 실패 시 fallback (genie.py 4-tier로 우회).

D-3: optional mission_id로 Investigation을 특정 case에 bind.
     호출 성공 시 agent_activity_events table에 각 tool 호출 + synthesized 결과 persist.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.services.genie import fallback_canned
from app.services.supervisor import (
    SupervisorNotConfigured,
    SupervisorResponse,
    query_supervisor,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/supervisor", tags=["supervisor"])


# tool name → agent_activity actor 정규화 (frontend label 매핑용)
_TOOL_ACTOR_MAP = {
    "genie": "genie",
    "crude oil market analysis": "genie",
    "crude-compass-ka": "knowledge_assistant",
    "knowledge_assistant": "knowledge_assistant",
    "knowledge assistant": "knowledge_assistant",
    "mission_plan_advice": "mission_plan_uc",
}


def _build_reasoning_path(tools_called: list[str], response: dict | None = None) -> list[str]:
    """단순 narrative — tool 선택 이유 list.

    예: [
        "Genie 호출 — structured market evidence 필요",
        "KA 호출 — document evidence 보강",
        "mission_plan_advice UDF 호출 — recommendation 합성",
    ]
    """
    del response  # 미사용 (향후 확장 hook)
    path: list[str] = []
    if "genie" in tools_called:
        path.append("Genie 호출 — structured market evidence 필요")
    if "knowledge_assistant" in tools_called:
        path.append("KA 호출 — document evidence 보강")
    if "mission_plan_uc" in tools_called or "mission_plan_advice" in tools_called:
        path.append("mission_plan_advice UDF 호출 — recommendation 합성")
    if not path:
        path.append("도구 호출 없이 직접 합성 (단순 질의)")
    return path


def _normalize_actor(tool_name: str) -> str:
    """sub-agent name → agent_activity actor enum.

    매칭 안 되면 lowercased name 그대로 (frontend가 일반 'tool' label로 처리).
    """
    if not tool_name:
        return "supervisor"
    key = tool_name.strip().lower()
    return _TOOL_ACTOR_MAP.get(key, key)


def _persist_supervisor_events(mission_id: UUID | None, res: SupervisorResponse) -> None:
    """Supervisor 호출 결과를 agent_activity_events에 persist (best-effort).

    mission_id 없으면 system-wide event (mission_id NULL).
    각 tool_used → actor:invoked event, 최종 → supervisor:synthesized event.
    """
    try:
        from app.db.lakebase import acquire
        from app.db.repositories import agent_activity

        with acquire() as conn:
            tools_called: list[str] = []
            for tool in res.tools_used:
                actor = _normalize_actor(tool.name)
                tools_called.append(actor)
                preview = (tool.result_preview or "")[:200] or f"{tool.name} 호출"
                agent_activity.insert_event(
                    conn,
                    mission_id=mission_id,
                    actor=actor,
                    action="invoked",
                    result_preview=preview,
                    metadata={"tool_name": tool.name, "arguments": tool.arguments},
                )
            # 최종 합성
            answer_preview = (res.answer or "")[:200]
            agent_activity.insert_event(
                conn,
                mission_id=mission_id,
                actor="supervisor",
                action="synthesized",
                result_preview=answer_preview or "Supervisor 응답 종합",
                metadata={
                    "tool_count": len(res.tools_used),
                    "tools": tools_called,
                    "reasoning_path": _build_reasoning_path(tools_called),
                },
            )
            conn.commit()
    except Exception as e:
        logger.warning("agent_activity persist (supervisor) failed: %s", e)


class SupervisorQueryRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=500)
    mission_id: UUID | None = Field(
        default=None,
        description="Investigation을 특정 case에 bind. agent_activity_events에 mission_id 기록.",
    )


@router.post("/query")
async def query(body: SupervisorQueryRequest) -> dict[str, Any]:
    """Supervisor Agent 자연어 질의.

    Response:
    - answer: 종합 답변 텍스트
    - source: 'live' (Supervisor 호출 성공) | 'fallback' (Genie fallback으로 우회)
    - tools_used: [{name, arguments, result_preview}] — 어떤 sub-agent 사용됐는지
    """
    settings = get_settings()
    if settings.supervisor_enabled:
        try:
            res: SupervisorResponse = await query_supervisor(body.question)
            # best-effort persistence (실패해도 답변 흐름 유지)
            asyncio.create_task(
                asyncio.to_thread(_persist_supervisor_events, body.mission_id, res)
            )
            return res.to_dict()
        except (SupervisorNotConfigured, TimeoutError, Exception) as e:
            logger.warning("supervisor live → fallback: %s", e)

    # Fallback path — genie fallback canned 사용
    genie_res = await fallback_canned(body.question)
    return {
        "answer": genie_res.answer,
        "source": "fallback",
        "tools_used": [],
        "fallback_genie_source": genie_res.source,
        "fallback_sql": genie_res.sql,
        "fallback_data": genie_res.data,
    }


@router.get("/health")
async def supervisor_health() -> dict[str, Any]:
    settings = get_settings()
    return {
        "enabled": settings.supervisor_enabled,
        "endpoint_name": settings.supervisor_endpoint_name or "(missing)",
        "fallback_available": True,
    }
