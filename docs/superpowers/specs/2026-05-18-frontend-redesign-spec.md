# Frontend Redesign Spec — D-0 1등 진입 plan

> 작성: 2026-05-18 D-0
> 목적: Discovery 12 section overload → 시나리오 §13 4 component "AI assistant first" 정렬
> 형욱님 push back 반영: ① 한글화 일괄 ② Icon 자제 ③ 세련 + 이쁘게

---

## 1. 컨셉

**Editorial Korean Minimalist**:
- 큰 typography hero + 여백 generous
- 절제된 색 (crisis red / opportunity green / 회색 톤)
- 한 페이지 = 1 narrative arc (data dump X)
- "평시 가치가 메인" 시나리오 §2 narrative anchor
- **Icon 자제** — typography + color만 (emoji icon 모두 제거)

작년 APJ 1등 Puma "Beyond dashboards toward actionable intelligence" 정합.

## 2. 한글화 mapping (일괄)

| 영문 | 한글 |
|---|---|
| HEDGE | 위험방어 |
| OPPORTUNITY / OPP | 기회포착 |
| Term | 장기계약 |
| Spot | 즉시구매 |
| Mission | 임무 |
| Pivot | 방향전환 |
| Confidence | 신뢰도 |
| Reactive | 실시간 알림 |
| Bullish / Bearish | 위기 / 약세 |
| Backtest | 백테스트 검증 |
| Pre-emptive | 사전 |
| Bidirectional | 양방향 |
| Supervisor | AI 어시스턴트 |

영문 잔재 sweep target files:
- `frontend/src/pages/Discovery.tsx`
- `frontend/src/pages/Missions.tsx`
- `frontend/src/pages/WhatIf.tsx`
- `frontend/src/components/Sidebar.tsx`
- `frontend/src/components/Glossary.tsx`
- `frontend/src/components/StatusPill.tsx`
- `backend/app/store.py` (mission seed 이미 한글화)
- `backend/app/services/demo_scenarios.py` (이미 한글화)
- `backend/app/services/genie.py` (fallback narrative)

## 3. Page Architecture

### 3.1 Discovery (`/`) — "오늘의 결정"

**Hero (above fold)**:
```
        K-Petroleum · 2026년 5월 15일 화요일

                  오늘의 결정

      100점  ↗ 위험방어 강세
      ━━━━━━━━━━━━━━━━━━━━━━━
      위기 신호 7,862 · 안정 신호 3,575
      신뢰도 92% · 90일 시그널 1,046건

      [AI 권고: 장기계약 60% → 75% · 4주]
                [↻ 지금 새 권고 생성]
```

**5 cards (가로 grid, icon 없음)**:
1. **위험방어** — 장기계약 60→75% · 최대 절감 +410억원
2. **기회포착** — 즉시구매 40→55% · 최대 절감 +280억원
3. **실시간 알림** — 호르무즈 키워드 멘션 +280%
4. **신호 기여도** — 공개 6 소스 종합 (link)
5. **진행 임무** — 2건 진행 중 (link)

**Below fold (scroll)**:
- 시그널별 기여도 차트 (큰 시각화)
- Pattern Score · 6년 평시 가치 (호르무즈 봉우리 + 평시 narrative)
- Dubai/Brent/WTI · 90일
- USD/KRW · 90일
- 최근 7일 핵심 뉴스
- OPEC MOMR · Document Intelligence
- 백테스트 검증 라이브 badge

### 3.2 Missions (`/missions`) — "진행 중 임무"

**Hero**: "진행 중 임무 (2건) — AI가 양방향 권고"

**2-col mission cards**:
- 위험방어 카드 (사전 헤지)
- 기회포착 카드 (사전 매입)

각 card: title (한글) + 비중 변화 + 최대 절감 + reasoning + 신뢰도. Icon X.

### 3.3 WhatIf (`/whatif`) — "과거 시점 복원"

**Hero**: 6년 평시 가치 chart 큰 시각화 + "AI 추천을 따랐다면 어떻게 됐을까?"

**Below**:
- ● 라이브 검증 success card (n=15, hit 73.3%, run_id)
- Time Travel slider (15 시점)
- 최근 30개 AI 추천 테이블
- AI 어시스턴트 (Supervisor)

## 4. Visual Style

| 항목 | 결정 |
|---|---|
| Font | Pretendard Variable |
| Hero typography | font-display 5xl-6xl, tracking-tight |
| Body | font-sans, leading-relaxed |
| Color crisis | `#dc2626` ~ `#fee2e2` (유지) |
| Color opportunity | `#16a34a` ~ `#d1fae5` (유지) |
| Background | paper cream + panel white |
| Max-width | 1100px (1280 → 좁힘, 가운데 정렬 강조) |
| Hero spacing | py-16, mb-12 |
| Section gap | gap-12 |
| Border | subtle (line-1) |
| Shadow | minimal |
| **Icon** | **자제 (emoji 모두 제거, 절제된 unicode 화살표만 허용)** |
| Animation | subtle (hover scale, smooth transition) |

## 5. Implementation Plan

### Step 1: 한글화 일괄 sweep (30분)
영문 잔재 grep + 한글 변경.

### Step 2: Discovery Hero refactor (45분)
- 새 Hero component: 큰 typography + Pattern Score + 권고 1줄
- Pattern Score Card 3-col → Hero 통합
- "오늘의 1줄 의사결정" 배너 → Hero 통합
- "지금 새 추천 생성" 버튼 → Hero 하단

### Step 3: 5 cards 신규 (60분)
- `DecisionCards.tsx` 신규
- 5 cards 가로 grid (responsive)
- icon 없음, typography + 색 절제
- link to detail sections

### Step 4: Below the fold 재배치 (30분)
- 기존 component 그대로 유지
- 순서 재배치 (기여도 → 6년 chart → Detail charts → News → OPEC → Backtest)
- "백테스트 검증" Discovery 마지막에 라이브 badge

### Step 5: Missions Page Polish (30분)
- Hero 한 줄 추가
- 2-col mission cards (이미 정상)
- icon X (현재 없음)

### Step 6: WhatIf Polish (30분)
- Hero refactor (6년 chart 위로)
- ● 라이브 검증 success card 강조 (이미 추가됨)

### Step 7: Sidebar Polish (20분)
- 한글화 마무리
- 4 tool ● 라이브 표시 (이미 적용)

### Step 8: Glossary Update (15분)
- HEDGE/OPP/Term/Spot 한글 표제어 + 영문 secondary
- (현재 이미 한글 위주이지만 일부 영문 잔재 sweep)

### Step 9: Visual polish + responsive check (30분)
- max-width 1100 적용
- 여백 increase
- Pretendard Variable 강화

### Step 10: Commit + Deploy (15분)

**Total: 4-5h**

## 6. Success Criteria

- Discovery 첫 5초에 평가위원이 "AI assistant + 결정"으로 인식 (현재 "data dump")
- 영문 잔재 0 (한국어 트랙 정합)
- Icon 없음 (typography minimalism)
- 시나리오 §13 4 component 컨셉 정합
- A3 UX +3, A5 Storytelling +2 (Evaluator 2차 83.5 → 88+ 추정)

## 7. Skip / 후순위

- New visual component (chart 추가, mockup 새로) X — 기존 재사용
- Animation (Framer Motion 등) — minimal hover only
- Mobile breakpoint — desktop-first 유지 (1280px+ 기준)
- DESIGN.md (design system formal) — D-0 시간 X
