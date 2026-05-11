# Databricks notebook source
# MAGIC %md
# MAGIC # Sprint 3 Day 3 — Mock Backtest 산출 ⭐ v3 (multi-source + horizon sweep)
# MAGIC
# MAGIC ## 시나리오 v2 매핑
# MAGIC - § 부록 C Mock Backtest (양방향 architecture 검증)
# MAGIC - § 14 Phase 7 (Time Travel 백테스트 슬라이더 source)
# MAGIC
# MAGIC ## v3 변경점 (Day 3 후반 — 형욱님 push back 반영)
# MAGIC - **A. Multi-source weighting**: GDELT + EIA inventory delta + OPEC MoM + FX delta
# MAGIC - **B. Horizon sweep**: 14/30/60일 outcome 모두 측정 → 최선 horizon 선택
# MAGIC - **C. Cross-validation bonus 강화**: 카테고리 2+ source confirm 시 +15 (기존 +5)
# MAGIC - **D. Threshold tighten**: HEDGE 75+ / OPP 25- (기존 70/30)
# MAGIC - **E. Volatility-adjusted outcome**: ±10% 절대 → ±1σ Dubai rolling
# MAGIC
# MAGIC ## 데이터 의존성
# MAGIC - bronze.news_articles (gdelt_backtest, 17 queries × 3년 4개월)
# MAGIC - bronze.oil_prices_daily (DUBAI ticker)
# MAGIC - bronze.eia_inventory (3년 weekly)
# MAGIC - bronze.opec_momr_parsed (monthly with extracted indicators)
# MAGIC - bronze.fx_rates (KRW/USD daily)
# MAGIC - UC Function `weighted_signal()`
# MAGIC
# MAGIC ## Widget toggles
# MAGIC - variant: 'baseline' | 'D' | 'B' — D=A+B+C, B=A+B+C+D+E

# COMMAND ----------

import json
from datetime import datetime, timezone

# Widget — variant 선택
dbutils.widgets.dropdown("variant", "B", ["baseline", "D", "B"], "Variant (baseline=z-score만, D=A+B+C, B=A+B+C+D+E)")
VARIANT = dbutils.widgets.get("variant")

# Toggle flags
ENABLE_A = VARIANT in ("D", "B")   # multi-source
ENABLE_B = VARIANT in ("D", "B")   # horizon sweep
ENABLE_C = VARIANT in ("D", "B")   # CV bonus +15
ENABLE_D = VARIANT == "B"          # threshold tight 75/25
ENABLE_E = VARIANT == "B"          # vol-adj outcome

print(f"VARIANT={VARIANT}")
print(f"  A multi-source: {ENABLE_A}")
print(f"  B horizon sweep: {ENABLE_B}")
print(f"  C CV bonus strong: {ENABLE_C}")
print(f"  D threshold tight: {ENABLE_D}")
print(f"  E vol-adj outcome: {ENABLE_E}")

CV_BONUS = 15 if ENABLE_C else 5
THRESHOLD_HEDGE = 75 if ENABLE_D else 70
THRESHOLD_OPP = 25 if ENABLE_D else 30
HORIZONS = [14, 30, 60] if ENABLE_B else [30]

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Dubai daily price view

# COMMAND ----------

spark.sql("""
    CREATE OR REPLACE TEMP VIEW _dubai_daily AS
    SELECT
        trade_date AS price_date,
        CAST(price_usd AS DOUBLE) AS dubai_close_usd
    FROM crude_compass.bronze.oil_prices_daily
    WHERE ticker = 'DUBAI'
      AND trade_date BETWEEN DATE'2023-01-01' AND DATE'2026-04-30'
""")
n_dubai = spark.sql("SELECT COUNT(*) AS n FROM _dubai_daily").collect()[0].n
print(f"Dubai daily: {n_dubai} trade days")

# Dubai rolling 30-day stddev (E option용)
spark.sql("""
    CREATE OR REPLACE TEMP VIEW _dubai_with_vol AS
    SELECT
        price_date,
        dubai_close_usd,
        STDDEV_SAMP(dubai_close_usd / LAG(dubai_close_usd) OVER (ORDER BY price_date) - 1)
            OVER (ORDER BY price_date ROWS BETWEEN 60 PRECEDING AND 1 PRECEDING) AS vol_60d
    FROM _dubai_daily
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Multi-source signal table (A)

# COMMAND ----------

# 모든 source의 일별 시그널을 통합한 view 생성
# - GDELT (bronze.news_articles): 항상 사용
# - EIA inventory delta WoW: A enabled시 추가
# - OPEC MoM (Saudi production growth): A enabled시 추가
# - FX delta WoW (KRW weakness = bullish for imported oil cost): A enabled시 추가

signals_sql = """
WITH gdelt AS (
    SELECT
        DATE(published_at) AS event_date,
        direction,
        category,
        CAST(importance AS DOUBLE) AS raw_intensity,
        'news_tone' AS signal_type,
        CAST(CASE tier WHEN 'A' THEN 1.0 WHEN 'B' THEN 0.8 ELSE 0.7 END AS DOUBLE) AS source_credibility
    FROM crude_compass.bronze.news_articles
    WHERE source_type = 'gdelt_backtest'
      AND importance >= 50
)
"""

if ENABLE_A:
    signals_sql += """,
eia_signals AS (
    -- EIA inventory delta: build (>0) = bearish, draw (<0) = bullish
    SELECT
        week_ending AS event_date,
        CASE
            WHEN delta_vs_prev_wk > 5000 THEN 'bearish'    -- 5M bbl 이상 build
            WHEN delta_vs_prev_wk < -5000 THEN 'bullish'   -- 5M bbl 이상 draw
            ELSE 'neutral'
        END AS direction,
        'supply' AS category,
        LEAST(100.0, 60.0 + ABS(CAST(delta_vs_prev_wk AS DOUBLE)) / 500.0) AS raw_intensity,
        'eia_inventory' AS signal_type,
        1.0 AS source_credibility
    FROM crude_compass.bronze.eia_inventory
    WHERE inventory_type = 'commercial'
      AND delta_vs_prev_wk IS NOT NULL
      AND ABS(delta_vs_prev_wk) > 2000  -- 2M bbl 이상 변동만
),
opec_signals AS (
    -- OPEC MoM: Saudi production 증가 (>500 kbbl) = bearish, 감소 = bullish
    -- demand 증가 (>500) = bullish, 감소 = bearish
    SELECT
        TO_DATE(CONCAT(report_month, '-01'), 'yyyy-MM-dd') AS event_date,
        'bullish' AS direction,
        'demand' AS category,
        70.0 AS raw_intensity,
        'opec_momr' AS signal_type,
        1.0 AS source_credibility
    FROM crude_compass.bronze.opec_momr_parsed
    WHERE forecast_demand_kbbl_d IS NOT NULL
      AND saudi_production_kbbl_d IS NOT NULL
      AND forecast_demand_kbbl_d > saudi_production_kbbl_d * 11.5  -- demand > supply × OPEC share
),
fx_signals AS (
    -- KRW/USD spike: 일일 +1%↑ = bullish (KRW 약세 = 수입 원유 비용 ↑)
    SELECT
        f.date AS event_date,
        CASE
            WHEN f.rate - LAG(f.rate) OVER (ORDER BY f.date) > f.rate * 0.005 THEN 'bullish'
            WHEN f.rate - LAG(f.rate) OVER (ORDER BY f.date) < -f.rate * 0.005 THEN 'bearish'
            ELSE 'neutral'
        END AS direction,
        'macro' AS category,
        55.0 AS raw_intensity,
        'fx_krw_usd' AS signal_type,
        0.8 AS source_credibility
    FROM crude_compass.bronze.fx_rates f
    WHERE f.pair = 'USD/KRW'
)
"""

# Union all sources
if ENABLE_A:
    signals_sql += """
SELECT * FROM gdelt
UNION ALL
SELECT * FROM eia_signals WHERE direction != 'neutral'
UNION ALL
SELECT * FROM opec_signals
UNION ALL
SELECT * FROM fx_signals WHERE direction != 'neutral'
"""
else:
    signals_sql += """
SELECT * FROM gdelt
"""

spark.sql(f"CREATE OR REPLACE TEMP VIEW _signals_unified AS {signals_sql}")
n_signals = spark.sql("SELECT COUNT(*) FROM _signals_unified").collect()[0][0]
print(f"Unified signals (A={ENABLE_A}): {n_signals}")

# Source 분포
src_dist = spark.sql("""
    SELECT signal_type, direction, COUNT(*) AS n
    FROM _signals_unified
    GROUP BY signal_type, direction
    ORDER BY signal_type, direction
""").collect()
for r in src_dist:
    print(f"  {r.signal_type:<15} {r.direction:<8} n={r.n}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Daily Pattern Score with z-normalization (v3)

# COMMAND ----------

pattern_sql = f"""
WITH date_dim AS (
    SELECT explode(sequence(
        DATE'2023-04-01',
        DATE'2026-04-30',
        INTERVAL 1 DAY
    )) AS as_of_date
),
contribs AS (
    SELECT
        d.as_of_date,
        s.direction,
        s.category,
        s.signal_type,
        crude_compass.functions.weighted_signal(
            s.raw_intensity,
            CAST(DATEDIFF(d.as_of_date, s.event_date) AS INT),
            s.signal_type,
            s.source_credibility
        ) AS w
    FROM date_dim d
    JOIN _signals_unified s
        ON s.event_date BETWEEN d.as_of_date - INTERVAL 90 DAYS AND d.as_of_date
),
agg AS (
    SELECT
        as_of_date,
        SUM(CASE WHEN direction = 'bullish' THEN w ELSE 0 END) AS bullish,
        SUM(CASE WHEN direction = 'bearish' THEN w ELSE 0 END) AS bearish
    FROM contribs
    GROUP BY as_of_date
),
cross_val AS (
    SELECT
        as_of_date,
        SUM(CASE WHEN n >= 2 THEN {CV_BONUS} ELSE 0 END) AS cross_val_bonus
    FROM (
        SELECT as_of_date, category, direction, COUNT(DISTINCT signal_type) AS n
        FROM contribs
        WHERE direction IN ('bullish', 'bearish')
        GROUP BY as_of_date, category, direction
    )
    GROUP BY as_of_date
),
joined AS (
    SELECT a.as_of_date, a.bullish, a.bearish, a.bullish - a.bearish AS net,
           COALESCE(c.cross_val_bonus, 0) AS cross_val_bonus
    FROM agg a LEFT JOIN cross_val c ON a.as_of_date = c.as_of_date
),
rolling AS (
    SELECT *,
           AVG(net) OVER (ORDER BY as_of_date ROWS BETWEEN 90 PRECEDING AND 1 PRECEDING) AS mean_net,
           COALESCE(STDDEV_SAMP(net) OVER (ORDER BY as_of_date ROWS BETWEEN 90 PRECEDING AND 1 PRECEDING), 1.0) AS stddev_net
    FROM joined
),
scored AS (
    SELECT as_of_date, bullish, bearish, net, cross_val_bonus, mean_net, stddev_net,
           GREATEST(0.0, LEAST(100.0,
               50.0 + 25.0 * (net - mean_net) / GREATEST(stddev_net, 1.0) + cross_val_bonus
           )) AS pattern_score
    FROM rolling
    WHERE mean_net IS NOT NULL
)
SELECT as_of_date, pattern_score, bullish, bearish, cross_val_bonus,
       CASE
           WHEN pattern_score >= {THRESHOLD_HEDGE} THEN 'HEDGE'
           WHEN pattern_score <= {THRESHOLD_OPP}   THEN 'OPPORTUNITY'
           ELSE 'NONE'
       END AS zone
FROM scored
ORDER BY as_of_date
"""

df_daily = spark.sql(pattern_sql)
df_daily.createOrReplaceTempView("_daily_pattern")
n_days = df_daily.count()
print(f"daily Pattern Score: {n_days} days (threshold {THRESHOLD_HEDGE}/{THRESHOLD_OPP})")

zone_dist = spark.sql("""
    SELECT zone, COUNT(*) AS days,
           ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS pct
    FROM _daily_pattern GROUP BY zone ORDER BY zone
""").collect()
for r in zone_dist:
    print(f"  {r.zone:<13} {r.days:>4} days ({r.pct}%)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Signals with 7-day cool-down

# COMMAND ----------

signal_sql = """
WITH dp AS (
    SELECT d.as_of_date, d.zone, b.dubai_close_usd, b.vol_60d
    FROM _daily_pattern d
    LEFT JOIN _dubai_with_vol b ON d.as_of_date = b.price_date
    WHERE d.zone IN ('HEDGE', 'OPPORTUNITY')
      AND b.dubai_close_usd IS NOT NULL
),
ranked AS (
    SELECT as_of_date, zone, dubai_close_usd, vol_60d,
           LAG(as_of_date, 1) OVER (PARTITION BY zone ORDER BY as_of_date) AS prev_signal_date
    FROM dp
),
filtered AS (
    SELECT * FROM ranked
    WHERE prev_signal_date IS NULL OR DATEDIFF(as_of_date, prev_signal_date) >= 7
)
SELECT * FROM filtered ORDER BY as_of_date
"""
df_signals = spark.sql(signal_sql)
df_signals.createOrReplaceTempView("_signals")
n_signals_per_zone = spark.sql("SELECT zone, COUNT(*) AS n FROM _signals GROUP BY zone").collect()
for r in n_signals_per_zone:
    print(f"signal day {r.zone}: {r.n}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Horizon sweep — outcome for each {14, 30, 60} day window

# COMMAND ----------

# E option: volatility-adjusted threshold (±1σ rolling), 기본은 ±10% 절대
def get_outcome_sql(horizon: int, vol_adj: bool) -> str:
    if vol_adj:
        # ±1σ of horizon-adjusted vol
        thresh_clause = f"GREATEST(0.03, COALESCE(s.vol_60d, 0.05) * SQRT({horizon}))"
    else:
        thresh_clause = "0.10"
    return f"""
    WITH with_outcome AS (
        SELECT
            s.as_of_date AS signal_date,
            s.zone AS signal_type,
            s.dubai_close_usd AS dubai_at_signal,
            (
                SELECT b.dubai_close_usd FROM _dubai_daily b
                WHERE b.price_date >= s.as_of_date + INTERVAL {horizon} DAYS
                ORDER BY b.price_date LIMIT 1
            ) AS dubai_h,
            {thresh_clause} AS threshold
        FROM _signals s
    )
    SELECT
        signal_date, signal_type, dubai_at_signal, dubai_h, threshold,
        ROUND((dubai_h - dubai_at_signal) / dubai_at_signal * 100, 2) AS pct_change,
        CASE
            WHEN signal_type = 'HEDGE'       AND (dubai_h - dubai_at_signal) / dubai_at_signal >=  threshold THEN 1
            WHEN signal_type = 'OPPORTUNITY' AND (dubai_h - dubai_at_signal) / dubai_at_signal <= -threshold THEN 1
            ELSE 0
        END AS hit
    FROM with_outcome WHERE dubai_h IS NOT NULL
    """

# Horizon sweep
results_by_horizon = {}
for h in HORIZONS:
    out_sql = get_outcome_sql(h, ENABLE_E)
    summary = spark.sql(f"""
        WITH eval AS ({out_sql})
        SELECT signal_type,
               COUNT(*) AS n,
               SUM(hit) AS hit,
               ROUND(SUM(hit) * 100.0 / COUNT(*), 1) AS precision_pct
        FROM eval
        GROUP BY signal_type
        ORDER BY signal_type
    """).collect()
    results_by_horizon[h] = [(r.signal_type, r.n, r.hit, r.precision_pct) for r in summary]
    print(f"\n=== Horizon {h}d (vol_adj={ENABLE_E}) ===")
    for r in summary:
        print(f"  {r.signal_type:<13} n={r.n:>3} hit={r.hit:>3} precision={r.precision_pct}%")

# Best horizon per signal type
best_by_type: dict[str, dict] = {}
for h, rows in results_by_horizon.items():
    for sig_type, n, hit, prec in rows:
        cur = best_by_type.get(sig_type)
        # 우선 sample size ≥ 5 + 가장 높은 precision
        if n < 5: continue
        if cur is None or (prec or 0) > (cur["precision"] or 0):
            best_by_type[sig_type] = {"horizon": h, "n": n, "hit": hit, "precision": float(prec or 0)}

print(f"\n=== Best per signal type ===")
for st, b in best_by_type.items():
    print(f"  {st:<13} horizon={b['horizon']}d n={b['n']} hit={b['hit']} precision={b['precision']}%")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Lead time for best variant

# COMMAND ----------

lead_map = {}
if best_by_type:
    for sig_type, b in best_by_type.items():
        h = b["horizon"]
        out_sql = get_outcome_sql(h, ENABLE_E)
        lead_sql = f"""
        WITH eval AS ({out_sql}),
             hits AS (SELECT * FROM eval WHERE hit = 1 AND signal_type = '{sig_type}'),
             lead_pairs AS (
                 SELECT h.signal_date, h.signal_type, h.dubai_at_signal, h.threshold,
                        DATEDIFF(b.price_date, h.signal_date) AS days_offset,
                        CASE
                            WHEN h.signal_type = 'HEDGE'       AND (b.dubai_close_usd - h.dubai_at_signal) / h.dubai_at_signal >=  h.threshold THEN 1
                            WHEN h.signal_type = 'OPPORTUNITY' AND (b.dubai_close_usd - h.dubai_at_signal) / h.dubai_at_signal <= -h.threshold THEN 1
                            ELSE 0
                        END AS reached
                 FROM hits h
                 JOIN _dubai_daily b ON b.price_date > h.signal_date AND b.price_date <= h.signal_date + INTERVAL {h} DAYS
             ),
             first_reach AS (
                 SELECT signal_date, signal_type, MIN(days_offset) AS lead_days
                 FROM lead_pairs WHERE reached = 1
                 GROUP BY signal_date, signal_type
             )
        SELECT ROUND(AVG(lead_days), 1) AS avg_lead_days FROM first_reach
        """
        rows = spark.sql(lead_sql).collect()
        if rows and rows[0].avg_lead_days is not None:
            lead_map[sig_type] = float(rows[0].avg_lead_days)

print(f"\n=== Lead time ===")
for k, v in lead_map.items():
    print(f"  {k:<13} {v} days")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 7: gold.backtest_results 적재

# COMMAND ----------

now = datetime.now(timezone.utc)
run_id = f"backtest_v3_{VARIANT}_{now.strftime('%Y%m%dT%H%M%S')}"
window_label = f"variant={VARIANT} | A={ENABLE_A} B={ENABLE_B} C={ENABLE_C} D={ENABLE_D} E={ENABLE_E}"

from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DecimalType
from decimal import Decimal

typed_rows = []
for sig_type, b in best_by_type.items():
    lead = lead_map.get(sig_type)
    typed_rows.append((
        run_id, window_label[:200], sig_type, int(b["n"]), int(b["hit"]),
        Decimal(str(round(b["precision"], 2))),
        Decimal(str(round(lead, 1))) if lead is not None else None,
        Decimal(str(THRESHOLD_HEDGE if sig_type == "HEDGE" else THRESHOLD_OPP)),
    ))

if typed_rows:
    schema = StructType([
        StructField("run_id", StringType(), False),
        StructField("backtest_window", StringType(), False),
        StructField("mission_type", StringType(), False),
        StructField("signal_count", IntegerType(), False),
        StructField("correct_count", IntegerType(), False),
        StructField("accuracy_pct", DecimalType(5, 2), False),
        StructField("avg_lead_time_days", DecimalType(5, 1), True),
        StructField("threshold_used", DecimalType(5, 2), False),
    ])
    df_out = spark.createDataFrame(typed_rows, schema=schema)
    df_out.createOrReplaceTempView("_results_in")
    spark.sql(f"DELETE FROM crude_compass.gold.backtest_results WHERE run_id = '{run_id}'")
    spark.sql("""
        INSERT INTO crude_compass.gold.backtest_results
        SELECT run_id, backtest_window, mission_type, signal_count, correct_count,
               accuracy_pct, avg_lead_time_days, threshold_used, current_timestamp() AS computed_at
        FROM _results_in
    """)
    print(f"✅ {run_id} 적재")

# COMMAND ----------

dbutils.notebook.exit(json.dumps({
    "run_id": run_id,
    "variant": VARIANT,
    "toggles": {"A": ENABLE_A, "B": ENABLE_B, "C": ENABLE_C, "D": ENABLE_D, "E": ENABLE_E},
    "best": best_by_type,
    "lead": lead_map,
}))
