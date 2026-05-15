# Databricks notebook source
# MAGIC %md
# MAGIC # opec_momr_monthly + Document Intelligence
# MAGIC
# MAGIC OPEC MOMR PDF auto-fetch → UC Volume → `ai_parse_document()` SQL → LLM extraction.
# MAGIC bronze.opec_momr_parsed 적재 (saudi/iran/total production + demand forecast).
# MAGIC Cron: 매월 12일. 시나리오 §7 #6 + §9.6 Document Intelligence.

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

# Widget: target_month (YYYY-MM) — backfill specific month, or "auto" for latest
dbutils.widgets.text("target_month", "auto", "Target month (YYYY-MM, or 'auto' for latest)")
TARGET_MONTH_PARAM = dbutils.widgets.get("target_month")


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
                print(f"  found: {url}")
                return url, month_name, str(y)
            else:
                print(f"  {url} -> HTTP {resp.status_code}")
        except httpx.HTTPError as e:
            print(f"  {url} -> {e}")
    return None


def find_specific_pdf(year: int, month: int) -> tuple[str, str, str] | None:
    """특정 month PDF 탐색."""
    month_name = MONTH_NAMES[month - 1]
    url = OPEC_URL_TEMPLATE.format(month=month_name, year=year)
    try:
        resp = httpx.head(url, timeout=15.0, follow_redirects=True)
        if resp.status_code == 200:
            return url, month_name, str(year)
        # try -1 suffix variant
        url2 = url.replace(".pdf", "-1.pdf")
        resp2 = httpx.head(url2, timeout=15.0, follow_redirects=True)
        if resp2.status_code == 200:
            return url2, month_name, str(year)
    except httpx.HTTPError:
        pass
    return None


def download_to_volume(url: str, year: str, month: str) -> str:
    """Download PDF → UC Volume. Returns volume path."""
    filename = f"momr_{year}_{month}.pdf"
    target = f"{VOLUME_PATH}/{filename}"

    resp = httpx.get(url, timeout=120.0, follow_redirects=True)
    resp.raise_for_status()
    pdf_bytes = resp.content
    print(f"  downloaded {len(pdf_bytes)} bytes")

    # /Volumes/... 는 driver fs로 mount되어 binary write 가능 (dbutils.fs.put은 binary 미지원)
    local_path = target
    Path(local_path).write_bytes(pdf_bytes)
    print(f"  saved to {target}")
    return target

# COMMAND ----------

if TARGET_MONTH_PARAM and TARGET_MONTH_PARAM != "auto":
    try:
        yy, mm = TARGET_MONTH_PARAM.split("-")
        found = find_specific_pdf(int(yy), int(mm))
        print(f"  TARGET_MONTH={TARGET_MONTH_PARAM} → found={found}")
    except Exception as e:
        print(f"  invalid target_month '{TARGET_MONTH_PARAM}': {e}")
        found = None
else:
    found = find_latest_pdf()

if not found:
    print("No PDF found - skipping")
    dbutils.notebook.exit(json.dumps({"status": "skipped", "reason": "no_pdf_found"}))

url, month_name, year = found
volume_path = download_to_volume(url, year, month_name)
report_month = f"{year}-{MONTH_NAMES.index(month_name) + 1:02d}"

# COMMAND ----------

# MAGIC %md
# MAGIC ## ai_parse_document() — Document Intelligence

# COMMAND ----------

# `ai_parse_document()` GA function. Output VARIANT, access via `:` operator.
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
print(f"  parsed: {text_len} chars, pages={n_pages}, elements={n_elements}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## LLM extraction — Saudi/Iran/OPEC total/Demand
# MAGIC
# MAGIC parsed_content → relevant element 추출 (keyword + digit density) → LLM JSON extraction.
# MAGIC LLM 실패 시 regex range-based fallback.

# COMMAND ----------

import re

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

w = WorkspaceClient()


def extract_relevant_sections(parsed_json_str: str) -> str:
    """Document Intelligence JSON에서 production/demand 관련 element 선별.

    v2: keyword match + digit density score 기반. 짧은 ToC entry 제외.

    JSON 구조 2가지 모두 처리:
    - {"document": {"elements": [...]}}  (bronze 저장 raw)
    - {"elements": [...]}                  (cast(parsed:document AS STRING) 결과)
    """
    if not parsed_json_str:
        return ""
    try:
        doc = json.loads(parsed_json_str)
    except json.JSONDecodeError:
        return parsed_json_str[:30000]

    # 양쪽 구조 모두 대응
    if isinstance(doc, dict) and "elements" in doc:
        elements = doc.get("elements") or []
    else:
        elements = (doc.get("document") or {}).get("elements", []) or []
    keywords = [
        "saudi arabia", "iran (i.r.)", "iran (ir", "iran islamic",
        "total opec", "non-opec liquids", "world oil demand",
        "opec crude oil production",
    ]
    # Score by keyword hits + digit density
    scored: list[tuple[int, str]] = []
    for el in elements:
        if not isinstance(el, dict):
            continue
        text = el.get("content") or el.get("description") or ""
        if not text or len(text) < 50:
            continue
        text_lc = text.lower()
        kw_hits = sum(1 for kw in keywords if kw in text_lc)
        digits = sum(1 for c in text if c.isdigit())
        # 숫자 10+ + 키워드 1+ → production/demand table 후보
        if kw_hits >= 1 and digits >= 10:
            scored.append((kw_hits * 100 + digits, text.strip()))
    scored.sort(reverse=True)
    relevant = [s[1] for s in scored[:30]]
    joined = "\n\n---\n".join(relevant)

    if len(joined) < 500:
        # fallback: numeric-heavy table-like elements
        all_tables = []
        for el in elements:
            if isinstance(el, dict) and el.get("type") in ("table", "list"):
                t = el.get("content") or el.get("description") or ""
                if t and sum(1 for c in t if c.isdigit()) > 20:
                    all_tables.append(t.strip())
        joined = "\n\n---\n".join(all_tables[:50])
    return joined[:30000]  # context cap


def regex_fallback(text: str) -> dict:
    """Range-based fallback. 연도(2025/2026) false positive 방지.

    Saudi production은 7-12M kbbl/d range, Iran 1.5-4.5M, OPEC total 25-35M, demand 95-115M.
    """
    out: dict = {}
    RANGES = {
        "saudi_production_kbbl_d":  (7000, 12000),
        "iran_production_kbbl_d":   (1500, 4500),
        "opec_total_kbbl_d":        (25000, 35000),
        "forecast_demand_kbbl_d":   (95000, 115000),
    }

    def find_in_range(name_pat: str, lo: int, hi: int) -> float | None:
        for m in re.finditer(rf"{name_pat}([\s\S]{{0,500}})", text, flags=re.IGNORECASE):
            ctx = m.group(1)
            for nm in re.finditer(r"\b(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d{4,6}(?:\.\d+)?)\b", ctx):
                raw = nm.group(1).replace(",", "")
                try:
                    v = float(raw)
                    if lo <= v <= hi:
                        return v
                except ValueError:
                    pass
        return None

    for k, p in [
        ("saudi_production_kbbl_d", r"Saudi\s+Arabia"),
        ("iran_production_kbbl_d",  r"Iran\s*\(?I\.?R\.?"),
        ("opec_total_kbbl_d",       r"Total\s+OPEC"),
        ("forecast_demand_kbbl_d",  r"world\s+oil\s+demand"),
    ]:
        lo, hi = RANGES[k]
        v = find_in_range(p, lo, hi)
        if v:
            out[k] = v
    return out


text_excerpt = extract_relevant_sections(parsed_content)
print(f"  relevant text extracted: {len(text_excerpt)} chars")
print(f"  preview: {text_excerpt[:300]}")

# Step 2: LLM extraction
extraction_prompt = """You extract numeric indicators from OPEC Monthly Oil Market Report.

Return ONLY a JSON object (no markdown, no explanation):
{
  "saudi_production_kbbl_d": <Saudi Arabia crude oil production, thousand barrels/day, latest available month>,
  "iran_production_kbbl_d": <Iran (I.R.) crude oil production, thousand barrels/day>,
  "opec_total_kbbl_d": <Total OPEC crude oil production, thousand barrels/day>,
  "forecast_demand_kbbl_d": <World oil demand forecast for next quarter, thousand barrels/day>
}

Use null if a value is not in the text.
Numbers are usually 4-5 digits (e.g., 9083 for Saudi). Return ONLY the JSON object."""

extracted: dict = {}
try:
    resp = w.serving_endpoints.query(
        name=LLM_ENDPOINT,
        messages=[
            ChatMessage(role=ChatMessageRole.SYSTEM, content=extraction_prompt),
            ChatMessage(role=ChatMessageRole.USER, content=text_excerpt),
        ],
        max_tokens=400,
        temperature=0.0,
    )
    raw = resp.choices[0].message.content if resp.choices else "{}"
    print(f"  LLM raw response (first 500 chars): {raw[:500]}")

    # markdown code fence 강건 stripping
    raw = raw.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", raw)
    if fence_match:
        raw = fence_match.group(1)
    else:
        # no fence, try to find first { ... }
        brace = re.search(r"(\{[\s\S]*\})", raw)
        if brace:
            raw = brace.group(1)

    extracted = json.loads(raw)
    # 값 정제 (string → float, kbbl 단위 sanity check)
    for k, v in list(extracted.items()):
        if v is None:
            continue
        if isinstance(v, str):
            v = re.sub(r"[^\d.\-]", "", v) or None
            if v:
                v = float(v)
        if isinstance(v, (int, float)):
            if not (100 < float(v) < 200000):
                # outlier — sanity drop
                extracted[k] = None
            else:
                extracted[k] = float(v)
except Exception as e:
    print(f"  LLM extraction failed: {e}")

if not all(extracted.get(k) for k in [
    "saudi_production_kbbl_d", "iran_production_kbbl_d",
    "opec_total_kbbl_d", "forecast_demand_kbbl_d"
]):
    print("  regex fallback for missing fields")
    fb = regex_fallback(text_excerpt)
    for k, v in fb.items():
        if not extracted.get(k):
            extracted[k] = v

print(f"  Extracted: {extracted}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## INSERT into bronze.opec_momr_parsed

# COMMAND ----------

# 기존 row 덮어쓰기 (월별 idempotent)
spark.sql(f"DELETE FROM {TARGET_TABLE} WHERE report_month = '{report_month}'")

# Driver memory row → DataFrame INSERT (명시 schema for ArrayType inference 방지)
from pyspark.sql import Row as SparkRow
from pyspark.sql.types import (
    StructType, StructField, StringType, TimestampType,
    ArrayType, IntegerType, DecimalType
)
from decimal import Decimal

def _dec(v):
    return Decimal(str(v)) if v is not None else None

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
print(f"\n{report_month} OPEC MOMR parsed + extracted into {TARGET_TABLE}")

dbutils.notebook.exit(json.dumps({
    "status": "success",
    "report_month": report_month,
    "pages": n_pages,
    "text_chars": text_len,
    "extracted_keys": list(extracted.keys()),
}))
