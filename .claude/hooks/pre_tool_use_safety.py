#!/usr/bin/env python
"""PreToolUse hook: dangerous bash command guard.

차단 패턴:
- rm -rf <broad path>
- git push --force (main/master)
- DROP TABLE / TRUNCATE
- credential 파일 commit / 노출

exit 2 + stderr → Claude. User explicit override 가능.
"""
from __future__ import annotations
import json
import re
import sys


# 패턴 트리거 조건: 명령 시작 또는 ; && || | 뒤 — quoted string 안 false positive 회피
_CMD_BOUNDARY = r"(?:^|[;&|]\s*)"

DANGER_PATTERNS = [
    (_CMD_BOUNDARY + r"rm\s+-rf\s+(?:/(?!tmp/|var/tmp/)|~|\$HOME)",
     "rm -rf system path risk"),
    (r"git\s+push\s+--force(?:-with-lease)?\s+.*\s+(main|master)\b",
     "main/master force push risk"),
    (r"\bDROP\s+TABLE\b(?!.*(temp|tmp_))",
     "DROP TABLE risk — use TRUNCATE or specific WHERE"),
    (r"\bTRUNCATE\s+TABLE\b",
     "TRUNCATE risk — confirm intent"),
    (r"\bDELETE\s+FROM\s+\w+\s*;",
     "DELETE without WHERE clause risk"),
    (_CMD_BOUNDARY + r"cat\s+[^|>]*\.env(?:\.local|\.production)?\b",
     ".env file dump — credential exposure"),
    (r"DATABRICKS_TOKEN\s*=\s*['\"]?[a-zA-Z0-9]{20,}",
     "DATABRICKS_TOKEN plaintext exposure"),
]


def main() -> int:
    # Windows cp949 회피
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input", {})

    if tool_name != "Bash":
        return 0

    command = tool_input.get("command", "")
    if not command:
        return 0

    hits = []
    for pat, msg in DANGER_PATTERNS:
        if re.search(pat, command, flags=re.IGNORECASE):
            hits.append(msg)

    if hits:
        sys.stderr.write(
            "[WARNING: dangerous command detected]\n"
            + "\n".join(f"  - {h}" for h in hits)
            + f"\n\ncommand: {command[:200]}\n"
            + "\nIf truly intended, ask user explicit confirm. Demo safety."
        )
        # exit 2 = blocking (Claude receives stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
