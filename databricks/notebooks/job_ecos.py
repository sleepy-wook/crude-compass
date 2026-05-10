# Databricks notebook source
# MAGIC %md
# MAGIC # Job 6 — ecos_daily (KRW/USD)
# MAGIC
# MAGIC ## 시나리오 v2 매핑
# MAGIC - § 7 #5 ECOS 한국은행 (KRW/USD 일 1회)
# MAGIC - § 12 #6 cron `0 18 * * 1-5` (평일 장 마감 후)
# MAGIC
# MAGIC ## API
# MAGIC - https://ecos.bok.or.kr/api/StatisticSearch/{key}/json/kr/1/1000/731Y004/D/{start}/{end}/0000001
# MAGIC - 731Y004 = 시장평균환율 통계표
# MAGIC - 0000001 = 원/미국달러(매매기준율)

# COMMAND ----------

# MAGIC %pip install --quiet httpx==0.28.1
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import json
from datetime import datetime, timezone, date, timedelta
from decimal import Decimal

import httpx
from pyspark.sql import Row
from pyspark.sql.types import (
    StructType, StructField, StringType, DateType, DecimalType
)

# COMMAND ----------

TARGET_TABLE = "crude_compass.bronze.fx_rates"
api_key = dbutils.secrets.get(scope="crude", key="ecos_api_key")

# Widget: mode (daily | historical) + hist_start
dbutils.widgets.dropdown("mode", "daily", ["daily", "historical"], "Run mode")
dbutils.widgets.text("hist_start", "2023-01-01", "Historical start date (YYYY-MM-DD)")
MODE = dbutils.widgets.get("mode")
HIST_START = dbutils.widgets.get("hist_start")

end_dt = date.today()
if MODE == "historical":
    start_dt = date.fromisoformat(HIST_START)
    page_size = 5000  # ~3.5년 daily ≈ 870 records, 안전 margin
else:
    start_dt = end_dt - timedelta(days=14)
    page_size = 100

start_str = start_dt.strftime("%Y%m%d")
end_str = end_dt.strftime("%Y%m%d")

ECOS_URL = (
    f"https://ecos.bok.or.kr/api/StatisticSearch/{api_key}/json/kr/1/{page_size}/"
    f"731Y004/D/{start_str}/{end_str}/0000001"
)
print(f"MODE={MODE}, range={start_dt} ~ {end_dt}, page_size={page_size}")

# COMMAND ----------

resp = httpx.get(ECOS_URL, timeout=30.0)
resp.raise_for_status()
data = resp.json()

# ECOS 응답: {"StatisticSearch": {"list_total_count": N, "row": [...]}}
items = data.get("StatisticSearch", {}).get("row", [])
print(f"  ✅ {len(items)} daily records ({start_str} ~ {end_str})")

# COMMAND ----------

rows = []
for item in items:
    period = item.get("TIME", "")  # YYYYMMDD
    value = item.get("DATA_VALUE", "")
    if not (period and value):
        continue
    try:
        d = date(int(period[:4]), int(period[4:6]), int(period[6:8]))
        rate = float(value)
    except (ValueError, TypeError):
        continue
    rows.append(Row(
        date=d,
        pair="USD/KRW",
        rate=Decimal(rate),
        source="ECOS",
    ))

# COMMAND ----------

if rows:
    schema = StructType([
        StructField("date", DateType(), False),
        StructField("pair", StringType(), False),
        StructField("rate", DecimalType(8, 2), False),
        StructField("source", StringType(), False),
    ])
    df = spark.createDataFrame(rows, schema=schema)
    df.createOrReplaceTempView("_fx_new")
    spark.sql(f"""
        MERGE INTO {TARGET_TABLE} t
        USING _fx_new s
        ON t.date = s.date AND t.pair = s.pair
        WHEN MATCHED THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *
    """)
    print(f"✅ MERGE {len(rows)} rows")
else:
    print("ℹ️  No rows")

dbutils.notebook.exit(json.dumps({"rows_written": len(rows)}))
