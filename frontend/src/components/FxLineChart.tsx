/**
 * FxLineChart — USD/KRW 일별 환율 + 30일 변동성.
 *
 * 시나리오 §7 #5 + §13 랜딩 코스트 계산 핵심 input.
 * 데이터 source: `gold.fx_with_delta` view.
 */
import { useMemo } from "react";
import { useFxHistory } from "../lib/queries";

const VIEW_W = 720;
const VIEW_H = 180;
const PAD_L = 48;
const PAD_R = 8;
const PAD_T = 14;
const PAD_B = 22;

interface FxPoint {
  date: string;
  rate: number | null;
  delta_1d: number | null;
  delta_7d: number | null;
  vol_30d: number | null;
}

function buildPath(
  points: FxPoint[],
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
    const v = points[i].rate;
    if (v == null) continue;
    const x = PAD_L + (i / (n - 1)) * innerW;
    const y = PAD_T + ((yMax - v) / yRange) * innerH;
    d += `${moved ? "L" : "M"} ${x.toFixed(1)} ${y.toFixed(1)} `;
    moved = true;
  }
  return d;
}

export function FxLineChart({ days = 90 }: { days?: number }) {
  const { data, isLoading, isError } = useFxHistory(days);
  const points = useMemo(() => data?.history ?? [], [data]);

  const innerW = VIEW_W - PAD_L - PAD_R;
  const innerH = VIEW_H - PAD_T - PAD_B;

  const { yMin, yMax } = useMemo(() => {
    const all = points.map((p) => p.rate).filter((v): v is number => v != null);
    if (all.length === 0) return { yMin: 1300, yMax: 1450 };
    const min = Math.min(...all);
    const max = Math.max(...all);
    const pad = (max - min) * 0.15 || 5;
    return { yMin: Math.floor(min - pad), yMax: Math.ceil(max + pad) };
  }, [points]);

  const path = buildPath(points, innerW, innerH, yMin, yMax);
  const latest = points[points.length - 1];
  const first = points[0];

  const deltaSign = latest?.delta_7d != null
    ? latest.delta_7d > 0 ? "+" : ""
    : "";
  const deltaTone = latest?.delta_7d != null
    ? latest.delta_7d > 0 ? "text-crisis-700" : latest.delta_7d < 0 ? "text-opportunity-700" : "text-ink-3"
    : "text-ink-3";

  return (
    <section className="mb-8">
      <div className="flex items-baseline justify-between mb-3">
        <h3 className="font-display text-lg font-semibold tracking-tight text-ink-1">
          원·달러 환율
        </h3>
        <span className="text-[11px] text-ink-3">최근 {days}일</span>
      </div>

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
                  ₩{v.toFixed(0)}
                </text>
              </g>
            );
          })}

          {/* Line */}
          {path && (
            <path
              d={path}
              fill="none"
              stroke="#1B3139"
              strokeWidth="1.5"
              strokeLinejoin="round"
              strokeLinecap="round"
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
              {isError ? "환율 데이터 일시 불가" : "데이터 없음"}
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
                {first?.date}
              </text>
              <text
                x={PAD_L + innerW}
                y={VIEW_H - 6}
                fontSize="9"
                fontFamily="JetBrains Mono"
                fill="#7A8A91"
                textAnchor="end"
              >
                {latest?.date}
              </text>
            </>
          )}
        </svg>

        {/* Legend strip — latest + 7d delta + 30d vol */}
        <div className="flex items-center gap-4 px-4 py-2 border-t border-line-1 bg-line-1/30 text-[11px] font-mono">
          <span className="text-ink">
            최신 ₩
            <span className="font-semibold">
              {latest?.rate?.toFixed(2) ?? "—"}
            </span>
          </span>
          {latest?.delta_7d != null && (
            <span className={deltaTone}>
              7일 변동 {deltaSign}
              {latest.delta_7d.toFixed(2)}
            </span>
          )}
          {latest?.vol_30d != null && (
            <span className="ml-auto text-ink-3">
              30일 변동성 {latest.vol_30d.toFixed(2)}
            </span>
          )}
        </div>
      </div>
    </section>
  );
}
