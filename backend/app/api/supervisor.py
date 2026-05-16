"""Agent Bricks Supervisor Agent endpoint.

POST /api/supervisor/query — 자연어 질의 → Supervisor가 4 sub-agent 자동 라우팅 →
종합 답변 + tools_used trace 반환.

settings.supervisor_enabled False 또는 호출 실패 시 fallback (genie.py 4-tier로 우회).
"""
from __future__ import annotations

import logging
from typing import Any

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


class SupervisorQueryRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=500)


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
