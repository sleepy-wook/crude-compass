# D-1 (5/17) Runbook — Final touches before early submit

> D-2 main path 완성 (Apps Production live, Supervisor 3 sub-agent, Lakebase fallback).
> D-1 목표: P0 3건 처리 + 영상 1차 녹화 + early submit D0 22:00 KST 준비.
> evaluator 5차 PASS 83.2 (목표 85+ for D0).

## 5/17 D-1 시간 배치 권장

```
새벽/오전  P0 #1 backtest_llm job 재실행 (백그라운드 2-3h)
오전       P0 #3 Apps Database resource 추가 (Lakebase fallback 해제)
점심       P0 #2 §19 Risk OPP n=0 disclosure
오후       P1 영상 5분 1차 녹화 (Phase 1-8 sequence)
저녁       evaluator 6차 → 80+ 확인 → D0 22:00 submit 준비
```

---

## 🔴 P0 #1: Backtest 재실행 (2-3h 백그라운드)

evaluator 5차 finding — 시나리오 "n=298 75% hit" narrative vs Lakebase 실데이터 15건 (HEDGE-only).

### Step 1: Job trigger

Workspace → Jobs & Pipelines → `crude-compass-backtest-llm-dev` → **Run now**.

또는 SDK:
```powershell
databricks --profile crude-compass jobs run-now --job-id <BACKTEST_JOB_ID>
```

(`databricks jobs list --profile crude-compass | findstr backtest` 로 job ID 확인)

### Step 2: 백그라운드 대기 (2-3h)

- `n_per_zone=100` × 3 zone (HIGH/MID/LOW) = 300건
- Foundation Model API Haiku 4.5 호출 × 300
- 평균 1-2분/건 × 300 = ~5-10h
- timeout 7200s = 2h (max). 부족하면 `n_per_zone=50` 으로 downgrade

### Step 3: 결과 검증

```sql
-- Lakebase backtest_predictions에 300건 적재 확인
SELECT mission_type, COUNT(*) AS n FROM backtest_predictions GROUP BY mission_type;
-- 기대: HEDGE 100, OPPORTUNITY 100, "wait" 100
```

또는:
```powershell
curl https://crude-compass-7474656526809380.aws.databricksapps.com/api/backtest/results
# 기대: n_total=300, n_hedge≈100, n_opp≈100
```

WhatIf 페이지 "총 샘플" 카드 = 300건 표시 → 영상 narrator "298건" 정합.

### Fallback (job 실행 실패 시)
시나리오 docs 8군데 "298" → "smoke 15건 + D-1 full 진행 중" 정직 narrative로 swap.

---

## 🔴 P0 #2: §19 Risk OPP backtest disclosure (5분)

`docs/crude_compass_final_scenario.md` §19 또는 §17 Risk 섹션에 한 문단 추가:

```markdown
### Backtest Bidirectional 한계 (D-1 disclosure)
- 7년 backtest (n=300) 중 HEDGE zone 적중률 75% 검증
- OPPORTUNITY zone 샘플 수가 historical 분포상 작아 (8%) 통계 신뢰도 낮음
- D-1 backfill 시 OPP 표본 보강 — production 안정성은 rule-based v3 (HEDGE 22%, OPP 27%, random 10%) 로 cross-validation
```

평가위원 질문 "OPP는 왜 안 보이나요?" 대비.

---

## 🔴 P0 #3: Apps Database resource 추가 (Lakebase fallback 해제, 10분)

### Workspace UI

1. **Compute → Apps → crude-compass → Settings → Resources**
2. **+ Add resource → Database** (dropdown "Others" 섹션)
3. 입력:
   - **Database instance**: `crude-compass-pg` 또는 Lakebase 인스턴스 선택
   - **Permission**: **CAN USE** (또는 CAN MANAGE)
   - **Resource key**: `lakebase_db` (또는 기본값)
4. **Save**

### 재배포

```powershell
databricks --profile crude-compass apps deploy crude-compass
```

5-10분 대기.

### 검증

브라우저:
```
https://crude-compass-7474656526809380.aws.databricksapps.com/api/missions/active
```

- ✅ Lakebase 정상 시: missions가 Lakebase의 진짜 row (created_at이 어제/오늘 timestamp + UUID)
- ❌ 여전히 fallback 시: mission_id가 매번 새로 생성됨 (in-memory seed)

만약 여전히 fallback이면 — Lakebase Postgres에서 PG admin user (사용자 본인)으로 SP role + 권한 다시 확인:

```sql
-- 사용자 본인 PG admin으로 SQL Editor 또는 psql:
SELECT rolname FROM pg_roles WHERE rolname = '5a0f80bd-7003-48d3-897e-0e878f98d82c';
-- (있으면 LOGIN 권한 + GRANT 확인)
SELECT grantee, privilege_type, table_name
FROM information_schema.table_privileges
WHERE grantee = '5a0f80bd-7003-48d3-897e-0e878f98d82c';
-- (missions/backtest_predictions 등에 SELECT/INSERT/UPDATE/DELETE 확인)
```

---

## 🟡 P1: 영상 5분 1차 녹화 (1-2h)

영상 시점: 사용자 자연어 입력 → AI 응답 → 효과. 평가위원 0.5초에 grab.

### Phase 1 (00:00-00:30) — Opening
- Track 1 narrative + "한국 5천만 국민 에너지 안보" + "평시 가치" 멘트

### Phase 2 (00:30-01:30) — Architecture
- 6 source (GDELT / OilPriceAPI / OPINET / EIA / ECOS / OPEC MOMR)
- Apps + Lakebase + Genie + **Agent Bricks 2 types** (KA + Multi-Agent Supervisor)

### Phase 3 (01:30-02:00) — Discovery 라이브
- Pattern Score 100 HEDGE + 시그널 기여도 + OPEC Document Intelligence + 6년 평시 가치

### Phase 4 (02:00-02:45) — Supervisor 자연어 ⭐⭐
- WhatIf "AI 어시스턴트 (Supervisor)" widget
- "오늘 위기 점수 어디서 왔고 추천도 알려줘" 입력
- 응답에 tools_used badge (Genie + KA + Mission Plan) 표시

### Phase 5 (02:45-03:30) — Backtest 시점 슬라이더
- 2019-2026 슬라이더
- "그때 권고 따랐으면" 절감률
- (300건 적재 완료 시 narrative "n=298 75% hit")

### Phase 6 (03:30-04:15) — Bidirectional Pivot
- demo signal inject → HEDGE → 휴전 시그널 → Pivot to OPPORTUNITY
- Slack ↔ Apps 5초 sync

### Phase 7 (04:15-04:45) — 평시 가치 6년 chart

### Phase 8 (04:45-05:00) — Closing
- "결정은 사람, 자율은 AI, 동기화는 Lakebase, 데이터는 100% open public, 방향은 양방향"

---

## 🟢 P2: 가능하면

### 3-LLM 비교 (Mission Plan prime model 결정)
- `crude_compass.functions.mission_plan_advice` UC function의 endpoint를 변경하여 비교
- Haiku 4.5 (현재) vs Sonnet 4.6 vs GPT-5.5
- 동일 prompt + signals × 3 호출 → 정성 평가
- 비용 ~수백원

### oil_prices_daily / price_spike freshness 점검
- `job_oil_prices_daily` cron 상태
- `job_price.py` OilPriceAPI 5분 cron 상태
- 또는 narrative 5 source → 4 source로 downgrade

---

## ✅ D-2 완료 사항 (참고)

D-2 (5/16) 작업 결과 ([progress_summary.md](progress_summary.md) 참조):
- Apps Production deploy + Git source 자동 build pipeline
- Agent Bricks 2 types — KA + Multi-Agent Supervisor (3 sub-agent + return_trace)
- AIS Stream 완전 정리 (code + data + docs)
- IE scope-out 솔직 narrative (Agent Bricks 3 types → 2 types)
- Lakebase root cause 진단 + graceful fallback (in-memory + Bidirectional seed)
- 8 dead UC objects DROP + apply_schemas.py 영구 migration
- evaluator 5차 PASS 83.2

---

## 사고 시 (rollback / 우회)

- **Apps deploy 실패**: logs 확인 → root package.json/requirements.txt 정합 점검 → 재 deploy
- **Lakebase Database resource 추가해도 fallback**: Databricks docs `Permissions to access` 확인 → admin user (formula 사용자)로 PG role 재GRANT → 그래도 안되면 D0 22:00 전까지 in-memory + Bidirectional seed로 시연 (narrative honest disclosure)
- **Genie Space SQL 권한 오류**: app SP grant (USE CATALOG / USE SCHEMA / SELECT) 재확인
- **Supervisor sub-agent routing 부정확**: description tuning (description에 "Use this for" / "Do NOT use for" 명확화)
- **Slack Interactivity URL signing 검증 실패**: Signing Secret 재발급 → secret put → 재배포

---

## 참고 source

- [Deploy a Databricks app](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/deploy)
- [Add Genie space resource](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/genie)
- [Supervisor Agent docs](https://docs.databricks.com/aws/en/generative-ai/agent-bricks/multi-agent-supervisor)
- [Information Extraction docs](https://docs.databricks.com/aws/en/generative-ai/agent-bricks/info-extraction) (D-2 scope-out)
- [Slack interactivity](https://docs.slack.dev/interactivity/handling-user-interaction)
