# Databricks notebook source
# MAGIC %md
# MAGIC # Sprint 3 Day 3 — v5 Backtest 종합 분석 + Counterfactual
# MAGIC
# MAGIC ## 목적
# MAGIC v5 backtest (300 stratified samples) 결과를 다각도로 분석:
# MAGIC 1. **Per zone metrics**: HIGH/MID/LOW zone별 hit rate + saving
# MAGIC 2. **Time period split**: 2019-2024 (LLM cutoff IN) vs 2025-2026 (OUT) — cheating check
# MAGIC 3. **Multi-metric**: Sharpe + max drawdown + volatility reduction
# MAGIC 4. **Counterfactual**:
# MAGIC    - AI vs default mix (current)
# MAGIC    - AI vs random mix (sanity check)
# MAGIC    - AI vs anti-AI (upper/lower bound)
# MAGIC    - AI vs rule-based v3 D variant
# MAGIC 5. **Confidence calibration**: conf level별 hit rate
# MAGIC
# MAGIC ## 입력
# MAGIC - `crude_compass.gold.llm_backtest_predictions` 최신 run (v5)

# COMMAND ----------

# Widget: run_id 선택 (없으면 최신)
dbutils.widgets.text("run_id", "auto", "Run ID ('auto' = latest)")
RUN_ID_PARAM = dbutils.widgets.get("run_id")

import json
TARGET_TABLE = "crude_compass.gold.llm_backtest_predictions"

if RUN_ID_PARAM == "auto":
    latest = spark.sql(f"""
        SELECT run_id FROM {TARGET_TABLE}
        WHERE run_id LIKE 'llm_v5_%'
        ORDER BY computed_at DESC LIMIT 1
    """).collect()
    RUN_ID = latest[0].run_id if latest else None
else:
    RUN_ID = RUN_ID_PARAM

print(f"Analysis target: run_id = {RUN_ID}")
if RUN_ID is None:
    dbutils.notebook.exit(json.dumps({"error": "no v5 run found"}))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Per-zone breakdown

# COMMAND ----------

print("=== 1. Per-zone breakdown ===")
per_zone = spark.sql(f"""
    SELECT
        CASE WHEN pattern_score >= 70 THEN 'HIGH'
             WHEN pattern_score <= 30 THEN 'LOW'
             ELSE 'MID' END AS zone,
        action_type, mission_type,
        COUNT(*) AS n,
        ROUND(AVG(confidence_score), 1) AS avg_conf,
        ROUND(AVG(cost_saving_30d), 3) AS avg_s30,
        ROUND(SUM(CASE WHEN cost_saving_30d > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS hit_30d
    FROM {TARGET_TABLE} WHERE run_id = '{RUN_ID}'
    GROUP BY zone, action_type, mission_type
    ORDER BY zone, action_type, mission_type
""").collect()
print(f"{'zone':<5} {'action':<13} {'mission':<13} {'n':>4} {'conf':>6} {'s30':>8} {'hit_30d':>8}")
for r in per_zone:
    print(f"{r.zone:<5} {r.action_type or '-':<13} {r.mission_type or '-':<13} {r.n:>4} {r.avg_conf or '-':>6} {r.avg_s30 or '-':>8} {r.hit_30d or 0:>7}%")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Time period split (LLM cutoff cheating check)

# COMMAND ----------

print("\n=== 2. Time period split ===")
period_split = spark.sql(f"""
    SELECT
        CASE WHEN as_of_date < DATE'2025-01-01' THEN '2019-2024 (LLM cutoff IN)'
             ELSE '2025-2026 (cutoff OUT)' END AS period,
        mission_type, COUNT(*) AS n,
        ROUND(AVG(cost_saving_30d), 3) AS avg_s30,
        ROUND(SUM(CASE WHEN cost_saving_30d > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS hit_30d
    FROM {TARGET_TABLE} WHERE run_id = '{RUN_ID}'
      AND action_type = 'new_mission'
    GROUP BY period, mission_type
    ORDER BY period, mission_type
""").collect()
print(f"{'period':<28} {'mission':<13} {'n':>4} {'s30':>8} {'hit_30d':>8}")
for r in period_split:
    print(f"{r.period:<28} {r.mission_type or '-':<13} {r.n:>4} {r.avg_s30 or 0:>8} {r.hit_30d or 0:>7}%")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Multi-metric: Sharpe + Max Drawdown + Vol Reduction

# COMMAND ----------

print("\n=== 3. Multi-metric ===")
multi = spark.sql(f"""
    WITH active AS (
        SELECT mission_type,
               CAST(cost_saving_7d AS DOUBLE) AS s7,
               CAST(cost_saving_30d AS DOUBLE) AS s30,
               CAST(cost_saving_90d AS DOUBLE) AS s90
        FROM {TARGET_TABLE}
        WHERE run_id = '{RUN_ID}' AND action_type = 'new_mission'
    )
    SELECT mission_type, COUNT(*) AS n,
           ROUND(AVG(s30), 3) AS mean,
           ROUND(STDDEV_SAMP(s30), 3) AS std,
           ROUND(AVG(s30) / NULLIF(STDDEV_SAMP(s30), 0), 3) AS sharpe,
           ROUND(MIN(s30), 3) AS worst_dd,
           ROUND(MAX(s30), 3) AS best,
           ROUND(SUM(CASE WHEN s30 > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS hit_pct
    FROM active GROUP BY mission_type
""").collect()
print(f"{'mission':<13} {'n':>4} {'mean':>8} {'std':>8} {'sharpe':>8} {'worst_dd':>10} {'best':>8} {'hit':>6}")
for r in multi:
    print(f"{r.mission_type or '-':<13} {r.n:>4} {r.mean:>8} {r.std:>8} {r.sharpe or 0:>8} {r.worst_dd:>10} {r.best:>8} {r.hit_pct:>5}%")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Counterfactual — AI vs alternatives (per-row simulation)
# MAGIC
# MAGIC 같은 sample에 대해:
# MAGIC - AI 권고 (current)
# MAGIC - default mix (saving = 0 by definition)
# MAGIC - random mix (50% 확률로 HEDGE/OPP 적용)
# MAGIC - anti-AI (AI 권고 반대로)
# MAGIC
# MAGIC anti-AI 평가:
# MAGIC - HEDGE 권고 → OPP 적용 → saving = -1 × AI saving
# MAGIC - OPP 권고 → HEDGE 적용 → saving = -1 × AI saving
# MAGIC (대칭 mix 가정 시)

# COMMAND ----------

print("\n=== 4. Counterfactual ===")
counterfactual = spark.sql(f"""
    WITH base AS (
        SELECT
            CAST(cost_saving_30d AS DOUBLE) AS ai_save,
            -- Anti-AI: assume symmetric
            -CAST(cost_saving_30d AS DOUBLE) AS anti_save,
            -- Random: 50% prob 적용 → expected = AI/2 (rough)
            CAST(cost_saving_30d AS DOUBLE) * 0.5 AS random_save,
            -- Default = 0 always
            0.0 AS default_save
        FROM {TARGET_TABLE}
        WHERE run_id = '{RUN_ID}' AND action_type = 'new_mission' AND cost_saving_30d IS NOT NULL
    )
    SELECT
        'AI (Mission Plan Agent)' AS strategy,
        ROUND(AVG(ai_save), 3) AS mean_s30,
        ROUND(SUM(CASE WHEN ai_save > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS hit_pct,
        COUNT(*) AS n
    FROM base
    UNION ALL SELECT 'Random mix (50/50 coinflip)',
        ROUND(AVG(random_save), 3),
        ROUND(SUM(CASE WHEN random_save > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1),
        COUNT(*) FROM base
    UNION ALL SELECT 'Anti-AI (opposite recommendation)',
        ROUND(AVG(anti_save), 3),
        ROUND(SUM(CASE WHEN anti_save > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1),
        COUNT(*) FROM base
    UNION ALL SELECT 'Default mix (no AI, baseline 75/25)',
        ROUND(AVG(default_save), 3),
        ROUND(SUM(CASE WHEN default_save > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1),
        COUNT(*) FROM base
""").collect()
print(f"{'strategy':<40} {'mean_s30':>10} {'hit_pct':>10} {'n':>4}")
for r in counterfactual:
    print(f"{r.strategy:<40} {r.mean_s30:>10} {r.hit_pct:>9}% {r.n:>4}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Confidence calibration

# COMMAND ----------

print("\n=== 5. Confidence calibration ===")
calibration = spark.sql(f"""
    SELECT
        CASE WHEN confidence_score >= 90 THEN '90-100 (very high)'
             WHEN confidence_score >= 80 THEN '80-89 (high)'
             WHEN confidence_score >= 70 THEN '70-79 (medium)'
             WHEN confidence_score >= 60 THEN '60-69 (lower)'
             ELSE '< 60 (low)' END AS conf_bin,
        COUNT(*) AS n,
        ROUND(AVG(cost_saving_30d), 3) AS avg_s30,
        ROUND(SUM(CASE WHEN cost_saving_30d > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS hit_30d
    FROM {TARGET_TABLE} WHERE run_id = '{RUN_ID}'
      AND action_type = 'new_mission'
      AND confidence_score IS NOT NULL
    GROUP BY conf_bin
    ORDER BY MAX(confidence_score) DESC
""").collect()
print(f"{'conf_bin':<22} {'n':>4} {'s30':>10} {'hit_30d':>9}")
for r in calibration:
    print(f"{r.conf_bin:<22} {r.n:>4} {r.avg_s30 or 0:>10} {r.hit_30d or 0:>8}%")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. By regime (year)

# COMMAND ----------

print("\n=== 6. By year ===")
by_year = spark.sql(f"""
    SELECT YEAR(as_of_date) AS yr,
           mission_type, COUNT(*) AS n,
           ROUND(AVG(cost_saving_30d), 3) AS avg_s30,
           ROUND(SUM(CASE WHEN cost_saving_30d > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS hit_30d
    FROM {TARGET_TABLE} WHERE run_id = '{RUN_ID}'
      AND action_type = 'new_mission'
    GROUP BY yr, mission_type
    ORDER BY yr, mission_type
""").collect()
print(f"{'year':<5} {'mission':<13} {'n':>4} {'s30':>8} {'hit_30d':>9}")
for r in by_year:
    print(f"{r.yr:<5} {r.mission_type or '-':<13} {r.n:>4} {r.avg_s30 or 0:>8} {r.hit_30d or 0:>8}%")

# COMMAND ----------

# Summary stats final
print("\n\n=========================================")
print(f"=== v5 Backtest 종합 (run_id={RUN_ID}) ===")
print("=========================================")
overall = spark.sql(f"""
    SELECT COUNT(*) AS n_total,
           SUM(CASE WHEN action_type = 'new_mission' THEN 1 ELSE 0 END) AS n_action,
           SUM(CASE WHEN mission_type = 'HEDGE' AND action_type = 'new_mission' THEN 1 ELSE 0 END) AS n_hedge,
           SUM(CASE WHEN mission_type = 'OPPORTUNITY' AND action_type = 'new_mission' THEN 1 ELSE 0 END) AS n_opp,
           SUM(CASE WHEN action_type = 'continue' THEN 1 ELSE 0 END) AS n_stay,
           ROUND(AVG(CASE WHEN action_type = 'new_mission' THEN cost_saving_30d END), 3) AS avg_save_active,
           ROUND(SUM(CASE WHEN action_type = 'new_mission' AND cost_saving_30d > 0 THEN 1 ELSE 0 END) * 100.0 /
                 NULLIF(SUM(CASE WHEN action_type = 'new_mission' THEN 1 ELSE 0 END), 0), 1) AS hit_active
    FROM {TARGET_TABLE} WHERE run_id = '{RUN_ID}'
""").collect()[0]
print(f"Total samples: {overall.n_total}")
print(f"  STAY (continue): {overall.n_stay}")
print(f"  Active recommendation: {overall.n_action} (HEDGE={overall.n_hedge}, OPP={overall.n_opp})")
print(f"Active recommendation outcomes (30d):")
print(f"  Average cost saving: {overall.avg_save_active}%")
print(f"  Hit rate (saving > 0): {overall.hit_active}%")

# COMMAND ----------

dbutils.notebook.exit(json.dumps({
    "run_id": RUN_ID,
    "n_samples": overall.n_total,
    "n_active": overall.n_action,
    "avg_save_active": float(overall.avg_save_active or 0),
    "hit_active": float(overall.hit_active or 0),
}))
