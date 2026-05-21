"""Trigger detection — 3 event types that fire AI report generation.

시나리오 §0 (reports model 2026-05-21):
1. gdelt_signal   — bronze.news_articles importance >= 80, 최근 N분
2. price_spike    — gold.oil_prices_wide Dubai 24h ±2%
3. pattern_drift  — gold.daily_risk_score 오늘 vs 7일 MA ±10pt

Query: Databricks SQL Warehouse via WorkspaceClient (UC tables).
       Lakebase X — UC bronze/gold만.

Caller: 보통 Databricks notebook (15분 cron) 또는 backend admin endpoint.
        return된 TriggerEvent를 report_generator.generate_report()로 넘김.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

from databricks.sdk import WorkspaceClient

from app.schemas.report import TriggerType

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────
# TriggerEvent — detector 결과 + report_generator input
# ────────────────────────────────────────────────────────────────────
@dataclass
class TriggerEvent:
    """trigger 1건 — report_generator input + reports.trigger_meta JSONB.

    fingerprint: dedup용 key (notebook 단계에서 같은 article_id/trade_date 중복 skip).
    """
    trigger_type: TriggerType
    fingerprint: str
    headline_hint: str
    meta: dict[str, Any] = field(default_factory=dict)
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_trigger_meta(self) -> dict[str, Any]:
        """reports.trigger_meta JSONB로 serializable."""
        return {
            "fingerprint": self.fingerprint,
            "headline_hint": self.headline_hint,
            "detected_at": self.detected_at.isoformat(),
            **self.meta,
        }


# ────────────────────────────────────────────────────────────────────
# Threshold defaults — env override 가능
# ────────────────────────────────────────────────────────────────────
GDELT_IMPORTANCE_THRESHOLD = int(os.getenv("TRIGGER_GDELT_IMPORTANCE", "80"))
GDELT_LOOKBACK_MIN = int(os.getenv("TRIGGER_GDELT_LOOKBACK_MIN", "30"))
PRICE_SPIKE_PCT = float(os.getenv("TRIGGER_PRICE_SPIKE_PCT", "2.0"))
PATTERN_DRIFT_PT = float(os.getenv("TRIGGER_PATTERN_DRIFT_PT", "10.0"))


# ────────────────────────────────────────────────────────────────────
# SQL Warehouse client (pattern.py와 같은 패턴)
# ────────────────────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def _client() -> WorkspaceClient:
    profile = os.getenv("DATABRICKS_CONFIG_PROFILE", "crude-compass")
    try:
        return WorkspaceClient(profile=profile)
    except Exception:
        return WorkspaceClient()


@lru_cache(maxsize=1)
def _warehouse_id() -> str:
    w = _client()
    for wh in w.warehouses.list():
        n = (wh.name or "").lower()
        if "serverless" in n or "starter" in n:
            return wh.id
    whs = list(w.warehouses.list())
    if not whs:
        raise RuntimeError("No warehouses available")
    return whs[0].id


def _q(sql: str, timeout: str = "30s") -> list[list]:
    w = _client()
    r = w.statement_execution.execute_statement(
        statement=sql.strip(), warehouse_id=_warehouse_id(), wait_timeout=timeout,
    )
    if r.status and r.status.error:
        raise RuntimeError(r.status.error.message)
    if r.result and r.result.data_array:
        return r.result.data_array
    return []


# ────────────────────────────────────────────────────────────────────
# 1. detect_gdelt_signal — high-importance news burst
# ────────────────────────────────────────────────────────────────────
def detect_gdelt_signal(
    *,
    importance_threshold: int | None = None,
    lookback_minutes: int | None = None,
) -> list[TriggerEvent]:
    """최근 N분 importance >= threshold인 news article들.

    Returns 각 article 1건씩 TriggerEvent. 0건도 정상 (signal 없음).
    Caller는 fingerprint(article_id) 기반 dedup 책임.
    """
    imp = importance_threshold if importance_threshold is not None else GDELT_IMPORTANCE_THRESHOLD
    lookback = lookback_minutes if lookback_minutes is not None else GDELT_LOOKBACK_MIN

    try:
        rows = _q(
            f"""
            SELECT article_id, title, source, category, direction,
                   importance, mention_count, published_at
              FROM crude_compass.bronze.news_articles
             WHERE published_at >= CURRENT_TIMESTAMP() - INTERVAL {lookback} MINUTES
               AND importance >= {imp}
               AND direction IN ('bullish', 'bearish')
             ORDER BY importance DESC, mention_count DESC
             LIMIT 5
            """,
            timeout="15s",
        )
    except Exception as e:
        logger.warning("detect_gdelt_signal query failed: %s", e)
        return []

    events: list[TriggerEvent] = []
    for r in rows:
        article_id = str(r[0])
        title = str(r[1] or "")[:200]
        events.append(
            TriggerEvent(
                trigger_type=TriggerType.GDELT_SIGNAL,
                fingerprint=f"gdelt:{article_id}",
                headline_hint=title,
                meta={
                    "article_id": article_id,
                    "source": r[2],
                    "category": r[3],
                    "direction": r[4],
                    "importance": int(r[5]) if r[5] is not None else None,
                    "mention_count": int(r[6]) if r[6] is not None else None,
                    "published_at": str(r[7]) if r[7] is not None else None,
                },
            )
        )
    return events


# ────────────────────────────────────────────────────────────────────
# 2. detect_price_spike — Dubai 24h ±N%
# ────────────────────────────────────────────────────────────────────
def detect_price_spike(*, threshold_pct: float | None = None) -> TriggerEvent | None:
    """Dubai 가장 최근 가격 vs 24h 전 (= 1 trading day) 변동률 ±N%.

    None 반환: 스파이크 없음 (정상).
    """
    thr = threshold_pct if threshold_pct is not None else PRICE_SPIKE_PCT

    try:
        rows = _q(
            """
            WITH latest AS (
                SELECT trade_date, dubai_usd
                  FROM crude_compass.gold.oil_prices_wide
                 WHERE dubai_usd IS NOT NULL
                 ORDER BY trade_date DESC
                 LIMIT 1
            ),
            prev AS (
                SELECT dubai_usd AS dubai_prev
                  FROM crude_compass.gold.oil_prices_wide
                 WHERE dubai_usd IS NOT NULL
                   AND trade_date < (SELECT trade_date FROM latest)
                 ORDER BY trade_date DESC
                 LIMIT 1
            )
            SELECT latest.trade_date, latest.dubai_usd, prev.dubai_prev
              FROM latest CROSS JOIN prev
            """,
            timeout="15s",
        )
    except Exception as e:
        logger.warning("detect_price_spike query failed: %s", e)
        return None

    if not rows or len(rows[0]) < 3:
        return None

    r = rows[0]
    trade_date = str(r[0])
    dubai_now = float(r[1]) if r[1] is not None else None
    dubai_prev = float(r[2]) if r[2] is not None else None
    if dubai_now is None or dubai_prev is None or dubai_prev == 0:
        return None

    delta_pct = (dubai_now - dubai_prev) / dubai_prev * 100.0
    if abs(delta_pct) < thr:
        return None

    direction = "up" if delta_pct > 0 else "down"
    headline = f"Dubai {dubai_prev:.2f} → {dubai_now:.2f} USD ({delta_pct:+.2f}%, 24h)"
    return TriggerEvent(
        trigger_type=TriggerType.PRICE_SPIKE,
        fingerprint=f"price:{trade_date}:{direction}",
        headline_hint=headline,
        meta={
            "trade_date": trade_date,
            "dubai_usd": dubai_now,
            "dubai_prev_usd": dubai_prev,
            "delta_pct": round(delta_pct, 3),
            "direction": direction,
            "threshold_pct": thr,
        },
    )


# ────────────────────────────────────────────────────────────────────
# 3. detect_pattern_drift — pattern_score 7일 MA 이탈
# ────────────────────────────────────────────────────────────────────
def detect_pattern_drift(*, threshold_pt: float | None = None) -> TriggerEvent | None:
    """오늘 pattern_score vs 직전 7일 MA — 절대값 N pt 이상 차이 → trigger.

    daily-curation cron 직후 (06:30 KST 이후)에 호출. 매일 1번만 의미 있음.
    """
    thr = threshold_pt if threshold_pt is not None else PATTERN_DRIFT_PT

    try:
        rows = _q(
            """
            WITH latest AS (
                SELECT date, pattern_score
                  FROM crude_compass.gold.daily_risk_score
                 ORDER BY date DESC
                 LIMIT 1
            ),
            ma AS (
                SELECT AVG(pattern_score) AS ma7
                  FROM (
                    SELECT pattern_score
                      FROM crude_compass.gold.daily_risk_score
                     WHERE date < (SELECT date FROM latest)
                     ORDER BY date DESC
                     LIMIT 7
                  )
            )
            SELECT latest.date, latest.pattern_score, ma.ma7
              FROM latest CROSS JOIN ma
            """,
            timeout="15s",
        )
    except Exception as e:
        logger.warning("detect_pattern_drift query failed: %s", e)
        return None

    if not rows or len(rows[0]) < 3:
        return None

    r = rows[0]
    today = str(r[0])
    score_now = float(r[1]) if r[1] is not None else None
    ma7 = float(r[2]) if r[2] is not None else None
    if score_now is None or ma7 is None:
        return None

    delta = score_now - ma7
    if abs(delta) < thr:
        return None

    direction = "spike_up" if delta > 0 else "spike_down"
    zone = "HEDGE" if score_now >= 70 else ("OPPORTUNITY" if score_now <= 30 else "STABLE")
    headline = f"Pattern Score {ma7:.1f} → {score_now:.1f} ({delta:+.1f}pt vs 7d MA, zone={zone})"
    return TriggerEvent(
        trigger_type=TriggerType.PATTERN_DRIFT,
        fingerprint=f"pattern:{today}",
        headline_hint=headline,
        meta={
            "date": today,
            "pattern_score": score_now,
            "ma7": round(ma7, 2),
            "delta": round(delta, 2),
            "direction": direction,
            "zone": zone,
            "threshold_pt": thr,
        },
    )


# ────────────────────────────────────────────────────────────────────
# Convenience — 3 detector 한 번에
# ────────────────────────────────────────────────────────────────────
def detect_all() -> list[TriggerEvent]:
    """3 detector 모두 실행해서 결과 합침. notebook / admin endpoint용."""
    events: list[TriggerEvent] = []
    events.extend(detect_gdelt_signal())
    spike = detect_price_spike()
    if spike:
        events.append(spike)
    drift = detect_pattern_drift()
    if drift:
        events.append(drift)
    return events
