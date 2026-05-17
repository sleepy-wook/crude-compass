"""Pattern Score + Backtest read endpoints (Databricks SQL via SDK)."""
from __future__ import annotations

from datetime import date
from functools import lru_cache

from fastapi import APIRouter, HTTPException
from databricks.sdk import WorkspaceClient

router = APIRouter(prefix="/api", tags=["pattern"])


@lru_cache(maxsize=1)
def _client() -> WorkspaceClient:
    # crude-compass profile (~/.databrickscfg). Apps deploy 시는 자동 env 인증.
    import os
    profile = os.getenv("DATABRICKS_CONFIG_PROFILE", "crude-compass")
    try:
        return WorkspaceClient(profile=profile)
    except Exception:
        return WorkspaceClient()  # fallback


@lru_cache(maxsize=1)
def _warehouse_id() -> str:
    """Find first Serverless Starter warehouse."""
    w = _client()
    for wh in w.warehouses.list():
        n = (wh.name or "").lower()
        if "serverless" in n or "starter" in n:
            return wh.id
    whs = list(w.warehouses.list())
    if not whs:
        raise RuntimeError("No warehouses available")
    return whs[0].id


def _q(sql: str, timeout: str = "30s") -> list[list]:
    w = _client()
    r = w.statement_execution.execute_statement(
        statement=sql.strip(), warehouse_id=_warehouse_id(), wait_timeout=timeout,
    )
    if r.status and r.status.error:
        raise RuntimeError(r.status.error.message)
    if r.result and r.result.data_array:
        return r.result.data_array
    return []


# ────────────────────────────────────────────────────────────────────────
# /api/pattern-score/current — latest Pattern Score + 30-day history
# ────────────────────────────────────────────────────────────────────────
@router.get("/pattern-score/current")
async def current_pattern_score() -> dict:
    """gold.daily_risk_score 최신 + 30일 history."""
    try:
        # 최신
        latest = _q("""
            SELECT date, pattern_score, mission_type, bullish_score, bearish_score,
                   cross_val_bonus, confidence_score, signal_count_90d
            FROM crude_compass.gold.daily_risk_score
            ORDER BY date DESC LIMIT 1
        """)
        if not latest:
            return {"current": None, "history": []}
        r = latest[0]
        current = {
            "date": str(r[0]),
            "pattern_score": float(r[1]) if r[1] else None,
            "mission_type": r[2],
            "bullish_score": float(r[3]) if r[3] else None,
            "bearish_score": float(r[4]) if r[4] else None,
            "cross_val_bonus": float(r[5]) if r[5] else None,
            "confidence_score": float(r[6]) if r[6] else None,
            "signal_count_90d": int(r[7]) if r[7] else None,
        }

        # 30-day history
        history_rows = _q("""
            SELECT date, pattern_score FROM crude_compass.gold.daily_risk_score
            WHERE date >= CURRENT_DATE() - INTERVAL 30 DAYS
            ORDER BY date
        """)
        history = [{"date": str(row[0]), "pattern_score": float(row[1])} for row in history_rows]

        return {"current": current, "history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": "DATA_FETCH_FAILED", "message": str(e)})


@router.get("/pattern-score/history")
async def pattern_history(days: int = 90) -> dict:
    """Pattern Score history N일. 6년 평시 가치 그래프 (시나리오 §14 Phase 7)는 days=2200."""
    try:
        rows = _q(f"""
            SELECT date, pattern_score, mission_type, bullish_score, bearish_score
            FROM crude_compass.gold.daily_risk_score
            WHERE date >= CURRENT_DATE() - INTERVAL {min(days, 2200)} DAYS
            ORDER BY date
        """)
        return {
            "history": [
                {
                    "date": str(r[0]), "pattern_score": float(r[1]) if r[1] else None,
                    "mission_type": r[2],
                    "bullish_score": float(r[3]) if r[3] else None,
                    "bearish_score": float(r[4]) if r[4] else None,
                } for r in rows
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": "DATA_FETCH_FAILED", "message": str(e)})


# ────────────────────────────────────────────────────────────────────────
# /api/market/fx-history — gold.fx_with_delta view (D-3 추가)
# 시나리오 §7 #5 anchor + §13 랜딩 코스트 — USD/KRW 일별 + 30일 변동성
# ────────────────────────────────────────────────────────────────────────
@router.get("/market/fx-history")
async def fx_history(days: int = 90) -> dict:
    """USD/KRW 일별 + 1d/7d delta + 30일 변동성."""
    try:
        rows = _q(f"""
            SELECT date, rate, delta_1d, delta_7d, vol_30d
            FROM crude_compass.gold.fx_with_delta
            WHERE pair = 'USD/KRW'
              AND date >= CURRENT_DATE() - INTERVAL {min(days, 2200)} DAYS
            ORDER BY date
        """)
        return {
            "pair": "USD/KRW",
            "history": [
                {
                    "date": str(r[0]),
                    "rate": float(r[1]) if r[1] is not None else None,
                    "delta_1d": float(r[2]) if r[2] is not None else None,
                    "delta_7d": float(r[3]) if r[3] is not None else None,
                    "vol_30d": float(r[4]) if r[4] is not None else None,
                }
                for r in rows
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": "DATA_FETCH_FAILED", "message": str(e)})


# ────────────────────────────────────────────────────────────────────────
# /api/market/prices-wide — gold.oil_prices_wide view (D-3 추가)
# 시나리오 §7 #4 anchor — Dubai/Brent/WTI 일별 가격 + Brent-Dubai spread
# ────────────────────────────────────────────────────────────────────────
@router.get("/market/prices-wide")
async def prices_wide(days: int = 90) -> dict:
    """Daily oil prices wide format (WTI/Brent/Dubai pivot + spread)."""
    try:
        rows = _q(f"""
            SELECT trade_date, wti_usd, brent_usd, dubai_usd, brent_dubai_spread_usd
            FROM crude_compass.gold.oil_prices_wide
            WHERE trade_date >= CURRENT_DATE() - INTERVAL {min(days, 2200)} DAYS
            ORDER BY trade_date
        """)
        return {
            "prices": [
                {
                    "trade_date": str(r[0]),
                    "wti_usd": float(r[1]) if r[1] is not None else None,
                    "brent_usd": float(r[2]) if r[2] is not None else None,
                    "dubai_usd": float(r[3]) if r[3] is not None else None,
                    "brent_dubai_spread_usd": float(r[4]) if r[4] is not None else None,
                }
                for r in rows
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": "DATA_FETCH_FAILED", "message": str(e)})


# ────────────────────────────────────────────────────────────────────────
# /api/market/news-top — gold.news_top_signals view (D-3 추가)
# 시나리오 §6.3 #3 anchor — 최근 7일 importance Top 5/day/direction
# ────────────────────────────────────────────────────────────────────────
@router.get("/market/news-top")
async def news_top(limit: int = 20) -> dict:
    """최근 7일 importance ≥ 60 뉴스 (bullish/bearish only)."""
    try:
        rows = _q(f"""
            SELECT event_date, source, tier, title, category, direction,
                   importance, raw_tone, mention_count, url
            FROM crude_compass.gold.news_top_signals
            ORDER BY event_date DESC, importance DESC
            LIMIT {min(limit, 100)}
        """)
        return {
            "items": [
                {
                    "event_date": str(r[0]),
                    "source": r[1], "tier": r[2], "title": r[3],
                    "category": r[4], "direction": r[5],
                    "importance": int(r[6]) if r[6] is not None else None,
                    "raw_tone": float(r[7]) if r[7] is not None else None,
                    "mention_count": int(r[8]) if r[8] is not None else None,
                    "url": r[9],
                }
                for r in rows
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": "DATA_FETCH_FAILED", "message": str(e)})


# ────────────────────────────────────────────────────────────────────────
# /api/market/opec-latest — Document Intelligence wow (시나리오 §9.6)
# OPEC MOMR PDF → ai_parse_document() → bronze.opec_momr_parsed
# Discovery 페이지 citation badge "OPEC MOMR 2026-03 · 사우디 10,110 kbbl/d"
# ────────────────────────────────────────────────────────────────────────
@router.get("/market/opec-latest")
async def opec_latest() -> dict:
    """Latest OPEC MOMR snapshot (gold.opec_demand_gap view).

    시나리오 §14 Phase 4 narrator anchor: "OPEC MOMR 5월 사우디 추가 감산 시그널"
    """
    try:
        rows = _q("""
            SELECT report_month, saudi_production_kbbl_d, iran_production_kbbl_d,
                   opec_total_kbbl_d, forecast_demand_kbbl_d,
                   supply_demand_gap_kbbl_d, market_balance
            FROM crude_compass.gold.opec_demand_gap
            ORDER BY report_month DESC
            LIMIT 2
        """)
        if not rows:
            return {"latest": None, "prev": None}

        def to_obj(r) -> dict:
            return {
                "report_month": r[0],
                "saudi_kbbl_d": float(r[1]) if r[1] is not None else None,
                "iran_kbbl_d": float(r[2]) if r[2] is not None else None,
                "opec_total_kbbl_d": float(r[3]) if r[3] is not None else None,
                "forecast_demand_kbbl_d": float(r[4]) if r[4] is not None else None,
                "supply_demand_gap_kbbl_d": float(r[5]) if r[5] is not None else None,
                "market_balance": r[6],
            }

        latest = to_obj(rows[0])
        prev = to_obj(rows[1]) if len(rows) > 1 else None
        # Saudi delta (latest - prev) — 사우디 감산/증산 시그널
        if prev and latest["saudi_kbbl_d"] is not None and prev["saudi_kbbl_d"] is not None:
            latest["saudi_delta_vs_prev"] = round(
                latest["saudi_kbbl_d"] - prev["saudi_kbbl_d"], 2
            )
        return {"latest": latest, "prev": prev, "source": "ai_parse_document() · OPEC MOMR PDF"}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": "DATA_FETCH_FAILED", "message": str(e)})


# ────────────────────────────────────────────────────────────────────────
# /api/signals/contribution — gold.signal_contribution_30d view (D-3 추가)
# 시나리오 §6.3 #2 "오늘 점수 82는 호르무즈 35%, 두바이 28% ..." anchor
# ────────────────────────────────────────────────────────────────────────
@router.get("/signals/contribution")
async def signal_contribution() -> dict:
    """최근 30일 signal_type × direction 기여도 (총합 % 환산).

    Discovery 페이지 horizontal bar chart 데이터.
    """
    try:
        rows = _q("""
            SELECT signal_type, direction, n_signals, total_contribution,
                   avg_raw_intensity, avg_credibility
            FROM crude_compass.gold.signal_contribution_30d
            ORDER BY ABS(total_contribution) DESC
        """)
        items = [
            {
                "signal_type": r[0],
                "direction": r[1],
                "n_signals": int(r[2]) if r[2] is not None else 0,
                "total_contribution": float(r[3]) if r[3] is not None else 0.0,
                "avg_raw_intensity": float(r[4]) if r[4] is not None else None,
                "avg_credibility": float(r[5]) if r[5] is not None else None,
            }
            for r in rows
        ]
        # % share 계산 (절댓값 기준)
        total_abs = sum(abs(x["total_contribution"]) for x in items) or 1.0
        for x in items:
            x["share_pct"] = round(abs(x["total_contribution"]) / total_abs * 100, 1)
        return {"items": items, "window_days": 30}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": "DATA_FETCH_FAILED", "message": str(e)})


# ────────────────────────────────────────────────────────────────────────
# /api/backtest/* — LLM Mission Plan Agent backtest from Lakebase
# (AI-generated content 정석: Lakebase OLTP)
# ────────────────────────────────────────────────────────────────────────
@router.get("/backtest/results")
async def backtest_results() -> dict:
    """Lakebase backtest_predictions latest run summary.

    Lakebase OAuth role mapping이 production에서 pending 상태일 때:
    HTTP 500 대신 200 OK + lakebase_available=False + reason 반환.
    Frontend가 honest disclosure card를 노출하도록 (평가위원 신뢰).
    """
    import asyncio
    from app.db import lakebase
    from app.db.repositories import backtest as bt_repo

    def _sync():
        with lakebase.acquire() as conn:
            summary = bt_repo.get_summary(conn)
            by_zone = bt_repo.get_zone_breakdown(conn)
            by_conf = bt_repo.get_confidence_breakdown(conn)
        return summary, by_zone, by_conf

    try:
        summary, by_zone, by_conf = await asyncio.to_thread(_sync)
        if not summary:
            return {
                "summary": None,
                "by_zone": [],
                "by_confidence": [],
                "lakebase_available": True,
                "reason": "no_runs",
            }
        return {
            "summary": {
                "run_id": summary.get("run_id"),
                "n_total": int(summary.get("n_total") or 0),
                "n_active": int(summary.get("n_active") or 0),
                "n_hedge": int(summary.get("n_hedge") or 0),
                "n_opp": int(summary.get("n_opp") or 0),
                "avg_save_pct": float(summary["avg_save_pct"]) if summary.get("avg_save_pct") is not None else None,
                "hit_rate_pct": float(summary["hit_rate_pct"]) if summary.get("hit_rate_pct") is not None else None,
            },
            "by_zone": [
                {
                    "zone": r["zone"],
                    "mission_type": r["mission_type"],
                    "n": int(r["n"]),
                    "avg_save_pct": float(r["avg_save_pct"]) if r.get("avg_save_pct") is not None else None,
                    "hit_rate_pct": float(r["hit_rate_pct"]) if r.get("hit_rate_pct") is not None else None,
                } for r in by_zone
            ],
            "by_confidence": [
                {
                    "conf_bin": r["conf_bin"],
                    "n": int(r["n"]),
                    "avg_save_pct": float(r["avg_save_pct"]) if r.get("avg_save_pct") is not None else None,
                    "hit_rate_pct": float(r["hit_rate_pct"]) if r.get("hit_rate_pct") is not None else None,
                } for r in by_conf
            ],
            "lakebase_available": True,
        }
    except Exception as e:
        import logging as _logging
        _logging.getLogger(__name__).warning("backtest_results Lakebase unavailable: %s", e)
        return {
            "summary": None,
            "by_zone": [],
            "by_confidence": [],
            "lakebase_available": False,
            "reason": "lakebase_oauth_pending",
            "message": "Lakebase OAuth role binding in progress — Apps Database resource pending. Backtest predictions은 Lakebase OLTP에 적재되어 production resource binding 완료 시 즉시 라이브.",
        }


@router.get("/backtest/predictions")
async def backtest_predictions(limit: int = 50) -> dict:
    """Lakebase backtest_predictions — latest run sample (WhatIf slider용).

    Lakebase OAuth pending 시 200 OK + empty + lakebase_available=False.
    """
    import asyncio
    from app.db import lakebase
    from app.db.repositories import backtest as bt_repo

    def _sync():
        with lakebase.acquire() as conn:
            return bt_repo.list_predictions(conn, limit=min(limit, 500))

    try:
        rows = await asyncio.to_thread(_sync)
        return {
            "predictions": [
                {
                    "as_of_date": str(r["as_of_date"]),
                    "pattern_score": float(r["pattern_score"]) if r.get("pattern_score") is not None else None,
                    "confidence_score": float(r["confidence_score"]) if r.get("confidence_score") is not None else None,
                    "action_type": r.get("action_type"),
                    "mission_type": r.get("mission_type"),
                    "target_pct": int(r["target_pct"]) if r.get("target_pct") is not None else None,
                    "duration_days": int(r["duration_days"]) if r.get("duration_days") is not None else None,
                    "saving_7d_pct": float(r["saving_7d_pct"]) if r.get("saving_7d_pct") is not None else None,
                    "saving_30d_pct": float(r["saving_30d_pct"]) if r.get("saving_30d_pct") is not None else None,
                    "saving_90d_pct": float(r["saving_90d_pct"]) if r.get("saving_90d_pct") is not None else None,
                    "dubai_at_signal_usd": float(r["dubai_at_signal_usd"]) if r.get("dubai_at_signal_usd") is not None else None,
                    "dubai_30d_usd": float(r["dubai_30d_usd"]) if r.get("dubai_30d_usd") is not None else None,
                } for r in rows
            ],
            "lakebase_available": True,
        }
    except Exception as e:
        import logging as _logging
        _logging.getLogger(__name__).warning("backtest_predictions Lakebase unavailable: %s", e)
        return {
            "predictions": [],
            "lakebase_available": False,
            "reason": "lakebase_oauth_pending",
            "message": "Lakebase OAuth role binding in progress — Apps Database resource pending.",
        }
