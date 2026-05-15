# Databricks notebook source
# MAGIC %md
# MAGIC # daily_risk_score backfill — 7년치 일괄 적재
# MAGIC
# MAGIC 시나리오 §14 Phase 7 "평시 가치 6년 그래프" anchor 데이터 부재 fix.
# MAGIC bronze.news_articles (gdelt_backtest source_type, 7년치 누적)을 입력으로
# MAGIC silver.signal_events_decayed → silver.pattern_scores_daily → gold.daily_risk_score
# MAGIC 7년치 daily row 일괄 적재.
# MAGIC
# MAGIC 사용: 워크스페이스에서 'Run now' 1회. ~15-25min Spark.
# MAGIC Idempotent — job_run_id 기준 DELETE+INSERT.

# COMMAND ----------

import json
from datetime import datetime, timezone

run_id = f"backfill_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"
print(f"backfill run_id: {run_id}")

# Widget — start/end date
dbutils.widgets.text("start_date", "2019-04-01", "Backfill start date (YYYY-MM-DD)")
dbutils.widgets.text("end_date", "2026-05-15", "Backfill end date (YYYY-MM-DD)")
START = dbutils.widgets.get("start_date")
END = dbutils.widgets.get("end_date")
print(f"range: {START} ~ {END}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: silver.signal_events_decayed 7년치 적재
# MAGIC
# MAGIC bronze 5 source (news/eia/opec/fx/oil_prices) × 시간 감쇠 람다 × direction × credibility.
# MAGIC date_dim sequence + cross-join으로 모든 (date, signal) pair 계산.

# COMMAND ----------

step1_sql = f"""
INSERT INTO crude_compass.silver.signal_events_decayed
WITH
  date_dim AS (
    SELECT explode(sequence(DATE'{START}', DATE'{END}', INTERVAL 1 DAY)) AS as_of_date
  ),
  news_signals AS (
    SELECT
      DATE(published_at) AS event_date,
      'news_tone' AS signal_type,
      article_id AS signal_id,
      CAST(importance AS DOUBLE) AS raw_intensity,
      direction,
      CASE tier WHEN 'A' THEN 1.0 WHEN 'B' THEN 0.8 ELSE 0.7 END AS source_credibility
    FROM crude_compass.bronze.news_articles
    WHERE source_type IN ('gdelt_backtest', 'gdelt_detect')
      AND importance >= 50
      AND direction IN ('bullish', 'bearish')
  ),
  eia_signals AS (
    SELECT
      week_ending AS event_date,
      'eia_inventory' AS signal_type,
      CAST(series_id AS STRING) AS signal_id,
      LEAST(100.0, 60.0 + ABS(CAST(delta_vs_prev_wk AS DOUBLE)) / 500.0) AS raw_intensity,
      CASE
        WHEN delta_vs_prev_wk > 5000 THEN 'bearish'
        WHEN delta_vs_prev_wk < -5000 THEN 'bullish'
        ELSE 'neutral'
      END AS direction,
      1.0 AS source_credibility
    FROM crude_compass.bronze.eia_inventory
    WHERE inventory_type = 'commercial'
      AND delta_vs_prev_wk IS NOT NULL
      AND ABS(delta_vs_prev_wk) > 2000
  ),
  opec_signals AS (
    SELECT
      TO_DATE(CONCAT(report_month, '-01'), 'yyyy-MM-dd') AS event_date,
      'opec_momr' AS signal_type,
      report_month AS signal_id,
      70.0 AS raw_intensity,
      'bullish' AS direction,
      1.0 AS source_credibility
    FROM crude_compass.bronze.opec_momr_parsed
    WHERE forecast_demand_kbbl_d IS NOT NULL
      AND saudi_production_kbbl_d IS NOT NULL
      AND forecast_demand_kbbl_d > saudi_production_kbbl_d * 11.5
  ),
  fx_signals AS (
    SELECT
      f.date AS event_date,
      'fx_krw_usd' AS signal_type,
      CAST(f.date AS STRING) AS signal_id,
      55.0 AS raw_intensity,
      CASE
        WHEN f.rate - LAG(f.rate) OVER (ORDER BY f.date) > f.rate * 0.005 THEN 'bullish'
        WHEN f.rate - LAG(f.rate) OVER (ORDER BY f.date) < -f.rate * 0.005 THEN 'bearish'
        ELSE 'neutral'
      END AS direction,
      0.8 AS source_credibility
    FROM crude_compass.bronze.fx_rates f
    WHERE f.pair = 'USD/KRW'
  ),
  all_signals AS (
    SELECT * FROM news_signals
    UNION ALL SELECT * FROM eia_signals WHERE direction != 'neutral'
    UNION ALL SELECT * FROM opec_signals
    UNION ALL SELECT * FROM fx_signals WHERE direction != 'neutral'
  )
SELECT
  d.as_of_date AS event_date,
  s.signal_type,
  s.signal_id,
  CAST(s.raw_intensity AS DECIMAL(6, 2)) AS raw_intensity,
  s.direction,
  CAST(s.source_credibility AS DECIMAL(3, 2)) AS source_credibility,
  DATEDIFF(d.as_of_date, s.event_date) AS days_ago,
  CASE s.signal_type
    WHEN 'news_tone'     THEN 0.046
    WHEN 'ais_traffic'   THEN 0.023
    WHEN 'eia_inventory' THEN 0.012
    WHEN 'opec_momr'     THEN 0.012
    WHEN 'fx_krw_usd'    THEN 0.023
    WHEN 'price_spike'   THEN 0.046
    ELSE 0.023
  END AS lambda_used,
  CAST(EXP(
    -(CASE s.signal_type
        WHEN 'news_tone'     THEN 0.046
        WHEN 'ais_traffic'   THEN 0.023
        WHEN 'eia_inventory' THEN 0.012
        WHEN 'opec_momr'     THEN 0.012
        WHEN 'fx_krw_usd'    THEN 0.023
        WHEN 'price_spike'   THEN 0.046
        ELSE 0.023
      END) * DATEDIFF(d.as_of_date, s.event_date)
  ) AS DECIMAL(6, 4)) AS applied_weight,
  CAST(
    s.raw_intensity * crude_compass.functions.weighted_signal(
      s.raw_intensity,
      CAST(DATEDIFF(d.as_of_date, s.event_date) AS INT),
      s.signal_type,
      s.source_credibility
    ) / NULLIF(s.raw_intensity, 0)
    * CASE s.direction WHEN 'bullish' THEN 1 WHEN 'bearish' THEN -1 ELSE 0 END
    AS DECIMAL(8, 2)
  ) AS weighted_contribution,
  current_timestamp() AS computed_at,
  '{run_id}' AS job_run_id
FROM date_dim d
JOIN all_signals s
  ON s.event_date BETWEEN d.as_of_date - INTERVAL 90 DAYS AND d.as_of_date
"""

# Idempotency: backfill run_id 별 중복 적재 방지
spark.sql(f"DELETE FROM crude_compass.silver.signal_events_decayed WHERE job_run_id = '{run_id}'")
spark.sql(step1_sql)
print("  silver.signal_events_decayed 7년치 적재 완료")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: silver.pattern_scores_daily 7년치 적재
# MAGIC
# MAGIC 양방향 aggregate (bullish_score - bearish_score) z-norm → Pattern Score 0~100.

# COMMAND ----------

step2_sql = f"""
INSERT INTO crude_compass.silver.pattern_scores_daily
WITH
  daily_agg AS (
    SELECT
      event_date AS date,
      SUM(CASE WHEN direction = 'bullish' THEN weighted_contribution ELSE 0 END) AS bullish,
      SUM(CASE WHEN direction = 'bearish' THEN ABS(weighted_contribution) ELSE 0 END) AS bearish,
      COUNT(*) AS sig_count
    FROM crude_compass.silver.signal_events_decayed
    WHERE job_run_id = '{run_id}'
    GROUP BY event_date
  ),
  cv AS (
    SELECT
      event_date AS date,
      SUM(CASE WHEN n >= 2 THEN 15 ELSE 0 END) AS cross_val_bonus
    FROM (
      SELECT event_date, signal_type, direction, COUNT(*) AS n
      FROM crude_compass.silver.signal_events_decayed
      WHERE job_run_id = '{run_id}' AND direction IN ('bullish', 'bearish')
      GROUP BY event_date, signal_type, direction
    )
    GROUP BY event_date
  ),
  joined AS (
    SELECT
      a.date,
      a.bullish,
      a.bearish,
      a.sig_count,
      a.bullish - a.bearish AS net,
      COALESCE(c.cross_val_bonus, 0) AS cross_val_bonus
    FROM daily_agg a
    LEFT JOIN cv c ON a.date = c.date
  ),
  rolling AS (
    SELECT *,
      AVG(net) OVER (ORDER BY date ROWS BETWEEN 90 PRECEDING AND 1 PRECEDING) AS mean_net,
      COALESCE(STDDEV_SAMP(net) OVER (ORDER BY date ROWS BETWEEN 90 PRECEDING AND 1 PRECEDING), 1.0) AS std_net
    FROM joined
  )
SELECT
  date,
  CAST(GREATEST(0.0, LEAST(100.0,
    50.0 + 25.0 * (net - mean_net) / GREATEST(std_net, 1.0) + cross_val_bonus
  )) AS DECIMAL(5, 2)) AS pattern_score,
  CAST(bullish AS DECIMAL(8, 2)) AS bullish_score,
  CAST(bearish AS DECIMAL(8, 2)) AS bearish_score,
  CAST(cross_val_bonus AS DECIMAL(5, 2)) AS cross_val_bonus,
  CASE
    WHEN GREATEST(0.0, LEAST(100.0,
      50.0 + 25.0 * (net - mean_net) / GREATEST(std_net, 1.0) + cross_val_bonus
    )) >= 70 THEN 'HEDGE'
    WHEN GREATEST(0.0, LEAST(100.0,
      50.0 + 25.0 * (net - mean_net) / GREATEST(std_net, 1.0) + cross_val_bonus
    )) <= 30 THEN 'OPPORTUNITY'
    ELSE 'NONE'
  END AS mission_type,
  sig_count AS signal_count_90d,
  CAST(NULL AS ARRAY<STRING>) AS top_categories,
  current_timestamp() AS computed_at,
  '{run_id}' AS job_run_id
FROM rolling
WHERE mean_net IS NOT NULL
"""

spark.sql(f"DELETE FROM crude_compass.silver.pattern_scores_daily WHERE job_run_id = '{run_id}'")
spark.sql(step2_sql)
print("  silver.pattern_scores_daily 7년치 적재 완료")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: gold.daily_risk_score 7년치 적재
# MAGIC
# MAGIC silver.pattern_scores_daily 그대로 + confidence_score 추가.

# COMMAND ----------

step3_sql = f"""
INSERT INTO crude_compass.gold.daily_risk_score
SELECT
  date,
  pattern_score,
  bullish_score,
  bearish_score,
  cross_val_bonus,
  CAST(LEAST(100.0, GREATEST(0.0,
    50.0 + 0.3 * cross_val_bonus + 0.2 * LEAST(50.0, signal_count_90d / 2.0)
  )) AS DECIMAL(5, 2)) AS confidence_score,
  mission_type,
  CAST(NULL AS STRING) AS top_contributors,
  signal_count_90d,
  computed_at,
  CAST(NULL AS STRING) AS lambda_table_id,
  job_run_id
FROM crude_compass.silver.pattern_scores_daily
WHERE job_run_id = '{run_id}'
"""

# Idempotency: full backfill 시 기존 daily 데이터 모두 클리어 (해당 range)
spark.sql(f"""
  DELETE FROM crude_compass.gold.daily_risk_score
  WHERE date BETWEEN DATE'{START}' AND DATE'{END}'
""")
spark.sql(step3_sql)
print("  gold.daily_risk_score 7년치 적재 완료")

# COMMAND ----------

# Verification — row count + date range + zone distribution
verify = spark.sql("""
  SELECT
    MIN(date) AS min_date,
    MAX(date) AS max_date,
    COUNT(*) AS n_total,
    SUM(CASE WHEN pattern_score >= 70 THEN 1 ELSE 0 END) AS n_hedge_days,
    SUM(CASE WHEN pattern_score <= 30 THEN 1 ELSE 0 END) AS n_opp_days,
    ROUND(AVG(pattern_score), 1) AS avg_score
  FROM crude_compass.gold.daily_risk_score
""").collect()[0]
print(f"\n=== gold.daily_risk_score backfill result ===")
print(f"range: {verify.min_date} ~ {verify.max_date}")
print(f"total: {verify.n_total} rows")
print(f"HEDGE days (70+): {verify.n_hedge_days}")
print(f"OPP days (30-): {verify.n_opp_days}")
print(f"avg score: {verify.avg_score}")

# COMMAND ----------

dbutils.notebook.exit(json.dumps({
    "run_id": run_id,
    "status": "success",
    "range_start": START,
    "range_end": END,
    "rows_written": verify.n_total,
    "hedge_days": verify.n_hedge_days,
    "opp_days": verify.n_opp_days,
}))
