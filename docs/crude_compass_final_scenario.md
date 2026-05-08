# Crude Compass — Pre-emptive Bidirectional Decision Support Agent

> Databricks APJ Hackathon 2026 · 한국어 트랙 · Track 1 (Social Impact, Open Data)
> 마감: 2026-05-22

---

## 한 줄 요약

**한국 정유사 매니저를 위한 Bidirectional 위기·기회 신호 감지 AI Agent.**

- 위기 신호 누적 → Pre-emptive Hedge Mission (Term ↑)
- 약세 신호 누적 → Pre-emptive Opportunity Mission (Spot ↑)
- 결정은 사람, 자율은 AI, 동기화는 Lakebase, 데이터는 100% open data

---

## 1. 핵심 가치 — 왜 지금 이게 필요한가

### 1.1 매니저의 진짜 일

원유 조달팀의 진짜 일은 "위기 헤지"가 아니라 **"매월 가장 싸게 사기"**.

| 시장 상황 | Pattern Score | 매니저 행동 | 잘못 대응 시 손실 |
|---|---|---|---|
| 위기 신호 누적 | 70+ | Term ↑ (가격 폭등 보험) | 미리 안 락하면 폭등가 매수 → 손실 |
| 평시 | 30-70 | 균형 유지 | — |
| 약세 신호 누적 | 30 이하 | Spot ↑ (싸게 매수 기회) | Term 묶여 비싸게 매수 → 기회손실 |

위기는 1년 1-2회 (큰 임팩트), 기회는 분기 1-2회 (꾸준한 임팩트). **양방향 모두가 매일의 가치**.

### 1.2 AI Agent의 진짜 가치 — 신호 누적 단계

> 위기 발발 후 알아챔 = 누구나 가능 (CNN 보면 됨)
> 발발 1-2개월 전 신호 누적 패턴 catch = AI Agent만 가능

#### Hedge 케이스 — 호르무즈 봉쇄 (실제 진행 중)

```
[2026-1월 — Pre-Crisis 신호 누적]
  Brent $80 / Dubai $80
  단일 event 평균 importance 65
  → 누적 Pattern Score 82 도달

  AI 권고: "Pre-emptive Term hedge mission"
  매니저 Confirm → Term lock $85
        ↓
[2026-2/28 — Operation Epic Fury 발발]
  Brent $80 → $126, Dubai $80 → $166
        ↓
[결과 — 가상 K-Petroleum 시뮬]
  Term lock한 회사: $85 유지
  락 안 한 회사: $126 시장가
  → +410억 절약*
```
*가상 정유사 K-Petroleum 시뮬 기준. 실제 정유사는 자사 cargo / 정제 capacity / hedging instrument 따라 보정 필요.

#### Opportunity 케이스 — 약세 신호

```
[가상 시나리오 — Pre-Opportunity 신호 누적]
  Brent $90, 휴전 협상 진행 중
  Pattern Score 35 → 28 → 22 (2주 누적)
  - 휴전 임박 (Reuters · AP confirm)
  - 미국 SPR 1억 배럴 방출 발표
  - 중국 PMI 49.2 (수축 영역)
  - VLCC 운임 -15%
  - 글로벌 정유 재고 ↑

  AI 권고: "Pre-emptive Spot opportunity mission"
  매니저 Confirm → Spot 50% → 70%, Term 만기 차례 미연장
        ↓
[4주 후 — 약세 실현]
  Brent $90 → $72
  Spot 평균 매수가 $74
  Term 락 풀지 않았으면 $88 (이전 가격)
  → +130억 절약*
```

### 1.3 Open Data Democratization — Track 1 핵심

Crude Compass는 의도적으로 **100% open data**만 사용한다.

정유 빅5는 이미 Bloomberg / Platts / Vortexa / Kpler 같은 유료 시스템에 연 수천만원 지출 가능. **그게 없는 곳도 같은 인텔리전스를 가질 수 있도록.**

수혜자:
- **중소 정유사** — 유료 시스템 도입 부담 없음
- **석화 trading desk** — 나프타 의존 산업 보호
- **정책 연구자** — 대외경제정책연구원 / 산업연구원
- **정부 분석관** — 산업부 / 외교부 에너지 안보

이것이 Track 1 (Social Impact, Open Data) 진짜 의도, 그리고 진짜 social value.

---

## 2. 위기 4가지 카테고리 — 일반화

호르무즈 봉쇄는 메인 데모 시나리오일 뿐. AI는 4 카테고리 모두 동일 architecture로 처리.

| 카테고리 | 위기 신호 (Hedge) | 약세 신호 (Opportunity) |
|---|---|---|
| **지정학** | 호르무즈 봉쇄 / 후티 홍해 공격 / 러우 전쟁 | 휴전 발표 / 제재 해제 / 외교 정상화 |
| **정책** | OPEC+ 감산 / 추가 제재 / 환경 규제 | OPEC+ 증산 / SPR 방출 / 핵합의 복귀 |
| **자연재해** | 허리케인 정유시설 타격 / 중동 지진 | 재해 복구 진척 / 공급 정상화 |
| **시장 shock** | 달러 약세 / war risk premium | Backwardation→Contango / 운임·재고 정상화 |

→ **이번 한 번 위기 전용 솔루션이 아니라, 항상 작동하는 조기 경보 시스템**.

---

## 3. Bidirectional Pattern Detection

### 3.1 Score 재설계 — 양방향

```
              위기 신호 (Hedge Mission, Term ↑)
                    ▲
                    │ 90+   Urgent Crisis
                    │ 70-90  Crisis Pattern
                    │ 50-70  Caution
       ─────────────┼───────────── (50 = 균형)
                    │ 30-50  Stable
                    │ 10-30  Opportunity Pattern
                    │ 10-    Urgent Opportunity
                    ▼
              약세 신호 (Opportunity Mission, Spot ↑)
```

### 3.2 양방향 누적 계산

```python
# 3-6개월 window
window_days = 90

bullish_score = SUM(
    importance × time_decay_weight × source_credibility
) WHERE direction = 'bullish' AND importance >= 60

bearish_score = SUM(
    importance × time_decay_weight × source_credibility
) WHERE direction = 'bearish' AND importance >= 60

# Cross-validation bonus
cross_val = COUNT(category × direction WITH ≥2 sources confirm) × 5

# 최종
net_signal = bullish_score - bearish_score
pattern_score = 50 + (net_signal / max_normalized) × 50 + cross_val
pattern_score = clamp(0, 100)
```

**Time decay**: 최근 100% → 3개월 전 10% (지수 가중)
**Cross-validation**: 같은 카테고리에서 2 source 이상 confirm 시 가중치 ↑
**Asymmetric threshold**: False positive (1분 review)는 cheap, false negative (수백억 손실)는 expensive → 약간 보수적 설정

### 3.3 Mission 자동 trigger

```
Pattern Score 70+ (위기) → HEDGE Mission 자동 제안
   "Term 50% → 70% (4주), Pre-emptive Hedge"

Pattern Score 30 이하 (기회) → OPPORTUNITY Mission 자동 제안
   "Spot 50% → 70% (4주), Pre-emptive Opportunity"

또는 단일 event importance 80+ → 즉시 trigger (정기 cron 안 기다림)
```

---

## 4. AI Agent Architecture — 4-Layer

### Layer 1: 정기 News Fetch (2시간 cron)

```
2시간마다:
  Tier A 속보: Reuters · AP · 연합뉴스 · FT · BBC
  Tier B 1차: EIA · IEA · OPEC · OFAC · Aramco IR · 외교부
       ↓
  Hard rule filter (cheap):
    - 오피니언/사설/광고 → skip
    - 200자 미만 → skip
    - 에너지 키워드 0개 → skip
    - OFAC/OPEC/Aramco 공식 → always keep
       ↓
  LLM importance scoring (Foundation Model API, Claude Haiku):
    {
      "importance": 0-100,
      "category": "geopolitical|policy|disaster|market|supply|demand",
      "direction": "bullish|bearish|neutral",  ← 양방향 핵심
      "horizon": "short|medium|long",
      "confidence": "low|med|high",
      "entities": ["IRGC", "OPEC", ...]
    }
       ↓
  importance 60+ → bronze.news_articles 적재
  importance 80+ → 즉시 Mission Plan Agent 호출
```

### Layer 2: Reactive Trigger (5분 cron)

```
trigger 감지 (rule-based):
  ✓ Brent/WTI/Dubai +/- 2% in 5min
  ✓ AIS 호르무즈 통과량 +/- 20% in 1hr
  ✓ JWC War zone 변경
  ✓ KRW/USD +/- 1% in 5min
  ✓ GDACS 중동 재해 발생
  ✓ 키워드 burst (특정 키워드 1시간 5+ source)
       ↓
  즉시 reactive 뉴스 검색 (정기 cron 안 기다림)
       ↓
  LLM 분석: "원인 + direction + 진행 mission 영향"
       ↓
  매니저 Slack URGENT alert
```

### Layer 3: Bidirectional Pattern Detection (매일 06:30)

```
3-6개월 window 양방향 분석:

input: bronze.news_articles (importance 60+, direction 보존)
       
analysis:
  - bullish_score 계산 (시간 가중 + cross-validation)
  - bearish_score 계산 (동일)
  - pattern_score = 50 + ((bullish - bearish) / max_normalized) * 50

output:
  - Pattern Score (0-100)
  - 70+ → HEDGE Mission trigger
  - 30 이하 → OPPORTUNITY Mission trigger
  - 30-70 → Stable (skip, log only)
```

### Layer 4: Mission Plan Agent — 양방향 Mission 생성

```
Trigger 조건:
  Pattern Score >= 70 (HEDGE) or Pattern Score <= 30 (OPPORTUNITY)
  OR 단일 event importance >= 80
       ↓
Mission 제안 생성:
  if pattern_score >= 70:
    mission_type = 'HEDGE'
    goal = "Term 50% → 70% (4주)"
    color = 빨강
  elif pattern_score <= 30:
    mission_type = 'OPPORTUNITY'
    goal = "Spot 50% → 70% (4주)"
    color = 초록
  
  필드:
    - goal: 구체적 (Term 50% → 70%, 4주)
    - reasoning: "왜 지금" (어떤 신호 catch)
    - simulation: ROI 시나리오별
    - urgency: optional / default / urgent
    - mission_type: HEDGE / OPPORTUNITY
       ↓
Lakebase INSERT (status='proposed')
       ↓
동시 발송 (5초 이내):
  - Slack DM (interactive buttons)
  - Apps WebSocket push
```

---

## 5. AI 능동 + 사람 결정

### AI 역할 (proactive, 24/7)
- 5종 데이터 + 뉴스 24/7 모니터링
- 단일 event importance + direction scoring
- 3-6개월 누적 Bidirectional Pattern Detection
- Reactive trigger 즉시 반응
- Pre-emptive Mission 양방향 제안 (HEDGE / OPPORTUNITY)
- Plan vs Reality 매일 비교
- 변화 시 Pivot 권고 (양방향 반전 가능)
- 매주 Self-Critique + Calibration

### 사람 역할 (reactive)
- AI 제안 review
- Confirm / Reject / Modify
- Pivot 4 옵션 결정 (Abort / Pause / Pivot / Continue)
- (보조) 자유 NL 질문

---

## 6. Living Mission — Lifecycle

### 6.1 Mission 상태 (7가지)

```
draft → active → 
  ├─ on_track       (계획대로 진행)
  ├─ at_risk        (시장 변화 감지)
  ├─ paused         (시장 관망 결정)
  ├─ pivoted        (목표 수정 — 양방향 반전 포함)
  ├─ aborted        (완전 폐기)
  └─ completed      (4주 완료)
```

### 6.2 양방향 Pivot — 진짜 Living Mission

| Pivot 방향 | 시장 변화 | AI 권고 |
|---|---|---|
| Hedge → Opportunity | 휴전 발표 / OPEC 증산 / SPR 방출 | "현재 Hedge 손해 위험. Pivot to OPPORTUNITY" |
| Opportunity → Hedge | 갑작스 협상 결렬 / 새 위기 | "현재 Opportunity 위험. Pivot to HEDGE" |
| Pause | 시장 방향 불확실 | "1주 관망 후 재평가" |
| Abort | 시장 완전 reverse | "더 진행 시 손해 확정. 폐기" |
| Continue | 매니저 자기 판단 | AI: outcome 추적 강화 |

매니저 결정 시 **5초 안에 새 plan 자동 생성 + Slack/Apps 동기화**.

---

## 7. Slack ↔ Apps 양방향 동기화

### 7.1 Single Source of Truth — Lakebase

```
            [Lakebase missions table]
            mission_id, mission_type, status, ...
                    ↑ ↓
            ┌───────────────────┐
            │  FastAPI Backend  │
            └────┬─────────┬────┘
                 │         │
        ┌────────┘         └────────┐
        ▼                           ▼
    [Slack Bot]              [Apps UI]
    Bolt SDK                 Vite + React
        ↑                           ↑
        └─────── 매니저 ────────────┘
```

### 7.2 4가지 동기화 흐름

#### A. AI가 Pre-emptive Mission 제안
```
04:30  Tier 1 Daily 실행
06:30  Pattern Detection → score 82 (HEDGE) 또는 22 (OPPORTUNITY)
07:00  Mission Plan Agent → Mission 자동 생성
       Lakebase INSERT (status='proposed', mission_type='HEDGE'|'OPPORTUNITY')
       ↓
       동시 발송 (5초):
       - Slack DM (interactive buttons)
       - Apps WebSocket push
```

#### B. 매니저 Slack에서 Confirm
```
07:32  Slack [Confirm] 클릭
       ↓
       Slack Bot → FastAPI POST /missions/{id}/confirm
       Lakebase UPDATE status='active', confirmed_via='slack'
       ↓
       Broadcast (5초):
       - Slack 메시지 update ("✅ Confirmed via Slack")
       - Apps WebSocket → status pill 'proposed' → 'active'
```

#### C. 매니저 Apps에서 Confirm
```
09:15  Apps Mission Dashboard 'proposed' 카드 봄
       Confirm 클릭
       ↓
       Apps → FastAPI POST /confirm
       Lakebase UPDATE status='active', confirmed_via='apps'
       ↓
       Broadcast (5초):
       - Apps 'proposed' → 'active' status pill
       - Slack 카드 update ("✅ Confirmed via Apps at 09:15")
       - Slack 채널 추가: "Mission 활성화. Term lock 시작"
```

#### D. 동시 충돌 방지
- FastAPI optimistic concurrency (version 컬럼)
- 첫 요청만 처리, 두 번째는 "이미 confirmed" 응답
- 양쪽 화면 일관 동기화

---

## 8. 위기·평시·기회 — 3-mode 작동

### Crisis Mode (Pattern Score 70+)

```
시장 폭등 risk → Term 비중 ↑
4주 헤지 mission 자율 운영
Cargo 위치 실시간 추적
Mission Pivot 능동 권고
```

**예시**:
> 🚨 AI: "Pattern Detection: 3 weeks 6건 escalation 누적.
> Pre-emptive Term +15pt mission 제안. 시뮬 +320억. Confirm?"

### Stable Mode (Pattern Score 30-70)

```
시장 안정
AI: 매일 모니터링 + Pattern Detection (변화 없음 = skip)
매니저: 균형 유지

이때도 매일 작동:
- 시장 동향 모니터링
- Aramco Formula 발표 시뮬
- Spot pickup 권고 가능
```

### Opportunity Mode (Pattern Score 30 이하)

```
시장 약세 신호 → Spot 비중 ↑
4주 opportunity mission 자율 운영
약세 지속 여부 모니터링
시장 reverse 시 Pivot 권고
```

**예시**:
> 🟢 AI: "Bidirectional Pattern Detection: 약세 신호 5건 누적.
> Pre-emptive Spot +20pt mission 제안. 시뮬 +130억. Confirm?"

→ **위기는 1년 1-2회. 기회는 분기 1-2회. Opportunity가 더 자주 가치 만든다.**

---

## 9. 페르소나 — 2층 구조

### 1층: 김지훈 (가상 매니저, K-Petroleum)
- 30대 후반 원유조달팀 시니어 매니저
- 가상 정유사 K-Petroleum (정제 80만 b/d)
- baseline Term 50% : Spot 50%
- Slack always-on, Apps deep work
- Crude Compass 4주째 보조 중

### 2층: 평가위원 (실제 5분 데모)
- 매니저 입장 직접 체험
- AI Pre-emptive 제안 receive (Slack)
- Slack 또는 Apps에서 Confirm
- Spike trigger → AI Reactive 반응
- Mission Pivot 결정 (양방향)

### Cargo 데이터 — 익명화 실제 cargo
- 한국 정유 4사 중 한 곳의 실제 VLCC AIS 데이터 (공개 source)
- 데모에서 "VLCC #003" 같은 가명
- 실제 정유사 도입 시 자사 cargo MMSI로 변경

---

## 10. 데이터 Source — 100% Open Data

### 정량 source 5종 (검증 완료)

| Source | 데이터 | 빈도 | 비용 |
|---|---|---|---|
| **OilPriceAPI** | WTI + Brent + Dubai | 5분 (REST) | $19/mo (1달만) |
| **AIS aisstream** | 호르무즈 통과량 + 익명화 cargo | WebSocket continuous | 무료 |
| **GDACS** | UN/EU 글로벌 재해 events | REST | 무료 |
| **ECOS 한국은행** | KRW/USD 환율 | REST 일 1회 | 무료 |
| **JWC PDF** | War zone (Lloyd's Market Association) | Manual upload | 무료 |

### News Pipeline (RSS, 양방향 신호 핵심)

**Tier A — 속보**:
Reuters · AP · 연합뉴스 · FT · BBC

**Tier B — 1차 정보**:
EIA STEO · IEA OMR · OPEC Monthly · OFAC SDN · Aramco IR · 외교부 RSS

→ News RSS가 **양방향 Pattern Detection의 핵심**. 5종 정량 데이터는 보조.

### 총 외부 비용
- OilPriceAPI: $19 (5/15 결제 → 5/22 데모 → 5/23 cancel)
- 그 외 모두 무료
- **총 $19**

---

## 11. Databricks Architecture — 6 Lakeflow Jobs

### Job 구조

```
┌─────────────────────────────────────────────────────────┐
│  Job 1: news_pipeline_2hr      cron 0 */2 * * *         │
│  Job 2: price_pipeline_5min    cron */5 * * * *         │
│  Job 3: ais_websocket          Continuous               │
│  Job 4: ecos_daily             cron 0 18 * * 1-5        │
│  Job 5: daily_curation         cron 30 6 * * *          │
│  Job 6: weekly_self_critique   cron 0 18 * * 0          │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  Unity Catalog (분석)                                   │
│    crude_compass.bronze.{news_articles, oil_prices,     │
│                          ais_positions, fx_rates}       │
│    crude_compass.silver.{pattern_scores_daily,          │
│                          hormuz_traffic_hourly}         │
│    crude_compass.gold.{mission_outcomes,                │
│                        backtest_results}                │
├─────────────────────────────────────────────────────────┤
│  Lakebase Postgres (의사결정 OLTP)                      │
│    missions, decisions, pivot_history                   │
│    → Slack ↔ Apps 동기화 Single Source of Truth        │
└─────────────────────────────────────────────────────────┘
```

### Job 1 — news_pipeline_2hr

- 2시간마다 RSS 11 source fetch
- Hard rule filter (90% 이상 cheap 절감)
- LLM importance + direction scoring (Foundation Model API, Claude Haiku)
- importance 60+ Bronze 적재, 80+ 즉시 Mission Plan Agent trigger
- 일 비용 ~$0.7

### Job 2 — price_pipeline_5min

- OilPriceAPI WTI / Brent / Dubai 3 ticker fetch
- Bronze append + 5분 윈도우 spike 감지
- +/- 2% spike → reactive trigger
- Serverless Job cluster (start-up 5-10초)
- 운영 패턴: 60분 cron (개발) → 15분 (테스트) → 5분 (데모)

### Job 3 — ais_websocket

- aisstream WebSocket continuous connection
- 호르무즈 bounding box 내 vessel position
- 100건 또는 60초 batch flush → Bronze
- All-purpose On-demand cluster (Spot 불가)
- 가장 비싼 컴포넌트 (~$7/일) → 데모 직전 1주만 가동

### Job 4 — ecos_daily

- 평일 18:00 KST (장 마감 후)
- KRW/USD 환율 fetch (한국은행 ECOS)
- 비용 거의 0

### Job 5 — daily_curation ⭐⭐⭐

- 매일 06:30 KST
- 5종 데이터 + 뉴스 종합 fetch
- **Bidirectional Pattern Detection 3-6개월 window 분석** (핵심)
- Pattern Score 70+ HEDGE 또는 30- OPPORTUNITY → Mission Plan Agent 호출
- Plan vs Reality 비교

### Job 6 — weekly_self_critique

- 매주 일요일 18:00 KST
- 지난 주 매니저 결정 vs AI 권고 outcome 비교
- HEDGE 정확도 + OPPORTUNITY 정확도 양방향 backtest
- LLM importance score calibration
- MLflow tracking

---

## 12. Agent Bricks — 4 Custom Agents

### Agent 1: Monitoring Agent
- **언제**: 매일 06:30 + 2시간 cron + 5분 realtime
- **역할**: 5종 데이터 + 뉴스 → risk score + importance + direction scoring
- **Output**: bronze 테이블 적재 + MLflow tracking

### Agent 2: Simulation Agent
- **언제**: Mission 제안 시 + 매니저 NL query 시
- **역할**: 양방향 ROI 계산
  - HEDGE: "Brent $130 시 +XXX억"
  - OPPORTUNITY: "Brent $72 시 +XXX억"
- **Genie와 협업**: 자연어 → SQL → 시뮬

### Agent 3: Mission Plan Agent ⭐⭐⭐ (가장 핵심)
- **언제**: Pattern Detection trigger / 매일 / 시장 변화 시
- **역할**:
  - **Pre-emptive Mission 양방향 제안 생성** (HEDGE / OPPORTUNITY)
  - mission_type 분기
  - 매일 plan vs reality 비교
  - 변화 시 Pivot 권고 (양방향 반전 가능)
  - 매니저 결정 시 새 plan 자동 생성
  - Slack + Apps 동시 발송

### Agent 4: Self-Critique Agent
- **언제**: 매주 일요일
- **역할**:
  - 지난 주 매니저 결정 vs AI 권고 outcome 비교
  - **양방향 Pattern Detection 정확도 backtest**
    - HEDGE 정확도
    - OPPORTUNITY 정확도
    - 양방향 평균 lead time
  - LLM importance score calibration
  - MLflow model 보정

---

## 13. Databricks Stack 활용

| Tool | 역할 | Wow Moment |
|---|---|---|
| **Apps** | Vite + React + FastAPI hybrid<br>Mission Dashboard 단일 페이지<br>Slack Bot 백엔드 | UI 핵심 |
| **Genie** | Apps embed (Agent Mode GA)<br>Slack Bot 통합 자연어 시뮬 | Wow 5 |
| **Lakebase** | Postgres OLTP, 4 tables<br>**Slack ↔ Apps Single Source of Truth** | ⭐ Wow 1, 3 |
| **Agent Bricks** | 4 Custom Agents (GA)<br>Monitoring · Simulation · **Mission Plan** · Self-Critique<br>Bidirectional Pattern Detection | ⭐⭐⭐ Wow 2, 5, 6 |
| **AI/BI Dashboard** | Apps embed<br>30일 storytelling + 양방향 backtest 시각화 | ⭐ Wow 7 |

---

## 14. 5분 데모 — 평가위원 직접 체험

### 평가위원 인터랙션 요약
- 평가위원 클릭 4회 (Phase 3, 5, 6 각 1-2회)
- AI 자율 작업 5회
- 양방향 동기화 시연 2회

### Phase 1 (00:00 — 00:30): Opening + Open Data Democratization 선언

**Narrator**:
> "AI는 위기 발발 후가 아니라, 신호 누적 단계에서 가치를 만든다.
> 그리고 그 가치는 양방향 — 위기 헤지 + 기회 포착 모두.
>
> Crude Compass는 의도적으로 **100% open data만** 사용했다.
> 정유 빅5는 이미 Bloomberg·Platts·Vortexa·Kpler에 연 수천만원 쓰지만,
> 그게 없는 곳 — 중소 정유사, 정책 연구자, 정부 분석관 — 도
> 같은 인텔리전스를 가질 수 있도록.
> 이게 Track 1 진짜 의도, 진짜 social value."

### Phase 2 (00:30 — 01:30): Pre-emptive HEDGE Mission 제안 ⭐⭐⭐

**화면**: 평가위원 폰 Slack

평가위원 Slack 열면 — AI가 이미 Pre-emptive HEDGE 제안 도착:

> 🤖 Crude Compass Bot · 07:30
> 🚨 **Pre-emptive HEDGE Mission 제안**
>
> **Bidirectional Pattern Detection**: 지난 3주 escalation 신호 6건 누적
> - 1/15: 미 펜타곤 중동 군 가족 출국
> - 1/22: Geneva 협상 결렬
> - 1/30: IRGC 강경 발언
> - 2/05: 미 국무부 비필수 인력 출국
> - 2/10: UK Maritime "increased tensions"
> - 2/15: Brent vs Dubai spread 변화 + VLCC 운임 ↑
>
> **누적 Pattern Score**: 82 (Cross-validation 4 source confirm)
>
> **권고**: Term 50% → 70% (4주) — Pre-emptive Hedge
> **시뮬**: 봉쇄 발발 시 +410억 / 평화 유지 시 -50억
> **현재 cargo**: 익명화 VLCC #003 호르무즈 진입 D-1
>
> [Confirm] [Reject] [Modify] [Open in Apps]

**Narrator**:
> "AI는 위기 발발 1-2주 전부터 신호 누적 모니터링.
> 단일 event 평균 65에서 누적 Pattern Score 82 도달.
> 매니저는 Slack에서 Confirm 한 번만."

### Phase 3 (01:30 — 02:30): ⭐⭐⭐ Apps에서 Confirm → Slack 동기화

**화면 분할**: 왼쪽 Slack / 오른쪽 Apps

평가위원 "Open in Apps" 클릭:
- Apps Mission Dashboard 열림
- 같은 Mission 'proposed' 카드 + Pre-Crisis timeline 시각화

평가위원 Apps에서 Confirm 클릭:

5초 안에 양쪽 변화:
- Apps: 'proposed' → 'active' status pill (빨강)
- Slack: 카드 update "✅ Confirmed via Apps at 09:15"
- Slack 채널 추가 메시지: "Mission 활성화. Term lock 시작"

**Narrator**:
> "Lakebase가 Single Source of Truth.
> Slack에서든 Apps에서든 어디서 결정해도 5초 동기화."

### Phase 4 (02:30 — 03:00): Reactive Trigger — Spike 즉시 반응

평가위원 데모용 "Inject Brent +5% spike" 클릭:
- Bronze.oil_prices에 mock spike data 적재
- Layer 2 Reactive Trigger 즉시 감지
- 5초 안에 reactive 뉴스 검색
- LLM 분석: "OPEC 갑작스 발표 가능성"
- Slack URGENT alert: "Brent +5% spike. 진행 중 HEDGE Mission Term lock 가속 권고"

### Phase 5 (03:00 — 03:45): ⭐⭐⭐ Pre-emptive OPPORTUNITY Mission

**평가위원 데모용 "Inject Bearish signals" 클릭**:
- Mock 약세 신호 5건 inject (휴전 임박, SPR 방출, 중국 PMI 둔화, VLCC 운임 ↓, 재고 ↑)
- Bidirectional Pattern Detection: Pattern Score → **22**
- Mission Plan Agent: OPPORTUNITY Mission 자동 제안

**평가위원 Slack에 도착**:
> 🤖 Crude Compass Bot · 14:32
> 🟢 **Pre-emptive OPPORTUNITY Mission 제안**
>
> **Bidirectional Pattern Detection**: 약세 신호 5건 누적
> - 휴전 임박 (외교, Reuters confirm)
> - 미국 SPR 1억 배럴 방출 (정책)
> - 중국 PMI 49.2 — 수축 영역 (수요)
> - VLCC 운임 -15% (시장)
> - 글로벌 정유 재고 ↑ (공급)
>
> **누적 Pattern Score**: 22 (낮을수록 약세 강함)
> **Cross-validation**: 5 source confirm
>
> **권고**: Spot 50% → 70% (4주) — Pre-emptive Opportunity
> **시뮬**: Brent $72 하락 시 +130억 / 다시 상승 시 -30억
>
> [Confirm] [Reject] [Modify] [Open in Apps]

**Narrator**:
> "위기만이 아니다. 약세 신호도 동일 architecture로 catch.
> AI는 매일 양방향 최적화.
> 위기는 1년 1-2회, 기회는 분기 1-2회.
> **Opportunity가 더 자주 가치 만든다**."

### Phase 6 (03:45 — 04:30): ⭐⭐⭐ Bidirectional Pivot — 양방향 반전

진행 중 OPPORTUNITY Mission (Spot 70%) 가정.

**평가위원 데모용 "Inject Sudden Crisis" 클릭**:
- 휴전 결렬 + IRGC 위협 재개
- Pattern Score: 22 → 78 (반대 방향 급변)

**Slack URGENT push**:
> 🚨 **Mission Pivot 권고 — Opportunity → Hedge 반전**
>
> 휴전 결렬 + IRGC 위협 재개 (Reuters · AP confirm)
> 현재 OPPORTUNITY Mission 진행 시 손해 ↑
>
> AI 권고 4 옵션 (각각 시뮬 ROI):
> [Abort] [Pause] [**Pivot to HEDGE ⭐**] [Continue]

**평가위원 "Pivot to HEDGE" 클릭**:

5초 안에 양쪽 동기화:
- Lakebase: mission_type 'OPPORTUNITY' → 'HEDGE'
- Mission Plan Agent: 새 plan 자동 (Spot 70% → Term 70%)
- Apps timeline에 양방향 Pivot marker (🟢 → 🚨)
- Slack 메시지: "Pivoted to HEDGE. Term lock 가속 시작"

**Narrator**:
> "양방향 Mission이 살아있다.
> 어느 방향이든 시장 변화 시 AI 즉시 권고.
> 매니저 결정 시 5초 안에 새 plan."

### Phase 7 (04:30 — 04:50): ⭐ AI/BI Dashboard + 양방향 backtest

**Apps 스크롤**:
- AI/BI Dashboard 4 차트:
  - Pattern Score 30일 (양방향 spike 시각)
  - 호르무즈 통과량
  - WTI/Brent/Dubai
  - 매니저 결정 outcome
- **Bidirectional Pattern Detection backtest**:
  - HEDGE 정확도: 78%
  - OPPORTUNITY 정확도: 71%
  - 양방향 평균 lead time: 발발 12-14일 전
- Self-Critique: "AI 권고 vs 매니저 결정 outcome 비교 + MLflow 보정"

### Phase 8 (04:50 — 05:00): Closing

**Narrator**:
> "위기 + 기회 양방향 신호 감지 = AI Agent 진짜 가치.
> Slack ↔ Apps 동기화 = 매니저 어디서든 결정.
> Mission이 살아있다 = 진짜 Agentic.
> 100% open data로 인텔리전스 democratize.
>
> Crude Compass — Pre-emptive Bidirectional Decision Support."

---

## 15. Wow Moments — 7개

### 🎬 Wow 1 (Phase 2) — Pre-emptive HEDGE Mission
- Slack 알림 이미 도착
- Pattern Detection 시각화 (3주 6건 누적)

### 🎬 Wow 2 (Phase 2) — Bidirectional Pattern Detection
- 양방향 누적 분석 (bullish + bearish)
- Cross-validation 4 source

### 🎬 Wow 3 (Phase 3) — Slack ↔ Apps 양방향 동기화
- 화면 분할 시연
- 5초 안에 양쪽 동기화

### 🎬 Wow 4 (Phase 4) — Reactive Trigger + News Search
- 평가위원 trigger → 5초 안에 뉴스 검색 + alert

### 🎬 Wow 5 (Phase 5) — Pre-emptive OPPORTUNITY Mission ⭐⭐⭐
- 약세 신호 5건 누적 catch
- Pattern Score 22 → Spot ↑ 권고
- "위기만이 아니다" narrative

### 🎬 Wow 6 (Phase 6) — Bidirectional Living Mission Pivot ⭐⭐⭐
- AI 양방향 Pivot 권고 (Opportunity → Hedge 반전)
- 5초 안에 새 plan + 동기화

### 🎬 Wow 7 (Phase 7) — AI/BI + 양방향 backtest
- 30일 dashboard
- HEDGE + OPPORTUNITY 정확도 별도 추적
- Self-Critique 자기 학습

---

## 16. AI 판단 기준 — Calibration

### Importance Score Anchors (0-100)

```
100: 이란 핵 협상 결렬, IRGC 군사 동원
80:  미 중동 군 가족 출국 명령
60:  OPEC monthly report 발표
40:  사우디 정유 capacity 일부 수정
20:  일반 시장 전망 보고서
```

### Score → 행동
```
0-30:  skip (DB 적재 X)
30-60: log only (적재만)
60-80: enrich (관련 가격 데이터 join)
80+:   alert + Mission Plan Agent 즉시 호출
```

### Pattern Detection (Bidirectional)
```
window: 3-6개월
weighting: time-decay (최근 100% → 3mo 10%)
cross-validation: 2 source 이상 confirm 우선

Pattern Score 70+: HEDGE Mission 제안
Pattern Score 30 이하: OPPORTUNITY Mission 제안
Pattern Score 90+: Urgent (즉시 Slack push)
Pattern Score 10 이하: Urgent (즉시 Slack push)
```

### False Positive vs Negative — Asymmetric
- False Positive: 매니저 1분 review (cheap)
- False Negative: 수백억 손실 (expensive)
- → 약간 보수적 (낮은 threshold) + 매니저 쉽게 reject UX

---

## 17. 알림 정책

### URGENT (즉시 Slack push, 24/7)
- 가격 spike +/- 5%
- 호르무즈 통과량 -30%
- 진행 중 mission Pivot 필요 (양방향)
- 위기 발발 (2 source confirm)
- Pattern Score 양방향 90+/10-

### DAILY (07:00 KST morning brief)
- Discovery Feed 3-5건
- 진행 중 mission 상태 (HEDGE / OPPORTUNITY)
- 신규 Mission 제안

### WEEKLY (일요일 18:00 KST digest)
- 지난 주 결정 outcome
- Self-Critique 결과 (양방향)
- Bidirectional Pattern Detection backtest
- 다음 주 예상 events

### Quiet Hours
- 평일 22:00-06:00, 주말 18:00-09:00
- URGENT만 통과

### Throttling
- 같은 신호 30분 내 중복 dedupe
- 일 max 5회 alert
- 매니저 직접 빈도 조정 가능

---

## 18. 평가 5축 (각 20%)

### Business Applicability
- 정유 9사 + 5,000만 국민 에너지 안보
- 매일 양방향 최적화 (위기 1-2회/년 + 기회 1-2회/분기)
- Pre-emptive 가치 +410억 (Hedge), +130억 (Opportunity) 시뮬
- **매니저의 진짜 워크플로우 반영** (위기 헤지 X, 매월 최적화 O)

### Creativity & Innovation
- **Bidirectional Pattern Detection** (일반 risk SaaS와 차별화)
- Slack ↔ Apps 양방향 동기화 (Lakebase Single Source of Truth)
- Living Mission Lifecycle (양방향 Pivot 가능)
- Open Data Democratization (의도적 design philosophy)

### User Experience & Insights
- Conversational AI (Slack 능동 reach)
- Pre-emptive 제안 (사람이 dashboard 열기 기다리지 않음)
- 양방향 동기화 (어디서든 결정 가능)
- 평시·위기·기회 3-mode 매일 작동

### Technical Capability
- 4-tool 깊이 활용 (Apps + Genie + Lakebase + Agent Bricks)
- AI/BI Dashboard embed
- 5종 데이터 + News Pipeline + Bidirectional Pattern Detection
- Single Source of Truth Lakebase 패턴

### Data Storytelling & Narrative
- 위기 발발 전 신호 감지 (Pre-emptive)
- 양방향 Pivot (Living Mission)
- 양방향 Pattern Detection backtest 30일
- Open Data Democratization (Track 1 정합)

---

## 19. 진짜 차별점

| | 일반 PM 도구 | 일반 Dashboard | RAG Chat | **Crude Compass** |
|---|---|---|---|---|
| 진입점 | 앱 새로 열기 | 로그인 | 채팅 | **Slack 알림 (능동)** |
| 위기 감지 | 없음 | 후행 | 후행 | **Pre-Crisis Pattern Detection** |
| **방향성** | — | — | — | **양방향 (Hedge + Opportunity)** ⭐ |
| AI 역할 | 없음 | 없음 | 답변 | **Mission 자율 제안** |
| 자율 작업 | 없음 | 없음 | 없음 | **24/7 자율 reasoning** |
| Plan vs Reality | 사람이 비교 | 없음 | 없음 | **AI 24/7 자율** |
| Pivot | 없음 | 없음 | 없음 | **AI 능동 양방향 Pivot** |
| 동기화 | N/A | N/A | N/A | **Slack ↔ Apps 양방향** |
| 자기 비판 | 없음 | 없음 | 없음 | **매주 양방향 backtest** |
| 사용 빈도 | 프로젝트별 | 필요시 | 질문 시 | **매일 (위기·평시·기회)** |
| 데이터 source | 자체 | 자체 | 자체 | **100% Open data** ⭐ |

---

## 20. Risk 분석

### 기술 Risk
- ✅ aisstream × Databricks 검증 완료 (2026-05-03)
- ✅ OilPriceAPI Dubai 실시간 검증 완료 (2026-05-06)
- ✅ Agent Bricks Custom Agents GA
- ✅ Lakebase Autoscaling GA
- ✅ Slack Bolt SDK 표준 라이브러리
- ⚠️ Bidirectional Pattern Detection 정확도 (mock backtest 시뮬 필요)
- ⚠️ Vite + React + FastAPI hybrid + Slack Bot 통합 안정성

### 도메인 Risk
- ⚠️ 김지훈 가상 매니저 (정유사 도메인 검증 진행 중)
- ✅ Term/Spot baseline = 대한석유협회 공식
- ✅ Cargo = 익명화 실제 AIS 데이터
- ✅ Pre-Crisis timeline = 검색 검증된 사실 (실제 진행 중인 위기)
- ✅ 한국 중동 의존도 70.7% (산업부 2025 공식)

### 평가위원 잠재 의문 → 선제 답변

| 의문 | 답변 |
|---|---|
| "예측 정확도?" | "Decision Support" reframe + Self-Critique 양방향 backtest |
| "회사 보안?" | AIS 공개 데이터 + 익명화 처리 |
| "Slack ↔ Apps 동기화?" | Lakebase Single Source of Truth |
| "Pattern Detection 진짜?" | Mock backtest + production 가능 narrative |
| "양방향 동시 운영?" | mission_type 컬럼 분기 + 양방향 Pivot lifecycle |
| **"Bloomberg/Platts 풀 옵션 못 쓰는 한계?"** | **"의도적 Open data 선택, democratization. 그게 Track 1 진짜 의도"** |

---

## 21. 한 문단 narrative (평가위원 brief용)

> 한국 정유사 K-Petroleum 매니저 김지훈은 매일 16분 Crude Compass와 일한다. AI Agent는 4주째 24/7 자율 모니터링 — 5종 공공 데이터 + 글로벌 뉴스 + 익명화 실제 cargo AIS 추적. 핵심은 **양방향**: 위기 발발 전 Pattern Detection으로 Pre-emptive HEDGE Mission 제안 (Term ↑), **약세 신호 누적 시 Pre-emptive OPPORTUNITY Mission 제안** (Spot ↑). LLM이 모든 뉴스에 `direction: bullish|bearish|neutral` 부여 → 3-6개월 누적 양방향 가중 → Pattern Score 70+ HEDGE / 30- OPPORTUNITY 자동 trigger. 출근길 김지훈이 Slack을 열면 AI가 이미 결정 — "Pre-emptive HEDGE Mission, Pattern Score 82" 또는 "Pre-emptive OPPORTUNITY Mission, Pattern Score 22". Slack [Confirm] 또는 [Open in Apps] → 5초 안에 양쪽 동기화. 진행 중 시장 변화 시 (예: 진행 중 OPPORTUNITY 중 갑작스 협상 결렬) AI 즉시 양방향 Pivot 권고 — "Opportunity → HEDGE 반전". 매주 Self-Critique Agent가 HEDGE 정확도 + OPPORTUNITY 정확도 양방향 backtest + MLflow 보정. **위기는 1년 1-2회, 기회는 분기 1-2회 — Opportunity Mission이 매니저에게 더 자주 가치 만든다.** 100% open data만 사용 — 정유 빅5의 Bloomberg·Platts 풀 옵션 (연 수천만원) 없이도 동일 인텔리전스. 중소 정유사·정책 연구자·정부 분석관도 same level. **결정은 사람, 자율은 AI, 동기화는 Lakebase, 방향은 양방향.**

---

## 22. 다음 액션 (D-14, 5/8 → 5/22 마감)

### 완료된 사항
- aisstream × Databricks 검증
- API key 발급 (5종)
- 5종 ingestion 검증
- Cargo target 결정 (익명화)
- Mission Lifecycle 설계
- Slack ↔ Apps 동기화 architecture
- Bidirectional Pattern Detection 설계
- Open Data Democratization 선언
- 위기 4가지 카테고리 일반화
- Claude Design prototype

### 코드 일정 (Claude Code 세션)

**Phase 1 (1-2일, 5/8-5/9)**:
- 검증·설계 보강
- 양방향 로직 통합 (direction 필드 활용)
- Mock backtest 데이터 준비

**Phase 2 (3-4일, 5/10-5/13)**:
- Bronze Delta 5종 ingestion
- Lakebase 4 tables 설계 (missions, decisions, pivot_history, audit_log)
- Lakeflow Job 6개 정의 (news / price / ais / ecos / curation / self-critique)

**Phase 3 (2-3일, 5/14-5/16)**:
- Agent Bricks 4개 (Monitoring + Simulation + Mission Plan + Self-Critique)
- 양방향 Pattern Detection 로직 (Layer 3)
- Mission Plan Agent prompt 설계

**Phase 4 (5일, 5/17-5/21)**:
- Vite + React + FastAPI Apps 구현
- Mission Dashboard UI (HEDGE 빨강 / OPPORTUNITY 초록)
- Slack Bolt Bot 통합
- WebSocket 양방향 동기화
- AI/BI Dashboard embed

**Phase 5 (1-2일, 5/21-5/22)**:
- Mock backtest 통합 테스트
- 5분 데모 영상 녹화 (사전 녹화 + 라이브 인터랙션)
- 영상 편집 + 제출

### Cron Job 운영 일정

```
[5/8-5/14] 개발: 60분 cron (무료 1,000 quota 안)
[5/15] $19 OilPriceAPI plan 결제
[5/15-5/19] 통합 테스트: 15분 cron
[5/20-5/22] 데모 준비/녹화: 5분 cron
[5/23] $19 plan cancel + AIS WebSocket Job 정지
```

총 외부 비용: **$19**

---

## 부록 A — 검증된 위기 timeline

```
2025 후반:
- 12-Day War (Iran ↔ Israel) 미해결
- Geneva 핵 협상 결렬

2026 1월 (Pre-Crisis 신호):
- 미 펜타곤 중동 군 가족 출국 명령
- 미 국무부 비필수 인력 출국
- UK Maritime "increased tensions"
- IRGC 강경 발언 빈도 ↑

2026-2/28: Operation Epic Fury 발발
2026-3/01: 호르무즈 봉쇄 시작
[현재 5/8] 봉쇄 지속, 휴전 협상 결렬

→ 가상 시나리오가 아니라 실제 진행 중인 위기
→ Backtest 검증 가능
```

## 부록 B — 데이터 Schema 핵심

### bronze.news_articles (양방향 핵심)
```sql
article_id    STRING        -- SHA256(url)
source        STRING        -- "Reuters", "Yonhap"
tier          STRING        -- "A" | "B"
published_at  TIMESTAMP
importance    INT           -- 0-100
category      STRING        -- geopolitical|policy|disaster|market|supply|demand
direction     STRING        -- bullish|bearish|neutral ⭐ 핵심
horizon       STRING
confidence    STRING
entities      ARRAY<STRING>
```

### Lakebase.missions
```sql
mission_id        UUID PRIMARY KEY
mission_type      VARCHAR(20)   -- 'HEDGE' | 'OPPORTUNITY' ⭐
status            VARCHAR(20)   -- proposed/active/on_track/at_risk/paused/pivoted/aborted/completed
goal_text         TEXT
pattern_score     FLOAT         -- 0-100 (50=균형)
reasoning         TEXT
simulation_roi    JSONB
urgency           VARCHAR(10)
created_at        TIMESTAMPTZ
confirmed_at      TIMESTAMPTZ
confirmed_by      VARCHAR(50)
confirmed_via     VARCHAR(20)   -- 'slack' | 'apps'
pivot_history     JSONB         -- [{from, to, at, reason}]
version           INT           -- optimistic concurrency
```

### silver.pattern_scores_daily
```sql
date              DATE
pattern_score     FLOAT         -- 0-100
bullish_score     FLOAT
bearish_score     FLOAT
cross_val_bonus   FLOAT
mission_type      STRING        -- 'HEDGE' | 'OPPORTUNITY' | 'NONE'
computed_at       TIMESTAMP
```
