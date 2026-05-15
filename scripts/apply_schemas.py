"""Apply Bronze/Silver/Gold DDL via Databricks SQL Statement Execution API.

Bootstrap script — bronze/silver/gold schema + tables 일괄 생성.
실제 DDL은 databricks/schemas/{bronze,silver,gold}.sql과 동기화 유지.

사용:
    cd backend
    $env:DATABRICKS_CONFIG_PROFILE = "crude-compass"
    $env:PYTHONIOENCODING = "utf-8"
    uv run python ../scripts/apply_schemas.py
"""
from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass

# Windows PowerShell cp949 → UTF-8
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except (AttributeError, OSError):
        pass

from databricks.sdk import WorkspaceClient


PROFILE = "crude-compass"  # ~/.databrickscfg
WAREHOUSE_ID = "da56f72320e22238"  # Serverless Starter Warehouse (crude-compass workspace)


@dataclass
class Stmt:
    label: str
    sql: str


# ════════════════════════════════════════════════════════════════════════
# Bronze (6 tables)
# ════════════════════════════════════════════════════════════════════════
BRONZE = [
    Stmt("bronze.news_articles", """
CREATE TABLE IF NOT EXISTS crude_compass.bronze.news_articles (
    article_id      STRING        NOT NULL,
    source          STRING        NOT NULL,
    source_type     STRING        NOT NULL COMMENT 'gdelt_detect | rss_enrich',
    tier            STRING        NOT NULL,
    published_at    TIMESTAMP     NOT NULL,
    fetched_at      TIMESTAMP     NOT NULL,
    url             STRING        NOT NULL,
    title           STRING        NOT NULL,
    body            STRING,
    body_lang       STRING,
    raw_tone        DECIMAL(5, 2) COMMENT 'GDELT tone -10~10',
    mention_count   INT,
    importance      INT           NOT NULL,
    category        STRING        NOT NULL,
    direction       STRING        NOT NULL COMMENT 'bullish|bearish|neutral',
    horizon         STRING        NOT NULL,
    confidence      STRING        NOT NULL,
    entities        ARRAY<STRING>,
    job_run_id      STRING,
    llm_model       STRING
)
USING DELTA
CLUSTER BY (published_at)
TBLPROPERTIES (
    delta.autoOptimize.optimizeWrite = true,
    delta.autoOptimize.autoCompact   = true
)
"""),
    Stmt("bronze.oil_prices", """
CREATE TABLE IF NOT EXISTS crude_compass.bronze.oil_prices (
    fetched_at      TIMESTAMP     NOT NULL,
    ticker          STRING        NOT NULL,
    price_usd       DECIMAL(8, 2) NOT NULL,
    delta_pct_5min  DECIMAL(5, 2),
    source          STRING        NOT NULL,
    raw_response    STRING
)
USING DELTA
CLUSTER BY (ticker, fetched_at)
"""),
    Stmt("bronze.oil_prices_daily", """
CREATE TABLE IF NOT EXISTS crude_compass.bronze.oil_prices_daily (
    trade_date      DATE          NOT NULL COMMENT 'KNOC 공시 거래일',
    ticker          STRING        NOT NULL COMMENT 'DUBAI | BRENT | WTI',
    price_usd       DECIMAL(8, 2) NOT NULL,
    fetched_at      TIMESTAMP     NOT NULL,
    source          STRING        NOT NULL COMMENT 'OPINET KNOC'
)
USING DELTA
CLUSTER BY (ticker, trade_date)
"""),
    Stmt("bronze.ais_positions", """
CREATE TABLE IF NOT EXISTS crude_compass.bronze.ais_positions (
    fetched_at      TIMESTAMP     NOT NULL,
    mmsi            STRING        NOT NULL,
    vessel_name     STRING,
    lat             DOUBLE        NOT NULL,
    lon             DOUBLE        NOT NULL,
    speed_knots     DECIMAL(4, 1),
    heading_deg     INT,
    in_hormuz_bbox  BOOLEAN,
    status          STRING
)
USING DELTA
CLUSTER BY (fetched_at)
"""),
    Stmt("bronze.fx_rates", """
CREATE TABLE IF NOT EXISTS crude_compass.bronze.fx_rates (
    date            DATE          NOT NULL,
    pair            STRING        NOT NULL,
    rate            DECIMAL(8, 2) NOT NULL,
    source          STRING        NOT NULL
)
USING DELTA
PARTITIONED BY (date)
"""),
    Stmt("bronze.eia_inventory", """
CREATE TABLE IF NOT EXISTS crude_compass.bronze.eia_inventory (
    week_ending       DATE          NOT NULL,
    series_id         STRING        NOT NULL,
    inventory_type    STRING        NOT NULL,
    value_kbbl        DECIMAL(12, 2) NOT NULL,
    delta_vs_prev_wk  DECIMAL(10, 2),
    fetched_at        TIMESTAMP     NOT NULL,
    source            STRING        NOT NULL
)
USING DELTA
PARTITIONED BY (week_ending)
"""),
    Stmt("bronze.opec_momr_parsed", """
CREATE TABLE IF NOT EXISTS crude_compass.bronze.opec_momr_parsed (
    report_month             STRING        NOT NULL,
    pdf_volume_path          STRING        NOT NULL,
    parsed_at                TIMESTAMP     NOT NULL,
    parsed_content           STRING,
    pages                    ARRAY<STRUCT<page_num INT, content STRING>>,
    tables                   ARRAY<STRING>,
    saudi_production_kbbl_d  DECIMAL(10, 2),
    iran_production_kbbl_d   DECIMAL(10, 2),
    opec_total_kbbl_d        DECIMAL(10, 2),
    forecast_demand_kbbl_d   DECIMAL(10, 2),
    extraction_model         STRING
)
USING DELTA
"""),
]

# ════════════════════════════════════════════════════════════════════════
# Silver schema + 4 tables
# ════════════════════════════════════════════════════════════════════════
SILVER = [
    Stmt("CREATE SCHEMA silver", "CREATE SCHEMA IF NOT EXISTS crude_compass.silver"),
    Stmt("silver.pattern_scores_daily", """
CREATE TABLE IF NOT EXISTS crude_compass.silver.pattern_scores_daily (
    date              DATE          NOT NULL,
    pattern_score     DECIMAL(5, 2) NOT NULL,
    bullish_score     DECIMAL(8, 2) NOT NULL,
    bearish_score     DECIMAL(8, 2) NOT NULL,
    cross_val_bonus   DECIMAL(5, 2) NOT NULL,
    mission_type      STRING        NOT NULL,
    signal_count_90d  INT           NOT NULL,
    top_categories    ARRAY<STRING>,
    computed_at       TIMESTAMP     NOT NULL,
    job_run_id        STRING
)
USING DELTA
"""),
    # silver.hormuz_traffic_hourly: 2026-05-16 DROP (populating job 0, 0 rows, dead).
    Stmt("silver.signal_events_decayed", """
CREATE TABLE IF NOT EXISTS crude_compass.silver.signal_events_decayed (
    event_date            DATE          NOT NULL,
    signal_type           STRING        NOT NULL,
    signal_id             STRING        NOT NULL,
    raw_intensity         DECIMAL(6, 2) NOT NULL,
    direction             STRING        NOT NULL,
    source_credibility    DECIMAL(3, 2) NOT NULL,
    days_ago              INT           NOT NULL,
    lambda_used           DECIMAL(6, 4) NOT NULL,
    applied_weight        DECIMAL(6, 4) NOT NULL,
    weighted_contribution DECIMAL(8, 2) NOT NULL,
    computed_at           TIMESTAMP     NOT NULL,
    job_run_id            STRING
)
USING DELTA
PARTITIONED BY (event_date)
"""),
    # silver.dubai_premium_daily: 2026-05-16 DROP (gold.oil_prices_wide의 brent_dubai_spread로 대체).
]

# ════════════════════════════════════════════════════════════════════════
# Gold schema + 3 tables
# ════════════════════════════════════════════════════════════════════════
GOLD = [
    Stmt("CREATE SCHEMA gold", "CREATE SCHEMA IF NOT EXISTS crude_compass.gold"),
    Stmt("gold.daily_risk_score", """
CREATE TABLE IF NOT EXISTS crude_compass.gold.daily_risk_score (
    date              DATE          NOT NULL,
    pattern_score     DECIMAL(5, 2) NOT NULL,
    bullish_score     DECIMAL(8, 2) NOT NULL,
    bearish_score     DECIMAL(8, 2) NOT NULL,
    cross_val_bonus   DECIMAL(5, 2) NOT NULL,
    confidence_score  DECIMAL(5, 2) NOT NULL,
    mission_type      STRING        NOT NULL,
    top_contributors  STRING,
    signal_count_90d  INT           NOT NULL,
    computed_at       TIMESTAMP     NOT NULL,
    lambda_table_id   STRING,
    job_run_id        STRING
)
USING DELTA
"""),
    # gold.backtest_results: 2026-05-16 DROP (Apps 사용 0건, LLM backtest가 main).
    # gold.mission_outcomes / landing_cost_scenarios / backtest_risk_score:
    # 2026-05-15 DROP (narrative만 약속됐고 코드 0건 사용 — dead).
    # gold.llm_backtest_predictions: 2026-05-15 Lakebase Postgres로 마이그레이션
    # (AI-generated content → OLTP). databricks/schemas/lakebase.sql §5 참조.
    # gold analytics views 8개는 별도 — databricks/schemas/gold.sql 직접 실행.
]


def execute(w: WorkspaceClient, stmt: Stmt) -> None:
    """Single statement 실행 + wait."""
    t0 = time.perf_counter()
    resp = w.statement_execution.execute_statement(
        statement=stmt.sql.strip(),
        warehouse_id=WAREHOUSE_ID,
        wait_timeout="30s",  # 동기 wait
    )
    dt = (time.perf_counter() - t0) * 1000
    state = resp.status.state.value if resp.status else "unknown"
    if state in ("SUCCEEDED",):
        print(f"  OK  {stmt.label:<40} ({dt:.0f}ms · {state})")
    else:
        err = resp.status.error.message if resp.status and resp.status.error else "?"
        print(f"  FAIL {stmt.label:<40} ({dt:.0f}ms · {state})")
        print(f"     {err}")
        raise RuntimeError(f"DDL failed: {stmt.label}")


def main() -> None:
    print("=" * 70)
    print(f"Apply schemas → {WAREHOUSE_ID} (Serverless Starter Warehouse)")
    print("=" * 70)

    w = WorkspaceClient(profile=PROFILE)
    print(f"  host: {w.config.host}")
    print(f"  user: {w.current_user.me().user_name}")

    print(f"\nBronze ({len(BRONZE)} stmts)")
    for s in BRONZE:
        execute(w, s)

    print(f"\nSilver ({len(SILVER)} stmts: 1 schema + 2 tables)")
    for s in SILVER:
        execute(w, s)

    print(f"\nGold ({len(GOLD)} stmts: 1 schema + 2 tables)")
    for s in GOLD:
        execute(w, s)

    # 최종 검증
    print("\n" + "=" * 70)
    print("최종 검증 — information_schema.tables")
    print("=" * 70)
    verify = w.statement_execution.execute_statement(
        statement="""
            SELECT table_schema, COUNT(*) AS n
            FROM crude_compass.information_schema.tables
            WHERE table_catalog = 'crude_compass'
            GROUP BY table_schema
            ORDER BY table_schema
        """,
        warehouse_id=WAREHOUSE_ID,
        wait_timeout="30s",
    )
    if verify.result and verify.result.data_array:
        for row in verify.result.data_array:
            print(f"  {row[0]:<10}  {row[1]} 테이블")

    print("\nSchema apply 완료")


if __name__ == "__main__":
    main()
