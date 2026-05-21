"""FastAPI app factory — mounts routers + CORS + lifespan."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api import admin as admin_api, daily_reports as daily_reports_api, decision_room as decision_room_api, demo as demo_api, genie as genie_api, jobs as jobs_api, missions, pattern, pulse as pulse_api, reactive as reactive_api, reports as reports_api, signals as signals_api, slack as slack_api, supervisor as supervisor_api
from app.core.config import get_settings
from app.services.slack_bus_subscriber import run_slack_subscriber
from app.services.slack_notify import get_notifier
from app.store import get_bus, get_store
from app.ws import missions as ws_missions, pulse as ws_pulse

logger = logging.getLogger(__name__)

# frontend build output path. backend/app/main.py → project_root/frontend/dist
_FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup — Lakebase D-4 schema migration (idempotent, silent skip on failure)
    try:
        from app.db.lakebase import migrate_d4
        await asyncio.to_thread(migrate_d4)
    except Exception as e:
        logger.warning("Lakebase migrate_d4 wrapper error: %s", e)

    # Decision Room refactor — user_last_seen table
    try:
        from app.db.lakebase import migrate_decision_room
        await asyncio.to_thread(migrate_decision_room)
    except Exception as e:
        logger.warning("Lakebase migrate_decision_room wrapper error: %s", e)

    # Reports model (2026-05-21) — reports + daily_reports tables
    try:
        from app.db.lakebase import migrate_reports
        await asyncio.to_thread(migrate_reports)
    except Exception as e:
        logger.warning("Lakebase migrate_reports wrapper error: %s", e)

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
    app.include_router(reactive_api.router)
    app.include_router(slack_api.router)
    app.include_router(genie_api.router)
    app.include_router(supervisor_api.router)
    app.include_router(admin_api.router)
    app.include_router(pulse_api.router)
    app.include_router(signals_api.router)
    app.include_router(jobs_api.router)
    app.include_router(decision_room_api.router)
    app.include_router(reports_api.router)
    app.include_router(daily_reports_api.router)
    app.include_router(ws_missions.router)
    app.include_router(ws_pulse.router)

    # Demo router — DEMO_MODE=true 일 때만 mount (production 보호)
    settings = get_settings()
    if settings.demo_mode:
        app.include_router(demo_api.router)
        logger.info("demo router mounted (DEMO_MODE=true)")

    @app.get("/api/health")
    async def health() -> dict:
        return {
            "status": "ok",
            "version": __version__,
            "service": "crude-compass-backend",
            "frontend_bundled": _FRONTEND_DIST.exists(),
        }

    # Frontend static serve (production / single-process Apps deploy)
    # Local dev에서는 vite (npm run dev)가 5173 별도, FastAPI는 API만.
    # frontend/dist 존재할 때만 mount — 라우트 우선순위상 모든 /api/* 다음.
    if _FRONTEND_DIST.exists():
        assets_dir = _FRONTEND_DIST / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        @app.api_route(
            "/{full_path:path}",
            methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        )
        async def spa_fallback(full_path: str, request: Request):
            """SPA fallback — 모든 non-API path는 index.html (React Router client-side).

            `/api/*` 등록 안 된 path 또는 non-GET method → 명시적 404
            (catch-all이 GET만 받으면 등록 안 된 POST가 405 Method Not Allowed로
            잘못 답변하는 문제 회피).
            """
            from fastapi import HTTPException
            if full_path.startswith("api/") or full_path.startswith("ws/"):
                raise HTTPException(status_code=404, detail={"code": "NOT_FOUND"})
            if request.method != "GET":
                raise HTTPException(status_code=404, detail={"code": "NOT_FOUND"})
            index = _FRONTEND_DIST / "index.html"
            return FileResponse(str(index))

        logger.info("frontend bundled — static mount %s", _FRONTEND_DIST)
    else:
        logger.info("frontend NOT bundled (local dev or build missing). vite dev server 별도 필요.")

    return app


app = create_app()
