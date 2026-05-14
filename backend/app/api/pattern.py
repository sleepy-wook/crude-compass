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
    """Pattern Score history N일."""
    try:
        rows = _q(f"""
            SELECT date, pattern_score, mission_type, bullish_score, bearish_score
            FROM crude_compass.gold.daily_risk_score
            WHERE date >= CURRENT_DATE() - INTERVAL {min(days, 365)} DAYS
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
# /api/backtest/* — LLM Mission Plan Agent backtest from Lakebase
# (AI-generated content 정석: Lakebase OLTP)
# ────────────────────────────────────────────────────────────────────────
@router.get("/backtest/results")
async def backtest_results() -> dict:
    """Lakebase backtest_predictions latest run summary."""
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
            return {"summary": None, "by_zone": [], "by_confidence": []}
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
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": "DATA_FETCH_FAILED", "message": str(e)})


@router.get("/backtest/predictions")
async def backtest_predictions(limit: int = 50) -> dict:
    """Lakebase backtest_predictions — latest run sample (WhatIf slider용)."""
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
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": "DATA_FETCH_FAILED", "message": str(e)})
