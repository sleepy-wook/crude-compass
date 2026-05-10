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

-- ────────────────────────────────────────────────────────────────────
-- 3. signal_events_decayed  (D-14 추가, 시나리오 §6.2 시간 감쇠)
-- ────────────────────────────────────────────────────────────────────
-- 모든 시그널 (news/price/ais/eia/fx/opec)의 시간 감쇠 적용 결과.
-- weighted_contribution 보존 → "오늘 점수 82는 호르무즈 35%, 두바이 28% ..." 시각화.
CREATE TABLE IF NOT EXISTS crude_compass.silver.signal_events_decayed (
    event_date            DATE          NOT NULL,
    signal_type           STRING        NOT NULL COMMENT 'news_tone|ais_traffic|eia_inventory|opec_momr|fx_krw_usd|price_spike',
    signal_id             STRING        NOT NULL COMMENT 'source row id (article_id, etc.)',
    raw_intensity         DECIMAL(6, 2) NOT NULL COMMENT '0-100 (importance) or signed value',
    direction             STRING        NOT NULL COMMENT 'bullish|bearish|neutral',
    source_credibility    DECIMAL(3, 2) NOT NULL COMMENT '0.00-1.00 (Tier A=1.0, B=0.8 등)',

    -- 감쇠 적용
    days_ago              INT           NOT NULL,
    lambda_used           DECIMAL(6, 4) NOT NULL COMMENT 'exp(-λ × days_ago) 의 λ',
    applied_weight        DECIMAL(6, 4) NOT NULL COMMENT 'exp(-λ × days_ago)',
    weighted_contribution DECIMAL(8, 2) NOT NULL COMMENT 'raw × weight × credibility',

    computed_at           TIMESTAMP     NOT NULL,
    job_run_id            STRING
)
USING DELTA
PARTITIONED BY (event_date);

-- ────────────────────────────────────────────────────────────────────
-- 4. dubai_premium_daily  (D-14 추가, 시나리오 §13 What-If 차트)
-- ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS crude_compass.silver.dubai_premium_daily (
    date              DATE          NOT NULL    PRIMARY KEY,
    brent_close       DECIMAL(8, 2) NOT NULL,
    dubai_close       DECIMAL(8, 2) NOT NULL,
    spread_usd        DECIMAL(6, 2) NOT NULL COMMENT 'Dubai - Brent (양수면 Dubai premium)',
    spread_7d_avg     DECIMAL(6, 2),
    is_premium_anomaly BOOLEAN     COMMENT '7일 평균 대비 ±2σ 초과'
)
USING DELTA;
