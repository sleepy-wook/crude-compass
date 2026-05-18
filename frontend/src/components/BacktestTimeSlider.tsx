/**
 * BacktestTimeSlider — 과거 시점 선택 → AI 추천 vs 실제 결과 비교.
 *
 * 시나리오 §14 Phase 5 ★ Wow. Single page에서 collapsible로 expose.
 * Lazy load: expand 시에만 데이터 fetch (초기 로딩 시간 단축).
 */
import { useMemo, useState } from "react";
import { useBacktestPredictions } from "../lib/queries";
import { formatPct, formatScore, formatUsd } from "../lib/utils";

export function BacktestTimeSlider() {
  const [idx, setIdx] = useState<number | null>(null);
  const [expanded, setExpanded] = useState(false);
  // Lazy load — expand 시에만 fetch
  const preds = useBacktestPredictions(300, { enabled: expanded });

  const sorted = useMemo(() => {
    if (!preds.data?.predictions) return [];
    return [...preds.data.predictions].sort((a, b) =>
      a.as_of_date < b.as_of_date ? -1 : 1,
    );
  }, [preds.data]);

  const effectiveIdx = idx ?? Math.floor(sorted.length / 2);
  const current = sorted[effectiveIdx];

  return (
    <section className="mb-10 bg-panel border border-line-1 rounded-xl overflow-hidden">
      <button
        type="button"
        onClick={() => setExpanded((e) => !e)}
        className="w-full px-6 py-4 flex items-center justify-between text-left hover:bg-paper transition-colors"
      >
        <div>
          <h3 className="font-display text-lg font-semibold text-ink-1">과거 권고 검증</h3>
          <p className="text-xs text-ink-3 mt-0.5">
            과거 시점에서 AI 권고와 실제 결과를 비교합니다
          </p>
        </div>
        <span className="text-ink-3 text-sm">{expanded ? "접기" : "펼치기"}</span>
      </button>

      {expanded && (
        <div className="px-6 pb-6 border-t border-line-1 pt-6">
          {preds.isLoading && (
            <div className="text-sm text-ink-3">데이터 불러오는 중...</div>
          )}
          {!preds.isLoading && (preds.isError || sorted.length === 0) && (
            <div className="text-sm text-ink-3">과거 검증 데이터를 불러올 수 없습니다.</div>
          )}
          {!preds.isLoading && sorted.length > 0 && (
            <div>
              {/* Slider */}
              <div className="flex items-center justify-between mb-3 text-[11px] text-ink-3">
                <span>{sorted[0]?.as_of_date}</span>
                <span>{sorted[sorted.length - 1]?.as_of_date}</span>
              </div>
              <input
                type="range"
                min={0}
                max={sorted.length - 1}
                value={effectiveIdx}
                onChange={(e) => setIdx(Number(e.target.value))}
                className="w-full mb-4 accent-ink-1"
              />
              <div className="flex items-center justify-center gap-5 text-[11px] text-ink-3 mb-6">
                <span className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-crisis-500" /> 위기
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-ink-3" /> 관망
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-opportunity-500" /> 기회
                </span>
              </div>

              {current && (
                <div className="text-center mb-6">
                  <div className="text-[11px] text-ink-3 mb-1">선택한 시점</div>
                  <div className="font-display text-xl font-semibold text-ink-1">
                    {current.as_of_date}
                  </div>
                </div>
              )}

              {current && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-6 border-t border-line-1">
                  <div>
                    <div className="text-[11px] uppercase tracking-wider text-ink-3 mb-2">
                      AI 권고 (그 날)
                    </div>
                    <div className="font-display text-base font-semibold text-ink-1">
                      {current.action_type === "new_mission"
                        ? `${current.mission_type === "HEDGE" ? "장기계약" : "즉시구매"} ${current.target_pct}%`
                        : "관망"}
                    </div>
                    <div className="text-xs text-ink-3 mt-1">
                      위기 점수 {formatScore(current.pattern_score)} · 신뢰도{" "}
                      {formatScore(current.confidence_score)}
                    </div>
                  </div>

                  <div>
                    <div className="text-[11px] uppercase tracking-wider text-ink-3 mb-2">
                      두바이유 (30일 후)
                    </div>
                    <div className="font-display text-base font-semibold text-ink-1">
                      {formatUsd(current.dubai_at_signal_usd)} →{" "}
                      {formatUsd(current.dubai_30d_usd)}
                    </div>
                    <div className="text-xs text-ink-3 mt-1">
                      변동{" "}
                      {current.dubai_at_signal_usd && current.dubai_30d_usd
                        ? formatPct(
                            ((current.dubai_30d_usd - current.dubai_at_signal_usd) /
                              current.dubai_at_signal_usd) *
                              100,
                            2,
                          )
                        : "—"}
                    </div>
                  </div>

                  <div>
                    <div className="text-[11px] uppercase tracking-wider text-ink-3 mb-2">
                      권고 채택 시 절감
                    </div>
                    <div className="grid grid-cols-3 gap-3">
                      <Outcome label="7일" value={current.saving_7d_pct} />
                      <Outcome label="30일" value={current.saving_30d_pct} />
                      <Outcome label="90일" value={current.saving_90d_pct} />
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function Outcome({ label, value }: { label: string; value: number | null | undefined }) {
  const tone =
    value == null ? "text-ink-3" : value > 0 ? "text-opportunity-700" : "text-crisis-700";
  return (
    <div>
      <div className="text-[10px] text-ink-3 mb-0.5">{label}</div>
      <div className={`font-display text-sm font-semibold ${tone}`}>
        {formatPct(value, 2)}
      </div>
    </div>
  );
}
