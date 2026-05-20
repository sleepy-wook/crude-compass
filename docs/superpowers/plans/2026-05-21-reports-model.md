# Reports Model Implementation Plan

> 날짜: 2026-05-21 (D-1, 마감 5/22)
> 작성 컨텍스트: Decision Room mission/case 모델이 도메인 (Term/Spot 비중 자주 안 바꿈) 과 모순 → 보고서(report) 모델로 전면 reframe.
> 이 plan은 post-compaction 후에도 단독으로 읽고 진행 가능하게 설계됨.

---

## 0. Compact-safe Context

### 0.1 핵심 변경 요지

- **mission 폐기, reports 도입**: AI는 "비중 X% 권고" mission을 매일 만드는 spam이 아니라, **trigger 시 보고서 생성** → 매니저가 keep/drop으로 시그널 가치 평가 → keep된 시그널만 비중에 영향
- **2-단 구조**:
  1. **일반 reports** (event-driven, trigger 시): 시그널 + 권고 action. 매니저 [보관/추가조사/drop].
  2. **Daily 비중 보고서** (매일 06:30, 1건): 어제 보관된 일반 reports + 전날 daily → 비중 제안 (**참고용 only, action 없음**)
- **AI 자율**: stale report 자동 drop, continuation 시 thread 자동 추가. **보관은 매니저만**.
- **Slack 양방향 sync** 유지.

### 0.2 도메인 reality (이 plan을 정당화하는 사실)

- 정유사 Term 비중 변경 = 협상·계약 갱신 시간 (주~월). 매일 변경 불가
- OSP 발표 = 매월 2주차 (lagging, 직전 2개월 평균)
- Spot cargo 구매 결정 = 주/10일 단위
- 따라서 **매일 "비중 60→75%" 권고는 도메인 mismatch** → 시그널 보고서로 분리

### 0.3 최종 결정된 trigger (옵션 A + Dubai ±2%)

| Trigger | 임계치 | 빈도 | 의미 |
|---|---|---|---|
| `gdelt_signal` | 단일 뉴스 importance ≥ 80 | 주 2-5회 | 큰 뉴스 이벤트 |
| `price_spike` | Dubai 24h ±2% | 주 2-3회 | 시장 reaction |
| `pattern_drift` | pattern_score 7일 이동평균 ±10점 | 월 1-2회 | 누적 regime shift |

### 0.4 매니저 action vocabulary (보고서 안 recommendation 필드 hint)

- `HOLD` — 현 비중 유지
- `DEFER SPOT` — 이번 주 Spot 발주 보류
- `ACCELERATE SPOT` — Spot 발주 가속
- `REVIEW TERM` — 다음 분기 회의에서 Term 비중 검토 (즉시 X)
- `HEDGE` — futures/options 단기 검토
- `DIVERSIFY` — 공급원 다변화 검토 (Dubai → Murban/ESPO)

> AI는 위 vocabulary에서 1개 primary + 0-2 secondary 권고. `recommendation` 필드는 TEXT (AI freely formed, but should map to one of above).

### 0.5 현재 자산 (변경 안 함)

- Lakebase live (instance: `ep-lucky-star-d1rlmmrr`)
- Apps deployed (`crude-compass.aws.databricksapps.com`)
- Agent Bricks: Supervisor (mas-ba3fbcb5) + Knowledge Assistant (ka-6b456458)
- Genie Space `01f150e05229190aa9de93c97afde034`
- Foundation Models: Haiku-4-5, Opus-4-7, etc.
- UC Catalog: bronze (6) + silver (2) + gold (1+7 views) + 2 UDFs
- Jobs (12): gdelt-15min, price-pipeline, oil-prices-daily, ecos-daily, eia-weekly, opec-momr, daily-curation, daily-risk-backfill, backtest x3

### 0.6 deprecation 대상

- `missions` 테이블 — 그대로 두되 UI 비노출 (DB 보존, 코드 안 씀)
- `agent_activity_events` 테이블 — 그대로 유지 (Pulse 용 시그널이며 reports와는 별개 layer)
- frontend `ActionQueue` / `SelectedCaseDetail` / `CaseRow` / `CaseThread` — 코드는 남겨두고 Decision Room에서는 새 컴포넌트로 교체

---

## 1. Architecture Overview

```
[데이터 layer — 변경 없음]
  bronze.news_articles (gdelt) / oil_prices / oil_prices_daily / fx_rates / eia_inventory / opec_momr_parsed
  silver.pattern_scores_daily / signal_events_decayed
  gold.daily_risk_score + 7 views
  Lakebase: missions (deprecated) + agent_activity_events (유지)

[신설 layer — 이 plan]
  Lakebase tables:
    - reports        (event-driven, 매니저 inbox)
    - daily_reports  (매일 06:30 cron, 비중 제안)
  Backend:
    - app/api/reports.py    CRUD + action endpoints
    - app/db/repositories/reports.py
    - app/services/report_generator.py    LLM call (Haiku-4-5)
    - app/services/daily_report.py        06:30 aggregation + LLM
    - app/services/trigger_detector.py    3 trigger types
  Notebook:
    - databricks/notebooks/job_daily_report.py    NEW (06:30)
    - databricks/notebooks/job_gdelt.py           MODIFY (gdelt_signal trigger)
    - databricks/notebooks/job_price.py           MODIFY (price_spike trigger)
    - databricks/notebooks/job_curation.py        MODIFY (pattern_drift trigger)
  Frontend:
    - components/ReportsInbox.tsx       NEW (Decision Room 좌)
    - components/SelectedReportDetail.tsx  NEW (Decision Room 우)
    - components/ReportThread.tsx       NEW (추가 조사 thread)
    - components/DailyReportHero.tsx    NEW (Dashboard 상단)
    - pages/ArchivePage.tsx             NEW (보관/drop 보고서)
    - pages/Dashboard.tsx               MODIFY (Reports 모델로 교체)
  Slack:
    - DM with [보관/추가조사/drop] interactive buttons
    - Daily report channel push
```

---

## 2. Schema

### 2.1 `reports` 테이블

```sql
CREATE TABLE IF NOT EXISTS reports (
  report_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  parent_id          UUID REFERENCES reports(report_id),

  trigger_type       TEXT NOT NULL,
  trigger_meta       JSONB NOT NULL DEFAULT '{}'::jsonb,

  status             TEXT NOT NULL DEFAULT 'pending',
  status_changed_at  TIMESTAMPTZ,
  status_changed_by  TEXT,

  headline           TEXT NOT NULL,
  summary            TEXT NOT NULL,
  reasoning          JSONB NOT NULL DEFAULT '{}'::jsonb,
  recommendation     TEXT,
  related_signals    JSONB NOT NULL DEFAULT '[]'::jsonb,

  revisits_id        UUID REFERENCES reports(report_id),
  ai_drop_reason     TEXT,

  version            INT NOT NULL DEFAULT 1,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT chk_trigger CHECK (trigger_type IN ('gdelt_signal', 'price_spike', 'pattern_drift')),
  CONSTRAINT chk_status  CHECK (status IN ('pending', 'kept', 'dropped', 'ai_dropped')),
  CONSTRAINT chk_changed_by CHECK (status_changed_by IS NULL OR status_changed_by IN ('manager', 'ai'))
);

CREATE INDEX IF NOT EXISTS idx_reports_status_created ON reports (status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reports_parent ON reports (parent_id, created_at);
CREATE INDEX IF NOT EXISTS idx_reports_pending ON reports (created_at DESC) WHERE status = 'pending';
```

### 2.2 `daily_reports` 테이블

```sql
CREATE TABLE IF NOT EXISTS daily_reports (
  daily_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  report_date        DATE UNIQUE NOT NULL,
  prev_daily_id      UUID REFERENCES daily_reports(daily_id),

  kept_report_ids    UUID[] NOT NULL DEFAULT ARRAY[]::uuid[],
  kept_count         INT NOT NULL DEFAULT 0,
  kept_summary       TEXT,
  prev_daily_summary TEXT,
  market_context     TEXT,

  ratio_suggestion   JSONB NOT NULL DEFAULT '{}'::jsonb,
  reasoning          TEXT,
  confidence         NUMERIC(5,2),

  created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_daily_reports_date ON daily_reports (report_date DESC);
```

`ratio_suggestion` JSONB 예시:
```json
{
  "direction": "lean_hedge | neutral | lean_opportunity",
  "term_delta_pct": "+5",
  "spot_delta_pct": "-5",
  "qualitative": "단기 위험 누적 — 보수적 자세 권고",
  "scenarios": [
    {"name": "base",   "expected_saving_pct": 0.3},
    {"name": "bull",   "expected_saving_pct": -1.1},
    {"name": "bear",   "expected_saving_pct": 1.5}
  ]
}
```

---

## Phase 0 — Pre-flight (사용자 직접 검증, 5분)

이 phase는 사용자가 직접 SDK 명령으로 현재 상태 검증. **AI는 결과 받아서 확인 후 다음 phase**.

### 0.1 작업

다음 명령 실행 후 결과를 chat에 붙여넣음:

```powershell
# (1) 현재 cron jobs 확인
databricks --profile crude-compass jobs list

# (2) 현재 Lakebase tables 확인 (psql)
# (또는 notebook에서):
# SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';

# (3) Unity Catalog crude_compass schemas
databricks --profile crude-compass schemas list crude_compass

# (4) Apps 상태
databricks --profile crude-compass apps get crude-compass | python -c "import sys,json; d=json.load(sys.stdin); print('status:', d.get('compute_status', {}).get('state'))"

# (5) Serving endpoints (Foundation Model + Agent Bricks)
databricks --profile crude-compass serving-endpoints list --output json | python -c "import sys,json; data=json.load(sys.stdin); print(*[e['name'] for e in data], sep='\n')"
```

### 0.2 확인 항목

- ✅ Jobs 12개 모두 존재 (특히 `daily-curation`, `gdelt-15min`, `price-pipeline`)
- ✅ Lakebase `missions`, `agent_activity_events` 테이블 존재
- ✅ Apps ACTIVE
- ✅ Foundation Model `databricks-claude-haiku-4-5` READY

### 0.3 🛑 CONFIRM GATE 1

사용자 응답 후 AI가 결과 검토. 이상 있으면 plan 조정. 정상이면 Phase 1.

---

## Phase 1 — Lakebase DDL + repo (backend, 2시간)

### 1.1 작업 (AI)

- Create: `databricks/schemas/lakebase.sql` 에 reports / daily_reports DDL 추가
- Create: `backend/app/db/repositories/reports.py`
  - `insert_report(conn, report) -> report_id`
  - `update_status(conn, report_id, status, by) -> bool`
  - `list_pending(conn, limit) -> [Report]`
  - `list_by_status(conn, status, limit, since) -> [Report]`
  - `get_with_thread(conn, report_id) -> {report, thread: [Report]}`
  - `find_similar_in_archive(conn, signal_fingerprint) -> Report | None`
- Create: `backend/app/db/repositories/daily_reports.py`
  - `insert_daily(conn, daily) -> daily_id`
  - `get_for_date(conn, date) -> Daily | None`
  - `get_prev(conn, date) -> Daily | None`
  - `list_recent(conn, limit) -> [Daily]`
- Create: `backend/app/schemas/report.py` Pydantic 모델 (Report, DailyReport, ReportThread)
- Create: `backend/tests/test_reports_repo.py` Lakebase-gated tests
- Modify: `backend/app/db/lakebase.py` 의 `migrate_d4` (또는 신규 `migrate_reports`) 에 DDL 자동 apply 추가

### 1.2 검증 (AI)

```powershell
cd backend
uv run pytest tests/test_reports_repo.py -v
```
PASS or SKIPPED (LAKEBASE_HOST 없을 때)

### 1.3 🛑 사용자 action 필요

backend lifespan startup에 migrate 호출이 포함되지만, Apps 재배포 전까지는 DDL 적용 X. 옵션 둘:

- **Option A (추천)**: backend 로컬 boot → `migrate_reports()` 자동 실행 → 테이블 생성. backend 한 번 띄우고 stop.
- **Option B**: psql 직접 접속해서 DDL 수동 apply.

사용자가 어느 쪽 선호하는지 chat에서 답:
```
A) backend 로컬 boot로 migrate (가장 단순)
B) psql 수동 apply
```

### 1.4 🛑 CONFIRM GATE 2

테이블 생성 확인 (psql 또는 Apps deploy 후):
```sql
SELECT table_name FROM information_schema.tables 
 WHERE table_schema='public' AND table_name IN ('reports','daily_reports');
```
→ 2 rows 확인 후 Phase 2.

---

## Phase 2 — Report generator (backend, 3-4시간)

### 2.1 작업 (AI)

- Create: `backend/app/services/trigger_detector.py`
  - `detect_gdelt_signal(conn) -> List[TriggerEvent]` — 최근 N분 importance≥80 articles
  - `detect_price_spike(conn) -> List[TriggerEvent]` — Dubai 24h ±2%
  - `detect_pattern_drift(conn) -> List[TriggerEvent]` — pattern_score 7일 MA ±10pt
- Create: `backend/app/services/report_generator.py`
  - `generate_report(trigger_event) -> Report`
  - Foundation Model API call (Haiku-4-5)
  - Prompt: trigger context + recent signals + current portfolio (Term 60/Spot 40 default) → headline / summary / reasoning / recommendation (from vocabulary)
- Create: `backend/app/services/report_ai_decision.py` — AI 자율 판단
  - `judge_pending(prev_report, new_snapshot) -> Verdict` (`stale` | `continuation` | `unrelated`)
  - `find_archive_match(new_snapshot, archive) -> Report | None`
- Create: `backend/app/api/reports.py`
  - `GET /api/reports/inbox` — pending list (max 10)
  - `GET /api/reports/{id}` — detail + thread
  - `GET /api/reports/archive?status=...` — archive list
  - `POST /api/reports/{id}/keep` — 보관
  - `POST /api/reports/{id}/drop` — drop
  - `POST /api/reports/{id}/investigate` — 추가 조사 (AI invoke + thread row insert)
- Create: `backend/tests/test_report_generator.py`
- Create: `backend/tests/test_reports_api.py`
- Modify: `backend/app/main.py` — router register

### 2.2 LLM Prompt 구조 (report_generator)

```
System:
You are Crude Compass Report Generator. Korean refinery procurement analyst.

Input:
  Trigger: <gdelt_signal | price_spike | pattern_drift>
  Trigger detail: <data>
  Recent signals (24h): <top 5 with importance, direction, source>
  Current portfolio (assumed): Term 60% / Spot 40%
  Recent pattern_score: <value, 7-day trend>

Output (JSON):
  {
    "headline": "한 줄 (50자 이내)",
    "summary": "3줄 (200자 이내)",
    "reasoning": {
      "key_signals": [...],
      "logic": "한 단락 (300자 이내)",
      "risk_factors": [...]
    },
    "recommendation": "HOLD | DEFER SPOT | ACCELERATE SPOT | REVIEW TERM | HEDGE | DIVERSIFY",
    "recommendation_text": "구체 권고 (100자 이내, 예: '이번 주 Spot 발주 1주 보류 권고')"
  }
```

### 2.3 검증

```powershell
cd backend && uv run pytest tests/test_report_generator.py tests/test_reports_api.py -v
```

### 2.4 🛑 사용자 action 필요

없음 (Foundation Model API 권한 이미 있음). 단 demo data 생성 위해 매뉴얼 trigger 1회 가능:
```
POST /api/admin/reports/trigger-now (테스트 endpoint)
```
사용자 chat 응답에서 확인 후 Phase 3.

### 2.5 🛑 CONFIRM GATE 3

Demo data 1-3건 자동 생성 OK 확인 후 Phase 3.

---

## Phase 3 — Daily report cron (backend + notebook, 3시간)

### 3.1 작업 (AI)

- Create: `databricks/notebooks/job_daily_report.py` (06:30 cron, 신규)
  - Step 1: 어제 보관된 reports 수집 (`status='kept' AND DATE(status_changed_at)=CURRENT_DATE-1`)
  - Step 2: 어제 daily_reports row 가져옴
  - Step 3: Foundation Model API call (Haiku-4-5 또는 Opus-4-7) → 종합 + ratio_suggestion JSONB 생성
  - Step 4: daily_reports에 INSERT
  - Step 5: Slack push (옵션 — Phase 8에서)
- Create: `databricks/jobs/daily_report.yml` (Asset Bundle)
- Create: `backend/app/services/daily_report.py`
  - `generate_daily_report(target_date)` — notebook과 동일 로직 (테스트 가능)
- Modify: `backend/app/api/reports.py`
  - `GET /api/daily-reports/today` — 오늘 daily report
  - `GET /api/daily-reports/recent?limit=7`
- Create: `backend/tests/test_daily_report.py`

### 3.2 LLM Prompt 구조 (daily_report)

```
System: Korean refinery procurement strategist. Aggregate yesterday's kept reports + previous daily report into today's portfolio direction.

Input:
  Yesterday's kept reports: [N]
  Previous daily report summary: <text>
  Current pattern_score: <value>
  Current portfolio (assumed): Term 60% / Spot 40%

Output (JSON):
  {
    "kept_summary": "어제 보관 시그널 정리 (3줄)",
    "prev_daily_summary": "전날 daily 요약 (2줄)",
    "market_context": "현재 시장 상황 (3줄)",
    "ratio_suggestion": {
      "direction": "lean_hedge | neutral | lean_opportunity",
      "term_delta_pct": "+5 | 0 | -5",
      "spot_delta_pct": "-5 | 0 | +5",
      "qualitative": "한 줄 권고"
    },
    "reasoning": "근거 한 단락 (400자 이내)",
    "confidence": 75
  }
```

### 3.3 🛑 사용자 action 필요

- **Asset Bundle deploy**: `databricks --profile crude-compass bundle deploy --target dev`
- **Daily job manual run** (cron 06:30 안 기다리고 즉시 테스트):
  ```
  databricks --profile crude-compass jobs run-now <job_id_for_daily_report>
  ```
- 사용자가 chat에서 "deploy + run 완료" 보고

### 3.4 🛑 CONFIRM GATE 4

`daily_reports` 테이블에 1 row INSERT 확인 (사용자가 psql 또는 Apps에서 확인). 정상이면 Phase 4.

---

## Phase 4 — Trigger emit (notebook, 2시간)

### 4.1 작업 (AI)

기존 notebook 수정 — trigger 발생 시 backend `/api/reports/generate` 호출 (또는 notebook이 직접 Lakebase INSERT + LLM call):

- Modify: `databricks/notebooks/job_gdelt.py`
  - 기존 importance≥70 emit (agent_activity)는 그대로
  - **추가**: importance≥80 단일 article 발견 시 → report 생성 trigger
- Modify: `databricks/notebooks/job_price.py`
  - 기존 ±2% spike emit (agent_activity) 유지
  - **추가**: Dubai 24h ±2% 시 report 생성 trigger
- Modify: `databricks/notebooks/job_curation.py`
  - 기존 score change emit 유지
  - **추가**: pattern_score 7일 MA 변화 ±10점 시 report 생성 trigger
- Create: `databricks/notebooks/_report_emit.py`
  - 헬퍼: notebook → backend `/api/reports/generate?trigger_type=X` POST
  - Best-effort, fail silent

### 4.2 🛑 사용자 action 필요

- Asset Bundle re-deploy
- Manual job trigger (gdelt / price / curation 각 1회) → 실제 trigger event 발생하면 report 생성 확인

### 4.3 🛑 CONFIRM GATE 5

`reports` 테이블에 trigger_type별 rows 최소 1개씩 확인. 정상이면 Phase 5.

---

## Phase 5 — Frontend foundation (3시간)

### 5.1 작업 (AI)

- Modify: `frontend/src/lib/api.ts`
  - `reports.inbox()` / `reports.detail(id)` / `reports.archive(status)` / `reports.keep(id)` / `reports.drop(id)` / `reports.investigate(id)`
  - `dailyReports.today()` / `dailyReports.recent(limit)`
- Modify: `frontend/src/lib/queries.ts`
  - `useReportsInbox` / `useReportDetail` / `useReportsArchive` / `useDailyReportToday`
  - mutation hooks: `useKeepReport` / `useDropReport` / `useInvestigateReport`
- Modify: `frontend/src/lib/types.ts`
  - `Report` / `DailyReport` / `ReportThread` 타입
- Modify: `frontend/src/lib/ws.ts`
  - `connectReportsWs` — WebSocket subscribe (재사용 missions pattern)
- Create: `frontend/src/hooks/useReportsStream.ts`

### 5.2 검증

```
cd frontend && pnpm tsc --noEmit
```

### 5.3 🛑 CONFIRM GATE 6

별도 사용자 action 없음. Phase 6으로.

---

## Phase 6 — Decision Room reports inbox UI (4시간)

### 6.1 작업 (AI)

기존 `ActionQueue` / `SelectedCaseDetail` 컴포넌트 제거하지 않고 Dashboard에서 import만 교체.

- Create: `frontend/src/components/ReportsInbox.tsx` — 검토 대기 목록 (최근 10개 pending)
  - 각 row: [trigger icon] [headline] [age] [thread depth 표시]
  - trigger별 색상/icon 다르게:
    - `gdelt_signal` → Newspaper (info-blue)
    - `price_spike` → DollarSign (ok-green)
    - `pattern_drift` → Activity (warn-amber)
- Create: `frontend/src/components/SelectedReportDetail.tsx`
  - headline + summary + reasoning + recommendation
  - thread (parent_id) 표시 — 자식 reports 시간순 (이메일 회신 풍)
  - "이전 보관/drop 유사" 라벨 (revisits_id 있을 때)
  - 액션: [보관] [추가 조사] [drop]
- Create: `frontend/src/components/ReportThread.tsx` — thread 내 자식 reports
- Create: `frontend/src/components/DailyReportHero.tsx`
  - 오늘 daily report 1건
  - 비중 suggestion + 신뢰도 + reasoning
  - read-only, action 없음
  - "참고용" 명시 라벨
- Modify: `frontend/src/pages/Dashboard.tsx`
  - 새 layout:
    ```
    [Header — Decision Room | OSP D-N]
    [DailyReportHero 상단 — 오늘의 비중 제안 (참고용)]
    [Grid 5/12: ReportsInbox | 7/12: SelectedReportDetail]
    [Signal Strength (Bidirectional3Zone — 유지)]
    [Market Memory — 유지]
    ```
  - 기존 ActionQueue / SelectedCaseDetail / MonitoringStrip / DeltaStrip import 제거 (Decision Room에서만)

### 6.2 검증 (시각)

```
cd frontend && pnpm tsc --noEmit && pnpm build
```
preview server에서 dashboard 시각 확인.

### 6.3 🛑 CONFIRM GATE 7

사용자가 preview에서 UI 시각 확인 후 OK. 안 OK면 폴리시 round.

---

## Phase 7 — Archive 페이지 (2시간)

### 7.1 작업 (AI)

- Create: `frontend/src/pages/ArchivePage.tsx`
  - 좌측 필터: kept / dropped / ai_dropped / all + 날짜 range
  - 메인: 보고서 카드 list (kept 위, dropped 아래 muted)
  - 클릭 → detail + thread + 액션 (drop → kept 복구 / kept → drop)
- Modify: `frontend/src/App.tsx` — route `/archive` 등록
- Modify: `frontend/src/components/Sidebar.tsx` — Archive 메뉴 추가 (또는 Case File 안 탭으로)

### 7.2 🛑 CONFIRM GATE 8

사용자 시각 확인.

---

## Phase 8 — Slack integration (2-3시간)

### 8.1 작업 (AI)

- Modify: `backend/app/services/slack_notify.py` 또는 새 `slack_reports.py`
  - report 생성 시 매니저 DM (interactive blocks: [보관] [추가조사] [drop])
  - daily report 생성 시 채널 또는 DM push (read-only, no buttons)
- Modify: `backend/app/api/slack.py` — interactive callback 처리:
  - button "보관" → POST `/api/reports/{id}/keep`
  - button "추가조사" → POST `/api/reports/{id}/investigate`
  - button "drop" → POST `/api/reports/{id}/drop`
  - 결과: Slack 메시지 edit + WebSocket broadcast (Dashboard 실시간 sync)

### 8.2 🛑 사용자 action 필요

- Slack workspace 설정 확인 (이미 done인지 확인)
- 기존 Slack DM/Bot 작동 여부 (missions Slack과 동일 패턴이므로 무리 없음 예상)

### 8.3 🛑 CONFIRM GATE 9

사용자가 Slack에서 report DM 받고 [보관] 클릭 → Dashboard 실시간 sync 확인.

---

## Phase 9 — AI 자율 행동 (2-3시간)

### 9.1 작업 (AI)

- Modify: `backend/app/services/report_ai_decision.py`
  - 매 trigger 발생 시:
    1. pending reports 10개 로드
    2. 각각 새 snapshot과 LLM judge → stale / continuation / unrelated
    3. stale → ai_drop (status 변경 + ai_drop_reason 저장)
    4. continuation → parent_id 연결한 새 row INSERT (thread)
    5. 어느 것에도 매칭 안 되는 새 시그널 → archive 검색 후 새 report INSERT (revisits_id 가능)
- 이 로직을 Phase 2 report generator에 통합 또는 별도 service. **추천: 별도 service `report_ai_decision.judge_and_persist()`** — report generator는 단순 LLM call, decision은 별개 layer.

### 9.2 검증

테스트: pending 보고서가 있는 상태에서 새 trigger 발생 시 AI judge 호출되는지.

### 9.3 🛑 CONFIRM GATE 10

별도 사용자 action 없음. Phase 10.

---

## Phase 10 — Polish + cleanup + demo seed (3시간)

### 10.1 작업 (AI)

- **Demo seed**: 매뉴얼 trigger script 작성해서 5-10건 report + 1-2건 daily report 생성
  - `scripts/seed_demo_reports.py`
- **Remove deprecated UI**: missions 관련 Decision Room 컴포넌트는 다른 페이지(Case File)에 잔존 OK. Decision Room에서만 깨끗.
- **README + architecture.md**: reports 모델 반영
- **demo_script_5min.md**: 시연 flow 업데이트
- **Visual polish**: 시각 확인하면서 작은 카피·spacing 정리

### 10.2 🛑 사용자 action 필요

- demo 영상 녹화 (사용자 책임)
- 최종 deploy: `databricks bundle deploy --target prod` (있으면)

### 10.3 🛑 FINAL GATE

전체 flow demo 1회 — 사용자 확인 후 종료.

---

## 3. Phase 의존관계 + 우선순위

```
Phase 0 (사용자 검증)
  ↓
Phase 1 (DDL) ─── 사용자 deploy/migrate ───
  ↓
Phase 2 (Report generator backend)
  ↓
Phase 3 (Daily report cron) ─── 사용자 deploy ───
  ↓
Phase 4 (Trigger emit notebook) ─── 사용자 deploy ───
  ↓
Phase 5 (Frontend foundation)
  ↓
Phase 6 (Decision Room UI) ─── 사용자 시각 확인 ───
  ↓
Phase 7 (Archive) ─── 사용자 시각 확인 ───
  ↓
Phase 8 (Slack) ─── 사용자 Slack 테스트 ───
  ↓
Phase 9 (AI 자율) — 백엔드만
  ↓
Phase 10 (Polish + demo seed)
```

각 phase 이후 confirm gate에서 사용자 OK 받고 다음.

---

## 4. 시간 견적

| Phase | AI 시간 | 사용자 action 시간 |
|---|---|---|
| 0 | 5분 | 10분 (SDK 확인) |
| 1 | 2시간 | 15분 (DDL apply) |
| 2 | 3-4시간 | 10분 (manual trigger 테스트) |
| 3 | 3시간 | 20분 (bundle deploy + run-now) |
| 4 | 2시간 | 15분 (bundle deploy) |
| 5 | 3시간 | 0 |
| 6 | 4시간 | 10분 (시각 확인) |
| 7 | 2시간 | 5분 (시각 확인) |
| 8 | 2-3시간 | 15분 (Slack 테스트) |
| 9 | 2-3시간 | 0 |
| 10 | 3시간 | 30분 (demo data 검증) |
| **합계** | **26-32시간** | **2시간** |

D-1 + 밤샘이면 빠듯하지만 가능. Phase 8(Slack)이나 Phase 9(AI 자율)은 시간 부족 시 P1로 미룰 수 있음 (demo 핵심은 5-7).

---

## 5. 미해결 / Phase 진입 시 결정 항목

1. **Phase 1 DDL apply 방식** (A: backend boot 자동 / B: psql 수동) — Phase 1 시작 전 결정
2. **Phase 2 recommendation vocabulary 확정** — 위 6개 (HOLD/DEFER SPOT/ACCELERATE SPOT/REVIEW TERM/HEDGE/DIVERSIFY) 그대로 vs 줄임
3. **Phase 3 Daily report Foundation Model 선택** — Haiku-4-5 (빠름) vs Opus-4-7 (질 ↑, 비용 ↑) — 추천 Haiku
4. **Phase 6 DailyReportHero 위치** — Dashboard 상단 vs 별도 페이지 — 추천 상단
5. **Phase 7 Archive 위치** — sidebar 새 메뉴 vs Case File 안 탭 — 추천 sidebar 새 메뉴
6. **Phase 8 Daily report Slack 채널** — DM only vs 팀 채널 push — 추천 DM only (demo 단순)

---

## 6. Out of scope (이 plan에서 안 함)

- missions 테이블 DROP (그대로 보존, 데이터 안 건드림)
- agent_activity_events / Pulse 변경 (그대로 유지 — 다른 layer)
- Investigation 페이지 reports 통합 (현재 supervisor chat 그대로 유지)
- Case File / MissionsPage reports 통합 (현재 mission CaseThread 그대로 — Decision Room만 reports)
- 가격 5분 cron 빈도 변경 (그대로)

---

## 7. Compact-safe 시작 시 첫 발화 (사용자가 새 세션에서 plan 읽고)

이 plan을 읽은 새 세션이라면 다음 메시지로 시작:

```
이 plan 문서를 따라 Phase 0부터 진행해줘. 
각 phase confirm gate에서 멈춰서 내 OK 받고 다음으로.
```

AI는:
1. plan 파일 Read
2. Phase 0 항목 사용자에게 명령 list 보여주고 결과 chat 응답 기다림
3. Phase 1 시작 전 DDL apply 방식 (A/B) 결정 받음
4. 이후 phase별 순차 진행
