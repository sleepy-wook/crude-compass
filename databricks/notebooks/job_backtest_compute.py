# Databricks notebook source
# MAGIC %md
# MAGIC # Sprint 3 Day 3 — Mock Backtest 산출 ⭐ (v2: Dubai + 3년 4개월)
# MAGIC
# MAGIC ## 시나리오 v2 매핑
# MAGIC - § 부록 C Mock Backtest (HEDGE / OPP precision + lead day)
# MAGIC - § 14 Phase 7 (Time Travel 백테스트 슬라이더 source)
# MAGIC - § 17 Storytelling 핵심 narrative
# MAGIC
# MAGIC ## v2 변경점
# MAGIC - **Brent → Dubai** (한국 정유사 baseline, 중동 원유 70%+ 수입)
# MAGIC - **5개월 → 3년 4개월** (2023-01 ~ 2026-04)
# MAGIC   - 다양한 regime: 2023 OPEC+ cut + Israel-Hamas, 2024 홍해 후티,
# MAGIC     2025 중동 긴장 + 미 셰일, 2026 Q1-Q2 호르무즈 위기
# MAGIC - **Entry-event → daily-state with 7-day cool-down** (sample size 확보)
# MAGIC - **EIA hard-code → bronze.oil_prices_daily** (OPINET KNOC 실측)
# MAGIC
# MAGIC ## 데이터 의존성
# MAGIC - bronze.news_articles (gdelt_backtest 3년치, START_DT=20230101)
# MAGIC - bronze.oil_prices_daily (OPINET KNOC ticker='DUBAI', 2023-01 ~)
# MAGIC - UC Function `weighted_signal()`
# MAGIC
# MAGIC ## 산출 단계
# MAGIC 1. 3년 4개월 daily Pattern Score (각 date의 90일 window 시그널 aggregate)
# MAGIC 2. zone 분류 (HEDGE 70+ / OPP 30- / NONE)
# MAGIC 3. signal day 식별 — Option D: zone day with 7-day cool-down
# MAGIC 4. 30-day outcome (Dubai ±10%)
# MAGIC 5. precision + lead time 산출 → gold.backtest_results

# COMMAND ----------

import json
from datetime import datetime, timezone, date, timedelta

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Dubai daily price view (bronze.oil_prices_daily)

# COMMAND ----------

# bronze.oil_prices_daily에서 DUBAI ticker만 뽑아 view 생성
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
print(f"  ✅ Dubai daily: {n_dubai} trade days")

if n_dubai < 100:
    raise RuntimeError(
        f"Dubai daily insufficient ({n_dubai}). "
        "OPINET historical ingest 먼저 실행: job_oil_prices_daily MODE=historical"
    )

display(spark.sql("""
    SELECT MIN(price_date) AS min_d, MAX(price_date) AS max_d,
           ROUND(MIN(dubai_close_usd), 2) AS min_p,
           ROUND(MAX(dubai_close_usd), 2) AS max_p
    FROM _dubai_daily
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: 3년 4개월 daily Pattern Score
# MAGIC
# MAGIC 각 date의 90일 lookback window. 90일 buffer 위해 시그널 evaluation은 2023-04-01부터.

# COMMAND ----------

backtest_pattern_sql = """
WITH date_dim AS (
    SELECT explode(sequence(
        DATE'2023-04-01',  -- 90일 buffer (2023-01-01 + 90일)
        DATE'2026-04-30',
        INTERVAL 1 DAY
    )) AS as_of_date
),
contribs AS (
    SELECT
        d.as_of_date,
        a.direction,
        a.category,
        crude_compass.functions.weighted_signal(
            CAST(a.importance AS DOUBLE),
            CAST(DATEDIFF(d.as_of_date, DATE(a.published_at)) AS INT),
            CASE
                WHEN a.source LIKE 'GDELT_opec%' OR a.source LIKE 'OPEC%'   THEN 'opec_momr'
                WHEN a.source LIKE 'GDELT_eia%'  OR a.source LIKE 'EIA%'    THEN 'eia_inventory'
                ELSE 'news_tone'
            END,
            CAST(CASE a.tier WHEN 'A' THEN 1.0 WHEN 'B' THEN 0.8 ELSE 0.7 END AS DOUBLE)
        ) AS w
    FROM date_dim d
    JOIN crude_compass.bronze.news_articles a
        ON a.source_type = 'gdelt_backtest'
        AND DATE(a.published_at) BETWEEN d.as_of_date - INTERVAL 90 DAYS AND d.as_of_date
        AND a.importance >= 50
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
        SUM(CASE WHEN n >= 2 THEN 5 ELSE 0 END) AS cross_val_bonus
    FROM (
        SELECT as_of_date, category, direction, COUNT(*) AS n
        FROM contribs
        WHERE direction IN ('bullish', 'bearish')
        GROUP BY as_of_date, category, direction
    )
    GROUP BY as_of_date
),
final AS (
    SELECT
        a.as_of_date,
        a.bullish,
        a.bearish,
        COALESCE(c.cross_val_bonus, 0) AS cross_val_bonus,
        GREATEST(a.bullish, a.bearish, 1.0) AS max_norm
    FROM agg a
    LEFT JOIN cross_val c ON a.as_of_date = c.as_of_date
)
SELECT
    as_of_date,
    GREATEST(0, LEAST(100,
        50 + (bullish - bearish) / max_norm * 50 + cross_val_bonus
    )) AS pattern_score,
    bullish,
    bearish,
    cross_val_bonus,
    CASE
        WHEN GREATEST(0, LEAST(100, 50 + (bullish - bearish) / max_norm * 50 + cross_val_bonus)) >= 70 THEN 'HEDGE'
        WHEN GREATEST(0, LEAST(100, 50 + (bullish - bearish) / max_norm * 50 + cross_val_bonus)) <= 30 THEN 'OPPORTUNITY'
        ELSE 'NONE'
    END AS zone
FROM final
ORDER BY as_of_date
"""

df_daily = spark.sql(backtest_pattern_sql)
n_days = df_daily.count()
print(f"  ✅ daily Pattern Score: {n_days} days")
df_daily.createOrReplaceTempView("_daily_pattern")

display(spark.sql("""
    SELECT zone, COUNT(*) AS days, ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS pct
    FROM _daily_pattern GROUP BY zone ORDER BY zone
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Signal day 식별 (Option D: daily-state + 7-day cool-down)
# MAGIC
# MAGIC - 매일 zone in (HEDGE, OPPORTUNITY) → 잠재 signal
# MAGIC - **7-day cool-down**: 같은 zone이 직전 7일 안에 이미 signal로 식별됐으면 skip
# MAGIC - production "weekly review" 운영 모델과 일치

# COMMAND ----------

signal_sql = """
WITH dp AS (
    SELECT
        d.as_of_date,
        d.zone,
        b.dubai_close_usd
    FROM _daily_pattern d
    LEFT JOIN _dubai_daily b ON d.as_of_date = b.price_date
    WHERE d.zone IN ('HEDGE', 'OPPORTUNITY')
      AND b.dubai_close_usd IS NOT NULL  -- 거래일만 (주말 제외)
),
ranked AS (
    SELECT
        as_of_date,
        zone,
        dubai_close_usd,
        LAG(as_of_date, 1) OVER (PARTITION BY zone ORDER BY as_of_date) AS prev_signal_date
    FROM dp
),
filtered AS (
    -- 7-day cool-down: prev signal이 없거나 7일 이상 전이면 새 signal로 인정
    SELECT *
    FROM ranked
    WHERE prev_signal_date IS NULL
       OR DATEDIFF(as_of_date, prev_signal_date) >= 7
)
SELECT * FROM filtered ORDER BY as_of_date
"""
df_signals = spark.sql(signal_sql)
n_signals = df_signals.count()
print(f"  ✅ signal days (Option D + 7d cool-down): {n_signals}")
df_signals.createOrReplaceTempView("_signals")

display(spark.sql("""
    SELECT zone, COUNT(*) AS n
    FROM _signals
    GROUP BY zone
    ORDER BY zone
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: 30-day outcome (Dubai ±10%)

# COMMAND ----------

outcome_sql = """
WITH with_outcome AS (
    SELECT
        s.as_of_date AS signal_date,
        s.zone AS signal_type,
        s.dubai_close_usd AS dubai_at_signal,
        -- 30일 후 가장 가까운 거래일 (correlated subquery)
        (
            SELECT b.dubai_close_usd
            FROM _dubai_daily b
            WHERE b.price_date >= s.as_of_date + INTERVAL 30 DAYS
            ORDER BY b.price_date
            LIMIT 1
        ) AS dubai_30d
    FROM _signals s
)
SELECT
    signal_date,
    signal_type,
    dubai_at_signal,
    dubai_30d,
    ROUND((dubai_30d - dubai_at_signal) / dubai_at_signal * 100, 2) AS pct_change_30d,
    CASE
        WHEN signal_type = 'HEDGE'       AND (dubai_30d - dubai_at_signal) / dubai_at_signal >= 0.10  THEN 1
        WHEN signal_type = 'OPPORTUNITY' AND (dubai_30d - dubai_at_signal) / dubai_at_signal <= -0.10 THEN 1
        ELSE 0
    END AS hit
FROM with_outcome
WHERE dubai_30d IS NOT NULL
ORDER BY signal_date
"""

df_eval = spark.sql(outcome_sql)
n_eval = df_eval.count()
print(f"  ✅ Signals + outcomes (30d window 측정 가능): {n_eval}")
df_eval.createOrReplaceTempView("_eval")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: precision + lead time 산출

# COMMAND ----------

result = spark.sql("""
    SELECT
        signal_type,
        COUNT(*) AS signal_count,
        SUM(hit) AS correct_count,
        ROUND(SUM(hit) * 100.0 / COUNT(*), 1) AS precision_pct,
        ROUND(AVG(CASE WHEN hit = 1 THEN ABS(pct_change_30d) ELSE NULL END), 2) AS avg_outcome_pct
    FROM _eval
    GROUP BY signal_type
    ORDER BY signal_type
""").collect()

print("\n=== Backtest 결과 (Dubai, 2023-04 ~ 2026-04, 3년) ===")
print(f"{'type':<15} {'n':<6} {'correct':<8} {'precision':<10} {'avg outcome'}")
for r in result:
    print(f"{r.signal_type:<15} {r.signal_count:<6} {r.correct_count:<8} {r.precision_pct}%       {r.avg_outcome_pct}%")

# Lead time = signal date에서 ±10% 도달까지 days
lead_sql = """
WITH eval AS (""" + outcome_sql + """),
hits AS (
    SELECT * FROM eval WHERE hit = 1
),
lead_calc AS (
    SELECT
        h.signal_date,
        h.signal_type,
        h.dubai_at_signal,
        -- 처음 ±10% 돌파한 날까지 days
        (
            SELECT MIN(DATEDIFF(b.price_date, h.signal_date))
            FROM _dubai_daily b
            WHERE b.price_date > h.signal_date
              AND b.price_date <= h.signal_date + INTERVAL 30 DAYS
              AND CASE
                  WHEN h.signal_type = 'HEDGE'       THEN (b.dubai_close_usd - h.dubai_at_signal) / h.dubai_at_signal >= 0.10
                  WHEN h.signal_type = 'OPPORTUNITY' THEN (b.dubai_close_usd - h.dubai_at_signal) / h.dubai_at_signal <= -0.10
                  ELSE FALSE
              END
        ) AS lead_days
    FROM hits h
)
SELECT signal_type, ROUND(AVG(lead_days), 1) AS avg_lead_days
FROM lead_calc
WHERE lead_days IS NOT NULL
GROUP BY signal_type
"""
lead_rows = spark.sql(lead_sql).collect()
lead_map = {r.signal_type: float(r.avg_lead_days) for r in lead_rows}
print("\n=== Lead time (signal → ±10% 돌파, hit case 평균) ===")
for k, v in lead_map.items():
    print(f"  {k:<15} {v} days")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: gold.backtest_results 적재

# COMMAND ----------

now = datetime.now(timezone.utc)
run_id = f"backtest_dubai_3y_{now.strftime('%Y%m%dT%H%M%S')}"

# 결과 row 직접 조립 (LATERAL JOIN 호환성 위해 collect → INSERT)
insert_rows = []
for r in result:
    lead = lead_map.get(r.signal_type, None)
    insert_rows.append((
        run_id,
        "2023-04 ~ 2026-04 (3y, Dubai/OPINET)",
        r.signal_type,
        int(r.signal_count),
        int(r.correct_count or 0),
        float(r.precision_pct or 0),
        float(lead) if lead is not None else None,
        70.0,
    ))

from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DecimalType, TimestampType
from decimal import Decimal

# DECIMAL 변환
typed_rows = [
    (rid, w, t, sc, cc, Decimal(str(round(p, 2))), Decimal(str(round(l, 1))) if l is not None else None, Decimal(str(round(th, 2))))
    for (rid, w, t, sc, cc, p, l, th) in insert_rows
]
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
spark.sql(f"""
    INSERT INTO crude_compass.gold.backtest_results
    SELECT
        run_id, backtest_window, mission_type, signal_count, correct_count,
        accuracy_pct, avg_lead_time_days, threshold_used, current_timestamp() AS computed_at
    FROM _results_in
""")

print(f"\n✅ gold.backtest_results 적재 (run_id={run_id})")
display(spark.sql(f"""
    SELECT * FROM crude_compass.gold.backtest_results WHERE run_id = '{run_id}'
"""))

# COMMAND ----------
dbutils.notebook.exit(json.dumps({
    "run_id": run_id,
    "results": [{"type": r.signal_type, "n": r.signal_count, "correct": r.correct_count, "precision": float(r.precision_pct), "lead_days": lead_map.get(r.signal_type)} for r in result],
}))
