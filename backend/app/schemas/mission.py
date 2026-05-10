"""Pydantic v2 schema for missions.

api_contract.md §1.1 와 1:1 매핑. TypeScript 타입은 frontend/src/lib/types.ts.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class MissionType(str, Enum):
    HEDGE = "HEDGE"
    OPPORTUNITY = "OPPORTUNITY"


class MissionStatus(str, Enum):
    PROPOSED = "proposed"
    ACTIVE = "active"
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    PAUSED = "paused"
    PIVOTED = "pivoted"
    ABORTED = "aborted"
    COMPLETED = "completed"


class MissionUrgency(str, Enum):
    OPTIONAL = "optional"
    DEFAULT = "default"
    URGENT = "urgent"


class PivotEntry(BaseModel):
    from_type: MissionType
    to_type: MissionType
    occurred_at: datetime
    reason: str
    pattern_score_at: float


class Mission(BaseModel):
    mission_id: UUID
    mission_type: MissionType
    status: MissionStatus
    goal_text: str
    pattern_score: float = Field(ge=0, le=100)
    reasoning: str
    simulation_roi: dict[str, float]
    urgency: MissionUrgency = MissionUrgency.DEFAULT
    target_pct: int | None = None
    duration_days: int = 28

    created_at: datetime
    confirmed_at: datetime | None = None
    confirmed_by: str | None = None
    confirmed_via: Literal["slack", "apps"] | None = None
    completed_at: datetime | None = None

    pivot_history: list[PivotEntry] = Field(default_factory=list)
    version: int = 1


class MissionPlanOutput(BaseModel):
    """Mission Plan Agent (Agent Bricks) 출력 schema.

    시나리오 § 9.7 + § 10 Lifecycle rule 반영.
    """

    # 새 mission 또는 Pivot — action_type으로 구분
    action_type: Literal["new_mission", "pivot", "pause", "abort", "continue"] = "new_mission"

    mission_type: MissionType
    goal_text: str
    reasoning: str
    simulation_roi: dict[str, float]
    urgency: MissionUrgency = MissionUrgency.DEFAULT
    pattern_score: float = Field(ge=0, le=100)
    confidence_score: float = Field(ge=0, le=100, default=70.0)
    target_pct: int | None = None
    duration_days: int = 28


class SignalContext(BaseModel):
    """Mission Plan Agent input — 최근 90일 top 시그널."""

    signal_id: str          # bronze.news_articles.article_id
    published_at: datetime
    source: str             # GDELT_hormuz, EIA_inventory, OPEC_monthly...
    direction: Literal["bullish", "bearish", "neutral"]
    importance: int         # 0-100
    category: str
    title: str


class MissionPlanInput(BaseModel):
    """Mission Plan Agent input."""

    pattern_score: float = Field(ge=0, le=100)
    bullish_score: float
    bearish_score: float
    cross_val_bonus: float
    signal_count_90d: int

    # 최근 90일 top 시그널 (importance desc, max 20)
    top_signals: list[SignalContext] = Field(default_factory=list)

    # 진행 중 mission (Pivot 검토용)
    active_mission: Mission | None = None
