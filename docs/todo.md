# Crude Compass — TODO / Carryover / Blocker

> 진행 중 발견된 미해결 사항 + 형욱님 manual step + 후속 patch.
> 매 sprint 끝마다 업데이트.

---

## 🔴 Active blocker / carryover

### 2026-05-13 — Backtest v6 (Recency + Structured Fields) — production model ⭐
- **v6 prompt 개선**: Signal recency (C, 최근 7일 가중) + Structured fields (D, EIA/OPEC/Dubai 정량)
- **결과**: HEDGE 75% hit (n=298), +0.626% avg saving, $100-200M annual K-Petroleum
- **v5 → v6**: hit 69 → 75%, saving -0.245 → +0.626%, active sample 176 → 298
- **OPP**: 1건만 권고 (시스템 양방향 capable, 7년 강세 regime dominated, paper trade 4주 검증)
- **시나리오 §부록 C v6 narrative 완성** (Sprint 4 진입 준비 완료)

### 2026-05-12 — LLM Mission Plan Backtest v5 (300 samples, 7년) ✅
- **결과**: HEDGE 67% hit (+0.37%), OPP 15% hit (-1.36%)
- **LLM cheating 검증**: 2019-2024 (training IN) 73% vs 2025-2026 (OUT) 43% → 30pp drop
- **Confidence calibration**: conf 80+ → 70% hit, +0.5% saving (production rule)
- **Sample bias 보정**: 300 stratified (HIGH/MID/LOW 100개씩) vs 이전 100 sample inflated bias
- **K-Petroleum 적용 시 conservative ROI**: ~$40-60M = 530-820억 KRW/year (conf-gated)
- **시나리오 §부록 C 전면 재작성 완료** (LLM 강점/약점 audit 포함)

### 2026-05-11 — Multi-source backtest D variant (rule-based, v3) ✅ — superseded by v5
- **결과**: HEDGE 22.2% / OPP 27.3% (random 10% 대비 2.2-2.7배)
- **기여**: GDELT (17 queries) + EIA inventory (348 weekly) + OPEC monthly (3 reports) + FX (820 daily)
- **EIA 효과**: API key 재발급 후 활성 → OPP precision 11→27% (2.5배 ↑)
- **시나리오 §부록 C narrative 업데이트 완료**

### 2026-05-11 — Dubai daily price source 확정 ✅ (해결)
- **이전 blocker**: EIA RBRTE 403 차단 (Brent daily 부재)
- **해결**: OPINET (한국석유공사) `gloptotSelect.do` CSV endpoint
  - Dubai/Brent/WTI 일별 1996~ 동시 반환 (cp949 인코딩)
  - 3년 4개월 (864 trade days) 한 번에 0.7s fetch 검증 완료
  - robots.txt 미차단, Public web feature fair-use
- **Bronze**: `crude_compass.bronze.oil_prices_daily` (Dubai 중심, ticker별 row)
- **Job**: `databricks/jobs/oil_prices_daily.yml` (daily / historical mode widget)
- **시나리오 변경**: Brent baseline → **Dubai baseline** (한국 정유사 중동산 70%+ 수입)
- **남은 manual**: Workspace에서 historical mode 1회 실행하면 3년치 적재

### 2026-05-11 — OPEC 4월 PDF 403 차단
- **상황**: `https://www.opec.org/assets/assetdb/momr-april-2026.pdf` HTTP 403 (다른 suffix `-1`, `-2`도 마찬가지)
- **publications.opec.org** route도 anti-bot (JavaScript challenge)로 httpx 차단
- **Twitter short URL** (`t.co/a9NcCcq8QR`) → `momr.opec.org/pdf-download/` (dynamic page) → 403
- **확인**: 1-3월 + 2024-2025 모든 월은 `assets/assetdb/` 경로로 정상 access. 4월 2026부터 access pattern 변경된 듯.
- **임시 처리**: Jan/Feb/Mar 3개월 데이터로 Sprint 3 진행. 4-5월은 미해결.

**해결 옵션** (형욱님 진행):
- [ ] **(빠름) Browser manual download** — Sprint 4 데모 직전:
  1. https://publications.opec.org/momr 방문
  2. April 2026 / May 2026 viewer에서 다운로드 버튼 클릭
  3. UC Volume `crude_compass.bronze.opec_pdfs/`에 `momr_2026_april.pdf`, `momr_2026_may.pdf` 이름으로 upload
  4. `INSERT INTO bronze.opec_momr_parsed SELECT ... FROM read_files('/Volumes/.../*.pdf')` 재실행
- [ ] **(production) Playwright headless browser 자동화** — Sprint 4 또는 데모 후
  - `databricks/notebooks/job_opec_momr.py`에 Playwright 추가
  - `pip install playwright` + `playwright install chromium`
  - 매월 12일 cron으로 publications.opec.org → JS execute → PDF download → UC Volume

---

## 🟡 Sprint 2 carryover (Sprint 3+에서 처리)

- [x] **OPEC Document Intelligence 시연** — Sprint 3 day 1에 정상 작동 (1-3월 indicator 추출 PASS)
- [ ] **Price/AIS/EIA/ECOS Job manual run 검증** — 5/15 schedule 활성화 시 자동 검증
- [ ] **bronze.opec_momr_parsed UPDATE 컬럼 채우기** — Sprint 4 Apps 작업 시점에 (현재는 raw_text만 적재)
- [ ] **GDELT Job 본문 fetch 추가** — Sprint 3 daily_curation에 보강
- [ ] **April/May OPEC 시그널 적재** — 위 blocker 해결 후

---

## 🟢 Sprint 3 진행 중

### Day 1 (5/11)
- [x] OPEC Document Intelligence 재작성 (SQL-only) PASS
- [x] 1-3월 OPEC indicator 추출 + 검증 로직 PASS
- [x] Mission Plan Agent prompt 설계 (Foundation Model API) PASS
- [x] backtest seed 5개월 (job_backtest_seed.py 906 rows) — **Sprint 3 Day 3에서 3년 4개월로 확장**

### Day 2 (5/15) ⭐
- [x] UC Function `weighted_signal()` 등록
- [x] Job 5 daily_curation (Bidirectional Pattern Detection)
- [ ] **OilPriceAPI $15 Exploration plan 결제** (형욱님 manual)
- [ ] Cron 60min → 15min 전환
- [ ] Mission Plan Agent 등록 (Agent Bricks Custom Agent)

### Day 3 (5/11-12) — **Dubai/3년 backtest pivot**
- [x] Dubai daily price source 확정 (OPINET KNOC) ✅
- [x] Bronze `oil_prices_daily` 스키마 + apply_schemas
- [x] `job_oil_prices_daily.py` ingestion notebook + bundle YAML
- [x] GDELT backtest seed 5개월 → 3년 4개월 (START_DT 20230101)
- [x] ECOS FX historical mode widget 추가
- [x] Backtest compute Dubai 기반 재작성 (Option D + 7d cool-down)
- [x] 시나리오 §부록 C narrative 전면 교체 (Dubai 3년)
- [ ] **형욱님 manual**: `apply_schemas.py` 재실행 (oil_prices_daily 추가)
- [ ] **형욱님 manual**: `job_oil_prices_daily` MODE=historical 1회 실행 (~864 trade days × 3 ticker)
- [ ] **형욱님 manual**: `job_backtest_seed` 3년 재실행 (~9000 GDELT rows)
- [ ] **형욱님 manual**: `job_ecos` MODE=historical 1회 실행
- [ ] **형욱님 manual**: `job_backtest_compute` 재실행 → precision 검증
- [ ] Supervisor Agent No-code UI 등록 + sub-agent 라우팅
- [ ] Knowledge Assistant — OPEC MOMR + 가상 정유사 정책 PDF 업로드
- [ ] Genie Space + certified queries
- [ ] mini end-to-end smoke test

---

## 🛑 형욱님 manual step (sprint별)

| 시점 | 작업 | 상태 |
|---|---|---|
| Sprint 2 진입 전 | EIA API key + Catalog/Schema/Volume | ✅ 완료 |
| Sprint 3 day 2 (5/15) | **OilPriceAPI $15 Exploration plan 결제** | ⏳ |
| Sprint 3 day 3 | Knowledge Assistant용 가상 정유사 정책 PDF 1개 (Lorem ipsum 가능) Volume upload | ⏳ |
| Sprint 3 day 3 | Supervisor Agent No-code UI sub-agent 라우팅 등록 | ⏳ |
| Sprint 4 (5/17 경) | Slack app 만들기 + secret 2개 (`slack_bot_token`, `slack_signing_secret`) | ⏳ |
| Sprint 4 | Lakehouse Sync (CDC) UI에서 missions → gold.missions_history 활성화 | ⏳ |
| Sprint 4 | AI/BI Dashboard 4 chart 만들기 + iframe URL | ⏳ |
| Sprint 4 데모 직전 | OPEC 4월/5월 manual download (위 blocker 참조) | ⏳ |
| 언제든 | 친구분과 30분 sync — 시나리오 v2 검수 + 데모 영상 plan | ⏳ |

---

## 📌 Future work (5/22 데모 이후)

- [ ] Playwright OPEC scrape 자동화
- [ ] GDELT borderline case (importance 50-65)에만 LLM scoring 보강
- [ ] AIS WebSocket continuous → batch trade-off 재평가 (실서비스 진행 시)
- [ ] Mission Plan Agent CLEARS evaluation framework 통합
