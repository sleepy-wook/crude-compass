# Crude Compass 프런트엔드 컴포넌트 매핑 문서

> 날짜: 2026-05-19  
> 목적: `docs/frontend_restructure_proposal.md`의 새 정보구조를 실제 현재 프런트엔드 코드에 연결하기 위한 실행 문서다.  
> 성격: 이 문서는 새 아이디어를 추가로 제안하는 문서가 아니라, **현재 파일/컴포넌트를 무엇으로 재해석하고 어디에 배치할지**를 정리하는 문서다.  
> 참고:
> - 진단서: `docs/agentic_redesign_review.md`
> - 구조 개편안: `docs/frontend_restructure_proposal.md`
> - 최종 점검표: `docs/home_validation_checklist.md`

---

## 1. 이 문서의 역할

이 문서가 답하려는 질문은 아래와 같다.

> "좋다. Decision Room / Case File / Investigation / Market Watch 구조로 가기로 했다.  
> 그럼 **지금 있는 프런트 코드에서 무엇을 살리고, 무엇을 옮기고, 무엇을 새로 최소 추가해야 하는가?**"

즉 이 문서는:

- 현재 페이지와 컴포넌트의 **재사용 가치**를 평가하고
- 새 IA 기준으로 **새 역할**을 부여하고
- 남은 3일 안에 가능한 수준으로 **삭제 / 축소 / 유지 / 확장** 결정을 돕는

**구현 브릿지 문서**다.

---

## 2. 새 IA 기준 최종 화면 구조

이번 개편에서 목표로 하는 최종 화면 구조는 아래와 같다.

- `Decision Room`
- `Case File`
- `Investigation`
- `Market Watch`

이 구조는 단순 탭 이름 변경이 아니라,

- dashboard → 운영실
- mission detail → decision dossier
- ask → case investigation
- market page → evidence board

로 제품의 성격을 바꾸는 작업이다.

---

## 3. 현재 페이지 → 새 페이지 매핑

### 3.1 `frontend/src/pages/Dashboard.tsx`

- **현재 역할**
  - 오늘의 결정 요약
  - bidirectional signal
  - 유사 과거 사례
  - active mission 요약
- **새 역할**
  - `Decision Room`
- **판단**
  - 가장 중요한 재사용 기반이다
  - 새 메인 화면의 뼈대로 유지하는 것이 맞다
- **필요 조치**
  - `Mission` 중심 카피를 `Open Case` / `Decision Case` 중심으로 전환
  - hero의 질문을 "오늘 무엇을 결정해야 하나"로 더 선명하게 변경
  - `Agent Activity Timeline` 블록 추가
  - `Suggested Next Actions` 블록 추가
  - dashboard-like summary tone을 줄이고 운영실/상황실 tone 강화
- **우선순위**
  - 최우선

### 3.2 `frontend/src/pages/MissionsPage.tsx`

- **현재 역할**
  - mission 목록 및 상세 맥락
  - 승인/수정/pivot 등 lifecycle
- **새 역할**
  - `Case File`
- **판단**
  - 이름은 가장 많이 바뀌어야 하지만, 구조적 재사용 가치는 높다
  - 현재 상태/변경 이력/manager action 흐름이 살아 있어 case dossier로 전환하기 좋다
- **필요 조치**
  - 전체 용어를 `Mission` → `Decision Case`로 전환
  - `pivot history`를 `revision history`로 재해석
  - approval / monitoring / revision state를 더 전면에 배치
  - evidence 요약과 Slack interaction 기록 연결부 추가
- **우선순위**
  - 최우선

### 3.3 `frontend/src/pages/AskPage.tsx`

- **현재 역할**
  - supervisor 기반 질문 응답
  - multi-agent trace 표시
- **새 역할**
  - `Investigation`
- **판단**
  - 지금 상태로는 generic AI chat처럼 읽힐 위험이 있다
  - 그러나 Agent Bricks를 보여줄 수 있는 핵심 페이지이기도 하다
- **필요 조치**
  - 자유 질의보다는 `현재 case 조사` 중심 UX로 수정
  - Supervisor / Genie / Knowledge / tool orchestration이 가장 선명하게 드러나는 페이지로 재배치
  - 예시 질문도 `현재 case` 기준으로 다시 작성
  - 결과를 `answer`보다 `evidence / findings / conflicts / recommendation note`처럼 보이게 정리
- **우선순위**
  - 최우선

### 3.4 `frontend/src/pages/MarketDataPage.tsx`

- **현재 역할**
  - 원천 데이터 시각화
  - 가격/뉴스/OPEC/FX 중심 데이터 보드
- **새 역할**
  - `Market Watch`
- **판단**
  - 유지 가치가 높다
  - 다만 독립 데이터 페이지가 아니라 현재 case를 검증하는 evidence board가 되어야 한다
- **필요 조치**
  - 각 블록에 `So what for current case?` 카피 추가
  - case와 직접 연결되는 요약 문장 추가
  - 단순 차트 전시 인상을 줄이고 근거판 성격 강화
- **우선순위**
  - 높음

---

## 4. 현재 컴포넌트 → 새 역할 매핑

## 4.1 메인 의사결정 영역에서 재사용할 컴포넌트

### `frontend/src/components/SimilarPastWidget.tsx`

- **현재 의미**
  - market memory / 유사 과거 사례
- **새 역할**
  - `Decision Room`의 상단 또는 중단 `Historical Analogs`
- **판단**
  - 매우 좋은 자산이다
  - 시나리오의 핵심인 "market memory"를 가장 잘 시각화한다
- **조치**
  - 유지
  - 현재 case와의 연결 카피만 강화

### `frontend/src/components/MissionSplitBar.tsx`

- **현재 의미**
  - term/spot split 제안
- **새 역할**
  - `Decision Room`과 `Case File`의 `Decision Draft Split`
- **판단**
  - 시나리오 핵심인 조달 방향 변경을 직접 보여주는 컴포넌트라 유지 가치가 높다
- **조치**
  - 유지
  - `Mission Split`이 아니라 `Decision Draft` 또는 `Suggested Position` 같은 이름으로 재해석

### `frontend/src/components/SignalContribution.tsx`

- **현재 의미**
  - 현재 점수/판단에 기여한 요소 설명
- **새 역할**
  - `Decision Room`의 `Why this case is open`
  - `Case File`의 `Evidence Summary`
- **판단**
  - Agent가 왜 이런 draft를 냈는지 설명하는 데 매우 중요하다
- **조치**
  - 유지
  - label만 recommendation style에서 evidence style로 조정

### `frontend/src/components/TimeHorizonBreakdown.tsx`

- **현재 의미**
  - GDELT / OPEC / EIA / FX의 시간축 설명
- **새 역할**
  - `Case File`의 `Time Horizon Evidence`
  - `Market Watch`의 해설 블록
- **판단**
  - Agent Bricks가 왜 여러 소스를 함께 봤는지 설명하는 좋은 연결 장치다
- **조치**
  - 유지
  - structured evidence / document evidence / event evidence 카피로 미세 조정

### `frontend/src/components/Bidirectional3Zone.tsx`

- **현재 의미**
  - 위험/기회 양방향 시그널 시각화
- **새 역할**
  - `Decision Room`의 signal status panel
- **판단**
  - 현재 시나리오의 평시 가치/양방향 구조를 잘 보여준다
- **조치**
  - 유지
  - 단순 점수판처럼 보이지 않게 case narrative와 함께 배치

---

## 4.2 Investigation / Agent Bricks 페이지에서 재사용할 컴포넌트

### `frontend/src/components/MultiAgentTrace.tsx`

- **현재 의미**
  - 멀티에이전트 trace 표시
- **새 역할**
  - `Investigation` 페이지의 핵심 증빙 컴포넌트
- **판단**
  - Agent Bricks 해커톤 관점에서 매우 중요하다
  - 지금까지는 데모성 요소에 가까웠지만, 앞으로는 핵심 가치 증빙 요소가 되어야 한다
- **조치**
  - 유지
  - trace를 `Supervisor orchestration timeline`처럼 보이게 카피 조정

### `frontend/src/components/SupervisorChat.tsx`

- **현재 의미**
  - 자연어 질의 응답 UI
- **새 역할**
  - `Investigation Console`
- **판단**
  - 재사용 가능하지만 generic chatbot 인상을 강하게 줄여야 한다
- **조치**
  - 예시 질문을 `현재 case 기준 조사 질의`로 교체
  - 결과 레이아웃을 `chat answer`보다 `investigation result`에 가깝게 수정
  - case context가 기본 포함되도록 UX 방향 정리
  - P0에서는 chat UI를 완전히 없애지 않아도 되지만, 첫 인상은 반드시 `free-form chatbot`이 아니라 `current case investigation console`이어야 한다

### `frontend/src/components/OpecCitation.tsx`

- **현재 의미**
  - OPEC 문서 근거 표시
- **새 역할**
  - `Investigation`과 `Market Watch`의 `Document Evidence`
- **판단**
  - Knowledge Assistant / document-grounded agent 성격을 보여주기에 좋다
- **조치**
  - 유지
  - "문서 근거" 라벨을 더 선명하게 부여

### `frontend/src/components/NewsTopList.tsx`

- **현재 의미**
  - 상위 뉴스 리스트
- **새 역할**
  - `Investigation`의 event evidence
  - `Market Watch`의 live signal evidence
- **판단**
  - 데이터 자체보다 현재 case와 어떻게 연결되는지가 중요하다
- **조치**
  - 유지
  - 뉴스 자체 나열보다 current case relevance를 보조 텍스트로 붙이는 방향 추천

---

## 4.3 Market Watch에서 유지할 컴포넌트

### `frontend/src/components/IntradayTicker.tsx`

- **현재 의미**
  - intraday 가격 변동 요약
- **새 역할**
  - `Market Watch`의 live market strip
- **판단**
  - 유지 가능
  - 다만 메인 hero를 잡아먹지 않게 위치 조정이 필요하다
- **조치**
  - 유지하되 메인 홈 비중 축소

### `frontend/src/components/IntradayChart.tsx`

- **현재 의미**
  - intraday 차트
- **새 역할**
  - `Market Watch`의 세부 차트
- **판단**
  - 차트 자체는 유효하지만, 메인 내러티브를 대신하면 안 된다
- **조치**
  - 유지하되 investigation/evidence 맥락 문구 필요

### `frontend/src/components/PriceLineChart.tsx`

- **현재 의미**
  - 가격 추세 시각화
- **새 역할**
  - `Market Watch` 주요 시계열
- **판단**
  - 유지
- **조치**
  - current case connection 문구 추가

### `frontend/src/components/FxLineChart.tsx`

- **현재 의미**
  - 환율 시각화
- **새 역할**
  - `Market Watch` 보조 근거
- **판단**
  - 한국 정유사 페르소나 기준으로 유지 가치 있음
- **조치**
  - 유지
  - 원화 기준 수입비용과의 연결 설명 강화

### `frontend/src/components/PatternScoreLine.tsx`

- **현재 의미**
  - risk/pattern score history
- **새 역할**
  - `Decision Room`의 case backdrop snapshot
  - `Market Watch`의 signal history drill-down
- **판단**
  - 유지 가능
  - score만 보여주면 대시보드처럼 보일 수 있어 해설과 함께 써야 한다
- **조치**
  - 단독 hero 사용 지양

---

## 4.4 상태 / 공통 UI 컴포넌트

### `frontend/src/components/StatusPill.tsx`

- **현재 의미**
  - mission status, mission type pill
- **새 역할**
  - `Case Status`, `Decision Direction`
- **판단**
  - 작은 변경으로 큰 semantic shift를 줄 수 있다
- **조치**
  - 적극 재사용
  - 텍스트 체계만 새 상태값에 맞게 개편

### `frontend/src/components/Sidebar.tsx`

- **현재 의미**
  - 페이지 네비게이션
- **새 역할**
  - 새 IA의 핵심 전환 포인트
- **판단**
  - 구조 개편의 직접 대상
- **조치**
  - 메뉴를 아래 기준으로 재정리
    - `Decision Room`
    - `Case File`
    - `Investigation`
    - `Market Watch`
  - mission, ask 같은 과거 용어 제거

### `frontend/src/components/Layout.tsx`

- **현재 의미**
  - 앱 공통 레이아웃
- **새 역할**
  - 유지
- **판단**
  - 구조 개편 시에도 기반으로 충분히 쓸 수 있다
- **조치**
  - 큰 수정 없이 내비게이션/헤더만 정리

### `frontend/src/components/ReactiveAlertToast.tsx`

- **현재 의미**
  - reactive trigger 알림
- **새 역할**
  - `Decision Room`과 `Case File`의 `Case Update Event`
- **판단**
  - agent가 계속 일하고 있다는 인상을 주기 좋다
- **조치**
  - 유지
  - alert가 아니라 case update / revision suggested tone으로 재해석 가능

---

## 5. P0에서 사실상 필수인 신규 컴포넌트

남은 3일 기준으로, 아래 컴포넌트는 사실상 필수에 가깝다.

### 5.1 `AgentActivityTimeline`

- **왜 필요한가**
  - 지금 앱이 recommendation app처럼 보이는 가장 큰 이유는 intermediate step이 부족하기 때문이다
  - 이 컴포넌트는 Agent Bricks orchestration을 사용자 눈에 보이게 만드는 가장 효율적인 장치다
- **들어갈 내용 예시**
  - Supervisor opened case
  - Genie checked structured market evidence
  - Knowledge Assistant retrieved OPEC evidence
  - Similar case tool returned analogs
  - Draft moved to monitoring
  - Manager requested more evidence
- **배치 위치**
  - `Decision Room`
  - `Case File`

### 5.2 `SuggestedNextActions`

- **왜 필요한가**
  - approve/reject만 있으면 recommendation workflow처럼 보인다
  - keep watching / ask for more evidence / re-check later 같은 선택지를 보여줘야 agentic workflow처럼 보인다
- **배치 위치**
  - `Decision Room`
  - `Case File`

### 5.3 `CaseHeader` 또는 `OpenCaseSummary`

- **왜 필요한가**
  - 현재 `MissionHero`가 있더라도 이름과 카피가 mission 기반이면 인상이 남는다
  - open case를 한눈에 정의하는 헤더가 있으면 구조가 안정된다
- **배치 위치**
  - `Decision Room`
  - `Case File`

---

## 6. 삭제 / 축소 / 경계할 요소

### 6.1 generic chatbot 인상

- `AskPage`와 `SupervisorChat`가 자유 질의 위주로 유지되면,
  judge는 이 제품을 그냥 "Agent Bricks 위 챗봇"으로 이해할 위험이 있다.
- 따라서 generic chat 성격은 줄이고 `case-bound investigation` 성격을 강화해야 한다.
- `Investigation`이 free-form chatbot처럼 보이면 실패라고 봐야 한다.

### 6.2 과한 market ticker hero화

- intraday ticker/차트가 메인 페이지 전면에 나오면,
  앱이 의사결정 시스템보다 시세 앱처럼 보일 수 있다.
- 실시간성은 중요하지만 hero를 차지하면 narrative가 흔들린다.

### 6.3 `Mission` 용어 잔존

- 일부만 바꾸고 일부가 남으면 구조 개편 효과가 크게 줄어든다.
- sidebar, status pill, heading, button, helper copy까지 전체 semantic layer를 같이 바꿔야 한다.

### 6.4 page 간 역할 중복

- `Decision Room`과 `Case File`이 둘 다 비슷한 요약만 보여주면 안 된다.
- 메인 홈은 현재 open case 중심,
- detail은 evidence / revision / monitoring / approval history 중심으로 차이를 분명히 둬야 한다.
- 또한 `Decision Room`은 action 중심, `Market Watch`는 evidence 중심이라는 경계를 끝까지 유지해야 한다.

---

## 7. 페이지별 구현 우선순위

### P0 — 반드시 손댈 것

- `frontend/src/components/Sidebar.tsx`
- `frontend/src/pages/Dashboard.tsx`
- `frontend/src/pages/MissionsPage.tsx`
- `frontend/src/pages/AskPage.tsx`
- `frontend/src/components/StatusPill.tsx`
- 신규 `AgentActivityTimeline`
- 신규 `SuggestedNextActions`

### P1 — 가능하면 손댈 것

- `frontend/src/pages/MarketDataPage.tsx`
- `frontend/src/components/SupervisorChat.tsx`
- `frontend/src/components/MultiAgentTrace.tsx`
- `frontend/src/components/ReactiveAlertToast.tsx`
- `frontend/src/components/NewsTopList.tsx`
- `frontend/src/components/OpecCitation.tsx`
- Slack next action 확장

### P2 — 시간 남으면 다듬을 것

- `frontend/src/components/IntradayTicker.tsx`
- `frontend/src/components/IntradayChart.tsx`
- `frontend/src/components/PatternScoreLine.tsx`
- `frontend/src/components/FxLineChart.tsx`
- 문구/아이콘/로딩/empty state 전반

---

## 8. 새 IA 기준 파일별 한 줄 결론

- `frontend/src/pages/Dashboard.tsx` → 새 메인 `Decision Room`의 기반으로 유지
- `frontend/src/pages/MissionsPage.tsx` → `Case File`로 이름과 의미를 바꿔 재사용
- `frontend/src/pages/AskPage.tsx` → `Investigation`으로 재포지셔닝
- `frontend/src/pages/MarketDataPage.tsx` → `Market Watch`로 유지
- `frontend/src/components/MultiAgentTrace.tsx` → Agent Bricks 시연 핵심 자산
- `frontend/src/components/SupervisorChat.tsx` → generic chat에서 investigation console로 전환
- `frontend/src/components/MissionSplitBar.tsx` → 시나리오 핵심 자산, 적극 재사용
- `frontend/src/components/SimilarPastWidget.tsx` → market memory 핵심 자산, 적극 재사용
- `frontend/src/components/StatusPill.tsx` → semantic shift를 위한 비용 대비 효율 높은 변경 지점
- `frontend/src/components/Sidebar.tsx` → 개편의 시작점

---

## 9. 최종 판단

현재 프런트는 완전히 버리고 새로 짤 상태가 아니다.
오히려 중요한 것은:

- 좋은 자산은 살리고
- semantic layer를 바꾸고
- page 역할을 재정의하고
- Agent Bricks orchestration이 보이게 만드는 최소 신규 컴포넌트를 추가하는 것

이다.

즉 남은 3일 기준으로 가장 현실적인 전략은:

> **현재 컴포넌트를 최대한 재사용하되,  
> `Decision Room / Case File / Investigation / Market Watch` 구조로 재배치하고,  
> `Agent Activity Timeline`과 `Suggested Next Actions`를 추가해 Agent Bricks workflow를 전면화하는 것**

이다.