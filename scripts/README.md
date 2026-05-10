# Scripts — Crude Compass

Sprint 별 실행 스크립트 모음. backend uv 환경 사용.

## 실행 방법

```powershell
# backend uv 환경 진입
cd backend

# 환경변수 (Lakebase + API key)
$env:LAKEBASE_HOST = "ep-lucky-star-d1rlmmrr-pooler.database.us-west-2.cloud.databricks.com"
$env:LAKEBASE_DATABASE = "databricks_postgres"
$env:LAKEBASE_ENDPOINT_PATH = "projects/crude-compass-pg/branches/production/endpoints/primary"
$env:LAKEBASE_USER = "hyeongwook.lee@lginnotek.com"
$env:OILPRICE_API_KEY = "<key>"
$env:DATABRICKS_CONFIG_PROFILE = "crude-compass"

# 실행
uv run python ../scripts/<script_name>.py
```

> ⚠️ 실제 운영에서는 `dbutils.secrets.get(scope='crude', ...)` 사용. 로컬 테스트용으로만 환경변수.

## Sprint 1 검증 스크립트

| 파일 | 목적 | DoD |
|---|---|---|
| `oilpriceapi_endpoint_check.py` | OilPriceAPI batch (3 ticker 1 call) 가능 여부 | "batch OK" 또는 "1-by-1 only" 출력 |
| `lakebase_dialect_test.py` | Lakebase Postgres dialect — JSONB / UUID / version optimistic concurrency | INSERT 1건 + version conflict 시뮬 + 정리 |
| `seed_mock_backtest.py` | RSS archive 5개월 (2025-12 ~ 2026-04) fetch — Mock backtest 78%/71% 산출용 | sample 10건 fetch 성공 (Sprint 3 본격 사용) |

## Sprint 2-3 추가 예정

- `inject_demo_signals.py` — 데모 평가위원 inject 트리거
- `run_lakebase_ddl.py` — `databricks/schemas/lakebase.sql` 자동 적용
- `backtest_signals.py` ⭐ — 5개월 RSS archive backtest, HEDGE 78% / OPP 71% 산출 (Sprint 3 ⭐ critical)
