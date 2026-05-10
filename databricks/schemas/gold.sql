-- ====================================================================
-- Crude Compass · Gold layer (Delta, analytics)
-- ====================================================================
-- 적재: Job 6 weekly_self_critique (mock stub) + Lakehouse Sync (CDC)
-- 보존: infinite
-- ====================================================================

CREATE SCHEMA IF NOT EXISTS crude_compass.gold;

-- ────────────────────────────────────────────────────────────────────
-- 1. mission_outcomes
-- ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS crude_compass.gold.mission_outcomes (
    mission_id        STRING        NOT NULL,
    mission_type      STRING        NOT NULL,
    proposed_at       TIMESTAMP     NOT NULL,
    confirmed_at      TIMESTAMP,
    completed_at      TIMESTAMP,
    final_status      STRING        NOT NULL,
    pattern_score     DECIMAL(5, 2),
    target_pct        INT,
    actual_pct        INT,
    roi_simulated     DECIMAL(12, 2),
    roi_realized      DECIMAL(12, 2),
    pivot_count       INT
)
USING DELTA;

-- ────────────────────────────────────────────────────────────────────
-- 2. backtest_results  ⭐ Mock backtest narrative source (78%/71%)
-- ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS crude_compass.gold.backtest_results (
    run_id              STRING        NOT NULL,
    backtest_window     STRING        NOT NULL COMMENT '2025-12 ~ 2026-04',
    mission_type        STRING        NOT NULL,
    signal_count        INT           NOT NULL,
    correct_count       INT           NOT NULL,
    accuracy_pct        DECIMAL(5, 2) NOT NULL,
    avg_lead_time_days  DECIMAL(5, 1),
    threshold_used      DECIMAL(5, 2) COMMENT '70 (HEDGE) or 30 (OPP)',
    computed_at         TIMESTAMP     NOT NULL
)
USING DELTA;

-- ────────────────────────────────────────────────────────────────────
-- 3. missions_history  (Lakehouse Sync target — auto)
-- ────────────────────────────────────────────────────────────────────
-- Lakebase missions 테이블의 CDC append-only mirror.
-- 형욱님 직접 만들지 않음. Sprint 4 진입 시 Lakebase UI에서 Lakehouse Sync 활성화 →
-- Databricks가 자동 생성. 여기는 placeholder 주석.
--
-- Schema: Lakebase missions schema + (cdc_op, cdc_ts, cdc_seq)
