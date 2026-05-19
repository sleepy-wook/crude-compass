# Text Review — 2026-05-20

해커톤 D-2 직전 한국어 텍스트 교정 패스. Decision Case framing + 4기능 narrative 정직성 강화 + 일관성 통일.

**범위**: `frontend/src/**` user-visible 한국어 텍스트만. 코드 식별자 변경 X. 의도된 디자인 결정 (영문 overline + 한글 h1, "Mission" 코드 식별자, "Term/Spot" 업계 용어, 4기능 영문 명) 보존.

**결과**: 9개 파일 / 34줄 변경. `npx tsc --noEmit` 통과.

---

## §1. 발견된 문제 카테고리

### 1.1 "AI 권고" / "AI 추천" — Recommendation-app 잔재 (Decision Case framing 약화)
- 코드 base 전체 12회 발견
- "AI 권고"는 단방향 black-box recommendation 인상을 줌 → Decision Case framing과 충돌
- 정책: `Supervisor 권고` (Agent Bricks Supervisor narrative 강화) 또는 case-pending 톤으로 통일
- **변경 8회**

### 1.2 User-visible "임무" / "Mission" 잔존 — Case-centric framing 미적용
- TopBar "진행 임무", MissionsPage "임무를 찾을 수 없습니다" / "임무를 선택하세요" / "임무가 없습니다" / "임무는 Slack에서도..."
- Glossary footer "양방향 Mission (위기+기회)"
- 정책: 코드 식별자 (`Mission`, `mission_id`) 보존, user-visible은 "case" / "결정 케이스"로 통일
- **변경 6회**

### 1.3 영문 jargon 잔존 — 매니저 페르소나 톤 불일치
- AskPage sample 질문 `"structured 데이터와 document evidence가 충돌하나?"` — 매니저가 실제로 안 쓸 표현
- `"approve보다 keep watching이 더 나은 이유는?"` — 동일
- AskPage 응답 spinner `"Multi-Agent가 분석 중..."` — narrative 약화 (Supervisor 명시 X)
- BacktestTimeSlider preview `"Term 비중 75%로 hedge한 케이스"` — "hedge" 영문 어색
- Sidebar `"결정 기록 + revision"` — 한글 + 영문 혼재
- **변경 5회**

### 1.4 단위 표기 일관성 — "Pattern Score" 0~100 vs "위기 강도" 0~10
- 사용자 visible "Pattern Score" 잔존: MarketDataPage 섹션 헤더 "Pattern Score 7년 시계열", AskPage case context "Pattern Score 78"
- 다른 곳은 모두 `Math.round(pattern_score / 10)/10` 한국어 "위기 강도 N/10" 일관 적용 중
- 정책: user-visible은 "위기 강도 N/10" 통일 (TopBar / MissionsPage Detail / Dashboard MiniStat과 일치)
- **변경 2회** (LLM에 보내는 enriched context의 "Pattern Score:" 라벨은 모델 입력이라 보존)

### 1.5 narrative 약화 표현 — Agent Bricks orchestration 가시화 X
- MissionsPage DecisionChainPanel `"Mission Plan Agent"` — codex P0 정책에 따라 `"Mission Plan (FMA)"`가 정직 표기
- AskPage input hint `"자연어 질의는 Multi-Agent를 통해 응답됩니다"` — 정직 narrative `"Agent Bricks Supervisor가 sub-agent를 라우팅"`이 더 강함
- **변경 2회**

### 1.6 NewsTopList / OpecCitation / Bidirectional3Zone / SuggestedNextActions
- 점검 결과 user-visible 한국어 자연스럽고, "Approve Draft" / "Keep Watching" 등 SuggestedNextActions 영문 라벨은 codex P0 "6 agentic options" narrative 의도된 디자인. 변경 X.

---

## §2. 변경 내역 (파일별)

### `frontend/src/components/MissionSplitBar.tsx`
| Before | After |
|---|---|
| `AI 권고 비중` (column label) | `Supervisor 권고 비중` |
| `AI 권고 Term (장기 계약) ...` (title attr) | `Supervisor 권고 Term (장기 계약) ...` |
| `AI 권고 Spot (즉시 매입) ...` (title attr) | `Supervisor 권고 Spot (즉시 매입) ...` |

### `frontend/src/pages/MissionsPage.tsx`
| Before | After |
|---|---|
| `해당 상태의 임무가 없습니다.` | `해당 상태의 case가 없습니다.` |
| `모든 임무는 Slack에서도 채택/거절/방향 전환할 수 있습니다.` | `모든 case는 Slack에서도 채택/거절/방향 전환할 수 있습니다.` |
| `왼쪽에서 임무를 선택하세요.` | `왼쪽에서 case를 선택하세요.` |
| `임무를 찾을 수 없습니다.` | `case를 찾을 수 없습니다.` |
| `AI 권고는 {target}%. 매니저 판단으로 조정해서 기록할 수 있습니다.` | `Supervisor 권고는 {target}%. 매니저 판단으로 조정해서 기록할 수 있습니다.` |
| `AI 권고 {target}% → 매니저 조정 {modifyTarget}%` | `Supervisor 권고 {target}% → 매니저 조정 {modifyTarget}%` |
| placeholder: `예: AI 권고보다 보수적으로, OSP 발표 직후 확정 예정` | `예: Supervisor 권고보다 보수적으로, OSP 발표 직후 확정 예정` |
| DecisionChainPanel step: `AI 권고 생성` / sub: `Mission Plan Agent · ...` | `Supervisor 권고 생성` / sub: `Mission Plan (FMA) · ...` |

### `frontend/src/components/SimilarPastWidget.tsx`
| Before | After |
|---|---|
| `... 변동, AI 추천을 따랐다면 평균 ...` | `... 변동, Supervisor 권고를 따랐다면 평균 ...` |

### `frontend/src/pages/AskPage.tsx`
| Before | After |
|---|---|
| EXAMPLES_GENERIC[1] preview: `... Term 비중 75%로 hedge한 케이스 절감 효과 유의` | `... Term 비중 75%로 방어한 case 절감 효과 유의` |
| EXAMPLES_CASE_BOUND[0] preview: `Pattern Score + ... structured + document evidence 종합 — Supervisor가 case open 결정한 이유` | `위기 강도 + 핵심 시그널 + 구조화 데이터 + 문서 근거 종합 — Supervisor가 case 개시한 이유` |
| EXAMPLES_CASE_BOUND[2] text: `structured 데이터와 document evidence가 충돌하나?` | `구조화 데이터와 문서 근거가 충돌하나?` |
| EXAMPLES_CASE_BOUND[2] preview: `Genie (가격/재고/환율) vs Knowledge (OPEC 보고 톤) ...` | `Genie (가격/재고/환율) vs Knowledge Assistant (OPEC 보고 톤) ...` |
| EXAMPLES_CASE_BOUND[3] preview: `Pattern Score ±10 zone 7년 backtest analog 4-7건 + 그때 AI 권고 적중률` | `위기 강도 ±1 zone 7년 backtest analog 4-7건 + 그때 Supervisor 권고 적중률` |
| EXAMPLES_CASE_BOUND[4] text: `approve보다 keep watching이 더 나은 이유는?` | `지금 채택하기보다 모니터링이 더 나은 이유는?` |
| EXAMPLES_CASE_BOUND[4] preview: `현재 confidence 자신감 + monitoring 트리거 조건 + 다음 발표 D-N 비교` | `현재 confidence + 모니터링 트리거 조건 + 다음 발표 D-N 비교` |
| Case context badge: `Pattern Score {N.toFixed(0)} · 긴급도 ...` | `위기 강도 {N/10}/10 · 긴급도 ...` |
| Enriched context prefix: `AI 추천 적중률 ...%,` | `Supervisor 권고 적중률 ...%,` |
| Input hint: `자연어 질의는 Multi-Agent를 통해 응답됩니다` | `자연어 질의는 Agent Bricks Supervisor가 sub-agent를 라우팅해 응답합니다` |
| Pending spinner: `Multi-Agent가 분석 중...` | `Supervisor가 sub-agent 호출 중...` |

### `frontend/src/pages/MarketDataPage.tsx`
| Before | After |
|---|---|
| `Pattern Score 7년 시계열` / subtitle `... current case의 historical 위치` | `위기 신호 점수 7년 시계열` / `... 현재 case의 과거 위치` |

### `frontend/src/components/TopBar.tsx`
| Before | After |
|---|---|
| `<KpiChip label="진행 임무" ...>` | `<KpiChip label="진행 case" ...>` |
| title: `Slack에서도 임무 처리 가능` | `Slack에서도 case 처리 가능` |

### `frontend/src/components/Glossary.tsx`
| Before | After |
|---|---|
| CONFIDENCE_SCORE label `AI 자신감` / def `AI 권고의 자신감 (0~100). 시그널 cross-validation + ...` | label `권고 자신감` / def `Supervisor 권고의 자신감 (0~100). 시그널 교차검증 + ...` |
| Footer: `... 양방향 Mission (위기+기회).` | `... 양방향 case (위기+기회).` |

### `frontend/src/components/BacktestTimeSlider.tsx`
| Before | After |
|---|---|
| `과거 시점에서 AI 권고와 실제 결과를 비교합니다` | `과거 시점에서 Supervisor 권고와 실제 결과를 비교합니다` |
| `AI 권고 (그 날)` (column label) | `Supervisor 권고 (그 날)` |

### `frontend/src/components/Sidebar.tsx`
| Before | After |
|---|---|
| `{ to: "/missions", label: "Case File", desc: "결정 기록 + revision" }` | `desc: "결정 기록 + 재편"` |

---

## §3. 변경하지 않은 것 (의도된 디자인으로 판단)

| 위치 | 이유 |
|---|---|
| `Mission`, `mission_id`, `MissionType`, `useMissionsActive` 등 코드 식별자 | 사용자 정책: 코드 식별자 rename 금지 |
| Sidebar tab labels (`Decision Room` / `Market Watch` / `Investigation` / `Case File`) | codex P0 4-tab IA, 영문 overline 디자인 의도 |
| 4기능 영문명 (`Apps`, `Lakebase`, `Genie`, `Agent Bricks`, `Knowledge Assistant`) | 사용자 정책 |
| `Term`, `Spot` | 업계 표준 영문 (사용자 D-15 결정) |
| `위험방어` / `기회포착` | mission_type 한글 라벨 표준 |
| `Supervisor`, `Mission Plan (FMA)`, `mission_plan_advice (UC Func)`, `weighted_signal (UC Func)` | 정직 narrative 표기 (Agent Bricks 라고 부르지 않음) |
| SuggestedNextActions 영문 label (`Approve Draft`, `Adjust Draft`, `Dismiss Case`, `Keep Watching`, `Ask for More Evidence`, `Re-check Later`) | codex P0 "6 agentic options" narrative 의도 (description은 한국어) |
| MultiAgentTrace.tsx (dead component, import 없음) | Surgical Changes 원칙 — 사용처 없는 컴포넌트 건드리지 않음 |
| SimulationScenarios.tsx (dead component) | 동일 |
| 영문 변수/함수/타입/JSX 주석 | non-user-visible |
| AskPage enriched LLM context의 `Pattern Score: ${N}` 라벨 | LLM 입력이라 보존 (모델 routing 영향) |
| `mission_id={caseId}` 같은 case 매핑 텍스트 (error fallback) | 사용자가 디버깅용 마커로 의도한 것으로 추정 (이미 case_id 변수명) |
| Bidirectional3Zone "양방향 신호 강도" / SignalContribution "신호 기여도" / NewsTopList / OpecCitation / TimeHorizonBreakdown 등 한국어 자연스러운 문구 | 변경 불필요 |

---

## §4. 사용자에게 확인 요청 (애매한 항목)

1. **EXAMPLES_GENERIC[3] preview `위기 강도 10/10 + 호르무즈 신호 누적 → Brent 130 시나리오 580억 절감 가능 (보수적)`**: 시나리오 §6.3 anchor와 일치하는 fixed copy인지 확인 필요. 그대로 유지함.

2. **AskPage 응답 `source === "live"` chip 라벨 `"실시간 응답"` / `"캐시된 응답"`**: 정직성 OK. 그대로 유지.

3. **MissionSplitBar "현재 운영 비중" vs "Supervisor 권고 비중"**: 권고 비중이 "AI" → "Supervisor"로 바뀌면서 "신호 추정"이 약해질 수 있음. 사용자가 다른 표기 (e.g., "권고안 비중", "검토안 비중") 선호 시 일괄 교체 가능.

4. **TopBar `"진행 case"`**: "진행 중인 case"가 더 자연스러울 수 있으나 공간 제약상 "진행 case"로 통일. KpiChip 폭 보존 우선.

5. **Glossary CONFIDENCE_SCORE `권고 자신감`**: "권고 자신감"이 한국어로 다소 어색할 수 있음. "권고 신뢰도"가 더 자연스러울 가능성. 사용자 결정 요청.

6. **MultiAgentTrace.tsx / SimulationScenarios.tsx (dead code)**: import 없음 확인. 별도 cleanup spawn task 가능하나, 현재 패스 범위 외라 건드리지 않음.

---

## §5. 검증

- `npx tsc --noEmit` 통과
- `git diff --stat`: 9 files / +34 -34
- 변경된 텍스트 모두 user-visible (코드 식별자 변경 0건)
