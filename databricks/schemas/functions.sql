-- ====================================================================
-- Crude Compass · UC Functions
-- ====================================================================
-- 시나리오 §9.5 — Genie + Mission Plan + curation/backtest 공통 호출용.
-- ====================================================================

CREATE SCHEMA IF NOT EXISTS crude_compass.functions;

-- ────────────────────────────────────────────────────────────────────
-- weighted_signal — 시간 감쇠 (시나리오 §6.2 람다 차등)
-- ────────────────────────────────────────────────────────────────────
-- 사용 예:
--   SELECT crude_compass.functions.weighted_signal(80.0, 30, 'news_tone', 1.0)
--   → 80 × exp(-0.046 × 30) × 1.0 = ~20.1 (반감기 15일이라 30일은 1/4 영향)
--
-- 반감기:
--   news_tone, price_spike: 15일 (λ = 0.046)
--   ais_traffic, fx_krw_usd: 30일 (λ = 0.023)
--   eia_inventory, opec_momr: 60일 (λ = 0.012)

CREATE OR REPLACE FUNCTION crude_compass.functions.weighted_signal(
    raw_intensity DOUBLE,
    days_ago INT,
    signal_type STRING,
    source_credibility DOUBLE
)
RETURNS DOUBLE
COMMENT '시나리오 §6.2 시간 감쇠 — 시그널별 람다 차등 적용'
RETURN
    raw_intensity
    * CASE signal_type
        WHEN 'news_tone'      THEN exp(-0.046 * days_ago)
        WHEN 'ais_traffic'    THEN exp(-0.023 * days_ago)
        WHEN 'eia_inventory'  THEN exp(-0.012 * days_ago)
        WHEN 'opec_momr'      THEN exp(-0.012 * days_ago)
        WHEN 'fx_krw_usd'     THEN exp(-0.023 * days_ago)
        WHEN 'price_spike'    THEN exp(-0.046 * days_ago)
        ELSE                       exp(-0.023 * days_ago)
      END
    * source_credibility;
