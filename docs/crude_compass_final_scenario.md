# Crude Compass — 최종 시나리오

> Databricks Building Intelligent Apps Hackathon 2026 (with AWS)
> 한국어 트랙 · Track 1 Social Impact (Open Data)
> 마감 2026-05-22 제출 → 심사 → 결과 발표
>
> 본 문서가 프로젝트 ground truth (2026-05-21 reports 모델 기준). 구현 계획은 [2026-05-21-reports-model.md](superpowers/plans/2026-05-21-reports-model.md), API 계약은 [api_contract.md](api_contract.md).

---

## 1. 한 줄 정의

**한국 정유사 원유 조달 의사결정 코파일럿.** 지정학·시장 시그널을 24시간 자동 종합해, AI가 먼저 보고서를 쓰고 매니저는 채택/기각만 판단한다. 결정은 사람, 분석은 AI, 동기화는 Lakebase, 데이터는 100% 공개 데이터.

- 위기 신호 누적 → HEDGE / DEFER SPOT 권고 (장기계약 비중 ↑, 스팟 구매 연기)
- 약세 신호 누적 → ACCELERATE SPOT / DIVERSIFY 권고 (저점 스팟 확보)
- 매일 아침 종합 일일 보고서(06:35) + 이벤트 발생 시 즉시 트리거 보고서

---

## 2. 사회적 임팩트 — 왜 Track 1인가

한국은 원유를 거의 전량 수입하며, 정유사의 조달 단가는 휘발유·경유·항공유 가격, 나아가 물가 전반에 직접 전가된다. 그러나 조달 의사결정은 여전히 소수 전문가의 경험과 단편적 정보에 의존한다.

> 사람은 호르무즈 봉쇄가 갑자기 터졌다고 보지만, 데이터에는 몇 주 전부터 선행 시그널이 있었다. AI가 지정학·재고·환율·생산량 시그널을 가격 반영 전에 종합하면, 한 번의 위기뿐 아니라 평시 매주 발생하는 중간 강도 시그널(OPEC 회의, EIA 재고, 사우디 감산, 환율 급변)까지 일상적으로 포착할 수 있다.

**핵심 가치는 위기 한 번이 아니라 평시 일상 도구라는 점.** 공개 데이터만으로 누구나 재현 가능한 구조라, 중소 정유사·트레이딩사·정책 기관으로 확장 가능하다.

---

## 3. 솔루션 — Reports 모델

매니저가 대시보드를 들여다보는 게 아니라, **AI가 먼저 보고서를 작성해 받은편지함에 넣는다.** 매니저는 읽고 "활성화"(채택) 또는 "기각"만 한다.

```
시그널 감지 (trigger)
   → AI 보고서 자동 작성 (Haiku-4-5)
   → 의사결정 받은편지함 (pending)
   → 매니저 활성화 / 기각
   → 06:30 curation(pattern_score 산출) → 06:35 일일 보고서가 활성화된 보고서들을 종합 → 비중 제안
   → 사용된 보고서는 자동 보관(archived)
```

이전 "mission" 모델(AI가 작업을 만들고 추적)을 폐기하고, **보고서 중심(read-and-decide)** 으로 단순화했다. 매니저의 인지 부하를 최소화하는 것이 설계 원칙.

---

## 4. 4-Tool 매핑 (해커톤 필수 4종)

| Tool | 역할 | 구현 |
|------|------|------|
| **Databricks Apps** | FastAPI + React SPA 단일 호스팅 | `app.yaml`, workspace OAuth 자동 주입 |
| **Genie** | 자연어 → 정형 데이터 질의 (가격·시그널) | space `01f150e05229190aa9de93c97afde034` |
| **Lakebase** | OLTP — 보고서·결정·AI 활동 이력 (ms 응답) | Postgres `ep-lucky-star-d1rlmmrr`, OAuth 토큰 회전 |
| **Agent Bricks** | Multi-Agent Supervisor 오케스트레이션 | Supervisor `mas-ba3fbcb5-endpoint`, KA `ka-6b456458` |

**Agent Bricks가 핵심.** 단일 엔드포인트에 자연어를 보내면 Supervisor가 3개 sub-agent(Genie 데이터 / Knowledge Assistant 문서 / 권고 생성)에 자동 라우팅하고, 응답을 종합한다. 일일 보고서 생성과 "조사" 콘솔 모두 이 Supervisor를 경유한다.

---

## 5. 데이터 소스 — 100% 공개 데이터

| 소스 | 데이터 | 수집 주기 |
|------|--------|-----------|
| GDELT | 지정학 뉴스 시그널 (importance, direction) | 15분 |
| OilPriceAPI | Dubai/Brent/WTI 실시간 가격 | 30분 |
| (일별 종가) | 두바이유 일별 OHLC | 평일 19시 |
| EIA | 미국 원유 재고 | 주간 (수) |
| OPEC MOMR | 월간 시장 보고서 (사우디 생산량·수요 전망) | 월간 |
| ECOS (한국은행) | USD/KRW 환율 | 평일 18시 |

Unity Catalog `crude_compass.{bronze,silver,gold}` 3계층으로 적재. 매일 06:30 curation job이 멀티소스 가중 합산으로 `pattern_score`(0~100, 가격 상승 압력 지표)를 산출한다.

---

## 6. 사용자 워크플로우 — 5개 메뉴

| 메뉴 | 기능 |
|------|------|
| **의사결정** | 오늘의 일일 보고서 + 비중 제안 + 트리거 보고서 받은편지함 (채택/기각) |
| **보관함** | 트리거/일일 보고서 history (활성화·기각·AI기각·보관, 필터) |
| **시황** | 유가·환율·pattern score 차트 (7/30/90일, Recharts 인터랙티브) |
| **자료실** | OPEC 월간 보고서 + 주요 보도 게시판 |
| **조사** | Agent Bricks Supervisor 자연어 조사 콘솔 (ChatGPT 스타일, 토큰 스트리밍, 대화 기록) |

---

## 7. Reports 모델 상세

**Trigger (3종)** — 보고서 자동 생성 조건:
- `gdelt_signal` — 뉴스 importance ≥ 80
- `price_spike` — Dubai 24h ±2%
- `pattern_drift` — pattern_score 7일 이동평균 대비 ±10pt

**Recommendation (6종)**: HOLD / DEFER SPOT / ACCELERATE SPOT / REVIEW TERM / HEDGE / DIVERSIFY

**Status flow**: pending → kept(활성화) / dropped(기각) / ai_dropped(AI 기각) → archived(일일 보고서 입력으로 사용 후 자동 보관)

**일일 보고서 (06:35, curation 06:30 직후)**: 활성화된 트리거 보고서들을 Agent Bricks Supervisor가 종합 → 텀/스팟 비중 델타 제안(direction: lean_hedge / neutral / lean_opportunity).

모든 보고서는 비용 절감을 위해 `databricks-claude-haiku-4-5`로 생성.

---

## 8. AI Agent 아키텍처

```
매니저 자연어 질문
   → Agent Bricks Supervisor (단일 엔드포인트)
       ├─ Genie sub-agent      (정형 데이터: 가격·생산량)
       ├─ Knowledge Assistant  (비정형 문서: OPEC MOMR RAG)
       └─ 권고 생성 sub-agent   (조달 권고 종합)
   → 토큰 스트리밍 (SSE) → 프론트 실시간 표시
```

- **스트리밍**: OpenAI Responses API `stream=True` → SSE → 프론트가 토큰 단위 렌더 + sub-agent 호출 trace 표시
- **투명성**: 어떤 sub-agent를 거쳤는지 응답에 노출 → "AI가 일하고 있다"는 신뢰
- **Genie 미설정 시 fallback**: SQL Warehouse 직접 질의로 graceful degrade

---

## 9. 5분 데모 흐름

1. **의사결정** — 오늘 일일 보고서 + AI가 자동 생성한 트리거 보고서 받은편지함. 하나 "활성화".
2. **조사** — "지금 같은 시장 상황은 과거에 어떻게 됐어?" 입력 → Supervisor가 Genie/KA 거쳐 토큰 스트리밍으로 답변. sub-agent trace 노출.
3. **시황** — pattern score + 유가 추이 인터랙티브 차트.
4. **자료실** — OPEC 월간 보고서 원문 + 주요 보도.
5. 마무리: "결정은 사람, 분석은 AI, 데이터는 100% 공개." Track 1 Social Impact 메시지.

---

## 10. 기술 스택

- **Frontend**: React 18 + TypeScript + Vite + TanStack Query + Tailwind 3 + Recharts + react-markdown
- **Backend**: FastAPI + Pydantic v2 + psycopg3(ConnectionPool) + SSE/WebSocket
- **Data/AI**: Databricks Apps · Unity Catalog · Genie · Lakebase(Postgres) · Agent Bricks · Foundation Model(Haiku-4-5)
- **Jobs**: Lakeflow (gdelt 15분, price 30분, daily curation 06:30 / report 06:35 등)

---

## 11. 비용 효율

공개 데이터 + serverless로 운영 비용을 최소화했다 (2026-05-21 최적화):

- 가격 파이프라인 5분 → 30분
- SQL Warehouse auto-stop 60분 → 10분
- Lakebase 8~16 CU → 0.5~1 CU + scale-to-zero
- Live Pulse REST polling(5초) → WebSocket 전환으로 Lakebase idle 보존
- 모든 LLM 보고서를 Haiku-4-5로 생성

---

## 12. 차별점

- **양방향**: 위기(HEDGE)뿐 아니라 기회(ACCELERATE SPOT)도 포착
- **선제적**: 가격 반영 전 선행 시그널 종합
- **투명한 Agent**: sub-agent 라우팅을 실시간 노출, 환각이 아닌 데이터 기반
- **재현 가능**: 100% 공개 데이터 — 누구나 같은 파이프라인 구축 가능
- **인지 부하 최소화**: 대시보드 응시가 아니라 "AI가 쓴 보고서를 채택/기각"
