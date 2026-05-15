/**
 * PriceLineChart — Dubai/Brent/WTI 일별 가격 + Brent-Dubai spread.
 *
 * 시나리오 §7 #4 anchor — 한국 정유사 baseline = Dubai.
 * 데이터 source: `gold.oil_prices_wide` view (bronze.oil_prices_daily 3-ticker pivot).
 * 라이브러리 0 — pure SVG.
 */
import { useMemo } from "react";
import { usePricesWide } from "../lib/queries";

const VIEW_W = 720;
const VIEW_H = 200;
const PAD_L = 40;
const PAD_R = 8;
const PAD_T = 16;
const PAD_B = 22;

const COLORS = {
  dubai: "#1B3139",     // ink (primary — 한국 정유사 baseline)
  brent: "#F59E0B",     // amber
  wti: "#10B981",       // green
};

interface PricePoint {
  trade_date: string;
  wti_usd: number | null;
  brent_usd: number | null;
  dubai_usd: number | null;
  brent_dubai_spread_usd: number | null;
}

function buildPath(
  points: PricePoint[],
  field: keyof Pick<PricePoint, "wti_usd" | "brent_usd" | "dubai_usd">,
  innerW: number,
  innerH: number,
  yMin: number,
  yMax: number,
): string {
  if (points.length < 2) return "";
  const yRange = yMax - yMin || 1;
  const n = points.length;
  let d = "";
  let moved = false;
  for (let i = 0; i < n; i++) {
    const v = points[i][field];
    if (v == null) continue;
    const x = PAD_L + (i / (n - 1)) * innerW;
    const y = PAD_T + ((yMax - v) / yRange) * innerH;
    d += `${moved ? "L" : "M"} ${x.toFixed(1)} ${y.toFixed(1)} `;
    moved = true;
  }
  return d;
}

export function PriceLineChart({ days = 90 }: { days?: number }) {
  const { data, isLoading, isError } = usePricesWide(days);
  const points = useMemo(() => data?.prices ?? [], [data]);

  const innerW = VIEW_W - PAD_L - PAD_R;
  const innerH = VIEW_H - PAD_T - PAD_B;

  // y range — 모든 ticker 합쳐서 min/max
  const { yMin, yMax } = useMemo(() => {
    const all: number[] = [];
    for (const p of points) {
      for (const v of [p.wti_usd, p.brent_usd, p.dubai_usd]) {
        if (v != null) all.push(v);
      }
    }
    if (all.length === 0) return { yMin: 0, yMax: 100 };
    const min = Math.min(...all);
    const max = Math.max(...all);
    const pad = (max - min) * 0.1 || 1;
    return { yMin: Math.floor(min - pad), yMax: Math.ceil(max + pad) };
  }, [points]);

  const pathDubai = buildPath(points, "dubai_usd", innerW, innerH, yMin, yMax);
  const pathBrent = buildPath(points, "brent_usd", innerW, innerH, yMin, yMax);
  const pathWti = buildPath(points, "wti_usd", innerW, innerH, yMin, yMax);

  const latest = points[points.length - 1];
  const first = points[0];

  return (
    <section className="mb-6">
      <div className="flex items-baseline justify-between mb-2">
        <h2 className="font-display text-base font-semibold tracking-tight">
          Dubai · Brent · WTI — {days}일
        </h2>
        <span className="text-[11px] text-ink-3 font-mono">
          gold.oil_prices_wide · KNOC OPINET
        </span>
      </div>
      <p className="text-xs text-ink-3 mb-3">
        한국 정유사 baseline = <span className="font-semibold text-ink">Dubai</span> (중동산 70%+ 수입).
        Brent/WTI는 비교 기준선.
      </p>

      <div className="rounded-xl border border-line-1 bg-panel">
        <svg
          width="100%"
          height={VIEW_H}
          viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
          style={{ display: "block", background: "#FAFAF7" }}
        >
          {/* Y axis grid + labels */}
          {[0, 0.25, 0.5, 0.75, 1].map((f) => {
            const y = PAD_T + f * innerH;
            const v = yMax - f * (yMax - yMin);
            return (
              <g key={f}>
                <line
                  x1={PAD_L}
                  y1={y}
                  x2={VIEW_W - PAD_R}
                  y2={y}
                  stroke="#EFEFEA"
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
                  ${v.toFixed(0)}
                </text>
              </g>
            );
          })}

          {/* 3 lines */}
          {pathBrent && (
            <path
              d={pathBrent}
              fill="none"
              stroke={COLORS.brent}
              strokeWidth="1.2"
              opacity={0.7}
            />
          )}
          {pathWti && (
            <path
              d={pathWti}
              fill="none"
              stroke={COLORS.wti}
              strokeWidth="1.2"
              opacity={0.7}
            />
          )}
          {pathDubai && (
            <path
              d={pathDubai}
              fill="none"
              stroke={COLORS.dubai}
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          )}

          {/* Empty / loading state */}
          {!isLoading && points.length === 0 && (
            <text
              x={VIEW_W / 2}
              y={VIEW_H / 2}
              fontSize="11"
              fontFamily="JetBrains Mono"
              fill="#7A8A91"
              textAnchor="middle"
            >
              {isError ? "가격 데이터 일시 불가" : "데이터 없음"}
            </text>
          )}
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

          {/* X axis date labels */}
          {points.length > 1 && (
            <>
              <text
                x={PAD_L}
                y={VIEW_H - 6}
                fontSize="9"
                fontFamily="JetBrains Mono"
                fill="#7A8A91"
              >
                {first?.trade_date}
              </text>
              <text
                x={PAD_L + innerW}
                y={VIEW_H - 6}
                fontSize="9"
                fontFamily="JetBrains Mono"
                fill="#7A8A91"
                textAnchor="end"
              >
                {latest?.trade_date}
              </text>
            </>
          )}
        </svg>

        {/* Legend + latest values */}
        <div className="flex items-center gap-4 px-4 py-2 border-t border-line-1 bg-line-1/30 text-[11px] font-mono">
          <span className="flex items-center gap-1.5">
            <span
              className="inline-block w-3 h-0.5"
              style={{ background: COLORS.dubai }}
            />
            <span className="text-ink">
              Dubai ${latest?.dubai_usd?.toFixed(2) ?? "—"}
            </span>
          </span>
          <span className="flex items-center gap-1.5">
            <span
              className="inline-block w-3 h-0.5"
              style={{ background: COLORS.brent }}
            />
            <span className="text-ink-3">
              Brent ${latest?.brent_usd?.toFixed(2) ?? "—"}
            </span>
          </span>
          <span className="flex items-center gap-1.5">
            <span
              className="inline-block w-3 h-0.5"
              style={{ background: COLORS.wti }}
            />
            <span className="text-ink-3">
              WTI ${latest?.wti_usd?.toFixed(2) ?? "—"}
            </span>
          </span>
          {latest?.brent_dubai_spread_usd != null && (
            <span className="ml-auto text-ink-3">
              Brent − Dubai spread{" "}
              <span className="text-ink font-semibold">
                ${latest.brent_dubai_spread_usd.toFixed(2)}
              </span>
            </span>
          )}
        </div>
      </div>
    </section>
  );
}
