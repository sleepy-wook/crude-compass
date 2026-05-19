/**
 * MarketDataPage — /market (Market Watch)
 *
 * codex P0: data dashboard → Agent Bricks reasoning evidence board.
 * 각 chart 위에 "So what for current case?" sub-label 부착 — 단순 차트 전시가 아닌
 * Supervisor / Genie / Knowledge Assistant가 참조한 evidence 검증 surface로 reframe.
 *
 * D-2: daily chart 기간 toggle (7/30/90/180일) — 단기 변동 vs 중기 trend 양쪽 검증.
 */
import { useState } from "react";
import { Link } from "react-router-dom";
import { TimeHorizonBreakdown } from "../components/TimeHorizonBreakdown";
import { PatternScoreLine } from "../components/PatternScoreLine";
import { OpecCitation } from "../components/OpecCitation";
import { PriceLineChart } from "../components/PriceLineChart";
import { NewsTopList } from "../components/NewsTopList";
import { FxLineChart } from "../components/FxLineChart";
import { IntradayTicker } from "../components/IntradayTicker";
import { IntradayChart } from "../components/IntradayChart";
import { usePatternCurrent } from "../lib/queries";

type DailyRange = 7 | 30 | 90 | 180;

export function MarketDataPage() {
  const pattern = usePatternCurrent();
  const cur = pattern.data?.current ?? null;
  const [dailyDays, setDailyDays] = useState<DailyRange>(90);
  const score10 = cur?.pattern_score != null ? Math.round(cur.pattern_score / 10) : null;
  const mode =
    cur?.mission_type === "HEDGE"
      ? "위험방어"
      : cur?.mission_type === "OPPORTUNITY"
        ? "기회포착"
        : "관망";
  const modeColor =
    cur?.mission_type === "HEDGE"
      ? "text-crisis-700"
      : cur?.mission_type === "OPPORTUNITY"
        ? "text-opportunity-700"
        : "text-ink-2";

  return (
    <div className="max-w-7xl mx-auto px-8 py-10">
      <header className="mb-8 flex items-baseline justify-between flex-wrap gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-3 mb-1.5">Market Watch</div>
          <h1 className="font-display text-[28px] md:text-[32px] font-semibold tracking-tight text-ink-1 leading-tight">
            Agent Bricks 근거판 — 현재 case 검증
          </h1>
          <p className="text-[13px] text-ink-3 mt-2 leading-relaxed">
            Supervisor가 참조한 원천 데이터. Genie · Knowledge Assistant · UC Function이 어떤 evidence를
            본 후 case를 운영하는지 검증할 수 있는 surface.
          </p>
        </div>
        {/* 종합 한 줄 — 카드 X, 헤더 우측 inline */}
        <div className="text-[12px] text-ink-2 flex items-center gap-2">
          <span className="text-ink-3">90일 시그널</span>
          <span className="font-medium text-ink-1 tabular-nums">
            {cur?.signal_count_90d?.toLocaleString() ?? "—"}
          </span>
          <span className="text-ink-3">→</span>
          <span className={`font-display font-semibold ${modeColor}`}>
            {mode} {score10 ?? "—"}/10
          </span>
        </div>
      </header>

      {/* Intraday 5분 — Reactive trigger surface */}
      <SoWhat
        actor="Reactive Trigger"
        text="Brent/WTI/Dubai 5분 spike → case 재평가 자동 trigger"
      />
      <IntradayTicker />
      <IntradayChart hours={24} />

      {/* Price + FX (daily) — Genie evidence */}
      <SectionHeader
        title="Structured market evidence"
        subtitle="Genie가 참조하는 구조화 데이터 — 가격 추세 + 환율 비용 압력"
      />
      <SoWhat
        actor="Genie"
        text={`가격 trend (${dailyDays}일) + USD/KRW 환율 → Mission Plan UC Function의 target_pct 계산 input`}
      />
      {/* Daily range toggle — 7/30/90/180일 */}
      <div className="flex items-center gap-1.5 mb-4 text-[11px]">
        <span className="text-ink-3 uppercase tracking-wider mr-1">기간</span>
        {([7, 30, 90, 180] as DailyRange[]).map((d) => (
          <button
            key={d}
            type="button"
            onClick={() => setDailyDays(d)}
            className={
              dailyDays === d
                ? "px-2.5 py-1 rounded bg-ink-1 text-paper font-medium"
                : "px-2.5 py-1 rounded text-ink-3 hover:text-ink-1 hover:bg-line-1 border border-line-2"
            }
          >
            {d}일
          </button>
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <PriceLineChart days={dailyDays} />
        <FxLineChart days={dailyDays} />
      </div>

      {/* OPEC + News — Knowledge Assistant + GDELT evidence */}
      <SectionHeader
        title="Document & event evidence"
        subtitle="Knowledge Assistant (OPEC MOMR PDF) + GDELT 키워드 burst (leading signal)"
      />
      <SoWhat
        actor="Knowledge Assistant"
        text="MOMR PDF: 사우디 공급 / 수요 전망 / market balance. GDELT: 호르무즈·이란 키워드 burst (D-7 leading)"
      />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-3">
        <OpecCitation />
        <NewsTopList limit={5} />
      </div>
      <div className="mb-10 text-right">
        <Link
          to="/evidence"
          className="text-[12px] text-ink-2 hover:text-ink-1 underline underline-offset-2 decoration-line-2 hover:decoration-ink-2"
        >
          OPEC + 주요 보도 게시판 자세히 보기 →
        </Link>
      </div>

      {/* Long-term timeline */}
      <SectionHeader title="위기 신호 점수 7년 시계열" subtitle="1년 1-2회 위기 · 분기 1-2회 기회 — 현재 case의 과거 위치" />
      <SoWhat
        actor="weighted_signal (UC Function)"
        text="양방향 시간 감쇠 score 계산 — 90일 window. backtest 75% hit rate 검증된 동일 함수"
      />
      <div className="mb-10">
        <PatternScoreLine days={2200} variant="long" />
      </div>

      {/* Time-horizon breakdown */}
      <SectionHeader title="시간 지평별 시그널" subtitle="선행 (D-7) · 구조 (D-30) · 확인 (D-1)" />
      <SoWhat
        actor="Supervisor"
        text="3개 lead time category 통합 — leading + structural + fundamentals 일치할 때 confidence ↑"
      />
      <TimeHorizonBreakdown />

      <div className="h-20" />
    </div>
  );
}

function SectionHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="mt-16 mb-6 pb-4 border-b border-line-1">
      <h2 className="font-display text-xl font-semibold text-ink-1 tracking-tight mb-0.5">
        {title}
      </h2>
      <p className="text-xs text-ink-3">{subtitle}</p>
    </div>
  );
}

/** "So what for current case?" — 각 section의 reasoning relevance 1줄. */
function SoWhat({ actor, text }: { actor: string; text: string }) {
  return (
    <div className="mb-3 px-3 py-2 rounded-md bg-line-1/30 border-l-2 border-ink-3 flex items-baseline gap-2 flex-wrap">
      <span className="text-[10px] uppercase tracking-wider text-ink-3 font-medium shrink-0">
        {actor} 참조
      </span>
      <span className="text-[12px] text-ink-2 leading-snug">{text}</span>
    </div>
  );
}
