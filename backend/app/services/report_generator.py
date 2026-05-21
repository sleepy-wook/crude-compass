"""Report generator — TriggerEvent → AI report 1건 (Haiku-4-5).

시나리오 (reports model 2026-05-21):
- trigger_detector가 잡은 1건의 TriggerEvent 받아서
- 최근 시장 context (signals + prices + pattern) 수집해서
- Haiku-4-5에게 prompt → JSON (headline / summary / reasoning / recommendation) emit
- ReportCreate Pydantic으로 validate해서 caller에게 return

Caller가 reports_repo.insert_report로 Lakebase에 저장.

Credit 절약 위해 endpoint = databricks-claude-haiku-4-5 고정.
"""
from __future__ import annotations

import json
import logging
import os
import re
from functools import lru_cache
from typing import Any

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

from app.schemas.report import (
    Recommendation,
    ReportCreate,
    TriggerType,
)
from app.services.trigger_detector import TriggerEvent, _q

logger = logging.getLogger(__name__)


LLM_ENDPOINT = "databricks-claude-haiku-4-5"


# ════════════════════════════════════════════════════════════════════════
# System prompt — short, structured (Haiku는 길게 줘도 잘 못따라옴)
# ════════════════════════════════════════════════════════════════════════
SYSTEM_PROMPT = """You are **Crude Compass Report Agent** — Korean refinery procurement analyst.

## 역할
시장 trigger 이벤트 1건 받아서 한국 정유사 구매 매니저용 짧은 보고서 작성.
**비중 조정을 자주 권하지 말 것** — 실제 Term 비중 변경은 수주~몇 달 걸림.
대부분의 trigger는 HOLD (정보 모니터링) 또는 DEFER/ACCELERATE SPOT (1주 단위 조정) 권고.

## Trigger 종류
- **gdelt_signal**: 고importance 뉴스 — 지정학·정책·공급 충격 가능성
- **price_spike**: Dubai 가격 24h ±2% — 단기 변동성
- **pattern_drift**: 90일 누적 위험 지수 7일 평균 ±10pt — 추세 변화

## Output STRICT JSON ONLY (markdown X, code block X)
```
{
  "headline": "한 줄 50자 이내 — 일어난 사건 + 시사점",
  "summary": "3줄 200자 이내 — 무슨 일 / 왜 중요 / 시장 영향",
  "reasoning": {
    "key_signals": ["...", "..."],
    "logic": "한 단락 300자 이내 — 왜 이 권고인지",
    "risk_factors": ["가설1", "가설2"]
  },
  "recommendation": "HOLD | DEFER SPOT | ACCELERATE SPOT | REVIEW TERM | HEDGE | DIVERSIFY",
  "recommendation_text": "구체 권고 100자 이내 (예: '이번 주 Spot 발주 1주 보류')"
}
```

## Recommendation 의미
- **HOLD**: 현재 비중 유지, 모니터링만
- **DEFER SPOT**: 단기 Spot 발주 1주~2주 연기 (1주 단위)
- **ACCELERATE SPOT**: 단기 Spot 발주 1주 앞당김
- **REVIEW TERM**: Term contract 재검토 시그널 누적 — 다음 OSP cycle 회의 안건
- **HEDGE**: 위험 강함 — Term 비중 +5%p 검토 (실행은 OSP cycle)
- **DIVERSIFY**: supplier 다변화 검토 (Saudi 의존도 ↓)

대부분의 trigger는 **HOLD** 또는 **DEFER/ACCELERATE SPOT**. HEDGE/REVIEW TERM은 정말 강한 시그널일 때만.

## 작성 규칙 (가장 중요 — 위반 시 보고서 reject)

### 절대 금지 — 매니저가 5초에 이해 못함
- `Pattern Score 100.0`, `pattern_score 73.5`, `signal_count_90d` → 영문 변수명 + raw 점수 X
- `bullish_score`, `bearish_score`, `cross_val_bonus`, `confidence_score` → 내부 변수명 X
- `HEDGE 존`, `OPPORTUNITY 존`, `STABLE zone` → 영문 zone 라벨 X
- `importance 88`, `tone -0.93`, `(imp 92)` → 점수 raw 값 X
- `Term 60%`, `Spot 40%` → portfolio 라벨은 OK (자주 쓰임)

### 위반 예시
❌ "Pattern Score 100.0(헤지 수준)에 진입한 상태"
✅ "90일 누적 위험 지수가 최고 수준 도달 (헤지 구간)"

❌ "GDELT 신호 importance 81 + tone -0.93"
✅ "러우 갈등 관련 매우 강한 부정 신호 1건"

❌ "HEDGE 존 진입, 변동성 확대 신호"
✅ "위험방어 구간 진입, 변동성 확대 신호"

### 정상 표현 (한국어 자연어로 풀어쓰기)
- "위험 지수 매우 높음 (10점 만점 9-10)" — 강도 자연어
- "위험 신호가 안정 신호보다 약 2배 우세" — 자연어 비교
- "지난 3주 위험 신호 6건 누적, 4 source가 같은 방향 확인" — 빈도 + 다양성
- "두바이유 7일간 +9% 상승 (공급 차질 우려 반영)" — 숫자 + 의미
- "위험방어 구간 (90일 누적 위험 지수)" — 점수 라벨은 한국어 풀어쓰기

### Self-check (output 직전 필수)
1. headline/summary/reasoning 다시 읽기
2. 영문 underscore_case 단어 (`pattern_score`, `bullish_score`, `signal_count_90d` 등) 있나? → 자연어 교체
3. 숫자 점수 raw 값 노출됐나? → 강도 자연어로 풀어쓰기 ("강도 9-10" 등)
4. 영문 zone 라벨 (`HEDGE`, `OPPORTUNITY`, `STABLE`) 있나? → "위험방어", "기회포착", "관망"으로 교체

한국 정유사 구매 매니저가 영문 jargon 없이도 5초에 의미 파악 가능해야 합격."""


def _strip_markdown(text: str) -> str:
    """LLM이 ```json``` wrap하면 strip."""
    text = text.strip()
    if "```" in text:
        m = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
        if m:
            return m.group(1).strip()
    return text


# ════════════════════════════════════════════════════════════════════════
# Context fetch — recent signals + market snapshot
# ════════════════════════════════════════════════════════════════════════
def _fetch_recent_signals(limit: int = 5) -> list[dict[str, Any]]:
    """최근 24h importance Top N news. Prompt에 추가 context로 주입."""
    try:
        rows = _q(
            f"""
            SELECT title, source, category, direction, importance, url
              FROM crude_compass.bronze.news_articles
             WHERE published_at >= CURRENT_TIMESTAMP() - INTERVAL 24 HOURS
               AND direction IN ('bullish', 'bearish')
             ORDER BY importance DESC, mention_count DESC
             LIMIT {limit}
            """,
            timeout="10s",
        )
    except Exception as e:
        logger.warning("recent signals fetch failed: %s", e)
        return []
    out = []
    for r in rows:
        out.append({
            "title": str(r[0] or "")[:150],
            "source": str(r[1] or ""),
            "category": str(r[2] or ""),
            "direction": str(r[3] or ""),
            "importance": int(r[4]) if r[4] is not None else None,
            "url": str(r[5]) if len(r) > 5 and r[5] else None,
        })
    return out


def _fetch_market_snapshot() -> dict[str, Any]:
    """오늘 Dubai / 7d 변동 / 최신 pattern_score."""
    snapshot: dict[str, Any] = {}
    try:
        price_rows = _q(
            """
            WITH latest AS (
                SELECT trade_date, dubai_usd, brent_usd, brent_dubai_spread_usd
                  FROM crude_compass.gold.oil_prices_wide
                 WHERE dubai_usd IS NOT NULL
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
                   latest.brent_dubai_spread_usd, d7.dubai_7d_ago
              FROM latest CROSS JOIN d7
            """,
            timeout="10s",
        )
        if price_rows:
            r = price_rows[0]
            dubai = float(r[1]) if r[1] is not None else None
            d7 = float(r[4]) if r[4] is not None else None
            snapshot["dubai_usd"] = dubai
            snapshot["brent_usd"] = float(r[2]) if r[2] is not None else None
            snapshot["brent_dubai_spread_usd"] = float(r[3]) if r[3] is not None else None
            if dubai is not None and d7 is not None and d7 != 0:
                snapshot["dubai_7d_change_pct"] = round((dubai - d7) / d7 * 100.0, 2)
    except Exception as e:
        logger.warning("price snapshot fetch failed: %s", e)

    try:
        pat_rows = _q(
            """
            SELECT date, pattern_score, mission_type, signal_count_90d
              FROM crude_compass.gold.daily_risk_score
             ORDER BY date DESC LIMIT 1
            """,
            timeout="10s",
        )
        if pat_rows:
            r = pat_rows[0]
            snapshot["pattern_score"] = float(r[1]) if r[1] is not None else None
            snapshot["pattern_mission_type"] = str(r[2]) if r[2] else None
            snapshot["signal_count_90d"] = int(r[3]) if r[3] is not None else None
    except Exception as e:
        logger.warning("pattern snapshot fetch failed: %s", e)

    return snapshot


# ════════════════════════════════════════════════════════════════════════
# LLM client
# ════════════════════════════════════════════════════════════════════════
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


# ════════════════════════════════════════════════════════════════════════
# Main — TriggerEvent → ReportCreate (LLM call)
# ════════════════════════════════════════════════════════════════════════
def generate_report(event: TriggerEvent) -> ReportCreate | None:
    """TriggerEvent → ReportCreate (LLM emit) via Haiku-4-5.

    None 반환: LLM 실패. last_llm_error()로 진단.
    Caller는 insert_report로 저장 책임.
    """
    global _LAST_ERROR

    # 1. Context 수집
    recent_signals = _fetch_recent_signals(limit=5)
    market = _fetch_market_snapshot()

    # 2. Prompt 구성
    trigger_detail_lines = [f"- type: {event.trigger_type.value}", f"- detected_at: {event.detected_at.isoformat()}"]
    for k, v in event.meta.items():
        trigger_detail_lines.append(f"- {k}: {v}")
    trigger_block = "\n".join(trigger_detail_lines)

    signals_block = (
        "\n".join(
            f"- {s.get('title')} ({s.get('source')}, {s.get('category')}, {s.get('direction')}, 강도 {s.get('importance')})"
            for s in recent_signals
        )
        if recent_signals
        else "(최근 24h 강한 시그널 없음)"
    )

    market_lines = []
    if market.get("dubai_usd") is not None:
        chg = market.get("dubai_7d_change_pct")
        market_lines.append(
            f"- Dubai: ${market['dubai_usd']:.2f}/bbl"
            + (f" (7일 {chg:+.2f}%)" if chg is not None else "")
        )
    if market.get("brent_dubai_spread_usd") is not None:
        market_lines.append(f"- Brent-Dubai spread: ${market['brent_dubai_spread_usd']:.2f}")
    if market.get("pattern_score") is not None:
        market_lines.append(
            f"- Pattern Score (90일 위험 누적): {market['pattern_score']:.1f}"
            + (f" ({market.get('pattern_mission_type')})" if market.get("pattern_mission_type") else "")
        )
    market_block = "\n".join(market_lines) if market_lines else "(시장 snapshot 미수집)"

    user_msg = f"""## Trigger 이벤트 (1건)
{trigger_block}

이벤트 headline 힌트: {event.headline_hint}

## 최근 24h 강한 시그널 (참고)
{signals_block}

## 시장 snapshot (현재)
{market_block}

## 현재 portfolio (가정)
Term 60% / Spot 40%

→ 위 trigger를 매니저에게 알려야 한다. JSON 형식으로 보고서 작성. 비중 조정을 권하지 말고 모니터링/Spot 단기 조정 위주."""

    # 3. LLM call
    w = _client()
    raw_content = ""
    try:
        resp = w.serving_endpoints.query(
            name=LLM_ENDPOINT,
            messages=[
                ChatMessage(role=ChatMessageRole.SYSTEM, content=SYSTEM_PROMPT),
                ChatMessage(role=ChatMessageRole.USER, content=user_msg),
            ],
            max_tokens=2000,
            temperature=0.2,
        )
        raw_content = resp.choices[0].message.content if resp.choices else ""
        content = _strip_markdown(raw_content) if raw_content else ""
        if not content.strip():
            raise ValueError(f"empty LLM response (raw len={len(raw_content)})")
        data = json.loads(content)
    except Exception as e:
        import traceback
        logger.error("report_generator LLM call failed: %s", e)
        logger.error("raw[:300]=%r", raw_content[:300])
        logger.error("traceback: %s", traceback.format_exc())
        _LAST_ERROR = f"{type(e).__name__}: {str(e)[:200]} | raw[:200]={raw_content[:200]!r}"
        return None

    # 4. Validate + ReportCreate
    try:
        headline = str(data.get("headline", ""))[:200]
        summary = str(data.get("summary", ""))[:500]
        reasoning = data.get("reasoning") or {}
        if not isinstance(reasoning, dict):
            reasoning = {"logic": str(reasoning)}
        recommendation_raw = data.get("recommendation")
        rec_text = data.get("recommendation_text")
        if rec_text:
            # 별도 field 없으니 reasoning에 합쳐 보존
            reasoning.setdefault("recommendation_text", str(rec_text)[:200])

        rec: Recommendation | None = None
        if recommendation_raw:
            try:
                rec = Recommendation(str(recommendation_raw).strip())
            except ValueError:
                logger.warning("unknown recommendation from LLM: %r — using None", recommendation_raw)

        return ReportCreate(
            trigger_type=event.trigger_type,
            trigger_meta=event.to_trigger_meta(),
            headline=headline or event.headline_hint[:200],
            summary=summary or event.headline_hint,
            reasoning=reasoning,
            recommendation=rec,
            related_signals=[
                {
                    "title": s.get("title"),
                    "source": s.get("source"),
                    "direction": s.get("direction"),
                    "importance": s.get("importance"),
                    "url": s.get("url"),
                }
                for s in recent_signals
            ],
        )
    except Exception as e:
        import traceback
        logger.error("report_generator validation failed: %s", e)
        logger.error("data=%r", data)
        logger.error("traceback: %s", traceback.format_exc())
        _LAST_ERROR = f"validation: {type(e).__name__}: {e}"
        return None
