---
description: Evaluator subagent 호출 — 최근 변경분을 5축 hackathon 점수로 평가, REVISE/PASS 판정
argument-hint: "[optional: 특정 평가 초점]"
---

**evaluator subagent**를 명시 호출해서 최근 작업을 hackathon judge 관점에서 검토하세요.

평가 초점: $ARGUMENTS (없으면 최근 commit 또는 unstaged changes)

## Evaluator 호출

`Task` tool with `subagent_type: "evaluator"` 사용.

Evaluator에 전달할 input:
- "최근 작업을 평가해줘"
- 추가 컨텍스트가 있다면 (e.g., "Slack Bolt 통합 직후 평가")

## Evaluator output 받은 후

1. 5축 점수 + average 표 형태로 보여줘
2. **verdict** 강조 (PASS or REVISE)
3. **scenario_drift** 항목 우선 처리 — blocker severity는 즉시 fix 권장
4. **critical_issues** 파일:라인 그대로 노출
5. **recommended_next_actions** P0/P1/P2 분류

## 후속

- **PASS (avg ≥ 80, no blocker)** → commit + push 진행
- **REVISE** → critical_issues 중 P0부터 차례로 수정 → 다시 `/evaluate` 호출 (loop)
- **3회 연속 REVISE** → 사용자에게 scope cut 또는 narrative pivot 협의

## Anti-pattern

- evaluator가 낮은 점수 줬다고 "그래도 PoC라" 같은 변명 금지
- 점수 inflate 위해 evaluator 다시 부르기 (같은 코드인데) 금지
- 점수 표시 안 하고 넘어가기 금지 — 항상 5축 점수 보여줘야 함
