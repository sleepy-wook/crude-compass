# Crude Compass Agentic Redesign Review (Agent Bricks 관점 진단서)

> 날짜: 2026-05-19  
> 문서 역할: 이 문서는 **진단서**다.  
> 목적: 현재 제품이 왜 아직 충분히 agentic하게 보이지 않는지, 그리고 왜 Databricks 해커톤 제출작으로서 **Apps / Lakebase / Genie / Agent Bricks** 활용이 제품 전면에 충분히 드러나지 않는지를 진단한다.  
> 참고:
> - 구조 개편안: `docs/frontend_restructure_proposal.md`
> - 최종 점검 문서: `docs/home_validation_checklist.md`

---

## 1. 이 문서의 역할

이 문서는 "어떻게 바꿀까"를 쓰는 문서가 아니라,

> **왜 지금 구조가 부족한가**

를 설명하는 문서다.

즉 이 문서는:

- 현재 앱의 agentic함 부족을 진단하고
- Databricks 필수 4기능이 왜 제품 중심에서 덜 보이는지 설명하고
- 어떤 종류의 오해를 심사위원이 할 수 있는지 미리 드러내는

**문제 정의 문서**다.

반대로 아래는 이 문서의 역할이 아니다.

- 최종 IA 설계
- 페이지 구조 제안
- 와이어프레임
- 구현 체크리스트

그건 proposal/checklist 문서의 역할이다.

---

## 2. 현재 시스템에 대한 핵심 진단

현재 시스템은 분명히 많은 것을 갖추고 있다.

- Databricks pipelines
- Apps
- Lakebase
- Genie
- Supervisor
- Slack
- WebSocket sync
- Mission lifecycle

하지만 제품 인상은 아직 아래에 더 가깝다.

- data dashboard
- recommendation generator
- LLM-assisted workflow

반면 아직 충분히 강하지 않은 인상은 다음이다.

- Databricks Agent Bricks 기반 multi-agent system
- stateful case orchestration workflow
- human-in-the-loop decision room

즉 현재 제품은:

> **"Agent Bricks를 활용한 agentic decision workflow"** 보다는  
> **"데이터와 LLM이 결합된 의사결정 보조 앱"**

처럼 읽힐 위험이 있다.

---

## 3. 왜 지금 agentic함이 약하게 느껴지는가

### 3.1 recommendation은 보이지만 orchestration은 덜 보인다

현재 구조의 중심은 여전히:

- 데이터를 읽고
- 추천안을 만들고
- 사람이 approve/reject하는 흐름

이다.

즉 "에이전트가 case를 운영한다"는 느낌보다,
"AI가 추천 초안을 만든다"는 느낌이 더 강하다.

이 차이는 중요하다.

해커톤의 주제가 단순 LLM 사용이 아니라 **agent 활용**이라면,
judge는 결국 아래를 보고 싶어한다.

- agent가 무엇을 관찰했는가
- 어떤 tool / subagent를 호출했는가
- 어떤 intermediate step을 거쳤는가
- 왜 그 next action을 택했는가
- 이후 무엇을 계속 모니터링하는가

현재 제품은 최종 result는 보여주지만,
이 **중간 orchestration 단계**는 충분히 앞에 나와 있지 않다.

### 3.2 Supervisor가 backend router처럼 보일 수 있다

현재 Supervisor는 분명 중요한 자산이지만,
사용자/심사위원 관점에서는

- "멀티에이전트 챗봇"
- "질문을 잘 라우팅하는 backend layer"

정도로 읽힐 수 있다.

문제는 이럴 경우 Agent Bricks가

- case orchestrator
- workflow manager
- specialized agents coordinator

로 보이지 않는다는 점이다.

즉 Supervisor는 있는데,

> **Agent Bricks Supervisor가 제품의 중심 orchestration layer라는 인상**

은 아직 약하다.

### 3.3 agent는 답변하지만, case를 오래 관리하진 않는다

현재 구조에서 agent는:

- recommendation 생성
- question answering
- 일부 trace 출력

에는 관여하지만,

- case open
- case update
- monitoring transition
- revision suggestion
- follow-up question

같은 **상태 있는 작업 흐름**이 충분히 노출되지 않는다.

즉 agent가 "계속 일하고 있는 존재"보다는
"필요할 때 한 번 호출되는 기능"처럼 보일 위험이 있다.

---

## 4. 왜 Databricks 4대 필수 기능이 제품 중심에서 약하게 보이는가

이번 해커톤에서 필수인 기능은 다음 4가지다.

1. Databricks Apps
2. Lakebase
3. Genie
4. Agent Bricks

현재 문제는 이 기능들이 "존재"하긴 하지만,

> **제품의 핵심 가치 구조 안에서 각자 무슨 역할을 하는지가 충분히 선명하지 않다**

는 점이다.

---

## 5. Databricks Apps 관점 진단

현재 Apps는 실제로 중요한 역할을 하고 있지만,
겉으로는 자칫 아래처럼 보일 수 있다.

- 그냥 프런트엔드 호스팅
- 웹페이지 배포 수단
- UI shell

이 인상은 해커톤 관점에서 약하다.

왜냐하면 Apps는 단순 배포 도구가 아니라:

- Databricks-native app surface
- governed data/AI UI
- agent workflow를 소비하는 manager-facing interface

로 보여야 하기 때문이다.

현재 앱이 충분히 보여주지 못한 부분은:

- Apps가 왜 "decision room"인지
- Apps 안에서 왜 approval / monitoring / investigation이 이어지는지
- Apps가 다른 Databricks 기능들의 상위 경험 계층인지

이다.

즉 Apps는 존재하지만,

> **Apps가 product surface로서 왜 중요한지**

가 아직 충분히 전달되지 않는다.

---

## 6. Lakebase 관점 진단

Lakebase는 현재 구조에서 분명 중요한 persistence layer다.

하지만 겉으로는 다음처럼 읽힐 수 있다.

- 그냥 DB
- mission row 저장소
- 상태 저장용 backend table

이 역시 해커톤 관점에서는 약하다.

Lakebase는 현재 더 강하게 이렇게 보여야 한다.

- case memory
- approval / revision / watch state 저장소
- Slack / Apps / backend가 공유하는 operational source of truth
- "agent가 case를 이어서 관리한다"는 걸 가능하게 하는 state layer

즉 Lakebase는 단순 저장소가 아니라,

> **Agent Bricks workflow의 operational memory**

여야 한다.

현재 제품은 이 점이 충분히 앞에 나와 있지 않다.

---

## 7. Genie 관점 진단

Genie는 지금 구조 안에서 유용하게 쓰이고 있지만,
사용자/심사위원 입장에서는 아래처럼 보일 수 있다.

- 자연어로 SQL 해주는 기능
- 부가적인 data Q&A
- ask page의 한 서브 기능

이 인상도 약하다.

Genie는 제품에서 아래 역할로 보여야 한다.

- structured market specialist
- score / FX / prices / historical patterns에 대한 structured evidence agent
- investigation 단계에서 Supervisor가 호출하는 핵심 subagent

즉 Genie는 "Q&A 기능"이 아니라,

> **Agent Bricks Supervisor가 structured evidence를 확보할 때 호출하는 specialist**

로 보여야 한다.

현재는 이 연결이 충분히 명확하지 않다.

---

## 8. Agent Bricks 관점 진단

이 부분이 가장 중요하다.

현재 제품에는 Supervisor, trace, 여러 data source, 일부 agent-like behavior가 있다.

하지만 judge가 보기에는 다음처럼 오해될 수 있다.

- 그냥 backend LLM orchestration
- 그냥 멀티에이전트 데모
- 그냥 여러 모델/툴을 붙인 챗봇

즉 **Agent Bricks가 제품의 중심 orchestration layer라는 인상**이 약하다.

Agent Bricks가 강하게 보이려면:

- Supervisor가 case를 열어야 하고
- specialist agents / tools가 evidence를 모아야 하고
- 결과가 timeline으로 보여야 하고
- next action이 human-in-the-loop로 이어져야 하고
- monitoring / revision까지 이어져야 한다

현재 제품은 이 중 일부는 갖췄지만,

> **Agent Bricks orchestration이 결과보다 앞에서 보이지 않는다**

는 점이 핵심 한계다.

---

## 9. OpenClaw류 UX와 비교했을 때의 부족함

OpenClaw류 UX가 강하게 느껴지는 이유는 다음 때문이다.

- channel이 곧 work surface다
- intermediate steps가 보인다
- agent가 계속 상태를 이어간다
- user가 next action을 주면 agent가 이어서 일한다

현재 제품은 Slack을 붙였지만,
아직 아래 수준에 더 가깝다.

- 알림
- 승인 버튼
- 결과 표시

즉 Slack이 "agent work surface"까지는 올라가지 못했다.

현재 부족한 부분:

- case thread / activity feed
- "더 조사해줘", "계속 지켜봐", "다음 발표 후 다시" 같은 next action
- agent가 manager에게 질문하는 흐름
- case state가 timeline으로 누적되는 구조

이런 요소가 부족하니 제품이 recommendation workflow처럼 보이기 쉽다.

---

## 10. 현재 제품의 가장 큰 위험한 오해

심사위원이나 사용자 입장에서 아래 같은 오해가 생길 수 있다.

### 오해 1

"이건 그냥 데이터 대시보드 아닌가?"

왜 생기나:

- Apps가 operating surface보다는 dashboard처럼 보이기 때문

### 오해 2

"이건 그냥 LLM이 추천문 써주는 앱 아닌가?"

왜 생기나:

- recommendation은 잘 보이는데 agent activity는 덜 보이기 때문

### 오해 3

"Genie는 그냥 NL2SQL, Lakebase는 그냥 DB, Apps는 그냥 프런트, Agent Bricks는 그냥 이름만 붙인 거 아닌가?"

왜 생기나:

- 4개 기능이 제품 안에서 각각 무엇을 맡는지 전면에 안 나와 있기 때문

### 오해 4

"이건 정유사의 실제 구매 의사결정을 자동화한다고 주장하는데, 너무 과장된 것 아닌가?"

왜 생기나:

- case workflow가 아니라 execution recommendation처럼 보일 때

---

## 11. 현실성 관점에서의 진단

현재 제품은 실제 정유사 procurement execution system처럼 보이면 안 된다.

그렇게 보일 경우 다음 문제가 생긴다.

- 공개 데이터만으로 최종 조달 실행을 한다는 인상
- Slack 승인 한 번으로 실제 구매가 반영된다는 인상
- 운영/품질/물류/계약 제약이 생략된다는 인상

현실적인 포지셔닝은:

- 시장 변화 감지
- 조달 방향 재검토
- 근거 수집
- 승인 준비
- monitoring과 revision 지원

이다.

즉 이 제품은:

> **execution engine이 아니라 decision prep + approval + monitoring system**

으로 보여야 한다.

이 점이 프런트 구조와 카피에 충분히 반영되지 않으면
agentic함을 살리려다 오히려 현실성을 잃을 수 있다.

---

## 12. 정리: 지금 진짜 부족한 것은 무엇인가

현재 제품의 핵심 부족점은 아래 5가지로 요약된다.

### 1) Agent Bricks가 중심 orchestration layer로 안 보인다

있긴 있지만, 앞에 보이지 않는다.

### 2) Apps가 decision room이 아니라 dashboard처럼 보인다

즉 product surface로서의 의미가 약하다.

### 3) Lakebase가 case memory가 아니라 단순 persistence처럼 보인다

상태 기반 workflow가 전면에 덜 나온다.

### 4) Genie가 specialist agent가 아니라 질문응답 부속 기능처럼 보인다

structured evidence retrieval 역할이 충분히 드러나지 않는다.

### 5) case timeline과 next action 구조가 약하다

그래서 recommendation app처럼 보이기 쉽다.

---

## 13. 이 진단이 의미하는 것

이 문서의 결론은 단순히 "더 agentic하게 해야 한다"가 아니다.

더 정확한 결론은 이거다.

> **제품은 Agent Bricks 기반 multi-agent workflow처럼 보여야 하고,  
> 그 workflow가 Apps 안에서 case 형태로 소비되며,  
> Lakebase에 상태를 남기고,  
> Genie와 document agents가 evidence를 공급하는 구조가 전면에 보여야 한다.**

즉 지금 필요한 것은:

- 더 화려한 모델
- 더 많은 데이터
- 더 복잡한 backend

가 아니라,

- 더 선명한 orchestration visibility
- 더 분명한 역할 분리
- 더 강한 case workflow
- 더 정확한 Databricks-native framing

이다.

---

## 14. 다음 문서와의 관계

이 문서는 **진단서**다.

다음 문서들은 아래 역할을 가진다.

- `docs/frontend_restructure_proposal.md`
  - 어떻게 구조를 바꿀지 정리한 **처방전**

- `docs/home_validation_checklist.md`
  - 실제로 잘 됐는지 확인하는 **검증표**

즉 문서 구조는 다음처럼 이해하면 된다.

1. **Review** = 왜 문제인가
2. **Proposal** = 어떻게 바꿀 것인가
3. **Checklist** = 실제로 잘 됐는가

---

끝.