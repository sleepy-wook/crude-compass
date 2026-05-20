"""Credit burn rate diagnostic v2 — endpoint/cost driver focus."""
import os
import sys
import io
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Force UTF-8 on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Load env
ROOT = Path(__file__).resolve().parent.parent
env_file = ROOT / "backend" / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from databricks.sdk import WorkspaceClient
w = WorkspaceClient()

print(f"=== Credit burn analysis v2 @ {datetime.now(timezone.utc).isoformat()} ===\n")

# ─────────────────────────────────────────
# 1. SERVING ENDPOINTS — full detail
# ─────────────────────────────────────────
print("\n[1] SERVING ENDPOINTS (가장 비싼 cost driver)")
print("=" * 80)
try:
    endpoints = list(w.serving_endpoints.list())
    print(f"Total: {len(endpoints)} endpoints\n")
    for ep in endpoints:
        name = ep.name or "?"
        state = ep.state.ready.value if ep.state and ep.state.ready else "?"
        print(f"  [{state:8}] {name}")
        cfg = ep.config
        if cfg:
            for sm in (cfg.served_models or []):
                attrs = {k: getattr(sm, k, None) for k in [
                    "name", "model_name", "model_version",
                    "workload_size", "workload_type", "scale_to_zero_enabled",
                    "min_provisioned_throughput", "max_provisioned_throughput",
                ]}
                attrs = {k: v for k, v in attrs.items() if v is not None}
                print(f"      model: {attrs}")
            for se in (cfg.served_entities or []):
                # Different attribute set for entities (Agent Bricks / custom)
                attrs = {}
                for k in ["name", "entity_name", "entity_version", "entity_type",
                          "scale_to_zero_enabled", "min_provisioned_throughput",
                          "max_provisioned_throughput", "instance_profile_arn"]:
                    v = getattr(se, k, None)
                    if v is not None:
                        attrs[k] = v
                print(f"      entity: {attrs}")
        if ep.tags:
            tag_str = ", ".join(f"{t.key}={t.value}" for t in ep.tags if t.key)
            if tag_str:
                print(f"      tags: {tag_str}")
        print()
except Exception as e:
    print(f"  ERR: {e}")

# ─────────────────────────────────────────
# 2. SQL WAREHOUSES
# ─────────────────────────────────────────
print("\n[2] SQL WAREHOUSES")
print("=" * 80)
try:
    for wh in w.warehouses.list():
        name = wh.name or "?"
        state = wh.state.value if wh.state else "?"
        print(f"  [{state:8}] {name} size={wh.cluster_size} auto_stop={wh.auto_stop_mins}min serverless={wh.enable_serverless_compute}")
        if wh.tags and wh.tags.custom_tags:
            for tag in wh.tags.custom_tags:
                print(f"      tag: {tag.key}={tag.value}")
except Exception as e:
    print(f"  ERR: {e}")

# ─────────────────────────────────────────
# 3. JOBS — last 7d run count + total compute time
# ─────────────────────────────────────────
print("\n[3] JOBS — last 7d run count + total compute time")
print("=" * 80)
try:
    jobs = list(w.jobs.list())
    since = datetime.now(timezone.utc) - timedelta(days=7)
    since_ms = int(since.timestamp() * 1000)

    print(f"  {'Job name':<50} {'Schedule':<22} {'7d runs':<10} {'Total dur':<12} {'Avg run'}")
    print(f"  {'-'*50} {'-'*22} {'-'*10} {'-'*12} {'-'*10}")

    total_compute_hours = 0
    for job in jobs:
        name = (job.settings.name if job.settings else "?")
        sched = ""
        paused = False
        if job.settings and job.settings.schedule:
            sched = job.settings.schedule.quartz_cron_expression or ""
            if job.settings.schedule.pause_status:
                ps_str = job.settings.schedule.pause_status.value if hasattr(job.settings.schedule.pause_status, 'value') else str(job.settings.schedule.pause_status)
                if ps_str == "PAUSED":
                    paused = True

        # last 7d runs (limit 25 max per SDK; multi-page if needed)
        all_runs = []
        try:
            page_iter = w.jobs.list_runs(job_id=job.job_id, start_time_from=since_ms, limit=25)
            for r in page_iter:
                all_runs.append(r)
        except Exception as e:
            err_short = str(e)[:30]
            print(f"  {name[:50]:<50} {sched[:22]:<22} ERR: {err_short}")
            continue
        n = len(all_runs)
        durs_ms = []
        for r in all_runs:
            if r.run_duration:
                durs_ms.append(r.run_duration)
            elif r.execution_duration:
                durs_ms.append(r.execution_duration)
        total_ms = sum(durs_ms)
        total_min = total_ms / 60_000
        total_hr = total_min / 60
        total_compute_hours += total_hr
        avg_s = (total_ms / n / 1000) if n > 0 else 0

        flag = " [PAUSED]" if paused else ""
        name_display = (name + flag)[:50]
        print(f"  {name_display:<50} {sched[:22]:<22} {n:<10} {total_min:6.1f}min   {avg_s:.1f}s")

    print(f"\n  → 7일간 jobs 총 compute time: {total_compute_hours:.1f} hours")
except Exception as e:
    print(f"  ERR: {e}")

# ─────────────────────────────────────────
# 4. APPS
# ─────────────────────────────────────────
print("\n[4] APPS (24/7 runtime)")
print("=" * 80)
try:
    for app in w.apps.list():
        name = app.name or "?"
        status = app.compute_status.state.value if app.compute_status and app.compute_status.state else "?"
        print(f"  [{status:8}] {name}  url={app.url}")
        if app.resources:
            for res in app.resources:
                print(f"      resource: {res.name} ({res.description or ''})")
except Exception as e:
    print(f"  ERR: {e}")

# ─────────────────────────────────────────
# 5. ASSESSMENT — Cost driver ranking
# ─────────────────────────────────────────
print("\n\n[ASSESSMENT] Likely cost drivers (가설)")
print("=" * 80)
print("""
순위 (큰→작은):
1. Agent Bricks endpoints (mas-ba3fbcb5, ka-6b456458) — 항상 운영 시 시간당 GPU 비용
   → scale_to_zero_enabled=True 면 idle 0 비용. False면 24/7 GPU 비용.
2. Apps 24/7 runtime — 비교적 저렴 (~$0.5/hour)
3. SQL Warehouse — STOPPED이면 0. 호출 시점만 비용.
4. Jobs cron — 15min cron이 가장 빈도 높음 (gdelt + price = 192/day)
   → serverless면 짧은 run이라 누적 적음. classic compute면 idle 5-10min 누적.
5. Lakebase Postgres — scale-to-zero 24h 후. 미사용 시 0.
6. FMA pay-per-token (claude-haiku-4-5) — Mission Plan UC Function 호출마다.
""")
print("=" * 80)
