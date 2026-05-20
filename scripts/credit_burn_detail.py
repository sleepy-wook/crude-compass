"""Detail probe — ais-batch / backtest-llm / endpoint scale-to-zero."""
import os
import sys
import io
from pathlib import Path
from datetime import datetime, timedelta, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

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

print("=== DETAIL PROBE — 정확한 cost driver 식별 ===\n")

# ─────────────────────────────────────────
# ais-batch job 정확한 상태 확인
# ─────────────────────────────────────────
print("\n[A] AIS-BATCH job — 1238 runs in 7d! 정말 PAUSED?")
print("=" * 80)
for job in w.jobs.list():
    name = job.settings.name if job.settings else ""
    if "ais-batch" in name.lower():
        print(f"Job name: {name}")
        print(f"Job ID: {job.job_id}")
        s = job.settings
        if s and s.schedule:
            print(f"Schedule cron: {s.schedule.quartz_cron_expression}")
            print(f"Pause status: {s.schedule.pause_status}")
            print(f"Timezone: {s.schedule.timezone_id}")
        if s and s.continuous:
            print(f"Continuous: {s.continuous.pause_status}")
        if s and s.trigger:
            print(f"Trigger: {s.trigger}")
        # Last 5 runs
        print("\nLast 5 runs:")
        try:
            since = datetime.now(timezone.utc) - timedelta(days=7)
            since_ms = int(since.timestamp() * 1000)
            for r in list(w.jobs.list_runs(job_id=job.job_id, limit=5)):
                dur_min = (r.run_duration or 0) / 60_000
                state = r.state.life_cycle_state.value if r.state and r.state.life_cycle_state else "?"
                start = datetime.fromtimestamp((r.start_time or 0)/1000, timezone.utc).isoformat() if r.start_time else "?"
                print(f"  run {r.run_id} start={start[:19]} state={state} dur={dur_min:.1f}min trigger={r.trigger}")
        except Exception as e:
            print(f"  runs ERR: {e}")
        break

# ─────────────────────────────────────────
# backtest-llm — 5 runs / 189 min = avg 38min/run
# ─────────────────────────────────────────
print("\n\n[B] BACKTEST-LLM — 5 runs / 189 min (avg 38min each)")
print("=" * 80)
for job in w.jobs.list():
    name = job.settings.name if job.settings else ""
    if "backtest-llm" in name.lower():
        print(f"Job name: {name}")
        s = job.settings
        if s and s.schedule:
            print(f"Schedule: {s.schedule.quartz_cron_expression} pause={s.schedule.pause_status}")
        if s and s.trigger:
            print(f"Trigger: {s.trigger}")
        try:
            for r in list(w.jobs.list_runs(job_id=job.job_id, limit=5)):
                dur_min = (r.run_duration or 0) / 60_000
                state = r.state.life_cycle_state.value if r.state and r.state.life_cycle_state else "?"
                start = datetime.fromtimestamp((r.start_time or 0)/1000, timezone.utc).isoformat() if r.start_time else "?"
                print(f"  run {r.run_id} start={start[:19]} state={state} dur={dur_min:.1f}min trigger={r.trigger}")
        except Exception as e:
            print(f"  ERR: {e}")
        break

# ─────────────────────────────────────────
# Agent Bricks endpoints — scale-to-zero 확인
# ─────────────────────────────────────────
print("\n\n[C] AGENT BRICKS ENDPOINTS — scale-to-zero?")
print("=" * 80)
for name in ["ka-6b456458-endpoint", "mas-ba3fbcb5-endpoint"]:
    print(f"\nEndpoint: {name}")
    try:
        ep = w.serving_endpoints.get(name=name)
        if ep.config:
            for se in (ep.config.served_entities or []):
                full = {}
                for attr in dir(se):
                    if attr.startswith("_"): continue
                    try:
                        v = getattr(se, attr)
                        if v is None or callable(v): continue
                        if hasattr(v, 'value'):
                            v = v.value
                        full[attr] = v
                    except Exception:
                        pass
                print(f"  entity: {full}")
            for sm in (ep.config.served_models or []):
                full = {}
                for attr in dir(sm):
                    if attr.startswith("_"): continue
                    try:
                        v = getattr(sm, attr)
                        if v is None or callable(v): continue
                        if hasattr(v, 'value'):
                            v = v.value
                        full[attr] = v
                    except Exception:
                        pass
                print(f"  model: {full}")
        print(f"  state: ready={ep.state.ready.value if ep.state and ep.state.ready else '?'}")
        print(f"  creator: {ep.creator}")
    except Exception as e:
        print(f"  ERR: {e}")

# ─────────────────────────────────────────
# gdelt-15min long run reason
# ─────────────────────────────────────────
print("\n\n[D] GDELT-15min — avg 205s (3.4min) 왜 김?")
print("=" * 80)
for job in w.jobs.list():
    name = job.settings.name if job.settings else ""
    if "gdelt-15min" in name.lower():
        try:
            for r in list(w.jobs.list_runs(job_id=job.job_id, limit=5)):
                dur_s = (r.run_duration or 0) / 1000
                state = r.state.life_cycle_state.value if r.state and r.state.life_cycle_state else "?"
                start = datetime.fromtimestamp((r.start_time or 0)/1000, timezone.utc).isoformat() if r.start_time else "?"
                print(f"  run {r.run_id} start={start[:19]} state={state} dur={dur_s:.0f}s")
        except Exception as e:
            print(f"  ERR: {e}")
        break

print("\n=== End ===")
