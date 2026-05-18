"""OilPriceAPI HTTP client (D-3 추가).

Backend가 OilPriceAPI를 직접 호출해 intraday-summary endpoint에 데이터 공급.
bronze.oil_prices 적재 cron 의존성 제거 — Databricks Job 안 돌아도 demo 작동.

Paid tier 가정 (사용자 D-3 확인):
- /v1/prices/latest 또는 /v1/prices/past_period 호출 가능
- 5분 단위 historical 가능

API docs: https://docs.oilpriceapi.com
- GET /v1/prices/latest?by_code=BRENT_CRUDE_USD
  Headers: Authorization: Token <key>
  Response: {"status": "success", "data": {"price": 105.5, "code": "BRENT_CRUDE_USD",
              "created_at": "2026-05-19T08:35:00+00:00", "type": "spot_price", ...}}

- GET /v1/prices/past_period?by_code=BRENT_CRUDE_USD&by_period=1day
  Response: {"status": "success", "data": {"prices": [{price, created_at}, ...]}}

Ticker codes (OilPriceAPI):
- DUBAI_USD → DUBAI_CRUDE_USD (혹은 DUBAI)
- Brent → BRENT_CRUDE_USD
- WTI → WTI_USD
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

OILPRICE_BASE = "https://api.oilpriceapi.com"

# Frontend ticker → OilPriceAPI code 매핑. 실제 paid tier endpoint에서 사용 가능한
# code 정확히 모르므로 후보 list. 첫 번째부터 시도하다 200 응답 코드 사용.
TICKER_CODE_CANDIDATES: dict[str, list[str]] = {
    "dubai": ["DUBAI_CRUDE_USD", "DUBAI", "DUBAI_USD"],
    "brent": ["BRENT_CRUDE_USD", "BRENT", "BRENT_USD"],
    "wti": ["WTI_USD", "WTI", "WTI_CRUDE"],
}


@dataclass
class IntradayTickerData:
    ticker: str
    price_usd: float | None
    fetched_at: str
    delta_30min_pct: float | None
    delta_24h_pct: float | None
    biggest_spike_pct: float | None
    biggest_spike_at: str | None
    sample_count: int


def _headers() -> dict[str, str]:
    s = get_settings()
    key = s.oilprice_api_key
    if not key:
        raise RuntimeError("OILPRICE_API_KEY env not set")
    # OilPriceAPI는 "Authorization: Token <key>" 패턴 (대부분의 docs 사례)
    return {"Authorization": f"Token {key}", "Accept": "application/json"}


def _fetch_latest(client: httpx.Client, code: str) -> dict | None:
    try:
        r = client.get(
            f"{OILPRICE_BASE}/v1/prices/latest",
            params={"by_code": code},
            headers=_headers(),
            timeout=10.0,
        )
        if r.status_code == 200:
            data = r.json().get("data")
            if isinstance(data, dict):
                return data
        return None
    except Exception as e:
        logger.warning("OilPriceAPI latest %s failed: %s", code, e)
        return None


def _fetch_past_period(client: httpx.Client, code: str, period: str = "1day") -> list[dict]:
    """5분/1day historical. paid tier."""
    try:
        r = client.get(
            f"{OILPRICE_BASE}/v1/prices/past_period",
            params={"by_code": code, "by_period": period},
            headers=_headers(),
            timeout=15.0,
        )
        if r.status_code == 200:
            payload = r.json()
            data = payload.get("data")
            # response shape variants — both {prices: [...]} and {[...]} possible
            if isinstance(data, dict) and isinstance(data.get("prices"), list):
                return data["prices"]
            if isinstance(data, list):
                return data
        return []
    except Exception as e:
        logger.warning("OilPriceAPI past_period %s failed: %s", code, e)
        return []


def _parse_created_at(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        # ISO 8601 — strip Z and add tz
        s2 = s.replace("Z", "+00:00")
        return datetime.fromisoformat(s2)
    except Exception:
        return None


def fetch_intraday_summary() -> list[IntradayTickerData]:
    """3 ticker (Dubai/Brent/WTI) latest + 24h history → summary.

    Returns empty list if OilPriceAPI key missing or all tickers fail.
    """
    out: list[IntradayTickerData] = []
    with httpx.Client() as client:
        for ticker_key, candidates in TICKER_CODE_CANDIDATES.items():
            # 1) latest 시도 — 후보 code 순차 시도
            latest: dict | None = None
            used_code: str | None = None
            for code in candidates:
                latest = _fetch_latest(client, code)
                if latest:
                    used_code = code
                    break
            if not latest or not used_code:
                logger.info("OilPriceAPI: ticker %s — no latest data (tried %s)", ticker_key, candidates)
                continue

            price_now = latest.get("price")
            if isinstance(price_now, str):
                try:
                    price_now = float(price_now)
                except ValueError:
                    price_now = None
            if not isinstance(price_now, (int, float)):
                continue
            now_iso = latest.get("created_at") or datetime.now(timezone.utc).isoformat()

            # 2) past 24h history
            history = _fetch_past_period(client, used_code, "1day")

            # parse + sort
            parsed: list[tuple[datetime, float]] = []
            for item in history:
                p = item.get("price")
                ts = _parse_created_at(item.get("created_at"))
                if ts is None or p is None:
                    continue
                try:
                    parsed.append((ts, float(p)))
                except (TypeError, ValueError):
                    continue
            parsed.sort(key=lambda x: x[0], reverse=True)

            # 30분 전 / 24h 전 price 찾기
            now_dt = datetime.now(timezone.utc)
            t_30m = now_dt - timedelta(minutes=30)
            t_24h = now_dt - timedelta(hours=23)
            price_30m: float | None = None
            price_24h: float | None = None
            for ts, p in parsed:
                if price_30m is None and ts <= t_30m:
                    price_30m = p
                if price_24h is None and ts <= t_24h:
                    price_24h = p
                if price_30m is not None and price_24h is not None:
                    break

            # biggest spike — 인접 sample 간 % 변동 max
            biggest_spike_pct: float | None = None
            biggest_spike_at: str | None = None
            for i in range(len(parsed) - 1):
                t0, p0 = parsed[i]
                _, p1 = parsed[i + 1]
                if p1 == 0:
                    continue
                delta = (p0 - p1) / p1 * 100
                if biggest_spike_pct is None or abs(delta) > abs(biggest_spike_pct):
                    biggest_spike_pct = delta
                    biggest_spike_at = t0.isoformat()

            d30 = (
                (price_now - price_30m) / price_30m * 100
                if price_30m is not None
                else None
            )
            d24 = (
                (price_now - price_24h) / price_24h * 100
                if price_24h is not None
                else None
            )

            out.append(
                IntradayTickerData(
                    ticker=ticker_key,
                    price_usd=float(price_now),
                    fetched_at=now_iso,
                    delta_30min_pct=d30,
                    delta_24h_pct=d24,
                    biggest_spike_pct=biggest_spike_pct,
                    biggest_spike_at=biggest_spike_at,
                    sample_count=len(parsed),
                )
            )
    return out
