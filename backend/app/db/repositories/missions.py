"""Mission CRUD against Lakebase Postgres.

Schema: databricks/schemas/lakebase.sql §1 missions.
Key features:
- gen_random_uuid() (pgcrypto) for mission_id default
- JSONB for simulation_roi + pivot_history
- Optimistic concurrency via `version` column (UPDATE ... WHERE version = :v)
- TIMESTAMPTZ throughout

psycopg3 Connection 직접 받음. Pool 관리는 store.py / db.lakebase.py에서.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row

from app.schemas.mission import (
    Mission,
    MissionStatus,
    MissionType,
    MissionUrgency,
    PivotEntry,
    SimulationAssumptions,
    SimulationScenario,
    SupplierAllocation,
)


# ──────────────────────────────────────────────────────────────────────────
# Row → Pydantic conversion
# ──────────────────────────────────────────────────────────────────────────
def _row_to_mission(row: dict[str, Any]) -> Mission:
    """Map a missions row (dict) to Mission pydantic model.

    JSONB columns come back as already-decoded Python objects from psycopg3.
    """
    # pivot_history is JSONB list of {from_type, to_type, occurred_at, reason, pattern_score_at}
    pivot_raw = row.get("pivot_history") or []
    pivot_history = [
        PivotEntry(
            from_type=p["from_type"],
            to_type=p["to_type"],
            occurred_at=p["occurred_at"] if isinstance(p["occurred_at"], datetime)
                        else datetime.fromisoformat(p["occurred_at"]),
            reason=p["reason"],
            pattern_score_at=float(p["pattern_score_at"]),
        )
        for p in pivot_raw
    ]

    # Sub-A — supplier_mix JSONB (옵션, column 없으면 [])
    supplier_mix_raw = row.get("supplier_mix") or []
    supplier_mix = [
        SupplierAllocation(
            supplier_name=s["supplier_name"],
            delta_bpd=int(s["delta_bpd"]),
            rationale=s["rationale"],
        )
        for s in supplier_mix_raw
    ]

    # delta_vs_previous JSONB (D-3, 옵션 — column 없으면 None)
    delta_raw = row.get("delta_vs_previous")
    delta_vs_previous = None
    if delta_raw:
        from app.schemas.mission import DeltaVsPrevious
        try:
            delta_vs_previous = DeltaVsPrevious.model_validate(delta_raw)
        except Exception:
            delta_vs_previous = None

    # Sub-B — simulation_scenarios JSONB (옵션, column 없으면 [])
    scenarios_raw = row.get("simulation_scenarios") or []
    simulation_scenarios = []
    for sc in scenarios_raw:
        a = sc.get("assumptions") or {}
        simulation_scenarios.append(
            SimulationScenario(
                name=sc["name"],
                label=sc["label"],
                assumptions=SimulationAssumptions(
                    scenario_label=a.get("scenario_label", ""),
                    brent_usd=float(a.get("brent_usd", 0)),
                    usd_krw=float(a.get("usd_krw", 0)),
                    vlcc_freight_multiplier=float(a.get("vlcc_freight_multiplier", 1.0)),
                ),
                saving_pct=float(sc.get("saving_pct", 0)),
                saving_krw_oku=int(sc.get("saving_krw_oku", 0)),
                confidence_note=sc.get("confidence_note"),
            )
        )

    return Mission(
        mission_id=row["mission_id"],
        mission_type=MissionType(row["mission_type"]),
        status=MissionStatus(row["status"]),
        goal_text=row["goal_text"],
        pattern_score=float(row["pattern_score"]),
        reasoning=row["reasoning"],
        simulation_roi=row["simulation_roi"] or {},
        urgency=MissionUrgency(row["urgency"]),
        target_pct=row["target_pct"],
        duration_days=row["duration_days"],
        created_at=row["created_at"],
        confirmed_at=row.get("confirmed_at"),
        confirmed_by=row.get("confirmed_by"),
        confirmed_via=row.get("confirmed_via"),
        completed_at=row.get("completed_at"),
        pivot_history=pivot_history,
        version=row["version"],
        # Sub-A + Sub-B fields
        cycle=row.get("cycle"),
        supplier_mix=supplier_mix,
        simulation_scenarios=simulation_scenarios,
        # AI Agent delta_vs_previous (D-3)
        delta_vs_previous=delta_vs_previous,
    )


# ──────────────────────────────────────────────────────────────────────────
# CRUD operations
# ──────────────────────────────────────────────────────────────────────────
def insert(conn: psycopg.Connection, mission: Mission) -> Mission:
    """Insert a new mission. mission_id 는 caller가 생성 (uuid4) 또는 None이면 DB default."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            INSERT INTO missions (
                mission_id, mission_type, status, goal_text, pattern_score, reasoning,
                simulation_roi, urgency, target_pct, duration_days,
                created_at, pivot_history, version,
                cycle, supplier_mix, simulation_scenarios, delta_vs_previous
            )
            VALUES (
                %(mission_id)s, %(mission_type)s, %(status)s, %(goal_text)s,
                %(pattern_score)s, %(reasoning)s,
                %(simulation_roi)s::jsonb, %(urgency)s, %(target_pct)s, %(duration_days)s,
                %(created_at)s, %(pivot_history)s::jsonb, %(version)s,
                %(cycle)s, %(supplier_mix)s::jsonb, %(simulation_scenarios)s::jsonb,
                %(delta_vs_previous)s::jsonb
            )
            RETURNING *
            """,
            {
                "mission_id": mission.mission_id,
                "mission_type": mission.mission_type.value,
                "status": mission.status.value,
                "goal_text": mission.goal_text,
                "pattern_score": mission.pattern_score,
                "reasoning": mission.reasoning,
                "simulation_roi": json.dumps(mission.simulation_roi),
                "urgency": mission.urgency.value,
                "target_pct": mission.target_pct,
                "duration_days": mission.duration_days,
                "created_at": mission.created_at,
                "pivot_history": json.dumps([p.model_dump(mode="json") for p in mission.pivot_history]),
                "version": mission.version,
                # Sub-A + Sub-B
                "cycle": mission.cycle,
                "supplier_mix": json.dumps([s.model_dump(mode="json") for s in mission.supplier_mix]),
                "simulation_scenarios": json.dumps([s.model_dump(mode="json") for s in mission.simulation_scenarios]),
                # Delta vs previous (D-3)
                "delta_vs_previous": (
                    json.dumps(mission.delta_vs_previous.model_dump(mode="json"))
                    if mission.delta_vs_previous
                    else None
                ),
            },
        )
        row = cur.fetchone()
        conn.commit()
    return _row_to_mission(row)


def get(conn: psycopg.Connection, mission_id: UUID) -> Mission | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT * FROM missions WHERE mission_id = %s", (mission_id,))
        row = cur.fetchone()
    return _row_to_mission(row) if row else None


def list_active(conn: psycopg.Connection) -> list[Mission]:
    """proposed + active + on_track + at_risk + paused."""
    active = {"proposed", "active", "on_track", "at_risk", "paused"}
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT * FROM missions WHERE status = ANY(%s) ORDER BY created_at DESC",
            (list(active),),
        )
        rows = cur.fetchall()
    return [_row_to_mission(r) for r in rows]


def list_all(conn: psycopg.Connection, limit: int = 200) -> list[Mission]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT * FROM missions ORDER BY created_at DESC LIMIT %s", (limit,)
        )
        rows = cur.fetchall()
    return [_row_to_mission(r) for r in rows]


# ──────────────────────────────────────────────────────────────────────────
# Optimistic concurrency updates
# Each update method: WHERE version = :expected_version AND returns None on conflict
# ──────────────────────────────────────────────────────────────────────────
def _update_with_version_check(
    conn: psycopg.Connection,
    mission_id: UUID,
    expected_version: int,
    set_clause: str,
    set_params: dict[str, Any],
) -> Mission | None:
    """Generic UPDATE with version check + RETURNING."""
    params = {"mission_id": mission_id, "expected_version": expected_version, **set_params}
    sql = f"""
        UPDATE missions
           SET {set_clause}, version = version + 1
         WHERE mission_id = %(mission_id)s
           AND version = %(expected_version)s
        RETURNING *
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        conn.commit()
    return _row_to_mission(row) if row else None


def confirm(
    conn: psycopg.Connection,
    mission_id: UUID,
    expected_version: int,
    confirmed_by: str,
    via: str,
) -> Mission | None:
    return _update_with_version_check(
        conn, mission_id, expected_version,
        set_clause="""status = 'active',
                      confirmed_at = NOW(),
                      confirmed_by = %(confirmed_by)s,
                      confirmed_via = %(via)s""",
        set_params={"confirmed_by": confirmed_by, "via": via},
    )


def reject(
    conn: psycopg.Connection,
    mission_id: UUID,
    expected_version: int,
    confirmed_by: str,
    via: str,
) -> Mission | None:
    return _update_with_version_check(
        conn, mission_id, expected_version,
        set_clause="""status = 'aborted',
                      completed_at = NOW(),
                      confirmed_by = %(confirmed_by)s,
                      confirmed_via = %(via)s""",
        set_params={"confirmed_by": confirmed_by, "via": via},
    )


def pivot(
    conn: psycopg.Connection,
    mission_id: UUID,
    expected_version: int,
    pivot_action: str,  # pivot | pause | abort | continue
    to_type: str | None,
    reason: str,
) -> Mission | None:
    """Atomic UPDATE — version check + pivot_history append + status change."""
    # 사전에 현재 mission load해서 pivot entry 만들기 (transactional)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT mission_id, mission_type, pattern_score, version FROM missions WHERE mission_id = %s",
            (mission_id,),
        )
        cur_row = cur.fetchone()
    if not cur_row or cur_row["version"] != expected_version:
        return None

    new_pivot = None
    new_mission_type = cur_row["mission_type"]
    new_status = None
    if pivot_action == "pivot" and to_type:
        new_pivot = {
            "from_type": cur_row["mission_type"],
            "to_type": to_type,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
            "pattern_score_at": float(cur_row["pattern_score"]),
        }
        new_mission_type = to_type
        new_status = "pivoted"
    elif pivot_action == "pause":
        new_status = "paused"
    elif pivot_action == "abort":
        new_status = "aborted"

    sets = []
    params: dict[str, Any] = {
        "mission_id": mission_id, "expected_version": expected_version,
    }
    if new_pivot is not None:
        sets.append("pivot_history = pivot_history || %(new_pivot)s::jsonb")
        sets.append("mission_type = %(mission_type)s")
        params["new_pivot"] = json.dumps([new_pivot])
        params["mission_type"] = new_mission_type
    if new_status is not None:
        sets.append("status = %(status)s")
        params["status"] = new_status
    if pivot_action == "abort":
        sets.append("completed_at = NOW()")

    if not sets:
        # 'continue' action — no state change, just return current mission as-is.
        # (Decision is recorded by caller in decisions table.)
        return get(conn, mission_id)

    sets.append("version = version + 1")
    sql = f"""
        UPDATE missions
           SET {", ".join(sets)}
         WHERE mission_id = %(mission_id)s
           AND version = %(expected_version)s
        RETURNING *
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        conn.commit()
    return _row_to_mission(row) if row else None


def modify(
    conn: psycopg.Connection,
    mission_id: UUID,
    expected_version: int,
    target_pct: int | None,
    duration_days: int | None,
) -> Mission | None:
    sets = []
    params: dict[str, Any] = {}
    if target_pct is not None:
        sets.append("target_pct = %(target_pct)s")
        params["target_pct"] = target_pct
    if duration_days is not None:
        sets.append("duration_days = %(duration_days)s")
        params["duration_days"] = duration_days
    if not sets:
        m = get(conn, mission_id)
        return m if (m and m.version == expected_version) else None

    return _update_with_version_check(
        conn, mission_id, expected_version,
        set_clause=", ".join(sets),
        set_params=params,
    )
