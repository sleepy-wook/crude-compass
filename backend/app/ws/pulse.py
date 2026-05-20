"""Pulse WebSocket — /api/ws/pulse. agent_activity_events INSERT 실시간 push.

Server → Client events:
  - connected: {type: connected, ts}
  - pulse:     {mission_id, actor, action, result_preview, metadata, ts}
  - ping:      {type: ping, ts} — 5s keepalive
"""
from __future__ import annotations

import asyncio
import json
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.store import get_pulse_bus

router = APIRouter(tags=["websocket"])

PING_INTERVAL_SEC = 5
EVENT_RECV_TIMEOUT = 1.0


@router.websocket("/api/ws/pulse")
async def ws_pulse(ws: WebSocket) -> None:
    await ws.accept()
    bus = get_pulse_bus()
    queue = await bus.subscribe()

    last_ping = time.time()
    try:
        await ws.send_json({"type": "connected", "ts": time.time()})

        while True:
            # 1) drain pulse events
            try:
                event = await asyncio.wait_for(queue.get(), timeout=EVENT_RECV_TIMEOUT)
                if isinstance(event, dict) and event.get("ts") is None:
                    event = {**event, "ts": time.time()}
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
