"""Block Kit JSON builder — mission 카드 생성 (proposed / post-action).

핵심:
- 단일 message 1개로 모든 상태 표현 (proposed→buttons / confirmed→actions 제거 + context 추가).
- button value 에 mission_id + version JSON (Slack 2000자 제한 안에 ~80자 안전).
- 데모 5초 sync narrative 핵심: 매니저는 Slack 카드 한 번 보고 모든 의사결정 가능.

시나리오 anchor: crude_compass_final_scenario.md §14 Phase 4 + §6 Slack actions.
"""
from __future__ import annotations

import json
from typing import Literal

from app.schemas.mission import Mission, MissionType, MissionUrgency


ActionState = Literal["proposed", "confirmed", "rejected", "pivoted", "paused", "aborted"]


# Slack shortcode + emoji=True flag → Slack이 자동 렌더링 (Python code는 char-free)
_URGENCY_LABEL: dict[MissionUrgency, str] = {
    MissionUrgency.URGENT: ":rotating_light: *URGENT*",
    MissionUrgency.DEFAULT: ":warning: *PROACTIVE*",
    MissionUrgency.OPTIONAL: ":information_source: *OPTIONAL*",
}

_TYPE_LABEL: dict[MissionType, str] = {
    MissionType.HEDGE: ":shield: HEDGE",
    MissionType.OPPORTUNITY: ":dart: OPPORTUNITY",
}


def _mission_value(mission: Mission) -> str:
    """버튼 value 에 박을 식별자 JSON. ≤ 2000자."""
    return json.dumps({"mid": str(mission.mission_id), "v": mission.version})


def _roi_lines(simulation_roi: dict[str, float]) -> str:
    """simulation_roi dict → markdown 표 (Slack mrkdwn).

    {"Brent_130_봉쇄": 410.0, "Brent_110_긴장": 140.0, "Brent_90_평화": -50.0}
    → ```
      Brent_130_봉쇄 :  +410.0 KRW억
      Brent_110_긴장 :  +140.0
      Brent_90_평화  :   -50.0
      ```
    """
    if not simulation_roi:
        return "_시뮬레이션 ROI 데이터 없음_"
    lines = []
    max_key = max((len(k) for k in simulation_roi), default=10)
    for k, v in simulation_roi.items():
        sign = "+" if v >= 0 else ""
        lines.append(f"`{k.ljust(max_key)}` : {sign}{v:.1f} 억원")
    return "\n".join(lines)


def _action_buttons(mission: Mission, apps_url_base: str = "http://localhost:5173") -> dict:
    """proposed 상태에서만 표시되는 actions block (5 buttons)."""
    value = _mission_value(mission)
    return {
        "type": "actions",
        "block_id": f"mission_actions_{mission.mission_id}",
        "elements": [
            {
                "type": "button",
                "action_id": "mission_confirm",
                "style": "primary",
                "text": {"type": "plain_text", "text": ":white_check_mark: Confirm", "emoji": True},
                "value": value,
            },
            {
                "type": "button",
                "action_id": "mission_reject",
                "style": "danger",
                "text": {"type": "plain_text", "text": ":x: Reject", "emoji": True},
                "value": value,
            },
            {
                "type": "button",
                "action_id": "mission_pivot",
                "text": {"type": "plain_text", "text": ":arrows_counterclockwise: Pivot", "emoji": True},
                "value": value,
            },
            {
                "type": "button",
                "action_id": "mission_modify",
                "text": {"type": "plain_text", "text": ":pencil2: Modify", "emoji": True},
                "value": value,
            },
            {
                "type": "button",
                "action_id": "mission_open_apps",
                "text": {"type": "plain_text", "text": ":link: Open in Apps", "emoji": True},
                "url": f"{apps_url_base}/missions/{mission.mission_id}",
                "value": value,
            },
        ],
    }


def _post_action_context(mission: Mission, action_state: ActionState) -> dict | None:
    """proposed가 아닌 상태에서 표시할 context block (no actions)."""
    via_label = mission.confirmed_via.upper() if mission.confirmed_via else "?"
    actor = mission.confirmed_by or "?"
    if action_state == "confirmed":
        text = f":white_check_mark: *Confirmed via {via_label}* by `{actor}`"
    elif action_state == "rejected":
        text = f":x: *Rejected via {via_label}* by `{actor}`"
    elif action_state == "pivoted":
        last = mission.pivot_history[-1] if mission.pivot_history else None
        if last:
            text = (
                f":arrows_counterclockwise: *Pivoted* "
                f"`{last.from_type.value}` → `{last.to_type.value}`  _{last.reason}_"
            )
        else:
            text = ":arrows_counterclockwise: *Pivoted*"
    elif action_state == "paused":
        text = ":double_vertical_bar: *Paused*"
    elif action_state == "aborted":
        text = ":octagonal_sign: *Aborted*"
    else:
        return None
    return {
        "type": "context",
        "block_id": f"mission_state_{mission.mission_id}",
        "elements": [{"type": "mrkdwn", "text": text}],
    }


def build_mission_card(
    mission: Mission,
    action_state: ActionState = "proposed",
    apps_url_base: str = "http://localhost:5173",
) -> list[dict]:
    """Mission 카드 Block Kit JSON 생성.

    Returns: blocks list (Slack chat.postMessage/chat.update의 'blocks' 인자에 박음)
    """
    urgency = _URGENCY_LABEL.get(mission.urgency, _URGENCY_LABEL[MissionUrgency.DEFAULT])
    mtype = _TYPE_LABEL.get(mission.mission_type, mission.mission_type.value)

    blocks: list[dict] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"Crude Compass — {mission.mission_type.value} Mission",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"{urgency}"},
                {"type": "mrkdwn", "text": f"*Type*\n{mtype}"},
                {
                    "type": "mrkdwn",
                    "text": f"*AI Confidence*\n`{mission.pattern_score:.1f}` / 100 (Pattern Score)",
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Target*\n`{mission.target_pct or '?'}%` "
                    f"for {mission.duration_days}일",
                },
            ],
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Goal*\n{mission.goal_text}"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Reasoning*\n{mission.reasoning}"},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Simulation ROI (시나리오별)*\n{_roi_lines(mission.simulation_roi)}",
            },
        },
        {"type": "divider"},
    ]

    if action_state == "proposed":
        blocks.append(_action_buttons(mission, apps_url_base=apps_url_base))
    else:
        ctx = _post_action_context(mission, action_state)
        if ctx:
            blocks.append(ctx)
        # 'Open in Apps'는 항상 유지 (post-action에서도 detail 확인 가능)
        blocks.append({
            "type": "actions",
            "block_id": f"mission_postaction_{mission.mission_id}",
            "elements": [
                {
                    "type": "button",
                    "action_id": "mission_open_apps",
                    "text": {"type": "plain_text", "text": ":link: Open in Apps", "emoji": True},
                    "url": f"{apps_url_base}/missions/{mission.mission_id}",
                    "value": _mission_value(mission),
                }
            ],
        })

    return blocks


def build_text_fallback(mission: Mission, action_state: ActionState = "proposed") -> str:
    """Slack notification preview text (Block Kit 미렌더링 클라이언트 fallback)."""
    return (
        f"[{mission.urgency.value.upper()}] "
        f"{mission.mission_type.value} — {mission.goal_text} "
        f"(Pattern {mission.pattern_score:.0f}, {action_state})"
    )
