# Crude Compass

> **Term/Spot Decision Support Agent for Korean Petroleum Refineries**
> Databricks APJ Hackathon 2026 / 한국어 트랙 / Track 1 (Social Impact, Open Data)
> 마감 2026-05-22

한국 정유사 매니저가 매월 원유 도입 시 Term(장기계약) vs Spot(현물) 비중을 결정할 때, 24/7 모니터링·시나리오 시뮬레이션·자동 RFQ로 의사결정 지원하는 SaaS. **결정은 사람, 정보 우위는 AI.**

## Repo 구조

```
crude-compass/
├─ docs/
│  ├─ scenario.md               # 시나리오 source of truth
│  └─ architecture.md           # Architecture v2 (검증 패턴 포함)
├─ design/                      # Claude Design 디자인 (수정 X — reference)
│  ├─ index.html
│  └─ src/*.jsx
├─ apps/
│  ├─ web/                      # Vite + React 18 + TypeScript + Tailwind v4
│  └─ api/                      # FastAPI + uv + Lakebase OAuth
├─ databricks/                  # (Phase 1+) ingestion, jobs, agents, genie
├─ infra/                       # (Phase 1) Lakebase schema, Bronze DDL
├─ app.yaml                     # Databricks Apps deploy spec
└─ README.md
```

## 4-tool 매핑

| Tool | 역할 |
|---|---|
| Apps | Vite + React + FastAPI 단일 프로세스 (Discovery / Mission / Yesterday) |
| Genie | Conversation API 4중 fallback chain (Mission 인라인 + Yesterday Genie bar) |
| Lakebase | OAuth refresh wrapper + 4 tables (missions/events/rfq/decisions) |
| Agent Bricks | Custom Agents (Plan A 4종 / Plan B 2종) |
| AI/BI Dashboard | Yesterday Review iframe embed |

## 로컬 개발

```bash
# Frontend (Vite dev server :5173)
cd apps/web
npm install
npm run dev

# Backend (FastAPI :8000)
cd apps/api
uv sync
uv run uvicorn apps.api.main:app --reload --port 8000
```

Vite가 `/api/*` 를 FastAPI로 proxy. 두 서버 동시에 띄우면 풀 스택 hot reload.

## Deploy (Databricks Apps)

```bash
# Build
cd apps/web && npm run build       # apps/web/dist 생성
cd apps/api && uv sync             # Python deps

# Deploy
databricks apps deploy crude-compass --source .
```

`app.yaml`이 단일 uvicorn 프로세스 띄움 → FastAPI가 `apps/web/dist` 정적 serve + `/api/*` route.
