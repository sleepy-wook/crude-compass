-- ====================================================================
-- Crude Compass · Silver layer (Delta, transformed)
-- ====================================================================
-- 적재: daily_curation job (signal_events_decayed + pattern_scores_daily).
-- 보존: 365일.
-- ====================================================================

CREATE SCHEMA IF NOT EXISTS crude_compass.silver;

-- ────────────────────────────────────────────────────────────────────
-- 1. pattern_scores_daily — Bidirectional Pattern Detection 결과
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

-- 2026-05-16 D-3 정리: silver.hormuz_traffic_hourly + silver.dubai_premium_daily 2개 dead table DROP.
-- 2026-05-16 D-2 정리: AIS Stream 완전 제거 — bronze.ais_positions 제거, signal_type ais_traffic 제거.
-- 호르무즈 narrative는 GDELT 뉴스 키워드 (news_tone) anchor로 대체.

-- ────────────────────────────────────────────────────────────────────
-- 2. signal_events_decayed — 시간 감쇠 적용 (시나리오 §6.2)
-- ────────────────────────────────────────────────────────────────────
-- 모든 시그널 (news/price/eia/fx/opec) × 시간 감쇠 + credibility + direction.
-- weighted_contribution 보존 → gold.signal_contribution_30d view 입력.
CREATE TABLE IF NOT EXISTS crude_compass.silver.signal_events_decayed (
    event_date            DATE          NOT NULL,
    signal_type           STRING        NOT NULL COMMENT 'news_tone|eia_inventory|opec_momr|fx_krw_usd|price_spike',
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
