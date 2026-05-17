/**
 * OpecCitation — Document Intelligence wow (시나리오 §9.6).
 *
 * OPEC MOMR PDF → ai_parse_document() SQL 한 줄 파싱 → bronze.opec_momr_parsed →
 * gold.opec_demand_gap view → 이 badge가 노출.
 *
 * 평가위원 narrator: "OPEC MOMR 5월 사우디 감산 시그널을 PDF에서 직접 파싱."
 */
import { useOpecLatest } from "../lib/queries";

function formatKbbl(v: number | null | undefined): string {
  if (v == null) return "—";
  return `${(v / 1000).toFixed(1)}M b/d`;
}

const BALANCE_LABEL: Record<string, string> = {
  oversupply: "공급 과잉",
  undersupply: "공급 부족",
  balanced: "균형",
};

export function OpecCitation() {
  const { data, isLoading, isError } = useOpecLatest();
  const latest = data?.latest;

  return (
    <section className="mb-6">
      <div className="flex items-baseline justify-between mb-3">
        <h2 className="font-display text-base font-semibold tracking-tight">
          OPEC MOMR — Document Intelligence 결과
        </h2>
        <span className="text-[11px] text-ink-3 font-mono">
          ai_parse_document() · monthly PDF
        </span>
      </div>

      {isLoading && (
        <div className="rounded-lg border border-line-1 bg-panel p-4 h-24 animate-pulse" />
      )}

      {isError && (
        <div className="rounded-lg border border-line-1 bg-panel p-4 text-xs text-ink-3">
          OPEC MOMR 데이터 일시 불가.
        </div>
      )}

      {!isLoading && !isError && !latest && (
        <div className="rounded-lg border border-line-1 bg-panel p-4 text-xs text-ink-3">
          OPEC MOMR 적재 데이터 없음.
        </div>
      )}

      {!isLoading && !isError && latest && (
        <div className="rounded-xl border border-line-1 bg-panel p-4">
          <div className="flex items-center gap-3 mb-3 flex-wrap">
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] border bg-ink/5 text-ink-2 border-line-2 font-mono">
              MOMR {latest.report_month}
            </span>
            {latest.market_balance && (
              <span
                className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] border font-medium ${
                  latest.market_balance === "undersupply"
                    ? "bg-crisis-50 text-crisis-700 border-crisis-100"
                    : latest.market_balance === "oversupply"
                      ? "bg-opportunity-50 text-opportunity-700 border-opportunity-100"
                      : "bg-line-1 text-ink-3 border-line-2"
                }`}
              >
                {BALANCE_LABEL[latest.market_balance] ?? latest.market_balance}
              </span>
            )}
            {(() => {
              // 최신 보고서 vs 현재 달 lag — 2개월+ 이상이면 disclosure
              const m = latest.report_month?.slice(0, 7);
              if (!m) return null;
              const [y, mm] = m.split("-").map(Number);
              const now = new Date();
              const lag = (now.getFullYear() - y) * 12 + (now.getMonth() + 1 - mm);
              if (lag >= 2) {
                return (
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] border bg-line-1 text-ink-3 border-line-2 font-mono">
                    최신 보고서 {lag}개월 lag · 4월 미수집 (anti-bot)
                  </span>
                );
              }
              return null;
            })()}
            <span className="text-[10px] text-ink-3 font-mono">
              {data?.source ?? "PDF parsed"}
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div>
              <div className="text-[10px] uppercase tracking-widest text-ink-3 mb-1">
                사우디 생산
              </div>
              <div className="font-display text-lg font-semibold">
                {formatKbbl(latest.saudi_kbbl_d)}
              </div>
              {latest.saudi_delta_vs_prev != null && (
                <div
                  className={`text-[11px] font-mono ${
                    latest.saudi_delta_vs_prev > 0
                      ? "text-opportunity-700"
                      : latest.saudi_delta_vs_prev < 0
                        ? "text-crisis-700"
                        : "text-ink-3"
                  }`}
                >
                  {latest.saudi_delta_vs_prev > 0 ? "+" : ""}
                  {latest.saudi_delta_vs_prev.toFixed(0)} kb/d (M/M)
                </div>
              )}
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-widest text-ink-3 mb-1">
                이란 생산
              </div>
              <div className="font-display text-lg font-semibold">
                {formatKbbl(latest.iran_kbbl_d)}
              </div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-widest text-ink-3 mb-1">
                OPEC 총공급
              </div>
              <div className="font-display text-lg font-semibold">
                {formatKbbl(latest.opec_total_kbbl_d)}
              </div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-widest text-ink-3 mb-1">
                예상 수요
              </div>
              <div className="font-display text-lg font-semibold">
                {formatKbbl(latest.forecast_demand_kbbl_d)}
              </div>
              {latest.supply_demand_gap_kbbl_d != null && (
                <div className="text-[11px] font-mono text-ink-3" title="수요 - OPEC 공급 (M b/d 단위, 음수 = OPEC 공급 부족)">
                  수급 gap {(latest.supply_demand_gap_kbbl_d / 1000).toFixed(1)}M b/d
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
