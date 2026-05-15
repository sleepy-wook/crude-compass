"""Lakebase Autoscaling connection — OAuth token runtime rotation.

핵심 패턴:
- 정적 DSN 저장 X (token이 60분 만료라 의미 없음)
- psycopg3 + psycopg_pool 사용 (Lakebase 공식 가이드 권장. asyncpg는 SASL 호환 X.)
- Direct host 사용 (`ep-...databricks.com`). Pooled host (`-pooler`)는 SASL 호환 X.
- Connection 생성 시마다 SDK로 fresh token 발급 (60분마다 rotation)
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import psycopg
from databricks.sdk import WorkspaceClient
from psycopg_pool import ConnectionPool

from app.core.config import get_settings


def _generate_token(endpoint_path: str) -> str:
    """SDK로 Lakebase OAuth token 발급 (60분 lifetime)."""
    w = WorkspaceClient()
    credential = w.postgres.generate_database_credential(endpoint=endpoint_path)
    if not credential.token:
        raise RuntimeError("Lakebase OAuth token empty")
    return credential.token


def _build_conninfo() -> str:
    """psycopg conninfo string — password는 connect 시점에 별도로 주입."""
    s = get_settings()
    return (
        f"host={s.lakebase_host} "
        f"port=5432 "
        f"dbname={s.lakebase_database} "
        f"user={s.lakebase_user} "
        f"sslmode=require"
    )


def _new_connection() -> psycopg.Connection:
    """Pool factory — 매 connection마다 fresh token 발급."""
    settings = get_settings()
    token = _generate_token(settings.lakebase_endpoint_path)
    return psycopg.connect(_build_conninfo(), password=token)


_pool: ConnectionPool | None = None


def get_pool() -> ConnectionPool:
    """Lazy singleton pool."""
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            connection_class=psycopg.Connection,
            min_size=1,
            max_size=5,
            # OAuth token life = 60min. max_lifetime 50min로 강제 reconnect → 토큰 만료 전 재발급.
            # 만약 max_lifetime 미설정 시 idle 60min+ pool connection은 stale token으로 SQL 실패.
            max_lifetime=3000,
            open=False,  # explicit open
            connection=_new_connection,  # custom factory for token rotation
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
