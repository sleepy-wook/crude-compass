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
    """D-4 schema migration — Sub-A/B 새 컬럼 추가.

    Idempotent (IF NOT EXISTS). Lakebase 미연동 환경에서는 silent skip.
    backend startup 시 한 번 호출.

    Returns: True if applied (or already applied), False if Lakebase 미연동.
    """
    import logging
    logger = logging.getLogger(__name__)
    try:
        with acquire() as conn:
            with conn.cursor() as cur:
                cur.execute("ALTER TABLE missions ADD COLUMN IF NOT EXISTS cycle TEXT")
                cur.execute(
                    "ALTER TABLE missions ADD COLUMN IF NOT EXISTS supplier_mix JSONB NOT NULL DEFAULT '[]'::jsonb"
                )
                cur.execute(
                    "ALTER TABLE missions ADD COLUMN IF NOT EXISTS simulation_scenarios JSONB NOT NULL DEFAULT '[]'::jsonb"
                )
                # D-3: delta_vs_previous (AI Agent 어제 vs 오늘 변동 narrative)
                cur.execute(
                    "ALTER TABLE missions ADD COLUMN IF NOT EXISTS delta_vs_previous JSONB"
                )
            conn.commit()
        logger.info("Lakebase migrate_d4 applied (cycle + supplier_mix + simulation_scenarios + delta_vs_previous)")
        return True
    except Exception as e:
        logger.warning("Lakebase migrate_d4 skipped: %s", e)
        return False
