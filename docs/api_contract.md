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

### 2.1b `GET /api/missions/all`
모든 mission (active + completed + aborted). 히스토리 페이지 또는 데모 시점 reset 확인용.

**Response 200**: `{ missions: Mission[] }`

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

### 2.7 `POST /api/missions/recommend`
LLM Mission Plan Agent 호출 (full body 버전).

**Request**: `MissionPlanInput` (pattern_score / bullish / bearish / cross_val_bonus / signal_count_90d / top_signals[] / active_mission?)
**Response 200**:
- `action_type='new_mission'` → `{ action: "new_mission", mission: Mission, confidence_score }`
- 기타 → `{ action: pivot|pause|abort|continue, output: MissionPlanOutput }`
**Response 500**: `{ code: "LLM_CALL_FAILED" }`

### 2.8 `POST /api/missions/recommend_now`
**Demo-friendly wrapper** — no body 또는 optional override. Discovery '지금 새 추천 생성' 버튼.
내부에서 (a) demo narrative signals seed, (b) active mission 자동 추출, (c) LLM 호출.

**Request** (모두 optional):
```json
{
  "pattern_score": 82.0,
  "bullish_score": 78.0,
  "bearish_score": 22.0,
  "use_demo_signals": true   // false면 빈 signals → LLM 추론에 의존
}
```

**Response 200**:
- `action='new_mission'` → `{ action, mission: Mission, confidence_score, llm_endpoint }`
  · mission.source = `"agent"` (provenance: LLM-generated)
- 기타 → `{ action, output: MissionPlanOutput, llm_endpoint }`

**LLM 응답시간**: cold start 5-10초. frontend는 mutation pending spinner. WS 'mission.proposed' event로 자동 list 업데이트.

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
평가위원 데모 시 narrative scenario별 Mission 직접 inject — 시그널 누적→LLM→Mission 흐름 shortcut.
`/api/missions/recommend`와 별도. Mission.source='demo_inject'로 구분.

**Request**:
```json
{
  "scenario": "hormuz_blockade",
  // scenario: "hormuz_blockade" | "ceasefire" | "saudi_cut" | "us_inventory_surprise" | "custom"
  // 이하 optional overrides — preset 위에 None 아닌 값만 적용. custom은 mission_type+goal_text+reasoning 필수.
  "mission_type": "HEDGE",            // optional. "HEDGE" | "OPPORTUNITY"
  "pattern_score": 82.0,              // optional, 0~100
  "urgency": "urgent",                // optional. "urgent" | "default" | "optional" (lowercase)
  "goal_text": "Term 60% → 75% (4주)", // optional
  "reasoning": "...",                  // optional
  "target_pct": 75,                   // optional, 0~100
  "duration_days": 28,                // optional, 1~365
  "simulation_roi": {"Brent_130": 410.0}  // optional
}
```

**Scenarios** (narrative 1:1 매핑 — `docs/crude_compass_final_scenario.md`):
- `hormuz_blockade`: §14 Phase 4 — HEDGE, URGENT, Score 82, Term 60%→75%
- `ceasefire`: §14 Phase 6 — OPPORTUNITY, URGENT, Score 78, Term 60%→40%/Spot 40%→60%
- `saudi_cut`: §5 평시 — HEDGE, DEFAULT, Score 70, Term 60%→70%
- `us_inventory_surprise`: §5 평시 — HEDGE, OPTIONAL, Score 62, Term 60%→65%
- `custom`: 100% overrides 의존 — mission_type/goal_text/reasoning 누락 시 422

**효과**:
1. Mission 생성 (source='demo_inject') + store.create
2. EventBus.publish('mission.proposed') → slack_bus_subscriber가 Slack DM 카드 push + WS broadcast
3. 매니저는 Slack 또는 Apps에서 [Confirm/Reject/Pivot/Modify/Open in Apps] 작동

**Response 200**:
```json
{
  "mission": { /* Mission full schema */ },
  "slack_status": "live",          // "live" | "dry-run"
  "channel": "C0B343F7771",        // Slack channel id or null
  "source": "demo_inject"
}
```

**Error**:
- `404`: `DEMO_MODE` 미활성화 — router 자체 mount 안 됨
- `422 INVALID_SCENARIO`: scenario 이름 잘못
- `422 CUSTOM_REQUIRES_FIELDS`: custom인데 필수 field 누락

> ⚠️ **데모용. Production rollout 시 disable** (env flag `DEMO_MODE=true`만 enable).
> 시그널 inject (bronze table) → Pattern Score 재계산 → LLM 흐름은 Sprint 5에서 추가 예정.

### 7.3 `POST /api/genie/query`
Databricks Genie Space 자연어 질의 — live 호출 또는 graceful fallback.
시나리오 §9.3 anchor. 평가위원 "Genie 어떻게 썼나요?" 질문 시 라이브 시연.

**Request**:
```json
{
  "question": "최근 7일 호르무즈 통과 유조선은?",
  "conversation_id": null
  // 또는 이전 응답의 conversation_id로 multi-turn 이어가기
}
```

**Response 200** (항상 200, source field로 mode 구분):
```json
{
  "answer": "최근 7일 호르무즈 BBOX 통과 유조선 N척 ...",
  "sql": "SELECT count(*) ...",  // live 또는 fallback_data 시
  "data": [{"vessels": 12, "latest": "2026-05-14T..."}],  // live 또는 fallback_data 시
  "conversation_id": "conv_abc123",
  "message_id": "msg_xyz789",
  "source": "live"
}
```

**Source enum** (transparency — UI에 항상 노출):
- `live`: Genie Conversation API 정상 호출 (settings.genie_enabled=true)
- `fallback_data`: GENIE_SPACE_ID 미설정 or SDK 실패 → Lakebase 직접 SQL 호출 + 결과 포맷팅
- `fallback_text`: SQL 실패 → hardcoded 설명 텍스트
- `fallback`: 키워드 매칭 실패 → generic meta-answer (예시 3가지 안내)

**Timeout**: live 호출 8초 (cold start 대응). 초과 시 fallback 분기.

**Health**: `GET /api/genie/health` → `{"enabled": bool, "space_id": str, "fallback_available": true}`

---

## 7.4 Fleet Endpoints (K-Petroleum 5척 lifecycle)

### `GET /api/fleet/positions`
시나리오 §4 K-Petroleum 가상 fleet 5척 (KPETRO_001~005) 실시간 위치 + zone 분류.

`bronze.ais_positions` 의 `mmsi LIKE 'KPETRO_%'` 최신 1행씩 (QUALIFY ROW_NUMBER).
5 fixed slot 보장 — 미적재 vessel은 placeholder (zone='unknown').

**Response 200**:
```json
{
  "vessels": [
    {
      "mmsi": "KPETRO_001",
      "vessel_name": "VLCC KPETRO_001",
      "lat": 28.58,
      "lon": -94.25,
      "speed_knots": 0.3,
      "heading_deg": null,
      "in_hormuz_bbox": false,
      "status": "anchored",
      "fetched_at": "2026-05-14T11:09:28Z",
      "zone": "gulf_of_mexico"
    },
    {
      "mmsi": "KPETRO_002",
      "vessel_name": null,
      "lat": null, "lon": null,
      "speed_knots": null, "heading_deg": null,
      "in_hormuz_bbox": null,
      "status": "no_data",
      "fetched_at": null,
      "zone": "unknown"
    }
  ]
}
```

**Zone enum**: `hormuz | red_sea | indian_ocean | korean_waters | gulf_of_mexico | transit | unknown`

**비고**:
- 5분 cron (`crude-compass-ais-batch-dev`)으로 매 5분 bronze 적재
- VLCC AIS 보고 빈도 ~6분 — 데이터 미적재 vessel은 1-2 cron 안에 채워짐
- vessel_name 도 anonymize 처리 (`VLCC KPETRO_NNN`)
- AIS public open data (IMO mandate) + 가상 K-Petroleum narrative (시나리오 §4)

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
