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
    SignalContext,
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


@router.get("/{mission_id}/activity")
async def get_mission_activity(mission_id: UUID) -> dict:
    """Agent Bricks orchestration activity timeline.

    Returns latest 50 events for the mission (occurred_at DESC).
    Lakebase 미연동 환경에서는 empty list 반환 (graceful).
    """
    import asyncio
    from app.core.config import get_settings

    settings = get_settings()
    if not getattr(settings, "use_lakebase", False) and __import__("os").getenv("USE_LAKEBASE", "false").lower() != "true":
        return {"events": []}

    def _read() -> list[dict]:
        try:
            from app.db.lakebase import acquire
            from app.db.repositories import agent_activity as activity_repo
            with acquire() as conn:
                return activity_repo.list_for_mission(conn, mission_id)
        except Exception:
            return []

    events = await asyncio.to_thread(_read)
    return {"events": events}


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
    """LLM Mission Plan Agent — Pattern Score + signals → recommend mission."""
    result = call_mission_plan_agent(payload)
    if result is None:
        from app.services.mission_plan import last_llm_error
        raise HTTPException(status_code=500, detail={"code": "LLM_CALL_FAILED", "error": last_llm_error()})

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
    """Discovery '지금 새 추천 생성' 버튼이 호출. 모두 optional override.

    default: silver.signal_events_decayed 최근 30일 top 20 자동 fetch.
    fetch 실패 또는 use_demo_signals=true 시 hardcoded _DEMO_SIGNALS fallback.
    """
    pattern_score: float | None = None
    bullish_score: float | None = None
    bearish_score: float | None = None
    use_demo_signals: bool = False  # default: silver fetch (true면 demo seed)


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


def _fetch_top_signals_from_silver(limit: int = 20) -> list[SignalContext]:
    """silver.signal_events_decayed 최근 30일 |weighted_contribution| top N → SignalContext.

    실패 시 RuntimeError raise. 호출자가 fallback 처리.
    """
    import asyncio  # noqa: F401 (caller threads)
    from datetime import datetime
    from app.api.pattern import _q  # 같은 Databricks SQL helper 재사용
    from app.schemas.mission import SignalContext

    sql = f"""
      SELECT
        s.signal_id,
        CAST(s.event_date AS STRING) AS event_date_iso,
        s.signal_type,
        s.direction,
        CAST(s.raw_intensity AS DOUBLE) AS importance,
        COALESCE(a.category,
          CASE s.signal_type
            WHEN 'eia_inventory' THEN 'supply'
            WHEN 'opec_momr'     THEN 'demand'
            WHEN 'fx_krw_usd'    THEN 'macro'
            WHEN 'price_spike'   THEN 'market'
            ELSE 'unknown'
          END) AS category,
        COALESCE(a.title,
          CONCAT(s.signal_type, ' ', CAST(s.event_date AS STRING),
                 ' weighted=', CAST(s.weighted_contribution AS STRING))) AS title
      FROM crude_compass.silver.signal_events_decayed s
      LEFT JOIN crude_compass.bronze.news_articles a
        ON s.signal_id = a.article_id AND s.signal_type = 'news_tone'
      WHERE s.event_date >= CURRENT_DATE() - INTERVAL 30 DAYS
        AND s.direction != 'neutral'
      ORDER BY ABS(s.weighted_contribution) DESC
      LIMIT {limit}
    """
    rows = _q(sql, timeout="20s")
    out: list[SignalContext] = []
    for r in rows:
        try:
            event_dt = datetime.fromisoformat(str(r[1])).replace(tzinfo=timezone.utc)
        except Exception:
            event_dt = datetime.now(timezone.utc)
        out.append(SignalContext(
            signal_id=str(r[0]),
            published_at=event_dt,
            source=str(r[2]),
            direction=str(r[3]),
            importance=int(float(r[4] or 0)),
            category=str(r[5]),
            title=(str(r[6])[:200] if r[6] else f"{r[2]} signal"),
        ))
    return out


def _fetch_market_context():
    """가격·환율·헤드라인 fetch → MarketContext.

    LLM이 신호 점수만 보지 않고 가격 timing까지 종합 판단하도록.
    실패 시 None — recommend_now가 None 그대로 넘기면 prompt에 "(no market context)" 표시.
    """
    from app.api.pattern import _q
    from app.schemas.mission import MarketContext
    try:
        # Oil prices — Dubai latest + 7d ago for change %
        price_rows = _q(
            """
            WITH latest AS (
              SELECT trade_date, wti_usd, brent_usd, dubai_usd, brent_dubai_spread_usd
              FROM crude_compass.gold.oil_prices_wide
              ORDER BY trade_date DESC LIMIT 1
            ),
            d7 AS (
              SELECT dubai_usd AS dubai_7d_ago
              FROM crude_compass.gold.oil_prices_wide
              WHERE trade_date <= (SELECT trade_date FROM latest) - INTERVAL 7 DAYS
              ORDER BY trade_date DESC LIMIT 1
            )
            SELECT latest.wti_usd, latest.brent_usd, latest.dubai_usd,
                   latest.brent_dubai_spread_usd, d7.dubai_7d_ago
            FROM latest CROSS JOIN d7
            """,
            timeout="15s",
        )
        wti = brent = dubai = spread = dubai_7d = None
        if price_rows:
            r = price_rows[0]
            wti = float(r[0]) if r[0] is not None else None
            brent = float(r[1]) if r[1] is not None else None
            dubai = float(r[2]) if r[2] is not None else None
            spread = float(r[3]) if r[3] is not None else None
            dubai_7d = float(r[4]) if r[4] is not None else None
        dubai_change = None
        if dubai is not None and dubai_7d not in (None, 0):
            dubai_change = round((dubai - dubai_7d) / dubai_7d * 100, 2)

        # FX — USD/KRW latest + 7d delta
        fx_rows = _q(
            """
            SELECT rate, delta_7d
            FROM crude_compass.gold.fx_with_delta
            WHERE pair = 'USD/KRW' ORDER BY date DESC LIMIT 1
            """,
            timeout="10s",
        )
        usd_krw = krw_change = None
        if fx_rows:
            r = fx_rows[0]
            usd_krw = float(r[0]) if r[0] is not None else None
            krw_change = float(r[1]) if r[1] is not None else None

        # Recent headlines (top 3, importance desc, last 7d)
        news_rows = _q(
            """
            SELECT title FROM crude_compass.gold.news_top_signals
            WHERE event_date >= CURRENT_DATE() - INTERVAL 7 DAYS
            ORDER BY importance DESC LIMIT 3
            """,
            timeout="10s",
        )
        headlines = [str(r[0]) for r in news_rows if r and r[0]]

        return MarketContext(
            dubai_usd=dubai,
            brent_usd=brent,
            wti_usd=wti,
            brent_dubai_spread_usd=spread,
            dubai_7d_change_pct=dubai_change,
            usd_krw_rate=usd_krw,
            usd_krw_7d_change_pct=krw_change,
            headline_titles=headlines,
        )
    except Exception:
        return None


def _fetch_latest_pattern_score() -> dict | None:
    """gold.daily_risk_score 최신 1행 — pattern_score/bullish/bearish/signal_count_90d/cross_val."""
    from app.api.pattern import _q
    sql = """
      SELECT
        CAST(pattern_score AS DOUBLE),
        CAST(bullish_score AS DOUBLE),
        CAST(bearish_score AS DOUBLE),
        CAST(cross_val_bonus AS DOUBLE),
        CAST(signal_count_90d AS INT)
      FROM crude_compass.silver.pattern_scores_daily
      ORDER BY date DESC
      LIMIT 1
    """
    rows = _q(sql, timeout="15s")
    if not rows:
        return None
    r = rows[0]
    return {
        "pattern_score": float(r[0] or 0),
        "bullish_score": float(r[1] or 0),
        "bearish_score": float(r[2] or 0),
        "cross_val_bonus": float(r[3] or 0),
        "signal_count_90d": int(r[4] or 0),
    }


@router.post("/recommend_now")
async def recommend_now(body: RecommendNowRequest = RecommendNowRequest()) -> dict:
    """No-body wrapper for demo '지금 새 추천 생성' button.

    Flow:
      1. silver 최근 30일 top 20 signals 자동 fetch (use_demo_signals=False default)
      2. 실패 또는 비어있으면 _DEMO_SIGNALS hardcoded fallback
      3. gold.daily_risk_score 최신 pattern/bullish/bearish 자동 채움
      4. active mission 있으면 Pivot 검토 candidate
      5. LLM 호출 → MissionPlanOutput

    Response.signals_source = 'silver' | 'demo_fallback' — 평가위원 검증용.
    """
    import asyncio
    import logging
    from datetime import datetime

    logger = logging.getLogger(__name__)

    top_signals: list[SignalContext] = []
    pattern_meta: dict | None = None
    signals_source = "demo_fallback"

    if not body.use_demo_signals:
        try:
            top_signals = await asyncio.to_thread(_fetch_top_signals_from_silver, 20)
            if top_signals:
                signals_source = "silver"
        except Exception as e:
            logger.warning("silver fetch failed → demo fallback: %s", e)
        try:
            pattern_meta = await asyncio.to_thread(_fetch_latest_pattern_score)
        except Exception as e:
            logger.warning("pattern score fetch failed: %s", e)

    # silver 비어있거나 실패 → hardcoded fallback
    if not top_signals:
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
        signals_source = "demo_fallback"

    # pattern/bullish/bearish: explicit override > silver pattern_meta > demo default 82/78/22
    pattern_score = (
        body.pattern_score if body.pattern_score is not None
        else (pattern_meta["pattern_score"] if pattern_meta else 82.0)
    )
    bullish_score = (
        body.bullish_score if body.bullish_score is not None
        else (pattern_meta["bullish_score"] if pattern_meta else 78.0)
    )
    bearish_score = (
        body.bearish_score if body.bearish_score is not None
        else (pattern_meta["bearish_score"] if pattern_meta else 22.0)
    )
    cross_val_bonus = (pattern_meta["cross_val_bonus"] if pattern_meta else 15.0)
    signal_count_90d = (pattern_meta["signal_count_90d"] if pattern_meta else len(top_signals))

    store = get_store()
    actives = await store.get_active()
    # 1 mission per 시점 정책 — 가장 최근 active만 LLM에 전달.
    # LLM은 active 존재 시 new_mission 대신 pivot/modify/continue 권장 (prompt constraint).
    active_mission = actives[0] if actives else None

    # 시장 컨텍스트 — 가격·환율·헤드라인 fetch (Warehouse 1회 호출, 실패 시 None)
    market_context = await asyncio.to_thread(_fetch_market_context)

    # K-Petroleum supplier universe + current_date (LLM이 cycle / supplier_mix 추론)
    from app.schemas.mission import K_PETROLEUM_SUPPLIER_UNIVERSE, PreviousRecommendation
    from datetime import date as _date

    # 이전 7일 권고 history — LLM이 delta_vs_previous narrative 생성
    previous_recommendations: list[PreviousRecommendation] = []
    try:
        store = get_store()
        all_missions = await store.all()
        # 오늘 외, 최근 7일, 가장 최근 순
        today_iso = _date.today().isoformat()
        prev_missions = [
            mm
            for mm in all_missions
            if mm.created_at.date().isoformat() != today_iso
            and mm.target_pct is not None
        ]
        prev_missions.sort(key=lambda x: x.created_at, reverse=True)
        for prev in prev_missions[:7]:
            previous_recommendations.append(
                PreviousRecommendation(
                    date=prev.created_at.date().isoformat(),
                    mission_type=prev.mission_type,
                    target_pct=prev.target_pct,
                    pattern_score=prev.pattern_score,
                    reasoning_summary=prev.reasoning[:100],
                )
            )
    except Exception as e:
        logger.warning("previous_recommendations fetch failed: %s", e)

    payload = MissionPlanInput(
        pattern_score=pattern_score,
        bullish_score=bullish_score,
        bearish_score=bearish_score,
        cross_val_bonus=cross_val_bonus,
        signal_count_90d=signal_count_90d,
        top_signals=top_signals,
        active_mission=active_mission,
        market_context=market_context,
        supplier_universe=K_PETROLEUM_SUPPLIER_UNIVERSE,
        current_date=_date.today().isoformat(),
        previous_recommendations=previous_recommendations,
    )

    # 기존 recommend logic 재사용
    result = call_mission_plan_agent(payload)
    if result is None:
        from app.services.mission_plan import last_llm_error
        raise HTTPException(status_code=500, detail={"code": "LLM_CALL_FAILED", "error": last_llm_error()})

    # Mission uniqueness 강제 — LLM이 active 있는데 new_mission 권장했으면 modify로 강등
    if active_mission is not None and result.action_type == "new_mission":
        logger.warning(
            "LLM ignored active_mission constraint — downgrading new_mission to modify"
        )
        result.action_type = "modify"

    # Sub-B Honest Simulation — Best/Likely/Worst 3 scenarios deterministic 계산
    from app.services.simulation import compute_3_scenarios as _compute_3_scen
    if result.target_pct is not None:
        try:
            sim_scenarios = _compute_3_scen(
                mission_type=result.mission_type.value if hasattr(result.mission_type, "value") else str(result.mission_type),
                target_pct=result.target_pct,
                duration_days=result.duration_days,
                market_context=market_context,
            )
        except Exception as e:
            logger.warning("simulation compute failed: %s", e)
            sim_scenarios = []
    else:
        sim_scenarios = []

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
            # Sub-A actionable + Sub-B honest sim
            cycle=result.cycle,
            supplier_mix=result.supplier_mix,
            simulation_scenarios=sim_scenarios,
            # AI Agent 어제 vs 오늘 변동 narrative
            delta_vs_previous=result.delta_vs_previous,
        )
        await store.create(mission)
        await bus.publish({"type": "mission.proposed", "mission": mission.model_dump(mode="json")})
        return {
            "action": "new_mission",
            "mission": mission.model_dump(mode="json"),
            "confidence_score": result.confidence_score,
            "llm_endpoint": "databricks-claude-haiku-4-5",
            "signals_source": signals_source,  # 'silver' | 'demo_fallback'
            "signal_count": len(top_signals),
        }

    return {
        "action": result.action_type,
        "output": result.model_dump(mode="json"),
        "llm_endpoint": "databricks-claude-haiku-4-5",
        "signals_source": signals_source,
        "signal_count": len(top_signals),
    }
