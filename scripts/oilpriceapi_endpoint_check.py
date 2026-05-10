"""OilPriceAPI batch endpoint 검증 (Sprint 1 task 6).

목적:
1. 3 ticker (BRENT/WTI/DUBAI)을 1 call로 받을 수 있는지 (batch)
2. 1-by-1 fallback도 작동하는지
3. 응답 latency / quota usage 확인

사용:
    cd backend
    $env:OILPRICE_API_KEY = "<key>"
    uv run python ../scripts/oilpriceapi_endpoint_check.py

근거 (2026-05-08 검색):
- OilPriceAPI Python SDK에 get_multiple() method 존재 → batch 가능 추정
- 정확한 REST endpoint 형태는 직접 호출로 확인 필요
"""
from __future__ import annotations

import os
import sys
import time
from typing import Any

import httpx


API_BASE = "https://api.oilpriceapi.com/v1"
TICKERS = ["BRENT_CRUDE_USD", "WTI_USD", "DUBAI_CRUDE_USD"]


def get_key() -> str:
    key = os.getenv("OILPRICE_API_KEY", "").strip()
    if not key:
        sys.exit("❌ OILPRICE_API_KEY 환경변수 비어있음")
    return key


def try_batch_query(client: httpx.Client, key: str) -> tuple[bool, dict[str, Any]]:
    """후보 1: ?by_codes=BRENT_CRUDE_USD,WTI_USD,DUBAI_CRUDE_USD"""
    try:
        resp = client.get(
            f"{API_BASE}/prices/latest",
            params={"by_codes": ",".join(TICKERS)},
            headers={"Authorization": f"Token {key}"},
            timeout=10.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            return True, data
        return False, {"status": resp.status_code, "body": resp.text[:200]}
    except httpx.HTTPError as e:
        return False, {"error": str(e)}


def try_single_ticker(client: httpx.Client, key: str, ticker: str) -> tuple[bool, dict[str, Any]]:
    """후보 2: ?by_code=BRENT_CRUDE_USD (1-by-1)"""
    try:
        resp = client.get(
            f"{API_BASE}/prices/latest",
            params={"by_code": ticker},
            headers={"Authorization": f"Token {key}"},
            timeout=10.0,
        )
        if resp.status_code == 200:
            return True, resp.json()
        return False, {"status": resp.status_code, "body": resp.text[:200]}
    except httpx.HTTPError as e:
        return False, {"error": str(e)}


def main() -> None:
    key = get_key()
    print(f"🔑 API key loaded (len={len(key)})\n")

    with httpx.Client() as client:
        # 1. Batch 시도
        print("─── 1. Batch endpoint (?by_codes=...) ───")
        t0 = time.perf_counter()
        ok, data = try_batch_query(client, key)
        dt = (time.perf_counter() - t0) * 1000
        if ok:
            print(f"✅ Batch OK ({dt:.0f}ms)")
            print(f"   Response keys: {list(data.keys())[:5]}")
            print(f"   Sample: {str(data)[:300]}")
        else:
            print(f"❌ Batch failed: {data}")

        print()

        # 2. 1-by-1 fallback
        print("─── 2. Per-ticker 1-by-1 (?by_code=...) ───")
        per_ticker_results: dict[str, Any] = {}
        for ticker in TICKERS:
            t0 = time.perf_counter()
            ok, d = try_single_ticker(client, key, ticker)
            dt = (time.perf_counter() - t0) * 1000
            status = "✅" if ok else "❌"
            print(f"{status} {ticker} ({dt:.0f}ms)")
            if ok:
                per_ticker_results[ticker] = d
            else:
                print(f"   {d}")

        print()
        print("─── Summary ───")
        if per_ticker_results:
            print("✅ 1-by-1 fallback OK")
            print(f"   {len(per_ticker_results)}/{len(TICKERS)} tickers fetched")
            sample = next(iter(per_ticker_results.values()))
            print(f"   Sample structure: {list(sample.keys())[:5]}")
        print()
        print("→ scenario §11 Job 2: batch 가능 시 1 call/5min, 1-by-1 시 3 calls/5min")


if __name__ == "__main__":
    main()
