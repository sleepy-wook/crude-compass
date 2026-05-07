# K-Petroleum Decision Support Agent — Architecture v2

> Databricks APJ Hackathon 2026 / 한국어 트랙 / Track 1
> 작성: 이형욱
> 환경: Databricks Express account ($700 credit, Premium tier 전체 기능)
> 마감: 2026-05-22
> v2 변경 (2026-05-07~08): Vite+React 단일 프로세스 / WebSocket→Workflow / Genie fallback chain / WhatIf→Mission·Yesterday 인라인

---

## 1. 환경

### Databricks
- **Express account** (Free Edition 아님)
- Premium tier 전체 기능 (Lakebase Autoscaling, Apps, Agent Bricks Custom Agents GA, Genie Agent Mode)
- $700 credit
- Cloud: AWS or Azure (확인 필요)

### 검증된 외부 API
| Source | 인증 | 제공 데이터 | 비용 | 검증 상태 |
|---|---|---|---|---|
| aisstream.io | API key | 호르무즈 선박 위치 (WebSocket) — 공공 vessel data | 무료 | ✅ Databricks 호환 검증 (2026-05-03) |
| OilPriceAPI Developer | API key | WTI / Brent / Dubai 5분 갱신 | $19/월 (10K calls) | ✅ 검증됨 |
| GDACS | 불필요 | 글로벌 재해 events — UN/EU 공식 | 무료 | ✅ 검증됨 |
| ECOS 한국은행 | API key | KRW/USD 환율 — 한국은행 공공 | 무료 | ✅ 검증됨 |
| News RSS | 불필요 | Reuters / AP / 연합뉴스 등 | 무료 | ⏳ 미검증 |
| JWC zone | 불필요 | War risk PDF (1회 download) | 무료 | ⏳ 미검증 |

**Track 1 "open data" 충족**: aisstream(공공) + GDACS(UN/EU) + ECOS(한국은행) 3종 공공 source.

### 비용 합계 (D-15 + post-deploy 1개월)
- OilPriceAPI Developer: $19/월 × 2 = **$38**
- 외 모두 무료
- Databricks Express credit $700 안에서 운영

---

## 2. Databricks 내부 아키텍처

```
┌────────────────────────────────────────────────────────────────┐
│                  Databricks Workspace (Express)                │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ Tool 1: Databricks Apps                                  │ │
│  │  Vite + React 18 + TS + FastAPI 단일 프로세스           │ │
│  │  단일 컨테이너 단일 포트 ($DATABRICKS_APP_PORT)          │ │
│  │  - Discovery Feed                                        │ │
│  │  - Living Mission (Wow ⭐ + 인라인 Genie 시뮬)          │ │
│  │  - Yesterday Review (Genie + AI/BI Dashboard iframe)     │ │
│  └─────────┬──────────┬──────────┬──────────┬─────────────┘ │
│            │          │          │          │                  │
│            ▼          ▼          ▼          ▼                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐          │
│  │ Tool 2:      │ │ Tool 3:      │ │ Tool 4:      │          │
│  │ Genie Space  │ │ Lakebase     │ │ Agent Bricks │          │
│  │              │ │ Autoscaling  │ │ Custom Agents│          │
│  │ Conversation │ │ (Postgres)   │ │ (2026-02 GA) │          │
│  │ API + 한국어 │ │ OAuth token  │ │              │          │
│  │ synonyms     │ │              │ │ ResponsesAg- │          │
│  │              │ │ 4 tables:    │ │ ent + MLflow │          │
│  │ polling 1~5s │ │ - missions   │ │              │          │
│  │ +24h cache + │ │ - events     │ │ Plan A 4종 / │          │
│  │ pre-warmed   │ │ - rfq        │ │ Plan B 2종   │          │
│  │ +AI/BI fbck  │ │ - decisions  │ │              │          │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘          │
│         │                │                │                   │
│         └────────────────┴────────────────┘                   │
│                          │                                     │
│                          ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ Unity Catalog — Bronze / Silver / Gold Delta tables      │ │
│  │                                                            │ │
│  │  bronze.oil_prices      (OilPriceAPI 5분, $19/월)        │ │
│  │  bronze.ais_positions   (aisstream WS, Workflow task)    │ │
│  │  bronze.gdacs_events    (REST 1시간)                     │ │
│  │  bronze.exchange_rates  (ECOS 일별)                      │ │
│  │  bronze.news_articles   (RSS 5분)                        │ │
│  │  bronze.jwc_zones       (PDF parsed 1회)                 │ │
│  │                                                            │ │
│  │  silver.* (정제·통합·중복제거)                          │ │
│  │  gold.risk_indicators (4종 input 종합)                   │ │
│  └──────────────────────────────────────────────────────────┘ │
│                          ▲                                     │
│                          │                                     │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ Lakeflow Jobs / Workflows                                 │ │
│  │  • Job 1: Tier 1 Daily (06:30 cron)                       │ │
│  │    - 모든 source 종합 fetch                              │ │
│  │    - risk score 계산                                      │ │
│  │    - Discovery Feed 3-5건 생성                           │ │
│  │  • Job 2: Tier 2 Realtime (5분 cron)                      │ │
│  │    - OilPriceAPI 가격 fetch                              │ │
│  │    - 뉴스 RSS fetch                                      │ │
│  │    - rule-based filter → 이상 시 Agent 호출              │ │
│  │  • Workflow continuous: AIS WebSocket                     │ │
│  │    - Apps 외부 (Apps scale-to-zero 정책 회피)            │ │
│  │    - 호르무즈 BoundingBox + 익명 charter MMSI            │ │
│  │    - bronze.ais_positions streaming insert               │ │
│  └──────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
                          ▲
                          │ HTTP / WebSocket
                          │
┌────────────────────────────────────────────────────────────────┐
│                  External APIs                                 │
│  • aisstream WS / OilPriceAPI / GDACS / ECOS                  │
│  • RSS feeds / JWC PDF (manual)                                │
└────────────────────────────────────────────────────────────────┘
```

---

## 3. Frontend 아키텍처 (Vite + React + FastAPI 단일 프로세스)

**핵심 설계**: FastAPI가 메인 프로세스. Vite로 빌드된 정적 파일(`apps/web/dist/`)을 FastAPI가 StaticFiles로 serve + `/api/*` 라우트 처리. 단일 컨테이너 단일 포트 = Databricks Apps deploy 단순화.

```
[Databricks App: crude-compass]
│
├── apps/web/  (Vite + React 18 + TypeScript)
│   ├── src/
│   │   ├── App.tsx                       # react-router-dom shell + Sidebar
│   │   ├── main.tsx                      # ReactDOM root
│   │   ├── styles/
│   │   │   ├── globals.css               # @tailwind + 디자인 토큰 (:root vars)
│   │   │   └── animations.css            # fadeup/blink/stagger keyframes
│   │   ├── routes/
│   │   │   ├── DiscoveryPage.tsx         # /
│   │   │   ├── MissionPage.tsx           # /mission/:id (인라인 Genie)
│   │   │   └── YesterdayPage.tsx         # /yesterday (Genie + AI/BI iframe)
│   │   ├── components/
│   │   │   ├── layout/Sidebar.tsx
│   │   │   ├── icons.tsx                 # I.* 24개 (design jsx 1:1)
│   │   │   ├── ui/{Button,Pill,Card,Tabs}.tsx
│   │   │   ├── charts/                   # hand-rolled SVG (design jsx 1:1)
│   │   │   │   ├── Sparkline.tsx
│   │   │   │   ├── GaugeRing.tsx
│   │   │   │   ├── LineChart.tsx
│   │   │   │   ├── BarChart.tsx
│   │   │   │   ├── ProgressBar.tsx
│   │   │   │   └── HormuzMap.tsx
│   │   │   ├── discovery/                # RiskScoreSummary, DiscoveryCard, CardC1..C5
│   │   │   ├── mission/                  # TimelineGrid, DayDetail, FrameContractList,
│   │   │   │                             # ScenarioROI, FleetMap, GenieInline
│   │   │   └── yesterday/                # SelfCritiqueCard, GenieInline, AIBIEmbed
│   │   ├── lib/
│   │   │   ├── api.ts                    # fetch /api/* helpers
│   │   │   └── types.ts
│   │   └── vite.config.ts
│   ├── tailwind.config.ts
│   └── package.json
│
├── apps/api/  (FastAPI + uv)
│   ├── pyproject.toml (uv managed)
│   ├── main.py                           # FastAPI app + StaticFiles mount
│   ├── routers/
│   │   ├── feed.py        # GET /api/feed         → Lakebase JOIN
│   │   ├── mission.py     # GET /api/mission/:id  → Lakebase
│   │   ├── genie.py       # POST /api/genie       → Genie polling + cache
│   │   ├── decision.py    # POST /api/decision    → Lakebase write
│   │   ├── risk.py        # GET /api/risk         → Gold table
│   │   └── dashboard.py   # GET /api/dashboard/token → AI/BI embed token
│   ├── services/
│   │   ├── lakebase.py    # OAuth token refresh + psycopg connection pool
│   │   ├── genie.py       # Conversation API client + cache
│   │   ├── agents.py      # Custom Agent invocation
│   │   └── embed_token.py # SP OAuth token for AI/BI iframe (1h refresh)
│   └── models/            # pydantic
│
└── app.yaml
    command: ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "$DATABRICKS_APP_PORT"]
    env:
      - name: PGHOST       # Lakebase 자동 주입
      - name: PGPORT       # Lakebase 자동 주입
      - name: PGDATABASE   # Lakebase 자동 주입
      - name: PGUSER       # Lakebase 자동 주입 (SP client ID)
      - name: PGSSLMODE    # Lakebase 자동 주입
      - name: OILPRICEAPI_KEY     # secret
      - name: GENIE_SPACE_ID
      - name: AIBI_DASHBOARD_ID
```

### Data flow 예시 (Discovery Feed)

```
1. 매니저가 https://crude-compass.cloud.databricks.com 접속
2. Apps OAuth 로그인 (회사 SSO)
3. FastAPI가 dist/index.html serve (정적)
4. React가 mount → fetch GET /api/feed
5. FastAPI feed.py → Lakebase OAuth 토큰 발급 → psycopg query
6. SELECT * FROM missions JOIN events WHERE date = today  → 3-5건
7. JSON 반환 → DiscoveryCard render
8. 매니저 "수락" 버튼 → POST /api/decision
9. FastAPI decision.py → INSERT INTO decisions
10. (Optional) Custom Agent trigger via Mosaic AI endpoint
```

### Data flow 예시 (Mission 인라인 Genie 시뮬)

```
1. 매니저가 /mission/:id 페이지에서 상단 Genie bar에 입력
   "Brent $140 / Dubai $135 가면?"
2. POST /api/genie body={query, mission_id}
3. FastAPI genie.py 4중 fallback chain:
   (a) cache hit?  → 즉시 반환
   (b) pre-warmed Gold table에 매칭? → 즉시 반환
   (c) Genie Conversation API start → polling 1s 간격
       - 5s 안 응답: progress UI "조회 중…" 표시 (design 그대로)
       - 8s 안 응답: 정적 fallback 결과 + AI/BI iframe 노출
4. 결과 chart 메타데이터 → React가 LineChart + SensitivityTable render
```

### Data flow 예시 (Yesterday Review + AI/BI Dashboard)

```
1. 매니저가 /yesterday 페이지 진입
2. React가 두 fetch 병렬:
   (a) GET /api/yesterday/summary       → Self-critique 텍스트 + 4-stat
   (b) GET /api/dashboard/token         → AI/BI embed token
3. AIBIEmbed 컴포넌트가 iframe src에 token 부착
   (Service Principal OAuth, 1h 만료, FastAPI에서 refresh 관리)
4. 상단에 작은 Genie bar — "어제 결정 다시 묻기"
   매니저 입력 → 동일 /api/genie 라우트 재사용
```

---

## 4. 4-tool 활용 깊이

### Tool 1: Databricks Apps
- Vite + React + FastAPI 단일 프로세스 단일 컨테이너
- 3 page (Discovery / Mission / Yesterday Review)
- Lakebase 자동 env 주입 + OAuth 토큰 wrapper
- AI/BI Dashboard iframe embed (Yesterday)
- desktop-first 1280px primary

### Tool 2: Genie (Conversation API)
- Genie Space 구성 (Bronze/Silver/Gold tables 등록)
- 한국어 synonyms 매핑: Term/Spot/lifting/OSP/리프팅/유전스/Aramco Formula 등 ~30개
- **Mission 인라인 Genie bar + Yesterday Review Genie bar 2 surface**
- 4중 fallback chain: cache → pre-warmed Gold → polling Conversation API → 정적 + AI/BI iframe
- (Plan A) `databricks_langchain.genie` Custom Agent tool로 supervisor 패턴 (Public Preview)
- (Plan B) Genie와 Custom Agents 별개 surface (안정성 ↑)

### Tool 3: Lakebase Autoscaling
- Postgres OLTP, Apps env 자동 주입
- **OAuth 토큰 refresh wrapper** (PGPASSWORD 미주입 → SDK로 발급)
- 4 tables (missions / mission_events / rfq_negotiations / decisions)
- 4주 mission state 영속 (회의·휴가에도 유지)

### Tool 4: Agent Bricks Custom Agents (2026-02-18 GA)
- Mosaic AI Agent Framework + ResponsesAgent 패턴
- MLflow signature 자동 추론 + tracking
- **Plan A 4종**:
  1. **Monitoring Agent** — 5종 데이터 + 뉴스 → risk score
  2. **Simulation Agent** — Genie 연동, 시나리오 ROI
  3. **RFQ Chaining Agent** — 4사 Frame Contract 자동 협상 시뮬
  4. **Self-Critique Agent** — 매주 모델 보정
- **Plan B 2종** (5/14 23:59 cut decision): Monitoring + Simulation만, RFQ는 정적, Self-Critique는 Yesterday 텍스트만

### Tool 5 (보조): AI/BI Dashboard
- 30일 시계열: Risk Score / Hormuz 통과량 / WTI·Brent·Dubai 가격 / 매니저 결정 outcome
- **iframe embed** (Yesterday Review 페이지 하단)
- Service Principal OAuth embed token (1h 만료, FastAPI `/api/dashboard/token` refresh)
- Storytelling 평가축 직접 매칭 (20%)

---

## 5. Lakebase 스키마

```sql
-- Lakebase Postgres (Autoscaling)

CREATE TABLE missions (
  mission_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  goal TEXT NOT NULL,
  start_date DATE,
  current_day INT,
  target_day INT DEFAULT 28,
  status TEXT DEFAULT 'active',  -- active/completed/paused
  manager_id TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE mission_events (
  event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  mission_id UUID REFERENCES missions(mission_id),
  day INT NOT NULL,
  actor TEXT NOT NULL,           -- 'ai' or 'human'
  action TEXT NOT NULL,
  payload JSONB,
  outcome JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE rfq_negotiations (
  rfq_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  mission_id UUID REFERENCES missions(mission_id),
  counterparty TEXT NOT NULL,    -- Aramco/ADNOC/BP/TotalEnergies
  request_payload JSONB,
  response_payload JSONB,
  status TEXT,                   -- sent/received/accepted/rejected
  price_offered NUMERIC,
  volume NUMERIC,
  sent_at TIMESTAMPTZ,
  responded_at TIMESTAMPTZ
);

CREATE TABLE decisions (
  decision_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL,
  decision_type TEXT NOT NULL,   -- discovery_swipe/mission_confirm/whatif
  context JSONB,                 -- AI가 제공한 정보
  decided_at TIMESTAMPTZ DEFAULT NOW(),
  outcome_at TIMESTAMPTZ,        -- 7일 후 자동 측정
  outcome JSONB
);

CREATE INDEX idx_missions_status ON missions(status);
CREATE INDEX idx_events_mission ON mission_events(mission_id);
CREATE INDEX idx_rfq_mission ON rfq_negotiations(mission_id);
CREATE INDEX idx_decisions_user ON decisions(user_id);
```

---

## 6. Bronze Delta 스키마

```sql
-- Unity Catalog: bronze schema

CREATE TABLE bronze.oil_prices (
  fetched_at TIMESTAMP,
  source TEXT,                   -- 'oilpriceapi'
  product TEXT,                  -- 'WTI_USD', 'BRENT_CRUDE_USD', 'DUBAI_CRUDE_USD'
  price DOUBLE,
  raw JSONB
) USING DELTA;

CREATE TABLE bronze.ais_positions (
  received_at TIMESTAMP,
  mmsi BIGINT,
  ship_name TEXT,
  latitude DOUBLE,
  longitude DOUBLE,
  sog DOUBLE,
  message_type TEXT,
  raw JSONB
) USING DELTA
PARTITIONED BY (date(received_at));

CREATE TABLE bronze.gdacs_events (
  fetched_at TIMESTAMP,
  event_id TEXT,
  event_type TEXT,               -- TC/EQ/FL/VO/WF/DR
  name TEXT,
  country TEXT,
  date DATE,
  severity TEXT,
  raw JSONB
) USING DELTA;

CREATE TABLE bronze.exchange_rates (
  fetched_at TIMESTAMP,
  date DATE,
  pair TEXT,                     -- 'KRW/USD'
  rate DOUBLE,
  raw JSONB
) USING DELTA;

CREATE TABLE bronze.news_articles (
  fetched_at TIMESTAMP,
  source TEXT,                   -- reuters/ap/yna/ft/bbc
  url TEXT,
  title TEXT,
  description TEXT,
  published_at TIMESTAMP,
  raw JSONB
) USING DELTA
PARTITIONED BY (date(fetched_at));

CREATE TABLE bronze.jwc_zones (
  fetched_at TIMESTAMP,
  zone_name TEXT,
  zone_type TEXT,
  geometry STRING,               -- WKT 형식
  effective_date DATE,
  raw STRING
) USING DELTA;
```

---

## 7. Lakeflow Jobs 정의

### Job 1: Tier 1 Daily (06:30 KST cron)
```yaml
name: tier1_daily_curation
schedule: "30 6 * * *"  # 06:30 KST daily
tasks:
  - fetch_oil_prices       # OilPriceAPI WTI/Brent/Dubai
  - fetch_gdacs_events
  - fetch_exchange_rates   # ECOS
  - fetch_news_rss         # Reuters/AP/연합뉴스
  - calculate_risk_score   # 4종 input 종합
  - generate_discovery_feed # 3-5건 큐레이션 → Lakebase
  - prewarm_genie_scenarios # Genie fallback용 자주 묻는 시나리오 nightly 배치
  - notify_managers
```

### Job 2: Tier 2 Realtime (5분 cron)
```yaml
name: tier2_realtime
schedule: "*/5 * * * *"  # 5 minutes
tasks:
  - fetch_oil_prices_5min  # OilPriceAPI 가격 변동 체크
  - fetch_news_rss_5min
  - rule_based_filter      # 2% 이상 변동? 키워드 매칭?
  - if anomaly_detected:
      - trigger_agent_analysis  # Agent Bricks Monitoring
      - urgent_alert            # Lakebase events priority='urgent'
```

### Workflow (continuous task) — AIS WebSocket
**Apps 외부**에 분리. Apps는 scale-to-zero 정책상 24/7 WS 미보장 (2026-05 검증).
```python
# Databricks Workflow continuous task (cluster 24/7)
import websockets, json, asyncio

async def run():
    url = "wss://stream.aisstream.io/v0/stream"
    async with websockets.connect(url) as ws:
        await ws.send(json.dumps({
            "APIKey": API_KEY,
            "BoundingBoxes": [[[24.0, 54.0], [27.5, 58.0]]],  # Strait of Hormuz
            "FiltersShipMMSI": [...],  # 익명 charter VLCC MMSI
        }))
        while True:
            msg = json.loads(await ws.recv())
            # bronze.ais_positions에 streaming append (Spark)
            spark_session.append_to_delta("bronze.ais_positions", msg)

asyncio.run(run())
```

---

## 8. 작업 우선순위 (D-15)

### Phase 0 (5/8, 1d)
- [ ] docs 동기화 ✅ (5/7 완료)
- [ ] apps/web Vite + React 18 + TS + Tailwind 부트스트랩 + 디자인 토큰
- [ ] icons.tsx + charts.tsx + ui primitives 포팅
- [ ] apps/api FastAPI + Lakebase OAuth wrapper + /api/health
- [ ] Apps deploy PoC (단일 컨테이너 PoC) ⭐ critical

### Phase 1 Foundation (5/9~5/11, 3d)
- [ ] Bronze Delta 6종 (oil_prices·ais_positions·gdacs·exchange·news·jwc)
- [ ] Unity Catalog · Silver · Gold tables
- [ ] Lakebase Postgres 4 tables (missions·events·rfq·decisions)
- [ ] Lakeflow Job 1 (Tier 1 Daily) + Job 2 (Tier 2 Realtime)
- [ ] AIS WebSocket Workflow continuous task

### Phase 2 Agents (5/12~5/14, 3d)
- [ ] Genie Space 설정 + 한국어 synonyms ~30개
- [ ] Custom Agents Plan A 4종 (Monitoring/Simulation/RFQ/Self-Critique)
- [ ] **5/14 23:59 trigger**: 미완 시 Plan B 2종 cut
- [ ] Genie pre-warmed scenarios 3종 nightly 배치 작성

### Phase 3 Frontend (5/15~5/19, 5d)
- [ ] Discovery / Mission(인라인 Genie) / Yesterday Review(Genie + AI/BI) 3 page
- [ ] FastAPI 라우팅 + Lakebase query + Genie 4중 fallback chain
- [ ] AI/BI Dashboard embed token endpoint

### Phase 4 Deploy (5/20~5/21, 2d)
- [ ] Apps deploy + AI/BI Dashboard 작성 + iframe embed
- [ ] end-to-end 통합 테스트
- [ ] **5/19 23:59 trigger**: Apps deploy 미완 시 Streamlit fallback 24h 안에 전환

### Phase 5 Demo (5/22, 1d)
- [ ] 5분 영상 + README + 제출

---

## 9. Risk (v2 — 2026-05-07 검증 후)

### 기술 risk
- ✅ **Vite + React + FastAPI 단일 프로세스** = Apps deploy 단순 (Day-1 PoC 검증 예정)
- ⚠️ Lakebase OAuth 토큰 refresh wrapper 작성 (PGPASSWORD 미주입, SDK 토큰 발급 + 만료 갱신)
- ⚠️ Agent Bricks Custom Agents 2026-02-18 GA — 신규 기능, supervisor 패턴 검증 사례 부족
- ⚠️ Genie Conversation API 5초 SLA 부재 → 4중 fallback chain 필수
- ⚠️ `databricks_langchain.genie` multi-agent **Public Preview** (Plan A) / 별도 surface (Plan B)
- ⚠️ AIS WebSocket = Workflow continuous task로 분리 (Apps 외부, 검증 완료)
- ⚠️ AI/BI Dashboard iframe embed: Service Principal OAuth token 1h refresh 코드 필요

### 도메인 risk
- ⚠️ 김지훈 가상 (LG화학 SCM 인터뷰 진행 중)
- ✅ 가격·비중 데이터는 대한석유협회 공식 ground truth + 父 LG화학 NCC 출신 ground truth
- ✅ GS Caltex 데이터 = AIS source only, app UI 익명 처리 ("VLCC #001~005")

### 일정 risk
- ⚠️ 15일 마감 — Frontend 5일, 버퍼 0
- ⚠️ Plan B trigger 2회 명문화 (5/14 Agents cut, 5/19 Streamlit fallback)
- ⚠️ 형욱 본업 + APEX + ApexF1 + 이거 동시 = burnout risk

---

## 10. Plan B (Trigger 명문화)

### Trigger 1: 5/14 23:59 (Phase 2 종료)
Custom Agents 4종 중 2종 미완 → **Agents 2종으로 cut**:
- 유지: Monitoring + Simulation
- Cut: RFQ Chaining → 정적 4사 견적 표 (이미 design에 있음)
- Cut: Self-Critique → Yesterday Review 정적 텍스트만

### Trigger 2: 5/19 23:59 (Phase 3 종료)
Apps deploy 미완 → **24h 안에 Streamlit fallback 전환**:
- Vite+React → Streamlit st.columns + st.markdown으로 단순 변환
- 디자인 충실도 ↓ (60%로 하락 수용)
- 5분 영상은 Streamlit으로 녹화

### Trigger 3: 데모 직전 5/21 (final dress)
Genie API 응답 불안정 → **What-If 정적 fallback chain 활성**:
- pre-warmed Lakebase 결과 3종으로 데모 영상 녹화
- "Genie 응답 5s" narrative 유지하되 cache 결과 사용

### 절대 유지 (Plan B에도)
- Discovery Feed 3장 (Wow 1)
- 4-tool 활용 명확 (Apps·Genie·Lakebase·Agent Bricks 모두 시연)
- 5종 데이터 ingestion
- AI/BI Dashboard iframe embed (Storytelling)
- 5분 데모 영상

---

## 11. 검증된 외부 패턴 (2026-05-07 docs.databricks.com)

### 11.1 Lakebase OAuth 연결 패턴
Apps 환경에서 자동 주입 env: `PGHOST/PGPORT/PGDATABASE/PGUSER/PGSSLMODE/PGAPPNAME`. **`PGPASSWORD` 미주입** — Databricks SDK로 OAuth 토큰 발급 후 password 자리에 사용.

```python
# apps/api/services/lakebase.py
from databricks.sdk import WorkspaceClient
import psycopg
from datetime import datetime, timedelta

class LakebaseClient:
    _token: str | None = None
    _expires_at: datetime | None = None

    def _get_token(self) -> str:
        # 토큰 만료 5분 전 갱신
        if self._token and self._expires_at and datetime.utcnow() < self._expires_at - timedelta(minutes=5):
            return self._token
        w = WorkspaceClient()
        creds = w.database.generate_database_credential(
            instance_names=[os.environ["DATABRICKS_LAKEBASE_INSTANCE"]],
        )
        self._token = creds.token
        self._expires_at = datetime.utcnow() + timedelta(seconds=3600)
        return self._token

    def conn(self) -> psycopg.Connection:
        return psycopg.connect(
            host=os.environ["PGHOST"],
            port=os.environ["PGPORT"],
            dbname=os.environ["PGDATABASE"],
            user=os.environ["PGUSER"],
            password=self._get_token(),
            sslmode=os.environ.get("PGSSLMODE", "require"),
        )
```

### 11.2 Genie Conversation API 4중 fallback chain
**중요**: Conversation API는 5초 SLA 없음. polling 1~5s, 최대 10분.

```python
# apps/api/services/genie.py
from databricks.sdk import WorkspaceClient
import asyncio, hashlib, json

CACHE_TTL = 24 * 3600  # 24h
PREWARMED_KEY_PREFIX = "prewarmed:"

async def whatif(query: str, mission_id: str) -> dict:
    # (1) cache hit
    key = hashlib.sha256(f"{mission_id}:{query}".encode()).hexdigest()
    if cached := await redis.get(key):
        return json.loads(cached)

    # (2) pre-warmed Gold table에 매칭 (nightly 배치로 채워둠)
    if prewarmed := lakebase.fetchone(
        "SELECT result FROM gold.prewarmed_scenarios WHERE query_pattern = %s", (query,)
    ):
        return prewarmed

    # (3) Conversation API polling (5s 안 응답 = 정상, UI는 progress 표시)
    w = WorkspaceClient()
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(
                w.genie.start_conversation_and_wait,
                space_id=os.environ["GENIE_SPACE_ID"],
                content=query,
            ),
            timeout=8.0,
        )
        await redis.setex(key, CACHE_TTL, json.dumps(result))
        return result
    except asyncio.TimeoutError:
        # (4) 정적 fallback + AI/BI iframe 노출 권고
        return {"status": "timeout", "fallback": True, "ai_bi_url": ai_bi_dashboard_url(mission_id)}
```

### 11.3 AI/BI Dashboard iframe embed 패턴
Service Principal OAuth embed token 1h 만료 → FastAPI에서 refresh 관리.

```python
# apps/api/routers/dashboard.py
from fastapi import APIRouter
from databricks.sdk import WorkspaceClient

router = APIRouter()

@router.get("/api/dashboard/token")
async def get_embed_token():
    w = WorkspaceClient()  # SP credential
    token = w.dashboards.generate_embed_token(
        dashboard_id=os.environ["AIBI_DASHBOARD_ID"],
        ttl_seconds=3600,
    )
    return {"token": token, "expires_in": 3600}
```

```tsx
// apps/web/src/components/yesterday/AIBIEmbed.tsx
const { data } = useSWR("/api/dashboard/token", fetcher, { refreshInterval: 50 * 60 * 1000 });
return (
  <iframe
    src={`https://workspace.databricks.com/embed/dashboard/${id}?token=${data?.token}`}
    width="100%" height={600} style={{ border: "none" }}
  />
);
```

### 11.4 app.yaml 단일 프로세스
```yaml
# app.yaml
command: ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "$DATABRICKS_APP_PORT"]
env:
  - name: OILPRICEAPI_KEY
    valueFrom: oilpriceapi-secret
  - name: GENIE_SPACE_ID
    value: "01ee..."
  - name: AIBI_DASHBOARD_ID
    value: "01ef..."
  - name: DATABRICKS_LAKEBASE_INSTANCE
    value: "crude-compass-pg"
```

빌드 단계: `cd apps/web && npm install && npm run build` (`apps/web/dist` 생성) → FastAPI가 `StaticFiles(directory="apps/web/dist", html=True)`로 mount.
