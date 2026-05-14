"""Phase 6 Reactive Trigger — OilPriceAPI spike 감지 → bus event.

시나리오 §15 Reactive narrative:
- bronze.oil_prices 5분 단위 데이터에서 |delta_pct_5min| ≥ 2% spike 감지
- EventBus 'reactive.alert' 발행 → WebSocket broadcast → Frontend toast
- (optional) Mission Plan Agent 재호출 → Pivot 권고

Endpoint:
- POST /api/reactive/check-spike — 최근 1h 내 spike scan
- POST /api/demo/inject_price_spike — 데모용 인위 spike inject (별도 demo router)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.pattern import _q
from app.store import get_bus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/reactive", tags=["reactive"])

SPIKE_THRESHOLD_PCT = 2.0


class SpikeCheckResponse(BaseModel):
    checked_at: str
    spikes_found: int
    latest_spike: dict | None  # {ticker, price_usd, delta_pct_5min, fetched_at}
    bus_published: bool


@router.post("/demo-spike")
async def demo_trigger_spike(ticker: str = "BRENT_CRUDE_USD", delta: float = 2.5) -> dict:
    """데모용 인위 spike alert trigger — bronze 데이터 변경 없이 bus event만 발행.

    데모 시 평가위원에게 spike narrative 시연 (실제 시장 spike 발생 대기 불필요).
    DEMO_MODE 무관 (시나리오 §15 narrative anchor).
    """
    from app.core.config import get_settings
    if not get_settings().demo_mode:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail={"code": "DEMO_MODE_DISABLED"})

    direction = "bullish" if delta > 0 else "bearish"
    sign = "+" if delta > 0 else ""
    price_now = 108.50 if ticker == "BRENT_CRUDE_USD" else 90.0

    bus = get_bus()
    await bus.publish({
        "type": "reactive.alert",
        "title": f"🚨 {ticker} {sign}{delta:.2f}% spike (demo)",
        "body": (
            f"현재 가격 ${price_now:.2f}. 5분 단위 {direction} 시그널 감지. "
            f"진행 중 Mission Pivot 검토 권고."
        ),
        "ticker": ticker,
        "price_usd": price_now,
        "delta_pct_5min": delta,
        "direction": direction,
    })
    return {
        "demo": True,
        "broadcast": "reactive.alert",
        "ticker": ticker,
        "delta_pct_5min": delta,
    }


@router.post("/check-spike")
async def check_spike() -> SpikeCheckResponse:
    """bronze.oil_prices 최근 1h 내 |delta_pct_5min| ≥ 2% spike scan.

    Spike 발견 시 EventBus 'reactive.alert' broadcast → frontend toast + Slack push.
    """
    sql = f"""
      SELECT ticker, price_usd, delta_pct_5min, fetched_at
      FROM crude_compass.bronze.oil_prices
      WHERE fetched_at >= CURRENT_TIMESTAMP() - INTERVAL 1 HOUR
        AND delta_pct_5min IS NOT NULL
        AND ABS(CAST(delta_pct_5min AS DOUBLE)) >= {SPIKE_THRESHOLD_PCT}
      ORDER BY fetched_at DESC
      LIMIT 5
    """
    try:
        rows = _q(sql, timeout="15s")
    except Exception as e:
        logger.warning("spike check failed: %s", e)
        return SpikeCheckResponse(
            checked_at=datetime.now(timezone.utc).isoformat(),
            spikes_found=0,
            latest_spike=None,
            bus_published=False,
        )

    if not rows:
        return SpikeCheckResponse(
            checked_at=datetime.now(timezone.utc).isoformat(),
            spikes_found=0,
            latest_spike=None,
            bus_published=False,
        )

    # 가장 최근 spike
    r = rows[0]
    latest = {
        "ticker": str(r[0]),
        "price_usd": float(r[1]),
        "delta_pct_5min": float(r[2]),
        "fetched_at": str(r[3]),
    }
    direction = "bullish" if latest["delta_pct_5min"] > 0 else "bearish"
    sign = "+" if latest["delta_pct_5min"] > 0 else ""

    # EventBus 'reactive.alert' broadcast
    bus = get_bus()
    await bus.publish({
        "type": "reactive.alert",
        "title": f"🚨 {latest['ticker']} {sign}{latest['delta_pct_5min']:.2f}% spike",
        "body": (
            f"현재 가격 ${latest['price_usd']:.2f}. 5분 단위 {direction} 시그널 감지. "
            f"진행 중 Mission Pivot 검토 권고."
        ),
        "ticker": latest["ticker"],
        "price_usd": latest["price_usd"],
        "delta_pct_5min": latest["delta_pct_5min"],
        "direction": direction,
    })

    return SpikeCheckResponse(
        checked_at=datetime.now(timezone.utc).isoformat(),
        spikes_found=len(rows),
        latest_spike=latest,
        bus_published=True,
    )
