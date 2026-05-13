"""FastAPI app factory — mounts routers + CORS + lifespan."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import missions, pattern, slack as slack_api
from app.core.config import get_settings
from app.services.slack_bus_subscriber import run_slack_subscriber
from app.services.slack_notify import get_notifier
from app.store import get_bus, get_store
from app.ws import missions as ws_missions

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup — Slack subscriber task (dry-run 모드여도 log 검증용으로 띄움)
    settings = get_settings()
    notifier = get_notifier()
    slack_task = asyncio.create_task(
        run_slack_subscriber(get_bus(), notifier, get_store())
    )
    logger.info(
        "slack subscriber started (enabled=%s, default_channel=%s)",
        settings.slack_enabled, settings.slack_default_channel or "(missing)",
    )
    app.state.slack_task = slack_task

    yield

    # Shutdown
    if not slack_task.done():
        slack_task.cancel()
        try:
            await slack_task
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.warning("slack task cleanup error: %s", e)
    try:
        from app.db.lakebase import close_pool
        close_pool()
    except Exception:
        pass


def create_app() -> FastAPI:
    app = FastAPI(
        title="Crude Compass",
        version=__version__,
        description="Pre-emptive Bidirectional Decision Support Agent",
        lifespan=lifespan,
    )

    # CORS — Apps frontend (local: vite dev server)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(missions.router)
    app.include_router(pattern.router)
    app.include_router(slack_api.router)
    app.include_router(ws_missions.router)

    @app.get("/api/health")
    async def health() -> dict:
        return {
            "status": "ok",
            "version": __version__,
            "service": "crude-compass-backend",
        }

    return app


app = create_app()
