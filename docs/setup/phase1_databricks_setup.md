# Phase 1 — Databricks Workspace Setup 가이드 (사용자 작업)

> **목적**: `infra/sql/*.sql` 코드 산출물을 Databricks workspace에 적용해서 데이터 인프라 구축.
> **소요**: 30~60분 (workspace UI + 몇 번의 SQL 실행)
> **필요**: Databricks Express account ($700 credit) 로그인 + workspace admin 권한

---

## 작업 분담 원칙

| 분류 | 담당 | 산출물 |
|---|---|---|
| 코드 산출물 (SQL · Python · YAML) | **AI** | `infra/sql/*` · `databricks/**/*` |
| Workspace UI 등록·생성·deploy | **사용자** | (이 문서가 안내) |

---

## 1. Unity Catalog · Bronze schema 생성

### 1.1 Catalog 생성 (UI)
1. Databricks workspace 접속
2. 좌측 메뉴 → **Catalog** → 우측 상단 **+ Create Catalog**
3. 이름: `crude_compass`
4. Type: **Standard**
5. Storage: workspace default 또는 본인 S3/ADLS bucket
6. **Create**

### 1.2 Schema 생성 (UI 또는 SQL)
1. `crude_compass` catalog 클릭
2. **+ Create schema** → 이름 `bronze` → **Create**
3. 같은 방식으로 `silver`, `gold` schema 생성 (Phase 1 Part C에서 사용)

### 1.3 Bronze tables DDL 적용
1. 좌측 메뉴 → **SQL Editor**
2. `infra/sql/bronze_schema.sql` 파일 내용 복사 → 붙여넣기
3. 우측 상단 **SQL warehouse** 선택 (Express는 "Starter" or "Serverless" warehouse 1개)
4. **Run** → 6 tables 생성 확인 (`oil_prices`, `ais_positions`, `gdacs_events`, `exchange_rates`, `news_articles`, `jwc_zones`)

---

## 2. Lakebase Postgres 인스턴스 + 4 tables

### 2.1 Lakebase 인스턴스 생성 (UI)
1. 좌측 메뉴 → **Compute** → 상단 **Database instances** 탭
2. **+ Create database instance**
3. 설정:
   - Name: `crude-compass-pg`
   - Capacity: **Capacity Units (CU)** — 최소 1 CU (Autoscaling 켜기)
   - Postgres version: 기본값
4. **Create** → 5분 정도 provisioning 대기

### 2.2 Database 생성
1. 인스턴스 페이지에서 **Connect** 버튼 → SQL editor 열기
2. SQL editor에서:
   ```sql
   CREATE DATABASE crude_compass;
   ```
3. 좌측 위 database 드롭다운에서 `crude_compass` 선택

### 2.3 Schema + 4 tables 적용
1. `infra/sql/lakebase_schema.sql` 파일 내용 복사 → SQL editor 붙여넣기
2. **Run** → 4 tables 생성 확인 (`missions`, `mission_events`, `rfq_negotiations`, `decisions`)
3. seed 데이터 1 mission + 4 RFQ 자동 insert (CardC4 데모용)

### 2.4 검증
```sql
SELECT mission_id, goal, current_term_pct, status FROM missions;
-- 1 row: "Term 50% → 70% (Hormuz 봉쇄 헤지)" / 65.00 / active

SELECT counterparty, status, ai_fit_score FROM rfq_negotiations ORDER BY ai_fit_score DESC;
-- 4 rows: Aramco 92 accepted / ADNOC 88 accepted / BP 71 received / TotalEnergies 64 sent
```

---

## 3. Secrets 등록

Apps + Jobs에서 외부 API 호출용 secret scope.

### 3.1 Secret scope 생성 (CLI)
```bash
# Databricks CLI 0.230+ 권장
databricks secrets create-scope crude-compass

# 검증
databricks secrets list-scopes  # crude-compass 보여야 함
```

### 3.2 API key 등록
```bash
# OilPriceAPI Developer ($19/월 결제 후 받은 key)
databricks secrets put-secret crude-compass oilpriceapi-key
# (인터랙티브 입력 또는 --string-value 옵션)

# aisstream (무료, https://aisstream.io 가입)
databricks secrets put-secret crude-compass aisstream-key

# ECOS 한국은행 (무료, https://ecos.bok.or.kr/api 신청)
databricks secrets put-secret crude-compass ecos-key
```

### 3.3 Apps + Workflow에 secret 연결
- Apps: `app.yaml`의 `valueFrom: oilpriceapi-key` 가 자동으로 scope `crude-compass` 매칭
- Workflow Job: 작업 등록 시 환경변수 또는 dbutils.secrets.get 사용 (코드는 이미 fallback 처리됨)

---

## 4. Lakeflow Job 등록 (Tier 1 Daily + Tier 2 Realtime)

> **Phase 1 Part B (5/10)**에 Asset Bundle (`databricks.yml` + `resources/jobs/*.yml`) 작성 예정.
> 현재 단계는 **수동 Job 1개만 등록해서 ingestion smoke-test**.

### 4.1 임시 manual Job (oil_prices 검증)
1. 좌측 메뉴 → **Workflows** → **+ Create job**
2. Job name: `crude-compass-oilprices-test`
3. Task:
   - Type: **Notebook** (또는 **Python script**)
   - Source: `databricks/ingestion/oil_prices.py` (Repos 또는 workspace path)
   - Cluster: existing or new (Single Node, 13.3 LTS+)
4. Schedule: **None** (수동 실행)
5. **Run now** → 성공 시 `crude_compass.bronze.oil_prices` 에 3 rows (WTI/Brent/Dubai) append 확인

```sql
SELECT product, price_usd, fetched_at FROM crude_compass.bronze.oil_prices
ORDER BY fetched_at DESC LIMIT 3;
```

---

## 5. AIS Workflow continuous task 등록

### 5.1 Workflow Job 생성
1. **Workflows** → **+ Create job** → name: `crude-compass-ais-stream`
2. Task:
   - Type: **Python script**
   - Source: `databricks/workflows/ais_continuous.py`
   - Cluster: **Single Node**, 13.3 LTS+, 2 vCPU 4GB (작은 cluster 충분)
   - Library 추가: `websockets>=12.0`
3. Schedule: **Continuous**
4. Max concurrent runs: 1
5. Retry: 3회 (WS 재연결은 코드에서 처리하지만 cluster 재시작 fallback)

### 5.2 환경변수
- `AISSTREAM_KEY` → secret reference `{{secrets/crude-compass/aisstream-key}}`
- `AIS_CHARTER_MMSI` → 익명 charter VLCC 5 MMSI comma-separated (또는 default 사용)

### 5.3 검증
```sql
SELECT COUNT(*) FROM crude_compass.bronze.ais_positions
WHERE received_at > current_timestamp() - INTERVAL 5 MINUTES;
-- 호르무즈 통과 선박이 있다면 5분 안에 N rows
```

---

## 6. 다음 단계 (Phase 1 Part B/C)

내가 만들 산출물:
- `databricks/ingestion/{gdacs,exchange_rates,news_rss}.py`
- `databricks.yml` Asset Bundle 정의
- `resources/jobs/{tier1_daily,tier2_realtime}.yml` Job 선언
- `databricks/silver/` + `databricks/gold/risk_score.py`

사용자 작업 (Part B 끝나면 안내 추가):
- Asset Bundle deploy (`databricks bundle deploy`)
- Job schedule 활성화 (Tier 1 daily 06:30 KST, Tier 2 5분)
- Genie Space 생성 + 한국어 synonyms 등록 (Phase 2)
- Apps `crude-compass` 등록 + Lakebase attach (Phase 4)
- AI/BI Dashboard 작성 (Phase 4)

---

## 트러블슈팅

| 증상 | 원인·조치 |
|---|---|
| `bronze_schema.sql` 실행 시 "catalog not found" | 1.1에서 catalog 이름 다른지 확인 (`crude_compass` 정확히) |
| Lakebase psql 연결 실패 | 인스턴스 provisioning 5분 대기. `Connect` 버튼 다시 |
| `oil_prices.py` Job "secret not found" | 3.1 scope 이름 정확히 `crude-compass` (하이픈) |
| AIS Workflow rows 0건 | aisstream key 유효성 + 호르무즈 BBox에 선박이 실제 있는지. `python databricks/workflows/ais_continuous.py` 로컬 실행으로 verbose log 확인 |

문제 생기면 정확한 에러 메시지 + 어느 step인지 알려주시면 같이 처리.
