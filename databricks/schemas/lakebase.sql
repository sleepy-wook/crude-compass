-- ====================================================================
-- Crude Compass · Lakebase Postgres OLTP
-- ====================================================================
-- 적재: FastAPI (mission CRUD) — Single Source of Truth
-- 실행: psql 또는 backend/scripts/run_lakebase_ddl.py (Sprint 1 day 2)
--
-- 인증: OAuth token (60분 lifetime, runtime 발급)
--   psql 한 번 실행:
--     databricks postgres generate-database-credential \
--         projects/crude-compass-pg/branches/production/endpoints/primary \
--         --profile crude-compass
--     → token 출력 → psql 명령에 paste:
--     psql "postgresql://hyeongwook.lee%40lginnotek.com@<host>/databricks_postgres?sslmode=require" \
--          -f databricks/schemas/lakebase.sql
-- ====================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- gen_random_uuid()

-- ────────────────────────────────────────────────────────────────────
-- 1. missions  ⭐ Single Source of Truth
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
-- Smoke test query (Sprint 1 day 2 검증용)
-- ────────────────────────────────────────────────────────────────────
-- SELECT
--   gen_random_uuid()                                AS test_uuid,
--   '{"Brent_130": 320}'::jsonb                       AS test_jsonb,
--   pg_typeof(NOW())                                  AS test_timestamptz;
