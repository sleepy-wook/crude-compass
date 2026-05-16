"""Agent Bricks Supervisor Agent client.

시나리오 §9.7 Multi-Agent Orchestration — single endpoint에 자연어 query 전달 시
Supervisor가 4 sub-agent (Genie + Knowledge Assistant + Information Extraction + Mission Plan FMA)에
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
from dataclasses import dataclass, field
from typing import Any, Literal

from app.core.config import get_settings

logger = logging.getLogger(__name__)

SUPERVISOR_TIMEOUT_SEC = 60.0  # cold start + multi-agent orchestration


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
    """Databricks OpenAI client → Supervisor endpoint (chat completions + return_trace).

    OpenAI compatible — `client.chat.completions.create` 패턴.
    `databricks_options.return_trace=true`로 sub-agent tool_calls trace 받음.
    """
    from databricks.sdk import WorkspaceClient

    profile = os.getenv("DATABRICKS_CONFIG_PROFILE", "crude-compass")
    try:
        w = WorkspaceClient(profile=profile)
    except Exception:
        w = WorkspaceClient()

    client = w.serving_endpoints.get_open_ai_client()
    resp = client.chat.completions.create(
        model=endpoint_name,
        messages=[{"role": "user", "content": question}],
        extra_body={"databricks_options": {"return_trace": True}},
    )

    # message content
    answer = ""
    if resp.choices and resp.choices[0].message:
        answer = resp.choices[0].message.content or ""

    # trace 파싱 — databricks_output.trace 또는 choices[0].message.tool_calls 시도
    tools_used: list[SubAgentCall] = []
    raw_trace: list[dict[str, Any]] | None = None

    try:
        # 1) Databricks 확장 schema (databricks_output / trace)
        databricks_output = getattr(resp, "databricks_output", None)
        if databricks_output:
            trace = getattr(databricks_output, "trace", None) or databricks_output.get("trace") if isinstance(databricks_output, dict) else None
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

    # 2) Fallback — tool_calls in message (legacy OpenAI schema)
    if not tools_used:
        try:
            if resp.choices and resp.choices[0].message:
                tool_calls = getattr(resp.choices[0].message, "tool_calls", None)
                if tool_calls:
                    for tc in tool_calls:
                        fn = getattr(tc, "function", None)
                        if fn:
                            tools_used.append(SubAgentCall(
                                name=str(getattr(fn, "name", "?")),
                                arguments=str(getattr(fn, "arguments", ""))[:200] or None,
                            ))
        except Exception as e:
            logger.warning("supervisor trace parse partial fail (tool_calls): %s", e)

    return SupervisorResponse(
        answer=answer or "(Supervisor 응답 비어있음)",
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
