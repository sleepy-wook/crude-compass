"""Lakebase Autoscaling connection — OAuth token runtime rotation.

핵심 패턴 (Databricks 공식 Lakebase Apps tutorial 정합):
- 정적 DSN 저장 X (token이 60분 만료라 의미 없음)
- psycopg3 + psycopg_pool 사용 (Lakebase 공식 가이드 권장. asyncpg는 SASL 호환 X.)
- Custom Connection subclass — pool이 reconnect할 때마다 classmethod connect()가
  호출되어 fresh token 자동 발급.
- max_lifetime=3000s (50min) — token TTL 60min 안전 마진.

SDK API (v0.81+ — Lakebase 공식 tutorial):
  w.postgres.generate_database_credential(endpoint='projects/<id>/branches/<id>/endpoints/<id>')
  → DatabaseCredential.token (PG password로 사용)
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

import psycopg
from databricks.sdk import WorkspaceClient
from psycopg_pool import ConnectionPool

from app.core.config import get_settings


def _resolve_endpoint_path(secret_path: str) -> str:
    """Lakebase endpoint path resolver.

    Secret value가 `endpoints/primary` (display name)일 수 있지만 실제 endpoint id는
    auto-generated `ep-<random>` 형태. PGHOST env에서 추출해서 path 재구성.

    예:
      secret_path = 'projects/crude-compass-pg/branches/production/endpoints/primary'
      PGHOST     = 'ep-lucky-star-d1rlmmrr.database.us-west-2.cloud.databricks.com'
      → 'projects/crude-compass-pg/branches/production/endpoints/ep-lucky-star-d1rlmmrr'

    Apps Database resource binding이 PGHOST 자동 주입 (또는 secret과 동일).
    PGHOST 없으면 secret_path 그대로 반환 (fallback).
    """
    import os as _os
    pghost = _os.getenv("PGHOST", "").strip()
    if not pghost or "endpoints/" not in secret_path:
        return secret_path
    # PGHOST first segment = endpoint_id (예: ep-lucky-star-d1rlmmrr)
    endpoint_id = pghost.split(".")[0]
    if not endpoint_id.startswith("ep-"):
        return secret_path  # not Lakebase host pattern
    # path의 endpoints/<x> 를 endpoints/<actual_id> 로 교체
    parts = secret_path.split("/")
    # parts = ['projects', '<project>', 'branches', '<branch>', 'endpoints', '<endpoint>']
    if len(parts) >= 6 and parts[4] == "endpoints":
        parts[5] = endpoint_id
        return "/".join(parts)
    return secret_path


def _generate_token(endpoint_path: str) -> str:
    """SDK로 Lakebase OAuth token 발급 (60분 lifetime).

    endpoint_path: Lakebase endpoint full path
      (예: 'projects/crude-compass-pg/branches/production/endpoints/ep-...')
    Apps Database resource binding이 자동 주입 (또는 secret으로 수동 등록).

    Secret value가 display name (`endpoints/primary`)이면 PGHOST로 실제 endpoint_id 추론.
    """
    resolved_path = _resolve_endpoint_path(endpoint_path)
    w = WorkspaceClient()
    credential = w.postgres.generate_database_credential(endpoint=resolved_path)
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
