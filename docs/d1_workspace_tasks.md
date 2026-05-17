# D-1 Workspace Tasks (형욱님 직접 작업)

> 작성: 2026-05-17 (D-1)
> 작업 분담: 코드는 Claude, **Workspace UI는 형욱님 본인** (memory `feedback_databricks_workspace_user_owned.md`)
> 우선순위: 1등 위해 모두 필요 — 누락 시 점수 -10 이상

## 🔴 Critical 1: Apps Database resource binding (Lakebase live화)

**현재 상태**: Apps SP가 Lakebase Postgres role mapping fail → `/api/backtest/*` 500 + Mission seed만 in-memory.

**조치 (5분)**:
1. https://<your-workspace>.cloud.databricks.com → 좌측 메뉴 **Apps** → `crude-compass-7474656526809380` 클릭
2. 상단 탭 **Resources** → **Add resource** → **Database** 선택
3. Lakebase instance (보통 `crude-compass-db` 또는 비슷한 이름) 선택
4. Permission: **Can use** 또는 더 높게
5. **Save** → Apps 자동 restart (~30초)

**검증**:
- 5분 후 https://crude-compass-7474656526809380.aws.databricksapps.com/what-if 접속
- "Backtest 데이터 — Lakebase OAuth 연동 진행 중" disclosure card **사라지고**
- 5-stat summary card (총 샘플 / 적중률 / 평균 절감 / HEDGE / OPP) + Time Travel slider (300건 시점) 노출

**점수 영향**: A4 +3, A5 +5 (sidebar narrative drift 완전 제거 + WhatIf 살아남)

---

## 🔴 Critical 2: Agent Bricks Supervisor endpoint live화

**현재 상태**: `settings.supervisor_enabled = False` (env 미설정) → Fallback mode → "Genie Space가 미연동..." 응답.

**조치 (10분)**:

### Step 1: Supervisor endpoint 이름 확인
1. Databricks workspace 좌측 메뉴 **Serving**
2. 본인이 등록한 Multi-Agent Supervisor endpoint 찾기 (이름 패턴: `mas-*` 또는 `crude-compass-supervisor`)
3. endpoint URL/name 메모

### Step 2: Apps 환경변수 추가
1. **Apps** → `crude-compass-7474656526809380` → **Environment variables** 탭
2. 다음 2개 변수 추가:
   - `SUPERVISOR_ENDPOINT_NAME` = `<위에서 메모한 endpoint 이름>` (예: `mas-ba3fbcb5-endpoint`)
   - `SUPERVISOR_ENABLED` = `true` (이미 있으면 skip)
3. **Save** → Apps 자동 restart

### Step 3: Supervisor agent self-test (workspace 내)
1. Serving page → 해당 endpoint → **Test** 또는 Playground
2. "오늘 위기 점수 어디서 왔고 추천도 알려줘" 입력
3. 응답 텍스트 + Routing (sub-agent trace) 확인

### Step 4 (만약 endpoint 없으면): 새로 만들기 (60-90분)
- `crude_compass.functions.mission_plan_advice` UC Function 이미 존재
- Genie Space `01f150e05229190aa9de93c97afde034` 이미 등록
- Knowledge Assistant `ka-6b456458-endpoint` 이미 등록
- → 3 sub-agent 모아서 Agent Bricks UI에서 Multi-Agent Supervisor 생성 (참고: `docs/architecture.md` 또는 `docs/crude_compass_final_scenario.md` §9.7)

**검증**:
- WhatIf 페이지 Supervisor widget에서 "오늘 위기 점수" example chip click → 질문하기
- 응답 상단에 **● Live Supervisor** (회색 ● Fallback 아닌 초록색) badge
- 하단에 "사용된 sub-agent" 3개 pill: Genie SQL (파랑) / Knowledge Assistant (보라) / Mission Plan (초록)

**점수 영향**: A2 +6, A4 +2 (Multi-Agent orchestration 진정성 anchor 살아남)

---

## 🟡 Optional 3: Backtest 재실행 (n=300)

**현재 상태**: `backtest_predictions` 테이블에 n=15 (HEDGE only, OPP=0). 시나리오 §17에는 n=298 약속.

**조치 (15분, 자동 실행 시간 포함)**:
1. Databricks workspace → **Workflows** → **Jobs**
2. `backtest_llm` job 찾기
3. **Run now** with parameters:
   - `n_per_zone` = `100` (default 5 → 100)
   - `zones` = `crisis,mid,opportunity` (3 zone × 100 = 300)
4. 10분 후 완료 확인

**검증**:
- Discovery 페이지 백테스트 검증 section: "AI 추천 적중률 75%" → **실제 hit_rate_pct 노출**
- WhatIf 페이지 5-stat: 총 샘플 ~300건

**점수 영향**: A5 +3 (scenario drift 완전 제거)

---

## 🟢 Optional 4: OPEC MOMR 2026-04 수집 (cron retry)

**현재 상태**: bronze.opec_momr_parsed 최신 = 2026-03. 4월 PDF anti-bot으로 미수집.

**조치 (5분)**:
1. Workflows → `opec_momr_monthly` job
2. **Run now** (manual retry — anti-bot tornado 회피되면 성공)
3. 또는 OPEC MOMR April PDF 수동 다운로드 + `databricks/notebooks/opec_momr_manual_upload.ipynb` 실행

만약 4월 PDF 정말 미공개 또는 anti-bot 회피 불가 → 그대로 두기. 이미 화면에 "최신 보고서 2개월 lag · 4월 미수집 (anti-bot)" disclosure 배지 추가됨.

**점수 영향**: A5 +1

---

## 우선순위 정리

| # | 작업 | 시간 | 점수 회복 | 1등 critical? |
|---|---|---|---|---|
| 1 | Apps Database resource binding | 5분 | +8 | **YES** |
| 2 | Supervisor endpoint env 설정 | 10분 | +8 | **YES** |
| 3 | Backtest 재실행 n=300 | 15분 | +3 | optional |
| 4 | OPEC 4월 수집 retry | 5분 | +1 | optional |

**1+2번이 1등의 60%**. 둘 다 끝나야 객관 점수 83 → 90+.

---

## D0 제출 전 확인 체크리스트

- [ ] 1번 Apps DB resource 완료 → WhatIf disclosure card 사라짐
- [ ] 2번 Supervisor env 완료 → ● Live badge + 3 sub-agent pill
- [ ] (optional) 3번 backtest n=300 완료 → 적중률 실제값 노출
- [ ] (optional) 4번 OPEC 4월 수집 retry
- [ ] 영상 5분 녹화 (다음 phase)
- [ ] Devpost 제출 (Track 1 + 한국어 트랙)
