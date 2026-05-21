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

    -- Sub-A (D-4) actionable recommendations: cycle label + supplier mix
    cycle                 TEXT,
    supplier_mix          JSONB    NOT NULL DEFAULT '[]'::jsonb,
    -- Sub-B (D-4) honest simulation: Best/Likely/Worst 3 scenarios with assumptions
    simulation_scenarios  JSONB    NOT NULL DEFAULT '[]'::jsonb,

    CONSTRAINT chk_mission_type CHECK (mission_type IN ('HEDGE', 'OPPORTUNITY')),
    CONSTRAINT chk_status CHECK (status IN (
        'proposed', 'active', 'on_track', 'at_risk',
        'paused', 'pivoted', 'aborted', 'completed'
    )),
    CONSTRAINT chk_urgency CHECK (urgency IN ('optional', 'default', 'urgent')),
    CONSTRAINT chk_confirmed_via CHECK (confirmed_via IS NULL OR confirmed_via IN ('slack', 'apps'))
);

-- Migration (D-4) — idempotent ALTER for existing production tables.
-- Apps lifespan startup이 이걸 자동 실행 (db/lakebase.py migrate_missions_d4).
ALTER TABLE missions ADD COLUMN IF NOT EXISTS cycle TEXT;
ALTER TABLE missions ADD COLUMN IF NOT EXISTS supplier_mix JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE missions ADD COLUMN IF NOT EXISTS simulation_scenarios JSONB NOT NULL DEFAULT '[]'::jsonb;

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
-- 5. backtest_predictions — LLM backtest output (AI-generated → OLTP)
-- ────────────────────────────────────────────────────────────────────
-- Read: market memory (find_similar_patterns) — Investigation/의사결정 "비슷한 시그널" 참고.
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
-- 6. reports — Event-driven AI report inbox (2026-05-21 reports model)
-- ────────────────────────────────────────────────────────────────────
-- Replaces `missions` for daily AI workflow. missions table은 backtest용 read-only로 유지.
-- 매 trigger (gdelt_signal / price_spike / pattern_drift)마다 1 row 생성.
-- status flow: pending → kept | dropped | ai_dropped
--   keep:        manager만 (UI/Slack click)
--   drop:        manager (UI/Slack click)
--   ai_drop:     AI가 stale 판정시 (Phase 9)
-- thread:       parent_id 로 연결 (continuation report)
-- revisit:      revisits_id 로 과거 archive 참조 (재발 시그널)
CREATE TABLE IF NOT EXISTS reports (
    report_id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_id          UUID         REFERENCES reports(report_id),

    trigger_type       TEXT         NOT NULL,
    trigger_meta       JSONB        NOT NULL DEFAULT '{}'::jsonb,

    status             TEXT         NOT NULL DEFAULT 'pending',
    status_changed_at  TIMESTAMPTZ,
    status_changed_by  TEXT,

    headline           TEXT         NOT NULL,
    summary            TEXT         NOT NULL,
    reasoning          JSONB        NOT NULL DEFAULT '{}'::jsonb,
    recommendation     TEXT,
    related_signals    JSONB        NOT NULL DEFAULT '[]'::jsonb,

    revisits_id        UUID         REFERENCES reports(report_id),
    ai_drop_reason     TEXT,

    version            INT          NOT NULL DEFAULT 1,
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_trigger CHECK (trigger_type IN ('gdelt_signal', 'price_spike', 'pattern_drift')),
    CONSTRAINT chk_status  CHECK (status IN ('pending', 'kept', 'dropped', 'ai_dropped', 'archived')),
    CONSTRAINT chk_changed_by CHECK (status_changed_by IS NULL OR status_changed_by IN ('manager', 'ai'))
);

CREATE INDEX IF NOT EXISTS idx_reports_status_created
    ON reports (status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_reports_parent
    ON reports (parent_id, created_at);

-- pending inbox 빠른 lookup (보통 < 10 rows 유지)
CREATE INDEX IF NOT EXISTS idx_reports_pending
    ON reports (created_at DESC) WHERE status = 'pending';

-- ────────────────────────────────────────────────────────────────────
-- 7. daily_reports — 매일 06:30 KST cron 종합 보고서 + 비중 제안
-- ────────────────────────────────────────────────────────────────────
-- input: 어제 kept reports + 어제 daily_report
-- output: 시장 종합 + ratio_suggestion (reference only — 실제 OSP 결재는 매니저)
-- report_date UNIQUE — 하루 1 row guarantee. 재생성 시 manual DELETE 필요.
CREATE TABLE IF NOT EXISTS daily_reports (
    daily_id           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    report_date        DATE         UNIQUE NOT NULL,
    prev_daily_id      UUID         REFERENCES daily_reports(daily_id),

    kept_report_ids    UUID[]       NOT NULL DEFAULT ARRAY[]::uuid[],
    kept_count         INT          NOT NULL DEFAULT 0,
    kept_summary       TEXT,
    prev_daily_summary TEXT,
    market_context     TEXT,

    ratio_suggestion   JSONB        NOT NULL DEFAULT '{}'::jsonb,
    reasoning          TEXT,
    confidence         NUMERIC(5,2),

    created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_daily_reports_date
    ON daily_reports (report_date DESC);

-- ────────────────────────────────────────────────────────────────────
-- Smoke test (DDL apply 후 dialect 검증)
-- ────────────────────────────────────────────────────────────────────
-- SELECT gen_random_uuid(), '{"k": 1}'::jsonb, pg_typeof(NOW());
