#!/usr/bin/env python
"""UserPromptSubmit hook: inject recent commits + active todo + branch state.

Compact 후에도 컨텍스트 유지. LLM 호출 X (git CLI만).
"""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path


REPO = "C:/crude-compass"


def run(cmd: list[str], cwd: str = REPO) -> str:
    try:
        r = subprocess.run(
            cmd, capture_output=True, timeout=5, cwd=cwd, shell=False,
            encoding="utf-8", errors="replace",
        )
        return (r.stdout or "").strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    user_text = event.get("prompt", "") or event.get("text", "")
    if not user_text:
        return 0

    # 1) 최근 commit 5개
    log = run(["git", "log", "--oneline", "-5"])

    # 2) 활성 branch + status
    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    status = run(["git", "status", "--short"])

    # 3) todo (Sprint 4 plan from docs/todo.md, 활성 항목만 — 정적)
    todo_path = Path(REPO) / "docs" / "todo.md"
    sprint_section = ""
    if todo_path.exists():
        try:
            content = todo_path.read_text(encoding="utf-8")
            # "🟢 Sprint" 또는 "Sprint 4" 섹션 추출 (Active blocker 다음 ~50줄)
            idx = content.find("Sprint 4")
            if idx == -1:
                idx = content.find("Sprint 3")
            if idx != -1:
                sprint_section = content[idx:idx + 800].strip()
        except (UnicodeDecodeError, OSError):
            pass

    parts = ["[Auto context — git/todo 상태]"]
    if branch:
        parts.append(f"branch: {branch}")
    if log:
        parts.append(f"recent commits:\n{log}")
    if status:
        parts.append(f"uncommitted ({len(status.splitlines())} files):\n{status[:300]}")
    if sprint_section:
        parts.append(f"todo.md sprint section:\n{sprint_section[:600]}")

    if len(parts) > 1:
        # additionalContext: stdout JSON
        ctx = "\n\n".join(parts)
        print(json.dumps({"additionalContext": ctx}))

    return 0


if __name__ == "__main__":
    sys.exit(main())
