# D-0 영상 5분 Storyboard (형욱님 녹화용)

> 작성: 2026-05-17 (D-1)
> 5축 평가 결과 영상이 60% 가중. 1등 위해 5 scene 정밀 합의.
> 본 storyboard는 형욱님 review 후 확정.

## 평가위원 시점 가정

- 영상 자동 재생 시작 후 첫 **30초가 시청 결정**
- 평가위원은 다수의 영상을 본 후 피로 상태 — emotional hook + 즉시 이해 가능 narrative 필수
- 한국어 트랙이지만 일부 영문권 위원도 가능 → 핵심 명사는 한글 + 영문 병기 권장 (예: "위험방어 (HEDGE)")

## Scene 구조 (5분 = 300초)

### Scene 1: Hook (0:00-0:30) — Track 1 Social Impact narrative

**화면**: title card → 호르무즈 해협 위성 사진 또는 뉴스 헤드라인 collage (Iran sanctions / Russia-Ukraine / UK Maritime alerts)

**나레이션 (한국어)**:
> "한국은 원유의 73.5%를 중동에서 수입합니다. 호르무즈 해협이 봉쇄되면 5,000만 국민의 에너지 안보가 흔들립니다.
>
> 대형 정유사는 분석가 50명을 두고 24시간 모니터링하지만, 중소 정유사 5인 구매팀은 같은 정보를 보지 못합니다.
>
> Crude Compass는 6가지 공개 데이터를 AI가 종합해서 '지금 사두세요(위험방어)' 또는 '지금 천천히(기회포착)' 를 추천합니다. **5인 팀도 대기업처럼 일하게.**"

**Hook 강도 강화**: 0:25에 K-Petroleum 가상 disclosure 자막 1줄 — "본 데모는 가상 정유사 K-Petroleum 페르소나 · 100% open data"

**평가 anchor**: A1 Business + Track 1 Social Impact 정합

---

### Scene 2: Discovery 화면 → Pattern Score + 6년 long chart (0:30-1:30)

**화면**: Discovery 페이지 위에서 아래로 천천히 scroll

**0:30-0:45 — Pattern Score Card**:
> "**오늘 위기 신호 점수 100점.** 위험방어 강세. AI는 장기계약 비중을 60%에서 75%로 4주간 올리라고 추천합니다."

**0:45-1:00 — Sidebar 4 tool 강조 (커서로 hover)**:
> "Databricks Apps에서 동작하고, Lakebase가 Mission CRUD를 담당, Genie가 자연어 SQL을, Agent Bricks Supervisor가 3 sub-agent를 자동 라우팅합니다. 네 가지 핵심 도구 모두 production 통합."

**1:00-1:30 — 6년 long chart**:
> "이건 6년 평시 가치 차트. 호르무즈 봉우리 3개가 보입니다. **하지만 매주 작은 봉우리들** — OPEC 회의, EIA 재고, 허리케인 — 이게 바로 일상 도구로서의 가치입니다. 위기 때만 쓰는 게 아니라 매일."

**평가 anchor**: A4 (4 tool 매핑) + A5 (6년 평시 가치 narrative)

---

### Scene 3: Bidirectional Mission — 차별화 핵심 (1:30-2:30)

**화면**: Discovery 하단 → "/missions" 페이지 클릭

**1:30-2:00 — 2 mission 동시 노출**:
> "여기가 우리의 차별화 — **양방향 Mission**. 위에는 호르무즈 위기 누적 시그널로 **위험방어 (Term 60→75%, +410억원 절감 시나리오)**. 아래는 **동시에** 약세 신호도 누적 — 중국 PMI 49.2, OECD 재고 증가, 사우디 OSP 인하 — **기회포착 (Spot 40→55%, +280억원)**.
>
> 표준 BI 대시보드는 위기든 기회든 한 방향만 봅니다. Crude Compass는 두 mission을 **동시에** 운영합니다."

**2:00-2:30 — Mission Detail 클릭**:
> "Mission detail. Brent 시나리오 3가지: 봉쇄 +410억, 긴장 +140억, 평화 -50억. 의사결정은 사람이 하고 AI는 근거를 정리합니다. **승인** 또는 **거절** 또는 시장 변하면 **방향 전환**."

**평가 anchor**: A2 Creativity (Bidirectional unique pattern) + A3 UX (한글 라벨 + 시나리오 명확)

---

### Scene 4: 🌟 Wow Factor — Slack ↔ Apps 5초 sync live (2:30-3:30)

**화면**: 화면 split — 왼쪽 Apps Mission detail, 오른쪽 Slack 채널

**2:30-3:00 — Slack click**:
> "여기서 가장 wow한 부분. Slack에서 매니저가 '승인' 버튼을 누르면..."

(Slack에서 [승인] 버튼 click)

**3:00-3:15 — 5초 대기 (실시간 시연)**:
> "5초 안에..."

**3:15-3:30 — Apps 자동 update**:
> "...Apps 화면이 자동으로 'PROPOSED' → 'ACTIVE'로 update됩니다. 양방향 동기화. WebSocket + Lakebase Single Source of Truth."

**평가 anchor**: A2 Creativity (Reactive trigger) + A4 Technical (WebSocket + Lakebase)

> **녹화 팁**: 이 scene이 모든 wow factor의 90%. **반드시 라이브로**. 사전 녹화 시 평가위원이 catch 가능.

---

### Scene 5: Multi-Agent + Time Travel + 4 tool 매핑 정리 (3:30-5:00)

**3:30-4:00 — WhatIf Supervisor widget**:
> "AI 어시스턴트 — Agent Bricks Multi-Agent Supervisor. 자연어 질문 하나 던지면..."
>
> "오늘 OPEC 5월 사우디 감산 근거는?"
>
> (응답 대기 ~10-15초)
>
> "...Supervisor가 Knowledge Assistant sub-agent에 자동 delegate. OPEC MOMR PDF 직접 인용. 응답 하단에 **사용된 sub-agent** transparency 라벨."

**4:00-4:30 — Time Travel slider**:
> "What-if 페이지 — 2019-2026 사이 300개 시점. 슬라이더 움직여서 과거 임의 시점 선택하면 **그 날 시그널만 보고** AI가 추천한 결정과 실제 30일/90일 후 가격 비교. 적중률 75%, 평균 비용 절감 +0.626%."

**4:30-5:00 — Architecture diagram (정리)**:
> "정리하면 Databricks 4 tool 1:1 매핑:
> - **Apps** — 본 페이지 (Vite + FastAPI 단일 컨테이너, Git source 자동 build)
> - **Lakebase** — Mission CRUD + Backtest OLTP + Slack/Apps Single Source of Truth
> - **Genie** — Crude Oil Market Analysis Space (gold view 10 tables certified)
> - **Agent Bricks** — Supervisor (Multi-Agent) + Knowledge Assistant (OPEC MOMR RAG) + Mission Plan (Foundation Model API)
>
> + Document Intelligence (ai_parse_document) + Lakeflow Jobs (8 cron) + Foundation Model API (Claude Haiku 4.5).
>
> 5,000만 국민 에너지 안보 — 5인 팀도 대기업처럼. Crude Compass."

**평가 anchor**: A4 (4 tool 매핑 명시) + A2 (Multi-Agent transparency) + A1 (closing narrative)

---

## 녹화 체크리스트

### 사전 작업 (녹화 전)
- [ ] **형욱님 workspace tasks 1+2번 완료** (Lakebase + Supervisor live) — 안 끝나면 Scene 4 + 5 fail
- [ ] Production URL 1회 사전 warmup (cold start 회피)
- [ ] Slack 사전 인터랙티비티 setup 확인 (Confirm button)
- [ ] 녹화 도구: OBS Studio 또는 Loom, 1080p 60fps
- [ ] 마이크 quality check (배경 소음)

### 녹화 중
- [ ] 0:00-0:30 Hook 발음 명료 (5,000만 국민 강조)
- [ ] 0:15 K-Petroleum 가상 disclosure 자막 표시
- [ ] 1:00 Sidebar 4 tool 영역 cursor hover로 강조
- [ ] 1:30 6년 chart "매주 작은 봉우리들" 부분 cursor로 가리키기
- [ ] 2:30-3:30 Slack click → Apps 5초 sync **반드시 라이브** (사전 녹화 catch)
- [ ] 4:30-5:00 Architecture diagram 자막 또는 image overlay

### 사후 작업
- [ ] 자막 한글 + 영문 핵심 명사 (HEDGE/OPP/Apps/Lakebase 등)
- [ ] BGM 없음 OR 매우 subtle (음성 중심)
- [ ] 5:00 정확히 끝남 (5:05+ 시 자동 cut 가능)
- [ ] 친구분 (LG Electronics) review — 시나리오 검수 + narrative tone

---

## 5분 시간 분배 검증

| Scene | 시간 | 누적 |
|---|---|---|
| 1. Hook | 30s | 0:30 |
| 2. Discovery + 6년 chart | 60s | 1:30 |
| 3. Bidirectional Mission | 60s | 2:30 |
| 4. Slack 5초 sync wow | 60s | 3:30 |
| 5. Multi-Agent + Time Travel + 정리 | 90s | 5:00 |
| **합계** | **300s** | ✅ |

---

## Risk + Mitigation

| Risk | Mitigation |
|---|---|
| Apps cold start (Scene 2 시작 시 로딩 지연) | 녹화 30초 전 사전 warmup navigate |
| Slack 5초 sync 실패 (Scene 4 fail) | 사전 5회 dress rehearsal, fallback: 사전 녹화 + "라이브 sync 시연" 자막 |
| Supervisor cold start 30초+ (Scene 5) | 녹화 전 supervisor 1회 warmup query |
| Lakebase fallback 상태에서 녹화 | **workspace task 1번 안 끝나면 절대 녹화 X** |

---

## 평가위원 emotional response 예측

**0:00-0:30** — "5,000만 국민" hook 강함, attention 잡힘 ✅
**1:30-2:30** — Bidirectional 차별화 즉시 catch ("이거 처음 봐") ✅
**3:00-3:15** — Slack click → 5초 sync live = **wow moment** ⭐
**4:30-5:00** — 4 tool 매핑 명확 → 평가표 5축 즉시 채점 가능 ✅

**최종 인상**: "실제 회사에서 쓸 수 있겠다" + "기술 깊이 진짜" + "honesty (K-Petroleum 가상 disclosure)"
