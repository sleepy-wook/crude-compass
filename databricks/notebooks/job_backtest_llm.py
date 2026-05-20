# Databricks notebook source
# MAGIC %md
# MAGIC # Backtest LLM — Signal Recency + Structured Fields
# MAGIC
# MAGIC ## 설계
# MAGIC
# MAGIC ### Signal Recency Weighting (prompt 구조)
# MAGIC **시간 버킷별 명시** ("최근 7일", "8-30일", "31-90일") + 각 버킷의 핵심 신호
# MAGIC →  LLM이 regime shift를 catch하기 쉬워짐 (예: 2020-11 vaccine rally)
# MAGIC
# MAGIC ### Structured Fields (정량 데이터 명시)
# MAGIC prompt에 명시:
# MAGIC - EIA 최근 4주 평균 재고 변화 (kbbl)
# MAGIC - OPEC supply-demand gap (latest monthly)
# MAGIC - Dubai 7-day momentum (%)
# MAGIC - Dubai 30-day volatility (%)
# MAGIC →  LLM이 추론할 필요 없이 명시 데이터 사용
# MAGIC
# MAGIC ## 비용
# MAGIC - 300 LLM call × $0.01 (Haiku 4.5) = ~$3

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


# databricks-sdk는 Databricks runtime에 pre-installed (보통). 다른 둘만 fallback.
_ensure_package("pydantic", "pydantic==2.11.10")
_ensure_package("psycopg", "psycopg[binary]==3.2.3")
_ensure_package("databricks.sdk", "databricks-sdk>=0.106.0")

# COMMAND ----------

import json
import random
import re
from datetime import datetime, timezone, date, timedelta
from decimal import Decimal

import psycopg
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

# COMMAND ----------

# Widgets
dbutils.widgets.text("n_per_zone", "100", "Samples per zone")
dbutils.widgets.text("seed", "42", "Random seed")
dbutils.widgets.text("smoke_test", "false", "Smoke test (5 per zone)")
dbutils.widgets.text("backtest_start", "2019-04-01", "Backtest start")
dbutils.widgets.text("backtest_end", "2026-01-31", "Backtest end")

N_PER_ZONE = int(dbutils.widgets.get("n_per_zone"))
SEED = int(dbutils.widgets.get("seed"))
SMOKE_TEST = dbutils.widgets.get("smoke_test").lower() == "true"
BACKTEST_START = dbutils.widgets.get("backtest_start")
BACKTEST_END = dbutils.widgets.get("backtest_end")

if SMOKE_TEST:
    N_PER_ZONE = 5

LLM_ENDPOINT = "databricks-claude-haiku-4-5"

# Target: Lakebase Postgres `backtest_predictions` (AI-generated content 정석 OLTP).
# Schema: databricks/schemas/lakebase.sql §5
# Connection: dbutils.secrets scope=crude — same lakebase_* keys Apps에서 사용
LAKEBASE_HOST = dbutils.secrets.get(scope="crude", key="lakebase_host")
LAKEBASE_DATABASE = dbutils.secrets.get(scope="crude", key="lakebase_database")
LAKEBASE_USER = dbutils.secrets.get(scope="crude", key="lakebase_user")
LAKEBASE_ENDPOINT_PATH = dbutils.secrets.get(scope="crude", key="lakebase_endpoint_path")

# K-Petroleum baseline mix
DEFAULT_TERM_PCT = 75
HEDGE_TERM_PCT = 90
OPP_TERM_PCT = 55
TERM_DISCOUNT = 0.03

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Signals view 

# COMMAND ----------

spark.sql("""
CREATE OR REPLACE TEMP VIEW _bt_signals AS
WITH gdelt AS (
    SELECT DATE(published_at) AS event_date, direction, category,
           CAST(importance AS DOUBLE) AS raw_intensity,
           'news_tone' AS signal_type, source,
           CAST(CASE tier WHEN 'A' THEN 1.0 WHEN 'B' THEN 0.8 ELSE 0.7 END AS DOUBLE) AS source_credibility
    FROM crude_compass.bronze.news_articles
    WHERE source_type = 'gdelt_backtest' AND importance >= 50
),
eia_signals AS (
    SELECT week_ending AS event_date,
           CASE WHEN delta_vs_prev_wk > 5000 THEN 'bearish'
                WHEN delta_vs_prev_wk < -5000 THEN 'bullish' ELSE 'neutral' END AS direction,
           'supply' AS category,
           LEAST(100.0, 60.0 + ABS(CAST(delta_vs_prev_wk AS DOUBLE)) / 500.0) AS raw_intensity,
           'eia_inventory' AS signal_type, 'EIA' AS source, 1.0 AS source_credibility
    FROM crude_compass.bronze.eia_inventory
    WHERE inventory_type='commercial' AND delta_vs_prev_wk IS NOT NULL AND ABS(delta_vs_prev_wk) > 2000
),
opec_signals AS (
    SELECT TO_DATE(CONCAT(report_month, '-01'), 'yyyy-MM-dd') AS event_date,
           'bullish' AS direction, 'demand' AS category,
           70.0 AS raw_intensity, 'opec_momr' AS signal_type, 'OPEC' AS source, 1.0 AS source_credibility
    FROM crude_compass.bronze.opec_momr_parsed
    WHERE forecast_demand_kbbl_d IS NOT NULL AND saudi_production_kbbl_d IS NOT NULL
      AND forecast_demand_kbbl_d > saudi_production_kbbl_d * 11.5
),
fx_signals AS (
    SELECT f.date AS event_date,
           CASE WHEN f.rate - LAG(f.rate) OVER (ORDER BY f.date) > f.rate * 0.005 THEN 'bullish'
                WHEN f.rate - LAG(f.rate) OVER (ORDER BY f.date) < -f.rate * 0.005 THEN 'bearish' ELSE 'neutral' END AS direction,
           'macro' AS category, 55.0 AS raw_intensity,
           'fx_krw_usd' AS signal_type, 'ECOS' AS source, 0.8 AS source_credibility
    FROM crude_compass.bronze.fx_rates f WHERE f.pair='USD/KRW'
)
SELECT * FROM gdelt
UNION ALL SELECT * FROM eia_signals WHERE direction != 'neutral'
UNION ALL SELECT * FROM opec_signals
UNION ALL SELECT * FROM fx_signals WHERE direction != 'neutral'
""")

spark.sql("""
    CREATE OR REPLACE TEMP VIEW _bt_dubai AS
    SELECT trade_date AS price_date, CAST(price_usd AS DOUBLE) AS dubai_close
    FROM crude_compass.bronze.oil_prices_daily WHERE ticker='DUBAI'
""")

# COMMAND ----------

# Pattern Score 
spark.sql(f"""
CREATE OR REPLACE TEMP VIEW _bt_pattern_daily AS
WITH date_dim AS (
    SELECT explode(sequence(DATE'{BACKTEST_START}', DATE'{BACKTEST_END}', INTERVAL 1 DAY)) AS as_of_date
),
contribs AS (
    SELECT d.as_of_date, s.direction, s.category, s.signal_type,
           crude_compass.functions.weighted_signal(
               s.raw_intensity, CAST(DATEDIFF(d.as_of_date, s.event_date) AS INT),
               s.signal_type, s.source_credibility
           ) AS w
    FROM date_dim d JOIN _bt_signals s
        ON s.event_date BETWEEN d.as_of_date - INTERVAL 90 DAYS AND d.as_of_date
),
agg AS (
    SELECT as_of_date,
           SUM(CASE WHEN direction='bullish' THEN w ELSE 0 END) AS bullish,
           SUM(CASE WHEN direction='bearish' THEN w ELSE 0 END) AS bearish,
           COUNT(*) AS sig_count
    FROM contribs GROUP BY as_of_date
),
cv AS (
    SELECT as_of_date, SUM(CASE WHEN n>=2 THEN 15 ELSE 0 END) AS cross_val_bonus
    FROM (
        SELECT as_of_date, category, direction, COUNT(DISTINCT signal_type) AS n
        FROM contribs WHERE direction IN ('bullish','bearish')
        GROUP BY as_of_date, category, direction
    ) GROUP BY as_of_date
),
joined AS (
    SELECT a.as_of_date, a.bullish, a.bearish, a.sig_count, a.bullish - a.bearish AS net,
           COALESCE(c.cross_val_bonus, 0) AS cross_val_bonus
    FROM agg a LEFT JOIN cv c ON a.as_of_date=c.as_of_date
),
rolling AS (
    SELECT *,
           AVG(net) OVER (ORDER BY as_of_date ROWS BETWEEN 90 PRECEDING AND 1 PRECEDING) AS mean_net,
           COALESCE(STDDEV_SAMP(net) OVER (ORDER BY as_of_date ROWS BETWEEN 90 PRECEDING AND 1 PRECEDING), 1.0) AS std_net
    FROM joined
)
SELECT as_of_date, bullish, bearish, sig_count, cross_val_bonus,
       GREATEST(0.0, LEAST(100.0,
           50.0 + 25.0 * (net - mean_net) / GREATEST(std_net, 1.0) + cross_val_bonus
       )) AS pattern_score
FROM rolling WHERE mean_net IS NOT NULL
""")
print("Pattern Score view OK")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Stratified sampling 

# COMMAND ----------

all_rows = spark.sql("""
    SELECT p.as_of_date,
           CASE WHEN p.pattern_score >= 70 THEN 'HIGH'
                WHEN p.pattern_score <= 30 THEN 'LOW' ELSE 'MID' END AS zone
    FROM _bt_pattern_daily p
    JOIN _bt_dubai b ON p.as_of_date = b.price_date
    WHERE p.as_of_date <= (SELECT DATE_SUB(MAX(price_date), 90) FROM _bt_dubai)
""").collect()
by_zone = {"HIGH": [], "MID": [], "LOW": []}
for r in all_rows:
    by_zone[r.zone].append(r.as_of_date)

random.seed(SEED)
sampled = []
for zone in ["HIGH", "MID", "LOW"]:
    pool = sorted(by_zone[zone])
    n_take = min(N_PER_ZONE, len(pool))
    if len(pool) <= N_PER_ZONE:
        sampled.extend([(d, zone) for d in pool])
    else:
        stride = len(pool) // n_take
        for i in range(n_take):
            offset = random.randint(0, max(stride - 1, 0))
            idx = min(i * stride + offset, len(pool) - 1)
            sampled.append((pool[idx], zone))
random.shuffle(sampled)
print(f"Sampled {len(sampled)} dates")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Prompt — C + D

# COMMAND ----------

w = WorkspaceClient()

SYSTEM_PROMPT = """You are **Crude Compass Mission Plan Agent** for K-Petroleum refinery.

## BACKTEST MODE
Use ONLY data BEFORE the given date. DO NOT assume any post-date knowledge.

## K-Petroleum baseline (한국 정유사 실제)
- 평시 default: Term 75% / Spot 25%
- HEDGE 권고: Term 90% (target_pct=90)
- OPP 권고: Spot 45% (target_pct=45)

## Decision framework

You receive THREE structured inputs:

### 1) Pattern Score + raw signal counts (90일 누적)
### 2) Recent vs older signal balance (RECENCY weighting)
- "최근 7일" 신호가 "31-90일" 신호와 방향이 다르면 = regime shift
- 최근 신호에 더 높은 weight 주기
### 3) Structured market indicators (정량 데이터, 추론 X)
- EIA inventory delta (최근 4주 평균) — positive = build (bearish), negative = draw (bullish)
- OPEC supply-demand gap — positive = oversupply (bearish), negative = undersupply (bullish)
- Dubai 7-day momentum (%) — recent price trend
- Dubai 30-day volatility (%) — uncertainty level

## Decision logic
- Pattern Score 70+ + 최근 신호 bullish 우세 + structured 일관 → HEDGE
- Pattern Score 30- + 최근 신호 bearish 우세 + structured 일관 → OPPORTUNITY
- 최근 신호와 누적 신호 방향 충돌 → STAY (recent shift 신호 더 가중)
- Structured 정량 데이터가 Pattern Score와 모순 → STAY 또는 confidence ↓

## CRITICAL — Self-check before output
1. Reasoning에서 인용한 신호 방향이 권고 방향과 일치하는지 확인
   (예: OPP 권고면 reasoning에 bearish 증거 인용해야지, "지정학 리스크 지속" 같은 bullish 증거 X)
2. Structured 데이터가 추천 방향 지지하는지 확인
3. 일관성 깨지면 confidence_score 하향 또는 STAY 전환

## Output: STRICT JSON ONLY (no markdown)

{
  "action_type": "new_mission" | "continue",
  "mission_type": "HEDGE" | "OPPORTUNITY" | "NONE",
  "target_pct": <int>,
  "duration_days": <int, 7-90>,
  "confidence_score": <0-100>,
  "reasoning": "한국어 3-5문장. 최근 7일 시그널과 정량 데이터를 명시적으로 인용"
}"""


def fetch_context(as_of_date):
    """시간 버킷 + structured fields 포함."""
    # Pattern Score
    ps_rows = spark.sql(f"""
        SELECT pattern_score, bullish, bearish, sig_count, cross_val_bonus
        FROM _bt_pattern_daily WHERE as_of_date = DATE'{as_of_date}'
    """).collect()
    if not ps_rows: return None
    ps = ps_rows[0]

    # Signals grouped by recency: 7d / 8-30d / 31-90d (regime shift catch)
    sig_buckets = spark.sql(f"""
        SELECT
            CASE
                WHEN DATEDIFF(DATE'{as_of_date}', event_date) <= 7 THEN '1_recent_7d'
                WHEN DATEDIFF(DATE'{as_of_date}', event_date) <= 30 THEN '2_mid_30d'
                ELSE '3_old_60_90d'
            END AS bucket,
            direction, category, signal_type,
            COUNT(*) AS n,
            ROUND(AVG(raw_intensity), 0) AS avg_imp
        FROM _bt_signals
        WHERE event_date BETWEEN DATE'{as_of_date}' - INTERVAL 90 DAYS AND DATE'{as_of_date}'
          AND direction IN ('bullish', 'bearish')
        GROUP BY bucket, direction, category, signal_type
        ORDER BY bucket, direction DESC, n DESC
    """).collect()

    # Top signals per bucket (text)
    bucket_texts = {"1_recent_7d": [], "2_mid_30d": [], "3_old_60_90d": []}
    for r in sig_buckets:
        if len(bucket_texts[r.bucket]) < 4:  # cap per bucket
            bucket_texts[r.bucket].append(
                f"  - {r.direction:7s} {r.category:12s} {r.signal_type:14s} (n={r.n}, avg_imp={int(r.avg_imp)})"
            )

    # Bucket direction balance
    bucket_balance = spark.sql(f"""
        SELECT
            CASE
                WHEN DATEDIFF(DATE'{as_of_date}', event_date) <= 7 THEN 'recent_7d'
                WHEN DATEDIFF(DATE'{as_of_date}', event_date) <= 30 THEN 'mid_30d'
                ELSE 'old_60_90d'
            END AS bucket,
            SUM(CASE WHEN direction='bullish' THEN 1 ELSE 0 END) AS bull,
            SUM(CASE WHEN direction='bearish' THEN 1 ELSE 0 END) AS bear
        FROM _bt_signals
        WHERE event_date BETWEEN DATE'{as_of_date}' - INTERVAL 90 DAYS AND DATE'{as_of_date}'
          AND direction IN ('bullish', 'bearish')
        GROUP BY bucket
    """).collect()
    balance_text = {r.bucket: f"bull={r.bull}, bear={r.bear}" for r in bucket_balance}

    # Structured fields: EIA 4-week avg, OPEC gap, Dubai momentum + volatility
    eia = spark.sql(f"""
        SELECT AVG(CAST(delta_vs_prev_wk AS DOUBLE)) AS eia_4wk_avg
        FROM crude_compass.bronze.eia_inventory
        WHERE inventory_type='commercial'
          AND week_ending BETWEEN DATE'{as_of_date}' - INTERVAL 28 DAYS AND DATE'{as_of_date}'
          AND delta_vs_prev_wk IS NOT NULL
    """).collect()
    eia_4wk = float(eia[0].eia_4wk_avg) if eia and eia[0].eia_4wk_avg is not None else None

    # OPEC latest
    opec = spark.sql(f"""
        SELECT CAST(saudi_production_kbbl_d AS DOUBLE) AS saudi,
               CAST(opec_total_kbbl_d AS DOUBLE) AS opec_total,
               CAST(forecast_demand_kbbl_d AS DOUBLE) AS demand
        FROM crude_compass.bronze.opec_momr_parsed
        WHERE saudi_production_kbbl_d IS NOT NULL
          AND TO_DATE(CONCAT(report_month, '-01'), 'yyyy-MM-dd') <= DATE'{as_of_date}'
        ORDER BY report_month DESC LIMIT 1
    """).collect()
    opec_gap = None
    if opec:
        o = opec[0]
        if o.opec_total and o.demand:
            opec_gap = o.opec_total - o.demand  # positive = oversupply (bearish)

    # Dubai 7-day momentum + 30-day vol
    dubai = spark.sql(f"""
        WITH d AS (
            SELECT price_date, dubai_close FROM _bt_dubai
            WHERE price_date BETWEEN DATE'{as_of_date}' - INTERVAL 35 DAYS AND DATE'{as_of_date}'
        ),
        returns AS (
            SELECT price_date, dubai_close,
                   dubai_close / LAG(dubai_close) OVER (ORDER BY price_date) - 1 AS r
            FROM d
        )
        SELECT
            (SELECT dubai_close FROM d ORDER BY price_date DESC LIMIT 1) AS p_now,
            (SELECT dubai_close FROM d WHERE price_date <= DATE'{as_of_date}' - INTERVAL 7 DAYS ORDER BY price_date DESC LIMIT 1) AS p_7d_ago,
            (SELECT STDDEV_SAMP(r) * 100 FROM returns WHERE r IS NOT NULL) AS vol_30d
    """).collect()
    momentum_7d = None
    vol_30d = None
    if dubai and dubai[0].p_now and dubai[0].p_7d_ago:
        momentum_7d = (dubai[0].p_now / dubai[0].p_7d_ago - 1) * 100
        vol_30d = float(dubai[0].vol_30d) if dubai[0].vol_30d else None

    # Dubai outcomes
    out_rows = spark.sql(f"""
        SELECT
            (SELECT dubai_close FROM _bt_dubai WHERE price_date = DATE'{as_of_date}') AS d0,
            (SELECT dubai_close FROM _bt_dubai WHERE price_date >= DATE'{as_of_date}' + INTERVAL 7 DAYS  ORDER BY price_date LIMIT 1) AS d7,
            (SELECT dubai_close FROM _bt_dubai WHERE price_date >= DATE'{as_of_date}' + INTERVAL 30 DAYS ORDER BY price_date LIMIT 1) AS d30,
            (SELECT dubai_close FROM _bt_dubai WHERE price_date >= DATE'{as_of_date}' + INTERVAL 90 DAYS ORDER BY price_date LIMIT 1) AS d90
    """).collect()[0]

    daily_rows = spark.sql(f"""
        SELECT price_date, dubai_close FROM _bt_dubai
        WHERE price_date > DATE'{as_of_date}' AND price_date <= DATE'{as_of_date}' + INTERVAL 90 DAYS
        ORDER BY price_date
    """).collect()
    daily_dubai = [(r.price_date, float(r.dubai_close)) for r in daily_rows]

    return {
        "pattern_score": float(ps.pattern_score),
        "bullish": float(ps.bullish), "bearish": float(ps.bearish),
        "sig_count": int(ps.sig_count), "cv_bonus": float(ps.cross_val_bonus),
        "bucket_texts": bucket_texts, "balance": balance_text,
        "eia_4wk": eia_4wk, "opec_gap": opec_gap,
        "momentum_7d": momentum_7d, "vol_30d": vol_30d,
        "dubai_0": float(out_rows.d0) if out_rows.d0 else None,
        "dubai_7d": float(out_rows.d7) if out_rows.d7 else None,
        "dubai_30d": float(out_rows.d30) if out_rows.d30 else None,
        "dubai_90d": float(out_rows.d90) if out_rows.d90 else None,
        "daily_dubai": daily_dubai,
    }


def call_llm(as_of_date, ctx):
    # Build prompt
    recent_text = "\n".join(ctx["bucket_texts"]["1_recent_7d"]) or "  (no signals)"
    mid_text = "\n".join(ctx["bucket_texts"]["2_mid_30d"]) or "  (no signals)"
    old_text = "\n".join(ctx["bucket_texts"]["3_old_60_90d"]) or "  (no signals)"

    eia_str = f"{ctx['eia_4wk']:+.0f} kbbl/wk avg" if ctx['eia_4wk'] is not None else "N/A"
    eia_interp = ""
    if ctx['eia_4wk'] is not None:
        if ctx['eia_4wk'] > 5000: eia_interp = " (강한 build = bearish)"
        elif ctx['eia_4wk'] < -5000: eia_interp = " (강한 draw = bullish)"
        elif ctx['eia_4wk'] > 1000: eia_interp = " (mild build)"
        elif ctx['eia_4wk'] < -1000: eia_interp = " (mild draw)"
        else: eia_interp = " (neutral)"

    opec_str = "N/A"
    opec_interp = ""
    if ctx['opec_gap'] is not None:
        opec_str = f"{ctx['opec_gap']:+.0f} kbbl/d"
        if ctx['opec_gap'] > 500: opec_interp = " (oversupply = bearish)"
        elif ctx['opec_gap'] < -500: opec_interp = " (undersupply = bullish)"
        else: opec_interp = " (balanced)"

    momentum_str = f"{ctx['momentum_7d']:+.2f}%" if ctx['momentum_7d'] is not None else "N/A"
    vol_str = f"{ctx['vol_30d']:.2f}%" if ctx['vol_30d'] is not None else "N/A"

    user_msg = f"""## Backtest date: {as_of_date}

## 1) Pattern Score (90일 누적 z-norm)
- Pattern Score: {ctx['pattern_score']:.1f}
- bullish_score: {ctx['bullish']:.1f}, bearish_score: {ctx['bearish']:.1f}
- cross_val_bonus: {ctx['cv_bonus']:.1f}, total_signals_90d: {ctx['sig_count']}

## 2) Recency-weighted signals
### 최근 7일 (가장 중요 — regime shift catch)
- Direction balance: {ctx['balance'].get('recent_7d', 'no data')}
- Top:
{recent_text}

### 8-30일
- Direction balance: {ctx['balance'].get('mid_30d', 'no data')}
- Top:
{mid_text}

### 31-90일 (background context)
- Direction balance: {ctx['balance'].get('old_60_90d', 'no data')}
- Top:
{old_text}

## 3) Structured market indicators
- **EIA 최근 4주 평균 재고 변화**: {eia_str}{eia_interp}
- **OPEC supply - demand (latest monthly)**: {opec_str}{opec_interp}
- **Dubai 7-day momentum**: {momentum_str}
- **Dubai 30-day volatility**: {vol_str}

→ Recommend HEDGE / OPPORTUNITY / continue.
Critical: 최근 7일 시그널이 31-90일과 충돌 시 STAY 고려. Structured 데이터가 Pattern Score와 모순 시 confidence ↓.
JSON only."""

    try:
        resp = w.serving_endpoints.query(
            name=LLM_ENDPOINT,
            messages=[
                ChatMessage(role=ChatMessageRole.SYSTEM, content=SYSTEM_PROMPT),
                ChatMessage(role=ChatMessageRole.USER, content=user_msg),
            ],
            max_tokens=700, temperature=0.0,
        )
        raw = resp.choices[0].message.content if resp.choices else "{}"
        raw = raw.strip()
        fence = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", raw)
        if fence: raw = fence.group(1)
        else:
            brace = re.search(r"(\{[\s\S]*\})", raw)
            if brace: raw = brace.group(1)
        return json.loads(raw)
    except Exception as e:
        return {"_error": f"{type(e).__name__}: {e}"}

# COMMAND ----------

def simulate_cost(term_pct, term_anchor, daily_spot_prices):
    if not daily_spot_prices: return None
    spot_pct = (100 - term_pct) / 100.0
    spot_avg = sum(p for _, p in daily_spot_prices) / len(daily_spot_prices)
    return (term_pct / 100.0) * term_anchor + spot_pct * spot_avg

def compute_saving(action_type, mission_type, target_pct, dubai_at_signal, daily_dubai, horizon_days):
    if dubai_at_signal is None or not daily_dubai: return None
    window = [(d, p) for d, p in daily_dubai if (d - daily_dubai[0][0]).days + 1 <= horizon_days]
    if not window: return None
    term_anchor = dubai_at_signal * (1 - TERM_DISCOUNT)
    default_cost = simulate_cost(DEFAULT_TERM_PCT, term_anchor, window)
    if not default_cost: return None
    if action_type in ("continue", "pause", "abort", None): return 0.0
    if mission_type == "HEDGE":
        new_term = target_pct if target_pct else HEDGE_TERM_PCT
    elif mission_type == "OPPORTUNITY":
        new_term = (100 - target_pct) if target_pct else OPP_TERM_PCT
    else: return 0.0
    mission_cost = simulate_cost(new_term, term_anchor, window)
    if not mission_cost: return None
    return (default_cost - mission_cost) / default_cost * 100

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Loop

# COMMAND ----------

import time as _time
run_id = f"llm_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"
print(f"run_id={run_id}, processing {len(sampled)}...")

results_rows = []
t0 = _time.time()
for idx, (d, zone) in enumerate(sampled):
    if idx % 20 == 0 and idx > 0:
        elapsed = _time.time() - t0
        eta = elapsed / idx * (len(sampled) - idx)
        print(f"  [{idx}/{len(sampled)}] {elapsed:.0f}s, ETA {eta:.0f}s")

    ctx = fetch_context(d)
    if ctx is None:
        results_rows.append({
            "run_id": run_id, "as_of_date": d, "zone": zone,
            "pattern_score": None, "confidence_score": None,
            "action_type": None, "mission_type": None,
            "target_pct": None, "duration_days": None,
            "saving_7d_pct": None, "saving_30d_pct": None, "saving_90d_pct": None,
            "dubai_at_signal_usd": None, "dubai_30d_usd": None, "dubai_90d_usd": None,
            "reasoning": f"[zone={zone}] no_context",
            "computed_at": datetime.now(timezone.utc),
        })
        continue

    llm_out = call_llm(d, ctx)
    action = llm_out.get("action_type")
    mission = llm_out.get("mission_type")
    target_pct = llm_out.get("target_pct")
    dur = llm_out.get("duration_days") or 30
    conf = llm_out.get("confidence_score")
    reason_text = llm_out.get("reasoning") or llm_out.get("_error") or ""
    reason = f"[zone={zone}] {reason_text[:480]}"

    s7 = compute_saving(action, mission, target_pct, ctx["dubai_0"], ctx["daily_dubai"], 7)
    s30 = compute_saving(action, mission, target_pct, ctx["dubai_0"], ctx["daily_dubai"], 30)
    s90 = compute_saving(action, mission, target_pct, ctx["dubai_0"], ctx["daily_dubai"], 90)

    results_rows.append({
        "run_id": run_id, "as_of_date": d, "zone": zone,
        "pattern_score": ctx["pattern_score"],
        "confidence_score": conf,
        "action_type": action, "mission_type": mission,
        "target_pct": target_pct if isinstance(target_pct, int) else None,
        "duration_days": dur,
        "saving_7d_pct": s7, "saving_30d_pct": s30, "saving_90d_pct": s90,
        "dubai_at_signal_usd": ctx["dubai_0"],
        "dubai_30d_usd": ctx["dubai_30d"], "dubai_90d_usd": ctx["dubai_90d"],
        "reasoning": reason,
        "computed_at": datetime.now(timezone.utc),
    })

elapsed = _time.time() - t0
print(f"{len(results_rows)} records in {elapsed:.0f}s")

# COMMAND ----------

# Write — Lakebase Postgres (AI-generated content → OLTP)
# OAuth token (60min lifetime) → psycopg connect → executemany INSERT
def _dec(v, scale):
    if v is None: return None
    try: return Decimal(str(round(float(v), scale)))
    except (ValueError, TypeError): return None

w_sdk = WorkspaceClient()
# postgres namespace는 databricks-sdk >=0.106에서 endpoint kwarg 지원.
# (database namespace는 instance_names kwarg — signature 다름)
credential = w_sdk.postgres.generate_database_credential(endpoint=LAKEBASE_ENDPOINT_PATH)
if not credential.token:
    raise RuntimeError("Lakebase OAuth token empty")

conninfo = (
    f"host={LAKEBASE_HOST} port=5432 dbname={LAKEBASE_DATABASE} "
    f"user={LAKEBASE_USER} sslmode=require"
)

insert_sql = """
    INSERT INTO backtest_predictions (
        run_id, as_of_date, zone, pattern_score, confidence_score,
        action_type, mission_type, target_pct, duration_days,
        saving_7d_pct, saving_30d_pct, saving_90d_pct,
        dubai_at_signal_usd, dubai_30d_usd, dubai_90d_usd,
        reasoning, computed_at
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    )
"""

rows_tuples = [(
    r["run_id"], r["as_of_date"], r["zone"],
    _dec(r["pattern_score"], 2), _dec(r["confidence_score"], 2),
    r["action_type"], r["mission_type"], r["target_pct"], r["duration_days"],
    _dec(r["saving_7d_pct"], 4), _dec(r["saving_30d_pct"], 4), _dec(r["saving_90d_pct"], 4),
    _dec(r["dubai_at_signal_usd"], 2), _dec(r["dubai_30d_usd"], 2), _dec(r["dubai_90d_usd"], 2),
    r["reasoning"], r["computed_at"],
) for r in results_rows]

with psycopg.connect(conninfo, password=credential.token) as conn:
    with conn.cursor() as cur:
        cur.executemany(insert_sql, rows_tuples)
    conn.commit()

print(f"{len(rows_tuples)} rows inserted into Lakebase backtest_predictions")

# COMMAND ----------

# Quick summary (in-Python from results_rows — Lakebase select 불필요)
from collections import defaultdict

groups = defaultdict(list)
for r in results_rows:
    if r["action_type"] == "new_mission":
        groups[r["mission_type"] or "-"].append(r)

print("\n=== Summary ===")
for mt, rs in sorted(groups.items()):
    n = len(rs)
    confs = [r["confidence_score"] for r in rs if r["confidence_score"] is not None]
    s30s = [r["saving_30d_pct"] for r in rs if r["saving_30d_pct"] is not None]
    avg_conf = round(sum(confs) / len(confs), 1) if confs else None
    avg_s30 = round(sum(s30s) / len(s30s), 3) if s30s else None
    hit = round(sum(1 for s in s30s if s > 0) * 100.0 / len(s30s), 1) if s30s else None
    print(f"  {mt:<13} n={n} conf={avg_conf} s30={avg_s30} hit30={hit}%")

n_errors = sum(1 for r in results_rows if r["reasoning"] and "no_context" in r["reasoning"])

# COMMAND ----------

dbutils.notebook.exit(json.dumps({
    "run_id": run_id, "n_samples": len(results_rows),
    "errors": n_errors,
    "elapsed_s": round(elapsed, 0),
    "n_per_zone": N_PER_ZONE,
}))
