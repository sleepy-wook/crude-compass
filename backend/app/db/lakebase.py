"""Lakebase Autoscaling connection — OAuth token runtime rotation.

핵심 패턴:
- 정적 DSN 저장 X (token이 60분 만료라 의미 없음)
- psycopg3 + psycopg_pool 사용 (Lakebase 공식 가이드 권장. asyncpg는 SASL 호환 X.)
- Custom Connection subclass — pool이 reconnect할 때마다 classmethod connect()가
  호출되어 fresh token 자동 발급.
- max_lifetime=3000s (50min) — token TTL 60min 안전 마진.

SDK API (v0.81+ 진짜 schema — github source 확인):
  w.database.generate_database_credential(
      request_id=str(uuid.uuid4()),
      instance_names=['<instance_name>'],  # 예: 'crude-compass-pg' (Lakebase project name)
  ) → DatabaseCredential.token

옛 `w.postgres.generate_database_credential(endpoint=path)`는 v0.81+에서 deprecated alias
— `endpoint=` parameter 자체가 새 API에 없음. silent fail (wrong token 발급).
"""
from __future__ import annotations

import uuid
from contextlib import contextmanager
from typing import Any, Iterator

import psycopg
from databricks.sdk import WorkspaceClient
from psycopg_pool import ConnectionPool

from app.core.config import get_settings


def _extract_instance_name(endpoint_path: str) -> str:
    """endpoint_path에서 instance (Lakebase project) name 추출.

    Secret value form:
      'projects/crude-compass-pg/branches/production/endpoints/primary'
                ^^^^^^^^^^^^^^^^
                instance_name (= project name in Lakebase)

    Path 아닌 경우 (단순 instance name) 그대로 반환.
    """
    s = endpoint_path.strip()
    if s.startswith("projects/"):
        parts = s.split("/")
        if len(parts) >= 2 and parts[1]:
            return parts[1]  # 'crude-compass-pg'
    return s


_RESOLVED_INSTANCE_NAME: str | None = None


def _resolve_actual_instance_name(w: WorkspaceClient, hint: str) -> str:
    """Apps SP context에서 진짜 visible instance name 발견.

    1. hint name 그대로 시도
    2. list_database_instances() — SP가 binding된 instance 추출
    3. fallback to hint
    """
    global _RESOLVED_INSTANCE_NAME
    if _RESOLVED_INSTANCE_NAME:
        return _RESOLVED_INSTANCE_NAME

    import logging as _logging
    log = _logging.getLogger(__name__)
    try:
        instances = list(w.database.list_database_instances())
        log.info("Lakebase list_database_instances: %d found", len(instances))
        for inst in instances:
            log.info("  instance: name=%s uid=%s", getattr(inst, 'name', '?'), getattr(inst, 'uid', '?'))
            name = getattr(inst, 'name', None)
            if name:
                _RESOLVED_INSTANCE_NAME = name
                return name
    except Exception as e:
        log.warning("list_database_instances failed: %s", e)
    return hint


def _generate_token(endpoint_path: str) -> str:
    """Apps SP OAuth token을 PG password로 직접 사용 (SDK Database API 우회).

    배경 (D-0 logs 분석):
    - Apps SP는 Database resource binding으로 PG connection 권한 받음 (CAN_CONNECT_AND_CREATE)
    - 하지만 SDK Database API (list_database_instances, generate_database_credential) 권한 없음
    - 모든 instance_names 변형 → "Database instance not found"
    - Lakebase는 PG `databricks_auth` extension으로 Databricks OAuth token 직접 validate
      → SP의 access token이 곧 PG password (binding이 자동 SP role grant)

    1차 시도: SP OAuth token (w.config.authenticate)
    2차 시도 (fallback): SDK API generate_database_credential (옛 코드 유지)
    """
    w = WorkspaceClient()
    # 1차: SP OAuth token 직접 (Apps SP context, 자동 authentication chain)
    try:
        auth_headers = w.config.authenticate()  # dict like {'Authorization': 'Bearer <token>'}
        if isinstance(auth_headers, dict):
            auth_value = auth_headers.get("Authorization", "")
            if auth_value.startswith("Bearer "):
                token = auth_value[len("Bearer "):]
                if token:
                    return token
    except Exception:
        pass
    # 2차 fallback: SDK Database API (권한 있으면 작동)
    instance_hint = _extract_instance_name(endpoint_path)
    instance_name = _resolve_actual_instance_name(w, instance_hint)
    credential = w.database.generate_database_credential(
        request_id=str(uuid.uuid4()),
        instance_names=[instance_name],
    )
    if not credential.token:
        raise RuntimeError("Lakebase OAuth token empty")
    return credential.token


def _resolve_user() -> str:
    """Lakebase PG user를 dynamic 결정.

    Local dev: settings.lakebase_user (.env의 사용자 이메일)
    Apps: workspace SP의 user_name (current_user.me() 자동 — OAuth token의 user와 일치)

    이유: Lakebase는 OAuth token의 user claim과 conninfo의 user를 일치 검증.
    Apps 환경에서 backend가 SP로 실행되는데 .env env가 사용자 이메일이면 mismatch → PoolTimeout.
    """
    s = get_settings()
    try:
        w = WorkspaceClient()
        me = w.current_user.me()
        # SP의 경우 user_name이 application_id (client_id UUID). User는 email.
        if me.user_name:
            return me.user_name
    except Exception:
        pass
    # Fallback: settings.lakebase_user (local dev path)
    return s.lakebase_user


def _build_conninfo() -> str:
    """psycopg conninfo string — password는 connect 시점에 kwargs로 주입."""
    s = get_settings()
    user = _resolve_user()
    return (
        f"host={s.lakebase_host} "
        f"port=5432 "
        f"dbname={s.lakebase_database} "
        f"user={user} "
        f"sslmode=require"
    )


class LakebaseConnection(psycopg.Connection):
    """psycopg.Connection subclass — connect()마다 fresh OAuth token 발급.

    psycopg_pool이 new connection 만들 때 (init + reconnect 시) 이 classmethod 호출.
    → token rotation 자동. pool 자체는 유지 (시나리오 §9 "Lakebase OAuth pool" 정합).
    """

    @classmethod
    def connect(cls, conninfo: str = "", **kwargs: Any) -> "LakebaseConnection":
        settings = get_settings()
        # 매 connect 시 fresh token 발급. kwargs.password 항상 overwrite.
        kwargs["password"] = _generate_token(settings.lakebase_endpoint_path)
        return super().connect(conninfo, **kwargs)  # type: ignore[return-value]


_pool: ConnectionPool | None = None


def get_pool() -> ConnectionPool:
    """Lazy singleton pool — Custom Connection subclass로 token rotation 자동."""
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            conninfo=_build_conninfo(),
            connection_class=LakebaseConnection,
            min_size=1,
            max_size=5,
            # token TTL 60min → max_lifetime 50min로 만료 전 reconnect 강제.
            max_lifetime=3000,
            open=False,
        )
        _pool.open()
    return _pool


def close_pool() -> None:
    """Application shutdown 시."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


@contextmanager
def acquire() -> Iterator[psycopg.Connection]:
    """Convenience context manager."""
    pool = get_pool()
    with pool.connection() as conn:
        yield conn


def migrate_d4() -> bool:
    """D-4/D-3 schema migration — Sub-A/B 컬럼 + agent_activity_events table.

    Idempotent (IF NOT EXISTS). Lakebase 미연동 환경에서는 silent skip.
    backend startup 시 한 번 호출.

    D-4 (2026-05-15): cycle / supplier_mix / simulation_scenarios
    D-3 (2026-05-18): delta_vs_previous
    D-3 (2026-05-19): agent_activity_events — Agent Bricks orchestration timeline persistence

    각 step 별로 try/except 분리 (D-3 hardening) — 한 step 실패해도 나머지 진행 + 진짜 에러 로깅.
    """
    import logging
    import traceback
    logger = logging.getLogger(__name__)

    def _step(name: str, sql: str, conn: psycopg.Connection) -> bool:
        try:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
            logger.info("migrate_d4 step OK: %s", name)
            return True
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            logger.warning(
                "migrate_d4 step FAIL [%s]: %s\n%s",
                name, e, traceback.format_exc(),
            )
            return False

    overall_ok = True
    try:
        with acquire() as conn:
            # ── DDL on missions ──
            _step("alter:cycle", "ALTER TABLE missions ADD COLUMN IF NOT EXISTS cycle TEXT", conn)
            _step("alter:supplier_mix",
                  "ALTER TABLE missions ADD COLUMN IF NOT EXISTS supplier_mix JSONB NOT NULL DEFAULT '[]'::jsonb", conn)
            _step("alter:simulation_scenarios",
                  "ALTER TABLE missions ADD COLUMN IF NOT EXISTS simulation_scenarios JSONB NOT NULL DEFAULT '[]'::jsonb", conn)
            _step("alter:delta_vs_previous",
                  "ALTER TABLE missions ADD COLUMN IF NOT EXISTS delta_vs_previous JSONB", conn)

            # ── CREATE agent_activity_events ──
            # BIGSERIAL 대신 UUID PK (SP가 CREATE SEQUENCE 권한 없을 가능성 대비).
            # missions table이 gen_random_uuid()를 쓰고 있어 pgcrypto는 활성화돼 있음.
            ok_table = _step(
                "create:agent_activity_events",
                """
                CREATE TABLE IF NOT EXISTS agent_activity_events (
                    id             UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                    mission_id     UUID,
                    occurred_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    actor          VARCHAR(64) NOT NULL,
                    action         VARCHAR(64) NOT NULL,
                    result_preview TEXT,
                    metadata       JSONB
                )
                """,
                conn,
            )
            if not ok_table:
                overall_ok = False
                # table 없으면 index/backfill 무의미 — 종료
                logger.warning("migrate_d4: agent_activity_events 생성 실패 → index/backfill skip")
                return overall_ok

            _step(
                "create:idx_agent_activity_mission",
                "CREATE INDEX IF NOT EXISTS idx_agent_activity_mission "
                "ON agent_activity_events(mission_id, occurred_at DESC)",
                conn,
            )

            # ── Backfill: 기존 missions에 누락 event 채우기 (idempotent, NOT EXISTS guard) ──
            _step(
                "backfill:score_computed",
                """
                INSERT INTO agent_activity_events
                    (mission_id, occurred_at, actor, action, result_preview, metadata)
                SELECT
                    m.mission_id,
                    m.created_at - interval '15 seconds',
                    'weighted_signal_uc',
                    'score_computed',
                    '양방향 가중 Pattern Score ' || ROUND(m.pattern_score) || ' 계산 (90일 window)',
                    jsonb_build_object('pattern_score', m.pattern_score, 'urgency', m.urgency)
                FROM missions m
                WHERE NOT EXISTS (
                    SELECT 1 FROM agent_activity_events e
                     WHERE e.mission_id = m.mission_id
                       AND e.actor = 'weighted_signal_uc'
                       AND e.action = 'score_computed'
                )
                """,
                conn,
            )

            _step(
                "backfill:case_opened",
                """
                INSERT INTO agent_activity_events
                    (mission_id, occurred_at, actor, action, result_preview, metadata)
                SELECT
                    m.mission_id,
                    m.created_at - interval '10 seconds',
                    'supervisor',
                    'case_opened',
                    (CASE WHEN m.mission_type = 'HEDGE' THEN '위험방어' ELSE '기회포착' END)
                    || ' case 개시 — Pattern Score ' || ROUND(m.pattern_score)
                    || ', 긴급도 ' || m.urgency,
                    jsonb_build_object('mission_type', m.mission_type, 'urgency', m.urgency)
                FROM missions m
                WHERE NOT EXISTS (
                    SELECT 1 FROM agent_activity_events e
                     WHERE e.mission_id = m.mission_id
                       AND e.actor = 'supervisor'
                       AND e.action = 'case_opened'
                )
                """,
                conn,
            )

            _step(
                "backfill:draft_generated",
                """
                INSERT INTO agent_activity_events
                    (mission_id, occurred_at, actor, action, result_preview, metadata)
                SELECT
                    m.mission_id,
                    m.created_at - interval '5 seconds',
                    'mission_plan_fma',
                    'draft_generated',
                    (CASE WHEN m.mission_type = 'HEDGE' THEN '위험방어' ELSE '기회포착' END)
                    || ' 권고 — ' || COALESCE(m.target_pct::text, '?') || '% / '
                    || COALESCE(m.duration_days::text, '?') || '일',
                    jsonb_build_object('target_pct', m.target_pct, 'duration_days', m.duration_days)
                FROM missions m
                WHERE NOT EXISTS (
                    SELECT 1 FROM agent_activity_events e
                     WHERE e.mission_id = m.mission_id
                       AND e.actor = 'mission_plan_fma'
                       AND e.action = 'draft_generated'
                )
                """,
                conn,
            )

            _step(
                "backfill:confirmed",
                """
                INSERT INTO agent_activity_events
                    (mission_id, occurred_at, actor, action, result_preview, metadata)
                SELECT
                    m.mission_id, m.confirmed_at, 'manager', 'confirmed',
                    '매니저 승인 (via ' || COALESCE(m.confirmed_via, 'apps') || ')',
                    jsonb_build_object('by', COALESCE(m.confirmed_by, 'unknown'),
                                       'via', COALESCE(m.confirmed_via, 'apps'))
                FROM missions m
                WHERE m.confirmed_at IS NOT NULL
                  AND m.status IN ('active', 'on_track', 'at_risk', 'paused', 'pivoted', 'completed')
                  AND NOT EXISTS (
                      SELECT 1 FROM agent_activity_events e
                       WHERE e.mission_id = m.mission_id AND e.actor = 'manager' AND e.action = 'confirmed'
                  )
                """,
                conn,
            )

            _step(
                "backfill:rejected",
                """
                INSERT INTO agent_activity_events
                    (mission_id, occurred_at, actor, action, result_preview, metadata)
                SELECT
                    m.mission_id, m.completed_at, 'manager', 'rejected',
                    '매니저 기각 (via ' || COALESCE(m.confirmed_via, 'apps') || ')',
                    jsonb_build_object('by', COALESCE(m.confirmed_by, 'unknown'),
                                       'via', COALESCE(m.confirmed_via, 'apps'))
                FROM missions m
                WHERE m.completed_at IS NOT NULL
                  AND m.status = 'aborted'
                  AND NOT EXISTS (
                      SELECT 1 FROM agent_activity_events e
                       WHERE e.mission_id = m.mission_id AND e.actor = 'manager' AND e.action = 'rejected'
                  )
                """,
                conn,
            )
        logger.info("Lakebase migrate_d4 finished (overall_ok=%s)", overall_ok)
        return overall_ok
    except Exception as e:
        import traceback as _tb
        logger.warning("Lakebase migrate_d4 fatal: %s\n%s", e, _tb.format_exc())
        return False
