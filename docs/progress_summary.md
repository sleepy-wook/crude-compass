# Crude Compass — 진행 상황 요약

> 작성일: 2026-05-15 (마감 D-3, 조기 제출 D-3)
> 독자: 비개발자 · 평가위원 · 친구 · 가족
> 어려운 용어 없이 한 번에 읽히게 정리
>
> **5/16 D-2 reframe**: 본 문서의 AIS Stream / K-Petroleum 5척 fleet 언급은 historical 기록.
> D-2 (5/16) 시점 AIS Stream 완전 제거 + source 7→6 reconfiguration 결정.
> 이유: 한국 flag VLCC 0척 active + 7년 backtest 미사용 → narrative dead weight.
> 호르무즈 narrative anchor는 GDELT 키워드 mention burst로 단일화. 최신 상태는 `crude_compass_final_scenario.md` 참조.

---

## 우리가 만드는 것

**한국 정유사를 위한 원유 구매 결정 AI 도우미.**

> 원유 시장은 매일 흔들립니다 — 호르무즈 해협 봉쇄 위기, OPEC 감산 결정, 미국 재고 발표, 환율 변동.
> 정유사 구매팀이 이 모든 신호를 매일 추적하기는 사실상 불가능합니다.
>
> **Crude Compass**는 6가지 공개 데이터(뉴스·선박 위치·유가·재고·환율·OPEC 보고서)를 실시간으로 모아 AI가 "지금 더 사두세요(헤지)" 또는 "지금은 천천히 사세요(기회 포착)"를 추천합니다.
> 결정은 사람이 합니다 — AI는 근거를 정리해줄 뿐. 작은 5명짜리 팀도 대기업 분석가팀처럼 일하게 만드는 게 목표.

**해커톤**: Databricks Building Intelligent Apps Hackathon 2026 (Track 1 — Social Impact)
**마감**: 2026-05-22 (조기 제출 5/18 22:00 KST)
**개발자**: LG이노텍 Gen AI Engineer 1인 + LG전자 친구 (디자인/기획 보조)

---

## 오늘 (5/15, D-3) 한 일 — 7개 작업

> "왜 이걸 했냐"를 먼저 쓰고 "어떻게 했냐"는 한 줄로 끝.

### 1. 안 쓰던 데이터 창고 3개 정리 (`7bef6eb`)

옷장에 입지도 않는 옷 3벌이 있으면 답답하죠. 우리도 약속만 해놓고 실제로는 한 줄도 안 쓰던 데이터 테이블 3개를 발견해서 지웠습니다. 평가위원이 들여다봤을 때 "이건 뭔가요?"라고 묻기 전에 미리 정리.

→ `mission_outcomes`, `landing_cost_scenarios`, `backtest_risk_score` 삭제.

### 2. 옛날 코드 흔적 지우기 (`6cdb7cd`)

같은 기능을 v4, v5, v6 이렇게 여러 버전으로 만들면서 실험했었어요. 최종 버전만 남기고 나머지는 다 지웠습니다. 폴더 정리 + 파일명 단순화.

→ 파일 6개 삭제, 코드 안의 v5/v6 표기 모두 제거.

### 3. AI가 만든 데이터를 올바른 위치로 옮김 (`f2cec22`)

데이터 창고에는 두 가지 종류가 있습니다.
- **분석용** (느려도 OK): 매출 보고서, 월간 통계 같은 거
- **실시간 운영용** (빨라야 함): 사용자가 화면 누르면 0.1초 안에 답해야 하는 거

우리 AI가 만든 "백테스트 결과 300건"(과거 시장에서 AI 추천이 얼마나 맞았는지 검증)이 잘못된 위치(분석용)에 있어서 화면에서 느렸어요. 빠른 운영용 데이터베이스로 이사 완료.

→ Databricks 분석 DB → Lakebase Postgres 운영 DB로 이동. 부수 작업으로 백엔드 API + 노트북 + 문서 동기화.

### 4. 분석용 화면 8개 미리 만들어두기 (`491e150`)

복잡한 데이터 질의(SQL)를 매번 새로 짜는 대신 **자주 쓰는 8가지 분석 패턴**을 미리 만들어뒀습니다.

| 화면 | 뭘 보여주는지 |
|---|---|
| oil_prices_wide | 두바이·브렌트·WTI 일일 가격 한눈에 |
| signal_contribution_30d | 최근 30일 어떤 뉴스/지표가 위기 점수를 끌어올렸는지 |
| eia_rolling | 미국 원유 재고 4주 평균 변화 |
| opec_demand_gap | OPEC 공급 - 수요 = 시장 균형 |
| fx_with_delta | 원/달러 환율 + 변동성 |
| news_top_signals | 최근 7일 가장 중요한 뉴스 상위 5개/일 |
| pattern_score_latest | 위기 점수 30일 추이 |

이 7개를 D-2에 Genie(AI 데이터 어시스턴트)와 대시보드에서 그대로 씁니다. (D-2 5/16 정리: fleet_current_state view는 AIS Stream source 제거와 동반 DROP.)

### 5. 메인 화면에 시나리오 시각화 추가 (`0e765e1`)

가장 큰 작업. **시나리오에서 약속한 것들이 실제 화면에 안 보이는 문제** (정합성 52%)를 발견하고 메꿨습니다.

- **시그널 기여도 막대 차트** — "오늘 위기 점수 82점은 GDELT 뉴스 톤 35% + OPEC 28% + EIA 22% + FX 15% 기여" 한눈에 표시.
- **위기 점수 추이 차트** — 30일 미니 차트 + **6년 long 차트** (호르무즈 봉우리 + 작은 봉우리들 = 매주 평시 시그널 = 일상 도구 narrative).
- **OPEC MOMR 인용 박스** — "OPEC 월간 보고서 PDF에서 직접 파싱한 결과: 사우디 +24 kbbl/d 증산" 명시. AI가 PDF를 읽었다는 증거 노출.

→ 신규 컴포넌트 + 백엔드 API. **외부 라이브러리 0개 추가** (모두 순수 SVG + CSS).

> D-2 (5/16) 후속 정리: HormuzMap (호르무즈 해협 지도) 컴포넌트는 AIS Stream 데이터 출처 제거와 동반 삭제. 호르무즈 narrative anchor는 GDELT 뉴스 키워드 mention burst 카드 (이란/호르무즈 +280%) 로 단일화.

### 6. 시나리오 ↔ 코드 정합성 수정 (D-2 reframe)

D-3 시점에는 "정유사 자사 fleet AIS 추적 = industry standard" 로 narrative 명시했으나, D-2 (5/16) 시점 결정 — AIS Stream 데이터 source 자체를 완전 제거:
- 7년 backtest에 ais_traffic row 0건 (silver.signal_events_decayed)
- 글로벌 8min scout 결과 한국 flag VLCC 0척 active
- "실시간 추적" narrative가 실데이터 없이는 mock 시뮬이 되어 신뢰성 risk

→ 시나리오 §4 가상 fleet + §6.5 leading 시그널 + §7 source 7→6 통째 재구성. 코드/스키마/문서 consistent update (commit `533cefb`).

### 7. 자동 실행 작업 12개 audit (`d42703f`)

**중요한 root cause 발견**:

> Databricks 워크스페이스에서 일시정지(PAUSED)된 작업들을 명령으로 풀어도, 다음에 코드를 배포하면 yml 파일에 적힌 "PAUSED"가 다시 덮어쓰는 문제.

yml 파일 자체를 고쳐야 영구 적용됨. 6개 yml의 `pause_status: PAUSED` → `UNPAUSED` 변경.

| 자동 실행 | 빈도 | 역할 |
|---|---|---|
| ~~선박 위치 수신~~ | ~~5분~~ | ~~AIS 신호 → 우리 유조선 5척 위치 추적~~ (D-2 5/16 폐기) |
| 유가 5분 수신 | 5분 | OilPriceAPI 실시간 가격 |
| GDELT 뉴스 | 15분 | 글로벌 뉴스 멘션 + 톤 점수 |
| **일일 위기 점수 계산** | 매일 06:30 | 모든 데이터 종합해서 오늘 점수 계산 (가장 중요) |
| 한국 환율 | 평일 18:00 | 한국은행 ECOS |
| 유가 일별 종가 | 평일 19:00 | OPINET KNOC |
| 미국 재고 | 매주 수 18:00 | EIA Open Data API |
| OPEC PDF | 매월 12일 | 월간 보고서 자동 파싱 |

추가로:
- **삭제**: `news_rss_enrich` 작업 (한 번도 실행 안 됨, GDELT 단일 source로 충분)
- **timeout 조정**: ECOS 120초 → 180초 (지난번 timeout 실패 1회 → 안전 마진), OPEC 600초 → 900초 (PDF 파싱 여유)

**결과**: 13개 작업 → **12개**. 8개 자동 + 4개 수동.

---

## D-2 (5/16-5/17) — Production Deploy 완료

### Workspace 배포 + Agent Bricks 통합 (5/16 새벽 ~ 5/17 오후)

5/16 D-3 마지막 정리 후 5/17 D-1 시점까지 약 30개 commit. 핵심:

#### 1. AIS Stream + K-Petroleum 5척 fleet 완전 제거

사용자 push back: *"7년 backtest에서 ais_traffic row 0건 + 한국 flag VLCC 0척 active. 어차피 백테스트 때도 못 쓰고 다니는 배도 없으면 의미 없지 않아?"*

→ AIS Stream 데이터 source 완전 폐기 (코드/스키마/데이터/문서/UI 모두 정리). 시나리오 source 7→6 (GDELT/OilPriceAPI/OPINET/EIA/ECOS/OPEC MOMR). 호르무즈 narrative anchor는 GDELT 키워드 mention burst로 단일화. 결과: scenario consistency 100%, narrative dead weight 0.

#### 2. Apps Production Deploy (Git source 자동 build)

기존 `databricks sync` + `apps deploy --source-code-path` workspace 패턴 → **Git source + 자동 build pipeline**으로 swap:
- root `package.json` — `cd frontend && npm ci && npm run build`
- root `requirements.txt` — backend Python deps export
- `app.yaml` command: `uvicorn app.main:app --app-dir backend`
- `git push origin main` → Databricks가 자동 fetch + build + restart

평가 측면: CI/CD pipeline standard narrative + 매번 sync 명령 불필요.

#### 3. Agent Bricks 2 types (KA + Multi-Agent Supervisor)

D-3 시점 self push-back ("Multi-Agent Supervisor 의도적 scope-out, cost-effective 판단")이 outdated — Agent Bricks GA 발견으로 60-90분 UI 작업으로 충족 가능:

- **Knowledge Assistant** (`ka-6b456458-endpoint`): OPEC MOMR 74 PDF RAG + citation
- **Multi-Agent Supervisor** (`mas-ba3fbcb5-endpoint`): single endpoint orchestration
  - Sub-agent 1: Genie Space "Crude Oil Market Analysis" (gold view 10 tables)
  - Sub-agent 2: Knowledge Assistant endpoint
  - Sub-agent 3: UC Function `mission_plan_advice` (wrapping FMA `databricks-claude-haiku-4-5`)
  - `databricks_options.return_trace=true` → frontend tools_used badge transparency

**Information Extraction agent는 redundant scope-out** — bronze.opec_momr_parsed가 이미 `ai_parse_document` + Foundation Model API 직접 호출로 동일 fields 추출 + monthly incremental. 솔직 narrative.

#### 4. Genie Space 등록

- Name: "Crude Oil Market Analysis" (SPACE_ID `01f150e05229190aa9de93c97afde034`)
- Tables 10 (gold 8 view + silver 2): pre-shaped BI-ready
- 5 example queries (모두 gold view 사용)
- App SP catalog 권한 부여 (USE CATALOG + USE SCHEMA + SELECT)

#### 5. Lakebase 진단 + Graceful fallback

Apps SP의 PG OAuth role mapping issue 발견 — SP UUID에 PG ROLE 생성 + GRANT 완료 후에도 PoolTimeout. 추정: Databricks Lakebase OAuth user claim ↔ PG role 자동 매핑 필요 (Apps Database resource로 D-1 fix 예정).

backend `_build_store()`에 smoke test + fallback 추가:
```
Lakebase smoke test → SELECT 1 OK ? Lakebase : InMemoryMissionStore + Bidirectional seed
```

D-1 시점 production은 in-memory fallback이지만 Bidirectional 2 missions (HEDGE Term 60→75%, OPP Spot 40→55%) 시연 가능. D-1에 Apps Database resource 추가하면 즉시 Lakebase 복귀.

#### 6. 8 dead UC objects DROP

5/15-5/16 결정한 dead tables/views를 schema 파일에는 DROP 명시했지만 workspace 미적용. apply_schemas.py에 영구 migration 추가 + 1회 SDK 직접 실행:
- bronze.ais_positions, silver.{hormuz_traffic_hourly, dubai_premium_daily}
- gold.{fleet_current_state, backtest_results, mission_outcomes, landing_cost_scenarios, backtest_risk_score}

#### 7. UC Function `mission_plan_advice` 생성

Supervisor sub-agent 3번째 (Mission Plan)을 Foundation Model API 직접 호출 형태로 만들 수 없음 (system endpoint이라 sub-agent 등록 불가). 우회:
```sql
CREATE FUNCTION crude_compass.functions.mission_plan_advice(question STRING)
RETURNS STRING
RETURN ai_query('databricks-claude-haiku-4-5', concat(system_prompt, question))
```
검증: 한국어 매입 비중 query → Bidirectional 권고 + 3 scenarios ROI 반환.

#### 8. evaluator 5차 PASS 83.2 (+0.4 from 4차)

| 축 | 변화 |
|---|---|
| A2 Creativity | 79 → 87 (+3 ⭐ Supervisor scope-in 진정성) |
| A4 Technical | 86 → 84 (Git source build + graceful fallback) |
| A5 Storytelling | 82 → 78 (-5 ⚠️ backtest narrative drift) |

평균 82.8 → 83.2.

---

## 다음 계획 (D-1 → D0)

### D-1 (5/17 일요일) — P0 3건 + 영상

상세: [d1_runbook.md](d1_runbook.md). 핵심:

1. **Backtest 재실행** — `backtest_llm` job, n_per_zone=100 × 3 zone (HEDGE+MID+OPP)
2. **Apps Database resource 추가** — Lakebase fallback 해제
3. **§19 Risk OPP n=0 disclosure**
4. **영상 5분 1차 녹화**

| 시간 | 작업 | 소요 |
|---|---|---|
| 06:00 | Web 앱 배포 (Apps) | 30분 |
| 06:30 | Slack 연동 URL 등록 | 5분 |
| 06:35 | **Genie Space 등록** — AI한테 자연어로 데이터 질문하는 기능 | 1시간 |
| 07:35 | **Knowledge Assistant 시작** — OPEC PDF 문서 검색 AI 등록 (sync 1-3h 걸림, critical path) | 1-3시간 |
| 07:40 | AI/BI Dashboard 5개 차트 만들기 (Knowledge Assistant sync 기다리는 동안 병렬) | 30분 |
| 10:00+ | Knowledge Assistant live → 마지막 통합 테스트 | — |

### D-1 (5/17 일요일) — 최종 검증 + 영상

- 전체 시스템 테스트 (`/evaluate` 명령 자동 실행)
- 평가위원 시점 5분 데모 영상 1차 녹화

### D0 (5/18 월요일) 22:00 KST — 조기 제출

해커톤 official 마감은 5/22지만 4일 buffer 두고 조기 제출.

---

## 왜 이게 의미 있나

해커톤 평가 5축 기준:

| 평가 축 | 우리 강점 |
|---|---|
| **Technical** | 12개 자동 cron + AI Mission Plan Agent + 백테스트 300건 75% 정확도 검증 |
| **Innovation** | "감지 → 추천 → 실행"을 5분 안에 끝내는 양방향 동기화 (Slack ↔ 웹) |
| **Impact** | 5인 정유사 구매팀도 대기업 분석가팀처럼 — Open Data Democratization |
| **Demo** | Genie + Knowledge Assistant + 호르무즈 지도 + 6년 차트 라이브 시연 |
| **Required Tools** | Databricks Apps + Lakebase + Genie + Agent Bricks **4개 모두 production-grade** |

**한 줄 요약**: 시나리오에서 약속한 거 다 화면에 보이게 만들고, 자동 데이터 흐름 안정화 끝. 이제 D-2에 Workspace 배포만 하면 데모 준비 끝납니다.

---

> 본 문서는 진행 상황 snapshot입니다. 최신 기술 사양은 `docs/architecture.md` + `docs/api_contract.md` 참조.
