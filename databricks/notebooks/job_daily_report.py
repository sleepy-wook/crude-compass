# Databricks notebook source
# MAGIC %md
# MAGIC # job_daily_report — 06:30 KST 종합 보고서 cron
# MAGIC
# MAGIC 매일 06:30 KST. 어제 매니저가 보관한 reports + 어제 daily_report + 시장 snapshot →
# MAGIC Haiku-4-5로 종합 + ratio_suggestion 생성 → Lakebase `daily_reports` INSERT.
# MAGIC
# MAGIC 구현 전략: backend Apps `POST /api/admin/daily-report/generate-now` 호출.
# MAGIC - 모든 logic은 backend `app/services/daily_report.py` (single source of truth, tested).
# MAGIC - notebook은 thin trigger + activity emit + Slack push (Phase 8).
# MAGIC
# MAGIC Failure mode: backend 미도달 / LLM 실패 → notebook 실패 (job 알람).

# COMMAND ----------

import importlib
import subprocess
import sys


def _ensure_package(import_name: str, install_spec: str):
    try:
        importlib.import_module(import_name)
    except ImportError:
        print(f"  installing {install_spec}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", install_spec])


_ensure_package("httpx", "httpx==0.28.1")

import json
import os
from datetime import datetime, timezone, timedelta

import httpx

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

# Apps URL — workspace secret 또는 env var.
# 첫 deploy 후 https://crude-compass-{workspace_id}.aws.databricksapps.com 형태.
APPS_URL = None
try:
    from pyspark.dbutils import DBUtils  # type: ignore
    from pyspark.sql import SparkSession
    spark = SparkSession.builder.getOrCreate()
    dbutils = DBUtils(spark)
    try:
        APPS_URL = dbutils.secrets.get(scope="crude", key="apps_url")
    except Exception:
        APPS_URL = None
except Exception:
    spark = None
    dbutils = None

if APPS_URL is None:
    APPS_URL = os.getenv("APPS_URL")

if APPS_URL is None:
    # Fallback hardcoded — workspace_id 7474656526809380 (production)
    APPS_URL = "https://crude-compass-7474656526809380.aws.databricksapps.com"

print(f"APPS_URL: {APPS_URL}")

# 오늘 (KST) 날짜 — backend도 동일 계산하지만 명시적 전달이 더 안전
NOW_KST = datetime.now(timezone.utc) + timedelta(hours=9)
TARGET_DATE = NOW_KST.date().isoformat()
print(f"TARGET_DATE (KST): {TARGET_DATE}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: OAuth token 발급 (Service Principal)

# COMMAND ----------

from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
auth = w.config.authenticate()
auth_token = auth.get("Authorization", "")
if not auth_token:
    raise RuntimeError("SP authenticate() returned no Authorization header")
print(f"auth token prefix: {auth_token[:20]}...")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: backend Apps에 generate-now POST

# COMMAND ----------

endpoint = f"{APPS_URL}/api/admin/daily-report/generate-now"
params = {"target_date": TARGET_DATE, "overwrite": "true"}
headers = {"Authorization": auth_token}

print(f"POST {endpoint}")
print(f"params: {params}")

try:
    with httpx.Client(timeout=120.0) as client:
        resp = client.post(endpoint, params=params, headers=headers)
    resp.raise_for_status()
    result = resp.json()
    print(f"response: {json.dumps(result, ensure_ascii=False, indent=2)}")
except httpx.HTTPStatusError as e:
    print(f"HTTP error {e.response.status_code}: {e.response.text}")
    raise
except Exception as e:
    print(f"unexpected error: {type(e).__name__}: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: activity emit (Lakebase agent_activity_events)

# COMMAND ----------

# notebook 디렉토리 sys.path 추가 — _lakebase_emit import 위해
notebook_dir = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else "/Workspace/Users/hyeongwook.lee@lginnotek.com/.bundle/crude-compass/dev/files/databricks/notebooks"
if notebook_dir not in sys.path:
    sys.path.insert(0, notebook_dir)

try:
    from _lakebase_emit import emit as _emit
    if result.get("ok"):
        _emit(
            actor="daily_report",
            action="report_created",
            result_preview=f"daily_report {TARGET_DATE} 생성 (daily_id={result.get('daily_id', '?')[:8]})",
            metadata={"target_date": TARGET_DATE, "daily_id": result.get("daily_id")},
        )
    else:
        _emit(
            actor="daily_report",
            action="report_failed",
            result_preview=f"daily_report {TARGET_DATE} 생성 실패: {str(result.get('error', ''))[:100]}",
            metadata={"target_date": TARGET_DATE, "error": str(result.get("error", ""))[:300]},
        )
    print("activity event emitted")
except Exception as e:
    print(f"emit skipped (best-effort): {type(e).__name__}: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: 결과 확인 (debugging only)

# COMMAND ----------

# 생성된 daily_report fetch
try:
    with httpx.Client(timeout=30.0) as client:
        verify = client.get(f"{APPS_URL}/api/daily-reports/{TARGET_DATE}", headers=headers)
    if verify.status_code == 200:
        body = verify.json()["daily_report"]
        print(f"daily_id:       {body['daily_id']}")
        print(f"kept_count:     {body['kept_count']}")
        print(f"direction:      {(body.get('ratio_suggestion') or {}).get('direction')}")
        print(f"term_delta:     {(body.get('ratio_suggestion') or {}).get('term_delta_pct')}")
        print(f"spot_delta:     {(body.get('ratio_suggestion') or {}).get('spot_delta_pct')}")
        print(f"confidence:     {body['confidence']}")
        print()
        print("kept_summary:")
        print(f"  {body.get('kept_summary')}")
        print()
        print("reasoning:")
        print(f"  {body.get('reasoning')}")
    else:
        print(f"verify GET returned {verify.status_code}: {verify.text}")
except Exception as e:
    print(f"verify skipped: {type(e).__name__}: {e}")
