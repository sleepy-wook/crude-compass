# Decision Support Reorient — D-4 fundamental rethink

> 작성: 2026-05-18 D-4 (마감 5/22)
> 목적: "AI 결정 권고" → "AI 결정 지원" 컨셉 전환. 실무자가 진짜 쓸 수 있는 도구.

---

## 1. Why — 형욱님 본질 push back

지금까지의 컨셉이 잘못된 부분:

1. **"AI가 Term 60→75% 결정"** — trader 영역 침범. 책임 + 전문성은 사람.
2. **Pattern Score / bullish / bearish 같은 jargon** — 매니저가 이해 못 함.
3. **시뮬레이션 절대값 (410억)** — 가정 explicit 없으면 fake처럼 보임.
4. **권고에 "어떻게 해야 할지" 없음** — Term 60→75%만 추상.

→ **결과**: "AI 흥미 있는 prototype"이지 "실무 매니저가 매일 쓰는 도구" 아님.

## 2. Industry research findings (D-4 web search)

**진짜 trader가 원하는 것** (bigdata.com case + Vortexa/Kpler 분석):
- "AI가 결정" → **No** (자기 책임)
- **"정보 정리 + 자동 cluster + impact score"** → Yes
- **"분 단위 discovery"** (hours 아님) → Yes
- **"customized morning briefing"** → Yes
- **자연어 query 기반 deep dive** → Yes
- **spike alert** → Yes
- **과거 유사 상황 비교** → Yes

**실패 사례**:
- Bloomberg/generic monitoring tools — "Too slow, too generic, unable to measure real market significance"

→ **우리 강점이 fit하는 곳**: morning brief + Multi-Agent Q&A + alert + backtest

---

## 3. 새 컨셉 — "Decision Support, Not Decision Maker"

**5초 가치 제안**:
> "정유사 매니저가 매일 아침 1분 안에 시장 상황을 파악하도록 AI가 6 source 시그널을 자동 cluster·impact score·자연어 brief로 정리. 매니저는 결정에 집중."

### Brainstorming 결정

| D | 결정 | 픽 |
|---|---|---|
| D1 | 컨셉 전환 단계 | **B — Brief hero + Mission demoted** |
| D2 | Brief 생성 | **B — Daily cron + Lakebase 저장** |

### 새 아키텍처

```
┌────────────────────────────────────────────────────────────────┐
│ HERO — Today's Brief (자연어 자동 cluster + impact score)       │
│                                                                  │
│   "위기 시그널이 매우 강합니다 (10/10)"                          │
│                                                                  │
│   주요 원인: 호르무즈 긴장 + Dubai +8% + USD/KRW +21원          │
│   시장 의미: 공급 차단 + 환율 악화. 과거 유사 → 3주 +12%        │
│   참고 시점: 수요일 Saudi OSP 발표, 다음 주 OPEC 회의           │
│                                                                  │
│   [AI에게 더 질문]  [내 결정 기록]                              │
├────────────────────────────────────────────────────────────────┤
│ Zone 1: 시그널 상세 (cluster + score, source 추적 가능)         │
│ Zone 2: 시장 추세 (가격·환율 차트, 이미 있음)                   │
│ Zone 3: 과거 유사 상황 (backtest cross-reference)               │
│ Zone 4: 내 결정 기록 (Mission demoted — 매니저 ledger)          │
└────────────────────────────────────────────────────────────────┘
```

### Mission concept 역할 변화

**기존**: AI가 "Term 60→75% HEDGE 4주" **결정 제안**
**새**: 매니저가 brief 읽고 **자기 결정**, 결정 후 직접 ledger 기록

```python
# 매니저가 "내 결정 기록" 클릭 → modal:
{
  "decision_type": "HEDGE_review" | "OPP_review" | "관망" | "추가 분석 필요",
  "manager_note": "이번 주 ARAMCO OSP 확인 후 Term lock 검토",
  "linked_brief_id": "...",
  "linked_signals": [...]  # 어떤 시그널 보고 결정했는지
}
```

→ Lakebase mission table 그대로 사용. `goal_text` 필드를 매니저 메모로. `mission_type`은 매니저가 자기 결정 type 선택. `simulation_roi`는 cut.

**효과**:
- 결정 audit trail = 매니저 자기 결정 기록 + brief reference
- Slack sync 그대로 가치 (다른 매니저 review)
- 시나리오 §10 Lifecycle (active/pivot/abort)도 그대로 (매니저 자기 결정 update)

---

## 4. Sub-projects

### Sub-1: Backend — Brief generation

**1.1 Lakebase schema 추가**:
```sql
CREATE TABLE IF NOT EXISTS daily_briefs (
    brief_id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    brief_date          DATE         NOT NULL UNIQUE,
    generated_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    market_state        VARCHAR(20)  NOT NULL,  -- "관망" / "주의" / "적극"
    headline            TEXT         NOT NULL,  -- 한 줄 헤드라인
    body                JSONB        NOT NULL,  -- structured brief sections
    key_signals_ref     JSONB        NOT NULL,  -- top signals 참조 (signal_id list)
    historical_ref      JSONB,                  -- 과거 유사 상황 ref
    upcoming_events     JSONB,                  -- 다가오는 시점 list
    pattern_score_at    NUMERIC(5,2),           -- brief 생성 시점 score (debug)
    confidence_pct      INT                      -- "10점 만점" 자연어 변환용
);

CREATE INDEX IF NOT EXISTS idx_briefs_date ON daily_briefs (brief_date DESC);
```

**1.2 Brief generation service** (`backend/app/services/brief.py` 신규):
- LLM call (databricks-claude-haiku-4-5)
- Input: pattern_score + top signals (90일) + market context + headlines
- Output: BriefSection list (자연어, jargon 풀어쓰기)
- Cache: Lakebase에 1일 1회 저장 (idempotent UPSERT)

**1.3 Endpoints**:
- `GET /api/brief/today` — Lakebase에서 latest brief 조회. 없으면 fallback (live LLM call).
- `POST /api/brief/refresh` — admin trigger (button 또는 cron). 새 brief 생성 + Lakebase upsert.

**1.4 daily_curation 통합**:
- 기존 daily_curation notebook 마지막 step에 `requests.post('/api/brief/refresh')` 추가
- 또는 backend lifespan에 daily timer로 호출 (scheduler library)

### Sub-2: Frontend — Brief hero + Mission demoted

**2.1 새 component `TodayBrief.tsx`**:
- Hero card (Dashboard 최상단)
- Sections: headline + market_state badge + key_signals list + historical_comparison + upcoming_events + posture_note
- Action button: "AI에게 더 질문" → `/ask` page, "내 결정 기록" → modal

**2.2 새 component `MyDecisionLedger.tsx`**:
- 매니저가 직접 결정 type 선택 (HEDGE_review / OPP_review / 관망 / 추가 분석 필요)
- 메모 입력 (자유 텍스트)
- 관련 brief + 시그널 자동 link
- Lakebase mission table에 저장 (backward compat — 기존 mission API 재사용)

**2.3 MissionsPage 재정의**:
- 기존 "AI 권고 mission" → "내 결정 기록 timeline"
- 매니저 결정 history (HEDGE_review 진행 중 → 매니저가 active로 mark → pivot/complete 직접)
- AI 추천 X. Slack sync는 그대로 (다른 매니저 review).

**2.4 Dashboard 구조 재설계**:
```
TopBar (위기 신호 강도 + 진행 결정 + 갱신 시간 + 실시간)
Sidebar (좌측 nav — 오늘의 브리핑 / 내 결정 / AI에게 묻기)

/             — Today's Brief (hero) + Zone 1-4
/decisions    — 내 결정 ledger (기존 /missions reorient)
/ask          — Multi-Agent Q&A (기존 keep)
```

### Sub-3: Jargon 자연어 풀이 (일괄)

**기존 → 새**:
| 기존 jargon | 자연어 |
|---|---|
| Pattern Score 100 | 위기 시그널 강도 10/10 (매우 강함) |
| bullish_score 9068 | 위기 신호 누적 강도 |
| bearish_score 3816 | 안정 신호 누적 강도 |
| HEDGE mode | 위기 대응 |
| OPPORTUNITY mode | 기회 포착 |
| Term 비중 | 장기 계약 비율 |
| Spot 비중 | 즉시 매수 비율 |
| Pivot | 방향 전환 |
| confidence 95+% | 신뢰도 매우 높음 |

**Brief 안 표기**:
- 숫자 hidden, "매우 강함 / 강함 / 보통 / 약함" 자연어 level
- 매니저가 hover 시 raw 숫자 tooltip (advanced 사용자용)

---

## 5. Out of scope (Phase 2)

- Cargo level recommendation (VLCC charter, supplier OSP 자동 lock-in)
- Real-time AIS / Vortexa-like cargo tracking
- ERP/broker portal 연동
- 매니저별 customized brief (개인화)
- Multi-language brief (현재는 한국어)

---

## 6. 5분 demo 재설계 (시나리오 §14)

| Phase | 시간 | Narrative |
|---|---|---|
| 1 | 0:00-0:30 | Opening + Track 1 narrative (Open Data 6 source) |
| 2 | 0:30-1:30 | 아키텍처 (Apps + Genie + Lakebase + Agent Bricks 4 tool) |
| 3 | 1:30-2:30 | **Today's Brief** — 자연어로 위기 강도 + 원인 + 시장 의미 (jargon X) |
| 4 | 2:30-3:30 | **Multi-Agent Q&A** — 매니저가 brief 보고 "더 자세히" 자연어 질의 → Genie + KA + FMA 호출 trace |
| 5 | 3:30-4:15 | **내 결정 기록** — 매니저가 HEDGE_review 선택, 메모 작성, Slack 동기화 |
| 6 | 4:15-4:45 | **과거 유사 상황 비교** — Backtest cross-reference (수치 검증) |

→ 시나리오 §14 Phase 4 "Pre-emptive HEDGE Mission" → "매니저 결정 기록" 자연.
→ 시나리오 §14 Phase 6 "Bidirectional Pivot" → 매니저가 직접 mode 전환 (자기 결정 update).

---

## 7. Implementation Phases (D-4 ~ D-Day)

| Day | 작업 | 산출 |
|---|---|---|
| **D-4 (오늘 5/18)** | Spec 작성 + 형욱님 review | 이 문서 |
| **D-3 (5/19)** | Sub-1 Backend: brief schema + generation service + endpoint | `/api/brief/today` 작동 |
| **D-2 (5/20)** | Sub-2 Frontend: TodayBrief hero + Dashboard 재구조 | Brief가 page hero |
| **D-1 (5/21)** | Sub-2.2/2.3 — MyDecisionLedger + MissionsPage reorient + jargon 일괄 | 매니저 ledger 작동 |
| **D-Day (5/22)** | 영상 녹화 + 제출 | 영상 5분 |

**Risk**: D-4 시간 압박. Sub-1만 D-3 안에 끝나면 Sub-2/3은 빨리 진행 필수.

---

## 8. Success Criteria (form-driven verification)

1. **Brief 자연어 검증** — 매니저 페르소나 모르는 사람이 brief 읽고 "오늘 시장 상황" 5초 안에 이해
2. **Jargon 검증** — Pattern Score / bullish / bearish 같은 단어 frontend에 0 노출 (raw 숫자는 tooltip만)
3. **Mission demoted 검증** — Dashboard hero에 "AI 권고" wording 0, "내 결정" 강조
4. **Backend `/api/brief/today` 작동** — Lakebase fetch 또는 live LLM fallback, 200ms 이하
5. **Multi-Agent Q&A 그대로** — AskPage `/ask` 기존 작동
6. **TS check + Vite build 통과**
7. **시나리오 §14 5분 demo flow** — 6 phase 자연스럽게 narrate 가능

---

## 9. Open Questions (Implementation 단계 결정)

1. **Brief LLM prompt** — 자연어 brief 생성 시 어떤 structure? few-shot examples 필요한가?
2. **Historical comparison source** — backtest_predictions에서 유사 condition 찾기 algorithm?
3. **Mission table reorient** — 기존 mission rows를 매니저 ledger로 자연스럽게 migrate? 또는 새 컬럼?
4. **Brief generation 자동 trigger** — Apps lifespan timer? 또는 외부 cron? 또는 daily_curation notebook 마지막 step?

---

**End of spec.**
