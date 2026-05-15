-- ====================================================================
-- Crude Compass · Gold layer (Delta, analytics)
-- ====================================================================
-- 적재: daily_curation (daily_risk_score) + backtest_compute (backtest_results)
-- + Lakehouse Sync (missions_history mirror).
-- 보존: infinite.
-- ====================================================================

CREATE SCHEMA IF NOT EXISTS crude_compass.gold;

-- ────────────────────────────────────────────────────────────────────
-- 1. daily_risk_score — Pattern Score daily snapshot (Lakebase Sync 대상)
-- ────────────────────────────────────────────────────────────────────
-- Apps Discovery 첫 화면 ms 응답용. daily_curation job이 매일 06:30 갱신.
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

-- 2026-05-15 정리: mission_outcomes / landing_cost_scenarios / backtest_risk_score
-- 3개 dead gold table DROP.
-- 2026-05-16 정리: silver.hormuz_traffic_hourly + silver.dubai_premium_daily 2개 dead silver DROP.

-- ────────────────────────────────────────────────────────────────────
-- 2. backtest_results — Rule-based backtest 결과 (LLM backtest는 Lakebase)
-- ────────────────────────────────────────────────────────────────────
-- backtest_compute job 출력. AI/BI Dashboard에서 rule-based vs LLM 비교용.
-- Apps WhatIf 페이지는 Lakebase backtest_predictions 사용.
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
-- 3. missions_history (Lakehouse Sync target — Databricks UI에서 자동 생성)
-- ────────────────────────────────────────────────────────────────────
-- Lakebase missions 테이블의 CDC append-only mirror.
-- Schema: Lakebase missions + (cdc_op, cdc_ts, cdc_seq).

-- ════════════════════════════════════════════════════════════════════
-- ANALYTICS VIEWS (D-3 추가, Genie / AI-BI Dashboard / Apps consumption)
-- ════════════════════════════════════════════════════════════════════
-- Gold layer의 본질 = 분석/BI 패턴별 pre-shaped views.
-- bronze 원천 + silver 계산값을 BI-ready 형태로 노출.
-- VIEW 사용 (vs CREATE TABLE): 항상 fresh, 추가 storage 비용 0, refresh cron 불필요.

-- ────────────────────────────────────────────────────────────────────
-- V1. oil_prices_wide — WTI / Brent / Dubai pivot (daily)
-- ────────────────────────────────────────────────────────────────────
-- 용도: WhatIf 페이지, Dashboard 가격 차트, Brent-Dubai spread 모니터링
CREATE OR REPLACE VIEW crude_compass.gold.oil_prices_wide AS
SELECT
    trade_date,
    MAX(CASE WHEN ticker = 'WTI'   THEN price_usd END) AS wti_usd,
    MAX(CASE WHEN ticker = 'BRENT' THEN price_usd END) AS brent_usd,
    MAX(CASE WHEN ticker = 'DUBAI' THEN price_usd END) AS dubai_usd,
    MAX(CASE WHEN ticker = 'BRENT' THEN price_usd END)
        - MAX(CASE WHEN ticker = 'DUBAI' THEN price_usd END) AS brent_dubai_spread_usd
FROM crude_compass.bronze.oil_prices_daily
GROUP BY trade_date;

-- ────────────────────────────────────────────────────────────────────
-- V2. fleet_current_state — KPETRO 5척 최신 위치 + zone enum
-- ────────────────────────────────────────────────────────────────────
-- 용도: Apps FleetMap, Dashboard, Genie "K-Petroleum 어디 있나?"
-- zone enum: hormuz | red_sea | indian_ocean | korean_waters | gulf_of_mexico | transit
CREATE OR REPLACE VIEW crude_compass.gold.fleet_current_state AS
SELECT
    mmsi,
    vessel_name,
    lat, lon, speed_knots, heading_deg,
    in_hormuz_bbox, status, fetched_at,
    CASE
        WHEN in_hormuz_bbox THEN 'hormuz'
        WHEN lat BETWEEN 12 AND 30 AND lon BETWEEN 32 AND 44   THEN 'red_sea'
        WHEN lat BETWEEN -10 AND 25 AND lon BETWEEN 45 AND 80  THEN 'indian_ocean'
        WHEN lat BETWEEN 25 AND 45 AND lon BETWEEN 122 AND 135 THEN 'korean_waters'
        WHEN lat BETWEEN 18 AND 30 AND lon BETWEEN -98 AND -82 THEN 'gulf_of_mexico'
        ELSE 'transit'
    END AS zone
FROM crude_compass.bronze.ais_positions
WHERE mmsi LIKE 'KPETRO_%'
QUALIFY ROW_NUMBER() OVER (PARTITION BY mmsi ORDER BY fetched_at DESC) = 1;

-- ────────────────────────────────────────────────────────────────────
-- V3. signal_contribution_30d — silver.signal_events_decayed 최근 30일 합
-- ────────────────────────────────────────────────────────────────────
-- 용도: Discovery 첫 화면 "오늘 점수 어떤 시그널이 끌어올렸나?"
-- Genie 평가위원 데모 핵심 query
CREATE OR REPLACE VIEW crude_compass.gold.signal_contribution_30d AS
SELECT
    signal_type,
    direction,
    COUNT(*) AS n_signals,
    ROUND(SUM(weighted_contribution), 2) AS total_contribution,
    ROUND(AVG(raw_intensity), 1) AS avg_raw_intensity,
    ROUND(AVG(source_credibility), 2) AS avg_credibility
FROM crude_compass.silver.signal_events_decayed
WHERE event_date >= CURRENT_DATE() - INTERVAL 30 DAYS
  AND direction != 'neutral'
GROUP BY signal_type, direction;

-- ────────────────────────────────────────────────────────────────────
-- V4. eia_rolling — EIA inventory 4-week rolling avg + direction
-- ────────────────────────────────────────────────────────────────────
-- 용도: Dashboard EIA 시계열, backtest prompt structured fields
CREATE OR REPLACE VIEW crude_compass.gold.eia_rolling AS
WITH base AS (
    SELECT
        week_ending, inventory_type,
        value_kbbl, delta_vs_prev_wk,
        AVG(delta_vs_prev_wk) OVER (
            PARTITION BY inventory_type
            ORDER BY week_ending
            ROWS BETWEEN 3 PRECEDING AND CURRENT ROW
        ) AS delta_4wk_avg
    FROM crude_compass.bronze.eia_inventory
    WHERE inventory_type = 'commercial'
)
SELECT
    week_ending, inventory_type, value_kbbl, delta_vs_prev_wk,
    ROUND(delta_4wk_avg, 1) AS delta_4wk_avg_kbbl,
    CASE
        WHEN delta_4wk_avg > 5000  THEN 'bearish'
        WHEN delta_4wk_avg < -5000 THEN 'bullish'
        ELSE 'neutral'
    END AS signal_direction
FROM base;

-- ────────────────────────────────────────────────────────────────────
-- V5. opec_demand_gap — OPEC supply minus demand (monthly)
-- ────────────────────────────────────────────────────────────────────
-- 용도: Dashboard OPEC 시계열, backtest prompt structured fields
CREATE OR REPLACE VIEW crude_compass.gold.opec_demand_gap AS
SELECT
    report_month,
    saudi_production_kbbl_d,
    iran_production_kbbl_d,
    opec_total_kbbl_d,
    forecast_demand_kbbl_d,
    opec_total_kbbl_d - forecast_demand_kbbl_d AS supply_demand_gap_kbbl_d,
    CASE
        WHEN opec_total_kbbl_d - forecast_demand_kbbl_d > 500  THEN 'oversupply'
        WHEN opec_total_kbbl_d - forecast_demand_kbbl_d < -500 THEN 'undersupply'
        ELSE 'balanced'
    END AS market_balance
FROM crude_compass.bronze.opec_momr_parsed
WHERE opec_total_kbbl_d IS NOT NULL
  AND forecast_demand_kbbl_d IS NOT NULL;

-- ────────────────────────────────────────────────────────────────────
-- V6. fx_with_delta — USD/KRW + delta + 30일 변동성
-- ────────────────────────────────────────────────────────────────────
-- 용도: Dashboard FX 시계열, landing cost 계산 input
CREATE OR REPLACE VIEW crude_compass.gold.fx_with_delta AS
SELECT
    date, pair, rate,
    rate - LAG(rate, 1) OVER (PARTITION BY pair ORDER BY date) AS delta_1d,
    rate - LAG(rate, 7) OVER (PARTITION BY pair ORDER BY date) AS delta_7d,
    ROUND(
        STDDEV_SAMP(rate) OVER (
            PARTITION BY pair ORDER BY date
            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        ), 2
    ) AS vol_30d
FROM crude_compass.bronze.fx_rates;

-- ────────────────────────────────────────────────────────────────────
-- V7. news_top_signals — 최근 7일 importance Top 5/day/direction
-- ────────────────────────────────────────────────────────────────────
-- 용도: Discovery "오늘의 발견" 카드, Genie news 질의
CREATE OR REPLACE VIEW crude_compass.gold.news_top_signals AS
SELECT
    DATE(published_at) AS event_date,
    source, tier, title, category, direction,
    importance, raw_tone, mention_count, url
FROM crude_compass.bronze.news_articles
WHERE published_at >= CURRENT_TIMESTAMP() - INTERVAL 7 DAYS
  AND direction IN ('bullish', 'bearish')
  AND importance >= 60
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY DATE(published_at), direction
    ORDER BY importance DESC, mention_count DESC
) <= 5;

-- ────────────────────────────────────────────────────────────────────
-- V8. pattern_score_latest — silver.pattern_scores_daily 최근 30일 + zone
-- ────────────────────────────────────────────────────────────────────
-- 용도: Discovery 첫 화면, Dashboard zone 분포, Genie 추이 질의
CREATE OR REPLACE VIEW crude_compass.gold.pattern_score_latest AS
SELECT
    date,
    pattern_score, bullish_score, bearish_score, cross_val_bonus,
    mission_type, signal_count_90d,
    CASE
        WHEN pattern_score >= 70 THEN 'HEDGE'
        WHEN pattern_score <= 30 THEN 'OPPORTUNITY'
        ELSE 'MID'
    END AS zone
FROM crude_compass.silver.pattern_scores_daily
WHERE date >= CURRENT_DATE() - INTERVAL 30 DAYS;
