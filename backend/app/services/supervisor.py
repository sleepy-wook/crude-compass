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
    # Markdown table 보호 — 정상 GFM table은 `|---|---|` separator line이 있음.
    # 있으면 pipe cleanup 전부 스킵 (LLM이 의도해서 만든 표). 없으면 SQL leak로 간주.
    has_md_table = bool(re.search(r"^\s*\|[\s\-:|]+\|\s*$", text, flags=re.MULTILINE))
    if not has_md_table:
        # Mid-line: 한 줄 안에 '||' (table header signal) 등장 시 거기서 end-of-line까지 제거.
        text = re.sub(r"\|\|[^\n]*", "", text)
        # Mid-line: 3개 이상 pipe-delimited 필드 → SQL row leak.
        text = re.sub(r"\|[^|\n]{0,80}\|[^|\n]{0,80}\|[^|\n]{0,80}(\|[^|\n]{0,80})*", "", text)
        # Line-based: 줄 시작이 '|' 인 line 전체 제거.
        text = re.sub(r"^[ \t]*\|[^\n]*\n?", "", text, flags=re.MULTILINE)
    # Markdown heading inline fix:
    # LLM이 종종 "문장.## heading" 처럼 토큰을 붙여 emit (특히 streaming).
    # ATX heading은 줄 시작에서만 인식되므로 parser가 plain text로 처리됨.
    text = re.sub(r"(?<=[^\n#])(#{1,6}\s)", r"\n\n\1", text)
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


# ════════════════════════════════════════════════════════════════════════
# Streaming — Responses API stream=True (2026-05-21)
# ════════════════════════════════════════════════════════════════════════
def _stream_call_supervisor(endpoint_name: str, question: str):
    """Synchronous generator yielding incremental events from Supervisor.

    Yields dicts:
      {"type": "delta", "text": "..."}          답변 토큰 append
      {"type": "tool_call", "name": "genie-..."}  sub-agent 호출됨
      {"type": "done", "tools_used": [...]}     완료 (전체 trace 합산)
      {"type": "error", "message": "..."}       실패

    Responses API event 종류 (참조):
      response.created
      response.output_item.added (item.type == 'function_call' → tool start)
      response.output_text.delta (delta text)
      response.completed
    """
    from databricks.sdk import WorkspaceClient

    profile = os.getenv("DATABRICKS_CONFIG_PROFILE", "crude-compass")
    try:
        w = WorkspaceClient(profile=profile)
    except Exception:
        w = WorkspaceClient()

    client = w.serving_endpoints.get_open_ai_client()
    tools_used: list[SubAgentCall] = []
    accumulated_text = ""

    try:
        stream = client.responses.create(
            model=endpoint_name,
            input=[{"role": "user", "content": question}],
            extra_body={"databricks_options": {"return_trace": True}},
            stream=True,
        )
        seen_tool_names: set[str] = set()
        # Agent Bricks Multi-Agent Supervisor는 한 응답에 여러 message item을 emit함
        # (예: "조회하겠습니다" → tool call → "## 결과..." 두 번째 message).
        # text.delta는 같은 stream에 평탄하게 와서 boundary가 사라짐.
        # 직전 event가 text.delta가 아니었으면 = step 사이 → 다음 첫 delta 앞에 \n\n 삽입.
        last_was_text_delta = False
        for event in stream:
            etype = getattr(event, "type", None) or ""
            # Debug: log all event types — Databricks Responses stream API 정확한 schema 확인용
            logger.debug("supervisor stream event: %s", etype)

            # 1. text delta
            if etype == "response.output_text.delta":
                delta_text = getattr(event, "delta", "") or ""
                if delta_text:
                    # step boundary 직후 첫 delta — 새 message 시작이므로 separator 삽입
                    if not last_was_text_delta and accumulated_text and not accumulated_text.endswith("\n\n"):
                        sep = "\n" if accumulated_text.endswith("\n") else "\n\n"
                        accumulated_text += sep
                        yield {"type": "delta", "text": sep}
                    accumulated_text += delta_text
                    yield {"type": "delta", "text": delta_text}
                    last_was_text_delta = True
                continue

            # 2. completion
            if etype == "response.completed":
                last_was_text_delta = False
                # response 객체에 trace가 들어있을 수 있음 — 최종 확인
                resp_obj = getattr(event, "response", None)
                if resp_obj:
                    out_items = getattr(resp_obj, "output", None) or []
                    for it in out_items:
                        it_type = getattr(it, "type", None)
                        if it_type in ("function_call", "tool_call", "tool_use"):
                            tname = getattr(it, "name", None) or getattr(it, "tool_name", None)
                            if tname and str(tname) not in seen_tool_names:
                                seen_tool_names.add(str(tname))
                                tools_used.append(SubAgentCall(
                                    name=str(tname),
                                    arguments=str(getattr(it, "arguments", ""))[:200] or None,
                                ))
                                yield {"type": "tool_call", "name": str(tname)}
                cleaned = _clean_answer(accumulated_text) if accumulated_text else ""
                yield {
                    "type": "done",
                    "answer": cleaned,
                    "tools_used": [
                        {"name": t.name, "arguments": t.arguments, "result_preview": t.result_preview}
                        for t in tools_used
                    ],
                }
                return

            # 3. tool call broad detection (response.output_item.added/done 등)
            # message boundary signal — 직전 stream을 종료시키고 separator 다음에 다시 시작.
            last_was_text_delta = False
            if "tool" in etype.lower() or "function_call" in etype.lower() or "output_item" in etype:
                name = getattr(event, "name", None) or getattr(event, "tool_name", None)
                item = getattr(event, "item", None)
                if item and not name:
                    name = getattr(item, "name", None) or getattr(item, "tool_name", None)
                if name and str(name) not in seen_tool_names:
                    seen_tool_names.add(str(name))
                    args_val = getattr(event, "arguments", None) or (getattr(item, "arguments", None) if item else None)
                    tools_used.append(SubAgentCall(
                        name=str(name),
                        arguments=str(args_val)[:200] if args_val else None,
                    ))
                    yield {"type": "tool_call", "name": str(name)}

        # 스트림이 'completed' 없이 끝났을 때 fallback
        cleaned = _clean_answer(accumulated_text) if accumulated_text else ""
        yield {
            "type": "done",
            "answer": cleaned or "(응답 비어있음)",
            "tools_used": [
                {"name": t.name, "arguments": t.arguments, "result_preview": t.result_preview}
                for t in tools_used
            ],
        }
    except Exception as e:
        import traceback
        logger.warning("supervisor stream failed: %s\n%s", e, traceback.format_exc())
        yield {"type": "error", "message": f"{type(e).__name__}: {e}"}
