# Crude Compass

> **Pre-emptive Bidirectional Decision Support Agent for Korean Petroleum Refineries**
>
> Databricks Building Intelligent Apps Hackathon 2026 · 한국어 트랙 · Track 1 (Social Impact, Open Data) · 마감 2026-05-22

한국 정유사 매니저를 위한 양방향 위기·기회 신호 감지 AI Agent. 위기 신호 누적 시 Pre-emptive Hedge Mission (Term ↑), 약세 신호 누적 시 Pre-emptive Opportunity Mission (Spot ↑) 자동 제안. 100% open data, 결정은 사람·자율은 AI·동기화는 Lakebase.

## 핵심 문서

| 문서 | 내용 |
|---|---|
| [docs/crude_compass_final_scenario.md](docs/crude_compass_final_scenario.md) | 시나리오 (logic ground truth) |
| [docs/progress_summary.md](docs/progress_summary.md) | 진행 상황 요약 (비기술자 친화) |
| [docs/self_evaluation.md](docs/self_evaluation.md) | 자체 평가 기준 + milestone별 self-eval |
| [docs/phase1_research.md](docs/phase1_research.md) | 사전 조사 (해커톤 공식 5축 + 도구 매트릭스) |
| [docs/phase2_critique.md](docs/phase2_critique.md) | 시나리오 비평 (D-12 archive — 결론은 scenario에 반영됨) |
| [docs/architecture.md](docs/architecture.md) | 시스템 architecture (4 Agent + 12 Job + Apps + Slack Bot) |
| [docs/data_model.md](docs/data_model.md) | Bronze/Silver/Gold Delta + Lakebase Postgres DDL |
| [docs/api_contract.md](docs/api_contract.md) | FastAPI route + Pydantic + TS 타입 |
| [docs/sync_protocol.md](docs/sync_protocol.md) | Slack ↔ Apps 5초 SLA 동기화 protocol |
| [docs/d2_runbook.md](docs/d2_runbook.md) | D-2 (5/16) workspace 작업 가이드 |
| [docs/deploy_guide.md](docs/deploy_guide.md) | Databricks Apps 배포 가이드 |
| [docs/genie_certified_queries.md](docs/genie_certified_queries.md) | Genie Space 등록용 5개 certified query |
| [docs/superpowers/specs/2026-05-20-time-axis-redesign-spec.md](docs/superpowers/specs/2026-05-20-time-axis-redesign-spec.md) | D-2 Time-Axis Redesign spec (Case Thread / Live Pulse / Lifecycle / Daily Loop / Self-Narration) |
| [docs/superpowers/plans/2026-05-20-time-axis-redesign.md](docs/superpowers/plans/2026-05-20-time-axis-redesign.md) | D-2 Time-Axis Redesign 실행 plan (25 tasks) |

## 디렉토리 구조

```
crude-compass/
├── docs/                    ← 시나리오·설계 문서
├── design/                  ← Claude Design export (시각 mockup)
├── databricks/              ← Asset Bundle, Jobs, Agents, Schemas
│   ├── databricks.yml
│   ├── jobs/
│   ├── notebooks/
│   ├── agents/
│   └── schemas/
├── backend/                 ← FastAPI + Slack Bolt + Lakebase DAL (uv)
│   ├── pyproject.toml
│   ├── app/
│   └── tests/
├── frontend/                ← Vite + React 18 + TS + Tailwind + shadcn (3 페이지)
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── design-system/   ← 토큰·atomic 컴포넌트 (재사용)
│       ├── features/        ← page 단위
│       ├── hooks/
│       └── lib/
└── scripts/
    ├── _backfill_reports.py    ← 실데이터 보고서 재생성(데모)
    ├── apply_schemas.py        ← UC 스키마 적용
    └── verify_data_quality.py  ← 데이터 품질 점검
```

## Quick Start (Sprint 1 진입 후)

```powershell
# Backend (uv)
cd backend
uv sync
uv run python -m app.main

# Frontend (pnpm)
cd ../frontend
pnpm install
pnpm dev

# Databricks bundle
databricks bundle deploy --target dev
```

## 5분 데모

5/22 제출 영상 — 60% pre-recorded + 40% live (Phase 3 Slack ↔ Apps 5초 sync만 라이브).

## 스택

| Layer | 기술 |
|---|---|
| Frontend | Vite 5 + React 18 + TypeScript 5 + Tailwind 3 + shadcn/ui |
| Backend | FastAPI + Pydantic v2 + Slack Bolt + uv (Python 3.11+) |
| Data | Databricks Unity Catalog (Bronze/Silver/Gold Delta) + Lakebase Postgres (OLTP) |
| AI | Foundation Model API (Claude Haiku 4.5) + Agent Bricks Custom Agents (Mission Plan) |
| Sync | FastAPI WebSocket + Lakebase Lakehouse Sync (CDC) |
| Analytics | AI/BI Dashboard (Apps embed) |

## 외부 비용

**$19** (OilPriceAPI Standard plan, 5/15-22 8일).

## 라이선스

Hackathon submission. License 추가 예정.
