# 02. Lakebase Autoscaling Postgres

> **Lakebase Autoscaling** = Databricks가 fully managed로 제공하는 **OLTP 전용 Postgres**.
> 0.5~32 CU 자동 확장, scale-to-zero, branching 지원. Apps에서 자동 env 주입.
> 우리 프로젝트의 **mission state 영속 4 tables**가 사는 집.

## 1. 왜 우리에게 필요한가 — Postgres가 Delta로 왜 안 되나

Crude Compass에서 OLTP 워크로드:
- 매니저가 swipe → `decisions` INSERT (1 row)
- AI가 RFQ 발송 → `rfq_negotiations` INSERT
- 매니저 confirm → `mission_events` INSERT + `missions.current_term_pct` UPDATE
- 5초마다 `current_day` 체크 → SELECT
- 분 단위 1~수십 row read/write가 끊임없이.

이걸 Delta로 하면:
- **단일 row UPDATE도 file 단위 rewrite** → 비용·latency 폭증
- 컬럼 포맷이라 row-level access 비효율
- 동시 writer 충돌 처리 보수적

→ **OLTP는 Postgres**, analytics는 Delta. Lakebase가 두 세계를 같은 UC governance 안에서 묶어줌.

**4주 mission이 살아있어야 하는 이유**: 매니저는 휴가·회의·잠 사이에도 mission이 계속 진행. AI가 47건 자율 행동을 모두 어딘가 영속해야. Lakebase가 그 어딘가.

---

## 2. 핵심 개념 7개

### (a) Autoscaling vs Provisioned
2026-03 이후 신규 Lakebase는 **Autoscaling 중심** (Databricks 공식: "New Lakebase development is focused on Autoscaling"). Provisioned는 수동 capacity 관리.

→ 우리 `crude-compass-pg` 인스턴스 = Autoscaling.

### (b) Capacity Unit (CU)
1 CU ≈ 2 GB RAM + CPU/SSD. Autoscaling 범위 0.5~32 CU.
**제약**: max − min ≤ 16 CU. 예) 1~16 OK, 8~24 OK, 0.5~32 **불가**.

→ 처음 1 CU (autoscale 1~8 정도)로 충분. 5분 데모는 0.5~2 CU도 됨.

### (c) Apps 자동 env 주입 (6개)
Apps에 Lakebase 리소스 attach하면 다음 env 자동:
```
PGHOST       — Postgres host
PGPORT       — 보통 5432
PGDATABASE   — DB 이름 (우리: crude_compass)
PGUSER       — 자동 발급된 SP의 Postgres role
PGSSLMODE    — require
PGAPPNAME    — 식별용 (logging)
```

`PGPASSWORD`는 **자동 주입 X**. 이게 가장 큰 함정.

### (d) OAuth 토큰 (PGPASSWORD 대체)
```python
from databricks.sdk import WorkspaceClient
w = WorkspaceClient()
creds = w.database.generate_database_credential(instance_names=["crude-compass-pg"])
token = creds.token  # 1h TTL
```
이 token을 Postgres password 자리에 쓰면 됨.

**TTL = 1시간**. 만료 후 새 connection 시 fail. 기존 연결은 유지.

### (e) Service Principal vs User principal
- **U2M** (User-to-Machine): 사용자 token, 로컬 dev에 쓰임
- **M2M** (Machine-to-Machine): Service Principal, **Apps 같은 무인 서비스 표준**

→ Apps가 deploy되면 SP context로 동작. PGUSER = SP의 Postgres role.

### (f) psycopg 3 권장 (vs psycopg2)
2026 docs 예시는 모두 `psycopg` (= psycopg3) + `psycopg_pool.ConnectionPool`. 차이:
- `psycopg.connect()`는 keyword args만
- async API 더 깔끔
- prepared statement 디폴트 다름

→ 우리 `pyproject.toml` 에 `psycopg[binary,pool]` 명시.

### (g) JSONB + GIN index — 반정형 데이터
Postgres만의 강점. `mission_events.payload` 같은 RFQ 견적·outcome JSONB로 저장 + GIN index로 query 가능.
```sql
CREATE INDEX idx_events_payload ON mission_events USING GIN (payload);
SELECT * FROM mission_events WHERE payload @> '{"counterparty":"Aramco"}';
```

→ Delta에는 없는 패턴. mission_events에 GIN index 적용.

---

## 3. 우리 repo 코드와 매칭

### `apps/api/services/lakebase.py` 분석

```python
class LakebaseClient:
    def _refresh_token(self) -> str:
        from databricks.sdk import WorkspaceClient
        instance = os.environ["DATABRICKS_LAKEBASE_INSTANCE"]
        w = WorkspaceClient()
        creds = w.database.generate_database_credential(instance_names=[instance])
        self._token = creds.token
        self._expires_at = datetime.now(tz=utc) + timedelta(seconds=3600)
        return self._token

    def _get_token(self) -> str:
        # 5분 전 refresh
        if self._token and self._expires_at and \
           datetime.now(tz=utc) < self._expires_at - timedelta(minutes=5):
            return self._token
        return self._refresh_token()

    def conn(self) -> psycopg.Connection:
        return psycopg.connect(
            host=os.environ["PGHOST"],
            port=int(os.environ.get("PGPORT", "5432")),
            dbname=os.environ["PGDATABASE"],
            user=os.environ["PGUSER"],
            password=self._get_token(),     # ← OAuth token!
            sslmode=os.environ.get("PGSSLMODE", "require"),
            application_name=os.environ.get("PGAPPNAME", "crude-compass"),
        )
```

핵심:
- `_refresh_token` 안의 `instance_names=[instance]` ← Databricks SDK 공식 패턴
- `_get_token` 의 5분 안전 마진 ← 1h 만료 직전 fail 방지
- `conn()` 의 `password=self._get_token()` ← env에서 안 가져오고 SDK token 주입
- `threading.Lock` 으로 concurrent refresh 방지

### `infra/sql/lakebase_schema.sql` 의 Postgres-only 기능들

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;        -- gen_random_uuid()
mission_id UUID PRIMARY KEY DEFAULT gen_random_uuid()
                                                  -- replica 환경에서 충돌 없는 PK
payload JSONB                                    -- 반정형 데이터
CREATE INDEX idx_events_payload USING GIN (payload)
                                                  -- JSON 안 query indexable
FOREIGN KEY (mission_id) REFERENCES missions(...) ON DELETE CASCADE
                                                  -- mission 삭제 시 자식 자동 정리
                                                  -- (Delta에는 없는 referential integrity)
CHECK (status IN ('active','completed','paused','cancelled'))
                                                  -- DB 레벨 enum validation
CREATE INDEX idx_decisions_outcome_pending
    ON decisions(decided_at) WHERE outcome IS NULL;
                                                  -- partial index — pending만 빠르게 scan
CREATE TRIGGER missions_set_updated_at
  BEFORE UPDATE ON missions
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
                                                  -- plpgsql trigger로 updated_at 자동
```

전부 OLTP/Postgres만의 기능. Delta로는 못 함.

---

## 4. 자주 헷갈리는 점 / 함정

### (1) PGPASSWORD가 env에 없다고 당황 X
Apps는 의도적으로 비워둠. **SDK 토큰을 password 자리에 주입하는 게 정답 패턴**. 처음 보면 "왜 PGPASSWORD가 없지?" 헷갈림.

### (2) 토큰 1h 만료 — refresh 안 짜면 정확히 1시간 후 fail
naive 구현:
```python
# ❌ 1시간 후 죽음
token = w.database.generate_database_credential(...).token
def conn():
    return psycopg.connect(..., password=token)
```

올바른 구현:
```python
# ✅ 5분 전 refresh
def get_token():
    if expires_at and now() < expires_at - 5min: return cached
    return refresh()
```

→ 우리 `LakebaseClient._get_token` 패턴 이미 적용.

### (3) Lakebase 인스턴스 provisioning은 즉시 X
`Create database instance` 클릭 후 **5~10분** Status=Available 대기.
**데모 직전** 만들지 말 것. 5/9 일찍 띄워두면 나머지 시간 안전.

### (4) Apps에서 user principal로 돌리면 권한 꼬임
Apps deploy하면 SP context로 동작. PGUSER에 user principal Postgres role 매핑하면 `permission denied for table missions` 발생. SP 매핑이 정답.

→ 사용자 setup 가이드(`docs/setup/phase1_databricks_setup.md`)에 SP 등록도 포함되어야 함 (Phase 4 deploy 전).

### (5) psycopg2 → psycopg3 마이그레이션 차이
- `psycopg2.connect("postgresql://...")` → `psycopg.connect(...)` keyword only
- `cursor.execute("SELECT %s", (1,))` 동일 (호환)
- `psycopg2.pool.ThreadedConnectionPool` → `psycopg_pool.ConnectionPool`

우리는 이미 psycopg3 사용 (`pyproject.toml`에 `psycopg[binary,pool]>=3.2.0`).

---

## 5. 5분 데모에 등장하는지

**Wow 1 (Phase 3, 01:00~02:00) — Living Mission Dashboard 직접 등장.**

```
매니저 페이지 진입 → React MissionPage
  → fetch /api/mission/00000000-...-001
  → FastAPI lakebase.py: SELECT m.*, e.* FROM missions m JOIN mission_events e
                          WHERE m.mission_id = $1
  → 즉시 응답 (Postgres OLTP, < 50ms)
```

**스크린샷에 표시되는 것**:
- D+18 timeline 28일 grid (28 calls in `mission_events`)
- Term 65% progress bar (`missions.current_term_pct`)
- Frame Contract 4사 (`rfq_negotiations` 4 rows)
- AI 자율 47건 / 매니저 승인 3건 (mission_events count)

→ "Lakebase가 4주 mission state 영속" narrative를 1 화면에 시각적으로 증명.

발표 멘트:
> "이 mission은 4주 진행 중. 매니저가 회의·휴가하는 사이에도 AI가 47건 자율 행동을 모두 **Lakebase Postgres에 영속**. 매니저가 어디서 접속해도 동일 state."

---

## 6. 더 깊이 파려면 — docs URL 5개

1. **[Lakebase Autoscaling 개요](https://docs.databricks.com/aws/en/oltp/projects/about)** — branching·scale-to-zero·CU 정의
2. **[Compute 관리 (CU)](https://docs.databricks.com/aws/en/oltp/projects/manage-computes)** — 1 CU = 2GB · max-min ≤ 16
3. **[OAuth 토큰 인증](https://docs.databricks.com/aws/en/oltp/instances/authentication)** — SP/User · CLI generate-database-credential
4. **[Apps + Lakebase 튜토리얼](https://docs.databricks.com/aws/en/oltp/projects/tutorial-databricks-apps-autoscaling)** — env 자동 주입 · psycopg pool · token rotation 코드 예시
5. **[Provisioned → Autoscaling 마이그레이션](https://docs.databricks.com/aws/en/oltp/upgrade-to-autoscaling)** — 신규 개발이 왜 Autoscaling 중심인지

---

## 7. 5분 안 떠올리기

```
1. Lakebase = managed Postgres OLTP. mission state 영속.
2. Apps에 attach하면 PG* 6개 env 자동, 단 PGPASSWORD는 미주입.
3. SDK로 OAuth token 받아 password 자리에. TTL 1h, 5분 전 refresh.
4. SP가 Apps 권한 컨텍스트. PGUSER=SP.
5. JSONB + GIN + plpgsql trigger + partial index — Delta에 없는 OLTP 기능 풀활용.
6. 인스턴스 provisioning 5~10분, 데모 직전 만들지 말 것.
7. 데모 Wow 1 = Mission Dashboard. 4주 영속이 증명.
```
