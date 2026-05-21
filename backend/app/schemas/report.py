"""Pydantic v2 schema for reports model (2026-05-21).

Event-driven AI report + 06:30 daily summary.
Replaces missions for daily workflow. missions = read-only backtest.

DDL: databricks/schemas/lakebase.sql §6-§7
"""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ────────────────────────────────────────────────────────────────────────
# Enums (PostgreSQL CHECK constraints와 1:1)
# ────────────────────────────────────────────────────────────────────────


class TriggerType(str, Enum):
    GDELT_SIGNAL = "gdelt_signal"
    PRICE_SPIKE = "price_spike"
    PATTERN_DRIFT = "pattern_drift"


class ReportStatus(str, Enum):
    PENDING = "pending"
    KEPT = "kept"  # 매니저 "활성화" — 다음 daily report input으로 사용 대기
    DROPPED = "dropped"
    AI_DROPPED = "ai_dropped"
    ARCHIVED = "archived"  # daily report가 input으로 한번 사용 → 자동 transition


class StatusActor(str, Enum):
    MANAGER = "manager"
    AI = "ai"


# Recommendation vocabulary — LLM이 이 6개 중 하나 emit (plan §2.2)
class Recommendation(str, Enum):
    HOLD = "HOLD"
    DEFER_SPOT = "DEFER SPOT"
    ACCELERATE_SPOT = "ACCELERATE SPOT"
    REVIEW_TERM = "REVIEW TERM"
    HEDGE = "HEDGE"
    DIVERSIFY = "DIVERSIFY"


# ────────────────────────────────────────────────────────────────────────
# Report (event-driven)
# ────────────────────────────────────────────────────────────────────────


class ReportReasoning(BaseModel):
    """reasoning JSONB structure."""

    key_signals: list[str] = Field(default_factory=list)
    logic: str = ""
    risk_factors: list[str] = Field(default_factory=list)


class Report(BaseModel):
    """reports table row.

    Frontend 노출 시 status_changed_by, ai_drop_reason 등 일부 column은 optional view.
    """

    model_config = ConfigDict(use_enum_values=True)

    report_id: UUID
    parent_id: UUID | None = None

    trigger_type: TriggerType
    trigger_meta: dict[str, Any] = Field(default_factory=dict)

    status: ReportStatus = ReportStatus.PENDING
    status_changed_at: datetime | None = None
    status_changed_by: StatusActor | None = None

    headline: str
    summary: str
    reasoning: dict[str, Any] = Field(default_factory=dict)
    recommendation: Recommendation | None = None
    related_signals: list[dict[str, Any]] = Field(default_factory=list)

    revisits_id: UUID | None = None
    ai_drop_reason: str | None = None

    version: int = 1
    created_at: datetime


class ReportCreate(BaseModel):
    """LLM 결과 + trigger meta → INSERT row.

    report_id, created_at은 DB가 채움.
    """

    parent_id: UUID | None = None
    trigger_type: TriggerType
    trigger_meta: dict[str, Any] = Field(default_factory=dict)
    headline: str
    summary: str
    reasoning: dict[str, Any] = Field(default_factory=dict)
    recommendation: Recommendation | None = None
    related_signals: list[dict[str, Any]] = Field(default_factory=list)
    revisits_id: UUID | None = None


class ReportThread(BaseModel):
    """get_with_thread() 응답.

    root: thread root (parent_id IS NULL인 첫 보고서)
    thread: root → 자손 chronological order
    """

    root: Report
    thread: list[Report] = Field(default_factory=list)


# ────────────────────────────────────────────────────────────────────────
# DailyReport (06:30 cron)
# ────────────────────────────────────────────────────────────────────────


class RatioScenario(BaseModel):
    """ratio_suggestion.scenarios[i]."""

    name: str  # "base" | "bull" | "bear"
    expected_saving_pct: float


class RatioSuggestion(BaseModel):
    """ratio_suggestion JSONB structure."""

    direction: str = "neutral"  # "lean_hedge" | "neutral" | "lean_opportunity"
    term_delta_pct: str = "0"  # "+5" / "-5" 등 string (LLM 출력 그대로)
    spot_delta_pct: str = "0"
    qualitative: str = ""
    scenarios: list[RatioScenario] = Field(default_factory=list)


class DailyReport(BaseModel):
    """daily_reports table row."""

    daily_id: UUID
    report_date: date
    prev_daily_id: UUID | None = None

    kept_report_ids: list[UUID] = Field(default_factory=list)
    kept_count: int = 0
    kept_summary: str | None = None
    prev_daily_summary: str | None = None
    market_context: str | None = None

    ratio_suggestion: dict[str, Any] = Field(default_factory=dict)
    reasoning: str | None = None
    confidence: float | None = None

    created_at: datetime


class DailyReportCreate(BaseModel):
    """LLM 결과 → INSERT row.

    daily_id, created_at은 DB가 채움.
    """

    report_date: date
    prev_daily_id: UUID | None = None
    kept_report_ids: list[UUID] = Field(default_factory=list)
    kept_count: int = 0
    kept_summary: str | None = None
    prev_daily_summary: str | None = None
    market_context: str | None = None
    ratio_suggestion: dict[str, Any] = Field(default_factory=dict)
    reasoning: str | None = None
    confidence: float | None = None
