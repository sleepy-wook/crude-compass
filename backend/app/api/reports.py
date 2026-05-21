"""Reports REST API — event-driven AI report inbox (2026-05-21).

Endpoints:
  GET  /api/reports/inbox            → status='pending' (max 10)
  GET  /api/reports/{id}             → 단건 + thread (parent_id chain)
  GET  /api/reports/archive          → status='kept' | 'dropped' | 'ai_dropped'
  POST /api/reports/{id}/keep        → status='kept', by='manager'
  POST /api/reports/{id}/drop        → status='dropped', by='manager'
  POST /api/reports/{id}/investigate → 추가 조사 (Phase 9 본격; Phase 2 stub)

Pulse broadcast: keep/drop 시 agent_activity_events에 manager:report_kept|dropped 1건.
"""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query

from app.db.lakebase import acquire
from app.db.repositories import agent_activity, daily_reports as daily_repo, reports as reports_repo
from app.schemas.report import (
    DailyReport,
    Report,
    ReportStatus,
    ReportThread,
    StatusActor,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reports", tags=["reports"])


# ────────────────────────────────────────────────────────────────────
# READ — inbox / archive / detail
# ────────────────────────────────────────────────────────────────────
@router.get("/inbox")
async def get_inbox(limit: int = Query(default=10, ge=1, le=50)) -> dict[str, Any]:
    """pending status 보고서 inbox.

    UI Decision Room이 polling/WS로 refresh. 최대 10건 (실제로 5건 이하 유지 기대).
    """
    try:
        with acquire() as conn:
            items = reports_repo.list_pending(conn, limit=limit)
        return {
            "count": len(items),
            "items": [_serialize_report(r) for r in items],
        }
    except Exception as e:
        logger.warning("get_inbox failed: %s", e)
        return {"count": 0, "items": []}


@router.get("/archive")
async def get_archive(
    status: str = Query(default="archived", pattern="^(kept|dropped|ai_dropped|archived)$"),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    """archive view — kept | dropped | ai_dropped 중 하나."""
    try:
        status_enum = ReportStatus(status)
    except ValueError:
        raise HTTPException(status_code=400, detail={"code": "INVALID_STATUS", "message": status})

    try:
        with acquire() as conn:
            items = reports_repo.list_by_status(conn, status_enum, limit=limit)
        return {
            "status": status,
            "count": len(items),
            "items": [_serialize_report(r) for r in items],
        }
    except Exception as e:
        logger.warning("get_archive failed: %s", e)
        return {"status": status, "count": 0, "items": []}


@router.get("/{report_id}")
async def get_report(report_id: UUID = Path(...)) -> dict[str, Any]:
    """단건 + thread (recursive parent_id 따라 root + 모든 자손).

    404: report_id 없음.
    """
    try:
        with acquire() as conn:
            thread = reports_repo.get_with_thread(conn, report_id)
        if thread is None:
            raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "report_id": str(report_id)})
        return {
            "root": _serialize_report(thread.root),
            "thread": [_serialize_report(r) for r in thread.thread],
            "thread_length": len(thread.thread),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("get_report failed (%s): %s", report_id, e)
        raise HTTPException(status_code=500, detail={"code": "FETCH_FAILED", "message": str(e)})


# ────────────────────────────────────────────────────────────────────
# WRITE — keep / drop / investigate
# ────────────────────────────────────────────────────────────────────
@router.post("/{report_id}/keep")
async def keep_report(report_id: UUID = Path(...)) -> dict[str, Any]:
    """status='kept', by='manager'. pulse broadcast manager:report_kept."""
    return _update_status_with_pulse(
        report_id, ReportStatus.KEPT, "report_kept", "매니저가 보관"
    )


@router.post("/{report_id}/drop")
async def drop_report(report_id: UUID = Path(...)) -> dict[str, Any]:
    """status='dropped', by='manager'."""
    return _update_status_with_pulse(
        report_id, ReportStatus.DROPPED, "report_dropped", "매니저가 drop"
    )


@router.post("/{report_id}/investigate")
async def investigate_report(report_id: UUID = Path(...)) -> dict[str, Any]:
    """추가 조사 — Agent Bricks Supervisor 호출.

    Flow:
      1. 선택된 report context 추출
      2. Supervisor에게 "이 보고서 cross-check + 추가 분석 1단락" 요청
      3. Supervisor 응답을 새 report row (parent_id=원본)으로 INSERT — thread 자식
      4. tools_used를 reasoning.agent_bricks_tools에 저장
      5. activity emit + WS broadcast 트리거

    Supervisor 미설정 / 실패 시 → 안전 fallback (활동 이벤트만 기록, no new row).
    """
    from app.schemas.report import ReportCreate
    from app.services.supervisor import (
        SupervisorNotConfigured,
        query_supervisor,
    )

    try:
        with acquire() as conn:
            existing = reports_repo.get_by_id(conn, report_id)
            if existing is None:
                raise HTTPException(status_code=404, detail={"code": "NOT_FOUND"})
        # Supervisor 호출 (lakebase connection 밖에서)
        trigger_type_value = (
            existing.trigger_type.value if hasattr(existing.trigger_type, "value")
            else existing.trigger_type
        )
        rec_value = (
            existing.recommendation.value if hasattr(existing.recommendation, "value")
            else existing.recommendation
        )
        supervisor_q = (
            f"다음 트리거 보고서를 cross-check 해줘:\n"
            f"제목: {existing.headline}\n"
            f"요약: {existing.summary}\n"
            f"트리거: {trigger_type_value}\n"
            f"권고: {rec_value or '없음'}\n\n"
            f"Genie로 시장 데이터 추가 조회, Knowledge Assistant로 OPEC 문서 cross-reference, "
            f"권고 sub-agent로 종합 의견 산출.\n\n"
            f"[출력 규칙 — 반드시 준수]\n"
            f"- '확인하겠습니다', '조회하겠습니다', '분석하겠습니다' 같은 작업 과정/서두를 절대 쓰지 말 것.\n"
            f"- 첫 문장부터 곧바로 분석 결론으로 시작 (결론 → 근거 순서).\n"
            f"- 완성된 보고서 형태의 한국어 자연어 1-2단락 (300자 이내).\n"
            f"- 한국 정유사 구매 매니저 대상. 변수명·점수 raw·인용 각주 노출 X."
        )
        try:
            sup = await query_supervisor(supervisor_q)
        except SupervisorNotConfigured:
            with acquire() as conn:
                agent_activity.insert_event_autocommit(
                    conn, mission_id=None, actor="manager", action="report_investigate_requested",
                    result_preview=f"추가 조사 요청 — Supervisor 미설정: {existing.headline[:80]}",
                    metadata={"report_id": str(report_id), "supervisor": "not_configured"},
                )
            return {
                "ok": False,
                "status": "supervisor_not_configured",
                "note": "SUPERVISOR_ENDPOINT_NAME env 미설정 — admin 설정 필요",
            }

        # Supervisor 응답을 thread 자식 report로 INSERT
        with acquire() as conn:
            # 원본의 trigger_type 그대로 (thread 일관성)
            try:
                from app.schemas.report import TriggerType
                trig_enum = TriggerType(trigger_type_value)
            except Exception:
                trig_enum = existing.trigger_type  # fallback

            child_payload = ReportCreate(
                parent_id=report_id,
                trigger_type=trig_enum,
                trigger_meta={
                    "fingerprint": f"investigate:{report_id}:{int(__import__('time').time())}",
                    "investigate": True,
                    "parent_headline": existing.headline,
                },
                headline=f"[추가 조사] {existing.headline[:100]}",
                summary=(sup.answer or "")[:800],
                reasoning={
                    # logic은 summary와 중복이므로 저장 안 함 (sub-agent trace만 유지)
                    "agent_bricks_tools": [
                        {"name": t.name, "preview": (t.result_preview or "")[:120]}
                        for t in sup.tools_used
                    ],
                },
                recommendation=existing.recommendation if hasattr(existing.recommendation, "value") else None,
                related_signals=list(existing.related_signals),
            )
            new_rid = reports_repo.insert_report(conn, child_payload)
            conn.commit()

            agent_activity.insert_event_autocommit(
                conn, mission_id=None, actor="supervisor", action="report_investigated",
                result_preview=(
                    f"Supervisor cross-check 완료 — {len(sup.tools_used)} sub-agent 호출: "
                    f"{', '.join(t.name for t in sup.tools_used) or '없음'}"
                ),
                metadata={
                    "parent_report_id": str(report_id),
                    "child_report_id": str(new_rid),
                    "tools_used": [t.name for t in sup.tools_used],
                },
            )

        return {
            "ok": True,
            "status": "completed",
            "new_report_id": str(new_rid),
            "tools_used": [t.name for t in sup.tools_used],
            "answer": sup.answer[:400],
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.warning("investigate failed (%s): %s\n%s", report_id, e, traceback.format_exc())
        raise HTTPException(status_code=500, detail={"code": "INVESTIGATE_FAILED", "message": str(e)})


# ────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────
def _update_status_with_pulse(
    report_id: UUID,
    new_status: ReportStatus,
    action_name: str,
    pulse_text: str,
) -> dict[str, Any]:
    """update_status + agent_activity emit. 공통 helper."""
    try:
        with acquire() as conn:
            existing = reports_repo.get_by_id(conn, report_id)
            if existing is None:
                raise HTTPException(status_code=404, detail={"code": "NOT_FOUND"})
            if existing.status != ReportStatus.PENDING.value:
                # 이미 처리된 보고서 — 무시 (idempotent 응답)
                return {
                    "ok": True,
                    "no_change": True,
                    "current_status": existing.status,
                    "report_id": str(report_id),
                }
            ok = reports_repo.update_status(conn, report_id, new_status, StatusActor.MANAGER)
            if not ok:
                raise HTTPException(status_code=500, detail={"code": "UPDATE_FAILED"})
            conn.commit()

            agent_activity.insert_event_autocommit(
                conn, mission_id=None, actor="manager", action=action_name,
                result_preview=f"{pulse_text} — {existing.headline[:80]}",
                metadata={"report_id": str(report_id), "new_status": new_status.value},
            )

        return {
            "ok": True,
            "report_id": str(report_id),
            "new_status": new_status.value,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("status update failed (%s → %s): %s", report_id, new_status, e)
        raise HTTPException(status_code=500, detail={"code": "STATUS_UPDATE_FAILED", "message": str(e)})


def _serialize_daily(d: DailyReport) -> dict[str, Any]:
    """DailyReport → frontend dict. JSONB/UUID[] → JSON-safe."""
    return {
        "daily_id": str(d.daily_id),
        "report_date": d.report_date.isoformat() if d.report_date else None,
        "prev_daily_id": str(d.prev_daily_id) if d.prev_daily_id else None,
        "kept_report_ids": [str(r) for r in d.kept_report_ids],
        "kept_count": d.kept_count,
        "kept_summary": d.kept_summary,
        "prev_daily_summary": d.prev_daily_summary,
        "market_context": d.market_context,
        "ratio_suggestion": d.ratio_suggestion,
        "reasoning": d.reasoning,
        "confidence": d.confidence,
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }


def _serialize_report(r: Report) -> dict[str, Any]:
    """Report Pydantic → frontend-friendly dict. datetime은 ISO."""
    return {
        "report_id": str(r.report_id),
        "parent_id": str(r.parent_id) if r.parent_id else None,
        "trigger_type": r.trigger_type if isinstance(r.trigger_type, str) else r.trigger_type.value,
        "trigger_meta": r.trigger_meta,
        "status": r.status if isinstance(r.status, str) else r.status.value,
        "status_changed_at": r.status_changed_at.isoformat() if r.status_changed_at else None,
        "status_changed_by": (
            r.status_changed_by if isinstance(r.status_changed_by, str)
            else (r.status_changed_by.value if r.status_changed_by else None)
        ),
        "headline": r.headline,
        "summary": r.summary,
        "reasoning": r.reasoning,
        "recommendation": (
            r.recommendation if isinstance(r.recommendation, str)
            else (r.recommendation.value if r.recommendation else None)
        ),
        "related_signals": r.related_signals,
        "revisits_id": str(r.revisits_id) if r.revisits_id else None,
        "ai_drop_reason": r.ai_drop_reason,
        "version": r.version,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }
