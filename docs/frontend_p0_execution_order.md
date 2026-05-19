# Crude Compass P0 프론트엔드 실행 순서 문서

> 날짜: 2026-05-19  
> 목적: `docs/frontend_restructure_proposal.md`와 `docs/frontend_component_mapping.md`를 실제 작업 순서로 내리기 위한 문서다.  
> 범위: 남은 3일 안에 반드시 손대야 하는 프론트엔드 P0 항목만 다룬다.  
> 참고:
> - 진단서: `docs/agentic_redesign_review.md`
> - 구조 개편안: `docs/frontend_restructure_proposal.md`
> - 컴포넌트 매핑: `docs/frontend_component_mapping.md`
> - 최종 점검표: `docs/home_validation_checklist.md`

---

## 1. 이 문서의 역할

이 문서는 "무엇을 바꿔야 하는가"를 다시 설명하는 문서가 아니다.

이 문서의 질문은 아래와 같다.

> "좋다. 그럼 **실제로 어떤 순서로 손대야 가장 적은 리스크로 구조를 바꿀 수 있는가?**"

즉 이 문서는:

- P0 범위의 실제 작업 순서를 정하고
- 어떤 변경이 다른 변경의 선행 조건인지 정리하고
- 중간에 구조가 꼬이지 않도록 의존관계를 줄이는

**실행 순서 문서**다.

---

## 2. P0의 목표

P0에서 반드시 달성해야 하는 것은 아래 5가지다.

- 첫 화면이 더 이상 recommendation dashboard가 아니라 `Decision Room`처럼 보일 것
- `Mission` 중심 용어가 `Decision Case` 중심 용어로 바뀔 것
- `Ask`가 generic chatbot이 아니라 `Investigation`처럼 보일 것
- Agent Bricks orchestration이 화면에서 더 분명히 보일 것
- judge가 봤을 때 Apps / Lakebase / Genie / Agent Bricks 역할을 제품 흐름 속에서 설명할 수 있을 것

즉 P0는 "예쁘게 고친다"가 아니라,

> **제품의 첫인상과 서사를 바꾸는 작업**

이다.

---

## 3. P0 작업 순서

## Step 1. 정보구조와 라우팅 이름부터 바꾼다

### 대상 파일
- `frontend/src/components/Sidebar.tsx`
- `frontend/src/App.tsx`
- 필요 시 `frontend/src/components/Layout.tsx`

### 해야 하는 일
- 좌측 네비게이션 또는 상단 메뉴 기준 명칭을 아래로 정리한다
  - `Decision Room`
  - `Case File`
  - `Investigation`
  - `Market Watch`
- 기존 `Ask`, `Mission`, `Dashboard` 용어를 사용자 노출 레벨에서 정리한다
- route path는 꼭 즉시 바꾸지 않아도 되지만, 화면 title / nav label / breadcrumb는 먼저 맞춘다

### 왜 먼저 하냐
- 내비게이션 이름이 바뀌지 않으면 이후 페이지를 바꿔도 전체 인상이 안 바뀐다
- semantic layer를 먼저 바꿔야 하위 컴포넌트 카피도 일관되게 수정할 수 있다

### 완료 조건
- 사용자가 앱에 들어왔을 때 `Mission`과 `Ask`라는 과거 개념보다 새 IA가 먼저 보인다

---

## Step 2. 상태 용어와 공통 semantic layer를 바꾼다

### 대상 파일
- `frontend/src/components/StatusPill.tsx`
- `frontend/src/lib/types.ts`
- `frontend/src/lib/utils.ts`
- mission status/type를 직접 렌더링하는 모든 페이지/컴포넌트

### 해야 하는 일
- `Mission` → `Decision Case`
- `mission type` → `decision direction`
- `active missions` → `open cases`
- `pivot history` → `revision history`
- `approve mission` → `approve draft`
- `reject mission` → `dismiss case`
- `pause/hold` 의미가 있으면 `keep watching` 계열로 재정렬

### 왜 지금 하냐
- 페이지 구조보다 먼저 semantic layer를 바꾸면, 이후 page rename과 카피 정리가 쉬워진다
- `StatusPill`은 작은 수정으로 전체 인상을 가장 크게 바꿀 수 있는 포인트다

### 완료 조건
- 대표 상태 텍스트만 봐도 recommendation workflow가 아니라 case workflow처럼 읽힌다

---

## Step 3. `Dashboard`를 `Decision Room`으로 재구성한다

### 대상 파일
- `frontend/src/pages/Dashboard.tsx`
- 재사용 후보:
  - `frontend/src/components/SimilarPastWidget.tsx`
  - `frontend/src/components/Bidirectional3Zone.tsx`
  - `frontend/src/components/MissionSplitBar.tsx`
  - `frontend/src/components/SignalContribution.tsx`
  - `frontend/src/components/StatusPill.tsx`

### 해야 하는 일
- 페이지 헤더를 `오늘의 결정`에서 더 명확한 `Decision Room` 톤으로 조정한다
- 현재 top mission summary를 `Open Case Summary`로 재해석한다
- current case가 왜 열렸는지를 보여주는 evidence summary를 더 전면에 배치한다
- `Agent Activity Timeline` 영역을 새로 추가한다
- `Suggested Next Actions` 영역을 새로 추가한다
- intraday market 성격이 지나치게 hero를 차지하지 않도록 억제한다

### 왜 중요하냐
- 첫 화면이 곧 제품 정체성이다
- 여기서 Agent Bricks orchestration, decision prep, manager action이 동시에 읽혀야 한다

### 완료 조건
- 첫 화면 한 장만 봐도 "이건 AI 추천 카드 앱"보다 "운영 중인 decision case를 관리하는 room"처럼 보인다

---

## Step 4. `MissionsPage`를 `Case File`로 바꾼다

### 대상 파일
- `frontend/src/pages/MissionsPage.tsx`
- 관련 컴포넌트 전반

### 해야 하는 일
- 페이지 제목/섹션명/버튼명을 전부 case vocabulary로 재작성한다
- case summary, evidence summary, approval history, revision history, monitoring state를 명확히 나눈다
- Slack에서 이뤄진 approval / pivot / follow-up 흔적을 이 페이지의 연속성 일부처럼 보이게 한다
- `Mission detail` 느낌을 줄이고 `Decision dossier` 느낌을 강화한다
- 단, P0에서는 완전한 dossier 완성보다 `summary + approval/revision history + monitoring state` 안정화가 우선이다

### 왜 이 단계가 4번째냐
- 새 메인 홈이 먼저 잡혀야 이 페이지의 역할이 자연스럽게 정리된다
- `Case File`은 메인에서 넘어온 open case의 상세 문서라는 성격이 분명해야 한다

### 완료 조건
- `Case File`은 요약 페이지가 아니라, "왜 이 case가 열렸고 어떻게 관리되고 있는가"를 설명하는 상세 문서처럼 보인다
- 단, P0에서는 모든 evidence panel을 다 담지 않아도 되며 과도한 확장은 피한다

---

## Step 5. `AskPage`를 `Investigation`으로 재포지셔닝한다

### 대상 파일
- `frontend/src/pages/AskPage.tsx`
- `frontend/src/components/SupervisorChat.tsx`
- `frontend/src/components/MultiAgentTrace.tsx`
- `frontend/src/components/OpecCitation.tsx`

### 해야 하는 일
- page title과 intro를 generic AI chat이 아니라 `Investigation` 성격으로 변경한다
- 예시 질문을 현재 case 기준 조사 질문으로 바꾼다
- `SupervisorChat` 응답 결과를 `answer`보다 `findings / evidence / conflicts / next consideration`처럼 보이게 정리한다
- `MultiAgentTrace`는 데모용 trace가 아니라 `Agent Bricks Supervisor orchestration evidence`처럼 보이게 정리한다
- 가능하면 현재 case context가 기본 주입되는 UX로 보이게 만든다

### 왜 중요하냐
- 이 페이지는 Apps / Genie / Agent Bricks / Knowledge Assistant를 가장 직접적으로 보여줄 수 있는 페이지다
- generic chat 느낌이 남으면 해커톤 메시지가 약해진다

### 완료 조건
- judge가 이 화면을 보고 "챗봇"보다 "조사/분석 워크벤치"로 이해한다

---

## Step 6. 최소 신규 컴포넌트 2개를 추가한다

### 신규 컴포넌트 A — `AgentActivityTimeline`

#### 목적
- 중간 orchestration step을 사용자에게 보이게 하기
- Agent Bricks를 "backend에 있는 무언가"가 아니라 "실제로 case를 운영하는 workflow"로 보이게 하기

#### 들어가야 할 내용
- case opened
- structured evidence checked
- document evidence retrieved
- similar cases found
- manager action requested
- monitoring started
- revision suggested

#### 우선 배치 위치
- `Dashboard.tsx`
- 이후 `MissionsPage.tsx`

### 신규 컴포넌트 B — `SuggestedNextActions`

#### 목적
- approve/reject 중심 UX를 벗어나기
- human-in-the-loop workflow를 더 agentic하게 보이게 만들기

#### 최소 액션 예시
- Approve Draft
- Adjust Draft
- Ask for More Evidence
- Keep Watching
- Re-check Later
- Dismiss Case

#### 우선 배치 위치
- `Dashboard.tsx`
- 이후 `MissionsPage.tsx`

### 왜 이 둘이 최소 필수인가
- 이 두 컴포넌트가 있어야 recommendation workflow가 아닌 agent workflow처럼 보이기 시작한다
- 큰 백엔드 변경 없이도 agentic한 인상을 크게 강화할 수 있다

---

## 4. 작업 순서 요약

실제 착수 순서는 아래처럼 가는 것이 가장 안전하다.

1. `Sidebar / App`에서 새 IA 이름 정리
2. `StatusPill / 공통 텍스트`에서 semantic layer 정리
3. `Dashboard`를 `Decision Room`으로 재구성
4. `AgentActivityTimeline` / `SuggestedNextActions` 추가
5. `MissionsPage`를 `Case File`로 재구성
6. `AskPage`를 `Investigation`으로 재구성
7. 시간이 남으면 `MarketDataPage` 카피를 `Market Watch`에 맞게 최소 정리
8. 시간이 허용되면 Slack next action을 `Keep Watching / Ask for More Evidence / Re-check Later` 중심으로 확장

---

## 5. P0에서 하지 않아도 되는 것

남은 시간이 3일이라면 아래는 P0에서 과감히 미뤄도 된다.

- 전체 디자인 시스템 재작성
- 차트 컴포넌트의 대규모 리팩터링
- route path 전체 rename에 집착하는 작업
- 새로운 복잡한 agent orchestration UI를 과도하게 추가하는 작업
- 완전 새로운 페이지를 0부터 여러 장 만드는 작업

핵심은 새로 많이 만드는 것이 아니라,

> **현재 자산을 새 의미 구조 안에 재배치하는 것**

이다.

---

## 6. 중간 점검 질문

P0 작업 중간마다 아래 질문으로 스스로 점검하면 좋다.

- 지금 화면은 `mission app`보다 `decision case app`처럼 보이는가?
- 지금 화면은 `챗봇`보다 `investigation console`처럼 보이는가?
- 지금 메인 화면은 `dashboard`보다 `decision room`처럼 보이는가?
- Agent Bricks orchestration이 화면 어디에서든 보이는가?
- approve/reject 말고도 manager가 고를 수 있는 다음 행동이 보이는가?
- Apps / Lakebase / Genie / Agent Bricks 4개를 이 화면 흐름으로 설명할 수 있는가?

---

## 7. 최종 판단

남은 3일 안에 가장 큰 임팩트를 내려면,
P0는 많은 페이지를 조금씩 손대는 방식보다

- semantic layer
- main room
- case detail
- investigation positioning
- visible orchestration

이 다섯 축에 집중해야 한다.

즉 P0의 본질은:

> **지금 앱을 더 많은 기능의 모음으로 만드는 것이 아니라,  
> Agent Bricks 기반 decision workflow처럼 읽히도록 재배열하는 것**

이다.