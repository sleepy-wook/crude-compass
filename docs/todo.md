# Crude Compass — TODO / Carryover / Blocker

> 진행 중 발견된 미해결 사항 + 형욱 manual step + 후속 patch.
> 매 milestone 끝마다 update. **D-3 (5/15) 기준 rewrite.**
> 진행 상황 전체 요약은 [progress_summary.md](progress_summary.md), 평가는 [self_evaluation.md](self_evaluation.md).

---

## 🟡 형욱 manual step (Workspace)

### D-3 ~ D-2 사이
- [ ] **`gold.daily_risk_score_sync` Lakehouse Sync 삭제** (Foreign Table wrapper)
  - 5/15 토론 결정: 사용 안 함 (Apps는 Lakebase 직접 read)
  - HOW: Lakebase UI → Sync configurations → daily_risk_score_sync → Delete
- [ ] **Backtest notebook 재실행 (Lakebase 300건 적재)**
  - 5/15 UC `gold.llm_backtest_predictions` DROP 완료, Lakebase `backtest_predictions` 빈 상태
  - HOW: Databricks workspace → `crude-compass-backtest-llm-dev` job → Run now
  - 소요: ~1h, ~$3 (Haiku 4.5 300 calls)
  - 검증: `/api/backtest/results` 응답 + WhatIf 페이지 데이터 노출

### D-2 (5/16) — 자세한 가이드는 [d2_runbook.md](d2_runbook.md)
- [ ] Databricks Apps 배포 (`databricks sync` + `apps deploy`)
- [ ] Slack Interactivity URL 등록 (배포된 Apps URL + `/api/slack/interactive`)
- [ ] **Genie Space 생성 + 5 certified queries 등록** ([genie_certified_queries.md](genie_certified_queries.md))
- [ ] **Knowledge Assistant 시작** (OPEC MOMR PDF 1-3개 UC Volume 적재 → KA endpoint 등록)
  - ⚠️ Critical path: sync 1-3h 소요
- [ ] AI/BI Dashboard 5개 차트 (gold view 8개 활용)
- [ ] Apps resource 추가 (Genie space + KA endpoint + secrets) → 재배포

---

## 🟠 후속 patch (D-1)

- [ ] **5분 데모 영상 1차 녹화** — 평가위원 시점 narrator script
- [ ] `/evaluate` agent 호출 → 5축 자동 점수 + REVISE/PASS 판정
- [ ] 잔여 frontend 미구현:
  - 가격 라인 차트 (`gold.oil_prices_wide` view 활용 — 데이터는 있음, 화면만)
  - 최근 7일 뉴스 리스트 (`gold.news_top_signals` view 활용)

---

## 🔴 알려진 blocker (해커톤 영향)

### 팀 자격 — 형욱 manual
- [ ] 팀 멤버 2-4명 확정 ([phase1_research.md](phase1_research.md) §1.1 자격 요건)
  - 친구 (LG Electronics) 합류 확정 → 2명 OK
  - corporate email 사용 가능 확인

### AIS Stream 5척 narrative (5/16 D-2 완전 제거)
- ✅ **D-2 결정**: AIS Stream 완전 제거. 이유: 한국 flag VLCC 0척 active (글로벌 8min scout 결과) + 7년 backtest 미사용 (silver.signal_events_decayed에 ais_traffic row 0건) → narrative dead weight. 호르무즈 narrative는 GDELT 키워드 mention burst로 단일화. source 7→6.

### OPEC PDF anti-bot (D-12 발견, 미해결)
- April/May 2026 OPEC MOMR PDF 403 차단 (publications.opec.org anti-bot)
- 현재: Jan/Feb/Mar 3개월 + 2020-2025 backfill로 narrative 충분
- 해결 옵션 (production, 데모 후): Playwright headless browser 자동화

---

## ✅ 최근 완료 (D-3 batch)

D-3 (5/15) push된 commit 7개:
1. `7bef6eb` Dead gold tables 3개 DROP
2. `6cdb7cd` v4/v5/v6 version naming 제거 (파일 6개 삭제, 코드 cleanup)
3. `f2cec22` UC Delta `gold.llm_backtest_predictions` → Lakebase Postgres migration
4. `491e150` Gold analytics views 8개 (Genie + Dashboard + Apps 공통)
5. `0e765e1` Discovery narrative anchor 3개 (SignalContribution / PatternScoreLine / OpecCitation) — HormuzMap은 D-2 AIS 제거 시 동반 삭제
6. `d42703f` Job audit — 13→12 jobs, yml UNPAUSE 6개, news_rss_enrich 삭제
7. `4072bc6` Progress summary 문서

상세는 [progress_summary.md](progress_summary.md).

---

## D-day count

- D-3 (5/15 목) — **현재**
- D-2 (5/16 토) — Workspace deploy
- D-1 (5/17 일) — 영상 1차 + evaluate
- D0 (5/18 월 22:00 KST) — early submit
- Final (5/22 목) — 공식 마감
- Judging (5/25 ~ 5/29) — 평가 기간
