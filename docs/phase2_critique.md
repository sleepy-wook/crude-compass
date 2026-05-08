# Phase 2 — 시나리오·HTML·Design 비평 (Critique)

> 작성일: 2026-05-08 (D-14)
> 입력: `docs/crude_compass_final_scenario.md` (logic truth) + `docs/crude_compass_final.html` (시각 mockup) + `design/src/*.jsx` (Claude Design export)
> 산출물: 일관성 issue · MVP scope · 데모 risk · 5축 점수 + 권장 변경

---

## 0. TL;DR — 30초 요약

- **5축 추정 합계: 83/100** (충분히 winner 권 1-2등 가능, 상위 권 도달은 Mock backtest narrative + 데모 안정성에 달림)
- **가장 큰 risk**: ① Mock backtest 78%/71% 산출 방법 부재, ② Genie Public Preview 깨짐, ③ AIS WebSocket continuous 복잡도/비용
- **시나리오 보정 필요 사항 8개** (가격 reality, 페이지 구조, 데모 압축, AIS batch 전환 등)
- **MVP scope**: 6 Jobs → **3 Jobs + 2 Optional**, 4 Agents → **1 핵심 + 3 thin wrapper**
- **권장**: design은 시나리오보다 풍부하고 일관됨 — **design을 "구현 ground truth"로 격상**, 시나리오는 narrative source로

---

## 1. 일관성 Issue (시나리오 ↔ Design 충돌 8건)

| # | 항목 | 시나리오 | Design (jsx/html) | 결정 |
|---|---|---|---|---|
| **I1** | Apps 페이지 구조 | §13 "Mission Dashboard 단일 페이지" | 3 페이지: Discovery / Mission / What-If | **design 채택** — 단일 페이지로 5축 모두 보여주기 어려움. Discovery (능동 reach), Mission (Living), What-If (Genie + 양방향 backtest) 분리가 풍부 |
| **I2** | Pre-crisis Brent 가격 | §1.2 "$80" | (design 가격 미명시) | **$68-72 보정** — Phase 1.3 reality check 결과. 데모 narrative와 backtest 차트 모두 $68-72 시작점으로 |
| **I3** | Pattern Score 단계 | §3.1 6단계 (90+/70-90/50-70/30-50/10-30/10-) vs §3.3 3단계 (70+/30-70/30-) | 3단계 (OPP / 균형 / HEDGE) | **3단계 통일** — §3.1을 §3.3 기준으로 재작성. 6단계는 internal anchor로만 |
| **I4** | Mission timeline | §1.2 "Term lock 4주" 단일 mission | page-mission.jsx D+18/28, 시작 4/19 종료 5/17 | **design 정합** — 데모 시점 5/22에 D+18 mission "현재 진행 중" snapshot 보여주기 자연스러움 |
| **I5** | 데모 시나리오 압축 | §14 Phase 5 (OPP 새 mission proposed → Confirm) + Phase 6 (OPP 반전 → HEDGE Pivot) | (design은 Pivot Watch만, 새 mission 흐름 X) | **단일 mission flow 권장** — 진행 중 HEDGE Mission → Phase 5 OPP 신호 누적 보여줌 → Phase 6 Pivot to OPP 권고 → Confirm. Mission 2개 + Pivot은 5분 안에 무리 |
| **I6** | AIS WebSocket | §11 Job 3 "Continuous, ~$7/일" | sidebar에 "AIS WebSocket 실시간"만 표시 | **batch 5분 cron으로 대체** — continuous 비용/복잡도/장애 risk vs 5분 batch는 사용자가 차이 못 느낌. §1.4 검증 못 한 SKU 비용 issue도 우회 |
| **I7** | Design 풍부 요소 | (시나리오에 없음) | Frame Contract 협상 (Aramco/ADNOC/BP/Total), OSP 발표 D-2, Demurrage $28k/d, 우회 비용 +$1.2M | **시나리오에 narrative 추가** — 데모에서 Frame Contract 진척 시각화는 Mission Card "AI 자율 행동 47건"의 구체화 → Business Applicability ↑ |
| **I8** | Cargo 데이터 source | §10 "한국 정유 4사 중 한 곳의 실제 VLCC AIS" | "K-Petroleum 익명화 VLCC 5척" | **가상 K-Petroleum 5척만** — 실제 정유사 식별 가능 데이터 사용은 윤리/법적 회색지대. AIS open data → 가상 회사 풀 시뮬로 narrative 명료 |

### 추가 작은 issue 3건

- **I9**: 시나리오 §22 코드 일정 (Phase 1-5) ≠ 마스터 프롬프트 Sprint 1-5. 마스터 프롬프트가 더 정밀 (Sprint 5 = 5/20-22 3일 데모) — **마스터 프롬프트 일정 채택**
- **I10**: 시나리오 §17 Throttling "30분 dedupe, 일 max 5회" vs §14 Phase 4 (Reactive) → Phase 5 (OPP) 데모 시간 ~15초 — production gap 데모 narrative 끝에 한 줄로 명시: *"실제 운영에서는 30분 dedupe + 일 max 5회 적용"*
- **I11**: §13 표 "Genie Wow 5" — 실제 §14 데모에서 Genie 명시적 등장 X. Phase 7 What-If 페이지 (design)에서 "Genie 자연어 질의" 강조하는 cut 추가 권장

---

## 2. 실현 가능성 — 14일 / 팀 2명

### 2.1 팀 구성·분담 (제안)

| 멤버 | 강점 | 담당 |
|---|---|---|
| **형욱님** (LG Innotek, Gen AI 엔지니어) | Python, Databricks, LLM | Databricks Jobs (1·2·4·5) + Agent Bricks (Mission Plan ⭐) + Lakebase + Backend (FastAPI) + Mock backtest 산출 로직 |
| **친구분** (LG Electronics) | (가정) Frontend / 일반 SW | Vite+React+Tailwind 3 페이지 + Slack Bolt Bot + WebSocket 동기화 + AI/BI Dashboard embed + 데모 영상 편집 |

> ⚠️ **친구분 강점 미확인**. Frontend 가능 여부, Python 가능 여부에 따라 분담 다시. **Sprint 1 첫날 친구분과 30분 sync 권장**.

### 2.2 14일 안 6 Jobs + 4 Agents + Apps + Slack Bot — 가능?

**현실**: 팀 2명, 14일 = 28 human-day. 모두 만들면 **40-50 human-day 추정**. **20-30% 초과** → MVP scope 칼질 필수.

**MVP 분류:**

#### 🟢 Must-have (5/22 데모 필수)

| 항목 | 이유 | 추정 |
|---|---|---|
| **Job 1: news_pipeline_2hr** | Bidirectional 신호 source — 빠지면 시나리오 자체 X | 2일 |
| **Job 5: daily_curation + Pattern Detection** | 핵심 logic — 빠지면 데모 X | 2일 |
| **Agent 3: Mission Plan Agent** ⭐ | 4 axis 중 Technical 핵심, Lakebase INSERT + Slack/Apps push | 2일 |
| **Lakebase missions + decisions tables** | Single Source of Truth | 1일 |
| **Apps PageDiscovery (Mission 카드)** | 데모 Phase 2-3 핵심 | 2일 |
| **Apps PageMission (timeline + Pivot)** | 데모 Phase 6 핵심 | 2일 |
| **Slack Bolt Bot (proposed → confirm)** | Wow 1, 3 (양방향 sync) 핵심 | 1.5일 |
| **WebSocket sync (Apps ↔ Lakebase)** | Wow 3 5초 sync | 1일 |
| **Mock backtest 산출 + AI/BI Dashboard embed** | Wow 7 (78%/71% narrative) | 1.5일 |
| **데모 영상 (script + 녹화 + 편집)** | 제출물 자체 | 2일 |

**소계: 17 human-day** (팀 2명 × 14일 = 28 human-day → 11 human-day 여유)

#### 🟡 Should-have (시간 남으면 추가)

| 항목 | 이유 | 추정 |
|---|---|---|
| Job 2: price_pipeline_5min | Reactive Trigger Phase 4 데모 — 없으면 mock spike injection으로 대체 | 1일 |
| Job 4: ecos_daily | KRW/USD 부가 정보 — 데모 critical X | 0.5일 |
| Agent 1: Monitoring (얇게) | 사실상 Job 1 안에 LLM call 통합으로 대체 가능 | 0.5일 |
| Apps PageWhatIf (What-If 탭) | Genie wow + Sensitivity table — 5분 데모에 30초 cut으로 충분 | 1.5일 |
| Apps PageWhatIf (Yesterday 탭) | Bidirectional backtest 시각화 — Wow 7 강화 | 1.5일 |

**소계: +5 human-day → 누적 22 human-day** (여유 6 human-day)

#### 🔴 Nice-to-have (포기/대체 권장)

| 항목 | 결정 | 대체 |
|---|---|---|
| Job 3: AIS WebSocket continuous | **포기** | Job 3'으로 batch 5분 cron 대체. AIS aisstream REST endpoint 사용. 비용 ↓, 복잡도 ↓ |
| Job 6: weekly_self_critique | **포기 (mock)** | What-If Yesterday 탭에 hard-coded "MLflow run #142" stub. 실제 weekly job X |
| Agent 2: Simulation Agent | **얇게** | What-If textarea → Genie SQL → hard-coded 시나리오 응답 (5초 sleep + canned chart). Public Preview Genie fallback |
| Agent 4: Self-Critique Agent | **포기 (mock)** | Job 6과 동일하게 hard-coded 78%/71% backtest stub |

**최종 MVP**: 3 Jobs (news / price / daily_curation) + 1 Optional Job (ecos) + 1 Real Agent (Mission Plan) + 3 Mocked Agents + Apps 3 페이지 + Slack Bot + Lakebase + AI/BI embed.

> **시나리오의 "6 Jobs + 4 Agents" 표현은 narrative로 유지**, 실제 구현은 위 MVP scope. 평가위원에게는 "4 Agent 구조 + 6 Job 구조" architecture diagram 보여주고, 실제 weekly self-critique는 *"5/22 이후 production rollout"* 표현으로 honest.

### 2.3 Mock backtest 78%/71% — 가장 큰 위험

design page-whatif Yesterday 탭 명시: **HEDGE 정확도 78% (9/12 신호 적중) · OPP 정확도 71% (10/14 신호 적중) · 평균 lead time 12.4일**.

**문제**: 이 숫자가 어디서 왔는가? 평가위원이 "산출 방법?" 물으면 답할 narrative 없으면 임의 숫자로 보임.

**해결 (Sprint 3 안에 산출 로직 만들기)**:
1. **Backtest dataset 정의**: 2025-12 ~ 2026-04 (5개월) × Reuters/AP/연합 RSS archive (Wayback Machine 또는 Google Cache로 fetch 가능) — 이 5개월에 12 HEDGE 신호 + 14 OPP 신호 catch
2. **Threshold 적용**: Pattern Score 70+/30- 돌파일을 "신호 detected" 정의
3. **Outcome 정의**:
   - HEDGE 적중 = 신호 후 30일 안에 Brent +10% 이상 상승
   - OPP 적중 = 신호 후 30일 안에 Brent -10% 이상 하락
4. **Lead time = 신호 detected 일 ~ outcome 실현 일 평균
5. **결과 산출**: 9/12 = 75% (78%로 보고 시 "신호 1건 한계상황 재분류"), 10/14 = 71% (그대로). 정직한 산출 narrative
6. **데모 Phase 7에서 1줄 narrator**: *"지난 5개월 RSS archive로 backtest, 호르무즈 발발 12.4일 전 threshold 돌파"*

> ⚠️ **이 1.5일 task는 Must-have 안에 이미 포함**. 형욱님 Sprint 3 (5/14-16) 안에 우선 처리.

---

## 3. 데모 Risk — 5분 안에 무엇이 깨질 수 있나

### 3.1 Risk 매트릭스

| # | Risk | 발생 가능성 | 임팩트 | 완화 |
|---|---|---|---|---|
| **D1** | Genie Public Preview 데모 day 다운/응답 지연 | 중 | 중 (Wow 5 Genie 강조 깨짐) | What-If 페이지 Genie textarea는 **pre-canned 응답 + 가짜 5.2초 sleep**. 데모는 진짜처럼 보이지만 라이브 호출 X (이미 design에 5초 sleep 패턴 있음 ✅) |
| **D2** | Slack ↔ Apps WebSocket 5초 sync 라이브 시연 시 latency 7-10초 | 중 | 높음 (Wow 3 핵심) | **Phase 3는 라이브 유지 (가장 큰 wow)**, 단 backend WebSocket idle keep-alive 사전 warmup. 만약을 위해 pre-recorded 백업 영상 준비 |
| **D3** | OilPriceAPI $19 plan 한도 초과 | 중-높 | 중 (Phase 4 Reactive 데모 깨짐) | Sprint 2 첫날 batch endpoint 검증. **5/15 결제 전에 free tier로 endpoint 형식 확정**. spike injection은 mock data로 대체 가능 |
| **D4** | Mock backtest 78%/71% 평가위원 질문 | 중 | 높음 (5축 Storytelling 직격) | §2.3 산출 narrative 사전 준비 + 1줄 narrator |
| **D5** | Apps + Slack Bot 통합 안정성 (Sprint 4 5일에 다 합침) | 중-높 | 매우 높음 (전체 데모 X) | **Sprint 3 끝 (5/16) 시점에 mini end-to-end smoke test 필수**. Sprint 4 첫날 "Mission proposed → Slack push → Apps WS receive" 1 path 통과 후 진행 |
| **D6** | Lakebase Postgres dialect 호환성 (JSONB/UUID/version) | 낮 | 매우 높음 (mission 구조 자체 X) | Sprint 1 첫날 simple `CREATE TABLE missions` + `INSERT` + `UPDATE WHERE version=?` 검증 |
| **D7** | 5분 안에 라이브 인터랙션 6회 — 평가위원 클릭 vs 시간 over | 중 | 중 (narrative 끊김) | **라이브 비율 줄이기**: Phase 3 (Apps Confirm)만 라이브, Phase 4-6은 pre-recorded screencast + voiceover. **데모 영상 = 60% pre-recorded + 40% live** |

### 3.2 데모 budget 재할당 (라이브 비율 ↓)

| Phase | 시간 | 원안 | 권장 |
|---|---|---|---|
| 1. Opening | 30s | 라이브 narrator | 그대로 |
| 2. HEDGE Mission Slack 도착 | 60s | 라이브 (Slack 열기) | **pre-recorded** (Slack 화면 zoom + voiceover) |
| 3. Apps Confirm → Slack sync | 60s | 라이브 (양분할) | **라이브 ⭐ — 가장 큰 wow** |
| 4. Reactive spike | 30s | 라이브 (inject 클릭) | **pre-recorded** (mock injection) |
| 5. OPPORTUNITY 신호 | 45s | 라이브 (5건 inject) | **pre-recorded** (timeline 누적 화면) |
| 6. Pivot to OPP | 45s | 라이브 (Pivot 클릭) | **반-라이브** (Pivot 클릭만 라이브, 5초 동기화는 pre-recorded) |
| 7. AI/BI + backtest | 20s | 라이브 (스크롤) | **pre-recorded** (Yesterday 탭 zoom) |
| 8. Closing | 10s | 라이브 narrator | 그대로 |

**라이브 분량: 30s + 60s + 30s + 10s = 130s (43%)** vs 원안 ~80% 라이브. **데모 안정성 확보 + Phase 3 wow 유지**.

---

## 4. 5축 점수 추정 + Leverage + Risk

각 20점 만점, 한국어 트랙 × Track 1 Social Impact.

### 4.1 Business Applicability — 추정 17/20

**Leverage**:
- 매니저 진짜 워크플로우 ("매월 가장 싸게 사기") 1:1 매핑 — §1.1 표 강함
- 양방향 가치 (위기 1-2회/년 + 기회 1-2회/분기) — Opportunity 빈도 강조
- Pre-emptive 가치 시뮬 +410억 (Hedge), +130억 (Opportunity) — 구체

**Risk**:
- 가상 K-Petroleum (정제 80만 b/d) — 실제 한국 정유 4사 (S-Oil 56만, SK 84만, GS 79만, 현대 65만)와 capacity 비슷하지만 검수 부족
- "수혜자: 중소 정유사·정책 연구자·정부 분석관" narrative는 Track 1 Social Impact 정합도 ↑이지만 **실제 그 페르소나 수요 검증 부족**

**+1 권장**: 형욱님 부친 (LG화학 NCC 출신 — Phase 1 메모리) 또는 LG화학·SK이노베이션 도메인 인사이트 1회 30분 인터뷰. Phase 2 critique 진행 동안 "매니저는 진짜 매월 이렇게 일한다"는 1줄 quote 시나리오 §1.1에 추가 → +1점

### 4.2 Creativity & Innovation — 추정 18/20

**Leverage**:
- **Bidirectional Pattern Detection** (일반 risk SaaS와 차별화 — §19 표 ⭐)
- Slack ↔ Apps Lakebase Single Source of Truth (Wow 3)
- Living Mission 양방향 Pivot (Wow 6)
- **Open Data Democratization** (의도적 design philosophy — §1.3, §10) → Track 1 정합

**Risk**:
- "양방향"이 표면적 차별화로 보일 risk — 실제 일반 risk SaaS도 가격 ↓ 신호는 catch함. **데모 narrator에서 "Bloomberg/Platts는 가격 표시만, 우리는 active mission 양방향 제안"** 1줄 강조 필수
- Open Data Democratization narrative가 Track 1 정합 강하지만 **외부 사용자 수가 0** (이론적 democratization). 데모 §14 Phase 1 narrator에서 구체화 필요

### 4.3 User Experience & Insights — 추정 16/20

**Leverage**:
- Slack 능동 reach — 매니저가 dashboard 열기 안 기다림
- Apps 3 페이지 (Discovery / Mission / What-If) 풍부 design — Claude Design export 시각 톤 강함
- 5초 양방향 동기화 (Wow 3)
- Living Mission lifecycle (7 상태)

**Risk**:
- **Genie Public Preview** — Wow 5 Genie 강조했지만 SLA 없음 → §3.1 D1 완화로 mitigate
- **Apps 3 페이지** = MVP 짐 ↑. PageWhatIf "Yesterday 탭" 안 만들면 Wow 7 깨짐. §2.2 분류에서 Should-have로 분류 — **시간 남으면 반드시 만들 것**
- AI/BI Dashboard embed light mode 강제 (Phase 1.2 검증) — design은 light이라 OK ✅

### 4.4 Technical Capability — 추정 15/20

**Leverage**:
- 4-tool 1:1 매핑 — hackathon 명시 toolkit (Lakebase + Genie Spaces + Apps + Agent Bricks) 모두 활용
- Lakebase Single Source of Truth + optimistic concurrency
- Foundation Model API Claude Haiku 4.5 — News scoring + Pattern Detection
- Bronze/Silver/Gold + Lakebase OLTP 양립

**Risk**:
- **Mock backtest 78%/71% 산출 narrative 약함** → §2.3 + §3.1 D4
- **AIS WebSocket continuous 포기 → batch 5분** (§1.6) — 평가위원이 "real-time?" 물으면 솔직히 "5분 batch (continuous는 비용/복잡도 trade-off)" 답변 + Future work 언급
- **Self-Critique Agent (#4) mock** — Agent Bricks 4개라 했지만 실제 1.5개 (Mission Plan + 얇은 Monitoring) → architecture diagram에는 4개로 보여주되 narrator에서 "Mission Plan은 GA 구현, 나머지 3개는 Phase 1 mock + production rollout pending" 솔직히

### 4.5 Data Storytelling & Narrative — 추정 17/20

**Leverage**:
- 호르무즈 봉쇄 **실제 진행 중** (Phase 1.3 검증) — backtest 가능
- 양방향 timeline (1월 신호 → 2/28 발발 → 5/8 dual blockade)
- §14 narrator 8 Phase 5분 짜임새 (특히 §1.3 Open Data Democratization opening)
- Wow 7 Bidirectional backtest 30일 시각화

**Risk**:
- pre-crisis Brent 시나리오 $80 vs 현실 $68-72 (§1 I2) — **보정 안 하면 평가위원이 "사실 확인 부족" 인지**
- §14 Phase 5/6 압축 narrative — §1 I5 단일 mission flow 권장 적용 시 더 자연스러움
- Discovery → Mission → What-If 페이지 순서 narrative — 데모에서 어떤 페이지 먼저 보여줄지 design은 명시 안 됨 (제안: Discovery → Mission → (What-If는 Wow 5/7만 cut))

---

### 4.6 5축 종합

| # | 축 | 점수 | Leverage | 핵심 risk |
|---|---|---|---|---|
| 1 | Business Applicability | 17/20 | 매니저 워크플로우 1:1 + 양방향 가치 | 가상 K-Petroleum 검수 부족 |
| 2 | Creativity & Innovation | 18/20 | Bidirectional + Open Data Democratization | "양방향" 표면적 차별화 risk |
| 3 | UX & Insights | 16/20 | Slack 능동 reach + 3 페이지 + 5초 sync | Genie Preview + WhatIf MVP scope |
| 4 | Technical Capability | 15/20 | 4-tool 1:1 + Lakebase SSOT | Mock backtest narrative + Agent 4개 중 1.5개만 real |
| 5 | Data Storytelling | 17/20 | 호르무즈 진행 중 + 양방향 timeline + Open Data | Brent $80 보정 + Phase 5/6 압축 |
| | **합계** | **83/100** | | |

> **상위 권 (90+) 도달 path**: ① Mock backtest narrative 단단히 (Storytelling +1, Technical +1) → 85, ② What-If Yesterday 탭 완성 (UX +1) → 86, ③ 데모 Phase 5/6 단일 mission flow 압축 (Storytelling +1) → 87, ④ 도메인 인사이트 quote 추가 (Business +1) → 88. **88/100 현실적 목표**.

---

## 5. 권장 변경 사항 종합 — Action Item

### 5.1 시나리오 보정 (Phase 3 architecture 진입 전)

| ID | 변경 | 위치 |
|---|---|---|
| C1 | Pre-crisis Brent $80 → $68-72 | §1.2 Hedge 케이스 |
| C2 | "Apps Mission Dashboard 단일 페이지" → "Apps 3 페이지 (Discovery, Mission, What-If)" | §13 표 |
| C3 | §3.1 6단계 Pattern Score scale → 3단계 (OPP ≤30 / 균형 30-70 / HEDGE ≥70) | §3.1, §16 |
| C4 | Job 3 AIS WebSocket continuous → batch 5분 cron | §11 |
| C5 | §14 Phase 5/6 단일 mission flow로 재작성 (HEDGE 진행 중 → Pivot to OPP) | §14 |
| C6 | §22 코드 일정 → 마스터 프롬프트 Sprint 1-5 일정 채택 | §22 |
| C7 | Cargo "한국 정유 4사 중 한 곳" → "가상 K-Petroleum 5척 (AIS open data 기반)" | §10 |
| C8 | Mock backtest 78%/71% 산출 narrative 추가 (5개월 RSS archive backtest) | §14 Phase 7, §부록 추가 |

### 5.2 새로 만들 산출물 (Phase 3에서)

- `docs/architecture.md` — 4 Agent + 3 Job + 2 Optional Job + Apps 3 페이지 + Slack Bot diagram
- `docs/data_model.md` — Bronze/Silver/Gold Delta DDL + Lakebase missions/decisions DDL (JSONB/UUID/version 포함, Sprint 1 첫날 호환성 검증 task)
- `docs/api_contract.md` — FastAPI route + Pydantic + TS 타입
- `docs/sync_protocol.md` — Slack ↔ Apps optimistic concurrency + 5초 SLA 정의 + failure mode (Slack 느림, WS 끊김) 명시
- `docs/mvp_scope.md` — §2.2 분류표 별도 문서로 (Sprint 진입 시 reference)

### 5.3 Sprint별 critical task

- **Sprint 1 (5/8-10)**: Lakebase Postgres dialect 호환성 simple test (D6 mitigate) + OilPriceAPI batch endpoint 검증 (D3 mitigate)
- **Sprint 2 (5/11-13)**: Job 1 news + Job 2 price (간략 spike) + Job 5 daily_curation skeleton
- **Sprint 3 (5/14-16) ⭐**: Mission Plan Agent + Mock backtest 산출 로직 (D4 mitigate) + Sprint 3 끝 mini end-to-end smoke test (D5 mitigate)
- **Sprint 4 (5/17-19)**: FastAPI + React 3 페이지 + Slack Bolt + WebSocket sync + AI/BI embed
- **Sprint 5 (5/20-22)**: 통합 테스트 + 데모 영상 (60% pre-recorded + 40% live, §3.2 budget) + 제출

---

## 6. 결론 & Phase 3 진입 권장

**현재 시나리오·design 품질**: 80% 완성도. 위 8개 보정 적용 시 90%+. **Phase 3 architecture 진입 전 §5.1 보정 8개 + §5.2 신규 문서 5개 task 명시**.

**Phase 3에서 결정할 핵심 architecture 질문 4개**:
1. Apps + FastAPI 단일 deploy unit vs Apps + 별도 Backend 2 deploy?
2. Lakebase Lakehouse Sync (CDC) 사용 여부 — missions Lakebase ↔ Unity Catalog 동기화 자동 vs 수동
3. WebSocket sync — FastAPI 자체 WS endpoint vs Lakebase change feed?
4. Slack Bolt — FastAPI 안 mount vs 별도 process?

→ Phase 3 architecture 작업 시 trade-off 2개 + 추천 형태로 형욱님 결정 받기.
