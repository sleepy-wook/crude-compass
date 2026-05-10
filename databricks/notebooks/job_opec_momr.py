# Databricks notebook source
# MAGIC %md
# MAGIC # Job 7 — opec_momr_monthly + Document Intelligence ⭐
# MAGIC
# MAGIC ## 시나리오 v2 매핑
# MAGIC - § 7 #6 OPEC MOMR PDF (월간)
# MAGIC - § 9.6 Document Intelligence — `ai_parse_document()` SQL 한 줄 시연
# MAGIC - § 12 #7 cron `0 0 12 * *` (매월 12일 — 보통 첫째~둘째 주 발표 후)
# MAGIC - § 16 importance 80 anchor (월 1회 정기)
# MAGIC
# MAGIC ## URL pattern (검증됨)
# MAGIC - https://www.opec.org/assets/assetdb/momr-{lowercase_month}-{year}.pdf
# MAGIC - 예: momr-april-2026.pdf, momr-may-2026.pdf
# MAGIC
# MAGIC ## 처리
# MAGIC 1. 최근 3개월 URL 시도 (HEAD 확인)
# MAGIC 2. PDF download → UC Volume `/Volumes/crude_compass/bronze/opec_pdfs/`
# MAGIC 3. `ai_parse_document()` → parsed text
# MAGIC 4. LLM extraction → 핵심 indicator (saudi/iran production)

# COMMAND ----------

# MAGIC %pip install --quiet httpx==0.28.1
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import json
from datetime import datetime, timezone, date
from pathlib import Path

import httpx

# COMMAND ----------

OPEC_URL_TEMPLATE = "https://www.opec.org/assets/assetdb/momr-{month}-{year}.pdf"
VOLUME_PATH = "/Volumes/crude_compass/bronze/opec_pdfs"
TARGET_TABLE = "crude_compass.bronze.opec_momr_parsed"
LLM_ENDPOINT = "databricks-claude-haiku-4-5"

MONTH_NAMES = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
]

# COMMAND ----------

def find_latest_pdf() -> tuple[str, str, str] | None:
    """최근 3개월 URL 시도 — HEAD로 존재 확인.

    Returns:
        (url, month_name, year_str) or None
    """
    today = date.today()
    for offset in range(0, 3):
        # offset 0 = 이번 달, 1 = 이전 달, 2 = 이전이전 달
        m = today.month - offset
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        month_name = MONTH_NAMES[m - 1]
        url = OPEC_URL_TEMPLATE.format(month=month_name, year=y)
        try:
            resp = httpx.head(url, timeout=15.0, follow_redirects=True)
            if resp.status_code == 200:
                print(f"  ✅ found: {url}")
                return url, month_name, str(y)
            else:
                print(f"  ❌ {url} → HTTP {resp.status_code}")
        except httpx.HTTPError as e:
            print(f"  ⚠️  {url} → {e}")
    return None


def download_to_volume(url: str, year: str, month: str) -> str:
    """Download PDF → UC Volume. Returns volume path."""
    filename = f"momr_{year}_{month}.pdf"
    target = f"{VOLUME_PATH}/{filename}"

    resp = httpx.get(url, timeout=120.0, follow_redirects=True)
    resp.raise_for_status()
    pdf_bytes = resp.content
    print(f"  📥 downloaded {len(pdf_bytes)} bytes")

    # UC Volume에 쓰기 — dbutils.fs.put은 binary 직접 안 됨, /Volumes path는 local fs로 보임
    local_path = target  # /Volumes/... 는 driver fs로 mount
    Path(local_path).write_bytes(pdf_bytes)
    print(f"  📁 saved to {target}")
    return target

# COMMAND ----------

found = find_latest_pdf()
if not found:
    print("⚠️  No recent OPEC MOMR PDF found — skipping (Sprint 2 day 5 manual upload fallback)")
    dbutils.notebook.exit(json.dumps({"status": "skipped", "reason": "no_pdf_found"}))

url, month_name, year = found
volume_path = download_to_volume(url, year, month_name)
report_month = f"{year}-{MONTH_NAMES.index(month_name) + 1:02d}"

# COMMAND ----------

# MAGIC %md
# MAGIC ## ai_parse_document() — SQL 한 줄 시연 ⭐

# COMMAND ----------

# Document Intelligence — `ai_parse_document()` GA function
# Output: VARIANT type. Access via `:` operator (not `.`).
parse_sql = f"""
WITH parsed AS (
    SELECT
        '{report_month}'                                       AS report_month,
        '{volume_path}'                                        AS pdf_volume_path,
        current_timestamp()                                    AS parsed_at,
        ai_parse_document(content)                             AS parsed
    FROM read_files(
        '{volume_path}',
        format => 'binaryFile'
    )
)
SELECT
    report_month,
    pdf_volume_path,
    parsed_at,
    -- VARIANT → string cast (전체 JSON dump)
    cast(parsed:document AS STRING)                            AS parsed_content,
    -- pages: VARIANT array → struct array via try_cast
    try_cast(parsed:document:pages AS ARRAY<STRUCT<page_num INT, content STRING>>) AS pages,
    -- elements (tables 포함) → JSON string array
    transform(
        try_cast(parsed:document:elements AS ARRAY<VARIANT>),
        e -> cast(e AS STRING)
    )                                                          AS tables
FROM parsed
"""

print("─── Running ai_parse_document() ───")
# Serverless는 cache() 미지원 → 한 번에 collect로 driver memory에 가져옴
parsed_row = spark.sql(parse_sql).collect()[0]
parsed_content = parsed_row["parsed_content"] or ""
pages_list = parsed_row["pages"] or []
tables_list = parsed_row["tables"] or []
text_len = len(parsed_content)
n_pages = len(pages_list)
n_elements = len(tables_list)
print(f"  ✅ parsed: {text_len} chars, pages={n_pages}, elements={n_elements}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## LLM extraction — 핵심 indicator

# COMMAND ----------

from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

# 첫 50000자 (production tables 보통 앞 부분)
text_excerpt = parsed_content[:50000]

extraction_prompt = """You are extracting key indicators from OPEC Monthly Oil Market Report.

Return JSON object:
{
  "saudi_production_kbbl_d": <number, Saudi Arabia crude production in thousand barrels per day>,
  "iran_production_kbbl_d": <number, Iran crude production>,
  "opec_total_kbbl_d": <number, OPEC total crude production>,
  "forecast_demand_kbbl_d": <number, OPEC world oil demand forecast>
}

If a value is not found, use null. Return JSON only, no other text."""

try:
    resp = w.serving_endpoints.query(
        name=LLM_ENDPOINT,
        messages=[
            {"role": "system", "content": extraction_prompt},
            {"role": "user", "content": text_excerpt[:30000]},
        ],
        max_tokens=300,
        temperature=0.0,
    )
    extracted_raw = resp.choices[0].message.content if resp.choices else "{}"
    extracted_raw = extracted_raw.strip()
    if extracted_raw.startswith("```"):
        extracted_raw = extracted_raw.split("```")[1].lstrip("json").strip()
    extracted = json.loads(extracted_raw)
except Exception as e:
    print(f"  ⚠️  LLM extraction failed: {e}")
    extracted = {}

print(f"  Extracted: {extracted}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## INSERT into bronze.opec_momr_parsed

# COMMAND ----------

# 기존 row 덮어쓰기 (월별 idempotent)
spark.sql(f"DELETE FROM {TARGET_TABLE} WHERE report_month = '{report_month}'")

# Driver memory의 row를 single-row DataFrame으로 다시 만들어 INSERT
from pyspark.sql import Row as SparkRow
from decimal import Decimal

def _dec(v):
    return Decimal(str(v)) if v is not None else None

new_row = SparkRow(
    report_month=parsed_row["report_month"],
    pdf_volume_path=parsed_row["pdf_volume_path"],
    parsed_at=parsed_row["parsed_at"],
    parsed_content=parsed_content,
    pages=pages_list,
    tables=tables_list,
    saudi_production_kbbl_d=_dec(extracted.get("saudi_production_kbbl_d")),
    iran_production_kbbl_d=_dec(extracted.get("iran_production_kbbl_d")),
    opec_total_kbbl_d=_dec(extracted.get("opec_total_kbbl_d")),
    forecast_demand_kbbl_d=_dec(extracted.get("forecast_demand_kbbl_d")),
    extraction_model=LLM_ENDPOINT,
)
insert_df = spark.createDataFrame([new_row])
insert_df.write.mode("append").saveAsTable(TARGET_TABLE)
print(f"\n✅ {report_month} OPEC MOMR parsed + extracted into {TARGET_TABLE}")

dbutils.notebook.exit(json.dumps({
    "status": "success",
    "report_month": report_month,
    "pages": n_pages,
    "text_chars": text_len,
    "extracted_keys": list(extracted.keys()),
}))
