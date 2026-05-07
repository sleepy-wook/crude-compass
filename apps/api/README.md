# crude-compass-api

FastAPI backend for Crude Compass. Serves Vite dist (production) + `/api/*` routes.

## 로컬 개발

```bash
# venv 생성 + 의존성
cd apps/api
uv sync

# 환경 변수 (로컬 dev — Apps에선 자동 주입)
cp .env.example .env
# .env 편집

# 서버
uv run uvicorn apps.api.main:app --reload --port 8000
```

Vite dev server는 `:5173`에서 `/api/*` 를 `:8000`으로 proxy. 두 서버 동시 띄우면 풀 스택 hot reload.

## Production (Databricks Apps)

`app.yaml`이 root에. uvicorn이 `$DATABRICKS_APP_PORT` 단일 포트 점유. FastAPI가 `apps/web/dist`를 정적 serve + `/api/*` route. 단일 프로세스 단일 컨테이너.

## Endpoints

- `GET /api/health` — liveness
- `GET /api/health/lakebase` — Lakebase OAuth + SELECT 1 검증
- (Phase 1+) `GET /api/feed`, `GET /api/mission/:id`, `POST /api/genie`, `POST /api/decision`, `GET /api/dashboard/token`
