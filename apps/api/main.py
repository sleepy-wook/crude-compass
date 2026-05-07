"""Crude Compass FastAPI — single process serving Vite dist + /api/* routes.

Databricks Apps deploy: uvicorn binds to $DATABRICKS_APP_PORT.
Local dev: uvicorn on :8000, Vite dev server on :5173 proxies /api → :8000.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from apps.api.routers import health
from apps.api.services.lakebase import LakebaseClient

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.lakebase = LakebaseClient()
    yield


app = FastAPI(title="Crude Compass API", lifespan=lifespan)

# CORS — local dev only (Vite :5173 → FastAPI :8000)
if os.environ.get("CRUDE_COMPASS_ENV", "dev") == "dev":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Routers
app.include_router(health.router, prefix="/api", tags=["health"])

# Static dist serve — production (Databricks Apps)
DIST_DIR = Path(__file__).resolve().parents[1] / "web" / "dist"
if DIST_DIR.exists():
    # html=True → falls back to index.html for client-side routes
    app.mount("/", StaticFiles(directory=str(DIST_DIR), html=True), name="spa")
