# 03. Lakeflow Jobs (+ Secret Management 부록)

> **Lakeflow Jobs** = Databricks의 워크플로우 오케스트레이션 레이어 (구 Workflows Jobs).
> cron · file arrival · table change · continuous 4 trigger + retry + dependency.
> 우리의 **Tier 1 Daily (06:30 KST)** + **Tier 2 Realtime (5분)** 자동 실행 엔진.

## 1. 왜 우리에게 필요한가

OilPriceAPI를 5분마다 호출해서 bronze에 row 추가하려면 누가 그걸 5분마다 돌리나? 사람이 손으로 X. 외부 cron(GitHub Actions 등) X (Databricks workspace 안에서 동작해야 cluster·secret·UC 권한 자연스러움).

→ **Lakeflow Jobs**:
- cron `*/5 * * * *` 한 줄로 5분 자동
- API fail 시 자동 retry
- task A → B 의존성 (price fetch 다 끝나야 risk_score 계산)
- secret reference로 API key 안전 주입
- 실행 history + 알림 + monitoring UI

5분 데모 narrative "5분마다 Brent spike 알림" — 이 Job이 백그라운드에서 돌고 있다는 의미.

---

## 2. 핵심 개념 7개

### (a) 명칭 변천 — Workflows → Lakeflow Jobs
2024 이전 "Databricks Workflows" / "Workflow Jobs". 2024~2026 "Lakeflow" 브랜드로 통합. **현재 공식 명칭 = "Lakeflow Jobs"**. 다만:
- "Lakeflow Connect" = 별개 (외부 데이터 source ingestion connector, 우리 미사용)
- "Lakeflow Declarative Pipelines" = 별개 (구 DLT)
- "Lakeflow Jobs" = orchestration

→ 헷갈림 방지: **우리가 쓰는 건 Jobs 만**.

### (b) Job vs Task vs Pipeline 계층
- **Job**: scheduling/running 최상위 단위. 우리 = `tier1_daily`, `tier2_realtime` 2개.
- **Task**: Job 안 최소 실행 단위. 우리 Tier 1 Job 안에 task 5~6개 (oil_prices · gdacs · ecos · news · risk_score · feed_gen).
- **Pipeline**: Lakeflow Declarative Pipelines (구 DLT) 실행. Job task로 호출 가능. 우리 Phase 1엔 미사용.

**한계**: 1 job max 1,000 tasks · workspace max 12,000 saved jobs · 2,000 동시 task runs. 충분.

### (c) Task type 5종
1. **Notebook** (workspace의 .py/.sql notebook)
2. **Python script** (Git provider repo의 .py 파일) ← **우리 채택**
3. **SQL** (warehouse에서 SQL 실행)
4. **Lakeflow Declarative Pipeline run**
5. **Run Job** (다른 Job 호출)

+ control flow: **if/else condition**, **for-each**, **Run if**.

→ 우리는 Python script + Git provider source. `databricks/ingestion/oil_prices.py` path를 Job task에 등록.

### (d) Cluster type 3가지
| Type | spinup | 비용 | 우리 적합도 |
|---|---|---|---|
| **Job cluster** | 매번 새로, ~분 단위 | 격리·낮음 | Tier 1 Daily(매일 1회) ⭕ |
| **All-purpose cluster** | 항상 켜져 있음 | 높음 | 데모 직전 standby ⭕ |
| **Serverless compute** | 즉시 | 사용량 기반 | Tier 2 5분 cron ⭐ |

**Tier 2 5분 cron은 Serverless 권장**. Job cluster spinup이 5분 cron 간격을 잡아먹을 수 있음.

### (e) Trigger 4종
1. **Scheduled** (cron) ← Tier 1 `30 6 * * *` · Tier 2 `*/5 * * * *`
2. **Continuous** (run 끝나면 즉시 다음) ← AIS WebSocket Job (별도 노트 04)
3. **File arrival** (UC storage location에 새 파일)
4. **Table update** (source Delta 변경 시)

+ 수동 Run Now.

**Cron timezone trap**: DST 있는 timezone 선택 시 hourly job skip 가능. Asia/Seoul은 현재 DST 미관측이지만 **확실히 하려면 UTC로 cron 작성** 권장. 06:30 KST = `30 21 * * *` UTC.

### (f) Task dependency + run_if 6 conditions
의존성 + 조건부 분기:
```
oil_prices ─┐
gdacs       ├─→ risk_score (run_if = "All succeeded")
ecos        │
news        ┘
```

`run_if`:
1. **All succeeded** (default) — 전부 성공
2. **At least one succeeded** — 하나라도
3. **None failed** — 실패 없음 (skipped 허용)
4. **All done** — 결과 무관 끝나면
5. **At least one failed** — 하나라도 실패 (cleanup용)
6. **All failed**

→ **함정**: default "All succeeded"라서 한 ingestion task만 죽어도 risk_score 안 돔. **None failed**나 **At least one succeeded** 검토 또는 ingestion 자체에 fail-safe (default 값 반환).

### (g) Retry / Timeout / Notification
- **Retries**: 횟수 + interval(ms). 외부 API 일시 장애 흡수.
- **Timeout**: task 단위. **각 retry마다 별도 적용**. retry 3 + timeout 5분 = 최대 15분 실행.
- **Notification**: task/job-level email + webhook. 실패 시 즉시 알림.

우리 Tier 2: retry 2 + timeout 4분 (5분 cron 충돌 방지).

---

## 3. 우리 repo 코드와 매칭

### Tier 1 Daily Job 매핑 (mental model)
```yaml
# Phase 1 Part B에서 databricks/jobs/tier1_daily.yml로 실제 작성
name: tier1_daily_curation
schedule: "30 21 * * *"  # 06:30 KST = 21:30 UTC
tasks:
  - task_key: fetch_oil_prices
    spark_python_task:
      python_file: databricks/ingestion/oil_prices.py
    job_cluster_key: tier1_cluster

  - task_key: fetch_gdacs
    spark_python_task:
      python_file: databricks/ingestion/gdacs.py
    job_cluster_key: tier1_cluster

  # ... ecos, news 병렬

  - task_key: calculate_risk_score
    depends_on: [fetch_oil_prices, fetch_gdacs, fetch_ecos, fetch_news]
    run_if: "AT_LEAST_ONE_SUCCESS"  # ingestion 1개 죽어도 진행
    spark_python_task:
      python_file: databricks/scoring/risk_score.py

  - task_key: generate_discovery_feed
    depends_on: [calculate_risk_score]
    spark_python_task:
      python_file: databricks/curation/feed.py
```

### Tier 2 Realtime Job
```yaml
name: tier2_realtime
schedule: "*/5 * * * *"  # 5분 (UTC)
tasks:
  - task_key: poll_oil_prices
    spark_python_task:
      python_file: databricks/ingestion/oil_prices.py
    serverless: true            # spinup 절약
    timeout_seconds: 240        # 4분 (5분 cron 안전 마진)
    max_retries: 2

  - task_key: rule_filter
    depends_on: [poll_oil_prices]
    # ... 2% spike 검출

  - task_key: agent_trigger
    depends_on: [rule_filter]
    run_if: "AT_LEAST_ONE_SUCCESS"
    # ... Custom Agent Monitoring 호출
```

### `databricks/ingestion/oil_prices.py` 의 이미 적용된 패턴
- `_api_key()` 함수가 env → dbutils.secrets fallback. **Job 환경변수 reference + 로컬 dev env 둘 다 OK**
- 1개 product 실패해도 다른 product 계속 (`continue` in loop) → task 자체는 성공 처리

---

## 4. 자주 헷갈리는 점 / 함정

### (1) Job cluster spinup이 5분 cron 잡아먹음
Job cluster는 매 run마다 새로 띄움 → spinup 분 단위. Tier 2 5분 cron에 쓰면 cron 간격을 잡아먹을 수 있음.
→ **Tier 2는 Serverless compute 사용**. Tier 1은 Job cluster OK (매일 1회라 spinup 무관).

### (2) `dbutils.secrets.get()` vs `{{secrets/scope/key}}` 차이
**둘 다 secret reference이지만 동작 위치가 다름**:

| 방식 | 어디서 | 매번 fresh? |
|---|---|---|
| `dbutils.secrets.get(scope, key)` | Python script **코드 안** | ⭕ 매 호출 fresh |
| `{{secrets/scope/key}}` | Job/cluster **환경변수** | ❌ cluster restart 전엔 갱신 안 됨 |

→ **secret 변경 후엔 cluster restart 필요** (env reference 사용 시).

### (3) Cron timezone — 안전책은 UTC
`Asia/Seoul` 선택 가능하나, DST 있는 다른 zone 영향 또는 추후 변경 risk. **UTC로 작성하고 코드 안에서 KST 변환**이 안전.

```yaml
schedule: "30 21 * * *"   # UTC, = 06:30 KST
timezone_id: "UTC"
```

### (4) `run_if = "All succeeded"` 함정
default라서 한 ingestion 죽으면 risk_score 안 돔.
**완화**:
- `AT_LEAST_ONE_SUCCESS`: 최소 1개 성공이면 진행
- `NONE_FAILED`: 실패만 없으면 진행 (skipped 허용)
- 또는 ingestion 자체가 fail-safe (default 값 + log warning)

### (5) Serverless 가용성·비용 — 명시적 수치 X
- 공식 docs: "available by default in most workspaces"
- 비용: `system.billing.usage` 테이블에서 확인 (24h delay 가능)
- → **벤치마크 1회 후 결정** 권장

### (6) Workspace 1시간당 Job 생성 한도 = 10,000
대규모 trigger system 만들 때 hit 가능. 우리는 무관 (수동 등록 2개).

---

## 5. Secret Management 부록

### 개념 (3분 읽기)
- **Secret scope**: secret 묶음. Databricks-managed encryption.
- **Secret**: scope 안의 key=value. 자동 redact (`[REDACTED]`).
- **Permission**: scope에 READ/WRITE. cluster owner는 READ 필요.

### CLI 등록 (우리 3 keys)
```bash
# 1) Scope 생성 (한 번만)
databricks secrets create-scope crude-compass

# 2) keys 등록 (각각 인터랙티브 또는 --string-value)
databricks secrets put-secret crude-compass oilpriceapi-key
databricks secrets put-secret crude-compass aisstream-key
databricks secrets put-secret crude-compass ecos-key

# 3) 검증
databricks secrets list-secrets crude-compass
```

### Python script 안에서 (`dbutils.secrets.get`)
```python
# databricks/ingestion/oil_prices.py 우리 코드
from databricks.sdk.runtime import dbutils  # Job runtime에서 자동 inject
api_key = dbutils.secrets.get(scope="crude-compass", key="oilpriceapi-key")
```

→ 우리는 env var fallback도 함께 처리:
```python
key = os.environ.get("OILPRICEAPI_KEY") or dbutils.secrets.get(...)
```
이러면 로컬 dev에선 env, Job에선 dbutils 둘 다 OK.

### 환경변수 reference 패턴
Job UI 또는 `databricks.yml` 에서:
```yaml
env_vars:
  OILPRICEAPI_KEY: "{{secrets/crude-compass/oilpriceapi-key}}"
```
script는 `os.environ["OILPRICEAPI_KEY"]` 로 접근.

**둘 중 하나만**: dbutils.secrets.get 직접 호출 OR env var reference. 우리는 dbutils 직접 호출 (코드 명시적).

### 권한 요구
- Cluster/Job owner = secret scope에 **CAN READ**
- secret 변경 시 env var reference 쓰면 **cluster restart 필요**

---

## 6. 5분 데모에 등장하는지

**간접 등장**. UI에 "Lakeflow Jobs"는 안 나오지만:
- **Phase 2 (00:30~01:00) — 24/7 Streaming Live**: "5분 cron이 Brent +3.2% spike 검출 → 매니저 알림" — 이 5분이 곧 **Lakeflow Jobs cron `*/5 * * * *`**.

발표 멘트:
> "백엔드는 Databricks Lakeflow Jobs로 5분 cron 자동. 외부 API fail 시 retry, 5분 안에 가격 spike 검출하면 Custom Agent로 trigger".

---

## 7. 더 깊이 파려면 — docs URL 5개

1. **[Lakeflow Jobs 개요](https://docs.databricks.com/aws/en/jobs/)** — Job/Task/Pipeline 한 곳
2. **[Trigger 4종](https://docs.databricks.com/aws/en/jobs/triggers)** — cron/file/table/continuous
3. **[Cron schedule + Quartz syntax + timezone](https://docs.databricks.com/aws/en/jobs/scheduled)** — DST trap
4. **[Task dependency / run_if 6 conditions](https://docs.databricks.com/aws/en/jobs/control-flow)**
5. **[Secret을 env var로 reference](https://docs.databricks.com/aws/en/security/secrets/secrets-spark-conf-env-var)**

추가:
- **[Asset Bundle (databricks.yml)](https://docs.databricks.com/aws/en/dev-tools/bundles/)** — Phase 1 Part B에 우리가 작성할 IaC

---

## 8. 5분 안 떠올리기

```
1. Lakeflow Jobs = Databricks orchestration.
2. cron `*/5 * * * *` 5분 / `30 21 * * *` 매일 21:30 UTC = 06:30 KST.
3. Task는 Python script + Git provider 권장. dbutils.secrets로 API key.
4. Tier 2 5분 cron엔 Serverless compute. Tier 1은 Job cluster OK.
5. 의존성 default = "All succeeded". 우린 "AT_LEAST_ONE_SUCCESS"로 완화.
6. retry + timeout으로 외부 API 안정화.
7. Secret = scope + key. CLI로 등록, dbutils.secrets.get으로 사용.
8. 데모에선 백그라운드. "5분 spike 알림"의 5분이 이 Job cron.
```
