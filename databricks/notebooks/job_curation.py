# Databricks notebook source
# MAGIC %md
# MAGIC # Job 5 — daily_curation 06:30 ⭐ Bidirectional Pattern Detection
# MAGIC
# MAGIC ## 시나리오 v2 매핑
# MAGIC - § 6 Bidirectional Pattern Detection (양방향 핵심)
# MAGIC - § 6.2 시간 감쇠 람다 차등 (UC Function `weighted_signal`)
# MAGIC - § 6.3 시그널별 기여도 보존 (`weighted_contribution` 컬럼)
# MAGIC - § 9.7 Mission Plan Agent trigger (Pattern Score 70+/30- 시)
# MAGIC - § 12 #8 cron `30 6 * * *` KST
# MAGIC
# MAGIC ## 입력
# MAGIC - bronze.news_articles (importance ≥ 50, 90일 window)
# MAGIC - bronze.opec_momr_parsed (월간 정기 시그널)
# MAGIC - bronze.eia_inventory (주간)
# MAGIC - bronze.oil_prices (5min spike — Sprint 3 day 3 추가 예정)
# MAGIC
# MAGIC ## 출력
# MAGIC - silver.signal_events_decayed: per-signal × time decay × credibility × direction sign
# MAGIC - silver.pattern_scores_daily: Pattern Score (양방향 aggregate)
# MAGIC - gold.daily_risk_score: latest snapshot (Lakebase cache 대상)
# MAGIC - (Sprint 4) 70+/30- 시 Mission Plan Agent 호출 → Lakebase missions INSERT

# COMMAND ----------

import json
from datetime import datetime, timezone

# COMMAND ----------

run_id = f"curation_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"
print(f"run_id: {run_id}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: signal_events_decayed 적재
# MAGIC
# MAGIC bronze.news_articles → signal_type 매핑 + weighted_signal() UC Function 적용.
# MAGIC weighted_contribution은 direction 부호 반영 (bullish +, bearish -, neutral 0).

# COMMAND ----------

# 90일 window. backtest seed로 5개월 데이터 있으니 오늘 = 2026-04-30 (backtest 마지막 날) 시뮬.
# 실제 production은 CURRENT_DATE() 사용.
# 데모용으로는 backtest 데이터 있는 마지막 날짜로 산출.

step1_sql = f"""
INSERT INTO crude_compass.silver.signal_events_decayed
WITH
  -- 1. GDELT news (감지층, λ=0.046)
  news_signals AS (
    SELECT
      DATE(published_at) AS event_date,
      'news_tone' AS signal_type,
      article_id AS signal_id,
      CAST(importance AS DOUBLE) AS raw_intensity,
      direction,
      CASE tier WHEN 'A' THEN 1.0 WHEN 'B' THEN 0.8 ELSE 0.7 END AS source_credibility
    FROM crude_compass.bronze.news_articles
    WHERE importance >= 50
      AND DATE(published_at) >= CURRENT_DATE() - INTERVAL 90 DAYS
  ),
  -- 2. EIA weekly inventory (fundamentals, λ=0.012)
  eia_signals AS (
    SELECT
      week_ending AS event_date,
      'eia_inventory' AS signal_type,
      CONCAT('eia_', series_id, '_', CAST(week_ending AS STRING)) AS signal_id,
      LEAST(100.0, 60.0 + ABS(CAST(delta_vs_prev_wk AS DOUBLE)) / 500.0) AS raw_intensity,
      CASE WHEN delta_vs_prev_wk > 0 THEN 'bearish'
           WHEN delta_vs_prev_wk < 0 THEN 'bullish' ELSE 'neutral' END AS direction,
      1.0 AS source_credibility
    FROM crude_compass.bronze.eia_inventory
    WHERE inventory_type = 'commercial'
      AND ABS(delta_vs_prev_wk) > 2000
      AND week_ending >= CURRENT_DATE() - INTERVAL 90 DAYS
  ),
  -- 3. OPEC MOMR monthly (fundamentals, λ=0.012)
  opec_signals AS (
    SELECT
      TO_DATE(CONCAT(report_month, '-01'), 'yyyy-MM-dd') AS event_date,
      'opec_momr' AS signal_type,
      CONCAT('opec_', report_month) AS signal_id,
      70.0 AS raw_intensity,
      'bullish' AS direction,
      1.0 AS source_credibility
    FROM crude_compass.bronze.opec_momr_parsed
    WHERE forecast_demand_kbbl_d IS NOT NULL
      AND saudi_production_kbbl_d IS NOT NULL
      AND forecast_demand_kbbl_d > saudi_production_kbbl_d * 11.5
      AND TO_DATE(CONCAT(report_month, '-01'), 'yyyy-MM-dd') >= CURRENT_DATE() - INTERVAL 90 DAYS
  ),
  -- 4. FX KRW/USD daily delta (macro, λ=0.023)
  fx_signals AS (
    SELECT
      date AS event_date,
      'fx_krw_usd' AS signal_type,
      CONCAT('fx_', CAST(date AS STRING)) AS signal_id,
      55.0 AS raw_intensity,
      CASE WHEN rate - LAG(rate) OVER (ORDER BY date) > rate * 0.005 THEN 'bullish'
           WHEN rate - LAG(rate) OVER (ORDER BY date) < -rate * 0.005 THEN 'bearish'
           ELSE 'neutral' END AS direction,
      0.8 AS source_credibility
    FROM crude_compass.bronze.fx_rates
    WHERE pair = 'USD/KRW'
      AND date >= CURRENT_DATE() - INTERVAL 90 DAYS
  ),
  -- 5. AIS K-Petroleum 5척 daily aggregate (leading, λ=0.023, D-7)
  ais_daily AS (
    SELECT
      DATE(fetched_at) AS event_date,
      COUNT(DISTINCT CASE WHEN in_hormuz_bbox THEN mmsi END) AS hormuz_count,
      COUNT(DISTINCT CASE WHEN status = 'stranded' THEN mmsi END) AS stranded_count,
      AVG(CAST(speed_knots AS DOUBLE)) AS avg_speed,
      COUNT(*) AS row_count
    FROM crude_compass.bronze.ais_positions
    WHERE DATE(fetched_at) >= CURRENT_DATE() - INTERVAL 90 DAYS
    GROUP BY DATE(fetched_at)
    HAVING COUNT(*) >= 5
  ),
  ais_signals AS (
    SELECT
      event_date,
      'ais_traffic' AS signal_type,
      CONCAT('ais_', CAST(event_date AS STRING)) AS signal_id,
      -- 정체(stranded) + 호르무즈 통과량 감소 = bullish 강도
      LEAST(100.0, 50.0 + stranded_count * 15.0
            + GREATEST(0, 3 - hormuz_count) * 10.0) AS raw_intensity,
      CASE WHEN stranded_count >= 2 OR hormuz_count <= 2 THEN 'bullish'
           WHEN hormuz_count >= 4 AND stranded_count = 0 THEN 'bearish'
           ELSE 'neutral' END AS direction,
      0.7 AS source_credibility
    FROM ais_daily
  ),
  -- 6. oil_prices 5min spike count daily aggregate (reactive, λ=0.046)
  spike_daily AS (
    SELECT
      DATE(fetched_at) AS event_date,
      SUM(CASE WHEN delta_pct_5min >= 2.0 THEN 1 ELSE 0 END) AS up_spikes,
      SUM(CASE WHEN delta_pct_5min <= -2.0 THEN 1 ELSE 0 END) AS down_spikes,
      MAX(CAST(ABS(delta_pct_5min) AS DOUBLE)) AS max_abs_delta
    FROM crude_compass.bronze.oil_prices
    WHERE ticker IN ('BRENT_CRUDE_USD', 'DUBAI_CRUDE_USD')
      AND delta_pct_5min IS NOT NULL
      AND DATE(fetched_at) >= CURRENT_DATE() - INTERVAL 90 DAYS
    GROUP BY DATE(fetched_at)
    HAVING SUM(CASE WHEN ABS(delta_pct_5min) >= 2.0 THEN 1 ELSE 0 END) > 0
  ),
  spike_signals AS (
    SELECT
      event_date,
      'price_spike' AS signal_type,
      CONCAT('spike_', CAST(event_date AS STRING)) AS signal_id,
      LEAST(100.0, 60.0 + (up_spikes + down_spikes) * 5.0 + max_abs_delta * 3.0) AS raw_intensity,
      CASE WHEN up_spikes > down_spikes THEN 'bullish'
           WHEN down_spikes > up_spikes THEN 'bearish'
           ELSE 'neutral' END AS direction,
      1.0 AS source_credibility
    FROM spike_daily
  ),
  unioned AS (
    SELECT * FROM news_signals WHERE direction IN ('bullish','bearish','neutral')
    UNION ALL SELECT * FROM eia_signals WHERE direction != 'neutral'
    UNION ALL SELECT * FROM opec_signals
    UNION ALL SELECT * FROM fx_signals WHERE direction != 'neutral'
    UNION ALL SELECT * FROM ais_signals WHERE direction != 'neutral'
    UNION ALL SELECT * FROM spike_signals WHERE direction != 'neutral'
  )
SELECT
  event_date,
  signal_type,
  signal_id,
  CAST(raw_intensity AS DECIMAL(6, 2)) AS raw_intensity,
  direction,
  CAST(source_credibility AS DECIMAL(3, 2)) AS source_credibility,
  CAST(DATEDIFF(CURRENT_DATE(), event_date) AS INT) AS days_ago,
  CAST(CASE signal_type
        WHEN 'eia_inventory' THEN 0.012
        WHEN 'opec_momr'     THEN 0.012
        WHEN 'fx_krw_usd'    THEN 0.023
        WHEN 'ais_traffic'   THEN 0.023
        WHEN 'price_spike'   THEN 0.046
        ELSE 0.046
       END AS DECIMAL(6, 4)) AS lambda_used,
  CAST(EXP(-CASE signal_type
        WHEN 'eia_inventory' THEN 0.012
        WHEN 'opec_momr'     THEN 0.012
        WHEN 'fx_krw_usd'    THEN 0.023
        WHEN 'ais_traffic'   THEN 0.023
        WHEN 'price_spike'   THEN 0.046
        ELSE 0.046
       END * DATEDIFF(CURRENT_DATE(), event_date)) AS DECIMAL(6, 4)) AS applied_weight,
  CAST(
    crude_compass.functions.weighted_signal(
      CAST(raw_intensity AS DOUBLE),
      CAST(DATEDIFF(CURRENT_DATE(), event_date) AS INT),
      signal_type,
      CAST(source_credibility AS DOUBLE)
    ) * CASE direction WHEN 'bullish' THEN 1 WHEN 'bearish' THEN -1 ELSE 0 END
  AS DECIMAL(8, 2)) AS weighted_contribution,
  current_timestamp() AS computed_at,
  '{run_id}' AS job_run_id
FROM unioned
"""

# Idempotent: run_id별 중복 적재. 기존 run_id 있으면 스킵하고 다시 적재.
spark.sql(f"DELETE FROM crude_compass.silver.signal_events_decayed WHERE job_run_id = '{run_id}'")
spark.sql(step1_sql)
print(f"  ✅ signal_events_decayed 적재 완료")

step1_check = spark.sql(f"""
    SELECT
        signal_type,
        direction,
        COUNT(*) AS n,
        ROUND(AVG(weighted_contribution), 2) AS avg_w_contrib
    FROM crude_compass.silver.signal_events_decayed
    WHERE job_run_id = '{run_id}'
    GROUP BY signal_type, direction
    ORDER BY signal_type, direction
""")
display(step1_check)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: pattern_scores_daily 산출 (Bidirectional)

# COMMAND ----------

# 시나리오 § 6.2 공식:
# bullish_score = SUM(weighted_contribution > 0)
# bearish_score = SUM(|weighted_contribution|) WHERE direction='bearish'
# cross_val_bonus = COUNT(category × direction with 2+ source) × 5
# pattern_score = clamp(0, 100, 50 + (bullish - bearish) / max_norm * 50 + cross_val_bonus)

step2_sql = f"""
WITH signals AS (
    SELECT
        s.weighted_contribution,
        s.direction,
        s.signal_type,
        -- non-news signal_type은 news_articles에 join 안 됨 → fallback 매핑
        COALESCE(a.category,
          CASE s.signal_type
            WHEN 'eia_inventory' THEN 'supply'
            WHEN 'opec_momr'     THEN 'demand'
            WHEN 'fx_krw_usd'    THEN 'macro'
            WHEN 'ais_traffic'   THEN 'geopolitical'
            WHEN 'price_spike'   THEN 'market'
            ELSE 'unknown'
          END
        ) AS category
    FROM crude_compass.silver.signal_events_decayed s
    LEFT JOIN crude_compass.bronze.news_articles a
      ON s.signal_id = a.article_id AND s.signal_type = 'news_tone'
    WHERE s.job_run_id = '{run_id}'
),
agg AS (
    SELECT
        SUM(CASE WHEN direction = 'bullish' THEN weighted_contribution ELSE 0 END) AS bullish_score,
        SUM(CASE WHEN direction = 'bearish' THEN -weighted_contribution ELSE 0 END) AS bearish_score,
        COUNT(*) AS signal_count_90d,
        collect_set(category) AS top_categories
    FROM signals
),
cross_val AS (
    -- backtest와 동일 *15 (signal_type 다양성 보상). signal_type DISTINCT로 진짜 다양성 측정.
    SELECT
        SUM(CASE WHEN n >= 2 THEN 15 ELSE 0 END) AS cross_val_bonus
    FROM (
        SELECT category, direction, COUNT(DISTINCT signal_type) AS n
        FROM signals
        WHERE direction IN ('bullish', 'bearish')
        GROUP BY category, direction
    )
),
final AS (
    SELECT
        CURRENT_DATE() AS date,
        agg.bullish_score,
        agg.bearish_score,
        cv.cross_val_bonus,
        -- max normalization: 가장 큰 score를 100점으로
        GREATEST(agg.bullish_score, agg.bearish_score, 1.0) AS max_norm,
        agg.signal_count_90d,
        agg.top_categories
    FROM agg, cross_val cv
)
INSERT INTO crude_compass.silver.pattern_scores_daily
SELECT
    date,
    -- pattern_score: 50 + signed delta scaled, clamp [0, 100]
    CAST(GREATEST(0, LEAST(100,
        50 + (bullish_score - bearish_score) / max_norm * 50 + cross_val_bonus
    )) AS DECIMAL(5, 2)) AS pattern_score,
    CAST(bullish_score AS DECIMAL(8, 2)) AS bullish_score,
    CAST(bearish_score AS DECIMAL(8, 2)) AS bearish_score,
    CAST(cross_val_bonus AS DECIMAL(5, 2)) AS cross_val_bonus,
    CASE
        WHEN GREATEST(0, LEAST(100, 50 + (bullish_score - bearish_score) / max_norm * 50 + cross_val_bonus)) >= 70 THEN 'HEDGE'
        WHEN GREATEST(0, LEAST(100, 50 + (bullish_score - bearish_score) / max_norm * 50 + cross_val_bonus)) <= 30 THEN 'OPPORTUNITY'
        ELSE 'NONE'
    END AS mission_type,
    signal_count_90d,
    top_categories,
    current_timestamp() AS computed_at,
    '{run_id}' AS job_run_id
FROM final
"""

# Idempotent
spark.sql("DELETE FROM crude_compass.silver.pattern_scores_daily WHERE date = CURRENT_DATE()")
spark.sql(step2_sql)
print(f"  ✅ pattern_scores_daily 적재 완료")

display(spark.sql("""
    SELECT *
    FROM crude_compass.silver.pattern_scores_daily
    WHERE date = CURRENT_DATE()
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: gold.daily_risk_score (Lakebase cache 대상)

# COMMAND ----------

step3_sql = f"""
WITH today AS (
    SELECT * FROM crude_compass.silver.pattern_scores_daily WHERE date = CURRENT_DATE()
),
contributors AS (
    SELECT
        signal_type,
        SUM(ABS(weighted_contribution)) AS total_abs_contrib
    FROM crude_compass.silver.signal_events_decayed
    WHERE job_run_id = '{run_id}'
    GROUP BY signal_type
),
total_contrib AS (
    SELECT SUM(total_abs_contrib) AS total FROM contributors
),
top_contributors_json AS (
    SELECT
        to_json(collect_list(struct(
            signal_type,
            total_abs_contrib,
            ROUND(total_abs_contrib / (SELECT total FROM total_contrib) * 100, 1) AS pct
        ))) AS top_contributors
    FROM contributors
)
INSERT INTO crude_compass.gold.daily_risk_score
SELECT
    today.date,
    today.pattern_score,
    today.bullish_score,
    today.bearish_score,
    today.cross_val_bonus,
    -- confidence_score: source 다양성 + cross_val 기반
    CAST(LEAST(100,
        50 + size(today.top_categories) * 5 + today.cross_val_bonus
    ) AS DECIMAL(5, 2)) AS confidence_score,
    today.mission_type,
    tcj.top_contributors,
    today.signal_count_90d,
    current_timestamp() AS computed_at,
    'lambda_v1_signal_specific' AS lambda_table_id,
    '{run_id}' AS job_run_id
FROM today, top_contributors_json tcj
"""

spark.sql("DELETE FROM crude_compass.gold.daily_risk_score WHERE date = CURRENT_DATE()")
spark.sql(step3_sql)
print(f"  ✅ daily_risk_score 적재 완료")

display(spark.sql("""
    SELECT date, pattern_score, mission_type, confidence_score, bullish_score, bearish_score, cross_val_bonus, top_contributors
    FROM crude_compass.gold.daily_risk_score
    WHERE date = CURRENT_DATE()
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Mission trigger 결정 (Sprint 4에서 실제 호출)

# COMMAND ----------

today_score = spark.sql(f"""
    SELECT pattern_score, mission_type, confidence_score
    FROM crude_compass.gold.daily_risk_score
    WHERE date = CURRENT_DATE() AND job_run_id = '{run_id}'
""").collect()

if today_score:
    s = today_score[0]
    print(f"\n📊 Pattern Score: {s.pattern_score} ({s.mission_type})")
    print(f"   Confidence: {s.confidence_score}")
    if s.mission_type == 'HEDGE':
        print(f"   🚨 → Mission Plan Agent 호출 (HEDGE 제안) — Sprint 4 implement")
    elif s.mission_type == 'OPPORTUNITY':
        print(f"   🟢 → Mission Plan Agent 호출 (OPPORTUNITY 제안) — Sprint 4 implement")
    else:
        print(f"   ✓ STABLE zone (30-70) — Mission trigger 안 함")

# COMMAND ----------

dbutils.notebook.exit(json.dumps({
    "run_id": run_id,
    "status": "success",
}))
