# Market Memory + Decision Platform — Final reorient

> 작성: 2026-05-18 D-4
> Supersedes: `2026-05-18-actionable-honest-redesign.md`, `2026-05-18-decision-support-reorient.md`
> 형욱님 본질 push back 반영: **매니저 history 없음 → "AI가 매니저 학습" 컨셉 cut**. 진짜 데이터(backtest 298건 + 6년 ingest)로만 가치 구성.

---

## 1. 5초 가치 제안

> "AI가 7년 시장 메모리를 가지고, 오늘 시그널이 과거 어떤 상황과 닮았는지 + 그때 outcome은 어땠는지 retrieve. 매니저 결정은 platform에 누적 (audit-ready)."

**Bloomberg/Vortexa와 진짜 다른 점**:
- Bloomberg = 시장 가격 history (raw data)
- 우리 = **시그널 패턴 history + AI 시뮬레이션 outcome 분포** (insight)

## 2. 진짜 데이터 자산 100% honest

| 자산 | 데모에 사용 | 정직성 |
|---|---|---|
| 7년 GDELT/EIA/OPEC/FX/OPINET ingest | 시그널 source | ✅ real |
| 298건 backtest_predictions | similar pattern retrieve base | ✅ real (LLM 시뮬) |
| Multi-Agent (Supervisor + Genie + KA + FMA) | conversation Q&A | ✅ real |
| Lakebase mission table | 매니저 결정 누적 platform (시간 지나며 build up) | ✅ real (현재 비어있음, platform 가치) |
| ~~매니저 페르소나 학습~~ | ❌ 사용 안 함 | (데이터 없음) |

---

## 3. 핵심 3 wow

### ★ Wow 1: Similar Market Pattern Retrieve

매니저 화면 진입 시 자동:
```
오늘 시그널 (pattern_score 82, HEDGE zone)

지난 7년 비슷한 패턴 7건:
  · 평균 30일 후 Brent +9.2%, USD/KRW +1.5%
  · AI 추천 따랐을 때 절감: 평균 +0.71%
  · 적중률: 75% (Worst -1.2%, Best +2.8%)
  · 가장 유사한 케이스: 2022/3 Brent +18%, 2017/11 Brent -5%
```

→ **모든 숫자가 진짜 backtest_predictions 데이터**. 매니저가 "이 결정 신뢰할 만한가" 검증 가능.

### ★ Wow 2: Multi-Agent with Auto-Context

매니저 자연어 질문 시 backend가 자동으로 similar pattern context를 prompt에 inject:

```
매니저: "이번 호르무즈 위기 어때?"

AI (Multi-Agent):
"호르무즈 mention burst 강함, GDELT 5/15~5/18에 280% 증가.
 지난 7년 비슷한 escalation 4건 발견:
   - 3건은 봉쇄 발발 안 함 → Brent flat 또는 -3%
   - 1건은 봉쇄 발발 (2022/3) → Brent +18%
 환율 동반 (현재 USD/KRW 1500)은 그 4건 중 2건만.
 환율 동반 케이스 outcome은 양극단 (한 건은 +18%, 한 건은 +0.8%)."
```

→ Genie SQL + Knowledge Assistant + similar retrieval 결합. **진짜 Agent**.

### ★ Wow 3: Decision Audit Platform

매니저 결정 시:
- 결정 type 선택 (HEDGE_review / OPP_review / 관망 / 추가 분석)
- 메모 입력
- **자동 evidence snapshot 첨부**: 시그널 N건, similar patterns ref, Multi-Agent 답
- Lakebase mission row + audit-ready

→ 시간 지나며 매니저 본인 history build up. 진짜 다음 demo (6개월 후)에는 X4 (개인 calibration) 가능. **Platform 가치**.

---

## 4. 5분 demo flow

| Phase | 시간 | Narrative |
|---|---|---|
| 1 | 0:00-0:30 | Opening + Track 1 Open Data 6 source |
| 2 | 0:30-1:30 | 아키텍처 (Apps + Genie + Lakebase + Agent Bricks) |
| 3 | 1:30-2:30 | **Today's Signals + Similar 7건 Retrieve** ★ — backtest 진짜 데이터 |
| 4 | 2:30-3:30 | **Multi-Agent Q&A with context** ★ — 매니저 + AI 양방향 |
| 5 | 3:30-4:15 | **Decision Ledger + Slack sync** ★ — 매니저 행동 기록 |
| 6 | 4:15-4:45 | **6년 시장 메모리 시각화** + 평시 가치 narrative |

---

## 5. Implementation (D-4 ~ D-Day)

### Day 1 (D-4 오늘 5/18)
- ✅ Spec 작성 (이 문서)
- Backend Sub-1 시작: `POST /api/market-memory/similar`
  - Input: current pattern_score + mission_type
  - SQL: backtest_predictions filter (±10 score range, same mission_type)
  - Aggregate: avg/min/max of saving_7d/30d/90d_pct + dubai change %
  - Top 3 most similar return (date + score + outcome)

### Day 2 (D-3 5/19)
- Backend Sub-2: Supervisor query prompt에 similar context auto-inject
- Frontend Sub-3: Dashboard hero `SimilarPastWidget` 신규
  - 오늘 시그널 + similar 7건 평균/분포 시각화
  - 가장 유사 case 3개 detail

### Day 3 (D-2 5/20)
- Frontend Sub-4: AskPage 강화 — Multi-Agent 응답에 similar reference display
- Frontend Sub-5: MissionsPage → "내 결정 ledger" reorient
  - "권고 채택" UX → "결정 type 선택 + 메모 + auto evidence snapshot"
- Jargon 자연어 일괄 풀이

### Day 4 (D-1 5/21)
- Polish + 시연 안전장치
- 영상 녹화 시작

### D-Day (5/22)
- 영상 마무리 + Devpost 제출

---

## 6. Schema 변경

### Lakebase (Sub-A/B columns 그대로 keep, semantic 재정의)

```sql
-- 기존 cycle/supplier_mix/simulation_scenarios columns 그대로 사용
-- semantic 재해석:
--   cycle → 매니저 결정 시점 label ("월간 OSP 검토" 등) — 매니저 input
--   supplier_mix → (cut, 매니저 영역) 또는 매니저 메모 attach용
--   simulation_scenarios → similar pattern outcome 분포 snapshot

-- 새 column (옵션, 향후 Phase 2):
-- decision_type VARCHAR(30)  -- "HEDGE_review" / "OPP_review" / "관망" / "추가분석"
-- similar_patterns_ref JSONB  -- snapshot of N similar patterns (audit-ready)
```

D-4 시간 압박이라 신규 column 추가 안 함. 기존 fields 재사용 + frontend 표시 변경.

### Backend 신규 endpoint

```python
POST /api/market-memory/similar
Request:
{
  "pattern_score": 82.0,
  "mission_type": "HEDGE",
  "limit": 7
}
Response:
{
  "similar_count": 7,
  "summary": {
    "avg_saving_30d_pct": 0.71,
    "avg_dubai_change_30d_pct": 9.2,
    "hit_rate_pct": 75.0,
    "best_case": {"date": "2022-03-12", "saving_30d_pct": 2.8},
    "worst_case": {"date": "2017-11-08", "saving_30d_pct": -1.2}
  },
  "top_matches": [
    {"date": "...", "pattern_score": ..., "saving_30d_pct": ...},
    ...
  ]
}
```

### Multi-Agent prompt 확장

`supervisor.py` query 시 backend가 자동:
1. Current pattern_score fetch
2. similar_patterns fetch (위 endpoint 재사용)
3. LLM user_msg에 inject:
   ```
   ## Similar Past Patterns (last 7 years)
   Found 7 similar market conditions:
   - Avg 30d Brent change: +9.2%
   - AI rec hit rate: 75%
   - Most similar: 2022/3 (Brent +18%), 2017/11 (Brent -5%)
   ```
4. LLM 답에 이 reference 자연스럽게 사용

---

## 7. Success Criteria

1. **Similar Past Widget** — Dashboard hero에 진짜 backtest_predictions 데이터 표시
2. **Multi-Agent reference** — Q&A 응답에 "지난 7년 N건..." 자연스럽게 등장
3. **Decision Ledger** — 매니저 결정 type + 메모 + signals/similar snapshot 자동 첨부
4. **Jargon 0** — Pattern Score / bullish / bearish raw 숫자 frontend에 0 노출
5. **모든 숫자 trace 가능** — 평가위원이 "이거 어디서?" 물으면 backtest_predictions row 가리킬 수 있어야
6. **TS check + Vite build 통과**
7. **5분 demo 6 phase 자연스러운 narrative**

---

## 8. Out of scope (cut)

- ~~Sub-A supplier mix~~ (cut — 가짜 숫자, 매니저 영역)
- ~~Sub-B 3 scenarios simulation~~ (cut — Brent 가정 fake)
- ~~매니저 페르소나 학습 (X2 calibration)~~ (cut — history 없음)
- ~~Bias audit~~ (cut — history 없음)
- ~~Justification memo generator~~ (cut — D-4 시간 부족, Multi-Agent Q&A로 대체)
- ~~Vector Search RAG~~ (cut — SQL filter로 충분, D-4 시간)
- ~~AI/BI Dashboard embed~~ (cut)

---

## 9. Phase 2 / Production (해커톤 이후)

매니저 결정 누적되면:
- X2 Personal calibration ("당신은 호르무즈에서 정확도 80%")
- X4 Counterfactual ("3주 전 다르게 결정했으면 N억")
- X5 Bias audit ("호르무즈 over-react 경향")
- ERP/SAP 연동
- Vector Search 도입 (정성 retrieval)

---

**End of spec.**
