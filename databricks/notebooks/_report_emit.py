"""Notebook → backend `/api/admin/reports/trigger-now` 호출 helper.

Job notebook 안에서 fire-and-forget:
    from _report_emit import emit_trigger
    emit_trigger("gdelt_signal")

trigger_detector가 backend에 있어 notebook은 해당 trigger 타입만 요청.
backend가 실제 detect → LLM call → Lakebase insert까지 처리.

Best-effort: backend 미도달 / LLM 실패 → silent skip (notebook flow 안 막음).

Auth: WorkspaceClient SP OAuth token으로 Apps endpoint 호출.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


# workspace 1개 고정 — env override 가능 (테스트용)
DEFAULT_APPS_URL = "https://crude-compass-7474656526809380.aws.databricksapps.com"


def _apps_url() -> str:
    return os.getenv("APPS_URL") or DEFAULT_APPS_URL


def _auth_header() -> dict[str, str]:
    """Databricks SDK SP OAuth token."""
    try:
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()
        auth = w.config.authenticate()
        token = auth.get("Authorization", "")
        if token:
            return {"Authorization": token}
    except Exception as e:
        logger.warning("_report_emit auth failed: %s", e)
    return {}


def emit_trigger(
    trigger_type: str,
    *,
    force: bool = False,
    timeout: float = 60.0,
) -> dict[str, Any]:
    """`POST /api/admin/reports/trigger-now?trigger_type=X` 호출.

    Args:
        trigger_type: gdelt_signal | price_spike | pattern_drift
        force: 잡힌 거 없어도 dummy 1건 만듦 (demo data 채울 때만)
        timeout: HTTP timeout (LLM call 포함하므로 길게)

    Returns:
        backend response dict (events_detected + results).
        실패 시 {"ok": False, "error": "..."} fallback.
    """
    try:
        import httpx
    except ImportError:
        import subprocess
        import sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "httpx==0.28.1"])
        import httpx

    url = f"{_apps_url()}/api/admin/reports/trigger-now"
    params: dict[str, Any] = {"trigger_type": trigger_type}
    if force:
        params["force"] = "true"
    headers = _auth_header()

    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.post(url, params=params, headers=headers)
        r.raise_for_status()
        result = r.json()
        events = result.get("events_detected", 0)
        oks = sum(1 for x in result.get("results", []) if x.get("ok"))
        logger.info("emit_trigger %s — events_detected=%d ok=%d", trigger_type, events, oks)
        return result
    except Exception as e:
        logger.warning("emit_trigger %s failed: %s", trigger_type, e)
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
