# Crude Compass — Databricks 학습 노트

> Databricks를 이번 프로젝트로 학습하면서 만든 강의 노트.
> 우리가 **실제로 사용하는** 8개 기능에 한정. 일반적인 docs 요약 X, 우리 코드 path와 1:1 매칭.

## Round 1 — 데이터 인프라 (Phase 1)

| # | 노트 | 사용처 | 우리 코드 |
|---|---|---|---|
| 01 | [Unity Catalog + Delta Lake](01_unity_catalog_delta.md) | bronze 6 tables 집 | `infra/sql/bronze_schema.sql` |
| 02 | [Lakebase Autoscaling Postgres](02_lakebase_postgres.md) | mission state 영속 | `apps/api/services/lakebase.py` · `infra/sql/lakebase_schema.sql` |
| 03 | [Lakeflow Jobs (+ Secret)](03_lakeflow_jobs.md) | Tier 1 Daily + Tier 2 5분 cron | `databricks/ingestion/oil_prices.py` |
| 04 | [Workflow continuous task](04_workflow_continuous.md) | AIS WebSocket 24/7 | `databricks/workflows/ais_continuous.py` |

## Round 2 — Apps + AI (Phase 2~3) — 작성 예정

| # | 노트 | 사용처 |
|---|---|---|
| 05 | Databricks Apps | Vite + React + FastAPI 단일 컨테이너 deploy |
| 06 | Genie Conversation API | Mission 인라인 + Yesterday "다시 묻기" |
| 07 | Agent Bricks Custom Agents (+ MLflow) | Monitoring · Simulation · RFQ Chaining · Self-Critique |
| 08 | AI/BI Dashboard | Yesterday Review iframe embed |

## 노트 사용법

각 노트는 약 500~700줄, 5~10분 안에 읽을 수 있게 구성.
- **1) 한 줄 요약** — 머리 정리용
- **2) 핵심 개념** — 처음 보는 용어 5~7개 정의
- **3) 우리 코드와 매칭** — 이론 → repo 실제 파일
- **4) 자주 헷갈리는 점** — 디버깅 시 즉답
- **5) 5분 데모에 등장하는지** — 평가위원 질문 대비
- **6) 더 깊이 파려면** — 공식 docs URL 4~5개 (모두 검증됨)

## 검증

모든 출처는 `docs.databricks.com` 에서 직접 fetch로 확인 (2026-05). 추측·기억 없음. 확인 안 된 부분은 노트 안에 "확인 안 됨"으로 명시.
