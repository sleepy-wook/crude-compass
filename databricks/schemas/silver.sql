-- ====================================================================
-- Crude Compass · Silver layer (Delta, transformed)
-- ====================================================================
-- 적재: Job 5 daily_curation + Job 3 ais (집계)
-- 보존: 365일
-- ====================================================================

CREATE SCHEMA IF NOT EXISTS crude_compass.silver;

-- ────────────────────────────────────────────────────────────────────
-- 1. pattern_scores_daily  ⭐ Bidirectional Pattern Detection 결과
-- ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS crude_compass.silver.pattern_scores_daily (
    date              DATE          NOT NULL,
    pattern_score     DECIMAL(5, 2) NOT NULL COMMENT '0-100',
    bullish_score     DECIMAL(8, 2) NOT NULL,
    bearish_score     DECIMAL(8, 2) NOT NULL,
    cross_val_bonus   DECIMAL(5, 2) NOT NULL,
    mission_type      STRING        NOT NULL COMMENT 'HEDGE | OPPORTUNITY | NONE',
    signal_count_90d  INT           NOT NULL,
    top_categories    ARRAY<STRING>,
    computed_at       TIMESTAMP     NOT NULL,
    job_run_id        STRING
)
USING DELTA
TBLPROPERTIES (
    delta.autoOptimize.optimizeWrite = true
);

-- ────────────────────────────────────────────────────────────────────
-- 2. hormuz_traffic_hourly
-- ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS crude_compass.silver.hormuz_traffic_hourly (
    hour_start            TIMESTAMP     NOT NULL,
    vessel_count          INT           NOT NULL,
    delta_pct_vs_7d_avg   DECIMAL(5, 2),
    is_anomaly            BOOLEAN
)
USING DELTA;
