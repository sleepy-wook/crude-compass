"""Jobs API — Databricks Jobs SDK wrapper.

GET /api/jobs/runs/today  → 오늘 24h 내 모든 crude-compass job run summary (Daily Loop dial 용)
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

# crude-compass job name → display label
CRUDE_COMPASS_JOB_PREFIXES = ["[dev hyeongwook_lee] crude-compass-"]
JOB_LABEL: dict[str, str] = {
    "gdelt-15min": "GDELT",
    "price-pipeline": "Price",
    "oil-prices-daily": "OilPrice Daily",
    "ecos-daily": "ECOS",
    "eia-weekly": "EIA",
    "opec-momr": "OPEC MOMR",
    "daily-curation": "Curation",
    "daily-risk-backfill": "Risk Backfill",
    "backtest-seed": "Backtest Seed",
    "backtest-compute": "Backtest Compute",
    "backtest-llm": "Backtest LLM",
}


def _normalize_job_name(full_name: str) -> str:
    """[dev hyeongwook_lee] crude-compass-gdelt-15min-dev → gdelt-15min"""
    for prefix in CRUDE_COMPASS_JOB_PREFIXES:
        if full_name.startswith(prefix):
            stripped = full_name[len(prefix):]
            if stripped.endswith("-dev"):
                stripped = stripped[:-4]
            return stripped
    return full_name


@router.get("/runs/today")
async def get_runs_today() -> dict[str, Any]:
    """오늘 24h 내 모든 crude-compass job run summary.

    Response:
      {
        "runs": [{job_name, label, start_time, end_time, result_state, ...}],
        "summary": {job_name: {"count": N, "success": N, "fail": N}}
      }
    """
    try:
        from databricks.sdk import WorkspaceClient

        w = WorkspaceClient()
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        since_ms = int(since.timestamp() * 1000)

        # SDK iterator — completed runs only
        runs: list[dict[str, Any]] = []
        for run in w.jobs.list_runs(
            completed_only=True,
            start_time_from=since_ms,
            limit=200,
        ):
            full_name = (run.run_name or "").strip()
            if "crude-compass" not in full_name:
                continue
            job_key = _normalize_job_name(full_name)
            runs.append({
                "job_name": job_key,
                "label": JOB_LABEL.get(job_key, job_key),
                "run_id": run.run_id,
                "start_time": run.start_time,
                "end_time": run.end_time,
                "result_state": (run.state.result_state.value if run.state and run.state.result_state else None),
                "duration_ms": (run.end_time - run.start_time) if (run.start_time and run.end_time) else None,
            })

        # Aggregate
        summary: dict[str, dict[str, int]] = {}
        for r in runs:
            key = r["job_name"]
            if key not in summary:
                summary[key] = {"count": 0, "success": 0, "fail": 0}
            summary[key]["count"] += 1
            if r["result_state"] == "SUCCESS":
                summary[key]["success"] += 1
            elif r["result_state"] in ("FAILED", "TIMEDOUT", "CANCELED"):
                summary[key]["fail"] += 1

        return {"runs": runs, "summary": summary}
    except Exception as e:
        logger.warning("jobs runs today failed: %s", e)
        return {"runs": [], "summary": {}}
