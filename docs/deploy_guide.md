# Databricks Apps Deploy Guide

> 작성: 2026-05-14 D-4. 업데이트: 2026-05-17 D-1 (Git source + 자동 build pipeline).
> 의존: `app.yaml`(root) + `package.json`(root) + `requirements.txt`(root) + `frontend/` + `backend/` + `crude-compass` profile + `crude` secret scope.

---

## 1. 사전 준비

### 1.1 Repo 구조 (5/17 D-1 시점)

```
crude-compass/
├── app.yaml                    ← Databricks Apps manifest (command + env)
├── package.json                ← root build wrapper (npm run build → cd frontend && npm ci && build)
├── requirements.txt            ← root Python deps (backend/pyproject.toml export)
├── backend/
│   ├── pyproject.toml + uv.lock
│   └── app/main.py             ← FastAPI entry (--app-dir backend)
├── frontend/
│   ├── package.json
│   ├── package-lock.json       ← npm lock (pnpm-lock.yaml 5/17 제거)
│   └── dist/                   ← Apps 자동 build 결과 (gitignored)
└── databricks/
```

⚠️ 핵심: Databricks Apps는 **root의 package.json + requirements.txt만 인식** (subdirectory recurse X). frontend 빌드 trigger를 root scripts에 delegate.

### 1.2 Secret scope (10개)

```bash
databricks --profile crude-compass secrets list-secrets crude
# 필요 secrets (모두 등록되어있어야):
# - lakebase_host / lakebase_database / lakebase_user / lakebase_endpoint_path
# - slack_bot_token / slack_signing_secret / slack_default_channel
# - oilprice_api_key / ecos_api_key / eia_api_key
# (5/16 D-2: aisstream_api_key 제거 — AIS Stream source 완전 폐기)
```

미등록 시:
```bash
databricks --profile crude-compass secrets put-secret crude <key> --string-value "<value>"
```

### 1.3 Apps Resources (12개)

Apps UI → crude-compass → Settings → Resources:
- **Secret × 10** (위 list, scope=`crude`, resource key는 secret key와 정확 일치 — app.yaml `valueFrom` 매칭)
- **Genie space × 1** (`crude-compass-genie` aka "Crude Oil Market Analysis", resource key `genie_space_id`, Can run)
- **Serving endpoint × 1** (Supervisor `mas-ba3fbcb5-endpoint`, resource key `supervisor_endpoint_name`, Can query)
- **(D-1 추가 예정) Database × 1** — Lakebase instance, resource key `lakebase_db`, CAN USE → SP의 PG OAuth role mapping 해제

---

## 2. Deploy 방식 — Git Source (Option B, D-2 5/16 swap)

### 2.1 Git source 설정 (1회만)

Apps Settings → General → Source:
- Git provider: GitHub
- Repository URL: `https://github.com/sleepy-wook/crude-compass.git`
- Reference type: Branch
- Branch: `main`

### 2.2 매번 deploy

```powershell
# (1) 코드 변경 + commit + push
git push origin main

# (2) Apps deploy trigger (Git source 자동 fetch + auto build)
databricks --profile crude-compass apps deploy crude-compass
```

또는 SDK:
```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.apps import AppDeployment, AppDeploymentMode
w = WorkspaceClient(profile='crude-compass')
w.apps.deploy(app_name='crude-compass', app_deployment=AppDeployment(mode=AppDeploymentMode.SNAPSHOT))
```

### 2.3 자동 build pipeline (Apps 내부 동작)

```
[1/5] git clone main branch
[2/5] root package.json 감지 → npm install (no-op, root deps 0)
[3/5] npm run build → cd frontend && npm ci → 227 packages
                   → npm run build → vite build → frontend/dist/ 생성
[4/5] root requirements.txt 감지 → pip install (backend deps)
[5/5] command 실행: uvicorn app.main:app --host 0.0.0.0 --app-dir backend
                    └─ --app-dir backend: PYTHONPATH 추가 → app.main 모듈 import
                    └─ DATABRICKS_APP_PORT 자동 inject
```

⚠️ Apps Node runtime에 corepack/pnpm 없음 (npm만). frontend/pnpm-lock.yaml D-2 시점 삭제, package-lock.json commit.

### 2.4 배포 상태 확인

```powershell
databricks --profile crude-compass apps get crude-compass
# → app_status.state: RUNNING + url 표시
```

또는 SDK로 latest deployment + state poll.

---

## 3. Slack Interactivity URL (배포 후)

배포 후 받은 public URL 사용:

1. https://api.slack.com/apps → Crude Compass app 선택
2. 좌측 **Interactivity & Shortcuts** → Toggle **On**
3. **Request URL**: `https://crude-compass-7474656526809380.aws.databricksapps.com/api/slack/interactive`
4. **Save Changes**

이 단계 완료 후 Slack 카드에서 [Confirm] / [Reject] / [Pivot] 버튼이 작동 (양방향 5초 sync).

---

## 4. 배포 검증 (D-1 시점 production URL)

```
APP_URL=https://crude-compass-7474656526809380.aws.databricksapps.com
```

브라우저로 (Databricks OAuth 자동 로그인 필요):

| URL | 기대 응답 |
|---|---|
| `$APP_URL/api/health` | `{"status":"ok", "frontend_bundled":true}` |
| `$APP_URL/api/slack/health` | `{"enabled":true, "default_channel":"C0B343F7771"}` |
| `$APP_URL/api/genie/health` | `{"enabled":true, "space_id":"01f150e0..."}` |
| `$APP_URL/api/supervisor/health` | `{"enabled":true, "endpoint_name":"mas-ba3fbcb5-endpoint"}` |
| `$APP_URL/api/pattern-score/current` | `{"current":{"pattern_score":100.0,"mission_type":"HEDGE",...}}` |
| `$APP_URL/api/missions/active` | `{"missions":[HEDGE, OPPORTUNITY]}` (Lakebase 또는 in-memory fallback) |
| `$APP_URL/api/market/opec-latest` | 2026-03 OPEC MOMR 정량 fields |
| `$APP_URL/` | React UI (Discovery 페이지) |

---

## 5. 데모 시연 흐름 (5/18 또는 평가위원 앞)

```
[Discovery 페이지]
  → Pattern Score 100 HEDGE 표시
  → 시그널 기여도 4 source bar
  → OPEC MOMR Document Intelligence 카드
  → 진행 중 미션 카드 (Bidirectional 2개)

[WhatIf 페이지 "AI 어시스턴트 (Supervisor)" widget]
  → "오늘 위기 점수 어디서 왔고 추천도 알려줘" 입력
  → 5-15초 응답 + tools_used badge (Genie + Mission Plan)
  → 단일 endpoint single response

[demo terminal]
$ curl -X POST $APP_URL/api/demo/inject_signal -d '{"scenario":"hormuz_blockade"}'
  ↓ (Slack 채널에 HEDGE Mission 카드 도착 — 5초 안)
  ↓ (Apps Discovery + Mission 목록 자동 update — WS)
[Slack에서 ✅ Confirm 클릭]
  ↓ (Apps Mission status pill 'PROPOSED' → 'ACTIVE' 자동 — 5초 안)
  ↓ (Slack 카드 "✅ Confirmed via SLACK" 으로 update)
```

---

## 6. 알려진 한계 / 트러블슈팅

| 증상 | 원인 | 해결 |
|---|---|---|
| `frontend_bundled: false` | Apps 자동 build 실패 | logs → npm/pip error 확인. root package.json 또는 requirements.txt 검증 |
| Build exit 127 | npm/corepack 명령 미존재 | frontend pnpm-lock.yaml 제거 + package-lock.json 사용 (D-2 fix) |
| missions/active 500 (PoolTimeout) | Apps SP의 Lakebase PG OAuth role mapping 미설정 | Apps Settings → Resources → + Add Database (D-1 P0 #3) |
| Discovery "Backend 연결 실패" | frontend production API_BASE를 `localhost:8000`으로 함 | `lib/api.ts`에 `import.meta.env.PROD ? "" : "localhost:8000"` (D-2 fix) |
| Slack Interactivity 401 | Slack Signing Secret 미일치 | secret scope `slack_signing_secret` 재확인 |
| Supervisor endpoint 미응답 | Resources에 `supervisor_endpoint_name` 미등록 | + Add Serving endpoint `mas-ba3fbcb5-endpoint` |

---

## 7. 비용 / 보안

- **Apps**: deploy 유지 시 ~$1-5/일 (Serverless compute idle scaling)
- **Foundation Model API**: Claude Haiku ~$0.001/호출. 데모 시연 = 100호출 안 = ~$0.10
- **Lakebase**: free tier (3GB) 충분
- **Genie Space**: Public Preview 무료
- **Agent Bricks (KA + Supervisor)**: GA 후 별도 pricing (현재 시점 무료 또는 minimal)

**Production rollout 시**:
- `DEMO_MODE=false` (`/api/demo/*` 미노출)
- Apps OAuth (Apps가 자동) — `X-Forwarded-User` 헤더 신뢰
- Lakebase OAuth token 60분 회전 — backend `max_lifetime=50min`로 만료 전 reconnect

---

## 8. Legacy: workspace path deploy (deprecated, 참고용)

D-2 5/16 이전 패턴 — 현재는 Git source 사용. fallback path로만 활용:

```bash
# (0) frontend build
cd frontend && npm run build && cd ..

# (1) Workspace sync
databricks --profile crude-compass sync . \
  /Workspace/Users/<email>/databricks_apps/crude-compass --full

# (2) Deploy
databricks --profile crude-compass apps deploy crude-compass \
  --source-code-path /Workspace/Users/<email>/databricks_apps/crude-compass
```

Git source 실패 시 rollback path. 단, frontend dist는 사용자가 명시적으로 build 필요.
