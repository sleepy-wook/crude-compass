# API Contract — Crude Compass

> 작성일: 2026-05-08 (D-14, Phase 3)
> 입력: [architecture.md](architecture.md) + [data_model.md](data_model.md)
> 본 문서는 FastAPI route + Pydantic v2 schema + TypeScript 타입 1:1 매핑.

---

## 0. 일반 사항

- **Base URL**: Databricks Apps deploy URL (예: `https://<app-name>.databricksapps.com`)
- **인증**: Apps OAuth (Databricks가 자동 처리). FastAPI는 `X-Forwarded-User` 헤더로 사용자 식별
- **JSON encoding**: UTF-8, `Content-Type: application/json`
- **Date format**: ISO 8601 with timezone (`2026-05-08T07:30:00+09:00`)
- **UUID format**: lowercase hex with hyphens
- **Error format**:
  ```json
  { "error": { "code": "MISSION_VERSION_CONFLICT", "message": "이미 confirmed", "details": {...} } }
  ```
- **Idempotency**: write endpoint는 `Idempotency-Key` 헤더 (UUID) 권장 — Slack action 재시도 시 동일 결과

---

## 1. Pydantic v2 모델 (단일 source) → TypeScript

### 1.1 Mission

```python
# backend/app/schemas/mission.py
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field

class MissionType(str, Enum):
    HEDGE = "HEDGE"
    OPPORTUNITY = "OPPORTUNITY"

class MissionStatus(str, Enum):
    PROPOSED = "proposed"
    ACTIVE = "active"
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    PAUSED = "paused"
    PIVOTED = "pivoted"
    ABORTED = "aborted"
    COMPLETED = "completed"

class MissionUrgency(str, Enum):
    OPTIONAL = "optional"
    DEFAULT = "default"
    URGENT = "urgent"

class PivotEntry(BaseModel):
    from_type: MissionType
    to_type: MissionType
    occurred_at: datetime
    reason: str
    pattern_score_at: float

class Mission(BaseModel):
    mission_id: UUID
    mission_type: MissionType
    status: MissionStatus
    goal_text: str
    pattern_score: float = Field(ge=0, le=100)
    reasoning: str
    simulation_roi: dict[str, float]
    urgency: MissionUrgency = MissionUrgency.DEFAULT
    target_pct: int | None = None
    duration_days: int = 28

    created_at: datetime
    confirmed_at: datetime | None = None
    confirmed_by: str | None = None
    confirmed_via: Literal["slack", "apps"] | None = None
    completed_at: datetime | None = None

    pivot_history: list[PivotEntry] = []
    version: int = 1
```

### 1.2 TypeScript 타입 (자동 생성 또는 수동 매핑)

```typescript
// frontend/src/lib/types.ts
export type MissionType = "HEDGE" | "OPPORTUNITY"
export type MissionStatus =
  | "proposed" | "active" | "on_track" | "at_risk"
  | "paused" | "pivoted" | "aborted" | "completed"
export type MissionUrgency = "optional" | "default" | "urgent"

export interface PivotEntry {
  from_type: MissionType
  to_type: MissionType
  occurred_at: string  // ISO 8601
  reason: string
  pattern_score_at: number
}

export interface Mission {
  mission_id: string  // UUID
  mission_type: MissionType
  status: MissionStatus
  goal_text: string
  pattern_score: number
  reasoning: string
  simulation_roi: Record<string, number>
  urgency: MissionUrgency
  target_pct: number | null
  duration_days: number

  created_at: string
  confirmed_at: string | null
  confirmed_by: string | null
  confirmed_via: "slack" | "apps" | null
  completed_at: string | null

  pivot_history: PivotEntry[]
  version: number
}
```

> 권장: Pydantic → TS 자동 변환 도구 (예: `datamodel-code-generator` 또는 OpenAPI export). 14일 단독 개발 시간 절약 위해 **수동 매핑 권장** (단순 8개 모델, 1시간 안에 끝).

---

## 2. REST Endpoints

### 2.1 `GET /api/missions/active`
진행 중 모든 mission (proposed + active + on_track + at_risk + paused).

**Response 200**:
```json
{
  "missions": [Mission, ...]
}
```

### 2.2 `GET /api/missions/{mission_id}`
단일 mission.

**Response 200**: `Mission`
**Response 404**: `{ error: { code: "MISSION_NOT_FOUND" } }`

### 2.3 `POST /api/missions/{mission_id}/confirm`
매니저가 proposed mission을 active로 전환.

**Request**:
```json
{
  "version": 1,            // optimistic concurrency
  "via": "apps"            // | "slack"
  // actor는 X-Forwarded-User에서 추출
}
```

**Response 200**: `Mission` (status='active', version=2)
**Response 409**: `{ error: { code: "MISSION_VERSION_CONFLICT", message: "이미 confirmed", current: Mission } }`

### 2.4 `POST /api/missions/{mission_id}/reject`
매니저가 reject.

**Request**: `{ version: int, via: "apps"|"slack", reason?: str }`
**Response 200**: `Mission` (status='aborted')

### 2.5 `POST /api/missions/{mission_id}/pivot`
양방향 Pivot — 가장 중요한 endpoint.

**Request**:
```json
{
  "version": 2,
  "via": "apps",
  "pivot_action": "pivot",     // "pivot" | "pause" | "abort" | "continue"
  "to_type": "OPPORTUNITY",    // pivot_action='pivot' 일 때만
  "reason": "휴전 임박 + SPR 방출 + PMI 49.2 ..."
}
```

**Response 200**: 새로 생성된 `Mission` (`pivot_history`에 entry 추가)
- `pivot_action='pivot'`: status='pivoted' + 새 mission 생성 (mission_type 변경)
- `pivot_action='pause'`: status='paused'
- `pivot_action='abort'`: status='aborted'
- `pivot_action='continue'`: 변경 없이 pivot_history에 기록만

### 2.6 `POST /api/missions/{mission_id}/modify`
매니저가 goal 일부 수정 (예: target_pct 70 → 65).

**Request**: `{ version: int, target_pct?: int, duration_days?: int }`
**Response 200**: `Mission`

---

## 3. Discovery Feed Endpoints

### 3.1 `GET /api/discovery/today`
오늘의 발견 feed (5개 카드).

**Response 200**:
```json
{
  "feed_date": "2026-05-08",
  "items": [
    {
      "item_id": "...",
      "item_type": "mission_proposal",
      "title": "Pre-emptive HEDGE Mission · Pattern Score 82",
      "body": "...",
      "related_mission_id": "...",
      "metadata": {...}
    }
  ]
}
```

### 3.2 `POST /api/discovery/{item_id}/dismiss`
카드 닫기.

**Response 200**: `{ ok: true }`

---

## 4. Pattern Score Endpoints

### 4.1 `GET /api/pattern-score/current`
현재 Pattern Score + 최근 30일 시계열.

**Response 200**:
```json
{
  "current": {
    "date": "2026-05-08",
    "pattern_score": 82.0,
    "mission_type": "HEDGE",
    "bullish_score": 187.5,
    "bearish_score": 23.0,
    "cross_val_bonus": 20.0
  },
  "history": [
    { "date": "2026-04-09", "pattern_score": 48.0 },
    ...30 entries...
    { "date": "2026-05-08", "pattern_score": 82.0 }
  ]
}
```

---

## 5. WebSocket Endpoint ⭐

### 5.1 `WS /api/ws/missions`
Apps frontend ↔ FastAPI 실시간 양방향 동기화. 상세 protocol은 [sync_protocol.md](sync_protocol.md).

**Connection**: 자동 (Apps page load 시)
**Authentication**: cookie (Apps OAuth session)

**Server → Client events**:
```typescript
type WSEvent =
  | { type: "mission.proposed",  mission: Mission }
  | { type: "mission.confirmed", mission: Mission }
  | { type: "mission.pivoted",   mission: Mission, pivot: PivotEntry }
  | { type: "mission.updated",   mission: Mission }
  | { type: "pattern.changed",   pattern_score: number, mission_type: MissionType }
  | { type: "reactive.alert",    title: string, body: string, related_mission_id?: string }
  | { type: "ping",              ts: number }   // 5s keepalive
```

**Client → Server events**:
```typescript
type WSClientEvent =
  | { type: "subscribe", last_event_id?: number }   // reconnect 시 missing event replay
  | { type: "pong",      ts: number }
```

**SLA**: server event emit ~ client receive < 1s (FastAPI broadcast asyncio).
**Total SLA** (Lakebase write ~ all clients update): < 5s.

---

## 6. Slack Endpoints

### 6.1 `POST /api/slack/events`
Slack Events API (URL verification + message events). Bolt SDK가 자동 처리.

### 6.2 `POST /api/slack/interactive`
Slack interactive button (Confirm / Reject / Pivot 등). Bolt action handler.

**Slack action_id**:
- `mission_confirm` → `POST /api/missions/{id}/confirm`
- `mission_reject` → `POST /api/missions/{id}/reject`
- `mission_modify` → ephemeral message + form
- `mission_pivot` → `POST /api/missions/{id}/pivot`

> Slack signing secret 검증은 Bolt SDK 자동.

---

## 7. Demo Endpoints (5분 데모용)

### 7.1 `POST /api/demo/inject_signal`
평가위원 데모 시 mock 신호 inject.

**Request**:
```json
{
  "scenario": "bearish",   // "bearish" | "crisis" | "spike"
  "count": 5
}
```

**효과**:
- `bearish`: bronze.news_articles 5건 mock insert (direction='bearish', importance 70+) + Pattern Score 즉시 재계산 트리거
- `crisis`: 갑작스 위기 신호 1건 + Brent +5% spike + IRGC 위협 — Reactive Trigger 작동
- `spike`: oil_prices에 mock spike (Brent +5%) — Reactive Trigger 작동

**Response 200**:
```json
{
  "injected": 5,
  "new_pattern_score": 22,
  "triggered_mission_id": "..."   // 있을 경우
}
```

> ⚠️ **데모용. Production rollout 시 disable** (env flag `DEMO_MODE=true`만 enable).

### 7.2 `POST /api/demo/reset`
데모 후 mock data 정리 (Lakebase delete + Bronze tag 삭제).

**Response 200**: `{ ok: true, deleted: 12 }`

---

## 8. Health / Meta

### 8.1 `GET /api/health`
헬스 체크 (Databricks Apps 자동 ping).

**Response 200**:
```json
{
  "status": "ok",
  "version": "0.1.0",
  "lakebase": "connected",
  "databricks_sdk": "connected"
}
```

### 8.2 `GET /api/meta/data-sources`
sidebar에 표시할 데이터 source 상태.

**Response 200**:
```json
{
  "sources": [
    { "name": "AIS aisstream", "status": "connected", "last_fetch": "...", "freshness": "real-time" },
    { "name": "OilPriceAPI",   "status": "connected", "last_fetch": "...", "freshness": "real-time" },
    { "name": "GDACS",         "status": "connected", "last_fetch": "...", "freshness": "real-time" },
    { "name": "ECOS",          "status": "connected", "last_fetch": "...", "freshness": "30m" },
    { "name": "Lakebase",      "status": "connected", "last_fetch": "...", "freshness": "real-time" }
  ]
}
```

---

## 9. FastAPI Project 구조 (`backend/app/`)

```
backend/app/
├── main.py                  ← FastAPI app + Slack Bolt mount
├── core/
│   ├── config.py            ← env vars, secret 로드
│   ├── deps.py              ← Depends (db, current_user)
│   └── logging.py
├── api/
│   ├── missions.py          ← REST endpoints (§2)
│   ├── discovery.py         ← §3
│   ├── pattern.py           ← §4
│   ├── slack.py             ← §6 Bolt handlers
│   ├── demo.py              ← §7
│   └── meta.py              ← §8
├── ws/
│   ├── manager.py           ← ConnectionManager (broadcast)
│   └── routes.py            ← /api/ws/missions
├── db/
│   ├── lakebase.py          ← asyncpg pool + helpers
│   └── repositories/
│       ├── missions.py      ← MissionRepo (CRUD + version check)
│       ├── decisions.py
│       └── feed.py
├── services/
│   ├── mission_plan.py      ← Agent 3 endpoint call
│   ├── pattern.py           ← Pattern Score 조회
│   └── broadcast.py         ← Slack + WS 동시 broadcast
├── schemas/                 ← Pydantic v2
│   ├── mission.py           ← §1.1
│   ├── feed.py
│   └── ws.py                ← §5.1 WSEvent
└── tests/
```

---

## 10. 에러 코드 모음

| code | HTTP | 의미 |
|---|---|---|
| `MISSION_NOT_FOUND` | 404 | mission_id 없음 |
| `MISSION_VERSION_CONFLICT` | 409 | optimistic concurrency 충돌 |
| `MISSION_INVALID_TRANSITION` | 422 | status 전환 불가 (예: completed → active) |
| `LAKEBASE_UNAVAILABLE` | 503 | Lakebase 일시 다운 — 재시도 권장 |
| `LLM_TIMEOUT` | 504 | Foundation Model API 시간 초과 |
| `IDEMPOTENCY_REPLAY` | 200 | 같은 Idempotency-Key 이전 응답 그대로 (정상 처리) |
| `SLACK_RATE_LIMIT` | 429 | Slack rate limit — Apps는 영향 없음 |
| `DEMO_MODE_DISABLED` | 403 | DEMO_MODE 미활성화 — `/api/demo/*` 호출 거부 |

---

## 11. Sprint 별 endpoint 구현 우선순위

| Sprint | Endpoint | 비고 |
|---|---|---|
| Sprint 4 day 1 | §8.1 health, §1.1 schemas, §2.1·2.2 missions GET | 골격 |
| Sprint 4 day 2 | §2.3·2.4 confirm/reject + §5 WebSocket broadcast | Wow 1, 3 |
| Sprint 4 day 3 | §6 Slack Bolt + §3 Discovery + §4 Pattern Score | Wow 5 |
| Sprint 4 day 4 | §2.5 pivot ⭐ + WebSocket replay | Wow 6 |
| Sprint 4 day 5 | §7 Demo endpoints + §8.2 meta | 데모 준비 |
