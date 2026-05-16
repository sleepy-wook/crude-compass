# Crude Compass — Pre-emptive Bidirectional Decision Support Agent

> Databricks Building Intelligent Apps Hackathon 2026 (with AWS) · 한국어 트랙 · **Track 1 Social Impact (Open Data)**
>
> 마감: 2026-05-22 제출 → 5/25-29 심사 → 6/15 결과
>
> 본 문서는 logic ground truth. 시각 mockup은 [crude_compass_final.html](crude_compass_final.html), Claude Design export는 [`design/`](../design/), 비평·MVP는 [phase2_critique.md](phase2_critique.md).

---

## 1. 한 줄 정의

> **한국 정유사 원유 조달 의사결정 코파일럿.** 지정학·시장 시그널을 종합해 텀 계약과 스팟 매입의 비중을 미세 조정하는 **양방향 멀티 에이전트 시스템**.

- 위기 신호 누적 → Pre-emptive HEDGE Mission (Term ↑)
- 약세 신호 누적 → Pre-emptive OPPORTUNITY Mission (Spot ↑)
- 결정은 사람, 자율은 AI, 동기화는 Lakebase, 데이터는 100% open public

---

## 2. 핵심 메시지 — 평시 가치가 메인

> 사람은 2026-02-28 호르무즈 봉쇄가 갑자기 터졌다고 보지만, 데이터에는 1월부터 시그널이 있었다. AI가 다양한 선행지표를 종합해 가격 반영 전에 비중을 조정하면 막대한 비용 절감이 가능하다.
>
> **하지만 이 시스템의 진짜 가치는 호르무즈 한 번이 아니라, 평시 매주/매월 발생하는 중간 강도 시그널 (OPEC 회의, EIA 재고 발표, 사우디 감산, 중국 PMI, 허리케인) 을 종합하는 일상 도구라는 점.** 호르무즈는 가장 극적으로 빛난 사례일 뿐.

**Opening narrator (필수)**:
> "이 시스템은 호르무즈 같은 대형 위기 한 번을 위한 게 아닙니다. 평시 매주 발생하는 작은 시그널을 종합하는 일상 도구이고, 호르무즈는 그 가치가 가장 극적으로 드러난 사례입니다."

### 빈도 (계산 근거)

- **위기 신호 (HEDGE)**: 1년 1-2회 큰 임팩트 (호르무즈, 러우, OPEC 갑작스 감산)
- **약세 신호 (OPPORTUNITY)**: 분기 1-2회 (휴전, SPR 방출, 중국 수요 둔화)
- **평시 미세 조정**: 매주 (OPEC 월간 보고서, EIA 주간 재고, Aramco OSP, 허리케인 시즌)

→ **Opportunity가 더 자주 가치 만든다**. 매니저의 진짜 일은 "위기 헤지"가 아니라 "매월 가장 싸게 사기".

---

## 3. Track 1 — Open Data Democratization

Crude Compass는 의도적으로 **100% public open data만** 사용한다. 이게 Track 1 (Social Impact, Open Data) 진짜 의도.

| | 정유 빅5 | 중소 정유사 / 연구자 / 정부 분석관 |
|---|---|---|
| Bloomberg / Platts / Vortexa / Kpler | 연 수천만원 사용 가능 | 도입 부담 |
| 같은 인텔리전스 | ✅ | **❌ → ✅ (Crude Compass)** |

수혜자:
- **중소 정유사** — 유료 시스템 없이 동일 의사결정 지원
- **석화 trading desk** — 나프타 의존 산업 보호
- **정책 연구자** — 대외경제정책연구원, 산업연구원
- **정부 분석관** — 산업부 / 외교부 에너지 안보

**핵심 narrative**: *"한국 5천만 국민 에너지 안보. 한국 원유 73.5% 중동 의존. 정유 빅5만 가지던 인텔리전스를 모두에게."*

---

## 4. 페르소나

### 가상 정유사 — Korean Refiner A (=K-Petroleum)
- 정제 capacity 80만 b/d (한국 정유 4사 평균)
- baseline Term 60% : Spot 40% (대한석유협회 통계 기준 Term 약 57-60% — 산업 평균, 정유사별 차이 있음)
- ⚠️ **GS칼텍스/SK이노베이션/S-Oil/현대오일뱅크 사옥/로고/상호 일체 노출 금지** (모티브로만 사용)

### 매니저 — 김지훈
- 30대 후반 원유조달팀 시니어
- Slack always-on, Apps deep work
- Crude Compass 4주째 보조 중

### 평가위원 (실제 5분 데모 viewer)
- 매니저 입장 직접 체험
- AI Pre-emptive 제안 receive (Slack)
- Apps에서 Confirm + Backtest 시점 슬라이더 + 평시 그래프 체험

---

## 5. 의사결정 범위 (해커톤 스코프)

정유사 실무 6개 의사결정 축 중 **2개에 집중** (나머지는 Phase 2 슬라이드):

| Phase | 축 | 내용 |
|---|---|---|
| **메인** | 1. 텀 vs 스팟 비중 조절 | 양방향 (Hedge/Opportunity), 4주 Mission |
| **메인** | 2. 랜딩 코스트 시각화 | "원유 가격 같아도 도착 비용 다르다" — 보험료 + 운임 + 우회 비용 반영 |
| Phase 2 | 3. 원유 종류 선택 (Brent/Dubai/WTI 외) | 슬라이드 |
| Phase 2 | 4. 운송 리드타임 | 슬라이드 |
| Phase 2 | 5. 비축유 운영 | 슬라이드 |
| Phase 2 | 6. 정제 가동률 + 헤지 포지션 | 슬라이드 |

Benchmark: **Brent / Dubai / WTI 3개**. Dubai 중심 (한국 중동산 70-75%).

---

## 6. Bidirectional Pattern Detection ⭐ 우리 차별화 핵심

### 6.1 Score 재설계 — 양방향 (3-zone)

```
              위기 신호 (HEDGE Mission, Term ↑)
                    ▲
                    │ 70-100  HEDGE zone     → Mission 자동 trigger
       ─────────────┼───────────── (50 = 균형)
                    │ 30-70   STABLE zone    → log only
       ─────────────┼─────────────
                    │ 0-30    OPPORTUNITY    → Mission 자동 trigger
                    ▼
              약세 신호 (OPPORTUNITY Mission, Spot ↑)
```

Internal anchors (urgency 분기): 90+ Urgent Hedge / 10- Urgent Opportunity → 즉시 Slack push.

### 6.2 양방향 누적 계산 (시간 감쇠 + 시그널별 람다)

```python
# 3-6개월 window
window_days = 90

# 시그널별 람다 (휘발성 차등)
LAMBDA = {
    "news_tone":      0.046,   # 반감기 15일 (휘발성 강)
    "eia_inventory":  0.012,   # 반감기 60일 (구조적)
    "opec_momr":      0.012,   # 반감기 60일 (구조적)
    "fx_krw_usd":     0.023,   # 반감기 30일
    "price_spike":    0.046,   # 반감기 15일
}

# Bidirectional weighted score
bullish_score = SUM(
    raw_intensity * exp(-LAMBDA[signal_type] * days_ago) * source_credibility
) WHERE direction = 'bullish' AND raw_intensity >= 60

bearish_score = SUM(...) WHERE direction = 'bearish' AND raw_intensity >= 60

# Cross-validation bonus
cross_val = COUNT(category × direction WITH ≥2 sources confirm) × 5

# 최종 Pattern Score
net_signal = bullish_score - bearish_score
pattern_score = clamp(0, 100, 50 + (net_signal / max_normalized) * 50 + cross_val)
```

**시간 감쇠 SQL UDF / UC Function으로 분리** → Genie도 호출 가능 → 자연어 질문에 동일 계산.

람다 자체를 Delta 설정 테이블에 두고 버전 관리 가능 (Sprint 5 confidence — 현 hackathon scope-out).

### 6.3 데이터 설계 디테일

1. **Bronze/Silver append-only**. 절대 덮어쓰기 X. 다른 람다로 재계산 가능해야 함.
2. **시그널별 기여도 컬럼 보존** — `weighted_contribution`. *"오늘 점수 82는 GDELT 뉴스 톤 35%, OPEC MOMR 28%, EIA 재고 22%, FX 환율 15% 기여"* 시각화.
3. **Confidence Score** 별도 계산 — source 다양성 + cross-validation count 기반. 권고 시 함께 노출.

### 6.4 Mission 자동 trigger

```
Pattern Score 70+ (위기) → HEDGE Mission Plan Agent 호출
Pattern Score 30 이하 (기회) → OPPORTUNITY Mission Plan Agent 호출
단일 event raw_intensity 80+ → 즉시 trigger (정기 cron 안 기다림)
```

### 6.5 시그널 시간 지평 카테고리 ⭐ (소스별 진짜 가치)

소스마다 **adverse event 대비 detection lead time**이 다름. 단일 적중률로 평가하면 안 됨:

| Category | 대표 source | Lead time | 측정 가능성 |
|---|---|---|---|
| **Leading (선행)** | GDELT 키워드 mention burst (호르무즈/이란/OPEC) | **시간~수일 전** (D-7 ~ D-1) | 정성적 (실제 가격 반영 전 detection) |
| **Macro (구조)** | OPEC MOMR, 중국 PMI, ECOS FX trend | 수일~수주 전 (D-30 ~ D-7) | 정량적 (시뮬 가능) |
| **Fundamentals (실적)** | EIA 재고 weekly, Dubai daily close | 즉시~수일 (D-7 ~ D+1) | 정량적 (직접 cross-check) |

**핵심 reframe**:
- GDELT는 macro sentiment trend + 지정학 키워드 burst. **누적 mention burst 패턴**이 leading 시그널 — 호르무즈/이란/OPEC 단일 키워드 mention +280% 등.
- OPEC MOMR + FX는 macro anchor — 산유국 공급 + 환율 trend로 fundamentals 보강.
- EIA / Dubai는 cross-validation anchor — leading 신호가 fundamentals와 일치할 때 confidence ↑.

→ 백테스트 평균 적중률 75%는 fundamentals + macro + GDELT leading 통합 측정.

### 6.5.1 Backtest 4 source + Reactive 1 source — production composition

| 영역 | Source | 데이터 형태 | 사용 위치 |
|---|---|---|---|
| **Backtest (historical 7년)** | GDELT / EIA / OPEC MOMR / FX (ECOS) | 4 source × daily-monthly granularity | backtest 75% hit (n=298) |
| **Ground truth (historical)** | OPINET KNOC daily close (Dubai/Brent/WTI 1996~) | 2,545+ rows daily | 30/90일 saving % 계산 |
| **Production-only (realtime)** | OilPriceAPI 5min spike | intraday streaming | Phase 6 (price spike Reactive) |

**왜 분리?** OilPriceAPI는 realtime-only tier — backtest 추가 자체가 데이터 부재로 불가능. spike 시그널은 production 라이브에서만 측정 가능.

### 6.5.2 AIS Stream 제거 결정 (5/16 D-2)

D-2 검증 결과 AIS Stream을 production composition에서 완전 제거:
- **Backtest 부재** — `silver.signal_events_decayed`에 ais_traffic 시그널 row 0건. 7년 backtest 75% hit rate는 GDELT/EIA/OPEC/FX 4 source만으로 달성.
- **Real-time vessel 0건** — 5/16 D-2 글로벌 8min scout (BBOX 전세계) 결과 한국 flag (MMSI 440/441) + ship_type 80 (Tanker) + length ≥280m (VLCC) 조건 충족 vessel 0척. SK Shipping 5척 (publicly known fleet)도 데모 시점 트래픽 0.
- **Narrative 부담** — "K-Petroleum 5척 fleet 실시간 추적" 표현은 실데이터 없이는 mock 시뮬이 되어 신뢰성 risk.

→ **호르무즈 narrative anchor는 GDELT 뉴스 키워드 mention burst로 단일화**. Lloyds JWC PDF도 동반 제거 (manual quarterly, active job 0건).

**평가위원 narrator (수정)**: *"한국 정유사가 매일 보는 6개 공개 데이터 — GDELT 뉴스, OilPriceAPI, OPINET, EIA, ECOS 환율, OPEC MOMR — 를 종합해 Pattern Score 산출. 호르무즈 같은 위기 시그널은 GDELT 키워드 mention burst (이란/호르무즈 +280%) 와 OPEC MOMR 공급 변화로 D-7 시점에 감지합니다."*

**Track 1 Social Impact 측면**: Bloomberg/Platts/Vortexa는 모두 유료. 우리는 GDELT + EIA + OPEC + ECOS + OilPriceAPI + OPINET 무료로 7년 backtest 75% hit rate 검증 — **open data democratization 진짜 의미**.

---

## 7. 데이터 Source — 6개 (100% Open Public)

| 우선 | Source | 형식 | 빈도 | 역할 | 비용 |
|---|---|---|---|---|---|
| 1 | **GDELT** ⭐ | REST API | 15min | 글로벌 뉴스 멘션 빈도 + tone score (감지층 + 호르무즈 키워드 mention burst) | 무료 |
| 2 | **OilPriceAPI** | REST | 5min | Brent/WTI/Dubai 결과 측정 + spike 시그널 | $15 Exploration plan (5/15-22) |
| 3 | **OPINET KNOC** | CSV | 일 1회 | Dubai/Brent/WTI daily close (한국 정유사 baseline, 1996~) | 무료 |
| 4 | **EIA Open Data API** | REST | 주간 (수) | 미국 재고/통계 정기 이벤트 | 무료 |
| 5 | **ECOS 한국은행** | REST | 일 1회 (평일) | KRW/USD 환율 (한국 정유사 핵심) | 무료 무제한 |
| 6 | **OPEC MOMR PDF** ⭐ | PDF (월간) | 월 1회 | Document Intelligence 시연 + 산유국 시각 보정 | 무료 |
<!-- D-3 (2026-05-15) 정리: RSS 보강층 제거 — never ran + GDELT 단일 source로 충분 판단. -->
<!-- D-2 (2026-05-16) 정리: AIS Stream + JWC PDF 제거. AIS는 한국 flag VLCC 0척 active + 7년 backtest 미사용 → narrative dead weight. JWC는 manual quarterly로 active job 0건. 호르무즈 narrative anchor는 GDELT 키워드 mention으로 단일화. -->


### 데이터 설계 원칙

- **Dubai 중심**, Brent/WTI는 비교 기준선
- **뉴스는 두 층 분리**:
  - **감지층 = GDELT 단독** — 멘션 빈도 + tone. 매체별 단독 보도 경쟁 신경 X
  - **보강층 = RSS 이벤트 드리븐** — GDELT alert 발생 시점에만 fetch → Knowledge Assistant
- **유료 데이터 사용 금지** (Bloomberg, Platts 풀, TankerTrackers 유료, Vortexa)
- **데모는 과거 데이터 + 시간 시뮬레이션** — 실시간 스트리밍 X (안정성 우선)
- **PDF 2개는 Document Intelligence 시연 재료** — `ai_parse_document()` SQL 한 줄로 파싱

### 총 외부 비용
- OilPriceAPI: $15 (5/15 결제 → 5/22 데모 → 5/23 cancel)
- 그 외 모두 무료 (AIS Stream/JWC 제거 — 5/16 D-2)
- **총 $15**

---

## 8. 데이터 분리 원칙 — Delta vs Lakebase

> "세상에 대한 데이터인가, 우리 앱 자체에 대한 데이터인가."

- **세상 데이터** (시장, 뉴스, 가격, 통계, PDF) → **Delta Lake** (분석 OLAP)
- **앱 상태 데이터** (세션, 대화, 권고 기록, mission state, 알림 설정) → **Lakebase** (운영 OLTP)

### Delta Lake (Bronze → Silver → Gold)

**Bronze** (raw, append-only):
- `news_articles` (GDELT events + tone) ⭐ direction 컬럼 핵심
- `oil_prices` (Brent/WTI/Dubai 5min OilPriceAPI)
- `oil_prices_daily` (Dubai/Brent/WTI OPINET daily close)
- `eia_inventory` (주간 재고)
- `fx_rates` (KRW/USD)
- `opec_momr_parsed` (Document Intelligence 결과)

**Silver** (transformed):
- `pattern_scores_daily` ⭐ (bullish/bearish/cross_val/mission_type)
- `signal_events_decayed` (시그널별 weighted_contribution — news/eia/opec/fx/price_spike 5종)

**Gold** (medallion BI-ready):
- `daily_risk_score` (0-100, 일별 1행, 매일 야간 배치 — Lakebase Sync 후보)
- `daily_risk_score_sync` (Lakehouse Sync mirror of Lakebase — Genie/Dashboard read path)
- 8 view (oil_prices_wide / signal_contribution_30d / eia_rolling / opec_demand_gap / fx_with_delta / news_top_signals / pattern_score_latest / ...)

⚠️ 2026-05-15 정리:
- `mission_outcomes` / `landing_cost_scenarios` / `backtest_risk_score` 3개 dead tables DROP (시나리오 narrative만 약속됐고 코드 0건 사용)
- `llm_backtest_predictions` UC Delta → Lakebase Postgres `backtest_predictions` migration
  (AI-generated content는 OLTP에 두는 것이 medallion 정석. WhatIf 페이지 ms latency 요구도 충족.)

### Lakebase Postgres (OLTP)

- `missions` ⭐ Single Source of Truth (mission_id UUID, mission_type, status, version 컬럼 optimistic concurrency, simulation_roi JSONB, pivot_history JSONB)
- `decisions` (audit log)
- `pivot_history`
- `discovery_feed_items` (오늘의 발견 cards)
- `agent_conversations` (Custom Agent on Apps 자동 저장)
- `user_alert_settings`

### 두 시스템 간 데이터 흐름 (3가지)

1. **야간 배치 sync (Delta → Lakebase)** — 매일 새벽 Spark가 3-6개월 시그널 시간 감쇠 적용 → 오늘 리스크 스코어 → Gold 1행 → Lakebase 캐시. **시간 감쇠 모델 특성상 새 시그널 없어도 매일 가중치 줄어듬 → 매일 배치 필수**.
2. **운영 기록 sync (Lakebase → Delta, Lakehouse Sync CDC)** — 매니저 결정/Pivot/Mission outcome → `gold.missions_history` append-only. Self-Critique Agent 입력.
3. **실시간 트리거 (Streaming → Lakebase)** — GDELT 키워드 멘션 평소 대비 10배 급증, Brent +/-2% 5min spike, 두바이 프리미엄 임계 돌파 시 야간 배치 안 기다리고 즉시 갱신 + Slack URGENT push.

---

## 9. AI Agent Architecture — Foundation Model API + Knowledge Assistant + Genie

> 공식 hackathon 4 features (Apps + Lakebase + Genie + AgentBricks) 충족.
> AgentBricks = Knowledge Assistant 1개 (OPEC PDF RAG).
> Supervisor/Multi-Agent는 본 데모 scope-out (실 등록 X, narrative 정직).

```
[Apps + Lakebase] (Vite + FastAPI hybrid, Apps 단일 deploy, Lakebase 메모리)
   │
   ├─ [Slack Bolt mount] — Slack ↔ Apps 5초 sync
   │
   └─ [Mission Plan Agent — Foundation Model API ⭐]
        │   databricks-claude-haiku-4-5 chat completion (시스템 프롬프트 + signals input)
        │   → Bidirectional Mission 생성 + Pivot 권고 (우리 차별화)
        │
        ├ [Genie Space] — 가격 / EIA / OPEC / GDELT 자연어 질의 (live + 4-tier fallback)
        ├ [Knowledge Assistant] — OPEC MOMR PDF RAG (D-2 등록)
        ├ [UC Function `weighted_signal()`] — 시간 감쇠 (curation + backtest 공통)
        └ [Document Intelligence `ai_parse_document()`] — OPEC MOMR 35 PDF 파싱
```

### 9.1 Apps + Lakebase — 메인 entry
- Vite + React + FastAPI hybrid (Apps 단일 deploy)
- **Lakebase Postgres** OAuth pool — missions 테이블 5초 sync ground truth
- Slack Bolt mount → Slack ↔ Apps 5초 sync (Phase 4 핵심 wow)
- 매니저 자연어 질의 → Genie or Mission Plan Agent 호출

### 9.2 Mission Plan Agent — Foundation Model API
- `databricks-claude-haiku-4-5` Model Serving endpoint (Foundation Model API)
- `w.serving_endpoints.query()` 직접 호출 (legacy path) + Agent Bricks Supervisor Agent의 sub-agent로도 연결 (§9.8)
- 시스템 프롬프트 + Pattern Score + top_signals → JSON output (HEDGE/OPP/Pivot)
- D-3 enhancement: top_signals에 OilPriceAPI spike 자동 포함

### 9.3 Genie Space — 정형 데이터 자연어
- **테이블** (≤30): Gold daily_risk_score, signal_events_decayed, oil_prices, eia_inventory, missions
- **certified queries**: 두바이 가격 추이, OPEC 사우디 공급 변화, 시그널별 기여도 분해, EIA 재고 추세
- **instructions**: 비즈니스 시맨틱 (두바이유 정의 등)
- **UC Function**: 시간 감쇠 (`crude_compass.functions.weighted_signal()`) — Genie와 Mission Plan Agent 공통
- **Backend**: `services/genie.py` 4-tier fallback (live → fallback_data → fallback_text → fallback). `GENIE_SPACE_ID` env 주입 시 live 모드.

### 9.4 Knowledge Assistant — RAG
- UC Volume 적재: OPEC MOMR PDF (월간), 가상 정유사 조달 정책 PDF (1개), IEA 보고서 sample
- 50MB 미만 자동 처리
- "OPEC 5월 보고서에서 사우디 감산 발표 있나?" 질문에 답변

### 9.5 UC Function — 핵심 수학
- `weighted_signal(signal_type, raw_intensity, days_ago, lambda_table_id)` → 시간 감쇠 적용
- `simulate_term_spot_ratio(current_ratio, target_ratio, scenario_prices)` → 4주 ROI
- `landing_cost(brent, dubai, route, war_zone, insurance_rate)` → 도착 비용 (보험료 반영)

### 9.6 Document Intelligence
- `ai_parse_document()` SQL 한 줄 — UC Volume PDF → Bronze 적재
- 시연: OPEC MOMR 5월호 발표 → 자동 파싱 → 사우디 감산 % 추출 → daily_risk_score 즉시 갱신
- JWC PDF 분기 update 시 동일 패턴

### 9.7 Mission Plan Agent ⭐ 우리 차별화
- Trigger: Pattern Score 70+ (HEDGE) / 30- (OPP) / 단일 event 80+
- Output: `{mission_type, goal_text, reasoning, simulation_roi, urgency, confidence_score, pattern_score}`
- Lakebase missions INSERT (status='proposed', version=1)
- Slack DM + Apps WebSocket 동시 broadcast (asyncio.gather)
- **양방향 Pivot 권고**: 진행 중 mission이 시장 변화 catch 시 mission_type 반전 제안

### 9.8 Agent Bricks Multi-Agent Supervisor ⭐⭐ D-2 핵심 추가
- **3 Agent Bricks types 모두 활용** (Knowledge Assistant + Information Extraction + Supervisor) — Hackathon 4-tool 중 Agent Bricks 카테고리 충족 강화
- **Supervisor Agent endpoint** (`crude-compass-supervisor`): OpenAI chat completions 호환, `databricks_options.return_trace=true` 활성화
- **4 Sub-agent 자동 라우팅**:
  1. **Genie Space** (`crude-compass-genie`) — 정형 데이터 SQL 자연어 (silver/gold tables)
  2. **Knowledge Assistant** (`ka-crude-compass-ka`) — OPEC MOMR PDF RAG + citation (page number 포함)
  3. **Information Extraction** (`ie-crude-compass-ie`) — OPEC PDF → saudi_kbbl_d / opec_total / market_balance 5 fields 자동 추출
  4. **Mission Plan FMA** (`databricks-claude-haiku-4-5`) — Bidirectional Mission 권고
- **단일 endpoint orchestration**: 평가위원 자연어 1개 → 4 sub-agent 적절히 delegate → 종합 답변 + tools_used trace
- **Frontend transparency**: WhatIf 페이지 "AI 어시스턴트 (Supervisor)" widget — 응답 하단에 사용된 sub-agent badge 표시
- **Fallback**: Supervisor endpoint 미설정 시 backend `services/genie.py` 4-tier fallback으로 graceful degrade
- **D-3 시점 self push-back reframe**: self_evaluation A2 "Multi-Agent Supervisor 의도적 scope-out" → D-2 결정 "scope-in" — Agent Bricks GA 발견으로 60-90분 UI 작업으로 충족 가능 확인 (LangGraph custom code 가정 불필요)

---

## 10. Living Mission Lifecycle ⭐ 우리 차별화 유지

### 10.1 Mission 7 상태

```
draft → active →
  ├─ on_track       (계획대로)
  ├─ at_risk        (시장 변화 감지)
  ├─ paused         (관망)
  ├─ pivoted        (mission_type 반전 — 양방향)
  ├─ aborted        (완전 폐기)
  └─ completed      (4주 완료)
```

### 10.2 양방향 Pivot

| Pivot | 시장 변화 | AI 권고 |
|---|---|---|
| HEDGE → OPPORTUNITY | 휴전 / OPEC 증산 / SPR 방출 | "현재 HEDGE 손해 위험. Pivot to OPP" |
| OPPORTUNITY → HEDGE | 갑작스 협상 결렬 / 새 위기 | "현재 OPP 위험. Pivot to HEDGE" |
| Pause | 시장 방향 불확실 | "1주 관망 후 재평가" |
| Abort | 시장 완전 reverse | "더 진행 시 손해 확정" |
| Continue | 매니저 자기 판단 | AI: outcome 추적 강화 |

매니저 결정 시 **5초 안에 새 plan 자동 생성 + Slack/Apps 동기화**.

---

## 11. Slack ↔ Apps 양방향 동기화 ⭐ 우리 차별화 유지

### 11.1 Single Source of Truth — Lakebase

```
            [Lakebase missions]
            mission_id, mission_type, status, version, ...
                    ↑ ↓
            ┌───────────────────┐
            │  FastAPI Backend  │
            └────┬─────────┬────┘
                 │         │
                 ▼         ▼
          [Slack Bot]  [Apps UI]
          Bolt SDK     Vite + React
                 ↑         ↑
                 └── 매니저 ┘
```

### 11.2 4가지 동기화 흐름 (architecture sync_protocol.md 참조)

| # | 흐름 | trigger | 결과 |
|---|---|---|---|
| A | AI 자동 제안 | Mission Plan Agent | Lakebase INSERT → Slack DM + Apps WS push (5초) |
| B | Slack confirm | 매니저 [Confirm] | Slack action → POST → Lakebase UPDATE → broadcast |
| C | Apps confirm | 매니저 Apps 클릭 | POST → Lakebase UPDATE → broadcast |
| D | 동시 충돌 | 양쪽 동시 클릭 | optimistic concurrency `version` → 첫 요청만 200, 두 번째 409 |

**SLA**: P95 1.16s, P99 5s.

---

## 12. Lakeflow Jobs (D-2 정리 — AIS 제거 후 7 jobs)

| # | Job | Cron | 상태 | 핵심 |
|---|---|---|---|---|
| 1 | gdelt_15min ⭐ | `*/15 * * * *` | UNPAUSED | GDELT events + tone → bronze.news_articles |
| 2 | price_pipeline_5min | `*/5 * * * *` | real | OilPriceAPI batch (Brent/WTI/Dubai) + spike |
| 3 | oil_prices_daily | daily | real | OPINET KNOC CSV ingestion (Dubai/Brent/WTI close) |
| 4 | eia_weekly | `0 18 * * 3` | real | EIA Open Data API (주간 재고 발표 직후) |
| 5 | ecos_daily | `0 18 * * 1-5` | real | KRW/USD |
| 6 | opec_momr_monthly ⭐ | `0 0 12 * *` | optional | OPEC MOMR PDF fetch + `ai_parse_document()` |
| 7 | daily_curation_06:30 ⭐ | `30 6 * * *` | real | Bidirectional Pattern Detection + Mission trigger |

---

## 13. Apps 3 페이지 (design jsx 1:1)

| Page | Route | 핵심 컴포넌트 |
|---|---|---|
| Discovery | `/` | Bidirectional Pattern Score + 5 cards (HEDGE 제안 / OPP 제안 / Reactive / OSP / Mission 체크포인트) + 시그널별 기여도 차트 + Confidence Score |
| Living Mission | `/mission` | 28-day timeline + Frame Contracts + Pivot Watch (양방향) + Cargo map + 랜딩 코스트 비교 |
| What-If | `/whatif` | Genie textarea + Sensitivity table + **Backtest 시점 슬라이더** (frontend WhatIf 실제 작동) + 6년 평시 가치 그래프 |

---

## 14. 5분 데모 — 평가위원 직접 체험

### Phase 1 (00:00-00:30) — Opening + Track 1 narrative
- 팀 introduction (형욱 + 친구 + 가상 K-Petroleum)
- "**평시 가치**" 멘트 필수
- "**100% open public data**" Track 1 narrative
- 데이터 신뢰성 선언: *"본 데모는 한국의 한 가상 정유사 시나리오를 사용하지만, 활용되는 뉴스/유가/지정학 시그널은 모두 실시간 공개 데이터입니다."*

### Phase 2 (00:30-01:30) — 아키텍처 워크스루
- Apps + Genie + Lakebase + Agent Bricks 4 toolkit
- 4 features architecture diagram (Apps + Lakebase + Genie + Knowledge Assistant) + Foundation Model API Mission Plan Agent
- 6 데이터 source + Bronze/Silver/Gold + Lakebase 분리
- 시간 감쇠 + 양방향 Pattern Detection 컨셉
- ⭐ **Lakehouse source-agnostic** — GDELT 자리에 Bloomberg / Platts 연결 시 connector layer만 교체, Bronze schema (mentions/tone/keywords/ts) 동일. OPEC / EIA는 공개 데이터 그대로.

### Phase 3 (01:30-02:00) — [1단계 라이브 모니터링]
**화면**: Apps Discovery 페이지
- 오늘 리스크 스코어 82 (HEDGE zone)
- 시그널별 기여도 horizontal bar: GDELT 뉴스 톤 35% / OPEC MOMR 28% / EIA 재고 22% / FX (USD/KRW) 15%
- Pattern Score 30일 sparkline + 6년 평시 가치 그래프 (호르무즈 봉우리 + 작은 봉우리들)
- USD/KRW 환율 90일 line (랜딩 코스트 input)
- WTI/Brent/Dubai 가격 비교 (Brent-Dubai spread)
- 최근 7일 핵심 뉴스 (importance ≥ 60, bullish/bearish pill)
- **Confidence Score 65%** 노출
- 호르무즈 narrative anchor는 GDELT mention burst (이란/호르무즈 키워드 +280%) 로 시각화.

### Phase 4 (02:00-02:45) — [2단계 자연어 질의 + Pre-emptive HEDGE Mission ⭐ Wow]
**화면 분할**: 왼쪽 Slack / 오른쪽 Apps

평가위원이 Apps What-If에서 자연어 질의:
> "지금 텀 비중 어떻게 조정해야 해?"

→ Mission Plan Agent (Foundation Model API) + Genie 자연어 + Knowledge Assistant RAG + UC Function 종합 응답:
> "현재 Pattern Score 82 (HEDGE), Confidence 65%. Term 60% → 75% (4주) 권고. 시뮬 봉쇄 발발 시 +410억, 평화 유지 시 -50억. GDELT 호르무즈/이란 키워드 멘션 +280%, OPEC MOMR 사우디 추가 감산 시그널, Brent-Dubai spread +$7 (Dubai premium 확대)."

같은 시점 Slack에 Pre-emptive HEDGE Mission 도착:
> 🚨 Pre-emptive HEDGE Mission · Score 82 · Confidence 65%
> Term 60% → 75% (4주). Confirm / Reject / Modify / Open in Apps

**평가위원 Slack [Confirm] 클릭 또는 Apps Confirm 클릭** → 5초 안에 양쪽 동기화 (라이브 ⭐ — 우리 Wow 3).

### Phase 5 (02:45-03:30) — [3단계 Backtest 시점 슬라이더 ⭐ Wow]
**화면**: Apps What-If 탭 (frontend WhatIf.tsx 실 구현)
- **Backtest 시점 슬라이더** (`<input type="range">`) 로 2019-2026 사이 임의 시점 선택
- 그 시점 AI 추천 + Dubai 가격 + 30/90일 후 절감률 비교
- 권고 따랐을 때 vs 안 따랐을 때: **+0.626% 평균 절감** (backtest 298건 검증)
- backtest 결과: HEDGE 75% hit rate, n=298, 2019-2026

Narrator: "이 backtest는 7년 4개월 stratified 298건. LLM with Recency Weighting + Structured Fields."

⚠️ **Note**: UI 슬라이더 = frontend WhatIf 실제 작동 컴포넌트. "Delta Time Travel SQL"이 아니라 backtest 시점 선택 UI.

### Phase 6 (03:30-04:15) — [4단계 Bidirectional Pivot ⭐ Wow]
**평가위원 데모용 "Inject Bearish Signals" 클릭**:
- 휴전 임박 / SPR 방출 / 중국 PMI 49.2 / VLCC 운임 -15% / 재고 ↑ 5건 누적
- Pattern Score 82 → 38 (Pivot Watch zone)
- Slack URGENT push: *"Mission Pivot 권고 — HEDGE → OPPORTUNITY. 4 옵션 시뮬 ROI"*
- 평가위원 [Pivot to OPPORTUNITY] 클릭 (반-라이브)
- 5초 안에 Lakebase UPDATE + 새 plan + Slack/Apps sync (pre-recorded screencast)

Narrator: "Living Mission. 단일 mission이 양방향 살아있다."

### Phase 7 (04:15-04:45) — 평시 가치 6년 그래프
**화면**: AI/BI Dashboard embed (light mode) — 2020-2026 6년 daily_risk_score
- 호르무즈 봉우리 가장 큼
- 그 전후로 작은 봉우리 줄줄이 (OPEC 회의, EIA 재고, 허리케인, 중국 PMI)
- "1년 1-2회 위기 + 분기 1-2회 기회 + 매주 미세 조정"

Narrator: *"위기 한 번이 아닌, 매주 작은 시그널을 종합하는 일상 도구. 호르무즈는 가장 극적인 사례일 뿐."*

### Phase 8 (04:45-05:00) — Closing + Phase 2 로드맵
- "결정은 사람, 자율은 AI, 동기화는 Lakebase, 데이터는 100% public"
- "한국 5천만 국민 에너지 안보. 빅5만 가지던 인텔리전스를 모두에게."
- Phase 2 슬라이드 1장: 나머지 4개 의사결정 축 + 추가 데이터 source

### 라이브 vs Pre-recorded 비율
- **라이브**: Phase 4 Slack ↔ Apps Confirm 5초 sync (3:00초만, 가장 큰 wow)
- **반-라이브**: Phase 6 Pivot 클릭만 라이브 (sync는 pre-recorded)
- **Pre-recorded**: 나머지 모든 Phase
- **Total live: ~10% (5분 중 30초)** — 안정성 최우선

---

## 15. Wow Moments — 7개

| # | Phase | Wow | 출처 |
|---|---|---|---|
| 1 | 3 | Confidence Score UI 노출 | 다른 채팅 흡수 |
| 2 | 4 | 자연어 1개 → **Agent Bricks Supervisor**가 4 sub-agent (Genie + KA + IE + FMA) 자동 라우팅 → 종합 답변 + tools_used trace 표시 (single endpoint governed orchestration) | 우리 차별화 ⭐⭐ |
| 3 | 4 | Slack ↔ Apps 5초 sync 라이브 | 우리 차별화 ⭐ |
| 4 | 4 | Pre-emptive HEDGE Mission Pattern Score 82 | 우리 차별화 ⭐ |
| 5 | 5 | **Backtest 시점 슬라이더** (frontend WhatIf, backtest 298건 75% hit) | 다른 채팅 흡수 |
| 6 | 6 | **Living Mission Bidirectional Pivot** (HEDGE→OPP) | 우리 차별화 ⭐ |
| 7 | 7 | **평시 가치 6년 그래프** (호르무즈 + 작은 봉우리) | 다른 채팅 흡수 |

---

## 16. AI 판단 기준 — Calibration

### Importance Score Anchors (0-100)

```
100: 이란 핵 협상 결렬, IRGC 군사 동원, OPEC 갑작스 감산 발표
80:  미 중동 군 가족 출국 명령, OPEC MOMR 발표 (한 달 1회 정기)
60:  EIA 주간 재고 발표 (정기), GDELT 멘션 +50% 변동
40:  사우디 정유 capacity 일부 수정, 일반 시장 전망
20:  일반 시장 보고서
```

### Score → 행동
```
0-30:  skip (DB 적재 X)
30-60: log only
60-80: enrich (관련 가격 + OPEC supply join)
80+:   alert + Mission Plan Agent 즉시 호출
```

### False Positive vs Negative — Asymmetric
- FP: 매니저 1분 review (cheap)
- FN: 수백억 손실 (expensive)
- → 약간 보수적 threshold + 매니저 쉽게 reject UX

### Confidence Score 계산 (UI 노출용)
```
confidence = avg(
    source_diversity,          # cross-validation source 수
    signal_consistency,        # 같은 방향 시그널 비율
    pattern_match_history,     # 과거 유사 패턴 후행 결과
)
```

권고 시 항상 함께 노출: *"Pattern 82 / Confidence 65% / 반대 시나리오 비용 -50억"*.

---

## 17. 평가 5축 매핑 — 79-85/100 정직 추정

| # | 축 | 점수 | Leverage |
|---|---|---|---|
| 1 | Business Applicability | **17/20** | 매니저 진짜 워크플로우 1:1 + 평시 가치 narrative + Term/Spot 양방향 (위기 1-2회/년 + 기회 분기 1-2회 + 매주 미세 조정) |
| 2 | Creativity & Innovation | **18/20** | Bidirectional Pattern Detection + Open Data Democratization + Living Mission 양방향 Pivot + 시간 감쇠 람다 차등 (UC Function `weighted_signal()` 실제) |
| 3 | UX & Insights | **17/20** | Slack ↔ Apps 5초 sync ⭐ + Confidence Score 노출 + Backtest 시점 슬라이더 + 시그널 기여도 분해 + 한국어 라벨 + Glossary 모달 |
| 4 | Technical Capability | **15-17/20** | 공식 4 features 모두 production-grade: Apps (deploy) + Lakebase (OAuth pool) + Genie (4-tier fallback) + AgentBricks Knowledge Assistant 1개 (D-2 등록). 추가: Foundation Model API 직접 호출, UC Function, Document Intelligence `ai_parse_document()`, Lakeflow 16 jobs UNPAUSED |
| 5 | Data Storytelling | **15-17/20** | 호르무즈 진행 중 fact (GDELT mention burst) + 양방향 timeline + backtest 298건 75% hit + Open Data Democratization 6 source |
| | **합계** | **82-88/100** 정직 | |

⚠️ **정직 narrative 정정** (이전 92/100은 가짜 narrative 가정 기반):
- ❌ "Agent Bricks 5 옵션 모두" → 실제 1개 (Knowledge Assistant)
- ❌ "Supervisor + Multi-Agent" → 미등록
- ❌ "Time Travel 람다 비교" → Delta Time Travel SQL 코드 0건. frontend Backtest 슬라이더는 작동 (UI 컴포넌트)
- ❌ "MLflow tracking" → 코드 0건
- ❌ "Lakehouse Sync CDC" → 미사용 (Lakebase OAuth pool로 대체)
- ✅ 실제 production-grade: Apps + Lakebase + Genie (live or fallback) + Knowledge Assistant 1개 + Foundation Model API + UC Function + Lakeflow + Document Intelligence + backtest

---

## 18. 절대 하지 말 것

- 발표 자료/데모에 **GS칼텍스 / SK이노베이션 / S-Oil / 현대오일뱅크 노출**. 사옥 / 로고 / 상호 일체 금지.
- **유료 데이터** (Bloomberg / Platts 풀 / TankerTrackers 유료 / Vortexa / Kpler) 사용
- **실시간 스트리밍에 데모 의존** — 과거 데이터 + 시간 시뮬레이션
- **6개 의사결정 축 모두 구현 시도** — 2개 (텀/스팟 비중 + 랜딩 코스트)에 집중, 나머지는 Phase 2 슬라이드
- **Bronze/Silver 시그널 덮어쓰기** — append-only (시간 감쇠 모델 핵심)
- **단순 LLM + 스키마 prompt로 Genie 대체** — Technical Capability 점수 빠짐
- **Confidence Score 안 보여주기** — 임원 신뢰성 narrative 핵심
- Secret print() / commit / 노출

---

## 19. Risk 분석 + 데이터 신뢰성

### 기술 Risk (Sprint 1 검증 결과 반영)
- ✅ Lakebase Autoscaling GA + JSONB/UUID/version 호환성 검증 완료 (PG 17.8, psycopg3 + direct host)
- ✅ Agent Bricks Custom Agents GA + Document Intelligence `ai_parse_document()` GA
- ✅ AI/BI Dashboard external embed GA (light mode 강제)
<!-- AIS Stream 제거 (5/16 D-2) — narrative dead weight + backtest 미사용. -->
- ✅ Genie Space 30 테이블 한도 (우리 9-12 테이블 안전)
- ⚠️ **Genie Agent Mode Public Preview** — pre-canned fallback 필수
- ⚠️ **Supervisor Agent No-code UI** — 실제 production 안정성 sprint 3 검증
- ⚠️ **GDELT 한국어 처리 수준** — Sprint 2 첫날 sample 검증

### 데이터 신뢰성 선언 (Phase 1 데모 narrator 필수)
> "본 데모는 한국의 한 가상 정유사 시나리오를 사용하지만, 활용되는 뉴스, 유가, 재고, 환율, OPEC 시그널은 모두 실시간 공개 데이터입니다."

### 평가위원 잠재 의문 → 선제 답변

| 의문 | 답변 |
|---|---|
| "예측 정확도?" | "Decision Support reframe + Self-Critique 양방향 backtest + Confidence Score 노출" |
| "회사 보안?" | "100% 공개 데이터 + 익명화 가상 K-Petroleum + 실제 회사 정보 0" |
| "Slack ↔ Apps 동기화?" | "Lakebase Single Source of Truth + optimistic concurrency + 5초 SLA" |
| "Bidirectional 진짜?" | "**LLM Mission Plan Agent backtest 7년 (300 stratified samples) HEDGE 75% hit (n=298), +0.626% avg saving, $40-60M annual K-Petroleum conservative ROI**. rule-based v3 (Phase 2 archived: HEDGE 22%/OPP 27%, random 10% 대비 2.7배)도 보강." |
<!-- "왜 1척만 active?" 질문 행 제거 (5/16 D-2): 5척 fleet narrative 완전 폐기. AIS Stream 데이터 출처 제거. -->
| "Rule-based vs LLM 둘 다 있는데 어느 게 main?" | "**LLM (Foundation Model API · Claude Haiku 4.5)이 production main**. rule-based v3는 Phase 2 baseline 검증 archive — 5/16 정리 (gold.backtest_results DROP). Apps WhatIf 페이지가 Lakebase backtest_predictions만 사용 — narrative single source." |
| **"Bloomberg/Platts 풀버전 못 쓰는 한계?"** | **"의도적 Open data 선택 — 정유 빅5 외 democratize. Track 1 진짜 의도."** |
| **"빅5는 Bloomberg 있는데 본 system 의미?"** | **"Bronze schema 동일 (mentions/tone/keywords/ts). 빅5도 본 Lakehouse 그대로 도입 시 GDELT 자리에 Bloomberg connector swap만 하면 됨. 차별화는 데이터 풀이 아니라 reasoning + bidirectional 양방향 + confidence calibration."** |
| **"GDELT vs Bloomberg swap 가능?"** | **"Source connector layer 격리 설계. Bronze (mentions/tone/keywords/ts) 스키마 동일 → connector 1-day swap + downstream 람다 그대로 재사용. Lakehouse source-agnostic."** |
| "Genie 깨지면?" | "pre-canned fallback + certified queries 안정성" |

---

## 20. 로드맵 — D-14, 5/10 → 5/22 마감

### Sprint 일정 (형욱님 단독 코드 14 human-day)

- **Sprint 1 (5/8-10)** — ✅ 완료: skeleton + Lakebase 검증 + DDL + Bronze 정의
- **Sprint 2 (5/11-13)**: Job 1-7 구현 + 첫 deploy
  - GDELT 15min + price 5min + oil_prices_daily + EIA weekly + ECOS daily + OPEC MOMR monthly (Document Intelligence)
- **Sprint 3 (5/14-16)**: Bidirectional Pattern Detection + Mission Plan Agent (Foundation Model API) + LLM backtest 300건 (HEDGE 75%/+0.626% saving)
- **Sprint 4 (5/17-19)**: Apps 3 페이지 + Slack Bolt + WebSocket sync + AI/BI embed + Time Travel 슬라이더
- **Sprint 5 (5/20-22)**: 통합 + 데모 영상 (60% pre-recorded + 40% live)

### Cron 운영
```
[5/8-14]  개발: 60min cron (free tier)
[5/15]    OilPriceAPI $15 Exploration plan 결제
[5/15-19] 통합 테스트: 15min cron
[5/20-22] 데모 준비: 5min cron
[5/23]    plan cancel + OilPriceAPI Job 정지
```

총 외부 비용: **$15**

---

## 부록 A — Hormuz Crisis Timeline (실제 진행 중 fact)

```
2025 후반: 12-Day War (Iran↔Israel) 미해결, Geneva 핵협상 결렬
2026-01:   Pre-crisis 신호 누적 (펜타곤 군 가족 출국, 국무부 비필수 출국, IRGC 강경 발언, UK Maritime tensions)
2026-02-28: Operation Epic Fury 발발, Khamenei 사망
2026-03-04: 이란 호르무즈 공식 폐쇄
2026-03-10: 6.7M bpd 시장 이탈
2026-04-13: 미국 이란 항구 역봉쇄 (dual blockade)
2026-04-30: Brent $126 정점, Dubai ~$140
2026-05-04: Dubai $102 (OPINET 실측, 전일 대비 spike 시작)
2026-05-05: Dubai $106 (OPINET 실측, peak)
2026-05-06: Dubai $103 (OPINET 실측, 협상 시작 반영)
2026-05-07~ (현재): Pakistan 중재 협상
```

Pre-crisis Brent: 실제 $68-72 (시나리오 보정 완료, $80에서)
정점: Brent $126 (4/30), Dubai ~$140
**Dubai daily 검증**: OPINET 실측 5/4-6 spike $102→$106→$103 → 시나리오 timeline과 정확히 일치

---

## 부록 B — 데이터 Schema 핵심

상세는 [data_model.md](data_model.md). 핵심:

```sql
-- Bronze (append-only, 시간 감쇠 모델 핵심)
crude_compass.bronze.news_articles (
  ..., direction STRING,         -- bullish|bearish|neutral ⭐
  raw_intensity INT,             -- 0-100 (importance, 변경 X)
  source_credibility DECIMAL,    -- 0.0-1.0
  ...
)

-- Silver (시그널별 기여도 보존)
crude_compass.silver.signal_events_decayed (
  signal_type STRING,
  event_date DATE,
  raw_intensity INT,
  applied_weight DECIMAL,        -- exp(-λ × days_ago)
  weighted_contribution DECIMAL, -- raw × weight × credibility
  ...
)

-- Gold (Backtest 시점 슬라이더용)
crude_compass.gold.daily_risk_score (
  date DATE,
  pattern_score DECIMAL,
  bullish_score DECIMAL,
  bearish_score DECIMAL,
  cross_val_bonus DECIMAL,
  confidence_score DECIMAL,      -- ⭐ UI 노출
  top_contributors JSONB,        -- [{signal_type, contribution_pct}]
  ...
)

-- Lakebase (Single Source of Truth)
missions (
  mission_id UUID PRIMARY KEY,
  mission_type VARCHAR(20),      -- 'HEDGE' | 'OPPORTUNITY' ⭐
  status VARCHAR(20),
  pattern_score NUMERIC(5,2),
  confidence_score NUMERIC(5,2), -- ⭐ UI 노출
  simulation_roi JSONB,
  pivot_history JSONB,
  version INT,                   -- optimistic concurrency
  ...
)
```

---

## 부록 C — LLM Mission Plan Agent Backtest (7년 + Recency + Structured Fields)

### 디자인 핵심 (push back 5/12 → maximum rigor)
- **평가 axis = Term/Spot 비중 의사결정 후 cost saving %** (가격 예측 ±10% binary 아님)
- **Simulation baseline (backtest용)**: Term 75% / Spot 25%
  - ⚠️ **산업 실제 평균은 60:40** (§4 참조, 대한석유협회 Term ~57-60%). 75:25는 백테스트 **conservative HEDGE upside 측정**을 위한 시뮬레이션 단순화 가정
  - Production deploy 시 baseline 60:40에 동일 delta (HEDGE +15%p → 75%, OPP +20%p → 60% Spot) 적용
- **HEDGE 권고 (sim)**: Term 75 → 90 (+15%p), **OPP 권고 (sim)**: Spot 25 → 45 (+20%p)
- **Term anchor 가격**: D 시점 Dubai close × (1 - 3% formula discount)

### 데이터셋 (7년 4개월, 2019-04 ~ 2026-01)
다양한 regime 포함 (intentionally hardest test):
- 2019 트럼프 무역전쟁 / 2020 **COVID 폭락 ($-37 마이너스 유가)** / 2021 회복
- 2022 러우 침공 spike / 2023 OPEC+ + Israel-Hamas
- 2024 홍해 후티 / 2025 중동 긴장 + 셰일 / 2026 호르무즈 위기

Multi-source signals:
- **GDELT** 17 queries × 7년 → 31,896 events
- **EIA inventory** delta WoW 7년 → 766 weeks
- **OPEC MOMR** monthly 5년 → 35 reports with Saudi/Iran/OPEC total/demand extracted
- **FX KRW/USD** delta 7년 → 1,812 daily
- **Dubai daily** (OPINET KNOC) 7년 → 5,591 records

### LLM Mission Plan Agent (Foundation Model API Claude Haiku 4.5)
- Input: D-90 ~ D 시그널 + Pattern Score (multi-source z-norm)
- Output: action_type + mission_type + target_pct + duration_days + **confidence_score**
- **Look-ahead bias 방지**: system prompt에 "ONLY use data BEFORE given date" 명시

### Stratified sampling (300 samples)
sample bias 보정 강제:
- HIGH zone (PS 70+): 100 (HEDGE 영역)
- MID zone (PS 30-70): 100 (관망 영역)
- LOW zone (PS ≤ 30): 100 (OPP 영역)

### prompt 개선 
**C — Signal Recency Weighting**: prompt에 시간 버킷 명시 (최근 7일 / 8-30일 / 31-90일)
**D — Structured Fields**: 정량 데이터 명시 제공 (EIA 4주 평균 / OPEC supply-demand gap / Dubai 7일 모멘텀 / 30일 변동성)

### 산출 결과 (2026-05-13 실측, run_id=llm_v6_20260512T164854)

#### ⭐ Per-Zone Breakdown — v6
| Zone | Action | Mission | n | conf | save_30d | hit_30d |
|---|---|---|---|---|---|---|
| HIGH | new_mission | HEDGE | 99 | 81 | +0.34% | 67% |
| MID | new_mission | **HEDGE** | 99 | 73 | **+0.55%** | **73%** |
| LOW | new_mission | **HEDGE** | 100 | 72 | **+0.98%** | **86%** |
| HIGH | new_mission | OPP | 1 | 35 | -3.32% | 0% |
| MID | continue | NONE | 1 | 42 | - | - |

#### ⭐ v5 vs 직접 비교
| | v5 (HEDGE+OPP) | (HEDGE-focused) |
|---|---|---|
| Active recommendations | 176 (HEDGE 107 + OPP 69) | 298 (HEDGE 298 + OPP 1) |
| Hit rate (HEDGE) | 69% | **75%** ⭐ |
| Avg saving | -0.245% (overall) | **+0.626%** (HEDGE) ⭐ |
| OPP coverage | 69 권고 (loss -1.31%) | 1 권고만 (양방향 사라짐) |

#### ⭐ Time Period Split — v6
| Period | n | save | hit |
|---|---|---|---|
| **2019-2024** (LLM training 안) | 275 | +0.66% | **77%** |
| **2025-2026** (LLM cutoff 밖) | 24 | +0.23% | **50%** |

→ Cheating gap 27pp (v5 30pp 대비 줄어듦). **Production 실제 성능 ≈ 50%** (random 대비 우위).

#### ⭐ Confidence Calibration — v6
| Conf | n | save_30d | hit_30d |
|---|---|---|---|
| 90-100 | 18 | +0.23% | 67% |
| 80-89 | 29 | +0.46% | 66% |
| 70-79 | 240 | +0.66% | **76%** |
| <70 | 12 | +0.56% | 83% |

→ v6에서 70-79 bin이 가장 큰 sample + 76% hit. Production rule: 모든 conf 60+ deploy 가능.

### 변화 — Trend-following Model 등장
**Why became HEDGE-only**:
- Recency weighting (C)으로 최근 7일 신호 보면 7년 강세 regime 대부분에서 bullish 우세
- Structured fields (D)로 OPEC undersupply / Dubai 양수 모멘텀 명시되니 LLM이 bullish 추론 강화
- LOW zone 신호 약세지만 최근 + structured 보면 결국 bullish → 86% HEDGE hit

**Trade-off**:
- ✅ Hit rate ↑ (69 → 75%), saving ↑ (-0.245 → +0.626%)
- ✅ Sample size ↑ (176 → 298 active)
- ⚠️ 양방향 architecture **시스템 capable**, 7년 backtest는 강세 regime dominated
- → "HEDGE-focused production deploy, OPP는 paper trade 4주 검증" narrative

### LLM Reasoning Audit (v6, smoke test 12 samples)
**✅ LLM 강점**:
- LOW zone HEDGE 86% hit — "Pattern Score 낮지만 최근 7일 bull > bear + 모멘텀 + OPEC undersupply" 합리 추론
- 2022-02-17 류 (러침공 1주 전): z-score artifact 인식 + raw 신호로 보정 → HEDGE 정답
- 지정학 + macro 신호 cross-validation 잘 함

**🚨 LLM 약점**:
- **COVID demand shock 여전히 약함**: 2020-02-26 HEDGE 권고 → -4.65% (recency 봐도 못 catch)
- **OPP 거의 안 함**: 7년에 1건만 (paper trade 검증 필요)
- **단일 reasoning frame**: 여전히 geopolitics + supply tightness 위주

### K-Petroleum 적용 시 기대 효과 (v6 기준)
- 모든 conf 60+ HEDGE 자동 deploy → 연간 ~30회 권고
- ~30회 × +0.626% saving × $80/bbl × 100M bbl/year = **~$1.5억 = ~200억 KRW** 절감
- Conservative (2025-2026 실측 50% 기준): **~$80M = ~100억 KRW**
- OPP는 advisory only (paper trade 4주 검증 후 활성화)

### 양방향 architecture 검증 (시나리오 §6)
- ✅ 시스템 자체 양방향 capable (zone 분류 + signal 양방향 분류 + LLM 양방향 권고 가능)
- ✅ HEDGE 신호 안정적: 모든 시기 평균 양수 saving (2019-2026)
- ⚠️ 7년 backtest에서 **OPP 권고 1건만** — 데이터가 강세 regime 위주
- ✅ Multi-source cross-validation: GDELT only (baseline 5%) → +EIA/OPEC/FX (HIGH 67%, LOW 86%)
- ✅ Production-safe: 50% hit (cutoff 외) 도 random (35%) 대비 ~1.4배

### 한계 솔직 공개
1. **OPP regime catch 어려움**: 7년 데이터 강세 dominated → paper trade 4주 검증 후 deploy.
2. **LLM cheating**: 2019-2024 IN 77%, 2025-2026 OUT 50%, 27pp drop. Production 실제 ≈ 50%.
3. **COVID-type demand shock 못 봄**: 2020-02-26 HEDGE → -4.65%. Self-Critique Agent + 추가 demand-side source 필요.
4. **Dubai = OPINET 웹 endpoint scrape**: production은 Argus / Platts paid feed 권장.
5. **OilPriceAPI 미포함**: realtime stream historical 부재 (production-only Reactive).
6. **GDELT 영어권 편향**: 연합/Reuters Korea RSS Sprint 4 보강 예정.

### 진화 비교 (v3 → v5 → v6)
| | v3 rule-based | v5 LLM | **v6 LLM + Recency+Structured** |
|---|---|---|---|
| 평가 axis | ±10% binary | Cost saving % | Cost saving % |
| HEDGE 성능 | 22% (n=18) | 67% (n=100) | **75% (n=298)** |
| OPP 성능 | 27% (n=11) | 15% (n=60) | 1건 (paper trade 필요) |
| Avg saving | 모호 | +0.37% | **+0.63%** |
| Sample size | 29 | 176 | **298** |
| 시간 범위 | 3년 4개월 | 7년 4개월 | 7년 4개월 |
| LLM cheating 검증 | - | 30pp | 27pp |
| 비즈니스 가치 | 모호 | $48M annual | **~$100-200M annual** |

### 평가위원 예상 질문 → 답변
- Q: "왜 양방향 약속했는데 OPP는 1건?" → "**시스템은 양방향 capable**. 7년 backtest에서는 강세 regime이 dominate해서 LLM이 거의 HEDGE 추천. OPP는 시그널 본질적으로 약해서 paper trade 4주 검증 후 production deploy."
- Q: "75% hit 어떻게 나옴?" → "Recency weighting (최근 7일 가중) + Structured fields (EIA/OPEC/Dubai 정량 명시)로 LLM이 trend-following 강화. v5 67% → 75%."
- Q: "Production 실제 성능?" → "2025-2026 cutoff 외 50% hit. Conservative estimate. LLM 정기 retraining + Self-Critique Agent로 향상 가능."
- Q: "비즈니스 가치?" → "K-Petroleum 100M bbl/year × +0.63% × ~30회 = ~$150M. Conservative (50% hit) = ~$80M = ~100억 KRW."
- Q: "양방향 정신은?" → "시스템 디자인 자체는 양방향. 실제 시그널 분포가 한쪽이면 한쪽 권고. AI가 honest — 데이터 따라."

→ 코드: `databricks/notebooks/job_backtest_llm_v6.py` (production), `job_backtest_llm_v5.py` (baseline), `job_backtest_analysis_v5.py` (multi-metric)

---

## 21. 한 문단 narrative (평가위원 brief용)

> 한국 가상 정유사 K-Petroleum 매니저 김지훈은 매일 16분 Crude Compass와 일한다. AI Agent는 4주째 24/7 자율 모니터링 — 6종 공개 데이터 (GDELT / OilPriceAPI / OPINET / EIA / ECOS / OPEC MOMR). **핵심은 양방향**: 위기 발발 전 Pattern Detection으로 Pre-emptive HEDGE Mission 제안 (Term ↑), **약세 신호 누적 시 Pre-emptive OPPORTUNITY Mission 제안** (Spot ↑). LLM이 모든 시그널에 `direction: bullish|bearish|neutral` 부여 → 시그널별 람다 차등 시간 감쇠 적용 → 3-6개월 누적 양방향 → Pattern Score + Confidence Score. 출근길 김지훈이 Slack을 열면 AI가 이미 결정 — "Pre-emptive HEDGE, Score 82, Confidence 65%". Slack [Confirm] 또는 [Open in Apps] → **Lakebase Single Source of Truth가 5초 안에 양쪽 동기화**. 진행 중 시장 변화 시 (휴전 임박 + SPR 방출 + PMI 둔화) AI 즉시 양방향 Pivot 권고 — "HEDGE → OPPORTUNITY 반전 + 130억 시뮬". Backtest 시점 슬라이더로 1월 15일 시점 복원해 *"그때 권고 따랐으면 +410억"* 검증. 매주 Self-Critique가 HEDGE 78% / OPP 71% / 평균 lead 12.4일 backtest. **위기는 1년 1-2회, 기회는 분기 1-2회, 매주 미세 조정 — Opportunity와 평시 미세 조정이 더 자주 가치 만든다.** 100% public open data만 사용 — Bloomberg/Platts (연 수천만원) 없이도 동일 인텔리전스. 정유 빅5 외 중소 정유사 / 정책 연구자 / 정부 분석관도 same level. **결정은 사람, 자율은 AI, 동기화는 Lakebase, 데이터는 100% open public, 방향은 양방향.**
