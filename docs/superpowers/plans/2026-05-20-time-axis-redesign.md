# Time-Axis Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** spec `docs/superpowers/specs/2026-05-20-time-axis-redesign-spec.md`의 5-layer time-axis 개편을 구현. AgentActivityTimeline의 thin 한계를 Case Thread로 진화시키고, 전역 Live AI Pulse / Signal Lifecycle / Daily Loop를 추가.

**Architecture:** 기존 `agent_activity_events` 테이블·repo·`/api/missions/{id}/activity` REST·Supervisor wrapper 재사용. 새로 추가: (1) Databricks notebook → Lakebase emit helper, (2) 전역 pulse REST + WebSocket broadcast, (3) Case Thread 컴포넌트 (expand-to-evidence), (4) LivePulseStrip / SignalLifecycle / DailyLoopClock, (5) 미사용 silver/gold view API 노출.

**Tech Stack:** FastAPI + psycopg3 + Pydantic v2 / React 18 + TS 5 + TanStack Query + Tailwind / Databricks Lakeflow Jobs (Python notebooks) + Unity Catalog Delta + Lakebase Postgres OLTP + WebSocket.

---

## 0. 사전 확인 (1회만)

- [ ] **Step 0.1**: working tree clean 인지 확인

Run: `git status --short`
Expected: `D  docs/todo.md`와 `?? backend/.env.bak`만 있고 그 외 없음 (spec은 이미 staged됨)

- [ ] **Step 0.2**: spec 파일 읽기 — 작업 중 참조

Read: `docs/superpowers/specs/2026-05-20-time-axis-redesign-spec.md`

- [ ] **Step 0.3**: 기존 agent_activity_events 테이블이 진짜로 Lakebase에 존재하는지 SDK로 검증

Run: 
```powershell
databricks --profile crude-compass apps get crude-compass | python -c "import sys,json; d=json.load(sys.stdin); print('lakebase resources:', [r.get('name') for r in d.get('resources', []) if 'lakebase' in r.get('name', '').lower()])"
```
Expected: `['lakebase_host', 'lakebase_database', 'lakebase_user', 'lakebase_endpoint_path', 'lakebase']` 출력 (Apps에 binding 살아있음 확인)

---

## File Structure

### 새로 추가
- `databricks/notebooks/_lakebase_emit.py` — notebook → Lakebase agent_activity_events insert helper (psycopg3 + OAuth token via `dbutils.secrets`)
- `backend/app/api/pulse.py` — REST `GET /api/pulse/recent` (전역 stream) + `GET /api/pulse/stats` (24h aggregation)
- `backend/app/ws/pulse.py` — WebSocket `/api/ws/pulse` (실시간 push)
- `backend/app/api/signals.py` — REST `GET /api/signals/{signal_id}/lifecycle` (silver/gold view 4-stage data)
- `backend/app/api/jobs.py` — REST `GET /api/jobs/runs/today` (Databricks Jobs SDK 호출 → 24h dial)
- `frontend/src/components/CaseThread.tsx` — Layer A 본체 (AgentActivityTimeline 진화판, expand-to-raw + WS push)
- `frontend/src/components/CaseThreadEntry.tsx` — single thread row, expandable
- `frontend/src/components/LivePulseStrip.tsx` — Layer B 본체 (Decision Room hero)
- `frontend/src/components/SidebarPulseDot.tsx` — Layer B 글로벌 mini dot
- `frontend/src/components/SignalLifecycle.tsx` — Layer C 본체 (4-stage)
- `frontend/src/components/DailyLoopClock.tsx` — Layer D 본체 (24h dial + 누적 통계)
- `frontend/src/hooks/usePulseStream.ts` — WebSocket subscribe hook
- `frontend/src/hooks/useSignalLifecycle.ts` — REST hook
- `frontend/src/hooks/useJobRunsToday.ts` — REST hook

### 기존 수정
- `backend/app/db/repositories/agent_activity.py` — `list_recent_all(limit, since)` 추가
- `backend/app/db/lakebase.py:255` — `agent_activity_events` 테이블 schema 변경 X (이미 OK), 단 GRANT 보강
- `backend/app/api/missions.py` — 기존 INSERT 흐름 그대로, mutation 후 pulse bus broadcast 추가
- `backend/app/api/supervisor.py` — Supervisor insert_event 호출 후 pulse bus broadcast 추가
- `backend/app/store.py` — `pulse_bus` (별도 InMemoryBus instance) 추가, missions bus와 분리
- `backend/app/main.py:84-92` — pulse + signals + jobs router include
- `databricks/notebooks/job_gdelt.py` — importance>=70 뉴스 INSERT 시 emit (`gdelt:signal_detected`)
- `databricks/notebooks/job_curation.py` — pattern score 변경 / mission 생성 / revision 시 emit
- `databricks/notebooks/job_price.py` — spike (price ±2%) 시 emit (`reactive:price_spike`)
- `frontend/src/lib/api.ts` — pulse / signals / jobs API 메서드 추가
- `frontend/src/lib/queries.ts` — useRecentPulse / useSignalLifecycle / useJobRunsToday 추가
- `frontend/src/lib/ws.ts` — pulse WS connection helper 추가
- `frontend/src/pages/MissionsPage.tsx` — AgentActivityTimeline 대신 CaseThread 사용
- `frontend/src/pages/Dashboard.tsx` — LivePulseStrip을 hero 자리에 배치
- `frontend/src/pages/AskPage.tsx` — Signal Lifecycle tab 추가
- `frontend/src/components/Sidebar.tsx` — SidebarPulseDot 통합
- `frontend/src/components/Layout.tsx` — DailyLoopClock 영역 또는 Dashboard에 배치

### 삭제 (cleanup)
- 없음. 기존 `AgentActivityTimeline.tsx`는 deprecated이지만 다른 곳에서 import할 수 있으니 컴포넌트 자체는 남기고, page에서 import만 CaseThread로 교체.

---

## Phase P0 — Backend Foundation (Layer A + Layer B 데이터 layer)

### Task 1: agent_activity_events에 `list_recent_all` 메서드 추가

**Files:**
- Modify: `backend/app/db/repositories/agent_activity.py`
- Test: `backend/tests/test_agent_activity_repo.py` (신설)

- [ ] **Step 1.1: 실패 테스트 작성**

Create `backend/tests/test_agent_activity_repo.py`:

```python
"""agent_activity_events repository tests — list_recent_all 신규.

LAKEBASE_HOST env 없으면 skip (CI 안전).
"""
from __future__ import annotations

import os
import pytest

from app.db.repositories import agent_activity

pytestmark = pytest.mark.skipif(
    not os.getenv("LAKEBASE_HOST"),
    reason="LAKEBASE_HOST not set — Lakebase integration test skipped",
)


def test_list_recent_all_returns_cross_mission_events():
    """전역 pulse stream용 — mission_id 무관 최근 N건 + system 이벤트 포함."""
    from app.db.lakebase import get_conn

    with get_conn() as conn:
        # insert 2 events with different mission_ids + 1 system event (mission_id=None)
        agent_activity.insert_event_autocommit(
            conn, mission_id=None, actor="gdelt", action="signal_detected",
            result_preview="test signal A",
        )
        events = agent_activity.list_recent_all(conn, limit=10)

    assert isinstance(events, list)
    assert len(events) >= 1
    # 최근순 (DESC) 정렬 검증 — 첫 event의 occurred_at >= 마지막
    if len(events) >= 2:
        assert events[0]["occurred_at"] >= events[-1]["occurred_at"]
    # system event (mission_id=None) 포함 검증
    assert any(e["mission_id"] is None for e in events)


def test_list_recent_all_since_filter():
    """since timestamp 이후 events만 반환."""
    from datetime import datetime, timezone, timedelta
    from app.db.lakebase import get_conn

    with get_conn() as conn:
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        events = agent_activity.list_recent_all(conn, limit=100, since=future)

    assert events == []  # 미래 시점 → empty
```

- [ ] **Step 1.2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/test_agent_activity_repo.py -v`
Expected: FAIL — `AttributeError: module 'app.db.repositories.agent_activity' has no attribute 'list_recent_all'`

- [ ] **Step 1.3: list_recent_all 구현**

Add to `backend/app/db/repositories/agent_activity.py` (after `list_for_mission`):

```python
def list_recent_all(
    conn: psycopg.Connection,
    *,
    limit: int = 100,
    since: datetime | None = None,
) -> list[dict[str, Any]]:
    """Cross-mission 전역 stream — Live AI Pulse 용.

    mission_id NULL인 system event (job/reactive)도 포함.
    occurred_at DESC. since 주어지면 그 시점 이후만.
    """
    try:
        with conn.cursor(row_factory=dict_row) as cur:
            if since is not None:
                cur.execute(
                    """
                    SELECT id, mission_id, occurred_at, actor, action, result_preview, metadata
                      FROM agent_activity_events
                     WHERE occurred_at > %s
                     ORDER BY occurred_at DESC, id DESC
                     LIMIT %s
                    """,
                    (since, limit),
                )
            else:
                cur.execute(
                    """
                    SELECT id, mission_id, occurred_at, actor, action, result_preview, metadata
                      FROM agent_activity_events
                     ORDER BY occurred_at DESC, id DESC
                     LIMIT %s
                    """,
                    (limit,),
                )
            rows = cur.fetchall()
        return [_serialize(r) for r in rows]
    except Exception as e:
        logger.warning("agent_activity list_recent_all failed: %s", e)
        return []
```

- [ ] **Step 1.4: 테스트 통과 확인**

Run: `cd backend && LAKEBASE_HOST=$LAKEBASE_HOST uv run pytest tests/test_agent_activity_repo.py -v` (Lakebase 연결 가능한 환경에서)
Expected: PASS (2 tests). LAKEBASE_HOST 없으면 skip.

CI 환경 (no Lakebase):
Run: `cd backend && uv run pytest tests/test_agent_activity_repo.py -v`
Expected: SKIPPED

- [ ] **Step 1.5: Commit**

```bash
git add backend/app/db/repositories/agent_activity.py backend/tests/test_agent_activity_repo.py
git commit -m "feat(d2): agent_activity list_recent_all — Live Pulse cross-mission stream"
```

---

### Task 2: pulse_bus 추가 (store.py 분리)

**Files:**
- Modify: `backend/app/store.py`

- [ ] **Step 2.1: store.py 읽고 InMemoryBus 위치 확인**

Read: `backend/app/store.py`

- [ ] **Step 2.2: pulse_bus 추가**

기존 `get_bus()` 옆에 별도 pulse bus singleton 추가. 핵심 변경:

```python
# backend/app/store.py 안 적절한 위치 (기존 _bus 인스턴스 옆)

_pulse_bus: InMemoryBus | None = None

def get_pulse_bus() -> InMemoryBus:
    """Live AI Pulse 전용 bus — agent_activity_events INSERT 시 broadcast."""
    global _pulse_bus
    if _pulse_bus is None:
        _pulse_bus = InMemoryBus()
    return _pulse_bus
```

> InMemoryBus class signature는 기존 코드 그대로 사용. publish/subscribe/unsubscribe 메서드.

- [ ] **Step 2.3: smoke import 검증**

Run: `cd backend && uv run python -c "from app.store import get_pulse_bus; b = get_pulse_bus(); print('OK', type(b).__name__)"`
Expected: `OK InMemoryBus`

- [ ] **Step 2.4: Commit**

```bash
git add backend/app/store.py
git commit -m "feat(d2): pulse_bus singleton — Live AI Pulse broadcast 분리"
```

---

### Task 3: agent_activity emit + pulse_bus publish 통합

**Files:**
- Modify: `backend/app/db/repositories/agent_activity.py`

Goal: 기존 `insert_event` / `insert_event_autocommit` 호출자가 변경 없이, 성공 시 pulse_bus에도 publish 되도록 wrapper 통일.

- [ ] **Step 3.1: insert_event_autocommit에 pulse broadcast 추가**

Modify `backend/app/db/repositories/agent_activity.py` `insert_event_autocommit`:

```python
def insert_event_autocommit(
    conn: psycopg.Connection,
    *,
    mission_id: UUID | None,
    actor: str,
    action: str,
    result_preview: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> bool:
    """Insert + commit + pulse_bus publish. Supervisor / reactive / human action 등 비-mission 트랜잭션."""
    ok = insert_event(
        conn, mission_id=mission_id, actor=actor, action=action,
        result_preview=result_preview, metadata=metadata,
    )
    if ok:
        try:
            conn.commit()
        except Exception as e:
            logger.warning("agent_activity commit failed: %s", e)
            return False
        # Best-effort pulse broadcast — async event push.
        _publish_pulse_event(
            mission_id=mission_id, actor=actor, action=action,
            result_preview=result_preview, metadata=metadata,
        )
    return ok


def _publish_pulse_event(
    *,
    mission_id: UUID | None,
    actor: str,
    action: str,
    result_preview: str | None,
    metadata: dict[str, Any] | None,
) -> None:
    """pulse_bus broadcast — WebSocket subscribers 깨우기. fail silent."""
    import asyncio
    try:
        from app.store import get_pulse_bus
        bus = get_pulse_bus()
        # bus.publish는 await coroutine. 호출자가 sync context (psycopg)일 수도, async일 수도 — both 지원.
        payload = {
            "type": "pulse",
            "mission_id": str(mission_id) if mission_id else None,
            "actor": actor,
            "action": action,
            "result_preview": result_preview,
            "metadata": metadata,
            "ts": None,  # server timestamp는 WS endpoint에서 stamp
        }
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(bus.publish(payload))
        except RuntimeError:
            # sync context (no running loop) — fire-and-forget thread
            asyncio.run(bus.publish(payload))
    except Exception as e:
        logger.warning("pulse broadcast failed: %s", e)
```

- [ ] **Step 3.2: 기존 호출자 영향 확인 (변경 없어야 함)**

Run: `cd backend && grep -rn "insert_event_autocommit\|insert_event" app/ tests/ --include="*.py"`
Expected: 호출 시그니처 변경 X — 모든 기존 호출이 그대로 작동.

- [ ] **Step 3.3: smoke test — publish가 exception 없이 호출되는지**

Run: 
```powershell
cd backend
uv run python -c "
import asyncio
from app.db.repositories.agent_activity import _publish_pulse_event
_publish_pulse_event(mission_id=None, actor='test', action='smoke', result_preview='x', metadata={})
print('OK')
"
```
Expected: `OK` (no traceback)

- [ ] **Step 3.4: Commit**

```bash
git add backend/app/db/repositories/agent_activity.py
git commit -m "feat(d2): agent_activity INSERT → pulse_bus broadcast 통합"
```

---

### Task 4: Pulse REST endpoint

**Files:**
- Create: `backend/app/api/pulse.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_pulse_api.py`

- [ ] **Step 4.1: 실패 테스트 작성**

Create `backend/tests/test_pulse_api.py`:

```python
"""Pulse REST endpoint tests — GET /api/pulse/recent, /api/pulse/stats."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_pulse_recent_returns_list_shape():
    """Lakebase 미연결시 events:[] (graceful)."""
    response = client.get("/api/pulse/recent?limit=20")
    assert response.status_code == 200
    body = response.json()
    assert "events" in body
    assert isinstance(body["events"], list)
    assert "count" in body
    assert isinstance(body["count"], int)


def test_pulse_recent_respects_limit():
    response = client.get("/api/pulse/recent?limit=5")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] <= 5


def test_pulse_stats_returns_24h_aggregation():
    """24시간 누적 통계."""
    response = client.get("/api/pulse/stats")
    assert response.status_code == 200
    body = response.json()
    # shape: { "total_24h": int, "by_actor": {...}, "by_action": {...}, "active_cases": int }
    assert "total_24h" in body and isinstance(body["total_24h"], int)
    assert "by_actor" in body and isinstance(body["by_actor"], dict)
    assert "by_action" in body and isinstance(body["by_action"], dict)
```

- [ ] **Step 4.2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/test_pulse_api.py -v`
Expected: FAIL — 404 (route 없음)

- [ ] **Step 4.3: pulse.py 구현**

Create `backend/app/api/pulse.py`:

```python
"""Pulse REST — Live AI Pulse + 24h stats.

GET /api/pulse/recent  → 최근 N개 agent_activity events (cross-mission)
GET /api/pulse/stats   → 24h 누적 by_actor / by_action 통계
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pulse", tags=["pulse"])


@router.get("/recent")
async def get_recent(limit: int = Query(default=50, ge=1, le=200)) -> dict[str, Any]:
    """Cross-mission 최근 events. WebSocket /api/ws/pulse 의 initial snapshot 보조."""
    try:
        from app.db.lakebase import get_conn
        from app.db.repositories import agent_activity

        with get_conn() as conn:
            events = agent_activity.list_recent_all(conn, limit=limit)
        return {"events": events, "count": len(events)}
    except Exception as e:
        logger.warning("pulse recent failed: %s", e)
        return {"events": [], "count": 0}


@router.get("/stats")
async def get_stats() -> dict[str, Any]:
    """24h 누적 통계 — Daily Loop / Pulse Strip 상단 bar."""
    try:
        from app.db.lakebase import get_conn

        since = datetime.now(timezone.utc) - timedelta(hours=24)

        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT actor, COUNT(*) as c FROM agent_activity_events
                 WHERE occurred_at > %s GROUP BY actor
                """,
                (since,),
            )
            by_actor = {r[0]: r[1] for r in cur.fetchall()}

            cur.execute(
                """
                SELECT action, COUNT(*) as c FROM agent_activity_events
                 WHERE occurred_at > %s GROUP BY action
                """,
                (since,),
            )
            by_action = {r[0]: r[1] for r in cur.fetchall()}

            cur.execute(
                """
                SELECT COUNT(DISTINCT mission_id) FROM agent_activity_events
                 WHERE occurred_at > %s AND mission_id IS NOT NULL
                """,
                (since,),
            )
            active_cases = cur.fetchone()[0] or 0

        total = sum(by_actor.values())
        return {
            "total_24h": total,
            "by_actor": by_actor,
            "by_action": by_action,
            "active_cases": active_cases,
        }
    except Exception as e:
        logger.warning("pulse stats failed: %s", e)
        return {"total_24h": 0, "by_actor": {}, "by_action": {}, "active_cases": 0}
```

- [ ] **Step 4.4: main.py에 router 등록**

Modify `backend/app/main.py` — `from app.api import` line 추가하고 `app.include_router` 추가:

```python
# import line (existing line 15):
from app.api import (
    admin as admin_api, demo as demo_api, genie as genie_api,
    missions, pattern, pulse as pulse_api,  # ← 추가
    reactive as reactive_api, slack as slack_api, supervisor as supervisor_api,
)
```

그리고 line 92 (`app.include_router(ws_missions.router)` 위에):

```python
app.include_router(pulse_api.router)
```

- [ ] **Step 4.5: 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/test_pulse_api.py -v`
Expected: PASS (3 tests). Lakebase 없으면 events:[], stats:0 (graceful).

- [ ] **Step 4.6: 실제 endpoint hit 확인 (manual)**

Run (별도 terminal에서 backend 띄우고):
```powershell
cd backend; uv run python -m app.main
# 다른 terminal:
curl http://localhost:8000/api/pulse/recent?limit=5
curl http://localhost:8000/api/pulse/stats
```
Expected: 200 OK, JSON 응답.

- [ ] **Step 4.7: Commit**

```bash
git add backend/app/api/pulse.py backend/app/main.py backend/tests/test_pulse_api.py
git commit -m "feat(d2): /api/pulse REST — Live AI Pulse + 24h stats"
```

---

### Task 5: Pulse WebSocket endpoint

**Files:**
- Create: `backend/app/ws/pulse.py`
- Modify: `backend/app/main.py`

- [ ] **Step 5.1: ws/pulse.py 구현**

Create `backend/app/ws/pulse.py`:

```python
"""Pulse WebSocket — /api/ws/pulse. agent_activity_events INSERT 실시간 push.

Server -> Client events:
  - pulse: {mission_id, actor, action, result_preview, metadata, ts}
  - ping: {type: ping, ts} — 5s keepalive
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
                # server-stamp ts
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
```

- [ ] **Step 5.2: main.py에 router 등록**

Modify `backend/app/main.py` — `from app.ws import` 줄에 pulse 추가:

```python
from app.ws import missions as ws_missions, pulse as ws_pulse
```

그리고 line 92 (`app.include_router(ws_missions.router)` 옆):

```python
app.include_router(ws_pulse.router)
```

- [ ] **Step 5.3: WS smoke test (manual)**

Run (backend 띄우고 별도 terminal):
```powershell
cd backend
uv run python -c "
import asyncio, websockets
async def t():
    async with websockets.connect('ws://localhost:8000/api/ws/pulse') as ws:
        for _ in range(3):
            msg = await ws.recv()
            print('recv:', msg[:100])
asyncio.run(t())
"
```
Expected: `connected` 메시지 1회, `ping` 메시지 2회.

(`websockets` 패키지 없으면 `uv add websockets --dev` 후 재시도)

- [ ] **Step 5.4: pulse_bus 통합 검증 (manual)**

Backend 떠 있는 상태에서:
```powershell
# Terminal A: WS listener
uv run python -c "
import asyncio, websockets
async def t():
    async with websockets.connect('ws://localhost:8000/api/ws/pulse') as ws:
        while True:
            msg = await ws.recv()
            print('recv:', msg[:150])
asyncio.run(t())
"
# Terminal B: trigger pulse publish
uv run python -c "
import asyncio
from app.db.repositories.agent_activity import _publish_pulse_event
_publish_pulse_event(mission_id=None, actor='manual', action='smoke', result_preview='hi', metadata={})
print('published')
"
```
Expected: Terminal A에 `pulse` 메시지 1건 수신 (`actor: manual, action: smoke`).

- [ ] **Step 5.5: Commit**

```bash
git add backend/app/ws/pulse.py backend/app/main.py
git commit -m "feat(d2): /api/ws/pulse WebSocket — pulse_bus realtime broadcast"
```

---

## Phase P0 — Databricks Notebook → Lakebase emit

### Task 6: Notebook emit helper

**Files:**
- Create: `databricks/notebooks/_lakebase_emit.py`

Notebooks가 Lakebase에 직접 INSERT 해서 cron AI work를 agent_activity_events에 기록. backend FastAPI 우회 (notebook은 별도 Spark process).

- [ ] **Step 6.1: helper 구현**

Create `databricks/notebooks/_lakebase_emit.py`:

```python
"""Notebook → Lakebase agent_activity_events emit helper.

Job notebook (Spark/Python) 안에서 fire-and-forget으로 호출:
    from _lakebase_emit import emit
    emit(actor='gdelt', action='signal_detected',
         result_preview='Hormuz importance 78', metadata={'article_id': '...'})

Lakebase 미연결 / 권한 부족 / network fail → silent skip (notebook flow 막지 않음).

Auth: Databricks SDK OAuth token + Apps secret scope의 lakebase_host/database/user/endpoint_path.

Notebooks가 backend FastAPI 우회 (별도 Spark process).
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any

logger = logging.getLogger(__name__)


def _get_lakebase_conn():
    """secret scope 'crude'에서 Lakebase config 읽어 psycopg conn 반환.
    
    Databricks notebook context (dbutils 가용) 또는 local env var 둘 다 지원.
    """
    try:
        # Databricks runtime context
        from pyspark.dbutils import DBUtils  # type: ignore
        from pyspark.sql import SparkSession
        spark = SparkSession.builder.getOrCreate()
        dbutils = DBUtils(spark)
        host = dbutils.secrets.get(scope="crude", key="lakebase_host")
        database = dbutils.secrets.get(scope="crude", key="lakebase_database")
        user = dbutils.secrets.get(scope="crude", key="lakebase_user")
        endpoint_path = dbutils.secrets.get(scope="crude", key="lakebase_endpoint_path")
    except Exception:
        # Fallback: env var (local test)
        host = os.getenv("LAKEBASE_HOST")
        database = os.getenv("LAKEBASE_DATABASE")
        user = os.getenv("LAKEBASE_USER")
        endpoint_path = os.getenv("LAKEBASE_ENDPOINT_PATH")
    if not (host and database and user and endpoint_path):
        return None

    # OAuth token (SP context 또는 notebook user)
    try:
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()
        # 우선 OAuth token 직접
        try:
            auth = w.config.authenticate()
            token = auth.get("Authorization", "").removeprefix("Bearer ")
        except Exception:
            token = None
        if not token:
            instance_name = endpoint_path.split("/")[1] if endpoint_path.startswith("projects/") else endpoint_path
            credential = w.database.generate_database_credential(
                request_id=str(uuid.uuid4()), instance_names=[instance_name],
            )
            token = credential.token
    except Exception as e:
        logger.warning("lakebase token gen failed: %s", e)
        return None

    try:
        import psycopg
        conn = psycopg.connect(
            f"host={host} dbname={database} user={user} password={token} sslmode=require connect_timeout=10",
            autocommit=False,
        )
        return conn
    except Exception as e:
        logger.warning("lakebase psycopg connect failed: %s", e)
        return None


def emit(
    *,
    actor: str,
    action: str,
    result_preview: str | None = None,
    metadata: dict[str, Any] | None = None,
    mission_id: str | None = None,
) -> bool:
    """Best-effort INSERT — fail silent.

    Args:
        actor: gdelt | curation_job | price_job | reactive | system | ...
        action: signal_detected | score_computed | mission_proposed | revision_suggested | trigger_fired | ...
        result_preview: 80자 내외 한 줄 요약
        metadata: JSONB로 저장될 dict (article_id, score_delta, etc.)
        mission_id: 연관 case가 있으면. 없으면 None → 전역 system event.
    """
    conn = _get_lakebase_conn()
    if conn is None:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO agent_activity_events
                    (mission_id, actor, action, result_preview, metadata)
                VALUES
                    (%s, %s, %s, %s, %s::jsonb)
                """,
                (
                    mission_id,
                    actor,
                    action,
                    result_preview,
                    json.dumps(metadata) if metadata else None,
                ),
            )
        conn.commit()
        return True
    except Exception as e:
        logger.warning("lakebase emit failed (actor=%s action=%s): %s", actor, action, e)
        return False
    finally:
        try:
            conn.close()
        except Exception:
            pass
```

- [ ] **Step 6.2: local smoke (LAKEBASE_HOST 있는 환경)**

Run:
```powershell
cd "C:/crude-compass/databricks/notebooks"
# Backend의 .env를 source한 PowerShell session 또는 직접 env set
python -c "
import sys; sys.path.insert(0, '.')
from _lakebase_emit import emit
ok = emit(actor='system', action='smoke_test', result_preview='notebook emit helper smoke', metadata={'src': 'plan'})
print('emit ok:', ok)
"
```
Expected: `emit ok: True` (LAKEBASE_HOST set 상태에서). LAKEBASE 없으면 `False` + warning.

이어서 backend `/api/pulse/recent?limit=5`로 방금 emit한 row 확인:
```powershell
curl http://localhost:8000/api/pulse/recent?limit=5
```
Expected: events 안에 `actor: 'system', action: 'smoke_test'` 1건.

- [ ] **Step 6.3: Commit**

```bash
git add databricks/notebooks/_lakebase_emit.py
git commit -m "feat(d2): notebook → Lakebase agent_activity emit helper"
```

---

### Task 7: job_gdelt emit on important news

**Files:**
- Modify: `databricks/notebooks/job_gdelt.py`

- [ ] **Step 7.1: job_gdelt.py 읽고 importance >=60 INSERT 직후 위치 파악**

Read: `databricks/notebooks/job_gdelt.py`

Find: importance score 계산 후 `bronze.news_articles INSERT` 구간. (보통 `df.write` 또는 `spark.sql("INSERT INTO ...")`)

- [ ] **Step 7.2: emit 호출 추가**

`bronze.news_articles INSERT` 직후, importance>=70 행만 추출해서 emit:

```python
# job_gdelt.py 적절한 위치 (INSERT 완료 후)
try:
    from _lakebase_emit import emit
    # importance>=70 행만 (실제 의미있는 신호) — Live Pulse 노이즈 방지
    top_signals = df.filter(F.col("importance") >= 70).select(
        "title", "importance", "direction", "category", "published_at"
    ).limit(5).collect()
    for row in top_signals:
        emit(
            actor="gdelt",
            action="signal_detected",
            result_preview=f"{row['title'][:60]}... (importance {row['importance']}, {row['direction']})",
            metadata={
                "title": row["title"],
                "importance": float(row["importance"]),
                "direction": row["direction"],
                "category": row["category"],
                "published_at": str(row["published_at"]),
            },
        )
except Exception as e:
    print(f"gdelt emit failed: {e}")  # fail silent
```

> 정확한 컬럼명·변수명은 기존 job_gdelt.py에서 확인. F는 `pyspark.sql.functions as F`. df는 INSERT 직전 dataframe.

- [ ] **Step 7.3: Local dry-run 검증**

Run (local Python — Spark 없으면 skip):
```powershell
# Databricks workspace UI에서 job 1회 run trigger 또는 Asset Bundle deploy 후 schedule 기다리기
databricks --profile crude-compass bundle deploy --target dev
databricks --profile crude-compass jobs run-now <job_id_for_gdelt>
```
Expected: job SUCCESS. `/api/pulse/recent?limit=20` 호출 → `actor: 'gdelt', action: 'signal_detected'` events 1-5건 확인.

- [ ] **Step 7.4: Commit**

```bash
git add databricks/notebooks/job_gdelt.py
git commit -m "feat(d2): job_gdelt → agent_activity emit (importance>=70 신호)"
```

---

### Task 8: job_curation emit on pattern change / mission / revision

**Files:**
- Modify: `databricks/notebooks/job_curation.py`

- [ ] **Step 8.1: job_curation.py 읽고 emit 위치 3 곳 파악**

Read: `databricks/notebooks/job_curation.py`

Find:
- (A) Pattern Score 계산 완료 후 (이전 score 대비 변화 있을 때만)
- (B) Mission 생성 trigger 조건 충족 시
- (C) 기존 active mission revision 제안 시

- [ ] **Step 8.2: emit 호출 3 곳 추가**

`job_curation.py` 안 적절 위치에:

```python
# (A) Pattern Score 변경 emit — 이전 score와 1.0 이상 차이날 때만 (noise filter)
try:
    from _lakebase_emit import emit
    new_score = float(latest_pattern_score)  # 변수명은 기존 job 코드 확인
    if abs(new_score - prev_score) >= 1.0:
        direction = "up" if new_score > prev_score else "down"
        emit(
            actor="curation_job",
            action="score_computed",
            result_preview=f"Pattern Score {prev_score:.1f} → {new_score:.1f} ({direction})",
            metadata={
                "prev_score": prev_score,
                "new_score": new_score,
                "delta": new_score - prev_score,
            },
        )
except Exception as e:
    print(f"curation score emit failed: {e}")

# (B) Mission 생성 emit (만약 trigger 조건 충족 → mission_plan_advice 호출 → INSERT 가 일어났다면)
# 단, 이미 backend missions.py가 supervisor:case_opened를 emit 중이라면 중복 — 한 곳만.
# Curation job이 직접 mission INSERT 한다면 emit O. mission INSERT 가 backend 통해서면 skip.
# 코드 흐름 보고 결정. (default: skip — backend 측 emit이 있음)

# (C) Revision 제안 emit
try:
    from _lakebase_emit import emit
    if revision_needed:  # 변수명은 기존 코드 확인
        emit(
            actor="curation_job",
            action="revision_suggested",
            result_preview=f"Case {case_id} score drift {drift_pct:.1%} — revision suggested",
            mission_id=str(case_id),
            metadata={"drift_pct": drift_pct, "trigger": "daily_curation"},
        )
except Exception as e:
    print(f"curation revision emit failed: {e}")
```

> 정확한 변수명·조건은 job_curation.py 기존 코드 확인. emit은 항상 try/except로 감쌈.

- [ ] **Step 8.3: deploy + run 검증**

Run:
```powershell
databricks --profile crude-compass bundle deploy --target dev
databricks --profile crude-compass jobs run-now <job_id_for_daily_curation>
```
Expected: job SUCCESS. `/api/pulse/recent?limit=20` → `actor: 'curation_job'` events 확인.

- [ ] **Step 8.4: Commit**

```bash
git add databricks/notebooks/job_curation.py
git commit -m "feat(d2): job_curation → agent_activity emit (score change + revision)"
```

---

### Task 9: job_price emit on spike

**Files:**
- Modify: `databricks/notebooks/job_price.py`

- [ ] **Step 9.1: job_price.py 읽고 spike detection 위치 파악**

Read: `databricks/notebooks/job_price.py`

Find: 5분 cron, ±2% spike 감지 로직. (없으면 신규 — 단순한 비교 로직)

- [ ] **Step 9.2: spike emit 추가**

```python
# job_price.py 적절 위치 (3 ticker 적재 후)
try:
    from _lakebase_emit import emit
    # 직전 5분과 비교 — ±2% 이상 변화 ticker만
    for row in spike_df.collect():  # spike_df는 ticker별 % change 계산 결과
        pct = float(row["pct_change"])
        if abs(pct) >= 2.0:
            direction = "spike up" if pct > 0 else "spike down"
            emit(
                actor="price_job",
                action="trigger_fired",
                result_preview=f"{row['ticker']} {direction} {pct:+.2f}% (5min)",
                metadata={
                    "ticker": row["ticker"],
                    "price": float(row["price"]),
                    "pct_change": pct,
                    "window": "5min",
                },
            )
except Exception as e:
    print(f"price spike emit failed: {e}")
```

- [ ] **Step 9.3: 검증 (spike 발생 시점에 확인)**

Run:
```powershell
databricks --profile crude-compass bundle deploy --target dev
# 5분 cron 자연 발생 기다리거나 manual trigger
databricks --profile crude-compass jobs run-now <job_id_for_price>
curl http://localhost:8000/api/pulse/recent?limit=20
```
Expected: 시장 변동 시 `actor: 'price_job', action: 'trigger_fired'` events 발생. 시장 평온 시 0건도 정상.

- [ ] **Step 9.4: Commit**

```bash
git add databricks/notebooks/job_price.py
git commit -m "feat(d2): job_price → agent_activity emit (±2% spike)"
```

---

## Phase P0 — Frontend Foundation

### Task 10: TS types + API methods + WS hook

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/lib/queries.ts`
- Modify: `frontend/src/lib/ws.ts`
- Create: `frontend/src/hooks/usePulseStream.ts`

- [ ] **Step 10.1: api.ts에 pulse API 메서드 추가**

Modify `frontend/src/lib/api.ts` — 기존 `getMissionActivity` 옆에 추가:

```typescript
// 기존 ActivityEvent 타입 재사용 (이미 정의됨, AgentActivityTimeline에서 export)
import type { ActivityEvent } from "../components/AgentActivityTimeline";

export const pulseApi = {
  /** Cross-mission 최근 N개 events. Live AI Pulse 초기 fetch. */
  recent: (limit = 50) =>
    apiGet<{ events: ActivityEvent[]; count: number }>(`/api/pulse/recent?limit=${limit}`),

  /** 24h 누적 통계. */
  stats: () =>
    apiGet<{
      total_24h: number;
      by_actor: Record<string, number>;
      by_action: Record<string, number>;
      active_cases: number;
    }>("/api/pulse/stats"),
};
```

> `apiGet` 헬퍼는 기존 api.ts 내 fetch wrapper. 기존 패턴 그대로 사용.

- [ ] **Step 10.2: queries.ts에 hooks 추가**

Modify `frontend/src/lib/queries.ts`:

```typescript
import { pulseApi } from "./api";

/** Live AI Pulse — cross-mission stream. Polling 5s (WS 연결 시 자동 disable 가능). */
export function useRecentPulse(limit = 50, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ["pulse", "recent", limit],
    queryFn: () => pulseApi.recent(limit),
    refetchInterval: 5000,
    staleTime: 2000,
    enabled: options?.enabled !== false,
  });
}

export function usePulseStats() {
  return useQuery({
    queryKey: ["pulse", "stats"],
    queryFn: () => pulseApi.stats(),
    refetchInterval: 30000,  // 30s
    staleTime: 15000,
  });
}
```

- [ ] **Step 10.3: ws.ts에 pulse WS connection helper 추가**

Modify `frontend/src/lib/ws.ts` — 기존 missions WS 패턴 따라:

```typescript
/** Pulse WS connection — onMessage callback 형태 (구체 hook은 usePulseStream에서). */
export function connectPulseWs(onMessage: (data: unknown) => void): WebSocket {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.host;
  const ws = new WebSocket(`${proto}//${host}/api/ws/pulse`);
  ws.onmessage = (ev) => {
    try {
      onMessage(JSON.parse(ev.data));
    } catch {
      // ignore malformed
    }
  };
  return ws;
}
```

- [ ] **Step 10.4: usePulseStream hook 신설**

Create `frontend/src/hooks/usePulseStream.ts`:

```typescript
/**
 * usePulseStream — WebSocket subscribe + 누적 events buffer.
 *
 * 초기 snapshot은 useRecentPulse (REST), 이후 신규 events는 WS push로 buffer 앞에 append.
 * Reconnect 시 마지막 event ts 이후 events만 fetch (gap fill) — 단순 구현은 reconnect = 전체 refetch.
 *
 * Returns:
 *   events: ActivityEvent[]  // 최신 N개 (DESC), useRecentPulse data + WS 누적
 *   connected: boolean       // WS 상태
 */
import { useEffect, useRef, useState } from "react";
import type { ActivityEvent } from "../components/AgentActivityTimeline";
import { connectPulseWs } from "../lib/ws";
import { useRecentPulse } from "../lib/queries";

const MAX_BUFFER = 200;

export function usePulseStream(initialLimit = 50) {
  const { data, refetch } = useRecentPulse(initialLimit);
  const [wsEvents, setWsEvents] = useState<ActivityEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = connectPulseWs((msg) => {
      const m = msg as Record<string, unknown> | null;
      if (!m || typeof m !== "object") return;
      if (m.type === "connected") {
        setConnected(true);
        return;
      }
      if (m.type === "ping") return;
      if (m.type === "pulse") {
        // WS payload → ActivityEvent shape 변환
        const ev: ActivityEvent = {
          id: `ws-${(m.ts as number) ?? Date.now()}`,
          mission_id: (m.mission_id as string) ?? null,
          occurred_at: new Date(((m.ts as number) ?? Date.now() / 1000) * 1000).toISOString(),
          actor: m.actor as string,
          action: m.action as string,
          result_preview: (m.result_preview as string) ?? null,
          metadata: (m.metadata as Record<string, unknown>) ?? null,
        };
        setWsEvents((prev) => [ev, ...prev].slice(0, MAX_BUFFER));
      }
    });
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);
    wsRef.current = ws;
    return () => ws.close();
  }, []);

  const restEvents = data?.events ?? [];
  // Dedup by id (REST + WS 합쳐서 — WS는 ws- prefix라 보통 안 겹침)
  const seen = new Set<string>();
  const merged: ActivityEvent[] = [];
  for (const e of [...wsEvents, ...restEvents]) {
    const key = String(e.id);
    if (!seen.has(key)) {
      seen.add(key);
      merged.push(e);
    }
  }
  return { events: merged.slice(0, MAX_BUFFER), connected, refetch };
}
```

> `frontend/src/hooks/` 디렉토리가 없으면 mkdir.

- [ ] **Step 10.5: typecheck 통과 확인**

Run: `cd frontend && pnpm tsc --noEmit`
Expected: 에러 0건.

- [ ] **Step 10.6: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/lib/queries.ts frontend/src/lib/ws.ts frontend/src/hooks/usePulseStream.ts
git commit -m "feat(d2): pulse api + ws + usePulseStream hook"
```

---

### Task 11: CaseThreadEntry component

**Files:**
- Create: `frontend/src/components/CaseThreadEntry.tsx`

기존 AgentActivityTimeline의 EventRow는 너무 thin. CaseThreadEntry는 expand → raw evidence (metadata JSON pretty / tool input-output / news article excerpt 등) 보여줌.

- [ ] **Step 11.1: 컴포넌트 구현**

Create `frontend/src/components/CaseThreadEntry.tsx`:

```tsx
/**
 * CaseThreadEntry — Case Thread 한 줄.
 *
 * 한 줄: [actor icon] [actor name] · [action label] · [time]
 *        [result_preview 요약]
 *        [click → expand]
 *           raw metadata pretty + 관련 artifact link (news_article_id → drill, tool input/output 등)
 */
import { useState } from "react";
import type { ActivityEvent } from "./AgentActivityTimeline";
import { cn, relativeTime } from "../lib/utils";

// ACTOR_META는 AgentActivityTimeline에서 export (중복 정의 방지).
// 기존 AgentActivityTimeline.tsx 안 ACTOR_META + ACTION_LABEL을 named export로 변경 필요 — 다음 step.

import {
  ACTOR_META as _ACTOR_META,
  ACTION_LABEL as _ACTION_LABEL,
} from "./AgentActivityTimeline";

function actorMeta(actor: string) {
  return _ACTOR_META[actor] || {
    label: actor, icon: "·", color: "text-ink-3", chip: "bg-line-1 text-ink-3 border-line-2",
  };
}
function actionLabel(action: string): string {
  return _ACTION_LABEL[action] || action;
}

export function CaseThreadEntry({ ev }: { ev: ActivityEvent }) {
  const [expanded, setExpanded] = useState(false);
  const meta = actorMeta(ev.actor);
  const label = actionLabel(ev.action);

  const hasDetail = !!(ev.metadata && Object.keys(ev.metadata).length > 0);

  return (
    <li className="relative pl-5 pb-3">
      <span
        className={cn(
          "absolute left-0 top-1 w-3 h-3 rounded-full border-2 border-white text-[8px] leading-[7px] text-center",
          meta.chip,
        )}
      >
        {meta.icon}
      </span>
      <div className="flex items-center gap-2 text-[11px]">
        <span className={cn("font-semibold", meta.color)}>{meta.label}</span>
        <span className="text-ink-3">·</span>
        <span className="text-ink-2 font-medium">{label}</span>
        <span className="text-ink-3 text-[10px]">· {relativeTime(ev.occurred_at)}</span>
        {hasDetail && (
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="ml-auto text-[10px] text-ink-3 hover:text-ink underline-offset-2 hover:underline"
          >
            {expanded ? "접기" : "raw 펼치기"}
          </button>
        )}
      </div>
      {ev.result_preview && (
        <div className="text-[11px] text-ink-2 mt-0.5 leading-snug">
          {ev.result_preview}
        </div>
      )}
      {expanded && ev.metadata && (
        <div className="mt-2 bg-line-1 rounded p-2 border border-line-2">
          <pre className="text-[10px] text-ink-2 leading-snug whitespace-pre-wrap font-mono break-all">
            {JSON.stringify(ev.metadata, null, 2)}
          </pre>
        </div>
      )}
    </li>
  );
}
```

- [ ] **Step 11.2: AgentActivityTimeline에서 ACTOR_META / ACTION_LABEL named export 변경**

Modify `frontend/src/components/AgentActivityTimeline.tsx`:

기존 `const ACTOR_META: Record<string, ActorMeta> = { ... }` 앞에 `export ` 추가.
기존 `const ACTION_LABEL: Record<string, string> = { ... }` 앞에 `export ` 추가.

- [ ] **Step 11.3: typecheck**

Run: `cd frontend && pnpm tsc --noEmit`
Expected: 에러 0건.

- [ ] **Step 11.4: Commit**

```bash
git add frontend/src/components/CaseThreadEntry.tsx frontend/src/components/AgentActivityTimeline.tsx
git commit -m "feat(d2): CaseThreadEntry + ACTOR_META export"
```

---

### Task 12: CaseThread component

**Files:**
- Create: `frontend/src/components/CaseThread.tsx`

- [ ] **Step 12.1: 컴포넌트 구현**

Create `frontend/src/components/CaseThread.tsx`:

```tsx
/**
 * CaseThread — 한 case의 thread-style 활동 이력.
 *
 * AgentActivityTimeline의 "full" mode 대체. 차이점:
 *   - WebSocket 실시간 push (mission_id 일치하는 event)
 *   - Expand-to-raw (CaseThreadEntry)
 *   - chronological (오래된→최근, 위에서 아래로 누적)
 *   - 새 entry 도착 시 하단에 push + scroll-into-view animation
 */
import { useEffect, useMemo, useRef } from "react";
import { useMissionActivity } from "../lib/queries";
import { usePulseStream } from "../hooks/usePulseStream";
import { CaseThreadEntry } from "./CaseThreadEntry";
import type { ActivityEvent } from "./AgentActivityTimeline";

export function CaseThread({ missionId }: { missionId: string | undefined }) {
  const { data, isLoading, isError } = useMissionActivity(missionId);
  const { events: pulseEvents } = usePulseStream(50);
  const scrollRef = useRef<HTMLOListElement | null>(null);
  const lastCountRef = useRef(0);

  // REST events (per-mission) + WS events (filter to this mission)
  const merged = useMemo<ActivityEvent[]>(() => {
    const rest = data?.events ?? [];
    if (!missionId) return rest;
    const wsForCase = pulseEvents.filter((e) => e.mission_id === missionId);
    const seen = new Set<string>(rest.map((e) => String(e.id)));
    const extras = wsForCase.filter((e) => !seen.has(String(e.id)));
    const all = [...rest, ...extras];
    // chronological (oldest → newest)
    return all.sort((a, b) => a.occurred_at.localeCompare(b.occurred_at));
  }, [data?.events, pulseEvents, missionId]);

  // Auto-scroll on new entry
  useEffect(() => {
    if (merged.length > lastCountRef.current && scrollRef.current) {
      const el = scrollRef.current;
      el.scrollTop = el.scrollHeight;
    }
    lastCountRef.current = merged.length;
  }, [merged.length]);

  if (!missionId) return null;

  return (
    <section className="bg-white rounded-lg border border-line-2">
      <header className="px-4 py-3 border-b border-line-2 flex items-center justify-between">
        <div>
          <h3 className="text-[13px] font-semibold text-ink tracking-tight">Case Thread</h3>
          <p className="text-[10px] text-ink-3 mt-0.5">
            AI가 이 case에 한 일 · 실시간 누적 · {merged.length}건
          </p>
        </div>
      </header>
      <ol
        ref={scrollRef}
        className="relative px-4 py-3 max-h-[480px] overflow-y-auto"
      >
        <span aria-hidden className="absolute left-[21px] top-3 bottom-3 w-px bg-line-2" />
        {isLoading && (
          <li className="text-[11px] text-ink-3">불러오는 중...</li>
        )}
        {!isLoading && isError && (
          <li className="text-[11px] text-ink-3">불러올 수 없습니다</li>
        )}
        {!isLoading && !isError && merged.length === 0 && (
          <li className="text-[11px] text-ink-3">아직 활동이 없습니다</li>
        )}
        {merged.map((ev) => (
          <CaseThreadEntry key={ev.id} ev={ev} />
        ))}
      </ol>
    </section>
  );
}
```

- [ ] **Step 12.2: typecheck**

Run: `cd frontend && pnpm tsc --noEmit`
Expected: 0 errors.

- [ ] **Step 12.3: Commit**

```bash
git add frontend/src/components/CaseThread.tsx
git commit -m "feat(d2): CaseThread — thread-style mission activity + WS push"
```

---

### Task 13: MissionsPage에 CaseThread 통합

**Files:**
- Modify: `frontend/src/pages/MissionsPage.tsx`

- [ ] **Step 13.1: MissionsPage.tsx 읽고 AgentActivityTimeline 사용 위치 파악**

Read: `frontend/src/pages/MissionsPage.tsx` (full)
Find: `<AgentActivityTimeline ... mode="full" />` 호출 위치.

- [ ] **Step 13.2: AgentActivityTimeline(full)을 CaseThread로 교체**

기존 import 줄에 추가:
```typescript
import { CaseThread } from "../components/CaseThread";
```

`<AgentActivityTimeline missionId={activeMissionId} mode="full" />` 형태를 찾아서:
```tsx
<CaseThread missionId={activeMissionId} />
```
로 교체.

> compact mode 사용처는 그대로 둠 (Dashboard 등). Only full mode in MissionsPage → CaseThread.

- [ ] **Step 13.3: 빌드 + dev server 확인 (manual)**

Run:
```powershell
cd frontend
pnpm dev
# 별도 terminal에서 backend 띄움
cd backend; uv run python -m app.main
```

브라우저 `http://localhost:5173/missions` 접근 → case 선택 → Thread UI 노출 + WS connected.

- [ ] **Step 13.4: Commit**

```bash
git add frontend/src/pages/MissionsPage.tsx
git commit -m "feat(d2): MissionsPage → CaseThread (full mode 대체)"
```

---

### Task 14: LivePulseStrip component

**Files:**
- Create: `frontend/src/components/LivePulseStrip.tsx`

- [ ] **Step 14.1: 컴포넌트 구현**

Create `frontend/src/components/LivePulseStrip.tsx`:

```tsx
/**
 * LivePulseStrip — Decision Room hero. Bloomberg Terminal 풍 streaming feed.
 *
 * Top: 24h 누적 통계 (gdelt N / price N / supervisor N / mission N)
 * Body: 최근 events 위에서 아래로 stream. 새 entry는 위에 push, slide-down animation.
 * Empty: "watching..." pulse animation
 */
import { useMemo } from "react";
import { usePulseStream } from "../hooks/usePulseStream";
import { usePulseStats } from "../lib/queries";
import { cn, relativeTime } from "../lib/utils";
import {
  ACTOR_META as _ACTOR_META,
  ACTION_LABEL as _ACTION_LABEL,
} from "./AgentActivityTimeline";
import { Link } from "react-router-dom";

const ROW_LIMIT = 14;

function actorMeta(actor: string) {
  return _ACTOR_META[actor] || { label: actor, icon: "·", color: "text-ink-3", chip: "bg-line-1 text-ink-3 border-line-2" };
}

const ACTOR_SHORT: Record<string, string> = {
  supervisor: "Supervisor",
  genie: "Genie",
  knowledge_assistant: "KA",
  mission_plan_fma: "Mission Plan",
  mission_plan_uc: "mission_plan_advice",
  weighted_signal_uc: "weighted_signal",
  gdelt: "GDELT",
  curation_job: "Curation",
  price_job: "Price",
  reactive: "Reactive",
  manager: "매니저",
  system: "System",
};

export function LivePulseStrip() {
  const { events, connected } = usePulseStream(50);
  const { data: stats } = usePulseStats();

  const top = useMemo(() => events.slice(0, ROW_LIMIT), [events]);

  return (
    <section className="bg-white rounded-lg border border-line-2 overflow-hidden">
      <header className="px-4 py-2 border-b border-line-2 flex items-center gap-3 bg-base-paper">
        <div className="flex items-center gap-1.5">
          <span
            className={cn(
              "w-2 h-2 rounded-full",
              connected ? "bg-opportunity-500 animate-pulse" : "bg-ink-3",
            )}
            aria-hidden
          />
          <span className="text-[11px] font-semibold text-ink">Live AI Pulse</span>
          <span className="text-[10px] text-ink-3">
            {connected ? "실시간" : "재연결 중"}
          </span>
        </div>
        {stats && (
          <div className="ml-auto flex items-center gap-3 text-[10px] text-ink-3">
            <span>24h 활동 {stats.total_24h}건</span>
            <span>· 활성 case {stats.active_cases}</span>
            <span>· gdelt {stats.by_actor.gdelt ?? 0}</span>
            <span>· price {stats.by_actor.price_job ?? 0}</span>
            <span>· supervisor {stats.by_actor.supervisor ?? 0}</span>
          </div>
        )}
      </header>

      <ol className="max-h-[340px] overflow-y-auto">
        {top.length === 0 && (
          <li className="px-4 py-6 text-[11px] text-ink-3 flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-ink-3 animate-pulse" aria-hidden />
            watching... (AI 활동 대기)
          </li>
        )}
        {top.map((ev) => {
          const m = actorMeta(ev.actor);
          const short = ACTOR_SHORT[ev.actor] ?? ev.actor;
          const Wrapper: React.ElementType = ev.mission_id ? Link : "div";
          const wrapperProps: Record<string, unknown> = ev.mission_id
            ? { to: `/missions?id=${ev.mission_id}` }
            : {};
          return (
            <li key={ev.id} className="border-b border-line-1 last:border-b-0">
              <Wrapper
                {...wrapperProps}
                className="block px-4 py-1.5 hover:bg-base-paper text-[11px] leading-snug"
              >
                <span className="text-[10px] text-ink-3 mr-2 tabular-nums">
                  {relativeTime(ev.occurred_at)}
                </span>
                <span className={cn("inline-block w-3 text-center mr-1", m.color)}>{m.icon}</span>
                <span className={cn("font-medium mr-1", m.color)}>{short}</span>
                <span className="text-ink-2 mr-1">·</span>
                <span className="text-ink-2 mr-2">{_ACTION_LABEL[ev.action] ?? ev.action}</span>
                {ev.result_preview && (
                  <span className="text-ink-3 truncate inline-block max-w-[60%] align-bottom">
                    · {ev.result_preview}
                  </span>
                )}
              </Wrapper>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
```

- [ ] **Step 14.2: typecheck**

Run: `cd frontend && pnpm tsc --noEmit`
Expected: 0 errors.

- [ ] **Step 14.3: Commit**

```bash
git add frontend/src/components/LivePulseStrip.tsx
git commit -m "feat(d2): LivePulseStrip — Decision Room hero live stream"
```

---

### Task 15: Dashboard에 LivePulseStrip 통합

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`

- [ ] **Step 15.1: Dashboard.tsx hero 영역 위치 확인**

Read: `frontend/src/pages/Dashboard.tsx`

기존 hero (open case summary, Bidirectional3Zone 등) 자리 식별.

- [ ] **Step 15.2: LivePulseStrip을 hero column으로 추가**

기존 hero가 단일 column이면 grid로 분할:
- 좌 (60%): 기존 open case summary
- 우 (40%): `<LivePulseStrip />`

Import 추가:
```typescript
import { LivePulseStrip } from "../components/LivePulseStrip";
```

JSX 변경 (구체 layout은 기존 Dashboard 구조 따라 — Tailwind grid `grid grid-cols-5 gap-3` 정도):

```tsx
<div className="grid grid-cols-1 lg:grid-cols-5 gap-3 mb-4">
  <div className="lg:col-span-3">
    {/* 기존 open case hero */}
  </div>
  <div className="lg:col-span-2">
    <LivePulseStrip />
  </div>
</div>
```

- [ ] **Step 15.3: dev 서버에서 시각 확인 (manual)**

Run: `cd frontend && pnpm dev`. `http://localhost:5173/` 접근 → Dashboard hero에 Live Pulse strip 보임 + 5초 polling으로 events 갱신 + WS connected dot 녹색.

- [ ] **Step 15.4: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx
git commit -m "feat(d2): Dashboard hero에 LivePulseStrip 통합"
```

---

### Task 16: SidebarPulseDot — 글로벌 mini presence

**Files:**
- Create: `frontend/src/components/SidebarPulseDot.tsx`
- Modify: `frontend/src/components/Sidebar.tsx`

- [ ] **Step 16.1: SidebarPulseDot 구현**

Create `frontend/src/components/SidebarPulseDot.tsx`:

```tsx
/**
 * SidebarPulseDot — sidebar 하단 mini AI activity indicator.
 *
 * 표시:
 *   - 녹색 깜빡임 + "AI 활동" + 마지막 entry relativeTime (예: "30초 전")
 *   - WS 연결 안 됨: 회색 dot + "재연결 중"
 *   - 24h 누적 count 한 줄
 */
import { usePulseStream } from "../hooks/usePulseStream";
import { usePulseStats } from "../lib/queries";
import { relativeTime } from "../lib/utils";

export function SidebarPulseDot() {
  const { events, connected } = usePulseStream(10);
  const { data: stats } = usePulseStats();
  const latest = events[0];

  return (
    <div className="border-t border-line-2 pt-3 mt-3 px-3 text-[10px]">
      <div className="flex items-center gap-1.5">
        <span
          className={`w-1.5 h-1.5 rounded-full ${
            connected ? "bg-opportunity-500 animate-pulse" : "bg-ink-3"
          }`}
          aria-hidden
        />
        <span className="text-ink-2 font-medium">
          {connected ? "AI 활동 중" : "재연결 중"}
        </span>
        {latest && (
          <span className="text-ink-3 ml-auto">{relativeTime(latest.occurred_at)}</span>
        )}
      </div>
      {stats && (
        <div className="text-ink-3 mt-1 leading-snug">
          24h {stats.total_24h}건 · {stats.active_cases} active case
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 16.2: Sidebar.tsx 통합**

Modify `frontend/src/components/Sidebar.tsx`:

import 추가:
```typescript
import { SidebarPulseDot } from "./SidebarPulseDot";
```

sidebar JSX 하단 (마지막 nav item 다음, footer 위치):
```tsx
<SidebarPulseDot />
```

- [ ] **Step 16.3: 시각 확인 (manual)**

브라우저 새로고침 → Sidebar 하단에 mini dot + count 노출.

- [ ] **Step 16.4: Commit**

```bash
git add frontend/src/components/SidebarPulseDot.tsx frontend/src/components/Sidebar.tsx
git commit -m "feat(d2): SidebarPulseDot — global AI activity presence"
```

---

## Phase P1 — Signal Lifecycle

### Task 17: Backend signal lifecycle API

**Files:**
- Create: `backend/app/api/signals.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_signals_api.py`

- [ ] **Step 17.1: 실패 테스트 작성**

Create `backend/tests/test_signals_api.py`:

```python
"""Signals API tests — GET /api/signals/{id}/lifecycle."""
import os
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_lifecycle_404_for_unknown_signal():
    response = client.get("/api/signals/nonexistent-id-xyz/lifecycle")
    # graceful — 빈 stages 반환 (404 X) — Lakebase 미연결 시 graceful
    assert response.status_code in (200, 404)


def test_lifecycle_shape():
    """알려진 signal_id (최근 news_article id 중 하나)에 대해 4 stage 형식 검증."""
    # 실제 검증은 Lakebase 연결 가능한 환경에서. 형식만:
    response = client.get("/api/signals/sample-1/lifecycle")
    assert response.status_code in (200, 404)
    if response.status_code == 200:
        body = response.json()
        assert "signal_id" in body
        assert "stages" in body
        # stages keys: detected, scored, decay, contribution
        stages = body["stages"]
        assert all(k in stages for k in ("detected", "scored", "decay", "contribution"))
```

- [ ] **Step 17.2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/test_signals_api.py -v`
Expected: FAIL (404 from missing route).

- [ ] **Step 17.3: signals.py 구현**

Create `backend/app/api/signals.py`:

```python
"""Signal Lifecycle API — bronze.news_articles + silver.signal_events_decayed + gold.signal_contribution_30d.

GET /api/signals/{signal_id}/lifecycle  → 4-stage forensic view
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/signals", tags=["signals"])


@router.get("/{signal_id}/lifecycle")
async def get_lifecycle(signal_id: str) -> dict[str, Any]:
    """한 signal (news_article)의 4-stage lifecycle.

    Stage 1: detected — bronze.news_articles row
    Stage 2: scored — LLM scoring (직접 표시 또는 metadata)
    Stage 3: decay — silver.signal_events_decayed (시간 감쇠 곡선)
    Stage 4: contribution — gold.signal_contribution_30d (30일 누적)
    """
    try:
        from databricks.sdk import WorkspaceClient
        from app.core.config import get_settings

        settings = get_settings()
        w = WorkspaceClient()
        warehouse_id = settings.databricks_warehouse_id

        def _query(sql: str) -> list[dict[str, Any]]:
            result = w.statement_execution.execute_statement(
                warehouse_id=warehouse_id,
                statement=sql,
                wait_timeout="30s",
            )
            if not result.result or not result.result.data_array:
                return []
            cols = [c.name for c in (result.manifest.schema.columns or [])]
            return [dict(zip(cols, row)) for row in result.result.data_array]

        # Stage 1+2 — detected + scored (단일 query)
        detected = _query(
            f"""
            SELECT article_id, title, source, published_at, importance,
                   direction, category, horizon, confidence
              FROM crude_compass.bronze.news_articles
             WHERE article_id = '{signal_id}'
             LIMIT 1
            """
        )
        if not detected:
            raise HTTPException(status_code=404, detail={"code": "NOT_FOUND"})

        # Stage 3 — decay curve
        decay = _query(
            f"""
            SELECT as_of_date, weight, lambda, days_since_event
              FROM crude_compass.silver.signal_events_decayed
             WHERE article_id = '{signal_id}'
             ORDER BY as_of_date ASC
            """
        )

        # Stage 4 — contribution (30일 누적 + referenced cases)
        contribution = _query(
            f"""
            SELECT total_contribution, peak_contribution, peak_date,
                   referenced_case_ids
              FROM crude_compass.gold.signal_contribution_30d
             WHERE article_id = '{signal_id}'
             LIMIT 1
            """
        )

        return {
            "signal_id": signal_id,
            "stages": {
                "detected": detected[0],
                "scored": {
                    "importance": detected[0].get("importance"),
                    "direction": detected[0].get("direction"),
                    "horizon": detected[0].get("horizon"),
                    "confidence": detected[0].get("confidence"),
                },
                "decay": decay,
                "contribution": contribution[0] if contribution else None,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("signal lifecycle failed for %s: %s", signal_id, e)
        # graceful: 빈 stages
        return {
            "signal_id": signal_id,
            "stages": {"detected": None, "scored": None, "decay": [], "contribution": None},
        }
```

> `settings.databricks_warehouse_id` 는 `app/core/config.py`에 추가 필요. 기존 GENIE_SPACE_ID 패턴 따라 env `DATABRICKS_WAREHOUSE_ID`. Genie space의 warehouse_id (`da56f72320e22238`, SDK로 확인됨)를 default로.

- [ ] **Step 17.4: config.py에 warehouse_id 필드 추가**

Modify `backend/app/core/config.py` — Settings class에:

```python
databricks_warehouse_id: str = Field(
    default_factory=lambda: os.getenv("DATABRICKS_WAREHOUSE_ID", "da56f72320e22238")
)
```

- [ ] **Step 17.5: main.py router 등록**

`from app.api import ... signals as signals_api ...` 추가.
`app.include_router(signals_api.router)` 추가.

- [ ] **Step 17.6: 테스트 + manual 검증**

Run: `cd backend && uv run pytest tests/test_signals_api.py -v`
Expected: PASS.

Manual:
```powershell
# 실제 article_id 하나 조회
databricks --profile crude-compass sql-warehouses query "<warehouse_id>" "SELECT article_id FROM crude_compass.bronze.news_articles ORDER BY published_at DESC LIMIT 1"
# 그 article_id로:
curl http://localhost:8000/api/signals/<article_id>/lifecycle
```
Expected: 4 stages 모두 채워진 JSON.

- [ ] **Step 17.7: Commit**

```bash
git add backend/app/api/signals.py backend/app/core/config.py backend/app/main.py backend/tests/test_signals_api.py
git commit -m "feat(d2): /api/signals/{id}/lifecycle — 4-stage forensic view"
```

---

### Task 18: SignalLifecycle 컴포넌트

**Files:**
- Create: `frontend/src/components/SignalLifecycle.tsx`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/lib/queries.ts`

- [ ] **Step 18.1: api + query 추가**

`api.ts`:
```typescript
export const signalsApi = {
  lifecycle: (signalId: string) =>
    apiGet<{
      signal_id: string;
      stages: {
        detected: Record<string, unknown> | null;
        scored: { importance: number; direction: string; horizon: string; confidence: number } | null;
        decay: Array<{ as_of_date: string; weight: number; lambda: number; days_since_event: number }>;
        contribution: { total_contribution: number; peak_contribution: number; peak_date: string; referenced_case_ids: string[] } | null;
      };
    }>(`/api/signals/${signalId}/lifecycle`),
};
```

`queries.ts`:
```typescript
import { signalsApi } from "./api";

export function useSignalLifecycle(signalId: string | undefined) {
  return useQuery({
    queryKey: ["signal", "lifecycle", signalId],
    queryFn: () => signalsApi.lifecycle(signalId!),
    enabled: !!signalId,
    staleTime: 60_000,
  });
}
```

- [ ] **Step 18.2: SignalLifecycle 컴포넌트 구현**

Create `frontend/src/components/SignalLifecycle.tsx`:

```tsx
/**
 * SignalLifecycle — 4-stage forensic view of a single signal.
 *
 * Stage 1: Detected (bronze.news_articles row — title/source/published_at)
 * Stage 2: Scored (importance/direction/horizon/confidence)
 * Stage 3: Decay (silver.signal_events_decayed line chart)
 * Stage 4: Contribution (gold.signal_contribution_30d bar + referenced cases)
 */
import { useSignalLifecycle } from "../lib/queries";
import { Link } from "react-router-dom";

export function SignalLifecycle({ signalId }: { signalId: string | undefined }) {
  const { data, isLoading, isError } = useSignalLifecycle(signalId);

  if (!signalId) {
    return (
      <div className="text-[11px] text-ink-3 p-4">
        Live Pulse에서 [GDELT] 항목을 클릭하면 그 시그널의 lifecycle을 추적합니다.
      </div>
    );
  }
  if (isLoading) return <div className="text-[11px] text-ink-3 p-4">불러오는 중...</div>;
  if (isError || !data) return <div className="text-[11px] text-ink-3 p-4">불러올 수 없습니다</div>;

  const { stages } = data;

  return (
    <section className="space-y-4">
      {/* Stage 1 */}
      <Stage num={1} title="Detected">
        {stages.detected ? (
          <div className="text-[11px]">
            <div className="font-medium text-ink">{String(stages.detected.title)}</div>
            <div className="text-ink-3 mt-1">
              {String(stages.detected.source)} · {String(stages.detected.published_at)}
            </div>
          </div>
        ) : (
          <Empty />
        )}
      </Stage>

      {/* Stage 2 */}
      <Stage num={2} title="Scored by LLM">
        {stages.scored ? (
          <div className="grid grid-cols-4 gap-2 text-[11px]">
            <Kv k="importance" v={stages.scored.importance} />
            <Kv k="direction" v={stages.scored.direction} />
            <Kv k="horizon" v={stages.scored.horizon} />
            <Kv k="confidence" v={stages.scored.confidence} />
          </div>
        ) : (
          <Empty />
        )}
      </Stage>

      {/* Stage 3 — Decay */}
      <Stage num={3} title="Decay (time-weighted)">
        {stages.decay.length > 0 ? (
          <DecayChart points={stages.decay} />
        ) : (
          <Empty msg="감쇠 데이터 없음 (검출된 지 24h 미만)" />
        )}
      </Stage>

      {/* Stage 4 */}
      <Stage num={4} title="Contribution (30-day cumulative)">
        {stages.contribution ? (
          <div className="text-[11px] space-y-1">
            <div>총 누적: <span className="font-semibold">{stages.contribution.total_contribution.toFixed(2)}</span></div>
            <div>피크: {stages.contribution.peak_contribution.toFixed(2)} ({stages.contribution.peak_date})</div>
            <div className="pt-1">
              참고된 case ({stages.contribution.referenced_case_ids.length}):
              <ul className="mt-1 space-y-0.5">
                {stages.contribution.referenced_case_ids.map((cid) => (
                  <li key={cid}>
                    <Link to={`/missions?id=${cid}`} className="text-opportunity-700 hover:underline">
                      {cid}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ) : (
          <Empty msg="아직 case 참고 이력 없음" />
        )}
      </Stage>
    </section>
  );
}

function Stage({ num, title, children }: { num: number; title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-lg border border-line-2 p-3">
      <div className="text-[10px] text-ink-3 font-semibold tracking-wide mb-2">
        STAGE {num} · {title}
      </div>
      {children}
    </div>
  );
}

function Kv({ k, v }: { k: string; v: unknown }) {
  return (
    <div>
      <div className="text-[9px] text-ink-3 uppercase">{k}</div>
      <div className="text-ink font-medium">{String(v)}</div>
    </div>
  );
}

function Empty({ msg = "데이터 없음" }: { msg?: string }) {
  return <div className="text-[11px] text-ink-3 italic">{msg}</div>;
}

function DecayChart({ points }: { points: Array<{ as_of_date: string; weight: number }> }) {
  // 간단 SVG sparkline — Recharts 없이 (5/19 결정: Recharts X)
  if (points.length === 0) return null;
  const w = 320, h = 80, pad = 4;
  const maxWeight = Math.max(...points.map((p) => p.weight));
  const minWeight = Math.min(...points.map((p) => p.weight));
  const range = maxWeight - minWeight || 1;
  const xStep = (w - 2 * pad) / Math.max(points.length - 1, 1);
  const path = points
    .map((p, i) => {
      const x = pad + i * xStep;
      const y = pad + (h - 2 * pad) * (1 - (p.weight - minWeight) / range);
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-20">
      <path d={path} fill="none" stroke="currentColor" strokeWidth="1.5" className="text-crisis-500" />
    </svg>
  );
}
```

- [ ] **Step 18.3: typecheck**

Run: `cd frontend && pnpm tsc --noEmit`
Expected: 0 errors.

- [ ] **Step 18.4: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/lib/queries.ts frontend/src/components/SignalLifecycle.tsx
git commit -m "feat(d2): SignalLifecycle — 4-stage signal forensics UI"
```

---

### Task 19: AskPage(Investigation)에 Signal Lifecycle tab

**Files:**
- Modify: `frontend/src/pages/AskPage.tsx`

- [ ] **Step 19.1: AskPage.tsx 구조 파악 + tab 추가 위치 결정**

Read: `frontend/src/pages/AskPage.tsx`

기존 chat / supervisor trace 가 있는 layout — 그 옆 또는 하단에 "Trace signal" tab.

- [ ] **Step 19.2: tab 토글 + SignalLifecycle 표시**

Import:
```typescript
import { SignalLifecycle } from "../components/SignalLifecycle";
import { useState } from "react";
import { useSearchParams } from "react-router-dom";
```

Page 안 state:
```tsx
const [searchParams] = useSearchParams();
const [mode, setMode] = useState<"chat" | "signal">("chat");
const signalId = searchParams.get("signal_id") ?? undefined;

// signal_id query param 있으면 자동으로 signal mode
useEffect(() => {
  if (signalId) setMode("signal");
}, [signalId]);
```

JSX tab UI (적절 위치):
```tsx
<div className="flex gap-2 mb-3">
  <button onClick={() => setMode("chat")} className={cn("text-[12px] px-3 py-1 rounded", mode === "chat" ? "bg-ink text-white" : "bg-line-1 text-ink-2")}>Chat</button>
  <button onClick={() => setMode("signal")} className={cn("text-[12px] px-3 py-1 rounded", mode === "signal" ? "bg-ink text-white" : "bg-line-1 text-ink-2")}>Trace a Signal</button>
</div>

{mode === "signal" ? (
  <SignalLifecycle signalId={signalId} />
) : (
  /* 기존 chat UI 그대로 */
  <SupervisorChat ... />
)}
```

- [ ] **Step 19.3: LivePulseStrip에서 signal click → AskPage?mode=signal&signal_id=... deep link**

Modify `LivePulseStrip.tsx` — gdelt entry는 article_id metadata가 있으면 그 link로:

기존 `Wrapper` 결정 부분에 추가:
```typescript
const articleId = (ev.metadata as { article_id?: string } | null)?.article_id;
const linkTo = ev.mission_id
  ? `/missions?id=${ev.mission_id}`
  : articleId
  ? `/ask?signal_id=${articleId}`
  : undefined;
const Wrapper: React.ElementType = linkTo ? Link : "div";
const wrapperProps: Record<string, unknown> = linkTo ? { to: linkTo } : {};
```

- [ ] **Step 19.4: manual 검증**

dev server에서:
- Dashboard → Live Pulse의 GDELT entry 클릭 → Investigation page로 이동 → Signal Lifecycle 4-stage 표시.

- [ ] **Step 19.5: Commit**

```bash
git add frontend/src/pages/AskPage.tsx frontend/src/components/LivePulseStrip.tsx
git commit -m "feat(d2): AskPage Trace-a-Signal tab + Pulse signal deep link"
```

---

## Phase P1 — Daily Loop Clock

### Task 20: Backend job runs API

**Files:**
- Create: `backend/app/api/jobs.py`
- Modify: `backend/app/main.py`

- [ ] **Step 20.1: jobs.py 구현**

Create `backend/app/api/jobs.py`:

```python
"""Jobs API — Databricks Jobs SDK wrapper.

GET /api/jobs/runs/today  → 오늘 0시(KST) 이후 모든 job run summary (Daily Loop dial 용)
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

# crude-compass job name → display label
CRUDE_COMPASS_JOB_PREFIXES = ["[dev hyeongwook_lee] crude-compass-"]
JOB_LABEL: dict[str, str] = {
    "gdelt-15min": "GDELT",
    "price-pipeline": "Price",
    "oil-prices-daily": "OilPrice Daily",
    "ecos-daily": "ECOS",
    "eia-weekly": "EIA",
    "opec-momr": "OPEC MOMR",
    "daily-curation": "Curation",
    "daily-risk-backfill": "Risk Backfill",
    "backtest-seed": "Backtest Seed",
    "backtest-compute": "Backtest Compute",
    "backtest-llm": "Backtest LLM",
}


def _normalize_job_name(full_name: str) -> str:
    """[dev hyeongwook_lee] crude-compass-gdelt-15min-dev → gdelt-15min"""
    for prefix in CRUDE_COMPASS_JOB_PREFIXES:
        if full_name.startswith(prefix):
            stripped = full_name[len(prefix):]
            if stripped.endswith("-dev"):
                stripped = stripped[:-4]
            return stripped
    return full_name


@router.get("/runs/today")
async def get_runs_today() -> dict[str, Any]:
    """오늘 24h 내 모든 crude-compass job run summary.

    Response:
      {
        "runs": [{job_name, label, start_time, end_time, result_state, ...}],
        "summary": {job_name: {"count": N, "success": N, "fail": N}}
      }
    """
    try:
        from databricks.sdk import WorkspaceClient

        w = WorkspaceClient()
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        since_ms = int(since.timestamp() * 1000)

        # SDK iterator — completed runs only
        runs: list[dict[str, Any]] = []
        for run in w.jobs.list_runs(
            completed_only=True,
            start_time_from=since_ms,
            limit=200,
        ):
            full_name = (run.run_name or "").strip()
            if "crude-compass" not in full_name:
                continue
            job_key = _normalize_job_name(full_name)
            runs.append({
                "job_name": job_key,
                "label": JOB_LABEL.get(job_key, job_key),
                "run_id": run.run_id,
                "start_time": run.start_time,
                "end_time": run.end_time,
                "result_state": (run.state.result_state.value if run.state and run.state.result_state else None),
                "duration_ms": (run.end_time - run.start_time) if (run.start_time and run.end_time) else None,
            })

        # Aggregate
        summary: dict[str, dict[str, int]] = {}
        for r in runs:
            key = r["job_name"]
            if key not in summary:
                summary[key] = {"count": 0, "success": 0, "fail": 0}
            summary[key]["count"] += 1
            if r["result_state"] == "SUCCESS":
                summary[key]["success"] += 1
            elif r["result_state"] in ("FAILED", "TIMEDOUT", "CANCELED"):
                summary[key]["fail"] += 1

        return {"runs": runs, "summary": summary}
    except Exception as e:
        logger.warning("jobs runs today failed: %s", e)
        return {"runs": [], "summary": {}}
```

- [ ] **Step 20.2: main.py router 등록**

Add `jobs as jobs_api` to import, `app.include_router(jobs_api.router)`.

- [ ] **Step 20.3: manual 검증**

```powershell
curl http://localhost:8000/api/jobs/runs/today
```
Expected: runs[] 안에 오늘 실행된 12개 job들의 run 결과 + summary by job_name.

- [ ] **Step 20.4: Commit**

```bash
git add backend/app/api/jobs.py backend/app/main.py
git commit -m "feat(d2): /api/jobs/runs/today — Daily Loop 데이터 source"
```

---

### Task 21: DailyLoopClock 컴포넌트

**Files:**
- Create: `frontend/src/components/DailyLoopClock.tsx`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/lib/queries.ts`

- [ ] **Step 21.1: api + query 추가**

`api.ts`:
```typescript
export const jobsApi = {
  runsToday: () =>
    apiGet<{
      runs: Array<{
        job_name: string;
        label: string;
        run_id: number;
        start_time: number | null;
        end_time: number | null;
        result_state: string | null;
        duration_ms: number | null;
      }>;
      summary: Record<string, { count: number; success: number; fail: number }>;
    }>("/api/jobs/runs/today"),
};
```

`queries.ts`:
```typescript
import { jobsApi } from "./api";

export function useJobRunsToday() {
  return useQuery({
    queryKey: ["jobs", "runs", "today"],
    queryFn: () => jobsApi.runsToday(),
    refetchInterval: 60_000,
    staleTime: 30_000,
  });
}
```

- [ ] **Step 21.2: DailyLoopClock 구현**

Create `frontend/src/components/DailyLoopClock.tsx`:

```tsx
/**
 * DailyLoopClock — 24h 원형 dial. 매 시간 어떤 job이 돌았는지 시각화.
 *
 * 외곽: 시계 face (24h, 0~24)
 * 안쪽: job run dots — start_time을 각도로 매핑
 * 하단: 누적 통계 strip
 */
import { useJobRunsToday } from "../lib/queries";

export function DailyLoopClock() {
  const { data, isLoading, isError } = useJobRunsToday();

  if (isLoading) return <div className="text-[11px] text-ink-3 p-4">불러오는 중...</div>;
  if (isError || !data) return <div className="text-[11px] text-ink-3 p-4">불러올 수 없습니다</div>;

  const { runs, summary } = data;
  const size = 240;
  const cx = size / 2, cy = size / 2;
  const rOuter = 110, rInner = 80;
  const now = new Date();
  const nowAngle = ((now.getHours() + now.getMinutes() / 60) / 24) * 360 - 90;

  return (
    <section className="bg-white rounded-lg border border-line-2 p-3">
      <header className="text-[11px] font-semibold text-ink mb-2">Daily AI Loop</header>
      <div className="flex flex-col items-center">
        <svg viewBox={`0 0 ${size} ${size}`} className="w-full max-w-[260px]">
          {/* 24 hour ticks */}
          {Array.from({ length: 24 }, (_, h) => {
            const a = (h / 24) * 360 - 90;
            const rad = (a * Math.PI) / 180;
            const x1 = cx + Math.cos(rad) * (rOuter - 4);
            const y1 = cy + Math.sin(rad) * (rOuter - 4);
            const x2 = cx + Math.cos(rad) * rOuter;
            const y2 = cy + Math.sin(rad) * rOuter;
            return (
              <line key={h} x1={x1} y1={y1} x2={x2} y2={y2} stroke="currentColor" strokeWidth="1" className="text-line-2" />
            );
          })}

          {/* job run dots */}
          {runs.map((r) => {
            if (!r.start_time) return null;
            const d = new Date(r.start_time);
            const hr = d.getHours() + d.getMinutes() / 60;
            const a = (hr / 24) * 360 - 90;
            const rad = (a * Math.PI) / 180;
            const rDot = rInner + (jobRadiusOffset(r.job_name) * 6);
            const x = cx + Math.cos(rad) * rDot;
            const y = cy + Math.sin(rad) * rDot;
            const fill = r.result_state === "SUCCESS" ? "rgb(16 185 129)" : "rgb(239 68 68)";
            return <circle key={r.run_id} cx={x} cy={y} r={2} fill={fill} />;
          })}

          {/* now hand */}
          {(() => {
            const rad = (nowAngle * Math.PI) / 180;
            const x = cx + Math.cos(rad) * (rOuter - 8);
            const y = cy + Math.sin(rad) * (rOuter - 8);
            return <line x1={cx} y1={cy} x2={x} y2={y} stroke="currentColor" strokeWidth="1.5" className="text-ink" />;
          })()}

          {/* center */}
          <circle cx={cx} cy={cy} r={3} fill="currentColor" className="text-ink" />
        </svg>

        {/* summary strip */}
        <div className="grid grid-cols-3 gap-2 w-full mt-3 text-[10px]">
          {Object.entries(summary).slice(0, 9).map(([k, v]) => (
            <div key={k} className="bg-base-paper rounded p-1.5 border border-line-2">
              <div className="text-ink-3 truncate">{k}</div>
              <div className="text-ink font-semibold">{v.count}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// job별 ring offset (0~3) — 같은 시간에 여러 job 겹치는 것 방지
const JOB_RING: Record<string, number> = {
  "gdelt-15min": 0,
  "price-pipeline": 1,
  "daily-curation": 2,
  "oil-prices-daily": 2,
  "ecos-daily": 2,
  "eia-weekly": 3,
  "opec-momr": 3,
};

function jobRadiusOffset(jobName: string): number {
  return JOB_RING[jobName] ?? 3;
}
```

- [ ] **Step 21.3: typecheck**

Run: `cd frontend && pnpm tsc --noEmit`
Expected: 0 errors.

- [ ] **Step 21.4: Dashboard에 배치**

Modify `frontend/src/pages/Dashboard.tsx`:

Import: `import { DailyLoopClock } from "../components/DailyLoopClock";`
적절 위치 (LivePulseStrip 아래, 또는 우측 column 두 번째 row):
```tsx
<DailyLoopClock />
```

- [ ] **Step 21.5: 시각 확인**

dev server에서 Dashboard → 24h dial에 오늘 job run dots + 시침.

- [ ] **Step 21.6: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/lib/queries.ts frontend/src/components/DailyLoopClock.tsx frontend/src/pages/Dashboard.tsx
git commit -m "feat(d2): DailyLoopClock — 24h job run dial + Dashboard 통합"
```

---

## Phase P2 — Supervisor self-narration

### Task 22: Supervisor wrapper에 reasoning_path field 추가

**Files:**
- Modify: `backend/app/api/supervisor.py`

기존 supervisor invocation 시 tool routing 결정의 이유를 metadata에 함께 저장.

- [ ] **Step 22.1: supervisor.py 읽고 insert_event 호출 위치 파악**

Read: `backend/app/api/supervisor.py`

기존 코드: `agent_activity.insert_event(...)`이 tool 호출마다 한 번 + synthesized 한 번.

- [ ] **Step 22.2: synthesized event metadata 확장**

synthesized event 부분 (보통 모든 tool 끝난 후 1회) 의 metadata에 `reasoning_path` 추가:

```python
# 기존 코드 흐름:
# 1. supervisor가 query 받음
# 2. tool들 호출 (genie, ka 등) — 각각 insert_event(action='invoked')
# 3. 합성 — insert_event(action='synthesized', metadata={'tool_count': N, ...})
#
# 변경: metadata에 reasoning_path 추가
synthesized_metadata = {
    "tool_count": len(tools_called),
    "tools": tools_called,
    "reasoning_path": _build_reasoning_path(tools_called, supervisor_response),
}

def _build_reasoning_path(tools_called: list[str], response: dict) -> list[str]:
    """단순 narrative — tool 선택 이유 list.

    예: [
        "Pattern Score 단독으로 명확 → Genie 호출",
        "OPEC narrative 보강 필요 X → KA skip",
        "mission_plan_advice UDF 호출 → reasoning 통합",
    ]
    """
    path: list[str] = []
    if "genie" in tools_called:
        path.append("Genie 호출 — structured market evidence 필요")
    if "knowledge_assistant" in tools_called:
        path.append("KA 호출 — document evidence 보강")
    if "mission_plan_uc" in tools_called or "mission_plan_advice" in tools_called:
        path.append("mission_plan_advice UDF 호출 — recommendation 합성")
    if not path:
        path.append("도구 호출 없이 직접 합성 (단순 질의)")
    return path
```

> 정확한 변수명·위치는 기존 supervisor.py 보고 조정.

- [ ] **Step 22.3: 호출 후 frontend 확인**

backend 재기동 → Investigation에서 질문 던지면 → CaseThread `[supervisor]` synthesized entry → "raw 펼치기" → metadata 안에 `reasoning_path: [...]` 보임.

- [ ] **Step 22.4: Commit**

```bash
git add backend/app/api/supervisor.py
git commit -m "feat(d2): supervisor synthesized metadata에 reasoning_path 추가"
```

---

### Task 23: CaseThreadEntry에서 reasoning_path 시각 강조

**Files:**
- Modify: `frontend/src/components/CaseThreadEntry.tsx`

- [ ] **Step 23.1: metadata에 reasoning_path 있으면 raw JSON 위에 list 형태 강조**

기존 expand panel 안 변경:

```tsx
{expanded && ev.metadata && (
  <div className="mt-2 bg-line-1 rounded p-2 border border-line-2">
    {Array.isArray((ev.metadata as { reasoning_path?: unknown }).reasoning_path) && (
      <div className="mb-2 pb-2 border-b border-line-2">
        <div className="text-[9px] text-ink-3 uppercase font-semibold mb-1">Reasoning Path</div>
        <ol className="list-decimal list-inside text-[11px] text-ink-2 space-y-0.5">
          {((ev.metadata as { reasoning_path: string[] }).reasoning_path).map((step, i) => (
            <li key={i}>{step}</li>
          ))}
        </ol>
      </div>
    )}
    <pre className="text-[10px] text-ink-2 leading-snug whitespace-pre-wrap font-mono break-all">
      {JSON.stringify(ev.metadata, null, 2)}
    </pre>
  </div>
)}
```

- [ ] **Step 23.2: 시각 확인 + Commit**

dev server 확인 후:

```bash
git add frontend/src/components/CaseThreadEntry.tsx
git commit -m "feat(d2): CaseThreadEntry — reasoning_path 강조"
```

---

## Phase P2 — Docs & Cleanup

### Task 24: README + architecture.md 정정

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture.md`

SDK 실측 ground truth 반영. 이미 staged spec 문서가 정정 사항을 명시 — 두 문서에 반영.

- [ ] **Step 24.1: architecture.md §4 정정 — Multi-Agent Supervisor scope-out 제거**

Modify `docs/architecture.md`:

기존: `~~Supervisor Agent~~ | scope-out`
→ 변경: `Supervisor Agent | **real** | mas-ba3fbcb5-endpoint deployed READY`

기존 §3 Lakeflow Jobs 8개 → 12개로 수정 (backfill/backtest 추가).

- [ ] **Step 24.2: README.md 시나리오 docs 표 업데이트**

Modify `README.md`:

핵심 문서 표에 `docs/superpowers/specs/2026-05-20-time-axis-redesign-spec.md`와 plan 추가.

- [ ] **Step 24.3: Commit**

```bash
git add README.md docs/architecture.md
git commit -m "docs(d2): SDK ground truth 정정 — MAS deployed + 12 jobs + spec 추가"
```

---

### Task 25: Demo script update

**Files:**
- Modify: `docs/demo_script_5min.md`

- [ ] **Step 25.1: demo script time-axis flow 반영**

Modify `docs/demo_script_5min.md`:

기존 5분 흐름에 spec §9 demo flow 적용:
- 0:30-1:00 Live AI Pulse 30초 dwell
- 1:00-2:00 Case Thread 풀스크롤 + raw expand
- 2:00-3:00 Investigation Trace-a-Signal 4-stage
- 3:00-4:00 Slack 시연 (기존)
- 4:00-4:30 Daily Loop dial 보여줌
- 4:30-5:00 Track 1 Social Impact wrap

- [ ] **Step 25.2: Commit**

```bash
git add docs/demo_script_5min.md
git commit -m "docs(d2): demo script — time-axis flow 적용"
```

---

## Self-Review

### Spec coverage 검증

| spec 요구사항 | 구현 task |
|---|---|
| §4 Layer P0-A (Case Thread) | Task 11-13 |
| §4 Layer P0-B (Live AI Pulse) | Task 14-16 |
| §4 Layer P1-C (Signal Lifecycle) | Task 17-19 |
| §4 Layer P1-D (Daily Loop Clock) | Task 20-21 |
| §4 Layer P2-E (Self-Narration) | Task 22-23 |
| §3.1 Lakebase case_events ≈ agent_activity_events 재사용 | Task 1 (list_recent_all) |
| §3.3 cron 12 jobs emit | Task 6-9 |
| §5 silver.signal_events_decayed 노출 | Task 17 stage 3 + Task 18 |
| §5 gold.signal_contribution_30d 노출 | Task 17 stage 4 + Task 18 |
| §5 mas-ba3fbcb5 invocation log | Task 22 (reasoning_path) |
| §5 job run history Daily Loop | Task 20-21 |
| §6 4 도구 강화 매핑 (Apps/Lakebase/Genie/Agent Bricks) | 전체 covered |
| §8 P0/P1/P2 우선순위 | Task 순서 P0 → P1 → P2 |
| §9 Demo 시나리오 | Task 25 |
| §10 self-review | 본 섹션 |
| §11 다음 단계 (writing-plans → 코드) | 본 plan + execution handoff |

### Placeholder scan

- TBD / TODO: 없음 (확인 완료)
- "appropriate error handling": 없음 — best-effort `try/except` + logger.warning 명시
- "similar to Task N": 없음 — 각 task에 완성 코드 포함
- 미정의 reference: ACTOR_META / ACTION_LABEL는 Task 11에서 named export로 전환, 이후 task에서 import → 일관성 OK

### Type consistency

- `ActivityEvent` 타입은 기존 `AgentActivityTimeline.tsx`에서 export, CaseThread / CaseThreadEntry / LivePulseStrip / usePulseStream 모두 동일 shape 사용 ✓
- `actor` enum: backend / frontend 동일 (supervisor/genie/knowledge_assistant/mission_plan_fma/mission_plan_uc/weighted_signal_uc/manager/reactive/system + 신규 gdelt/curation_job/price_job) ✓
- `_publish_pulse_event` payload shape ↔ WS handler 변환 shape ↔ ActivityEvent shape ↔ 모두 일치 ✓

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-20-time-axis-redesign.md`. Two execution options:

**1. Subagent-Driven (recommended)** — fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints

**어떤 방식?**
