# Databricks notebook source
# MAGIC %md
# MAGIC # Sprint 3 Day 1 task 2 — Backtest Seed
# MAGIC
# MAGIC ## 시나리오 v2 매핑
# MAGIC - § 부록 C Mock Backtest 산출 (HEDGE 78% / OPP 71% / lead 12.4d)
# MAGIC - § 6 양방향 direction backtest
# MAGIC
# MAGIC ## 작업
# MAGIC 1. GDELT historical timelinetone — 5개월 (2025-12 ~ 2026-04)
# MAGIC 2. 7 queries (평시 5개 + 위기 2개)
# MAGIC 3. 일별 avg_tone + bucket 수 → bronze.news_articles 적재 (source_type='gdelt_backtest')
# MAGIC 4. Brent daily price (별도 — Sprint 3 day 3에서)
# MAGIC
# MAGIC ## Sprint 3 day 3에서
# MAGIC - Pattern Score threshold 70+/30- 돌파 시점 산출
# MAGIC - 30일 outcome (Brent ±10%) 매핑
# MAGIC - HEDGE 78% / OPP 71% 산출

# COMMAND ----------

# MAGIC %pip install --quiet httpx==0.28.1
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import hashlib
import json
import time
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict

import httpx
from pyspark.sql import Row
from pyspark.sql.functions import col
from pyspark.sql.types import (
    StructType, StructField, StringType, TimestampType, IntegerType,
    DoubleType, ArrayType
)

# COMMAND ----------

GDELT_API = "https://api.gdeltproject.org/api/v2/doc/doc"
TARGET_TABLE = "crude_compass.bronze.news_articles"

# 시나리오 §16 anchor + §6 양방향 direction
# 12 queries — 균형 잡힌 bullish/bearish 시그널 catch
# verify 결과 bearish 1.8% 편향 → 본질적 bearish query 5개 + default_direction 명시
#
# default_direction 의미:
#   - "bullish": query 자체가 가격 ↑ 시그널 (위기/공급차질). tone 부호와 무관하게 bullish.
#   - "bearish": query 자체가 가격 ↓ 시그널 (수요둔화/공급증가). tone 부호와 무관하게 bearish.
#   - "auto":    tone 부호로 추정 (geopolitical 기본값)
QUERIES = [
    # ─── Tier A 위기 (bullish 본질) ───────────────────────────────────
    {"label": "hormuz",          "query": "Strait of Hormuz Iran",                     "tier": "A", "category": "geopolitical", "horizon": "short",  "confidence": "high", "baseline": 75, "default_direction": "bullish"},
    {"label": "iran_sanctions",  "query": "Iran sanctions oil export",                 "tier": "A", "category": "policy",       "horizon": "medium", "confidence": "high", "baseline": 70, "default_direction": "bullish"},

    # ─── Tier B 평시 정기 (auto, tone 부호로 결정) ─────────────────────
    {"label": "opec_monthly",    "query": "OPEC monthly oil market report",            "tier": "B", "category": "policy",       "horizon": "medium", "confidence": "high", "baseline": 65, "default_direction": "auto"},
    {"label": "eia_inventory",   "query": "EIA crude oil inventory weekly",            "tier": "B", "category": "supply",       "horizon": "short",  "confidence": "high", "baseline": 60, "default_direction": "auto"},
    {"label": "saudi_osp",       "query": "Saudi Aramco OSP official",                 "tier": "B", "category": "supply",       "horizon": "medium", "confidence": "high", "baseline": 65, "default_direction": "auto"},
    {"label": "us_spr",          "query": "strategic petroleum reserve release",       "tier": "A", "category": "policy",       "horizon": "short",  "confidence": "high", "baseline": 60, "default_direction": "auto"},
    {"label": "china_demand",    "query": "China oil demand PMI",                      "tier": "A", "category": "demand",       "horizon": "medium", "confidence": "med",  "baseline": 55, "default_direction": "auto"},

    # ─── Tier A bearish 본질 (가격 ↓ 시그널, OPP zone catch) ⭐ NEW ──
    {"label": "china_recession",     "query": "China oil demand slowdown recession",   "tier": "A", "category": "demand",       "horizon": "medium", "confidence": "med",  "baseline": 60, "default_direction": "bearish"},
    {"label": "oecd_inventory_build","query": "OECD commercial crude inventory build", "tier": "A", "category": "supply",       "horizon": "medium", "confidence": "high", "baseline": 60, "default_direction": "bearish"},
    {"label": "saudi_osp_cut",       "query": "Saudi Aramco OSP price cut Asia",       "tier": "A", "category": "supply",       "horizon": "medium", "confidence": "high", "baseline": 65, "default_direction": "bearish"},
    {"label": "ev_adoption",         "query": "electric vehicle adoption oil demand peak", "tier": "B", "category": "demand",   "horizon": "long",   "confidence": "med",  "baseline": 50, "default_direction": "bearish"},
    {"label": "us_shale_surge",      "query": "US shale oil production record surge",  "tier": "A", "category": "supply",       "horizon": "medium", "confidence": "high", "baseline": 60, "default_direction": "bearish"},
]

# Backtest range — 3년 4개월 (2023-01 ~ 2026-04)
# 다양한 regime 포함: 2023 OPEC+ cut + Israel-Hamas, 2024 홍해 후티,
# 2025 중동 긴장 + 미 셰일, 2026 Q1-Q2 호르무즈 위기
# Dubai daily price (OPINET KNOC)와 동일 기간으로 매핑
START_DT = "20230101000000"
END_DT   = "20260430235959"

# COMMAND ----------

def fetch_timelinetone(query: str, start: str, end: str) -> list[dict]:
    params = {
        "query": query,
        "mode": "timelinetone",
        "format": "json",
        "startdatetime": start,
        "enddatetime": end,
    }
    for attempt in range(3):
        try:
            time.sleep(1)
            r = httpx.get(GDELT_API, params=params, timeout=60.0)
            if r.status_code == 429:
                time.sleep(2 ** (attempt + 1))
                continue
            r.raise_for_status()
            data = r.json()
            timeline = data.get("timeline", [])
            if timeline and timeline[0].get("data"):
                return timeline[0]["data"]
            return []
        except Exception as e:
            if attempt == 2:
                print(f"  ⚠️  failed: {e}")
                return []
            time.sleep(2 ** attempt)
    return []

# COMMAND ----------

def score_from_signal(label: str, q: dict, avg_tone: float, daily_value: float) -> dict:
    """Rule-based scoring — query 본질 direction 우선, tone은 강도로만 사용.

    default_direction:
      'bullish'/'bearish' → query 본질 (위기/공급차질 vs 수요둔화/공급증가)
      'auto' → tone 부호로 추정 (geopolitical 평시)
    """
    default_dir = q.get("default_direction", "auto")
    if default_dir in ("bullish", "bearish"):
        direction = default_dir
    else:
        # auto: GDELT 일반 매핑 (negative tone = 가격 ↑ bullish)
        if avg_tone <= -0.5:
            direction = "bullish"
        elif avg_tone >= 0.5:
            direction = "bearish"
        else:
            direction = "neutral"

    # importance: tone 절대값으로 강도 부여 (본질 direction은 이미 정해짐)
    # mention_count (daily_value)도 strength 반영
    tone_boost = min(20, int(abs(avg_tone) * 4))
    mention_boost = min(10, int(daily_value / 10)) if daily_value else 0
    importance = min(100, q["baseline"] + tone_boost + mention_boost)
    return {
        "importance": importance,
        "direction": direction,
        "category": q["category"],
        "horizon": q["horizon"],
        "confidence": q["confidence"],
    }

# COMMAND ----------

@dataclass
class NewsRow:
    article_id: str
    source: str
    source_type: str
    tier: str
    published_at: datetime
    fetched_at: datetime
    url: str
    title: str
    body: str
    body_lang: str
    raw_tone: float
    mention_count: int
    importance: int
    category: str
    direction: str
    horizon: str
    confidence: str
    entities: list[str]
    job_run_id: str
    llm_model: str

# COMMAND ----------

run_id = f"backtest_seed_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"
all_rows: list[NewsRow] = []
now = datetime.now(timezone.utc)

print(f"─── Backtest seed: {START_DT} → {END_DT} ───")
for q in QUERIES:
    print(f"\n{q['label']:<18} '{q['query']}'")
    points = fetch_timelinetone(q["query"], START_DT, END_DT)
    if not points:
        print(f"  no data")
        continue

    # 일별 그룹화 — GDELT bucket은 기본 15min. day로 aggregate.
    daily: dict[str, list[float]] = {}
    for p in points:
        dt_str = p.get("date", "")  # "20260203T000000Z"
        if not dt_str or "value" not in p:
            continue
        day_key = dt_str[:8]  # YYYYMMDD
        daily.setdefault(day_key, []).append(float(p["value"]))

    # 각 day → 1 row
    for day_key, tones in sorted(daily.items()):
        avg_tone = sum(tones) / len(tones)
        score = score_from_signal(q["label"], q, avg_tone, len(tones))
        if score["importance"] < 50:
            continue

        try:
            pub_dt = datetime.strptime(day_key, "%Y%m%d").replace(tzinfo=timezone.utc)
        except ValueError:
            continue

        url = f"gdelt-backtest://{q['label']}/{day_key}"
        article_id = hashlib.sha256(url.encode()).hexdigest()[:32]

        all_rows.append(NewsRow(
            article_id=article_id,
            source=f"GDELT_{q['label']}",
            source_type="gdelt_backtest",
            tier=q["tier"],
            published_at=pub_dt,
            fetched_at=now,
            url=url,
            title=f"{q['label']} signal · {day_key} · tone={avg_tone:+.2f}",
            body="",
            body_lang="en",
            raw_tone=round(avg_tone, 2),
            mention_count=len(tones),
            importance=score["importance"],
            category=score["category"],
            direction=score["direction"],
            horizon=score["horizon"],
            confidence=score["confidence"],
            entities=[q["label"].upper()],
            job_run_id=run_id,
            llm_model="rule_based_v1",
        ))

    print(f"  {len(daily)} days fetched, {sum(1 for r in all_rows if r.source.endswith(q['label']))} signals scored")

print(f"\n{'='*60}\nTotal rows: {len(all_rows)}")

# COMMAND ----------

if all_rows:
    schema = StructType([
        StructField("article_id", StringType(), False),
        StructField("source", StringType(), False),
        StructField("source_type", StringType(), False),
        StructField("tier", StringType(), False),
        StructField("published_at", TimestampType(), False),
        StructField("fetched_at", TimestampType(), False),
        StructField("url", StringType(), False),
        StructField("title", StringType(), False),
        StructField("body", StringType(), True),
        StructField("body_lang", StringType(), True),
        StructField("raw_tone", DoubleType(), True),
        StructField("mention_count", IntegerType(), True),
        StructField("importance", IntegerType(), False),
        StructField("category", StringType(), False),
        StructField("direction", StringType(), False),
        StructField("horizon", StringType(), False),
        StructField("confidence", StringType(), False),
        StructField("entities", ArrayType(StringType()), True),
        StructField("job_run_id", StringType(), True),
        StructField("llm_model", StringType(), True),
    ])
    df = spark.createDataFrame([Row(**asdict(r)) for r in all_rows], schema=schema)
    df = df.withColumn("raw_tone", col("raw_tone").cast("decimal(5,2)"))
    df.write.mode("append").saveAsTable(TARGET_TABLE)
    print(f"✅ {len(all_rows)} rows appended to {TARGET_TABLE}")

# Verify
result = spark.sql(f"""
SELECT
    DATE(published_at) AS day,
    direction,
    COUNT(*) AS n
FROM {TARGET_TABLE}
WHERE source_type = 'gdelt_backtest' AND job_run_id = '{run_id}'
GROUP BY day, direction
ORDER BY day, direction
LIMIT 20
""")
display(result)

# COMMAND ----------
dbutils.notebook.exit(json.dumps({
    "run_id": run_id,
    "rows_written": len(all_rows),
    "queries_processed": len(QUERIES),
    "date_range": f"{START_DT} → {END_DT}",
}))
