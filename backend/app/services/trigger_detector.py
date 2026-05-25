"""Trigger detection — 3 event types that fire AI report generation.

시나리오 §0 (reports model 2026-05-21):
1. gdelt_signal   — bronze.news_articles importance >= 80, 최근 N분
2. price_spike    — bronze.oil_prices (OilPriceAPI) Brent/WTI/Dubai 최대 24h ±2% (OPINET 일별은 지연 → 미사용)
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
# 2. detect_price_spike — Brent/WTI/Dubai 24h ±N% (최대 변동 기준)
# ────────────────────────────────────────────────────────────────────
_BENCHMARKS = {
    "DUBAI_CRUDE_USD": "Dubai",
    "BRENT_CRUDE_USD": "Brent",
    "WTI_USD": "WTI",
}


def detect_price_spike(*, threshold_pct: float | None = None) -> TriggerEvent | None:
    """Brent·WTI·Dubai 3개 벤치마크의 최신 시세 vs ~24h 전 변동률 — 최대 변동이 ±N% 돌파 시 트리거.

    소스 = bronze.oil_prices (OilPriceAPI, ~30분 실시간 적재). OPINET 일별(gold)은
    1일 지연이라 트리거엔 부적합 → 시황 차트·공식 일별 표시 전용.
    중동 공급 충격 땐 Brent-Dubai 스프레드가 벌어지므로 셋을 함께 보고, 가장 크게
    움직인 벤치마크로 발행하되 보고서는 일(日)·방향당 1건으로 묶음(롤링 24h를 30분마다
    검사하되 스팸 방지).

    None 반환: 스파이크 없음 (정상).
    """
    thr = threshold_pct if threshold_pct is not None else PRICE_SPIKE_PCT

    try:
        rows = _q(
            """
            WITH base AS (
                SELECT ticker, fetched_at, price_usd
                  FROM crude_compass.bronze.oil_prices
                 WHERE ticker IN ('BRENT_CRUDE_USD', 'WTI_USD', 'DUBAI_CRUDE_USD')
                   AND price_usd IS NOT NULL
            ),
            ranked AS (
                SELECT ticker, fetched_at, price_usd,
                       ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY fetched_at DESC) AS rn
                  FROM base
            ),
            lt AS (SELECT ticker, fetched_at AS now_at, price_usd AS now_px FROM ranked WHERE rn = 1),
            prevr AS (
                SELECT b.ticker, b.fetched_at, b.price_usd,
                       ROW_NUMBER() OVER (PARTITION BY b.ticker ORDER BY b.fetched_at DESC) AS rn
                  FROM base b JOIN lt ON b.ticker = lt.ticker
                 WHERE b.fetched_at <= lt.now_at - INTERVAL 24 HOURS
            )
            SELECT lt.ticker, lt.now_at, lt.now_px, p.price_usd AS prev_px
              FROM lt
              LEFT JOIN (SELECT ticker, price_usd FROM prevr WHERE rn = 1) p
                ON lt.ticker = p.ticker
            """,
            timeout="15s",
        )
    except Exception as e:
        logger.warning("detect_price_spike query failed: %s", e)
        return None

    if not rows:
        return None

    moves: list[tuple[str, float, float, float]] = []  # (label, now, prev, pct)
    latest_at = ""
    for r in rows:
        label = _BENCHMARKS.get(str(r[0]), str(r[0]))
        now_at = str(r[1])
        now_px = float(r[2]) if r[2] is not None else None
        prev_px = float(r[3]) if r[3] is not None else None
        if now_at > latest_at:
            latest_at = now_at
        if now_px is None or prev_px is None or prev_px == 0:
            continue
        pct = (now_px - prev_px) / prev_px * 100.0
        moves.append((label, now_px, prev_px, pct))

    if not moves:
        return None

    # 가장 크게 움직인 벤치마크
    label, now_px, prev_px, pct = max(moves, key=lambda m: abs(m[3]))
    if abs(pct) < thr:
        return None

    direction = "up" if pct > 0 else "down"
    day = latest_at[:10]  # YYYY-MM-DD — 하루·방향당 1회 dedup
    all_moves = ", ".join(f"{m[0]} {m[3]:+.2f}%" for m in moves)
    headline = f"{label} {prev_px:.2f} → {now_px:.2f} USD ({pct:+.2f}%, 24h)"
    return TriggerEvent(
        trigger_type=TriggerType.PRICE_SPIKE,
        fingerprint=f"price:{day}:{direction}",
        headline_hint=headline,
        meta={
            "lead_benchmark": label,
            "lead_pct": round(pct, 3),
            "now_usd": now_px,
            "prev_usd": prev_px,
            "all_moves": all_moves,
            "direction": direction,
            "threshold_pct": thr,
            "source": "OilPriceAPI",
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
