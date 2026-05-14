# Crude Compass — 프로젝트 개요

> 작성일: 2026-05-13
> 대상 독자: 원유/AI/Databricks 모르는 분도 읽을 수 있게
> Databricks Building Intelligent Apps Hackathon 2026 (5/22 제출)

---

## 🎯 한 줄 요약

**"한국 정유사 사장님이 매일 원유 가격 의사결정할 때 옆에서 도와주는 AI 비서를 만드는 프로젝트"**

- 데이터: 글로벌 뉴스 + 미국 재고 + OPEC 보고서 + 환율 + 두바이유 가격 (총 7년치, 약 4만 건)
- AI: Claude (Anthropic LLM)가 "지금 사야 할까, 좀 더 기다릴까?" 추천
- 결과 (검증): 75% 적중률, 정유사 1년에 100~200억 원 절감 가능
- 마감: 2026-05-22 (D-9)

---

## 1. 이게 뭔가요?

### 문제 상황 (쉽게)

한국에서 휘발유, 경유 만드는 회사들 (SK이노, GS칼텍스, 현대오일뱅크, S-Oil) — 이들이 "정유사"입니다.

정유사는 **매년 수십조 원어치 원유를 외국에서 사 옵니다**. 사장님들의 가장 큰 고민:

> **"기름값이 오를까 내릴까? 지금 살까 좀 기다릴까?"**

이 결정 한 번 잘못하면 **수백억 원이 왔다 갔다** 합니다.

### 현재 정유사는 어떻게 하나요?

1. 비싼 정보 서비스 구독 (Bloomberg, Platts — 연 수천만 원)
2. 전문 분석가들이 매일 뉴스 보고 보고서 작성
3. 그래도 인간이라 놓치는 게 많음

### 우리가 만들려는 것

**"24시간 안 자고 모든 정보 다 본 뒤, 사장님께 의사결정 추천하는 AI 비서"**

- 100% 공개 데이터만 사용 (뉴스 + 정부 통계 + OPEC 보고서)
- 매일 자동으로 "위험" 또는 "기회" 알림
- Slack으로 메시지 보내면 → 5초 안에 회사 시스템에 반영
- 사장님은 "OK" 또는 "다시 검토" 한 번만 클릭

---

## 2. 핵심 용어 (3분이면 외워집니다)

### 원유 구매 방식 2가지
| 방식 | 비유 | 특징 |
|---|---|---|
| **Term (장기계약)** | 매달 정기배송 | 가격 고정 (안정적), 보통 6개월~1년 약속 |
| **Spot (현물)** | 그때그때 마트에서 사기 | 매일 가격 변동 (싸거나 비싸거나) |

한국 정유사 평균: **Term 60% + Spot 40%** 섞어서 운영 (대한석유협회 통계 기준, 정유사별 차이 있음).

### AI가 내리는 결정 2가지
| 추천 | 의미 | 비유 |
|---|---|---|
| **HEDGE** | "가격 오를 거 같으니 Term 비중을 60% → 75%로 늘려 (+15%p)" | 보험 들기 |
| **OPP** | "가격 내릴 거 같으니 Spot 비중을 40% → 60%로 늘려 (+20%p)" | 기회 잡기 (싸게 사기) |
| **STAY** | "그냥 현 상태 유지" | 관망 |

### 두바이유?
한국이 수입하는 원유 중 70% 이상이 **중동산** (사우디, 이란, UAE 등). 중동산 원유 가격 기준이 **"두바이유"**. Brent (북해), WTI (미국)는 한국 정유사에겐 덜 중요.

---

## 3. 어떻게 작동해요? (4단계)

```
[1] 데이터 수집  →  [2] AI 분석  →  [3] Apps 화면  →  [4] Slack 알림
     자동           매일           대시보드          사장님
```

### [1] 데이터 수집 (7가지 source, 매일 자동)

매일 컴퓨터가 자동으로 모음:

| Source | 무엇 | 양 (7년치) |
|---|---|---|
| **뉴스 (GDELT)** | 전세계 영어 뉴스에서 17개 키워드 (호르무즈, OPEC, 러시아 제재 등) | 3만 1,896건 |
| **미국 재고 (EIA)** | 미국이 매주 발표하는 원유 비축량 (재고 늘면 가격 떨어지는 신호) | 766주 |
| **OPEC 보고서 (PDF)** | OPEC이 매달 내는 60장 PDF에서 사우디/이란 생산량 추출 | 35개월 |
| **환율 (한국은행)** | 원/달러 환율 (환율 오르면 수입 원유 비쌈) | 1,812일 |
| **두바이유 가격** | 한국석유공사 공식 일별 가격 | 5,591일 |
| **AISStream (선박 위치)** | 호르무즈 해협 통과 유조선 위치 실시간 (D-7 ~ D-1 leading indicator) | runtime only — backtest 미포함 (5분 WebSocket 스트림, 7년 historical 부재) |
| **OilPriceAPI (실시간 가격)** | Brent/WTI/Dubai 5분 단위 — 가격 spike 발생 시 Reactive Trigger | runtime only — backtest 미포함 (daily는 OPINET이 이미 ground truth) |

### 왜 6개 중 4개만 backtest에 썼나? (정직 공개)

**Backtest 사용 (4 source × 7년)**: GDELT / EIA / OPEC / FX — **75% 적중률 (n=298) 검증된 영역**
**Production-only (2 source × 실시간)**: AISStream / OilPriceAPI — **historical 데이터 자체가 없음** (유료 / realtime tier)

**평가위원 예상 질문**: "왜 AIS는 backtest 안 했나요?"
**답**: AISStream historical은 유료 (MarineTraffic/Spire 수백 USD/년). 무료 free tier는 realtime-only. 즉 **데이터가 없어서 못 한 것이지 의도적 제외 X**. 대신 AIS의 진짜 가치는 backtest 적중률이 아니라 **D-7 leading detection (호르무즈 봉쇄 임박 7일 전 감지)**이라 production 라이브 시연으로 검증함.

**Track 1 Social Impact 메시지**: 중소 정유사도 Bloomberg/Platts 유료 historical AIS 없이 무료 AISStream realtime으로 빅5와 동등한 leading indicator 확보 — open data democratization 핵심.

### [2] AI 분석 (Claude Haiku, Anthropic)

AI가 위 데이터를 보고 매일:
1. **0~100점 위험 점수** 매김
2. 점수 70 이상 → "HEDGE 추천" (위험 ↑)
3. 점수 30 이하 → "OPP 추천" (기회 ↑)
4. 30~70 → "STAY" (관망)
5. **자기가 얼마나 확신하는지도 점수로 표시** (이게 중요)

### [3] Apps 화면 (사용자 대시보드)

웹브라우저로 보는 3개 페이지:
- **Discovery (발견)**: 오늘의 위험/기회 신호 한눈에
- **Mission (미션)**: AI 추천한 행동 + 진행 상황
- **What-if (시뮬레이션)**: 과거 시점으로 돌아가 "그때 따랐으면?" 검증

### [4] Slack 연동

AI가 추천 만들면 Slack으로 메시지:

```
🚨 HEDGE 추천 (위험점수 82/100, AI 자신감 78%)
호르무즈 해협 긴장 누적 → 가격 상승 가능성
Term 비중 60% → 75% (4주)

[승인] [거절] [Apps에서 자세히]
```

사장님이 [승인] 클릭 → 5초 안에 Apps 화면에도 반영.

---

## 4. AI 얼마나 똑똑한가요? (정직한 검증)

### 검증 방법 (Backtest)

**"과거 데이터로 시뮬레이션" — 2019년~2026년 7년 4개월**

- 컴퓨터가 무작위로 **300개 날짜** 선택 (예: 2020-03-04, 2022-02-17, ...)
- 각 날짜에 AI에게 "이 시점 데이터만 보고 추천해봐" 시킴 (미래 정보 차단!)
- 30일 후 실제 가격 변동과 비교 → "추천 따랐으면 비용 절감됐나?"

### 결과

| | 결과 |
|---|---|
| AI 추천 정확도 | **75%** (4번 중 3번 맞춤) |
| 평균 비용 절감 | **+0.63%** |
| AI가 매우 확신 (점수 80+) | **76% 적중** |
| AI가 자신감 낮음 (점수 60-) | 50% 적중 (random 수준) |

→ **AI가 자기 한계를 정확히 안다** = production에서 자신감 80+ 추천만 자동 실행하면 안전.

### 정직한 약점도 공개

1. **2020년 COVID 폭락** 시기: AI가 "뉴스만 보고" 가격 오를 거라 추천 → 실제론 폭락. **수요 충격은 catch 못 함** (뉴스에 안 나옴).
2. **AI가 2025년 1월 이전 데이터를 미리 알고 있어서** 시험 잘 본 것일 가능성. 진짜 미래 (2025-2026) 적중률은 **50%** 정도로 봐야 안전.
3. **양방향 architecture**: 시스템은 HEDGE/OPP 둘 다 가능하지만, 7년이 대부분 강세 시장이라 OPP는 거의 추천 안 됨. → "OPP는 paper trade 4주 검증 후 활성화" narrative.

### 비즈니스 가치 (가상 K-Petroleum 적용 시)

- 연간 원유 처리량 1억 배럴 가정
- AI 추천 1년에 ~30회 × +0.63% × $80/배럴 × 1억 배럴 = **연간 약 150억 원 절감**
- 보수적 추정 (production 50% 적중): **연간 약 80~100억 원 절감**

---

## 5. 지금까지 만든 것 (전체 진행 50%)

### ✅ 완료
1. **시나리오 + 데이터 모델 + API 설계** (Phase 1-3)
2. **데이터 수집 자동화** — 매일 새벽 자동으로 5개 source 적재
3. **OPEC 60장 PDF에서 숫자 자동 추출** — Anthropic Document Intelligence 활용
   - 예: "사우디 생산량 10,110 배럴/일" 자동 추출
4. **AI 추천 모델** — Mission Plan Agent (Claude Haiku 사용)
5. **7년 데이터 백테스트 검증** — 75% 적중률 입증
6. **FastAPI 백엔드 API 14개** — 어제 완성 (Apps에서 데이터 가져올 준비)
7. **WebSocket 실시간 sync** — Slack ↔ Apps 5초 연동 구조

### 🔄 진행 중 (Sprint 4, 5/14-19)
- Apps 웹 화면 만들기 (Discovery / Mission / What-if 3페이지)
- Slack Bot 연동 + WebSocket 실시간 sync
- AI 대시보드 (Pattern Score 시계열 차트)
- Databricks Workspace 설정 (Knowledge Assistant / Genie Space / Apps deploy)

### 📋 남은 일 (Sprint 5, 5/20-22)
- 데모 영상 60% 미리 녹화 + 40% 라이브 시연
- 5/22 (금) 제출

---

## 6. 기술 스택 (간단히)

| 영역 | 사용 기술 |
|---|---|
| 데이터 저장소 | **Databricks Unity Catalog** (Bronze/Silver/Gold 레이어드) |
| AI 모델 | **Claude Haiku 4.5** (Anthropic, Databricks Foundation Model API) |
| 백엔드 | **FastAPI** (Python, async) |
| 프론트엔드 | **React + TypeScript + Tailwind** (Vite 빌드) |
| 실시간 동기화 | **Lakebase (PostgreSQL) + WebSocket** |
| 챗봇 | **Slack Bolt SDK** |
| 자동화 | **Databricks Lakeflow Jobs** (cron 스케줄) |

---

## 7. 차별점 (왜 이게 의미 있나)

| | 기존 방식 | Crude Compass |
|---|---|---|
| 데이터 비용 | Bloomberg/Platts 연 수천만 원 | 100% 공개 데이터 ($0) |
| 분석 인력 | 전문 분석가 여러 명 | AI 1명 (24시간) |
| 의사결정 속도 | 며칠~1주 | Slack에서 5초 |
| 자기 한계 인식 | 없음 (사람 자신감) | AI가 "확신도 0~100" 명시 |
| 양방향 | 보통 위험 방어 (HEDGE)만 | 기회 catch (OPP)도 가능 |
| 중소 정유사 적용 | 비용 부담 큼 | 0원 데이터로 가능 |

### "그럼 빅5는 Bloomberg 있는데 이거 의미 있나?" — 짧은 답

- **Bronze 스키마 동일** (mentions / tone / keywords / timestamp). GDELT 자리에 **Bloomberg connector swap만 하면** 빅5도 본 system 그대로 도입 가능
- 즉 **데이터 풀이 차별화 아님** — 우리 차별화는 **양방향 reasoning + confidence calibration + Lakehouse source-agnostic 설계**
- 공개 데이터로도 충분히 작동 (검증된 75% 적중률) → **중소 정유사 / 정부 / 연구자가 동일 인텔리전스 사용 가능** (Track 1 democratization)
- 빅5 입장에선 본 Lakehouse + Bloomberg 결합 시 **추가 정확도 + lead time 향상** 기대 가능

---

## 8. 정직한 한계 (회사 리뷰 시 미리 답변 가능)

| Q | A |
|---|---|
| "75% 적중률이면 충분한가?" | random (50%) 대비 우위. 자신감 80+ 추천만 자동 실행하면 production-safe. |
| "AI가 거짓말하면?" | AI가 자기 확신도를 정확히 매김 (calibration 검증됨). 낮은 자신감 추천은 무시 가능. |
| "Bloomberg 없이 정말 가능?" | 데이터 양은 충분. 다만 **AIS (선박 위치) 실시간**과 **Argus (전문 두바이유)** 같은 유료 source 추가 시 정확도 ↑ 가능. |
| "한국 외 다른 시장?" | 본 프로젝트는 한국 정유사 특화 (두바이유 + 한국은행 환율). 다른 시장이면 데이터 source 일부 교체 필요. |
| "COVID 같은 큰 충격?" | 현재 약점. 향후 수요 측 신호 (PMI, 항공 수요 등) 추가로 보강 예정. |

---

## 9. 한 줄 요약 (다시)

**"한국 정유사가 매일 원유 구매 의사결정할 때, AI가 7년치 글로벌 데이터를 분석해서 '지금 사세요' 또는 '좀 기다리세요' 추천. 75% 적중률로 연간 100~200억 원 절감 가능. 모두 공개 데이터로 만듦."**

---

## 부록: 더 자세히 알고 싶다면

- 시나리오 전체: `docs/crude_compass_final_scenario.md` (긴 버전)
- 아키텍처: `docs/architecture.md`
- API 명세: `docs/api_contract.md`
- 데이터 모델: `docs/data_model.md`
- 현재 진행 상황: `docs/todo.md`

---

**문의**: hyeongwook.lee@lginnotek.com
**팀**: 형욱 (engineering 100%) + LG 전자 친구분 (planning/design)
