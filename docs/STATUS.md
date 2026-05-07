# Crude Compass — 출근길 5분 status

> 마감 2026-05-22 (D-14). 어디까지 왔고 어디서 시작할지.

## ✅ 완료 (5/7~5/8)

| 단계 | 산출물 |
|---|---|
| **Phase 0** 검증·부트스트랩 | docs v2 / apps/web Vite build pass / apps/api FastAPI smoke-test pass |
| **Phase 1 Part A** 코드 | bronze 6 tables DDL · lakebase 4 tables + seed · oil_prices.py · ais_continuous.py · 사용자 setup 가이드 |
| **학습 노트 Round 1** | `docs/databricks/{01..04}_*.md` (UC+Delta · Lakebase · Lakeflow Jobs · Workflow continuous) |

## ☕ 출근하자마자 — 15분 reading

`docs/databricks/01..04` 4개의 **§7 "5분 안 떠올리기"** 만 읽기. 4 × 7줄 = 30줄. 이걸로 다음 setup 작업의 모든 결정이 머리에 들어옴.

각 노트는 일관된 구조:
1. 한 줄 요약 + 우리 프로젝트 기준 "왜 쓰나"
2. 핵심 개념 5~7개
3. **우리 repo 코드와 1:1 매칭** ← 이론과 코드 연결 핵심
4. 자주 헷갈리는 점 / 함정
5. 5분 데모에 등장하는지
6. 더 깊이 파려면 (검증된 docs URL)
7. **5분 안 떠올리기** ← 출근길용

## 🔑 1순위 작업 — 사용자 Databricks setup (~1.5h)

`docs/setup/phase1_databricks_setup.md` 따라서:

| | 작업 | 시간 |
|---|---|---|
| A. 미리 준비 | OilPriceAPI Developer **$19 결제** + aisstream/ECOS key 발급 + Databricks CLI 0.230+ | 15분 |
| B. workspace | UC `crude_compass` catalog + bronze 6 tables + Lakebase 인스턴스 + 4 tables + secrets 3개 + oil_prices Job smoke-test + AIS Workflow continuous 등록 | 40~60분 |
| C. 검증 | 7개 SQL query로 row count 확인 | 5분 |

> Lakebase 인스턴스 provisioning이 5~10분 걸리니까 일찍 띄우고 다른 거 하면 효율적.

→ B 어디서 막히면 정확한 에러 + step 알려주세요. 같이 즉답.

## ❓ 결정 필요 — 5/9 어떻게 시작?

- **(a) 위 사용자 setup 1.5h** — Phase 1 가장 위험한 가정 검증 (Apps에서 Lakebase OAuth 작동 + cron 5분 Job 작동) ⭐ 권고
- **(b) Round 2 학습 노트 4개 먼저** (Apps · Genie · Agent Bricks · AI/BI Dashboard) 30분 → 그 후 setup
- **(c) Phase 1 Part B 코드 먼저** (gdacs/ecos/news ingest + Asset Bundle) ~3h → setup은 5/10

권고: **(a)**. 코드만 쌓으면 deploy risk가 D-day까지 누적. Setup 1번 검증해두면 Phase 4 deploy 자신감.

대안 (b)도 합리적 — 머리 정리 후 setup이 더 매끄러움. 30분 추가 투자 가치 있음.

## 📍 현재 Phase 위치

```
Phase 0  ✅ 검증·부트스트랩
Phase 1  ⏳ Part A ✅ / Part B 미진행 / Part C 미진행
Phase 2  ⏸ Agents (5/12~14, Plan B trigger 5/14 23:59)
Phase 3  ⏸ Frontend (5/15~19)
Phase 4  ⏸ Deploy (5/20~21)
Phase 5  ⏸ Demo (5/22)
```

## 📂 어디 있나

| | path |
|---|---|
| 시나리오 (source of truth) | `docs/scenario.md` |
| 아키텍처 v2 | `docs/architecture.md` |
| 학습 노트 | `docs/databricks/` |
| 사용자 Databricks setup | `docs/setup/phase1_databricks_setup.md` |
| Frontend 코드 | `apps/web/` |
| Backend 코드 | `apps/api/` |
| Bronze/Lakebase DDL | `infra/sql/` |
| Databricks ingestion·Workflow | `databricks/` |
| Apps deploy spec | `app.yaml` |
| 메모리 | `~/.claude/projects/C--crude-compass/memory/MEMORY.md` |

## 💡 비용·시간 메모

- Databricks Express credit: $700 (현재까지 사용 ~$0)
- OilPriceAPI: **$19 × 2개월 = $38**
- 합계 $38 (D-15 + post-deploy 1개월)
- 사용자 시간: 15일 × 평균 3h ≈ 45h (본업 + 가족 + 이거 균형)

## 🚦 진행 원칙 재확인

1. **코드는 AI / Databricks workspace UI는 사용자** (학습 목적)
2. **D-15 마감 절대성** — scope 부풀리기 X, 단순 > 복잡
3. **약점 보이면 즉시 push back** (무지성 공감 X)
4. **Plan B trigger 명문화** (5/14 Agents cut, 5/19 Streamlit fallback, 5/21 Genie cache fallback)
5. **design/ 폴더 절대 수정 X** — apps/web/에 새로 작성

---

**잘 자고, 출근길 30줄 읽고, 어떻게 시작할지(a/b/c) 알려주세요. 그때부터 즉시 진행.**
