"""Credit cleanup — ais-batch delete + 상황 dump.

Safe ops only:
1. DELETE ais-batch (PAUSED but firing INTERNAL_ERROR 1238x/week = pure waste)
2. Report on backtest-llm (manual job, no recurring) — leave alone
3. Report on gdelt-15min (data freshness impact — 사용자 결정 대기)

User explicit consent: "너가 직접 할 수 있는건 해줘"
"""
import os
import sys
import io
from pathlib import Path

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

AIS_BATCH_JOB_ID = 789784434326986

print(f"=== Credit cleanup ===\n")

# 1. ais-batch 현 상태 재확인 (delete 전 검증)
print(f"\n[1] AIS-batch 현 상태 재확인")
print("-" * 60)
try:
    job = w.jobs.get(job_id=AIS_BATCH_JOB_ID)
    print(f"  Name: {job.settings.name}")
    print(f"  Created: {job.created_time}")
    if job.settings.schedule:
        print(f"  Schedule: {job.settings.schedule.quartz_cron_expression}")
        print(f"  Pause status: {job.settings.schedule.pause_status}")
    # 최근 1 run state
    recent = list(w.jobs.list_runs(job_id=AIS_BATCH_JOB_ID, limit=1))
    if recent:
        r = recent[0]
        print(f"  Last run state: {r.state.life_cycle_state} / result: {r.state.result_state}")
except Exception as e:
    print(f"  ERR: {e}")
    sys.exit(1)

# 2. DELETE
print(f"\n[2] AIS-batch DELETE 실행")
print("-" * 60)
try:
    w.jobs.delete(job_id=AIS_BATCH_JOB_ID)
    print(f"  ✓ deleted job_id={AIS_BATCH_JOB_ID}")
except Exception as e:
    print(f"  ✗ FAIL: {e}")
    sys.exit(1)

# 3. 삭제 후 list 검증
print(f"\n[3] 삭제 후 jobs 목록 (ais-batch 안 보여야)")
print("-" * 60)
ais_found = False
for j in w.jobs.list():
    name = j.settings.name if j.settings else ""
    if "ais-batch" in name.lower():
        ais_found = True
        print(f"  STILL EXISTS: {name} (id={j.job_id})")
if not ais_found:
    print(f"  ✓ ais-batch 완전 제거됨")

print(f"\n=== Cleanup done ===")
print(f"\nExpected savings (7d):")
print(f"  - 1238 runs × 0.5min/run = ~619 minutes = ~10.3 compute hours saved")
print(f"  - Serverless minimum charge (5min) 가정 시 1238 × 5min = 103 hours saved")
print(f"  - 어느 쪽이든 비용 크게 절감")
print(f"\n남은 대기 결정 (사용자):")
print(f"  - gdelt-15min cron 15min → 30min (freshness 약간 떨어짐, 비용 50%↓)")
print(f"  - backtest-llm-dev: 수동 job, recurring 아님. 그대로 두기 OK.")
