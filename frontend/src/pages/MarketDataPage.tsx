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
      <header className="mb-8">
        <div className="text-[11px] uppercase tracking-[0.2em] text-ink-3 mb-2">시장 데이터</div>
        <h1 className="font-display text-[28px] md:text-[32px] font-semibold tracking-tight text-ink-1 mb-3 leading-tight">
          가격 · 환율 · 공급 · 뉴스
        </h1>
        <p className="text-sm text-ink-2 leading-relaxed max-w-2xl">
          공개 데이터 6 source에서 수집한 시장 신호 종합 — 두바이/Brent/WTI 가격, USD/KRW 환율,
          OPEC 월간 보고서, 글로벌 뉴스 톤.
        </p>
      </header>

      {/* 종합 narrative bar — 4 카드 + 시계열 + 시간 지평이 어떻게 종합되는지 한 줄 결론 */}
      <div className="mb-10 bg-panel border border-line-1 rounded-xl p-5 flex flex-wrap items-baseline gap-x-6 gap-y-2">
        <div className="text-[11px] uppercase tracking-wider text-ink-3 w-full sm:w-auto">
          오늘 4 source 종합
        </div>
        <div className="text-[13px] text-ink-2 leading-relaxed flex-1 min-w-0">
          가격·환율·OPEC·뉴스 4 카드 + GDELT 90일 누적 시그널{" "}
          <span className="font-medium text-ink-1 tabular-nums">
            {cur?.signal_count_90d?.toLocaleString() ?? "—"}건
          </span>
          이 한 점수로 합쳐져{" "}
          <span className={`font-display font-semibold ${modeColor}`}>
            위기 강도 {score10 ?? "—"}/10 · {mode}
          </span>{" "}
          → AI는 이 종합 신호를 Mission Plan Agent에 전달해 권고를 만듭니다.
        </div>
      </div>

      {/* Intraday 5분 ticker — OilPriceAPI bronze 데이터 활용 */}
      <IntradayTicker />

      {/* Price + FX */}
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
      <SectionHeader
        title="6년 시계열"
        subtitle="1년 1-2 위기 + 분기 1-2 기회 + 매주 미세 조정"
      />
      <div className="mb-10">
        <PatternScoreLine days={2200} variant="long" />
      </div>

      {/* Time-horizon breakdown */}
      <SectionHeader
        title="시간 지평별 시그널 기여도"
        subtitle="선행 · 구조 · 확인 — 어느 시간대 신호인지에 따라 의미가 다릅니다"
      />
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
