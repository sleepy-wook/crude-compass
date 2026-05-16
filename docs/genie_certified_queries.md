# Genie Space — Certified Queries (D-2 형욱 manual 등록용)

> 시나리오 §9.3 Genie Space 등록 시 paste용 SQL 5개.
> Workspace → Genie → Create Space `crude-compass-genie` → Tables 선택 후 Certified Queries 탭.
>
> Space ID 받으면 backend `.env`의 `GENIE_SPACE_ID` 채워 live 모드 swap.

## Genie Space 설정

**Catalog**: `crude_compass`
**Schemas**: `bronze`, `silver`, `gold` (gold 우선)

**Tables (10개 — gold view 위주, 5/15 commit `491e150` 후 reframe)**:

Gold layer (BI-ready, pre-shaped — Genie 평가위원 demo 핵심):
- `gold.daily_risk_score` (Pattern Score daily snapshot, Lakebase Sync target)
- `gold.oil_prices_wide` (WTI/Brent/Dubai pivot + Brent-Dubai spread)
- `gold.signal_contribution_30d` (시그널 source × direction 기여도 ⭐ Genie demo)
- `gold.eia_rolling` (EIA 4주 rolling avg + bullish/bearish direction)
- `gold.opec_demand_gap` (OPEC supply-demand + oversupply/undersupply balance enum)
- `gold.fx_with_delta` (USD/KRW + 1d/7d delta + 30일 변동성)
- `gold.news_top_signals` (최근 7일 importance≥60 direction별 Top 5/day)
- `gold.pattern_score_latest` (Pattern Score 30일 + HEDGE/MID/OPP zone)

Silver (raw access, 깊은 분석 시):
- `silver.signal_events_decayed` (event-level weighted_contribution)
- `silver.pattern_scores_daily` (daily history full fields)

**Instructions** (Genie Space settings → Instructions):

```
- Pattern Score 의미: silver.signal_events_decayed의 weighted_contribution 합 → 시간 감쇠 + cross-validation bonus 적용. 0~100 scale. 70+ = HEDGE zone, 30- = OPPORTUNITY zone.
- 시그널 source 5종: news_tone (GDELT 글로벌 뉴스 mention/tone), eia_inventory (EIA 미국 주간 재고), opec_momr (OPEC MOMR 월간 공급/수요), fx_krw_usd (ECOS USD/KRW), price_spike (OilPriceAPI 5분 ±2% spike).
- 호르무즈 narrative anchor는 GDELT 키워드 mention burst로 단일화 (이전 AIS 5척 fleet 추적은 5/16 D-2 제거).
- Term 비중 = 장기계약 (산유국 1~6개월 사전 합의). Spot 비중 = 즉시구매 (시장 가격). 평시 baseline 60:40.
- Gold layer 사용 우선 — BI-ready pre-shaped views (oil_prices_wide / signal_contribution_30d / eia_rolling / opec_demand_gap / fx_with_delta / news_top_signals / pattern_score_latest). silver/bronze는 view에 없는 raw column 필요 시만.
```

---

## 1. 최근 30일 신호 source별 Pattern Score 기여도 ⭐ Genie demo 핵심

평가위원 데모 핵심 query — "오늘 점수 어떤 시그널이 끌어올렸나?"
Gold view `signal_contribution_30d` 사용 (silver.signal_events_decayed pre-aggregated).

```sql
SELECT
  signal_type,
  direction,
  n_signals,
  total_contribution,
  avg_raw_intensity,
  avg_credibility
FROM crude_compass.gold.signal_contribution_30d
ORDER BY ABS(total_contribution) DESC
```

**Expected**: news_tone bullish/bearish 합 + eia_inventory + opec_momr + fx + price_spike (5 signal_type)

---

## 2. 최근 7일 Dubai/Brent/WTI 가격 + spread

Gold view `oil_prices_wide` 사용 (3 ticker pivot + Brent-Dubai spread 자동 계산).

```sql
SELECT
  trade_date,
  dubai_usd,
  brent_usd,
  wti_usd,
  brent_dubai_spread_usd
FROM crude_compass.gold.oil_prices_wide
WHERE trade_date >= CURRENT_DATE() - INTERVAL 7 DAYS
ORDER BY trade_date DESC
```

**Expected**: 7 rows 가격 + spread (positive = Dubai discount, negative = Dubai premium).

---

## 3. 최근 3개월 OPEC MOMR 사우디 공급 + market balance

Gold view `opec_demand_gap` 사용 (supply-demand + balance enum 자동 분류).

```sql
SELECT
  report_month,
  saudi_production_kbbl_d,
  opec_total_kbbl_d,
  forecast_demand_kbbl_d,
  supply_demand_gap_kbbl_d,
  market_balance
FROM crude_compass.gold.opec_demand_gap
WHERE report_month >= DATE_FORMAT(CURRENT_DATE() - INTERVAL 3 MONTHS, 'yyyy-MM')
ORDER BY report_month DESC
```

**Expected**: 최근 3개월 OPEC MOMR + market_balance (oversupply/undersupply/balanced).

---

## 4. 최근 4주 EIA 재고 변화 (4주 rolling + direction)

Gold view `eia_rolling` 사용 (4-week rolling avg + bullish/bearish auto-tag).

```sql
SELECT
  week_ending,
  value_kbbl,
  delta_vs_prev_wk,
  delta_4wk_avg_kbbl,
  signal_direction
FROM crude_compass.gold.eia_rolling
WHERE week_ending >= CURRENT_DATE() - INTERVAL 4 WEEKS
ORDER BY week_ending DESC
```

**Expected**: 4 rows EIA commercial 재고 + delta_4wk_avg + bullish/bearish/neutral direction.

---

## 5. 최근 30일 Pattern Score 추이 (HEDGE/MID/OPP zone)

Gold view `pattern_score_latest` 사용 (zone enum 자동 분류).

```sql
SELECT
  date,
  pattern_score,
  bullish_score,
  bearish_score,
  cross_val_bonus,
  mission_type,
  zone
FROM crude_compass.gold.pattern_score_latest
ORDER BY date DESC
```

**Expected**: 30 rows daily Pattern Score + bullish/bearish + HEDGE/MID/OPPORTUNITY zone.

> Backtest predictions(300건, 75% hit rate)는 Lakebase Postgres에 적재됨 (`backtest_predictions` table).
> Apps의 `/api/backtest/results` endpoint로 조회. Genie 직접 query 대신 Apps WhatIf 페이지로 시연.

---

## 등록 절차 (D-2 5/16, 1h budget)

1. Workspace 좌측 → **Genie** → **+ Create Space**
2. **Name**: `crude-compass-genie`
3. **Catalog**: `crude_compass` 선택 → **Schemas**: bronze/silver/gold 모두 선택
4. **Tables**: 위 10개 선택 — **gold 8개 (1 table + 7 views) + silver 2개**. bronze는 view에 없는 raw column 필요 시만 (default skip)
5. **Instructions** 탭: 위 instructions 영역 paste
6. **Certified Queries** 탭: 위 5개 query 각각 추가
   - Query 1 → "Test" 1번 실행 후 "Certify" 클릭
   - Query 2-5 동일
7. **Save Space** → URL의 `/genie/rooms/<SPACE_ID>` 부분 복사 — 이게 `GENIE_SPACE_ID`
   - ⚠️ 2026-05 docs: URL path가 `/genie/rooms/` (구버전 `/spaces/` 아님)
8. **App Resources 추가** (Workspace UI → Apps → crude-compass → Resources → Add resource):
   - Type: **Genie space**, permission: **Can run**, resource key: `genie_space_id`
9. **App 재배포** (resource 변경 시 필수):
   ```
   databricks apps deploy crude-compass --source-code-path /Workspace/.../crude-compass
   ```
10. **권한 확인**: App service principal에 catalog 권한 별도 grant
    - Catalog Explorer → `crude_compass` → Permissions → app SP에 USE CATALOG / USE SCHEMA / SELECT
11. `curl https://<apps-url>/api/genie/health` → `enabled: true` 확인 (live 모드)
12. Frontend WhatIf 페이지 Genie widget → 자연어 질의 1회 시연

## 평가위원 narrate 시 활용

- "Pattern Score 82가 어디서?" → Genie에 query 1 (signal_type별 기여도) 자연어로 질문
- "최근 OPEC 사우디 공급 변화?" → query 3 (OPEC MOMR 3개월)
- "Backtest 정직성?" → query 5 (실제 saving_30d_pct)

---

## Fallback (Space 미등록 시)

`services/genie.py`의 4-tier fallback 자동 작동:
- `live` → 실패 시 `fallback_data` (silver/bronze 직접 SQL)
- 데이터 없으면 `fallback_text` (hardcoded narrative)

데모 narrative 안정성 — Genie Space 등록 실패해도 시연 가능.
