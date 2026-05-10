"""Mission Plan Agent test — 3 시나리오 검증 (Sprint 3 Day 1 task 3).

시나리오 § 1.2 + § 14 Phase 6 그대로:
1. HEDGE: Pattern Score 82, 호르무즈 pre-crisis
2. OPPORTUNITY: Pattern Score 22, 약세 5건 cross-val
3. PIVOT: HEDGE active 후 시장 reverse → Pivot to OPP

사용:
    cd backend
    DATABRICKS_CONFIG_PROFILE=crude-compass uv run python ../scripts/test_mission_plan_agent.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from uuid import uuid4

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except (AttributeError, OSError):
        pass

from app.schemas.mission import (
    Mission,
    MissionPlanInput,
    MissionStatus,
    MissionType,
    SignalContext,
)
from app.services.mission_plan import call_mission_plan_agent


# ════════════════════════════════════════════════════════════════════════
# 시나리오 1 — HEDGE Pre-emptive (시나리오 § 1.2)
# ════════════════════════════════════════════════════════════════════════
def test_hedge_pre_crisis() -> None:
    print("\n" + "=" * 70)
    print("Test 1 — HEDGE Pre-emptive (Pattern 82, 호르무즈 pre-crisis)")
    print("=" * 70)

    signals = [
        SignalContext(
            signal_id=str(uuid4()),
            published_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
            source="GDELT_hormuz",
            direction="bullish",
            importance=88,
            category="geopolitical",
            title="미 펜타곤 중동 군 가족 출국 명령",
        ),
        SignalContext(
            signal_id=str(uuid4()),
            published_at=datetime(2026, 1, 22, tzinfo=timezone.utc),
            source="GDELT_iran_sanctions",
            direction="bullish",
            importance=92,
            category="policy",
            title="Geneva 핵협상 결렬",
        ),
        SignalContext(
            signal_id=str(uuid4()),
            published_at=datetime(2026, 1, 30, tzinfo=timezone.utc),
            source="GDELT_hormuz",
            direction="bullish",
            importance=78,
            category="geopolitical",
            title="IRGC 강경 발언",
        ),
        SignalContext(
            signal_id=str(uuid4()),
            published_at=datetime(2026, 2, 5, tzinfo=timezone.utc),
            source="OilPriceAPI",
            direction="bullish",
            importance=70,
            category="market",
            title="VLCC 운임 +44%",
        ),
        SignalContext(
            signal_id=str(uuid4()),
            published_at=datetime(2026, 2, 10, tzinfo=timezone.utc),
            source="OilPriceAPI",
            direction="bullish",
            importance=68,
            category="market",
            title="Brent-Dubai spread +$7",
        ),
    ]

    input_data = MissionPlanInput(
        pattern_score=82.0,
        bullish_score=187.5,
        bearish_score=23.0,
        cross_val_bonus=20.0,
        signal_count_90d=47,
        top_signals=signals,
        active_mission=None,
    )

    result = call_mission_plan_agent(input_data)
    if result is None:
        print("  ❌ FAILED")
        return

    print(f"  action_type:      {result.action_type}")
    print(f"  mission_type:     {result.mission_type}")
    print(f"  goal:             {result.goal_text}")
    print(f"  pattern_score:    {result.pattern_score}")
    print(f"  confidence:       {result.confidence_score}")
    print(f"  urgency:          {result.urgency}")
    print(f"  target_pct:       {result.target_pct}")
    print(f"  reasoning:        {result.reasoning[:150]}...")
    print(f"  simulation_roi:   {result.simulation_roi}")

    # 검증
    assert result.action_type == "new_mission", f"Expected new_mission, got {result.action_type}"
    assert result.mission_type == MissionType.HEDGE, f"Expected HEDGE, got {result.mission_type}"
    print("  ✅ PASS — HEDGE Mission 정상 제안")


# ════════════════════════════════════════════════════════════════════════
# 시나리오 2 — OPPORTUNITY (시나리오 § 1.2)
# ════════════════════════════════════════════════════════════════════════
def test_opportunity() -> None:
    print("\n" + "=" * 70)
    print("Test 2 — OPPORTUNITY (Pattern 22, 약세 5건 cross-val)")
    print("=" * 70)

    signals = [
        SignalContext(
            signal_id=str(uuid4()),
            published_at=datetime(2026, 5, 5, tzinfo=timezone.utc),
            source="Reuters_AP",
            direction="bearish",
            importance=85,
            category="geopolitical",
            title="휴전 임박 - Reuters/AP confirm",
        ),
        SignalContext(
            signal_id=str(uuid4()),
            published_at=datetime(2026, 5, 6, tzinfo=timezone.utc),
            source="EIA",
            direction="bearish",
            importance=80,
            category="policy",
            title="미국 SPR 1억 배럴 방출 발표",
        ),
        SignalContext(
            signal_id=str(uuid4()),
            published_at=datetime(2026, 5, 4, tzinfo=timezone.utc),
            source="GDELT_china_demand",
            direction="bearish",
            importance=70,
            category="demand",
            title="중국 PMI 49.2 - 수축 영역",
        ),
        SignalContext(
            signal_id=str(uuid4()),
            published_at=datetime(2026, 5, 7, tzinfo=timezone.utc),
            source="OilPriceAPI",
            direction="bearish",
            importance=65,
            category="market",
            title="VLCC 운임 -15%",
        ),
        SignalContext(
            signal_id=str(uuid4()),
            published_at=datetime(2026, 5, 6, tzinfo=timezone.utc),
            source="EIA",
            direction="bearish",
            importance=60,
            category="supply",
            title="글로벌 정유 재고 ↑",
        ),
    ]

    input_data = MissionPlanInput(
        pattern_score=22.0,
        bullish_score=30.0,
        bearish_score=165.0,
        cross_val_bonus=15.0,
        signal_count_90d=38,
        top_signals=signals,
        active_mission=None,
    )

    result = call_mission_plan_agent(input_data)
    if result is None:
        print("  ❌ FAILED")
        return

    print(f"  action_type:      {result.action_type}")
    print(f"  mission_type:     {result.mission_type}")
    print(f"  goal:             {result.goal_text}")
    print(f"  pattern_score:    {result.pattern_score}")
    print(f"  confidence:       {result.confidence_score}")
    print(f"  reasoning:        {result.reasoning[:150]}...")

    assert result.action_type == "new_mission"
    assert result.mission_type == MissionType.OPPORTUNITY
    print("  ✅ PASS — OPPORTUNITY Mission 정상 제안")


# ════════════════════════════════════════════════════════════════════════
# 시나리오 3 — PIVOT (HEDGE → OPP, 시나리오 § 14 Phase 6)
# ════════════════════════════════════════════════════════════════════════
def test_pivot_hedge_to_opp() -> None:
    print("\n" + "=" * 70)
    print("Test 3 — PIVOT (active HEDGE → OPP, 시장 reverse)")
    print("=" * 70)

    active = Mission(
        mission_id=uuid4(),
        mission_type=MissionType.HEDGE,
        status=MissionStatus.ON_TRACK,
        goal_text="Term 50% → 70% (4주) — Pre-emptive Hedge",
        pattern_score=82.0,
        reasoning="...",
        simulation_roi={"Brent_130": 410},
        target_pct=70,
        duration_days=28,
        created_at=datetime(2026, 4, 19, tzinfo=timezone.utc),
        confirmed_at=datetime(2026, 4, 19, tzinfo=timezone.utc),
        confirmed_via="apps",
        version=2,
    )

    # 같은 약세 5건 (Test 2와 동일)
    signals = [
        SignalContext(
            signal_id=str(uuid4()),
            published_at=datetime(2026, 5, 5, tzinfo=timezone.utc),
            source="Reuters_AP",
            direction="bearish",
            importance=85,
            category="geopolitical",
            title="휴전 임박",
        ),
        SignalContext(
            signal_id=str(uuid4()),
            published_at=datetime(2026, 5, 6, tzinfo=timezone.utc),
            source="EIA",
            direction="bearish",
            importance=80,
            category="policy",
            title="SPR 1억 배럴 방출",
        ),
        SignalContext(
            signal_id=str(uuid4()),
            published_at=datetime(2026, 5, 4, tzinfo=timezone.utc),
            source="GDELT_china_demand",
            direction="bearish",
            importance=70,
            category="demand",
            title="중국 PMI 49.2",
        ),
    ]

    input_data = MissionPlanInput(
        pattern_score=38.0,  # HEDGE zone (70+) → STABLE/OPP zone 진입
        bullish_score=60.0,
        bearish_score=145.0,
        cross_val_bonus=10.0,
        signal_count_90d=35,
        top_signals=signals,
        active_mission=active,
    )

    result = call_mission_plan_agent(input_data)
    if result is None:
        print("  ❌ FAILED")
        return

    print(f"  action_type:      {result.action_type}")
    print(f"  mission_type:     {result.mission_type}")
    print(f"  goal:             {result.goal_text}")
    print(f"  pattern_score:    {result.pattern_score}")
    print(f"  confidence:       {result.confidence_score}")
    print(f"  urgency:          {result.urgency}")
    print(f"  reasoning:        {result.reasoning[:150]}...")
    print(f"  simulation_roi:   {result.simulation_roi}")

    # Pivot이거나 (정확) Pause (관망)도 reasonable.
    # 단 continue 또는 new_mission with HEDGE는 fail
    valid_actions = ("pivot", "pause", "abort")
    if result.action_type in valid_actions:
        print(f"  ✅ PASS — Living Mission lifecycle 작동 ({result.action_type})")
    else:
        print(f"  ⚠️  Unexpected action_type={result.action_type} (expected pivot/pause/abort)")


# ════════════════════════════════════════════════════════════════════════
def main() -> None:
    print("Mission Plan Agent — 3 시나리오 검증")
    print("LLM endpoint: databricks-claude-haiku-4-5")
    print("(profile: crude-compass)")

    test_hedge_pre_crisis()
    test_opportunity()
    test_pivot_hedge_to_opp()

    print("\n" + "=" * 70)
    print("All tests completed")


if __name__ == "__main__":
    main()
