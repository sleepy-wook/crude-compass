"""OilPriceAPI ingestion → bronze.oil_prices.

Lakeflow Job tasks (Tier 1 Daily + Tier 2 Realtime 5분 cron).
Databricks Runtime: 15.4 LTS+ (Spark 3.5+, Python 3.11+).

Secret 등록 (사용자 작업):
    databricks secrets put-secret crude-compass oilpriceapi-key
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

import httpx

# Databricks Runtime — spark는 자동 주입
from pyspark.sql import SparkSession  # noqa: F401  (런타임 자동 주입, 정적 분석용)
from pyspark.sql.types import (
    DoubleType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

# OilPriceAPI Developer tier endpoints
BASE_URL = "https://api.oilpriceapi.com/v1"
PRODUCTS = ["WTI_USD", "BRENT_CRUDE_USD", "DUBAI_CRUDE_USD"]
TARGET_TABLE = "crude_compass.bronze.oil_prices"

OIL_PRICES_SCHEMA = StructType(
    [
        StructField("fetched_at", TimestampType(), nullable=False),
        StructField("source", StringType(), nullable=False),
        StructField("product", StringType(), nullable=False),
        StructField("price_usd", DoubleType(), nullable=False),
        StructField("raw", StringType(), nullable=True),
    ]
)


def _api_key() -> str:
    """Read API key from Databricks secret scope or env (local dev)."""
    # Databricks Job: dbutils.secrets.get(scope="crude-compass", key="oilpriceapi-key")
    # Job task에서는 dbutils가 spark context로 노출됨; 여기는 env fallback 패턴
    key = os.environ.get("OILPRICEAPI_KEY")
    if not key:
        try:
            # 동적 import — 로컬 dev에서는 dbutils 없음
            from databricks.sdk.runtime import dbutils  # type: ignore

            key = dbutils.secrets.get(scope="crude-compass", key="oilpriceapi-key")
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(
                "OILPRICEAPI_KEY env var or 'crude-compass/oilpriceapi-key' secret 필요"
            ) from e
    return key


def fetch_one(client: httpx.Client, product: str) -> dict[str, Any]:
    """OilPriceAPI v1 latest price for a single product."""
    response = client.get(f"{BASE_URL}/prices/latest", params={"by_code": product})
    response.raise_for_status()
    payload = response.json()
    # payload shape: {"status":"success","data":{"price":78.42,"code":"BRENT_CRUDE_USD",...}}
    if payload.get("status") != "success":
        raise RuntimeError(f"OilPriceAPI {product} failed: {payload}")
    return payload["data"]


def fetch_all() -> list[tuple[Any, ...]]:
    """Fetch 3 products. Returns rows ready for Spark DataFrame creation."""
    api_key = _api_key()
    now = datetime.now(timezone.utc)
    rows: list[tuple[Any, ...]] = []
    with httpx.Client(timeout=10.0, headers={"Authorization": f"Token {api_key}"}) as client:
        for product in PRODUCTS:
            try:
                data = fetch_one(client, product)
                rows.append(
                    (
                        now,
                        "oilpriceapi",
                        product,
                        float(data["price"]),
                        json.dumps(data, ensure_ascii=False),
                    )
                )
            except Exception as e:  # noqa: BLE001
                # Tier 2 5분 cron 안정성 — 1개 실패는 다른 제품 fetch 계속
                print(f"[oil_prices] {product} fetch failed: {e}")
                continue
    return rows


def main() -> None:
    """Lakeflow Job entrypoint. Append rows to Bronze Delta."""
    from pyspark.sql import SparkSession

    spark = SparkSession.builder.getOrCreate()
    rows = fetch_all()
    if not rows:
        print("[oil_prices] no rows fetched, skipping write")
        return

    df = spark.createDataFrame(rows, schema=OIL_PRICES_SCHEMA)
    (df.write.mode("append").saveAsTable(TARGET_TABLE))
    print(f"[oil_prices] appended {df.count()} rows to {TARGET_TABLE}")


if __name__ == "__main__":
    main()
