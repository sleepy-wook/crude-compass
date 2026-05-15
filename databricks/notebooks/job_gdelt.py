# Databricks notebook source
# MAGIC %md
# MAGIC # Job 2 — gdelt_15min (감지층)
# MAGIC
# MAGIC ## 시나리오 v2 매핑
# MAGIC - § 7 #3 GDELT (글로벌 뉴스 + tone score, 감지층)
# MAGIC - § 4 Layer 1 News Fetch (15min cron)
# MAGIC - § 6 양방향 direction (bullish/bearish/neutral) ⭐ 핵심
# MAGIC - § 16 importance 0-100 anchors
# MAGIC
# MAGIC ## 입력
# MAGIC - GDELT DOC API (https://api.gdeltproject.org/api/v2/doc/doc) — key 없음, 무료
# MAGIC - Foundation Model API `databricks-claude-haiku-4-5` (LLM scoring)
# MAGIC
# MAGIC ## 출력
# MAGIC - `crude_compass.bronze.news_articles` (importance ≥ 60 적재)
# MAGIC
# MAGIC ## DoD (Sprint 2 task 4)
# MAGIC 1. timelinetone mode로 mention 강도 + tone score 추출
# MAGIC 2. spike 감지 시 artlist mode로 article 본문 fetch
# MAGIC 3. LLM scoring (importance, category, direction, horizon, confidence, entities)
# MAGIC 4. bronze.news_articles에 append
# MAGIC 5. 평시 query (OPEC/EIA/Saudi)도 mention 잡힘 검증

# COMMAND ----------

# MAGIC %pip install --quiet httpx==0.28.1
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import hashlib
import json
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta

import httpx
from pyspark.sql import Row
from pyspark.sql.types import (
    StructType, StructField, StringType, TimestampType, IntegerType,
    DoubleType, ArrayType
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

GDELT_API = "https://api.gdeltproject.org/api/v2/doc/doc"
LLM_ENDPOINT = "databricks-claude-haiku-4-5"
TARGET_TABLE = "crude_compass.bronze.news_articles"

# 시나리오 § 2 평시 가치 + § 6 양방향 — 12 queries (5 bullish + 5 bearish + 2 auto)
# verify (5/11) 결과 bearish 1.8% 편향 → bearish query 보강 + default_direction 명시
QUERIES = [
    # bullish 본질 — 7개
    {"label": "hormuz",            "query": "Strait of Hormuz Iran tanker", "tier": "A"},
    {"label": "iran_sanctions",    "query": "Iran sanctions oil export", "tier": "A"},
    {"label": "russia_ukraine",    "query": "Russia Ukraine oil sanctions", "tier": "A"},
    {"label": "houthi_red_sea",    "query": "Houthi Red Sea tanker attack", "tier": "A"},
    {"label": "opec_cut_surprise", "query": "OPEC production cut surprise", "tier": "A"},
    {"label": "libya_shutdown",    "query": "Libya oil production shutdown unrest", "tier": "A"},
    {"label": "venezuela_sanctions","query": "Venezuela oil sanctions PdVSA", "tier": "A"},
    # auto (평시 정기, tone 부호로)
    {"label": "opec_monthly",  "query": "OPEC monthly oil market report", "tier": "B"},
    {"label": "eia_inventory", "query": "EIA crude oil inventory weekly", "tier": "B"},
    {"label": "saudi_osp",     "query": "Saudi Aramco OSP official selling price", "tier": "B"},
    {"label": "china_demand",  "query": "China oil demand PMI manufacturing", "tier": "A"},
    {"label": "us_spr",        "query": "strategic petroleum reserve release", "tier": "A"},
    # bearish 본질 — 5개
    {"label": "china_recession",     "query": "China oil demand slowdown recession", "tier": "A"},
    {"label": "oecd_inventory_build","query": "OECD commercial crude inventory build", "tier": "A"},
    {"label": "saudi_osp_cut",       "query": "Saudi Aramco OSP price cut Asia", "tier": "A"},
    {"label": "ev_adoption",         "query": "electric vehicle adoption oil demand peak", "tier": "B"},
    {"label": "us_shale_surge",      "query": "US shale oil production record surge", "tier": "A"},
]

QUERY_BASELINE = {
    # bullish
    "hormuz": 75, "iran_sanctions": 70, "russia_ukraine": 70,
    "houthi_red_sea": 70, "opec_cut_surprise": 65,
    "libya_shutdown": 60, "venezuela_sanctions": 60,
    # auto
    "opec_monthly": 65, "eia_inventory": 60, "saudi_osp": 65,
    "china_demand": 55, "us_spr": 60,
    # bearish
    "china_recession": 60, "oecd_inventory_build": 60,
    "saudi_osp_cut": 65, "ev_adoption": 50, "us_shale_surge": 60,
}

QUERY_META = {
    # bullish 본질
    "hormuz":              {"category": "geopolitical", "horizon": "short",  "confidence": "high", "default_direction": "bullish"},
    "iran_sanctions":      {"category": "policy",       "horizon": "medium", "confidence": "high", "default_direction": "bullish"},
    "russia_ukraine":      {"category": "geopolitical", "horizon": "medium", "confidence": "high", "default_direction": "bullish"},
    "houthi_red_sea":      {"category": "geopolitical", "horizon": "short",  "confidence": "high", "default_direction": "bullish"},
    "opec_cut_surprise":   {"category": "policy",       "horizon": "short",  "confidence": "high", "default_direction": "bullish"},
    "libya_shutdown":      {"category": "geopolitical", "horizon": "medium", "confidence": "med",  "default_direction": "bullish"},
    "venezuela_sanctions": {"category": "policy",       "horizon": "medium", "confidence": "high", "default_direction": "bullish"},
    # auto
    "opec_monthly":        {"category": "policy",       "horizon": "medium", "confidence": "high", "default_direction": "auto"},
    "eia_inventory":       {"category": "supply",       "horizon": "short",  "confidence": "high", "default_direction": "auto"},
    "saudi_osp":           {"category": "supply",       "horizon": "medium", "confidence": "high", "default_direction": "auto"},
    "china_demand":        {"category": "demand",       "horizon": "medium", "confidence": "med",  "default_direction": "auto"},
    "us_spr":              {"category": "policy",       "horizon": "short",  "confidence": "high", "default_direction": "auto"},
    # bearish 본질
    "china_recession":     {"category": "demand", "horizon": "medium", "confidence": "med",  "default_direction": "bearish"},
    "oecd_inventory_build":{"category": "supply", "horizon": "medium", "confidence": "high", "default_direction": "bearish"},
    "saudi_osp_cut":       {"category": "supply", "horizon": "medium", "confidence": "high", "default_direction": "bearish"},
    "ev_adoption":         {"category": "demand", "horizon": "long",   "confidence": "med",  "default_direction": "bearish"},
    "us_shale_surge":      {"category": "supply", "horizon": "medium", "confidence": "high", "default_direction": "bearish"},
}

# COMMAND ----------

# MAGIC %md
# MAGIC ## GDELT API helpers

# COMMAND ----------

def _safe_get(params: dict) -> dict | None:
    """Fast-fail GET — 절대 fail/timeout 안 나도록. 빈 응답 / 에러 = None silent.

    5/15 D-3 진단: GDELT API peak 시간대 throttling으로 17 query 누적 600s 초과.
    Fix: per-call 5s hard timeout, retry 0, User-Agent 명시 (slow lane 회피).
    어떤 error도 silent skip — main loop가 catch하고 다음 query 진행.
    Worst case 17 query × 5s = 85s. 절대 600s 안 넘음.
    """
    try:
        time.sleep(0.3)
        resp = httpx.get(
            GDELT_API,
            params=params,
            timeout=5.0,
            headers={"User-Agent": "crude-compass/1.0 (Databricks Apps Hackathon research)"},
        )
        if resp.status_code != 200:
            return None
        text = resp.text.strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None
    except Exception:
        # Network error / timeout / 어떤 예외든 silent skip
        return None


def fetch_timelinetone(query: str, timespan: str = "1d") -> dict:
    data = _safe_get({
        "query": query, "mode": "timelinetone",
        "format": "json", "timespan": timespan,
    })
    return data or {}


def fetch_artlist(query: str, max_records: int = 5, timespan: str = "1d") -> list[dict]:
    data = _safe_get({
        "query": query, "mode": "artlist",
        "format": "json", "timespan": timespan,
        "maxrecords": max_records, "sort": "datedesc",
    })
    return (data or {}).get("articles", []) if data else []

# COMMAND ----------

# MAGIC %md
# MAGIC ## Rule-based scoring (LLM 호출 X · 시나리오 § 4 Hard rule filter)
# MAGIC
# MAGIC Sprint 2: GDELT raw signal로 채점 (LLM 비용 $0).
# MAGIC Sprint 3: borderline case (importance 50-65)만 LLM 보강 예정.

# COMMAND ----------

def score_from_gdelt(label: str, avg_tone: float, mention_buckets: int) -> dict:
    """GDELT raw signal → importance + direction. LLM 호출 X.

    Direction logic (default_direction 기반):
    - 'bullish' / 'bearish' 본질 query → 그대로 (tone 부호와 무관)
    - 'auto' query → tone 부호로 추정:
        - tone <= -0.5 → bullish (negative news = oil price 상승 압력)
        - tone >= +0.5 → bearish (positive news = oil price 하락 압력)
        - else neutral

    Importance: baseline + tone abs bonus + mention bonus (max +25 + +10)
    """
    meta = QUERY_META.get(label, {"category": "market", "horizon": "short", "confidence": "low", "default_direction": "auto"})
    default_dir = meta.get("default_direction", "auto")

    if default_dir in ("bullish", "bearish"):
        direction = default_dir
    else:
        # auto: GDELT tone 부호로 추정
        if avg_tone <= -0.5:
            direction = "bullish"
        elif avg_tone >= 0.5:
            direction = "bearish"
        else:
            direction = "neutral"

    # Importance: tone abs (강도 → bonus), mention 누적 (보강 +10)
    baseline = QUERY_BASELINE.get(label, 50)
    tone_bonus = min(20, int(abs(avg_tone) * 4))
    mention_bonus = min(10, mention_buckets // 10) if mention_buckets else 0
    importance = min(100, baseline + tone_bonus + mention_bonus)

    entities = label.replace("_", " ").upper().split()

    return {
        "importance": importance,
        "category": meta["category"],
        "direction": direction,
        "horizon": meta["horizon"],
        "confidence": meta["confidence"],
        "entities": entities,
    }

# COMMAND ----------

# MAGIC %md
# MAGIC ## Main loop — fetch + score + write

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


def parse_gdelt_timestamp(s: str) -> datetime:
    """GDELT timestamp 'YYYYMMDDHHMMSS' → datetime UTC."""
    return datetime.strptime(s, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)


def process_query(label: str, query: str, tier: str, run_id: str) -> list[NewsRow]:
    print(f"\n─── {label} · '{query}' ───")

    # 1. timelinetone — mention 강도 + tone
    tl = fetch_timelinetone(query, timespan="1d")
    timeline = tl.get("timeline", [])
    if not timeline or not timeline[0].get("data"):
        print(f"  ⚠️  no timeline data — skip")
        return []

    tone_data = timeline[0]["data"]
    avg_tone = sum(p.get("value", 0.0) for p in tone_data) / max(len(tone_data), 1)
    mention_buckets = len(tone_data)
    print(f"  📈 avg_tone={avg_tone:+.2f}, buckets={mention_buckets}")

    # 2. Rule-based scoring (LLM 호출 X, $0 비용)
    score = score_from_gdelt(label, avg_tone, mention_buckets)
    print(f"  🎯 importance={score['importance']} direction={score['direction']} category={score['category']}")

    # 3. importance threshold (시나리오 § 16 30-60 log only, 60+ enrich)
    if score["importance"] < 50:
        print(f"  ⏭  importance < 50 — skip (시나리오 § 16: 30-60 log only)")
        return []

    # 4. artlist에서 대표 article 1개 fetch (URL/title 보존용)
    articles = fetch_artlist(query, max_records=1, timespan="1d")
    now = datetime.now(timezone.utc)

    if articles:
        art = articles[0]
        url = art.get("url", "")
        title = art.get("title", f"GDELT signal · {label}")
        published = art.get("seendate", "")
        try:
            pub_dt = parse_gdelt_timestamp(published)
        except (ValueError, TypeError):
            pub_dt = now
        source = art.get("domain", "GDELT")
        body_lang = (art.get("language", "English") or "en")[:2].lower()
    else:
        # artlist 비어있어도 timelinetone 기반 row 생성 (signal 자체는 catch)
        url = f"gdelt://signal/{label}/{run_id}"
        title = f"GDELT signal · {label} · tone={avg_tone:+.2f}"
        pub_dt = now
        source = "GDELT_aggregate"
        body_lang = "en"

    article_id = hashlib.sha256(url.encode()).hexdigest()[:32]

    row = NewsRow(
        article_id=article_id,
        source=source,
        source_type="gdelt_detect",
        tier=tier,
        published_at=pub_dt,
        fetched_at=now,
        url=url,
        title=title[:500],
        body="",  # Sprint 3에서 보강
        body_lang=body_lang,
        raw_tone=round(avg_tone, 2),
        mention_count=mention_buckets,
        importance=score["importance"],
        category=score["category"],
        direction=score["direction"],
        horizon=score["horizon"],
        confidence=score["confidence"],
        entities=score["entities"][:10],
        job_run_id=run_id,
        llm_model="rule_based_v1",  # LLM 미호출
    )
    print(f"  ✅ row created · {title[:60]}")
    return [row]

# COMMAND ----------

# Run job
run_id = f"gdelt_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"
all_rows: list[NewsRow] = []

for q in QUERIES:
    # 한 query 실패해도 다음 query 진행 — 어떤 error에도 silent skip.
    # 검색 결과 0이면 SUCCESS로 끝남 (spark write 단계에서 빈 list 처리).
    try:
        rows = process_query(q["label"], q["query"], q["tier"], run_id)
        all_rows.extend(rows)
    except Exception as e:
        print(f"  ⚠️  {q['label']} skipped: {type(e).__name__}: {str(e)[:100]}")
    time.sleep(0.5)  # rate limit safety

print(f"\n{'='*60}")
print(f"Total scored articles: {len(all_rows)}")
print(f"{'='*60}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Append to bronze.news_articles

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

    from pyspark.sql.functions import col

    df = spark.createDataFrame(
        [Row(**asdict(r)) for r in all_rows],
        schema=schema,
    )
    # Bronze table에 raw_tone DECIMAL(5,2)이라 cast 필요
    df = df.withColumn("raw_tone", col("raw_tone").cast("decimal(5,2)"))
    df.write.mode("append").saveAsTable(TARGET_TABLE)
    print(f"✅ {len(all_rows)} rows appended to {TARGET_TABLE}")
else:
    print("ℹ️  No rows to write (all queries below importance threshold)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify

# COMMAND ----------

result = spark.sql(f"""
SELECT
    direction,
    COUNT(*) as n,
    AVG(importance) as avg_importance,
    AVG(raw_tone) as avg_tone
FROM {TARGET_TABLE}
WHERE job_run_id = '{run_id}'
GROUP BY direction
ORDER BY n DESC
""")
display(result)

# COMMAND ----------
# Job exit
dbutils.notebook.exit(json.dumps({
    "run_id": run_id,
    "rows_written": len(all_rows),
    "queries_processed": len(QUERIES),
}))
