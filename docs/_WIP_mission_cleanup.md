# WIP — Mission 모델 제거 작업 (compact-safe handoff)

> 2026-05-21 작성. **이 작업이 완전히 끝나고 빌드/화면 검증까지 완료되면 이 파일(`docs/_WIP_mission_cleanup.md`)을 삭제할 것.**
> reports 모델 전환 후 남은 mission 잔재를 단계적으로 제거하는 작업의 진행 상황·계획 기록.

---

## 배경 — 왜 제거하나

프로젝트는 옛 "missions" 모델 → 새 "reports" 모델로 전환 완료. mission CRUD 코드는 남아있지만 **데이터가 흐르지 않는 빈 껍데기**다 (sub-agent 감사 + 직접 코드 검증으로 확인).

### 검증 결과 (mission이 dead인 증거)
- `case_id` 링크를 거는 곳: `SelectedCaseDetail`(import nowhere=dead) + `SuggestedNextActions`(MissionsPage 전용)뿐 → AskPage `useMission(caseId)`는 실제로 caseId를 못 받음.
- `reactive.alert` publish: backend에 **0건** → `ReactiveAlertToast`는 안 오는 이벤트 무한 대기 = dead.
- Dashboard는 `<Bidirectional3Zone topMission={null}>` 고정 → mission 데이터 안 씀.
- `missionsActive`는 Sidebar prefetch(/missions nav 없음) + MissionsPage(stranded)에서만.
- `CaseThread`/`CaseThreadEntry`는 MissionsPage 전용 체인.
- mission 생성 자체가 없음 (reports 모델이 대체). mission.* WS 이벤트도 안 발생.

### ⚠️ 이름만 mission이고 실제로 살아있는 것 — 절대 건드리지 말 것
1. **`mission_type`** = `gold.daily_risk_score`의 **zone 컬럼**(HEDGE/OPPORTUNITY/NONE, 가격 기반). job_curation이 매일 생성. `pattern.py`·`TopBar`·`Bidirectional3Zone`이 사용. mission 객체가 아니라 pattern score zone 라벨. **유지.**
2. **`useMissionsWebSocket`** (`/api/ws/missions`) = WS 연결 status 채널. mission.* 이벤트는 죽었지만 "실시간" 연결 표시에 쓰임. 제거 시 TopBar status·Dashboard lastEventAt 영향 → pulse WS(`/api/ws/pulse`, 살아있음)로 대체하거나 status만 유지.

### 유지(살아있는 핵심)
reports / daily_reports / agent_activity / pulse WS / Genie / Agent Bricks Supervisor / Slack(report·daily 알림) / market_memory(SimilarPastWidget — 의도적 유지).

---

## 제거 단계 (각 단계마다 `npx tsc --noEmit` + backend import 검증 + 커밋)

### 1단계 — 순수 dead 컴포넌트 (의존 없는 잎, 위험 0)
어디서도 import 안 됨 (frontend agent 확인):
`SelectedCaseDetail`, `ActionQueue`, `CaseRow`, `MonitoringStrip`, `DeltaStrip`, `DailyLoopClock`, `SignalContribution`, `TimeHorizonBreakdown`, `SimulationScenarios`, `IntradayTicker`, `Glossary`(GlossaryModal 포함)
+ `ReactiveAlertToast`(reactive.alert publish 0) — 단 호출부(어디서 렌더되는지) 확인 후.

### 2단계 — dead query hooks / api 메서드
hooks(`queries.ts`): `useBacktestResults`, `useDecisionQueue`, `useDecisionLastSeen`, `useDecisionDelta`, `useDecisionTouch`, `useJobRunsToday`, (`useSignalLifecycle` — consumer 재확인)
api(`api.ts`): `backtestResults`, `signalLifecycle`, `decisionRoom*`(queue/lastSeen/touch/delta), `genieQuery`, `missionsAll`, `missionRecommendNow`, `curationStatus`, `dailyReportByDate`
+ 대응 queryKeys + 고아 type import (`BacktestResults`, `GenieQueryResponse`, `DeltaEvent`)

### 3단계 — MissionsPage 체인
`MissionsPage`, `CaseThread`, `CaseThreadEntry`, `SuggestedNextActions` 삭제 + `App.tsx`의 `/missions`·`/missions/:id` route 제거.

### 4단계 — 호출부 정리 (live 페이지에서 mission 의존 제거)
- `AskPage`: `useMission(caseId)` + `CaseChip` + caseContextPrefix 제거 (caseId 안 옴).
- `Dashboard`: `useMissionsWebSocket` 처리, `Bidirectional3Zone topMission` prop 제거.
- `TopBar`: `useMissionsWebSocket` status → pulse WS 기반으로 교체 or 단순화. `decideMode(cur.mission_type)`는 zone이라 **유지**.
- `Bidirectional3Zone`: `topMission` prop + `Mission` import 제거 (zone 로직은 유지).
- mission mutation hooks(`useMissionConfirm/Reject/Pivot/Modify`, `useMissionActivity`, `useMission`, `useMissionsActive`) 제거.

### 5단계 — Backend
삭제 후보: `api/missions.py`, `api/decision_room.py`, `api/demo.py`(mission 의존), `schemas/mission.py`, `db/repositories/missions.py`, `db/repositories/last_seen.py`, `app/store.py`(in-memory MissionStore/EventBus), `services/mission_plan.py`, `services/simulation.py`, `services/slack_bus_subscriber.py`, `services/report_ai_decision.py`(Phase 9 stub), `api/ws/missions.py`
→ `main.py`에서 해당 router include + lifespan(slack_bus_subscriber, store) 정리.
- slack.py: mission_* action 핸들러 제거 (report_* 는 유지).
- ⚠️ `db/repositories/backtest.py`는 `pattern.py` market memory가 사용 → **유지** (확인 후).

### 6단계 — Databricks (이미 일부 완료)
- dead notebooks: `job_backtest_compute.py`, `job_backtest_llm.py`, `job_backtest_seed.py`
- dead jobs yml: `backtest_compute.yml`, `backtest_llm.yml`, `backtest_seed.yml`
- `gold.sql` 죽은 객체 주석 정리. `lakebase.sql`의 missions/decisions/pivot_history 테이블 (mission_type zone 컬럼은 daily_risk_score에 있고 유지).

### 7단계 — 최종 검증
- `npx tsc --noEmit` clean
- backend 전체 import smoke test
- 화면: 의사결정/보관함/시황/자료실/조사 5개 메뉴 정상 + console error 0
- 검증 완료 시 **이 문서 삭제 + 커밋**.

---

## 이번 세션에서 이미 완료된 것 (참고)
- Investigation 스트리밍 버그(stale closure) + markdown(heading/step boundary/table/footnote/agentic 서두) fix
- 비용 최적화: price 30분, warehouse auto_stop 10분, Lakebase scale-zero, pulse polling→WS
- 성과/백테스트 페이지 폐기, dead scripts/docs 정리, 문서 최종본(`crude_compass_final_scenario.md`)
- Sidebar 한글 통일(의사결정/보관함/시황/자료실/조사)
- Slack report 알림(트리거 채널 + 일일 전용 채널 C0B55UA42J1 + 활성화/기각 버튼)
- 빌드 pnpm 통일, git 히스토리 secret(.env.bak) 제거
- 의사결정 detail UI: markdown 렌더 + sub-agent 한글 라벨 + 관련 신호 뉴스 링크
- OSP 배지 제거, Agent Bricks 라벨 한글화, 보관함 default→활성화, market memory 배너 제거

## 현재 git 상태
`main` = origin/main 동기화 (마지막 커밋 `e6e3c3b`). 미커밋 없음.

---

**다시 강조: 이 작업 완료 + 검증 끝나면 `docs/_WIP_mission_cleanup.md` 삭제할 것.**
