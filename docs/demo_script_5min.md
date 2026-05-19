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

### 0:30 ~ 1:30 — Decision Room (Apps + Lakebase + Agent Bricks 동시 visible, 60초)

**[화면 녹화: /]**

> "첫 화면 — Decision Room. **Databricks Apps** 위 manager-facing decision room으로 정의했습니다."

(스크롤 — top header: "DECISION ROOM" / "오늘의 결정실")

> "현재 위기 시그널 강함 10/10. **Agent Bricks Supervisor**가 Pattern Score 100을 감지하고 case를 열었습니다."

(MissionSummaryCard 짚기)

> "위험방어 case — 장기계약 비중을 60%에서 75%로 올리라는 권고."

(SuggestedNextActions 6 chip 짚기)

> "여기가 차별화 포인트입니다. **approve/reject 같은 binary가 아닌 6가지 agentic next action**: Approve Draft, Adjust Draft, Dismiss Case, Keep Watching, Ask for More Evidence, Re-check Later."

(스크롤 down — Agent Bricks 활동 section)

> "**가장 중요한 부분 — Agent Bricks 활동 이력**. 이것이 Agent Bricks orchestration이 실제로 작동한 흔적입니다."

(timeline 5+ events 짚기)

> "weighted_signal UC Function이 Pattern Score 계산, Supervisor가 case 개시, Mission Plan UC Function이 draft 생성, 매니저가 승인, 매니저가 조정. **각 event가 Lakebase agent_activity_events table의 row로 영구 persisted**. 단순 frontend 시뮬이 아닙니다."

---

### 1:30 ~ 2:30 — Investigation (Agent Bricks Supervisor + Genie + KA 동시 visible, 60초)

**[Ask for More Evidence 클릭 → /ask?case_id=...]**

> "**Ask for More Evidence** 클릭하면 case context를 그대로 들고 Investigation으로 이동합니다."

(case context badge 짚기)

> "현재 조사 중 case 정보가 자동 주입돼 있고, sample query 6개가 case-bound 질문 set으로 자동 교체됩니다."

(Agent Bricks Supervisor orchestration diagram 짚기)

> "여기가 4기능의 정수입니다. **Agent Bricks Supervisor** (`crude-compass-supervisor`)가 3개 subagent를 orchestration합니다:
> - **Genie** (`Crude Oil Market Analysis`) — structured market specialist
> - **Knowledge Assistant** (`crude-compass-ka`) — OPEC MOMR document evidence agent
> - **mission_plan_advice** (UC Function) — Bidirectional decision advisor"

(시연: "왜 이 case가 열렸지?" 클릭)

> "Supervisor에게 자연어로 질문하면 — **실제 endpoint 호출**입니다. simulated trace 아닙니다."

(응답 + tools_used 보여주기)

> "응답이 오면 어떤 subagent가 호출됐는지 trace로 보입니다. 그리고 — 이 호출 자체도 Lakebase agent_activity에 4 event 추가됩니다."

(Decision Room으로 돌아가서 timeline 추가된 거 보여주기)

> "보시다시피 방금 한 Investigation이 timeline에 누적됐습니다. Agent가 일했다는 증거가 case memory에 영구 기록됩니다."

---

### 2:30 ~ 3:30 — Case File (Lakebase case memory + dossier, 60초)

**[Case File 클릭 → /missions/...]**

> "**Case File** — 이 case의 dossier. Lakebase가 case state·approval·revision·monitoring을 어떻게 잇는지 보여주는 surface."

(detail panel 짚기)

> "Decision Chain 5단계 — AI 권고 → 매니저 회부 → 트레이딩 데스크 검토 → 리스크 위원회 → OSP 실행. AI 권고는 단순 1-click이 아니라 회사 결정 흐름의 input입니다."

(스크롤 down → 매니저의 다음 행동 + full timeline)

> "그리고 여기 **full mode Agent Bricks 활동 이력** — vertical timeline으로 모든 event를 시간 순으로. weighted_signal, Supervisor, Mission Plan, 매니저 승인, 매니저 조정 — **9개 actor 타입**이 색·icon별로 구분됩니다."

(방향 전환 / 조정 demo — optional)

> "case가 진행되다 시그널이 반대로 가면 매니저가 방향 전환할 수 있고, 그 revision도 timeline에 누적됩니다."

---

### 3:30 ~ 4:00 — Market Watch (evidence board, 30초)

**[Market Watch 클릭 → /market]**

> "**Market Watch** — 단순 데이터 페이지가 아닙니다. **Agent Bricks 근거판** — Supervisor가 참조한 원천 데이터 surface."

(SoWhat 카드 짚으면서 스크롤)

> "각 차트마다 어떤 agent가 어떻게 참조했는지 명시:
> - 5분 intraday — Reactive Trigger가 spike 감지하면 case re-eval
> - 가격 + FX — Genie가 target_pct 계산 input
> - OPEC MOMR + GDELT — Knowledge Assistant가 document evidence
> - Pattern Score 7년 — weighted_signal UC Function의 동일 backtest 75% hit rate 검증 함수"

---

### 4:00 ~ 4:30 — Slack interactive (optional, 30초)

**[Slack 채널 짚기]**

> "Slack 채널에서도 동일한 6-action workflow를 사용할 수 있습니다."

(만약 작동하면) Slack에서 Approve 클릭 → Apps에 5초 안 sync 보여주기

---

### 4:30 ~ 5:00 — Closing (4-feature summary + Track 1 impact, 30초)

**[슬라이드: 4기능 매핑]**

> "정리하면 — **4 features 모두 정직하게 활용**:
> - **Databricks Apps** — manager-facing decision room (단순 호스팅 X)
> - **Lakebase** — operational case memory + agent_activity_events orchestration timeline (단순 DB X)
> - **Genie** — Supervisor의 structured market specialist subagent (단순 NL2SQL X)
> - **Agent Bricks** — Supervisor + Knowledge Assistant 등록 + 3 subagent orchestration (단순 이름 X)"

**[슬라이드: closing message]**

> "**Bloomberg 없이도 정유 빅5와 동일한 인텔리전스. 한국 5천만 국민 에너지 안보를 모두에게.**
>
> Crude Compass — Databricks Agent Bricks 기반 decision workflow."

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
