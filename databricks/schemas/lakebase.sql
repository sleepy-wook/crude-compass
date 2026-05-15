-- ====================================================================
-- Crude Compass · Lakebase Postgres OLTP
-- ====================================================================
-- 적재: FastAPI (mission CRUD) + job_backtest_llm (predictions).
-- 인증: OAuth token (60분 lifetime, runtime 발급 via databricks SDK).
-- 실행 (DDL apply):
--   databricks postgres generate-database-credential \
--       projects/crude-compass-pg/branches/production/endpoints/primary \
--       --profile crude-compass
--   psql "postgresql://<user>@<host>/databricks_postgres?sslmode=require" \
--        -f databricks/schemas/lakebase.sql
-- ====================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- gen_random_uuid()

-- ────────────────────────────────────────────────────────────────────
-- 1. missions — Single Source of Truth (양방향 sync 핵심)
-- ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS missions (
    mission_id        UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    mission_type      VARCHAR(20)  NOT NULL,
    status            VARCHAR(20)  NOT NULL DEFAULT 'proposed',
    goal_text         TEXT         NOT NULL,
    pattern_score     NUMERIC(5,2) NOT NULL,
    reasoning         TEXT         NOT NULL,
    simulation_roi    JSONB        NOT NULL,
    urgency           VARCHAR(10)  NOT NULL DEFAULT 'default',
    target_pct        INT,
    duration_days     INT          NOT NULL DEFAULT 28,

    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    confirmed_at      TIMESTAMPTZ,
    confirmed_by      VARCHAR(100),
    confirmed_via     VARCHAR(20),
    completed_at      TIMESTAMPTZ,

    pivot_history     JSONB        NOT NULL DEFAULT '[]'::jsonb,
    version           INT          NOT NULL DEFAULT 1,
    last_event_id     BIGINT,

    CONSTRAINT chk_mission_type CHECK (mission_type IN ('HEDGE', 'OPPORTUNITY')),
    CONSTRAINT chk_status CHECK (status IN (
        'proposed', 'active', 'on_track', 'at_risk',
        'paused', 'pivoted', 'aborted', 'completed'
    )),
    CONSTRAINT chk_urgency CHECK (urgency IN ('optional', 'default', 'urgent')),
    CONSTRAINT chk_confirmed_via CHECK (confirmed_via IS NULL OR confirmed_via IN ('slack', 'apps'))
);

CREATE INDEX IF NOT EXISTS idx_missions_status_created
    ON missions (status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_missions_type_active
    ON missions (mission_type)
    WHERE status IN ('active', 'on_track', 'at_risk');

-- WS replay 용 sequence
CREATE SEQUENCE IF NOT EXISTS missions_event_seq START 1;

-- ────────────────────────────────────────────────────────────────────
-- 2. decisions  (audit log)
-- ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS decisions (
    decision_id       UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    mission_id        UUID         NOT NULL REFERENCES missions(mission_id) ON DELETE CASCADE,
    action            VARCHAR(20)  NOT NULL,
    actor             VARCHAR(100) NOT NULL,
    via               VARCHAR(20)  NOT NULL,
    payload           JSONB        NOT NULL DEFAULT '{}'::jsonb,
    occurred_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    request_id        UUID,

    CONSTRAINT chk_action CHECK (action IN (
        'confirm', 'reject', 'modify', 'pivot', 'pause', 'abort'
    )),
    CONSTRAINT chk_via CHECK (via IN ('slack', 'apps', 'api'))
);

CREATE INDEX IF NOT EXISTS idx_decisions_mission
    ON decisions (mission_id, occurred_at DESC);

-- ────────────────────────────────────────────────────────────────────
-- 3. pivot_history
-- ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS pivot_history (
    pivot_id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    mission_id        UUID         NOT NULL REFERENCES missions(mission_id) ON DELETE CASCADE,
    from_type         VARCHAR(20)  NOT NULL,
    to_type           VARCHAR(20)  NOT NULL,
    pivot_action      VARCHAR(20)  NOT NULL,
    reason            TEXT         NOT NULL,
    pattern_score_at  NUMERIC(5,2) NOT NULL,
    occurred_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_pivot_action CHECK (pivot_action IN ('pivot', 'pause', 'abort', 'continue'))
);

-- ────────────────────────────────────────────────────────────────────
-- 4. discovery_feed_items
-- ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS discovery_feed_items (
    item_id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    feed_date          DATE         NOT NULL,
    item_type          VARCHAR(30)  NOT NULL,
    title              TEXT         NOT NULL,
    body               TEXT,
    related_mission_id UUID         REFERENCES missions(mission_id) ON DELETE SET NULL,
    metadata           JSONB        NOT NULL DEFAULT '{}'::jsonb,
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    dismissed_at       TIMESTAMPTZ,

    CONSTRAINT chk_item_type CHECK (item_type IN (
        'mission_proposal', 'reactive', 'osp', 'mission_checkpoint'
    ))
);

CREATE INDEX IF NOT EXISTS idx_discovery_date
    ON discovery_feed_items (feed_date DESC);

-- ────────────────────────────────────────────────────────────────────
-- 5. backtest_predictions — LLM backtest output (AI-generated → OLTP)
-- ────────────────────────────────────────────────────────────────────
-- Read: WhatIf 페이지 300 rows fetch (ms latency).
-- Write: job_backtest_llm batch (1 run = ~300 INSERT via psycopg executemany).
CREATE TABLE IF NOT EXISTS backtest_predictions (
    id                BIGSERIAL    PRIMARY KEY,
    run_id            VARCHAR(80)  NOT NULL,
    as_of_date        DATE         NOT NULL,
    zone              VARCHAR(10),
    pattern_score     NUMERIC(5,2),
    confidence_score  NUMERIC(5,2),
    action_type       VARCHAR(20),
    mission_type      VARCHAR(20),
    target_pct        INT,
    duration_days     INT,
    saving_7d_pct     NUMERIC(8,4),
    saving_30d_pct    NUMERIC(8,4),
    saving_90d_pct    NUMERIC(8,4),
    dubai_at_signal_usd  NUMERIC(8,2),
    dubai_30d_usd     NUMERIC(8,2),
    dubai_90d_usd     NUMERIC(8,2),
    reasoning         TEXT,
    computed_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_bt_zone CHECK (zone IS NULL OR zone IN ('HIGH', 'MID', 'LOW')),
    CONSTRAINT chk_bt_action CHECK (action_type IS NULL OR action_type IN ('new_mission', 'continue', 'no_action')),
    CONSTRAINT chk_bt_mission_type CHECK (mission_type IS NULL OR mission_type IN ('HEDGE', 'OPPORTUNITY'))
);

CREATE INDEX IF NOT EXISTS idx_backtest_run_date
    ON backtest_predictions (run_id, as_of_date DESC);

CREATE INDEX IF NOT EXISTS idx_backtest_as_of
    ON backtest_predictions (as_of_date DESC);

-- ────────────────────────────────────────────────────────────────────
-- Smoke test (DDL apply 후 dialect 검증)
-- ────────────────────────────────────────────────────────────────────
-- SELECT gen_random_uuid(), '{"k": 1}'::jsonb, pg_typeof(NOW());
