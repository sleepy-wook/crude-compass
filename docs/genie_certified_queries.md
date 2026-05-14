# Genie Space — Certified Queries (D-2 형욱 manual 등록용)

> 시나리오 §9.3 Genie Space 등록 시 paste용 SQL 5개.
> Workspace → Genie → Create Space `crude-compass-genie` → Tables 선택 후 Certified Queries 탭.
>
> Space ID 받으면 backend `.env`의 `GENIE_SPACE_ID` 채워 live 모드 swap.

## Genie Space 설정

**Catalog**: `crude_compass`
**Schemas**: `bronze`, `silver`, `gold`
**Tables** (≤30, 우선 10개):
- bronze.news_articles
- bronze.oil_prices_daily
- bronze.oil_prices
- bronze.eia_inventory
- bronze.opec_momr_parsed
- bronze.fx_rates
- bronze.ais_positions
- silver.signal_events_decayed
- silver.pattern_scores_daily
- gold.daily_risk_score_sync  (Lakehouse Sync mirror of Lakebase daily_risk_score)

**Instructions** (Genie Space settings → Instructions):

```
- Pattern Score 의미: silver.signal_events_decayed의 weighted_contribution 합 → 시간 감쇠 + cross-validation bonus 적용. 0~100 scale. 70+ = HEDGE zone, 30- = OPPORTUNITY zone.
- K-Petroleum 5척 = 시나리오 §4 가상 VLCC fleet. MMSI 'KPETRO_001'~'KPETRO_005' 익명화 표시. SK Shipping operated VLCC fleet (AIS public data 활용).
- 시그널 source 6종: news_tone (GDELT), eia_inventory, opec_momr, fx_krw_usd, ais_traffic (5척 호르무즈 통과/stranded), price_spike (5분 ±2% spike).
- Term 비중 = 장기계약 (산유국 1~6개월 사전 합의). Spot 비중 = 즉시구매 (시장 가격). 평시 baseline 60:40.
```

---

## 1. 최근 30일 신호 source별 Pattern Score 기여도

평가위원 데모 핵심 query — "오늘 점수 어떤 시그널이 끌어올렸나?"

```sql
SELECT
  signal_type,
  direction,
  COUNT(*) AS n_signals,
  ROUND(SUM(weighted_contribution), 2) AS total_contribution
FROM crude_compass.silver.signal_events_decayed
WHERE event_date >= CURRENT_DATE() - INTERVAL 30 DAYS
  AND direction != 'neutral'
GROUP BY signal_type, direction
ORDER BY ABS(SUM(weighted_contribution)) DESC
```

**Expected**: news_tone bullish/bearish 합 + eia_inventory + opec_momr + fx + (있으면) ais_traffic + price_spike

---

## 2. 최근 7일 Dubai유 가격 추이

```sql
SELECT
  trade_date,
  price_usd AS dubai_close_usd
FROM crude_compass.bronze.oil_prices_daily
WHERE ticker = 'DUBAI'
  AND trade_date >= CURRENT_DATE() - INTERVAL 7 DAYS
ORDER BY trade_date DESC
```

---

## 3. K-Petroleum 5척 현재 위치 (가상 fleet)

```sql
SELECT
  mmsi AS vessel_id,
  vessel_name,
  lat,
  lon,
  speed_knots,
  status,
  in_hormuz_bbox,
  fetched_at
FROM crude_compass.bronze.ais_positions
WHERE mmsi LIKE 'KPETRO_%'
QUALIFY ROW_NUMBER() OVER (PARTITION BY mmsi ORDER BY fetched_at DESC) = 1
ORDER BY mmsi
```

**Expected**: 5 rows (K-Petroleum 가상 fleet). 데이터 적재된 vessel만 표시.

---

## 4. 최근 4주 EIA 미국 재고 변화 (주간)

```sql
SELECT
  week_ending,
  inventory_type,
  delta_vs_prev_wk AS weekly_change_kbbl
FROM crude_compass.bronze.eia_inventory
WHERE inventory_type = 'commercial'
  AND week_ending >= CURRENT_DATE() - INTERVAL 4 WEEKS
ORDER BY week_ending DESC
```

---

## 5. 최근 30일 Pattern Score 추이 (HEDGE/MID/OPP zone 분류)

```sql
SELECT
  date,
  pattern_score,
  mission_type,
  bullish_score,
  bearish_score,
  CASE
    WHEN pattern_score >= 70 THEN 'HEDGE'
    WHEN pattern_score <= 30 THEN 'OPPORTUNITY'
    ELSE 'MID'
  END AS zone
FROM crude_compass.gold.daily_risk_score_sync
WHERE date >= CURRENT_DATE() - INTERVAL 30 DAYS
ORDER BY date DESC
```

**Expected**: 30 rows showing daily Pattern Score + bullish/bearish breakdown + zone.

> Backtest predictions(300건, 75% hit rate)는 Lakebase Postgres에 적재됨 (`backtest_predictions` table).
> Apps의 `/api/backtest/results` endpoint로 조회. Genie 직접 query 대신 Apps WhatIf 페이지로 시연.

---

## 등록 절차 (D-2 5/16, 1h budget)

1. Workspace 좌측 → **Genie** → **+ Create Space**
2. **Name**: `crude-compass-genie`
3. **Catalog**: `crude_compass` 선택 → **Schemas**: bronze/silver/gold 모두 선택
4. **Tables**: 위 10개 선택 (또는 자동 검색)
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
- "K-Petroleum 5척 어디 있나요?" → query 3
- "Backtest 정직성?" → query 5 (실제 saving_30d_pct)

---

## Fallback (Space 미등록 시)

`services/genie.py`의 4-tier fallback 자동 작동:
- `live` → 실패 시 `fallback_data` (silver/bronze 직접 SQL)
- 데이터 없으면 `fallback_text` (hardcoded narrative)

데모 narrative 안정성 — Genie Space 등록 실패해도 시연 가능.
