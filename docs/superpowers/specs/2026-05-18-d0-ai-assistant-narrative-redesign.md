# Discovery "AI Assistant First" Narrative Redesign — D-0

> 작성: 2026-05-18 D-0
> 목적: Discovery 12 section "data dump" 비판 → "AI assistant가 살아 일하는" narrative scroll
> Scope: **디자인 개선 + demo flow** (implementation 디테일은 형욱님 자유도)
> Supersedes: `2026-05-18-frontend-redesign-spec.md` (정적 5 cards 접근, same day evolve)

---

## 1. 컨셉

작년 APJ 1등 Puma "Beyond dashboards toward actionable intelligence" 패턴 정합.

**Discovery는 dashboard가 아니라 결정 narrative**:
- 평시 dashboard 12 section 균등 무게 → **Hero sticky + 5 super-section narrative scroll**
- 정적 데이터 표시 → **AI agent가 trigger되고 살아 morph하는 reactive 화면**
- 영문 잔재 → **한글 일괄** (위험방어/기회포착/장기계약/즉시구매 등 이전 spec §2 retain)

5 결정 픽 (brainstorming):

| D | 결정 |
|---|---|
| D1 컨셉 | Recommendation-first (Puma mirror) |
| D2 Hero h1 | Hybrid 명령 h1 + 추론 subhead |
| D3 layout | Hero sticky + Narrative scroll |
| D4 grouping | 5 super-section (12 subsection all kept) |
| D5 wow | Multi-Agent live trace (§3) |

---

## 2. Page architecture

```
┌────────────────────────────────────────────────────────────┐
│ STICKY HERO BAND (~280px, max-w-7xl, backdrop-blur)         │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ Crude Compass                  [ trigger badge ]          ││
│ │                                                            ││
│ │ 오늘 두바이 장기계약 비중 75%로 상향   ← h1 (mode-aware)   ││
│ │ 호르무즈 긴장↑ + spread↓ → 60%→75% 사전 방어 권고         ││
│ │                                                            ││
│ │ 신뢰도 91%  ·  pattern_score 78  ·  [ HEDGE 78 ]         ││
│ └──────────────────────────────────────────────────────────┘│
├────────────────────────────────────────────────────────────┤
│ NARRATIVE SCROLL · 5 super-sections                         │
│                                                              │
│ §1. 오늘 결정 (Hero detail expand)                          │
│ §2. 왜 이 결정인가 (근거)                                    │
│ §3. AI가 어떻게 추론했나 (★ wow anchor)                     │
│ §4. 무엇을 할까 (액션)                                       │
│ §5. 다른 가능성은 (대안)                                     │
│                                                              │
│ [left rail] 5 dot scroll milestone (현재 읽는 곳 차오름)     │
└────────────────────────────────────────────────────────────┘
```

- Sticky band: `position: sticky; top: 0; z-index: 50` (lg breakpoint only)
- Scroll milestone rail: fixed left, 5 dot vertical
- `scroll-snap-type: y proximity` super-section heading 락온

**Typography hierarchy** (Pretendard Variable):

| Element | Size | Weight | Color |
|---|---|---|---|
| Hero h1 | 56px / 48px | semibold | mode-aware |
| Hero subhead | 16px | regular | ink-2 |
| Hero meta | 14px mono | regular | ink-3 |
| Super-section heading | 32px | semibold | ink-1 |
| "§N" prefix | 14px mono | regular | ink-3 |
| Body | 14-16px | regular | ink-1 |

---

## 3. Components — 5 super-section × 12 subsection

```
§1. 결정 (Hero sticky · ~280px)
├─ Trigger badge        [12. last_refresh]
├─ h1 mode-aware        [1. hero]
├─ Subhead 추론 chain   [1. hero]
└─ Meta strip           [2. bidirectional mini chip]

§2. 왜 이 결정인가 (근거)
├─ Signal contribution 30d   [4. signal_contribution]
├─ Pre-emptive momentum      [5. pre_emptive_momentum]
└─ Signal events feed (live) [10. signal_events_feed]

§3. AI가 어떻게 추론했나 (★ wow)
├─ "지금 다시 분석" button → live trace start
├─ Multi-Agent live trace    [9. supervisor]
├─ Bidirectional Pattern viz [2. bidirectional full]
└─ Why? reasoning summary    [11. why_panel]

§4. 무엇을 할까 (액션)
├─ Mission proposals card    [3. mission_cards]
└─ Decision history timeline [7. decision_history · Lakebase]

§5. 다른 가능성은 (대안)
├─ What-if sensitivity slider [6. what_if (현재 시나리오 조작)]
└─ Genie ask box (자연어 Q&A) [8. genie]
```

**Cut된 것 없음** — 12개 다 살아있음. 묶음/위치만 재배치.

**Genie 두 entry point**: §3 trace 안 sub-step (automatic) + §5 직접 입력 카드 (interactive).

**Bidirectional Pattern 두 표현**: §1 mini chip ("HEDGE 78") + §3 full viz (양방향 bar + 1-line reasoning).

**Backtest 슬라이더는 What-If page** (`/whatif`, 시나리오 §13 retain). Discovery §5는 sensitivity slider (현재 시나리오 조작)만.

**Other pages (minimal touch)**:
- Missions (`/missions`): 한글화 sweep, 구조 retain
- What-If (`/whatif`): 한글화 sweep + Hero 1-line narrative anchor
- Sidebar: 한글화 + WebSocket connecting indicator hide (silent)

---

## 4. Hero anatomy

### 4.1 Trigger badge (top-right)

매니저가 "AI agent가 살아있다"를 인지하는 핵심 단서. 4 variants:

| trigger | bg | text color | dot | wording |
|---|---|---|---|---|
| daily_cron | line-1 | ink-3 | (없음) | `06:30 정기 갱신 · 12분 전` |
| price_spike | crisis-50 | crisis-700 | crisis-500 pulse | `● WTI 5% spike 감지 · 재계산 중` |
| manual_query | opportunity-50 | opportunity-700 | opportunity-500 pulse | `● 매니저 요청 · Multi-Agent 추론 중` |
| manual_recommend | opportunity-50 | opportunity-700 | (정적) | `● 수동 재호출 완료 · 1분 전` |

Pulse: `opacity 1 → 0.4 → 1` 1.2s ease-in-out infinite.

### 4.2 h1 mode-aware (실제 데이터 align, fictional quantity 금지)

| Mode | Template | 실예 | h1 color |
|---|---|---|---|
| HEDGE | `오늘 {crude} 장기계약 비중 {prev}% → {next}%` | 오늘 두바이 장기계약 비중 60% → 75% | ink-1 |
| OPPORTUNITY | `오늘 {crude} 즉시구매 비중 {prev}% → {next}%` | 오늘 WTI 즉시구매 비중 10% → 30% | opportunity-800 |
| STABLE | `오늘은 큰 신호 없음, 통상 운영` (고정) | (동일) | ink-2 |

mission table의 `mission_type` + `term_pct/spot_pct` 변화 기반. "5만 배럴" 같은 fictional quantity 만들지 않음.

### 4.3 Subhead 추론 chain

```
{top signal 1} ↑ + {top signal 2} ↓  →  {action narrative}
```

- top 2 signal: `gold.signal_contribution_30d` ABS share 상위 2
- ↑/↓: direction (bullish/bearish)
- action: mission_type → 한글 ("사전 방어 권고" / "기회 매수 권고" / "관망 권고")

예: `호르무즈 긴장↑ + 두바이 spread↓  →  60%→75% 사전 방어 권고`

### 4.4 Meta strip (mono 14px)

```
신뢰도 91%   ·   pattern_score 78   ·   [ HEDGE 78 ]
```

- 신뢰도: `formatConfidence()` — 99.5+ → "95+%" clamp (이미 utils.ts)
- pattern_score: `formatRoundedScore()` — 정수 round
- mode chip: pill, mode-aware color

### 4.5 Mode-aware morph

Hero band 자체 bg는 panel(white) 고정 — **morph는 typography/chip에서만**. 산만함 회피.

WebSocket `pattern.changed` / `reactive.alert` / `mission.proposed` 수신 시 hero state invalidate → mode 전환 시 h1 색·subhead·chip이 fade morph (200ms).

---

## 5. Wow anchor — §3 Multi-Agent live trace

**Trigger**: 매니저가 "지금 다시 분석" 클릭 → Supervisor query 호출 → 3 sub-agent fan-out → trace tree가 §3에 실시간 unfold.

### 5.1 Idle state (page load 시)

```
§3. AI가 어떻게 추론했나
────────────────────────────────────────────
직전 분석: 06:30 정기 갱신 (mission #346)        [ 지금 다시 분석 ]

▸ Supervisor → 3 sub-agents · 8.6s · mission #346 제안   [trace 펼치기 ↓]
```

### 5.2 Running state (button click 직후)

```
● Supervisor 시작                                       0.4s
  ├─ ● Genie Space 호출 중...
  │     "WTI/두바이 30일 평균 대비 spike 여부, EIA 재고 변화"
  │     └─ ✓ WTI +5.2%, 재고 -3.1MB                    2.1s
  ├─ ● Knowledge Assistant 호출 중...
  │     "호르무즈 해협 긴장 관련 기사 분석"
  │     └─ ✓ 7건 retrieve, 평균 tone -0.82             1.8s
  └─ ● Mission Plan FMA 호출 중...
        입력: pattern_score=78, bullish=4, bearish=1
        └─ ✓ 결정: HEDGE pivot 60% → 75%               4.3s
────────────────────────────────────────────────
✓ 8.6s · 새 mission #347 제안됨   [§4 Mission proposals ↓]
```

### 5.3 Visual tokens

| Element | Style |
|---|---|
| `●` running | crisis-500 · 6px · pulse 1.2s infinite |
| `✓` completed | opportunity-600 · 14px · solid |
| Agent name | 16px · semibold · ink-1 |
| Query string | 13px mono · italic · ink-3 · indent 24px |
| Response | 14px · ink-1 · indent 24px |
| Elapsed time | 12px mono · ink-3 · right-aligned |
| Tree indent | 24px per level, line-2 vertical guide |
| Footer success | opportunity-700 · 14px medium |

(아이콘 자제 — `●` `✓` `└─` `├─` ASCII/Unicode만)

### 5.4 Bidirectional Pattern viz (§3 trace 아래)

```
HEDGE  ████████████████░░░░  78
                            ↑ 현재 mode
OPP    █████░░░░░░░░░░░░░░░  22
STABLE ░░░░░░░░░░░░░░░░░░░░   0

신호 5개 중 bullish 4, bearish 1 → HEDGE 압도
```

### 5.5 Why? reasoning summary (§3 footer)

trace 완료 후 자동 생성 (LLM narrative_summary):

```
> 호르무즈 긴장 7건 (tone -0.82) + WTI spike 5.2% + EIA 재고 -3.1MB
  복합 충격으로 공급 리스크 우세. 두바이 장기계약 75%로 상향,
  단기 변동성 헷지 권고.
```

---

## 6. Demo flow — 6-act 240s

5축 평가 anchor + 시나리오 §14 Phase 매핑:

| Act | 시간 | Trigger | 시나리오 §14 | 5축 anchor |
|---|---|---|---|---|
| 1. 평시 진입 | 0:00–0:30 | page load · daily_curation 결과 | Phase 3 | Storytelling, Business |
| 2. 근거 확인 | 0:30–1:00 | scroll | Phase 3 | UX, Technical (Lakebase silver) |
| 3. 분석 재요청 (★) | 1:00–2:00 | click "지금 다시 분석" · Supervisor live trace | Phase 4 | **Technical+Creativity+Storytelling** |
| 4. 결과 반영 | 2:00–2:30 | `mission.proposed` event | Phase 4 (Slack 동기화) | Technical (Lakebase persistence), UX |
| 5. Bidirectional Pivot | 2:30–3:15 | `demo-spike` POST: bearish cluster (휴전+SPR+China PMI+VLCC+재고↑) | Phase 6 (위기→기회) | Creativity, Storytelling |
| 6. What-if + 마무리 | 3:15–4:00 | §5 sensitivity slider + Genie 1턴 | Phase 5 + Phase 7 | UX, Business value |

(영상 5분 중 Discovery surface 4분, 나머지 1분은 §14 Phase 1-2 opening + Phase 7 평시 narrative)

### 6.1 Camera focus map (영상 녹화 가이드)

```
0:00 ─── [HERO]     ── 06:30 갱신 정적 hero
0:15 ─── [HERO+§1]  ── eyebrow → h1 → subhead → meta 순으로 zoom
0:30 ─── [§2]       ── scroll to signal contribution
0:45 ─── [§2]       ── pre-emptive momentum sparkline
1:00 ─── [§3]       ── click + trace tree unfold (CLOSE-UP)
1:30 ─── [§3]       ── trace tree pulse 애니메이션 (FRAME RATE 핵심)
2:00 ─── [HERO+§4]  ── hero morph + mission card slide-in 동시 capture
2:30 ─── [HERO]     ── toast + badge 빨간 pulse (split-screen with §3)
3:15 ─── [§5]       ── slider grid + score live update
3:50 ─── [HERO]     ── 최종 화면 fade out
```

### 6.2 Narrator 대본

```
[Act 1] 정유사 매니저는 매일 아침, 어제까지의 시그널을 종합한 오늘 결정을 봅니다.
        호르무즈에서 긴장이 높아졌어요. 두바이 spread도 좁아졌고요.
        AI는 이걸 보고 — 장기계약을 60%에서 75%로 올리라고 권합니다.

[Act 2] 왜 그런지 — 한눈에. 시그널 기여도, 30일 추세, 실시간 이벤트.
        이건 dashboard가 아니라 결정 근거의 reasoning trace예요.

[Act 3] 그런데 매니저는 한 번 더 묻고 싶어요.
        클릭. Supervisor가 깨어나서 3개 sub-agent를 동시에 호출합니다.
        Genie가 데이터를 캐고, Knowledge Assistant가 뉴스를 읽고,
        Mission Plan FMA가 판단합니다. 8.6초. 새로운 결정.

[Act 4] 결정은 Lakebase에 즉시 기록되고, 다음 분석 때 history로 활용됩니다.
        AI는 한 번 결정하고 끝나는 게 아니에요. 결정의 outcome을 추적합니다.

[Act 5] 그리고 시장은 기다리지 않죠. 방금 — 휴전 임박 보도, SPR 방출, 중국 PMI 49.2.
        bearish signal 5건이 5분 안에 누적됐고, AI agent가 알아서 재계산을 시작합니다.
        Pattern Score 78에서 38로. mode가 HEDGE에서 OPPORTUNITY로 pivot.
        매니저는 알람만 받습니다 — 단일 mission이 양방향으로 살아있다는 증거입니다.

[Act 6] 마지막으로 — AI는 도구입니다. 매니저가 직접 시나리오를 돌려볼 수 있어요.
        '호르무즈가 더 악화되면?' 슬라이더 한 번에 다시 계산됩니다.
        궁극의 결정자는 사람이고, AI는 그 사람을 매주, 매시간 함께합니다.
        — 일회성 위기 대응이 아니라, 일상의 AI assistant.
```

### 6.3 시연 안전 장치

| Risk | Mitigation |
|---|---|
| Supervisor query 지연/timeout | 직전 성공 trace cache replay (visual 동일, "캐시" badge만 추가) |
| SSE 연결 끊김 | WebSocket fallback (mission.* 채널 재활용) |
| Genie 응답 깨짐 | 4-tier canned fallback도 trace 단계에 그대로 노출 |
| demo-spike 미동작 | §5 slider 직접 조작으로 동일 morph 효과 |
| WebSocket 끊김 | hero 우측 silent dot (alarming 안 함) + 10s polling fallback |
| Lakebase 일시 불가 | in-memory store 즉시 표시 + "동기화 대기 중" 미니 표기 |

---

**End of spec.**
