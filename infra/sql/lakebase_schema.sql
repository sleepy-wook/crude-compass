-- ============================================================
-- Crude Compass — Lakebase Postgres Schema
-- Target: Databricks Lakebase Autoscaling Postgres (instance: crude-compass-pg)
-- 사용자 적용 (workspace UI 또는 psql):
--   1) Lakebase 인스턴스 'crude-compass-pg' 생성
--   2) database 'crude_compass' 생성
--   3) 이 파일을 psql로 실행 (SP 자격으로 OAuth 토큰 발급 후)
-- ============================================================

-- 외래키·UUID·JSONB 위해 필요
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ------------------------------------------------------------
-- missions: 4주 living mission state (Wow 1)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS missions (
  mission_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  goal              TEXT        NOT NULL,
  start_date        DATE        NOT NULL,
  current_day       INT         NOT NULL DEFAULT 1,
  target_day        INT         NOT NULL DEFAULT 28,
  status            TEXT        NOT NULL DEFAULT 'active'
                              CHECK (status IN ('active','completed','paused','cancelled')),
  baseline_term_pct NUMERIC(5,2) NOT NULL DEFAULT 50.00,
  target_term_pct   NUMERIC(5,2) NOT NULL,
  current_term_pct  NUMERIC(5,2) NOT NULL,
  manager_id        TEXT        NOT NULL,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_missions_status ON missions(status);
CREATE INDEX IF NOT EXISTS idx_missions_manager ON missions(manager_id);

-- ------------------------------------------------------------
-- mission_events: AI 자율 행동 + 매니저 승인 timeline
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mission_events (
  event_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  mission_id  UUID        NOT NULL REFERENCES missions(mission_id) ON DELETE CASCADE,
  day         INT         NOT NULL,
  actor       TEXT        NOT NULL CHECK (actor IN ('ai','manager')),
  action_type TEXT        NOT NULL,    -- e.g. 'rfq_send','term_lock','manager_approve'
  title       TEXT        NOT NULL,
  detail      TEXT,
  payload     JSONB,                   -- 구조화된 데이터 (RFQ 견적, lock 수량, 가격 등)
  outcome     JSONB,                   -- 7일 후 자동 outcome 측정 결과
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_mission_day ON mission_events(mission_id, day);
CREATE INDEX IF NOT EXISTS idx_events_actor      ON mission_events(actor);
CREATE INDEX IF NOT EXISTS idx_events_payload    ON mission_events USING GIN (payload);

-- ------------------------------------------------------------
-- rfq_negotiations: 4사 Frame Contract 자동 RFQ chaining (Wow 2)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rfq_negotiations (
  rfq_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  mission_id       UUID        NOT NULL REFERENCES missions(mission_id) ON DELETE CASCADE,
  counterparty     TEXT        NOT NULL,    -- 'Aramco','ADNOC','BP','TotalEnergies'
  request_payload  JSONB       NOT NULL,    -- 수량·기간·기준원유·약정조건
  response_payload JSONB,                   -- 견적 답변 (가격·약관)
  status           TEXT        NOT NULL DEFAULT 'sent'
                              CHECK (status IN ('sent','received','accepted','rejected','expired')),
  price_offered    NUMERIC(10,4),           -- USD/bbl
  price_basis      TEXT,                    -- 'Dubai+OSP', 'Brent-X' 등
  volume_bbl       NUMERIC(14,2),
  ai_fit_score     INT,                     -- 0~100, AI 적합도
  ai_recommended   BOOLEAN     NOT NULL DEFAULT FALSE,
  sent_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  responded_at     TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_rfq_mission ON rfq_negotiations(mission_id);
CREATE INDEX IF NOT EXISTS idx_rfq_status  ON rfq_negotiations(status);

-- ------------------------------------------------------------
-- decisions: 매니저 의사결정 audit trail + outcome 회고
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS decisions (
  decision_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       TEXT        NOT NULL,
  decision_type TEXT        NOT NULL
                          CHECK (decision_type IN ('discovery_swipe','mission_confirm','rfq_accept','genie_query')),
  context       JSONB       NOT NULL,    -- AI가 제공한 정보 (risk score, 권고, 시뮬 결과)
  ai_recommend  JSONB,                   -- AI 권고 (Term +Xpt 등)
  user_choice   JSONB,                   -- 매니저 실제 선택
  decided_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  outcome_at    TIMESTAMPTZ,             -- 7일 후 자동 측정 시점
  outcome       JSONB,                   -- ROI 실측, AI 권고와 일치 여부
  outcome_30d   JSONB                    -- 30일 후 측정 (장기 outcome)
);

CREATE INDEX IF NOT EXISTS idx_decisions_user ON decisions(user_id);
CREATE INDEX IF NOT EXISTS idx_decisions_type ON decisions(decision_type);
CREATE INDEX IF NOT EXISTS idx_decisions_outcome_pending
    ON decisions(decided_at) WHERE outcome IS NULL;

-- ============================================================
-- updated_at 자동 갱신 trigger (missions)
-- ============================================================
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS missions_set_updated_at ON missions;
CREATE TRIGGER missions_set_updated_at
  BEFORE UPDATE ON missions
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- 데모용 seed: 진행 중 mission 1건 (D+18 — design page-mission.jsx와 일치)
-- ============================================================
INSERT INTO missions (
  mission_id, goal, start_date, current_day, target_day, status,
  baseline_term_pct, target_term_pct, current_term_pct, manager_id
) VALUES (
  '00000000-0000-0000-0000-000000000001',
  'Term 50% → 70% (Hormuz 봉쇄 헤지)',
  '2026-04-19', 18, 28, 'active',
  50.00, 70.00, 65.00, 'kim.jihoon'
) ON CONFLICT (mission_id) DO NOTHING;

-- 4사 RFQ 시드 (CardC4·Mission FrameContract 패널)
INSERT INTO rfq_negotiations (
  mission_id, counterparty, request_payload, response_payload,
  status, price_offered, price_basis, volume_bbl, ai_fit_score, ai_recommended,
  sent_at, responded_at
) VALUES
  ('00000000-0000-0000-0000-000000000001', 'Aramco',
   '{"volume_bbl":1200000,"basis":"Dubai+OSP","term_months":12}'::jsonb,
   '{"price_basis":"Dubai+$2.10","terms":"12mo TPP"}'::jsonb,
   'accepted', 2.10, 'Dubai+$2.10', 1200000, 92, TRUE,
   NOW() - INTERVAL '5 days', NOW() - INTERVAL '4 days'),
  ('00000000-0000-0000-0000-000000000001', 'ADNOC',
   '{"volume_bbl":800000,"basis":"Dubai+OSP","term_months":6}'::jsonb,
   '{"price_basis":"Dubai+$1.90","terms":"6mo FOB"}'::jsonb,
   'accepted', 1.90, 'Dubai+$1.90', 800000, 88, TRUE,
   NOW() - INTERVAL '5 days', NOW() - INTERVAL '4 days'),
  ('00000000-0000-0000-0000-000000000001', 'BP',
   '{"volume_bbl":500000,"basis":"Brent","term_months":3}'::jsonb,
   '{"price_basis":"Brent-$0.40","terms":"3mo CFR"}'::jsonb,
   'received', -0.40, 'Brent-$0.40', 500000, 71, FALSE,
   NOW() - INTERVAL '3 days', NOW() - INTERVAL '2 days'),
  ('00000000-0000-0000-0000-000000000001', 'TotalEnergies',
   '{"volume_bbl":600000,"basis":"Dubai+OSP","term_months":12}'::jsonb,
   '{"price_basis":"Dubai+$2.60","terms":"12mo CFR"}'::jsonb,
   'sent', 2.60, 'Dubai+$2.60', 600000, 64, FALSE,
   NOW() - INTERVAL '2 days', NULL)
ON CONFLICT DO NOTHING;
