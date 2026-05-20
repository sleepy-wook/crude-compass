# Time-Axis Redesign Spec — Crude Compass Agentic Layer 2

> 날짜: 2026-05-20 (D-2)
> 입력: 5/19 brainstorming 결과(`docs/agentic_redesign_review.md` 외 4 문서) + SDK 실측 inventory + Hackathon 공식 가이드
> 출력: time-axis 중심 5-layer 개편 spec. 다음 단계는 writing-plans skill로 implementation plan 작성.

---

## 0. 한 줄 결론

> **Decision Room은 더 이상 페이지가 아니라 시간이다. AI가 24/7 case를 진화시키는 운영실 라이브 화면이 되어야 한다.**

5/19 처방은 IA(공간) 개편 — Decision Room / Case File / Investigation / Market Watch. 이번 spec은 **time-axis 개편** — case가 시간 따라 진화하는 흔적, AI work의 분 단위 pulse, signal lifecycle 추적이 UI 주축이 된다.

---

## 1. 왜 5/19 처방만으로는 부족한가

5/19 commits 확인 결과 처방 대부분 land됨 (4-page IA, rename, 6-action, AgentActivityTimeline). 그런데 여전히 "AI가 일하는 것"이 안 보이는 이유:

1. **AgentActivityTimeline이 thin** — 한 case당 4-5줄 정적 list. case가 진화하는 시간감 X.
2. **`silver.signal_events_decayed` UI 노출 0%** — 시간 감쇠 weighted_signal UDF 결과가 silver layer까지 도달했는데 UI 미사용.
3. **`gold.signal_contribution_30d` view 미사용** — 시그널별 30일 누적 contribution을 view로 만들어놓고 UI에 없음.
4. **Case가 진화하지 않음** — "5분 전 vs 지금" 차이 안 보임. 모든 case가 시간 freeze된 snapshot.
5. **Live AI work pulse 없음** — gdelt 매 15분, price 매 5분, supervisor on-demand가 돌고 있는데 "방금 막 일어난 일" UI 흔적 없음.

즉 5/19는 **공간 frame**을 바꿨다. 이번 spec은 **시간 frame**을 추가한다.

---

## 2. Hackathon 공식 평가와의 정합 (verified)

[공식 가이드](https://buildintelligentapps-databricks.com/) WebFetch 결과:

| 평가축 (각 20%) | time-axis redesign으로 강화되는 부분 |
|---|---|
| Business Applicability | "AI가 24/7 일하는 실제 운영 흐름" — manager가 들어와서 reviewer 역할만 하면 되는 현실적 ops |
| Creativity & Innovation | "case가 thread로 진화" + "live AI pulse hero" — 기존 dashboard 패턴과 차별 |
| User Experience & Insights | thread + pulse가 동시에 동작하는 **stateful + streaming** UX |
| Technical Capability | Lakebase case_events + WebSocket broadcast + 미사용 silver/gold view 노출 + UC Function ai_query 시연 |
| Data Storytelling | 같은 case가 "5/12 시그널 감지 → 5/18 weight 0.4로 감쇠 → 5/19 case 영향 -1.3" 식의 시간 narrative |

Track 1 Social Impact 메시지도 강화: "open data 7년 + AI 24/7 + 시간축 stateful → APJ 에너지 수입국이 Bloomberg 없이도 빅5급 의사결정 luxury를 누리는 데모".

---

## 3. SDK 실측 inventory (verified 2026-05-20)

이 spec의 모든 claim은 아래 ground truth 위에 짜여있다.

### 3.1 인프라

| 항목 | 상태 | Evidence |
|---|---|---|
| Databricks Apps | ✅ ACTIVE | `crude-compass.aws.databricksapps.com` |
| Lakebase | ✅ live | `ep-lucky-star-d1rlmmrr` (Apps에 bound — `list-database-instances` API는 빈 list 반환 버그) |
| Genie Space | ✅ 1 space | "Crude Oil Market Analysis" (`space_id: 01f150e05229190aa9de93c97afde034`) |
| Agent Bricks — Knowledge Assistant | ✅ READY | `ka-6b456458-endpoint` |
| Agent Bricks — Multi-Agent Supervisor | ✅ READY | `mas-ba3fbcb5-endpoint` (mas-base-model-719a744c) |
| Foundation Models | ✅ 30+ | Haiku-4-5 / Sonnet-4-6 / Opus-4-7 / GPT-5-5 / Gemini-3-1 등 |

> **중요 정정**: 기존 docs/architecture.md는 Multi-Agent Supervisor를 "scope-out"이라고 적었으나 SDK 실측 결과 endpoint 실제 deployed + READY. spec은 이 ground truth 위에 작성.

### 3.2 Unity Catalog

- **bronze (6 tables)**: `news_articles`, `oil_prices`, `oil_prices_daily`, `fx_rates`, `eia_inventory`, `opec_momr_parsed`
- **silver (2 tables)**: `pattern_scores_daily`, `signal_events_decayed`
- **gold (1 table + 7 views)**: `daily_risk_score`, `eia_rolling`, `fx_with_delta`, `news_top_signals`, `oil_prices_wide`, `opec_demand_gap`, `pattern_score_latest`, `signal_contribution_30d`
- **functions (2 UDFs)**: `mission_plan_advice` (ai_query Haiku-4-5 SQL UDF), `weighted_signal` (time-decay)

### 3.3 Jobs (12, 모두 SUCCESS)

`gdelt-15min` / `price-pipeline-5min` / `oil-prices-daily` / `ecos-daily` / `eia-weekly` / `opec-momr-monthly` / `opec-momr-backfill` / `daily-curation-06:30` / `daily-risk-backfill` / `backtest-seed` / `backtest-compute` / `backtest-llm`

> README는 8 jobs 적혀있으나 실측 12. backfill/backtest helper 4개 미반영.

---

## 4. 5-Layer 개편 (time-axis 주축)

### Layer P0-A. Case Thread (단일 최대 임팩트)

**기존**: Case File 페이지는 case summary + evidence panels + approval history + pivot history가 평면 배치.

**개편**: Case File 본문을 **Slack-like thread**로 전면 교체.

#### Thread entry schema

```typescript
type CaseEvent = {
  case_id: string;
  ts: ISODateTime;
  actor: 'supervisor' | 'genie' | 'knowledge_assistant' | 'mission_plan_udf' |
         'curation_job' | 'gdelt_job' | 'price_job' | 'reactive_trigger' |
         'human_apps' | 'human_slack' | 'system';
  event_type: 'case_opened' | 'signal_arrived' | 'tool_called' |
              'draft_generated' | 'evidence_cited' | 'approved' | 'modified' |
              'revision_suggested' | 'monitoring_started' | 'case_closed' |
              'note_added';
  summary: string;          // 한 줄, 사용자 가시
  detail: object;           // expand 시 raw evidence (tool input/output, SQL, citation)
  related_artifact?: {
    type: 'news_article' | 'opec_field' | 'tool_call' | 'score_change';
    id: string;
  };
};
```

#### 예시 entry stream (case `cc-127` 5/12 ~ 5/20)

```
05/12 14:33  [gdelt_job]            "Hormuz tension" 뉴스 importance 78, direction=bullish
05/12 14:34  [supervisor]           case_opened — Hormuz cluster trigger
05/12 14:35  [genie]                Saudi supply check → 10,110 mb/d (OPEC MOMR 04/2026)
05/12 14:35  [knowledge_assistant]  OPEC p.23 cited — "supply tightening narrative"
05/12 14:36  [mission_plan_udf]     HEDGE draft — Term 60→75% (4주, confidence 78)
05/12 14:40  [human_slack]          승인 (Manager A)
05/13 06:30  [curation_job]         Pattern Score 71→73 (+2.1 from Hormuz contribution)
05/15 06:30  [curation_job]         Pattern Score 73→69 (signal decay -1.8)
05/17 09:12  [reactive_trigger]     Dubai spot +2.3% in 10min — case relevance check
05/18 06:30  [curation_job]         Pattern Score 69→64 — revision_suggested
05/19 09:45  [supervisor]           revision draft — Term 75→65% (de-escalation evidence)
05/19 09:50  [human_apps]           Keep watching (review at 05/22 EIA)
```

#### 핵심 차별점

- **하나의 case가 시간을 살아간다** — open snapshot이 아니라 진화하는 thread
- 매 entry는 click → expand → raw evidence (tool input/output, SQL query, OPEC PDF excerpt 등)
- WebSocket으로 새 entry 실시간 추가
- Slack thread와 1:1 mapping — Slack에서 댓글 달면 thread에 `[human_slack]` entry 추가

#### Data layer 신설

**Lakebase 새 테이블**: `case_events` (append-only)

```sql
CREATE TABLE case_events (
  event_id      UUID PRIMARY KEY,
  case_id       UUID NOT NULL REFERENCES missions(case_id),
  ts            TIMESTAMPTZ NOT NULL,
  actor         TEXT NOT NULL,
  event_type    TEXT NOT NULL,
  summary       TEXT NOT NULL,
  detail        JSONB,
  related_artifact JSONB
);
CREATE INDEX idx_case_events_case_id_ts ON case_events(case_id, ts DESC);
```

**Insertion paths**:
- Lakeflow jobs → INSERT via psycopg3 (gdelt/price/curation)
- Backend FastAPI → INSERT on human action (approve/modify/keep_watching)
- Reactive trigger (Job 2) → INSERT on spike
- Supervisor endpoint → INSERT on each tool call (backend wrapper logs)

> Lakehouse Sync (CDC) 자동 → Unity Catalog Delta로 append → 분석 가능.

---

### Layer P0-B. Live AI Pulse (Decision Room hero)

**기존**: Decision Room hero = open case summary (Bidirectional3Zone + draft + SimilarPastWidget).

**개편**: hero 자리에 **live AI activity stream** 들어가고, 기존 case summary는 좌측 column으로 demoted.

#### Pulse stream schema

`case_events` table에서 `case_id` 무관 전체 최근 N건 + `system` actor의 global events (job runs, supervisor invocations) 동시 stream.

#### 시각 표현

- **상단 hero strip**: Bloomberg Terminal 풍, 한 줄씩 위로 drift
- 각 entry: `[10:23] [GDELT-Agent] news importance 78 → Case #127 +2.1점`
- 색상: actor별 (supervisor 보라 / job 파랑 / human 녹색 / reactive 빨강)
- 빈 시간 (1분 이상 새 entry 없음) → "watching..." pulse animation
- click → 해당 case 또는 signal로 deep link

#### Global presence

- Sidebar 하단 mini pulse dot — 마지막 entry timestamp + 색상
- Topbar에 "AI activity in last 1h: 23 events" counter
- 모든 페이지에서 보임 → 사용자가 어디에 있든 "AI가 일하는 것" 인지

#### 데이터 source

```sql
SELECT * FROM case_events
WHERE ts > NOW() - INTERVAL '24 hours'
UNION ALL
SELECT * FROM job_run_summary  -- job runs (system events)
WHERE ts > NOW() - INTERVAL '24 hours'
ORDER BY ts DESC LIMIT 100;
```

WebSocket endpoint: `/ws/pulse` — case_events INSERT trigger broadcast.

---

### Layer P1-C. Signal Lifecycle (Investigation forensics mode)

**기존**: Investigation = supervisor-driven Q&A.

**추가**: 새 mode "trace a signal" — 한 시그널의 lifecycle을 4-stage로 추적.

#### 사용 흐름

1. Investigation page에 "Trace signal" tab
2. Signal 검색 / 선택 (예: "Hormuz tension news 2026-05-12")
3. 4-stage lifecycle 시각화:

| Stage | Source | UI |
|---|---|---|
| **1. Detected** | `bronze.news_articles` row | timestamp, source, importance score, raw text excerpt |
| **2. Scored** | LLM scoring trace | direction, horizon, confidence, entities |
| **3. Decay curve** | `silver.signal_events_decayed` | line chart — initial weight → decay over days |
| **4. Contribution** | `gold.signal_contribution_30d` view | 30일 누적 contribution bar + cases referenced |

#### 데이터 활용

- `silver.signal_events_decayed` — 첫 UI 노출. weighted_signal UDF의 시간 감쇠 결과 시각화
- `gold.signal_contribution_30d` — 첫 UI 노출. 30일 cumulative impact + reverse-lookup to cases

#### 강력한 narrative

"이 신문기사 한 줄이 어떻게 case를 만들고, 다른 신호와 합쳐지고, 시간 따라 weight가 줄어들고, 30일 후 잊혀지는가" — 시그널의 life-and-death.

---

### Layer P1-D. Daily Loop Clock

**위치**: Decision Room 우측 column 또는 Market Watch 상단.

**개념**: 24h 원형 dial. 매 정각마다 어떤 cron job이 돌고 무엇이 산출됐는지 표시.

#### 시각

- 시계 face 위에 dot/bar:
  - 매 15분 GDELT tick (96/day)
  - 매 5분 price tick (288/day)
  - 06:30 daily curation (1/day)
  - 매주 수 18:00 EIA (1/week)
  - 매월 12일 OPEC MOMR (1/month)
- 색상으로 success/fail/empty
- hover → 해당 run의 detail (row count, latency, output sample)

#### 누적 통계 (하단 strip)

```
오늘 Agent 활동 — gdelt 96회 / price 288회 / curation 1회 / supervisor 호출 23회 / mission 생성 2건
```

#### 데이터 source

`databricks jobs list-runs` SDK 호출 결과 + Lakebase `case_events` aggregation.

#### Social Impact narrative 강화

"AI는 잠들지 않는다. 매 5분, 매 15분, 매 새벽 6:30에 자동으로 — 사람 분석가 24명을 동시에 고용한 비용 없이." → open data + 자동화의 democratization 메시지.

---

### Layer P2-E. Agent Self-Narration

**위치**: Investigation supervisor 응답 + Case Thread `[supervisor]` entry expand.

**개념**: Supervisor가 자기 routing 결정 narrative로 explain.

#### 예시

```
Investigation: "왜 이 case가 OPP가 아니라 HEDGE인가?"

Supervisor self-narration:
1. 먼저 Genie를 호출했다 — pattern_score_latest 확인 → 71 (HEDGE zone)
2. KA를 호출하지 않았다 — pattern score 단독으로 충분히 명확
3. mission_plan_advice UDF를 호출했다 — 시그널 detail까지 reasoning에 통합 필요
4. 결과: HEDGE Term 60→75%, confidence 78

대안 path (만약 score가 30-70 사이였다면):
- KA를 먼저 호출해 OPEC 중기 narrative 확인했을 것
- Genie는 보조 evidence로 후속 호출
```

이는 supervisor를 "blackbox router"에서 "explainable orchestrator"로 격상.

---

## 5. 데이터 자산 활성화 매핑

| 미사용 / 약사용 자산 | 활성화 위치 | 노출 형식 |
|---|---|---|
| `silver.signal_events_decayed` | Layer C stage 3 | line chart |
| `gold.signal_contribution_30d` | Layer C stage 4 + Decision Room "Why this case" panel | bar chart + click → news_article |
| `bronze.opec_momr_parsed` raw fields | Layer A Case Thread `[knowledge_assistant]` expand | structured field key-value |
| `bronze.eia_inventory` weekly | Layer D weekly tick + Market Watch | "EIA 주간 surprise" card |
| Job run history (12 jobs) | Layer D Daily Loop | 시계 dial + 누적 통계 |
| `mas-ba3fbcb5` invocation logs | Layer A Case Thread `[supervisor]` entries | tool call trace |
| `mission_plan_advice` UC function | Genie certified query + Layer A entries | `SELECT mission_plan_advice('...')` 시연 |
| `gold.daily_risk_score` | (이미 노출 — Bidirectional3Zone) | unchanged |
| `gold.pattern_score_latest` view | (이미 노출 — hero score) | unchanged |
| `gold.oil_prices_wide` view | (이미 노출 — Market Watch) | unchanged |
| `gold.news_top_signals` view | Layer A entry → news drill-down | top signals deep link |
| `gold.fx_with_delta` view | Layer C stage 4 + Market Watch | FX context for case |
| `gold.opec_demand_gap` view | Layer A `[knowledge_assistant]` expand | demand gap context |
| `gold.eia_rolling` view | Layer D EIA tick expand | rolling avg context |

---

## 6. 4 필수 도구 강화 매핑

| 도구 | 현재 사용 | time-axis 개편 후 강화점 |
|---|---|---|
| **Databricks Apps** | manager UI shell | "live 운영실" — pulse strip + thread → 단순 호스팅 아닌 stateful work surface |
| **Lakebase** | mission state | + `case_events` append-only thread → operational memory 정체성 강화. CDC로 Unity Catalog 자동 sync |
| **Genie** | NL2SQL + 4-tier fallback | + `mission_plan_advice` UC function을 Genie certified query에 등록 → "AI를 SQL로 호출" 임팩트. Layer A `[genie]` entry로 invocation 시각화 |
| **Agent Bricks** | Supervisor + KA 2 endpoint | Layer A `[supervisor]` / `[knowledge_assistant]` entries로 매 invocation이 thread에 기록 → orchestration 완전 visible. Layer E self-narration → "blackbox" 오해 차단 |

---

## 7. 비-목표 (이번 spec에서 안 함)

- 새 데이터 source 추가 (Bloomberg, Argus 등 X)
- 새 LLM 모델 변경 (Haiku-4-5 유지)
- backend FastAPI 대규모 refactor (case_events INSERT helper만 추가)
- Slack Bot 큰 변경 (entry INSERT trigger만 추가)
- AI/BI Dashboard 변경 (기존 iframe 그대로)
- 모바일 responsive (desktop-first 유지)

---

## 8. 구현 우선순위 (writing-plans skill 입력)

다음 skill로 작업 분해할 때 따를 priority:

### P0 (필수)
1. **Lakebase `case_events` 테이블 신설** + DDL + repo wrapper
2. **case_events INSERT integration** — gdelt/price/curation jobs / backend mutation endpoints / reactive trigger / Supervisor wrapper
3. **WebSocket `/ws/pulse` broadcast** — case_events INSERT trigger
4. **Layer A — Case Thread UI** — Case File 본문 교체, entry component, expand detail
5. **Layer B — Live AI Pulse UI** — Decision Room hero strip + sidebar mini dot

### P1 (가능하면)
6. **Layer C — Signal Lifecycle Investigation mode** — 4-stage view, signal_events_decayed + signal_contribution_30d 노출
7. **Layer D — Daily Loop Clock** — 24h dial component + job run history fetch

### P2 (시간 남으면)
8. **Layer E — Agent Self-Narration** — supervisor wrapper에 reasoning_path field 추가, UI render

### 비-필수 정리
9. 기존 AgentActivityTimeline 컴포넌트 → Case Thread로 흡수 (단순 redirect)
10. ReactiveAlertToast → Live Pulse로 흡수
11. README + docs/architecture.md update (Multi-Agent Supervisor scope-out 표기 제거, 12 jobs 정정, case_events 추가)

---

## 9. Demo 시나리오 영향

5분 비디오 script에 time-axis 흐름 반영:

```
[0:00-0:30] Problem — APJ 에너지 수입국, Bloomberg 없는 SMB 정유사
[0:30-1:00] Apps 진입 → Live AI Pulse hero 30초 동안 stream 흐름 보여줌 (AI never sleeps)
[1:00-2:00] Case #127 클릭 → Thread 풀스크롤
            [gdelt → supervisor → genie → KA → mission_plan_udf → human approve → curation revise]
            매 entry expand하면서 raw evidence 드러냄
[2:00-3:00] Investigation "trace a signal" → Hormuz 뉴스의 lifecycle 4-stage
[3:00-4:00] Slack 시연 — manager가 Slack에서 댓글 달면 thread에 [human_slack] entry 실시간 추가
[4:00-4:30] Daily Loop dial → 오늘 96 gdelt + 288 price + 23 supervisor 호출 누적
[4:30-5:00] Track 1 Social Impact wrap — open data + 24/7 AI = APJ democratization
```

---

## 10. 자체 self-review (spec 작성 후)

- [x] Placeholder 없음 (TBD, TODO 등)
- [x] 내부 일관성 — 5 layer가 각각 다른 데이터 자산을 활용, overlap 없음
- [x] Scope — 단일 implementation plan으로 가능 (5 layer 모두 frontend + thin backend addition + 1 table)
- [x] Ambiguity — 각 layer의 schema + 데이터 source + 시각 표현 명시
- [x] SDK ground truth와 정합 (Multi-Agent Supervisor 실제 deployed 반영)
- [x] Hackathon 5축 평가와 정합 (§2)
- [x] 미해결 (`docs/agentic_redesign_review.md` 5/19 진단의 5개 한계) 직접 addressing (§1)

---

## 11. 다음 단계

이 spec 승인 후:

1. **writing-plans skill 호출** — 5 layer × P0/P1/P2 우선순위대로 implementation plan 작성
2. plan 승인 후 → **executing-plans skill 또는 직접 코드** — review checkpoint마다 user 동기화
3. 작업 완료 후 → README + architecture.md update (SDK 실측 ground truth 반영)

---

끝.
