/**
 * IntradayTicker — OilPriceAPI 5분 데이터 ticker (D-3 추가).
 *
 * 시나리오 §7: Dubai/Brent/WTI intraday 변동 + 24h spike.
 * /market 페이지 Price chart 옆 또는 / Dashboard 상단에 small ticker.
 */
import { useIntradaySummary } from "../lib/queries";

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

export function IntradayTicker() {
  const { data, isLoading, isError } = useIntradaySummary();
  const tickers = data?.tickers ?? [];

  // 데이터 없거나 fetch 실패 시 컴포넌트 자체 hide — demo에서 empty card 노출 방지.
  // bronze.oil_prices 적재 cron 정상화되면 자동 표시.
  if (!isLoading && (isError || tickers.length === 0)) {
    return null;
  }

  return (
    <section className="bg-panel border border-line-1 rounded-xl p-5 mb-6">
      <div className="flex items-baseline justify-between mb-3">
        <div className="flex items-baseline gap-2">
          <h3 className="font-display text-sm font-semibold text-ink-1">
            Intraday 시세
          </h3>
          <span className="text-[10px] uppercase tracking-wider text-ink-3">
            OilPriceAPI · 5분 단위
          </span>
        </div>
        <span className="text-[10px] text-ink-3 italic">
          {tickers[0]?.fetched_at
            ? `${relTime(tickers[0].fetched_at)} 갱신`
            : "—"}
        </span>
      </div>

      {isLoading && (
        <div className="grid grid-cols-3 gap-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-16 rounded bg-line-1/40 animate-pulse" />
          ))}
        </div>
      )}

      {!isLoading && tickers.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {tickers.map((t) => (
            <div
              key={t.ticker}
              className="rounded-lg border border-line-1 bg-paper/60 p-3"
            >
              <div className="flex items-baseline justify-between mb-1">
                <span className="text-[11px] uppercase tracking-wider text-ink-3">
                  {TICKER_LABEL[t.ticker] ?? t.ticker.toUpperCase()}
                </span>
                <span className="text-[10px] text-ink-3 tabular-nums">
                  n={t.sample_count}
                </span>
              </div>
              <div className="font-display text-xl font-semibold text-ink-1 tabular-nums mb-2">
                ${t.price_usd?.toFixed(2) ?? "—"}
              </div>
              <div className="flex items-baseline gap-3 text-[11px] tabular-nums">
                <div>
                  <span className="text-ink-3 mr-1">30분</span>
                  <span className={pctColor(t.delta_30min_pct)}>
                    {fmtPct(t.delta_30min_pct)}
                  </span>
                </div>
                <div>
                  <span className="text-ink-3 mr-1">24h</span>
                  <span className={pctColor(t.delta_24h_pct)}>
                    {fmtPct(t.delta_24h_pct)}
                  </span>
                </div>
              </div>
              {t.biggest_spike_pct != null && Math.abs(t.biggest_spike_pct) >= 1 && (
                <div className="text-[10px] text-ink-3 mt-2 pt-2 border-t border-line-1">
                  최근 spike{" "}
                  <span className={`${pctColor(t.biggest_spike_pct)} font-medium`}>
                    {fmtPct(t.biggest_spike_pct)}
                  </span>
                  {t.biggest_spike_at && (
                    <span className="ml-1.5 italic">· {relTime(t.biggest_spike_at)}</span>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
