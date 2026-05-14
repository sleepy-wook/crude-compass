"""Backtest predictions CRUD against Lakebase Postgres.

Schema: databricks/schemas/lakebase.sql §5 backtest_predictions
Read pattern: WhatIf 페이지 — 최근 run 300 rows fetch (ms latency)
Write pattern: backtest notebook batch (`executemany`)
"""
from __future__ import annotations

import psycopg
from psycopg.rows import dict_row


# ──────────────────────────────────────────────────────────────────────────
# Read (Apps consumption)
# ──────────────────────────────────────────────────────────────────────────
def get_summary(conn: psycopg.Connection) -> dict | None:
    """Latest run summary — hit_rate, n_active, n_hedge, n_opp, avg_saving."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            WITH latest AS (
              SELECT run_id, MAX(computed_at) AS latest_at
              FROM backtest_predictions
              GROUP BY run_id
              ORDER BY latest_at DESC
              LIMIT 1
            )
            SELECT
              p.run_id,
              COUNT(*) AS n_total,
              COUNT(*) FILTER (WHERE p.action_type = 'new_mission') AS n_active,
              COUNT(*) FILTER (WHERE p.mission_type = 'HEDGE') AS n_hedge,
              COUNT(*) FILTER (WHERE p.mission_type = 'OPPORTUNITY') AS n_opp,
              ROUND(AVG(p.saving_30d_pct)::numeric, 4) AS avg_save_pct,
              ROUND(
                100.0 * COUNT(*) FILTER (
                  WHERE p.action_type = 'new_mission' AND p.saving_30d_pct > 0
                ) / NULLIF(COUNT(*) FILTER (WHERE p.action_type = 'new_mission'), 0),
                1
              ) AS hit_rate_pct
            FROM backtest_predictions p
            JOIN latest l ON p.run_id = l.run_id
            GROUP BY p.run_id
        """)
        row = cur.fetchone()
    if not row:
        return None
    return dict(row)


def list_predictions(conn: psycopg.Connection, limit: int = 300) -> list[dict]:
    """최근 run의 predictions (frontend WhatIf slider용)."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            WITH latest AS (
              SELECT run_id, MAX(computed_at) AS latest_at
              FROM backtest_predictions
              GROUP BY run_id
              ORDER BY latest_at DESC
              LIMIT 1
            )
            SELECT
              p.as_of_date,
              p.pattern_score,
              p.confidence_score,
              p.action_type,
              p.mission_type,
              p.target_pct,
              p.duration_days,
              p.saving_7d_pct,
              p.saving_30d_pct,
              p.saving_90d_pct,
              p.dubai_at_signal_usd,
              p.dubai_30d_usd
            FROM backtest_predictions p
            JOIN latest l ON p.run_id = l.run_id
            ORDER BY p.as_of_date DESC
            LIMIT %s
        """, (limit,))
        return [dict(r) for r in cur.fetchall()]


def get_zone_breakdown(conn: psycopg.Connection) -> list[dict]:
    """Latest run — zone × mission_type breakdown."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            WITH latest AS (
              SELECT run_id, MAX(computed_at) AS latest_at
              FROM backtest_predictions GROUP BY run_id
              ORDER BY latest_at DESC LIMIT 1
            )
            SELECT
              p.zone,
              p.mission_type,
              COUNT(*) AS n,
              ROUND(AVG(p.saving_30d_pct)::numeric, 4) AS avg_save_pct,
              ROUND(
                100.0 * COUNT(*) FILTER (WHERE p.saving_30d_pct > 0) / NULLIF(COUNT(*), 0), 1
              ) AS hit_rate_pct
            FROM backtest_predictions p
            JOIN latest l ON p.run_id = l.run_id
            WHERE p.action_type = 'new_mission'
            GROUP BY p.zone, p.mission_type
            ORDER BY p.zone, p.mission_type
        """)
        return [dict(r) for r in cur.fetchall()]


def get_confidence_breakdown(conn: psycopg.Connection) -> list[dict]:
    """Confidence bin × hit_rate."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            WITH latest AS (
              SELECT run_id, MAX(computed_at) AS latest_at
              FROM backtest_predictions GROUP BY run_id
              ORDER BY latest_at DESC LIMIT 1
            ),
            binned AS (
              SELECT
                CASE
                  WHEN p.confidence_score >= 80 THEN '80-100'
                  WHEN p.confidence_score >= 60 THEN '60-79'
                  WHEN p.confidence_score >= 40 THEN '40-59'
                  ELSE '<40'
                END AS conf_bin,
                p.saving_30d_pct
              FROM backtest_predictions p
              JOIN latest l ON p.run_id = l.run_id
              WHERE p.action_type = 'new_mission'
            )
            SELECT
              conf_bin,
              COUNT(*) AS n,
              ROUND(AVG(saving_30d_pct)::numeric, 4) AS avg_save_pct,
              ROUND(100.0 * COUNT(*) FILTER (WHERE saving_30d_pct > 0) / NULLIF(COUNT(*), 0), 1) AS hit_rate_pct
            FROM binned
            GROUP BY conf_bin
            ORDER BY conf_bin DESC
        """)
        return [dict(r) for r in cur.fetchall()]
