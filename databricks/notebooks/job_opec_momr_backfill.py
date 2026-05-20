# Databricks notebook source
# MAGIC %md
# MAGIC # OPEC MOMR Batch Backfill — 2020-2025
# MAGIC
# MAGIC 7년 backtest용 ~72 PDFs 일괄 추출. job_opec_momr.py와 동일 로직, 72개월 loop.
# MAGIC ~$7-10, ~3h sequential.

# COMMAND ----------

# D-2 optimization: subprocess pip = no restartPython 60s overhead.

# COMMAND ----------

import importlib
import subprocess
import sys


def _ensure_package(import_name: str, install_spec: str):
    try:
        importlib.import_module(import_name)
    except ImportError:
        print(f"  installing {install_spec}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", install_spec])


_ensure_package("httpx", "httpx==0.28.1")

import json
import re
import time
from datetime import datetime, timezone, date
from pathlib import Path

import httpx
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

# COMMAND ----------

OPEC_URL_TEMPLATE = "https://www.opec.org/assets/assetdb/momr-{month}-{year}.pdf"
VOLUME_PATH = "/Volumes/crude_compass/bronze/opec_pdfs"
TARGET_TABLE = "crude_compass.bronze.opec_momr_parsed"
LLM_ENDPOINT = "databricks-claude-haiku-4-5"

MONTH_NAMES = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
]

# Widget — year range
dbutils.widgets.text("start_year", "2020", "Start year")
dbutils.widgets.text("end_year", "2025", "End year")
START_YEAR = int(dbutils.widgets.get("start_year"))
END_YEAR = int(dbutils.widgets.get("end_year"))

# Build target months
TARGETS = []
for y in range(START_YEAR, END_YEAR + 1):
    for m in range(1, 13):
        TARGETS.append((y, m))

print(f"Backfill range: {START_YEAR}-01 ~ {END_YEAR}-12 = {len(TARGETS)} months")

# COMMAND ----------

# Skip already-processed months
existing = spark.sql(f"""
    SELECT report_month FROM {TARGET_TABLE}
    WHERE saudi_production_kbbl_d IS NOT NULL
""").collect()
already_done = {r.report_month for r in existing}
print(f"Already done ({len(already_done)}): {sorted(already_done)[-5:]}...")

PENDING = [(y, m) for (y, m) in TARGETS if f"{y}-{m:02d}" not in already_done]
print(f"Pending: {len(PENDING)} months")

# COMMAND ----------

# MAGIC %md
# MAGIC ## PDF download helpers

# COMMAND ----------

def find_pdf(year, month):
    month_name = MONTH_NAMES[month - 1]
    candidates = [
        OPEC_URL_TEMPLATE.format(month=month_name, year=year),
        OPEC_URL_TEMPLATE.format(month=month_name, year=year).replace(".pdf", "-1.pdf"),
        OPEC_URL_TEMPLATE.format(month=month_name, year=year).replace(".pdf", "-2.pdf"),
    ]
    for url in candidates:
        try:
            resp = httpx.head(url, timeout=15.0, follow_redirects=True)
            if resp.status_code == 200:
                return url, month_name, str(year)
        except httpx.HTTPError:
            continue
    return None


def download_to_volume(url, year, month):
    filename = f"momr_{year}_{month}.pdf"
    target = f"{VOLUME_PATH}/{filename}"
    resp = httpx.get(url, timeout=120.0, follow_redirects=True)
    resp.raise_for_status()
    Path(target).write_bytes(resp.content)
    return target


# COMMAND ----------

# MAGIC %md
# MAGIC ## Extraction helpers (job_opec_momr.py v2와 동일)

# COMMAND ----------

def extract_relevant_sections(parsed_json_str):
    if not parsed_json_str: return ""
    try:
        doc = json.loads(parsed_json_str)
    except json.JSONDecodeError:
        return parsed_json_str[:30000]
    if isinstance(doc, dict) and "elements" in doc:
        elements = doc.get("elements") or []
    else:
        elements = (doc.get("document") or {}).get("elements", []) or []
    keywords = [
        "saudi arabia", "iran (i.r.)", "iran (ir", "iran islamic",
        "total opec", "non-opec liquids", "world oil demand",
        "opec crude oil production",
    ]
    scored = []
    for el in elements:
        if not isinstance(el, dict): continue
        text = el.get("content") or el.get("description") or ""
        if not text or len(text) < 50: continue
        text_lc = text.lower()
        kw_hits = sum(1 for kw in keywords if kw in text_lc)
        digits = sum(1 for c in text if c.isdigit())
        if kw_hits >= 1 and digits >= 10:
            scored.append((kw_hits * 100 + digits, text.strip()))
    scored.sort(reverse=True)
    relevant = [s[1] for s in scored[:30]]
    joined = "\n\n---\n".join(relevant)
    return joined[:30000]


def regex_fallback(text):
    out = {}
    RANGES = {
        "saudi_production_kbbl_d":  (7000, 12000),
        "iran_production_kbbl_d":   (1500, 4500),
        "opec_total_kbbl_d":        (25000, 35000),
        "forecast_demand_kbbl_d":   (95000, 115000),
    }
    def find_in_range(name_pat, lo, hi):
        for m in re.finditer(rf"{name_pat}([\s\S]{{0,500}})", text, flags=re.IGNORECASE):
            ctx = m.group(1)
            for nm in re.finditer(r"\b(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d{4,6}(?:\.\d+)?)\b", ctx):
                raw = nm.group(1).replace(",", "")
                try:
                    v = float(raw)
                    if lo <= v <= hi: return v
                except ValueError: pass
        return None
    for k, p in [
        ("saudi_production_kbbl_d", r"Saudi\s+Arabia"),
        ("iran_production_kbbl_d",  r"Iran\s*\(?I\.?R\.?"),
        ("opec_total_kbbl_d",       r"Total\s+OPEC"),
        ("forecast_demand_kbbl_d",  r"world\s+oil\s+demand"),
    ]:
        lo, hi = RANGES[k]
        v = find_in_range(p, lo, hi)
        if v: out[k] = v
    return out


EXTRACTION_PROMPT = """You extract numeric indicators from OPEC Monthly Oil Market Report.

Return ONLY a JSON object (no markdown, no explanation):
{
  "saudi_production_kbbl_d": <Saudi Arabia crude oil production, thousand barrels/day, latest available month>,
  "iran_production_kbbl_d": <Iran (I.R.) crude oil production, thousand barrels/day>,
  "opec_total_kbbl_d": <Total OPEC crude oil production, thousand barrels/day>,
  "forecast_demand_kbbl_d": <World oil demand forecast for next quarter, thousand barrels/day>
}

Use null if a value is not in the text.
Numbers are usually 4-5 digits (e.g., 9083 for Saudi). Return ONLY the JSON object."""


w = WorkspaceClient()


def extract_indicators(parsed_content):
    extracted = {}
    excerpt = extract_relevant_sections(parsed_content)
    if not excerpt or len(excerpt) < 500:
        return regex_fallback(parsed_content[:25000])

    try:
        resp = w.serving_endpoints.query(
            name=LLM_ENDPOINT,
            messages=[
                ChatMessage(role=ChatMessageRole.SYSTEM, content=EXTRACTION_PROMPT),
                ChatMessage(role=ChatMessageRole.USER, content=excerpt),
            ],
            max_tokens=400, temperature=0.0,
        )
        raw = resp.choices[0].message.content if resp.choices else "{}"
        raw = raw.strip()
        fence = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", raw)
        if fence: raw = fence.group(1)
        else:
            brace = re.search(r"(\{[\s\S]*\})", raw)
            if brace: raw = brace.group(1)
        extracted = json.loads(raw)
        for k, v in list(extracted.items()):
            if v is None: continue
            if isinstance(v, str):
                v = re.sub(r"[^\d.\-]", "", v) or None
                if v: v = float(v)
            if isinstance(v, (int, float)):
                if not (100 < float(v) < 200000):
                    extracted[k] = None
                else:
                    extracted[k] = float(v)
    except Exception as e:
        print(f"    LLM fail: {e}")

    # regex fallback for missing
    if not all(extracted.get(k) for k in [
        "saudi_production_kbbl_d", "iran_production_kbbl_d",
        "opec_total_kbbl_d", "forecast_demand_kbbl_d"
    ]):
        fb = regex_fallback(excerpt)
        for k, v in fb.items():
            if not extracted.get(k): extracted[k] = v
    return extracted


# COMMAND ----------

# MAGIC %md
# MAGIC ## Main loop — sequential 72 PDFs

# COMMAND ----------

from pyspark.sql.types import (
    StructType, StructField, StringType, TimestampType,
    ArrayType, IntegerType, DecimalType
)
from pyspark.sql import Row as SparkRow
from decimal import Decimal

insert_schema = StructType([
    StructField("report_month", StringType(), False),
    StructField("pdf_volume_path", StringType(), False),
    StructField("parsed_at", TimestampType(), False),
    StructField("parsed_content", StringType(), True),
    StructField("pages", ArrayType(StructType([
        StructField("page_num", IntegerType(), True),
        StructField("content", StringType(), True),
    ])), True),
    StructField("tables", ArrayType(StringType()), True),
    StructField("saudi_production_kbbl_d", DecimalType(10, 2), True),
    StructField("iran_production_kbbl_d", DecimalType(10, 2), True),
    StructField("opec_total_kbbl_d", DecimalType(10, 2), True),
    StructField("forecast_demand_kbbl_d", DecimalType(10, 2), True),
    StructField("extraction_model", StringType(), True),
])

def _dec(v):
    return Decimal(str(v)) if v is not None else None

success_count = 0
fail_count = 0
t0 = time.time()

for idx, (year, month) in enumerate(PENDING):
    elapsed = time.time() - t0
    if idx > 0:
        eta = elapsed / idx * (len(PENDING) - idx)
        print(f"\n[{idx}/{len(PENDING)}] {elapsed:.0f}s elapsed, ETA {eta:.0f}s")
    report_month = f"{year}-{month:02d}"
    print(f"\n  === {report_month} ===")

    found = find_pdf(year, month)
    if not found:
        print(f"    no PDF found")
        fail_count += 1
        continue
    url, month_name, year_str = found
    print(f"    found {url}")

    try:
        volume_path = download_to_volume(url, year_str, month_name)
    except Exception as e:
        print(f"    download fail: {e}")
        fail_count += 1
        continue

    parse_sql = f"""
WITH parsed AS (
    SELECT
        '{report_month}'                                       AS report_month,
        '{volume_path}'                                        AS pdf_volume_path,
        current_timestamp()                                    AS parsed_at,
        ai_parse_document(content)                             AS parsed
    FROM read_files('{volume_path}', format => 'binaryFile')
)
SELECT
    report_month, pdf_volume_path, parsed_at,
    cast(parsed:document AS STRING)                            AS parsed_content,
    try_cast(parsed:document:pages AS ARRAY<STRUCT<page_num INT, content STRING>>) AS pages,
    transform(
        try_cast(parsed:document:elements AS ARRAY<VARIANT>),
        e -> cast(e AS STRING)
    )                                                          AS tables
FROM parsed
"""
    try:
        parsed_row = spark.sql(parse_sql).collect()[0]
        parsed_content = parsed_row["parsed_content"] or ""
        pages_list = parsed_row["pages"] or []
        tables_list = parsed_row["tables"] or []
    except Exception as e:
        print(f"    parse fail: {e}")
        fail_count += 1
        continue

    extracted = extract_indicators(parsed_content)
    print(f"    extracted: {extracted}")

    # Idempotent insert
    spark.sql(f"DELETE FROM {TARGET_TABLE} WHERE report_month = '{report_month}'")
    new_row = SparkRow(
        report_month=parsed_row["report_month"],
        pdf_volume_path=parsed_row["pdf_volume_path"],
        parsed_at=parsed_row["parsed_at"],
        parsed_content=parsed_content,
        pages=pages_list or [],
        tables=tables_list or [],
        saudi_production_kbbl_d=_dec(extracted.get("saudi_production_kbbl_d")),
        iran_production_kbbl_d=_dec(extracted.get("iran_production_kbbl_d")),
        opec_total_kbbl_d=_dec(extracted.get("opec_total_kbbl_d")),
        forecast_demand_kbbl_d=_dec(extracted.get("forecast_demand_kbbl_d")),
        extraction_model=LLM_ENDPOINT,
    )
    insert_df = spark.createDataFrame([new_row], schema=insert_schema)
    insert_df.write.mode("append").saveAsTable(TARGET_TABLE)
    print(f"    {report_month} done")
    success_count += 1

# COMMAND ----------

elapsed = time.time() - t0
print(f"\n=== Backfill 완료 ===")
print(f"Success: {success_count} / Fail: {fail_count} / Total: {len(PENDING)}")
print(f"Elapsed: {elapsed:.0f}s")

# Final row check
n_rows = spark.sql(f"""
    SELECT COUNT(*) FROM {TARGET_TABLE} WHERE saudi_production_kbbl_d IS NOT NULL
""").collect()[0][0]
print(f"Total OPEC rows with Saudi extracted: {n_rows}")

dbutils.notebook.exit(json.dumps({
    "success": success_count, "fail": fail_count, "total": len(PENDING), "elapsed_s": int(elapsed),
}))
