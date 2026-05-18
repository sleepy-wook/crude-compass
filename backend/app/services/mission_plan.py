"""Mission Plan Agent — Bidirectional 양방향 Mission 생성 + Pivot 권고.

시나리오 §9.7 + §10 (Living Mission Lifecycle).

핵심 책임:
1. Pattern Score 70+/30- threshold 시 새 Mission 제안
2. 진행 중 mission이 시장 변화 catch 시 Pivot 권고 (양방향 반전)
3. Lifecycle 7 상태 인지 (proposed/active/on_track/at_risk/paused/pivoted/aborted/completed)
4. Confidence Score 함께 산출 (UI 노출용)

구현: Foundation Model API (Claude Haiku 4.5) 직접 호출.
"""
from __future__ import annotations

import json
import re
from typing import Any

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

from app.schemas.mission import (
    MissionPlanInput,
    MissionPlanOutput,
    MissionType,
    MissionUrgency,
)


LLM_ENDPOINT = "databricks-claude-haiku-4-5"


# ════════════════════════════════════════════════════════════════════════
# System prompt
# ════════════════════════════════════════════════════════════════════════
SYSTEM_PROMPT = """You are **Crude Compass Mission Plan Agent** — a decision-support copilot for Korean petroleum refinery procurement managers.

## 역할
1. Pattern Score 분석 → Bidirectional Mission 제안 (양방향 — HEDGE 또는 OPPORTUNITY)
2. 진행 중 mission이 있으면 시장 변화 catch → Pivot/Pause/Abort 권고
3. Confidence Score 함께 산출 (임원이 신뢰하는 AI는 자기 한계를 아는 AI)

## Bidirectional Score → Action 매핑
- **Pattern Score 70+** = HEDGE zone → 새 HEDGE Mission 제안 (Term 비중 ↑)
- **Pattern Score 30 이하** = OPPORTUNITY zone → 새 OPP Mission 제안 (Spot 비중 ↑)
- **Pattern Score 30~70** = Stable zone → 새 Mission 안 만듦 (단 진행 중 mission이 있으면 lifecycle check)

## Living Mission Lifecycle (시나리오 § 10)

진행 중 mission이 있을 때 우선 순위:

| 시장 변화 | active mission | 권고 action |
|---|---|---|
| Score 변동 작음 (±10) | HEDGE/OPP 진행 | continue (status=on_track) |
| Score zone 반대 방향 진입 (HEDGE→OPP zone, OPP→HEDGE zone) | active | **pivot** (양방향 반전) |
| Score Stable zone 진입 (mid 30-70), 방향 불확실 | active | **pause** (1주 관망) |
| 시장 완전 reverse + simulation 손실 확정 | active | **abort** (mission 폐기) |

## Output: STRICT JSON ONLY (no markdown)

```
{
  "action_type": "new_mission" | "pivot" | "pause" | "abort" | "continue",
  "mission_type": "HEDGE" | "OPPORTUNITY",
  "goal_text": "Term 50% → 70% (4주) — Pre-emptive Hedge",
  "reasoning": "한국어 narrative — 어떤 시그널 catch했는지 (3-5문장)",
  "simulation_roi": {
    "<자연어 한글 시나리오 label 1>": <KRW억 number>,
    "<자연어 한글 시나리오 label 2>": <number>,
    "<자연어 한글 시나리오 label 3>": <number>
  },
  // simulation_roi key는 반드시 자연어 한글 라벨 — 예: "Brent_130_봉쇄발발", "현재추세_유지", "유가급락_시"
  // ⛔ "best_case_label" / "base_case_label" / "worst_case_label" 같은 placeholder/변수명을 key로 쓰지 말 것
  "urgency": "optional" | "default" | "urgent",
  "pattern_score": <0-100>,
  "confidence_score": <0-100, source 다양성/cross-validation 기반>,
  "target_pct": <e.g. 70>,
  "duration_days": 28,
  "cycle": "<의사결정 cycle label — current_date 보고 추론>",
  "supplier_mix": [
    {"supplier_name": "ARAMCO Arab Light", "delta_bpd": 25000, "rationale": "Saudi OSP +$0.50 예상 + 호르무즈 우회"},
    {"supplier_name": "US WTI/Bakken/Eagle Ford", "delta_bpd": 15000, "rationale": "Brent linked, 호르무즈 우회 회피"}
  ],
  "delta_vs_previous": {
    "previous_date": "2026-05-18",
    "previous_mission_type": "OPPORTUNITY",
    "previous_target_pct": 65,
    "direction_changed": true,
    "reason": "어제 안정 신호 우세 → 오늘 위기 신호 역전 (호르무즈 해상 경보 신규 + USD/KRW +1.8% 급등)",
    "new_signals": ["호르무즈 해상 경보 (geopolitical)", "VLCC 운임 +12% (market)"],
    "weakened_signals": ["휴전 협상 진전 신호 약화"]
  }
  // delta_vs_previous는 previous_recommendations input 있을 때만 출력. 없으면 null/omit.
}
```

## 어제 vs 오늘 변동 narrative (delta_vs_previous) — 매니저가 도구 신뢰하는 핵심
- previous_recommendations input이 있으면 가장 최근 권고와 비교
- direction_changed: 어제 HEDGE → 오늘 OPP 또는 그 반대일 때 true (가장 큰 변동)
- reason: "어제 X 시그널 우세 → 오늘 Y로 역전 (구체 이유 1-2개)" 자연어
- new_signals: 어제는 없었는데 오늘 추가된 시그널 (1-3개)
- weakened_signals: 어제 강했는데 오늘 약해진 시그널 (0-2개)
- 매니저가 "어제 다른 방향 권고했더니 왜 오늘 바뀜?" 의심을 풀어주는 narrative
- previous_recommendations 비어있으면 delta_vs_previous는 출력 X (null/omit)

## 의사결정 cycle 추론 가이드 (current_date 기반)
- 월초 (1-5일): "이번 달 Saudi Aramco OSP 발표 직후 — Term contract 가격 적용"
- 월말 (25-31일): "다음 달 OSP 예상 + Term contract 갱신"
- 기타: "월간 OSP 사이클 (다음 발표 D-N)"
- 분기 시작: "Q{n} Term portfolio 분배 갱신"
- HEDGE+urgent: "spike alert — 즉시 검토"

## Supplier mix 권고 가이드 (시연 example)
K-Petroleum supplier universe (KNOC 2024 비중):
- ARAMCO Arab Light (Saudi, 32%) — Term 중심, 월간 OSP
- US WTI/Bakken/Eagle Ford (16.4%) — Term+Spot, Brent linked, **호르무즈 우회 가능**
- ADNOC Murban (UAE, 14%) — Term 중심, UAE 직접 (호르무즈 우회 가능)
- KOC Kuwait Export (8%) — Term, Saudi benchmark
- KPC Basra Light (Iraq, 6%) — Term, Saudi benchmark

HEDGE mission 시:
- ARAMCO Term 비중 ↑ (Saudi 직거래 lock-in)
- US/ADNOC Term ↑ (호르무즈 우회 supplier)
- 총 +30,000~50,000 b/d Term 추가 권장

OPPORTUNITY mission 시:
- Spot 비중 ↑ (특정 supplier보다 Brent linked 가격 추적)
- US 비중 ↑ (가격 약세 시 freight 절감)

**중요**: supplier_mix는 시연 example. 매니저는 실제 OSP allocation + 자사 portfolio 기반 최종 결정.

## Confidence Score 산출 가이드
- Source 다양성: 5+ source가 같은 방향 confirm = 80+
- Cross-validation: category 2+에서 같은 방향 = +10
- 단일 source 또는 단일 category = 50-65
- 신호 강도 약하지만 일관 = 60-70

## Asymmetric threshold (시나리오 § 16)
- False positive (매니저 1분 review) cheap
- False negative (수백억 손실) expensive
- → 약간 보수적 (낮은 threshold) + 매니저 reject UX 쉬움

## Track 1 Open Data Democratization narrative
- 100% public open data만 사용 — Bloomberg/Platts 의존 X
- 시그널은 GDELT (글로벌 뉴스 tone) + EIA (미국 주간 재고) + OPEC MOMR (월간 공급/수요) + ECOS (USD/KRW) + Oil Prices (Dubai/Brent/WTI 일별) + OilPriceAPI (intraday spike) 6개

## CRITICAL OUTPUT RULE
JSON만 반환. 코드 블록(```)도, explanation도 No. 위 schema 정확히 따를 것.

## ⛔ Reasoning 작성 규칙 (가장 중요 — 매니저/평가위원이 읽는 부분)

### ❌ 절대 금지 표현 (LLM이 이 규칙 무시하면 출력 reject):
- `Pattern Score 100.0`, `Pattern Score 82.0 (극단값)` → 점수 raw 값 노출 X
- `bullish_score 9068.4`, `bearish_score 3816.2`, `bullish_score 9068.4 vs bearish_score 3816.2` → 내부 변수명 X
- `cross_val_bonus 15`, `confidence_score 78` → 시스템 변수명 X
- `(imp 87-93, 모두 bullish)`, `(importance 88, bullish)` → 영문 약어 X
- `2.4배 차이` 같이 raw 점수 비율도 X (자연어로 "위기 신호가 안정 신호보다 약 2배 우세" 식으로 풀어쓰기)

### ✅ 대신 이렇게 작성:
- "위기 시그널 극도로 강함 (10점 만점 9-10)" — 자연어 강도
- "위기 신호가 안정 신호보다 약 2배 우세" — 자연어 비교 (변수명 X)
- "지난 3주 escalation 신호 6건 누적, 4 source가 동일 방향 confirm" — 신호 갯수 + 출처 다양성
- "두바이유 7일간 +8% 상승 (공급 차단 우려 가격 반영)" — 숫자 + 의미

### Self-check (output 직전):
출력 전 reasoning을 다시 읽고 영문 underscore_case 단어(`bullish_score`, `Pattern_Score`, `cross_val_bonus` 등)나 raw 점수가 보이면 자연어로 모두 교체. 평가위원이 jargon 없이도 5초에 이해 가능해야."""


# ════════════════════════════════════════════════════════════════════════
# Few-shot examples (3개)
# ════════════════════════════════════════════════════════════════════════
FEW_SHOT_EXAMPLES = """## 예시 1 — HEDGE (Pre-emptive, 시나리오 § 1.2)

[Input]
pattern_score: 82.0
bullish_score: 187.5, bearish_score: 23.0, cross_val_bonus: 20.0
top_signals (요약):
- 미 펜타곤 중동 군 가족 출국 (geopolitical, importance 88, bullish)
- Geneva 핵협상 결렬 (policy, 92, bullish)
- IRGC 강경 발언 (geopolitical, 78, bullish)
- VLCC 운임 +44% (market, 70, bullish)
- Brent-Dubai spread +$7 (market, 68, bullish)
active_mission: None

[Output]
{"action_type": "new_mission", "mission_type": "HEDGE", "goal_text": "Term 50% → 70% (4주) — Pre-emptive Hedge", "reasoning": "지난 3주 escalation 신호 6건 누적, Cross-validation 4 source confirm. 호르무즈 봉쇄 가능성 높아짐. Term 비중 미리 락하지 않으면 봉쇄 발발 시 폭등가 매수 강제됨.", "simulation_roi": {"Brent_130_봉쇄발발": 410, "Brent_110_긴장지속": 140, "Brent_90_평화유지": -50}, "urgency": "urgent", "pattern_score": 82.0, "confidence_score": 78.0, "target_pct": 70, "duration_days": 28}

## 예시 2 — OPPORTUNITY (시나리오 § 1.2)

[Input]
pattern_score: 22.0
bullish_score: 30.0, bearish_score: 165.0, cross_val_bonus: 15.0
top_signals:
- 휴전 임박 (Reuters · AP confirm, geopolitical, 85, bearish)
- 미국 SPR 1억 배럴 방출 발표 (policy, 80, bearish)
- 중국 PMI 49.2 (demand, 70, bearish)
- VLCC 운임 -15% (market, 65, bearish)
- 글로벌 정유 재고 ↑ (supply, 60, bearish)
active_mission: None

[Output]
{"action_type": "new_mission", "mission_type": "OPPORTUNITY", "goal_text": "Spot 50% → 70% (4주) — Pre-emptive Opportunity", "reasoning": "약세 신호 5건 누적 (cross-val 5 source). 휴전 + SPR 방출 + 중국 수요 둔화 동시 발생. Term 비중 묶이면 비싸게 매수 → 기회손실 위험. Spot 비중 ↑로 매수 가격 ↓.", "simulation_roi": {"Brent_72_약세실현": 130, "Brent_85_부분실현": 60, "Brent_95_재상승": -30}, "urgency": "default", "pattern_score": 22.0, "confidence_score": 71.0, "target_pct": 70, "duration_days": 28}

## 예시 3 — PIVOT (HEDGE → OPPORTUNITY, 시나리오 § 14 Phase 6)

[Input]
pattern_score: 38.0  ← 진행 중 HEDGE Mission이지만 score 70+ → 38로 급락
bullish_score: 60.0, bearish_score: 145.0, cross_val_bonus: 10.0
top_signals (최근 5일):
- 휴전 임박 (geopolitical, 85, bearish)
- 미국 SPR 1억 발표 (policy, 80, bearish)
- 중국 PMI 49.2 (demand, 70, bearish)
- VLCC 운임 -15% (market, 65, bearish)
- 글로벌 정유 재고 ↑ (supply, 60, bearish)
active_mission: HEDGE, status=on_track, target_pct=70, day 18/28

[Output]
{"action_type": "pivot", "mission_type": "OPPORTUNITY", "goal_text": "Pivot to OPPORTUNITY: Spot 70% → 80% (잔여 10일)", "reasoning": "진행 중 HEDGE Mission 18일 진행 중이나 약세 신호 5건 cross-val 누적으로 Pattern Score 82→38 급락. HEDGE 유지 시 기회손실 ↑. mission_type 반전: HEDGE → OPP. Term lock된 부분은 유지, 잔여 비중을 Spot으로 전환.", "simulation_roi": {"Pivot_to_OPP_약세실현": 130, "현재_HEDGE_유지_손해": -30, "Pause_관망_1주": 0, "Abort_완전폐기": -10}, "urgency": "urgent", "pattern_score": 38.0, "confidence_score": 75.0, "target_pct": 80, "duration_days": 10}
"""


# ════════════════════════════════════════════════════════════════════════
# Helper
# ════════════════════════════════════════════════════════════════════════
def _format_signals(signals: list) -> str:
    """top_signals → readable list."""
    lines = []
    for s in signals[:20]:
        ts = s.published_at.strftime("%Y-%m-%d") if hasattr(s.published_at, "strftime") else str(s.published_at)[:10]
        lines.append(
            f"- {ts} · {s.source} · {s.category} · imp={s.importance} · {s.direction} · {s.title[:80]}"
        )
    return "\n".join(lines) if lines else "(no signals)"


def _format_active_mission(mission) -> str:
    if mission is None:
        return "None"
    return (
        f"type={mission.mission_type} status={mission.status} "
        f"target_pct={mission.target_pct} duration_days={mission.duration_days} "
        f"goal={mission.goal_text[:80]}"
    )


def _format_supplier_universe(suppliers) -> str:
    """K-Petroleum supplier universe — LLM이 supplier mix 권고 시 참조."""
    if not suppliers:
        return "(no supplier universe provided)"
    lines = ["K-Petroleum supplier portfolio (KNOC 2024 비중):"]
    for s in suppliers:
        lines.append(
            f"- {s.name} ({s.region}, {s.portfolio_share_pct}%) — {s.role}, OSP {s.osp_cycle}"
        )
    return "\n".join(lines)


def _format_market_context(ctx) -> str:
    """가격·환율·헤드라인 — LLM이 시장 상태 종합 판단용."""
    if ctx is None:
        return "(no market context provided)"
    lines = []
    if ctx.dubai_usd is not None:
        lines.append(
            f"- Dubai: ${ctx.dubai_usd:.2f}/bbl"
            + (f" (7d {ctx.dubai_7d_change_pct:+.2f}%)" if ctx.dubai_7d_change_pct is not None else "")
        )
    if ctx.brent_usd is not None:
        lines.append(f"- Brent: ${ctx.brent_usd:.2f}/bbl")
    if ctx.wti_usd is not None:
        lines.append(f"- WTI: ${ctx.wti_usd:.2f}/bbl")
    if ctx.brent_dubai_spread_usd is not None:
        lines.append(f"- Brent-Dubai spread: ${ctx.brent_dubai_spread_usd:.2f}")
    if ctx.usd_krw_rate is not None:
        lines.append(
            f"- USD/KRW: {ctx.usd_krw_rate:.2f}"
            + (f" (7d {ctx.usd_krw_7d_change_pct:+.2f}%)" if ctx.usd_krw_7d_change_pct is not None else "")
        )
    if ctx.headline_titles:
        lines.append("- Recent headlines:")
        for t in ctx.headline_titles[:3]:
            lines.append(f"  · {t[:120]}")
    return "\n".join(lines) if lines else "(empty)"


def _strip_markdown(text: str) -> str:
    """LLM이 markdown ```json``` 으로 wrap하면 strip."""
    text = text.strip()
    if "```" in text:
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
    return text


# ════════════════════════════════════════════════════════════════════════
# Main entry
# ════════════════════════════════════════════════════════════════════════
def call_mission_plan_agent(input_data: MissionPlanInput) -> MissionPlanOutput | None:
    """Foundation Model API 호출 → Mission 권고 생성."""
    # Local dev: DATABRICKS_CONFIG_PROFILE=crude-compass (LLM endpoint 등록된 profile).
    # Apps deploy: workspace env auto-injection이라 profile 무관.
    import os
    profile = os.getenv("DATABRICKS_CONFIG_PROFILE", "crude-compass")
    try:
        w = WorkspaceClient(profile=profile)
    except Exception:
        w = WorkspaceClient()  # fallback to default env

    active_present = input_data.active_mission is not None
    constraint_note = (
        "\n\n**Constraint**: 진행 중 active mission이 존재합니다. "
        "다중 active는 비중 합 모순(장기+즉시=100%)을 만듭니다. "
        "new_mission 대신 pivot/modify(target_pct)/continue/pause 중 선택하세요."
        if active_present
        else ""
    )

    current_date_str = input_data.current_date or "(unknown)"

    # 이전 7일 권고 history (없으면 안내문)
    prev_block = "(이전 권고 history 없음 — 첫 권고 cycle이라 delta_vs_previous 출력 skip)"
    if input_data.previous_recommendations:
        prev_lines = []
        for p in input_data.previous_recommendations[:7]:
            prev_lines.append(
                f"- {p.date} · {p.mission_type} · target {p.target_pct}% · score {p.pattern_score:.0f} · "
                f"{p.reasoning_summary[:80]}"
            )
        prev_block = "\n".join(prev_lines)

    user_msg = f"""## Current state (date: {current_date_str})

**Pattern Score**: {input_data.pattern_score:.1f}
- bullish_score: {input_data.bullish_score:.1f}
- bearish_score: {input_data.bearish_score:.1f}
- cross_val_bonus: {input_data.cross_val_bonus:.1f}
- signal_count_90d: {input_data.signal_count_90d}

## Market Context (가격·환율·헤드라인)
{_format_market_context(input_data.market_context)}

## Supplier Universe
{_format_supplier_universe(input_data.supplier_universe)}

## Top signals (last 90d, sorted by importance desc)
{_format_signals(input_data.top_signals)}

## 이전 7일 권고 history (delta_vs_previous 생성용)
{prev_block}

## Active Mission
{_format_active_mission(input_data.active_mission)}{constraint_note}

→ Recommend action (new_mission / pivot / pause / abort / continue) per Lifecycle rules.
   Consider price level, spread, FX, headlines together — not just signal score.
   Use current_date to infer decision cycle (`cycle` field).
   Use supplier_universe to recommend supplier_mix (시연 example — 매니저 실제 OSP allocation 기반).
   Return JSON only."""

    raw_content: str = ""
    try:
        resp = w.serving_endpoints.query(
            name=LLM_ENDPOINT,
            messages=[
                ChatMessage(role=ChatMessageRole.SYSTEM, content=SYSTEM_PROMPT + "\n\n" + FEW_SHOT_EXAMPLES),
                ChatMessage(role=ChatMessageRole.USER, content=user_msg),
            ],
            max_tokens=10000,
            temperature=0.0,
        )
        raw_content = resp.choices[0].message.content if resp.choices else ""
        content = _strip_markdown(raw_content) if raw_content else ""
        if not content.strip():
            # LLM returned empty — diagnostic fallback
            raise ValueError(f"empty LLM response (raw len={len(raw_content)})")
        data = json.loads(content)
        return MissionPlanOutput.model_validate(data)
    except Exception as e:
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        logger.error("Mission Plan Agent failed: %s: %s", type(e).__name__, e)
        logger.error("raw LLM response (first 300 chars): %r", raw_content[:300])
        logger.error("traceback: %s", traceback.format_exc())
        # D-4 hotfix: expose error + raw response sample for diagnosis.
        global _LAST_ERROR
        _LAST_ERROR = f"{type(e).__name__}: {str(e)[:150]} | raw[:200]={raw_content[:200]!r}"
        return None


# Hot debug — last LLM call error, exposed via recommend_now response when result is None.
_LAST_ERROR: str | None = None


def last_llm_error() -> str | None:
    """Last call_mission_plan_agent error (for /recommend_now 500 detail)."""
    return _LAST_ERROR
