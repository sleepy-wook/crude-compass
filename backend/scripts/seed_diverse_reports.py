"""Demo seed — 다양한 시장 상황 + recommendation vocabulary 시범 보고서.

현재 Lakebase 상태는 HEDGE zone (pattern_score 100)에서 만들어진 DEFER SPOT 보고서만 있음.
demo 시 매니저에게 "AI가 시장 상황 따라 다른 권고도 한다"는 인상을 주기 위해
5종 시나리오로 inject:

  1. HEDGE 시나리오 (현재 시점) — DEFER SPOT
  2. OPPORTUNITY 시나리오 (지난주 가상) — ACCELERATE SPOT
  3. REVIEW TERM 시나리오 (10일 전) — REVIEW TERM
  4. HEDGE 강화 시나리오 (2주 전) — HEDGE
  5. STABLE 시나리오 (3주 전) — HOLD

각 시나리오는 LLM 호출 안 하고 사전 작성된 보고서 직접 INSERT (1) demo seeding이라 빠름
(2) 결과가 deterministic해야 매번 같은 demo flow 가능.

실행:
  cd backend
  uv run python scripts/seed_diverse_reports.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Make app/ importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.lakebase import acquire
from app.db.repositories import reports as reports_repo
from app.schemas.report import Recommendation, ReportCreate, ReportStatus, StatusActor, TriggerType


NOW = datetime.now(timezone.utc)


SEED_REPORTS = [
    # 1. ACCELERATE SPOT (5일 전, kept) — 가격 약세 + 휴전 협상 시그널
    {
        "days_ago": 5,
        "status": ReportStatus.KEPT,
        "trigger_type": TriggerType.GDELT_SIGNAL,
        "fingerprint": "seed:ceasefire_signal",
        "headline": "휴전 협상 진전 보도 — 단기 약세 압력, 현물 매수 기회",
        "summary": "이스라엘-하마스 휴전 협상 진전 보도 2건 동시 감지 (강도 7-8/10). 두바이유 7일간 -3.4% 하락 중. 단기 약세 압력 누적으로 현물 매수 기회 윈도우 형성.",
        "reasoning": {
            "key_signals": [
                "휴전 협상 진전 보도 2건 — 안정 신호 매우 강함 (강도 7-8)",
                "두바이유 7일 누적 -3.4% 하락 — 약세 추세 확인",
                "안정 신호가 위험 신호보다 약 1.8배 우세 (90일 누적)",
            ],
            "logic": "지정학 긴장 완화 신호가 다발로 잡히면서 단기 약세 압력이 형성됨. 두바이유 가격 하락이 이를 확인. Term 비중은 60%로 충분히 안정적이고, Spot 발주를 평소보다 앞당기면 평균 매수가 인하 효과 기대.",
            "risk_factors": [
                "휴전 협상 결렬 시 가격 반등 가능성",
                "OPEC 추가 감산 발표 시 약세 무효화",
            ],
            "recommendation_text": "이번 주 Spot 발주 1주 앞당김 권고. 평소 대비 3-5% 낮은 평균가 확보 가능.",
        },
        "recommendation": Recommendation.ACCELERATE_SPOT,
        "related_signals": [
            {"title": "Israel Hamas Ceasefire Progress Reuters", "source": "GDELT", "direction": "bearish", "importance": 82},
            {"title": "Hostage Deal Framework Talks AP", "source": "GDELT", "direction": "bearish", "importance": 77},
        ],
    },
    # 2. REVIEW TERM (10일 전, kept) — Aramco OSP 인상 + 사우디 감산
    {
        "days_ago": 10,
        "status": ReportStatus.KEPT,
        "trigger_type": TriggerType.PATTERN_DRIFT,
        "fingerprint": "seed:saudi_term_premium",
        "headline": "Aramco OSP 인상 + 사우디 추가 감산 — 다음 분기 Term 재검토 필요",
        "summary": "사우디 Aramco 6월 아시아향 OSP $0.50/bbl 인상 발표. OPEC MOMR 5월 보고서에서 사우디 추가 감산 시그널. Term 비중이 사우디 의존 70% 구조라 다음 분기 portfolio 재조정 검토 시점.",
        "reasoning": {
            "key_signals": [
                "Aramco OSP 인상 발표 — Term 가격 직접 영향",
                "OPEC MOMR 사우디 감산 시그널 — 공급 타이트닝 신호",
                "Brent-Dubai spread 정상 범위 ($4-5) — 아시아 프리미엄 정상화",
            ],
            "logic": "사우디 OSP 인상은 향후 3개월 Term 매입가에 직접 반영됨. 현재 Term 비중이 사우디 70%에 편중되어 있어 spread 위험. UAE ADNOC, 미국 WTI 등 비-사우디 supplier로 다변화 검토가 다음 분기 안건으로 적합.",
            "risk_factors": [
                "ADNOC OSP도 동반 인상 시 다변화 효과 제한",
                "사우디 외교 관계 악화 시 보복 감산 가능성",
            ],
            "recommendation_text": "Term 비중 자체는 유지 (60%). 다음 분기 OSP cycle 회의 안건으로 사우디 의존도 ↓ 검토 권고.",
        },
        "recommendation": Recommendation.REVIEW_TERM,
        "related_signals": [
            {"title": "Saudi Aramco OSP June Asia Premium", "source": "GDELT", "direction": "bullish", "importance": 88},
            {"title": "OPEC MOMR May Saudi Production Cut Signal", "source": "OPEC", "direction": "bullish", "importance": 75},
        ],
    },
    # 3. HEDGE (15일 전, kept) — 호르무즈 위협 + 이란 도발
    {
        "days_ago": 15,
        "status": ReportStatus.KEPT,
        "trigger_type": TriggerType.GDELT_SIGNAL,
        "fingerprint": "seed:hormuz_threat",
        "headline": "호르무즈 해상 경보 + 이란 IRGC 강경 발언 — 봉쇄 가능성 대비",
        "summary": "이란 IRGC 호르무즈 해협 군사 행동 위협 발언 + UK 해군 호르무즈 통과 선박 경보 발표. 두바이유 3일간 +6.8% 급등. 봉쇄 발발 시 한국 수입 60% 차단 위험.",
        "reasoning": {
            "key_signals": [
                "이란 IRGC 호르무즈 군사 행동 위협 — 위험 신호 최고 강도",
                "UK 해군 호르무즈 통과 경보 — 동맹국 confirm",
                "VLCC 운임 +12% — 시장 봉쇄 시나리오 가격 반영 시작",
            ],
            "logic": "지난 10년간 호르무즈 봉쇄 위협 7회 중 실제 봉쇄 0회. 그러나 7회 모두 6주 평균 두바이유 +18% 상승. 봉쇄 안 일어나도 spike 손실 발생. Term 비중을 미리 락하지 않으면 가격 폭등기에 강제 매수.",
            "risk_factors": [
                "외교 중재 성공 시 가격 급락 — over-hedge 위험",
                "한미일 함대 추가 배치 시 도발 escalation",
            ],
            "recommendation_text": "Term 비중 60% → 65-70% 인상 검토 (다음 OSP cycle). UAE Murban, 미국 WTI 비중 ↑로 호르무즈 우회.",
        },
        "recommendation": Recommendation.HEDGE,
        "related_signals": [
            {"title": "IRGC Hormuz Strait Military Threat", "source": "GDELT", "direction": "bullish", "importance": 92},
            {"title": "UK Navy Hormuz Passage Alert Vessels", "source": "GDELT", "direction": "bullish", "importance": 85},
        ],
    },
    # 4. HOLD (3일 전, kept) — 평시, 큰 변동 없음
    {
        "days_ago": 3,
        "status": ReportStatus.KEPT,
        "trigger_type": TriggerType.PRICE_SPIKE,
        "fingerprint": "seed:hold_minor_spike",
        "headline": "두바이유 단기 -2.1% 조정 — 미국 재고 발표 영향, 추세 전환 아님",
        "summary": "EIA 미국 주간 원유 재고 +400만 배럴 발표 (예상 -200만 배럴 대비 surprise). 두바이유 24h -2.1% 조정. 단발 데이터 영향이며 90일 위험 지수 추세는 안정 구간 유지.",
        "reasoning": {
            "key_signals": [
                "EIA 미국 원유 재고 +400만 배럴 — 단기 약세 요인",
                "90일 누적 위험 지수 안정 구간 유지 — 추세 변화 아님",
                "Brent-Dubai spread $4.2 — 정상 범위",
            ],
            "logic": "단발 재고 데이터로 인한 일시 조정. 지난 30일 비슷한 -2~3% 조정 4회 발생했으나 모두 5일 내 회복. Term/Spot 비중 변경 사유 없음. 정상 cycle 유지.",
            "risk_factors": [
                "다음 주 EIA 재고도 surprise하면 추세 전환 신호",
            ],
            "recommendation_text": "현 portfolio 유지 (Term 60% / Spot 40%). 다음 주 EIA 재고 발표 추가 확인.",
        },
        "recommendation": Recommendation.HOLD,
        "related_signals": [
            {"title": "EIA Weekly Crude Inventory +4M Surprise Build", "source": "EIA", "direction": "bearish", "importance": 62},
        ],
    },
    # 5. DIVERSIFY (8일 전, kept) — 사우디 정정 불안
    {
        "days_ago": 8,
        "status": ReportStatus.KEPT,
        "trigger_type": TriggerType.GDELT_SIGNAL,
        "fingerprint": "seed:saudi_political_risk",
        "headline": "사우디 왕실 내부 갈등 보도 — supplier 다변화 검토 시점",
        "summary": "사우디 왕실 내부 후계 갈등 보도 3건 (Reuters / Bloomberg / WSJ 동시 confirm). 정치 리스크는 누적 신호. Term 70% 사우디 의존 구조 재검토 필요.",
        "reasoning": {
            "key_signals": [
                "사우디 왕실 후계 갈등 — Reuters/Bloomberg/WSJ 3 source confirm",
                "사우디 5y CDS 스프레드 +18bp — 시장 정치 리스크 반영 시작",
                "지난 6개월 사우디 외교 관계 변동 4건 누적",
            ],
            "logic": "사우디 정치 리스크는 봉쇄/감산 같은 직접 충격보다 천천히 누적되는 시그널. 단기에 가격 영향 미미하나, Term contract 락-인 portfolio는 정치 충격 시 회피 옵션 X. UAE / 미국 / 카자흐 등 비-사우디 supplier 다변화 검토가 다음 분기 안건.",
            "risk_factors": [
                "후계 갈등 실제 정변으로 발전 시 단기 spike",
                "사우디 외교 정상화 시 다변화 oversteering 위험",
            ],
            "recommendation_text": "Term 사우디 비중 70% → 55% 다단계 감축 검토 (3분기 OSP cycle). UAE ADNOC / 미국 WTI / 카자흐 CPC 각 +5%p 권고.",
        },
        "recommendation": Recommendation.DIVERSIFY,
        "related_signals": [
            {"title": "Saudi Royal Family Succession Tension Reuters", "source": "GDELT", "direction": "bullish", "importance": 78},
            {"title": "Saudi 5Y CDS Spread Widens Bloomberg", "source": "GDELT", "direction": "bullish", "importance": 71},
        ],
    },
]


def seed():
    inserted_ids = []
    with acquire() as conn:
        for s in SEED_REPORTS:
            payload = ReportCreate(
                trigger_type=s["trigger_type"],
                trigger_meta={"fingerprint": s["fingerprint"], "seed": True},
                headline=s["headline"],
                summary=s["summary"],
                reasoning=s["reasoning"],
                recommendation=s["recommendation"],
                related_signals=s["related_signals"],
            )
            rid = reports_repo.insert_report(conn, payload)
            conn.commit()

            # 과거 시점으로 created_at + status_changed_at 조정 (demo timeline 자연스럽게)
            days = s["days_ago"]
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE reports
                       SET created_at = NOW() - (%s::int * INTERVAL '1 day'),
                           status = %s,
                           status_changed_at = NOW() - ((%s::int - 1) * INTERVAL '1 day'),
                           status_changed_by = 'manager'
                     WHERE report_id = %s
                    """,
                    (days, s["status"].value, days, rid),
                )
            conn.commit()
            inserted_ids.append((rid, s["recommendation"].value, s["headline"][:50]))
            print(f"  {days:>3}d ago — {s['recommendation'].value:<16} — {s['headline'][:60]}")

    print(f"\n{len(inserted_ids)} seed reports inserted.")


if __name__ == "__main__":
    seed()
