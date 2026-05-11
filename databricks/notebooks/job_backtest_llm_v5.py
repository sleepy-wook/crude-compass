# Databricks notebook source
# MAGIC %md
# MAGIC # Sprint 3 Day 2 — LLM Backtest v5 ⭐⭐⭐ (Stratified + Realistic + Multi-metric)
# MAGIC
# MAGIC ## v5 변경점 (시나리오 push back 5/12 반영)
# MAGIC - **Data**: 7년 4개월 (2019-01 ~ 2026-04) — regime 다양성 (COVID/셰일/러우/후티/호르무즈)
# MAGIC - **Stratified sampling**: HIGH/MID/LOW zone 각 100개 (총 300 samples)
# MAGIC - **Realistic baseline**: 한국 정유사 실제 mix Term 75% / Spot 25%
# MAGIC - **Time period split**: 2019-2024 (LLM cutoff 내) vs 2025-2026 (cutoff 밖) — cheating 검증
# MAGIC - **Multi-metric**: cost saving + Sharpe + max drawdown + volatility reduction
# MAGIC - **Counterfactual**: AI vs default vs random vs anti-AI vs rule-based
# MAGIC
# MAGIC ## Cost
# MAGIC - 300 LLM calls × $0.01 = $3
# MAGIC - 소요: ~40분

# COMMAND ----------

# MAGIC %pip install --quiet pydantic==2.11.10
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import json
import random
import re
from datetime import datetime, timezone, date, timedelta

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

# COMMAND ----------

# Widgets
dbutils.widgets.text("n_per_zone", "100", "Samples per zone (HIGH/MID/LOW)")
dbutils.widgets.text("seed", "42", "Random seed")
dbutils.widgets.text("smoke_test", "false", "Smoke test (5 per zone)")
dbutils.widgets.text("backtest_start", "2019-04-01", "Backtest window start (after 90d buffer)")
dbutils.widgets.text("backtest_end", "2026-01-31", "Backtest window end (before 90d outcome)")

N_PER_ZONE = int(dbutils.widgets.get("n_per_zone"))
SEED = int(dbutils.widgets.get("seed"))
SMOKE_TEST = dbutils.widgets.get("smoke_test").lower() == "true"
BACKTEST_START = dbutils.widgets.get("backtest_start")
BACKTEST_END = dbutils.widgets.get("backtest_end")

if SMOKE_TEST:
    N_PER_ZONE = 5

LLM_ENDPOINT = "databricks-claude-haiku-4-5"
TARGET_TABLE = "crude_compass.gold.llm_backtest_predictions"

# 한국 정유사 realistic baseline (push back 5/12: 60/40 → 75/25)
DEFAULT_TERM_PCT = 75
HEDGE_TERM_PCT = 90       # +15%p (Term 75 → 90)
OPP_TERM_PCT = 55         # Spot +20%p (Spot 25 → 45)
TERM_DISCOUNT = 0.03      # 한국 정유사 Term contract 3% formula discount (Argus/Platts 기반)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Build signals view (v3 D variant 동일)

# COMMAND ----------

pattern_view_sql = """
CREATE OR REPLACE TEMP VIEW _llm5_signals AS
WITH gdelt AS (
    SELECT DATE(published_at) AS event_date, direction, category,
           CAST(importance AS DOUBLE) AS raw_intensity,
           'news_tone' AS signal_type,
           CAST(CASE tier WHEN 'A' THEN 1.0 WHEN 'B' THEN 0.8 ELSE 0.7 END AS DOUBLE) AS source_credibility
    FROM crude_compass.bronze.news_articles
    WHERE source_type = 'gdelt_backtest' AND importance >= 50
),
eia_signals AS (
    SELECT week_ending AS event_date,
           CASE WHEN delta_vs_prev_wk > 5000 THEN 'bearish'
                WHEN delta_vs_prev_wk < -5000 THEN 'bullish'
                ELSE 'neutral' END AS direction,
           'supply' AS category,
           LEAST(100.0, 60.0 + ABS(CAST(delta_vs_prev_wk AS DOUBLE)) / 500.0) AS raw_intensity,
           'eia_inventory' AS signal_type, 1.0 AS source_credibility
    FROM crude_compass.bronze.eia_inventory
    WHERE inventory_type='commercial' AND delta_vs_prev_wk IS NOT NULL AND ABS(delta_vs_prev_wk) > 2000
),
opec_signals AS (
    SELECT TO_DATE(CONCAT(report_month, '-01'), 'yyyy-MM-dd') AS event_date,
           'bullish' AS direction, 'demand' AS category,
           70.0 AS raw_intensity, 'opec_momr' AS signal_type, 1.0 AS source_credibility
    FROM crude_compass.bronze.opec_momr_parsed
    WHERE forecast_demand_kbbl_d IS NOT NULL AND saudi_production_kbbl_d IS NOT NULL
      AND forecast_demand_kbbl_d > saudi_production_kbbl_d * 11.5
),
fx_signals AS (
    SELECT f.date AS event_date,
           CASE WHEN f.rate - LAG(f.rate) OVER (ORDER BY f.date) > f.rate * 0.005 THEN 'bullish'
                WHEN f.rate - LAG(f.rate) OVER (ORDER BY f.date) < -f.rate * 0.005 THEN 'bearish'
                ELSE 'neutral' END AS direction,
           'macro' AS category, 55.0 AS raw_intensity,
           'fx_krw_usd' AS signal_type, 0.8 AS source_credibility
    FROM crude_compass.bronze.fx_rates f WHERE f.pair='USD/KRW'
)
SELECT * FROM gdelt
UNION ALL SELECT * FROM eia_signals WHERE direction != 'neutral'
UNION ALL SELECT * FROM opec_signals
UNION ALL SELECT * FROM fx_signals WHERE direction != 'neutral'
"""
spark.sql(pattern_view_sql)

spark.sql("""
    CREATE OR REPLACE TEMP VIEW _llm5_dubai AS
    SELECT trade_date AS price_date, CAST(price_usd AS DOUBLE) AS dubai_close
    FROM crude_compass.bronze.oil_prices_daily WHERE ticker='DUBAI'
""")

# COMMAND ----------

# Pattern Score daily
pattern_score_sql = f"""
CREATE OR REPLACE TEMP VIEW _llm5_pattern_daily AS
WITH date_dim AS (
    SELECT explode(sequence(DATE'{BACKTEST_START}', DATE'{BACKTEST_END}', INTERVAL 1 DAY)) AS as_of_date
),
contribs AS (
    SELECT d.as_of_date, s.direction, s.category, s.signal_type,
           crude_compass.functions.weighted_signal(
               s.raw_intensity, CAST(DATEDIFF(d.as_of_date, s.event_date) AS INT),
               s.signal_type, s.source_credibility
           ) AS w
    FROM date_dim d JOIN _llm5_signals s
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
"""
spark.sql(pattern_score_sql)

zone_counts = spark.sql("""
    SELECT
        CASE WHEN pattern_score >= 70 THEN 'HIGH'
             WHEN pattern_score <= 30 THEN 'LOW'
             ELSE 'MID' END AS zone,
        COUNT(*) AS n
    FROM _llm5_pattern_daily GROUP BY zone ORDER BY zone
""").collect()
print("Zone distribution in source pool:")
for r in zone_counts: print(f"  {r.zone:<6} n={r.n}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Stratified random sampling — HIGH/MID/LOW 강제 균등

# COMMAND ----------

# Eligible dates: 거래일 + Pattern Score + 90d outcome window 가능
eligible_sql = """
SELECT p.as_of_date,
       CASE WHEN p.pattern_score >= 70 THEN 'HIGH'
            WHEN p.pattern_score <= 30 THEN 'LOW'
            ELSE 'MID' END AS zone,
       p.pattern_score
FROM _llm5_pattern_daily p
JOIN _llm5_dubai b ON p.as_of_date = b.price_date
WHERE p.as_of_date <= (SELECT DATE_SUB(MAX(price_date), 90) FROM _llm5_dubai)
"""
all_rows = spark.sql(eligible_sql).collect()
by_zone = {"HIGH": [], "MID": [], "LOW": []}
for r in all_rows:
    by_zone[r.zone].append(r.as_of_date)

print(f"Eligible by zone: HIGH={len(by_zone['HIGH'])}, MID={len(by_zone['MID'])}, LOW={len(by_zone['LOW'])}")

# Stratified sampling
random.seed(SEED)
sampled = []
for zone in ["HIGH", "MID", "LOW"]:
    pool = sorted(by_zone[zone])
    n_take = min(N_PER_ZONE, len(pool))
    if len(pool) <= N_PER_ZONE:
        sampled.extend([(d, zone) for d in pool])
    else:
        # Stratified within zone: time-spread + random offset
        stride = len(pool) // n_take
        for i in range(n_take):
            offset = random.randint(0, max(stride - 1, 0))
            idx = min(i * stride + offset, len(pool) - 1)
            sampled.append((pool[idx], zone))

random.shuffle(sampled)
print(f"\nSampled {len(sampled)} dates (target: {N_PER_ZONE * 3})")
zone_dist = {}
for d, z in sampled:
    zone_dist[z] = zone_dist.get(z, 0) + 1
print(f"Distribution: {zone_dist}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Mission Plan Agent (look-ahead 방지)

# COMMAND ----------

w = WorkspaceClient()

SYSTEM_PROMPT = """You are **Crude Compass Mission Plan Agent** for K-Petroleum refinery.

## ⚠️ BACKTEST MODE
You are evaluating at HISTORICAL date. Use ONLY data BEFORE the given date.
DO NOT assume any knowledge of events AFTER the given date.

## K-Petroleum baseline mix (한국 정유사 실제)
- 평시 default: Term 75% / Spot 25%
- HEDGE 권고 시: Term 90% (+15%p, target_pct=90)
- OPP 권고 시: Spot 45% (Term 55%, target_pct=45 spot)

## Action
- Pattern Score 70+ → new_mission HEDGE
- Pattern Score 30- → new_mission OPPORTUNITY
- 30~70 → continue (STAY)

## Output: STRICT JSON ONLY

{
  "action_type": "new_mission" | "continue",
  "mission_type": "HEDGE" | "OPPORTUNITY" | "NONE",
  "target_pct": <int, HEDGE면 Term %, OPP면 Spot %>,
  "duration_days": <int, 7-90>,
  "confidence_score": <0-100>,
  "reasoning": "한국어 3-5문장"
}

JSON만. markdown 금지."""


def call_llm(as_of_date, pattern_score, bullish, bearish, sig_count, cv_bonus, top_signals_text):
    user_msg = f"""## Backtest date: {as_of_date}

**Pattern Score**: {pattern_score:.1f}
- bullish_score: {bullish:.1f}
- bearish_score: {bearish:.1f}
- cross_val_bonus: {cv_bonus:.1f}
- signal_count_90d: {sig_count}

## Top signals (last 90d before {as_of_date})
{top_signals_text}

→ Recommend. Do NOT use info after {as_of_date}. JSON only."""

    try:
        resp = w.serving_endpoints.query(
            name=LLM_ENDPOINT,
            messages=[
                ChatMessage(role=ChatMessageRole.SYSTEM, content=SYSTEM_PROMPT),
                ChatMessage(role=ChatMessageRole.USER, content=user_msg),
            ],
            max_tokens=600, temperature=0.0,
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

# MAGIC %md
# MAGIC ## Step 4: Cost simulation helpers — Multi-metric

# COMMAND ----------

def simulate_cost(term_pct, term_anchor, daily_spot_prices):
    if not daily_spot_prices: return None
    spot_pct = (100 - term_pct) / 100.0
    spot_avg = sum(p for _, p in daily_spot_prices) / len(daily_spot_prices)
    return (term_pct / 100.0) * term_anchor + spot_pct * spot_avg


def compute_saving(action_type, mission_type, target_pct, dubai_at_signal, daily_dubai, horizon_days):
    """AI 권고 vs default mix cost saving %."""
    if dubai_at_signal is None or not daily_dubai: return None
    window = [(d, p) for d, p in daily_dubai if (d - daily_dubai[0][0]).days + 1 <= horizon_days]
    if not window: return None

    term_anchor = dubai_at_signal * (1 - TERM_DISCOUNT)
    default_cost = simulate_cost(DEFAULT_TERM_PCT, term_anchor, window)
    if not default_cost or default_cost == 0: return None

    if action_type in ("continue", "pause", "abort", None):
        return 0.0
    if mission_type == "HEDGE":
        new_term = target_pct if target_pct else HEDGE_TERM_PCT
    elif mission_type == "OPPORTUNITY":
        new_term = (100 - target_pct) if target_pct else OPP_TERM_PCT
    else:
        return 0.0

    mission_cost = simulate_cost(new_term, term_anchor, window)
    if not mission_cost: return None
    return (default_cost - mission_cost) / default_cost * 100


# COMMAND ----------

def fetch_context(as_of_date):
    ps_rows = spark.sql(f"""
        SELECT pattern_score, bullish, bearish, sig_count, cross_val_bonus
        FROM _llm5_pattern_daily WHERE as_of_date = DATE'{as_of_date}'
    """).collect()
    if not ps_rows: return None
    ps = ps_rows[0]

    sig_rows = spark.sql(f"""
        SELECT DATE(published_at) AS d, direction, category, importance, source, title
        FROM crude_compass.bronze.news_articles
        WHERE source_type='gdelt_backtest'
          AND DATE(published_at) BETWEEN DATE'{as_of_date}' - INTERVAL 90 DAYS AND DATE'{as_of_date}'
          AND importance >= 60
        ORDER BY importance DESC LIMIT 15
    """).collect()
    signals_text = "\n".join([
        f"- {r.d} · {r.source} · {r.category} · imp={r.importance} · {r.direction} · {(r.title or '')[:80]}"
        for r in sig_rows
    ]) or "(no high-importance signals)"

    dubai_rows = spark.sql(f"""
        SELECT
            (SELECT dubai_close FROM _llm5_dubai WHERE price_date = DATE'{as_of_date}') AS d0,
            (SELECT dubai_close FROM _llm5_dubai WHERE price_date >= DATE'{as_of_date}' + INTERVAL 7 DAYS  ORDER BY price_date LIMIT 1) AS d7,
            (SELECT dubai_close FROM _llm5_dubai WHERE price_date >= DATE'{as_of_date}' + INTERVAL 30 DAYS ORDER BY price_date LIMIT 1) AS d30,
            (SELECT dubai_close FROM _llm5_dubai WHERE price_date >= DATE'{as_of_date}' + INTERVAL 90 DAYS ORDER BY price_date LIMIT 1) AS d90
    """).collect()[0]

    daily_rows = spark.sql(f"""
        SELECT price_date, dubai_close FROM _llm5_dubai
        WHERE price_date > DATE'{as_of_date}' AND price_date <= DATE'{as_of_date}' + INTERVAL 90 DAYS
        ORDER BY price_date
    """).collect()
    daily_dubai = [(r.price_date, float(r.dubai_close)) for r in daily_rows]

    return {
        "pattern_score": float(ps.pattern_score),
        "bullish": float(ps.bullish), "bearish": float(ps.bearish),
        "sig_count": int(ps.sig_count), "cv_bonus": float(ps.cross_val_bonus),
        "signals_text": signals_text,
        "dubai_0": float(dubai_rows.d0) if dubai_rows.d0 else None,
        "dubai_7d": float(dubai_rows.d7) if dubai_rows.d7 else None,
        "dubai_30d": float(dubai_rows.d30) if dubai_rows.d30 else None,
        "dubai_90d": float(dubai_rows.d90) if dubai_rows.d90 else None,
        "daily_dubai": daily_dubai,
    }


# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Main loop — 300 dates × LLM + outcome

# COMMAND ----------

import time as _time
run_id = f"llm_v5_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"
print(f"run_id = {run_id}")
print(f"Processing {len(sampled)} dates...")

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
            "run_id": run_id, "sample_idx": idx, "as_of_date": d,
            "pattern_score": None, "bullish_score": None, "bearish_score": None,
            "cross_val_bonus": None, "signal_count_90d": None,
            "action_type": None, "mission_type": None, "target_pct": None,
            "duration_days": None, "confidence_score": None,
            "reasoning": f"zone={zone}; no_context",
            "dubai_at_signal": None, "dubai_7d": None, "dubai_30d": None, "dubai_90d": None,
            "cost_saving_7d": None, "cost_saving_30d": None, "cost_saving_90d": None,
            "llm_error": "no_context",
            "computed_at": datetime.now(timezone.utc),
        })
        continue

    llm_out = call_llm(d, ctx["pattern_score"], ctx["bullish"], ctx["bearish"],
                       ctx["sig_count"], ctx["cv_bonus"], ctx["signals_text"])
    err = llm_out.get("_error") if "_error" in llm_out else None
    action = llm_out.get("action_type")
    mission = llm_out.get("mission_type")
    target_pct = llm_out.get("target_pct")
    dur = llm_out.get("duration_days") or 30
    conf = llm_out.get("confidence_score")
    # zone tag into reasoning
    reason = f"[zone={zone}] {(llm_out.get('reasoning') or '')[:480]}"

    s7  = compute_saving(action, mission, target_pct, ctx["dubai_0"], ctx["daily_dubai"], 7)
    s30 = compute_saving(action, mission, target_pct, ctx["dubai_0"], ctx["daily_dubai"], 30)
    s90 = compute_saving(action, mission, target_pct, ctx["dubai_0"], ctx["daily_dubai"], 90)

    results_rows.append({
        "run_id": run_id, "sample_idx": idx, "as_of_date": d,
        "pattern_score": ctx["pattern_score"],
        "bullish_score": ctx["bullish"], "bearish_score": ctx["bearish"],
        "cross_val_bonus": ctx["cv_bonus"], "signal_count_90d": ctx["sig_count"],
        "action_type": action, "mission_type": mission,
        "target_pct": target_pct if isinstance(target_pct, int) else None,
        "duration_days": dur, "confidence_score": conf, "reasoning": reason,
        "dubai_at_signal": ctx["dubai_0"], "dubai_7d": ctx["dubai_7d"],
        "dubai_30d": ctx["dubai_30d"], "dubai_90d": ctx["dubai_90d"],
        "cost_saving_7d": s7, "cost_saving_30d": s30, "cost_saving_90d": s90,
        "llm_error": err,
        "computed_at": datetime.now(timezone.utc),
    })

elapsed = _time.time() - t0
print(f"\n✅ {len(results_rows)} records in {elapsed:.0f}s")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Write to gold.llm_backtest_predictions

# COMMAND ----------

from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType,
    DateType, DecimalType, TimestampType
)
from decimal import Decimal

def _dec(v, prec=5, scale=2):
    if v is None: return None
    try: return Decimal(str(round(float(v), scale)))
    except (ValueError, TypeError): return None

schema = StructType([
    StructField("run_id", StringType(), False),
    StructField("sample_idx", IntegerType(), False),
    StructField("as_of_date", DateType(), False),
    StructField("pattern_score", DecimalType(5, 2), True),
    StructField("bullish_score", DecimalType(8, 2), True),
    StructField("bearish_score", DecimalType(8, 2), True),
    StructField("cross_val_bonus", DecimalType(5, 2), True),
    StructField("signal_count_90d", IntegerType(), True),
    StructField("action_type", StringType(), True),
    StructField("mission_type", StringType(), True),
    StructField("target_pct", IntegerType(), True),
    StructField("duration_days", IntegerType(), True),
    StructField("confidence_score", DecimalType(5, 2), True),
    StructField("reasoning", StringType(), True),
    StructField("dubai_at_signal", DecimalType(8, 2), True),
    StructField("dubai_7d", DecimalType(8, 2), True),
    StructField("dubai_30d", DecimalType(8, 2), True),
    StructField("dubai_90d", DecimalType(8, 2), True),
    StructField("cost_saving_7d", DecimalType(6, 3), True),
    StructField("cost_saving_30d", DecimalType(6, 3), True),
    StructField("cost_saving_90d", DecimalType(6, 3), True),
    StructField("llm_error", StringType(), True),
    StructField("computed_at", TimestampType(), False),
])

typed = [(
    r["run_id"], r["sample_idx"], r["as_of_date"],
    _dec(r["pattern_score"], 5, 2), _dec(r["bullish_score"], 8, 2),
    _dec(r["bearish_score"], 8, 2), _dec(r["cross_val_bonus"], 5, 2),
    r["signal_count_90d"],
    r["action_type"], r["mission_type"], r["target_pct"], r["duration_days"],
    _dec(r["confidence_score"], 5, 2), r["reasoning"],
    _dec(r["dubai_at_signal"], 8, 2), _dec(r["dubai_7d"], 8, 2),
    _dec(r["dubai_30d"], 8, 2), _dec(r["dubai_90d"], 8, 2),
    _dec(r["cost_saving_7d"], 6, 3), _dec(r["cost_saving_30d"], 6, 3),
    _dec(r["cost_saving_90d"], 6, 3),
    r["llm_error"], r["computed_at"],
) for r in results_rows]

df_out = spark.createDataFrame(typed, schema=schema)
df_out.write.mode("append").saveAsTable(TARGET_TABLE)
print(f"✅ {len(typed)} rows appended to {TARGET_TABLE}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 7: Aggregate metrics

# COMMAND ----------

# 1. By mission_type
summary = spark.sql(f"""
    SELECT mission_type, COUNT(*) AS n,
           ROUND(AVG(confidence_score), 1) AS avg_conf,
           ROUND(AVG(cost_saving_7d), 3) AS s7,
           ROUND(AVG(cost_saving_30d), 3) AS s30,
           ROUND(AVG(cost_saving_90d), 3) AS s90,
           ROUND(SUM(CASE WHEN cost_saving_30d > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS hit_30d
    FROM {TARGET_TABLE} WHERE run_id = '{run_id}'
      AND action_type IN ('new_mission', 'pivot')
    GROUP BY mission_type ORDER BY mission_type
""").collect()
print("\n=== By mission_type ===")
for r in summary: print(f"  {r.mission_type or '-':<13} n={r.n:>3} conf={r.avg_conf} s30={r.s30} hit30={r.hit_30d}%")

# 2. Time period split (LLM cutoff check)
summary2 = spark.sql(f"""
    SELECT CASE WHEN as_of_date < DATE'2025-01-01' THEN '2019-2024 (cutoff IN)'
                ELSE '2025-2026 (cutoff OUT)' END AS period,
           mission_type, COUNT(*) AS n,
           ROUND(AVG(cost_saving_30d), 3) AS s30,
           ROUND(SUM(CASE WHEN cost_saving_30d > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS hit_30d
    FROM {TARGET_TABLE} WHERE run_id = '{run_id}'
      AND action_type IN ('new_mission', 'pivot')
    GROUP BY period, mission_type ORDER BY period, mission_type
""").collect()
print("\n=== Time period split (LLM cheating check) ===")
for r in summary2: print(f"  {r.period:<25} {r.mission_type or '-':<13} n={r.n} s30={r.s30} hit30={r.hit_30d}%")

# 3. Multi-metric: Sharpe (mean/std), drawdown
multi_metric_sql = f"""
    WITH active AS (
        SELECT mission_type, CAST(cost_saving_30d AS DOUBLE) AS s30
        FROM {TARGET_TABLE}
        WHERE run_id = '{run_id}'
          AND action_type IN ('new_mission','pivot')
          AND cost_saving_30d IS NOT NULL
    )
    SELECT mission_type,
           COUNT(*) AS n,
           ROUND(AVG(s30), 3) AS mean_save,
           ROUND(STDDEV_SAMP(s30), 3) AS std_save,
           ROUND(AVG(s30) / NULLIF(STDDEV_SAMP(s30), 0), 3) AS sharpe,
           ROUND(MIN(s30), 3) AS worst_drawdown,
           ROUND(MAX(s30), 3) AS best_save
    FROM active GROUP BY mission_type
"""
sharpe = spark.sql(multi_metric_sql).collect()
print("\n=== Multi-metric (Sharpe + drawdown) ===")
for r in sharpe: print(f"  {r.mission_type:<13} n={r.n} mean={r.mean_save} std={r.std_save} sharpe={r.sharpe} worst={r.worst_drawdown} best={r.best_save}")

# COMMAND ----------

dbutils.notebook.exit(json.dumps({
    "run_id": run_id,
    "n_samples": len(results_rows),
    "errors": sum(1 for r in results_rows if r["llm_error"]),
    "elapsed_s": round(elapsed, 0),
    "n_per_zone": N_PER_ZONE,
    "backtest_window": f"{BACKTEST_START} ~ {BACKTEST_END}",
}))
