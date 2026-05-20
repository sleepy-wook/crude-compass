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

### 2.2b `GET /api/missions/{mission_id}/activity`
Agent Bricks orchestration activity timeline (Lakebase `agent_activity_events` table).

해당 mission의 lifecycle 동안 발생한 agent activity event 50건 (최신순).

**Event source paths**:
- mission create → `weighted_signal_uc:score_computed` + `supervisor:case_opened` + `mission_plan_fma:draft_generated` (3 events, atomic in INSERT transaction)
- confirm / reject / modify / pivot / pause / abort → `manager:<action>` (1 event per call)
- POST /api/supervisor/query with mission_id → 각 sub-agent `<actor>:invoked` + 최종 `supervisor:synthesized`

**Response 200**:
```json
{
  "events": [
    {
      "id": 12,
      "mission_id": "uuid",
      "occurred_at": "2026-05-19T08:15:00+00:00",
      "actor": "supervisor" | "genie" | "knowledge_assistant" | "mission_plan_fma" | "mission_plan_uc" | "weighted_signal_uc" | "manager" | "reactive",
      "action": "case_opened" | "score_computed" | "draft_generated" | "confirmed" | "rejected" | "modified" | "pivoted" | "paused" | "aborted" | "invoked" | "synthesized" | "trigger_fired",
      "result_preview": "위험방어 case 개시 — Pattern Score 82, 긴급도 urgent",
      "metadata": { "...": "..." }
    }
  ]
}
```

**Response 200 (Lakebase 미연동 시)**: `{ "events": [] }`

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

## 3. Discovery Feed (frontend 직접 fetch — endpoint 없음)

D-14 시점 계획 (`/api/discovery/today` + `/api/discovery/{id}/dismiss`)은 미구현.
Discovery 페이지는 다음 endpoint들을 frontend에서 직접 조합하여 feed를 구성:
- `/api/missions/active` (mission proposal)
- `/api/pattern-score/current` (오늘 점수)
- `/api/signals/contribution` (시그널 기여도)
- `/api/market/news-top` (최근 뉴스)
- `/api/market/opec-latest` (OPEC 인용)

복잡한 feed CRUD 불필요 → simplicity. discovery_feed_items Lakebase table은 reactive alert
persist용 (현재 미사용, D-2 이후 옵션).

---

## 4. Pattern Score Endpoints

### 4.1 `GET /api/pattern-score/current`
현재 Pattern Score + 최근 30일 시계열 (Databricks SQL warehouse → silver.pattern_scores_daily).

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
    { "date": "2026-05-08", "pattern_score": 82.0 }
  ]
}
```

### 4.2 `GET /api/pattern-score/history?days=90`
지난 N일 Pattern Score history (default 90, max 2200 — 6년 평시 가치 그래프 §14 Phase 7).

### 4.3 `GET /api/signals/contribution`
최근 30일 signal_type × direction 기여도 (`gold.signal_contribution_30d` view).
시나리오 §6.3 #2 "오늘 점수 82는 호르무즈 35%, 두바이 28% ..." anchor.

### 4.3b `GET /api/signals/{signal_id}/lifecycle`
단일 signal (news_article)의 4-stage forensic view — Trace-a-Signal Investigation 진입점.

- Path param `signal_id`: 정규식 `^[A-Za-z0-9_-]+$` 위반 시 **400 BAD_SIGNAL_ID**
- Databricks SDK `execute_statement` + parameterized query (`:signal_id`) — SQL-injection 방어
- Lakebase/Warehouse 미연결 시 graceful 200 + empty stages

**Stages**:
- `detected`: `bronze.news_articles` row (title/source/published_at)
- `scored`: importance/direction/horizon/confidence (LLM scoring)
- `decay`: `silver.signal_events_decayed` 시간 감쇠 곡선
- `contribution`: `gold.signal_contribution_30d` 30일 누적 + referenced_case_ids

**Response 200**:
```json
{
  "signal_id": "gdelt-2026...",
  "stages": {
    "detected": {"article_id": "...", "title": "...", "source": "Reuters", "published_at": "2026-05-19T...", "importance": 78, "direction": "bullish", "category": "geopolitics", "horizon": "30d", "confidence": 0.82},
    "scored": {"importance": 78, "direction": "bullish", "horizon": "30d", "confidence": 0.82},
    "decay": [{"as_of_date": "2026-05-19", "weight": 1.0, "lambda": 0.05, "days_since_event": 0}],
    "contribution": {"total_contribution": 12.4, "peak_contribution": 3.1, "peak_date": "2026-05-19", "referenced_case_ids": ["case-..."]}
  }
}
```

### 4.4c `GET /api/market/fx-history?days=90`
USD/KRW 일별 환율 + 1d/7d delta + 30일 변동성 (`gold.fx_with_delta` view).
시나리오 §7 #5 + §13 랜딩 코스트 input.

**Response 200**:
```json
{
  "pair": "USD/KRW",
  "history": [
    {"date": "2026-05-14", "rate": 1395.2, "delta_1d": 2.1, "delta_7d": 8.3, "vol_30d": 12.4}
  ]
}
```

### 4.4a `GET /api/market/prices-wide?days=90`
일별 WTI/Brent/Dubai 가격 wide format (`gold.oil_prices_wide` view).
시나리오 §7 #4 anchor — Brent-Dubai spread 포함.

**Response 200**:
```json
{
  "prices": [
    {"trade_date": "2026-05-14", "wti_usd": 78.5, "brent_usd": 82.1, "dubai_usd": 81.2, "brent_dubai_spread_usd": 0.9}
  ]
}
```

### 4.4a-1 `GET /api/market/intraday-summary`
OilPriceAPI 5분 데이터 ticker별 요약 (`bronze.oil_prices`). Cache TTL 60s.
시나리오 §7 — Dubai/Brent/WTI intraday 변동 + 24h 내 spike 시각.

**Response 200**:
```json
{
  "tickers": [
    {
      "ticker": "dubai",
      "price_usd": 105.50,
      "fetched_at": "2026-05-19T08:35:00+00:00",
      "delta_30min_pct": -0.12,
      "delta_24h_pct": 1.05,
      "biggest_spike_pct": 2.8,
      "biggest_spike_at": "2026-05-19T03:15:00+00:00",
      "sample_count": 287
    }
  ]
}
```

### 4.4a-2 `GET /api/market/intraday-prices?hours=24`
bronze.oil_prices 5분 단위 raw 가격 시계열 (chart 시각화용). Cache TTL 60s.
hours 최대 168 (1주).

**Response 200**:
```json
{
  "hours": 24,
  "series": [
    {
      "ticker": "dubai",
      "points": [
        {"price_usd": 105.50, "fetched_at": "2026-05-19T08:35:00+00:00"}
      ]
    }
  ]
}
```

### 4.4b `GET /api/market/news-top?limit=20`
최근 7일 importance ≥ 60 + direction bullish/bearish 뉴스 (`gold.news_top_signals` view).
시나리오 §6.3 #3 anchor — Discovery 페이지 "오늘의 발견" 뉴스 리스트.

**Response 200**:
```json
{
  "items": [
    {
      "event_date": "2026-05-14",
      "source": "Reuters", "tier": "A",
      "title": "...",
      "category": "geopolitics", "direction": "bullish",
      "importance": 78, "raw_tone": -3.5, "mention_count": 12,
      "url": "https://..."
    }
  ]
}
```

### 4.4 `GET /api/market/opec-latest`
최신 OPEC MOMR snapshot (`gold.opec_demand_gap` view). Document Intelligence wow (§9.6) citation badge용.
시나리오 §14 Phase 4 narrator anchor "OPEC MOMR 사우디 추가 감산 시그널".

**Response 200**:
```json
{
  "latest": {
    "report_month": "2026-03",
    "saudi_kbbl_d": 10110.0,
    "iran_kbbl_d": 3176.0,
    "opec_total_kbbl_d": 28630.0,
    "forecast_demand_kbbl_d": 105590.0,
    "supply_demand_gap_kbbl_d": -76960.0,
    "market_balance": "undersupply",
    "saudi_delta_vs_prev": 24.0
  },
  "prev": { /* same shape, 직전 월 */ },
  "source": "ai_parse_document() · OPEC MOMR PDF"
}
```

**Response 200**:
```json
{
  "window_days": 30,
  "items": [
    {
      "signal_type": "news_tone",
      "direction": "bullish",
      "n_signals": 412,
      "total_contribution": 187.5,
      "avg_raw_intensity": 68.0,
      "avg_credibility": 0.85,
      "share_pct": 35.2
    }
  ]
}
```

`share_pct` = absolute(total_contribution) / sum(all abs) × 100. Bar chart bar 길이 = share_pct.

---

## 4.5 Backtest Endpoints (Lakebase OLTP)

> AI-generated content — Lakebase Postgres `backtest_predictions` table.
> Read pattern: WhatIf 페이지 진입 시 300 rows fetch (ms latency).

### `GET /api/backtest/results`
Latest run summary + breakdown (zone, confidence).

**Response 200**:
```json
{
  "summary": {
    "run_id": "llm_20260512T164854",
    "n_total": 300, "n_active": 245,
    "n_hedge": 198, "n_opp": 47,
    "avg_save_pct": 0.626,
    "hit_rate_pct": 74.9
  },
  "by_zone": [
    {"zone": "HIGH", "mission_type": "HEDGE", "n": 89, "avg_save_pct": 1.12, "hit_rate_pct": 81.2}
  ],
  "by_confidence": [
    {"conf_bin": "80-100", "n": 65, "avg_save_pct": 1.34, "hit_rate_pct": 83.0}
  ]
}
```

### `GET /api/backtest/predictions?limit=300`
Latest run의 sample predictions (frontend WhatIf 슬라이더).

**Response 200**:
```json
{
  "predictions": [
    {
      "as_of_date": "2025-11-12",
      "pattern_score": 85.5,
      "confidence_score": 78.0,
      "action_type": "new_mission",
      "mission_type": "HEDGE",
      "target_pct": 75,
      "duration_days": 28,
      "saving_7d_pct": 0.32,
      "saving_30d_pct": 1.18,
      "saving_90d_pct": 1.55,
      "dubai_at_signal_usd": 55.83,
      "dubai_30d_usd": 61.74
    }
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
  "answer": "최근 OPEC MOMR 3개월 사우디 공급 9,500kb/d ...",
  "sql": "SELECT report_month, saudi_kbbl_d ...",  // live 또는 fallback_data 시
  "data": [{"report_month": "2026-04", "saudi_kbbl_d": 9500}],  // live 또는 fallback_data 시
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

## 7.5 Reactive Trigger (Phase 6 — OilPriceAPI spike)

### `POST /api/reactive/demo-spike`
데모용 인위 spike alert trigger — bronze 데이터 변경 없이 EventBus `reactive.alert` 이벤트만 발행.
`DEMO_MODE=true` 필요 (production 404).

**Query params**: `ticker` (default `BRENT_CRUDE_USD`), `delta` (default 2.5)

**Response 200**:
```json
{
  "demo": true,
  "broadcast": "reactive.alert",
  "ticker": "BRENT_CRUDE_USD",
  "delta_pct_5min": 2.5
}
```

데모 시 narrator 1줄: "Brent 5% spike 감지하면 즉시 alert. 시연합니다." → curl POST → frontend 우상단 toast 즉시 표시.

---

### `POST /api/reactive/check-spike`
시나리오 §15 Reactive Trigger — bronze.oil_prices 최근 1h 내 |delta_pct_5min| ≥ 2% spike scan.

Spike 발견 시 **EventBus `reactive.alert` event broadcast** → WebSocket frontend toast + Slack push.

**Response 200**:
```json
{
  "checked_at": "2026-05-14T12:34:56Z",
  "spikes_found": 1,
  "latest_spike": {
    "ticker": "BRENT_CRUDE_USD",
    "price_usd": 108.50,
    "delta_pct_5min": 2.45,
    "fetched_at": "2026-05-14T12:30:00Z"
  },
  "bus_published": true
}
```

**Event schema** (`reactive.alert`):
```json
{
  "type": "reactive.alert",
  "title": "🚨 BRENT_CRUDE_USD +2.45% spike",
  "body": "현재 가격 $108.50. 5분 단위 bullish 시그널 감지. 진행 중 Mission Pivot 검토 권고.",
  "ticker": "BRENT_CRUDE_USD",
  "price_usd": 108.50,
  "delta_pct_5min": 2.45,
  "direction": "bullish"
}
```

**Threshold**: `SPIKE_THRESHOLD_PCT = 2.0` (절대값). Lookback 1 hour.

---

## 7.4 (deprecated 5/16 D-2 — AIS Stream 완전 제거)

이전 `GET /api/fleet/positions` endpoint (K-Petroleum 5척 fleet lifecycle) 는 제거됨.
이유: 한국 flag VLCC 0척 active + 7년 backtest 미사용 → narrative dead weight.
호르무즈 narrative anchor는 GDELT 뉴스 키워드 mention burst로 단일화.

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

### 8.2 `GET /api/slack/health`
Slack Bolt mount + signing secret 상태 확인 (Apps deploy 후 Slack interactivity URL 등록 검증용).

**Response 200**:
```json
{
  "enabled": true,
  "default_channel": "C0B343F7771",
  "signing_secret_set": true
}
```

> D-14 계획됐던 `GET /api/meta/data-sources`는 미구현 — sidebar에 데이터 source 상태 표시 narrative는 Apps 우상단 "6 source · 100% open data · X external" 표시로 대체.

---

## 8.3 Admin Endpoints (D-0 추가)

매니저/시연자가 daily_curation job을 수동으로 trigger + freshness 확인.

### `POST /api/admin/refresh-curation`
Daily curation job 수동 실행 (gold.daily_risk_score 갱신).

**Prerequisite**:
- env `DAILY_CURATION_JOB_ID` (Databricks Workflows job id)
- Apps Service Principal에 해당 job MANAGE 권한

**Response 200**:
```json
{
  "ok": true,
  "run_id": 123456789,
  "job_id": 987654321,
  "message": "데이터 갱신을 시작했습니다. 완료까지 5-10분 소요됩니다."
}
```

**Response 503** (env 미설정):
```json
{
  "detail": {
    "code": "JOB_NOT_CONFIGURED",
    "message": "DAILY_CURATION_JOB_ID 환경변수가 설정되지 않았습니다."
  }
}
```

### `GET /api/admin/curation-status`
gold.daily_risk_score latest date 반환. Frontend가 stale 여부 판단용 (오늘 데이터인지 N일 전인지).

**Response 200**:
```json
{
  "latest_date": "2026-05-18"
}
```

### `POST /api/admin/setup-agent-activity`
One-off setup: agent_activity_events table 생성 + 권한 grant + 기존 mission backfill.

`scripts/setup_agent_activity_events.sql` 파일의 10개 statement를 SP context로 순차 실행 (step-level try/except로 isolation). 멱등 (NOT EXISTS 가드 + IF NOT EXISTS).

Apps SP가 호출 시 SP가 새 table의 owner가 됨 → 이후 INSERT/SELECT 자유.

**Request body**: 없음

**Response 200**:
```json
{
  "total_statements": 10,
  "ok": 8,
  "fail": 2,
  "results": [
    {"idx": 1, "preview": "CREATE TABLE IF NOT EXISTS agent_activity_events ...", "status": "ok", "rowcount": -1},
    {"idx": 2, "preview": "CREATE INDEX ...", "status": "ok"},
    ...
    {"idx": 10, "preview": "SELECT actor, action, COUNT(*) ...", "status": "ok", "select_result": [...]}
  ]
}
```

### `POST /api/admin/missions/clear-active`
기존 active/proposed mission을 hard delete (decisions/pivot_history ON DELETE CASCADE).
mission_plan prompt 갱신 후 jargon-laden mission record를 정리하고 새로 생성하는 demo reset 용도.

**Request body**: 없음

**Response 200**:
```json
{
  "ok": true,
  "deleted_count": 2,
  "deleted_ids": ["uuid-1", "uuid-2"],
  "message": "2건의 mission을 삭제했습니다. (CASCADE: decisions, pivot_history 자동 정리)"
}
```

**Response 503** (Lakebase 미초기화):
```json
{
  "detail": {"code": "LAKEBASE_UNAVAILABLE", "message": "Lakebase pool not initialized."}
}
```

---

## 8.4 Market Memory Endpoints (D-4 추가)

매니저 결정 시점에 "지난 7년 비슷한 패턴 N건 outcome 분포" retrieve.
spec: `2026-05-18-market-memory-decision-platform.md` §3 ★ Wow 1.

### `POST /api/market-memory/similar`

오늘 시그널과 닮은 과거 backtest_predictions row retrieve.

**Request body**:
```json
{
  "pattern_score": 82.0,
  "mission_type": "HEDGE",   // 또는 "OPPORTUNITY" / null
  "limit": 7,                 // default 7
  "score_range": 10.0          // pattern_score ± range
}
```

**Response 200**:
```json
{
  "input": {"pattern_score": 82.0, "mission_type": "HEDGE", "score_range": 10.0},
  "summary": {
    "n": 7,
    "avg_saving_30d_pct": 0.71,
    "avg_saving_7d_pct": 0.32,
    "avg_saving_90d_pct": 1.18,
    "best_saving_30d_pct": 2.8,
    "worst_saving_30d_pct": -1.2,
    "avg_dubai_change_30d_pct": 9.2,
    "hit_rate_pct": 75.0
  },
  "top_matches": [
    {
      "as_of_date": "2022-03-12",
      "pattern_score": 85.0,
      "confidence_score": 78.0,
      "mission_type": "HEDGE",
      "target_pct": 75,
      "saving_7d_pct": 0.4,
      "saving_30d_pct": 2.8,
      "saving_90d_pct": 3.5,
      "dubai_at_signal_usd": 98.5,
      "dubai_30d_usd": 116.3,
      "distance": 3.0
    }
  ],
  "lakebase_available": true
}
```

**Response 200 (Lakebase OAuth pending)**:
```json
{
  "input": {...},
  "summary": {},
  "top_matches": [],
  "lakebase_available": false,
  "reason": "lakebase_oauth_pending"
}
```

---

## 8.5 Pulse Endpoints (D-2 추가 — Live AI Pulse)

`agent_activity_events` cross-mission stream + 24h 누적 통계.
spec: `2026-05-20-time-axis-redesign.md` Tasks 4–5.

### `GET /api/pulse/recent?limit=50`

Cross-mission 최근 events (mission_id NULL인 system/cron event 포함).

**Query**: `limit` (1–200, default 50)

**Response 200**:
```json
{
  "events": [
    {
      "id": "uuid",
      "mission_id": "uuid|null",
      "occurred_at": "2026-05-20T12:34:56Z",
      "actor": "supervisor",
      "action": "case_opened",
      "result_preview": "string|null",
      "metadata": {}
    }
  ],
  "count": 1
}
```

Lakebase 미가용 시 `{"events": [], "count": 0}` graceful.

### `GET /api/pulse/stats`

24h 누적 by_actor / by_action — Daily Loop / Pulse Strip 상단 bar.

**Response 200**:
```json
{
  "total_24h": 42,
  "by_actor": {"supervisor": 12, "weighted_signal_uc": 8},
  "by_action": {"case_opened": 5, "synthesized": 7},
  "active_cases": 3
}
```

Lakebase 미가용 시 0 / 빈 dict graceful.

### `WS /api/ws/pulse`

`agent_activity_events` INSERT 실시간 push. `pulse_bus` (missions bus와 분리) 구독.

**Server → Client events**:
- `{"type": "connected", "ts": <epoch>}` — accept 직후 1회
- `{"type": "pulse", "mission_id": "uuid|null", "actor": "...", "action": "...", "result_preview": "...", "metadata": {}, "ts": <epoch>}`
- `{"type": "ping", "ts": <epoch>}` — 5s keepalive

**Client → Server**:
- `{"type": "subscribe"}` (옵션, ack로 `{"type":"subscribed"}` 회신)

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
