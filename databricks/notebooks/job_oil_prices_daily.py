# Databricks notebook source
# MAGIC %md
# MAGIC # Job — oil_prices_daily (OPINET KNOC, Dubai 중심)
# MAGIC
# MAGIC ## 시나리오 v2 매핑
# MAGIC - § 부록 C Mock Backtest의 **price baseline = Dubai** (한국 정유사 중동 원유 70%+ 수입)
# MAGIC - § 7 #2 가격 source 보강 (OilPriceAPI realtime + OPINET daily close)
# MAGIC - EIA RBRTE 403 차단 우회 (todo.md blocker 해결)
# MAGIC
# MAGIC ## 데이터 source
# MAGIC - **출처**: OPINET (한국석유공사 https://www.opinet.co.kr) CSV download endpoint
# MAGIC - **종류**: Dubai (현물) / Brent (선물) / WTI (선물) 일별 close
# MAGIC - **기간**: 1996-01 ~ 현재 (오늘 close는 KNOC 공시 시점 이후)
# MAGIC - **응답**: cp949 인코딩 CSV (`기간,Dubai,Brent,WTI`)
# MAGIC - **robots.txt**: 미차단 (Yeti 외 허용)
# MAGIC - **제한**: Public web feature, fair-use 1회 일별 fetch 가정
# MAGIC
# MAGIC ## MODE
# MAGIC - `historical` — 2023-01-01 ~ 어제 일괄 (one-shot, ~864 rows × 3 ticker)
# MAGIC - `daily` — 어제 1일 (idempotent MERGE, cron 매일 18:00)

# COMMAND ----------

# MAGIC %pip install --quiet httpx==0.28.1
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import json
import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import httpx
from pyspark.sql import Row
from pyspark.sql.types import (
    StructType, StructField, StringType, DateType, DecimalType, TimestampType
)

# COMMAND ----------

TARGET_TABLE = "crude_compass.bronze.oil_prices_daily"
OPINET_CSV_URL = "https://www.opinet.co.kr/glopcoil_csv.do"
SOURCE = "OPINET KNOC"

# Widget으로 MODE 받음 (Job param). 기본값: daily
dbutils.widgets.dropdown("mode", "daily", ["daily", "historical"], "Run mode")
dbutils.widgets.text("hist_start", "2023-01-01", "Historical start date (YYYY-MM-DD)")
MODE = dbutils.widgets.get("mode")
HIST_START = dbutils.widgets.get("hist_start")

# 기간 결정
today = date.today()
yesterday = today - timedelta(days=1)
if MODE == "historical":
    sta_dt = date.fromisoformat(HIST_START)
    end_dt = yesterday
else:  # daily
    sta_dt = yesterday
    end_dt = yesterday

print(f"MODE={MODE}, range={sta_dt} ~ {end_dt}")

# COMMAND ----------

# OPINET form fields (브라우저 form 분석 결과)
form_data = [
    ("TERM", "D"),
    ("STA_Y", f"{sta_dt.year}"),
    ("STA_M", f"{sta_dt.month:02d}"),
    ("STA_D", f"{sta_dt.day:02d}"),
    ("END_Y", f"{end_dt.year}"),
    ("END_M", f"{end_dt.month:02d}"),
    ("END_D", f"{end_dt.day:02d}"),
    ("STDDATE", sta_dt.strftime("%Y%m%d")),
    ("ENDDATE", end_dt.strftime("%Y%m%d")),
    ("SEL_DIV", "div_dar"),  # USD/bbl 단위
    ("OILSRTCD", "001"),  # Dubai
    ("OILSRTCD", "002"),  # Brent
    ("OILSRTCD", "003"),  # WTI
    ("OILSRTCD1", "001"),
    ("OILSRTCD2", "002"),
    ("OILSRTCD3", "003"),
]
headers = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.opinet.co.kr/gloptotSelect.do",
}

with httpx.Client(timeout=60.0) as client:
    resp = client.post(OPINET_CSV_URL, data=form_data, headers=headers)
    resp.raise_for_status()
    text = resp.content.decode("cp949")

print(f"✅ fetched {len(text)} bytes")
print("--- HEAD ---")
print("\n".join(text.split("\n")[:3]))

# COMMAND ----------

# CSV parsing — `기간,Dubai,Brent,WTI` + `25년02월05일,82.07,82.10,76.93`
DATE_RE = re.compile(r"(\d{2})년(\d{1,2})월(\d{1,2})일")
TICKERS = ["DUBAI", "BRENT", "WTI"]

def parse_kor_date(s: str) -> date | None:
    m = DATE_RE.match(s.strip())
    if not m:
        return None
    yy, mm, dd = m.groups()
    # "23" ~ "26"은 2023-2026, "99"은 1999. 정유사 backtest 기준 2000~ assume 20xx
    year = 2000 + int(yy) if int(yy) < 80 else 1900 + int(yy)
    return date(year, int(mm), int(dd))

now_ts = datetime.now(timezone.utc).replace(tzinfo=None)
rows = []
lines = [l for l in text.strip().split("\n") if l.strip()]

for line in lines[1:]:  # skip header
    cols = line.split(",")
    if len(cols) < 4:
        continue
    d = parse_kor_date(cols[0])
    if d is None:
        continue
    for ticker, raw_price in zip(TICKERS, cols[1:4]):
        price_str = raw_price.strip()
        if not price_str:
            continue  # 당일 미공시 (예: 오늘 close)
        try:
            price = Decimal(price_str)
        except Exception:
            continue
        rows.append(Row(
            trade_date=d,
            ticker=ticker,
            price_usd=price,
            fetched_at=now_ts,
            source=SOURCE,
        ))

print(f"✅ parsed {len(rows)} rows ({len(lines)-1} trade days × ≤3 tickers)")
if rows:
    print("--- sample ---")
    for r in rows[:3]:
        print(f"  {r.trade_date} {r.ticker:6s} ${r.price_usd}")
    print("...")
    for r in rows[-3:]:
        print(f"  {r.trade_date} {r.ticker:6s} ${r.price_usd}")

# COMMAND ----------

if rows:
    schema = StructType([
        StructField("trade_date", DateType(), False),
        StructField("ticker", StringType(), False),
        StructField("price_usd", DecimalType(8, 2), False),
        StructField("fetched_at", TimestampType(), False),
        StructField("source", StringType(), False),
    ])
    df = spark.createDataFrame(rows, schema=schema)
    df.createOrReplaceTempView("_oil_new")
    spark.sql(f"""
        MERGE INTO {TARGET_TABLE} t
        USING _oil_new s
        ON t.trade_date = s.trade_date AND t.ticker = s.ticker
        WHEN MATCHED THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *
    """)
    print(f"✅ MERGE {len(rows)} rows into {TARGET_TABLE}")
else:
    print("ℹ️  No rows (KNOC 미공시 또는 빈 응답)")

# COMMAND ----------

# 검증: Dubai 최근 5일 + 호르무즈 위기 (2026-05-04 ~ 2026-05-08) 노출
print("\n=== Dubai 최근 7일 ===")
display(spark.sql(f"""
    SELECT trade_date, ticker, price_usd
    FROM {TARGET_TABLE}
    WHERE ticker = 'DUBAI'
    ORDER BY trade_date DESC
    LIMIT 7
"""))

# COMMAND ----------

dbutils.notebook.exit(json.dumps({
    "mode": MODE,
    "range_start": str(sta_dt),
    "range_end": str(end_dt),
    "rows_written": len(rows),
}))
