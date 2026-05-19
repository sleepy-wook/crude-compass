# Crude Compass P0 실행 계획 (compact-safe note)

> 날짜: 2026-05-19 (1차 작성) → 2026-05-19 update (Supervisor/endpoint 실 상태 반영)
> 목적: codex 4개 문서 평가 + 우리 코드 base 실제 검토 + Databricks 4기능 reality check 결과.
> 다음 대화 compact 후에도 이 파일만 읽으면 즉시 동기화 가능하도록 설계.
> 참고:
> - 진단서: `docs/agentic_redesign_review.md`
> - 처방전: `docs/frontend_restructure_proposal.md`
> - 컴포넌트 매핑: `docs/frontend_component_mapping.md`
> - 실행 순서: `docs/frontend_p0_execution_order.md`
> - 검증표: `docs/home_validation_checklist.md`

---

## 0. 2026-05-19 update — Databricks 4기능 reality check

### Hackathon 공식 정보 (research agent 확정)
- **Track 2개** (Social Impact / Business Impact) × 3 언어. "Track 3/4" 오해.
- **심사 5개 criteria × 각 20%**: Business Applicability / Creativity / UX / **Technical Capability (4기능)** / Data Storytelling
- **제출물**: 5분 데모 영상 (사실상 유일 deliverable, AngelHack portal 확인 필요)
- **1등 상금**: USD 4,000 + DAIS 2027 ticket + USD 3,000 training coupon

### Workspace 실 상태 (D-1 확인)
- **Supervisor Agent ✅ 이미 등록**: `crude-compass-supervisor` (Multi-Agent)
- **Endpoint URL**: `https://dbc-437c7d62-5826.cloud.databricks.com/serving-endpoints/mas-ba3fbcb5-endpoint/invocations`
- **3 subagent**:
  - `Crude Oil Market Analysis` (Genie Space)
  - `crude-compass-ka` (Knowledge Assistant — OPEC MOMR 2019~2026 / Saudi production / demand forecast / supply-demand balance / OPEC+ compliance / 지정학 risk / 재고/정유 분석)
  - `mission_plan_advice` (UC Function — `ai_query('databricks-claude-haiku-4-5', concat(...))` Bidirectional decision framework)
- **Agent Bricks 자산 2개**: Supervisor + KA (사용자 (b) confirm)

### Backend wiring (코드 verify, D-1 deploy 완료)
- `services/supervisor.py`: Responses API + `databricks_options.return_trace=true` + tools_used 파싱 + `_clean_answer()` 디버깅 흔적 (D-1 00:22 KST log)
- `api/supervisor.py`: `/query` + `/health` + Genie fallback
- ENV gate: `SUPERVISOR_ENDPOINT_NAME`
- **이미 production 수준** — 새로 작성할 backend 코드 없음

### narrative 정직성 검증 (research agent 보고)
- ❌ ~~"Mission Plan FMA = Agent Bricks"~~ — 부정확. FMA chat completion은 Mosaic AI Model Serving.
- ✅ **`mission_plan_advice` UC Function** = 동일 로직을 SQL UC Function으로 wrap. Supervisor의 valid subagent type. **narrative 정직**.
- ✅ Direct path (recommend_now) + Supervisor path (investigation) — 둘 다 명확하고 정직

### 최종 narrative 한 줄 (확정)
> Databricks **Apps** 위 manager-facing decision room.
> **Agent Bricks Supervisor** (`crude-compass-supervisor`)가 **Genie** (Crude Oil Market Analysis) + **Knowledge Assistant** (`crude-compass-ka`, OPEC document evidence) + **UC Function** (`mission_plan_advice`, Bidirectional decision advisor) 3개 subagent를 orchestration해 case를 운영하고,
> **Lakebase**에 case state / approval / monitoring을 기록하면서 human-in-the-loop workflow를 이어간다.

### Agent Bricks Supervisor Agent 사실 정정
- Supervisor Agent **2026-02-10 GA** (Beta 아님). 심사위원 친숙.
- 5 subagent type: Genie / Knowledge Assistant / Model Serving / **UC Functions** / MCP servers. UC Function이 valid type.

---

## 1. 핵심 결정 (이미 합의됨)

### 방향성 100% 동의
- "recommendation app처럼 보인다" 진단 정확
- IA 4-탭 (Decision Room / Case File / Investigation / Market Watch) 채택
- 신규 컴포넌트 2개 (AgentActivityTimeline + SuggestedNextActions) 추가
- 4기능 (Apps / Lakebase / Genie / Agent Bricks) 역할 narrative 전면화

### 핵심 절충 — "Mission" rename 범위
- ❌ Type-safe full rename (Mission → DecisionCase) 시도 X — type/API/backend/Lakebase cascading risk 큼
- ✅ **Visible text + nav label + StatusPill display + 페이지 헤더만 rename** — 매니저/judge 시각으로 70%+ shift 달성
- 코드 식별자 (`Mission` interface, `mission_id`, `mission_type`, `/api/missions/*`, `useMissionConfirm`) 모두 그대로

### Dead code 정리 ✅ 완료 (2026-05-19)
- ~~`frontend/src/components/MissionHero.tsx`~~ (572 LOC) → 삭제
- ~~`frontend/src/components/SupervisorChat.tsx`~~ (130 LOC) → 삭제
- ~~`frontend/src/components/OpenDataBadge.tsx`~~ (105 LOC) → 삭제
- 총 807 LOC removed. `utils.ts` 안 comment 1줄 정리.

---

## 2. P0 첫 10 파일 (실행 순서)

| # | 파일 | LOC | 작업 | 시간 |
|---|---|---|---|---|
| 1 | `components/Sidebar.tsx` | 97 | nav label 4개 rename: 오늘→Decision Room / 시장 데이터→Market Watch / AI 도우미→Investigation / 내 결정 기록→Case File | 20분 |
| 2 | `components/StatusPill.tsx` | 59 | display text rename (proposed→검토 대기, active→진행 중, pivoted→재편) | 20분 |
| 3 | `lib/utils.ts` | 133 | `termSpotLabel`/`statusLabel`/`missionTypeLabel` 한글 표시 정리 | 20분 |
| 4 | `pages/Dashboard.tsx` | 272 | 헤더 카피 + Mission summary mini → Open Case Summary rename + AgentActivityTimeline 삽입 | 1.5h |
| 5 | **신규** `components/AgentActivityTimeline.tsx` | — | mission.created_at + mission_type 기반 시뮬레이션 timeline 6-8 event | 2h |
| 6 | **신규** `components/SuggestedNextActions.tsx` | — | 기존 3 button + Keep Watching / Ask for More Evidence / Re-check Later 3개. modify endpoint로 mapping | 1h |
| 7 | `pages/MissionsPage.tsx` | 745 | h1/subtitle rename + DecisionChainPanel 강화 + SuggestedNextActions 통합 | 2h |
| 8 | `pages/AskPage.tsx` | 460 | 헤더 rename (Investigation) + 현재 case context badge + Sample 응답 wrapper (answer → evidence/findings) | 1.5h |
| 9 | `components/Bidirectional3Zone.tsx` | 216 | "양방향 신호 강도" → Case Signal Status framing 또는 sub-label 강화 | 30분 |
| 10 | `pages/MarketDataPage.tsx` | 96 | 헤더 rename + 각 카드 mini sub-label "Case relevance" 추가 | 30분 |

**총 ~10시간** (3일 안 가능).

---

## 3. 재사용 자산 (15개, 그대로 살림)

| 컴포넌트 | 새 역할 | 변경 비용 |
|---|---|---|
| `SimilarPastWidget` | Historical Analogs | label 1개 |
| `Bidirectional3Zone` | Case Signal Status | 헤더 text |
| `MissionSplitBar` | Decision Draft Split | 0 (이미 영문 Term/Spot) |
| `SignalContribution` | Evidence Summary | label |
| `TimeHorizonBreakdown` | Time Horizon Evidence | 0 |
| `MultiAgentTrace` | Supervisor Orchestration | 0 (Agent Bricks 핵심) |
| `OpecCitation` | Document Evidence (Knowledge Assistant) | sub-label |
| `NewsTopList` | Event Evidence | 0 |
| `DecisionChainPanel` (MissionsPage 내부) | Activity Timeline baseline | AgentActivityTimeline과 통합 |
| `IntradayTicker` / `IntradayChart` | Market Watch live strip | 0 |
| `PatternScoreLine` | Signal History | 0 |
| `PriceLineChart` / `FxLineChart` | 그대로 | 0 |
| `BacktestTimeSlider` | Investigation 안의 검증 도구 | 0 |
| `OspCycleChip` (Dashboard 내부) | Decision Cycle indicator | 0 |
| `ReactiveAlertToast` | Case Update Event | toast text |

---

## 4. 3일 안에 하지 말아야 할 것 (10개)

1. **Mission → DecisionCase type-safe full rename** — type/api/backend/Lakebase cascading
2. **Backend schema 신규** (monitoring_rules, watch_state, case_lifecycle_event) — Lakebase ALTER + SP owner 권한
3. **AgentActivityTimeline real backend persistence** — Lakebase에 activity event table 추가 X. **frontend simulation으로 demo**
4. **Slack interactive 5종 next action** — Slack Bolt handler 큰 작업
5. **SupervisorChat 컴포넌트 재활성화** — 현재 dead. AskPage inline 사용. 그대로 둠
6. **MissionHero 컴포넌트 부활** — 572 LOC dead
7. **자체 chat UI 신규 디자인** — 현재 ChatTurnView 충분
8. **Investigation에서 free-form chat 완전 제거** — chat은 유지, framing만 case-bound
9. **route path rename** (/missions → /cases) — bookmark/share/WS 깨짐
10. **전체 디자인 시스템 재정의** — tokens.ts 안정

---

## 5. 신규 컴포넌트 명세

### A. `AgentActivityTimeline`

**목적**: recommendation → workflow 전환의 핵심. "agent가 case를 운영 중" 시각화.

**위치**: Dashboard (Decision Room) + MissionsPage detail (Case File)

**데이터 source**:
- mission record의 field 기반 시뮬레이션 (D-3 안 backend schema 추가 X)
- `created_at` + `mission_type` + `pattern_score` + `confirmed_at` 등으로 derive

**event 예시** (mission이 active일 때 표시할 6-8개):
```
1. [created_at - 12분] Supervisor: 신호 spike 감지 (위기 강도 N)
2. [created_at - 8분]  Genie: 가격/환율/OPEC 데이터 조회 완료
3. [created_at - 5분]  Knowledge Assistant: GDELT/MOMR 문서 검색
4. [created_at - 3분]  Similar Case Tool: 7년 백테스트 4건 retrieve
5. [created_at]        Mission Plan Agent: draft 생성 (Term/Spot N%)
6. [confirmed_at]      매니저 회부 (via Apps 또는 Slack)
7. [confirmed_at + 1h] 트레이딩 데스크 검토 시작
8. [next check]        다음 review trigger (D+N OPEC 발표)
```

**Layout**: 좌측 시간/icon + 우측 actor + action + 결과 1줄 + 펼치기.

### B. `SuggestedNextActions`

**목적**: binary approve/reject → multi-action workflow.

**위치**: Dashboard (Mission mini) + MissionsPage detail.

**액션 6개**:
| 액션 | 의미 | Backend mapping |
|---|---|---|
| Approve Draft | 권고 그대로 기록 | `POST /missions/:id/confirm` (기존) |
| Adjust Draft | 조정 후 기록 | `modify` + `confirm` chain (기존) |
| Dismiss Case | 거절 | `POST /missions/:id/reject` (기존) |
| **Keep Watching** | 모니터링 유지 | `modify(duration_days=다음 7일)` (기존 endpoint 재사용) |
| **Ask for More Evidence** | Investigation 자동 이동 + 현재 case context pre-fill | UI navigate to `/ask?case_id=N` |
| **Re-check Later** | 다음 review timestamp 설정 | `modify(duration_days=14)` 또는 frontend defer |

---

## 6. P1 / P2 (시간 남으면)

- **P1**: AskPage case context auto-inject, Market Watch evidence connection dynamic, Slack interactive 일부 확장
- **P2**: Case File full dossier (approval/revision/monitoring 통합), Activity Timeline real backend persistence (Lakebase event table)

---

## 7. 최종 GO 시점 체크리스트

P0 작업 시작 전 확인:
- [ ] 기존 mission 1건 active 상태 유지 (테스트용)
- [ ] dead code 3 file 삭제 (5분)
- [ ] semantic layer rename 범위 확정 (visible text only)
- [ ] AgentActivityTimeline 시뮬레이션 데이터 schema 결정

P0 작업 끝 후 검증:
- [ ] 4 페이지 visual check (Chrome MCP)
- [ ] `home_validation_checklist.md` Phase 1-3 통과
- [ ] demo 5분 rehearsal — 4기능 (Apps/Lakebase/Genie/Agent Bricks) 30초에 설명 가능

---

## 8. compact 후 즉시 동기화 키워드

다음 대화 시작 시:
```
Read docs/p0_implementation_plan.md
```
한 줄이면 이 작업 컨텍스트 전부 복원됨.

추가 컨텍스트 필요 시:
```
Read docs/frontend_p0_execution_order.md
Read docs/frontend_component_mapping.md
```

---

끝.
