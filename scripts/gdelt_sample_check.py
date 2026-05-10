"""GDELT DOC API sample fetch + tone score 검증 (Sprint 2 task 2).

시나리오 v2 § 2 핵심: 호르무즈는 가장 극적 사례일 뿐, 평시 매주 시그널이 메인.
→ 평시 정기 시그널 (OPEC monthly / EIA inventory / Saudi OSP) catch 가능 검증.

API: https://api.gdeltproject.org/api/v2/doc/doc (key 없음, 100% free)

DoD:
1. HTTP 200 + JSON 파싱
2. tone score 추출 (-10~10 범위)
3. 평시 query에서도 mention 잡힘 (호르무즈만 잡히는 시스템이면 narrative 깨짐)
4. 한국어 query 결과 reasonable
5. bullish/bearish/neutral mapping 패턴 도출
"""
from __future__ import annotations

import sys
from typing import Any

# Windows PowerShell cp949 → UTF-8
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except (AttributeError, OSError):
        pass

import httpx


API_BASE = "https://api.gdeltproject.org/api/v2/doc/doc"


# 시나리오 § 16 Importance anchor 매핑:
# 100: 핵 협상 / IRGC 동원 (위기 극단)
#  80: 미 중동 군 출국, OPEC MOMR 발표 (평시 정기)
#  60: EIA 주간 재고, GDELT 멘션 +50% (평시 정기)
#  40: 사우디 정유 capacity (평시 미세)
QUERIES = [
    # 평시 정기 시그널 ⭐ (메인 가치)
    ("평시-OPEC monthly",   "OPEC monthly oil market report",   None),
    ("평시-EIA inventory",  "EIA crude oil inventory",          None),
    ("평시-Saudi OSP",      "Saudi Aramco OSP official price",  None),
    ("평시-중국 수요",       "China oil demand PMI",             None),
    # 한국어 처리
    ("한국어-원유",          "원유 OPEC",                          "korean"),
    # 위기 시그널 (극단 능력 검증)
    ("위기-호르무즈",        "Hormuz strait blockade",           None),
]


def fetch_articles(query: str, lang: str | None = None) -> dict[str, Any]:
    """artlist 모드 — 최근 article + tone score 추출."""
    params = {
        "query": query,
        "mode": "artlist",
        "format": "json",
        "timespan": "7d",     # 최근 7일
        "maxrecords": 10,
        "sort": "datedesc",
    }
    if lang == "korean":
        # GDELT는 sourcelang에 ISO 639-3 코드 (kor)
        params["query"] = f"{query} sourcelang:kor"

    resp = httpx.get(API_BASE, params=params, timeout=30.0)
    resp.raise_for_status()
    return resp.json()


def fetch_tonechart(query: str) -> dict[str, Any]:
    """tonechart 모드 — tone bucket 분포."""
    params = {
        "query": query,
        "mode": "tonechart",
        "format": "json",
        "timespan": "7d",
    }
    resp = httpx.get(API_BASE, params=params, timeout=30.0)
    resp.raise_for_status()
    return resp.json()


def fetch_timelinetone(query: str) -> dict[str, Any]:
    """timelinetone 모드 — 시계열 평균 tone (mention 강도)."""
    params = {
        "query": query,
        "mode": "timelinetone",
        "format": "json",
        "timespan": "7d",
    }
    resp = httpx.get(API_BASE, params=params, timeout=30.0)
    resp.raise_for_status()
    return resp.json()


def main() -> None:
    print("=" * 70)
    print("GDELT DOC API 검증 — 평시 시그널 catch 가능성 (시나리오 § 2 fit)")
    print("=" * 70)
    print()

    for label, query, lang in QUERIES:
        print(f"\n─── {label} · query='{query}' ───")

        # 1. artlist
        try:
            data = fetch_articles(query, lang)
            articles = data.get("articles", [])
            print(f"  📰 artlist: {len(articles)} articles")

            if articles:
                # tone 분포
                tones = [a.get("tone", 0.0) for a in articles[:5] if "tone" in a]
                if tones:
                    avg_tone = sum(tones) / len(tones)
                    print(f"     평균 tone (top 5): {avg_tone:+.2f} (range: {min(tones):+.2f} ~ {max(tones):+.2f})")
                    direction = "bullish" if avg_tone > 1.0 else "bearish" if avg_tone < -1.0 else "neutral"
                    print(f"     → direction 추정: {direction}")
                else:
                    print(f"     ⚠️  tone 필드 없음")

                # 첫 article sample
                a = articles[0]
                title = a.get("title", "")[:80]
                src = a.get("domain") or a.get("sourceurl", "")[:40]
                print(f"     첫 article: [{src}] {title}")
        except httpx.HTTPError as e:
            print(f"  ❌ artlist failed: {e}")

        # 2. timelinetone — 평시 정기 시그널의 mention 강도
        try:
            tl = fetch_timelinetone(query)
            timeline = tl.get("timeline", [])
            if timeline and timeline[0].get("data"):
                points = timeline[0]["data"]
                values = [p.get("value", 0.0) for p in points if "value" in p]
                if values:
                    avg = sum(values) / len(values)
                    print(f"  📈 timelinetone (7d): {len(values)} buckets, avg={avg:+.2f}, max={max(values):+.2f}, min={min(values):+.2f}")
        except (httpx.HTTPError, KeyError, IndexError) as e:
            print(f"  ⚠️  timelinetone error: {e}")

    print("\n" + "=" * 70)
    print("평가 항목:")
    print("  ✅ 평시 query (OPEC/EIA/Saudi/중국) 모두 mention 잡혀야 함")
    print("  ✅ tone score 분포 reasonable (-10~10)")
    print("  ✅ 한국어 query 결과 존재 (없으면 RSS 보강층 의존도 ↑)")
    print("  ⚠️  위기 query만 잘 잡고 평시 안 잡히면 시나리오 § 2 narrative 깨짐")


if __name__ == "__main__":
    main()
