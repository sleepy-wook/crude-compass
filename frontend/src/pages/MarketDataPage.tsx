/**
 * MarketDataPage — /market (Market Watch).
 *
 * 2026-05-21 전면 재구성:
 *   - "Agent Bricks 근거판" reframe + SoWhat 배너 제거
 *   - 단순 데이터 차트 보드로 reset
 *   - OPEC + 뉴스 → 자료실(/library)로 이전
 *   - Intraday 2 카드 → 1 카드 병합 (Ticker는 차트 header strip으로 흡수)
 *
 * Layout (top-down 단일 컬럼):
 *   [Header — Market Watch + global 기간 toggle (7/30/90/180/1y)]
 *   [Section 1: 위기 신호 점수 timeline (long-term reference, 풀폭)]
 *   [Section 2: 유가 daily (Dubai/Brent/WTI)]
 *   [Section 3: 단기 변동 24h intraday]
 *   [Section 4: USD/KRW 환율]
 */
import { PatternScoreLine } from "../components/PatternScoreLine";
import { PriceLineChart } from "../components/PriceLineChart";
import { FxLineChart } from "../components/FxLineChart";
import { IntradaySection } from "../components/IntradaySection";
import { cn } from "../lib/utils";

export function MarketDataPage() {
  return (
    <div className="max-w-7xl mx-auto px-8 py-10">
      <header className="mb-8">
        <div className="text-[11px] uppercase tracking-[0.2em] text-ink-3 mb-1.5">
          Market Watch
        </div>
        <h1 className="font-display text-[28px] md:text-[32px] font-semibold tracking-tight text-ink-1 leading-tight">
          시장 데이터 추세
        </h1>
        <p className="text-[13px] text-ink-3 mt-2 leading-relaxed">
          유가 · 환율 · 위기 신호 점수 — 일별/단기 차트.
          각 차트 우상단에서 기간을 자유롭게 변경할 수 있습니다.
          OPEC 월간 보고서와 주요 보도는{" "}
          <span className="text-ink-2 font-medium">자료실</span>에서 확인.
        </p>
      </header>

      {/* Section 1: 위기 신호 점수 (long-term, fixed 6y) */}
      <Section
        title="위기 신호 점수"
        subtitle="90일 누적 위험 지수 · 6년 시계열 · 1년 1-2회 위기, 분기 1-2회 기회"
        accent
      >
        <PatternScoreLine days={2200} variant="long" hideTitle />
      </Section>

      {/* Section 2: 유가 */}
      <Section
        title="유가"
        subtitle="Dubai · Brent · WTI 일별"
      >
        <PriceLineChart days={90} />
      </Section>

      {/* Section 3: 단기 변동 24h intraday */}
      <Section
        title="단기 변동 (24h)"
        subtitle="5분 spike · ±2% 시 자동 trigger"
      >
        <IntradaySection hours={24} />
      </Section>

      {/* Section 4: USD/KRW */}
      <Section
        title="USD/KRW 환율"
        subtitle="원유 매입 원가 압력 — 환율 변동성"
      >
        <FxLineChart days={90} />
      </Section>

      <div className="h-12" />
    </div>
  );
}

/**
 * Section wrapper — 일관된 visual rhythm + optional accent (primary section 강조).
 */
function Section({
  title,
  subtitle,
  accent,
  children,
}: {
  title: string;
  subtitle: string;
  accent?: boolean;
  children: React.ReactNode;
}) {
  return (
    <section className="mb-10">
      <header
        className={cn(
          "mb-4 pb-3 border-b",
          accent ? "border-ink-1/30" : "border-line-1",
        )}
      >
        <div className="flex items-baseline gap-3">
          {accent && (
            <span className="w-1 h-4 rounded-sm bg-ink-1 self-center" aria-hidden />
          )}
          <h2 className="font-display text-lg font-semibold text-ink-1 tracking-tight">
            {title}
          </h2>
          <p className="text-[11.5px] text-ink-3">{subtitle}</p>
        </div>
      </header>
      {children}
    </section>
  );
}
