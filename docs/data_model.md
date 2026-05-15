# Data Model — Crude Compass

> 작성일: 2026-05-08 (D-14, Phase 3)
> 입력: [architecture.md](architecture.md) + 시나리오 부록 B
> 본 문서는 모든 테이블의 DDL + 인덱스 + sample row.

---

## 0. Catalog 구조

```
crude_compass (Unity Catalog)
├── bronze
│   ├── news_articles
│   ├── oil_prices                   (5min realtime)
│   ├── oil_prices_daily              (KNOC OPINET daily close)
│   ├── fx_rates                      (ECOS USD/KRW)
│   ├── eia_inventory                 (EIA weekly)
│   └── opec_momr_parsed              (Document Intelligence)
├── silver
│   ├── pattern_scores_daily          (Pattern Score daily)
│   └── signal_events_decayed         (시간 감쇠 적용)
└── gold
    ├── daily_risk_score              (Pattern Score snapshot)
    ├── missions_history              (Lakehouse Sync CDC)
    └── (7 analytics views)           ← oil_prices_wide / signal_contribution_30d /
                                        eia_rolling / opec_demand_gap /
                                        fx_with_delta / news_top_signals /
                                        pattern_score_latest

lakebase (Postgres OLTP, schema: public)
├── missions                          ← Single Source of Truth (양방향 sync)
├── decisions                         (audit log)
├── pivot_history
├── discovery_feed_items
└── backtest_predictions              (AI-generated → OLTP, 2026-05-15 신규)
```

---

## 1. Bronze (Delta, append-only)

### 1.1 `bronze.news_articles` ⭐ 핵심

```sql
CREATE TABLE crude_compass.bronze.news_articles (
    article_id      STRING        NOT NULL,    -- SHA256(url)
    source          STRING        NOT NULL,    -- "Reuters", "Yonhap", "EIA", ...
    tier            STRING        NOT NULL,    -- "A" | "B"
    published_at    TIMESTAMP     NOT NULL,
    fetched_at      TIMESTAMP     NOT NULL,
    url             STRING        NOT NULL,
    title           STRING        NOT NULL,
    body            STRING,
    body_lang       STRING,                    -- "ko" | "en"

    -- LLM scoring (Foundation Model API · Claude Haiku 4.5)
    importance      INT           NOT NULL,    -- 0-100
    category        STRING        NOT NULL,    -- geopolitical|policy|disaster|market|supply|demand
    direction       STRING        NOT NULL,    -- bullish|bearish|neutral ⭐ 양방향 핵심
    horizon         STRING        NOT NULL,    -- short|medium|long
    confidence      STRING        NOT NULL,    -- low|med|high
    entities        ARRAY<STRING>,              -- ["IRGC", "OPEC", ...]

    -- Job metadata
    job_run_id      STRING,
    llm_model       STRING                    -- "databricks-claude-haiku-4-5"
)
USING DELTA
PARTITIONED BY (DATE(published_at))
TBLPROPERTIES (delta.autoOptimize.optimizeWrite = true);

CREATE INDEX idx_news_direction_importance
  ON crude_compass.bronze.news_articles (direction, importance);
```

> Direction 컬럼이 **양방향 Pattern Detection의 핵심**. importance >= 60만 적재.

### 1.2 `bronze.oil_prices`

```sql
CREATE TABLE crude_compass.bronze.oil_prices (
    fetched_at      TIMESTAMP     NOT NULL,
    ticker          STRING        NOT NULL,    -- "BRENT" | "WTI" | "DUBAI"
    price_usd       DECIMAL(8, 2) NOT NULL,
    delta_pct_5min  DECIMAL(5, 2),             -- spike detection
    source          STRING        NOT NULL,    -- "OilPriceAPI"
    raw_response    STRING                     -- JSON for audit
)
USING DELTA
PARTITIONED BY (DATE(fetched_at))
CLUSTER BY (ticker, fetched_at);
```

### 1.3 (deprecated 5/16 D-2 — `bronze.ais_positions` DROP)

AIS Stream 데이터 출처 제거. 이유: 한국 flag VLCC 0척 active + 7년 backtest 미사용 → narrative dead weight.
호르무즈 narrative anchor는 GDELT 뉴스 키워드 mention burst로 단일화.

### 1.4 `bronze.fx_rates`

```sql
CREATE TABLE crude_compass.bronze.fx_rates (
    date            DATE          NOT NULL,
    pair            STRING        NOT NULL,    -- "USD/KRW"
    rate            DECIMAL(8, 2) NOT NULL,
    source          STRING        NOT NULL,    -- "ECOS"
    PRIMARY KEY (date, pair)
)
USING DELTA;
```

---

## 2. Silver (Delta, transformed)

### 2.1 `silver.pattern_scores_daily` ⭐ Bidirectional Pattern Detection 결과

```sql
CREATE TABLE crude_compass.silver.pattern_scores_daily (
    date              DATE         NOT NULL    PRIMARY KEY,
    pattern_score     DECIMAL(5, 2) NOT NULL,  -- 0-100
    bullish_score     DECIMAL(8, 2) NOT NULL,  -- 누적 weighted
    bearish_score     DECIMAL(8, 2) NOT NULL,
    cross_val_bonus   DECIMAL(5, 2) NOT NULL,
    mission_type      STRING       NOT NULL,   -- 'HEDGE' | 'OPPORTUNITY' | 'NONE'
    signal_count_90d  INT          NOT NULL,
    top_categories    ARRAY<STRING>,           -- ["geopolitical", "policy"]
    computed_at       TIMESTAMP    NOT NULL,
    job_run_id        STRING
)
USING DELTA
TBLPROPERTIES (delta.autoOptimize.optimizeWrite = true);
```

**Sample row**:
```json
{
  "date": "2026-05-07",
  "pattern_score": 82.0,
  "bullish_score": 187.5,
  "bearish_score": 23.0,
  "cross_val_bonus": 20.0,
  "mission_type": "HEDGE",
  "signal_count_90d": 47,
  "top_categories": ["geopolitical", "policy", "market"],
  "computed_at": "2026-05-07T06:30:00+09:00"
}
```

### 2.2 `silver.signal_events_decayed`

시그널별 시간 감쇠 적용 결과 — `weighted_contribution` 보존.
실제 column은 `databricks/schemas/silver.sql` 참조.

> 2026-05-16 정리: `silver.hormuz_traffic_hourly` + `silver.dubai_premium_daily` 2개 DROP
> (populating job 0, 0 rows, code 참조 0).
> 2026-05-16 D-2 정리: AIS Stream 완전 제거 → `signal_type` 종류 6→5 (news_tone / eia_inventory / opec_momr / fx_krw_usd / price_spike).

---

## 3. Gold (Delta, analytics)

> 2026-05-15 정리: `gold.mission_outcomes` / `gold.landing_cost_scenarios` /
> `gold.backtest_risk_score` 3개 dead table DROP. `gold.llm_backtest_predictions`는
> Lakebase `backtest_predictions`로 마이그레이션 (AI-generated content → OLTP).
> 실제 column은 `databricks/schemas/gold.sql` 참조.

### 3.1 (archived) `gold.mission_outcomes` — DROP됨

```sql
-- 참고용 archived schema (2026-05-15 DROP, dead table)
CREATE TABLE crude_compass.gold.mission_outcomes (
    mission_id        STRING       NOT NULL    PRIMARY KEY,
    mission_type      STRING       NOT NULL,
    proposed_at       TIMESTAMP    NOT NULL,
    confirmed_at      TIMESTAMP,
    completed_at      TIMESTAMP,
    final_status      STRING       NOT NULL,
    pattern_score     DECIMAL(5, 2),
    target_pct        INT,
    actual_pct        INT,
    roi_simulated     DECIMAL(12, 2),
    roi_realized      DECIMAL(12, 2),
    pivot_count       INT          DEFAULT 0
)
USING DELTA;
```

### 3.2 `gold.backtest_results` ⭐ Mock backtest narrative source

```sql
CREATE TABLE crude_compass.gold.backtest_results (
    run_id            STRING       NOT NULL    PRIMARY KEY,
    backtest_window   STRING       NOT NULL,   -- "2025-12 ~ 2026-04"
    mission_type      STRING       NOT NULL,
    signal_count      INT          NOT NULL,
    correct_count     INT          NOT NULL,
    accuracy_pct      DECIMAL(5, 2) NOT NULL,
    avg_lead_time_days DECIMAL(5, 1),
    threshold_used    DECIMAL(5, 2),           -- 70 (HEDGE) or 30 (OPP)
    computed_at       TIMESTAMP    NOT NULL
)
USING DELTA;
```

**Sample row**:
```json
{
  "run_id": "bt_2026-05-15_142",
  "backtest_window": "2025-12 ~ 2026-04",
  "mission_type": "HEDGE",
  "signal_count": 12,
  "correct_count": 9,
  "accuracy_pct": 75.0,
  "avg_lead_time_days": 12.4,
  "threshold_used": 70.0
}
```

### 3.3 `gold.missions_history` (Lakehouse Sync target)

> **Lakebase missions 테이블의 CDC append-only 미러** — 자동 sync. 형욱님이 직접 작성하지 않음. Self-Critique Agent가 이 테이블로 backtest.

```sql
-- Auto-created by Lakebase Lakehouse Sync
-- crude_compass.gold.missions_history
-- Schema: same as Lakebase missions + (cdc_op, cdc_ts, cdc_seq)
```

---

## 4. Lakebase Postgres (OLTP)

> **Single Source of Truth for mission state**. Slack ↔ Apps 동기화의 anchor.
> ⚠️ Sprint 1 첫날 simple test로 JSONB / UUID / version 컬럼 호환성 검증 (Phase 1.4 Manual Step #2 mitigation).

### 4.1 `missions` ⭐ 핵심

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- gen_random_uuid()

CREATE TABLE missions (
    mission_id        UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    mission_type      VARCHAR(20)  NOT NULL,    -- 'HEDGE' | 'OPPORTUNITY'
    status            VARCHAR(20)  NOT NULL DEFAULT 'proposed',
                                                -- proposed | active | on_track | at_risk
                                                -- | paused | pivoted | aborted | completed
    goal_text         TEXT         NOT NULL,
    pattern_score     NUMERIC(5,2) NOT NULL,
    reasoning         TEXT         NOT NULL,
    simulation_roi    JSONB        NOT NULL,    -- {scenario: krw_billion}
    urgency           VARCHAR(10)  NOT NULL DEFAULT 'default',
                                                -- optional | default | urgent
    target_pct        INT,                      -- e.g. 70 (Term 70%)
    duration_days     INT          NOT NULL DEFAULT 28,

    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    confirmed_at      TIMESTAMPTZ,
    confirmed_by      VARCHAR(50),
    confirmed_via     VARCHAR(20),              -- 'slack' | 'apps'
    completed_at      TIMESTAMPTZ,

    pivot_history     JSONB        NOT NULL DEFAULT '[]'::jsonb,
                                                -- [{from, to, at, reason}]
    version           INT          NOT NULL DEFAULT 1,    -- optimistic concurrency
    last_event_id     BIGINT,                   -- for WS replay

    CONSTRAINT chk_mission_type CHECK (mission_type IN ('HEDGE', 'OPPORTUNITY')),
    CONSTRAINT chk_status CHECK (status IN (
        'proposed', 'active', 'on_track', 'at_risk',
        'paused', 'pivoted', 'aborted', 'completed'
    ))
);

CREATE INDEX idx_missions_status_created ON missions (status, created_at DESC);
CREATE INDEX idx_missions_type_active   ON missions (mission_type)
    WHERE status IN ('active', 'on_track', 'at_risk');
```

**Sample row**:
```json
{
  "mission_id": "550e8400-e29b-41d4-a716-446655440000",
  "mission_type": "HEDGE",
  "status": "proposed",
  "goal_text": "Term 60% → 75% (4주) — Pre-emptive Hedge",
  "pattern_score": 82.0,
  "reasoning": "지난 3주 escalation 신호 6건 누적, Cross-validation 4 source confirm...",
  "simulation_roi": {
    "Brent_130_Dubai_125": 320,
    "Brent_110_Dubai_108": 140,
    "Brent_100_Dubai_98":  40,
    "Brent_90_Dubai_85":   -50
  },
  "urgency": "urgent",
  "target_pct": 70,
  "duration_days": 28,
  "version": 1
}
```

### 4.2 `decisions` (audit log)

```sql
CREATE TABLE decisions (
    decision_id       UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    mission_id        UUID         NOT NULL REFERENCES missions(mission_id),
    action            VARCHAR(20)  NOT NULL,
                                                -- 'confirm' | 'reject' | 'modify'
                                                -- | 'pivot' | 'pause' | 'abort'
    actor             VARCHAR(50)  NOT NULL,    -- "kim_jihoon"
    via               VARCHAR(20)  NOT NULL,    -- 'slack' | 'apps' | 'api'
    payload           JSONB        NOT NULL DEFAULT '{}'::jsonb,
    occurred_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    request_id        UUID                     -- for idempotency
);

CREATE INDEX idx_decisions_mission ON decisions (mission_id, occurred_at DESC);
```

### 4.3 `pivot_history`

```sql
CREATE TABLE pivot_history (
    pivot_id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    mission_id        UUID         NOT NULL REFERENCES missions(mission_id),
    from_type         VARCHAR(20)  NOT NULL,
    to_type           VARCHAR(20)  NOT NULL,
    pivot_action      VARCHAR(20)  NOT NULL,    -- 'pivot' | 'pause' | 'abort' | 'continue'
    reason            TEXT         NOT NULL,
    pattern_score_at  NUMERIC(5,2) NOT NULL,
    occurred_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
```

### 4.4 `discovery_feed_items`

```sql
CREATE TABLE discovery_feed_items (
    item_id           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    feed_date         DATE         NOT NULL,
    item_type         VARCHAR(30)  NOT NULL,    -- 'mission_proposal' | 'reactive' | 'osp' | 'mission_checkpoint'
    title             TEXT         NOT NULL,
    body              TEXT,
    related_mission_id UUID        REFERENCES missions(mission_id),
    metadata          JSONB        NOT NULL DEFAULT '{}'::jsonb,
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    dismissed_at      TIMESTAMPTZ
);

CREATE INDEX idx_discovery_date ON discovery_feed_items (feed_date DESC);
```

---

## 5. Lakehouse Sync (CDC) 설정

> A2 결정. Lakebase Autoscaling 기본 기능. 형욱님 직접 코드 작성 X.

🛑 **MANUAL STEP — Lakehouse Sync 활성화**
WHERE: Databricks Workspace UI → Lakebase instance → Sync settings
HOW:
  1. Lakebase 인스턴스 안 `missions` 테이블 → Enable Lakehouse Sync
  2. Target catalog: `crude_compass.gold`
  3. Target table name: `missions_history`
  4. Sync mode: **CDC append-only** (full history 유지, Self-Critique Agent용)
SOURCE: https://docs.databricks.com/aws/en/oltp/projects/sync-tables
완료하면 답해주세요: "done: Lakehouse Sync 활성화"

> Sprint 4 (5/17-19) 진입 시 형욱님이 manual로 활성화. 그 전에는 Sprint 1-3에서 missions 테이블 INSERT/UPDATE 직접 사용.

---

## 6. ER Diagram (간략)

```
crude_compass.bronze.news_articles ──┐
crude_compass.bronze.oil_prices    ──┤
crude_compass.bronze.eia_inventory ──┼──> Job 5 daily_curation
crude_compass.bronze.fx_rates      ──┘         │
                                                ↓
                          crude_compass.silver.pattern_scores_daily
                                                │
                                                ↓
                                  Mission Plan Agent (Agent 3)
                                                │
                                                ↓
                            ┌─────────────────────────────────┐
                            │  lakebase.missions ⭐           │
                            │   ↑ ↓                            │
                            │  lakebase.decisions             │
                            │  lakebase.pivot_history         │
                            │  lakebase.discovery_feed_items  │
                            └────────────┬────────────────────┘
                                         │ Lakehouse Sync (CDC)
                                         ↓
                          crude_compass.gold.missions_history
                                         │
                                         ↓
                          crude_compass.gold.{mission_outcomes, backtest_results}
                                         │
                                         ↓
                                AI/BI Dashboard (Apps embed)
```

---

## 7. DDL 적용 순서 (Sprint 1·2)

| 시점 | 작업 | 파일 |
|---|---|---|
| Sprint 1 day 1 | Lakebase 인스턴스 프로비저닝 (manual) + simple test (JSONB/UUID/version) | `scripts/lakebase_dialect_test.py` |
| Sprint 1 day 1-2 | Bronze 4 테이블 DDL 실행 | `databricks/schemas/bronze.sql` |
| Sprint 1 day 2-3 | Lakebase 4 테이블 DDL 실행 | `databricks/schemas/lakebase.sql` |
| Sprint 2 day 1 | Job 1·2·3·4 첫 적재 → Bronze 검증 | (Job notebooks) |
| Sprint 3 day 1 | Silver / Gold 테이블 DDL + Job 5 첫 실행 | `databricks/schemas/silver.sql`, `gold.sql` |
| Sprint 4 day 1 | Lakehouse Sync 활성화 (manual) | (UI) |

---

## 8. 데이터 보존 정책

| Layer | 보존 기간 | 이유 |
|---|---|---|
| Bronze | 90일 (auto-delete) | Pattern Detection window 90일이면 충분. 이전 데이터는 Wayback으로 backfill 가능 |
| Silver | 365일 | 1년 backtest 충분 |
| Gold | infinite | 장기 분석 |
| Lakebase missions | infinite | 비즈니스 audit |
| Lakebase decisions | infinite | 매니저 의사결정 audit |

