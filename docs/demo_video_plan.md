# Crude Compass — 제출 영상 제작 계획

> Databricks Building Intelligent Apps Hackathon 2026 (with AWS) · 한국어 트랙 · Track 1 Social Impact
> 제출 마감 2026-05-22 · 심사 5/25~29 · 발표 6/15
> 제품 ground truth: [crude_compass_final_scenario.md](crude_compass_final_scenario.md)

---

## 1. 제출물 = 5분 이내 영상 1개 (필수 포함)

1. **팀 소개 및 문제 정의**
2. **솔루션 아키텍처 설명**
3. **프로젝트 사양(Lakebase / Genie / Apps / Agent Bricks / 대시보드 등) 포함 작동하는 솔루션 시연**

(공식 요건: 위 3개를 5분 안에. 데이터셋 출처도 언급.)

## 2. 심사 기준 (각 20%, 5축)

- **Business Applicability** — 실문제 관련성·임팩트
- **Creativity & Innovation** — BI/분석 그 이상
- **User Experience & Insights** — 직관적 설계 → 행동 유발
- **Technical Capability** — Databricks 통합·아키텍처
- **Data Storytelling & Narrative** — 가치 전달력 (내레이션 비중 큼)

## 3. 영상 구조 (하이브리드, 5분 하드캡)

| 블록 | 방식 | 분량 |
|------|------|------|
| 인트로(팀) + 문제 정의 + 솔루션 아키텍처 | **hyperframes HTML 영상** | ~2분 |
| 작동 솔루션 시연 (앱 + Slack 양방향) | **실제 화면 녹화** | ~2.5~3분 |

## 4. hyperframes (HeyGen 오픈소스, HTML→MP4)

- `npx hyperframes` : init / preview / render / lint + **transcribe(Whisper)**
- 요구사항: **Node ≥22 + FFmpeg**
- HTML 씬 + 실제 영상 클립 혼합 지원
- 합치기: 앞 HTML 렌더 → 데모 mp4와 **ffmpeg concat** (옵션 A)

### 한 번 녹음 방식
- 통으로 화면+음성 한 take
- 앞부분: 화면 무관(HTML로 덮음), 음성만 중요 / 뒷부분: 화면+음성 그대로
- **전환 멘트 + 1초 정적**으로 컷 지점 표시 (whisper JSON에서 그 지점 잘라 concat)

### 워크플로우 + 분담
| # | 단계 | 담당 |
|---|------|------|
| 1 | 5분 대본 (5블록 + 전환멘트 + 컷지점 + 컷별 시간) | 나 |
| 2 | 데모 리포트 생성 | 나 (완료) |
| 3 | 한 take 녹음/녹화 | 형욱 |
| 4 | `npx hyperframes transcribe` → 단어별 JSON | 형욱 |
| 5 | JSON 타이밍 기반 앞부분 HTML 씬 작성 + 조립 | 나 |
| 6 | `npx hyperframes render` → 데모와 concat → 최종 MP4 | 형욱 |

순서 의존: 1 → 3 → 4 → 5.

## 5. 앞부분 honesty 서사 (Track 1 정조준)

- **100% 공개 데이터 by design** — Bloomberg 못 사는 곳도 재현 가능 = Social Impact
- Platts 실시간 Dubai → **KNOC OPINET 공식 일별** (한국 정유사 실제 기준)
- Bloomberg/Reuters → **GDELT** (15분 갱신, 무료, 글로벌)
- "정유사는 사용자, 수혜자는 사회(소비자 물가)" — Track 분류 기준은 *데이터 출처*(공개)지 *수혜자*가 아님
- GDELT 노이즈 방어: importance≥80 임계 + tone/mention 가중 + 멀티시그널 교차검증(pattern_score)

## 6. 데모 상태 (녹화 준비 완료)

- **데이터(Lakebase)**: trigger 9건 (pending 3 / kept 3 / archived 2 / ai_dropped 1) + daily 2건 (5/21 prev, 5/22 Hero). 전부 실제 트리거 타임라인(5/15~5/21) 기반.
- **Slack**: 트리거 3건 인터랙티브 카드(default 채널) + 5/22 일일 카드(일일 채널 C0B55UA42J1).
- **Socket Mode 양방향**: Slack 활성화/기각 → 배포본 → Lakebase → 앱 반영 (Databricks Apps inbound 401을 outbound WS로 우회, 검증 완료).
- **시황**: 실시간 Dubai 차트 분리(OilPriceAPI Dubai 미갱신) → OPINET 일별로 노출.

### 녹화 직전 리셋 (테스트 클릭으로 pending 소비됐을 때)
```
python scripts/_seed_demo_reports.py        # 9 reports + daily 2 재시드
python scripts/_post_pending_to_slack.py    # 트리거 3 Slack 재전송
python scripts/_post_daily_to_slack.py      # 일일 카드 재전송
```
(scripts/_*.py 는 임시 데모 운영 스크립트 — git 미추적)

## 7. 5분 데모 동선 (녹화 화면부 참고)

1. **의사결정** — 5/22 일일 보고서 Hero + 받은편지함 pending 3. 1건 채택.
2. **Slack 양방향** — Slack 카드에서 활성화 클릭 → 앱 즉시 반영 (wow)
3. **조사** — Agent Bricks Supervisor 자연어 질의, sub-agent trace
4. **시황** — pattern score + 유가(OPINET Dubai) 차트
5. **자료실** — OPEC 월간 + 주요 보도(GDELT)
6. 마무리: "결정은 사람, 분석은 AI, 데이터는 100% 공개" — Track 1 메시지
