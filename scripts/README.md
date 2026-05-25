# Scripts — Crude Compass

운영·데모용 보조 스크립트. `databricks --profile crude-compass` 인증 + secret scope `crude` 사용.

```bash
PYTHONIOENCODING=utf-8 python scripts/<name>.py
```

> `_`로 시작하는 스크립트는 로컬 보조용(커밋 제외 대상). 나머지는 인프라/검증용.

## 데모 데이터
| 파일 | 목적 |
|---|---|
| `_backfill_reports.py` | **실데이터 point-in-time 재생성** — 트리거·일일 보고서를 5/15~오늘까지 실제 수집 데이터로 LLM 생성(미래 미지, 시계열). `run` = DELETE 후 재생성, `preview <YYYY-MM-DD>` = 1일 미리보기(미기록). **데모 데이터 표준.** |
| `_post_pending_to_slack.py` | pending 트리거 보고서를 Slack으로 전송(양방향 데모) |
| `_post_daily_to_slack.py` | 오늘 일일 종합 보고서를 Slack으로 전송 |
| `_seed_demo_reports.py` | (구) 손-큐레이션 시드 — `_backfill_reports.py`로 **대체됨**. 폴백용으로만 잔존 |

## 인프라 · 검증
| 파일 | 목적 |
|---|---|
| `apply_schemas.py` | Unity Catalog bronze/silver/gold DDL 일괄 적용 (하드코딩 DDL). **`databricks/schemas/config.sql`(gdelt_queries)은 미포함 — 별도 적용 필요** |
| `setup_agent_activity_events.sql` | Lakebase `agent_activity` 이벤트 테이블 셋업 |
| `verify_data_quality.py` | 수집 데이터 품질 점검 |
| `_trigger_ingest_jobs.py` | 수집 잡(gdelt/price 등) 수동 트리거 |
| `dev_local.bat` | 로컬 dev(백엔드+프론트) 실행기 |

## 데모 전 데이터 리셋 순서
```bash
PYTHONIOENCODING=utf-8 python scripts/_backfill_reports.py run   # 실데이터 재생성
python scripts/_post_pending_to_slack.py
python scripts/_post_daily_to_slack.py
```
