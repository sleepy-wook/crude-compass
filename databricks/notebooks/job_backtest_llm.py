# Databricks notebook source
# MAGIC %md
# MAGIC # Sprint 3 Day 4 — LLM Mission Plan Agent Backtest v4 ⭐⭐
# MAGIC
# MAGIC ## 시나리오 본질 재정렬 (형욱님 push back 5/12 반영)
# MAGIC - 시나리오 = 단순 "가격 예측" 아님. **Term vs Spot 비중 의사결정**.
# MAGIC - 평가 axis = **Landing Cost 절감액** (±10% binary hit 아님)
# MAGIC - 진짜 AI = Mission Plan Agent (rule-based scoring + LLM 권고)
# MAGIC
# MAGIC ## v4 디자인
# MAGIC - **Random sampling**: 100 dates (시드 42, stratified — 매 ~7일에 1개)
# MAGIC - **Look-ahead 방지**: D-90 ~ D 데이터만 LLM 제공, D 이후 절대 노출 X
# MAGIC - **Multi-horizon**: 7일 / 30일 / 90일 cost saving 동시 측정
# MAGIC - **LLM = Claude Haiku 4.5** (Mission Plan Agent inline call)
# MAGIC - **Outcome = Cost saving %** vs default mix (Term 60% / Spot 40%)
# MAGIC
# MAGIC ## K-Petroleum 가상 baseline mix (시나리오 §3)
# MAGIC | Mission | Term | Spot |
# MAGIC |---|---|---|
# MAGIC | default (no AI) | 60% | 40% |
# MAGIC | HEDGE | 75% (+15%p) | 25% |
# MAGIC | OPP | 40% | 60% (+20%p) |
# MAGIC
# MAGIC Term contract = D 시점 Dubai close × (1 - 0.05) (5% 장기계약 할인 가정)

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
dbutils.widgets.text("n_samples", "100", "Sample size")
dbutils.widgets.text("seed", "42", "Random seed")
dbutils.widgets.text("smoke_test", "false", "Smoke test (5 samples only)")

N_SAMPLES = int(dbutils.widgets.get("n_samples"))
SEED = int(dbutils.widgets.get("seed"))
SMOKE_TEST = dbutils.widgets.get("smoke_test").lower() == "true"

if SMOKE_TEST:
    N_SAMPLES = 5
    print("⚠️  SMOKE TEST mode — only 5 samples")

LLM_ENDPOINT = "databricks-claude-haiku-4-5"
TARGET_TABLE = "crude_compass.gold.llm_backtest_predictions"

# K-Petroleum mix params
DEFAULT_TERM_PCT = 60
HEDGE_TERM_PCT = 75    # +15%p
OPP_TERM_PCT = 40      # Spot +20%p (so Term -20%p)
TERM_DISCOUNT = 0.05   # Term contract 5% discount

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Build Pattern Score view (D-90 ~ D, look-ahead 없음)

# COMMAND ----------

# Pattern Score view — backtest_compute v3 D variant 동일 로직 (multi-source + z-norm)
pattern_view_sql = """
CREATE OR REPLACE TEMP VIEW _llm_signals_unified AS
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
n_signals = spark.sql("SELECT COUNT(*) FROM _llm_signals_unified").collect()[0][0]
print(f"Unified signals: {n_signals}")

# Dubai daily view
spark.sql("""
    CREATE OR REPLACE TEMP VIEW _llm_dubai AS
    SELECT trade_date AS price_date, CAST(price_usd AS DOUBLE) AS dubai_close
    FROM crude_compass.bronze.oil_prices_daily
    WHERE ticker='DUBAI'
""")

# COMMAND ----------

# Pattern Score per date — multi-source z-norm (D variant 동일)
pattern_score_sql = """
CREATE OR REPLACE TEMP VIEW _llm_pattern_daily AS
WITH date_dim AS (
    SELECT explode(sequence(DATE'2023-04-01', DATE'2026-01-31', INTERVAL 1 DAY)) AS as_of_date
),
contribs AS (
    SELECT d.as_of_date, s.direction, s.category, s.signal_type,
           crude_compass.functions.weighted_signal(
               s.raw_intensity,
               CAST(DATEDIFF(d.as_of_date, s.event_date) AS INT),
               s.signal_type, s.source_credibility
           ) AS w
    FROM date_dim d JOIN _llm_signals_unified s
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
print(f"Pattern Score view created")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Stratified random sampling

# COMMAND ----------

# 거래일 + Pattern Score 있는 날만 (look-ahead window: D + 90일 outcome 필요)
sample_pool = spark.sql("""
    SELECT p.as_of_date
    FROM _llm_pattern_daily p
    JOIN _llm_dubai b ON p.as_of_date = b.price_date
    WHERE p.as_of_date <= (SELECT DATE_SUB(MAX(price_date), 90) FROM _llm_dubai)
    ORDER BY p.as_of_date
""").collect()
all_dates = [r.as_of_date for r in sample_pool]
print(f"Eligible date pool: {len(all_dates)} (need ≥{N_SAMPLES})")

# Stratified: 동일 간격 + 시드 기반 랜덤 offset
random.seed(SEED)
if N_SAMPLES >= len(all_dates):
    sampled_dates = all_dates
else:
    stride = len(all_dates) // N_SAMPLES
    sampled_dates = []
    for i in range(N_SAMPLES):
        offset = random.randint(0, max(stride - 1, 0))
        idx = min(i * stride + offset, len(all_dates) - 1)
        sampled_dates.append(all_dates[idx])

print(f"Sampled {len(sampled_dates)} dates")
print(f"First 5: {sampled_dates[:5]}")
print(f"Last 5: {sampled_dates[-5:]}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Mission Plan Agent (inline LLM call)

# COMMAND ----------

w = WorkspaceClient()

# System prompt — backtest mode emphasizes look-ahead 금지
SYSTEM_PROMPT_BACKTEST = """You are **Crude Compass Mission Plan Agent** — a decision-support copilot for Korean petroleum refinery (K-Petroleum) procurement managers.

## ⚠️ BACKTEST MODE — CRITICAL CONSTRAINT
You are evaluating signals at a HISTORICAL date. You have access ONLY to data BEFORE the given date.
DO NOT assume any knowledge of events AFTER the given date.
Reason based purely on the signals provided.

## 역할
1. Pattern Score 분석 → Bidirectional Mission 권고 (HEDGE / OPPORTUNITY)
2. 또는 시그널 약함 → STAY (no_action)
3. Confidence Score 함께 산출

## Bidirectional Score → Action
- Pattern Score 70+ → HEDGE Mission (Term 비중 ↑, e.g. 60% → 75%)
- Pattern Score 30 이하 → OPP Mission (Spot 비중 ↑, e.g. 40% → 60%)
- 30~70 → STAY (no action, action_type=continue)

## K-Petroleum baseline mix
- 평시 default: Term 60% / Spot 40%
- HEDGE 권고 시: Term 75% / Spot 25% (target_pct = 75)
- OPP 권고 시: Term 40% / Spot 60% (target_pct = 60, 즉 Spot 60)

## Output: STRICT JSON ONLY

{
  "action_type": "new_mission" | "continue",
  "mission_type": "HEDGE" | "OPPORTUNITY" | "NONE",
  "target_pct": <int, HEDGE면 Term %, OPP면 Spot %>,
  "duration_days": <int, 7-90>,
  "confidence_score": <0-100>,
  "reasoning": "한국어 3-5문장 — 어떤 시그널 catch했는지"
}

If STAY: {"action_type": "continue", "mission_type": "NONE", "target_pct": null, "duration_days": null, "confidence_score": <0-100>, "reasoning": "..."}

JSON만 반환. markdown code fence (```) 도 금지."""


def call_llm(as_of_date, pattern_score, bullish, bearish, sig_count, cv_bonus, top_signals_text):
    """Mission Plan Agent inline call. Returns dict or None."""
    user_msg = f"""## Backtest date: {as_of_date}

**Pattern Score**: {pattern_score:.1f}
- bullish_score: {bullish:.1f}
- bearish_score: {bearish:.1f}
- cross_val_bonus: {cv_bonus:.1f}
- signal_count_90d: {sig_count}

## Top signals (last 90d before {as_of_date}, importance desc)
{top_signals_text}

→ Recommend action (HEDGE / OPPORTUNITY / continue). Return JSON only.
Remember: do NOT use any information after {as_of_date}."""

    try:
        resp = w.serving_endpoints.query(
            name=LLM_ENDPOINT,
            messages=[
                ChatMessage(role=ChatMessageRole.SYSTEM, content=SYSTEM_PROMPT_BACKTEST),
                ChatMessage(role=ChatMessageRole.USER, content=user_msg),
            ],
            max_tokens=600,
            temperature=0.0,
        )
        raw = resp.choices[0].message.content if resp.choices else "{}"
        # strip markdown fence
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
# MAGIC ## Step 4: Loop — fetch context + LLM + outcome per date

# COMMAND ----------

def fetch_context(as_of_date):
    """Fetch Pattern Score + top signals + Dubai outcome for as_of_date."""
    # Pattern Score
    ps_rows = spark.sql(f"""
        SELECT pattern_score, bullish, bearish, sig_count, cross_val_bonus
        FROM _llm_pattern_daily WHERE as_of_date = DATE'{as_of_date}'
    """).collect()
    if not ps_rows:
        return None
    ps = ps_rows[0]

    # Top signals (D-90 ~ D)
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

    # Dubai at signal + outcomes
    dubai_rows = spark.sql(f"""
        SELECT
            (SELECT dubai_close FROM _llm_dubai WHERE price_date = DATE'{as_of_date}') AS d0,
            (SELECT dubai_close FROM _llm_dubai WHERE price_date >= DATE'{as_of_date}' + INTERVAL 7 DAYS  ORDER BY price_date LIMIT 1) AS d7,
            (SELECT dubai_close FROM _llm_dubai WHERE price_date >= DATE'{as_of_date}' + INTERVAL 30 DAYS ORDER BY price_date LIMIT 1) AS d30,
            (SELECT dubai_close FROM _llm_dubai WHERE price_date >= DATE'{as_of_date}' + INTERVAL 90 DAYS ORDER BY price_date LIMIT 1) AS d90
    """).collect()[0]

    # Daily Dubai for cost simulation
    daily_rows = spark.sql(f"""
        SELECT price_date, dubai_close FROM _llm_dubai
        WHERE price_date > DATE'{as_of_date}' AND price_date <= DATE'{as_of_date}' + INTERVAL 90 DAYS
        ORDER BY price_date
    """).collect()
    daily_dubai = [(r.price_date, float(r.dubai_close)) for r in daily_rows]

    return {
        "pattern_score": float(ps.pattern_score),
        "bullish": float(ps.bullish),
        "bearish": float(ps.bearish),
        "sig_count": int(ps.sig_count),
        "cv_bonus": float(ps.cross_val_bonus),
        "signals_text": signals_text,
        "dubai_0": float(dubai_rows.d0) if dubai_rows.d0 else None,
        "dubai_7d": float(dubai_rows.d7) if dubai_rows.d7 else None,
        "dubai_30d": float(dubai_rows.d30) if dubai_rows.d30 else None,
        "dubai_90d": float(dubai_rows.d90) if dubai_rows.d90 else None,
        "daily_dubai": daily_dubai,
    }


def simulate_cost(term_pct, term_anchor, daily_spot_prices):
    """Mix cost over duration."""
    if not daily_spot_prices: return None
    spot_pct = (100 - term_pct) / 100.0
    spot_avg = sum(p for _, p in daily_spot_prices) / len(daily_spot_prices)
    return (term_pct / 100.0) * term_anchor + spot_pct * spot_avg


def compute_saving(action_type, mission_type, target_pct, duration_days, dubai_at_signal, daily_dubai, horizon_days):
    """AI 권고 따랐을 때 vs default mix cost saving %.

    Positive = 권고가 default 대비 비용 절감 (good for K-Petroleum)
    """
    if dubai_at_signal is None or not daily_dubai: return None

    # Limit to horizon
    window = [(d, p) for d, p in daily_dubai if (d - daily_dubai[0][0]).days + 1 <= horizon_days]
    if not window: return None

    term_anchor = dubai_at_signal * (1 - TERM_DISCOUNT)
    default_cost = simulate_cost(DEFAULT_TERM_PCT, term_anchor, window)

    # AI 권고에 따른 mix
    if action_type in ("continue", "pause", "abort", None):
        return 0.0  # No action taken
    if mission_type == "HEDGE":
        new_term = target_pct if target_pct else HEDGE_TERM_PCT
    elif mission_type == "OPPORTUNITY":
        # target_pct는 OPP 시 Spot %
        new_term = (100 - target_pct) if target_pct else OPP_TERM_PCT
    else:
        return 0.0

    mission_cost = simulate_cost(new_term, term_anchor, window)
    if not mission_cost or default_cost == 0: return None
    return (default_cost - mission_cost) / default_cost * 100

# COMMAND ----------

# Loop — Smoke test 또는 Full
import time as _time
run_id = f"llm_backtest_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"
print(f"run_id = {run_id}")
print(f"Processing {len(sampled_dates)} dates...")

results_rows = []
t0 = _time.time()
for idx, d in enumerate(sampled_dates):
    if idx % 10 == 0 and idx > 0:
        elapsed = _time.time() - t0
        print(f"  [{idx}/{len(sampled_dates)}] {elapsed:.0f}s elapsed, ETA {elapsed/idx*(len(sampled_dates)-idx):.0f}s")

    ctx = fetch_context(d)
    if ctx is None:
        results_rows.append({
            "run_id": run_id, "sample_idx": idx, "as_of_date": d,
            "pattern_score": None, "bullish_score": None, "bearish_score": None,
            "cross_val_bonus": None, "signal_count_90d": None,
            "action_type": None, "mission_type": None, "target_pct": None,
            "duration_days": None, "confidence_score": None, "reasoning": None,
            "dubai_at_signal": None, "dubai_7d": None, "dubai_30d": None, "dubai_90d": None,
            "cost_saving_7d": None, "cost_saving_30d": None, "cost_saving_90d": None,
            "llm_error": "no_context",
            "computed_at": datetime.now(timezone.utc),
        })
        continue

    # Call LLM
    llm_out = call_llm(d, ctx["pattern_score"], ctx["bullish"], ctx["bearish"],
                       ctx["sig_count"], ctx["cv_bonus"], ctx["signals_text"])
    err = llm_out.get("_error") if "_error" in llm_out else None
    action = llm_out.get("action_type")
    mission = llm_out.get("mission_type")
    target_pct = llm_out.get("target_pct")
    dur = llm_out.get("duration_days") or 30
    conf = llm_out.get("confidence_score")
    reason = llm_out.get("reasoning", "")[:500]

    # Compute saving per horizon
    s7  = compute_saving(action, mission, target_pct, dur, ctx["dubai_0"], ctx["daily_dubai"], 7)
    s30 = compute_saving(action, mission, target_pct, dur, ctx["dubai_0"], ctx["daily_dubai"], 30)
    s90 = compute_saving(action, mission, target_pct, dur, ctx["dubai_0"], ctx["daily_dubai"], 90)

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
print(f"✅ {len(results_rows)} records processed in {elapsed:.0f}s")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Write to gold.llm_backtest_predictions

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

typed = []
for r in results_rows:
    typed.append((
        r["run_id"], r["sample_idx"], r["as_of_date"],
        _dec(r["pattern_score"], 5, 2),
        _dec(r["bullish_score"], 8, 2),
        _dec(r["bearish_score"], 8, 2),
        _dec(r["cross_val_bonus"], 5, 2),
        r["signal_count_90d"],
        r["action_type"], r["mission_type"], r["target_pct"], r["duration_days"],
        _dec(r["confidence_score"], 5, 2),
        r["reasoning"],
        _dec(r["dubai_at_signal"], 8, 2),
        _dec(r["dubai_7d"], 8, 2),
        _dec(r["dubai_30d"], 8, 2),
        _dec(r["dubai_90d"], 8, 2),
        _dec(r["cost_saving_7d"], 6, 3),
        _dec(r["cost_saving_30d"], 6, 3),
        _dec(r["cost_saving_90d"], 6, 3),
        r["llm_error"], r["computed_at"],
    ))

df_out = spark.createDataFrame(typed, schema=schema)
df_out.write.mode("append").saveAsTable(TARGET_TABLE)
print(f"✅ {len(typed)} rows appended to {TARGET_TABLE}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Aggregate metrics

# COMMAND ----------

summary = spark.sql(f"""
    SELECT
        action_type,
        mission_type,
        COUNT(*) AS n,
        ROUND(AVG(confidence_score), 1) AS avg_conf,
        ROUND(AVG(cost_saving_7d), 3) AS avg_save_7d,
        ROUND(AVG(cost_saving_30d), 3) AS avg_save_30d,
        ROUND(AVG(cost_saving_90d), 3) AS avg_save_90d,
        ROUND(SUM(CASE WHEN cost_saving_30d > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS hit_30d_pct
    FROM {TARGET_TABLE}
    WHERE run_id = '{run_id}'
    GROUP BY action_type, mission_type
    ORDER BY action_type, mission_type
""").collect()

print(f"\n=== Backtest v4 summary (run_id={run_id}) ===")
print(f"{'action':<14} {'mission':<13} {'n':>3} {'avg_conf':>9} {'save_7d':>9} {'save_30d':>9} {'save_90d':>9} {'hit_30d':>9}")
for r in summary:
    print(f"{(r.action_type or '-'):<14} {(r.mission_type or '-'):<13} {r.n:>3} "
          f"{r.avg_conf or 0:>9} {r.avg_save_7d or 0:>9} {r.avg_save_30d or 0:>9} "
          f"{r.avg_save_90d or 0:>9} {r.hit_30d_pct or 0:>9}%")

# COMMAND ----------

dbutils.notebook.exit(json.dumps({
    "run_id": run_id,
    "n_samples": len(results_rows),
    "errors": sum(1 for r in results_rows if r["llm_error"]),
    "elapsed_s": round(elapsed, 0),
}))
