"""Demo scenario presets — `/api/demo/inject_signal` 의 payload 생성.

narrative 1:1 매핑:
- docs/crude_compass_final_scenario.md §14 Phase 4 (hormuz_blockade) — Score 82, Confidence 65%
- docs/crude_compass_final_scenario.md §14 Phase 6 (ceasefire) — Pivot bidirectional 시연용
- docs/crude_compass_final_scenario.md §5 평시 미세 조정 (saudi_cut, us_inventory_surprise)

NOTE: 시나리오 doc 변경 시 본 파일도 sync 필요 — grep 'hormuz_blockade' / 'ceasefire' 로 단일 anchor.
"""
from __future__ import annotations

from typing import Any

from app.schemas.mission import MissionType, MissionUrgency


# scenario → preset dict mapping
_PRESETS: dict[str, dict[str, Any]] = {
    # §14 Phase 4 (02:00-02:45) — Pre-emptive HEDGE
    "hormuz_blockade": {
        "mission_type": MissionType.HEDGE,
        "goal_text": "Term 60% → 75% (4주)",
        "reasoning": (
            "호르무즈 통과 -93% (AIS 7일 평균 대비) + OPEC MOMR 5월 사우디 추가 감산 시그널 "
            "+ GDELT 키워드 멘션 +280% + Iran 제재 + UK Maritime alerts. AI confidence 65%."
        ),
        "pattern_score": 82.0,
        "urgency": MissionUrgency.URGENT,
        "target_pct": 75,
        "duration_days": 28,
        "simulation_roi": {
            "Brent_130_봉쇄": 410.0,
            "Brent_110_긴장": 140.0,
            "Brent_90_평화": -50.0,
        },
    },
    # §14 Phase 6 (03:30-04:15) — Bidirectional Pivot (휴전/SPR/중국 PMI)
    "ceasefire": {
        "mission_type": MissionType.OPPORTUNITY,
        "goal_text": "Term 60% → 40% / Spot 40% → 60% (3주)",
        "reasoning": (
            "Israel-Hamas 휴전 임박 시그널 + SPR 방출 가능성 + 중국 PMI 49.2 "
            "+ VLCC 운임 -15%. 약세 reversal."
        ),
        "pattern_score": 78.0,
        "urgency": MissionUrgency.URGENT,
        "target_pct": 40,
        "duration_days": 21,
        "simulation_roi": {
            "Brent_70_급락": 320.0,
            "Brent_80_안정": 110.0,
            "Brent_95_재확전": -80.0,
        },
    },
    # §5 평시 미세 조정 — Aramco OSP / OPEC+ 감산
    "saudi_cut": {
        "mission_type": MissionType.HEDGE,
        "goal_text": "Term 60% → 70% (2주)",
        "reasoning": "Aramco OSP 발표 + OPEC+ 감산 연장. AI confidence 58%.",
        "pattern_score": 70.0,
        "urgency": MissionUrgency.DEFAULT,
        "target_pct": 70,
        "duration_days": 14,
        "simulation_roi": {
            "Brent_100": 180.0,
            "Brent_90": 60.0,
            "Brent_80": -30.0,
        },
    },
    # §5 평시 — EIA 주간 재고 surprise
    "us_inventory_surprise": {
        "mission_type": MissionType.HEDGE,
        "goal_text": "Term 60% → 65% (1주)",
        "reasoning": "EIA 재고 -5M bbl surprise. AI confidence 52%.",
        "pattern_score": 62.0,
        "urgency": MissionUrgency.OPTIONAL,
        "target_pct": 65,
        "duration_days": 7,
        "simulation_roi": {
            "Brent_95": 80.0,
            "Brent_85": 20.0,
            "Brent_75": -25.0,
        },
    },
    # custom — 전적으로 overrides에 의존 (필수 field 누락 시 422)
    "custom": {},
}


VALID_SCENARIOS = list(_PRESETS.keys())


class CustomScenarioIncomplete(ValueError):
    """custom scenario에서 필수 field (goal_text, reasoning, mission_type) 누락 시."""


def build_preset(scenario: str, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """scenario 이름 + overrides → merged payload dict.

    overrides는 None이 아닌 값만 preset 위에 덮어쓴다.
    custom scenario는 mission_type + goal_text + reasoning 셋 다 overrides에 있어야 함.
    """
    if scenario not in _PRESETS:
        raise ValueError(f"Unknown scenario: {scenario}. Valid: {VALID_SCENARIOS}")

    preset = dict(_PRESETS[scenario])
    if overrides:
        for k, v in overrides.items():
            if v is not None:
                preset[k] = v

    if scenario == "custom":
        required = {"mission_type", "goal_text", "reasoning"}
        missing = required - preset.keys()
        if missing:
            raise CustomScenarioIncomplete(
                f"custom scenario requires: {sorted(missing)}"
            )

    # default fallbacks (preset 자체에 없으면 채워둠)
    preset.setdefault("simulation_roi", {})
    preset.setdefault("urgency", MissionUrgency.DEFAULT)
    preset.setdefault("pattern_score", 60.0)
    preset.setdefault("target_pct", None)
    preset.setdefault("duration_days", 28)

    return preset
