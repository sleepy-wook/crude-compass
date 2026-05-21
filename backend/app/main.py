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
from app.api import admin as admin_api, daily_reports as daily_reports_api, genie as genie_api, jobs as jobs_api, pattern, pulse as pulse_api, reports as reports_api, signals as signals_api, slack as slack_api, supervisor as supervisor_api
from app.ws import pulse as ws_pulse

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

    # Reports model (2026-05-21) — reports + daily_reports tables
    try:
        from app.db.lakebase import migrate_reports
        await asyncio.to_thread(migrate_reports)
    except Exception as e:
        logger.warning("Lakebase migrate_reports wrapper error: %s", e)

    # Slack Socket Mode — Databricks Apps inbound 401 우회 (outbound WS). no-op if no app_token.
    try:
        from app.api.slack import start_socket_mode
        await start_socket_mode()
    except Exception as e:
        logger.warning("slack socket mode start error: %s", e)

    yield

    # Shutdown
    try:
        from app.api.slack import stop_socket_mode
        await stop_socket_mode()
    except Exception:
        pass
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
    app.include_router(pattern.router)
    app.include_router(slack_api.router)
    app.include_router(genie_api.router)
    app.include_router(supervisor_api.router)
    app.include_router(admin_api.router)
    app.include_router(pulse_api.router)
    app.include_router(signals_api.router)
    app.include_router(jobs_api.router)
    app.include_router(reports_api.router)
    app.include_router(daily_reports_api.router)
    app.include_router(ws_pulse.router)

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
