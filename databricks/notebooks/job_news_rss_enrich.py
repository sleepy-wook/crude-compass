# Databricks notebook source
# MAGIC %md
# MAGIC # Job 1 — news_rss_event_driven (보강층)
# MAGIC
# MAGIC ## 시나리오 v2 매핑
# MAGIC - § 7 RSS 보강층: GDELT alert 시점에만 fetch → Knowledge Assistant 입력
# MAGIC - § 4 Layer 1 News Fetch (event-driven, GDELT 후속)
# MAGIC - **한국어 처리** (Sprint 2 task 2 발견 — GDELT 한국어 weak)
# MAGIC
# MAGIC ## Trigger
# MAGIC - GDELT job (Job 2)에서 importance ≥ 80 article 감지 시 호출
# MAGIC - 또는 manual run으로 한국어 source 일별 fetch (개발/검증 용)
# MAGIC
# MAGIC ## 입력
# MAGIC - RSS Tier A: Reuters · AP · 연합뉴스 (한국어 핵심) · BBC · FT
# MAGIC
# MAGIC ## 출력
# MAGIC - bronze.news_articles (source_type='rss_enrich')

# COMMAND ----------

# MAGIC %pip install --quiet feedparser==6.0.11 httpx==0.28.1
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import hashlib
import json
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

import feedparser
import httpx
from pyspark.sql import Row
from pyspark.sql.types import (
    StructType, StructField, StringType, TimestampType, IntegerType,
    DecimalType, ArrayType
)

# COMMAND ----------

LLM_ENDPOINT = "databricks-claude-haiku-4-5"
TARGET_TABLE = "crude_compass.bronze.news_articles"

# Tier A RSS — GDELT 한국어 처리 보강
RSS_FEEDS = [
    {"source": "Yonhap_KR",  "tier": "A", "lang": "ko", "url": "https://www.yna.co.kr/rss/economy.xml"},
    {"source": "Yonhap_EN",  "tier": "A", "lang": "en", "url": "https://en.yna.co.kr/RSS/economy.xml"},
    {"source": "Reuters_Energy", "tier": "A", "lang": "en", "url": "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best"},
    # 일부 source는 robots.txt 또는 deprecation으로 fallback 필요. Sprint 3에서 보강.
]

# 키워드 filter (oil/petroleum 관련만)
KEYWORDS_KR = ["원유", "석유", "유가", "OPEC", "사우디", "이란", "호르무즈", "정유", "감산", "증산", "재고"]
KEYWORDS_EN = ["oil", "crude", "petroleum", "OPEC", "Saudi", "Iran", "Hormuz", "refinery", "production", "inventory"]

# COMMAND ----------

# 시나리오 § 16 importance anchor (job_gdelt.py와 일관)
IMPORTANCE_ANCHORS = """
시나리오 § 16 Importance Score (0-100) anchor:
- 100: 핵 협상 결렬 / IRGC 군사 동원 / OPEC 갑작스 감산 발표
-  80: 미 중동 군 가족 출국 / OPEC MOMR 발표 (월 1회 정기)
-  60: EIA 주간 재고 (정기) / GDELT 멘션 +50% 변동
-  40: 사우디 정유 capacity 일부 수정 / 일반 시장 전망
"""

LLM_SYSTEM_PROMPT = f"""You are Crude Compass news scoring agent for Korean petroleum refinery decisions.

Task: Score article relevance to crude oil market. Korean and English supported. Return JSON only.

{IMPORTANCE_ANCHORS}

Output schema (JSON object only):
{{
  "importance": <int 0-100>,
  "category": <"geopolitical"|"policy"|"disaster"|"market"|"supply"|"demand">,
  "direction": <"bullish"|"bearish"|"neutral">,
  "horizon": <"short"|"medium"|"long">,
  "confidence": <"low"|"med"|"high">,
  "entities": [<entity strings>]
}}
"""

# COMMAND ----------

def is_relevant(title: str, summary: str, lang: str) -> bool:
    """Quick keyword filter — LLM call 줄이기."""
    text = (title + " " + summary).lower()
    keywords = KEYWORDS_KR if lang == "ko" else KEYWORDS_EN
    return any(kw.lower() in text for kw in keywords)


def score_article(title: str, body: str, lang: str) -> dict:
    """LLM scoring."""
    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient()

    user_msg = f"""Title: {title}

Body: {body[:1500]}

Language: {lang}"""

    try:
        resp = w.serving_endpoints.query(
            name=LLM_ENDPOINT,
            messages=[
                {"role": "system", "content": LLM_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=300,
            temperature=0.0,
        )
        content = resp.choices[0].message.content if resp.choices else "{}"
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1].lstrip("json").strip()
        return json.loads(content)
    except Exception as e:
        print(f"  ⚠️  LLM scoring failed: {e}")
        return {
            "importance": 50,
            "category": "market",
            "direction": "neutral",
            "horizon": "short",
            "confidence": "low",
            "entities": [],
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


def process_feed(feed_config: dict, run_id: str, max_items: int = 10) -> list[NewsRow]:
    source = feed_config["source"]
    print(f"\n─── {source} ({feed_config['lang']}) ───")

    try:
        d = feedparser.parse(feed_config["url"])
    except Exception as e:
        print(f"  ⚠️  parse failed: {e}")
        return []

    if not d.entries:
        print(f"  ⚠️  no entries")
        return []

    rows: list[NewsRow] = []
    processed = 0
    for entry in d.entries[:max_items * 2]:  # filter 후 max_items
        if processed >= max_items:
            break

        title = entry.get("title", "")
        summary = entry.get("summary", "")
        url = entry.get("link", "")

        if not (title and url):
            continue

        # Keyword filter (LLM call 절감)
        if not is_relevant(title, summary, feed_config["lang"]):
            continue

        score = score_article(title, summary, feed_config["lang"])
        if score.get("importance", 0) < 60:
            continue

        article_id = hashlib.sha256(url.encode()).hexdigest()[:32]
        try:
            pub_dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        except (AttributeError, TypeError):
            pub_dt = datetime.now(timezone.utc)

        row = NewsRow(
            article_id=article_id,
            source=source,
            source_type="rss_enrich",
            tier=feed_config["tier"],
            published_at=pub_dt,
            fetched_at=datetime.now(timezone.utc),
            url=url,
            title=title[:500],
            body=summary[:5000],
            body_lang=feed_config["lang"],
            raw_tone=0.0,           # GDELT raw_tone 없음 (보강층은 LLM scoring만)
            mention_count=0,
            importance=score.get("importance", 0),
            category=score.get("category", "market"),
            direction=score.get("direction", "neutral"),
            horizon=score.get("horizon", "short"),
            confidence=score.get("confidence", "low"),
            entities=score.get("entities", [])[:10],
            job_run_id=run_id,
            llm_model=LLM_ENDPOINT,
        )
        rows.append(row)
        processed += 1
        print(f"  ✅ imp={row.importance} · {row.direction} · {row.title[:60]}")

    return rows

# COMMAND ----------

run_id = f"rss_enrich_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"
all_rows: list[NewsRow] = []

for feed in RSS_FEEDS:
    rows = process_feed(feed, run_id)
    all_rows.extend(rows)
    time.sleep(1)

print(f"\n{'='*60}\nTotal: {len(all_rows)} rows\n{'='*60}")

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
        StructField("raw_tone", DecimalType(5, 2), True),
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
    df.write.mode("append").saveAsTable(TARGET_TABLE)
    print(f"✅ {len(all_rows)} rows appended")
else:
    print("ℹ️  No rows")

dbutils.notebook.exit(json.dumps({
    "run_id": run_id,
    "rows_written": len(all_rows),
    "feeds_processed": len(RSS_FEEDS),
}))
