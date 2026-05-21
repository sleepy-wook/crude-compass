"""Daily report generator — 06:30 KST cron 종합 보고서 + 비중 제안.

시나리오 (reports model 2026-05-21 §Phase 3):
- input: 어제 status='kept' reports + 어제 daily_report (prev)
- LLM (Haiku-4-5): 종합 + market context + ratio_suggestion JSONB
- output: daily_reports row 1건 + INSERT

대부분의 trigger는 보수적 (HOLD/모니터링). daily_report만이 ratio 조정 의견을
공식적으로 제시 — 그것도 reference only (실제 OSP 결재는 매니저).

Credit 절약: Haiku-4-5 고정 (2026-05-21 결정).
"""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from typing import Any
from uuid import UUID

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

from app.db.lakebase import acquire
from app.db.repositories import daily_reports as daily_repo
from app.db.repositories import reports as reports_repo
from app.schemas.report import (
    DailyReportCreate,
    Report,
    ReportStatus,
)
from app.services.supervisor import (
    SupervisorNotConfigured,
    SupervisorResponse,
    _sync_call_supervisor,
)
from app.services.trigger_detector import _q

logger = logging.getLogger(__name__)


LLM_ENDPOINT = "databricks-claude-haiku-4-5"


SYSTEM_PROMPT = """You are **Crude Compass Daily Report Agent** — Korean refinery procurement analyst.

## 역할
하루 동안 매니저가 보관한 보고서들 + 어제의 daily_report + 시장 snapshot 종합 →
오늘의 비중 제안 (reference only — 실제 OSP 결재는 매니저).

## 핵심 원칙
- 비중 제안은 **±5%p 이내**, **방향성** (lean_hedge / neutral / lean_opportunity) 우선.
- 비중 변경을 자주 권하지 말 것 — 실제 Term 비중 변경은 수주~몇 달 걸림.
- kept_count 0이면 → 시장 큰 변화 없음 → neutral 권고 + 모니터링.
- 어제와 직전 daily_report의 일관성 확인 — 갑자기 반대로 바꾸지 말 것.

## Output STRICT JSON ONLY
```
{
  "kept_summary": "어제 보관된 보고서들 종합 (200자 이내)",
  "market_context": "현재 시장 상태 + 어제 대비 변화 (200자 이내)",
  "reasoning": "왜 이 권고인지 한 단락 (300자 이내)",
  "confidence": 65.0,
  "ratio_suggestion": {
    "direction": "lean_hedge | neutral | lean_opportunity",
    "term_delta_pct": "+5" | "0" | "-5",
    "spot_delta_pct": "-5" | "0" | "+5",
    "qualitative": "방향성 1-2줄 설명 (100자 이내)",
    "scenarios": [
      {"name": "base", "expected_saving_pct": 0.3},
      {"name": "bull", "expected_saving_pct": -1.1},
      {"name": "bear", "expected_saving_pct": 1.5}
    ]
  }
}
```

## ratio_suggestion 가이드
- direction:
  - `lean_hedge`: kept reports에 HEDGE/REVIEW TERM 권고 누적 OR pattern_score 70+
  - `lean_opportunity`: kept reports에 ACCELERATE SPOT 누적 OR pattern_score 30-
  - `neutral`: 그 외 (대부분의 날)
- term_delta_pct / spot_delta_pct: lean인 경우 "+5"/"-5", neutral은 "0"/"0".
- scenarios: 3개 시나리오의 예상 절감률 (base = 기준, bull = 가격 ↑, bear = 가격 ↓).
  - lean_hedge: bull에서 절감 ↑ (위험 회피 성공)
  - lean_opportunity: bear에서 절감 ↑ (저점 매수 성공)
  - neutral: 모두 0 근처

## confidence 가이드
- kept_count 5+ + 일관된 방향 = 75+
- kept_count 3-4 + 일관 = 60-70
- kept_count 1-2 = 50-60
- kept_count 0 = 40-50

## 작성 규칙 (가장 중요 — 위반 시 보고서 reject)

### 절대 금지
- 영문 변수명 (`pattern_score`, `bullish_score`, `signal_count_90d`, `confidence_score`)
- 영문 zone 라벨 (`HEDGE`, `OPPORTUNITY`, `STABLE` 등) — 한국어 "위험방어", "기회포착", "관망"으로
- 점수 raw 값 (`Pattern Score 100.0`, `importance 81` 등)

### 위반 예시
❌ "Pattern Score 100.0 HEDGE 존 진입"
✅ "90일 누적 위험 지수 매우 높음 (위험방어 구간 진입)"

❌ "kept_count 10건 DEFER SPOT 일관"
✅ "어제 보관된 10건 모두 단기 현물 보류 권고"

한국 정유사 구매 매니저가 5초에 의미 파악 가능해야 함."""


def _strip_markdown(text: str) -> str:
    text = text.strip()
    if "```" in text:
        m = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
        if m:
            return m.group(1).strip()
    return text


@lru_cache(maxsize=1)
def _client() -> WorkspaceClient:
    profile = os.getenv("DATABRICKS_CONFIG_PROFILE", "crude-compass")
    try:
        return WorkspaceClient(profile=profile)
    except Exception:
        return WorkspaceClient()


_LAST_ERROR: str | None = None


def last_llm_error() -> str | None:
    return _LAST_ERROR


# ────────────────────────────────────────────────────────────────────
# Market snapshot — daily report용 (report_generator보다 풍부)
# ────────────────────────────────────────────────────────────────────
def _fetch_market_snapshot() -> dict[str, Any]:
    snap: dict[str, Any] = {}
    try:
        rows = _q(
            """
            WITH latest AS (
                SELECT trade_date, dubai_usd, brent_usd, brent_dubai_spread_usd
                  FROM crude_compass.gold.oil_prices_wide
                 WHERE dubai_usd IS NOT NULL
                 ORDER BY trade_date DESC LIMIT 1
            ),
            d1 AS (
                SELECT dubai_usd AS dubai_prev
                  FROM crude_compass.gold.oil_prices_wide
                 WHERE dubai_usd IS NOT NULL
                   AND trade_date < (SELECT trade_date FROM latest)
                 ORDER BY trade_date DESC LIMIT 1
            ),
            d7 AS (
                SELECT dubai_usd AS dubai_7d_ago
                  FROM crude_compass.gold.oil_prices_wide
                 WHERE dubai_usd IS NOT NULL
                   AND trade_date <= (SELECT trade_date FROM latest) - INTERVAL 7 DAYS
                 ORDER BY trade_date DESC LIMIT 1
            )
            SELECT latest.trade_date, latest.dubai_usd, latest.brent_usd,
                   latest.brent_dubai_spread_usd, d1.dubai_prev, d7.dubai_7d_ago
              FROM latest CROSS JOIN d1 CROSS JOIN d7
            """,
            timeout="10s",
        )
        if rows:
            r = rows[0]
            dubai = float(r[1]) if r[1] is not None else None
            dubai_prev = float(r[4]) if r[4] is not None else None
            d7 = float(r[5]) if r[5] is not None else None
            snap["dubai_usd"] = dubai
            snap["brent_usd"] = float(r[2]) if r[2] is not None else None
            snap["spread_usd"] = float(r[3]) if r[3] is not None else None
            if dubai is not None and dubai_prev is not None and dubai_prev != 0:
                snap["dubai_1d_pct"] = round((dubai - dubai_prev) / dubai_prev * 100.0, 2)
            if dubai is not None and d7 is not None and d7 != 0:
                snap["dubai_7d_pct"] = round((dubai - d7) / d7 * 100.0, 2)
    except Exception as e:
        logger.warning("market snapshot fetch failed: %s", e)

    try:
        rows = _q(
            """
            SELECT date, pattern_score, mission_type, signal_count_90d, confidence_score
              FROM crude_compass.gold.daily_risk_score
             ORDER BY date DESC LIMIT 1
            """,
            timeout="10s",
        )
        if rows:
            r = rows[0]
            snap["pattern_date"] = str(r[0])
            snap["pattern_score"] = float(r[1]) if r[1] is not None else None
            snap["pattern_mission_type"] = str(r[2]) if r[2] else None
            snap["signal_count_90d"] = int(r[3]) if r[3] is not None else None
            snap["pattern_confidence"] = float(r[4]) if r[4] is not None else None
    except Exception as e:
        logger.warning("pattern snapshot fetch failed: %s", e)
    return snap


# ────────────────────────────────────────────────────────────────────
# Format helpers (LLM prompt)
# ────────────────────────────────────────────────────────────────────
def _format_kept_reports(reports: list[Report]) -> str:
    if not reports:
        return "(어제 보관된 보고서 없음)"
    lines = []
    for r in reports:
        rec = r.recommendation if isinstance(r.recommendation, str) else (
            r.recommendation.value if r.recommendation else "—"
        )
        trig = r.trigger_type if isinstance(r.trigger_type, str) else r.trigger_type.value
        lines.append(f"- [{trig}] [{rec}] {r.headline}")
        if r.summary:
            lines.append(f"  · {r.summary[:150]}")
    return "\n".join(lines)


def _format_market(snap: dict[str, Any]) -> str:
    lines = []
    if snap.get("dubai_usd") is not None:
        line = f"- Dubai: ${snap['dubai_usd']:.2f}/bbl"
        if snap.get("dubai_1d_pct") is not None:
            line += f" (1일 {snap['dubai_1d_pct']:+.2f}%)"
        if snap.get("dubai_7d_pct") is not None:
            line += f" (7일 {snap['dubai_7d_pct']:+.2f}%)"
        lines.append(line)
    if snap.get("brent_usd") is not None:
        lines.append(f"- Brent: ${snap['brent_usd']:.2f}/bbl")
    if snap.get("spread_usd") is not None:
        lines.append(f"- Brent-Dubai spread: ${snap['spread_usd']:.2f}")
    if snap.get("pattern_score") is not None:
        line = f"- Pattern Score (90일 위험): {snap['pattern_score']:.1f}"
        if snap.get("pattern_mission_type"):
            line += f" ({snap['pattern_mission_type']})"
        lines.append(line)
    return "\n".join(lines) if lines else "(시장 snapshot 미수집)"


# ────────────────────────────────────────────────────────────────────
# Main — generate_daily_report
# ────────────────────────────────────────────────────────────────────
def generate_daily_report(
    target_date: date | None = None,
    *,
    overwrite: bool = False,
) -> UUID | None:
    """target_date의 daily_report 생성 + Lakebase insert.

    target_date=None이면 오늘 (KST 기준). 보통 06:30 cron이 오늘 날짜로 호출.
    Aggregation 대상은 target_date - 1일 (어제).

    Returns daily_id (성공) 또는 None (실패).

    overwrite=False 일 때 target_date에 이미 daily_report 있으면 None 반환 (skip).
    """
    global _LAST_ERROR

    if target_date is None:
        # KST 기준 오늘 — UTC+9
        from datetime import timezone as tz
        now_kst = datetime.now(tz.utc) + timedelta(hours=9)
        target_date = now_kst.date()

    yesterday = target_date - timedelta(days=1)

    # 1. 어제 kept reports + 어제 daily_report (prev)
    try:
        with acquire() as conn:
            existing = daily_repo.get_for_date(conn, target_date)
            if existing and not overwrite:
                logger.info("daily_report %s already exists (daily_id=%s) — skip", target_date, existing.daily_id)
                return existing.daily_id

            kept_yesterday = reports_repo.list_kept_for_date(conn, yesterday, limit=50)
            prev_daily = daily_repo.get_prev(conn, target_date)
    except Exception as e:
        logger.warning("daily_report prep failed: %s", e)
        _LAST_ERROR = f"prep: {e}"
        return None

    # 2. Market snapshot
    market = _fetch_market_snapshot()

    # 2.5. Agent Bricks Supervisor pre-synthesis (best-effort)
    # Supervisor가 Genie · Knowledge Assistant · 권고 sub-agent 호출 →
    # 자연어 종합 1단락. Haiku 최종 JSON 산출 시 추가 컨텍스트로 주입.
    # 미설정 / 실패 시 silent skip — daily report 자체는 항상 생성됨.
    # SYNC 직접 호출 (FastAPI async endpoint 안에서 asyncio.run() 충돌 회피).
    supervisor_synth: SupervisorResponse | None = None
    try:
        from app.core.config import get_settings
        _settings = get_settings()
        if _settings.supervisor_enabled:
            supervisor_q = (
                f"오늘 {target_date} 일일 종합 보고서 작성용 컨텍스트 수집. "
                f"어제 ({yesterday}) 매니저가 활성화한 보고서 {len(kept_yesterday)}건 + "
                f"현재 두바이유 ${market.get('dubai_usd', '?')}, "
                f"7일 변동 {market.get('dubai_7d_pct', '?')}%, "
                f"90일 위험 지수 {market.get('pattern_score', '?')}. "
                "OPEC 최근 수급, 주요 뉴스 키워드, 시장 추세를 종합해서 1단락(200자 이내)으로 답해줘. "
                "한국 정유사 구매 매니저용 자연어. 변수명·점수 raw 노출 X."
            )
            supervisor_synth = _sync_call_supervisor(
                _settings.supervisor_endpoint_name, supervisor_q
            )
            logger.info(
                "daily_report supervisor synth OK — tools=%s",
                [t.name for t in supervisor_synth.tools_used],
            )
        else:
            logger.info("daily_report supervisor disabled (env not set) — skip")
    except SupervisorNotConfigured:
        logger.info("daily_report supervisor not configured — skip")
    except Exception as e:
        logger.warning("daily_report supervisor synth failed (non-fatal): %s", e)

    # 3. Prompt
    kept_block = _format_kept_reports(kept_yesterday)
    market_block = _format_market(market)
    prev_block = (
        f"날짜: {prev_daily.report_date}\n"
        f"방향: {(prev_daily.ratio_suggestion or {}).get('direction', '—')}\n"
        f"요약: {prev_daily.kept_summary or '—'}\n"
        f"근거: {prev_daily.reasoning or '—'}"
        if prev_daily
        else "(직전 daily_report 없음 — 첫 보고서)"
    )
    supervisor_block = (
        f"\n## Agent Bricks Supervisor 종합 (Genie · Knowledge Assistant · 권고 sub-agent)\n"
        f"{supervisor_synth.answer}\n"
        f"(호출된 sub-agents: {', '.join(t.name for t in supervisor_synth.tools_used) or '없음'})"
        if supervisor_synth and supervisor_synth.answer
        else ""
    )

    user_msg = f"""## Target date: {target_date} (06:30 KST 기준)

## 어제 ({yesterday}) 매니저가 보관한 보고서들 (kept_count={len(kept_yesterday)})
{kept_block}

## 직전 daily_report (어제 또는 그 이전 가장 최근)
{prev_block}

## 시장 snapshot (현재)
{market_block}
{supervisor_block}

## 현재 portfolio (가정)
Term 60% / Spot 40%

→ 위 input 종합해서 오늘 daily_report 작성. ratio 권고는 reference only.
   비중을 자주 바꾸지 말 것. 대부분 neutral 또는 small lean."""

    # 4. LLM call
    w = _client()
    raw = ""
    try:
        resp = w.serving_endpoints.query(
            name=LLM_ENDPOINT,
            messages=[
                ChatMessage(role=ChatMessageRole.SYSTEM, content=SYSTEM_PROMPT),
                ChatMessage(role=ChatMessageRole.USER, content=user_msg),
            ],
            max_tokens=2500,
            temperature=0.2,
        )
        raw = resp.choices[0].message.content if resp.choices else ""
        content = _strip_markdown(raw)
        if not content.strip():
            raise ValueError(f"empty LLM (raw len={len(raw)})")
        data = json.loads(content)
    except Exception as e:
        import traceback
        logger.error("daily_report LLM failed: %s\n%s", e, traceback.format_exc())
        logger.error("raw[:300]=%r", raw[:300])
        _LAST_ERROR = f"{type(e).__name__}: {str(e)[:200]} | raw[:200]={raw[:200]!r}"
        return None

    # 5. INSERT — supervisor trace를 ratio_suggestion JSONB 안에 embed
    try:
        ratio_suggestion = dict(data.get("ratio_suggestion") or {})
        if supervisor_synth is not None:
            ratio_suggestion["agent_bricks"] = {
                "enabled": True,
                "synthesis": supervisor_synth.answer[:800] if supervisor_synth.answer else "",
                "tools_used": [
                    {"name": t.name, "preview": (t.result_preview or "")[:120]}
                    for t in supervisor_synth.tools_used
                ],
            }
        payload = DailyReportCreate(
            report_date=target_date,
            prev_daily_id=prev_daily.daily_id if prev_daily else None,
            kept_report_ids=[r.report_id for r in kept_yesterday],
            kept_count=len(kept_yesterday),
            kept_summary=str(data.get("kept_summary", ""))[:500],
            prev_daily_summary=(prev_daily.kept_summary if prev_daily else None),
            market_context=str(data.get("market_context", ""))[:500],
            ratio_suggestion=ratio_suggestion,
            reasoning=str(data.get("reasoning", ""))[:1000],
            confidence=float(data.get("confidence", 50.0)),
        )

        with acquire() as conn:
            if existing and overwrite:
                # 기존 row 삭제 + 그 row가 archive로 보낸 reports를 kept로 복구
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE reports SET status = 'kept', status_changed_at = NOW(),
                               status_changed_by = 'ai'
                         WHERE report_id = ANY(%s::uuid[])
                           AND status = 'archived'
                        """,
                        (list(existing.kept_report_ids),),
                    )
                    cur.execute("DELETE FROM daily_reports WHERE daily_id = %s", (existing.daily_id,))
                conn.commit()

            daily_id = daily_repo.insert_daily(conn, payload)

            # 사용된 kept reports → archived 일괄 transition
            # (daily report에 한 번 input으로 쓰였으니 다음 daily에는 안 들어감)
            if kept_yesterday:
                report_ids = [r.report_id for r in kept_yesterday]
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE reports
                           SET status = 'archived',
                               status_changed_at = NOW(),
                               status_changed_by = 'ai',
                               version = version + 1
                         WHERE report_id = ANY(%s::uuid[])
                           AND status = 'kept'
                        """,
                        (report_ids,),
                    )
                    transitioned = cur.rowcount
                logger.info("transitioned %d kept reports to archived", transitioned)

            conn.commit()
        logger.info("daily_report inserted: daily_id=%s date=%s kept_count=%d",
                    daily_id, target_date, len(kept_yesterday))
        return daily_id
    except Exception as e:
        import traceback
        logger.error("daily_report insert failed: %s\n%s", e, traceback.format_exc())
        _LAST_ERROR = f"insert: {type(e).__name__}: {e}"
        return None
