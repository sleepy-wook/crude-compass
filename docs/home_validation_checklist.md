> 이 문서는 **최종 전체 검증표**다.  
> 시간이 부족하면 먼저 6. 집에서 직접 확인할 때 추천 순서만 따라도 된다.  
> P0 최소 검증 항목은 1.0, 1.1, 1.2, 1.3, 2.2, 2.4, 5.1이다.
>

> 날짜: 2026-05-19  
> 목적: 집 환경에서 Databricks CLI / SDK 연결이 가능한 상태에서, 제출 전 **실제 동작 / 데이터 정합성 / agentic narrative / 프런트 표현**을 체계적으로 점검하기 위한 체크리스트  
> 원칙:  
> - 단순 "보였음"이 아니라 **실제 확인 가능한 증거**를 남긴다  
> - 가능하면 **스크린샷 / 로그 / job run URL / SQL 결과**를 함께 남긴다  
> - 확인 결과는 `PASS / WARN / FAIL / N/A`로 표시한다

---

## 0. 점검 결과 기록 규칙

각 항목마다 아래 형식으로 기록하는 것을 권장한다.

```md
- [ ] 항목명
  - Result: PASS / WARN / FAIL
  - Evidence: job run link / screenshot / SQL result / API response
  - Notes: 한 줄 요약
```

예:

```md
- [ ] `gdelt_15min` job 정상 실행
  - Result: PASS
  - Evidence: latest run success, 2026-05-20 08:15 KST
  - Notes: row 312 insert, no timeout
```

---

# 1. Databricks

## 1.0 해커톤 필수 4기능 점검

이번 해커톤에서는 아래 4가지 Databricks 기능 활용이 핵심이다.

1. Databricks Apps
2. Lakebase
3. Genie
4. Agent Bricks

따라서 이 섹션은 단순히 "기능이 있다"를 확인하는 것이 아니라,

> **각 기능이 제품 안에서 올바른 역할로 보이는가**

를 확인하는 데 목적이 있다.

### 1.0.a Databricks Apps

- [ ] Apps가 실제 manager-facing main surface로 동작하는가
- [ ] Apps가 단순 프런트 호스팅이 아니라 decision room처럼 보이는가
- [ ] Apps 안에서 case workflow가 자연스럽게 이어지는가
- [ ] Apps가 Lakebase / Genie / Agent Bricks workflow를 소비하는 상위 surface로 보이는가

### 1.0.b Lakebase

- [ ] Lakebase가 단순 DB가 아니라 case memory / operational state로 작동하는가
- [ ] approval / revision / monitoring 상태가 Lakebase 기준으로 유지되는가
- [ ] Apps / Slack / backend가 같은 case state를 공유하는가
- [ ] case state transition이 실제로 persistence되는가

### 1.0.c Genie

- [ ] Genie가 실제 structured market evidence retrieval 역할을 하는가
- [ ] Genie가 단순 NL2SQL 데모가 아니라 specialized structured agent처럼 보이는가
- [ ] Investigation 흐름에서 Genie의 역할이 분명한가
- [ ] Genie 결과가 현재 case와 연결되어 보이는가

### 1.0.d Agent Bricks

- [ ] Agent Bricks / Supervisor가 실제 중심 orchestration layer처럼 보이는가
- [ ] specialized agents/tools 호출 흐름이 보이는가
- [ ] Agent Bricks가 단순 backend LLM router처럼 읽히지 않는가
- [ ] case open / investigation / next action / monitoring 흐름에 Agent Bricks가 분명히 개입하는가

## 1.1 Jobs

### 1.1.a 모든 job이 정상적으로 실행되는가

- [ ] `databricks/jobs/` 아래 정의된 모든 yml job 목록을 추린다
- [ ] 각 job이 Databricks workspace에 실제 존재하는지 확인한다
- [ ] 각 job의 최신 run 상태를 확인한다
- [ ] 최근 실패 이력이 있는 job은 failure reason을 확인한다
- [ ] cron/trigger가 의도대로 설정되어 있는지 확인한다
- [ ] paused 상태인 job이 없는지 확인한다
- [ ] timeout / retry / notification 설정이 의도와 맞는지 확인한다

점검 대상 예시:

- [ ] `gdelt_15min`
- [ ] `price_pipeline_5min`
- [ ] `oil_prices_daily`
- [ ] `ecos_daily`
- [ ] `eia_weekly`
- [ ] `opec_momr_monthly`
- [ ] `opec_momr_backfill`
- [ ] `daily_curation`
- [ ] `daily_risk_backfill`
- [ ] `backtest_seed`
- [ ] `backtest_compute`
- [ ] `backtest_llm`

확인 포인트:

- [ ] latest run success
- [ ] latest success timestamp가 freshness 기대치에 맞음
- [ ] row write가 0인데도 성공 처리되는 job인지, 의도된 것인지 확인
- [ ] fail-proof로 성공 종료하도록 짠 job은 "정말 문제 없는 성공"인지 구분

### 1.1.b 모든 yml job이 Databricks SDK 기준으로도 실제 존재하는가

- [ ] `databricks/jobs/*.yml` 파일 목록과 workspace 내 job 목록을 대조한다
- [ ] 선언된 job name과 실제 deployed job name이 일치하는지 확인한다
- [ ] yml은 있는데 workspace에 없는 job이 있는지 확인한다
- [ ] workspace에는 있는데 repo에는 없는 legacy job이 남아있는지 확인한다
- [ ] obsolete / duplicate job이 있는지 확인한다

특히 확인할 것:

- [ ] 이름이 바뀌고 legacy job이 남은 경우
- [ ] versioned job (`v5`, `v6`) 흔적이 실제 workspace에 아직 남아 있는 경우
- [ ] backfill 전용 job이 production narrative에 섞여 있지 않은 경우

### 1.1.c job별 실동작 품질

- [ ] `gdelt_15min`가 실제로 최근 기사/이벤트를 수집하고 있는가
- [ ] `price_pipeline_5min` 또는 현행 intraday 파이프라인이 실제 row를 적재하는가
- [ ] `oil_prices_daily`가 최신 일자를 따라가고 있는가
- [ ] `ecos_daily`가 최신 환율 데이터를 적재하는가
- [ ] `eia_weekly`가 최신 주간 데이터까지 반영하는가
- [ ] `opec_momr_monthly`가 최신 월간 PDF 기준으로 적재되는가
- [ ] `daily_curation`이 silver / gold를 실제 갱신하는가
- [ ] `backtest_seed / compute / llm`가 narrative와 맞는 row 수를 만든 적이 있는가

---

## 1.2 Medallion

### 1.2.a Bronze → Silver → Gold가 표준에 맞게 적재되는가

- [ ] 각 레이어의 책임이 명확한가
  - Bronze = raw / append / external source landing
  - Silver = normalized / curated / event logic
  - Gold = presentation / analytics / app-facing view

- [ ] Bronze 테이블이 실제 raw 성격을 유지하는가
- [ ] Silver 테이블이 실제 변환/정제/신호 생성 역할을 하는가
- [ ] Gold 테이블이 실제 dashboard/app 소비용 요약 레이어인가
- [ ] Gold에 raw-like table이 섞여 있지 않은가
- [ ] Silver/Gold 계산 logic이 docs 설명과 일치하는가

필수 테이블 확인:

### Bronze
- [ ] `bronze.news_articles`
- [ ] `bronze.oil_prices`
- [ ] `bronze.oil_prices_daily`
- [ ] `bronze.fx_rates`
- [ ] `bronze.eia_inventory`
- [ ] `bronze.opec_momr_parsed`

### Silver
- [ ] `silver.pattern_scores_daily`
- [ ] `silver.signal_events_decayed`
- [ ] silver에 실제 사용되는 핵심 테이블만 남아 있는지 확인

### Gold
- [ ] `gold.daily_risk_score`
- [ ] app/API가 읽는 gold 레이어가 실제 최신 상태인지 확인
- [ ] gold가 프런트/Genie/설명문과 같은 숫자를 반환하는지 확인

### 1.2.b freshness / completeness

- [ ] 각 핵심 테이블의 latest date / latest timestamp 확인
- [ ] bronze 최신 시점과 silver/gold 최신 시점 간 지연이 허용 범위 내인지 확인
- [ ] row count가 비정상적으로 급감/급증한 테이블이 없는지 확인
- [ ] NULL 비율이 높은 핵심 컬럼이 없는지 확인

예시 질문:

- [ ] `gold.daily_risk_score` latest date는 언제인가?
- [ ] `bronze.oil_prices_daily` latest trade_date는 언제인가?
- [ ] `bronze.opec_momr_parsed` latest report_month는 언제인가?
- [ ] `bronze.news_articles` latest published_at은 언제인가?

### 1.2.c dead table / unused table 존재 여부

- [ ] schema에는 있는데 코드/API/프런트 어디에서도 안 읽는 table이 있는가
- [ ] 과거 narrative용이었는데 현재는 dead인 table이 남아 있는가
- [ ] 실제 row는 계속 쌓이는데 app에서 쓰이지 않는 table이 있는가
- [ ] docs에서 제거했다고 했지만 workspace에는 남아 있는 table이 있는가

특히 확인할 것:

- [ ] AIS 관련 흔적이 실제 workspace에 남아 있는지
- [ ] backtest 관련 obsolete table이 남아 있는지
- [ ] discovery용 table이 현재 앱에서 실질적으로 안 쓰이는데 유지 중인지

### 1.2.d medallion naming / docs 정합성

- [ ] `docs/architecture.md` 설명과 실제 스키마가 일치하는가
- [ ] `docs/data_model.md`와 실제 table 구성이 일치하는가
- [ ] 현재 코드가 설명하는 source-of-truth와 실제 workspace 상태가 일치하는가

---

## 1.3 Databricks Apps / SDK / deployment

- [ ] App가 실제 최신 git 상태로 deploy되어 있는가
- [ ] build/deploy 실패 이력이 없는가
- [ ] health endpoint가 모두 통과하는가
- [ ] Apps runtime에서 Databricks SDK 호출이 문제없는가
- [ ] warehouse access / serving endpoint access / Lakebase access가 정상인가

체크할 health 예시:

- [ ] `/api/health`
- [ ] `/api/genie/health`
- [ ] `/api/supervisor/health`
- [ ] `/api/slack/health`

---

## 1.4 Agentic

여기는 단순 "LLM이 있냐"가 아니라 **agent loop가 실제로 보이는가**를 본다.

그리고 이번 점검에서는 단순한 일반 agentic함이 아니라,

> **Databricks Agent Bricks 기반 workflow처럼 보이는가**

를 기준으로 본다.

### 1.4.a Observe

- [ ] 시스템이 변화를 감시하는 source가 실제 존재하는가
- [ ] reactive trigger가 실제 동작하는가
- [ ] spike / new signal이 발생했을 때 사용자에게 노출되는가

### 1.4.b Investigate

- [ ] agent가 증거를 모으는 흐름이 실제로 설명 가능한가
- [ ] Supervisor / Genie / OPEC evidence가 "질문 응답"이 아니라 "case investigation"처럼 보이는가
- [ ] UI에서 evidence 수집 과정이 최소한 일부라도 드러나는가
- [ ] structured evidence와 document evidence가 분리된 역할로 보이는가
- [ ] Supervisor가 어떤 tool/agent를 호출했는지 trace/timeline에서 드러나는가

### 1.4.c Draft

- [ ] Mission Plan Agent가 현재 state를 받아 draft를 생성하는가
- [ ] draft가 단순 문장 생성이 아니라 actionable recommendation인가
- [ ] target_pct / duration / reasoning / delta_vs_previous가 일관적인가
- [ ] draft가 "즉시 실행"이 아니라 "decision case draft"로 보이는가

### 1.4.d Approve

- [ ] Apps에서 approve / reject / modify / pivot가 실제 동작하는가
- [ ] Slack에서 interactive action이 실제 동작하는가
- [ ] action 후 state sync가 Apps와 Slack에 반영되는가
- [ ] approve/reject 외에 keep watching / more evidence / re-check later 같은 next action이 존재하는가

### 1.4.e Monitor

- [ ] 승인 이후에도 case를 계속 추적한다는 인상이 UI/API 상에 있는가
- [ ] next review / watch condition / follow-up narrative가 있는가
- [ ] pivot/revision 조건이 드러나는가
- [ ] monitoring이 단순 상태값이 아니라 실제 후속 workflow처럼 보이는가

### 1.4.f Revise

- [ ] bidirectional pivot 시나리오가 실제로 시연 가능한가
- [ ] 기존 case → revised case 전환 흐름이 자연스러운가
- [ ] revision history가 남는가
- [ ] revision suggestion이 agent의 재평가 결과처럼 보이는가

### 1.4.g 최종 질문

- [ ] 이 시스템은 "dashboard + LLM"보다 "human-in-the-loop agent workflow"처럼 보이는가?
- [ ] agent 역할을 30초 안에 설명할 수 있는가?
- [ ] judge가 "이게 agent냐?"라고 물었을 때 구조적으로 답할 수 있는가?
- [ ] judge가 "이게 Agent Bricks냐?"라고 물었을 때 구조적으로 답할 수 있는가?

---

# 2. Frontend

## 2.1 정보구조(IA)

- [ ] 첫 화면이 "지금 어떤 decision case가 열려 있는가"를 명확히 보여주는가
- [ ] 페이지 구조가 기능 중심이 아니라 의사결정 흐름 중심인가
- [ ] navigation label이 현재 narrative와 맞는가
- [ ] `Mission`이라는 단어가 불필요하게 남아 있지 않은가
- [ ] `Decision Case / Open Case / Investigation / Market Watch` 같은 새 framing이 일관적인가
- [ ] 각 페이지가 Apps / Lakebase / Genie / Agent Bricks 역할을 자연스럽게 보여주는가

## 2.2 Decision Room / 메인 홈

- [ ] 현재 open case가 한눈에 보이는가
- [ ] 왜 이 case가 열렸는지가 5초 안에 이해되는가
- [ ] agent status가 보이는가 (`watching`, `investigating`, `approval pending`, `monitoring`, `revision`)
- [ ] Agent Bricks activity / supervisor orchestration이 보이는가
- [ ] manager가 바로 취할 수 있는 액션이 보이는가
- [ ] 유사 과거 사례가 현재 case와 연결되어 보이는가
- [ ] Apps가 단순 dashboard가 아니라 manager-facing decision room처럼 보이는가

## 2.3 Case File

- [ ] case summary가 명확한가
- [ ] evidence collected가 "데이터 나열"이 아니라 "case 근거"로 보이는가
- [ ] approval history가 보이는가
- [ ] revision history가 자연스럽게 보이는가
- [ ] monitoring rules / next check가 보이는가
- [ ] Lakebase-backed stateful workflow처럼 보이는가

## 2.4 Investigation

- [ ] Ask가 generic chatbot처럼 보이지 않는가
- [ ] current case context를 바탕으로 조사하는 느낌이 있는가
- [ ] quick prompt가 business question에 맞는가
- [ ] multi-agent trace가 시각적으로만 멋진 게 아니라 실제 근거 흐름을 설명하는가
- [ ] Genie와 document evidence agent의 역할 차이가 드러나는가
- [ ] Agent Bricks Supervisor orchestration이 이 페이지에서 가장 잘 보이는가

## 2.5 Market Watch

- [ ] 원천 데이터가 현재 case와 연결되어 보이는가
- [ ] 각 블록에 "so what for current case?"가 있는가
- [ ] 단순 차트 전시 페이지처럼 보이지 않는가
- [ ] 가격 / 뉴스 / OPEC / FX / pattern history의 역할이 분명한가
- [ ] structured evidence와 document evidence가 reasoning context 안에서 설명되는가

## 2.6 Copy / language

- [ ] jargon이 과도하지 않은가
- [ ] `pattern score`, `bullish`, `bearish` 같은 내부 용어를 그대로 남발하지 않는가
- [ ] manager / judge가 5초 안에 이해할 수 있는 문장인가
- [ ] 화면 문구와 docs narrative가 일치하는가
- [ ] Apps / Lakebase / Genie / Agent Bricks의 역할을 말로 설명할 수 있는 카피인가

## 2.7 Visual / interaction

- [ ] 첫 인상이 대시보드가 아니라 운영실/decision room처럼 보이는가
- [ ] 버튼 액션이 분명한가
- [ ] 빈 상태 / 오류 상태 / loading 상태가 자연스러운가
- [ ] reactive event나 sync가 "살아있는 시스템"처럼 느껴지는가
- [ ] activity timeline / case progression이 "agent가 계속 일한다"는 인상을 주는가

---

# 3. Backend / API

## 3.1 Health / availability

- [ ] 백엔드가 정상 기동되는가
- [ ] 모든 health endpoint가 정상인가
- [ ] Databricks SDK / Lakebase / Serving endpoint 연결이 정상인가

## 3.2 API contract

- [ ] 프런트가 실제 호출하는 endpoint가 모두 응답하는가
- [ ] 응답 shape와 frontend expectation이 일치하는가
- [ ] deprecated endpoint가 실제로 프런트에서 남아 있지 않은가

## 3.3 Missions / Case workflow

- [ ] recommend_now가 정상 동작하는가
- [ ] confirm / reject / modify / pivot가 정상 동작하는가
- [ ] optimistic concurrency conflict 처리도 자연스러운가
- [ ] pivot 후 새 상태가 실제로 반영되는가

## 3.4 Reactive / Slack / WebSocket

- [ ] reactive event가 실제 프런트에 도달하는가
- [ ] Slack DM / card가 정상 발송되는가
- [ ] Slack interactive action이 실제 backend state를 바꾸는가
- [ ] WebSocket이 Apps 화면과 상태를 동기화하는가

## 3.5 Supervisor / Genie

- [ ] Supervisor가 live call을 실제로 수행하는가
- [ ] trace가 실제 의미 있는 tool usage를 보여주는가
- [ ] Genie fallback / error handling이 자연스러운가
- [ ] OPEC / structured query / backtest analogy가 사용자의 질문에 맞게 연결되는가

---

# 4. Data ↔ Product 정합성

## 4.1 문서와 실제 앱이 같은 말을 하는가

- [ ] `docs/project_overview.md`와 앱 narrative가 일치하는가
- [ ] `docs/crude_compass_final_scenario.md`와 데모 플로우가 일치하는가
- [ ] 앱이 실제로 보여주는 데이터와 docs에서 강조하는 데이터가 일치하는가

## 4.2 숫자/주장 검증

- [ ] `n=298`, `75% hit rate` 같은 숫자가 실제 source와 맞는가
- [ ] backtest row 수가 narrative와 모순되지 않는가
- [ ] OPP / HEDGE 분포 설명이 실제 데이터와 크게 어긋나지 않는가
- [ ] freshness 날짜가 UI와 docs에서 과장되지 않는가

## 4.3 unused data / hidden value

- [ ] 수집했지만 UI에서 드러나지 않는 가치 있는 데이터가 있는가
- [ ] 앱이 실제 사용하는 데이터와 계속 적재되는 데이터 사이에 괴리가 큰가
- [ ] product narrative상 중요한데 화면에 충분히 안 드러나는 데이터가 있는가

---

# 5. Demo readiness

## 5.1 5분 데모 흐름

- [ ] 첫 30초 안에 problem / user / value가 설명되는가
- [ ] 첫 화면만 보고도 "이 앱이 뭘 하는지" 이해되는가
- [ ] agentic narrative를 30초 안에 설명할 수 있는가
- [ ] Slack / Apps / Databricks / evidence loop가 자연스럽게 이어지는가
- [ ] Apps / Lakebase / Genie / Agent Bricks 4개 역할을 자연스럽게 설명할 수 있는가

## 5.2 데모 시연 포인트

- [ ] open case 진입
- [ ] why this case is open 설명
- [ ] evidence / market memory 설명
- [ ] investigation drill-down
- [ ] approve / modify / pivot 시연
- [ ] reactive or revision 시연
- [ ] Agent Bricks Supervisor / Genie / Knowledge / tool orchestration 시연 포인트가 있는가

## 5.3 데모 리스크

- [ ] live dependency가 너무 많은가
- [ ] fail 시 fallback narrative가 준비되어 있는가
- [ ] network / auth / token / warehouse cold start 위험이 관리되는가
- [ ] 가장 위험한 부분 3개를 미리 적어두었는가
- [ ] judge가 "4기능을 어디에 썼냐"라고 물었을 때 바로 답할 수 있는가

---

# 6. 집에서 직접 확인할 때 추천 순서

시간이 부족하면 아래 순서로 체크하는 것을 권장한다.

## Phase 1 — Databricks reality check

- [ ] workspace job 목록 vs yml 목록 대조
- [ ] 핵심 job latest run 확인
- [ ] 핵심 bronze / silver / gold latest row / latest date 확인
- [ ] dead table / legacy job 존재 여부 확인

## Phase 2 — App / backend health

- [ ] health endpoints 확인
- [ ] 주요 API endpoint 응답 확인
- [ ] recommend / confirm / pivot / reactive flow 확인

## Phase 3 — Frontend narrative

- [ ] 첫 화면 캡처 보고 5초 테스트
- [ ] case / evidence / monitoring / investigation 흐름 점검
- [ ] jargon / dead section / 중복 section 정리

## Phase 4 — Demo rehearsal

- [ ] 5분 흐름 한 번 끝까지 시연
- [ ] 말이 꼬이는 부분 / 화면상 설명이 안 되는 부분 기록
- [ ] judge 예상 질문 5개 적기

---

# 7. 최종 판정 질문

집에서 마지막으로 아래 질문에 답해보면 좋다.

- [ ] 지금 이 시스템은 실제로 "작동하는 Databricks app"인가?
- [ ] 지금 이 시스템은 "데이터 파이프라인 + 앱 + 승인 루프"가 실제 연결되어 있는가?
- [ ] 지금 이 시스템은 "agentic"하다고 설명할 수 있는가?
- [ ] 지금 이 시스템은 "정유사 구매 의사결정 지원"이라는 가치가 분명한가?
- [ ] 지금 이 시스템은 첫인상에서 recommendation viewer가 아니라 decision room처럼 보이는가?
- [ ] 지금 이 시스템은 Databricks Apps / Lakebase / Genie / Agent Bricks를 제품 역할로 설명할 수 있는가?

---

## 8. 추천 후속 문서

이 체크리스트를 실제로 쓰려면, 다음 문서와 같이 보면 좋다.

- `docs/frontend_restructure_proposal.md`
- `docs/agentic_redesign_review.md`
- `docs/crude_compass_final_scenario.md`
- `docs/project_overview.md`
- `docs/architecture.md`

---

끝.

