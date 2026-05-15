-- ====================================================================
-- Crude Compass · Bronze layer (Delta, append-only)
-- ====================================================================
-- 적재: Lakeflow Jobs (gdelt / price / ais / ecos / eia / opec / oil_prices_daily)
-- 보존: 90일 (Pattern Detection window)
-- ====================================================================

CREATE CATALOG IF NOT EXISTS crude_compass;
CREATE SCHEMA  IF NOT EXISTS crude_compass.bronze;

-- ────────────────────────────────────────────────────────────────────
-- 1. news_articles — GDELT + RSS (gdelt_detect + gdelt_backtest source_type)
-- ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS crude_compass.bronze.news_articles (
    article_id      STRING        NOT NULL COMMENT 'SHA256(url) or GDELT artid',
    source          STRING        NOT NULL COMMENT 'GDELT | Reuters | Yonhap | EIA | ...',
    source_type     STRING        NOT NULL COMMENT 'gdelt_detect | rss_enrich (시나리오 §7 감지층/보강층)',
    tier            STRING        NOT NULL COMMENT 'A | B',
    published_at    TIMESTAMP     NOT NULL,
    fetched_at      TIMESTAMP     NOT NULL,
    url             STRING        NOT NULL,
    title           STRING        NOT NULL,
    body            STRING,
    body_lang       STRING        COMMENT 'ko | en',

    -- GDELT timelinetone output
    raw_tone        DECIMAL(5, 2) COMMENT 'GDELT tone score, range -10 ~ 10',
    mention_count   INT           COMMENT 'GDELT mention count (기간 내)',

    -- LLM scoring (Foundation Model API · Claude Haiku 4.5)
    importance      INT           NOT NULL COMMENT '0-100',
    category        STRING        NOT NULL COMMENT 'geopolitical|policy|disaster|market|supply|demand',
    direction       STRING        NOT NULL COMMENT 'bullish|bearish|neutral (양방향 핵심)',
    horizon         STRING        NOT NULL COMMENT 'short|medium|long',
    confidence      STRING        NOT NULL COMMENT 'low|med|high',
    entities        ARRAY<STRING> COMMENT '[IRGC, OPEC, ...]',

    job_run_id      STRING,
    llm_model       STRING        COMMENT 'databricks-claude-haiku-4-5'
)
USING DELTA
PARTITIONED BY (DATE(published_at))
TBLPROPERTIES (
    delta.autoOptimize.optimizeWrite = true,
    delta.autoOptimize.autoCompact   = true
);

-- ────────────────────────────────────────────────────────────────────
-- 2. oil_prices  (realtime — OilPriceAPI 1-min stream)
-- ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS crude_compass.bronze.oil_prices (
    fetched_at      TIMESTAMP     NOT NULL,
    ticker          STRING        NOT NULL COMMENT 'BRENT | WTI | DUBAI',
    price_usd       DECIMAL(8, 2) NOT NULL,
    delta_pct_5min  DECIMAL(5, 2) COMMENT 'spike detection',
    source          STRING        NOT NULL COMMENT 'OilPriceAPI',
    raw_response    STRING        COMMENT 'JSON for audit'
)
USING DELTA
PARTITIONED BY (DATE(fetched_at))
CLUSTER BY (ticker, fetched_at);

-- ────────────────────────────────────────────────────────────────────
-- 2-b. oil_prices_daily — KNOC OPINET daily close (Dubai 중심)
-- ────────────────────────────────────────────────────────────────────
-- 한국 정유사 baseline = Dubai (중동 원유 70%+ 수입). 1996~ daily.
-- 적재: job_oil_prices_daily.py (daily | historical mode).
CREATE TABLE IF NOT EXISTS crude_compass.bronze.oil_prices_daily (
    trade_date      DATE          NOT NULL COMMENT 'KNOC 공시 거래일',
    ticker          STRING        NOT NULL COMMENT 'DUBAI | BRENT | WTI',
    price_usd       DECIMAL(8, 2) NOT NULL COMMENT 'USD/bbl close',
    fetched_at      TIMESTAMP     NOT NULL,
    source          STRING        NOT NULL COMMENT 'OPINET KNOC — 한국석유공사 CSV download'
)
USING DELTA
CLUSTER BY (ticker, trade_date);

-- ────────────────────────────────────────────────────────────────────
-- 3. ais_positions  (5분 batch — continuous WebSocket 대체)
-- ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS crude_compass.bronze.ais_positions (
    fetched_at      TIMESTAMP     NOT NULL,
    mmsi            STRING        NOT NULL COMMENT '가명 (K-Petroleum 5척)',
    vessel_name     STRING        COMMENT 'VLCC #001 가명',
    lat             DOUBLE        NOT NULL,
    lon             DOUBLE        NOT NULL,
    speed_knots     DECIMAL(4, 1),
    heading_deg     INT,
    in_hormuz_bbox  BOOLEAN       COMMENT '호르무즈 bounding box',
    status          STRING        COMMENT 'transit | stranded | anchored | safe'
)
USING DELTA
PARTITIONED BY (DATE(fetched_at));

-- ────────────────────────────────────────────────────────────────────
-- 4. fx_rates
-- ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS crude_compass.bronze.fx_rates (
    date            DATE          NOT NULL,
    pair            STRING        NOT NULL COMMENT 'USD/KRW',
    rate            DECIMAL(8, 2) NOT NULL,
    source          STRING        NOT NULL COMMENT 'ECOS'
)
USING DELTA
PARTITIONED BY (date);

-- ────────────────────────────────────────────────────────────────────
-- 5. eia_inventory — EIA Open Data API (weekly crude stocks)
-- ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS crude_compass.bronze.eia_inventory (
    week_ending       DATE          NOT NULL COMMENT '주간 보고서 종료일 (수요일 직전 금요일)',
    series_id         STRING        NOT NULL COMMENT 'EIA series identifier',
    inventory_type    STRING        NOT NULL COMMENT 'commercial | spr | total',
    value_kbbl        DECIMAL(12, 2) NOT NULL COMMENT 'thousand barrels',
    delta_vs_prev_wk  DECIMAL(10, 2) COMMENT 'WoW 변화량 (시그널 강도)',
    fetched_at        TIMESTAMP     NOT NULL,
    source            STRING        NOT NULL DEFAULT 'EIA Open Data API'
)
USING DELTA
PARTITIONED BY (week_ending);

-- ────────────────────────────────────────────────────────────────────
-- 6. opec_momr_parsed — Document Intelligence (시나리오 §9.6)
-- ────────────────────────────────────────────────────────────────────
-- ai_parse_document() 결과 적재. OPEC MOMR PDF monthly cron.
CREATE TABLE IF NOT EXISTS crude_compass.bronze.opec_momr_parsed (
    report_month      STRING        NOT NULL COMMENT 'YYYY-MM (예: 2026-04)',
    pdf_volume_path   STRING        NOT NULL COMMENT '/Volumes/crude_compass/bronze/opec_pdfs/...',
    parsed_at         TIMESTAMP     NOT NULL,

    -- ai_parse_document output
    parsed_content    STRING        COMMENT 'Full text content',
    pages             ARRAY<STRUCT<page_num INT, content STRING>> COMMENT 'Page-level structure',
    tables            ARRAY<STRING> COMMENT 'Extracted tables (JSON)',

    -- LLM extraction (job_opec_momr.py)
    saudi_production_kbbl_d  DECIMAL(10, 2),
    iran_production_kbbl_d   DECIMAL(10, 2),
    opec_total_kbbl_d        DECIMAL(10, 2),
    forecast_demand_kbbl_d   DECIMAL(10, 2),

    extraction_model  STRING        COMMENT 'databricks-claude-haiku-4-5'
)
USING DELTA;
