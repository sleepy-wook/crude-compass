"""Agent Bricks Supervisor Agent client.

시나리오 §9.8 Multi-Agent Orchestration — single endpoint에 자연어 query 전달 시
Supervisor가 3 sub-agent (Genie + Knowledge Assistant + Mission Plan FMA)에
자동 delegate. OpenAI chat completions 호환 + `databricks_options.return_trace=true`로
어떤 sub-agent가 사용됐는지 frontend 노출.

설정:
- SUPERVISOR_ENDPOINT_NAME env (예: 'crude-compass-supervisor') 미설정 시 graceful raise
- DATABRICKS_CONFIG_PROFILE은 mission_plan.py와 동일 (local dev 시 'crude-compass')

Apps deploy 시: workspace OAuth auto-injection이라 profile 무관.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Literal

from app.core.config import get_settings


def _clean_answer(text: str) -> str:
    """Sub-agent tool output이 LLM answer에 그대로 echo된 raw markup 제거.

    매니저가 보는 자연어 답만 남기고:
    - <name>...</name> sub-agent identifier
    - leaked markdown table header / separator / data rows
    - excess newlines
    """
    if not text:
        return text
    # <name>genie-xxxx</name>, <name>crude-compass-supervisor</name>
    text = re.sub(r"<name>[^<]*</name>", "", text)
    # leaked SQL/table data row patterns ("|0|17|None|None|None|None|")
    text = re.sub(r"\|+(?:\d+(?:\.\d+)?|None|null)(?:\|(?:\d+(?:\.\d+)?|None|null))+\|+", "", text)
    # leaked table header row ("||n_cases|avg_dubai_price_change_30d|...|")
    text = re.sub(r"\|+[a-zA-Z_][\w_]*(?:\|[a-zA-Z_][\w_]*)+\|+", "", text)
    # leaked table separator ("|-|-|-|-|-|")
    text = re.sub(r"\|+(?:-+\|)+", "", text)
    # collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

logger = logging.getLogger(__name__)

SUPERVISOR_TIMEOUT_SEC = 180.0  # cold start (30-60s) + 3 sub-agent fan-out + LLM synthesis


class SupervisorNotConfigured(RuntimeError):
    """SUPERVISOR_ENDPOINT_NAME 미설정."""


SupervisorSource = Literal["live", "fallback"]


@dataclass
class SubAgentCall:
    """sub-agent 1회 호출 trace."""
    name: str
    arguments: str | None = None
    result_preview: str | None = None


@dataclass
class SupervisorResponse:
    answer: str
    source: SupervisorSource = "live"
    tools_used: list[SubAgentCall] = field(default_factory=list)
    raw_trace: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "source": self.source,
            "tools_used": [
                {"name": t.name, "arguments": t.arguments, "result_preview": t.result_preview}
                for t in self.tools_used
            ],
        }


def _sync_call_supervisor(endpoint_name: str, question: str) -> SupervisorResponse:
    """Databricks OpenAI client → Supervisor endpoint (Responses API + return_trace).

    Agent Bricks Multi-Agent Supervisor는 **Responses API** 사용 (chat.completions X).
    Apps logs (D-1 00:22 KST) 확인: "'messages' field is not supported. Please use 'input' field instead."

    - `client.responses.create(model, input=[{role, content}], ...)` 패턴
    - `databricks_options.return_trace=True`로 sub-agent routing trace 받음 (best-effort)
    """
    from databricks.sdk import WorkspaceClient

    profile = os.getenv("DATABRICKS_CONFIG_PROFILE", "crude-compass")
    try:
        w = WorkspaceClient(profile=profile)
    except Exception:
        w = WorkspaceClient()

    client = w.serving_endpoints.get_open_ai_client()
    resp = client.responses.create(
        model=endpoint_name,
        input=[{"role": "user", "content": question}],
        extra_body={"databricks_options": {"return_trace": True}},
    )

    # answer: Responses API는 output_text shortcut 제공
    answer = ""
    try:
        answer = getattr(resp, "output_text", "") or ""
    except Exception:
        pass

    # output_text 없으면 output items 순회
    if not answer:
        try:
            output = getattr(resp, "output", None) or []
            text_parts: list[str] = []
            for item in output:
                item_type = getattr(item, "type", None)
                if item_type == "message":
                    for content in getattr(item, "content", []) or []:
                        c_type = getattr(content, "type", None)
                        if c_type in ("output_text", "text"):
                            text_parts.append(getattr(content, "text", "") or "")
            answer = "\n".join(p for p in text_parts if p)
        except Exception as e:
            logger.warning("supervisor output parse partial fail: %s", e)

    # trace 파싱 — Responses API output items 또는 databricks_output.trace
    tools_used: list[SubAgentCall] = []
    raw_trace: list[dict[str, Any]] | None = None

    # 1) Responses API output items에서 function_call / tool_use 추출
    try:
        output = getattr(resp, "output", None) or []
        for item in output:
            item_type = getattr(item, "type", None)
            if item_type in ("function_call", "tool_call", "tool_use"):
                name = getattr(item, "name", None) or getattr(item, "tool_name", None)
                if name:
                    tools_used.append(SubAgentCall(
                        name=str(name),
                        arguments=str(getattr(item, "arguments", ""))[:200] or None,
                    ))
    except Exception as e:
        logger.warning("supervisor responses output parse partial fail: %s", e)

    # 2) Databricks 확장 schema (databricks_output / trace) — fallback
    if not tools_used:
        try:
            databricks_output = getattr(resp, "databricks_output", None)
            if databricks_output:
                trace = None
                if isinstance(databricks_output, dict):
                    trace = databricks_output.get("trace")
                else:
                    trace = getattr(databricks_output, "trace", None)
                if trace:
                    raw_trace = trace if isinstance(trace, list) else [trace]
                    for step in raw_trace:
                        if isinstance(step, dict):
                            name = step.get("tool_name") or step.get("name") or step.get("subagent")
                            if name:
                                tools_used.append(SubAgentCall(
                                    name=str(name),
                                    arguments=str(step.get("arguments", ""))[:200] or None,
                                    result_preview=str(step.get("result", ""))[:200] or None,
                                ))
        except Exception as e:
            logger.warning("supervisor trace parse partial fail (databricks_output): %s", e)

    cleaned = _clean_answer(answer) if answer else ""
    return SupervisorResponse(
        answer=cleaned or "(Supervisor 응답 비어있음)",
        source="live",
        tools_used=tools_used,
        raw_trace=raw_trace,
    )


async def query_supervisor(question: str) -> SupervisorResponse:
    """Async wrapper. settings.supervisor_enabled False면 raise SupervisorNotConfigured."""
    settings = get_settings()
    if not settings.supervisor_enabled:
        raise SupervisorNotConfigured("SUPERVISOR_ENDPOINT_NAME not set")

    try:
        return await asyncio.wait_for(
            asyncio.to_thread(
                _sync_call_supervisor, settings.supervisor_endpoint_name, question
            ),
            timeout=SUPERVISOR_TIMEOUT_SEC,
        )
    except asyncio.TimeoutError:
        logger.warning("supervisor timeout after %ss", SUPERVISOR_TIMEOUT_SEC)
        raise
    except Exception as e:
        logger.warning("supervisor call failed: %s", e)
        raise
