-- ====================================================================
-- Crude Compass · Bronze layer (Delta, append-only)
-- ====================================================================
-- 적재: Lakeflow Jobs (1 news / 2 price / 3 ais batch / 4 ecos)
-- 보존: 90일 (Pattern Detection window 90일이면 충분)
-- 실행: databricks/notebooks/setup_bronze.py 또는 SQL warehouse에서 직접
-- ====================================================================

CREATE CATALOG IF NOT EXISTS crude_compass;
CREATE SCHEMA  IF NOT EXISTS crude_compass.bronze;

-- ────────────────────────────────────────────────────────────────────
-- 1. news_articles  ⭐ Bidirectional Pattern Detection 핵심
-- ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS crude_compass.bronze.news_articles (
    article_id      STRING        NOT NULL COMMENT 'SHA256(url)',
    source          STRING        NOT NULL COMMENT 'Reuters | Yonhap | EIA | ...',
    tier            STRING        NOT NULL COMMENT 'A | B',
    published_at    TIMESTAMP     NOT NULL,
    fetched_at      TIMESTAMP     NOT NULL,
    url             STRING        NOT NULL,
    title           STRING        NOT NULL,
    body            STRING,
    body_lang       STRING        COMMENT 'ko | en',

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
-- 2. oil_prices
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
    status          STRING        COMMENT 'transit | stranded | safe'
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
