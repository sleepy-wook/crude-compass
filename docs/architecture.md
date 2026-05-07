# K-Petroleum Decision Support Agent — Architecture v1

> Databricks APJ Hackathon 2026 / 한국어 트랙 / Track 1
> 작성: 이형욱
> 환경: Databricks Express account ($700 credit, Premium tier 전체 기능)
> 마감: 2026-05-22 (D-16)

---

## 1. 환경

### Databricks
- **Express account** (Free Edition 아님)
- Premium tier 전체 기능 (Lakebase Autoscaling, Apps, Agent Bricks Custom Agents GA, Genie Agent Mode)
- $700 credit
- Cloud: AWS or Azure (확인 필요)

### 검증된 외부 API (모두 무료)
| Source | 인증 | 제공 데이터 | 검증 상태 |
|---|---|---|---|
| aisstream.io | API key | 호르무즈 선박 위치 (WebSocket) | ✅ Databricks 호환 검증 (2026-05-03) |
| OilPriceAPI | API key | WTI / Brent / Dubai (REST 5분 갱신) | ✅ 검증됨 |
| GDACS | 불필요 | 글로벌 재해 events (REST) | ✅ 검증됨 |
| ECOS 한국은행 | API key | KRW/USD 환율 종가 (REST) | ✅ 검증됨 |
| News RSS | 불필요 | Reuters / AP / 연합뉴스 등 | ⏳ 미검증 |
| JWC zone | 불필요 | War risk PDF (1회 download) | ⏳ 미검증 |

---

## 2. Databricks 내부 아키텍처

```
┌────────────────────────────────────────────────────────────────┐
│                  Databricks Workspace (Express)                │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ Tool 1: Databricks Apps                                  │ │
│  │  Next.js 15 (App Router) + FastAPI hybrid               │ │
│  │  - Discovery Feed (mobile-first)                         │ │
│  │  - Living Mission Dashboard (Wow ⭐)                     │ │
│  │  - What-If + Yesterday Review                            │ │
│  └─────────┬──────────┬──────────┬──────────┬─────────────┘ │
│            │          │          │          │                  │
│            ▼          ▼          ▼          ▼                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐          │
│  │ Tool 2:      │ │ Tool 3:      │ │ Tool 4:      │          │
│  │ Genie Space  │ │ Lakebase     │ │ Agent Bricks │          │
│  │              │ │ Autoscaling  │ │ Custom Agents│          │
│  │ • NL → SQL   │ │ (Postgres)   │ │ (GA)         │          │
│  │ • What-If    │ │              │ │              │          │
│  │ • Agent Mode │ │ 4 tables:    │ │ 4 agents:    │          │
│  │              │ │ - missions   │ │ - Monitoring │          │
│  │              │ │ - events     │ │ - Simulation │          │
│  │              │ │ - rfq        │ │ - RFQ Chain  │          │
│  │              │ │ - decisions  │ │ - Self-Crit  │          │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘          │
│         │                │                │                   │
│         └────────────────┴────────────────┘                   │
│                          │                                     │
│                          ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ Unity Catalog — Bronze / Silver / Gold Delta tables      │ │
│  │                                                            │ │
│  │  bronze.oil_prices       (OilPriceAPI WTI/Brent/Dubai)   │ │
│  │  bronze.ais_positions    (aisstream WebSocket)           │ │
│  │  bronze.gdacs_events     (REST 1시간)                    │ │
│  │  bronze.exchange_rates   (ECOS 일별)                     │ │
│  │  bronze.news_articles    (RSS 5분)                       │ │
│  │  bronze.jwc_zones        (PDF parsed 1회)                │ │
│  │                                                            │ │
│  │  silver.* (정제·통합·중복제거)                          │ │
│  │  gold.risk_indicators (4종 input 종합)                   │ │
│  └──────────────────────────────────────────────────────────┘ │
│                          ▲                                     │
│                          │                                     │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ Lakeflow Jobs                                             │ │
│  │  • Job 1: Tier 1 Daily (06:30 cron)                       │ │
│  │    - 모든 source 종합 fetch                               │ │
│  │    - risk score 계산                                      │ │
│  │    - Discovery Feed 3-5건 생성                           │ │
│  │  • Job 2: Tier 2 Realtime (5분 cron)                      │ │
│  │    - OilPriceAPI 가격 fetch                              │ │
│  │    - 뉴스 RSS fetch                                      │ │
│  │    - rule-based filter → 이상 시 Agent 호출              │ │
│  │  • Job 3: AIS WebSocket (continuous)                      │ │
│  │    - 호르무즈 BoundingBox subscribe                      │ │
│  │    - bronze.ais_positions streaming insert               │ │
│  └──────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
                          ▲
                          │ HTTP / WebSocket
                          │
┌────────────────────────────────────────────────────────────────┐
│                  External APIs                                 │
│  • aisstream WebSocket / OilPriceAPI REST / GDACS REST        │
│  • ECOS REST / RSS feeds / JWC PDF (manual)                   │
└────────────────────────────────────────────────────────────────┘
```

---

## 3. Frontend 아키텍처 (Next.js + FastAPI)

```
[Databricks App: k-petroleum-decision-support]
│
├── Next.js 15 (App Router) [public 8000]
│   ├── app/
│   │   ├── layout.tsx (공통 layout, 사이드바)
│   │   ├── page.tsx (랜딩 → Discovery Feed redirect)
│   │   ├── feed/page.tsx (Discovery Feed)
│   │   ├── mission/page.tsx (Mission List)
│   │   ├── mission/[id]/page.tsx (Mission Detail)
│   │   └── whatif/page.tsx (What-If + Yesterday)
│   ├── components/
│   │   ├── ui/* (shadcn/ui)
│   │   ├── DiscoveryCard.tsx (swipe UX)
│   │   ├── MissionTimeline.tsx (Framer Motion)
│   │   ├── RiskScoreGauge.tsx
│   │   └── PriceDisplay.tsx (WTI/Brent/Dubai)
│   ├── lib/
│   │   ├── api.ts (FastAPI client)
│   │   └── types.ts
│   └── tailwind.config.ts
│
├── FastAPI backend [internal 8080]
│   ├── main.py (uvicorn)
│   ├── routers/
│   │   ├── feed.py        # Discovery Feed query
│   │   ├── mission.py     # Mission CRUD
│   │   ├── whatif.py      # Genie SDK 호출
│   │   ├── decision.py    # 결정 기록
│   │   └── risk.py        # risk score query
│   ├── services/
│   │   ├── lakebase.py    # Postgres connection
│   │   ├── genie.py       # Genie SDK wrapper
│   │   └── agents.py      # Agent Bricks 호출
│   └── models/ (pydantic)
│
└── app.yaml (Databricks Apps 설정)
    command:
      - bash
      - -c
      - |
        cd backend && uvicorn main:app --port 8080 &
        cd frontend && npm run start --port 8000
```

### Data flow 예시 (Discovery Feed)

```
1. 매니저가 폰으로 https://k-petroleum.cloud.databricks.com 접속
2. SSO 로그인 (회사 OAuth)
3. Next.js /feed 페이지 로드
4. Client-side fetch → /api/feed
5. FastAPI feed.py → Lakebase query (오늘 큐)
6. SELECT * FROM missions JOIN events WHERE date = today
7. 3-5건 결과 → JSON
8. Next.js DiscoveryCard 컴포넌트 render
9. 매니저 "OK" 버튼 → POST /api/decision
10. FastAPI decision.py → INSERT INTO decisions
11. (Optional) Agent Bricks Mission Operator trigger
```

### Data flow 예시 (What-If)

```
1. 매니저가 /whatif 페이지에서 NL 입력
   "Brent $140 / Dubai $135 가면 우리 portfolio impact?"
2. POST /api/whatif body={query, current_position}
3. FastAPI whatif.py → Genie SDK Agent Mode 호출
4. Genie가 Lakebase + gold tables 종합 reasoning
5. SQL 생성 → 실행 → 결과 chart 메타데이터 반환
6. Next.js Recharts로 시각화
7. 5초 안에 ROI 차트 표시
```

---

## 4. 4-tool 활용 깊이

### Tool 1: Databricks Apps
- Next.js + FastAPI hybrid
- 3 page (Feed / Mission / What-If)
- Lakebase direct connection
- mobile-responsive

### Tool 2: Genie
- Genie Space 구성 (Bronze/Silver/Gold tables 등록)
- Agent Mode 활성화 (2025-09 GA)
- Semantic layer (한국 SCM 용어: Term/Spot/lifting/OSP)
- What-If 페이지에 SDK 임베드

### Tool 3: Lakebase
- Autoscaling Postgres
- 4 tables (missions / mission_events / rfq_negotiations / decisions)
- Apps에서 direct connection
- 4주 mission state 영속

### Tool 4: Agent Bricks (Custom Agents GA)
- Mosaic AI Agent Framework 사용
- 4 Custom Agents:
  1. **Monitoring Agent** — 5종 데이터 + 뉴스 → risk score
  2. **Simulation Agent** — Genie 연동, 시나리오 ROI
  3. **RFQ Chaining Agent** — 4사 Frame Contract 자동 협상 시뮬
  4. **Self-Critique Agent** — 매주 모델 보정
- MLflow tracking

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
  - fetch_oil_prices  # OilPriceAPI WTI/Brent/Dubai
  - fetch_gdacs_events
  - fetch_exchange_rates  # ECOS
  - fetch_news_rss  # Reuters/AP/연합뉴스
  - calculate_risk_score  # 4종 input 종합
  - generate_discovery_feed  # 3-5건 큐레이션 → Lakebase
  - notify_managers  # 알림
```

### Job 2: Tier 2 Realtime (5분 cron)
```yaml
name: tier2_realtime
schedule: "*/5 * * * *"  # 5 minutes
tasks:
  - fetch_oil_prices_5min  # 가격 변동 체크
  - fetch_news_rss_5min
  - rule_based_filter  # 2% 이상 변동? 키워드 매칭?
  - if anomaly_detected:
      - trigger_agent_analysis  # Agent Bricks Monitoring
      - urgent_alert  # Lakebase events priority='urgent'
```

### Job 3: AIS WebSocket (continuous)
```python
# 별도 long-running job
# Databricks Apps에서 실행 또는 Job Cluster
async with websockets.connect(URL) as ws:
    while True:
        msg = await ws.recv()
        # bronze.ais_positions에 streaming insert
```

---

## 8. 작업 우선순위 (D-16)

### Week 1 (5/6 - 5/12)
- [x] API key 발급 ✅
- [x] Source 6종 ingestion 검증 ✅
- [ ] Databricks workspace 구조 setup
- [ ] Bronze Delta tables 6종 생성
- [ ] Lakebase Postgres 4 tables 생성
- [ ] Lakeflow Job 1·2 작성 (Daily, Realtime)
- [ ] AIS WebSocket Job 작성

### Week 2 (5/13 - 5/19)
- [ ] Genie Space 설정 + semantic layer
- [ ] Agent Bricks Custom Agents 4개
- [ ] Next.js 15 setup + Tailwind + shadcn/ui
- [ ] 3 page 구현 (Feed / Mission / What-If)
- [ ] FastAPI 백엔드
- [ ] Databricks Apps deploy

### Week 3 (5/20 - 5/22)
- [ ] end-to-end 통합 테스트
- [ ] 5분 데모 영상
- [ ] 제출 README + Devpost

---

## 9. Risk

### 기술 risk
- ⚠️ Next.js + FastAPI hybrid Databricks Apps 안정성 — 공식 가이드 있음, 그러나 첫 시도
- ⚠️ Agent Bricks Custom Agents 안정성 (GA지만 새 기능)
- ⚠️ Lakebase Autoscaling × Apps connection
- ⚠️ AIS WebSocket long-running job 안정성

### 도메인 risk
- ⚠️ 김지훈 가상 (LG화학 SCM 인터뷰 진행 중)
- ✅ 가격·비중 데이터는 대한석유협회 공식 ground truth

### 일정 risk
- ⚠️ 16일 마감 — Frontend 5일 잡음
- ⚠️ 형욱 본업 + APEX + ApexF1 + 이거 동시 = burnout risk

---

## 10. Plan B (시간 부족 시)

### Cut 가능
1. **Agent Bricks 4개 → 2개** (Monitoring + Simulation만)
2. **Next.js → Streamlit** (프로토타입 quality 낮춤, 시간 -3일)
3. **Living Mission 6건 → 1건** (시연용만)
4. **What-If Genie → 정적 시뮬** (NL X)

### 유지 필수
- Discovery Feed (Wow 1)
- 4-tool 활용 명확
- 5종 데이터 ingestion
- 5분 데모 영상
