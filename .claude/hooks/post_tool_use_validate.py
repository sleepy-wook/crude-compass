#!/usr/bin/env python
"""PostToolUse hook: code quality + scenario drift validation.

Triggered after Edit/Write/MultiEdit. Reads JSON from stdin.

Behavior:
- .py 파일 변경 시 → `python -m py_compile` (syntax check)
- .ts/.tsx 파일 변경 시 → `pnpm exec tsc --noEmit <file>` (type check)
- API/scenario 파일 변경 시 → 정적 grep으로 drift 체크 (LLM 호출 X)
- 실패 시 stderr로 Claude에 피드백 + exit 2 (blocking)
- 성공 시 silent
"""
from __future__ import annotations
import json
import os
import re
import subprocess
import sys
from pathlib import Path


def main() -> int:
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0  # silent skip

    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input", {})

    # 대상: Write / Edit / MultiEdit
    if tool_name not in ("Write", "Edit", "MultiEdit"):
        return 0

    file_path = tool_input.get("file_path", "")
    if not file_path:
        return 0

    # 절대 경로
    p = Path(file_path)
    if not p.exists():
        return 0

    feedback: list[str] = []

    # 1. Python syntax check
    if p.suffix == ".py" and "/.venv/" not in str(p).replace("\\", "/"):
        try:
            r = subprocess.run(
                ["python", "-m", "py_compile", str(p)],
                capture_output=True, timeout=10,
                encoding="utf-8", errors="replace",
            )
            if r.returncode != 0:
                err = (r.stderr or "").strip()[:600]
                feedback.append(f"[Python syntax error in {p.name}]\n{err}")
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass

    # 2. TypeScript type-check (compile only, no build)
    if p.suffix in (".ts", ".tsx") and "node_modules" not in str(p).replace("\\", "/"):
        # tsconfig.json 가까운 거 사용
        frontend_dir = Path("C:/crude-compass/frontend")
        if frontend_dir.exists() and str(p).startswith(str(frontend_dir)):
            try:
                # tsc with project config (full type-check, slow but correct)
                # Run only on .tsx (components) — skip pure type files .ts to save time
                if p.suffix == ".tsx":
                    r = subprocess.run(
                        ["pnpm", "exec", "tsc", "--noEmit", "-p", "tsconfig.app.json"],
                        capture_output=True, timeout=30, cwd=str(frontend_dir),
                        encoding="utf-8", errors="replace",
                        shell=True,
                    )
                    if r.returncode != 0:
                        out = (r.stdout or "").strip()
                        # Filter TS5112 (informational about tsconfig)
                        relevant = [
                            line for line in out.split("\n")
                            if "error TS" in line and "TS5112" not in line
                        ]
                        if relevant:
                            feedback.append(
                                f"[TS type error in {p.name}]\n" + "\n".join(relevant[:10])
                            )
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                pass

    # 3. Scenario drift check (정적 grep, LLM X)
    # api/*.py 변경 시 → docs/api_contract.md에 endpoint 정의되어 있나
    p_str = str(p).replace("\\", "/")
    if "/backend/app/api/" in p_str:
        try:
            content = p.read_text(encoding="utf-8")
            # FastAPI route decorator 찾기 (@router.get/.post/.put/...)
            new_endpoints = re.findall(r'@router\.(get|post|put|patch|delete)\("([^"]+)"', content)
            api_contract = Path("C:/crude-compass/docs/api_contract.md")
            if api_contract.exists() and new_endpoints:
                contract = api_contract.read_text(encoding="utf-8")
                missing = []
                for method, path in new_endpoints:
                    # path를 contract에서 찾기 (params {id} 일치 허용)
                    pat = path.replace("{", r"\{").replace("}", r"\}")
                    if path not in contract and not re.search(pat, contract):
                        missing.append(f"{method.upper()} {path}")
                if missing:
                    feedback.append(
                        f"[Scenario drift] {p.name}에 새 endpoint 추가됐는데 docs/api_contract.md에 없음:\n"
                        + "\n".join(f"  - {m}" for m in missing[:5])
                        + "\n→ api_contract.md 업데이트하거나 의도된 변경이면 무시"
                    )
        except (UnicodeDecodeError, OSError):
            pass

    if feedback:
        # exit 2 = blocking, stderr → Claude
        sys.stderr.write("\n\n".join(feedback))
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
