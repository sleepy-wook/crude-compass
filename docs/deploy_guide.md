# Databricks Apps Deploy Guide

> 작성: 2026-05-14 D-4. 대상: 5/18 22:00 KST early submit + 5/22 final.
> 의존: `app.yaml`(project root) + `frontend/dist/`(build artifact) + `crude-compass` profile + `crude` secret scope.

---

## 1. 사전 준비

### 1.1 Frontend build
```bash
cd frontend
npm run build
# → frontend/dist/ 생성 (index.html + assets/*)
```

### 1.2 Secret scope 점검
```bash
databricks --profile crude-compass secrets list-secrets crude
# 필요 secrets (모두 등록되어있어야):
# - lakebase_host / lakebase_database / lakebase_user / lakebase_endpoint_path
# - slack_bot_token / slack_signing_secret / slack_default_channel
# - genie_space_id (D-2 형욱 manual 등록 후 — 없으면 fallback 모드)
# - oilprice_api_key / aisstream_api_key / ecos_api_key / eia_api_key
```

미등록 시:
```bash
databricks --profile crude-compass secrets put-secret crude <key> --string-value "<value>"
```

### 1.3 backend 의존성 lock 확인
```bash
cd backend && uv lock --check && uv sync
```

---

## 2. Apps Deploy

### 2.1 첫 배포 (App 생성)
```bash
# project root에서 실행
databricks --profile crude-compass apps create crude-compass
databricks --profile crude-compass apps deploy crude-compass \
  --source-code-path . \
  --description "Crude Compass — Pre-emptive Bidirectional Decision Agent"
```

### 2.2 재배포 (코드 변경 후)
```bash
cd frontend && npm run build && cd ..
databricks --profile crude-compass apps deploy crude-compass --source-code-path .
```

### 2.3 배포 상태 확인
```bash
databricks --profile crude-compass apps get crude-compass
# → status: RUNNING + url 표시
# url: https://crude-compass-<workspace-id>.databricksapps.com
```

---

## 3. 배포 후 Slack Interactivity URL 등록

배포 후 받은 public URL 사용:

1. https://api.slack.com/apps → Crude Compass app 선택
2. 좌측 **Interactivity & Shortcuts** → Toggle **On**
3. **Request URL**: `https://crude-compass-<workspace-id>.databricksapps.com/api/slack/interactive`
4. 좌측 **Event Subscriptions** (선택) → **Request URL**: `https://.../api/slack/events`
5. **Save Changes**

이 단계 완료 후 Slack 카드에서 [Confirm] / [Reject] / [Pivot] 버튼이 작동 (양방향 5초 sync).

---

## 4. 배포 검증 체크리스트

```bash
APP_URL="https://crude-compass-<workspace-id>.databricksapps.com"

# (1) Health
curl -s "$APP_URL/api/health" | jq
# expect: {"status":"ok","version":"0.1.0","frontend_bundled":true}

# (2) Slack live
curl -s "$APP_URL/api/slack/health" | jq
# expect: {"enabled":true,"has_bot_token":true,"default_channel":"C..."}

# (3) Genie (D-2 형욱 Space 등록 후)
curl -s "$APP_URL/api/genie/health" | jq
# expect: {"enabled":true,"space_id":"01ef..."}

# (4) Frontend SPA
curl -s "$APP_URL/" -o /dev/null -w "%{http_code}\n"
# expect: 200 (index.html serve)

# (5) Demo inject (DEMO_MODE=true 검증)
curl -X POST "$APP_URL/api/demo/inject_signal" \
  -H "Content-Type: application/json" \
  -d '{"scenario":"hormuz_blockade"}'
# expect: 200 + slack_status="live" + Slack 채널에 카드 도착

# (6) LLM live (Foundation Model API)
curl -X POST "$APP_URL/api/missions/recommend_now" \
  -H "Content-Type: application/json" -d '{}'
# expect: 200 + llm_endpoint="databricks-claude-haiku-4-5"
```

---

## 5. 데모 시연 흐름 (5/18 또는 평가위원 앞)

```
[demo terminal]
$ curl -X POST $APP_URL/api/demo/inject_signal -d '{"scenario":"hormuz_blockade"}'
↓ (Slack 채널에 HEDGE Mission 카드 도착 — 5초 안)
↓ (Apps Discovery + Mission 목록 자동 update — WS)
[Slack에서 ✅ Confirm 클릭]
↓ (Apps Mission status pill 'PROPOSED' → 'ACTIVE' 자동 — 5초 안)
↓ (Slack 카드 "✅ Confirmed via SLACK" 으로 update)

[추가 시연: Live LLM]
[Discovery 화면에서 '🤖 지금 새 추천 생성' 버튼 클릭]
↓ (Databricks Foundation Model API 호출 — 5-10초)
↓ (새 Mission 추천 또는 'action=continue' lifecycle 인지 응답)
```

---

## 6. 알려진 한계 / 트러블슈팅

| 증상 | 원인 | 해결 |
|---|---|---|
| `frontend_bundled: false` | `frontend/dist/` 누락 | `npm run build` 후 재배포 |
| Slack `not_in_channel` | 봇이 default channel 멤버 아님 | 채널에서 `/invite @crude_compass` |
| Slack Interactivity 401 | Slack Signing Secret 미일치 | secret scope `slack_signing_secret` 재확인 |
| Slack `dispatch_failed` | Interactivity URL 미설정 | §3 참조 |
| Genie `fallback_text` 응답만 | `GENIE_SPACE_ID` 미설정 | D-2 형욱 Space 만든 후 secret 재등록 + 재배포 |
| LLM `NotFound` endpoint | Foundation Model API 미활성 | Databricks workspace에서 Claude Haiku endpoint 등록 |
| Apps deploy 실패 (uvicorn missing) | `backend/pyproject.toml` lock outdated | `cd backend && uv lock && uv sync` |

---

## 7. 비용 / 보안

- **Apps**: D-2 ~ 5/22 배포 유지 시 ~$1-5 (Serverless compute idle scaling)
- **Foundation Model API**: Claude Haiku ~$0.001/호출. 데모 시연 + 라이브 = 100호출 안 = ~$0.10
- **Lakebase**: free tier (3GB) 충분
- **Genie**: Public Preview 무료

**Production rollout 시**:
- `DEMO_MODE=false` (`/api/demo/*` 미노출)
- Apps OAuth (Apps가 자동) — `X-Forwarded-User` 헤더 신뢰
- secret rotation 정기 (Lakebase OAuth token은 60분 자동 회전 — backend는 max_lifetime=50min로 회복)
