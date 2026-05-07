"""Health check + Lakebase ping. Phase 0 PoC verification."""

from __future__ import annotations

import os

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": "crude-compass-api",
        "env": os.environ.get("CRUDE_COMPASS_ENV", "dev"),
    }


@router.get("/health/lakebase")
async def health_lakebase(request: Request) -> dict:
    """Verify Lakebase OAuth token + connection. Returns 200 only if SELECT 1 succeeds."""
    client = request.app.state.lakebase
    try:
        with client.conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1 AS ok, current_database() AS db")
            row = cur.fetchone()
            return {"status": "ok", "ok": row[0], "db": row[1]}
    except Exception as e:
        return {"status": "error", "error": str(e), "env_pghost": os.environ.get("PGHOST", "<missing>")}
