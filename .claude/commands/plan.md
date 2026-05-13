---
description: Planner subagent 호출 — 작업을 구조화된 계획으로 분해 (Generator 실행 전 필수)
argument-hint: "<task description>"
---

다음 작업에 대해 **planner subagent**를 명시 호출해서 구조화된 계획을 받아주세요:

**Task**: $ARGUMENTS

## Planner 호출 방식

`Task` tool with `subagent_type: "planner"` 사용.

Planner에 전달할 input:
- 위 task description 그대로
- 현재 sprint context (5/13 → 5/18 early submit, D-5)

## Planner output 받은 후

1. JSON plan을 한국어로 짧게 요약 (3-5 bullets)
2. **success_criteria** 명확히 보여줘
3. **scenario_anchor** 확인 — 시나리오와 일치하나?
4. 사용자에게 plan 확인 받고 → Generator (= 메인 Claude) 실행 시작

만약 planner가 `pushback` 필드를 채워서 반환하면 → 사용자에게 우선 confirm 받기.
