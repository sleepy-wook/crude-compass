"""Databricks Genie Space 자연어 질의 wrapper + canned fallback.

평가위원 "Genie 어떻게 썼나요?" 질문 시 live 시연 가능. 단 GENIE_SPACE_ID 미설정
또는 SDK 호출 실패 시 graceful degrade:
- fallback_data: Lakebase에서 실제 SQL 직접 호출하여 답변 (Apps + UC 조합 시연)
- fallback_text: SQL fail 또는 unknown keyword 시 hardcoded text
- fallback: 키워드 매칭 실패 (generic meta 답변)

Source enum 4종 (live / fallback_data / fallback_text / fallback) — UI에 항상 노출.
transparency가 의심을 신뢰로.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Literal

from app.core.config import get_settings

logger = logging.getLogger(__name__)

GENIE_TIMEOUT_SEC = 8.0  # cold start 대응


GenieSource = Literal["live", "fallback_data", "fallback_text", "fallback"]


class GenieNotConfigured(RuntimeError):
    """GENIE_SPACE_ID 미설정 — fallback으로 분기."""


@dataclass
class GenieResponse:
    answer: str
    sql: str | None = None
    data: list[dict[str, Any]] | None = None
    conversation_id: str | None = None
    message_id: str | None = None
    source: GenieSource = "fallback"

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "sql": self.sql,
            "data": self.data,
            "conversation_id": self.conversation_id,
            "message_id": self.message_id,
            "source": self.source,
        }


# ════════════════════════════════════════════════════════════════════════
# Live Genie Conversation API
# ════════════════════════════════════════════════════════════════════════
def _sync_call_genie(
    space_id: str, question: str, conversation_id: str | None
) -> GenieResponse:
    """Databricks SDK Genie 호출 — sync (asyncio.to_thread로 감쌀 것)."""
    from databricks.sdk import WorkspaceClient

    w = WorkspaceClient()
    if conversation_id is None:
        # 새 conversation 시작
        msg = w.genie.start_conversation_and_wait(
            space_id=space_id, content=question
        )
    else:
        # 기존 conversation 이어가기
        msg = w.genie.create_message_and_wait(
            space_id=space_id,
            conversation_id=conversation_id,
            content=question,
        )

    answer_parts: list[str] = []
    sql_str: str | None = None
    data_rows: list[dict[str, Any]] | None = None

    # attachments 순회 — text / query 추출 (schema variance graceful)
    attachments = getattr(msg, "attachments", None) or []
    for att in attachments:
        try:
            text_obj = getattr(att, "text", None)
            if text_obj and getattr(text_obj, "content", None):
                answer_parts.append(str(text_obj.content))
        except Exception:
            pass
        try:
            query_obj = getattr(att, "query", None)
            if query_obj:
                q_str = getattr(query_obj, "query", None)
                if q_str:
                    sql_str = str(q_str)
                # statement_response.result.data_array 추출 시도
                stmt = getattr(query_obj, "statement_response", None)
                result = getattr(stmt, "result", None) if stmt else None
                data_array = getattr(result, "data_array", None) if result else None
                manifest = getattr(stmt, "manifest", None) if stmt else None
                schema = getattr(manifest, "schema", None) if manifest else None
                columns = getattr(schema, "columns", None) if schema else None
                if data_array and columns:
                    col_names = [getattr(c, "name", f"col_{i}") for i, c in enumerate(columns)]
                    data_rows = [dict(zip(col_names, row)) for row in data_array[:50]]
        except Exception as e:
            logger.warning("genie attachment parse partial fail: %s", e)

    answer = "\n\n".join(answer_parts) if answer_parts else "(Genie 응답 비어있음 — 다시 질문해주세요)"

    return GenieResponse(
        answer=answer,
        sql=sql_str,
        data=data_rows,
        conversation_id=str(getattr(msg, "conversation_id", "") or conversation_id or ""),
        message_id=str(getattr(msg, "id", getattr(msg, "message_id", "")) or ""),
        source="live",
    )


async def query_genie(question: str, conversation_id: str | None) -> GenieResponse:
    """Async wrapper — settings.genie_enabled False면 raise GenieNotConfigured."""
    settings = get_settings()
    if not settings.genie_enabled:
        raise GenieNotConfigured("GENIE_SPACE_ID not set")

    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(
                _sync_call_genie, settings.genie_space_id, question, conversation_id
            ),
            timeout=GENIE_TIMEOUT_SEC,
        )
        return result
    except asyncio.TimeoutError:
        logger.warning("genie timeout after %ss", GENIE_TIMEOUT_SEC)
        raise
    except Exception as e:
        logger.warning("genie call failed: %s", e)
        raise


# ════════════════════════════════════════════════════════════════════════
# Fallback canned (Lakebase 직접 SQL — Apps + UC 조합 시연)
# ════════════════════════════════════════════════════════════════════════
@dataclass
class FallbackEntry:
    keywords: list[str]
    sql: str | None
    text_template: str  # {row_count} {latest} {avg} 등 format 가능
    sample_text: str   # SQL 실패 시 text-only


# 3 entry — 시나리오 §14 narrative anchor와 일치
_FALLBACK_ENTRIES: list[FallbackEntry] = [
    FallbackEntry(
        keywords=["OPEC", "MOMR", "사우디", "saudi", "공급"],
        sql=(
            "SELECT report_month, saudi_kbbl_d, opec_total_kbbl_d, "
            "       forecast_demand_kbbl_d, market_balance "
            "FROM crude_compass.bronze.opec_momr_monthly "
            "ORDER BY report_month DESC LIMIT 3"
        ),
        text_template=(
            "최근 OPEC MOMR 3개월 공급/수요: {rows_summary}. "
            "사우디 감산 시그널 + 시장 balance 변화로 Pattern Score 영향."
        ),
        sample_text=(
            "OPEC Monthly Oil Market Report — bronze.opec_momr_monthly 24개월 데이터 "
            "(ai_parse_document로 PDF 직접 파싱). Genie Space 등록 후 라이브 응답."
        ),
    ),
    FallbackEntry(
        keywords=["EIA", "재고", "weekly", "inventory"],
        sql=(
            "SELECT week_ending, delta_vs_prev_wk, inventory_type "
            "FROM crude_compass.bronze.eia_inventory "
            "WHERE inventory_type = 'commercial' "
            "ORDER BY week_ending DESC LIMIT 4"
        ),
        text_template=(
            "최근 4주 EIA 상업용 원유 재고 변화: {rows_summary}. "
            "음수=재고 감소(가격 상승 신호), 양수=재고 증가(가격 하락 신호)."
        ),
        sample_text=(
            "EIA Weekly Petroleum Status Report — bronze.eia_inventory 766주 데이터 보유. "
            "(라이브 응답은 Genie Space 등록 후. fallback 모드)"
        ),
    ),
    FallbackEntry(
        keywords=["두바이", "Dubai", "momentum", "가격", "price"],
        sql=(
            "SELECT trade_date, price_usd "
            "FROM crude_compass.bronze.oil_prices_daily "
            "WHERE ticker = 'DUBAI' "
            "ORDER BY trade_date DESC LIMIT 7"
        ),
        text_template=(
            "최근 7일 Dubai유 종가: {rows_summary}. "
            "7일 momentum (첫일 vs 마지막일): {momentum}%. "
            "한국 정유사 핵심 벤치마크 (한국석유공사 OPINET)."
        ),
        sample_text=(
            "Dubai 일별 종가 — bronze.oil_prices_daily 2,545+ 행 (1996~). "
            "Genie Space 라이브 응답 미연동 시 fallback 모드 — 데이터는 그대로 활용."
        ),
    ),
]


def _format_opec_summary(rows: list[dict[str, Any]]) -> str:
    """OPEC MOMR 3개월 요약."""
    parts = []
    for r in rows:
        m = str(r.get("report_month"))[:7] if r.get("report_month") else "?"
        saudi = r.get("saudi_kbbl_d")
        bal = r.get("market_balance") or "?"
        saudi_str = f"{int(saudi):,}kb/d" if saudi is not None else "?"
        parts.append(f"{m} 사우디 {saudi_str} ({bal})")
    return " · ".join(parts)


def _format_eia_summary(rows: list[dict[str, Any]]) -> str:
    """EIA 4주 데이터 한 줄 요약."""
    parts = []
    for r in rows:
        wk = r.get("week_ending")
        delta = r.get("delta_vs_prev_wk")
        wk_str = str(wk)[:10] if wk else "?"
        delta_str = f"{int(delta):+,}" if delta is not None else "?"
        parts.append(f"{wk_str} {delta_str}kbbl")
    return " · ".join(parts)


def _format_price_summary(rows: list[dict[str, Any]]) -> tuple[str, str]:
    """가격 7일 + momentum 계산."""
    if len(rows) < 2:
        return "데이터 부족", "?"
    parts = []
    for r in rows[:5]:  # 5일만 표시
        d = str(r.get("trade_date", ""))[:10]
        p = r.get("price_usd")
        parts.append(f"{d} ${float(p):.2f}" if p is not None else f"{d} ?")
    # rows는 desc 정렬 → momentum = (최신 - 가장 오래된) / 가장 오래된 × 100
    latest = float(rows[0].get("price_usd") or 0)
    oldest = float(rows[-1].get("price_usd") or 0)
    momentum = ((latest - oldest) / oldest * 100) if oldest else 0
    return " · ".join(parts), f"{momentum:+.2f}"


def _exec_sql(sql: str) -> list[dict[str, Any]] | None:
    """Databricks SQL Warehouse에 직접 SQL 실행. UC tables (bronze/silver/gold) 대상.

    2026-05-21 fix: 기존 Lakebase psycopg connection 사용 → cross-database error.
    UC Delta tables는 Postgres에 없고 Warehouse에서만 query 가능.
    `trigger_detector._q()` 패턴 (WorkspaceClient.statement_execution) 재사용.
    """
    try:
        from app.services.trigger_detector import _client, _warehouse_id

        w = _client()
        r = w.statement_execution.execute_statement(
            statement=sql.strip(),
            warehouse_id=_warehouse_id(),
            wait_timeout="20s",
        )
        if r.status and r.status.error:
            logger.warning("fallback SQL warehouse error: %s", r.status.error.message)
            return None
        if not (r.result and r.result.data_array):
            return []
        # column names from manifest
        cols: list[str] = []
        if r.manifest and r.manifest.schema and r.manifest.schema.columns:
            cols = [c.name for c in r.manifest.schema.columns]
        rows: list[dict[str, Any]] = []
        for row in r.result.data_array:
            if cols and len(row) == len(cols):
                rows.append({cols[i]: row[i] for i in range(len(cols))})
            else:
                rows.append({str(i): v for i, v in enumerate(row)})
        return rows
    except Exception as e:
        logger.warning("fallback SQL failed: %s", e)
        return None


async def fallback_canned(question: str) -> GenieResponse:
    """키워드 매칭 + (가능하면) Lakebase 직접 SQL."""
    q_lower = question.lower()

    matched: FallbackEntry | None = None
    for entry in _FALLBACK_ENTRIES:
        for kw in entry.keywords:
            if kw.lower() in q_lower:
                matched = entry
                break
        if matched:
            break

    if matched is None:
        # generic meta-answer — placeholder leak 막기 위해 keyword 라벨만 노출
        _LABEL = {
            "OPEC": "OPEC MOMR 월간 보고서 (사우디·이란·총공급·수요·시장 균형)",
            "EIA": "EIA 미국 상업용 원유 재고 (주간 변화 ±kbbl)",
            "두바이": "Dubai유 7일 종가 + momentum (한국 정유사 벤치마크)",
        }
        examples = "\n".join(
            f"- {entry.keywords[0]}: {_LABEL.get(entry.keywords[0], entry.keywords[0])}"
            for entry in _FALLBACK_ENTRIES
        )
        return GenieResponse(
            answer=(
                "Multi-Agent Supervisor endpoint가 production 미연동 상태입니다 "
                "(Agent Bricks workspace 재등록 D-1 진행 중). "
                "현재 fallback 모드 — 다음 3가지 주제는 Lakebase에 직접 SQL로 응답:\n\n"
                f"{examples}\n\n"
                "예: \"OPEC 5월 사우디 감산 근거는?\" 또는 \"최근 EIA 재고 변화\" 등으로 질문해보세요."
            ),
            source="fallback",
        )

    # SQL 실행 시도
    if matched.sql:
        rows = await asyncio.to_thread(_exec_sql, matched.sql)
        if rows is not None:
            # text_template format
            try:
                if "OPEC" in matched.keywords[0]:
                    answer = matched.text_template.format(
                        rows_summary=_format_opec_summary(rows)
                    )
                elif "EIA" in matched.keywords[0]:
                    answer = matched.text_template.format(
                        rows_summary=_format_eia_summary(rows)
                    )
                elif "두바이" in matched.keywords[0] or "Dubai" in matched.keywords[0]:
                    summary, mom = _format_price_summary(rows)
                    answer = matched.text_template.format(
                        rows_summary=summary, momentum=mom
                    )
                else:
                    answer = matched.sample_text
                return GenieResponse(
                    answer=answer,
                    sql=matched.sql,
                    data=rows[:5],  # 최대 5행 노출
                    source="fallback_data",
                )
            except Exception as e:
                logger.warning("fallback format failed: %s", e)

    # SQL 실패 → text-only
    return GenieResponse(
        answer=matched.sample_text,
        sql=matched.sql,
        source="fallback_text",
    )
