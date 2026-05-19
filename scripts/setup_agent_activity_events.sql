-- ────────────────────────────────────────────────────────────────────
-- Lakebase Postgres: agent_activity_events table 수동 setup
-- ────────────────────────────────────────────────────────────────────
-- Apps SP는 missions table owner가 아니라 ALTER/CREATE TABLE을 못함.
-- 이 SQL을 Databricks SQL Editor에서 형욱님 user (admin)로 한 번 실행.
-- 그 후 GRANT로 SP가 INSERT/SELECT 가능하게 됨.
--
-- 멱등 (IF NOT EXISTS) — 여러 번 실행해도 안전.
-- ────────────────────────────────────────────────────────────────────

-- 1. Table 생성 (id = UUID, gen_random_uuid()는 pgcrypto 활성화돼 있음)
CREATE TABLE IF NOT EXISTS agent_activity_events (
    id             UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    mission_id     UUID,
    occurred_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor          VARCHAR(64) NOT NULL,
    action         VARCHAR(64) NOT NULL,
    result_preview TEXT,
    metadata       JSONB
);

CREATE INDEX IF NOT EXISTS idx_agent_activity_mission
    ON agent_activity_events(mission_id, occurred_at DESC);

-- 2. SP 권한 — PUBLIC에 grant (모든 role에 INSERT/SELECT 허용, 데모 단순화)
GRANT SELECT, INSERT ON agent_activity_events TO PUBLIC;

-- 3. Backfill — 기존 missions의 누락 event 채우기 (NOT EXISTS guard, idempotent)

-- 3.1 weighted_signal_uc:score_computed
INSERT INTO agent_activity_events (mission_id, occurred_at, actor, action, result_preview, metadata)
SELECT
    m.mission_id,
    m.created_at - interval '15 seconds',
    'weighted_signal_uc',
    'score_computed',
    '양방향 가중 Pattern Score ' || ROUND(m.pattern_score) || ' 계산 (90일 window)',
    jsonb_build_object('pattern_score', m.pattern_score, 'urgency', m.urgency)
FROM missions m
WHERE NOT EXISTS (
    SELECT 1 FROM agent_activity_events e
     WHERE e.mission_id = m.mission_id
       AND e.actor = 'weighted_signal_uc'
       AND e.action = 'score_computed'
);

-- 3.2 supervisor:case_opened
INSERT INTO agent_activity_events (mission_id, occurred_at, actor, action, result_preview, metadata)
SELECT
    m.mission_id,
    m.created_at - interval '10 seconds',
    'supervisor',
    'case_opened',
    (CASE WHEN m.mission_type = 'HEDGE' THEN '위험방어' ELSE '기회포착' END)
    || ' case 개시 — Pattern Score ' || ROUND(m.pattern_score)
    || ', 긴급도 ' || m.urgency,
    jsonb_build_object('mission_type', m.mission_type, 'urgency', m.urgency)
FROM missions m
WHERE NOT EXISTS (
    SELECT 1 FROM agent_activity_events e
     WHERE e.mission_id = m.mission_id
       AND e.actor = 'supervisor'
       AND e.action = 'case_opened'
);

-- 3.3 mission_plan_fma:draft_generated
INSERT INTO agent_activity_events (mission_id, occurred_at, actor, action, result_preview, metadata)
SELECT
    m.mission_id,
    m.created_at - interval '5 seconds',
    'mission_plan_fma',
    'draft_generated',
    (CASE WHEN m.mission_type = 'HEDGE' THEN '위험방어' ELSE '기회포착' END)
    || ' 권고 — ' || COALESCE(m.target_pct::text, '?') || '% / '
    || COALESCE(m.duration_days::text, '?') || '일',
    jsonb_build_object('target_pct', m.target_pct, 'duration_days', m.duration_days)
FROM missions m
WHERE NOT EXISTS (
    SELECT 1 FROM agent_activity_events e
     WHERE e.mission_id = m.mission_id
       AND e.actor = 'mission_plan_fma'
       AND e.action = 'draft_generated'
);

-- 3.4 manager:confirmed (confirmed_at가 있는 mission)
INSERT INTO agent_activity_events (mission_id, occurred_at, actor, action, result_preview, metadata)
SELECT
    m.mission_id,
    m.confirmed_at,
    'manager',
    'confirmed',
    '매니저 승인 (via ' || COALESCE(m.confirmed_via, 'apps') || ')',
    jsonb_build_object('by', COALESCE(m.confirmed_by, 'unknown'), 'via', COALESCE(m.confirmed_via, 'apps'))
FROM missions m
WHERE m.confirmed_at IS NOT NULL
  AND m.status IN ('active', 'on_track', 'at_risk', 'paused', 'pivoted', 'completed')
  AND NOT EXISTS (
      SELECT 1 FROM agent_activity_events e
       WHERE e.mission_id = m.mission_id AND e.actor = 'manager' AND e.action = 'confirmed'
  );

-- 3.5 manager:rejected (aborted mission)
INSERT INTO agent_activity_events (mission_id, occurred_at, actor, action, result_preview, metadata)
SELECT
    m.mission_id,
    m.completed_at,
    'manager',
    'rejected',
    '매니저 기각 (via ' || COALESCE(m.confirmed_via, 'apps') || ')',
    jsonb_build_object('by', COALESCE(m.confirmed_by, 'unknown'), 'via', COALESCE(m.confirmed_via, 'apps'))
FROM missions m
WHERE m.completed_at IS NOT NULL
  AND m.status = 'aborted'
  AND NOT EXISTS (
      SELECT 1 FROM agent_activity_events e
       WHERE e.mission_id = m.mission_id AND e.actor = 'manager' AND e.action = 'rejected'
  );

-- 4. 검증
SELECT
    COUNT(*) AS total_events,
    COUNT(DISTINCT mission_id) AS missions_with_events,
    MIN(occurred_at) AS earliest,
    MAX(occurred_at) AS latest
FROM agent_activity_events;

-- 5. (선택) Mission별 event 확인
SELECT actor, action, COUNT(*) AS n
FROM agent_activity_events
GROUP BY actor, action
ORDER BY n DESC;
