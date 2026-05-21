"""Admin endpoints — manual job trigger + curation freshness check.

Demo 시연 시 daily_curation job을 수동으로 trigger할 때 사용.
Apps Service Principal에 Job MANAGE 권한이 필요합니다.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

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


@router.post("/setup-agent-activity")
async def setup_agent_activity_events() -> dict[str, Any]:
    """One-off: agent_activity_events table 생성 + 권한 grant + 기존 mission backfill.

    Apps SP가 owner 되어 이후 INSERT/SELECT 자유. user (workspace admin)는 missions
    table owner지만 별도 admin endpoint 없이 자동 setup 위한 1회 path.

    실패할 수 있는 statement (e.g., ALTER, GRANT)는 step-level try/except로 isolation.
    멱등 (모두 NOT EXISTS 가드).
    """
    sql_path = Path(__file__).resolve().parent.parent.parent.parent / "scripts" / "setup_agent_activity_events.sql"
    if not sql_path.exists():
        # repo layout 다르면 fallback
        for candidate in (
            Path("/app/python/source_code/scripts/setup_agent_activity_events.sql"),
            Path.cwd() / "scripts" / "setup_agent_activity_events.sql",
        ):
            if candidate.exists():
                sql_path = candidate
                break
    if not sql_path.exists():
        raise HTTPException(
            status_code=500,
            detail={"code": "SQL_FILE_NOT_FOUND", "tried": str(sql_path)},
        )

    sql_text = sql_path.read_text(encoding="utf-8")
    # Strip line comments + split by ;
    lines = [ln for ln in sql_text.splitlines() if not ln.strip().startswith("--")]
    clean = "\n".join(lines)
    stmts = [s.strip() for s in clean.split(";") if s.strip()]

    results: list[dict[str, Any]] = []
    try:
        import asyncio
        from app.db.lakebase import acquire

        def _run() -> list[dict[str, Any]]:
            out: list[dict[str, Any]] = []
            with acquire() as conn:
                for i, stmt in enumerate(stmts, 1):
                    preview = stmt.splitlines()[0][:80] if stmt else ""
                    item: dict[str, Any] = {"idx": i, "preview": preview}
                    try:
                        with conn.cursor() as cur:
                            cur.execute(stmt)
                            if stmt.lstrip().upper().startswith("SELECT"):
                                rows = cur.fetchall()
                                cols = [d.name for d in (cur.description or [])]
                                item["select_result"] = [
                                    dict(zip(cols, [str(v) for v in r])) for r in rows[:20]
                                ]
                            else:
                                item["rowcount"] = cur.rowcount
                        conn.commit()
                        item["status"] = "ok"
                    except Exception as e:
                        item["status"] = "fail"
                        item["error"] = str(e)
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                    out.append(item)
            return out

        results = await asyncio.to_thread(_run)
    except Exception as e:
        logger.warning("setup-agent-activity outer fail: %s", e)
        raise HTTPException(status_code=500, detail={"code": "SETUP_FAIL", "error": str(e)})

    ok_count = sum(1 for r in results if r.get("status") == "ok")
    return {
        "total_statements": len(results),
        "ok": ok_count,
        "fail": len(results) - ok_count,
        "results": results,
    }


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


@router.post("/reports/trigger-now")
async def trigger_now(
    force: bool = False,
    trigger_type: str | None = None,
) -> dict[str, Any]:
    """매뉴얼 trigger — detector 돌려서 잡힌 거 LLM emit + Lakebase insert.

    Query:
      force=true: 0건이면 dummy event 1개 합성 (UI smoke).
      trigger_type: None (전체) | 'gdelt_signal' | 'price_spike' | 'pattern_drift'.
        notebook이 자기 trigger만 emit할 때 사용.

    notebook (15분 / daily 06:30 cron) + UI 둘 다 호출.
    """
    from app.db.lakebase import acquire
    from app.db.repositories import agent_activity
    from app.db.repositories import reports as reports_repo
    from app.services.report_generator import generate_report, last_llm_error
    from app.services.trigger_detector import (
        TriggerEvent,
        detect_all,
        detect_gdelt_signal,
        detect_pattern_drift,
        detect_price_spike,
    )
    from app.schemas.report import TriggerType
    from datetime import datetime, timezone

    # 선택적 detector 실행
    events: list[TriggerEvent] = []
    if trigger_type is None:
        events = detect_all()
    elif trigger_type == "gdelt_signal":
        events = detect_gdelt_signal()
    elif trigger_type == "price_spike":
        spike = detect_price_spike()
        if spike:
            events.append(spike)
    elif trigger_type == "pattern_drift":
        drift = detect_pattern_drift()
        if drift:
            events.append(drift)
    else:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_TRIGGER_TYPE", "message": trigger_type},
        )

    if not events and force:
        # 합성 dummy event — UI smoke용. 실제 trigger 안 잡혀도 1건 만들어줌.
        dummy_type = TriggerType(trigger_type) if trigger_type else TriggerType.PATTERN_DRIFT
        events.append(
            TriggerEvent(
                trigger_type=dummy_type,
                fingerprint=f"manual:{datetime.now(timezone.utc).isoformat()}",
                headline_hint=f"수동 trigger ({dummy_type.value}) — smoke 목적",
                meta={"forced": True, "note": "trigger-now endpoint forced=true"},
            )
        )

    results: list[dict[str, Any]] = []
    for ev in events:
        try:
            report = generate_report(ev)
            if report is None:
                results.append({
                    "fingerprint": ev.fingerprint,
                    "ok": False,
                    "error": last_llm_error(),
                })
                continue
            with acquire() as conn:
                rid = reports_repo.insert_report(conn, report)
                conn.commit()
                agent_activity.insert_event_autocommit(
                    conn, mission_id=None, actor="report_generator", action="report_created",
                    result_preview=f"{report.headline[:120]}",
                    metadata={
                        "report_id": str(rid),
                        "trigger_type": ev.trigger_type.value,
                        "fingerprint": ev.fingerprint,
                    },
                )
            # Slack 알림 — 보고서 발행 시 즉시 push (실패해도 report 생성엔 영향 X)
            try:
                from app.services.slack_notify import get_notifier
                await get_notifier().post_report_card(report, report_id=str(rid))
            except Exception as se:
                logger.warning("slack report card push failed: %s", se)
            results.append({
                "fingerprint": ev.fingerprint,
                "ok": True,
                "report_id": str(rid),
                "headline": report.headline,
                "recommendation": report.recommendation.value if report.recommendation else None,
            })
        except Exception as e:
            logger.warning("trigger-now per-event failed: %s", e)
            results.append({"fingerprint": ev.fingerprint, "ok": False, "error": str(e)})

    return {
        "events_detected": len(events),
        "results": results,
    }


@router.post("/daily-report/generate-now")
async def generate_daily_now(
    target_date: str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """매뉴얼 daily_report 생성 — 06:30 cron 흐름을 그대로 실행.

    Query:
      target_date: ISO YYYY-MM-DD. 생략시 KST 오늘.
      overwrite: 기존 row 있으면 삭제 후 새로 생성. default False (skip).
    """
    from datetime import date as date_type
    from app.services.daily_report import generate_daily_report, last_llm_error

    parsed_date: date_type | None = None
    if target_date:
        try:
            parsed_date = date_type.fromisoformat(target_date)
        except ValueError:
            raise HTTPException(status_code=400, detail={"code": "INVALID_DATE", "message": target_date})

    daily_id = generate_daily_report(target_date=parsed_date, overwrite=overwrite)
    if daily_id is None:
        return {
            "ok": False,
            "error": last_llm_error() or "unknown",
            "note": "이미 존재할 경우 overwrite=true로 재시도",
        }
    # Slack 발송 — 일일 보고서 전용 채널 (실패해도 생성엔 영향 X)
    try:
        from datetime import datetime as _dt, timedelta as _td, timezone as _tz
        from app.db.lakebase import acquire
        from app.db.repositories import daily_reports as daily_repo
        from app.services.slack_notify import get_notifier
        kst_today = (_dt.now(_tz.utc) + _td(hours=9)).date()
        target = parsed_date or kst_today
        with acquire() as conn:
            daily = daily_repo.get_for_date(conn, target)
        if daily:
            await get_notifier().post_daily_card(daily)
    except Exception as se:
        logger.warning("slack daily card push failed: %s", se)
    return {"ok": True, "daily_id": str(daily_id)}


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
