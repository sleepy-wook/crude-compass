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

    # Provenance — demo inject vs agent (Mission Plan LLM) vs seed
    # Lakebase column 미존재여도 default None이라 backward-compatible.
    source: Literal["demo_inject", "agent", "seed"] | None = None


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

    # 의사결정 cycle label (LLM이 current_date 기반 추론)
    cycle: str | None = None  # "6월 Term 갱신 (월말)" 등

    # Supplier mix 권고 — 시연 example (실제는 매니저 OSP allocation 기반)
    supplier_mix: list["SupplierAllocation"] = Field(default_factory=list)


class SignalContext(BaseModel):
    """Mission Plan Agent input — 최근 90일 top 시그널."""

    signal_id: str          # bronze.news_articles.article_id
    published_at: datetime
    source: str             # GDELT_hormuz, EIA_inventory, OPEC_monthly...
    direction: Literal["bullish", "bearish", "neutral"]
    importance: int         # 0-100
    category: str
    title: str


class MarketContext(BaseModel):
    """LLM이 가격/환율/뉴스를 종합 판단하도록 inject되는 시장 상태."""

    # Oil prices (USD/bbl, latest close)
    dubai_usd: float | None = None
    brent_usd: float | None = None
    wti_usd: float | None = None
    brent_dubai_spread_usd: float | None = None
    # Price trend (7d % change, Dubai 기준)
    dubai_7d_change_pct: float | None = None
    # FX (USD/KRW)
    usd_krw_rate: float | None = None
    usd_krw_7d_change_pct: float | None = None
    # Headline news (top 3 직전 7일)
    headline_titles: list[str] = Field(default_factory=list)


class SupplierInfo(BaseModel):
    """K-Petroleum supplier universe — 한국 정유 2024 import portfolio 정합."""

    name: str                # "ARAMCO Arab Light"
    region: str              # "Saudi" / "US" / "UAE" / "Kuwait" / "Iraq"
    grade: str               # "Arab Light" / "WTI" / "Murban" / "Kuwait Export" / "Basra Light"
    portfolio_share_pct: float  # 2024 KNOC 비중 (Saudi 32, US 16.4, UAE 14 etc)
    role: str                # "Term 중심" / "Term+Spot"
    osp_cycle: str | None    # "월간 발표 (월초)" 등


# K-Petroleum 5 supplier (KNOC 2024 통계 정합)
K_PETROLEUM_SUPPLIER_UNIVERSE: list[SupplierInfo] = [
    SupplierInfo(
        name="ARAMCO Arab Light",
        region="Saudi",
        grade="Arab Light",
        portfolio_share_pct=32.0,
        role="Term 중심",
        osp_cycle="월간 발표 (월초)",
    ),
    SupplierInfo(
        name="US WTI/Bakken/Eagle Ford",
        region="US",
        grade="WTI/Bakken",
        portfolio_share_pct=16.4,
        role="Term+Spot",
        osp_cycle="floating (Brent linked)",
    ),
    SupplierInfo(
        name="ADNOC Murban",
        region="UAE",
        grade="Murban",
        portfolio_share_pct=14.0,
        role="Term 중심",
        osp_cycle="월간 발표",
    ),
    SupplierInfo(
        name="KOC Kuwait Export",
        region="Kuwait",
        grade="Kuwait Export",
        portfolio_share_pct=8.0,
        role="Term 중심",
        osp_cycle="월간 발표 (Saudi benchmark)",
    ),
    SupplierInfo(
        name="KPC Basra Light",
        region="Iraq",
        grade="Basra Light",
        portfolio_share_pct=6.0,
        role="Term 중심",
        osp_cycle="월간 발표 (Saudi benchmark)",
    ),
]


class SupplierAllocation(BaseModel):
    """LLM 권고에 포함되는 supplier 분배 — 시연 example."""

    supplier_name: str       # "ARAMCO Arab Light"
    delta_bpd: int           # +25,000 (b/d 단위 추가/감소)
    rationale: str           # "Saudi OSP +$0.50 예상 + 호르무즈 우회 위험"


class MissionPlanInput(BaseModel):
    """Mission Plan Agent input."""

    pattern_score: float = Field(ge=0, le=100)
    bullish_score: float
    bearish_score: float
    cross_val_bonus: float
    signal_count_90d: int

    # 최근 90일 top 시그널 (importance desc, max 20)
    top_signals: list[SignalContext] = Field(default_factory=list)

    # 진행 중 mission (Pivot 검토용). 1 mission 정책 — list 아닌 single
    active_mission: Mission | None = None

    # 시장 컨텍스트 — LLM이 가격·환율·뉴스 종합 판단용
    market_context: MarketContext | None = None

    # K-Petroleum supplier universe — LLM이 supplier mix 권고에 참조
    supplier_universe: list[SupplierInfo] = Field(default_factory=list)

    # 현재 ISO date — LLM이 의사결정 cycle 추론 ("6월 Term 갱신" 등)
    current_date: str | None = None
