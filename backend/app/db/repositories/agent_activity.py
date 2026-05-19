"""Agent activity event persistence — Agent Bricks orchestration timeline.

Schema (lakebase.py migrate_d4):
  agent_activity_events (id, mission_id, occurred_at, actor, action, result_preview, metadata)

Write paths (시나리오 §9 Agent Bricks workflow):
- missions.py insert      → supervisor:case_opened + weighted_signal_uc:score_computed
                            + mission_plan_fma:draft_generated
- decisions.py insert     → manager:confirmed | modified | pivoted | rejected
- supervisor.py query     → <each tool>:invoked + supervisor:synthesized
- reactive trigger        → reactive:trigger_fired

Read path:
- /api/missions/:id/activity → list_for_mission()

actor enum (display label mapping은 frontend):
  supervisor / genie / knowledge_assistant /
  mission_plan_fma / mission_plan_uc / weighted_signal_uc /
  manager / reactive / system
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)


# Best-effort: write 실패해도 main flow 막지 않음. logger.warning만.
def insert_event(
    conn: psycopg.Connection,
    *,
    mission_id: UUID | None,
    actor: str,
    action: str,
    result_preview: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> bool:
    """Insert single activity event. exception swallow → False return + full traceback log.

    Caller가 conn.commit()을 별도 처리하거나, transaction 안에서 호출.
    여기서 commit X (caller가 main flow commit과 함께 묶을 수 있도록).
    """
    import traceback
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO agent_activity_events
                    (mission_id, actor, action, result_preview, metadata)
                VALUES
                    (%s, %s, %s, %s, %s::jsonb)
                """,
                (
                    mission_id,
                    actor,
                    action,
                    (result_preview or None),
                    (json.dumps(metadata) if metadata else None),
                ),
            )
        return True
    except Exception as e:
        logger.warning(
            "agent_activity insert_event FAIL (actor=%s action=%s): %s\n%s",
            actor, action, e, traceback.format_exc(),
        )
        return False


def insert_event_autocommit(
    conn: psycopg.Connection,
    *,
    mission_id: UUID | None,
    actor: str,
    action: str,
    result_preview: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> bool:
    """Insert + commit. Supervisor 호출처럼 별도 transaction에서 단일 event 기록할 때."""
    ok = insert_event(
        conn, mission_id=mission_id, actor=actor, action=action,
        result_preview=result_preview, metadata=metadata,
    )
    if ok:
        try:
            conn.commit()
        except Exception as e:
            logger.warning("agent_activity commit failed: %s", e)
            return False
    return ok


def list_for_mission(
    conn: psycopg.Connection,
    mission_id: UUID,
    *,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """mission 1건의 활동 이력 — occurred_at desc.

    Returns list of dict:
      { id, mission_id, occurred_at (datetime), actor, action, result_preview, metadata }
    """
    try:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id, mission_id, occurred_at, actor, action, result_preview, metadata
                  FROM agent_activity_events
                 WHERE mission_id = %s
                 ORDER BY occurred_at DESC, id DESC
                 LIMIT %s
                """,
                (mission_id, limit),
            )
            rows = cur.fetchall()
        return [_serialize(r) for r in rows]
    except Exception as e:
        logger.warning("agent_activity list_for_mission failed: %s", e)
        return []


def _serialize(row: dict[str, Any]) -> dict[str, Any]:
    """psycopg row → JSON-safe dict."""
    occurred_at = row.get("occurred_at")
    if isinstance(occurred_at, datetime):
        occurred_at = occurred_at.isoformat()
    # id is UUID (D-3 변경 — BIGSERIAL에서 변경)
    raw_id = row.get("id")
    return {
        "id": str(raw_id) if raw_id is not None else None,
        "mission_id": str(row["mission_id"]) if row.get("mission_id") else None,
        "occurred_at": occurred_at,
        "actor": row.get("actor"),
        "action": row.get("action"),
        "result_preview": row.get("result_preview"),
        "metadata": row.get("metadata"),
    }
