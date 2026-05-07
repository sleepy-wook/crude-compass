# Term/Spot Decision Support Agent

> Databricks APJ Hackathon 2026 — 한국어 트랙 / Track 1 (Social Impact, Open Data)
> 작성: 이형욱 (LG Innotek Gen AI Engineer)
> 마감: 2026-05-22

## 한 줄 요약

**AI는 미래를 예측하지 않는다. 정유사 매니저가 Term/Spot 비중을 결정할 때 필요한 모니터링·시뮬·자동 협상을 24/7 제공한다.**

결정은 사람, 정보 우위는 AI.

---

## Social Impact (Track 1 — Energy Security)

> **호르무즈 봉쇄는 단순 기업 issue가 아닌 한국 에너지 안보 사회적 위기.**

- 한국 원유 도입 73.5%가 중동 의존 (2018년 기준, 대한석유협회)
- 봉쇄 1주일 = Brent +60% / Dubai +73% 기록
- 영향: 정유 9사 → **5,000만 국민 휘발유·등유·항공유 가격**
- 도입 차질 시: 정제 가동 중단 → 석유화학 → 자동차·반도체·항공·해운 connected
- 한국 GDP의 ~30%가 호르무즈 통과 원유와 직접 연결

### Open Data로 사회 문제 해결

- **AIS aisstream** (공공): 호르무즈 통과량 실시간
- **OilPriceAPI** (open): WTI/Brent/Dubai 가격
- **GDACS** (UN/EU 공식): 글로벌 재해 events
- **ECOS 한국은행** (공공): 환율
- **News RSS** (Reuters·AP·연합뉴스 무료)

→ 모든 데이터 무료·공공·open. 정유사가 SaaS 도입 시 동일 architecture로 자사 데이터만 추가.

→ **Track 1 "energy efficiency" 직접 fit**: 한국 정유사 의사결정 정확도 ↑ = 도입 비용 ↓ = 5,000만 국민 에너지 가격 안정.

---

## 환경

- **Databricks Express account** ($700 credit, Premium tier 전체 기능)
- Databricks Apps · Genie · Lakebase Autoscaling (GA) · Agent Bricks Custom Agents (GA)
- Frontend: Next.js 15 + Tailwind + shadcn/ui + Framer Motion
- Backend: FastAPI (Apps 안에 hybrid deploy)

---

## 배경 — 2026 호르무즈 위기 (시연 시점 진행 중)

```
2/28  Operation Epic Fury — 호르무즈 군사 작전 시작
3/01  호르무즈 봉쇄 (이란)
3/02  Stena Imperative 피격 + 헤즈볼라 참전
3/03  JWLA-033 발효 (전쟁구역 신규)
3/05  GS Caltex·HD Hyundai Oilbank VLCC 호르무즈 stranded 시작
3/13  한국 정유사 비상 charter 경쟁 (VLCC 일당 $400K+)
4/30  Brent $126 (4년 최고치) / Dubai $166 (사상 최고)
5/01  휴전 결렬
[현재] 봉쇄 지속, 한국 정유사 도입 차질
```

→ **시연 시점에 진행 중인 진짜 위기**. 가상 시나리오 아님.

---

## 페르소나

### K-Petroleum (가상 한국 정유사)

**페르소나 매니저**: 김지훈 (가상)
- 30대 후반, 원유조달팀 시니어 매니저
- 매월 단위 원유 구매 결정 (정제 가동 위해 연속 도입)
- 선적 월 기준 2개월 이전부터 거래 시작
- 3개월 후 공장 가동·수급 계획 작성 (대한석유협회 공식)

**가상 회사 spec**:
- 정제 capacity: 일 80만 배럴 (한국 평균)
- 도입 75%+ Dubai 가격 연동 (한국 표준, 아빠 인풋)
- baseline: Term 50% : Spot 50% (균형 전략)

**매일 하는 일**:
- 원유 가용량·가격·판매자·정제 capacity 매칭 모니터링
- 매월 Aramco Formula·UAE OSP 발표 후 lifting 전략 결정
- 5대 석유제품 (나프타·등유/제트유·경유·중유) 국내외 소비량 + 수출 경제성 분석
- Term/Spot 비중 동적 조정

### Cargo 데이터 — GS Caltex VLCC (진짜 데이터)

**가상 페르소나 + 진짜 cargo 데이터** = 솔직하고 시연 강함.

**Why GS Caltex** (한국 정유 4사 중):
- 호르무즈 봉쇄 진행 중 GS Caltex VLCC 2척 stranded (2026-04 기준, Seoul Economic Daily 보도)
- Yeosu 정제 capacity 80만 b/d → K-Petroleum 가상 capacity와 매치
- 비상장 (GS·Chevron 합작) → 주가 영향 risk 0
- 단순 정유 회사 → narrative 깔끔

**aisstream filter**:
- Korean flag VLCC + GS Caltex charter 선단
- 약 5~10척 실시간 추적 가능

**데모 narrative**:
> "K-Petroleum (가상)이 GS Caltex 선단의 진짜 cargo 위치를 통해
> 호르무즈 봉쇄 영향을 실시간 모니터링한다.
> 진짜 정유사 도입 시 자사 cargo MMSI로 1줄 변경."

### 사용자 base

- **1차 (핵심)**: 한국 정유 4사 + 석유화학 5사 = 9개 회사 × 매니저 5~10명 = 수십~백 명
- **2차 (broaden)**: 종합상사·항공·해운·에너지 수출입 임원
- **잠재**: 한국 수출입 30만 기업 × 전략 임원 5명 = **150만**

---

## 한국 정유사 도입 메커니즘 (대한석유협회 공식 ground truth)

### 시장 구조

```
국제원유시장
├── 선물시장 (거래소 있음)
│   ├── NYMEX (뉴욕)    → WTI
│   ├── ICE (런던)      → Brent
│   └── DME (두바이)    → Oman/Dubai (2007 개설)
│
└── 실물시장
    ├── 현물시장 (Spot)
    │   └── 중동·아시아 기준원유: Dubai
    │       └── Platts e-window 플랫폼 (싱가포르)
    │
    └── 기간계약시장 (Term) — 3종
        ├── Long-term:    1년+ 가격 포뮬러 고정
        ├── Semi-Term:    1년 이하 일정량
        └── Frame:        물량만 합의 + 매 시점 가격 협의 ⭐
```

### 한국 정유사 진짜 reference = Dubai

> **"국내 정유회사들은 대부분 Dubai 현물가격에 연동되는 중동지역 원유를 위주로 구매"** (대한석유협회)

아빠 (前 LG화학 NCC 공장장) 인터뷰:
> "한국 도입 75% 이상이 Dubai 가격 연동.
> Dubai는 중질유 (탄소수 ↑) → 한국 정유사가 정제 시설 보유.
> 정제 후 나프타·등유·중유 yield가 한국 시장 fit."

→ **Dubai 가격 = 한국 정유사 의사결정의 가장 중요한 단일 변수**

### Aramco / 중동 산유국 가격 공식

| 방식 | 채택 국가 | 메커니즘 |
|---|---|---|
| **Formula** | 사우디·쿠웨이트·이란·이라크 | 매월 미리 발표 (지역별: 미국=WTI / 유럽=Brent / 아시아=Dubai) |
| **OSP** | UAE·카타르·말레이시아 | 선적월 다음달 초 OSP (Official Selling Price) 발표 |

### 도입 비중 baseline

> "전체 원유 도입량의 약 60% (2018년 57.0%)를 장기계약으로 도입" (대한석유협회 공식)

회사별 다름:
- **K-Petroleum (가상) baseline = Term 50% : Spot 50%** (균형 전략)
- AI가 매크로·가격·지정학·회사 4종 input 종합해서 dynamic 조정 권고

### 유전스 (Usance) — 환율 risk 메커니즘

- 원유 도입 = 외상구매 (대금 유예)
- B/L (선적일) + 30일 = 1차 결제일
- Banker's Usance: 추가 합의 기간
- 실제 결제 = B/L + 30일 + 합의기간

→ 구매-결제 시차 (수십 일) 동안 환율 변동 시 차손/차익 발생
→ AI agent가 진행 중 Usance 포지션의 환율 risk 정량 산출

### 사우디·쿠웨이트 재판매 금지

> "아시아 지역 구매자가 현물시장에 재판매 시 승인 필요"

→ Frame Contract 협상 시 법무 review 필요 항목 (AI agent가 자동 검토)

### Arbitrage 기회

5대 석유제품 (나프타·제트유·경유·중유) 지역간 가격차 차익 거래 활발
→ AI agent가 24/7 모니터링 + 매니저 알림

---

## AI 4종 input → Dynamic 비중 조정

K-Petroleum baseline 5:5에서 AI가 4종 input 종합해서 risk score 산출 → 조정 권고.

### Input 1: 매크로 환경
- 글로벌 GDP forecast (IMF·World Bank)
- 주요국 금리 (Fed·ECB·한국은행)
- 환율 (KRW/USD)
- 경기 침체/호황 (IEA OMR)

### Input 2: 원유 가격 dynamics
- WTI·Brent·**Dubai** 3종 가격 + 변동성
- spread (Brent vs Dubai = 아시아 프리미엄)
- 선물 contango/backwardation

### Input 3: 지정학 이슈
- **호르무즈 통과량 집계** (AIS) — 평시 ~3,000척/월 → 위기 ~191척
- **GS Caltex 선단 cargo 위치** (AIS) — 우리 stranded 2척 + 항해 중 cargo 추적
- 재해 (GDACS)
- War zone 변경 (JWC)
- 뉴스 streaming (Reuters·AP·연합뉴스)

### Input 4: 회사 자체 변수
- Usance 진행 포지션 (환차손 risk)
- 정제 capacity utilization
- 5대 석유제품 spread (정제 마진)

→ AI는 weighted ensemble이 아니라 **LLM reasoning으로 종합 판단**.
→ 가중치는 회사 정책에 따라 customize 가능.

### Risk Score → 권고

```
baseline:        Term 50% : Spot 50%  (K-Petroleum 균형 전략)

risk 0~30:       Spot +5pt   (5:5 → 4.5:5.5)  저비용 추구
risk 30~60:      5:5 유지    (baseline)
risk 60~80:      Term +10pt  (5:5 → 6:4)      헤지 시작
risk 80~100:     Term +20pt  (5:5 → 7:3)      강력 헤지
```

**AI는 권고만, 결정은 매니저.**

---

## 데이터 5종 + News Pipeline

### 검증된 정량 source 5종

| Source | 데이터 | 검증 |
|---|---|---|
| **OilPriceAPI** | WTI + Brent + **Dubai** + 가솔린·디젤 (REST 5분 갱신) | ✅ 2026-05-06 |
| **AIS aisstream** | 호르무즈 통과량 + GS Caltex VLCC 선단 (WebSocket) | ✅ 2026-05-03 |
| **GDACS** | 글로벌 재해 events (REST, no auth) | ✅ 2026-05-06 |
| **ECOS 한국은행** | KRW/USD 환율 종가 (REST) | ✅ 2026-05-06 |
| **JWC PDF** | War zone (Lloyd's Market Association) | ⏳ Manual download |

### AIS 두 가지 활용

**1. 호르무즈 통과량 집계 (BoundingBox)**
- 호르무즈 해협 BoundingBox 모든 선박 count
- 평시 ~3,000척/월 → 위기 ~191척 (CNN 인용 가능)
- → risk score Input 3 (지정학) 정량 indicator

**2. GS Caltex VLCC 선단 추적 (MMSI filter)**
- Korean flag + GS Caltex charter 선단
- 진행 중 cargo 위치·ETA·호르무즈 진입 여부
- 데모 시연에 진짜 cargo 표시 (회사명 익명 처리 가능)
- → "우리 cargo 어디 있나" 매니저 wow

### News Pipeline (RSS 통합)

**신뢰성 source만**:
- **Tier A 속보**: Reuters · AP · 연합뉴스 · FT · BBC RSS
- **Tier B 1차**: EIA STEO · IEA OMR · OPEC Monthly · OFAC SDN · Aramco IR · 한국 외교부 RSS

**제외**:
- ❌ Naver 검색 (광고·블로그 fake news risk)
- ❌ 일반 web search (Reddit·Twitter)

```
[5분마다]
  Tier A + Tier B RSS fetch
    ↓
  키워드 필터 (호르무즈·OPEC·Aramco·force majeure)
    ↓
  LLM 관련성 분석 (Claude Haiku 등 cheap)
    ↓
  관련성 > 50점 → 매니저 알림
```

---

## 24/7 Streaming Architecture (2-Tier)

### Tier 1: Daily Curation (06:30 KST cron)
- 5종 데이터 + 뉴스 종합 fetch
- risk score 정량 갱신
- Discovery Feed 3-5건 큐레이션
- LLM heavy (1회/일)

### Tier 2: Realtime (5분 cron)
- OilPriceAPI 가격 + 뉴스 RSS fetch
- Rule-based 필터 (2% 이상 변동, 키워드 매칭)
- Anomaly만 LLM 분석 → 긴급 alert
- Lakebase events 테이블에 기록

### Background (continuous)
- AIS WebSocket long-running job (호르무즈 + GS Caltex 선단)
- Mission lifecycle (4주 mission 매일 progress 체크)
- Self-critique (매주 1회)

### 비용

| Layer | 빈도 | 일 비용 |
|---|---|---|
| Tier 1 Daily | 1회/일 LLM heavy | ~₩500 |
| Tier 2 rule filter | 5분마다 | ₩0 |
| Tier 2 LLM | anomaly ~10건/일 | ~₩1,000 |
| Mission progress | 매일 | ~₩300 |
| **총** | | **~₩2,000/일** = 매니저당 월 ~₩6만원 |

---

## 매니저 하루 일과 (16분)

### 04:30 — Tier 1 Daily Curation
- AI가 5종 데이터 + 뉴스 모니터 시작
- risk score 정량 갱신
- 진행 mission 점검

### 05:43 — News Trigger
- Reuters: "이란 외무부 강경 발언"
- AIS: "호르무즈 통과량 -28% (어제 대비)"
- AIS: "우리 GS Caltex cargo #003 호르무즈 진입 5분 전"
- → risk score 65 → 78 정량 변화 감지

### 07:30 — 출근길 5분 (Discovery Feed swipe)
- 매니저 폰으로 3-5건 review

### 09:00 — 책상 10분
- Yesterday Review (어제 결정 outcome)
- Living Mission Dashboard (4주 mission 진행)
- What-If 시뮬 (Genie NL)

### 11:42 — Tier 2 Realtime Alert (낮 동안 발생)
- OilPriceAPI: Brent +3.2% spike (5분 rolling)
- LLM 분석: "OPEC 갑작스러운 발표 가능성"
- → 즉시 매니저 긴급 알림. 회의 중에도 1탭 review

### 14:15 — Aramco Formula 발표 임박
- Reuters: "Aramco June Formula 발표 30분 전"
- AP confirm
- → 시뮬 시작, 5분 후 결과 push

### 09:30~17:00 — AI 백그라운드
- 4사 Frame Contract RFQ chaining (필요 시)
- Mission progress 자율 체크
- Self-critique

### 17:00 — Daily Wrap 1분

→ **사람 16분 / AI 24/7 / mission 4주**
→ 하루 평균 매니저 push: 정기 1회 + 긴급 2-3회 = 3-5회

---

## Discovery Feed (3-5건/일)

### 1. 현재 Risk Score + 비중 권고
> "지정학 risk score 78 (어제 65). 현재 Term 55% / K-Petroleum baseline 50%.
> AI 4종 input 종합 → Term **+15pt 권고 (5:5 → 6.5:3.5)**.
> 시뮬: Brent $130 / WTI $115 / Dubai $128 시 +320억. 결정?"

### 2. 우리 Cargo 호르무즈 진입 알림
> "GS Caltex VLCC #003 (Korean flag, 320K DWT) 호르무즈 진입 D-1.
> 호르무즈 통과량 어제 -28%. ETA 변동 가능성. 정제 capacity 조정?"

### 3. Aramco Formula / OSP 발표 알림
> "사우디 Aramco Formula June 발표 D-2 (5/5). UAE OSP는 5/15 예정.
> 시장 예상 +$15(40%) / +$10(30%) / +$6(30%) 시나리오별 시뮬 도착."

### 4. Frame Contract 견적 비교
> "4사 Frame Contract RFQ 답신 도착.
> BP $87.5 / Aramco $92 (Dubai+OSP) / ADNOC $89 / TotalEnergies $88.
> 사우디·쿠웨이트 재판매 금지 조항 검토 완료. 어디 lock?"

### 5. Mission confirm 대기
> "Term 70% mission D+18 — Aramco 추가 500K bbl Frame Contract confirm 대기."

### 보너스 (필요 시)
- Spot pickup 기회 (호르무즈 통과 cargo 발견)
- Arbitrage 기회 (5대 석유제품 지역간 차익)
- Usance 환율 alert (진행 포지션 환차손 risk)
- EIA STEO 신규 발표

---

## Living Mission 예시

### Mission: "Term 50% → 70%" (4주, 호르무즈 봉쇄 헤지)

```
시작: 2026-04-15 (매니저 결정)
Target: 4주 (D+28)
현재: D+18

[Timeline]
D+1   ████ 4사 Frame Contract review (AI)
D+3   ████ 시뮬: Brent $100/$120/$140 + Dubai 시나리오 ROI (AI)
D+5   ████ Aramco·ADNOC RFQ 발송 (AI)
D+8   ████ 답변 NL 파싱 + 사우디 재판매 조항 검토 (AI)
D+10  ████ 매니저 confirm — "Aramco 500K bbl 추가 lock" (👤)
D+12  ████ 법무 force majeure review (AI)
D+15  ████ 계약 체결 + Usance 환율 헤지 추천 (AI)
D+18  ████ ← 지금. CFO 협의 + 환율 risk +12억 (👤)
D+25  □□□□ Spot 비중 줄이기 (예정)
D+28  □□□□ 종료 + 7·30일 outcome 추적

[누적]
매니저 confirm: 18일 동안 3번
AI 자율 작업: 18일 동안 47개
시뮬 결과: Brent $130+Dubai $125 시 +320억 / Brent $90+Dubai $85 시 -50억
Cargo 추적: GS Caltex 선단 5척 중 2척 호르무즈 stranded, 3척 정상 항해
```

→ AI는 시뮬 + 자동 협상만. **결정은 매니저.**

mission state는 Lakebase에 영속. 매니저가 회의·휴가에도 mission은 살아있음.

---

## Databricks 4-tool 매핑 + AI/BI Dashboard

| Tool | 역할 | Wow 모먼트 |
|---|---|---|
| **Apps** | Next.js + FastAPI hybrid<br>3 page (Feed / Mission / What-If) | mobile-friendly UI |
| **Genie** | NL 시뮬 ("Brent $140 가면?")<br>Agent Mode (2025-09 GA) | ⭐ Wow 3 |
| **Lakebase** | 4주 mission state + 4사 협상 + audit trail<br>Autoscaling Postgres | ⭐ Wow 1 |
| **Agent Bricks** | Custom Agents 4개 (GA):<br>Monitoring · Simulation · RFQ Chaining · Self-Critique | ⭐ Wow 2 |
| **AI/BI Dashboard** | Yesterday Review 페이지에 embed<br>30일 Risk Score + 호르무즈 통과량 + 가격 history + 매니저 결정 outcome | Storytelling fit |

각 Wow 모먼트가 4-tool 1개씩 정확 매칭. AI/BI Dashboard는 Storytelling 보조 도구.

### "대시보드 넘어 + 대시보드도 활용" 양쪽 다

해커톤 메시지:
- "**Go beyond dashboards**" → Decision Support Agent (Discovery Feed + Living Mission + What-If)
- "**Tell story with data using AI/BI dashboards**" → Yesterday Review 페이지의 회고용 dashboard

→ AI는 결정에 들어가지 않지만, **매니저가 자기 결정을 회고할 때** dashboard로 storytelling.
→ 두 가치 명확히 분리 = 평가위원에게 "양쪽 다 했다" narrative

---

## AI/BI Dashboard — Yesterday Review 페이지 embed

### 구성

```
[Yesterday Review Page]
│
├── Self-critique 텍스트 (AI)
│   "어제 매니저 결정: Term +10pt 추가 lock
│    AI 권고는 +15pt였음. 매니저 더 보수적.
│    7일 후 outcome 측정 예정."
│
└── AI/BI Dashboard (embedded)
    ├── 차트 1: Risk Score 30일 시계열
    │   (호르무즈 봉쇄 시점 spike 시각화)
    │
    ├── 차트 2: 호르무즈 통과량 30일
    │   (평시 ~3,000척/월 → 위기 ~191척)
    │
    ├── 차트 3: WTI/Brent/Dubai 30일 가격 history
    │   (Brent vs Dubai spread 변화 강조)
    │
    └── 차트 4: 매니저 결정 outcome 회고
        (지난 30일 결정 + 7·30일 outcome 추적)
```

### 데이터 source
- Bronze Delta tables (oil_prices, ais_positions, exchange_rates)
- Lakebase decisions table (매니저 결정 + outcome)
- Gold layer risk_indicators (계산된 risk score 시계열)

### Why this works
- **Storytelling 평가축 (20%)** 직접 답변
- "대시보드 넘어"와 모순 X (dashboard는 회고용, decision은 다른 layer)
- AI/BI Dashboard 만들기 단순 (Databricks 기본 기능)
- Phase 7 (Yesterday Review) 시연 강화

---

## 5분 데모 — 8 Phase

| Phase | 시간 | 화면 | 핵심 |
|---|---|---|---|
| 1 | 00:00~00:30 | Opening | "AI는 예측하지 않는다. 의사결정 지원한다" |
| 2 | 00:30~01:00 | 24/7 Streaming Live | Brent spike + 우리 Cargo 호르무즈 진입 → 5초 후 매니저 알림 |
| 3 | 01:00~02:00 | **Living Mission Dashboard** ⭐ | "Term 50→70% mission D+18 + 시나리오 ROI + Cargo 위치 지도" |
| 4 | 02:00~02:30 | Discovery Feed swipe | 매니저 폰 3-5건 |
| 5 | 02:30~03:30 | **4사 Frame Contract RFQ Chaining** ⭐ | Agent Bricks 자율 — 4사 동시 → 비교 표 |
| 6 | 03:30~04:00 | **Genie What-If 시뮬** ⭐ | NL "Brent $140·Dubai $135 가면?" → 5초 ROI |
| 7 | 04:00~04:30 | Yesterday Review + **AI/BI Dashboard** | 어제 결정 outcome + Self-critique + 30일 시계열 dashboard |
| 8 | 04:30~05:00 | Closing | "사람 16분 / AI 24/7 / mission 4주" |

### Wow 모먼트 3개

**🎬 Wow 1 (Phase 3) — Living Mission Dashboard** (Lakebase 빛남)
- 4주 timeline 시각화 + 진짜 state 영속
- Brent $100/$120/$140 + Dubai 시나리오 ROI 실시간
- GS Caltex 선단 cargo 위치 지도 (진짜 AIS 데이터)

**🎬 Wow 2 (Phase 5) — 4사 RFQ Chaining** (Agent Bricks 빛남)
- Aramco·ADNOC·BP·TotalEnergies 동시 RFQ
- 5초 후 비교 표 + 사우디 재판매 조항 자동 검토

**🎬 Wow 3 (Phase 6) — Genie What-If** (Genie 빛남)
- 한국어 NL → Lakebase + Gold tables 종합 reasoning
- 5초 안에 ROI 차트

---

## 메시지 키워드 fit

| 해커톤 키워드 | 어디 |
|---|---|
| 비즈니스 문제 | 한국 정유사 9사 + 수출입 30만 + 5,000만 국민 에너지 안보 |
| 일상적으로 사용 | 매일 16분 자발적 |
| 대시보드를 넘어 | Decision Support 3 layer (Feed + Mission + What-If) |
| **AI/BI Dashboard로 storytelling** | Yesterday Review 페이지 embed (Risk Score·통과량·가격·결정 outcome 시계열) |
| 데이터·AI·분석·자동화 | 5종 + 시뮬 + 4사 RFQ + 4주 mission |
| 인사이트 | risk score + 시나리오 ROI |
| 업무 자동화 | RFQ 자동 + Living Mission 자율 |
| 새로운 사용자 경험 | Decision Support Agent |
| 4-tool 활용 | Wow 3개가 Apps·Genie·Lakebase·Agent Bricks 1:1 매칭 + AI/BI Dashboard |

---

## 평가 5축 (각 20%) — 공식 기준 fit

- **Business Applicability**: 정유사 9사 + 수출입 30만 + **5,000만 국민 에너지 안보** (도메인 검증 + social impact)
- **Creativity & Innovation**: "Decision Support Agent" 카테고리 + Frame Contract 자동 RFQ
- **User Experience & Insights**: 매일 16분 swipe + 4주 mission + Living Mission Dashboard
- **Technical Capability**: 4-tool 깊이 활용 + AI/BI Dashboard + 진짜 cargo 추적 + 5종 데이터
- **Data Storytelling & Narrative**: 호르무즈 진행 중 위기 + GS Caltex stranded 보도 인용 + **AI/BI Dashboard 30일 시계열 회고** + 가상회사 narrative

---

## 진짜 차별점 — Decision Support 카테고리

### 다른 AI 데모와의 차이

| 카테고리 | 예시 | 약점 |
|---|---|---|
| 예측 모델 (Predictive AI) | 가격 예측 | 정확도 검증 hard, hallucination |
| Dashboard AI | Tableau Pulse | 결국 dashboard |
| RAG Chat | Glean, Notion AI | 단발 질의응답 |
| **Decision Support Agent** ⭐ | 우리 | **다각도 정보 우위 + 자율 mission** |

### Why Decision Support?
- 사람: 결정 권한 + 책임
- AI: 정보 우위 + 자율 실행 (사람 결정 후)
- → 책임 명확, hallucination risk 최소화

→ Anthropic·OpenAI·McKinsey 모두 강조: "Agentic AI의 진짜 가치는 예측이 아니라 의사결정 지원"

---

## Risk

### 기술
- ✅ aisstream × Databricks WebSocket 검증 (2026-05-03)
- ✅ OilPriceAPI Dubai 실시간 검증 (2026-05-06)
- ✅ Agent Bricks Custom Agents GA (Beta 아님)
- ✅ Lakebase Autoscaling GA (2026-03)
- ⚠️ Next.js + FastAPI hybrid Databricks Apps 안정성 (공식 가이드 있음, 첫 시도)

### 도메인
- ⚠️ 김지훈 가상 (LG화학 SCM 인터뷰 진행 중)
- ✅ Term/Spot 비중 baseline = 대한석유협회 공식 + K-Petroleum 5:5
- ✅ Dubai 75% 도입 = 아빠 (前 LG화학 NCC 공장장) 인풋
- ✅ GS Caltex cargo = 진짜 호르무즈 stranded 보도 인용

### 평가
- ⚠️ "정유사 niche?" → 한국 수출입 30만 broaden
- ✅ "예측 정확도?" → "Decision Support" reframe
- ✅ "AI 가짜 의견?" → Persona Arena 제거 ("매니저는 진짜 회사 사람과 결정")
- ✅ "회사 보안?" → GS Caltex cargo는 공개 AIS 데이터 + 회사명 익명 처리

---

## 한 문단 narrative (평가위원 brief용)

> 한국 정유사 원유조달팀 매니저 김지훈 (K-Petroleum, 가상)은 매일 아침 7시 30분 출근길에서 폰을 연다. 새벽 4시 30분부터 5종 공공 데이터 + 글로벌 뉴스를 24/7 모니터링한 AI Agent가 산출한 "지정학 risk score 78, Term/Spot 의사결정 정보 3-5건, 우리 Cargo 호르무즈 진입 D-1"이 도착해 있다. **AI는 미래를 예측하지 않는다.** 대신 매니저가 결정에 필요한 정량 모니터링·시나리오 시뮬·4사 자동 RFQ를 제공한다 (**Go beyond dashboards**). 5분 동안 swipe로 결정. 책상 도착 후 10분 동안 어제 결정 outcome 회고를 **AI/BI Dashboard** (Risk Score·호르무즈 통과량·가격·결정 outcome 30일 시계열)로 보고, Living Mission 4주 점검 + What-If 시뮬. 그동안 AI는 4사 (Aramco·ADNOC·BP·TotalEnergies) Frame Contract RFQ 동시 chaining + 4주 long-running 포트폴리오 재조정 mission 자율 운영 (Lakebase에 영속). 매니저는 매일 16분 사용, AI는 24시간 자율. **결정은 사람, 정보 우위는 AI.** 가상 K-Petroleum 페르소나 + 진짜 GS Caltex 선단 AIS 데이터로 시연 — 진짜 정유사 도입 시 자사 cargo MMSI로 1줄 변경. 한국 정유 9사 + 수출입 30만 기업 임원 + **5,000만 국민 에너지 안보**가 매일 자발적으로 들어오는 SaaS. **Databricks 4-tool + AI/BI Dashboard가 정확히 만들도록 설계한 Decision Support use case.**

---

## 다음 액션 (D-16 마감 5/22)

### 완료
- ✅ aisstream × Databricks 검증
- ✅ API key 발급 (aisstream, OilPriceAPI, ECOS, Databricks Express)
- ✅ 5종 ingestion 검증
- ✅ Brent vs Dubai spread 확인 (Dubai +$2.36 = 호르무즈 위기 진짜 증거)
- ✅ Cargo target 결정 (GS Caltex)

### 코드 (Claude Code 세션)
- Phase 1 (1-2일): 검증·설계 보강 + 4-tool 최신 문서 조사 + GS Caltex MMSI filter 검증
- Phase 2 (3-4일): Bronze Delta 5종 + Lakebase 4 tables + Lakeflow Job 2개
- Phase 3 (2-3일): Agent Bricks Custom Agent 4개
- Phase 4 (5일): Next.js + FastAPI hybrid + 3 page UI
- Phase 5 (3일): 통합 테스트 + 5분 데모 영상 + 제출

### 아빠 follow-up (남은 질문)
1. Term/Spot 비중 조정 빈도 (분기? 월? 주?)
2. 결정 권한 layer (매니저? 임원? CEO?)

---

## 부록 — 2018년 한국 원유수입 분포 (대한석유협회)

- 사우디 29% / 쿠웨이트 15% / 이란 12% / UAE 7% / 카타르 6% / 미국 6%
- 중동 73.5% / 아시아 11.0% / 미주 8.5% / 아프리카 3.7% / 유럽 3.3%

→ 봉쇄 시 중동 73.5% 모두 영향. 미국·러시아·아프리카 다변화 시급.
