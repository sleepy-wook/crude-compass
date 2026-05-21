/**
 * IntradaySection — 24h 단기 변동 통합 카드 (2026-05-21).
 *
 * 기존 IntradayTicker + IntradayChart를 하나의 시각 단위로 흡수:
 *   - 상단 strip: 3 ticker compact (Dubai/Brent/WTI, 가격 + 30분/24h delta)
 *   - 하단: 24h 차트 (3 ticker overlay)
 *
 * Market Watch에서 단일 카드로 노출. 데이터 없으면 null hide.
 */
import { useIntradayPrices, useIntradaySummary } from "../lib/queries";
import { IntradayChart } from "./IntradayChart";

interface Props {
  hours?: number;
}

const TICKER_LABEL: Record<string, string> = {
  dubai: "Dubai",
  brent: "Brent",
  wti: "WTI",
};

function fmtPct(p: number | null | undefined): string {
  if (p == null) return "—";
  const sign = p > 0 ? "+" : "";
  return `${sign}${p.toFixed(2)}%`;
}

function pctColor(p: number | null | undefined): string {
  if (p == null || p === 0) return "text-ink-3";
  return p > 0 ? "text-crisis-700" : "text-opportunity-700";
}

function relTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    const then = new Date(iso).getTime();
    const diff = Date.now() - then;
    const mins = Math.floor(diff / 60_000);
    if (mins < 1) return "방금";
    if (mins < 60) return `${mins}분 전`;
    const hours = Math.floor(mins / 60);
    return `${hours}시간 전`;
  } catch {
    return "—";
  }
}

export function IntradaySection({ hours = 24 }: Props) {
  const summary = useIntradaySummary();
  const prices = useIntradayPrices(hours);
  const tickers = summary.data?.tickers ?? [];

  // 데이터 모두 비어있을 때 (cron 미작동) → null hide
  const summaryEmpty = !summary.isLoading && (summary.isError || tickers.length === 0);
  const pricesEmpty = !prices.isLoading && (prices.isError || !prices.data?.series?.length);
  if (summaryEmpty && pricesEmpty) {
    return null;
  }

  return (
    <section className="bg-panel border border-line-1 rounded-xl overflow-hidden">
      {/* Header strip — Ticker 3 카드 + 갱신 시각 */}
      <header className="px-5 pt-4 pb-3 border-b border-line-1">
        <div className="flex items-baseline justify-between mb-3">
          <div className="flex items-baseline gap-2">
            <span className="text-[11px] uppercase tracking-wider text-ink-3">
              OilPriceAPI · 30분 단위
            </span>
          </div>
          <span className="text-[10px] text-ink-3 italic">
            {tickers[0]?.fetched_at
              ? `${relTime(tickers[0].fetched_at)} 갱신`
              : "—"}
          </span>
        </div>

        {summary.isLoading ? (
          <div className="grid grid-cols-3 gap-3">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-14 rounded bg-line-1/40 animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {tickers.map((t) => (
              <div
                key={t.ticker}
                className="rounded-lg border border-line-1 bg-paper/60 px-3 py-2"
              >
                <div className="flex items-baseline justify-between mb-0.5">
                  <span className="text-[10px] uppercase tracking-wider text-ink-3">
                    {TICKER_LABEL[t.ticker] ?? t.ticker.toUpperCase()}
                  </span>
                </div>
                <div className="flex items-baseline gap-2.5 tabular-nums">
                  <span className="font-display text-lg font-semibold text-ink-1">
                    ${t.price_usd?.toFixed(2) ?? "—"}
                  </span>
                  <span className={`text-[11px] font-medium ${pctColor(t.delta_24h_pct)}`}>
                    {fmtPct(t.delta_24h_pct)}
                  </span>
                  <span className="text-[10px] text-ink-3">24h</span>
                  {t.biggest_spike_pct != null && Math.abs(t.biggest_spike_pct) >= 2 && (
                    <span className={`text-[10px] font-medium ml-auto ${pctColor(t.biggest_spike_pct)}`}>
                      ⚡ {fmtPct(t.biggest_spike_pct)}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </header>

      {/* Body — 24h 차트 */}
      <div className="px-5 py-4">
        <IntradayChart hours={hours} />
      </div>
    </section>
  );
}
