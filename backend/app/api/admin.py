"""Admin endpoints — manual job trigger + curation freshness check.

Demo 시연 시 daily_curation job을 수동으로 trigger할 때 사용.
Apps Service Principal에 Job MANAGE 권한이 필요합니다.
"""
from __future__ import annotations

import logging
import os

from databricks.sdk import WorkspaceClient
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])


def _client() -> WorkspaceClient:
    profile = os.getenv("DATABRICKS_CONFIG_PROFILE", "crude-compass")
    try:
        return WorkspaceClient(profile=profile)
    except Exception:
        return WorkspaceClient()


@router.post("/refresh-curation")
async def refresh_curation() -> dict:
    """Daily curation job을 수동으로 trigger.

    env `DAILY_CURATION_JOB_ID` 필수.
    Service Principal에 Job MANAGE 권한 필요.
    """
    job_id_str = os.getenv("DAILY_CURATION_JOB_ID")
    if not job_id_str:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "JOB_NOT_CONFIGURED",
                "message": "DAILY_CURATION_JOB_ID 환경변수가 설정되지 않았습니다.",
            },
        )
    try:
        job_id = int(job_id_str)
    except ValueError:
        raise HTTPException(
            status_code=500,
            detail={"code": "JOB_ID_INVALID", "message": "DAILY_CURATION_JOB_ID는 숫자여야 합니다."},
        )
    try:
        w = _client()
        run = w.jobs.run_now(job_id=job_id)
        return {
            "ok": True,
            "run_id": run.run_id,
            "job_id": job_id,
            "message": "데이터 갱신을 시작했습니다. 완료까지 5-10분 소요됩니다.",
        }
    except Exception as e:
        logger.error("refresh-curation failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail={"code": "JOB_TRIGGER_FAILED", "message": str(e)},
        )


@router.post("/missions/clear-active")
async def clear_active_missions() -> dict:
    """기존 active/proposed mission을 hard delete (decisions/pivot_history cascade).

    Demo 시나리오 reset 용도. mission_plan prompt가 갱신됐을 때
    이전에 persisted된 jargon-laden mission을 정리하고 새로 생성 가능.
    """
    from app.db.lakebase import acquire

    try:
        with acquire() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM missions
                    WHERE status IN ('proposed','active','on_track','at_risk')
                    RETURNING mission_id
                    """
                )
                deleted = cur.fetchall()
                conn.commit()
        return {
            "ok": True,
            "deleted_count": len(deleted),
            "deleted_ids": [str(row[0]) for row in deleted],
            "message": f"{len(deleted)}건의 mission을 삭제했습니다. (CASCADE: decisions, pivot_history 자동 정리)",
        }
    except Exception as e:
        logger.error("clear-active-missions failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail={"code": "DB_OP_FAILED", "message": str(e)},
        )


@router.get("/curation-status")
async def curation_status() -> dict:
    """gold.daily_risk_score latest date 반환. Frontend가 stale 여부 판단용."""
    from app.api.pattern import _q

    try:
        rows = _q(
            """
            SELECT MAX(date) FROM crude_compass.gold.daily_risk_score
            """
        )
        latest = str(rows[0][0]) if rows and rows[0][0] else None
        return {"latest_date": latest}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"code": "DATA_FETCH_FAILED", "message": str(e)},
        )
