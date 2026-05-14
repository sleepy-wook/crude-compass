# D-2 (5/16) Runbook — 형욱 Workspace 4h + Claude 2h

> 2026-05 Databricks docs 검증 기반. 우리 자체 docs 정정 사항 모두 반영.
> 시간 배치는 KA sync 1-3h 백그라운드 의존 → **아침 일찍 KA 먼저** 시작 권장.
>
> 목표: 공식 hackathon 4 features 모두 production 충족
> (Apps + Lakebase + Genie + AgentBricks Knowledge Assistant) + Slack live + 모든 영상 시연 anchor 완성.

## 5/16 시간 배치 권장

```
09:00  ⭐ KA sync 먼저 시작 (1-3h 백그라운드)
       - UC Volume 생성 + OPEC PDF 업로드 + Knowledge Assistant create
       - 이후 다른 task와 병렬
09:30  Genie Space 등록 시작 (UI 작업)
       - tables 10개 + instructions + certified queries 5개
10:30  Apps 첫 deploy 준비 (frontend build)
11:00  Apps deploy + Resources 등록 (secret 11개 + Genie space)
11:30  Apps URL 확보 → Slack Interactivity URL 박기 (~5분)
12:00  KA sync 완료 — endpoint resource 추가 + 재배포
12:30  전 시스템 검증 (curl 6종 + Slack button + Genie + KA 시연 rehearsal)
13:00  Claude 영상 스크립트 초안 작성
```

---

## 1️⃣ Apps deploy (5/16 11:00, 30-45분)

### 사전 준비
```bash
# (0) frontend build
cd C:\crude-compass\frontend
npm run build
cd ..
```

### Step-by-step
```bash
# (1) App 생성 (1회만, 이미 만들었으면 skip)
databricks --profile crude-compass apps create crude-compass

# (2) local → Workspace sync (⚠️ --source-code-path . 안 됨)
databricks --profile crude-compass sync . \
  /Workspace/Users/hyeongwook.lee@lginnotek.com/databricks_apps/crude-compass

# (3) deploy (Workspace path)
databricks --profile crude-compass apps deploy crude-compass \
  --source-code-path /Workspace/Users/hyeongwook.lee@lginnotek.com/databricks_apps/crude-compass

# (4) status + URL 확인 (PENDING → STARTING → RUNNING ~2-5분)
databricks --profile crude-compass apps get crude-compass
# → url: https://crude-compass-<workspace-id>.databricksapps.com 복사
```

### Resources 등록 (Workspace UI)
1. Workspace → **Compute → Apps → crude-compass → Resources** 탭
2. **Add resource** → **Secret** 11개 (scope=`crude`):
   - `lakebase_host`, `lakebase_database`, `lakebase_user`, `lakebase_endpoint_path`
   - `slack_bot_token`, `slack_signing_secret`, `slack_default_channel`
   - `oilprice_api_key`, `aisstream_api_key`, `ecos_api_key`, `eia_api_key`
3. (D-2 진행 후 추가) **Genie space** + **Serving endpoint × 2** (FMA + KA)
4. 변경 시 **재배포 필수**

### 검증
```bash
APP_URL="https://crude-compass-<workspace-id>.databricksapps.com"
curl -s $APP_URL/api/health | jq            # {"status":"ok"}
curl -s $APP_URL/api/slack/health | jq      # enabled:true
curl -s $APP_URL/api/fleet/positions | jq   # 5 vessels
```

### Logs
```bash
databricks --profile crude-compass apps logs crude-compass --follow
```

---

## 2️⃣ Slack Interactivity URL (5/16 11:30, 5분)

1. https://api.slack.com/apps → **Crude Compass** 선택
2. **Features → Interactivity & Shortcuts**
3. **Interactivity** 토글 **On**
4. **Request URL**:
   ```
   https://crude-compass-<workspace-id>.databricksapps.com/api/slack/interactive
   ```
5. **Save Changes**
6. ⚠️ URL verification challenge 없음 (events URL만 challenge). 200 OK면 즉시 accept.

### 검증
1. Slack `#crude-compass-demo` 채널에서 carded mission의 [✅ Confirm] 클릭
2. 5초 안에 카드가 "✅ Confirmed via SLACK"으로 update
3. Apps Mission list에서 같은 mission status='active' update 확인

---

## 3️⃣ Genie Space 등록 (5/16 09:30, 60-90분)

**docs/genie_certified_queries.md** paste 사용. 핵심 step:

1. Workspace 좌측 → **AI/BI → Genie** → **+ New** (또는 **+ Create Space**)
2. **Name**: `crude-compass-genie`
3. **SQL Warehouse**: Serverless Starter Warehouse 또는 pro warehouse
4. **Data**:
   - Catalog: `crude_compass`
   - Schemas: `bronze`, `silver`, `gold`
   - Tables 10개 선택 (genie_certified_queries.md §"Tables" 참조)
5. **Instructions** (또는 "General Instructions"): genie_certified_queries.md §"Instructions" block paste
6. **Example SQL queries** (구 "Certified Queries"): query 1~5 각각 Add → **Test** 실행 → **Save**
7. **Save Space** → URL 복사 — `https://<workspace>/genie/rooms/<SPACE_ID>`
   - ⚠️ 2026-05: URL path `/genie/rooms/` (구버전 `/spaces/` 아님)

### App Resources에 추가
1. Apps → crude-compass → **Resources** → **Add resource** → **Genie space**
2. space 선택, permission **Can run**, resource key `genie_space_id`
3. **재배포** (resource 변경)

### Service principal 권한
- Catalog Explorer → `crude_compass` → **Permissions** → app service principal에 **USE CATALOG**, **USE SCHEMA**, **SELECT** grant
- 빼먹으면 Genie API 호출 성공이지만 결과 empty/permission error

### 검증
```bash
curl -s $APP_URL/api/genie/health | jq
# {"enabled":true, "has_space_id":true, "default_channel": "..."}
```
- Frontend WhatIf 페이지 Genie widget → "Pattern Score 어디서?" → 5-15초 내 SQL + 자연어 응답
- Slow: SQL warehouse cold start (serverless ~30초)

---

## 4️⃣ Agent Bricks Knowledge Assistant (5/16 09:00 시작, 90-180분 sync)

> ⭐ **가장 일찍 시작** — sync 1-3시간이 critical path

### UC Volume + PDF 업로드
1. Workspace → **Catalog Explorer**
2. `crude_compass.gold` schema → **Create → Volume** → name `knowledge_pdfs` (managed)
3. PDF 업로드 (50MB 이하, 파일명 `_`/`.` 시작 X):
   ```bash
   databricks --profile crude-compass fs cp ./docs/opec_momr_sample.pdf \
     dbfs:/Volumes/crude_compass/gold/knowledge_pdfs/
   ```
   또는 Catalog Explorer UI에서 drag&drop

### Knowledge Assistant 생성
1. Workspace 좌측 → **Agents → + Create Agent → Knowledge Assistant**
2. **Step 1 — Knowledge source**: **Files in a Volume** → path `/Volumes/crude_compass/gold/knowledge_pdfs`
3. **Step 2 — Agent name**: `crude-compass-ka`
4. **Step 3 — Create** → sync 시작 (1-3h backgrounded)
5. **Serving endpoint 자동 생성** name: `ka-crude-compass-ka` (Serving → endpoints)

### Backend swap (sync 완료 후 12:00)
1. AI Playground → KA agent 선택 → **Get code → Curl API** copy (endpoint 이름·schema 정확히 확인)
2. App Resources에 **Serving endpoint** 추가:
   - Apps → crude-compass → Resources → Add → **Serving endpoint** → `ka-crude-compass-ka` 선택 → key `ka_endpoint`
3. `app.yaml` 수정:
   ```yaml
   - name: KA_ENDPOINT
     valueFrom: ka_endpoint
   ```
4. **재배포** + `curl $APP_URL/api/health` 확인

### 검증
- AI Playground에서 PDF 내용 질의 → citation 포함 응답 확인
- App에서 (Claude가 KA endpoint helper 추가 시) curl로 chat completion 호환 확인:
  ```bash
  curl -X POST $APP_URL/serving-endpoints/ka-crude-compass-ka/invocations \
    -H "Authorization: Bearer $DATABRICKS_TOKEN" \
    -d '{"messages":[{"role":"user","content":"OPEC 5월 보고서 사우디 감산?"}]}'
  ```

### 함정
- **Sync 시간 진짜 1-3h** — 5/16 09:00 시작 → 11:00-12:00 endpoint live
- Embedding endpoint `databricks-gte-large-en` AI Guardrails / rate limits **disabled** 필요 (default일 가능성 높지만 확인)
- App SP에 KA endpoint **CAN QUERY** 권한 (resource 추가 시 자동, 확인)
- **OpenAI chat completions 호환** schema → Foundation Model API 호출 코드 거의 그대로 swap

---

## 5️⃣ (Optional) AI/BI Dashboard 1개 (5/16 13:00 이후, 1h)

- Workspace → **SQL / Dashboard**
- Pattern Score 시계열 + K-Petroleum 5척 위치 + Backtest hit rate 추이
- 영상 데모에서 1컷 짧게 표시

---

## 5/16 종합 검증 (13:00-14:00)

```bash
APP_URL="https://crude-compass-<workspace-id>.databricksapps.com"

# Health
curl -s $APP_URL/api/health
curl -s $APP_URL/api/slack/health  # enabled:true
curl -s $APP_URL/api/genie/health  # enabled:true

# 데이터
curl -s $APP_URL/api/missions/active | jq '.missions | length'
curl -s $APP_URL/api/fleet/positions | jq '.vessels | length'  # 5
curl -s $APP_URL/api/pattern-score/current

# 라이브 시연 chain
curl -X POST $APP_URL/api/demo/inject_signal -d '{"scenario":"hormuz_blockade"}'
# → Slack DM 5초 안 도착
# → Apps Mission list 5초 안 update
# → 채널에서 [Confirm] 클릭 → "Confirmed via SLACK" 5초 안 update

# Phase 6 spike
curl -X POST "$APP_URL/api/reactive/demo-spike?ticker=BRENT_CRUDE_USD&delta=2.5"
# → 우상단 toast 표시

# Genie 자연어
curl -X POST $APP_URL/api/genie/query \
  -d '{"question":"Pattern Score 어디서 왔어?"}'
# → live source 또는 fallback_data
```

---

## 우리 자체 docs 2026-05 정정사항 (이 runbook에 반영)

| docs | 정정 |
|---|---|
| `app.yaml` comment | `--source-code-path .` → `databricks sync` 후 Workspace path ✅ |
| `genie_certified_queries.md` § 7 | `/spaces/<ID>` → `/genie/rooms/<ID>` ✅ |
| `deploy_guide.md` | (점검 필요 — 형욱 5/16 작업 전 patch) |

---

## 사고 시 (rollback / 우회)

- **Apps deploy 실패**: `app.yaml` 검증 → 재 sync → 재 deploy. logs에서 traceback 확인.
- **KA sync 1-3h 안 끝남**: 4 features 중 KA는 scope-out, Foundation Model API + Genie + Apps + Lakebase 3개만으로도 deploy 가능. 영상 narrate "AgentBricks 등록은 deployment 자동화 path 시연" 정도로 정정.
- **Genie Space SQL warehouse 권한 오류**: app SP grant 확인. fallback (services/genie.py 4-tier)이 자동 작동하므로 endpoint 자체는 200 OK.
- **Slack Interactivity URL signing 검증 실패**: Slack app **Basic Information** → Signing Secret 다시 복사 → secret resource 갱신 → 재배포.

---

## 참고 source

- [Deploy a Databricks app](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/deploy)
- [Add Genie space resource to Databricks app](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/genie)
- [Use the Genie Spaces API](https://docs.databricks.com/aws/en/genie/conversation-api)
- [Knowledge Assistant](https://docs.databricks.com/aws/en/generative-ai/agent-bricks/knowledge-assistant)
- [Slack: Handling user interaction](https://docs.slack.dev/interactivity/handling-user-interaction)
