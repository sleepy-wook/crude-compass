# Crude Compass — 5분 데모 영상 스크립트

> 날짜: 2026-05-19 (D-3)
> 목적: Databricks APJ Hackathon 2026 Track 1 (Social Impact, Open Data) Korean track 1등 목표.
> 5분 video가 사실상 유일 deliverable — Data Storytelling (20%) + Technical Capability (20%) 합 40% 결정.
>
> 심사 5축 매핑:
> - **Business Applicability** (20%) — K-Petroleum 정유사 페르소나, Term/Spot 의사결정, 73.5% 중동 의존
> - **Creativity & Innovation** (20%) — Bidirectional Pattern Detection + Agent Bricks orchestration
> - **UX & Insights** (20%) — Decision Room / Case File / Investigation / Market Watch 4-tab IA + 6-action workflow
> - **Technical Capability** (20%) — Apps + Lakebase + Genie + Agent Bricks 4기능 통합
> - **Data Storytelling** (20%) — open data democratization narrative

---

## 영상 흐름 (5분, 슬라이드 + 화면 녹화 혼합)

### 0:00 ~ 0:30 — Opening (Problem + Track 1 narrative)

**[슬라이드 1: 한국 원유 의존도]**

> "한국은 원유의 **73.5%를 중동에서 수입**합니다. 호르무즈 봉쇄가 한 번 터지면 5천만 국민의 에너지가 흔들립니다."

**[슬라이드 2: 격차]**

> "정유 빅5는 Bloomberg, Platts, Vortexa 같은 유료 인텔리전스를 연 수천만원에 사용합니다. 하지만 중소 정유사·석화 trading desk·정책 연구자·정부 분석관은 같은 시스템이 없습니다."

**[슬라이드 3: 제품 한 줄]**

> "**Crude Compass는 100% 공개 데이터만으로** 정유사 매니저가 텀/스팟 비중 의사결정을 받을 수 있는 시스템입니다. Track 1 — Open Data Democratization."

(나레이션 25초, 슬라이드 3장)

---

### 0:30 ~ 1:00 — Live AI Pulse 30초 dwell (시간 축 narrative, 30초)

**[화면 녹화: /]**

> "첫 화면 — Decision Room. **Databricks Apps** 위 manager-facing decision room. 우상단 **Live AI Pulse**를 30초 동안 가만히 보겠습니다."

(LivePulseStrip 스크롤 멈추고 30초 dwell — event 새로 들어오는 거 보여주기)

> "cross-mission agent stream. supervisor가 case 열고, weighted_signal UC Function이 pattern 계산하고, Knowledge Assistant가 document evidence 끌어오고 — **시스템이 잠시도 멈추지 않는다는 증거**. 각 event는 Lakebase `agent_activity_events`에 즉시 persist."

---

### 1:00 ~ 2:00 — Case Thread 풀스크롤 + raw expand (Lakebase memory 증거, 60초)

(MissionSummaryCard 짚기)

> "현재 위기 시그널 강함 10/10. **Agent Bricks Supervisor**가 Pattern Score 100을 감지하고 case를 열었습니다. 위험방어 case — 장기계약 비중 60% → 75%."

(SuggestedNextActions 6 chip 짚기)

> "**approve/reject 같은 binary가 아닌 6가지 agentic next action** — Approve, Adjust, Dismiss, Keep Watching, Ask for More Evidence, Re-check Later."

(스크롤 down — Agent Bricks 활동 section, **Case Thread 끝까지 풀스크롤**)

> "**Case Thread** — 이 case에 일어난 모든 agent event 시계열. weighted_signal → Supervisor case open → Mission Plan draft → 매니저 승인 → 매니저 조정."

(supervisor synthesized event "raw 펼치기" 클릭)

> "각 event를 펼치면 **Reasoning Path** — Supervisor가 왜 Genie를 호출했는지, 왜 KA가 필요했는지 self-narration. 그 아래에 raw metadata JSON. 단순 시뮬이 아닙니다 — `agent_activity_events` table에 row로 영구 기록."

---

### 2:00 ~ 3:00 — Investigation Trace-a-Signal 4-stage (Supervisor + Genie + KA, 60초)

**[Ask for More Evidence 클릭 → /ask?case_id=...]**

> "**Ask for More Evidence** 클릭하면 case context를 그대로 들고 Investigation으로 이동합니다."

(Trace-a-Signal 4-stage forensic view 짚기)

> "한 signal을 골라 **Trace-a-Signal Investigation** — bronze.news_articles에서 detected → silver.signal_classified에서 importance·direction scored → silver.signal_events_decayed lambda 감쇠 → gold.signal_contribution_30d 누적 기여. **4개 stage가 동일 signal_id로 join된 forensic view**. Lakehouse medallion이 실제로 어떻게 한 signal을 결정으로 변환하는지 시각화."

(Supervisor orchestration diagram 짚기)

> "오른쪽 — **Agent Bricks Supervisor** (`mas-ba3fbcb5-endpoint` deployed READY)가 3 subagent orchestration:
> - **Genie** — structured market specialist
> - **Knowledge Assistant** — OPEC MOMR document evidence
> - **mission_plan_advice** UC Function — Bidirectional decision advisor"

(시연: "왜 이 case가 열렸지?" 클릭)

> "자연어로 질문하면 — **실제 endpoint 호출**. 응답 + tools_used trace + reasoning_path. 그리고 이 호출 자체도 Lakebase에 event 4개 추가 — Case Thread에 즉시 누적."

---

### 3:00 ~ 4:00 — Slack interactive + Case File flash (60초)

**[Slack 채널 짚기]**

> "현장의 결정은 매니저가 책상에서만 하지 않습니다. Slack에서도 동일한 6-action workflow."

(Slack에서 Approve 클릭 → Apps에 5초 안 sync 보여주기 — Live AI Pulse에 새 event 들어오는 거 강조)

> "Slack Approve 클릭 — **5초 SLA 안에 Apps Decision Room에 sync**. 그리고 그 manager_decision event는 Lakebase agent_activity_events에 row로 기록 — 동일 case memory."

**[Case File 빠르게 짚기 → /missions/...]**

> "**Case File** — 이 case의 dossier. Decision Chain 5단계 — AI 권고 → 매니저 회부 → 트레이딩 데스크 → 리스크 위원회 → OSP 실행. AI 권고는 1-click 결정이 아니라 회사 결정 흐름의 input."

(full timeline 한 번 스크롤)

> "**full Case Thread** — 9개 actor 타입이 색·icon별로 구분, vertical timeline 영구 누적."

---

### 4:00 ~ 4:30 — Daily AI Loop dial (시간 축 closure, 30초)

**[Dashboard로 돌아가서 Daily Loop Clock 짚기]**

> "마지막 — **Daily AI Loop**. 24시간 원형 dial. 우상단의 시침을 보세요."

(DailyLoopClock 24h dial 짚기 — 각 시간대 dot 강조)

> "오늘 하루 동안 **12개 Lakeflow Job**이 언제 어떤 결과로 돌았는지 한눈에. gdelt 15분 cron이 96번 success, price 5분 cron, daily curation, OPEC MOMR, EIA — 모든 cron이 자동으로 시스템을 살아있게 유지합니다. **Crude Compass는 매니저가 보지 않을 때도 일하는 시스템**."

---

### 4:30 ~ 5:00 — Closing (Track 1 Social Impact wrap, 30초)

**[슬라이드: 4기능 매핑]**

> "**4 features 모두 정직하게 활용** — Apps (decision room), Lakebase (case memory + agent_activity_events), Genie (Supervisor subagent), Agent Bricks (`mas-ba3fbcb5-endpoint` deployed READY, Supervisor + KA + Genie + UC Function orchestration + reasoning_path self-narration)."

**[슬라이드: Track 1 Social Impact closing]**

> "**Bloomberg 없이도 정유 빅5와 동일한 인텔리전스. 100% 공개 데이터로.**
>
> 중소 정유사, 석화 trading desk, 정책 연구자, 정부 분석관 — 누구나 같은 시스템을 쓸 수 있습니다.
>
> **한국 5천만 국민 에너지 안보를 모두에게.** — Track 1 Open Data Democratization.
>
> Crude Compass."

(End)

---

## 시연 risk + 대비

| Risk | 발생 가능성 | 대응 |
|---|---|---|
| Supervisor cold start 30~60s 지연 | 중 | demo 30분 전 warm-up query 1회 |
| Lakebase serverless scale-to-zero | 중 | warm-up + 첫 GET /missions/active로 wake |
| Slack interactive 사용 불가 | 낮 | section skip (4:00~4:30 → closing으로 합침) |
| Genie warehouse cold start | 중 | warm-up + 4-tier fallback 자동 |
| AskPage Investigation 호출 timeout | 낮 | 180s timeout 안 정상 응답 / 안 되면 demo skip + 캐시된 응답 보여주기 |

## Demo 직전 체크리스트 (D-day 30분 전)

- [ ] Apps deploy 최신 commit 확인
- [ ] Supervisor endpoint warm-up: `POST /api/supervisor/query` with `{question: "ping"}` 1회
- [ ] Genie warm-up: `POST /api/genie/query` 1회
- [ ] Lakebase warm-up: `GET /api/missions/active` 1회
- [ ] Slack channel reaction 1회 (token rotation)
- [ ] 5분 영상 한 번 dry run 끝까지
- [ ] OBS / screen recorder 화면 1920x1080 확인
- [ ] 마이크 input level / 마우스 cursor 추적 설정

## 4기능 question 대비 — 30초 안 답 가능

- **"Apps를 어떻게 활용했나?"** → "manager-facing decision room. Vite + FastAPI single container. WebSocket real-time sync."
- **"Lakebase를 어떻게 활용했나?"** → "case memory + agent_activity_events orchestration timeline. OAuth U2M JWT, psycopg3 pool, optimistic concurrency."
- **"Genie를 어떻게 활용했나?"** → "Agent Bricks Supervisor의 structured market specialist subagent. NL2SQL이 아니라 specialized agent로 호출."
- **"Agent Bricks를 어떻게 활용했나?"** → "Supervisor Agent + Knowledge Assistant 2개 등록. Supervisor가 Genie + KA + mission_plan_advice UC Function 3개 subagent orchestrate. Endpoint 실 호출 + return_trace로 tools_used 받음."

---

끝.
