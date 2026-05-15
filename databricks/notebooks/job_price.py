# Databricks notebook source
# MAGIC %md
# MAGIC # price_pipeline_5min
# MAGIC
# MAGIC OilPriceAPI (Brent/WTI/Dubai) → bronze.oil_prices. 5분 cron.
# MAGIC 시나리오 §7 #2 + §8 Reactive Trigger (±2% spike).

# COMMAND ----------

# MAGIC %pip install --quiet httpx==0.28.1
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import json
import time
from datetime import datetime, timezone
from decimal import Decimal

import httpx
from pyspark.sql import Row
from pyspark.sql.functions import col, lag
from pyspark.sql.window import Window
from pyspark.sql.types import (
    StructType, StructField, StringType, TimestampType, DecimalType
)

# COMMAND ----------

OILPRICE_API = "https://api.oilpriceapi.com/v1/prices/latest"
TARGET_TABLE = "crude_compass.bronze.oil_prices"
TICKERS = ["BRENT_CRUDE_USD", "WTI_USD", "DUBAI_CRUDE_USD"]

api_key = dbutils.secrets.get(scope="crude", key="oilprice_api_key")

# COMMAND ----------

def fetch_price(ticker: str) -> dict | None:
    try:
        resp = httpx.get(
            OILPRICE_API,
            params={"by_code": ticker},
            headers={"Authorization": f"Token {api_key}"},
            timeout=10.0,
        )
        resp.raise_for_status()
        return resp.json().get("data")
    except (httpx.HTTPError, ValueError) as e:
        print(f"  {ticker} failed: {e}")
        return None

# COMMAND ----------

now = datetime.now(timezone.utc)
rows: list[Row] = []

for ticker in TICKERS:
    data = fetch_price(ticker)
    if not data:
        continue
    price = float(data.get("price", 0))
    if price <= 0:
        print(f"  {ticker} invalid price: {price}")
        continue
    rows.append(Row(
        fetched_at=now,
        ticker=ticker,
        price_usd=Decimal(f"{price:.2f}"),
        delta_pct_5min=None,
        source="OilPriceAPI",
        raw_response=json.dumps(data)[:2000],
    ))
    print(f"  {ticker}: ${price}")
    time.sleep(0.5)

print(f"\nFetched {len(rows)}/{len(TICKERS)} tickers")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Spike detection — 이전 row 대비 delta_pct_5min

# COMMAND ----------

if not rows:
    dbutils.notebook.exit(json.dumps({"rows_written": 0, "reason": "no_fetch"}))

schema = StructType([
    StructField("fetched_at", TimestampType(), False),
    StructField("ticker", StringType(), False),
    StructField("price_usd", DecimalType(8, 2), False),
    StructField("delta_pct_5min", DecimalType(5, 2), True),
    StructField("source", StringType(), False),
    StructField("raw_response", StringType(), True),
])
df_new = spark.createDataFrame(rows, schema=schema)

# 이전 ticker 별 가장 최근 가격 join
df_prev = (
    spark.read.table(TARGET_TABLE)
    .filter(col("fetched_at") < now)
    .groupBy("ticker")
    .agg({"fetched_at": "max"})
    .withColumnRenamed("max(fetched_at)", "prev_at")
)

if df_prev.count() > 0:
    df_prev_full = (
        spark.read.table(TARGET_TABLE)
        .alias("p")
        .join(df_prev.alias("d"), (col("p.ticker") == col("d.ticker")) & (col("p.fetched_at") == col("d.prev_at")))
        .selectExpr("p.ticker as ticker_prev", "p.price_usd as price_prev")
    )
    df_with_delta = (
        df_new.alias("n")
        .join(df_prev_full, col("n.ticker") == col("ticker_prev"), "left")
        .withColumn(
            "delta_pct_5min_calc",
            ((col("n.price_usd") - col("price_prev")) / col("price_prev") * 100).cast(DecimalType(5, 2)),
        )
        .selectExpr(
            "n.fetched_at",
            "n.ticker",
            "n.price_usd",
            "delta_pct_5min_calc as delta_pct_5min",
            "n.source",
            "n.raw_response",
        )
    )
else:
    df_with_delta = df_new

df_with_delta.write.mode("append").saveAsTable(TARGET_TABLE)
written = df_with_delta.count()

# Spike 감지 (시나리오 § 8 ±2% 트리거)
spikes = df_with_delta.filter(
    col("delta_pct_5min").isNotNull() & (
        (col("delta_pct_5min") >= 2.0) | (col("delta_pct_5min") <= -2.0)
    )
).collect()

if spikes:
    print(f"\nSPIKE detected: {len(spikes)} ticker(s)")
    for r in spikes:
        print(f"   {r.ticker}: {r.price_usd:+.2f} ({r.delta_pct_5min:+.2f}%)")
else:
    print(f"\n{written} rows appended, no spike")

# COMMAND ----------

dbutils.notebook.exit(json.dumps({
    "rows_written": written,
    "spike_count": len(spikes),
    "tickers": [r.ticker for r in spikes],
}))
