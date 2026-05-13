---
description: 현재 진행 중인 작업 self-critique (Constitutional AI 패턴 on-demand)
---

지금까지 한 작업을 **다른 관점에서 비판적으로 검토**해주세요.

## 체크 항목

1. **시나리오 일관성**
   - `docs/crude_compass_final_scenario.md` 약속 (양방향 architecture, 7 source, 5초 sync 등)과 현재 코드가 일치하는가?
   - `docs/api_contract.md`에 정의된 endpoint signature와 실제 구현이 일치하는가?
   - 시나리오 narrative와 backtest 실측 (HEDGE 75% hit) 사이 모순 없나?

2. **숨겨진 가정 / 누락**
   - 내가 묵시적으로 가정한 것 중 사용자가 다르게 생각할 수 있는 부분?
   - "이건 안 해도 돼"라고 넘긴 부분이 실제 데모에서 필요한 거 아닌가?
   - Edge case (LLM 실패, Lakebase 연결 끊김, Slack timeout) 처리 누락?

3. **데모 영향**
   - 5/22 (또는 5/18 조기 제출) 데모에서 평가위원이 볼 것 중, 현재 못 보이는 게 있나?
   - "보여주는 화면"이 narrative보다 약하면 어디?
   - Live demo 시 실패할 수 있는 risk 어디?

4. **남은 일 우선순위**
   - 지금 진행 중 작업이 정말 최우선인가?
   - 더 ROI 높은 작업이 있나? (예: backend 완성 vs frontend 시작)
   - 시간 압박 (D-5) 고려할 때 cut 가능한 scope?

5. **사용자 push back 확률**
   - 지금까지 한 작업 중 사용자가 "이거 왜 이렇게 했어?" 물을 가능성 있는 부분?
   - 미리 답변 준비?

## Output 형식

각 항목별로:
- ✅ OK인 부분
- ⚠️ 의심스러운 부분 (구체적 근거)
- 🔴 fix 권장 (즉시 수정 / 다음 turn / Sprint 5)

마지막에 **3줄 요약**: 가장 critical 1-2개 + 즉시 action 권장사항.
