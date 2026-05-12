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
# /api/backtest/results — v6 LLM Mission Plan Agent backtest summary
# ────────────────────────────────────────────────────────────────────────
@router.get("/backtest/results")
async def backtest_results() -> dict:
    """gold.llm_backtest_predictions v6 summary."""
    try:
        # latest v6 run_id
        latest_run = _q("""
            SELECT run_id FROM crude_compass.gold.llm_backtest_predictions
            WHERE run_id LIKE 'llm_v6_%'
            ORDER BY computed_at DESC LIMIT 1
        """)
        if not latest_run:
            return {"summary": None, "by_zone": [], "by_confidence": []}
        run_id = latest_run[0][0]

        # Overall summary
        summary = _q(f"""
            SELECT COUNT(*) AS n_total,
                   SUM(CASE WHEN action_type='new_mission' THEN 1 ELSE 0 END) AS n_active,
                   SUM(CASE WHEN mission_type='HEDGE' AND action_type='new_mission' THEN 1 ELSE 0 END) AS n_hedge,
                   SUM(CASE WHEN mission_type='OPPORTUNITY' AND action_type='new_mission' THEN 1 ELSE 0 END) AS n_opp,
                   ROUND(AVG(CASE WHEN action_type='new_mission' THEN cost_saving_30d END), 3) AS avg_save,
                   ROUND(SUM(CASE WHEN action_type='new_mission' AND cost_saving_30d > 0 THEN 1 ELSE 0 END)*100.0/
                         NULLIF(SUM(CASE WHEN action_type='new_mission' THEN 1 ELSE 0 END), 0), 1) AS hit
            FROM crude_compass.gold.llm_backtest_predictions
            WHERE run_id = '{run_id}'
        """)
        s = summary[0] if summary else None
        summary_dict = {
            "run_id": run_id,
            "n_total": int(s[0]) if s else 0,
            "n_active": int(s[1]) if s else 0,
            "n_hedge": int(s[2]) if s else 0,
            "n_opp": int(s[3]) if s else 0,
            "avg_save_pct": float(s[4]) if s and s[4] else None,
            "hit_rate_pct": float(s[5]) if s and s[5] else None,
        } if s else None

        # By zone
        by_zone = _q(f"""
            SELECT CASE WHEN pattern_score >= 70 THEN 'HIGH'
                        WHEN pattern_score <= 30 THEN 'LOW' ELSE 'MID' END AS zone,
                   mission_type, COUNT(*) AS n,
                   ROUND(AVG(cost_saving_30d), 3) AS save,
                   ROUND(SUM(CASE WHEN cost_saving_30d > 0 THEN 1 ELSE 0 END)*100.0/COUNT(*), 1) AS hit
            FROM crude_compass.gold.llm_backtest_predictions
            WHERE run_id = '{run_id}' AND action_type='new_mission'
            GROUP BY zone, mission_type ORDER BY zone
        """)

        # By confidence
        by_conf = _q(f"""
            SELECT CASE WHEN confidence_score >= 90 THEN '90-100'
                        WHEN confidence_score >= 80 THEN '80-89'
                        WHEN confidence_score >= 70 THEN '70-79'
                        ELSE '<70' END AS conf_bin,
                   COUNT(*) AS n,
                   ROUND(AVG(cost_saving_30d), 3) AS save,
                   ROUND(SUM(CASE WHEN cost_saving_30d > 0 THEN 1 ELSE 0 END)*100.0/COUNT(*), 1) AS hit
            FROM crude_compass.gold.llm_backtest_predictions
            WHERE run_id = '{run_id}' AND action_type='new_mission'
            GROUP BY conf_bin ORDER BY MAX(confidence_score) DESC
        """)

        return {
            "summary": summary_dict,
            "by_zone": [
                {"zone": r[0], "mission_type": r[1], "n": int(r[2]),
                 "avg_save_pct": float(r[3]) if r[3] else None,
                 "hit_rate_pct": float(r[4]) if r[4] else None}
                for r in by_zone
            ],
            "by_confidence": [
                {"conf_bin": r[0], "n": int(r[1]),
                 "avg_save_pct": float(r[2]) if r[2] else None,
                 "hit_rate_pct": float(r[3]) if r[3] else None}
                for r in by_conf
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": "DATA_FETCH_FAILED", "message": str(e)})


@router.get("/backtest/predictions")
async def backtest_predictions(limit: int = 50) -> dict:
    """Sample predictions (latest v6)."""
    try:
        latest_run = _q("""
            SELECT run_id FROM crude_compass.gold.llm_backtest_predictions
            WHERE run_id LIKE 'llm_v6_%'
            ORDER BY computed_at DESC LIMIT 1
        """)
        if not latest_run:
            return {"predictions": []}
        run_id = latest_run[0][0]

        rows = _q(f"""
            SELECT as_of_date, pattern_score, confidence_score,
                   action_type, mission_type, target_pct, duration_days,
                   ROUND(cost_saving_7d, 3), ROUND(cost_saving_30d, 3),
                   ROUND(cost_saving_90d, 3),
                   dubai_at_signal, dubai_30d
            FROM crude_compass.gold.llm_backtest_predictions
            WHERE run_id = '{run_id}' AND action_type = 'new_mission'
            ORDER BY as_of_date DESC LIMIT {min(limit, 500)}
        """)
        return {
            "predictions": [
                {
                    "as_of_date": str(r[0]),
                    "pattern_score": float(r[1]) if r[1] else None,
                    "confidence_score": float(r[2]) if r[2] else None,
                    "action_type": r[3], "mission_type": r[4],
                    "target_pct": int(r[5]) if r[5] else None,
                    "duration_days": int(r[6]) if r[6] else None,
                    "saving_7d_pct": float(r[7]) if r[7] else None,
                    "saving_30d_pct": float(r[8]) if r[8] else None,
                    "saving_90d_pct": float(r[9]) if r[9] else None,
                    "dubai_at_signal_usd": float(r[10]) if r[10] else None,
                    "dubai_30d_usd": float(r[11]) if r[11] else None,
                } for r in rows
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": "DATA_FETCH_FAILED", "message": str(e)})
