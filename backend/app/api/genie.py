"""Genie 자연어 질의 endpoint.

POST /api/genie/query — settings.genie_enabled True 시 live Conversation API 호출,
실패/미설정 시 fallback (Lakebase 직접 SQL 또는 hardcoded text).

항상 200 응답 + source field로 mode 구분 (live / fallback_data / fallback_text / fallback).
평가위원에게 transparency — 데모 narrator '현재 fallback_data 모드입니다' 식 명시 가능.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.services.genie import (
    GenieNotConfigured,
    GenieResponse,
    fallback_canned,
    query_genie,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/genie", tags=["genie"])


class GenieQueryRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=500)
    conversation_id: str | None = None


@router.post("/query")
async def query(body: GenieQueryRequest) -> dict[str, Any]:
    """Genie 자연어 질의 — live 또는 fallback 응답.

    Response source enum:
    - live: Genie Conversation API 정상 응답
    - fallback_data: Lakebase 직접 SQL 호출 + 결과 포맷팅
    - fallback_text: SQL 실패, hardcoded 설명 텍스트
    - fallback: 키워드 매칭 실패 (generic meta-answer)
    """
    settings = get_settings()
    if settings.genie_enabled:
        try:
            res: GenieResponse = await query_genie(body.question, body.conversation_id)
            return res.to_dict()
        except (GenieNotConfigured, TimeoutError, Exception) as e:
            logger.warning("genie live → fallback: %s", e)

    # Fallback path
    res = await fallback_canned(body.question)
    return res.to_dict()


@router.get("/health")
async def genie_health() -> dict[str, Any]:
    """Quick health probe — config 상태."""
    settings = get_settings()
    return {
        "enabled": settings.genie_enabled,
        "space_id": settings.genie_space_id or "(missing)",
        "fallback_available": True,
    }
