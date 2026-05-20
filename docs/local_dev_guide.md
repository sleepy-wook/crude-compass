# Local Dev Guide — backend + frontend 즉시 iterate

> 매 변경마다 `databricks bundle deploy` + Apps redeploy 사이클을 돌리지 않고 로컬에서 즉시 확인.

## 실행

### 단축 — 한 번에 둘 다 (Windows)
```bat
scripts\dev_local.bat
```
→ 2개 cmd 창 자동 spawn (backend + frontend).

### 수동 — 두 터미널 따로
**Terminal 1 (backend)**:
```bat
cd backend
set PYTHONIOENCODING=utf-8
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 (frontend)**:
```bat
cd frontend
npm run dev
```

### 접속
- Frontend: http://localhost:5173 (vite HMR — code 저장 시 즉시 반영)
- Backend: http://localhost:8000 (uvicorn `--reload` — Python 저장 시 자동 restart)
- Backend health: http://localhost:8000/api/health

---

## 동작 / 제약 정리

### ✅ 로컬에서 잘 됨
| 영역 | 비고 |
|---|---|
| Frontend UI 모든 페이지 | Decision Room / Market Watch / Investigation / Case File / Evidence / Backtest |
| Pattern Score / 시장 데이터 | Databricks SQL warehouse statement_execution — PAT로 호출 |
| Market 차트 (price / FX / news / OPEC) | 동일 SQL warehouse path |
| Supervisor endpoint 호출 | PAT으로 `client.responses.create()` |
| Genie 4-tier fallback | PAT 호출 |
| Mission CRUD (in-memory) | 2 seed mission (HEDGE 82 / OPP 22) — backend 재시작 시 reset |
| WebSocket | uvicorn 기본 지원 |

### ⚠️ 로컬에서 안 되거나 제한
| 영역 | 원인 | workaround |
|---|---|---|
| **Lakebase Postgres 직접 연결** | PAT은 JWT 아니라 Lakebase reject | 로컬 PAT으로는 안 됨. 필요 시 Apps env에서만 |
| **`agent_activity_events` table 읽기/쓰기** | Lakebase 의존 | API `events:[]` 빈 응답 — AgentActivityTimeline 안 보임 |
| **Slack interactive button** | Slack이 외부 URL로 callback 발송 | ngrok 등 tunnel 필요 (선택) |
| **mission 영속화** | in-memory store — backend 재시작 시 사라짐 | demo 데이터는 production 사용 |

---

## 개발 흐름

1. `scripts\dev_local.bat` → 두 창 띄움
2. http://localhost:5173 접속
3. 코드 변경 → 저장
   - Frontend (.tsx/.ts): vite HMR이 즉시 반영 (페이지 새로고침 X)
   - Backend (.py): uvicorn `--reload`로 자동 restart (~1-2s)
4. 만족스러우면 production deploy:
   - `git add` + `git commit` + `git push origin main`
   - `databricks --profile crude-compass apps deploy crude-compass`

---

## 환경 변수 (`.env`)

이미 `backend/.env`에 PAT + Lakebase config + Slack secrets 있음.

로컬 모드에서 사용:
- `DATABRICKS_CONFIG_PROFILE=crude-compass` ✓ (PAT 인증)
- `SUPERVISOR_ENDPOINT_NAME=mas-ba3fbcb5-endpoint` ✓
- `GENIE_SPACE_ID=...` ✓
- Lakebase env vars는 있지만 PAT JWT issue로 무시됨

`USE_LAKEBASE=true`로 강제하면 connection pool 시도 → fail → fallback to in-memory + warning log.

---

## 자주 발생하는 issue

### `Port 8000 already in use`
이전 uvicorn 안 종료. Task manager에서 python.exe kill.

### `cors: ...`
frontend가 localhost:5173 아닌 곳에서 띄워짐. 또는 backend가 안 켜짐. main.py:78 CORS 확인.

### `cannot connect to localhost:8000` (frontend)
backend 안 켜짐. terminal 1 확인. `uvicorn` 명령 입력 확인.

### Lakebase 관련 warning 무한 반복
무시 OK — 로컬에서 fallback path로 자동 우회.

---

끝.
