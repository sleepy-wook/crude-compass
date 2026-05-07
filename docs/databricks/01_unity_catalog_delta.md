# 01. Unity Catalog + Delta Lake

> **Unity Catalog (UC)**: Databricks의 통합 데이터·AI 거버넌스 레이어 (catalog → schema → table 3-tier).
> **Delta Lake**: Parquet + transaction log로 ACID·time travel을 제공하는 lakehouse storage.
> 둘 다 **합쳐서 우리의 Bronze 6 tables가 사는 집**.

## 1. 왜 우리에게 필요한가

`infra/sql/bronze_schema.sql:6` 첫 줄이 `crude_compass.bronze.oil_prices` — 이게 UC 3-tier 이름. 그 아래 `USING DELTA`로 Delta Lake 활성. 두 기술이 합쳐서 다음을 보장:

- **5분 cron**으로 6개 tables가 동시에 row append 되는데도 ACID로 데이터 안 깨짐.
- **Genie · Agent Bricks · AI/BI Dashboard** 가 같은 카탈로그 read → 권한 한 곳에서 관리.
- **late-arriving 데이터** (예: AIS reconnect 후 직전 메시지 재수신)를 `MERGE`로 안전하게 upsert.
- **AI/BI Dashboard**가 "30일 전 가격" 차트 그릴 때 Delta time travel로 정확한 과거 snapshot.

UC + Delta가 없으면 — small file 폭증, 동시성 충돌, 권한 어디서 관리할지 모호 → 5분 cron 자체가 위험.

---

## 2. 핵심 개념 7개

### (a) Catalog → Schema → Table 3-tier
```
crude_compass        ← Catalog  (workspace 안 1개 만들어 두고 쓰는 단위)
  └── bronze         ← Schema   (= "DB", logical grouping)
        └── oil_prices  ← Table  (실제 데이터)
```
- 우리 카탈로그 = `crude_compass`
- Schema 3개 = `bronze` (raw) / `silver` (정제) / `gold` (집계, risk_score 시계열 등)
- Table = bronze 안에 6개 (oil_prices · ais_positions · gdacs_events · exchange_rates · news_articles · jwc_zones)

부모(catalog) 권한이 자식(schema·table)에 implicit 상속. 즉 **카탈로그 단위로 한 번 권한 주면 끝**.

### (b) Delta Lake = ACID + time travel + schema enforcement
보통 Parquet은 그냥 컬럼 파일이지만, Delta는 그 위에 "transaction log" (`_delta_log/`)를 붙여 버전·atomicity 관리. 효과:
- **ACID**: 5분 cron 동시 INSERT 충돌 X
- **Time travel**: `SELECT * FROM t VERSION AS OF 42` 또는 `TIMESTAMP AS OF '2026-05-08'`
- **Schema enforcement**: 잘못된 컬럼 타입으로 INSERT 시 거부 (Postgres 같은 보호)

### (c) `PARTITIONED BY (DATE(fetched_at))`
물리적으로 디렉터리를 일자별로 분리:
```
oil_prices/
├── _delta_log/
├── fetched_at=2026-05-07/
├── fetched_at=2026-05-08/
└── ...
```
시간 기반 query (`WHERE fetched_at > NOW() - INTERVAL 5 MINUTES`) 빠름. **함정**: 한 번 정하면 **재partition 시 테이블 전체 재작성** 필요.

→ 우리는 `oil_prices`·`ais_positions`·`news_articles` 3개에 partition 적용 (시간 기반 access dominant).

### (d) Liquid Clustering — 2026 권장 (vs Partition)
DBR 15.2+ GA. partition과 비호환 (둘 중 하나만 쓸 수 있음). 핵심 차이:

| | Partition | Liquid Clustering |
|---|---|---|
| 정의 후 변경 | 테이블 재작성 필요 | `OPTIMIZE` 한 번으로 변경 |
| Cardinality | 낮을 때 적합 (날짜) | 높을 때 적합 (mmsi 같은 유저 ID) |
| Skew | 취약 | 견딤 |

→ **2026 신규 테이블엔 Liquid Clustering 권장**. 우리는 partition 사용 중. `ais_positions`처럼 mmsi 기반 access 시 `CLUSTER BY (mmsi, date(received_at))`로 마이그레이션 검토 가치 있음 (Phase 1 Part C 또는 post-D-15).

### (e) `MERGE` — late-arriving / dedup upsert
```sql
MERGE INTO bronze.ais_positions tgt
USING staging src
ON tgt.mmsi = src.mmsi AND tgt.received_at = src.received_at
WHEN MATCHED THEN UPDATE SET ...
WHEN NOT MATCHED THEN INSERT ...
```
**제약**: 한 source row가 target row 여러 개에 매칭되면 fail. AIS reconnect 시 동일 메시지 재수신 dedup에 표준 패턴.

### (f) Change Data Feed (CDF) — `enableChangeDataFeed=true`
INSERT/UPDATE/DELETE row-level 변경을 별도 stream으로 노출:
```sql
SELECT * FROM table_changes('bronze.oil_prices', 100, 110)
```
→ silver/gold ETL에서 "마지막 처리 이후 변경분만" 가져올 때 사용. **활성화 시점 이후 변경분만** 캡처되는 점 주의.

→ 우리는 `oil_prices` 테이블만 CDF 활성 (silver layer가 5분 cron으로 새 가격만 incremental 처리).

### (g) `autoOptimize.optimizeWrite` + `autoOptimize.autoCompact`
**5분 cron에 6개 테이블에 매번 1~50 rows append 하면 하루 288 commits × 6 = 1700+ small files**. metadata overhead 폭증.

해결:
- `optimizeWrite=true`: 쓰기 시점에 파일 크기 개선 (큰 파일로 묶음)
- `autoCompact=true`: 쓰기 직후 자동 compaction (작은 파일 합침)

→ 우리는 자주 쓰는 테이블 4개(`oil_prices`·`ais_positions`·`gdacs_events`·`news_articles`)에 적용.

---

## 3. 우리 repo 코드와 매칭

### `infra/sql/bronze_schema.sql` 한 테이블 분석

```sql
CREATE TABLE IF NOT EXISTS crude_compass.bronze.oil_prices (
  fetched_at  TIMESTAMP    NOT NULL,
  source      STRING       NOT NULL COMMENT 'oilpriceapi',
  product     STRING       NOT NULL COMMENT 'WTI_USD | BRENT_CRUDE_USD | DUBAI_CRUDE_USD',
  price_usd   DOUBLE       NOT NULL,
  raw         STRING                COMMENT 'JSON 원본'
) USING DELTA
PARTITIONED BY (DATE(fetched_at))
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
);
```

| 요소 | 의미 |
|---|---|
| `crude_compass.bronze.oil_prices` | UC 3-tier 이름 |
| `USING DELTA` | (사실 default지만 명시. Databricks 표준) |
| `PARTITIONED BY (DATE(fetched_at))` | 일자별 디렉터리 — 시계열 query 가속 |
| `enableChangeDataFeed=true` | silver layer에서 "마지막 처리 이후 변경분만" 가져오기 |
| `optimizeWrite=true` + `autoCompact=true` | 5분 cron의 small file 폭증 자동 방지 |
| `raw` 컬럼 | 원본 JSON 보관 (디버깅·schema 변경 대응) |

### Bronze layer 설계 철학 (medallion)
- **Bronze** = 원본 그대로 (lossless). 우리 6 tables.
- **Silver** = 정제·통합·중복제거. (Phase 1 Part C 작성)
- **Gold** = 집계·domain logic. `gold.risk_indicators` 4-input 종합 risk score 시계열 등.

5분 데모에서 매니저가 보는 risk score 78점 = `gold.risk_indicators` query 결과.

---

## 4. 자주 헷갈리는 점 / 함정

### (1) Hive Metastore vs Unity Catalog
- 옛날 Databricks는 Hive Metastore (HMS) 기본. UC는 그 위에 govern 추가한 신세대.
- **현재 신규 workspace는 UC가 default**. HMS 표시되더라도 UC로 마이그레이션 권장.
- 공식 deprecation 날짜 명시 X. 다만 신규 기능(Genie semantic layer · Lakebase mirror · Lakeflow Connect)은 UC만 지원.

→ **우리는 무조건 UC**. `crude_compass` 카탈로그 생성 후 그 안에서만 작업.

### (2) `optimizeWrite` 누락 시 small files 폭증
시나리오:
- Tier 2 cron이 5분마다 1 row INSERT. 하루 288 row → 288 작은 Parquet file.
- 6개 테이블 × 30일 = **약 50,000 files**.
- query 시 metadata read overhead로 응답 시간 5~10배 증가.

**대응**: 우리 DDL이 이미 옵션 켜둠. 추가로 주 1회 `OPTIMIZE crude_compass.bronze.oil_prices` 명시 호출 권장 (Phase 1 Part C에서 nightly job).

### (3) Managed Table vs External Table
- **Managed** (우리 default — `LOCATION` 절 없음): cloud storage도 Databricks가 관리. `DROP TABLE` 시 8일 retention 후 영구 삭제. 그 전엔 `UNDROP TABLE`로 복구 가능.
- **External** (`LOCATION 's3://...'`): Databricks는 metadata만, storage는 별도. `DROP TABLE` 시 metadata만 삭제, 데이터 파일은 남음.

→ 우리는 Managed로 단순. 단 `DROP TABLE`은 신중히.

### (4) `DROP TABLE` vs `DELETE FROM`
- `DROP TABLE` (managed): 8일 후 영구 삭제. `UNDROP` 가능.
- `DELETE FROM`: transaction log에 tombstone. `VACUUM` 전까지 time travel로 과거 row 조회 가능.

### (5) Liquid Clustering 도입은 신규 테이블에만 권장
이미 partition 잡힌 테이블에 `CLUSTER BY` 추가하려면 **테이블 재생성** 필요. 우리 Phase 1엔 partition 그대로 진행, post-D-15에 Liquid 검토.

---

## 5. 5분 데모에 등장하는지

**간접 등장**. UI에 "Unity Catalog"라는 단어는 안 나오지만:
- **Phase 5 RFQ 비교 표**: `crude_compass.bronze.*` 데이터를 `silver`로 정제한 결과를 Genie가 query.
- **Phase 6 What-If**: Genie가 `crude_compass.gold.risk_indicators` JOIN.
- **Phase 7 AI/BI Dashboard**: Bronze 30일 시계열 직접 시각화.

발표자 멘트 한 줄 가능: "**모든 데이터는 Unity Catalog `crude_compass` 카탈로그 안에서 govern, 6개 Bronze Delta 테이블이 medallion 첫 단**".

---

## 6. 더 깊이 파려면 — docs URL 5개

1. **[Unity Catalog 시작하기](https://docs.databricks.com/aws/en/data-governance/unity-catalog/get-started)** — 3-tier 네임스페이스, 권한 기초
2. **[Delta Lake 전체](https://docs.databricks.com/aws/en/delta/)** — ACID·time travel·CDF·MERGE 한 곳
3. **[Liquid Clustering](https://docs.databricks.com/aws/en/delta/clustering)** — 2026 권장 방식
4. **[CREATE TABLE SQL Reference](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-table-using)** — TBLPROPERTIES 전체 목록
5. **[Auto Loader](https://docs.databricks.com/aws/en/ingestion/cloud-object-storage/auto-loader/)** — 파일 기반 점진 ingestion (참고용, 우리는 REST 호출이라 직접 미사용)

---

## 7. 5분 안 떠올리기

머릿속에 이것만 박혀 있으면 코드·디버깅 OK:

```
1. crude_compass.bronze.<table>  ← 항상 3-tier
2. 모든 우리 테이블 = Delta. autoOptimize 켜져 있음.
3. 시계열 access는 partition으로. (mmsi 같은 high-cardinality는 나중에 Liquid)
4. silver/gold는 우리가 만들 곳. risk_score는 gold에 살게 됨.
5. CDF 활성 = silver layer가 incremental refresh 가능.
6. UI에 안 보이지만, Genie/AI/BI Dashboard 모두 이 카탈로그를 read.
```
