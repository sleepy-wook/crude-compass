"""WebSocket route /api/ws/missions — 5초 sync ⭐.

API contract: docs/api_contract.md §5.
Server → Client events:
  - mission.proposed / mission.confirmed / mission.pivoted / mission.updated
  - pattern.changed
  - reactive.alert
  - ping (5s keepalive)
"""
from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.store import get_bus

router = APIRouter(tags=["websocket"])

PING_INTERVAL_SEC = 5
EVENT_RECV_TIMEOUT = 1.0


@router.websocket("/api/ws/missions")
async def ws_missions(ws: WebSocket) -> None:
    await ws.accept()
    bus = get_bus()
    queue = await bus.subscribe()

    last_ping = time.time()
    try:
        # Initial snapshot — let client know it's connected
        await ws.send_json({"type": "connected", "ts": time.time()})

        while True:
            # 1) drain events
            try:
                event = await asyncio.wait_for(queue.get(), timeout=EVENT_RECV_TIMEOUT)
                await ws.send_json(event)
            except asyncio.TimeoutError:
                pass

            # 2) keepalive ping
            now = time.time()
            if now - last_ping > PING_INTERVAL_SEC:
                await ws.send_json({"type": "ping", "ts": now})
                last_ping = now

            # 3) read from client (non-blocking)
            try:
                msg = await asyncio.wait_for(ws.receive_text(), timeout=0.01)
                # pong / subscribe handling — minimal for now
                try:
                    data = json.loads(msg)
                    if data.get("type") == "subscribe":
                        await ws.send_json({"type": "subscribed"})
                except json.JSONDecodeError:
                    pass
            except asyncio.TimeoutError:
                pass

    except WebSocketDisconnect:
        pass
    finally:
        await bus.unsubscribe(queue)
