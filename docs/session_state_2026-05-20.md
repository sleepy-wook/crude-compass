# Session State — 2026-05-20 (D-2)

> compact 후 resume 시 이 파일부터 read.
> 기존 docs (p0_implementation_plan.md / demo_script_5min.md / local_dev_guide.md) 와 보완.

---

## 🎯 Where we are (D-2, 마감 2026-05-22)

**프로젝트 상태**: production deploy 안정. P0 코드 작업 완료. 영상 녹화 + 최종 visual check 남음.

**최근 commit (시간순)**:
- `9e21662` perf(d2) — 9 notebook의 `restartPython()` 60s overhead 제거
- `edaef1b` feat(d2) Phase D — 6 액션 의미 분리 + 차트 polish + 2 sub-pages + ChatGPT 풍 Investigation
- `5a7082d` Phase C — staleTime + prefetch + Dashboard width
- `599289b` Phase B — Market Watch daily toggle + Investigation 다이어그램 collapse
- `d04e827` Phase A — 11개 polish (드래그 색 / TopBar / tooltip / filter 등)
- `c26e031` UI/UX + text agent review fixes

**남은 작업 (사용자 명시 요청)**:
1. **Evaluator agent spawn** — Claude Preview MCP로 localhost 자동 점검 (선택 A로 합의)
2. **새 피드백 처리** — 사용자가 로컬에서 직접 보고 줄 feedback
3. **데모 영상 녹화** (`docs/demo_script_5min.md` 그대로)

---

## 🔑 Critical facts (외워둘 것)

| 항목 | 값 |
|---|---|
| Workspace | `dbc-437c7d62-5826.cloud.databricks.com` |
| Apps URL | `https://crude-compass-7474656526809380.aws.databricksapps.com` |
| Supervisor endpoint | `mas-ba3fbcb5-endpoint` |
| KA endpoint | `ka-6b456458-endpoint` (`crude-compass-ka`) |
| Genie Space | `Crude Oil Market Analysis` |
| UC Function | `mission_plan_advice` (Bidirectional decision advisor) |
| 1개 active mission | `001353e8-0bf8-46a9-92a5-6725642609c0` (HEDGE Pattern Score 100, Term 75%) |
| Lakebase | `ep-lucky-star-d1rlmmrr.database.us-west-2.cloud.databricks.com` / `databricks_postgres` |
| Profile (PAT, prod) | `crude-compass` |
| Profile (U2M, local) | `crude-compass-u2m` (D-2 setup, browser auth 1회) |

**4기능 narrative 정직 표기 (변경 금지)**:
- Apps = manager-facing decision room
- Lakebase = case memory + agent_activity_events
- Genie = structured market specialist (Supervisor subagent)
- Agent Bricks = Supervisor + Knowledge Assistant 2개 등록 + 3 subagent orchestration
- Mission Plan = FMA (backend) + UC Function (mission_plan_advice). **"Agent Bricks"라고 부르면 X — 정직성**

---

## 🗂 페이지 IA (사이드바 4탭 mantra 유지)

- `/` Decision Room
- `/market` Market Watch (`/evidence` 서브: OPEC + 주요 보도 게시판)
- `/ask` Investigation (`/backtest` 서브: 과거 권고 검증)
- `/missions`, `/missions/:id` Case File

**핵심 신규 컴포넌트**:
- `AgentActivityTimeline` (compact / full) — Lakebase `agent_activity_events` 실 기록
- `SuggestedNextActions` — 6 액션 (Approve / Adjust / Dismiss / Keep Watching / Ask for More / Re-check Later)
  - Keep Watching = pivot:pause (보류, 모니터링만)
  - Re-check Later = modify:duration+14 (기간 연장)

**용어 정책** (rename 금지):
- 코드 식별자: `Mission` interface, `mission_id`, `/api/missions/*` 그대로
- 사용자 visible: "case" / "결정 케이스" (이미 다 정리됨)
- Term/Spot 영문 / 위험방어·기회포착 한글

---

## 💻 Local Dev — 현재 작동 중

`.env` 변경됨:
- `DATABRICKS_CONFIG_PROFILE=crude-compass-u2m`
- `USE_LAKEBASE=true`
- `DEMO_MODE=true`

실행:
```bat
scripts\dev_local.bat
```
- Backend: http://localhost:8000
- Frontend: http://localhost:5173 (vite HMR)

**OAuth U2M token 1시간 expire** — 만료 시 `databricks auth login --host <ws-url> --profile crude-compass-u2m` 재실행.

prod 복원: `.env`의 `DATABRICKS_CONFIG_PROFILE`을 `crude-compass`로 변경 (또는 `.env.bak` 복원).

---

## 💰 Credit cleanup (D-2 적용 완료)

**삭제**:
- `ais-batch` job (PAUSED인데 5분 cron 계속 firing INTERNAL_ERROR 1238 runs/week)

**변경**:
- `gdelt-15min` → 30min cron (487 → 244 runs/week)
- 9 notebook의 `%pip install` + `dbutils.library.restartPython()` 60s overhead 제거 → subprocess pip pattern

**예상 절약**: 65-114h compute/week.

bundle 재배포 후 gdelt 1회 manual trigger 검증 권장 — duration 205s → 140s 목표.

---

## 🚦 다음 step (사용자 명시)

**즉시 진행**:
- Evaluator agent spawn (선택 A 합의 — Claude Preview MCP)
- localhost:5173 자동 점검 → 5축 점수 + 개선 권고
- 사용자가 직접 피드백 후 iteration

**Spawn 가능 명령**:
```
"localhost:5173 evaluator agent 호출해줘"
또는
"docs/session_state_2026-05-20.md read 후 evaluator 호출"
```

evaluator agent type 이미 정의됨 — Claude Preview MCP 도구 사용.

---

## 📜 User context 기억할 것

- 형욱님 (hyeongwook.lee@lginnotek.com), LG Innotek Gen AI Engineer
- 한국어 terse 선호. **약점 보이면 즉시 근거 있는 push back, 무지성 공감 X**
- "Databricks workspace는 사용자에게 위임" — workspace UI / deploy는 사용자가 직접
- 프론트엔드 코드 100% 사용자 (친구분은 기획/디자인 only)

---

## 🗺 Doc map (compact 후 read 우선순위)

1. **이 파일** (`session_state_2026-05-20.md`) — 현재 상태
2. `docs/p0_implementation_plan.md` — P0 13개 작업 plan + 완료 표시
3. `docs/demo_script_5min.md` — 5분 영상 script
4. `docs/local_dev_guide.md` — 로컬 dev 환경
5. `docs/ui_ux_review_2026-05-20.md` — UI/UX agent 보고서 (참고용)
6. `docs/text_review_2026-05-20.md` — 텍스트 교정 보고서 (참고용)
7. `docs/crude_compass_final_scenario.md` — ground truth 시나리오 (변경 X)

---

끝.
