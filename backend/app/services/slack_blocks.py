"""Block Kit JSON builder — 트리거 보고서 / 일일 보고서 카드 (reports model).

mission 카드 빌더는 reports 모델 전환으로 제거됨.
"""
from __future__ import annotations

import json
from datetime import datetime


# ════════════════════════════════════════════════════════════════════════
# Reports model (2026-05-21) — 트리거 보고서 발행 알림 카드
# ════════════════════════════════════════════════════════════════════════
_TRIGGER_LABEL = {
    "gdelt_signal": "뉴스 시그널",
    "price_spike": "가격 급변",
    "pattern_drift": "패턴 이탈",
}


def build_report_card(
    report,
    report_id: str | None = None,
    apps_url: str = "http://localhost:5173",
) -> list[dict]:
    """트리거 보고서 1건 → Slack Block Kit 카드 (활성화/기각 버튼 + 링크).

    report: Report 객체 (use_enum_values=True → trigger_type/recommendation은 str).
    report_id: 버튼 value용. 미지정 시 report.report_id 사용.
    """
    rid = report_id or str(getattr(report, "report_id", "") or "")
    trig = _TRIGGER_LABEL.get(str(report.trigger_type), str(report.trigger_type))
    rec = report.recommendation or "검토 필요"
    summary = (report.summary or "")[:600]
    blocks: list[dict] = [
        {"type": "header", "text": {"type": "plain_text", "text": f"새 보고서 · {trig}", "emoji": False}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*{report.headline}*"}},
    ]
    if summary:
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": summary}})
    blocks.append({
        "type": "section",
        "fields": [
            {"type": "mrkdwn", "text": f"*권고*\n{rec}"},
            {"type": "mrkdwn", "text": "*상태*\n검토 대기"},
        ],
    })
    value = json.dumps({"rid": rid})
    blocks.append({
        "type": "actions",
        "elements": [
            {"type": "button", "text": {"type": "plain_text", "text": "활성화", "emoji": False},
             "style": "primary", "action_id": "report_keep", "value": value},
            {"type": "button", "text": {"type": "plain_text", "text": "기각", "emoji": False},
             "style": "danger", "action_id": "report_drop", "value": value},
            {"type": "button", "text": {"type": "plain_text", "text": "의사결정에서 열기", "emoji": False},
             "url": apps_url, "action_id": "report_open_apps"},
        ],
    })
    created = getattr(report, "created_at", None) or datetime.now()
    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": f"Crude Compass AI · {created:%Y-%m-%d %H:%M}"}],
    })
    return blocks


def build_report_resolved_card(report, action_label: str) -> list[dict]:
    """버튼 클릭 후 카드 — 버튼 제거 + 처리 결과 context."""
    trig = _TRIGGER_LABEL.get(str(report.trigger_type), str(report.trigger_type))
    rec = report.recommendation or "검토 필요"
    blocks: list[dict] = [
        {"type": "header", "text": {"type": "plain_text", "text": f"보고서 · {trig}", "emoji": False}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*{report.headline}*"}},
        {"type": "section", "fields": [
            {"type": "mrkdwn", "text": f"*권고*\n{rec}"},
            {"type": "mrkdwn", "text": f"*처리*\n{action_label}"},
        ]},
        {"type": "context", "elements": [{"type": "mrkdwn", "text": "Crude Compass AI"}]},
    ]
    return blocks


def build_report_text_fallback(report) -> str:
    """Block Kit 미렌더링 fallback 텍스트."""
    trig = _TRIGGER_LABEL.get(str(report.trigger_type), str(report.trigger_type))
    rec = report.recommendation or "검토 필요"
    return f"[새 보고서 · {trig}] {report.headline} — 권고: {rec}"


_DIRECTION_LABEL = {
    "lean_hedge": "방어 우위 (Term ↑)",
    "neutral": "중립 유지",
    "lean_opportunity": "기회 우위 (Spot ↑)",
}


def build_daily_card(daily, apps_url: str = "http://localhost:5173") -> list[dict]:
    """일일 종합 보고서 → Slack 카드 (read-only, 비중 제안 중심)."""
    rs = daily.ratio_suggestion or {}
    direction = _DIRECTION_LABEL.get(str(rs.get("direction", "neutral")), "중립 유지")
    term = str(rs.get("term_delta_pct", "0"))
    spot = str(rs.get("spot_delta_pct", "0"))
    blocks: list[dict] = [
        {"type": "header", "text": {"type": "plain_text",
         "text": f"오늘의 일일 보고서 · {daily.report_date}", "emoji": False}},
    ]
    if daily.market_context:
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": daily.market_context[:600]}})
    blocks.append({
        "type": "section",
        "fields": [
            {"type": "mrkdwn", "text": f"*방향*\n{direction}"},
            {"type": "mrkdwn", "text": f"*Term / Spot 델타*\n{term}% / {spot}%"},
        ],
    })
    if daily.reasoning:
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": daily.reasoning[:600]}})
    blocks.append({
        "type": "actions",
        "elements": [
            {"type": "button", "text": {"type": "plain_text", "text": "의사결정에서 열기", "emoji": False},
             "url": apps_url, "action_id": "daily_open_apps"},
        ],
    })
    created = getattr(daily, "created_at", None) or datetime.now()
    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn",
         "text": f"Crude Compass AI · 활성 보고서 {daily.kept_count}건 종합 · {created:%Y-%m-%d %H:%M}"}],
    })
    return blocks


def build_daily_text_fallback(daily) -> str:
    rs = daily.ratio_suggestion or {}
    direction = _DIRECTION_LABEL.get(str(rs.get("direction", "neutral")), "중립")
    return f"[오늘의 일일 보고서 · {daily.report_date}] {direction} · {daily.kept_count}건 종합"
