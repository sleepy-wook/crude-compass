/**
 * SignalContribution — Phase 3 Discovery wow.
 *
 * 시나리오 §6.3 #2 anchor: "오늘 점수 82는 호르무즈 35%, 두바이 28%, 뉴스 톤 22%, EIA 15% 기여"
 *
 * 데이터 source: `gold.signal_contribution_30d` view (silver.signal_events_decayed 30일).
 * 라이브러리 0 — pure CSS bar (Tailwind width %).
 */
import { useSignalContribution } from "../lib/queries";

const SIGNAL_LABEL: Record<string, string> = {
  news_tone: "GDELT 뉴스 톤",
  ais_traffic: "AIS 호르무즈 트래픽",
  eia_inventory: "EIA 미국 재고",
  opec_momr: "OPEC MOMR",
  fx_krw_usd: "USD/KRW 환율",
  price_spike: "Oil price spike",
};

const DIRECTION_COLOR: Record<string, { fill: string; text: string; label: string }> = {
  bullish: { fill: "bg-crisis-500/80", text: "text-crisis-700", label: "위기" },
  bearish: { fill: "bg-opportunity-500/80", text: "text-opportunity-700", label: "약세" },
  neutral: { fill: "bg-ink-3/40", text: "text-ink-3", label: "—" },
};

export function SignalContribution() {
  const { data, isLoading, isError } = useSignalContribution();
  const items = data?.items ?? [];
  // 상위 6개 + share_pct 기준 정렬 (이미 backend ORDER BY ABS desc)
  const top = items.slice(0, 6);

  return (
    <section className="mb-8">
      <div className="flex items-baseline justify-between mb-3">
        <h2 className="font-display text-xl font-semibold tracking-tight">
          시그널 기여도 — 최근 30일
        </h2>
        <span className="text-[11px] text-ink-3 font-mono">
          gold.signal_contribution_30d
        </span>
      </div>
      <p className="text-xs text-ink-3 mb-4">
        Pattern Score를 끌어올린 source × direction 기여도. 시간 감쇠 적용된{" "}
        <code className="text-[11px]">weighted_contribution</code> 절댓값 share.
      </p>

      {isLoading && (
        <div className="space-y-2.5">
          {[0, 1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="h-7 rounded bg-line-1/40 animate-pulse"
            />
          ))}
        </div>
      )}

      {isError && (
        <div className="rounded-lg border border-line-1 bg-panel p-4 text-xs text-ink-3">
          시그널 기여도 일시 불가.
        </div>
      )}

      {!isLoading && !isError && top.length === 0 && (
        <div className="rounded-lg border border-line-1 bg-panel p-4 text-xs text-ink-3">
          최근 30일 시그널 누적 없음.
        </div>
      )}

      {!isLoading && !isError && top.length > 0 && (
        <div className="space-y-2.5">
          {top.map((item, idx) => {
            const label = SIGNAL_LABEL[item.signal_type] ?? item.signal_type;
            const dir = DIRECTION_COLOR[item.direction] ?? DIRECTION_COLOR.neutral;
            return (
              <div
                key={`${item.signal_type}-${item.direction}-${idx}`}
                className="flex items-center gap-3 text-xs"
              >
                {/* Label column */}
                <div className="w-44 shrink-0 flex items-center justify-between gap-2">
                  <span className="text-ink truncate" title={label}>
                    {label}
                  </span>
                  <span
                    className={`shrink-0 inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-medium border ${
                      item.direction === "bullish"
                        ? "bg-crisis-50 text-crisis-700 border-crisis-100"
                        : item.direction === "bearish"
                          ? "bg-opportunity-50 text-opportunity-700 border-opportunity-100"
                          : "bg-line-1 text-ink-3 border-line-2"
                    }`}
                  >
                    {dir.label}
                  </span>
                </div>
                {/* Bar */}
                <div className="flex-1 h-6 rounded bg-line-1/40 overflow-hidden relative">
                  <div
                    className={`h-full ${dir.fill} transition-all duration-500`}
                    style={{ width: `${Math.max(item.share_pct, 1.5)}%` }}
                  />
                  <span
                    className={`absolute inset-y-0 left-2 flex items-center text-[11px] font-mono ${dir.text}`}
                  >
                    {item.share_pct.toFixed(1)}%
                  </span>
                </div>
                {/* Sidecar — n signals */}
                <div className="w-16 text-right text-[11px] font-mono text-ink-3 shrink-0">
                  n={item.n_signals}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
