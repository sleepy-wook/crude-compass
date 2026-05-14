# Architecture — Crude Compass

> 작성일: 2026-05-08 (D-14, Phase 3)
> 입력: Phase 1 research + Phase 2 critique + 형욱님 4 design decision
> 본 문서는 시스템 전체 그림. 상세는 [data_model.md](data_model.md) / [api_contract.md](api_contract.md) / [sync_protocol.md](sync_protocol.md) 참조.

---

## 0. Architecture Decisions

### Phase 3 결정 (5/8)
| # | 결정 | 근거 |
|---|---|---|
| **A1** | **Apps + FastAPI 단일 deploy unit** | apps-cookbook.dev 공식 패턴. Vite static = FastAPI mount. Slack Bolt도 같은 FastAPI 안에 mount. 14일 단독 개발 risk 최소화 |
| **A2** | **Lakebase Lakehouse Sync (CDC) 자동** | Autoscaling 기본 기능. missions 변경 → Unity Catalog Delta append (full history). Self-Critique Agent가 이 history로 작동. 추가 코드 X |
| **A3** | **FastAPI WebSocket endpoint (`/ws/missions`)** | mission INSERT/UPDATE 시 모든 connected client에 broadcast. Slack Bolt도 같은 FastAPI에서 emit. 5초 SLA 보장 + 디버그 용이 |
| **A4** | **Mock backtest 진짜 산출** (`scripts/backtest_signals.py`) | 5개월 RSS archive backtest. 5축 Storytelling + Technical 강화. Sprint 3 ⭐ 1.5일 task |

### Sprint 1 검증 결과 보정 (5/10)
| # | 결정 | 근거 |
|---|---|---|
| **A5** | **Lakebase driver = psycopg3 + direct host** (NOT asyncpg, NOT pooled host) | Sprint 1 검증 — pooler가 SASL OAuth bearer 호환 X, asyncpg도 SASL incompat. psycopg3 + direct host 9/9 check PASS |
| **A6** | **OAuth token = `w.postgres.generate_database_credential(endpoint=...)`** SDK method | Sprint 1 검증 — raw API path 잘못 추정한 것 SDK method로 보정 |

### D-14 통합 결정 (5/10, 다른 채팅 시나리오 흡수)
| # | 결정 | 근거 |
|---|---|---|
| **A7** | **Track 1 Social Impact 유지** (Track 2 변경 X) | 우리는 자체 organizational data X (가상 K-Petroleum + 100% open public data). Track 1 명백 정합. Open Data Democratization narrative 강화 |
| **A8** | **공식 4 features 모두 production-grade** (Apps + Lakebase + Genie + AgentBricks Knowledge Assistant) | Apps deploy + Lakebase OAuth pool + Genie 4-tier fallback + Knowledge Assistant 1개 (D-2 등록). Foundation Model API 직접 호출 (Mission Plan Agent). Supervisor/Multi-Agent는 scope-out. |
| **A9** | **GDELT (감지층) + RSS 보강층 (이벤트 드리븐)** 패턴 | RSS 11 source 직접 fetch 대신 GDELT tone score → alert 시점에만 RSS Knowledge Assistant 입력. 효율 + tone 자동화 |
| **A10** | **Document Intelligence 시연** (`ai_parse_document()`) — OPEC MOMR PDF | `bronze.opec_momr_parsed` 적재. Technical Capability 추가 점수. |
| **A11** | **시간 감쇠 시그널별 람다 차등 + UC Function 분리** | `crude_compass.functions.weighted_signal()` 실제 SQL UDF. Genie + curation + backtest 공통 호출. |
| **A12** | **Backtest 시점 슬라이더 (frontend WhatIf) + Confidence Score UI 노출** | UI 컴포넌트 작동 (실 데이터 v6 298건). Delta Time Travel SQL은 scope-out. |

---

## 1. 시스템 컴포넌트 다이어그램

```
                       ┌──────────────────────────────────────────┐
                       │            데이터 source (open)           │
                       │  Reuters · AP · 연합 · FT · BBC (Tier A)  │
                       │  EIA · IEA · OPEC · OFAC · Aramco (Tier B)│
                       │  OilPriceAPI · aisstream · GDACS · ECOS   │
                       └────────────────────┬─────────────────────┘
                                            ↓
   ┌────────────────────────────────────────────────────────────────────────┐
   │                    Databricks Workspace (Premium tier)                  │
   │                                                                         │
   │  ┌─────────────────────────────────────────────────────────────┐       │
   │  │  Lakeflow Jobs (Declarative Automation Bundles)             │       │
   │  │                                                              │       │
   │  │  Job 1: news_pipeline_2hr        →  bronze.news_articles   │       │
   │  │  Job 2: price_pipeline_5min      →  bronze.oil_prices       │       │
   │  │  Job 3: ais_batch_5min ✏️ batch  →  bronze.ais_positions    │       │
   │  │  Job 4: ecos_daily               →  bronze.fx_rates         │       │
   │  │  Job 5: daily_curation 06:30 ⭐  →  silver.pattern_scores  │       │
   │  │  Job 6: weekly_self_critique     →  gold.* (mock stub)      │       │
   │  └──────────────┬──────────────────────────────────┬───────────┘       │
   │                 ↓                                  ↓                    │
   │  ┌──────────────────────────────┐   ┌─────────────────────────────┐    │
   │  │   Unity Catalog (Delta)       │   │   Lakebase Postgres (OLTP)  │    │
   │  │                                │   │                              │    │
   │  │   bronze.news_articles        │   │   missions                  │    │
   │  │   bronze.oil_prices           │←CDC→  decisions                  │    │
   │  │   bronze.ais_positions        │   │   pivot_history             │    │
   │  │   bronze.fx_rates             │   │   discovery_feed_items      │    │
   │  │   silver.pattern_scores_daily │   │                              │    │
   │  │   silver.hormuz_traffic_hourly│   │   (Lakehouse Sync auto CDC) │    │
   │  │   gold.mission_outcomes       │   │                              │    │
   │  │   gold.backtest_results       │   │                              │    │
   │  └──────────────────────────────┘   └──────────────┬──────────────┘    │
   │                 ↑                                  ↓                    │
   │  ┌────────────────────────────────────────────────────────────────┐   │
   │  │  Agent Bricks Custom Agents (Model Serving endpoints)          │   │
   │  │                                                                  │   │
   │  │  Agent 1: Monitoring         (얇게, Job 1 안에 통합)            │   │
   │  │  Agent 2: Simulation          (mock — Genie + canned)          │   │
   │  │  Agent 3: Mission Plan ⭐    (real — Pre-emptive 양방향 제안)  │   │
   │  │  Agent 4: Self-Critique      (mock — hard-coded backtest)      │   │
   │  └────────────────────────────────────────────────────────────────┘   │
   │                                       ↓                                │
   │  ┌────────────────────────────────────────────────────────────────┐   │
   │  │  Foundation Model API · databricks-claude-haiku-4-5 (GA)       │   │
   │  │  News importance + direction scoring · Mission Plan reasoning  │   │
   │  └────────────────────────────────────────────────────────────────┘   │
   │                                                                         │
   │  ┌────────────────────────────────────────────────────────────────┐   │
   │  │  Databricks Apps (단일 deploy unit) · A1                        │   │
   │  │  ┌─────────────────────────┐  ┌──────────────────────────────┐ │   │
   │  │  │  FastAPI (Python 3.11)   │  │  Vite + React 18 (TS)        │ │   │
   │  │  │   ├── /api/missions/...  │  │   ├── PageDiscovery          │ │   │
   │  │  │   ├── /ws/missions  ⭐   │←─┤   ├── PageMission            │ │   │
   │  │  │   ├── /api/slack/events  │  │   ├── PageWhatIf             │ │   │
   │  │  │   ├── /api/slack/interact│  │   └── design-system/         │ │   │
   │  │  │   └── /api/demo/inject   │  │       (tokens + atoms)       │ │   │
   │  │  │                          │  │                              │ │   │
   │  │  │  Slack Bolt (mounted)    │  │  AI/BI Dashboard <iframe>    │ │   │
   │  │  └────────┬─────────────────┘  └──────────────────────────────┘ │   │
   │  │           ↓                                                      │   │
   │  └───────────┼──────────────────────────────────────────────────────┘   │
   └──────────────┼──────────────────────────────────────────────────────────┘
                  ↓
         ┌────────────────────────┐
         │  Slack Workspace        │
         │  Crude Compass Bot      │
         │  - DM (Mission propose) │
         │  - Interactive buttons  │
         │  - URGENT push          │
         └────────────────────────┘
```

---

## 2. 데이터 흐름 — 4-Layer

> 시나리오 §4 (4-Layer) 매핑.

### Layer 1: 정기 News Fetch (Job 1, 2시간 cron)

```
RSS 11 source
    ↓ feedparser
Hard rule filter (오피니언/길이/키워드/공식 source)
    ↓
Foundation Model API · Claude Haiku 4.5
    {importance, category, direction, horizon, confidence, entities}
    ↓
importance >= 60 → bronze.news_articles INSERT
importance >= 80 → Mission Plan Agent 즉시 호출 (URGENT)
```

### Layer 2: Reactive Trigger (Job 2 + Job 3, 5분 cron)

```
OilPriceAPI 3 ticker (Brent/WTI/Dubai) + AIS aisstream batch
    ↓
Spike detection (rule-based)
    - 가격 +/- 2% in 5min
    - AIS 호르무즈 통과량 +/- 20% in 1hr
    ↓
즉시 reactive 뉴스 검색 (Job 1과 별개로)
    ↓
LLM 분석: "원인 + direction + 진행 mission 영향"
    ↓
Slack URGENT alert + Apps WebSocket push
```

### Layer 3: Bidirectional Pattern Detection (Job 5, 매일 06:30) ⭐

```
input: bronze.news_articles (importance >= 60, 90일 window)
    ↓
bullish_score  = SUM(importance × time_decay × source_credibility) WHERE direction='bullish'
bearish_score  = SUM(...) WHERE direction='bearish'
cross_val      = COUNT(category × direction WITH 2+ sources) × 5
pattern_score  = clamp(0, 100, 50 + (bullish - bearish)/max_normalized × 50 + cross_val)
    ↓
silver.pattern_scores_daily INSERT
    ↓
70+ → Mission Plan Agent (HEDGE)
30- → Mission Plan Agent (OPPORTUNITY)
```

### Layer 4: Mission Plan Agent (Agent 3, on-demand)

```
trigger: Pattern Detection 결과 OR 단일 event importance >= 80
    ↓
Foundation Model API call:
   prompt = system + scenario + last 90d signals + active_missions
   output = {mission_type, goal_text, reasoning, simulation_roi, urgency}
    ↓
Lakebase missions INSERT (status='proposed', version=1)
    ↓
[Lakehouse Sync auto CDC → Unity Catalog Delta append]
    ↓
FastAPI broadcast:
   - Slack DM (interactive buttons)
   - WebSocket /ws/missions (proposed event)
```

---

## 3. Lakeflow Jobs — 9 Jobs (D-14 통합 후)

| # | Job | Cron | 상태 | 핵심 task | Notebook |
|---|---|---|---|---|---|
| 1 | news_rss_event_driven | event-driven | **real** (보강층) | GDELT alert 시 RSS fetch (Reuters/AP/연합) → Knowledge Assistant 입력 | `databricks/notebooks/job_news_rss.py` |
| 2 | **gdelt_15min** ⭐ | `*/15 * * * *` | **real** (감지층) | GDELT events + tone score → bronze.news_articles | `databricks/notebooks/job_gdelt.py` |
| 3 | price_pipeline_5min | `*/5 * * * *` | **real** | OilPriceAPI 3 ticker batch + spike | `databricks/notebooks/job_price.py` |
| 4 | ais_batch_5min | `*/5 * * * *` | **real** | aisstream REST polling | `databricks/notebooks/job_ais.py` |
| 5 | eia_weekly | `0 18 * * 3` | should-have | EIA Open Data API 주간 재고 | `databricks/notebooks/job_eia.py` |
| 6 | ecos_daily | `0 18 * * 1-5` | should-have | KRW/USD | `databricks/notebooks/job_ecos.py` |
| 7 | **opec_momr_monthly** ⭐ | `0 0 12 * *` | optional | OPEC MOMR PDF fetch + `ai_parse_document()` | `databricks/notebooks/job_opec_momr.py` |
| 8 | daily_curation_06:30 ⭐ | `30 6 * * *` | **real** ⭐ | Bidirectional Pattern Detection + Mission Plan trigger | `databricks/notebooks/job_curation.py` |
| 9 | weekly_self_critique | `0 18 * * 0` | **mock stub** | Hard-coded 78%/71% backtest | `databricks/notebooks/job_critique_mock.py` |

> Sprint 2 (5/11-13): 1·2·3·4·5·6 구현 + 7 (Document Intelligence 시연용). Sprint 3 (5/14-16): 8 + Mission Plan Agent + Mock backtest 산출.

### Cluster 정책 (비용 인식)

- 모든 Job: **Serverless Standard mode** (4-6분 startup, 70% 절감 vs Performance Optimized)
- Job 6 (weekly): 사실상 호출 안 됨 (mock stub) — startup 비용 0
- Job 3 (ais_batch_5min): 데모 직전 1주 (5/15-22) 가동, 평소 disabled
- $700 credit 중 ~$200 예상 (충분 여유)

---

## 4. AI Agent Architecture — 공식 4 features (정직 정리)

```
[Apps + Lakebase] (Vite + FastAPI, Apps deploy, Lakebase OAuth pool)
   │
   ├─ [Slack Bolt mount] — Slack ↔ Apps 5초 sync
   │
   └─ [Mission Plan Agent — Foundation Model API ⭐]
        │   w.serving_endpoints.query("databricks-claude-haiku-4-5")
        │   chat completion (시스템 프롬프트 + signals input)
        │   → Bidirectional Mission (HEDGE/OPP/Pivot)
        │
        ├ [Genie Space] — backend services/genie.py 4-tier fallback
        ├ [Knowledge Assistant] — D-2 등록 (OPEC MOMR PDF RAG)
        ├ [UC Function `weighted_signal()`] — curation + backtest 공통
        └ [Document Intelligence `ai_parse_document()`] — opec_momr_parsed 적재
```

| # | Component | 상태 | 구현 |
|---|---|---|---|
| 1 | **Databricks Apps** | **real** | `app.yaml` + FastAPI + StaticFiles SPA fallback + secrets resource. D-2 deploy. |
| 2 | **Lakebase Postgres** | **real** | `db/lakebase.py` OAuth pool (max_lifetime=3000), `LakebaseMissionStore` repo, missions DDL. `USE_LAKEBASE=true` flag. |
| 3 | **Genie Space** | **code real, registration D-2** | `services/genie.py` SDK 호출 + 4-tier fallback (live → fallback_data → fallback_text → fallback). `GENIE_SPACE_ID` env. |
| 4 | **AgentBricks Knowledge Assistant** | **D-2 manual** | UC Volume에 OPEC MOMR PDF 1-3개 적재 + Knowledge Assistant endpoint. 공식 AgentBricks 충족 1개 |
| 5 | **Foundation Model API** | **real** | `databricks-claude-haiku-4-5` 직접 호출 — mission_plan.py + recommend_now + backtest v6 3곳. |
| 6 | **Document Intelligence** | **real** | `ai_parse_document()` SQL 한 줄 — `bronze.opec_momr_parsed` 적재 (35 PDF 처리). |
| 7 | **UC Function** | **real** | `crude_compass.functions.weighted_signal()` 람다 차등 시간 감쇠. curation + backtest 공통. |
| 8 | **Lakeflow Jobs** | **real** | 16 YAML, AIS + OilPrice UNPAUSED 자동 5분 cron. |
| 9 | **Backtest v6** | **real** | 298건 stratified samples, 75% hit rate, 7년 4개월. `gold.llm_backtest_predictions` 적재. |
| - | ~~Supervisor Agent~~ | **scope-out** | 미등록. backend orchestration으로 대체 (Mission Plan + Genie + Knowledge Assistant 백엔드 호출). |
| - | ~~Custom Agent~~ | **scope-out** | Foundation Model API 직접 호출이 cost-effective. Agent Bricks Custom Agent 등록은 Sprint 5 swap. |
| - | ~~MLflow tracking~~ | **scope-out** | Delta append만, MLflow run tracking 미구현. |
| - | ~~Self-Critique Agent~~ | **mock** | What-If 페이지 v6 backtest 결과 그대로 표시 (75% hit, 298건 등). |

### Mission Plan Agent (Agent 3) — Real 구현

**입력**:
- pattern_score (current)
- last 90d signals (top importance × direction)
- active_missions (있으면)

**출력 schema** (Pydantic v2):
```python
class MissionPlanOutput(BaseModel):
    mission_type: Literal["HEDGE", "OPPORTUNITY"]
    goal_text: str           # "Term 60% → 75% (4주)"
    reasoning: str           # 한국어 narrative
    simulation_roi: dict     # {scenario: amount_krw_billion}
    urgency: Literal["optional", "default", "urgent"]
    pattern_score: float
```

**Prompt 구조** (system + few-shot):
- system: "You are Crude Compass Mission Plan Agent. Korean petroleum refinery context."
- few-shot: HEDGE 예시 1개 + OPPORTUNITY 예시 1개 (시나리오 §1.2 그대로)
- user: 실제 signal payload

**Endpoint**: `POST {model_serving_endpoint}/invocations`
**호출 시점**: Job 5 (daily_curation) 안 + Reactive Trigger 즉시 (Job 2)

---

## 5. Apps 3 페이지 + Slack Bot

### 5.1 Apps Page Structure (design jsx 1:1 변환)

| Page | Route | 핵심 컴포넌트 | design source |
|---|---|---|---|
| Discovery | `/` | `BidirectionalPatternScale` + 5 cards (HEDGE 제안 / OPP 제안 / Reactive / OSP / Mission 체크포인트) | `design/src/page-discovery.jsx` |
| Living Mission | `/mission` | 28-day timeline + Frame Contracts + Pivot Watch + Cargo map | `design/src/page-mission.jsx` |
| What-If | `/whatif` | Genie textarea + Sensitivity table + Bidirectional backtest | `design/src/page-whatif.jsx` |

> design jsx 파일은 시각 reference. 실제 구현은 `frontend/src/features/{discovery,mission,whatif}/` 안 .tsx 파일로 변환 (toBE Tailwind + shadcn/ui + 공통 design-system 활용).

### 5.2 Design System 구조

```
frontend/src/design-system/
├── tokens.ts              ← 색상/타이포/spacing single source
├── theme.css              ← CSS variables → Tailwind config
└── components/            ← atomic 재사용
    ├── MissionCard/       ← variant: hedge | opportunity
    ├── PatternScoreBar/   ← bidirectional 0-100
    ├── StatusPill/        ← 7가지 상태
    ├── DirectionBadge/    ← 🚨 HEDGE / 🟢 OPPORTUNITY
    ├── SlackMessageCard/
    ├── TimelineEvent/
    └── PivotIndicator/
```

`tokens.ts` 핵심 (design/index.html 추출):
```typescript
export const tokens = {
  colors: {
    crisis:      { 50: '#ffece9', 500: '#FF3621', 900: '#b81d0a' },
    opportunity: { 50: '#E1F4EB', 500: '#0E8F5E', 900: '#06724a' },
    base:        { ink: '#1B3139', paper: '#FCFCFB' },
    line:        { 1: '#ECECE8', 2: '#E2E2DD' },
    accent:      { warn: '#F59E0B', ok: '#10B981' },
  },
  font: {
    display: "'Space Grotesk', 'IBM Plex Sans KR', sans-serif",
    body:    "'IBM Plex Sans', 'IBM Plex Sans KR', system-ui, sans-serif",
    mono:    "'JetBrains Mono', ui-monospace, monospace",
  },
  spacing: { /* 4px base */ },
  radius:  { sm: 6, md: 8, lg: 10, xl: 12, '2xl': 14 },
}
```

→ Tailwind `theme.extend.colors` 등록. 컴포넌트는 토큰만 참조 (하드코딩 hex X).

### 5.3 Slack Bolt Bot

- FastAPI 안 mount (별도 process X — A1 결정)
- Endpoint: `/api/slack/events` + `/api/slack/interactive`
- Bolt SDK Python (`slack-bolt`)
- 핵심 핸들러:
  - `mission_proposed` event → Slack DM with interactive buttons ([Confirm] [Reject] [Modify] [Open in Apps])
  - `block_actions` (button click) → FastAPI POST `/api/missions/{id}/confirm` 등 → Lakebase UPDATE → broadcast
  - URGENT push (Reactive Trigger) → 채널 메시지

---

## 6. 동기화 Architecture (5초 SLA)

> 상세는 [sync_protocol.md](sync_protocol.md).

### 6.1 핵심 원칙

- **Lakebase Postgres = Single Source of Truth** — mission state는 항상 여기서
- **Optimistic concurrency**: `version INT` 컬럼. UPDATE 시 `WHERE version = ?` 검증, 충돌 시 첫 요청만 처리
- **FastAPI broadcast**: mission write → Slack push + WebSocket broadcast 동시 (asyncio.gather)
- **5초 SLA**: write_ts ~ broadcast_ts 차이 P95 5초 안

### 6.2 4가지 동기화 흐름

| # | 흐름 | trigger | 결과 |
|---|---|---|---|
| A | AI 자동 제안 | Job 5 → Mission Plan Agent | Lakebase INSERT → Slack DM + WS push |
| B | Slack confirm | 매니저 [Confirm] 클릭 | Slack action → POST /confirm → Lakebase UPDATE → WS broadcast (Apps update) + Slack message edit |
| C | Apps confirm | 매니저 Apps Confirm 클릭 | Apps POST /confirm → Lakebase UPDATE → WS broadcast (Apps own update + 다른 client) + Slack message edit |
| D | 동시 클릭 충돌 | 양쪽 동시 클릭 | optimistic concurrency `version` 검증 → 첫 요청 200, 두 번째 409 + "이미 confirmed" |

### 6.3 Failure Modes

| Failure | 영향 | 완화 |
|---|---|---|
| Slack API rate limit / 5xx | Slack push 실패, Apps는 정상 | retry 3회 + dead letter log. Apps 사용자는 영향 없음 |
| WebSocket 연결 끊김 | Apps 사용자 1명 sync 실패 | 5초 keepalive + 자동 reconnect, reconnect 시 last_event_id 보내서 missing event replay |
| Lakebase 일시 다운 | mission write 실패 | FastAPI 503 + frontend retry 3회. Slack message에 "동기화 일시 지연" |
| Lakehouse Sync (CDC) lag | Unity Catalog 분석은 지연되나 OLTP는 정상 | 사용자 영향 없음 (분석만 늦음). Self-Critique Agent backfill 가능 |

---

## 7. AI/BI Dashboard

- **embed 방식**: iframe (Apps What-If "어제 복기" 탭 안). Phase 1 검증 — light mode 강제 ✅ (design 이미 light)
- **Dashboard 4 chart**:
  1. Pattern Score 30일 (양방향 zone background)
  2. Hormuz traffic vessels/day
  3. WTI / Brent / Dubai 30일
  4. 매니저 결정 outcome 7건 table
- **데이터 source**: `silver.pattern_scores_daily` + `silver.hormuz_traffic_hourly` + `bronze.oil_prices` + `gold.mission_outcomes`
- **Workspace allowed surfaces**: 형욱님이 manual 추가 (Sprint 4 첫날)

🛑 **MANUAL STEP — AI/BI Dashboard 생성**
WHERE: Databricks Workspace UI → AI/BI → Dashboard
HOW: 4 chart query 작성 → Share > Embed > iframe URL 복사 → frontend `<iframe src=...>` 삽입
SOURCE: https://docs.databricks.com/aws/en/dashboards/share/embedding
완료하면 답해주세요: "done: AI/BI Dashboard 생성 + iframe URL 공유"

---

## 8. 보안

- **Secret 관리**: Databricks secret scope `crude` 안에 보관
  - `oilprice_api_key`, `aisstream_api_key`, `ecos_api_key`, `slack_bot_token`, `slack_signing_secret`, `lakebase_dsn`, `databricks_pat`
- **코드에서 접근**: `dbutils.secrets.get(scope='crude', key=...)` 패턴만. `print()` 절대 X
- **`.env`는 `.gitignore`** ✅
- **Slack signing secret 검증**: Bolt SDK가 자동 처리

🛑 **MANUAL STEP — Secret scope 생성**
WHERE: Databricks Workspace UI → User Settings → Developer → Secret scopes (또는 CLI)
HOW: `databricks secrets create-scope --scope crude` → `databricks secrets put --scope crude --key oilprice_api_key`
SOURCE: https://docs.databricks.com/aws/en/security/secrets/secrets

---

## 9. 비용 추정

| 항목 | 일 비용 | 월 환산 | 5/8-22 14일 |
|---|---|---|---|
| Job 1 (news 2hr) | $0.30 | $9 | $4.2 |
| Job 2 (price 5min) | $0.40 | $12 | $5.6 |
| Job 3 (ais batch 5min, 1주만) | $0.50 (gated) | — | $3.5 |
| Job 5 (daily 06:30) | $0.20 | $6 | $2.8 |
| Foundation Model API (Haiku) | $0.80 | $24 | $11.2 |
| Lakebase OLTP (autoscaling, scale-to-zero) | ~$0.50 | $15 | $7 |
| Apps Compute (Premium) | ~$1.00 | $30 | $14 |
| AI/BI Dashboard | $0 (Premium 포함) | — | $0 |
| **Databricks 합계** | ~$3.7 | ~$96 | **~$48** |
| OilPriceAPI Standard ($19) | — | — | $19 (5/15-22) |
| **총 외부 비용** | | | **~$67 / $700 credit + $19** |

> Continuous AIS WebSocket 채택 시 $7/일 × 14 = $98 추가 → batch 채택 결정 정당화 ✅

---

## 10. Phase 3 산출물 매핑

| 마스터 프롬프트 산출 | 본 작업 산출 |
|---|---|
| `docs/architecture.md` | ✅ 본 문서 |
| `docs/data_model.md` | → 다음 산출 |
| `docs/api_contract.md` | → 다음 산출 |
| `docs/sync_protocol.md` | → 다음 산출 |
| 디렉토리 skeleton | ✅ `databricks/`, `backend/`, `frontend/`, `scripts/` `.gitkeep` |
| `README.md` | ✅ root |
| `.gitignore` | ✅ root |

---

## 11. Sprint 1 진입 시 첫 task (Phase 3 후)

1. **친구분과 30분 sync** — 데모 영상 분량·style 합의, 시나리오 §1.1 도메인 검수 schedule
2. **Manual Step 1**: Databricks workspace secret scope `crude` 생성 + 5개 key 등록
3. **Manual Step 2**: Lakebase 인스턴스 프로비저닝 (Autoscaling project) — 형욱님 직접
4. **Code task**: Lakebase Postgres dialect simple test (`scripts/lakebase_dialect_test.py`) — JSONB/UUID/version 검증
5. **Code task**: OilPriceAPI batch endpoint 검증 (free tier로) — 3 ticker 한 번에 가능한지
6. **Code task**: Bronze Delta DDL (data_model.md 기준) → notebook으로 실행
7. **Code task**: `scripts/seed_mock_backtest.py` 시작 — RSS archive 5개월 fetch
