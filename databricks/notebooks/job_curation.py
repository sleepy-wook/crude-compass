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
SELECT
    DATE(published_at) AS event_date,
    -- signal_type 매핑 (시그널 source 기반)
    CASE
        WHEN source LIKE 'GDELT_opec%'    THEN 'opec_momr'
        WHEN source LIKE 'GDELT_eia%'     THEN 'eia_inventory'
        WHEN source LIKE 'GDELT_%'        THEN 'news_tone'
        WHEN source LIKE 'OPEC%'          THEN 'opec_momr'
        WHEN source LIKE 'EIA%'           THEN 'eia_inventory'
        WHEN source LIKE 'AIS%'           THEN 'ais_traffic'
        WHEN source LIKE 'OilPriceAPI%'   THEN 'price_spike'
        WHEN source LIKE 'ECOS%'          THEN 'fx_krw_usd'
        ELSE 'news_tone'
    END AS signal_type,
    article_id AS signal_id,
    CAST(importance AS DECIMAL(6, 2)) AS raw_intensity,
    direction,
    -- Source credibility (Tier A=1.0, B=0.8)
    CAST(CASE tier WHEN 'A' THEN 1.0 WHEN 'B' THEN 0.8 ELSE 0.7 END AS DECIMAL(3, 2)) AS source_credibility,
    -- days_ago (current run 시점 기준)
    CAST(DATEDIFF(CURRENT_DATE(), DATE(published_at)) AS INT) AS days_ago,
    -- 람다 (signal_type별)
    CAST(CASE
        WHEN source LIKE 'GDELT_opec%' OR source LIKE 'OPEC%'    THEN 0.012
        WHEN source LIKE 'GDELT_eia%'  OR source LIKE 'EIA%'     THEN 0.012
        WHEN source LIKE 'AIS%'                                  THEN 0.023
        WHEN source LIKE 'OilPriceAPI%'                          THEN 0.046
        WHEN source LIKE 'ECOS%'                                 THEN 0.023
        ELSE 0.046
    END AS DECIMAL(6, 4)) AS lambda_used,
    -- applied_weight = exp(-λ × days_ago)
    CAST(EXP(-CASE
        WHEN source LIKE 'GDELT_opec%' OR source LIKE 'OPEC%'    THEN 0.012
        WHEN source LIKE 'GDELT_eia%'  OR source LIKE 'EIA%'     THEN 0.012
        WHEN source LIKE 'AIS%'                                  THEN 0.023
        WHEN source LIKE 'OilPriceAPI%'                          THEN 0.046
        WHEN source LIKE 'ECOS%'                                 THEN 0.023
        ELSE 0.046
    END * DATEDIFF(CURRENT_DATE(), DATE(published_at))) AS DECIMAL(6, 4)) AS applied_weight,
    -- weighted_contribution: UC function × direction sign
    CAST(
        crude_compass.functions.weighted_signal(
            CAST(importance AS DOUBLE),
            CAST(DATEDIFF(CURRENT_DATE(), DATE(published_at)) AS INT),
            CASE
                WHEN source LIKE 'GDELT_opec%' OR source LIKE 'OPEC%'   THEN 'opec_momr'
                WHEN source LIKE 'GDELT_eia%'  OR source LIKE 'EIA%'    THEN 'eia_inventory'
                WHEN source LIKE 'AIS%'                                 THEN 'ais_traffic'
                WHEN source LIKE 'OilPriceAPI%'                         THEN 'price_spike'
                WHEN source LIKE 'ECOS%'                                THEN 'fx_krw_usd'
                ELSE 'news_tone'
            END,
            CAST(CASE tier WHEN 'A' THEN 1.0 WHEN 'B' THEN 0.8 ELSE 0.7 END AS DOUBLE)
        ) * CASE direction WHEN 'bullish' THEN 1 WHEN 'bearish' THEN -1 ELSE 0 END
    AS DECIMAL(8, 2)) AS weighted_contribution,
    current_timestamp() AS computed_at,
    '{run_id}' AS job_run_id
FROM crude_compass.bronze.news_articles
WHERE importance >= 50
  AND DATE(published_at) >= CURRENT_DATE() - INTERVAL 90 DAYS
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
        a.category
    FROM crude_compass.silver.signal_events_decayed s
    JOIN crude_compass.bronze.news_articles a ON s.signal_id = a.article_id
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
    SELECT
        SUM(CASE WHEN n >= 2 THEN 5 ELSE 0 END) AS cross_val_bonus
    FROM (
        SELECT category, direction, COUNT(*) AS n
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
