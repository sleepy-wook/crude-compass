# Crude Compass 프론트엔드 구조 개편안 (Agent Bricks 중심 버전)

> 날짜: 2026-05-19  
> 목적: 해커톤의 핵심 요구사항인 **Databricks Agent Bricks 활용**을 제품 전면에 드러내도록, 프런트엔드와 제품 구조를 재설계한다.  
> 전제:
> - Agent Bricks 활용은 선택이 아니라 필수다
> - 남은 시간은 3일
> - 현재 코드/데이터/컴포넌트를 최대한 재사용해야 한다
> - 단순한 "AI 추천 앱"이 아니라 **Agent Bricks 기반의 agentic decision workflow**로 보여야 한다

---

## 1. 가장 중요한 결론

이 proposal의 핵심 결론은 단순하다.

> **Crude Compass는 Databricks Agent Bricks 위에서 동작하는  
> 정유사 구매 의사결정용 agentic decision room** 으로 재정의되어야 한다.

즉 이 앱은 더 이상

- 대시보드
- AI 추천 카드
- 데이터 시각화 페이지

의 조합으로 보이면 안 된다.

대신 다음처럼 읽혀야 한다.

- Agent Bricks Supervisor가 case를 orchestration한다
- Genie가 structured market evidence를 가져온다
- Knowledge Assistant가 OPEC 같은 문서 근거를 가져온다
- custom tools / functions가 score, retrieval, watch condition을 계산한다
- Databricks Apps가 manager-facing decision room을 제공한다
- Slack은 human-in-the-loop approval / follow-up channel이 된다

즉 이 제품의 본질은:

> **Databricks Agent Bricks 기반 multi-agent decision workflow**

이다.

---

## 2. 왜 기존 proposal만으로는 부족한가

이전 proposal은 다음 점에서 맞는 방향이었다.

- mission → decision case
- recommendation viewer → decision room
- ask → investigation
- market → evidence board

하지만 이것만으로는 아직 해커톤 주제의 핵심인 **Agent Bricks 사용**이 전면에 드러나지 않는다.

즉 기존 proposal은:

- 현실성은 높였지만
- "왜 이게 Databricks Agent Bricks 해커톤 제출작인가?"에 대한 답이 아직 약했다

이번 버전에서는 이 점을 보완한다.

이번 proposal은 단순 UX 개편안이 아니라:

> **Agent Bricks 기반 제품 구조를 프런트엔드와 사용자 경험에 반영하는 개편안**

이다.

---

## 3. 제품을 어떻게 재정의할 것인가

### 3.1 제품 한 줄 정의

추천 문구:

> Crude Compass는 Databricks Agent Bricks 기반의 정유사 구매 의사결정 지원 시스템이다.  
> 시장 변화가 생기면 Agent Bricks Supervisor가 여러 specialized agents와 tools를 orchestration하여 evidence를 수집하고, decision case를 열고, manager approval과 monitoring workflow를 이어간다.

### 3.2 제품이 해야 하는 일

이 시스템은 현실적으로 다음 역할에 집중해야 한다.

- 시장 변화 감지
- evidence 수집
- decision case 생성
- draft action 제안
- 사람 승인 / 조정 / 보류
- monitoring / revision

즉 실행 시스템이 아니라,

> **Agent Bricks가 관리하는 human-in-the-loop decision prep workflow**

로 포지셔닝하는 것이 가장 적절하다.

---

## 4. Agent Bricks 중심 아키텍처로 다시 설명하기

이번 proposal의 핵심은 현재 자산을 Agent Bricks language로 다시 정렬하는 것이다.

### 4.1 현재 시스템을 Agent Bricks 관점으로 번역

| 현재 자산 | Agent Bricks 관점에서의 역할 |
|---|---|
| Supervisor | **Agent Bricks Supervisor / Case Orchestrator** |
| Genie | **Structured Market Agent** |
| OPEC 기반 지식 응답 | **Knowledge Assistant / Document Evidence Agent** |
| UC Function / scoring / retrieval | **Custom Tool / Function Tool** |
| Databricks Apps UI | **Decision Room** |
| Slack interactive | **Human Approval / Follow-up Channel** |
| Missions | **Decision Cases** |

즉 제품의 설명 구조는 아래처럼 바뀌어야 한다.

- 기존: "AI가 추천을 만든다"
- 변경: "Agent Bricks Supervisor가 여러 specialized agents와 tools를 조합해 case를 운영한다"

### 4.2 우리가 실제로 보여줘야 하는 agent 역할

제품과 데모에서는 아래 4개 역할을 명확히 보여주는 것이 좋다.

#### 1) Supervisor Agent

- 전체 case orchestration
- 어떤 tool/agent를 호출할지 결정
- 최종 case state / next action synthesis

#### 2) Structured Market Agent

- Genie 또는 structured query 기반
- 가격 / FX / score / signal / market memory 등 구조화 데이터 해석

#### 3) Document Evidence Agent

- Knowledge Assistant 역할
- OPEC 보고서 / 비정형 텍스트 근거 retrieval

#### 4) Monitoring / Action Tool Layer

- weighted signal
- similar case retrieval
- re-check condition
- case update / watch transition

중요한 점:

- 꼭 모든 것을 새로운 agent로 따로 구현할 필요는 없다
- **프런트와 narrative에서 이 역할이 분명히 보이기만 해도 충분하다**

---

## 4.5 해커톤 필수 4기능 매핑

이번 해커톤에서는 아래 4가지 Databricks 신기능 활용이 필수다.

1. **Databricks Apps**
2. **Lakebase**
3. **Genie**
4. **Agent Bricks**

따라서 proposal은 이 4개를 "어디엔가 쓰고 있다" 수준이 아니라,  
**제품 구조 안에서 각각의 역할이 명확히 드러나야 한다.**

### 4.5.1 기능별 제품 역할

| 기능 | 제품 안에서의 역할 | 사용자에게 보이는 방식 |
|---|---|---|
| **Databricks Apps** | manager-facing app surface | Decision Room / Case File / Investigation / Market Watch UI |
| **Lakebase** | case state / approval / monitoring memory | case status, revision history, monitoring rules, approval history |
| **Genie** | structured market evidence agent | structured data evidence, natural language market investigation |
| **Agent Bricks** | multi-agent orchestration layer | Supervisor activity, agent routing, tool usage, case workflow |

즉 4개는 다음처럼 연결되어야 한다.

> **Apps** 위에서  
> **Agent Bricks Supervisor**가  
> **Genie**와 document/tools를 orchestration하고,  
> **Lakebase**에 case state를 기록하며  
> manager에게 다음 행동을 제안한다.

### 4.5.2 제품 한 줄에 4기능을 모두 담는 방법

추천 문장:

> Crude Compass는 Databricks Apps 위에서 동작하는 manager-facing decision room이며,  
> Agent Bricks Supervisor가 Genie와 document evidence tools를 orchestration해 decision case를 열고,  
> Lakebase에 case state를 기록하면서 human-in-the-loop workflow를 이어간다.

이 문장은 심사위원에게

- Apps를 단순 호스팅으로만 쓴 것이 아니고
- Lakebase를 단순 DB로만 쓴 것이 아니며
- Genie를 단순 챗봇으로만 쓰지 않았고
- Agent Bricks가 실제 중심 orchestration이라는 점

을 한 번에 전달한다.

### 4.5.3 페이지별 필수 기능 매핑

| 페이지 | Apps | Lakebase | Genie | Agent Bricks |
|---|---|---|---|---|
| **Decision Room** | 메인 UI surface | open case / approval / monitoring 상태 | structured evidence snapshot | supervisor activity / next actions |
| **Case File** | case detail UI | revision / approval / watch state | structured evidence detail 일부 | orchestration timeline / case lifecycle |
| **Investigation** | manager investigation UI | case context state | 핵심 structured Q&A 및 evidence retrieval | supervisor routing / multi-agent trace |
| **Market Watch** | evidence board UI | optional saved state / filters | structured query backed explanation | evidence interpretation context |

### 4.5.4 심사 포인트 관점에서의 해석

이 4개가 전부 들어가더라도, 심사위원 입장에서는 결국 아래 질문을 할 가능성이 높다.

- Apps는 그냥 프런트 호스팅 아니냐?
- Lakebase는 그냥 저장소 아니냐?
- Genie는 그냥 NL2SQL 아니냐?
- Agent Bricks는 그냥 이름만 붙인 거 아니냐?

이 질문에 답하려면 제품 구조가 이렇게 보여야 한다.

- **Apps** = agent workflow를 소비하는 업무용 surface
- **Lakebase** = case memory / operational state
- **Genie** = structured market specialist
- **Agent Bricks** = 여러 specialist를 조합해 case를 운영하는 orchestration layer

즉 각 기능의 "존재"보다 "역할"이 더 중요하다.

---

## 5. 현실적인 페르소나와 Agent Bricks의 접점

이 제품은 현실적으로 **정유사 실거래 자동화 엔진**이 아니다.

따라서 가장 적합한 사용자도 아래와 같이 설정해야 한다.

### Primary Persona

**정유사 구매/전략 매니저**

이 사람에게 Agent Bricks가 주는 가치는:

- 여러 데이터 source를 agent가 대신 조사해준다
- 지금 open case가 왜 열렸는지 설명해준다
- approve / adjust / keep watching 중 무엇을 할지 고를 수 있게 해준다
- 필요한 경우 증거를 더 요청할 수 있다

즉 이 사용자는:

- "AI가 대신 구매"를 원하지 않고
- **agent가 case를 준비하고 관리해주는 decision room**을 원한다

### Secondary Persona

**승인권 있는 리더**

이 사람은:

- raw data가 아니라
- Agent Bricks가 수집한 evidence
- case summary
- next action

를 빠르게 이해하고 싶어한다.

즉 Agent Bricks는 이 사람에게 "복잡한 시장 해석을 대리 조사해주는 시스템"으로 보이면 된다.

---

## 6. 제품 핵심 개념 전환

### 6.1 Mission이 아니라 Decision Case

지금 제품이 더 agentic하고 더 현실적으로 보이려면,  
기본 객체는 "mission"이 아니라 **decision case**여야 한다.

이유:

- mission은 task object처럼 느껴진다
- case는 agent가 상태를 가지고 운영하는 업무 단위처럼 느껴진다

Agent Bricks와도 case 개념이 더 잘 맞는다.  
Supervisor가 subagent를 호출해 "답변"을 만드는 것보다,  
**case를 열고 evidence를 모으고 next action을 제안하는 구조**가 더 agentic하다.

### 6.2 recommendation이 아니라 case workflow

프런트는 더 이상

- 추천 결과
- 차트
- 질문응답

의 집합이 아니라,

> **Agent Bricks가 운영하는 case workflow의 시각화**

여야 한다.

---

## 7. Information Architecture 제안

제안 구조는 아래 4개다.

- **Decision Room**
- **Case File**
- **Investigation**
- **Market Watch**

이 구조는 단순히 보기 좋기 때문이 아니라,
Agent Bricks workflow를 가장 잘 보여줄 수 있는 구조다.

그리고 이 구조는 해커톤 필수 4기능을 페이지 단위로 분해해서 보여주기에도 적합하다.

- **Decision Room** → Apps + Agent Bricks + Lakebase
- **Case File** → Lakebase + Agent Bricks
- **Investigation** → Agent Bricks + Genie (+ Knowledge Assistant)
- **Market Watch** → Apps + Genie + evidence grounding

---

## 8. 페이지별 구조 개편안

## 8.1 Decision Room

### 역할

Agent Bricks workflow의 메인 운영실.  
현재 열린 case와, Supervisor가 어떤 evidence를 모았고 어떤 다음 행동을 제안하는지 보여준다.

`Decision Room`은 **행동 결정 화면**이어야 한다.
같은 데이터가 `Market Watch`에도 나타날 수는 있지만, 이 페이지의 시각적 무게중심은 끝까지 아래에 있어야 한다.

- open case
- why this case is open
- agent activity
- next actions
- approval / monitoring status

즉 `Decision Room`은 drill-down evidence board가 아니라, action-oriented operating surface처럼 보여야 한다.

이 페이지는 해커톤 4기능 중 특히 아래를 대표한다.

- **Apps**: manager-facing main surface
- **Lakebase**: current case state source
- **Agent Bricks**: supervisor-driven orchestration visibility

### 사용자가 이 페이지에서 이해해야 하는 것

- 지금 어떤 decision case가 열려 있는가
- Agent Bricks Supervisor가 왜 이 case를 열었는가
- 어떤 agent/tool이 evidence를 제공했는가
- 나는 지금 approve / adjust / keep watching 중 무엇을 할 것인가

### 핵심 섹션

#### A. Open Decision Case

보여줄 것:

- case title
- decision direction
- draft adjustment
- confidence
- urgency

주의:

- wording은 execution이 아니라 draft / re-evaluation / review 중심

#### B. Why This Case Is Open

보여줄 것:

- 강화된 시그널
- 약화된 시그널
- case open 이유
- structured / document evidence 요약

#### C. Agent Bricks Activity

이 섹션은 이번 proposal에서 매우 중요하다.

예시:

- Supervisor opened case
- Structured Market Agent checked FX / prices / score
- Knowledge Assistant retrieved OPEC evidence
- Similar Case Tool returned 7 analog cases
- Draft updated

즉 "에이전트가 뭘 했는가"를 보여줘야 한다.

#### D. Suggested Next Actions

현재 액션은 아래처럼 바꾸는 것이 좋다.

- Approve Draft
- Adjust Draft
- Keep Watching
- Ask for More Evidence
- Re-check After Next EIA
- Dismiss Case

이게 단순 approve/reject보다 훨씬 agentic하고 현실적이다.

#### E. Monitoring Queue

보여줄 것:

- 다음 review trigger
- watch condition
- monitoring state
- revision suggestion 가능성

#### F. Similar Past Cases

현재 case와 연결된 historical analog를 보여준다.

이것은 단순 backtest 시각화가 아니라,  
Supervisor가 사용할 수 있는 reasoning aid처럼 보여야 한다.

---

## 8.2 Case File

### 역할

현재 case를 깊게 보는 dossier.  
Agent Bricks Supervisor가 이 case를 어떻게 관리하고 있는지 시간축으로 보여준다.

이 페이지는 특히 아래 기능과 연결된다.

- **Lakebase**: approval / revision / monitoring state의 source of truth
- **Agent Bricks**: case lifecycle orchestration 기록

### 핵심 질문

- 왜 이 case가 열렸는가
- 어떤 agent가 어떤 근거를 가져왔는가
- manager가 무엇을 했는가
- monitoring과 revision이 어떻게 이어지는가

### 핵심 섹션

#### A. Case Summary

- case state
- direction
- draft adjustment
- duration / watch window
- confidence

#### B. Evidence Collected

이 섹션은 데이터 나열이 아니라,
아래 agent 역할과 연결되어야 한다.

- Structured Market Agent evidence
- Document Evidence Agent evidence
- Tool-based evidence (similar cases / score / triggers)

#### C. Approval History

- Apps action
- Slack action
- keep watching / adjust / dismiss 기록

#### D. Activity Timeline

예시:

- Signal detected
- Case opened
- Supervisor routed to Genie
- Knowledge Assistant returned OPEC evidence
- Manager asked for more evidence
- Draft revised
- Monitoring resumed
- Revision suggested

이 timeline이 있어야 OpenClaw류 UX와 Agent Bricks orchestration 감각이 살아난다.

#### E. Revision History

기존 pivot history를 business language로 재해석한다.

- `Pivot history` → `Revision history`

#### F. Monitoring Rules

- 현재 watch rule
- next review trigger
- revision trigger
- case close condition

---

## 8.3 Investigation

### 역할

기존 AskPage를 Agent Bricks 기반 조사 콘솔로 재정의한다.

이 페이지는 "AI와 대화" 페이지가 아니라,

> **Supervisor가 어떤 specialized agents/tools를 호출해 현재 case를 조사하는지 보여주는 page**

가 되어야 한다.

이 페이지는 해커톤 필수 기능 중 특히 아래를 보여주는 곳이다.

- **Agent Bricks**: Supervisor orchestration
- **Genie**: structured evidence retrieval
- **Knowledge Assistant**(Agent Bricks scope): document evidence retrieval

### 핵심 섹션

#### A. Current Case Context

- 현재 open case 요약
- case state
- current confidence

#### B. Suggested Investigations

예:

- "왜 이 case를 열었지?"
- "OPEC 근거만 보여줘"
- "structured data와 document evidence가 충돌하나?"
- "유사 과거 사례와 비교해줘"
- "지금 approve보다 keep watching이 더 나은 이유는?"
- "다음 review에서 무엇을 기다리는 중이지?"

#### C. Supervisor Trace

이건 단순한 기술 데모가 아니라,
아래를 보여주는 UX여야 한다.

- 어떤 agent를 호출했는가
- 어떤 tool을 썼는가
- 왜 그 path를 탔는가

즉 **Agent Bricks orchestration의 가시화**가 목적이다.

#### D. Evidence Answer

응답은 generic answer가 아니라
현재 case에 bound된 answer여야 한다.

---

## 8.4 Market Watch

### 역할

현재 `MarketDataPage`를 evidence board로 위치시킨다.

`Market Watch`는 **근거 검증 화면**이어야 한다.
같은 신호가 `Decision Room`에도 snapshot 형태로 보일 수는 있지만, 이 페이지의 시각적 무게중심은 아래에 있어야 한다.

- prices
- FX
- news
- OPEC / document evidence
- pattern / history / context

즉 `Market Watch`는 행동 결정 페이지가 아니라 evidence drill-down page처럼 보여야 한다.

이 페이지는 메인 스토리가 아니라,
Agent Bricks workflow가 참조한 원천 데이터를 검증하는 장소다.

이 페이지는 주로 아래 기능과 연결된다.

- **Apps**: evidence board UI
- **Genie**: structured explanation backing
- **Agent Bricks**: reasoning context를 제공하는 upstream workflow

### 핵심 원칙

각 블록은 반드시 아래를 포함해야 한다.

> **현재 case에 어떤 의미가 있는가**

예:

- OPEC → Document Evidence Agent가 참고한 중기 supply tone
- FX → Structured Market Agent가 확인한 cost pressure
- 뉴스 → short-term urgency evidence
- intraday price → monitoring queue trigger와 연결
- pattern history → current draft confidence 보강

즉 차트 전시가 아니라,
**Agent Bricks reasoning evidence board**처럼 보여야 한다.

---

## 9. 라벨링 전면 개편

이번 proposal에서는 용어도 Agent Bricks 중심으로 정리해야 한다.

| 기존 | 제안 |
|---|---|
| Mission | Decision Case |
| Mission Type | Decision Direction |
| Active Missions | Open Cases |
| Mission Detail | Case File |
| Mission Status | Case State |
| Pivot History | Revision History |
| Confirm | Approve Draft |
| Modify | Adjust Draft |
| Reject | Dismiss Case |
| Pause | Keep Watching |
| Ask | Investigation |
| Market | Market Watch |

추가 추천 표현:

| 기존 느낌 | 추천 표현 |
|---|---|
| AI가 추천함 | Supervisor opened a case |
| 이유 설명 | Evidence gathered |
| 챗봇 응답 | Investigation result |
| Pivot 제안 | Revision suggested |
| 단순 상태 변경 | Case moved to monitoring |

---

## 10. OpenClaw류 UX에서 차용할 부분

OpenClaw류 UX를 그대로 가져오는 것은 적절하지 않다.  
하지만 아래 3가지는 매우 유효하다.

### 1) Activity Timeline

에이전트가 무엇을 했는지 로그처럼 보여준다.

### 2) Next Action 중심 인터랙션

Approve/Reject만이 아니라:

- Keep Watching
- Ask for More Evidence
- Re-check Later

같은 action이 중요하다.

### 3) Thread-like Case Progression

case가 한 번 열리고 끝나는 것이 아니라,
조사 → 승인 대기 → 모니터링 → revision으로 이어진다는 감각이 필요하다.

이건 Agent Bricks Supervisor의 orchestration 감각과도 잘 맞는다.

---

## 11. Slack의 위치 재정의

Slack은 단순 알림 수단이 아니라,

> **Agent Bricks workflow의 human approval / follow-up channel**

로 보여야 한다.

### Slack에서 제공해야 할 액션

- Approve Draft
- Adjust Draft
- Keep Watching
- Ask for More Evidence
- Re-check Later

즉 Slack은 approval surface이면서,
동시에 case 진행을 이어가는 work surface가 되어야 한다.

---

## 12. 구현 우선순위

남은 3일 기준으로 아래 순서를 권장한다.

### 1순위 — Agent Bricks 중심 언어 전환

- Supervisor = case orchestrator
- Genie = structured market agent
- Knowledge Assistant = document evidence agent
- Apps = decision room
- Slack = human approval channel
- Lakebase = case memory / operational state

이 개념을 UI 카피와 발표 흐름에 먼저 반영한다.

### 2순위 — Decision Room 메인 홈 재구성

핵심 섹션:

- Open Decision Case
- Why This Case Is Open
- Agent Bricks Activity
- Suggested Next Actions
- Monitoring Queue
- Similar Past Cases

### 3순위 — Case File timeline 강화

Case file에서 activity timeline을 명확히 보이게 한다.

### 4순위 — Investigation 페이지를 Agent Bricks 조사 콘솔로 전환

Ask를 generic chat에서 supervisor-driven investigation으로 바꾼다.

### 5순위 — Slack interaction 확장

Approve/Reject 중심에서:

- Adjust Draft
- Keep Watching
- Ask for More Evidence
- Re-check Later

로 확장한다.

단, 이것은 P0의 절대 필수라기보다 **시간 허용 시 우선적으로 넣으면 좋은 P0.5 / P1 성격**으로 보는 것이 현실적이다.

### 6순위 — Market Watch를 evidence board화

각 블록에 현재 case와의 연결 의미를 넣는다.

---

## 13. 이 개편의 기대 효과

개편 전:

- 데이터 대시보드
- AI recommendation app
- 멀티에이전트 데모

개편 후:

- Agent Bricks Supervisor가 운영하는 decision room
- 여러 agent/tool이 evidence를 모아 case를 여는 시스템
- human-in-the-loop approval과 monitoring이 이어지는 workflow
- 해커톤 요구사항인 Agent Bricks 활용이 전면에 드러나는 제품

즉 이 제품은 더 이상 "AI가 추천해주는 앱"이 아니라,

> **Databricks Agent Bricks 기반의 multi-agent decision workflow**

로 읽히게 된다.

---

## 14. 최종 권고

이번 프런트 개편은 단순한 UI 정리가 아니다.

핵심은:

> **Databricks Agent Bricks를 실제 제품 구조의 중심에 놓고,  
> 이를 사용자 경험에서 명확히 드러내도록  
> 앱을 Decision Room / Case File / Investigation / Market Watch 구조로 재조직하는 것**

이다.

즉:

- Agent Bricks가 앞에 나오고
- case workflow가 중심이 되고
- evidence gathering이 보이고
- manager action이 natural next step으로 이어지고
- monitoring / revision이 살아 있어야 한다

이 방향이 해커톤 목적, 현재 코드, 남은 시간, 제품 현실성을 모두 고려했을 때 가장 적절하다.

---

## 15. 바로 다음 단계

이 문서 다음으로 바로 이어서 만들기 좋은 것은:

1. **페이지별 와이어프레임 텍스트**
2. **컴포넌트 매핑 문서**
3. **3일 실행 체크리스트**

추천 순서는:

1. 와이어프레임
2. 컴포넌트 매핑
3. 실행 체크리스트

---

끝.