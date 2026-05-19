# Crude Compass — UI/UX 점검 (2026-05-20, D-2)

스크린샷 기반 점검. 6 view state, 1440x900, Databricks Apps prod deploy.

---

## 0. 최우선 — narrative 붕괴 (read this first)

**현재 prod state가 데모 시나리오와 충돌함.**

- TopBar `진행 임무 0건` → Dashboard에서 `현재 열린 case 없음 — 평시 비중 유지` empty state 노출
- `useMissionsActive()`가 빈 배열을 돌려주기 때문 (백엔드 `active` filter에 mission이 안 잡힘)
- `/missions` 좌측 list: `전체 0 / 검토 대기 0 / 진행 중 0` — `해당 상태의 임무가 없습니다.`
- 그런데 `/missions/001353e8-…` direct URL은 HEDGE Term 75% / 29일 mission detail이 정상 렌더
- `/ask?case_id=001353e8…` 헤더의 status pill: `· aborted`
- `상세 보기 (Case File) →` deep link 자체가 Dashboard에 안 나옴 (case가 empty라서 sidebar에도 없음)

**즉 데모 영상 들고 ① TopBar → ② Decision Room hero "위기 10/10" → ③ Bidirectional → ④ Mission split bar → ⑤ Agent timeline → ⑥ 6 actions → ⑦ Case File 흐름이 ③에서 dead-end.** Supervisor가 case 안 열었다는 본문이 위기 10/10과 직접 충돌. 매니저가 볼 actionable surface가 사라짐.

**D-2 fix 후보 (택 1)**:
- (A) 백엔드: mission `001353e8…`의 status를 `aborted` → `proposed`로 복구 (또는 새 mission seed). frontend 코드 무수정.
- (B) frontend hack: `useMissionsActive`가 비었을 때 가장 최근 case 1건을 fallback으로 잡아서 Dashboard에 노출 + status pill을 `검토 보류` 같은 dimmed 라벨로 표기. 단 mission_type=HEDGE는 유지.
- (C) 시나리오 재구성: Decision Room의 empty 상태를 "평시" 데모 모드로 적극 활용하고, Case File 안으로 진입했을 때만 위기 demo. 단 hero가 위기 10/10이라 carrier로는 어색.

가장 안전한 path는 (A). 데모 5분 중 4분이 case 중심이므로.

---

## §1 페이지별 점검

### 1.1 `/` Decision Room (top → middle → bottom)

**top (Hero "위기 시그널 강함 10/10")**
- 잘된 점: copy 한 줄에 stat 4개 (유사 패턴 / 평균 절감 / 적중률 / 가격 변동) 응축됨. 색 token 일관 (crisis-700 vs opportunity-700).
- **필요 없음**:
  - 우측 상단 `월중 Spot 조정 · OSP D-16` chip은 hero와 시각 무게 거의 동등한데 카피가 약함. "월중 Spot 조정"이 매니저 행동 prompt가 아니라 정황 설명. → hero 무게 줄이거나 우상단 chip을 더 작게.
  - "지난 7년 시장 메모리 기반" 우상단 caption — 본문 "지난 7년 비슷한 시장 상황이 4번 있었습니다" 와 중복.
- **개선**:
  - hero stat 4개 중 "유사 패턴 4건"과 "적중률 75.0%"는 같은 의미 축. `평균 절감 0.09%`은 작아서 신뢰 못 줌 — `최고 사례 0.79% / 최악 -1.21%`이 더 강한 데모 hook. 최고/최악 카드를 위로 올리는 것 고려.
- **필요한데 빠짐**:
  - 데모 narrative 상 "그래서 매니저는 지금 뭐 해야 하지?" 가 hero 직후에 와야 하는데 비어 있음 (case 없음 empty state로 끊김). → §0 이슈와 직결.

**middle ("오늘의 시그널")**
- 좌 `양방향 신호 강도` 3-zone bar 좋음. crisis(빨강) vs opportunity(초록) 중간 `관망` zone gray. 현재 zone `위험방어 (90+)` 정상 표기.
- **필요 없음**: 좌측 카드 하단 `오늘 가장 강한 시그널 TOP 3` 세 항목 모두 `GDELT 뉴스 키워드 burst` (같은 라벨) + `USD/KRW 환율 2.1%` — 라벨이 거의 동일하면 데모 보는 사람이 "왜 같은 게 두 번 있지?" 의문 든다. 라벨에 sub-category 구분 필요 (예: `GDELT (호르무즈)` vs `GDELT (이란 제재)`).
- **개선**: 우측 `CASE FILE — 현재 열린 case 없음` 카드가 좌측 카드 1/2 높이에서 텅 빔. 시각 imbalance. case가 있으면 MissionSummaryCard로 fill되지만 지금은 dead air. min-height 맞추거나 case 없을 때만 좌측 카드 col-span-2.
- **일관성**:
  - 좌측 SectionHeader는 `오늘의 시그널 · 양방향 강도 · 위험·기회 동시 추적` — 다른 페이지에서는 `Decision Room / Market Watch` 같은 English overline + Korean h1 패턴인데 여기는 overline 없음.

**bottom**
- middle 영역이 사실상 page 끝. AgentActivityTimeline section 자체가 렌더 안됨 (topMission null).
- 즉 Dashboard의 1/2이 비어있는 셈. **5분 데모 영상에서 가장 손해 보는 페이지.**

### 1.2 `/market` Market Watch

**top**
- header overline `MARKET WATCH` + h1 `Agent Bricks 근거판 — 현재 case 검증` 좋음. 우상단 inline `90일 시그널 1,062 → 위험방어 10/10` 좋음.
- **필요 없음**: `REACTIVE TRIGGER 참조` 박스 카피 `… (Lakebase에 reactive 이벤트 기록)` 같은 백엔드 implementation detail은 매니저가 안 봄. 마침표 잘라도 무방.
- Intraday ticker 3-up (Brent/Dubai/WTI) 가독 좋음. `30분 +0.35%` / `24h -0.62%` / `최근 spike -1.59% · 20시간 전` — Brent에 spike `-1.59%`가 빨강(crisis)인데 실제론 가격 하락 = 매수자 입장 기회. 색 의미를 정유사 시점으로 통일하면 더 직관 (오를 때 빨강).

**middle (Intraday 시계열 차트)**
- y-axis label 위쪽이 `$1, $1, $0, $0` 같은 round-off 문제. **명백한 버그.** screenshot ss_86761hn5u 참조. 데이터 범위 좁은데 step format이 round 안 됨. → y-axis tick format 소수점 2자리 강제.
- 차트 자체 line 없는 빈 백색 영역이 큼 (Intraday 5분 24h). 5분 데이터 sparse하거나 fallback "로딩 중…" 둘 다 표시. 둘 중 하나로 결정.

**bottom (시간 지평별 시그널)**
- `선행 (Leading) 7일 ~ 1일 전` 좋음. 단 `GDELT 뉴스 키워드 burst` 같은 항목이 빨강 dot과 초록 dot 두 번 — 색 의미 불명확. legend 없음.
- `구조 (Macro)` 의 OPEC 사우디·이란 생산 contribution 0.1% — 거의 0인데 보여줄 이유? Top 3로 cap하면 비주얼 noise 줆.

### 1.3 `/ask` Investigation generic

**top**
- header `INVESTIGATION / Agent Bricks Supervisor 조사 콘솔` 좋음. AGENT BRICKS SUPERVISOR ORCHESTRATION 박스의 4-node diagram (매니저 → Supervisor → 3 sub-agent) 좋음 — 데모 영상에서 멈춰서 설명할 anchor.
- **개선**: Supervisor 박스가 너무 어두움 (gray-900 같은 톤). 매니저 박스/Genie/Knowledge Assistant/Mission Plan과 무게 격차가 큼. Supervisor가 강조되어야 하는 건 맞는데 black bg는 다른 카드와 visual style 깨짐.
- 박스 안 `mission_plan_advice · ai_query(claude-haiku-4-5)` — 매니저용으로는 implementation noise. demo면 model 이름 강조 좋지만 평가위원도 알아야 함. 결정: 유지.

**bottom (예시 질문 + 입력)**
- `보내기` 버튼 색이 disabled-look (gray) — 사실 enabled 상태인데 hover일 때만 ink-1로 진해진다면 affordance 부족.
- `과거 권고 검증` collapsible은 카드 한 줄만 보이고 펼치기 affordance가 우측 텍스트 `펼치기`로만. chevron icon 없음.

### 1.4 `/ask?case_id=…` Investigation case-bound

**top**
- h1이 `이 case 조사` — generic은 `Agent Bricks Supervisor 조사 콘솔`인데 case-bound는 갑자기 짧아짐. 일관성 깨짐. 제안: `이 case 조사 — Supervisor 콘솔` 같이 동일 suffix 유지.
- `현재 조사 중 CASE` 박스 안 `위험방어 · Pattern Score 100 · 긴급도 urgent · aborted` — **`aborted` 라벨이 평가위원에게 "케이스 중단된 거 왜 보여줘?"라는 의문 줌.** §0과 결합. fix.
- 예시 질문 6개 모두 case-bound로 잘 갈렸음.

### 1.5 `/missions` Case File list

- **top + 전체**: split layout. 좌측 list pane `전체 0 / 검토 대기 0 / 진행 중 0` — 빈 list. 우측 panel "왼쪽에서 임무를 선택하세요" placeholder.
- 단 sidebar 하단 `모든 임무는 Slack에서도 채택/거절/방향 전환할 수 있습니다.` footnote는 정보 있는 페이지지만 본 list는 empty. 데모에서는 절대 들어가면 안 되는 페이지 상태.
- **개선**: empty state 일러스트레이션 없음. 평시 모드 narrative 카피 추가 ("Supervisor가 평시 임계 안이라 case를 열지 않았습니다 — Market Watch에서 모니터링 신호를 확인하세요" + Market Watch 링크).

### 1.6 `/missions/:id` Case File detail

**top**
- pill 4종 한 줄: `위험방어 / 거각 / 긴급 / ● APPS 채택` — `거각` 오타? "각하" 또는 "기각" 의도? type label 인지 status pill인지 모호. `위험방어`(type) + `기각`(status) + `긴급`(urgency) + `● APPS 채택`(channel)이 한 줄에 섞임. 카테고리 그루핑 부족.
  → **`거각`은 명백한 오타 또는 컴포넌트 라벨 매핑 버그.** `frontend/src/lib/utils.ts`의 `statusLabel` 또는 `MissionTypePill` 라벨 확인 필요.
- h1 `Term 비중 (장기 계약) 권고` 좋음. 단 다른 페이지는 h1 위에 English overline (DECISION ROOM / MARKET WATCH / INVESTIGATION / CASE FILE) — 여기는 overline 없고 pill row가 대체. 일관성 깨짐.
- 본문 reasoning 4-5줄 (`지난 90일간 escalation 신호 1,059건 누적 …`) 매우 좋음. 데모 narrative carrier.
- `현재 운영 비중 Term 60% Spot 40%` + `AI 권고 비중 Term 75% Spot 25%` split bar + `Term +15%p / Spot -15%p` delta chip — 시나리오 핵심. 강점.

**middle**
- `위기 강도 10/10 / TERM 비중 75% / 기간 29일` — TopBar에는 `진행 임무 0건`이라 했는데 여기는 진행 중인 mission처럼 보임. **TopBar vs detail page 데이터 inconsistency**. §0과 직결.
- `예상 시나리오` 3 chip (긴장완화 -140억 / 평화협상 -280억 / Iran 제재강화 +320억) — 단위 `억원` 명시. 좋음.
- `매니저의 다음 행동` 6-button grid — Approve Draft / Adjust Draft / Dismiss Case / Keep Watching / Ask for More Evidence / Re-check Later. 
  - Approve Draft만 highlight active, 나머지 5개 dim. dim 정도가 disabled-look에 가까움. 실제 click 가능하면 hover affordance 강화.
  - `Dismiss Case` 라벨이 crisis(빨강). 맞는 선택. 다만 다른 5개 라벨이 영문(Approve/Adjust/Keep/Ask/Re-check) + 본문 한국어 sub label — `keep watching 모니터링 36일 연장` 같이. 의도된 voice/style mix이지만 평가위원에게는 약간 distract. 

**bottom (Agent Bricks 활동 이력)**
- `7건` count. weighted_signal / Agent Bricks Supervisor / Mission Plan (FMA) / 매니저 / Agent Bricks Supervisor / 매니저. **`매니저 · 기각` 12분 전** — 매니저가 12분 전에 기각했는데 위에 6 actions는 여전히 actionable처럼 보임. 정합 X.
- Agent Bricks Supervisor 응답 종합 항목: **`I'm ready to help you with crude oil market analysis and procurement recommendations. The system is warmed up and all agents are available. - **Crude Oil Market Analysis (Genie)** - for structured da`** — **영문 시스템 boilerplate가 그대로 노출**. LLM 응답 truncated + 영문 prompt 응답이 매니저용 UI에 출력됨. **명백한 fix 우선순위 1.**
- 매니저 actor 라벨이 영어 (`매니저`) + supervisor는 `Agent Bricks Supervisor` 영문. 일관 패턴: actor 한국어("매니저") + system tool 영문(Agent Bricks Supervisor / Mission Plan (FMA) / weighted_signal (UC Func)) — 이 패턴은 OK.

---

## §2 전체 일관성 issues (cross-page)

### 2.1 헤더 패턴
- `/` `/market` `/ask` `/ask?case` — 모두 `[ENGLISH OVERLINE] + [h1 Korean] + [subtitle Korean]` 패턴. **`/missions/:id` 만 overline 없음.** pill row가 그 자리를 차지. **일관성 1순위 fix.**

### 2.2 SectionHeader
- Dashboard `SectionHeader`: `mt-20 mb-6 pb-4 border-b border-line-1` + h2 `text-xl font-semibold tracking-tight` + subtitle `text-xs text-ink-3`.
- MarketDataPage `SectionHeader`: `mt-12 mb-4 pb-4 border-b border-line-1` — **mt-20 vs mt-12 차이.** 시각 rhythm 깨짐.
- 두 컴포넌트가 별도 inline 정의 — shared component로 통합 필요 (지금은 시간상 옵션 B: 두 값 중 하나로 표준화). 권장: mt-16.

### 2.3 Pill / Badge 일관성
- `StatusPill` vs `MissionTypePill` vs 그냥 `<span class="text-[10px] uppercase tracking-wider bg-crisis-500 text-white px-2 py-0.5 rounded">긴급</span>` — Dashboard MissionSummaryCard에서 inline span으로 직접 작성. shared component 없음.
- Case File detail의 `● APPS 채택` pill 모양이 다른 pill과 다름 (dot prefix + outline 다름).

### 2.4 Color token
- crisis vs opportunity 잘 지켜짐. 단:
  - Intraday spike `-1.59%` crisis-red 색 — semantic 의문 (가격 하락은 정유사 매수자 입장 호재).
  - Market Watch 시간 지평별 시그널 dot의 빨강/초록이 contribution 부호(+/-)인지 매도/매수인지 의미 안 보임. legend 없음.

### 2.5 한국어/영어 라벨 정책
- Overline은 영어 (DECISION ROOM, MARKET WATCH, INVESTIGATION, CASE FILE) — 좋음.
- Actor 라벨: 매니저(한) + Supervisor / Genie / Knowledge Assistant / Mission Plan (FMA) — 영문 system name. 의도된 voice. 유지 OK.
- `매니저의 다음 행동` 6 actions 라벨이 영문 (Approve Draft / Adjust Draft / Dismiss Case / Keep Watching / Ask for More Evidence / Re-check Later) — 의도된 agentic 용어 retention. 단 sub-label은 한국어 mix. 매니저 데모 hand-off 위해 OK.

### 2.6 actor name 표기 일관성
- Agent Bricks Supervisor (timeline) vs Supervisor (orchestration diagram) — 동일 주체인데 prefix 유무 다름.
- Knowledge Assistant (OPEC) vs Knowledge Assistant — suffix 유무 다름.
- Mission Plan (FMA) vs Mission Plan (UC Func) vs mission_plan_advice (UC Function) — 세 표기 mix. **혼란.** 권장: timeline에서 `Mission Plan (FMA)` 1개로 통일하고 UC Function 호출은 sub-event로 nesting.

### 2.7 시간 포맷
- `1일 전`, `1시간 전`, `16분 전`, `12분 전` — relativeTime 일관.
- `생성 2026. 05. 18. 오후 08:58` (case detail top) — Korean locale 절대 시각. OK.
- TopBar `데이터 어제 갱신` — "방금 갱신 / N시간 전 갱신 / 어제 갱신 / N일 전 갱신" 정의된 ladder. OK.

### 2.8 number formatting
- `tabular-nums` 클래스 hero stat / TopBar / case detail stat 모두 적용. OK.
- `1,062건` `9253` `3816` — 천 단위 콤마 일관성 깨짐. `9253` `3816` (Bidirectional 누적)이 콤마 없음. → comma 통일.
- 가격 `$110.35`, 환율 `+43.00%` 표기 OK.

---

## §3 demo narrative 관점 critical findings

심사 5축 중 **User Experience (20%)** + **Data Storytelling (20%)** = 40% 직접 영향.

**critical (데모 영상에서 평가위원이 즉시 인지)**

1. **§0 narrative 붕괴** — TopBar `진행 임무 0건` + Dashboard empty + `/missions` list 빈 상태. 5분 영상의 main flow가 끊김. **반드시 fix.**
2. **case detail에 영문 LLM boilerplate 노출** — "I'm ready to help you with crude oil market analysis…" agent_activity_events에 저장된 raw LLM 출력이 그대로 매니저 UI에 표시됨. 평가위원 즉시 인지.
3. **`거각` 오타 / 잘못된 status label** — Case File detail pill row.
4. **case status `aborted`** — /ask case-bound에 노출. 데모 카리어로는 부적합.
5. **Intraday y-axis `$1, $1, $0, $0`** — 명백한 chart format 버그. Market Watch first impression.

**high (데모 영상에서 흐름은 살리지만 디테일에서 감점)**

6. Dashboard middle 우측 CASE FILE 카드가 case 없을 때 좌측 카드와 height 격차로 dead air.
7. Case File detail에 overline 없음 (다른 4 페이지와 패턴 깨짐).
8. SectionHeader spacing 일관성 (mt-20 vs mt-12).
9. 6 actions의 dim 5개가 disabled-look. clickable affordance 강화.
10. `오늘 가장 강한 시그널 TOP 3` 라벨 중복 (GDELT 두 번).

**mid (눈에 띄지만 5분 영상에 안 잡힐 가능성)**

11. Intraday spike 색 semantic (정유사 매수자 시점).
12. Reactive Trigger 박스 카피 implementation detail 노출 (Lakebase 운운).
13. 시간 지평별 시그널 dot legend 없음.
14. Mission Plan (FMA) vs (UC Func) vs ai_query 명명 혼재.
15. AskPage `보내기` 버튼 affordance.

**low (안 고쳐도 무방)**

16. 천 단위 콤마 통일 (9253 → 9,253).
17. AskPage `과거 권고 검증` collapsible chevron icon 없음.
18. OspCycleChip의 우상단 무게.

---

## §4 우선순위 — D-2 fix 가능 작업

### High (오늘 D-2 안에 반드시)

| # | 작업 | 예상 소요 | 영향 |
|---|---|---|---|
| H1 | mission `001353e8…` status 복구 (`aborted` → `proposed` 또는 `active`) | 백엔드 DB 1줄 update | 5분 영상의 main flow 부활. **§0 해결.** |
| H2 | Agent Activity timeline에서 영문 LLM boilerplate event filter 또는 본문 truncate + 한국어 fallback | frontend `AgentActivityTimeline.tsx` ~10줄 | 평가위원 즉시 감지되는 unpolished 인상 제거 |
| H3 | `거각` 오타 fix (`MissionTypePill` 또는 `statusLabel` in `lib/utils.ts`) | 1줄 | obvious bug |
| H4 | Intraday chart y-axis format (소수점 2자리 또는 동적 step) | `IntradayChart.tsx` ~3줄 | Market Watch 첫인상 |
| H5 | `/missions/:id` overline 추가 (`CASE FILE`) — h1 위 11px uppercase tracking | `MissionsPage.tsx` detail panel header ~5줄 | 일관성 cross-page 즉시 회복 |

### Mid (시간 남으면)

| # | 작업 | 예상 소요 | 영향 |
|---|---|---|---|
| M1 | Dashboard MissionSummaryCard empty state height (좌측 Bidirectional과 row align) | 1줄 (min-height 또는 col-span 조건) | 시각 imbalance 제거 |
| M2 | 6 actions clickable affordance (border + hover ring) | `SuggestedNextActions.tsx` className 2개 | 데모에서 강조 |
| M3 | TOP 3 시그널 GDELT 중복 라벨 sub-category (호르무즈/이란) | 백엔드 reason_text 컬럼 또는 frontend regex | dense 감 살림 |
| M4 | Reactive Trigger 카피에서 `(Lakebase에 …)` 괄호 제거 | 1줄 | 평가위원 hint reduce |
| M5 | SectionHeader spacing 통일 (Dashboard mt-20 → mt-16, MarketData mt-12 → mt-16) | 2 파일 | 시각 rhythm |
| M6 | Bidirectional 누적 9253 / 3816 콤마 (`9,253 / 3,816`) | utils.ts toLocaleString 1줄 | polish |

### Low (안 해도 됨)

| # | 작업 |
|---|---|
| L1 | Actor name 표기 통일 (Agent Bricks Supervisor / Knowledge Assistant suffix 일관) |
| L2 | Intraday spike 색 semantic 반전 검토 |
| L3 | 시간 지평별 시그널 dot legend |
| L4 | AskPage `과거 권고 검증` chevron icon |
| L5 | AGENT BRICKS SUPERVISOR ORCHESTRATION diagram Supervisor 박스 톤 |

---

## §5 코드 ref

| 항목 | 파일 | line 추정 |
|---|---|---|
| Dashboard empty / topMission 분기 | `C:\crude-compass\frontend\src\pages\Dashboard.tsx` | 29-43, 104-119, 152-169 |
| TopBar `진행 임무` count | `C:\crude-compass\frontend\src\components\TopBar.tsx` | 51-55, 91 |
| `useMissionsActive` (data source) | `C:\crude-compass\frontend\src\lib\queries.ts` | grep `useMissionsActive` |
| Mission status `aborted` filter | 백엔드 `/api/missions/active` (frontend grep 안 됨, backend repo 확인) | — |
| Mission detail page overline 누락 | `C:\crude-compass\frontend\src\pages\MissionsPage.tsx` | detail panel header (수동 확인 필요) |
| `거각` 오타 (라벨 매핑) | `C:\crude-compass\frontend\src\lib\utils.ts` `statusLabel` 또는 `missionTypeLabel` | grep `거각` |
| Agent Activity LLM boilerplate filter | `C:\crude-compass\frontend\src\components\AgentActivityTimeline.tsx` | event payload `text` 또는 `summary` 필드 truncate |
| Intraday y-axis | `C:\crude-compass\frontend\src\components\IntradayChart.tsx` | y-axis tickFormatter |
| SectionHeader 중복 정의 | Dashboard.tsx:291-300, MarketDataPage.tsx:120-129 | 두 컴포넌트 inline — 통합 권장 |
| 6 actions dim 색 | `C:\crude-compass\frontend\src\components\SuggestedNextActions.tsx` | grep `Approve Draft` |
| MissionSplitBar baseline label | `C:\crude-compass\frontend\src\components\MissionSplitBar.tsx` | currentSourceLabel prop |
| Reactive Trigger 카피 | `C:\crude-compass\frontend\src\pages\MarketDataPage.tsx` | 62-65 SoWhat actor="Reactive Trigger" text |
| MissionTypePill / StatusPill 스타일 | `C:\crude-compass\frontend\src\components\StatusPill.tsx` | — |
| Bidirectional 누적 number format | `C:\crude-compass\frontend\src\components\Bidirectional3Zone.tsx` | grep `crisis 신호 누적` |

---

## 요약

**1등 목표 + D-2 + 5분 데모 + UX/Storytelling 합 40%** 관점에서 가장 위험한 single point는 **§0 narrative 붕괴 (case `aborted` → 진행 임무 0건 → Dashboard dead air)**. 백엔드 1줄 update로 5분 영상 main flow 부활. 그 외 H2 (영문 boilerplate)와 H3 (`거각` 오타)는 평가위원이 즉시 인지하는 unpolished signal — 무조건 fix. 나머지는 visual polish.

**push back**: 친구분의 디자인 직관을 의심하지 않지만, 현재 prod state는 디자인 이슈보다 데이터/상태 이슈가 압도적. UI 더 다듬기 전에 백엔드 mission state 복구가 1순위.
