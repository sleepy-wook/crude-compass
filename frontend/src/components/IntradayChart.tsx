/**
 * IntradayChart — bronze.oil_prices 5분 단위 raw 시계열 (D-3 추가).
 *
 * Dubai / Brent / WTI 3 ticker overlay. 최근 24h default.
 * SVG pure — 라이브러리 X.
 */
import { useMemo } from "react";
import { useIntradayPrices } from "../lib/queries";

interface Props {
  hours?: number; // default 24h
}

const TICKER_META: Record<string, { label: string; color: string }> = {
  dubai: { label: "Dubai", color: "#1B3139" },
  brent: { label: "Brent", color: "#E0A30E" },
  wti: { label: "WTI", color: "#0E8F5E" },
};

const VIEW_W = 800;
const VIEW_H = 220;
const PAD_L = 42;
const PAD_R = 12;
const PAD_T = 12;
const PAD_B = 24;

function fmtPrice(p: number): string {
  return `$${p.toFixed(0)}`;
}

function fmtTime(iso: string): string {
  try {
    const d = new Date(iso);
    const mm = `${d.getMonth() + 1}`.padStart(2, "0");
    const dd = `${d.getDate()}`.padStart(2, "0");
    const hh = `${d.getHours()}`.padStart(2, "0");
    const mi = `${d.getMinutes()}`.padStart(2, "0");
    return `${mm}/${dd} ${hh}:${mi}`;
  } catch {
    return iso;
  }
}

export function IntradayChart({ hours = 24 }: Props) {
  const { data, isLoading, isError } = useIntradayPrices(hours);
  const series = data?.series ?? [];

  const { yMin, yMax, allPoints, latestPerTicker } = useMemo(() => {
    let min = Infinity;
    let max = -Infinity;
    let allCount = 0;
    const latest: Record<string, { price: number; ts: string } | undefined> = {};
    for (const s of series) {
      if (!s.points.length) continue;
      allCount += s.points.length;
      for (const p of s.points) {
        if (p.price_usd < min) min = p.price_usd;
        if (p.price_usd > max) max = p.price_usd;
      }
      const last = s.points[s.points.length - 1];
      latest[s.ticker] = { price: last.price_usd, ts: last.fetched_at };
    }
    if (!Number.isFinite(min) || !Number.isFinite(max)) {
      return { yMin: 0, yMax: 1, allPoints: 0, latestPerTicker: latest };
    }
    // padding 5%
    const pad = (max - min) * 0.08 || 1;
    return {
      yMin: min - pad,
      yMax: max + pad,
      allPoints: allCount,
      latestPerTicker: latest,
    };
  }, [series]);

  // x-axis time range — earliest to latest across all series
  const { tMin, tMax } = useMemo(() => {
    let tMinN = Infinity;
    let tMaxN = -Infinity;
    for (const s of series) {
      for (const p of s.points) {
        const t = new Date(p.fetched_at).getTime();
        if (t < tMinN) tMinN = t;
        if (t > tMaxN) tMaxN = t;
      }
    }
    return { tMin: tMinN, tMax: tMaxN };
  }, [series]);

  // 데이터 없으면 컴포넌트 hide
  if (!isLoading && (isError || allPoints === 0)) {
    return null;
  }

  const innerW = VIEW_W - PAD_L - PAD_R;
  const innerH = VIEW_H - PAD_T - PAD_B;

  function buildPath(points: { price_usd: number; fetched_at: string }[]): string {
    if (points.length < 2 || tMax <= tMin) return "";
    return points
      .map((p, i) => {
        const t = new Date(p.fetched_at).getTime();
        const x = PAD_L + ((t - tMin) / (tMax - tMin)) * innerW;
        const y = PAD_T + ((yMax - p.price_usd) / (yMax - yMin)) * innerH;
        return `${i === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
      })
      .join(" ");
  }

  // y-axis ticks (4 ticks)
  const yTicks = [yMin, yMin + (yMax - yMin) / 3, yMin + ((yMax - yMin) * 2) / 3, yMax];

  return (
    <section className="bg-panel border border-line-1 rounded-xl p-5 mb-10">
      <div className="flex items-baseline justify-between mb-3">
        <div className="flex items-baseline gap-2">
          <h3 className="font-display text-sm font-semibold text-ink-1">
            Intraday 시계열
          </h3>
          <span className="text-[10px] uppercase tracking-wider text-ink-3">
            5분 단위 · 최근 {hours}시간
          </span>
        </div>
        {/* Legend */}
        <div className="flex items-center gap-3 text-[11px]">
          {(["dubai", "brent", "wti"] as const).map((tk) => {
            const meta = TICKER_META[tk];
            const last = latestPerTicker[tk];
            return (
              <span key={tk} className="inline-flex items-center gap-1.5">
                <span
                  className="inline-block w-2.5 h-0.5"
                  style={{ background: meta.color }}
                />
                <span className="text-ink-2 font-medium">{meta.label}</span>
                {last && (
                  <span className="text-ink-3 tabular-nums">${last.price.toFixed(2)}</span>
                )}
              </span>
            );
          })}
        </div>
      </div>

      <div className="rounded-lg border border-line-1 bg-paper/60">
        <svg
          width="100%"
          height={VIEW_H}
          viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
          style={{ display: "block" }}
        >
          {/* y-axis grid + labels */}
          {yTicks.map((tv, i) => {
            const y = PAD_T + ((yMax - tv) / (yMax - yMin)) * innerH;
            return (
              <g key={i}>
                <line
                  x1={PAD_L}
                  y1={y}
                  x2={VIEW_W - PAD_R}
                  y2={y}
                  stroke="#ECECE8"
                  strokeWidth="1"
                />
                <text
                  x={PAD_L - 6}
                  y={y + 3}
                  fontSize="9"
                  fontFamily="JetBrains Mono"
                  fill="#7A8A91"
                  textAnchor="end"
                >
                  {fmtPrice(tv)}
                </text>
              </g>
            );
          })}

          {/* x-axis labels (3 ticks: start, mid, end) */}
          {tMin !== Infinity && tMax !== -Infinity && (
            <>
              {[0, 0.5, 1].map((frac, i) => {
                const x = PAD_L + frac * innerW;
                const t = tMin + frac * (tMax - tMin);
                return (
                  <text
                    key={i}
                    x={x}
                    y={VIEW_H - 8}
                    fontSize="9"
                    fontFamily="JetBrains Mono"
                    fill="#7A8A91"
                    textAnchor={i === 0 ? "start" : i === 2 ? "end" : "middle"}
                  >
                    {fmtTime(new Date(t).toISOString())}
                  </text>
                );
              })}
            </>
          )}

          {/* Lines */}
          {series.map((s) => {
            const meta = TICKER_META[s.ticker];
            if (!meta) return null;
            const d = buildPath(s.points);
            if (!d) return null;
            return (
              <path
                key={s.ticker}
                d={d}
                fill="none"
                stroke={meta.color}
                strokeWidth="1.5"
                strokeLinejoin="round"
                strokeLinecap="round"
              />
            );
          })}

          {/* Loading */}
          {isLoading && (
            <text
              x={VIEW_W / 2}
              y={VIEW_H / 2}
              fontSize="11"
              fontFamily="JetBrains Mono"
              fill="#7A8A91"
              textAnchor="middle"
            >
              로딩 중…
            </text>
          )}
        </svg>
      </div>
      <p className="text-[10px] text-ink-3 mt-2 italic">
        OilPriceAPI 5분 cron 적재 · bronze.oil_prices · 총 {allPoints.toLocaleString()}개 sample
      </p>
    </section>
  );
}
