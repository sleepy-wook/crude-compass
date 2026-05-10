-- ====================================================================
-- Crude Compass · Gold layer (Delta, analytics)
-- ====================================================================
-- 적재: Job 6 weekly_self_critique (mock stub) + Lakehouse Sync (CDC)
-- 보존: infinite
-- ====================================================================

CREATE SCHEMA IF NOT EXISTS crude_compass.gold;

-- ────────────────────────────────────────────────────────────────────
-- 1. daily_risk_score  ⭐ (D-14 추가, 시나리오 §6 + §13 핵심)
-- ────────────────────────────────────────────────────────────────────
-- 매일 야간 배치로 갱신. Lakebase 캐시 sync.
-- Apps Discovery 첫 화면 ms 응답용.
CREATE TABLE IF NOT EXISTS crude_compass.gold.daily_risk_score (
    date              DATE          NOT NULL    PRIMARY KEY,
    pattern_score     DECIMAL(5, 2) NOT NULL COMMENT '0-100',
    bullish_score     DECIMAL(8, 2) NOT NULL,
    bearish_score     DECIMAL(8, 2) NOT NULL,
    cross_val_bonus   DECIMAL(5, 2) NOT NULL,
    confidence_score  DECIMAL(5, 2) NOT NULL COMMENT 'UI 노출용 0-100',

    mission_type      STRING        NOT NULL COMMENT 'HEDGE | OPPORTUNITY | NONE',
    -- 시그널별 기여도 (시나리오 §6.3 #2)
    top_contributors  STRING        COMMENT 'JSON: [{signal_type, contribution_pct, ...}]',

    signal_count_90d  INT           NOT NULL,
    computed_at       TIMESTAMP     NOT NULL,
    lambda_table_id   STRING        COMMENT '시간 감쇠 람다 버전 (Time Travel 비교용)',
    job_run_id        STRING
)
USING DELTA;

-- ────────────────────────────────────────────────────────────────────
-- 2. mission_outcomes
-- ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS crude_compass.gold.mission_outcomes (
    mission_id        STRING        NOT NULL,
    mission_type      STRING        NOT NULL,
    proposed_at       TIMESTAMP     NOT NULL,
    confirmed_at      TIMESTAMP,
    completed_at      TIMESTAMP,
    final_status      STRING        NOT NULL,
    pattern_score     DECIMAL(5, 2),
    confidence_score  DECIMAL(5, 2),
    target_pct        INT,
    actual_pct        INT,
    roi_simulated     DECIMAL(12, 2),
    roi_realized      DECIMAL(12, 2),
    pivot_count       INT
)
USING DELTA;

-- ────────────────────────────────────────────────────────────────────
-- 3. landing_cost_scenarios  (D-14 추가, 시나리오 §5 + §9.5 UC Function)
-- ────────────────────────────────────────────────────────────────────
-- "원유 가격 같아도 도착 비용 다르다" — 보험료 + 운임 + 우회 비용 반영
CREATE TABLE IF NOT EXISTS crude_compass.gold.landing_cost_scenarios (
    scenario_id       STRING        NOT NULL,
    computed_at       TIMESTAMP     NOT NULL,
    benchmark         STRING        NOT NULL COMMENT 'BRENT | DUBAI | WTI',
    benchmark_price   DECIMAL(8, 2) NOT NULL,
    route             STRING        NOT NULL COMMENT 'hormuz_direct | cape_of_good_hope (우회)',
    war_zone_premium  DECIMAL(6, 2) COMMENT 'JWC War Zone 보험료 추가',
    freight_cost      DECIMAL(8, 2),
    insurance_total   DECIMAL(8, 2),
    landing_cost_usd  DECIMAL(8, 2) NOT NULL COMMENT '$/bbl 도착 기준',
    extra_days        INT           COMMENT '우회 시 +9일 등'
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
