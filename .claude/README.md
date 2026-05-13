# Crude Compass — Claude Code Harness

**Anthropic Evaluator-Optimizer 패턴**을 Claude Code subagents + hooks로 구현. Sprint 4-5 개발 가속화 + 품질 관리.

## 핵심 패턴 — Planner → Generator ↔ Evaluator

```
User request
  ↓
[/plan <task>] → planner subagent → structured plan (success criteria + scenario anchor + risks)
  ↓
Main Claude (= Generator) → 코드 작성
  ↓
[/evaluate] → evaluator subagent → 5축 hackathon 점수 + 구체적 issue
  ↓
점수 < 80 또는 blocker drift → REVISE → Main이 수정 → 다시 /evaluate
점수 ≥ 80 + no blocker → PASS → commit + push
```

Anthropic 공식 [Building Effective Agents - Evaluator-Optimizer](https://anthropic.com/research/building-effective-agents) 패턴 그대로.

## Subagent vs Hooks 역할 분리

| 도구 | 역할 | 비용 | 자동/수동 |
|---|---|---|---|
| **Planner subagent** | 의미 단위 plan (semantic) | Sonnet $0.02/call | 명시 호출 (`/plan`) |
| **Evaluator subagent** | 의미 단위 grade (semantic, 5축) | Sonnet $0.03/call | 명시 호출 (`/evaluate`) |
| **PostToolUse hook** | 정적 quality check (syntax, type, drift) | $0 | 자동 |
| **PreToolUse hook** | Safety guard (rm -rf 등) | $0 | 자동 |
| **UserPromptSubmit hook** | git/todo context inject | $0 | 자동 |
| **`/critique`** | 일반 self-review | Haiku $0.01/call | 명시 호출 |

**핵심**: subagent = 의미적 검토 (의도 일치, 점수), hook = 정적 보호 (syntax, lint, drift). 보완 관계.

## 디렉토리 구조

```
.claude/
├── settings.local.json          # 자동 hooks 등록
├── agents/
│   ├── planner.md               # 작업 plan subagent (sonnet)
│   └── evaluator.md             # hackathon judge subagent (sonnet)
├── commands/
│   ├── plan.md                  # /plan <task> — planner 호출
│   ├── evaluate.md              # /evaluate — evaluator 호출
│   └── critique.md              # /critique — 일반 self-review
├── hooks/
│   ├── pre_tool_use_safety.py
│   ├── post_tool_use_validate.py
│   └── user_prompt_context.py
└── README.md
```

## 표준 workflow (Sprint 4 모든 task에 적용)

### 1. 작업 시작 — `/plan <task>`
```
사용자: /plan "Slack Bolt 통합 — webhook + Confirm action handler"
↓
planner subagent 호출 → JSON plan 반환
↓
Main이 한국어 요약 + 사용자 confirm
```

### 2. 구현 — Main Claude가 plan 따라 코드 작성
- 자동 hook이 syntax/type/drift check
- 위험 명령은 자동 차단

### 3. 평가 — `/evaluate`
```
사용자: /evaluate
↓
evaluator subagent 호출 → 5축 점수 + verdict
```

### 4. PASS/REVISE 분기
- **PASS (≥80 avg, no blocker)**: commit + push
- **REVISE**: critical_issues P0부터 수정 → 다시 `/evaluate`
- **3회 REVISE**: 사용자와 scope cut/pivot 협의

## 5축 평가 기준 (evaluator subagent rubric)

| 축 | 무엇 |
|---|---|
| **Innovation** | Pattern Score + bidirectional + confidence calibration 독창성 |
| **Technical** | 실제 작동 (compile ≠ runs), 통합, error handling, 테스트 |
| **Databricks features** | Foundation Model API / Document Intelligence / UC / Lakebase / Agent Bricks / AI/BI / Lakeflow |
| **Social Impact (Track 1)** | Open data democratization, 계량 ROI, 적용 가능성 |
| **Demo quality** | Live demo 작동, 시각 polish, storytelling, fallback 준비 |

## 자동화된 정적 hook 동작

### PreToolUse — Bash safety
- 차단 패턴: `rm -rf`, force push main, DROP TABLE, .env dump, TOKEN 노출
- exit 2 + stderr → Claude

### PostToolUse — Quality + Drift
- `.py` 저장 → `python -m py_compile`
- `.tsx` 저장 → `tsc --noEmit -p tsconfig.app.json`
- `backend/app/api/*.py` → `docs/api_contract.md` endpoint 일치 grep

### UserPromptSubmit — Context
- 매 prompt에 git log + status + todo.md sprint section 자동 inject

## 운영 원칙

1. **모든 non-trivial 작업은 `/plan` 먼저** (5분이라도)
2. **commit 전에 `/evaluate`** 필수
3. **점수 inflate 금지** — 평가위원 시뮬레이션이 핵심
4. **REVISE는 fail이 아니라 정상** — Anthropic cookbook도 평균 2-3 iteration
5. **scope cut 정직**: scenario drift blocker 발견 시 narrative pivot 또는 cut

## 참고

- [Anthropic — Building Effective Agents](https://anthropic.com/research/building-effective-agents)
- [Anthropic Cookbook — Evaluator-Optimizer](https://github.com/anthropics/anthropic-cookbook/blob/main/patterns/agents/evaluator_optimizer.ipynb)
- [Claude Code — Subagents](https://code.claude.com/docs/en/sub-agents)
- [Claude Code — Hooks](https://code.claude.com/docs/en/hooks)
