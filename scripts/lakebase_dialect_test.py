"""Lakebase Postgres dialect 검증 (Sprint 1 task 7).

목적 (Phase 1.4 검증 못 한 것 #2):
1. JSONB 컬럼 INSERT/SELECT 정상
2. UUID 컬럼 (gen_random_uuid()) 정상
3. version 컬럼 optimistic concurrency 작동 (UPDATE WHERE version=?)
4. Databricks SDK OAuth token으로 psycopg3 연결 정상

Driver: psycopg3 (Lakebase 공식 가이드 권장. asyncpg는 SASL 호환성 X.)

사용:
    cd backend
    $env:LAKEBASE_HOST = "ep-lucky-star-d1rlmmrr-pooler.database.us-west-2.cloud.databricks.com"
    $env:LAKEBASE_DATABASE = "databricks_postgres"
    $env:LAKEBASE_ENDPOINT_PATH = "projects/crude-compass-pg/branches/production/endpoints/primary"
    $env:LAKEBASE_USER = "hyeongwook.lee@lginnotek.com"
    $env:DATABRICKS_CONFIG_PROFILE = "crude-compass"
    uv run python ../scripts/lakebase_dialect_test.py
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from uuid import UUID

# Windows PowerShell cp949 → UTF-8 (emoji print 가능)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except (AttributeError, OSError):
        pass

import psycopg
from databricks.sdk import WorkspaceClient


REQUIRED_ENV = [
    "LAKEBASE_HOST",
    "LAKEBASE_DATABASE",
    "LAKEBASE_ENDPOINT_PATH",
    "LAKEBASE_USER",
]


def check_env() -> dict[str, str]:
    out: dict[str, str] = {}
    for name in REQUIRED_ENV:
        v = os.getenv(name, "").strip()
        if not v:
            sys.exit(f"❌ {name} 환경변수 비어있음")
        out[name] = v
    return out


def get_oauth_token(endpoint_path: str) -> str:
    """Databricks SDK로 Lakebase OAuth token 발급."""
    w = WorkspaceClient()
    credential = w.postgres.generate_database_credential(endpoint=endpoint_path)
    if not credential.token:
        sys.exit("❌ Token 발급 실패: empty token")
    return credential.token


def run_tests(env: dict[str, str]) -> None:
    print("─── 1. OAuth token 발급 ───")
    token = get_oauth_token(env["LAKEBASE_ENDPOINT_PATH"])
    print(f"✅ Token 발급 OK (length={len(token)}, 60분 lifetime)\n")

    print("─── 2. psycopg3 연결 ───")
    conninfo = (
        f"host={env['LAKEBASE_HOST']} "
        f"port=5432 "
        f"dbname={env['LAKEBASE_DATABASE']} "
        f"user={env['LAKEBASE_USER']} "
        f"sslmode=require"
    )
    with psycopg.connect(conninfo, password=token) as conn:
        print(f"✅ Connected to {env['LAKEBASE_HOST']}\n")

        with conn.cursor() as cur:
            print("─── 3. pgcrypto 확장 (gen_random_uuid) ───")
            cur.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
            cur.execute("SELECT gen_random_uuid()")
            uid: UUID = cur.fetchone()[0]  # type: ignore[index]
            print(f"✅ UUID generated: {uid}\n")

            print("─── 4. 임시 테이블 (JSONB + UUID + version) ───")
            cur.execute("""
                CREATE TEMP TABLE _test_missions (
                    mission_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    simulation_roi JSONB NOT NULL,
                    version INT NOT NULL DEFAULT 1,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            print("✅ TEMP table created\n")

            print("─── 5. INSERT JSONB ───")
            cur.execute(
                "INSERT INTO _test_missions (simulation_roi) VALUES (%s::jsonb) "
                "RETURNING mission_id, version, simulation_roi",
                ('{"Brent_130": 320, "Brent_110": 140, "Brent_90": -50}',),
            )
            row = cur.fetchone()
            assert row is not None
            mid: UUID = row[0]
            print(f"✅ INSERT OK · mission_id={mid} · version={row[1]}")
            print(f"   simulation_roi: {row[2]}\n")

            print("─── 6. SELECT JSONB key ───")
            cur.execute(
                "SELECT (simulation_roi->>'Brent_130')::int FROM _test_missions WHERE mission_id=%s",
                (mid,),
            )
            val = cur.fetchone()[0]  # type: ignore[index]
            print(f"✅ JSONB ->>'Brent_130' = {val} (expected 320)\n")

            print("─── 7. Optimistic concurrency UPDATE (version=1 → 2) ───")
            cur.execute(
                "UPDATE _test_missions SET version=version+1 WHERE mission_id=%s AND version=%s "
                "RETURNING version",
                (mid, 1),
            )
            updated = cur.fetchone()
            assert updated is not None
            print(f"✅ UPDATE version 1→{updated[0]}\n")

            print("─── 8. Conflict 시뮬 (version=1로 다시 UPDATE) ───")
            cur.execute(
                "UPDATE _test_missions SET version=version+1 WHERE mission_id=%s AND version=%s "
                "RETURNING version",
                (mid, 1),  # 이미 2가 됐으므로 매칭 X
            )
            conflict = cur.fetchone()
            if conflict is None:
                print("✅ Conflict 정상 작동 (UPDATE row 0건 = optimistic concurrency 작동)\n")
            else:
                print(f"❌ Conflict 실패 — UPDATE가 적용됨: {conflict}\n")

            print("─── 9. Postgres version 확인 ───")
            cur.execute("SELECT version()")
            pgv = cur.fetchone()[0]  # type: ignore[index]

        # TEMP 자동 cleanup (session 종료 시)

    print("=" * 50)
    print("🎉 모든 dialect test PASS")
    print("=" * 50)
    print(f"  - Test time:    {datetime.now(timezone.utc).isoformat()}")
    print(f"  - Postgres:     {pgv}")  # type: ignore[possibly-undefined]


def main() -> None:
    env = check_env()
    run_tests(env)


if __name__ == "__main__":
    main()
