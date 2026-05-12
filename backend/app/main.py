"""FastAPI app factory — mounts routers + CORS + lifespan."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import missions, pattern
from app.ws import missions as ws_missions


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown — close Lakebase pool if open
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
