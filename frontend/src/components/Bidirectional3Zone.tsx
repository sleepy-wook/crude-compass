/**
 * Bidirectional3Zone — Pattern Score 3-zone visualization.
 *
 * 시나리오 §6.1 양방향 (3-zone):
 *   70-100: HEDGE (위험방어, 빨강)
 *   30-70:  STABLE (관망, 회색)
 *   0-30:   OPPORTUNITY (기회포착, 녹색)
 *
 * 시각화: 세로 막대. 위가 위기, 아래가 기회 — §6.1 그림과 일치.
 */
import type { PatternScoreCurrent } from "../lib/types";
import { formatRoundedScore } from "../lib/utils";
import { useSignalContribution } from "../lib/queries";

interface Props {
  cur: PatternScoreCurrent | null | undefined;
}

const SIGNAL_LABEL: Record<string, string> = {
  news_tone: "GDELT 뉴스 키워드 burst",
  opec_momr: "OPEC 사우디·이란 생산",
  fx_krw_usd: "USD/KRW 환율",
  eia_inventory: "EIA 미국 재고",
  price_spike: "유가 급변동",
};

function zoneOf(score: number): "HEDGE" | "STABLE" | "OPPORTUNITY" {
  if (score >= 70) return "HEDGE";
  if (score <= 30) return "OPPORTUNITY";
  return "STABLE";
}

export function Bidirectional3Zone({ cur }: Props) {
  const score = cur?.pattern_score ?? null;
  const bullish = cur?.bullish_score ?? null;
  const bearish = cur?.bearish_score ?? null;
  const currentZone = score !== null ? zoneOf(score) : null;
  const isUrgent = score !== null && (score >= 90 || score <= 10);
  // 오늘 점수에 가장 크게 기여한 시그널 top 3 — "왜 위기인지" 인라인 답
  const sigContrib = useSignalContribution();
  const topContribs = (sigContrib.data?.items ?? []).slice(0, 3);

  // marker position (top = 0%, bottom = 100%)
  const markerTop = score !== null ? `${100 - score}%` : "50%";

  return (
    <section className="bg-panel border border-line-1 rounded-xl p-6">
      <div className="flex items-baseline justify-between mb-4">
        <div>
          <h3 className="font-display text-base font-semibold text-ink-1">
            Signal Strength
          </h3>
          <p className="text-[11px] text-ink-3 mt-0.5">
            위험 ↔ 기회 (0–100, 90일)
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[auto_1fr] gap-8">
        {/* LEFT — bar + zone labels (그대로) */}
        <div className="flex gap-5">
          {/* Vertical bar */}
          <div className="relative w-14 h-64 rounded-md overflow-hidden border border-line-1 shrink-0">
            <div className="absolute inset-x-0 top-0 h-[30%] bg-crisis-50" />
            <div className="absolute inset-x-0 top-[30%] h-[40%] bg-line-1" />
            <div className="absolute inset-x-0 bottom-0 h-[30%] bg-opportunity-50" />
            <div className="absolute inset-x-0 top-[30%] border-t border-dashed border-crisis-100" />
            <div className="absolute inset-x-0 top-[70%] border-t border-dashed border-opportunity-100" />
            <div className="absolute inset-x-0 top-[10%] border-t border-crisis-500/40" />
            <div className="absolute inset-x-0 top-[90%] border-t border-opportunity-500/40" />
            {score !== null && (
              <div
                className="absolute left-0 right-0 transition-all duration-500"
                style={{ top: markerTop, transform: "translateY(-50%)" }}
              >
                <div className="w-full h-0.5 bg-ink-1" />
                <div className="absolute right-full pr-2 top-1/2 -translate-y-1/2 whitespace-nowrap">
                  <span className="font-display text-base font-semibold text-ink-1 tabular-nums">
                    {formatRoundedScore(score)}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Zone labels */}
          <div className="flex flex-col justify-between h-64 py-1 w-32 shrink-0">
            <ZoneRow
              label="위험방어"
              range="70 — 100"
              active={currentZone === "HEDGE"}
              urgent={isUrgent && score! >= 90}
              urgentLabel="긴급 (90+)"
              tone="crisis"
            />
            <ZoneRow
              label="관망"
              range="30 — 70"
              active={currentZone === "STABLE"}
              tone="ink"
            />
            <ZoneRow
              label="기회포착"
              range="0 — 30"
              active={currentZone === "OPPORTUNITY"}
              urgent={isUrgent && score! <= 10}
              urgentLabel="긴급 (10-)"
              tone="opportunity"
            />
          </div>
        </div>

        {/* RIGHT — 강도 stats + 강한 시그널 */}
        <div className="flex flex-col gap-4">
          {(bullish !== null || bearish !== null) && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-[11px] text-ink-3 mb-1">위험 강도 (90일)</div>
                <div className="font-display text-2xl font-semibold text-crisis-700 tabular-nums">
                  {bullish !== null ? bullish.toFixed(0) : "—"}
                  <span className="text-[11px] text-ink-3 ml-1 font-normal">점</span>
                </div>
              </div>
              <div>
                <div className="text-[11px] text-ink-3 mb-1">안정 강도 (90일)</div>
                <div className="font-display text-2xl font-semibold text-opportunity-700 tabular-nums">
                  {bearish !== null ? bearish.toFixed(0) : "—"}
                  <span className="text-[11px] text-ink-3 ml-1 font-normal">점</span>
                </div>
              </div>
              {cur?.signal_count_90d != null && (
                <div className="col-span-2 text-[10px] text-ink-3 -mt-1">
                  누적 시그널 {cur.signal_count_90d}건 (위험 + 안정)
                </div>
              )}
            </div>
          )}

          {topContribs.length > 0 && (
            <div className="pt-3 border-t border-line-1 flex-1">
              <div className="text-[11px] uppercase tracking-wider text-ink-3 mb-2">
                최근 강한 시그널 (3)
              </div>
              <div className="space-y-1.5">
                {topContribs.map((s, i) => {
                  const dirLabel =
                    s.direction === "bullish" ? "위기" : s.direction === "bearish" ? "안정" : "중립";
                  const dirCls =
                    s.direction === "bullish"
                      ? "bg-crisis-50 text-crisis-700"
                      : s.direction === "bearish"
                        ? "bg-opportunity-50 text-opportunity-700"
                        : "bg-line-1 text-ink-3";
                  return (
                    <div key={`${s.signal_type}-${i}`} className="flex items-center gap-2 text-[12px]">
                      <span
                        className={`shrink-0 inline-flex items-center justify-center px-1.5 py-0.5 rounded text-[9px] font-medium uppercase tracking-wider ${dirCls}`}
                      >
                        {dirLabel}
                      </span>
                      <span className="text-ink-1 flex-1 truncate">
                        {SIGNAL_LABEL[s.signal_type] ?? s.signal_type}
                      </span>
                      <span className="text-ink-3 text-[11px] tabular-nums">
                        {s.share_pct.toFixed(1)}%
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

function ZoneRow({
  label,
  range,
  active,
  urgent,
  urgentLabel,
  tone,
}: {
  label: string;
  range: string;
  active: boolean;
  urgent?: boolean;
  urgentLabel?: string;
  tone: "crisis" | "ink" | "opportunity";
}) {
  const labelColor =
    tone === "crisis" ? "text-crisis-700" : tone === "opportunity" ? "text-opportunity-700" : "text-ink-2";
  return (
    <div className={active ? "" : "opacity-50"}>
      <div className="flex items-center gap-2">
        <span className={`font-display text-sm font-semibold ${labelColor}`}>{label}</span>
        {active && (
          <span className="text-[10px] uppercase tracking-wider text-ink-3 bg-line-1 px-1.5 py-0.5 rounded">
            현재
          </span>
        )}
        {urgent && urgentLabel && (
          <span className="text-[10px] text-crisis-700 font-medium">⚠ {urgentLabel}</span>
        )}
      </div>
      <div className="text-[11px] text-ink-3 mt-0.5 font-mono tabular-nums">{range}</div>
    </div>
  );
}
