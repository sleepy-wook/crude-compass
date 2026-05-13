# Crude Compass — Session Decision Log

> Purpose: 대화 핵심 압축 + 결정 rationale 보존 (compact / SA review용).
> Last updated: 2026-05-13 저녁
> Style: terse Korean, push back history 포함.

---

## 1. Project context

- **Databricks Building Intelligent Apps Hackathon 2026** (Track 1 Social Impact)
- Deadline: **5/22 final**, **5/18 22:00 KST early submit** → SA review 5/19-20 → 최종 5/22
- 팀: 형욱 (LG Innotek, code 100%) + 친구 (LG Electronics, planning/design only)
- Languge: 한국어 terse, push back 환영, 무지성 공감 X
- Databricks workspace: 형욱 owned (manual UI/deploy 본인), 코드만 AI

---

## 2. 핵심 narrative (확정)

**한 줄**: 한국 가상 정유사 K-Petroleum 사장 위한 양방향 의사결정 AI 비서. 7개 공개 source. Slack ↔ Apps 5초 sync. Term/Spot 비중 의사결정.

- baseline mix: **Term 60% / Spot 40%** (대한석유협회 통계, Term ~57-60%)
- HEDGE 권고: Term 60 → 75 (+15%p)
- OPP 권고: Spot 40 → 60 (+20%p)
- 의사결정 axis: **Landing cost saving %** (binary ±10% 아님)

---

## 3. 결정 history + rationale (push back 위주)

### Backtest 모델 진화 (v3 → v6)

| Version | 변경 | 결과 |
|---|---|---|
| v3 (rule-based) | ±10% binary precision | HEDGE 22% / OPP 27%, narrative 약함 |
| → push back: 단순 가격 예측 X, **Term vs Spot 의사결정** axis로 | | |
| v4 (LLM 100 random) | cost saving %, Mission Plan Agent inline | HEDGE 81% (sample bias inflated) |
| → push back: sample bias + LLM cheating 의심 | | |
| v5 (stratified 300, 7년) | HIGH/MID/LOW 100개씩 + look-ahead 방지 | HEDGE 67% / OPP 15%, **2019-2024 IN 73% vs 2025-2026 OUT 43%** (cheating gap 30pp 입증) |
| → push back: prompt engineering으로 75%까지 | | |
| v6 (Recency + Structured) | 시간 버킷 + EIA/OPEC/momentum 정량 명시 | **HEDGE 75% hit (n=298), +0.626% saving** |

**v6 trade-off (정직)**:
- 7년 데이터 강세 regime dominated → 거의 모두 HEDGE 권고 (OPP 1건만)
- 시스템은 양방향 capable, 데이터가 그렇게 분포
- LLM cheating gap 30pp → production 실제 50% conservative

**K-Petroleum ROI**:
- 연간 100M bbl × +0.63% × ~30회 = **~$150M (best)** / **~$80M conservative**
- = 100-200억 KRW/년 절감

### Dubai 데이터 source

- 처음 EIA Brent 시도 → 403 차단
- push back (형욱): "두바이유가 중요한데"
- → OPINET KNOC `gloptotSelect.do` CSV endpoint 발견
- Dubai/Brent/WTI 1996~ daily 동시 반환 (cp949 encoding)
- robots.txt 허용, fair-use scrape

### Bloomberg 포지셔닝

- push back (다른 채팅): "빅5는 Bloomberg 있는데 의미?"
- 답: **Bronze schema 동일** (mentions/tone/keywords/ts), GDELT 자리에 Bloomberg connector swap 가능
- 차별화: 데이터 풀이 아니라 **양방향 reasoning + confidence calibration + Lakehouse source-agnostic**
- 시나리오 §19 평가위원 Q&A에 추가 (commit d087e5e)

### AIS (선박 위치)

- 시나리오 §7 #1, §14 Phase 3 "호르무즈 -93%" 약속
- 현재 `bronze.ais_positions` 0 rows (Sprint 2-3에 GDELT/OPEC 우선)
- 결정: **Option B (Lakeflow batch 5min)** 채택
- 이유: 시나리오 narrative 일관 (7 source Lakeflow), `databricks/notebooks/job_ais.py` skeleton 이미 있음
- 비용: ~$1-2 데모 5일, ~$5-10/월 production
- 시그널 reframe: AIS = **leading indicator (D-7 ~ D-1)**, 정확도가 아니라 lead time (§6.5 신규 섹션)

### Harness 진화

- 1차 push back: 단순 lint hook → "진짜 Anthropic harness 디자인 적용"
- 조사 결과: Stop hook self-critique 무한루프 위험 (GitHub issues 입증)
- 채택: **Evaluator-Optimizer pattern** (Anthropic 공식)
  - planner subagent (Opus, read-only) → 구조화된 plan
  - generator (main Claude) → 코드 작성
  - evaluator subagent (Opus, hackathon judge persona) → 5축 점수 + REVISE/PASS
- 비용: **$0 incremental** (형욱 Max 정액 안)
- scope rule: evaluator는 직전 task만 평가 (full audit은 명시 요청 시만)

### 5축 평가 rubric (evaluator.md)

1. **Innovation**: Pattern Score + bidirectional + confidence calibration 독창성
2. **Technical**: 실제 작동 (compile ≠ runs), 통합, error handling
3. **Databricks features**: Foundation Model API / Document Intelligence / UC / Lakebase / Agent Bricks / AI/BI / Lakeflow
4. **Social Impact (Track 1)**: Open data democratization, 계량 ROI, 적용 가능성
5. **Demo quality**: Live demo 작동, 시각 polish, storytelling

PASS = avg ≥ 80, no `blocker` drift.

---

## 4. 현재 상태 (2026-05-13 저녁)

### 데이터 layer
- Bronze 7 tables (news_articles 31,896 / oil_prices_daily 2,545+ / fx_rates 820 / eia_inventory 766 / opec_momr_parsed 35 / ...)
- Silver/Gold (signal_events_decayed 489 / daily_risk_score 1 / llm_backtest_predictions 600+)
- UC Function `weighted_signal()` (시간 감쇠 람다 차등)
- Document Intelligence 35 OPEC PDFs 추출 완료
- v6 backtest run: `llm_v6_20260512T164854`

### Backend (FastAPI)
- 14 endpoints (missions CRUD + recommend + pattern + backtest + WS + health)
- Mission store **Pluggable** (InMemory default + Lakebase via USE_LAKEBASE env flag)
- Optimistic version 409 동작
- Lakebase pool: psycopg3 + max_lifetime=3000 (OAuth 60min 만료 안전)
- Tests: 13 pass + 1 skip (Lakebase live integration gated)

### Frontend (React 19 + Vite + Tailwind 3)
- 3 pages: Discovery / Mission list+detail / What-if
- Router + React Query + WS hook + design tokens
- TS build pass (321KB JS / gzip 99KB)

### Harness (.claude/)
- planner.md + evaluator.md (Opus, runtime_checkable scope)
- /plan + /evaluate + /critique slash commands
- PostToolUse (py_compile + tsc), PreToolUse (dangerous Bash), UserPromptSubmit (git/todo context)

### Docs
- crude_compass_final_scenario.md (v6 narrative 반영)
- project_overview.md (회사 리뷰용 쉬운 overview, 60:40 통일)
- api_contract.md / architecture.md / data_model.md
- todo.md (active blocker + Sprint 진행)

### Cost
- 누적 ~$53 (Databricks free trial, $700 예산 안)
- 남은 D-5에 ~$30-50 예상 (Slack 통합 + Lakebase pool + Genie call)

---

## 5. 남은 D-5 plan (2026-05-13 → 5/18)

| Day | 시간 | 핵심 |
|---|---|---|
| **D-5 (5/13 저녁)** | 4h | ✅ Lakebase swap (D1-T1+T2, PASS 85.5) |
| **D-4 (5/14)** | 6h | Slack Bolt + Demo inject + AIS run |
| **D-3 (5/15)** | 6h | Genie + /recommend wiring + WhatIf textarea |
| **D-2 (5/16)** | 6h | Phase 4·6 alpha + 형욱 Workspace 4h block |
| **D-1 (5/17)** | 6h | full /evaluate + bug fix + 영상 1차 (RISK BUFFER) |
| **D0 (5/18 22:00)** | 6h | 영상 final + 제출 |

### 형욱 manual (8.5h parallel)
- **5/13-14**: Slack workspace + app + 2 secret (slack_bot_token, slack_signing_secret) ⏳
- **5/14 오전**: AIS Lakeflow job UNPAUSE + manual Run 1회
- **5/15 (3h)**: Genie Space + certified queries 8 + UC Function 등록
- **5/16 (4h)**: Supervisor / Knowledge Assistant / AI/BI Dashboard
- **데모 직전**: OPEC 4-5월 manual download (가능 시)

### Cut priorities (시간 부족 시 순서)
1. Phase 4 라이브 (Slack 5초 sync) → screencast (-8pt demo)
2. Genie Space → FMA fallback (-10pt databricks)
3. AI/BI Dashboard → PNG (-3pt)
4. **Lakebase 통합** — 절대 cut 마지막 (-12pt 최대 손실)
5-8. 작은 polish

---

## 6. 알려진 한계 (정직 공개)

| 한계 | mitigation |
|---|---|
| OPP 권고 1건 (7년 강세 regime) | paper trade 4주 검증 후 deploy narrative |
| LLM cheating 30pp gap | 2025-2026 cutoff OUT 50% conservative estimate |
| COVID demand shock 약함 | Self-Critique Agent + 추가 demand source |
| AIS / OilPriceAPI realtime historical 부재 | production-only signal, backtest 4 source |
| Dubai = OPINET 웹 endpoint scrape | production은 Argus / Platts 권장 |
| GDELT 영어권 편향 | 연합/Reuters Korea RSS Sprint 5 보강 |

---

## 7. Open questions / 결정 대기

- **Sonnet vs Haiku 비교 backtest** (item 10, 11): Sprint 5 buffer (5/19-20) 여유 시 시도
- **crude_compass_final.html**: stale 50→70 잔존, 사용 여부 결정 필요
- **AIS mock data fixture**: 5/14 형욱 manual run 결과 따라 결정 (empty 시 mock seed)
- **5/18 조기 제출 시점**: 18:00 freeze + 22:00 submit. miss 시 5/19-21 추가 fix
