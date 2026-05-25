-- ─────────────────────────────────────────────────────────────
-- crude_compass.config — 런타임 설정 (코드 밖으로 뺀 것)
-- ─────────────────────────────────────────────────────────────
-- gdelt_queries: GDELT watchlist. job_gdelt.py가 하드코딩 대신 여기서 읽음.
--   horizon : short(단기·이벤트) / medium / long(장기·구조) — 단기/장기 분리
--   category: geopolitical | policy | supply | demand | broad(광역 catch-all)
--   source  : manual | auto  (auto = 향후 일일 자가 개편(curation)이 추가/회수)
--   active  : false면 job이 스킵
-- 적용: 이 파일 실행(또는 apply_schemas.py). 재실행 시 manual 기준선으로 리셋.
-- (주의: 자가 개편(component 3) 도입 후엔 CREATE OR REPLACE 대신 MERGE로 전환할 것)

CREATE SCHEMA IF NOT EXISTS crude_compass.config;

CREATE OR REPLACE TABLE crude_compass.config.gdelt_queries AS
SELECT
  label, query, tier, horizon, category, baseline,
  default_direction, confidence, active, source,
  current_timestamp() AS updated_at
FROM VALUES
  -- 단기(short) — 즉발 이벤트
  ('hormuz',              'Strait of Hormuz Iran tanker',          'A', 'short',  'geopolitical', 75, 'bullish', 'high', true, 'manual'),
  ('houthi_red_sea',      'Houthi Red Sea tanker attack',          'A', 'short',  'geopolitical', 70, 'bullish', 'high', true, 'manual'),
  ('opec_cut_surprise',   'OPEC production cut surprise',           'A', 'short',  'policy',       65, 'bullish', 'high', true, 'manual'),
  ('eia_inventory',       'EIA crude oil inventory weekly',         'B', 'short',  'supply',       60, 'auto',    'high', true, 'manual'),
  ('us_spr',              'strategic petroleum reserve release',    'A', 'short',  'policy',       60, 'auto',    'high', true, 'manual'),
  -- 중기(medium)
  ('iran_sanctions',      'Iran sanctions oil export',              'A', 'medium', 'policy',       70, 'bullish', 'high', true, 'manual'),
  ('russia_ukraine',      'Russia Ukraine oil sanctions',           'A', 'medium', 'geopolitical', 70, 'bullish', 'high', true, 'manual'),
  ('libya_shutdown',      'Libya oil production shutdown unrest',    'A', 'medium', 'geopolitical', 60, 'bullish', 'med',  true, 'manual'),
  ('venezuela_sanctions', 'Venezuela oil sanctions PdVSA',          'A', 'medium', 'policy',       60, 'bullish', 'high', true, 'manual'),
  ('opec_monthly',        'OPEC monthly oil market report',         'B', 'medium', 'policy',       65, 'auto',    'high', true, 'manual'),
  ('saudi_osp',           'Saudi Aramco OSP official selling price','B', 'medium', 'supply',       65, 'auto',    'high', true, 'manual'),
  ('china_demand',        'China oil demand PMI manufacturing',     'A', 'medium', 'demand',       55, 'auto',    'med',  true, 'manual'),
  ('china_recession',     'China oil demand slowdown recession',    'A', 'medium', 'demand',       60, 'bearish', 'med',  true, 'manual'),
  ('oecd_inventory_build','OECD commercial crude inventory build',  'A', 'medium', 'supply',       60, 'bearish', 'high', true, 'manual'),
  ('saudi_osp_cut',       'Saudi Aramco OSP price cut Asia',        'A', 'medium', 'supply',       65, 'bearish', 'high', true, 'manual'),
  ('us_shale_surge',      'US shale oil production record surge',    'A', 'medium', 'supply',       60, 'bearish', 'high', true, 'manual'),
  -- 장기(long) — 구조적
  ('ev_adoption',         'electric vehicle adoption oil demand peak','B','long',  'demand',       50, 'bearish', 'med',  true, 'manual'),
  -- 광역 catch-all (사전 정의 안 한 새 위기 포착)
  ('oil_broad',           'crude oil supply disruption',            'A', 'short',  'broad',        55, 'auto',    'med',  true, 'manual'),
  ('oil_shock',           'oil price shock geopolitics',            'A', 'short',  'broad',        55, 'auto',    'med',  true, 'manual')
AS t(label, query, tier, horizon, category, baseline, default_direction, confidence, active, source);
