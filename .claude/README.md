# Crude Compass — Claude Code Harness

이 디렉토리는 **Anthropic harness 패턴 (Constitutional AI / generate-critique-refine / safety guard)**을 Claude Code hooks로 구현한 것. 모든 Sprint 4-5 개발에 사용.

## 디자인 원칙

| 패턴 | 우리 구현 | 이유 |
|---|---|---|
| Self-critique 자동 (Stop hook) | ❌ 채택 X | 무한루프 위험 (GitHub issues 입증) |
| Self-critique 명시 (slash) | ✅ `/critique` | on-demand, 안전 |
| Code quality validation | ✅ PostToolUse | 즉시 catch + Claude 피드백 |
| Scenario drift detection | ✅ PostToolUse | LLM 호출 X, 정적 grep, 비용 0 |
| Context injection | ✅ UserPromptSubmit | compact 후 컨텍스트 유지 |
| Safety guard | ✅ PreToolUse | 데모 직전 사고 방지 |
| Subagent auto-dispatch | ❌ 불가능 | Anthropic 설계상 미지원 (suggest only) |

## 구성

```
.claude/
├── settings.local.json    # hook 등록 (PreToolUse / PostToolUse / UserPromptSubmit)
├── hooks/
│   ├── pre_tool_use_safety.py     # Bash dangerous pattern 차단
│   ├── post_tool_use_validate.py  # Python syntax + TS type + scenario drift
│   └── user_prompt_context.py     # git log + todo.md 자동 inject
├── commands/
│   └── critique.md        # /critique slash command (on-demand self-review)
└── README.md
```

## Hook 동작

### PreToolUse — Safety Guard
Trigger: `Bash` 호출 직전
검사: `rm -rf`, force push, DROP TABLE, .env dump, DATABRICKS_TOKEN 노출
결과: 위험 시 exit 2 (차단) + stderr → Claude

### PostToolUse — Quality + Drift Check
Trigger: `Write` / `Edit` / `MultiEdit` 직후
검사:
- `.py` → `python -m py_compile` (syntax)
- `.ts/.tsx` → `tsc --noEmit` (type)
- `backend/app/api/*.py` → API endpoint가 `docs/api_contract.md`와 일치하는지

결과: 실패 시 stderr → Claude 즉시 fix

### UserPromptSubmit — Context Injection
Trigger: 매 user prompt 직전
주입:
- `git log --oneline -5`
- `git status --short`
- `docs/todo.md` Sprint 섹션 일부

결과: `additionalContext` JSON → Claude prompt에 prepend
**비용 0** (LLM 호출 없음, git CLI만)

### /critique Slash Command — On-Demand Self-Review
사용: `/critique` 입력
동작: 현재 작업을 5가지 axis로 self-review (시나리오 일관성 / 가정 / 데모 영향 / 우선순위 / push back 위험)
**자동 X, 사용자가 명시 호출만**. 무한루프 회피.

## 비용

| Hook | 비용/turn |
|---|---|
| PreToolUse | $0 (regex) |
| PostToolUse | $0 (py_compile / tsc 로컬) |
| UserPromptSubmit | $0 (git CLI) |
| /critique | ~$0.01 (사용자 호출 시만) |

**총 추가 비용**: ~$0/turn (자동) + ~$0.01 (on-demand 사용 시)

## 참고

- [Claude Code Hooks Reference](https://code.claude.com/docs/en/hooks)
- [disler/claude-code-hooks-mastery](https://github.com/disler/claude-code-hooks-mastery)
- [Anthropic Constitutional AI](https://arxiv.org/abs/2212.08073)
