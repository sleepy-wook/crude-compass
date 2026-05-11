# Databricks notebook source
# MAGIC %md
# MAGIC # Job 5 — eia_weekly
# MAGIC
# MAGIC ## 시나리오 v2 매핑
# MAGIC - § 7 #4 EIA Open Data API (정기 평시 시그널)
# MAGIC - § 12 #5 cron `0 18 * * 3` (수요일 18:00 EIA 발표 직후)
# MAGIC - § 16 importance 60 anchor (정기 시그널)
# MAGIC
# MAGIC ## API
# MAGIC - https://api.eia.gov/v2/petroleum/stoc/wstk/data/  (Weekly Stocks)
# MAGIC - series_id: WCESTUS1 (U.S. commercial crude stocks, kbbl)

# COMMAND ----------

# MAGIC %pip install --quiet httpx==0.28.1
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import json
from datetime import datetime, timezone, date
from decimal import Decimal

import httpx
from pyspark.sql import Row
from pyspark.sql.types import (
    StructType, StructField, StringType, TimestampType, DateType, DecimalType
)

# COMMAND ----------

EIA_API = "https://api.eia.gov/v2/petroleum/stoc/wstk/data/"
TARGET_TABLE = "crude_compass.bronze.eia_inventory"

api_key = dbutils.secrets.get(scope="crude", key="eia_api_key")

# Widget: mode + hist_start
dbutils.widgets.dropdown("mode", "weekly", ["weekly", "historical"], "Run mode")
dbutils.widgets.text("hist_start", "2023-01-01", "Historical start (YYYY-MM-DD)")
MODE = dbutils.widgets.get("mode")
HIST_START = dbutils.widgets.get("hist_start")

# COMMAND ----------

def fetch_eia(series_id: str, length: int = 10, start_date: str | None = None) -> list[dict]:
    """EIA v2 API — weekly crude stocks. historical mode: start_date 지정."""
    params = {
        "api_key": api_key,
        "frequency": "weekly",
        "data[0]": "value",
        "facets[series][]": series_id,
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "length": length,
    }
    if start_date:
        params["start"] = start_date
    resp = httpx.get(EIA_API, params=params, timeout=30.0)
    resp.raise_for_status()
    data = resp.json().get("response", {}).get("data", [])
    return data

# COMMAND ----------

# 핵심 series:
# - WCESTUS1: U.S. Commercial Crude Stocks (kbbl)
# - WCSSTUS1: SPR Crude Stocks (kbbl)
SERIES = [
    {"id": "WCESTUS1", "type": "commercial"},
    {"id": "WCSSTUS1", "type": "spr"},
]

now = datetime.now(timezone.utc)
all_rows = []

# historical mode: 3년 = ~170 weeks
fetch_length = 5000 if MODE == "historical" else 8
fetch_start = HIST_START if MODE == "historical" else None
print(f"MODE={MODE}, length={fetch_length}, start={fetch_start}")

for s in SERIES:
    print(f"\n─── EIA series {s['id']} ({s['type']}) ───")
    try:
        data = fetch_eia(s["id"], length=fetch_length, start_date=fetch_start)
        print(f"  ✅ {len(data)} weekly records")

        # WoW 변화량 계산을 위해 정렬
        data_sorted = sorted(data, key=lambda d: d.get("period", ""))
        prev_value = None
        for d in data_sorted:
            period = d.get("period", "")  # YYYY-MM-DD
            value = d.get("value")
            if value is None or not period:
                continue
            try:
                value_f = float(value)
                week_end = date.fromisoformat(period)
            except (ValueError, TypeError):
                continue

            delta = value_f - prev_value if prev_value is not None else None

            all_rows.append(Row(
                week_ending=week_end,
                series_id=s["id"],
                inventory_type=s["type"],
                value_kbbl=Decimal(value_f),
                delta_vs_prev_wk=Decimal(delta) if delta is not None else None,
                fetched_at=now,
                source="EIA Open Data API",
            ))
            prev_value = value_f
    except Exception as e:
        print(f"  ⚠️  failed: {e}")

print(f"\nTotal {len(all_rows)} rows")

# COMMAND ----------

if all_rows:
    schema = StructType([
        StructField("week_ending", DateType(), False),
        StructField("series_id", StringType(), False),
        StructField("inventory_type", StringType(), False),
        StructField("value_kbbl", DecimalType(12, 2), False),
        StructField("delta_vs_prev_wk", DecimalType(10, 2), True),
        StructField("fetched_at", TimestampType(), False),
        StructField("source", StringType(), False),
    ])
    df = spark.createDataFrame(all_rows, schema=schema)

    # Idempotent: week_ending + series_id 중복 제거 (MERGE)
    df.createOrReplaceTempView("_eia_new")
    spark.sql(f"""
        MERGE INTO {TARGET_TABLE} t
        USING _eia_new s
        ON t.week_ending = s.week_ending AND t.series_id = s.series_id
        WHEN MATCHED THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *
    """)
    print(f"✅ MERGE {len(all_rows)} rows into {TARGET_TABLE}")
else:
    print("ℹ️  No rows")

dbutils.notebook.exit(json.dumps({"rows_written": len(all_rows)}))
