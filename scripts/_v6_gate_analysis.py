"""Plan B — Multi-source rule-based gate on v5 LLM predictions (single-session SQL)."""
from __future__ import annotations
import sys
sys.stdout.reconfigure(encoding="utf-8")

from databricks.sdk import WorkspaceClient

PROFILE = "crude-compass"
WH = "da56f72320e22238"
RUN_ID = "llm_v5_20260511T191230"

w = WorkspaceClient(profile=PROFILE)

GATE_CTE = f"""
WITH v5 AS (
    SELECT * FROM crude_compass.gold.llm_backtest_predictions WHERE run_id = '{RUN_ID}'
),
eia_avg AS (
    SELECT v.sample_idx, AVG(CAST(e.delta_vs_prev_wk AS DOUBLE)) AS eia_4wk_avg
    FROM v5 v LEFT JOIN crude_compass.bronze.eia_inventory e
        ON e.inventory_type='commercial'
        AND e.week_ending BETWEEN v.as_of_date - INTERVAL 28 DAYS AND v.as_of_date
    GROUP BY v.sample_idx
),
opec_latest AS (
    SELECT v.sample_idx,
           MAX(CAST(o.opec_total_kbbl_d AS DOUBLE)) AS opec_total,
           MAX(CAST(o.forecast_demand_kbbl_d AS DOUBLE)) AS demand
    FROM v5 v LEFT JOIN crude_compass.bronze.opec_momr_parsed o
        ON TO_DATE(CONCAT(o.report_month, '-01'), 'yyyy-MM-dd')
           BETWEEN v.as_of_date - INTERVAL 90 DAYS AND v.as_of_date
        AND o.saudi_production_kbbl_d IS NOT NULL
    GROUP BY v.sample_idx
),
gated AS (
    SELECT v.sample_idx, v.as_of_date, v.pattern_score, v.confidence_score,
           v.action_type, v.mission_type,
           CAST(v.cost_saving_30d AS DOUBLE) AS s30,
           e.eia_4wk_avg, o.opec_total, o.demand,
           CASE
               WHEN v.action_type = 'new_mission' AND v.mission_type = 'HEDGE'
                    AND (e.eia_4wk_avg > 5000
                         OR (o.opec_total IS NOT NULL AND o.demand IS NOT NULL AND o.opec_total > o.demand * 1.02))
                   THEN 'OVERRIDE_TO_STAY'
               WHEN v.action_type = 'new_mission' AND v.mission_type = 'OPPORTUNITY'
                    AND (e.eia_4wk_avg < -5000
                         OR (o.opec_total IS NOT NULL AND o.demand IS NOT NULL AND o.opec_total < o.demand * 0.98))
                   THEN 'OVERRIDE_TO_STAY'
               ELSE 'KEEP'
           END AS gate_decision,
           CASE
               WHEN v.action_type = 'new_mission' AND v.mission_type = 'HEDGE'
                    AND (e.eia_4wk_avg > 5000
                         OR (o.opec_total IS NOT NULL AND o.demand IS NOT NULL AND o.opec_total > o.demand * 1.02))
                   THEN 0.0
               WHEN v.action_type = 'new_mission' AND v.mission_type = 'OPPORTUNITY'
                    AND (e.eia_4wk_avg < -5000
                         OR (o.opec_total IS NOT NULL AND o.demand IS NOT NULL AND o.opec_total < o.demand * 0.98))
                   THEN 0.0
               ELSE CAST(v.cost_saving_30d AS DOUBLE)
           END AS new_s30
    FROM v5 v
    LEFT JOIN eia_avg e ON v.sample_idx = e.sample_idx
    LEFT JOIN opec_latest o ON v.sample_idx = o.sample_idx
)
"""


def q(sql):
    full = GATE_CTE + " " + sql
    r = w.statement_execution.execute_statement(statement=full, warehouse_id=WH, wait_timeout="50s")
    if r.status and r.status.error:
        print("err:", r.status.error.message[:500])
        return []
    return r.result.data_array if r.result else []


# 1. Gate decision distribution
print("=== 1. Gate decision breakdown ===")
print(f"{'mission':<14} {'decision':<20} {'n':>4} {'orig_s30':>10} {'new_s30':>9} {'orig_hit':>9} {'new_hit':>8}")
for row in q("""
    SELECT mission_type, gate_decision, COUNT(*) AS n,
           ROUND(AVG(s30), 3) AS orig_s30,
           ROUND(AVG(new_s30), 3) AS new_s30,
           ROUND(SUM(CASE WHEN s30 > 0 THEN 1 ELSE 0 END)*100.0/COUNT(*), 1) AS orig_hit,
           ROUND(SUM(CASE WHEN new_s30 > 0 THEN 1 ELSE 0 END)*100.0/COUNT(*), 1) AS new_hit
    FROM gated
    WHERE action_type = 'new_mission'
    GROUP BY mission_type, gate_decision
    ORDER BY mission_type, gate_decision
"""):
    print(f"{row[0] or '-':<14} {row[1] or '-':<20} {row[2]:>4} {row[3] or 0:>10} {row[4] or 0:>9} {row[5] or 0:>8}% {row[6] or 0:>7}%")

# 2. Overall comparison
print("\n=== 2. Overall (active recs only, kept after gate) ===")
print(f"{'mission':<14} {'orig_n':>6} {'kept':>4} {'override':>9} {'orig_hit':>9} {'kept_hit':>9} {'orig_save':>10} {'kept_save':>10}")
for row in q("""
    SELECT mission_type,
           COUNT(*) AS orig_n,
           SUM(CASE WHEN gate_decision='KEEP' THEN 1 ELSE 0 END) AS kept,
           SUM(CASE WHEN gate_decision='OVERRIDE_TO_STAY' THEN 1 ELSE 0 END) AS override_n,
           ROUND(SUM(CASE WHEN s30 > 0 THEN 1 ELSE 0 END)*100.0/COUNT(*), 1) AS orig_hit,
           ROUND(SUM(CASE WHEN gate_decision='KEEP' AND s30 > 0 THEN 1 ELSE 0 END)*100.0/NULLIF(SUM(CASE WHEN gate_decision='KEEP' THEN 1 ELSE 0 END), 0), 1) AS kept_hit,
           ROUND(AVG(s30), 3) AS orig_save,
           ROUND(AVG(CASE WHEN gate_decision='KEEP' THEN s30 END), 3) AS kept_save
    FROM gated
    WHERE action_type = 'new_mission'
    GROUP BY mission_type
    ORDER BY mission_type
"""):
    print(f"{row[0] or '-':<14} {row[1]:>6} {row[2]:>4} {row[3]:>9} {row[4] or 0:>8}% {row[5] or 0:>8}% {row[6] or 0:>10} {row[7] or 0:>10}")

# 3. By confidence (kept only)
print("\n=== 3. By confidence (kept only) ===")
print(f"{'conf':<8} {'n':>4} {'save':>10} {'hit':>8}")
for row in q("""
    SELECT
        CASE WHEN confidence_score >= 90 THEN '90-100'
             WHEN confidence_score >= 80 THEN '80-89'
             WHEN confidence_score >= 70 THEN '70-79'
             WHEN confidence_score >= 60 THEN '60-69'
             ELSE '<60' END AS conf_bin,
        COUNT(*) AS n,
        ROUND(AVG(s30), 3) AS save,
        ROUND(SUM(CASE WHEN s30 > 0 THEN 1 ELSE 0 END)*100.0/COUNT(*), 1) AS hit
    FROM gated WHERE action_type = 'new_mission' AND gate_decision = 'KEEP'
    GROUP BY conf_bin ORDER BY MAX(confidence_score) DESC
"""):
    print(f"{row[0]:<8} {row[1]:>4} {row[2] or 0:>10} {row[3] or 0:>7}%")

# 4. Override 효과 (overridden case 분포)
print("\n=== 4. Override 효과 — overridden case 원본 saving 분포 ===")
print(f"{'mission':<14} {'n':>4} {'orig_avg':>10} {'bad(<-1%)':>11} {'small_loss':>11} {'zero':>5} {'pos_lost':>9}")
for row in q("""
    SELECT mission_type, COUNT(*) AS n,
           ROUND(AVG(s30), 3) AS avg_orig,
           SUM(CASE WHEN s30 < -1.0 THEN 1 ELSE 0 END) AS bad_loss,
           SUM(CASE WHEN s30 >= -1.0 AND s30 < 0 THEN 1 ELSE 0 END) AS small_loss,
           SUM(CASE WHEN s30 = 0 THEN 1 ELSE 0 END) AS zero,
           SUM(CASE WHEN s30 > 0 THEN 1 ELSE 0 END) AS positive_lost
    FROM gated WHERE gate_decision = 'OVERRIDE_TO_STAY'
    GROUP BY mission_type
"""):
    print(f"{row[0] or '-':<14} {row[1]:>4} {row[2] or 0:>10} {row[3]:>11} {row[4]:>11} {row[5]:>5} {row[6]:>9}")
print("(pos_lost = override 때문에 놓친 positive opportunities)")

# 5. Total saving comparison (the bottom line)
print("\n=== 5. Total $ saving (active only, sum across all samples) ===")
for row in q("""
    SELECT mission_type,
           ROUND(SUM(s30), 2) AS orig_total_save,
           ROUND(SUM(new_s30), 2) AS gated_total_save
    FROM gated WHERE action_type = 'new_mission'
    GROUP BY mission_type
    ORDER BY mission_type
"""):
    print(f"  {row[0] or '-':<14} orig_total={row[1]}, gated_total={row[2]}, diff={(row[2] or 0) - (row[1] or 0):+.2f}")
