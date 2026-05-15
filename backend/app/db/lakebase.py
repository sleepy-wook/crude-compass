"""Lakebase Autoscaling connection — OAuth token runtime rotation.

핵심 패턴:
- 정적 DSN 저장 X (token이 60분 만료라 의미 없음)
- psycopg3 + psycopg_pool 사용 (Lakebase 공식 가이드 권장. asyncpg는 SASL 호환 X.)
- Direct host 사용 (`ep-...databricks.com`). Pooled host (`-pooler`)는 SASL 호환 X.
- Custom Connection subclass `LakebaseConnection` — pool이 reconnect할 때마다
  classmethod connect()가 호출되어 fresh token 자동 발급.
- max_lifetime=3000s (50min) — token TTL 60min 안전 마진.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

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
    """psycopg conninfo string — password는 connect 시점에 kwargs로 주입."""
    s = get_settings()
    return (
        f"host={s.lakebase_host} "
        f"port=5432 "
        f"dbname={s.lakebase_database} "
        f"user={s.lakebase_user} "
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
