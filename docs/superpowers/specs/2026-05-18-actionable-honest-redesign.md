# Actionable Recommendations + Honest Simulation — D-4 redesign

> 작성: 2026-05-18 D-4 (마감 5/22)
> 목적: Databricks Building Intelligent Apps Hackathon 2026 5축 평가 중 **Business Applicability + Data Storytelling** 갭 메우기
> Track: Social Impact (Open Data) · Korean track
> Scope: 실제 정유사 매니저가 daily 쓸 수 있는 도구로 transform

---

## 1. Why — 형욱님 마지막 push back ("실제 도움 X")

마지막 솔직 평가 7개 critical issue 중 **D-4 안에 메울 수 있는 2개**:

| 갭 | 5축 매핑 | 현재 문제 |
|---|---|---|
| 권고 추상 (Term 60→75%) | Business Applicability 🔴 | 어떤 supplier × 어떤 cargo × 언제 — 추가 분석 필요. 결정 가속 X |
| 시뮬레이션 fake (Brent_130=410억) | Data Storytelling 🔴 | 가정 explicit X, 신뢰구간 X, "왜 410?" 답 없음 |

나머지 5개 (시그널→행동 chain, cycle 미스, Backtest 의심 등)는 Phase 2.

---

## 2. 심사 기준 매핑 (5 × 20% 각)

| 기준 | 현재 | 이 spec 후 |
|---|---|---|
| Business Applicability | 🔴 추상 | 🟢 ARAMCO/ADNOC supplier mix + cycle label |
| Creativity & Innovation | 🟢 Bidirectional + Multi-Agent | 🟢 keep |
| UX & Insights | 🟢 3-page + KPI | 🟢 + 권고 카드 + 3 scenarios |
| Technical Capability | 🟡 Apps+Genie+Lakebase+Agent ✓ | 🟡 (Sub-C stretch면 🟢 MLflow 추가) |
| Data Storytelling | 🔴 시뮬 fake | 🟢 가정 explicit + Best/Likely/Worst |

→ A+B 메우면 5축 중 **3개 🔴/🟡 → 🟢**.

---

## 3. Brainstorming 결정 (D1-D3)

| D | 결정 | 픽 |
|---|---|---|
| D1 | Invest 우선순위 | **A+B 먼저** (권고 구체 + 시뮬 정직) |
| D2 | 권고 구체 수준 | **Term/Spot + supplier mix template + 시연 example disclosure** |
| D3 | 시뮬 정직 수준 | **Best/Likely/Worst 3 scenarios + 가정 explicit** |

---

## 4. Sub-project A — Actionable Recommendations

### 4.1 시나리오 정합 — K-Petroleum 페르소나 확장 (KNOC 2024 통계 정합)

시나리오 §4 K-Petroleum baseline:
- 정제 capacity 80만 b/d (한국 정유 4사 평균)
- baseline Term 60% : Spot 40% (대한석유협회 산업 평균)

이 spec 추가 — **2024 KNOC 통계 기반 supplier list**:

| 순위 | Supplier | 2024 비중 | Grade | 비고 |
|---|---|---|---|---|
| 1 | **Saudi (ARAMCO)** | 32% (3.3억 배럴) | Arab Light | 월간 OSP 발표 |
| 2 | **미국 (US)** | **16.4%** (1.7억) | WTI / Bakken / Eagle Ford | 2022→2024 13% → 16% (증가) |
| 3 | **UAE (ADNOC)** | 14% (1.4억) | Murban | YoY +28% (급증) |
| 4 | Kuwait (KOC) | Top 5 | Kuwait Export | Term 중심 |
| 5 | Iraq (KPC) | Top 5 | Basra Light | Term 중심 |
| — | Iran (NIOC) | 제재로 제외 | — | (현실 반영) |

**중동 의존도 72%** (2024 KNOC).

- **Cargo template**:
  - 1 VLCC = 2M bbl ≈ 4-5일 정제분
  - Term 계약 단위: 월간 fix volume + Saudi OSP floating
  - Spot cargo 단위: 1-2 VLCC

### 4.2 의사결정 cycle catalog (실제 정유사 일정 정합)

LLM이 현재 일자 + active mission 보고 자동 매핑:

| Cycle | 시점 | 행동 |
|---|---|---|
| **월간** | 월초 (Saudi Aramco OSP 발표) | 월간 가격 받아들임 (Term contract 안의 floating 가격) |
| **분기/연간** | 분기·연 갱신 | Term contract volume 분배 (ARAMCO/US/ADNOC/KOC/KPC 비중) |
| 분기 | 분기 시작 | VLCC charter (3-6개월) |
| 즉시 | spike alert | Pivot 검토 |

**Note**: Saudi OSP는 월간 발표 (주간 아님). Korea = Saudi 최대 Asia buyer 중 하나. OSP가 Iran/Kuwait/Iraq에도 benchmark.

권고 output에 `cycle` field — 매니저가 "이번 결정 cycle이 무엇" 5초 인지.

### 4.3 Backend — LLM prompt 확장

**MissionPlanInput에 supplier_universe 추가** (선택적):
```python
class SupplierInfo(BaseModel):
    name: str
    region: str          # "Saudi" / "UAE" / "Kuwait" / "Iraq"
    grade: str           # "Arab Light" / "Murban" / "Kuwait Export" / "Basra Light"
    role: str            # "Term 중심" / "Term+Spot"
    osp_cycle: str | None  # "수요일 발표" 등

# MissionPlanInput field 추가:
supplier_universe: list[SupplierInfo] = Field(default_factory=list)
current_date: str  # ISO date for cycle inference
```

**LLM SYSTEM_PROMPT 확장** — supplier mix + cycle 권고 가이드:
```
당신은 K-Petroleum (한국 가상 정유사, capacity 80만 b/d, baseline Term 60/Spot 40)의
원유 조달 의사결정 코파일럿입니다.

권고 output 형식:
1. cycle — 매니저의 이번 결정 시점 ("6월 Term 갱신 (월말)" 등)
2. headline — Term/Spot 비중 변화 (현재 keep)
3. supplier_mix — 어떤 supplier 추가 lock-in 권장 (시연 example)
   - ARAMCO Arab Light / ADNOC Murban / KOC Kuwait / KPC Basra Light 중
   - 각 supplier당 +N,000 b/d 명시
   - rationale (왜 이 supplier)
4. disclaimer (자동 포함) — "실제 매니저 OSP allocation 기반 결정"
```

**MissionPlanOutput에 추가 field**:
```python
class SupplierAllocation(BaseModel):
    supplier_name: str       # "ARAMCO Arab Light"
    delta_bpd: int           # +25_000
    rationale: str           # "Saudi OSP +$0.50 예상 + 호르무즈 우회"

class MissionPlanOutput(BaseModel):
    # 기존 fields...
    cycle: str | None = None           # "6월 Term 갱신 (월말)"
    supplier_mix: list[SupplierAllocation] = Field(default_factory=list)
```

### 4.4 Frontend — MissionHero / MissionsPage detail 확장

**MissionHero 추가 elements**:

```
┌─────────────────────────────────────────────┐
│ [위험방어]  [신규 권고]    6월 Term 갱신 (월말) │ ← cycle label 추가
│                                              │
│ 오늘 두바이 장기 비중 · 평시 60%             │
│ 60% → 75%                                   │
│                                              │
│ 호르무즈 긴장↑ + 두바이 spread↓ → 사전 방어  │
│                                              │
│ 위기 점수 78  ·  기간 28일                  │
│                                              │
│ ▾ Supplier 분배 (시연 example)              │
│   ┌──────────────────────────────────┐       │
│   │ ARAMCO Arab Light    +25,000 b/d │       │
│   │   Saudi OSP +$0.50 예상           │       │
│   │ ADNOC Murban         +10,000 b/d │       │
│   │   호르무즈 우회 회피 (UAE 직접)    │       │
│   │ 총 +35,000 b/d Term 추가          │       │
│   └──────────────────────────────────┘       │
│   📌 실제 분배는 매니저 OSP allocation 기반   │
│                                              │
│ [권고 채택] [거절] [세부 보기]               │
└─────────────────────────────────────────────┘
```

**Component 변경**:
- `MissionHero.tsx` — Supplier mix section 추가 (output.supplier_mix가 있을 때만)
- cycle label은 trigger badge 영역 또는 hero top
- "시연 example" disclaimer 명시

---

## 5. Sub-project B — Honest Simulation

### 5.1 가정 schema explicit

**기존 simulation_roi (제거 대상)**:
```python
# 추상적 절대값 — 가정 무
simulation_roi: dict[str, float]  # {"Brent_130_봉쇄": 410}
```

**신규 schemas**:
```python
class SimulationAssumptions(BaseModel):
    """시뮬레이션 가정 — 매니저가 보고 검증 가능."""
    scenario_label: str              # "봉쇄 30일" / "현재 추세" / "휴전 협상"
    brent_usd: float                 # Brent 가격 가정
    usd_krw: float                   # 환율 가정
    vlcc_freight_multiplier: float   # 운임 배수 (호르무즈 봉쇄 시 1.4 = +40%)
    duration_days: int               # 시뮬레이션 기간

class SimulationScenario(BaseModel):
    """시나리오별 outcome."""
    name: Literal["worst", "likely", "best"]
    label: str                       # "봉쇄 30일" 같은 narrative
    assumptions: SimulationAssumptions
    saving_pct: float                # ±%
    saving_krw_oku: float            # 절감액 (억원)
    confidence_note: str | None      # "기존 backtest n=298 적중률 75% 기반" 등
```

### 5.2 계산 로직 (Deterministic 공식)

LLM hallucination 회피 — backend가 계산:

```python
def compute_scenario(
    mission_type: Literal["HEDGE", "OPPORTUNITY"],
    target_pct: int,
    baseline_pct: int,        # K-Petroleum default: HEDGE=60, OPP=40
    capacity_bpd: int,         # 800_000
    duration_days: int,
    assumptions: SimulationAssumptions,
) -> SimulationScenario:
    """
    절감액 공식 (단순화):
    
    Term 비중 차이 × capacity × duration × (Brent_시나리오 - Brent_평시) × USD/KRW
    
    HEDGE면 Term 추가 lock-in이 cost saving (시나리오 가격 ↑ 시).
    OPPORTUNITY면 Spot 추가 매수가 cost saving (시나리오 가격 ↓ 시).
    """
    delta_pct = abs(target_pct - baseline_pct) / 100
    barrels_affected = capacity_bpd * duration_days * delta_pct
    brent_baseline = 89.0  # 5/18 기준 (env 또는 latest fetch 가능)
    price_delta = assumptions.brent_usd - brent_baseline
    saving_usd = barrels_affected * price_delta
    if mission_type == "OPPORTUNITY":
        saving_usd = -saving_usd  # OPP는 가격 ↓일 때 saving
    saving_krw = saving_usd * assumptions.usd_krw
    saving_oku = saving_krw / 100_000_000_00  # 원→억원
    saving_pct = (saving_krw / (capacity_bpd * duration_days * brent_baseline * assumptions.usd_krw)) * 100
    return SimulationScenario(...)
```

**현재 시장 baseline (2026-05-18 검증, web search)**:
- Brent: **$108-111** (5월 평균 $108.94, 4월 평균 $117.29 — 약세 진입)
- USD/KRW: **~1,500** (5/18 ~1,503)
- UBS forecast: end 2026 $90 → 2027 $85 (지속 약세)

**3 scenarios 자동 생성** (2026/5 시장 정합):
- **worst** (HEDGE 모드 가정) — 휴전 + UBS 약세 forecast 실현 (Brent $85, KRW 1,450)
- **likely** — 현재 추세 (Brent $100, KRW 1,480)
- **best** (HEDGE 모드 가정) — 호르무즈 재발 + 봉쇄 (Brent $135, KRW 1,550, 운임 +40%)

OPP mission이면 worst/best 방향 반대.

### 5.3 Frontend — ROI section 3 scenarios

**MissionHero ROI strip 재설계**:

```
┌─────────────────────────────────────────────┐
│ 예상 시나리오                                  │
│                                              │
│ ┌──────────┬──────────┬──────────┐           │
│ │ Worst    │ Likely   │ Best     │           │
│ │ 휴전+약세 │ 현재 추세 │ 봉쇄 재발 │           │
│ │          │          │          │           │
│ │  -180억  │  +80억   │  +520억  │           │
│ │          │          │          │           │
│ ├──────────┼──────────┼──────────┤           │
│ │ 가정:    │ 가정:    │ 가정:    │           │
│ │ Brent 85 │ Brent 100│ Brent 135│           │
│ │ KRW 1450 │ KRW 1480 │ KRW 1550 │           │
│ │ 운임 평균│ 운임 +5% │ 운임 +40%│           │
│ └──────────┴──────────┴──────────┘           │
│                                              │
│ 📌 신뢰구간 ±20% (backtest n=298 기반)        │
└─────────────────────────────────────────────┘
```

**Component**:
- `SimulationScenarios.tsx` 신규 component
- MissionHero 안에 embed (기존 simple ROI strip 대체)
- 각 scenario card에 가정 expand 가능

### 5.4 Backend endpoint 변경

기존 `simulation_roi: dict[str, float]` 그대로 유지 (backward compat).
신규 field `simulation_scenarios: list[SimulationScenario]` 추가.

Frontend는 신규 field 있으면 새 UI, 없으면 기존 simple ROI strip fallback.

---

## 6. Sub-project C (Stretch — D-3 남으면)

D-3 시점에 A+B 완료 + 영상 녹화 buffer 확보된 경우만 추가.

**우선순위 1: MLflow Backtest Tracking** (권장)
- `databricks-sdk` MLflow client로 backtest run logging
- Frontend `OpenDataBadge`에 "최신 run_id 4f8a..." + "재현 가능" badge
- 효과: Storytelling 강화 (백테스트 75% hit 의심 해소)
- 예상 작업: 2-3시간

**우선순위 2: Vector Search RAG** (대안)
- 호르무즈/제재/OPEC 관련 과거 뉴스 embeddings 인덱스
- Knowledge Assistant 강화 — Supervisor query 시 관련 뉴스 retrieve
- 효과: Technical wow factor
- 예상 작업: 4-5시간

**우선순위 3: AI/BI Dashboard embed**
- 6년 평시 가치 그래프 native dashboard로
- iframe embed
- 효과: BI feel 강화
- 예상 작업: 1-2시간 (Databricks workspace에서 dashboard 직접 setup)

D-3 시점 형욱님과 결정.

---

## 7. Implementation Phases

| Day | 작업 | 산출 |
|---|---|---|
| **D-4 (5/18)** | Spec 작성 + review | 이 문서 |
| **D-3 (5/19)** | Sub-project A: schemas + LLM prompt + MissionHero 카드 | LLM 권고에 supplier mix + cycle |
| **D-2 (5/20)** | Sub-project B: schemas + 계산 로직 + 3 scenarios UI | Best/Likely/Worst card |
| **D-1 (5/21)** | Sub-project C (stretch) + polish + 영상 녹화 시작 | MLflow tracking (선택) |
| **D-Day (5/22)** | 영상 마무리 + Devpost 제출 | 영상 5분 |

---

## 8. Success Criteria

1. **Mission 권고에 supplier mix 보임** — ARAMCO/ADNOC 같은 실제 supplier × b/d 명시
2. **Cycle label 자동** — "6월 Term 갱신 (월말)" 같은 매니저 mental model 라벨
3. **3 scenarios 카드** — Worst/Likely/Best 가정 explicit + 절감액 각각
4. **시연 example disclaimer** visible — 정직성 명시
5. **TS check + Vite build 통과**
6. **Backward compat** — supplier_mix 없는 mission도 정상 표시 (legacy in-memory mission)

---

## 9. Out of Scope (Phase 2 / Production roadmap)

- 실제 K-Petroleum portfolio 연동 (ERP/SAP)
- Broker portal 연동 (Clarkson/Braemar)
- 실제 supplier OSP feed (Bloomberg/Platts 대체)
- 매니저 수동 가정 변경 UI (Best/Worst slider)
- VLCC charter 권고 (현재는 Term 비중만)
- Cargo timing 권고 (월간 입찰 일정)
- 시그널 → cargo decision chain (호르무즈 burst → 운임 ↑ → cargo 앞당김)
- Backtest 가격 가정 정직성 (현재 평균 0.63% 절감 계산 검증)
- 신뢰구간 P10-P50-P90 (현재는 단순 Best/Likely/Worst label)

---

## 10. Open Questions (Implementation phase 결정)

1. **Supplier mix 계산 — LLM hallucination vs deterministic split rule?**
   - 현재 plan: LLM 자연어 generate (시그널 종합 따라 자연스럽게 ARAMCO/US/ADNOC 결정)
   - 위험: LLM이 매번 다른 split → 재현성 X
   - Mitigation: temperature=0.0 (이미) + few-shot examples로 stable
2. **3 scenarios 가정값 — backend deterministic vs LLM 생성?**
   - 현재 plan: Backend deterministic (수식 + 시나리오별 hardcoded 가정 range)
   - 매니저가 가정 수정 가능하면 더 좋지만 Phase 2
3. **Brent baseline — 어떻게 fetch?**
   - 현재 plan: latest `oil_prices_wide.brent_usd`에서 fetch (이미 `_fetch_market_context()` 있음)
   - 2026-05-18 검증 값: $108-111 (5월 평균 $108.94)

---

## 11. Verification Notes (web search 2026-05-18)

### 11.1 Supplier list (KNOC 2024 통계 정합)
- Saudi 32% (3.3억 배럴) — ARAMCO Arab Light, 1위
- 미국 16.4% (1.7억) — WTI/Bakken/Eagle Ford, 2022→2024 13% → 16% (증가 추세) — 2위
- UAE 14% (1.4억) — ADNOC Murban, YoY +28% — 3위
- 중동 의존도 72%

### 11.2 OSP cycle
- Saudi Aramco OSP **월간 발표** (월초)
- Asia 최대 buyer (9M b/d export benchmark)
- 한국 정유 4사 매월 가격 받아들임
- Iran/Kuwait/Iraq도 Saudi OSP benchmark 참조

### 11.3 시장 baseline (2026-05-18)
- Brent: $108-111 (5월 평균 $108.94, 4월 평균 $117.29 — **약세 진입**)
- USD/KRW: ~1,500 (5/18 ~1,503 — **원화 약세**)
- UBS forecast: end 2026 $90 → 2027 $85 (지속 약세)

### 11.4 Demo 시나리오 결정 — Mixed signal

2026/5 시장 실제 상태:
- **Brent 약세** (4월 $117 → 5월 $108, UBS $85 forecast) → **OPPORTUNITY 신호**
- **USD/KRW 약세** (1,500) → 수입비 ↑ → **HEDGE 신호**
- = **Mixed signal**

두 demo narrative 다 가능:
- **(A) 호르무즈 재발 demo** (HEDGE) — 시나리오 §14 기존 narrative. 가정에 "호르무즈 봉쇄 재발" 명시.
- **(B) 약세 진입 demo** (OPPORTUNITY) — 2026/5 실제 시장 100% 정합. 시나리오 §2 "Opportunity가 더 자주 가치" narrative와도 정합.

→ **시연 시 형욱님이 narrative 선택**. 두 가지 다 시연 가능하게 코드 구현.

---

**End of spec.**
