# Phase 1 — 사전조사 (Research)

> 작성일: 2026-05-08 (D-14)
> 검증 방법: WebSearch + WebFetch (공식 docs.databricks.com / databricks.com/blog 우선, 보조 출처 표시)
> 목적: 시나리오·구현 진입 전 외부 사실 검증

---

## 1.1 해커톤 — Databricks Building Intelligent Apps Hackathon ✅ 확정

> URL: https://buildintelligentapps-databricks.com/
> 공식명: **Databricks Building Intelligent Apps Hackathon, in collaboration with AWS**

### 핵심 일정

| 항목 | 일자 |
|---|---|
| Registration | 2026-04-06 ~ **05-22** |
| **Submission** | 2026-04-29 ~ **05-22** (D-14) |
| Judging | 2026-05-25 ~ 05-29 |
| **Winners 발표** | 2026-06-15 |

### 트랙

| Track | 설명 | Crude Compass 매칭 |
|---|---|---|
| **Track 1: Social Impact** | public/open data로 societal problems 해결 | ✅ 한국 정유사 매니저 의사결정 지원, 100% open data — 명백히 매칭 |
| Track 2: Business Impact | organizational data로 비즈니스 도전 | ✗ |

**Language tracks**: English / Japanese / **Korean** ✅ — 3개 언어 모두 동일 심사기준, 한국어 트랙 별도 winner.

### 심사 기준 (각 20%, 총 100%)

| # | 기준 | Crude Compass leverage point |
|---|---|---|
| 1 | **Business Applicability** | 한국 정유사 (S-Oil/SK 에너지/GS Caltex/현대오일뱅크) 실제 매니저 일과 1:1 매핑 — 강함 |
| 2 | **Creativity & Innovation** | Bidirectional Pattern Score (위기+기회 양방향) — 일반 hedge 모니터링 대비 차별화 |
| 3 | **User Experience & Insights** | Slack ↔ Apps 5초 sync, Mission Card 디자인 시스템 — 강함 |
| 4 | **Technical Capability** | Apps + Genie + Lakebase + Agent Bricks 4-tool 1:1 매핑 — 명시 toolkit 100% 활용 |
| 5 | **Data Storytelling & Narrative** | 호르무즈 실제 진행 중 timeline + backtest로 검증 가능 — 강함 |

### 필수 toolkit

> "Teams must incorporate Databricks technologies including **Lakebase, Genie Spaces, Databricks Apps, Agent Bricks**, etc."

→ 마스터 프롬프트의 4-tool 1:1 매핑 정확. Foundation Model API + Lakeflow Jobs + AI/BI Dashboard는 보조.

### 제출 형식

**5분 비디오 프레젠테이션** 필수. 포함 요소:
1. Team introduction
2. Problem statement
3. Solution architecture walkthrough
4. Functional demonstration

→ 마스터 프롬프트 Sprint 5 (5/20-22) "데모 영상 script + 녹화 + 편집" 5분 분량 유지.

### 상금

| 등급 | 상금 | 비고 |
|---|---|---|
| 1등 (track/language별) | $4,000 USD | + 컨퍼런스 티켓 + 트로피 |
| 2등 (track/language별) | $2,500 USD | + training coupons |
| 총 풀 | $19,500 USD | 6 winners |

→ 한국어 × Social Impact 트랙 1등 = **$4,000** 가능. 1팀 winner.

### 자격 / 팀 요건

- **APAC 9개국 중 South Korea 포함** ✅
- **팀 사이즈 2-4명** ⚠️ (단독 X)
- **모든 멤버 corporate email** 사용
- **제외 대상**: 정부 공무원, **Databricks 파트너 직원** ⚠️
- 각 멤버 독립적으로 자격 충족 필수

### ⚠️ 자격 확인 필요 — Manual Step (남은 1개)

🛑 **MANUAL STEP — 팀 + Databricks 파트너 자격 확인**
WHERE: (1) 형욱님 본인 / 같이 출전할 팀, (2) LG Innotek HR/법무 또는 Databricks 한국 담당자
HOW:
  1. **팀 멤버 확정**: 2-4명 필수. 단독이면 출전 불가. corporate email 사용 가능한 동료 1-3명 섭외 필요.
  2. **LG Innotek이 Databricks "파트너" 분류 여부 확인**: Databricks Partner Network (resell/SI/ISV/consulting) 등록 여부. LG 그룹 내 다른 계열사가 partner라도 LG Innotek 직원은 OK일 수 있으나 명시 확인.
SOURCE: hackathon official rules 페이지 (eligibility 섹션)
완료하면 답해주세요: "done: 팀 N명 확정 / partner 자격 OK" 또는 blocker 공유

---

## 1.2 Databricks 도구 매트릭스 (2026-05-08 기준)

| # | 도구 | 상태 | 핵심 사실 | 출처 | Crude Compass 영향 |
|---|---|---|---|---|---|
| 1 | **Apps** | GA | Vite+React+FastAPI 패턴 공식 (apps-cookbook.dev). FastAPI에서 Vite static 서빙 + API. Single-command deploy, Kubernetes 불필요. Node.js 프레임워크도 지원 (확장 中). | [docs](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/), [Cookbook](https://apps-cookbook.dev/docs/fastapi/getting_started/create/) | 마스터 프롬프트의 hybrid 패턴 ✅ 그대로 진행 가능 |
| 2 | **Genie** | **Public Preview** ⚠️ | Conversation APIs Public Preview. Agent Mode (multi-step reasoning) Public Preview. Slack/Teams/Apps embed 지원. 30분 Slack 통합 가이드 존재. | [Agent Mode 블로그](https://www.databricks.com/blog/introducing-genie-agent-mode), [Slack 가이드](https://www.databricksters.com/p/integrate-slack-with-genie-natively) | **Public Preview = SLA 없음**. 시나리오의 "Genie fallback 필수" 지시 적중. 데모 day에 깨지면 SQL pre-canned 응답으로 대체 |
| 3 | **Lakebase** | **GA 2026-02-03** ✅ | 2026-02-03 GA. **2026-03-12부터 신규 인스턴스 = Autoscaling project**. Scale-to-zero, autoscaling. Lakehouse Sync (CDC) 양방향: Postgres ↔ Unity Catalog Delta. | [Product](https://www.databricks.com/product/lakebase), [Sync docs](https://docs.databricks.com/aws/en/oltp/projects/sync-tables) | mission OLTP 채택 정당. **신규 인스턴스는 자동으로 Autoscaling — JSONB/UUID dialect 호환성 검증 Sprint 1에서 필수** |
| 4 | **Agent Bricks** | Custom Agents GA | Custom Agents GA, Document Intelligence GA. Supervisor API Beta. CLEARS framework (correctness/latency/execution/adherence/relevance/safety) MLflow 통합. AI Gateway 거버넌스. Custom MCP/Apps-hosted agent를 subagent로 결합 가능. | [Blog](https://www.databricks.com/blog/agent-bricks-governed-enterprise-agent-platform), [docs](https://docs.databricks.com/aws/en/generative-ai/agent-bricks/) | 4 Agent (Monitoring/Mission Plan/Simulation/Self-Critique) 정의 가능. CLEARS로 데모 시 quality 점수 시각화 가능 |
| 5 | **AI/BI Dashboard** | External embed GA | External embedding GA. iframe + `hideDatabricksLogo` 옵션. Genie space iframe embed 가능. Apps 내 embed 명시. allowed surfaces 워크스페이스 admin 설정 필요. **Embed는 항상 light mode**. | [embed docs](https://docs.databricks.com/aws/en/dashboards/share/embedding) | Apps에 dashboard embed ✅. 단 light mode 강제 → 디자인 system은 light 변형 우선 |
| 6 | **Foundation Model API + Claude Haiku 4.5** | GA (pay-per-token) | Endpoint 이름 `databricks-claude-haiku-4-5` 형태. **$1/M input, $5/M output**. 2026-02-15부터 pay-per-token 빌링. Databricks 보안 perimeter 내 호스팅. | [supported models](https://docs.databricks.com/aws/en/machine-learning/foundation-model-apis/supported-models), [pricing](https://www.databricks.com/product/pricing/proprietary-foundation-model-serving) | News scoring/Pattern Detection LLM call 비용 추정 가능. 일 ~1000 article × 800 input × $1/M = $0.8/day → $700 credit 부담 적음 |
| 7 | **Lakeflow Jobs** | GA, **이름 변경** ⚠️ | Asset Bundles → **Declarative Automation Bundles** (DAB)로 리브랜딩. DLT → **Lakeflow Declarative Pipelines**. YAML IaC. Continuous job 지원. Serverless **Standard mode** (배치, 4-6분 startup, 70% 절감) vs **Performance Optimized**. | [DAB docs](https://docs.databricks.com/aws/en/dev-tools/bundles/), [Serverless 블로그](https://www.databricks.com/blog/evolution-data-engineering-how-serverless-compute-transforming-notebooks-lakeflow-jobs) | `databricks.yml` bundle은 동일하게 작동. 5/15 cron 15min/5min job은 Standard mode 가능 (latency 허용). AIS WebSocket continuous는 Performance Optimized 필요 → **비용 추정 별도** |

### 비용 추정 — Continuous Job 경고

- **AIS WebSocket continuous job**: Performance Optimized serverless 필요 (실시간 stream). Databricks 공식 시간당 가격은 SKU별 상이 — Sprint 4 진입 전 정확한 SKU 확인 필요. $700 credit 중 절반 이상이 여기 들어갈 위험. 데모 day만 켜는 옵션 권장.
- 5/15 OilPriceAPI cron 15→5min 전환: Standard mode serverless로 충분. Job당 ~$0.50/day 미만 추정.

---

## 1.3 호르무즈 위기 — 실제 진행 중 fact sheet

> 시나리오의 "실제 진행 중" 주장은 정확. backtest 데이터 사용 가능.

### Timeline (검증된 사실)

| 날짜 | 사건 |
|---|---|
| 2025년 (전년도) | 12일 공중전 (1차), Geneva 핵협상 결렬, 호르무즈 일시 partial closure (warning) |
| 2026-01 | Pre-crisis 신호 누적 (시나리오 ground truth — 외부 검증 어려우나 정황 일치) |
| **2026-02-28** | **Operation Epic Fury 개시** (미국+이스라엘 공동 공습), Khamenei 사망, Iran "Operation True Promise IV" 보복 — 7개국 (Bahrain/Jordan/Kuwait/Qatar/Saudi/UAE/Iraq)으로 확전 |
| 2026-03-04 | 이란 호르무즈 공식 폐쇄 선언, 통과 선박 공격 위협 |
| 2026-03-10 | 6.7M bpd 글로벌 시장 이탈 |
| 2026-03-12 | 10M bpd 초과 이탈 |
| 2026-04-13 | 미국 이란 항구 역봉쇄 (dual blockade) |
| 2026-04-19 | US, 이란 cargo ship 호르무즈에서 압류 |
| 2026-04-30 | **Brent $126 정점** |
| 2026-05-04 | 이란 UAE 공격, Brent 5.9% ↑ $114.44 / WTI $106.42 |
| 2026-05-05 | Trump pause 발표, Rubio "Epic Fury is over" |
| **2026-05-07** | Brent **$100.06** / WTI $94.81 (Pakistan 중재 협상 中) |
| **2026-05-08 (오늘)** | 협상 진행 中, dual blockade 유지, Iran 통과 선박당 $1M 통행료 부과 |

### Brent 가격 reality check vs 시나리오

| 시점 | 시나리오 | 실제 | 차이 |
|---|---|---|---|
| Pre-crisis (1월) | $80 | $68-70 | **시나리오가 ~$10 high** |
| 정점 | $126 | $126 (4/30) | ✅ 일치 |
| 5/8 현재 | (명시 X) | $100 안팎 | 시나리오 update 권장 |

### Crude Compass에 미치는 영향

- **데이터 품질**: 1월 Pre-crisis 신호 누적 (Tier B 외교부/EIA 보도, war zone JWC PDF 등)는 외부 자료로 backtest 가능 ✅
- **시나리오 보정**: pre-crisis Brent 가격 $80 → $68-70로 시나리오 update 권장 (Phase 2 critique에서 다룰 항목)
- **데모 timing**: 5/22 데모 시점에 협상 결과에 따라 reopen scenario도 가능 — 데모는 1월~3월 backtest로 묶고 5월 현재 상황은 "ongoing" 표기

---

## 1.4 ✅ 확인된 것 / ⚠️ 검증 못 한 것

### ✅ 확인됨

- Databricks Apps Vite+React+FastAPI 패턴 공식 지원
- Lakebase 2026-02-03 GA, Autoscaling 2026-03-12 신규 인스턴스 자동 적용
- Agent Bricks Custom Agents GA, CLEARS MLflow 통합
- AI/BI Dashboard external embed GA, Apps 내 embed 가능 (light mode only)
- Foundation Model API에 Claude Haiku 4.5 pay-per-token 가능
- Lakeflow Jobs (구 Asset Bundles → Declarative Automation Bundles 리브랜딩) YAML continuous serverless 지원
- 호르무즈 봉쇄 2026-02-28 발발 / 03-04 폐쇄 / dual blockade 진행 중 / Brent 4/30 $126 정점
- pre-crisis Brent 실제 $68-70 (시나리오 $80과 차이)

### ⚠️ 검증 못 함 / Manual Step 필요

1. 🛑 **팀 2-4명 + Databricks partner 자격** — §1.1 Manual Step 참조
2. **Lakebase Postgres dialect** — JSONB/UUID/optimistic concurrency `version` 컬럼 호환성 (Sprint 1 진입 전 simple test로 확인)
3. **AIS WebSocket continuous job 시간당 비용** — Performance Optimized serverless SKU 정확 가격, $700 credit 영향 계산 (Sprint 4 진입 전)
4. **Genie Slack 통합 limit/SLA** — Public Preview라 production rate-limit/downtime 위험. fallback 시나리오 (SQL pre-canned) 사전 준비 필수
5. **OilPriceAPI 3 ticker = 3 calls 가정** — 실제 API endpoint가 batch 지원하는지 (Sprint 2 첫날 확인). 3 calls × 5min × 24h × 30day = ~26K calls/mo이 $19 plan 한도 안인지 확인

---

## 1.5 다음 단계 권장

1. **§1.1 Manual Step (팀 자격)** 해결: 팀 2-4명 확정 + Databricks partner 자격 확인 — 출전 자격 자체에 영향
2. Phase 2 critique에서 다룰 항목:
   - 시나리오 Brent pre-crisis 가격 보정 ($80 → $68-70)
   - 5축 심사기준 (Business Applicability / Creativity / UX / Technical / Storytelling) 별 leverage point + risk + 점수 추정
   - Track 1 Social Impact 키워드 (open data, societal problem) 시나리오에 충분히 노출되는지
3. Phase 3 architecture에서:
   - Lakebase JSONB/UUID 호환성 1차 확인 task 포함
   - Continuous job 비용 추정 별도 섹션
   - Genie fallback 디자인 명시
4. 도구 GA 변동 모니터링: 5/22까지 매주 docs.databricks.com release notes 1회 체크

---

## 1.6 Sources

### 해커톤
- [Building Intelligent Apps Hackathon (공식)](https://buildintelligentapps-databricks.com/) ← **확정**
- (참조용) [Built-On Databricks Startup Challenge 2026](https://www.databricks.com/blog/announcing-2026-built-databricks-startup-challenge) — 다른 hackathon
- (참조용) [Databricks Apps & Agents Hackathon for Good (MLH)](https://events.mlh.io/events/13878-databricks-apps-agents-hackathon-for-good)

### 도구
- [Databricks Apps docs](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/)
- [Apps Cookbook FastAPI](https://apps-cookbook.dev/docs/fastapi/getting_started/create/)
- [Genie Agent Mode 블로그](https://www.databricks.com/blog/introducing-genie-agent-mode)
- [Genie Conversation APIs PuP 발표](https://www.databricks.com/blog/genie-conversation-apis-public-preview)
- [Slack-Genie 통합 가이드](https://www.databricksters.com/p/integrate-slack-with-genie-natively)
- [Lakebase product](https://www.databricks.com/product/lakebase)
- [Lakebase Postgres docs](https://docs.databricks.com/aws/en/oltp/)
- [Lakebase Lakehouse Sync](https://docs.databricks.com/aws/en/oltp/projects/sync-tables)
- [Lakebase Autoscaling pricing](https://docs.databricks.com/aws/en/oltp/projects/pricing)
- [Agent Bricks Governed Platform](https://www.databricks.com/blog/agent-bricks-governed-enterprise-agent-platform)
- [Agent Bricks docs](https://docs.databricks.com/aws/en/generative-ai/agent-bricks/)
- [AI/BI Dashboard embed](https://docs.databricks.com/aws/en/dashboards/share/embedding)
- [AI/BI 2026 release notes](https://learn.microsoft.com/en-us/azure/databricks/ai-bi/release-notes/2026)
- [Foundation Model API supported models](https://docs.databricks.com/aws/en/machine-learning/foundation-model-apis/supported-models)
- [Proprietary FM Serving pricing](https://www.databricks.com/product/pricing/proprietary-foundation-model-serving)
- [Declarative Automation Bundles](https://docs.databricks.com/aws/en/dev-tools/bundles/)
- [Serverless Compute 진화](https://www.databricks.com/blog/evolution-data-engineering-how-serverless-compute-transforming-notebooks-lakeflow-jobs)
- [Modern Data Engineering 2026](https://jamesm.blog/data-engineering/modern-data-engineering-databricks-2026/)

### 호르무즈
- [2026 Strait of Hormuz crisis (Wikipedia)](https://en.wikipedia.org/wiki/2026_Strait_of_Hormuz_crisis)
- [2026 US naval blockade of Iran (Wikipedia)](https://en.wikipedia.org/wiki/2026_United_States_naval_blockade_of_Iran)
- [House of Commons Library briefing](https://commonslibrary.parliament.uk/research-briefings/cbp-10636/)
- [CRS R45281 (Hormuz commodities)](https://www.congress.gov/crs-product/R45281)
- [Britannica 2026 Iran war](https://www.britannica.com/event/2026-Iran-war)
- [EIA Q1 2026 oil prices](https://www.eia.gov/todayinenergy/detail.php?id=67424)
- [CNBC 2026-05-07 oil prices](https://www.cnbc.com/2026/05/07/oil-prices-today-trump-iran-strait-of-hormuz-us-crude-brent-.html)
- [Time 2026-05-05 Rubio statement](https://time.com/article/2026/05/05/rubio-iran-epic-fury-over-strait-hormuz/)
- [Al Jazeera 2026-05-06](https://www.aljazeera.com/news/2026/5/6/operation-epic-fury-has-ended-is-the-iran-war-over)
- [CNN traffic 시각화](https://www.cnn.com/2026/04/29/world/iran-war-gulf-hormuz-shipping-maps-intl-vis)
