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

    # 4. generate_database_credential — 다양한 path 시도
    attempts: dict[str, Any] = {}
    paths_to_try = [
        "crude-compass-pg",  # project display name
        project_uid,  # project UID
        "primary",  # endpoint display name
        "ep-lucky-star-d1rlmmrr",  # endpoint UID from PGHOST
        "databricks_postgres",  # PG database name
        "db-dxjk-xzuoq7qrwt",  # database UID from resource binding
        "projects/crude-compass-pg",
        "projects/crude-compass-pg/branches/production",
        "projects/crude-compass-pg/branches/production/endpoints/primary",
        "projects/crude-compass-pg/branches/production/endpoints/ep-lucky-star-d1rlmmrr",
    ]
    for name in paths_to_try:
        try:
            cred = w.database.generate_database_credential(
                request_id=str(uuid.uuid4()),
                instance_names=[name],
            )
            attempts[name] = {
                "ok": True,
                "token_prefix": (cred.token or "")[:30],
                "expiration": str(getattr(cred, "expiration_time", None)),
            }
        except Exception as e:
            attempts[name] = {
                "ok": False,
                "error": f"{type(e).__name__}: {str(e)[:200]}",
            }
    result["credential_attempts"] = attempts

    return result
