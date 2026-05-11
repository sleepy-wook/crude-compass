"""Sprint 3 Day 3 manual step — ingest jobs trigger + wait.

순서:
1. oil_prices_daily MODE=historical  (Dubai/Brent/WTI 3년 4개월)
2. ecos_daily MODE=historical         (FX 3년 4개월)
3. opec_momr_monthly                  (1-3월 LLM extraction v2)
4. backtest_seed                      (12 query × 3년 4개월)

병렬 trigger 후 모두 완료 대기.
"""
from __future__ import annotations
import sys, time, json

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except: pass

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.jobs import RunLifeCycleState

PROFILE = "crude-compass"

# job_name → (job_id, params)
# 1차 시도 후 실패한 3개만 재실행 (backtest_seed 7188 rows OK)
JOBS = {
    "oil_prices_daily":  {"params": {"mode": "historical", "hist_start": "2023-01-01"}},
    "ecos_daily":        {"params": {"mode": "historical", "hist_start": "2023-01-01"}},
    "opec_momr":         {"params": {}},
}


def main() -> None:
    w = WorkspaceClient(profile=PROFILE)
    print(f"host: {w.config.host}, user: {w.current_user.me().user_name}")

    # 1) Resolve job IDs
    print("\n=== Resolving job IDs ===")
    name_to_id: dict[str, int] = {}
    for j in w.jobs.list():
        n = j.settings.name if j.settings else ""
        for key in JOBS:
            # name 패턴: [dev hyeongwook_lee] crude-compass-{key-with-dashes}-dev
            if key.replace("_", "-") in n:
                name_to_id[key] = j.job_id
                print(f"  {key:<20} → {j.job_id} ({n})")
                break
    missing = [k for k in JOBS if k not in name_to_id]
    if missing:
        print(f"⚠️  Missing jobs: {missing}")

    # 2) Trigger all in parallel
    print("\n=== Triggering jobs ===")
    runs: dict[str, int] = {}  # key → run_id
    for key, jid in name_to_id.items():
        params = JOBS[key]["params"]
        r = w.jobs.run_now(job_id=jid, notebook_params=params)
        runs[key] = r.run_id
        print(f"  ⏵  {key} run_id={r.run_id} params={params}")

    # 3) Poll until all finished
    print("\n=== Polling (60s interval) ===")
    finished: dict[str, str] = {}
    t0 = time.time()
    MAX_WAIT = 1800  # 30 min

    while runs and (time.time() - t0) < MAX_WAIT:
        time.sleep(30)
        elapsed = int(time.time() - t0)
        still_running = []
        for key, rid in list(runs.items()):
            run = w.jobs.get_run(run_id=rid)
            state = run.state.life_cycle_state if run.state else None
            result_state = run.state.result_state if run.state else None
            if state in (RunLifeCycleState.TERMINATED, RunLifeCycleState.SKIPPED, RunLifeCycleState.INTERNAL_ERROR):
                finished[key] = f"{state.value if state else '?'} / {result_state.value if result_state else '?'}"
                del runs[key]
                print(f"  ✅ {key} done · {finished[key]} (after {elapsed}s)")
            else:
                still_running.append(key)
        if still_running:
            print(f"  ⏳ [{elapsed:>4}s] still running: {', '.join(still_running)}")

    # 4) Report
    print("\n=== Final status ===")
    for key, status in finished.items():
        print(f"  {key:<20} {status}")
    if runs:
        print(f"  ⚠️  TIMED OUT ({MAX_WAIT}s): {list(runs.keys())}")

    # 5) row counts after ingestion
    print("\n=== Quick row count check ===")
    whs = list(w.warehouses.list())
    wh = next((x for x in whs if "starter" in (x.name or "").lower()), whs[0])
    for tbl, where in [
        ("bronze.news_articles", "source_type='gdelt_backtest'"),
        ("bronze.oil_prices_daily", "1=1"),
        ("bronze.fx_rates", "1=1"),
        ("bronze.opec_momr_parsed", "saudi_production_kbbl_d IS NOT NULL"),
    ]:
        try:
            r = w.statement_execution.execute_statement(
                statement=f"SELECT COUNT(*) FROM crude_compass.{tbl} WHERE {where}",
                warehouse_id=wh.id, wait_timeout="30s",
            )
            n = r.result.data_array[0][0] if r.result and r.result.data_array else "?"
            print(f"  {tbl:<32} {where:<45} → {n}")
        except Exception as e:
            print(f"  {tbl}: {e}")


if __name__ == "__main__":
    main()
