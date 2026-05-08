# Sync Protocol — Slack ↔ Apps Single Source of Truth

> 작성일: 2026-05-08 (D-14, Phase 3)
> 입력: [architecture.md](architecture.md) + [api_contract.md](api_contract.md)
> 본 문서는 Lakebase Postgres = SSOT 패턴 + 5초 SLA 보장 + failure mode.

---

## 0. 핵심 원칙 (5개)

1. **Lakebase missions = Single Source of Truth**. 다른 어디에서도 mission state 저장 X
2. **모든 write는 FastAPI를 거침**. Slack Bot도 FastAPI에 POST. Apps도 FastAPI에 POST
3. **Optimistic concurrency**: `version INT` 컬럼. 모든 UPDATE는 `WHERE mission_id=? AND version=?`. 충돌 시 첫 요청만 200, 나머지 409
4. **Write-then-broadcast**: Lakebase write 성공 → asyncio.gather로 Slack push + WebSocket broadcast 동시 발사
5. **5초 SLA**: P95(write_ts ~ all_clients_received_ts) < 5s. P99 < 10s

---

## 1. 5초 SLA Budget

```
Total SLA: 5,000ms (5초)

  Lakebase UPDATE        : 100ms  (P95)
  asyncio.gather start   :  10ms
  Slack chat.update API  : 800ms  (P95, 외부 API)
  WebSocket broadcast    :  50ms  (loopback)
  Client render          : 200ms  (Apps frontend reactive)
  ─────────────────────────────
  Total                  : 1,160ms (P95)

여유: 5,000 - 1,160 = 3,840ms — Slack tail latency / network jitter 흡수 가능
```

---

## 2. Optimistic Concurrency

### 2.1 Pattern (모든 mutating endpoint)

```python
# backend/app/db/repositories/missions.py
async def confirm_mission(
    self,
    mission_id: UUID,
    expected_version: int,
    confirmed_by: str,
    via: str,
) -> Mission:
    async with self.pool.acquire() as conn:
        async with conn.transaction():
            # 1. SELECT FOR UPDATE (lock row)
            row = await conn.fetchrow(
                "SELECT * FROM missions WHERE mission_id=$1 FOR UPDATE",
                mission_id,
            )
            if row is None:
                raise MissionNotFound(mission_id)

            # 2. version check
            if row["version"] != expected_version:
                # 충돌! 다른 client가 먼저 confirm
                current = Mission.model_validate(dict(row))
                raise MissionVersionConflict(current=current)

            # 3. status 전환 가능 검증
            if row["status"] != "proposed":
                raise MissionInvalidTransition(
                    f"{row['status']} → active 불가"
                )

            # 4. UPDATE (version increment)
            updated = await conn.fetchrow("""
                UPDATE missions
                SET status='active',
                    confirmed_at=NOW(),
                    confirmed_by=$2,
                    confirmed_via=$3,
                    version=version+1
                WHERE mission_id=$1 AND version=$4
                RETURNING *
            """, mission_id, confirmed_by, via, expected_version)

            return Mission.model_validate(dict(updated))
```

### 2.2 Conflict 응답

```json
HTTP 409 Conflict
{
  "error": {
    "code": "MISSION_VERSION_CONFLICT",
    "message": "이미 confirmed",
    "current": {  // 최신 mission state — frontend 즉시 반영
      "mission_id": "...",
      "status": "active",
      "confirmed_at": "2026-05-08T07:32:15+09:00",
      "confirmed_by": "kim_jihoon",
      "confirmed_via": "slack",
      "version": 2
    }
  }
}
```

→ frontend는 409 받으면 자체 store update + "이미 Slack에서 confirmed" toast 표시.

---

## 3. 4가지 동기화 흐름 (Sequence Diagrams)

### 3.1 Flow A — AI 자동 Mission 제안 (Job 5 → 모든 surface)

```
Job 5 (06:30)        Mission Plan Agent       FastAPI            Lakebase           Slack             Apps WS
    │                       │                    │                  │                  │                 │
    ├─ pattern_score ──────▶│                    │                  │                  │                 │
    │                       ├─ generate plan ───▶│                  │                  │                 │
    │                       │                    ├─ INSERT missions▶│                  │                  │
    │                       │                    │                  │ (version=1)      │                  │
    │                       │                    │◀─ mission ───────┤                  │                  │
    │                       │                    │                                                        │
    │                       │      asyncio.gather─┤                                                        │
    │                       │                    ├─ chat.postMessage (DM) ────▶│                          │
    │                       │                    ├─ ws.broadcast ────────────────────────▶ {type:"mission.proposed"}
    │                       │                    │                              │                 │
    │                       │                    │◀─ Slack 200 ────────────────┤                          │
    │                       │                    │                                                        │
                                              [P95 1.16s]
```

### 3.2 Flow B — Slack에서 매니저 Confirm

```
매니저       Slack         FastAPI                Lakebase        Apps WS              Slack
   │           │              │                       │              │                    │
   ├─ click [Confirm] ───────▶│ /api/slack/interactive│              │                    │
   │           │              ├─ verify signing ──────│              │                    │
   │           │              ├─ confirm_mission ────▶│              │                    │
   │           │              │                       │ version 1→2  │                    │
   │           │              │◀─ mission.active ─────┤              │                    │
   │           │              │                                                            │
   │           │              ├─ asyncio.gather ──────┐                                    │
   │           │              ├─ ws.broadcast ─────────────────────▶ {type:"mission.confirmed"}
   │           │              ├─ chat.update (Slack 카드 "✅ Confirmed via Slack") ────────▶│
   │           │              │                                                            │
   │           │◀─ ack 200 ───┤                                                            │
   │◀─ button disabled                                                                     │
                              [P95 1.16s 안에 Apps + Slack 모두 update]
```

### 3.3 Flow C — Apps에서 매니저 Confirm

```
매니저       Apps              FastAPI            Lakebase        Apps WS              Slack
   │           │                  │                   │              │                    │
   ├─ click Confirm ─────────────▶│ POST /confirm    │              │                    │
   │                              ├─ confirm_mission ▶│              │                    │
   │                              │                   │ version 1→2  │                    │
   │                              │◀─ mission ───────┤              │                    │
   │                              │                                                       │
   │                              ├─ asyncio.gather ──┐                                   │
   │                              ├─ ws.broadcast ────────────────▶ {type:"mission.confirmed"}
   │                              │                            (자기 client + 다른 client)│
   │                              ├─ chat.update (Slack 카드 "✅ Confirmed via Apps") ────▶│
   │                              │                                                       │
   │                              │◀─ Slack 200 ─────────────────────────────────────────┤
   │◀─ HTTP 200 + WS event ───────┤                                                       │
                              [P95 1.16s]
```

### 3.4 Flow D — 동시 클릭 충돌 (race condition)

```
매니저₁ (Slack)    매니저₁ (Apps)    FastAPI                 Lakebase
    │ click Confirm     │ click Confirm    │                       │
    │ ──────────────────│─────────────────▶│ /api/missions/.../confirm  (Slack)
    │                   │                  ├─ SELECT FOR UPDATE ──▶│ row locked
    │                   │ ─────────────────▶│ /api/missions/.../confirm  (Apps)
    │                   │                  ├─ SELECT FOR UPDATE ──▶│ wait for lock
    │                   │                  │                       │
    │                   │                  │ Slack request:                │
    │                   │                  │ - version match (1==1) ✅      │
    │                   │                  │ - UPDATE version=2 ──▶│        │
    │                   │                  │◀─ mission v=2 ────────┤        │
    │                   │                  │ ◀── lock release ────────────  │
    │                   │                  │                                │
    │                   │                  │ Apps request:                  │
    │                   │                  │ - SELECT row (now version=2)   │
    │                   │                  │ - version mismatch (1 != 2) ✗  │
    │                   │                  │ - throw VersionConflict        │
    │ ◀ Slack 200 ──────│                  │                                │
    │                   │ ◀ HTTP 409 ──────┤                                │
                                          → Apps frontend: store update + "이미 Slack에서 confirmed" toast
```

→ **결과**: 양쪽 모두 일관 상태 (status='active', confirmed_via='slack'). Apps 사용자는 친절한 toast.

---

## 4. WebSocket 상세

### 4.1 Connection lifecycle

```
1. Apps page load → new WebSocket("/api/ws/missions")
2. Server: upgrade → call ConnectionManager.connect(ws, user_id)
3. Client: send { type: "subscribe" } (last_event_id optional)
4. Server: 5s마다 { type: "ping" } 발사 (keepalive)
5. Client: { type: "pong" } 응답
6. 30s 동안 pong 없으면 server disconnect (idle cleanup)
```

### 4.2 Reconnect + Replay

```
연결 끊김 감지 (browser onclose) → setTimeout(reconnect, 1s, exp_backoff_max=30s)
재연결 성공 → send { type: "subscribe", last_event_id: 142 }
서버: missions.last_event_id > 142 인 mission 모두 fetch → broadcast (catch up)
```

> **last_event_id 구현**: `missions` 테이블 `last_event_id BIGINT` 컬럼 (data_model.md §4.1). 매 INSERT/UPDATE 시 `nextval('missions_event_seq')` 발급. WS subscribe 시 `WHERE last_event_id > $1` SELECT로 missing event 발송.

### 4.3 ConnectionManager 구조

```python
# backend/app/ws/manager.py
class ConnectionManager:
    def __init__(self):
        self.connections: dict[str, list[WebSocket]] = {}  # user_id → ws list

    async def connect(self, ws: WebSocket, user_id: str):
        await ws.accept()
        self.connections.setdefault(user_id, []).append(ws)

    async def disconnect(self, ws: WebSocket, user_id: str):
        self.connections[user_id].remove(ws)

    async def broadcast(self, event: dict, user_ids: list[str] | None = None):
        targets = self.connections.values() if user_ids is None else \
                  [self.connections.get(uid, []) for uid in user_ids]
        for ws_list in targets:
            for ws in ws_list:
                try:
                    await ws.send_json(event)
                except WebSocketDisconnect:
                    pass  # 다음 cleanup cycle에서 정리
```

> 단일 user (kim_jihoon) 데모이지만 multi-user 가능 구조.

---

## 5. Failure Modes + 복구

### 5.1 Slack API 5xx / rate limit

**시나리오**: chat.update 호출이 5xx 응답 또는 429.
**영향**:
- Apps WebSocket은 정상 작동 ✅
- Slack 카드는 update 안 됨 (사용자 폰에서 stale 상태)
**복구**:
- FastAPI에서 retry 3회 (exponential backoff 100ms, 500ms, 2s)
- 3회 모두 실패 시 dead letter log (`gold.slack_dead_letter` 또는 file)
- 매니저 다음 Slack 메시지 또는 Apps에서 보면 정확한 상태 보임

### 5.2 WebSocket 연결 끊김

**시나리오**: 매니저 노트북 sleep, Wi-Fi 변경.
**영향**: Apps 1명 sync 실패. Slack은 정상.
**복구**: 4.2 재연결 + last_event_id replay.
**limit**: last_event_id 기록 보존 7일. 7일 이상 끊김 → full refresh (history 무손실)

### 5.3 Lakebase 일시 다운

**시나리오**: Lakebase Autoscaling scale-up 중 1-3초 지연 또는 maintenance.
**영향**: 모든 mission write 실패.
**복구**:
- FastAPI 503 응답
- Frontend 자동 retry 3회 (1s, 3s, 5s)
- Slack action button → ephemeral 메시지 "잠시 후 다시 시도"
**제한**: 30초 이상 다운 시 데모 영향 → Sprint 4 끝 부하 테스트로 사전 검증

### 5.4 Lakehouse Sync (CDC) lag

**시나리오**: Unity Catalog `gold.missions_history` append 지연 (수 분).
**영향**: 분석/Self-Critique Agent만 영향. OLTP는 정상.
**복구**: 사용자 영향 없음. Self-Critique Agent는 매주 weekly cron이라 분 단위 lag 무시.

### 5.5 Idempotency 깨짐 (Slack action 재시도)

**시나리오**: Slack interactive payload 재시도 시 같은 action 두 번 도착.
**영향**: 두 번째 confirm 시도 시 409.
**복구**: `Idempotency-Key` 헤더 (Slack action에 저장된 callback_id 활용). 같은 key로 들어오면 이전 응답 그대로 반환.

```python
# backend/app/services/idempotency.py
async def with_idempotency(key: str, handler: Callable) -> dict:
    cached = await redis.get(f"idem:{key}")
    if cached:
        return json.loads(cached)
    result = await handler()
    await redis.setex(f"idem:{key}", 300, json.dumps(result))  # 5분 TTL
    return result
```

> Sprint 4에서 Redis 도입 부담이면 in-memory dict + 60초 TTL로 대체 가능 (단일 FastAPI instance).

---

## 6. 테스트 시나리오 (Sprint 4 day 5)

### 6.1 Happy path
1. Job 5 → Mission proposed
2. Slack DM 1초 안 도착
3. Apps WebSocket event 1초 안 도착
4. 매니저 Apps에서 Confirm
5. Slack 카드 update + Apps status pill update — 5초 안

### 6.2 충돌 path
1. 매니저 Slack + Apps 양쪽 열고 거의 동시 Confirm 클릭
2. 첫 클릭만 success
3. 두 번째 클릭 — 409 응답 + frontend "이미 confirmed" toast

### 6.3 Reconnect path
1. Apps 연 상태에서 Wi-Fi 끊기
2. Slack에서 mission Pivot 클릭
3. Apps Wi-Fi 복구 — last_event_id replay로 pivot 이벤트 catch
4. Apps timeline에 pivot marker 표시

### 6.4 Reactive trigger path
1. `POST /api/demo/inject_signal { scenario: "spike" }` 호출
2. Bronze.oil_prices에 mock spike 적재
3. Job 2 next run에서 spike detect → Reactive trigger
4. Slack URGENT push + Apps WebSocket {type: "reactive.alert"} 도착 — 5초 안

---

## 7. Phase 3 → Sprint 진입 시 첫 sync 실험

**Sprint 1 day 2** (data_model + sync skeleton 완료 후):
- `scripts/sync_smoke_test.py` — 단일 mission INSERT → SELECT 1초 안 검증 + version conflict 시뮬

**Sprint 4 day 1** (FastAPI 골격 완성 후):
- 단일 client WebSocket connect → broadcast 1건 receive 검증

**Sprint 4 day 5** (통합):
- 위 §6 4가지 시나리오 수동 테스트 + 시간 측정

---

## 8. 시나리오와의 매핑 (시나리오 §7)

| 시나리오 §7 흐름 | 본 문서 |
|---|---|
| §7.1 Single Source of Truth diagram | §0 핵심 원칙 + §3 sequence diagrams |
| §7.2 A. AI Pre-emptive Mission | §3.1 Flow A |
| §7.2 B. Slack Confirm | §3.2 Flow B |
| §7.2 C. Apps Confirm | §3.3 Flow C |
| §7.2 D. 동시 충돌 방지 | §3.4 Flow D + §2 Optimistic Concurrency |
