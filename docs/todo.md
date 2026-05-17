# Crude Compass — TODO / D-1 Priority

> 2026-05-17 D-1 기준 rewrite. early submit D0 2026-05-18 22:00 KST.
> 진행 전체 요약: [progress_summary.md](progress_summary.md), 평가: [self_evaluation.md](self_evaluation.md)

---

## 🔴 P0 — 발표 전 반드시

### 1. Backtest narrative drift fix (evaluator 5차 −2pt 원인)
**문제**: 시나리오 docs에 "n=298, 75% hit, +0.626%" 8군데 단정 narrative. 실제 Lakebase `backtest_predictions`는 **n=15 (HEDGE-only, OPP=0)**.
**옵션 A (권장)**: `backtest_llm` job 재실행 — `n_per_zone=100` × 3 zone = 300건 (2-3h 백그라운드).
**옵션 B**: narrative downgrade — "smoke test 15건 + D-1 full run" 솔직 disclosure.
검증: WhatIf 페이지 "총 샘플 N건" 응답 + 영상 narrator 일치.

### 2. §19 Risk 섹션 — OPP backtest n=0 disclosure
"Bidirectional"이 차별화인데 backtest는 HEDGE-only. evaluator 의심 trigger.

### 3. Apps Database resource 추가 → Lakebase fallback 해제
**현재**: Apps SP의 PG OAuth role mapping issue로 in-memory fallback.
**fix**: Apps Settings → Resources → + Add → **Database** → Lakebase instance → CAN USE → 재배포.
**검증**: `/api/missions/active` 응답에 `_debug_store_type` 없어지고 진짜 Lakebase row 반환.

---

## 🟡 P1 — 시간 남으면

### 4. `/api/health`에 `store_backend` field 추가 (transparency)
fallback 작동 시 평가위원이 즉시 알도록.

### 5. Slack [Confirm] live test (사용자 채널에서 직접)
1. demo inject signal → mission 카드 Slack push 확인
2. 채널에서 [✅ Confirm] 클릭 → 5초 안 카드 "Confirmed via SLACK"으로 업데이트
3. Apps Mission list에서 같은 mission status='active' 동기화 확인

### 6. 영상 5분 1차 녹화
- Phase 1 (00:00-00:30): Track 1 narrative + 평시 가치
- Phase 2 (00:30-01:30): 아키텍처 6 source + Agent Bricks 2 types + Multi-Agent Supervisor
- Phase 3 (01:30-02:00): Discovery 페이지 라이브
- Phase 4 (02:00-02:45): Supervisor 자연어 + Slack ↔ Apps 5초 sync ⭐
- Phase 5 (02:45-03:30): WhatIf 시점 슬라이더 + backtest
- Phase 6 (03:30-04:15): Bidirectional Pivot
- Phase 7 (04:15-04:45): 6년 평시 가치 chart
- Phase 8 (04:45-05:00): Closing

---

## 🟢 P2 — 가능하면

### 7. 3-LLM 비교로 Mission Plan prime model 결정
- Haiku 4.5 / Sonnet 4.6 / GPT-5.5
- 동일 prompt + signals × 3 호출 → 정성 평가
- 결정 후 `crude_compass.functions.mission_plan_advice` UC function의 endpoint name swap
- 비용 ~수백원

### 8. oil_prices_daily freshness (5/14 lag 3일)
- `job_oil_prices_daily` cron 확인
- 또는 narrative 정정 ("OPINET data 매주 갱신")

### 9. price_spike 0 rows
- OilPriceAPI 5min cron 실패? `job_price.py` 상태 점검
- 또는 시나리오 narrative 4 signal source로 reframe (5→4)

---

## 🛑 알려진 한계 (D-1 fix 불가, narrative로만 처리)

### OPEC PDF anti-bot
- 2026-04/05 MOMR 403 차단 (publications.opec.org)
- bronze.opec_momr_parsed 최신 = 2026-03
- KA 응답 "2026년 5월 보고서 미등록" 솔직 transparency로 처리

### Lakebase Apps SP PG OAuth mapping
- SP UUID `5a0f80bd-...`에 PG ROLE 생성 + GRANT 완료 후에도 PoolTimeout
- 추정: Databricks Lakebase OAuth user claim ↔ PG role 자동 매핑 필요 (Database resource로 해결)
- D-1 P0 #3에서 fix 시도

---

## D-day count

- D-3 (5/15 목) — Apps 코드 + LLM backtest + medallion gold view 8개
- D-2 (5/16 토) — Apps deploy + Genie Space + KA + IE scope-out + Supervisor 3 sub-agent + AIS 완전 제거
- **D-1 (5/17 일) — 현재** — backtest 재실행 + Lakebase fix + 영상 1차
- D0 (5/18 월 22:00 KST) — early submit
- Final (5/22 목) — 공식 마감
- Judging (5/25 ~ 5/29) — 평가 기간

---

## D-2 (5/17) 완료 사항 — 참고

D-2 commit history (`533cefb..30cc2bf` 약 30 commits):
- AIS Stream + K-Petroleum 5척 fleet 완전 제거 (source 7→6)
- Apps Git source 자동 build pipeline (root package.json + requirements.txt + uvicorn --app-dir backend)
- Lakebase OAuth pool current_user.me() dynamic resolution
- IE scope-out → Agent Bricks 2 types (KA + Supervisor)
- Supervisor 3 sub-agent (Genie + KA + mission_plan_advice UC function)
- Backend store.py graceful fallback (Lakebase smoke test → in-memory)
- 8 dead UC objects DROP (apply_schemas.py에 영구 migration 추가)
- WhatIf widget Supervisor reframe + tools_used badge
- 시나리오 §9.6 + §9.8 IE scope-out 솔직 narrative
- evaluator 5차 PASS 83.2 (+0.4 from 4차 82.8)
