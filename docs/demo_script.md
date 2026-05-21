# Crude Compass — 5분 제출 영상 대본 (한 take)

> 제작 방식: docs/demo_video_plan.md 참조. 통으로 화면+음성 한 take 녹음 →
> 앞부분(블록 A·B)은 HTML 씬으로 화면을 덮고, 전환멘트 뒤부터는 화면+음성 그대로.
> 시드 데이터 출처: scripts/_seed_demo_reports.py (실제 트리거 타임라인 5/15~5/21).
> 아키텍처 ground truth: docs/crude_compass_final_scenario.md §4·§5·§8.
>
> **척추(hero) = AI가 지정학·가격 신호를 즉시 읽어 Term:Spot 조달 비중·타이밍을 조정.**
> social impact = 그 귀결(조달비↓ → 소비자 물가 안정). 공개 데이터 = 방법론(받침).
>
> ⏱ **타이밍은 아래 표가 단일 기준** (섹션 헤더엔 절대시간 안 박음 — 편집해도 드리프트 X).

## 시간 예산 (하드캡 5:00, 목표 ~4:42)

| 블록 | 구간 | 방식 | 시간 |
|------|------|------|------|
| A 인트로(팀)+문제정의(Term:Spot 레버) | 0:00–0:52 | HTML | 52s |
| B 솔루션 아키텍처 (애니메이션 다이어그램) | 0:52–1:56 | HTML | 64s |
| — 전환멘트 + 1초 정적 (컷지점) | 1:56–2:01 | — | 5s |
| C1 의사결정 (일일보고서 = Term:Spot 권고) | 2:01–2:48 | 화면녹화 | 47s |
| C2 Slack 양방향 | 2:48–3:16 | 화면녹화 | 28s |
| C3 시황 (위험지수+유가) | 3:16–3:40 | 화면녹화 | 24s |
| C4 자료실 (OPEC+GDELT) | 3:40–3:58 | 화면녹화 | 18s |
| C5 조사 (Agent Bricks Supervisor) — 피날레 | 3:58–4:28 | 화면녹화 | 30s |
| D 마무리 | 4:28–4:42 | 화면녹화 | 14s |

총 ~4:42 (버퍼 18s). 내레이션은 또박또박 + 약간 빠른 SaaS 톤. 앞부분(A·B)은 화면 무관(HTML로 덮음) — 음성만 중요.

---

## 블록 A — 인트로 + 문제정의 (HTML)

**HTML 씬 메모:** 타이틀 "Crude Compass · Lee & Choi" → 2026년 2월 미·이란 전쟁(브렌트 $72 → $120 스파크라인, 호르무즈) → "고유가 → 인플레이션 → 소비자 물가" 체인 → 핵심 레버 시각화 "Term ↔ Spot" 저울 → 매그니튜드("카고 1건 ≈ 수천억 원, 1% = 수십억") → 문제("느리고 비싼 판단").

**내레이션 (그대로 읽기):**

> 안녕하세요. 저희는 Lee & Choi 팀입니다.
>
> 2026년 2월 미·이란 전쟁으로 브렌트유는 한 달 새 배럴당 70달러대에서 120달러 가까이 치솟았습니다. 고유가는 곧 인플레이션이고, 충격은 결국 소비자 물가로 전가됩니다. 원유를 거의 전량 수입하는 한국은 특히 취약합니다.
>
> 정유사가 이 충격에 맞서는 핵심 레버는 하나, 장기계약 Term과 현물 Spot의 비중과 타이밍입니다. 공급 위험이 커지면 Term으로 물량과 가격을 고정해 헤지하고, 임박한 현물 발주는 폭등 정점을 피해 늦춥니다.
>
> 원유 한 cargo가 수천억 원입니다. 여기서 1%만 더 잘 사도 수십억이 갈리고, 그 차이는 다시 소비자 물가로 이어집니다.
>
> 그런데 이 판단은 느리고 비쌉니다. 고가 단말과 전담 애널리스트가 며칠에 걸쳐 신호를 모아야 하니까요.

---

## 블록 B — 솔루션 아키텍처 (HTML, 애니메이션 데이터플로우)

> **목표: Technical Capability 정조준.** 6개 beat가 내레이션에 맞춰 좌→우로 한 단계씩 쌓이는 애니메이션. whisper 단어 타이밍에 각 reveal을 동기화. **4개 필수 tool(Databricks Apps · Genie · Lakebase · Agent Bricks)은 글로우 + 배지로 강조**, 나머지(Unity Catalog · Jobs · Foundation Model API)는 보조 라벨.

**다이어그램 빌드 시퀀스 (HTML 씬 스펙):**

1. **[공개 데이터 소스]** 좌측 6개 노드 fade-in, 각 "PUBLIC" 배지 + 수집주기:
   OilPriceAPI(유가 실시간) · OPINET KNOC(두바이 일별) · GDELT(뉴스 15분) · OPEC MOMR(월간) · EIA(주간) · ECOS 한국은행(환율).
2. **[Lakehouse 수집·정제]** 화살표 → "Databricks Jobs" → **Unity Catalog** `crude_compass` Bronze→Silver→Gold 3계층 pill 순차 점등 → `pattern_score` 게이지 0→100 충전. OPEC PDF 노드엔 **Document Intelligence `ai_parse_document`** 배지(PDF→구조화 숫자).
3. **[트리거 → 보고서]** 임계 칩 3종 점멸(GDELT imp≥80 / 가격 ±2% / pattern ±10pt) → **Foundation Model API · Claude Haiku-4-5** 노드 → 보고서 카드가 **Lakebase**(실린더, 강조 글로우)로 낙하.
4. **[Agent Bricks]** **Agent Bricks Supervisor**(단일 엔드포인트) 노드가 3 sub-agent로 분기: Genie(정형 데이터) · **Knowledge Assistant**(OPEC PDF 원문 RAG, 페이지 인용 — 실측 확인) · 권고 생성. trace 라인 애니메이션. "일일 종합 + 조사 둘 다 경유" 캡션. OPEC은 두 경로(Document Intelligence 구조화 + KA 원문 RAG) 동시 표현.
5. **[전달]** 화살표 → **Databricks Apps**(브라우저 프레임, AI/BI Dashboard embed) + Slack(양방향 ⇄ 화살표, "Socket Mode" 작은 라벨).
6. **[휴먼 루프]** 매니저 아이콘 채택/기각 → 화살표가 **Lakebase로 되돌아와** 사이클 닫힘. **채택된 보고서 = 매일 아침 Agent Bricks 일일 종합의 입력** (점선 화살표로 Lakebase→Supervisor 재진입 표시). 하단 카피: "결정은 사람 · 분석은 AI · 동기화는 Lakebase".

**내레이션 (그대로 읽기 — 각 문장이 위 beat 1~6과 매칭):**

> Crude Compass는 이 판단을 자동화합니다. 100% 공개 데이터로요.
>
> 왼쪽이 데이터 소스입니다. 실시간 유가는 OilPriceAPI, 두바이 일별 공식 종가는 한국석유공사 OPINET, 뉴스는 GDELT, 수급은 OPEC 월간 보고서와 미국 EIA, 환율은 한국은행 ECOS — 전부 공개 출처입니다.
>
> 이 데이터는 Databricks job으로 매일 자동 수집돼, Unity Catalog에 브론즈·실버·골드 3계층으로 정제됩니다. OPEC 월간 보고서 PDF는 Document Intelligence가 직접 파싱하고, 아침마다 multi-source 가중 합으로 위험 지수를 만듭니다.
>
> 가격, 지정학, 위험 지수가 임계를 넘으면, Foundation Model API의 Claude Haiku모델이 보고서를 작성하여 Lakebase에 저장합니다.
>
> 분석과 일일 종합은 Agent Bricks Supervisor가 맡습니다. 단일 엔드포인트가 Genie로 데이터를 조회하고, 지식 도우미가 OPEC 보고서 원문을 RAG로 찾아 인용까지 붙이고, 권고를 종합합니다.
>
> 결과는 Databricks Apps와 Slack으로 가고, 매니저의 결정은 다시 Lakebase로 돌아와 한 바퀴를 닫습니다. 수집부터 배포까지, 전부 한 플랫폼 안에서요.

---

## 전환멘트 + 컷지점

**내레이션:**

> 그럼 실제로 어떻게 동작하는지 보시죠.

**→ 여기서 1초 정적. 이 지점이 컷지점.** (whisper JSON에서 "보시죠" 끝 + 정적 구간을 찾아 앞 HTML / 뒤 녹화 경계로 사용.)

이후부터는 **화면 그대로 노출** — 아래 동작을 실제로 클릭하며 내레이션.

---

## C1 — 의사결정: 일일보고서 = Term:Spot 권고 (화면녹화)

**화면 동작:**
1. 앱 첫 화면 = 5/22 일일 종합 보고서(Hero) = **지난 주 매니저가 채택한 트리거 보고서들을 Agent Bricks가 종합한 결과**.
2. TERM 60→65%(+5), SPOT 35%(-5), 신뢰도 87, "위험방어 쪽으로 소폭 이동" 배지, 시나리오 절감(기준 2.3 / 상승 4.6 / 하락 0.6%) 마우스로 짚음.
3. 같은 페이지 아래 받은편지함(pending 3)로 스크롤.
4. pending 1건 열어 **채택** 클릭 → 활성으로 이동 확인 = 내일 종합의 입력이 됨.

**내레이션:** (화면 값과 1:1 매칭 + 휴먼 루프 메커니즘 강조)

> 화면은 5월 22일 오늘의 종합 보고서입니다. 이건 AI 혼자 만든 게 아닙니다. 트리거 신호가 뜰 때마다 AI가 보고서를 쓰고, 매니저는 받은편지함에서 채택할지 기각할지만 정합니다. 그렇게 한 주간 채택된 보고서들을 매일 아침 Agent Bricks Supervisor가 하나로 종합한 결과가 바로 이 화면입니다.
>
> 핵심은 위쪽 비중 제안입니다. Term을 기준 60%에서 65%로 단계적으로 올리고, Spot은 35%로 내립니다. 신뢰도 87, 예상 절감은 기준 2.3퍼센트·강세 4.6퍼센트 — 수천억 원짜리 카고에선 한 건에 수십억이 갈립니다.
>
> 근거는, 이번 주 채택된 세 건이 모두 공급 위험을 가리켰고, 전일 대비 두바이유가 2.27% 올라 추세가 확인됐다는 것. 결정은 사람이, 종합은 AI가 한 셈입니다.
>
> 지금 받은편지함엔 아직 검토 안 된 새 신호가 세 건 있습니다. 제가 이걸 채택하면, 활성 보고서로 올라가 내일 아침 종합의 입력이 됩니다.

---

## C2 — Slack 양방향 (화면녹화)

**화면 동작:**
1. Slack 전환 — pending 카드 표시.
2. 카드의 **활성화** 버튼 클릭.
3. 앱으로 전환 후 새로고침 → 상태가 같이 바뀐 것 확인.

**내레이션:**

> 같은 신호는 Slack으로도 옵니다. Slack 카드에서 바로 활성화를 누르면, 웹앱 상태가 즉시 함께 바뀝니다.
>
> 따라서 사용자가 집에 있더라도, slack 어플을 이용하여 AI가 생성한 보고서를 읽고 행동을 취할 수 있습니다.

---

## C3 — 시황: 위험지수 + 유가 (화면녹화)

**화면 동작:**
1. 시황 탭.
2. 멀티소스 위험 지수(pattern_score) 차트 — 5/15 급등 지점 짚음.
3. 두바이유(OPINET 일별) 차트 + 실시간 Brent·WTI(OilPriceAPI) 분리 영역.

**내레이션:**

> 시황 탭은 근거 데이터를 보여줍니다. 멀티소스 위험 지수는 전쟁의 시작인 2월 28일 부터 100으로 급등했고, 이후 높은 점수를 유지중입니다.
>
> 아래에선 Dubai, Brent WTI의 일별 가격 추이와 환율 변동을 한눈에 확인해볼 수 있습니다.
---

## C4 — 자료실: OPEC + GDELT (화면녹화)

**화면 동작:**
1. 자료실 탭.
2. OPEC 월간 석유시장 보고서 + GDELT 주요 보도 목록.

**내레이션:**

> 자료실에는 cron job으로 수집하는 OPEC 월간 석유시장 보고서와, GDELT가 잡은 주요 보도가 정리됩니다.

---

## C5 — 조사: Agent Bricks Supervisor (피날레, 화면녹화)

**화면 동작:**
1. 조사 탭.
2. 자연어 질의 입력(Genie+KA 둘 다 부르도록 OPEC 포함): "이번 주 러시아 신호와 OPEC 수급 전망을 함께 보면 Term 비중을 어떻게 가야 해?"
3. **"사고 과정"** 블록에 추론이 흐르며 그 사이사이 **GENIE 호출 → KNOWLEDGE ASSISTANT 호출** 배지가 순서대로 뜸 → 그 아래 **최종 답변**(Term 비중 추천)이 시각 분리되어 렌더. (사고 과정은 접이식)

**내레이션:** (개선된 UI 기준 — 사고과정↔답변 분리, 에이전트 인라인 표시)

> 마지막으로, 더 깊이 파고들고 싶으면 조사 탭에서 자연어로 직접 묻습니다. 이번 주 러시아 신호와 OPEC 수급 전망을 묶어, Term을 어떻게 가야 할지 물어보겠습니다.
>
> 위쪽 "사고 과정"을 보면, Supervisor가 추론하면서 Genie와 지식 도우미를 차례로 호출하는 게 그대로 보입니다. 그리고 그 아래에 최종 권고가 분리되어 정리됩니다. 사람이 판단할 근거와 결론을 한눈에 주는 거죠.

> [체크] Supervisor·Genie·KA 엔드포인트는 실측 READY 확인됨(`mas-ba3fbcb5` / `01f1…034` / `ka-6b456458`). 사고과정↔답변 분리 UI는 프론트 검증 완료(스크린샷). 녹화 전 조사 탭에서 위 질문으로 trace에 Genie+KA 둘 다 뜨는지만 한 번 확인. 미라우팅 시 Genie fallback으로라도 동작.

---

## D — 마무리 (화면녹화)

**화면 동작:** 일일 보고서 화면으로 복귀하거나 정적 화면. (선택) 끝에 HTML 아웃트로 타이틀 카드 1.5초 덧붙임.

**내레이션:**

> 정리하면, 결정은 사람이 하고, Term과 Spot의 비중 판단은 AI가 즉시 보조합니다. 더 빠르고 정확한 조달은 수천억 단위에서 수십억을 아끼고, 그 안정은 결국 소비자 물가로 돌아갑니다.
>
> Crude Compass였습니다. 감사합니다.

---

## 녹화 전 체크 (형욱)

1. 데모 데이터 리셋 (테스트 클릭으로 pending 소비됐으면):
   ```
   python scripts/_seed_demo_reports.py
   python scripts/_post_pending_to_slack.py
   python scripts/_post_daily_to_slack.py
   ```
2. 조사 탭 Supervisor/Genie 실제 응답 확인 (C5 리스크).
3. 한 take 녹음: 앞부분(A·B) 화면은 아무거나(덮을 거라 무관), 음성만 또박또박. 전환멘트 "보시죠" 뒤 **1초 정적** 꼭 줄 것.
4. 녹화 후 `npx hyperframes transcribe` → 단어별 JSON → 내(클로드)가 HTML 씬 타이밍 맞춰 조립.

## 심사축 매핑 (자기검증)

- Business Applicability → Term:Spot 비중 조정이라는 정유사 핵심 의사결정 + 수천억 카고에서 수십억 절감 매그니튜드(A·C1)
- Creativity & Innovation → 신호 자동 감지 → Term:Spot 권고 보고서 자동 발행 + 멀티소스 위험 지수 + AI 자동 중복기각
- UX & Insights → 일일 Hero 보고서 한 장에 권고·근거·기대절감 + 받은편지함 + Slack 양방향(C1·C2)
- Technical Capability → **B 애니메이션 아키텍처 다이어그램**(공개소스 → Document Intelligence `ai_parse_document`(OPEC PDF) + Unity Catalog 3계층 → FMA Haiku → Lakebase → Agent Bricks Supervisor 3 sub-agent[Genie · KA OPEC RAG · 권고] → Apps/Slack → 휴먼 루프) + 소켓모드 우회(C2·C5). 4개 필수 tool + Document Intelligence 한 화면에 시각화.
- Data Storytelling → 전쟁→물가→Term:Spot 척추 서사 + "수집부터 배포까지 한 플랫폼" 아키텍처 클로징(A·B·D)
