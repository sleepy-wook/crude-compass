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
    "best_case_label": <KRW억 number>,
    "base_case_label": <number>,
    "worst_case_label": <number>
  },
  "urgency": "optional" | "default" | "urgent",
  "pattern_score": <0-100>,
  "confidence_score": <0-100, source 다양성/cross-validation 기반>,
  "target_pct": <e.g. 70>,
  "duration_days": 28
}
```

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
JSON만 반환. 코드 블록(```)도, explanation도 No. 위 schema 정확히 따를 것."""


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

    user_msg = f"""## Current state

**Pattern Score**: {input_data.pattern_score:.1f}
- bullish_score: {input_data.bullish_score:.1f}
- bearish_score: {input_data.bearish_score:.1f}
- cross_val_bonus: {input_data.cross_val_bonus:.1f}
- signal_count_90d: {input_data.signal_count_90d}

## Market Context (가격·환율·헤드라인)
{_format_market_context(input_data.market_context)}

## Top signals (last 90d, sorted by importance desc)
{_format_signals(input_data.top_signals)}

## Active Mission
{_format_active_mission(input_data.active_mission)}{constraint_note}

→ Recommend action (new_mission / pivot / pause / abort / continue) per Lifecycle rules.
   Consider price level, spread, FX, headlines together — not just signal score.
   Return JSON only."""

    try:
        resp = w.serving_endpoints.query(
            name=LLM_ENDPOINT,
            messages=[
                ChatMessage(role=ChatMessageRole.SYSTEM, content=SYSTEM_PROMPT + "\n\n" + FEW_SHOT_EXAMPLES),
                ChatMessage(role=ChatMessageRole.USER, content=user_msg),
            ],
            max_tokens=800,
            temperature=0.0,
        )
        content = resp.choices[0].message.content if resp.choices else "{}"
        content = _strip_markdown(content)
        data = json.loads(content)
        return MissionPlanOutput.model_validate(data)
    except Exception as e:
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        logger.error("Mission Plan Agent failed: %s: %s", type(e).__name__, e)
        logger.error("traceback: %s", traceback.format_exc())
        return None
