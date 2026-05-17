"""Debug endpoint — Lakebase 진단 (D-0 02:00 KST trial).

production logs에서 logger.info 안 보임 → debug endpoint로 직접 fetch.

Endpoint: GET /api/debug/lakebase
- env vars (PG* + DATABRICKS_*)
- list_database_instances() 결과
- find_database_instance_by_uid() 시도 (Project UID)
- generate_database_credential 다양한 path 시도 → 어떤 게 작동하는지

D-0 제출 전 진단용. 제출 후 제거 또는 DEMO_MODE gated.
"""
from __future__ import annotations

import os
import uuid
from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/api/debug", tags=["debug"])


@router.get("/lakebase")
async def debug_lakebase() -> dict[str, Any]:
    """Lakebase SDK call 진단 — 어떤 path/name이 작동하는지 fact-based 확인."""
    from databricks.sdk import WorkspaceClient

    result: dict[str, Any] = {}

    # 1. env vars
    result["env_pg"] = {
        k: v for k, v in os.environ.items() if k.startswith("PG")
    }
    result["env_lakebase"] = {
        k: ("***" if "TOKEN" in k or "SECRET" in k or "PASS" in k else v[:60])
        for k, v in os.environ.items()
        if k.startswith("LAKEBASE_") or k.startswith("DATABRICKS_")
    }

    w = WorkspaceClient()

    # 2. list_database_instances
    try:
        instances = list(w.database.list_database_instances())
        result["instances_count"] = len(instances)
        result["instances"] = [
            {
                "name": getattr(i, "name", None),
                "uid": getattr(i, "uid", None),
                "state": str(getattr(i, "state", None)),
            }
            for i in instances[:10]
        ]
    except Exception as e:
        result["instances_error"] = f"{type(e).__name__}: {str(e)[:300]}"

    # 3. find by UID (Project UID from screenshot)
    project_uid = "09fa6546-cbbc-491f-9ff4-9ed285fe2835"
    try:
        inst = w.database.find_database_instance_by_uid(uid=project_uid)
        result["find_by_uid"] = {
            "name": getattr(inst, "name", None),
            "uid": getattr(inst, "uid", None),
        }
    except Exception as e:
        result["find_by_uid_error"] = f"{type(e).__name__}: {str(e)[:300]}"

    # 4. w.postgres.generate_database_credential(endpoint=...) — Lakebase 전용 namespace
    postgres_attempts: dict[str, Any] = {}
    paths_to_try = [
        "projects/crude-compass-pg/branches/production/endpoints/primary",
        "projects/crude-compass-pg/branches/production/endpoints/ep-lucky-star-d1rlmmrr",
        "projects/crude-compass-pg/branches/production",
        "projects/crude-compass-pg",
        "crude-compass-pg",
        "primary",
        "ep-lucky-star-d1rlmmrr",
    ]
    for path in paths_to_try:
        try:
            cred = w.postgres.generate_database_credential(endpoint=path)
            postgres_attempts[path] = {
                "ok": True,
                "token_prefix": (cred.token or "")[:30],
            }
        except Exception as e:
            postgres_attempts[path] = {
                "ok": False,
                "error": f"{type(e).__name__}: {str(e)[:200]}",
            }
    result["postgres_attempts"] = postgres_attempts

    # 5. w.config.authenticate() — SP OAuth token 진짜 prefix
    try:
        auth_headers = w.config.authenticate()
        if isinstance(auth_headers, dict):
            auth_value = auth_headers.get("Authorization", "")
            result["sp_auth_token_prefix"] = auth_value[:50] if auth_value else "(empty)"
        else:
            result["sp_auth_token_prefix"] = f"(type: {type(auth_headers).__name__})"
    except Exception as e:
        result["sp_auth_error"] = f"{type(e).__name__}: {str(e)[:200]}"

    # 6. 직접 psycopg connect 시도 (각 token strategy)
    import psycopg
    pg_attempts: dict[str, Any] = {}
    host = os.environ.get("PGHOST", "")
    user = os.environ.get("PGUSER", "")
    database = os.environ.get("PGDATABASE", "databricks_postgres")

    # Strategy A: SP OAuth token 직접
    try:
        auth_headers = w.config.authenticate()
        token_a = auth_headers.get("Authorization", "").replace("Bearer ", "")
        if token_a:
            conn = psycopg.connect(
                host=host, port=5432, dbname=database, user=user,
                password=token_a, sslmode="require", connect_timeout=10,
            )
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
            conn.close()
            pg_attempts["sp_oauth_token"] = {"ok": True}
        else:
            pg_attempts["sp_oauth_token"] = {"ok": False, "error": "no token"}
    except Exception as e:
        pg_attempts["sp_oauth_token"] = {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}

    # Strategy B: w.postgres token (working path가 있으면)
    working_postgres_path = next((p for p, v in postgres_attempts.items() if v.get("ok")), None)
    if working_postgres_path:
        try:
            cred = w.postgres.generate_database_credential(endpoint=working_postgres_path)
            conn = psycopg.connect(
                host=host, port=5432, dbname=database, user=user,
                password=cred.token, sslmode="require", connect_timeout=10,
            )
            with conn.cursor() as cur:
                cur.execute("SELECT current_user")
                row = cur.fetchone()
            conn.close()
            pg_attempts["postgres_sdk_token"] = {"ok": True, "current_user": str(row[0]) if row else None}
        except Exception as e:
            pg_attempts["postgres_sdk_token"] = {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}
    result["pg_connect_attempts"] = pg_attempts

    return result
