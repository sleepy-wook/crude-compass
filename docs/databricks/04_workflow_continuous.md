# 04. Workflow Continuous Task

> **Continuous trigger** = Lakeflow Job의 4 trigger 중 하나. 한 run이 끝나면 (성공/실패) 자동으로 다음 run 시작.
> "**항상 켜져 있는 1 process**"가 아니라 **"run 끝나면 wrapper가 다시 띄움"**.
> 우리의 **AIS aisstream WebSocket 24/7 streaming** 패턴.

## 1. 왜 우리에게 필요한가

aisstream WebSocket은 24/7 연결 유지가 필수 (호르무즈 통과 선박을 놓치면 narrative 깨짐).

대안 검토:
- **Apps 안에서 직접 띄움?** ❌ Apps scale-to-zero 정책 (idle 컨테이너 죽음). long-lived socket 부적합.
- **Lakeflow Declarative Pipeline (DLT) Streaming Table?** ❌ DLT의 표준 source는 Auto Loader · Kafka · Delta. WebSocket은 custom DataSource 작성 필요 (비용 큼).
- **Lakeflow Job continuous task** ✅ raw Python `websockets` lib + 자동 재시작 wrapper.

**핵심 원칙**: AIS streaming만 Workflow에 분리. Apps는 Delta `bronze.ais_positions`만 read.

---

## 2. 핵심 개념 6개

### (a) Trigger 4종 중 continuous
이전 노트(03)에서 본 4 trigger:
- scheduled (cron)
- **continuous** ← 이 노트
- file_arrival
- table_change

continuous = "run wrapper". user code는 무한 loop 또는 짧은 batch 어느 쪽이든 OK.

### (b) max_concurrent_runs = 1 (강제)
continuous job은 **항상 동시 1개**. 한 run이 죽으면 시스템이 재시도 후 새 run.
**왜?** 같은 WebSocket 2개가 동시에 같은 메시지 받으면 **중복 append**. 절대 늘리지 말 것.

### (c) Exponential backoff
연속 실패 시 시스템이 backoff:
- run 1 실패 → 즉시 retry
- run 2 실패 → ~1분 후
- run 3 실패 → ~2분 후
- ... max 도달 후 그 주기로 무한 retry
- **성공 시 backoff sequence 리셋**

→ 외부 장애가 풀리면 자동 복구.

### (d) Continuous Job vs DLT Streaming
| | Continuous Job | DLT Streaming Table |
|---|---|---|
| 본질 | "run 끝나면 다시 시작" wrapper | Spark Structured Streaming micro-batch |
| User code | 자유 (무한 loop 권장) | declarative SQL/Python, source 정의만 |
| 표준 source | 아무거나 (raw `websockets`) | Auto Loader · Kafka · Delta |
| Checkpoint | user 책임 | 자동 |
| Exactly-once | user 책임 (idempotent write) | 자동 |
| 우리 use case | ✅ aisstream (custom WS) | ❌ 표준 source 미지원 |

→ aisstream은 Spark 표준 source 미지원이라 **Continuous Job + raw Python**가 현실적 표준 패턴.

### (e) Cluster size for streaming
WebSocket 1개 + 100 row buffer 정도면 **Single Node** 충분. driver만 있으면 됨. Photon · autoscale 불필요.

비용 최적화:
- 가장 작은 instance type (2 vCPU 4GB)
- spot instance 가능 (kill 시 reconnect 비용 고려)
- DBR 15.4 LTS+ Single Node 4GB 1대 = 시간당 1 DBU 미만

### (f) Reconnect 책임 분리
Continuous Job 시스템 retry는 **run 단위** (분 단위 지연). 짧은 네트워크 끊김에는 과함.

→ user code 안에 자체 reconnect:
```python
while True:
    try:
        async with websockets.connect(URL) as ws:
            async for msg in ws: ...
    except (ConnectionClosed, OSError):
        await asyncio.sleep(5)  # 짧은 backoff
```

진짜 fatal (cluster OOM 등)일 때만 process exit → 시스템 retry로 cluster 재시작.

---

## 3. 우리 repo 코드와 매칭

### `databricks/workflows/ais_continuous.py` 분석

```python
# (1) WebSocket subscribe 메시지
subscribe_msg = {
    "APIKey": api_key,
    "BoundingBoxes": [HORMUZ_BBOX],          # [[24.0, 54.0], [27.5, 58.0]]
    "FiltersShipMMSI": [str(m) for m in mmsi_list],  # 익명 charter 5척
    "FilterMessageTypes": ["PositionReport", "ShipStaticData"],
}
```

→ 두 필터(BBox + MMSI)가 AND인지 OR인지 aisstream 공식 문서 확인 필요. **추측 X**, 실측 또는 aisstream docs 별도 확인.

```python
# (2) 100 rows or 5초 buffer flush
BUFFER_FLUSH_SIZE = 100
BUFFER_FLUSH_SECONDS = 5.0

if len(buffer) >= BUFFER_FLUSH_SIZE or (now - last_flush) >= BUFFER_FLUSH_SECONDS:
    df = spark.createDataFrame(buffer, schema=AIS_SCHEMA)
    df.write.mode("append").saveAsTable(TARGET_TABLE)
    buffer.clear()
```

→ **장점**: 100 row 모아서 한 commit = small file 절약.
→ **함정**: cluster kill 시 buffer 메모리만에 있는 row 손실. 5초 max flush로 손실 최소화.

```python
# (3) 자동 reconnect (시스템 + user 이중)
def main():
    while True:                      # ← user reconnect
        try:
            asyncio.run(stream_loop(spark))
        except (ConnectionClosed, OSError):
            time.sleep(5)
```

cluster OOM 같은 fatal 시에만 process exit → continuous Job wrapper가 새 run 띄움.

### Job 등록 (사용자 setup 가이드 참조)
```
Workflows → + Create job → name: crude-compass-ais-stream
  Task type: Python script
  Source: Git provider, path = databricks/workflows/ais_continuous.py
  Cluster: Single Node, DBR 15.4 LTS, 2 vCPU 4GB
  Libraries: PyPI websockets>=12.0
  Schedule: Continuous (← cron 아님!)
  Max concurrent runs: 1 (강제, 변경 X)
  Retries: 3
```

---

## 4. 자주 헷갈리는 점 / 함정

### (1) "Continuous = 멈추지 않는 1개 process" 가 아님
run wrapper일 뿐. user code가 stdout exit하면 cluster도 재기동될 수 있음 → cold start 수십 초~분 지연.
→ **user code는 자체 long-lived loop**여야 진짜 24/7. exit 조건은 fatal에만.

### (2) max_concurrent_runs 늘리면 데이터 중복
같은 WebSocket 2개 = 같은 메시지 2번 append. 절대 늘리지 말 것. continuous 모드의 핵심 가드.

### (3) Cluster restart 시 buffer loss
100 row buffer가 메모리에만 있으면 OOM/spot kill 시 사라짐. aisstream은 backfill 미지원이라 그 시간 메시지 영구 손실.

**완화**:
- buffer size 작게 (우리 100 또는 5s)
- Spot 사용 시 trade-off 인지
- 매 메시지 즉시 append? → small file 폭증으로 더 비싸짐. 100 row buffer가 sweet spot.

### (4) 비용 — continuous는 cluster 24/7
Single Node 2vCPU × 24h × 30d ≈ 비용 산정 필요. Express $700 credit 안에서:
- 데모 기간 (5/9 ~ 5/22, 14일) ≈ Single Node 14일 24/7
- post-deploy 1개월 추가

→ **Express 한정**: 데모일 외엔 Workflow pause 검토. (트레이드: pause 시 그 시간 데이터 결손)

### (5) Append vs Merge — duplicate 가능
Delta `append`는 무조건 추가. reconnect 후 동일 timestamp 메시지 재수신 시 row 2개.

**완화**:
- silver 단계에서 `(mmsi, ts)` dedup
- 또는 bronze에 직접 MERGE (성능 trade-off)
- 우리는 silver dedup 채택 (Phase 1 Part C)

### (6) Pause 후 재개 시 catch-up 없음
aisstream은 live feed. pause 동안 메시지 재전송 X.
**Continuous Job suspend = 그 시간 데이터 영구 결손**.
→ 데모 직전에만 끄는 식 운영 X. 데모 1시간 전 row count 검증 필수.

---

## 5. 5분 데모에 등장하는지

**직접 등장 X, 백그라운드 의존성 O.**

- **Phase 3 Mission Cargo Map (01:00~02:00)**: 호르무즈 통과 charter 5척 위치 점멸. 이 데이터는 `bronze.ais_positions`에서 read. 데모 시작 30분 전부터 continuous job이 돌고 있어야 최신 row.
- 데모 발표자가 한 줄 멘트 가능: "이 위치 데이터는 백엔드 **Lakeflow continuous task**가 aisstream WebSocket 24/7 구독해서 적재".

**위험**: 데모 당일 cluster 죽어있으면 지도 텅 빔. 1시간 전 검증 필수:
```sql
SELECT COUNT(*), MAX(received_at)
  FROM crude_compass.bronze.ais_positions
  WHERE received_at > current_timestamp() - INTERVAL 5 MINUTES;
-- N rows. 0이면 Job 상태 + WS 연결 점검
```

---

## 6. 더 깊이 파려면 — docs URL 4개

1. **[Continuous Job](https://docs.databricks.com/aws/en/jobs/continuous)** — retry · backoff · 1개 동시 실행
2. **[Trigger 4종](https://docs.databricks.com/aws/en/jobs/triggers)** — continuous 비교
3. **[Structured Streaming 개요](https://docs.databricks.com/aws/en/structured-streaming/index)** — 표준 source 한계 (왜 raw WS 쓰는지 정당화)
4. **[DLT 개요](https://docs.databricks.com/aws/en/delta-live-tables/index)** — continuous job 대안 (우리 미사용 이유)

---

## 7. 5분 안 떠올리기

```
1. Continuous trigger = Lakeflow Job. run 끝나면 다음 run 자동 띄움.
2. max_concurrent_runs = 1 강제. 늘리면 데이터 중복.
3. Single Node 2vCPU 4GB 충분. Photon·autoscale 불필요.
4. user code = 무한 loop. WS reconnect는 코드 안. fatal 시만 exit.
5. DLT 안 쓰는 이유: aisstream은 표준 source 미지원.
6. 100 row or 5s buffer flush = small file vs latency 균형.
7. Append + silver dedup. 또는 bronze MERGE.
8. 데모 1시간 전 row count check 필수. 없으면 지도 텅 빔.
```
