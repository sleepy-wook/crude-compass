"""FastAPI app + Slack Bolt mount + WebSocket route.

Sprint 1 골격: health endpoint만 동작. 실제 endpoint는 Sprint 4에서 구현.
"""
from __future__ import annotations

from fastapi import FastAPI

from app import __version__


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title="Crude Compass",
        version=__version__,
        description="Pre-emptive Bidirectional Decision Support Agent",
    )

    @app.get("/api/health")
    async def health() -> dict:
        return {
            "status": "ok",
            "version": __version__,
            "lakebase": "not_connected",  # Sprint 4
            "databricks_sdk": "not_connected",  # Sprint 4
        }

    return app


app = create_app()
