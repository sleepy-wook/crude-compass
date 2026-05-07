-- ============================================================
-- Crude Compass — Unity Catalog Bronze Delta DDL
-- Target: Databricks Unity Catalog
--   catalog: crude_compass
--   schema:  bronze
-- 사용자 적용 (workspace UI 또는 SQL editor):
--   1) UC catalog 'crude_compass' 생성
--   2) schema 'bronze' 생성
--   3) 이 파일을 SQL editor에서 실행
-- ============================================================

-- 6 tables. KNOC 제거 (push back 반영, 2026-05-08).

-- ------------------------------------------------------------
-- bronze.oil_prices — OilPriceAPI 5분 갱신 (Tier 2)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS crude_compass.bronze.oil_prices (
  fetched_at  TIMESTAMP    NOT NULL,
  source      STRING       NOT NULL COMMENT 'oilpriceapi',
  product     STRING       NOT NULL COMMENT 'WTI_USD | BRENT_CRUDE_USD | DUBAI_CRUDE_USD',
  price_usd   DOUBLE       NOT NULL,
  raw         STRING                COMMENT 'JSON 원본'
) USING DELTA
PARTITIONED BY (DATE(fetched_at))
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
);

-- ------------------------------------------------------------
-- bronze.ais_positions — aisstream WebSocket continuous (Workflow)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS crude_compass.bronze.ais_positions (
  received_at   TIMESTAMP    NOT NULL,
  mmsi          BIGINT       NOT NULL,
  ship_name     STRING,
  ship_type     STRING,
  flag          STRING,
  latitude      DOUBLE       NOT NULL,
  longitude     DOUBLE       NOT NULL,
  sog           DOUBLE                COMMENT 'speed over ground (knots)',
  cog           DOUBLE                COMMENT 'course over ground',
  destination   STRING,
  message_type  STRING                COMMENT 'PositionReport | ShipStaticData',
  raw           STRING                COMMENT 'JSON 원본'
) USING DELTA
PARTITIONED BY (DATE(received_at))
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
);

-- ------------------------------------------------------------
-- bronze.gdacs_events — REST 1시간 (Tier 1)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS crude_compass.bronze.gdacs_events (
  fetched_at  TIMESTAMP    NOT NULL,
  event_id    STRING       NOT NULL,
  event_type  STRING       NOT NULL COMMENT 'TC | EQ | FL | VO | WF | DR',
  name        STRING,
  country     STRING,
  event_date  DATE,
  severity    STRING                COMMENT 'Green | Orange | Red',
  latitude    DOUBLE,
  longitude   DOUBLE,
  raw         STRING                COMMENT 'JSON 원본'
) USING DELTA
TBLPROPERTIES ('delta.autoOptimize.optimizeWrite' = 'true');

-- ------------------------------------------------------------
-- bronze.exchange_rates — ECOS 일별 (Tier 1)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS crude_compass.bronze.exchange_rates (
  fetched_at  TIMESTAMP    NOT NULL,
  trade_date  DATE         NOT NULL,
  pair        STRING       NOT NULL COMMENT 'KRW/USD',
  rate        DOUBLE       NOT NULL,
  raw         STRING                COMMENT 'JSON 원본'
) USING DELTA;

-- ------------------------------------------------------------
-- bronze.news_articles — RSS 5분 (Tier 2)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS crude_compass.bronze.news_articles (
  fetched_at    TIMESTAMP    NOT NULL,
  source        STRING       NOT NULL COMMENT 'reuters | ap | yna | ft | bbc',
  url           STRING       NOT NULL,
  title         STRING       NOT NULL,
  description   STRING,
  published_at  TIMESTAMP,
  keyword_match STRING                COMMENT 'comma-separated matched keywords',
  raw           STRING                COMMENT 'JSON 원본'
) USING DELTA
PARTITIONED BY (DATE(fetched_at));

-- ------------------------------------------------------------
-- bronze.jwc_zones — Lloyd's JWC War zone PDF (수동 1회)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS crude_compass.bronze.jwc_zones (
  fetched_at      TIMESTAMP    NOT NULL,
  zone_name       STRING       NOT NULL,
  zone_type       STRING                COMMENT 'war_listed | enhanced',
  geometry_wkt    STRING                COMMENT 'WKT polygon',
  effective_date  DATE,
  raw             STRING
) USING DELTA;

-- ============================================================
-- silver / gold schemas (Phase 1 Part C에서 정의)
-- ============================================================
-- crude_compass.silver.* — 정제·통합·중복제거
-- crude_compass.gold.risk_indicators — 4종 input 종합 risk score 시계열
-- crude_compass.gold.prewarmed_scenarios — Genie fallback용 자주 묻는 시나리오 결과 (nightly 배치)
