"""Sprint 3 Day 3 — 데이터 품질 검증 (시나리오 의도 vs 실제 적재 상태).

체크 항목:
1. Bronze 테이블별 row count + date range + freshness
2. news_articles 시그널 분포 (direction/category/tier × source_type)
3. opec_momr_parsed indicator 추출 quality (non-null %)
4. fx_rates / eia_inventory / oil_prices 적재 완전성
5. backtest seed 5개월 → 3년 확장 필요량 계산
6. Dubai daily ingest 후 예상 trade days

사용:
    cd backend
    $env:DATABRICKS_CONFIG_PROFILE = "crude-compass"
    $env:PYTHONIOENCODING = "utf-8"
    uv run python ../scripts/verify_data_quality.py
"""
from __future__ import annotations

import sys
import time

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except (AttributeError, OSError):
        pass

from databricks.sdk import WorkspaceClient

PROFILE = "crude-compass"  # ~/.databrickscfg
# WAREHOUSE_ID는 동적으로 해석 (workspace마다 다름)


_warehouse_id: str | None = None


def get_warehouse_id(w: WorkspaceClient) -> str:
    """Resolve Serverless Starter Warehouse ID dynamically."""
    global _warehouse_id
    if _warehouse_id:
        return _warehouse_id
    for wh in w.warehouses.list():
        if "serverless" in (wh.name or "").lower() or "starter" in (wh.name or "").lower():
            _warehouse_id = wh.id
            print(f"  📍 Resolved warehouse: {wh.name} ({wh.id})")
            return wh.id
    # fallback: 첫 번째 warehouse
    whs = list(w.warehouses.list())
    if not whs:
        raise RuntimeError("No warehouses found")
    _warehouse_id = whs[0].id
    print(f"  📍 Fallback warehouse: {whs[0].name} ({whs[0].id})")
    return whs[0].id


def q(w: WorkspaceClient, sql: str, label: str = "") -> list[list]:
    """Execute SQL, return data_array. Tolerates table-not-found."""
    t0 = time.perf_counter()
    try:
        resp = w.statement_execution.execute_statement(
            statement=sql.strip(),
            warehouse_id=get_warehouse_id(w),
            wait_timeout="30s",
        )
        dt = (time.perf_counter() - t0) * 1000
        state = resp.status.state.value if resp.status else "unknown"
        if state != "SUCCEEDED":
            err = resp.status.error.message if resp.status and resp.status.error else "?"
            if "TABLE_OR_VIEW_NOT_FOUND" in err or "does not exist" in err.lower():
                print(f"  ⚠️  {label}: 테이블 미존재 → skip")
                return []
            print(f"  ❌ {label} ({dt:.0f}ms · {state}): {err}")
            return []
        if resp.result and resp.result.data_array:
            return resp.result.data_array
        return []
    except Exception as e:
        print(f"  ❌ {label}: {e}")
        return []


def section(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def main() -> None:
    print("=" * 70)
    print(f"Crude Compass — 데이터 품질 검증 (Sprint 3 Day 3)")
    print(f"Profile: {PROFILE}")
    print("=" * 70)

    w = WorkspaceClient(profile=PROFILE)
    print(f"  host: {w.config.host}")
    print(f"  user: {w.current_user.me().user_name}")

    # ────────────────────────────────────────────────────────────────────
    section("1. Bronze 테이블별 row count + date range + freshness")
    # ────────────────────────────────────────────────────────────────────
    BRONZE_TABLES = [
        ("bronze.news_articles",       "published_at",  "DATE(published_at)"),
        ("bronze.oil_prices",          "fetched_at",    "DATE(fetched_at)"),
        ("bronze.oil_prices_daily",    "trade_date",    "trade_date"),
        ("bronze.fx_rates",            "date",          "date"),
        ("bronze.eia_inventory",       "week_ending",   "week_ending"),
        ("bronze.opec_momr_parsed",    "parsed_at",     "DATE(parsed_at)"),
    ]
    for tbl, ts_col, date_expr in BRONZE_TABLES:
        rows = q(w, f"""
            SELECT
                COUNT(*) AS n,
                MIN({date_expr}) AS min_d,
                MAX({date_expr}) AS max_d,
                DATEDIFF(CURRENT_DATE(), MAX({date_expr})) AS days_stale
            FROM crude_compass.{tbl}
        """, label=tbl)
        if rows:
            n, mn, mx, stale = rows[0]
            print(f"  {tbl:<32} n={n:>8} | {mn} ~ {mx} | stale={stale}d")
        else:
            print(f"  {tbl:<32} (empty or missing)")

    # ────────────────────────────────────────────────────────────────────
    section("2. news_articles 분포 (direction × source_type × tier)")
    # ────────────────────────────────────────────────────────────────────
    rows = q(w, """
        SELECT source_type, direction, tier, COUNT(*) AS n,
               ROUND(AVG(importance), 1) AS avg_imp,
               MIN(DATE(published_at)) AS min_d,
               MAX(DATE(published_at)) AS max_d
        FROM crude_compass.bronze.news_articles
        GROUP BY source_type, direction, tier
        ORDER BY source_type, direction, tier
    """, label="news_articles distribution")
    if rows:
        print(f"  {'source_type':<18} {'direction':<10} {'tier':<5} {'n':>6} {'avg_imp':>8} {'range'}")
        for r in rows:
            st, dir_, tier, n, avg_imp, mn, mx = r
            print(f"  {(st or '-'):<18} {(dir_ or '-'):<10} {(tier or '-'):<5} {n:>6} {(avg_imp or 0):>8} {mn} ~ {mx}")

    # category 분포
    rows = q(w, """
        SELECT category, COUNT(*) AS n
        FROM crude_compass.bronze.news_articles
        GROUP BY category
        ORDER BY n DESC
    """, label="news_articles categories")
    if rows:
        print("\n  category distribution:")
        for r in rows:
            print(f"    {r[0]:<20} {r[1]}")

    # ────────────────────────────────────────────────────────────────────
    section("3. opec_momr_parsed — indicator 추출 quality")
    # ────────────────────────────────────────────────────────────────────
    rows = q(w, """
        SELECT
            report_month,
            CASE WHEN parsed_content IS NOT NULL THEN '✓' ELSE '✗' END AS raw_text,
            CASE WHEN saudi_production_kbbl_d IS NOT NULL THEN '✓' ELSE '✗' END AS saudi,
            CASE WHEN iran_production_kbbl_d IS NOT NULL THEN '✓' ELSE '✗' END AS iran,
            CASE WHEN opec_total_kbbl_d IS NOT NULL THEN '✓' ELSE '✗' END AS opec_total,
            CASE WHEN forecast_demand_kbbl_d IS NOT NULL THEN '✓' ELSE '✗' END AS demand,
            saudi_production_kbbl_d, iran_production_kbbl_d,
            opec_total_kbbl_d, forecast_demand_kbbl_d
        FROM crude_compass.bronze.opec_momr_parsed
        ORDER BY report_month
    """, label="opec_momr_parsed quality")
    if rows:
        print(f"  {'month':<12} {'raw':<5} {'saudi':<7} {'iran':<6} {'total':<7} {'demand':<8} {'saudi_v':<10} {'iran_v':<10} {'total_v':<10} {'demand_v'}")
        for r in rows:
            mon, raw, sa, ir, tot, dm, sav, irv, totv, dmv = r
            print(f"  {mon:<12} {raw:<5} {sa:<7} {ir:<6} {tot:<7} {dm:<8} {sav or '-':<10} {irv or '-':<10} {totv or '-':<10} {dmv or '-'}")

    # ────────────────────────────────────────────────────────────────────
    section("4. backtest seed coverage (gdelt_backtest)")
    # ────────────────────────────────────────────────────────────────────
    rows = q(w, """
        SELECT
            DATE_TRUNC('month', published_at) AS month,
            COUNT(*) AS n,
            COUNT(DISTINCT DATE(published_at)) AS days_covered,
            ROUND(AVG(importance), 1) AS avg_imp,
            SUM(CASE WHEN direction='bullish' THEN 1 ELSE 0 END) AS bullish_n,
            SUM(CASE WHEN direction='bearish' THEN 1 ELSE 0 END) AS bearish_n,
            SUM(CASE WHEN direction='neutral' THEN 1 ELSE 0 END) AS neutral_n
        FROM crude_compass.bronze.news_articles
        WHERE source_type = 'gdelt_backtest'
        GROUP BY DATE_TRUNC('month', published_at)
        ORDER BY month
    """, label="backtest_seed monthly")
    if rows:
        print(f"  {'month':<12} {'n':>5} {'days':>5} {'avg_imp':>8} {'bull':>5} {'bear':>5} {'neut':>5}")
        for r in rows:
            mon, n, days, ai, bu, be, ne = r
            print(f"  {str(mon)[:10]:<12} {n:>5} {days:>5} {ai:>8} {bu:>5} {be:>5} {ne:>5}")

    # ────────────────────────────────────────────────────────────────────
    section("5. Silver/Gold 적재 상태")
    # ────────────────────────────────────────────────────────────────────
    SG_TABLES = [
        ("silver.signal_events_decayed", "event_date"),
        ("silver.pattern_scores_daily",  "date"),
        ("gold.daily_risk_score",        "date"),
    ]
    for tbl, dt_col in SG_TABLES:
        rows = q(w, f"""
            SELECT COUNT(*) AS n, MIN({dt_col}) AS mn, MAX({dt_col}) AS mx
            FROM crude_compass.{tbl}
        """, label=tbl)
        if rows:
            n, mn, mx = rows[0]
            print(f"  {tbl:<35} n={n:>6} | {mn} ~ {mx}")

    # ────────────────────────────────────────────────────────────────────
    section("6. backtest_results 최신 run")
    # ────────────────────────────────────────────────────────────────────
    rows = q(w, """
        SELECT run_id, backtest_window, mission_type, signal_count, correct_count,
               accuracy_pct, avg_lead_time_days
        FROM crude_compass.gold.backtest_results
        ORDER BY computed_at DESC
        LIMIT 10
    """, label="backtest_results")
    if rows:
        print(f"  {'run_id':<35} {'type':<13} {'n':>4} {'hit':>4} {'prec':>6} {'lead'}")
        for r in rows:
            run, win, t, n, hit, prec, lead = r
            print(f"  {run[:35]:<35} {t:<13} {n:>4} {hit:>4} {prec or 0:>6} {lead or '-'}")

    # ────────────────────────────────────────────────────────────────────
    section("7. 시나리오 의도 vs 실제 — Gap 진단")
    # ────────────────────────────────────────────────────────────────────
    diagnostics = []

    # 7-1. Backtest seed 3년 확장 필요량
    rows = q(w, """
        SELECT MIN(DATE(published_at)) AS mn, MAX(DATE(published_at)) AS mx, COUNT(*) AS n
        FROM crude_compass.bronze.news_articles
        WHERE source_type = 'gdelt_backtest'
    """, label="seed range")
    if rows and rows[0][2]:
        mn, mx, n = rows[0]
        target_start = "2023-01-01"
        diagnostics.append(
            f"Backtest seed 현재 범위: {mn} ~ {mx} (n={n})\n"
            f"   → 3년 4개월 (~9000 rows 예상) 위해 START_DT={target_start} 재실행 필요"
        )

    # 7-2. Dubai daily 적재 여부
    rows = q(w, """
        SELECT COUNT(*) AS n FROM crude_compass.bronze.oil_prices_daily WHERE ticker = 'DUBAI'
    """, label="dubai count")
    n = int(rows[0][0]) if rows and rows[0][0] is not None else 0
    if n < 100:
        diagnostics.append(
            f"Dubai daily 적재 부족 (n={n})\n"
            f"   → job_oil_prices_daily MODE=historical, hist_start=2023-01-01 1회 실행 필요 (~864 records)"
        )

    # 7-3. FX rate 3년 coverage
    rows = q(w, """
        SELECT MIN(date) AS mn, MAX(date) AS mx, COUNT(*) AS n
        FROM crude_compass.bronze.fx_rates
    """, label="fx range")
    if rows:
        mn, mx, n = rows[0]
        n = int(n) if n is not None else 0
        if n < 600:  # 3년 daily ~750
            diagnostics.append(
                f"FX rate 부족 (n={n}, range {mn} ~ {mx})\n"
                f"   → job_ecos MODE=historical, hist_start=2023-01-01 1회 실행 필요"
            )

    # 7-4. OPEC 추출 완전성
    rows = q(w, """
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN saudi_production_kbbl_d IS NOT NULL THEN 1 ELSE 0 END) AS saudi_n
        FROM crude_compass.bronze.opec_momr_parsed
    """, label="opec extraction")
    if rows and rows[0][0]:
        total, saudi_n = rows[0]
        if saudi_n < total:
            diagnostics.append(
                f"OPEC indicator 추출 부분 적재: {saudi_n}/{total} reports에 saudi extracted\n"
                f"   → 나머지는 LLM extraction 재실행 또는 추출 prompt 보강 필요"
            )

    if diagnostics:
        for i, d in enumerate(diagnostics, 1):
            print(f"\n  [{i}] {d}")
    else:
        print("\n  ✅ Gap 없음 — 시나리오 의도대로 적재됨")

    print("\n" + "=" * 70)
    print("✅ Verification 완료")
    print("=" * 70)


if __name__ == "__main__":
    main()
