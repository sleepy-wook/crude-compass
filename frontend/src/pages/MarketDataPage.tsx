/**
 * MarketDataPage — /market
 *
 * 시장 데이터 종합: 가격 · 환율 · 공급 · 뉴스 + 시그널 분석 + 장기 시계열.
 * Dashboard에서 옮긴 차트/breakdown 컴포넌트를 한 곳에 모음.
 */
import { TimeHorizonBreakdown } from "../components/TimeHorizonBreakdown";
import { PatternScoreLine } from "../components/PatternScoreLine";
import { OpecCitation } from "../components/OpecCitation";
import { PriceLineChart } from "../components/PriceLineChart";
import { NewsTopList } from "../components/NewsTopList";
import { FxLineChart } from "../components/FxLineChart";
import { IntradayTicker } from "../components/IntradayTicker";
import { IntradayChart } from "../components/IntradayChart";
import { usePatternCurrent } from "../lib/queries";

export function MarketDataPage() {
  const pattern = usePatternCurrent();
  const cur = pattern.data?.current ?? null;
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
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-3 mb-1.5">시장 데이터</div>
          <h1 className="font-display text-[28px] md:text-[32px] font-semibold tracking-tight text-ink-1 leading-tight">
            가격 · 환율 · 공급 · 뉴스
          </h1>
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

      {/* Intraday 5분 — ticker + chart 통합 한 묶음 */}
      <IntradayTicker />
      <IntradayChart hours={24} />

      {/* Price + FX (daily) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <PriceLineChart days={90} />
        <FxLineChart days={90} />
      </div>

      {/* OPEC + News */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-10">
        <OpecCitation />
        <NewsTopList limit={5} />
      </div>

      {/* Long-term timeline */}
      <SectionHeader title="6년 시계열" subtitle="1년 1-2 위기 · 분기 1-2 기회" />
      <div className="mb-10">
        <PatternScoreLine days={2200} variant="long" />
      </div>

      {/* Time-horizon breakdown */}
      <SectionHeader title="시간 지평별 시그널" subtitle="선행 · 구조 · 확인" />
      <TimeHorizonBreakdown />

      <div className="h-20" />
    </div>
  );
}

function SectionHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="mt-12 mb-6 pb-4 border-b border-line-1">
      <h2 className="font-display text-xl font-semibold text-ink-1 tracking-tight mb-0.5">
        {title}
      </h2>
      <p className="text-xs text-ink-3">{subtitle}</p>
    </div>
  );
}
