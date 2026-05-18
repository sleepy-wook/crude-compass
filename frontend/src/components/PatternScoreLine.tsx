/**
 * PatternScoreLine — Pattern Score 시계열 line chart.
 *
 * 2 모드:
 *   - 'mini' (default 30일): Discovery 페이지 sparkline 보강
 *   - 'long' (2200일 ≈ 6년): 시나리오 §14 Phase 7 "평시 가치 6년 그래프" anchor
 *
 * 라이브러리 0 — pure SVG. zone band (HEDGE 70+ / OPP 30-) 가시화.
 */
import { useMemo } from "react";
import { usePatternHistory } from "../lib/queries";
import type { PatternHistory } from "../lib/types";

interface Props {
  /** 표시 기간 (일). 30 = mini, 2200 = 6년 long. */
  days?: number;
  /** 컴포넌트 변종 — 'mini' (sparkline) | 'long' (full Phase 7) */
  variant?: "mini" | "long";
}

const VIEW_W = 720;
const MINI_H = 80;
const LONG_H = 220;
const PAD_L = 36;
const PAD_R = 8;
const PAD_T = 8;
const PAD_B = 22;

function buildPath(
  history: PatternHistory[],
  innerW: number,
  innerH: number,
): string {
  if (history.length < 2) return "";
  const n = history.length;
  return history
    .map((h, i) => {
      const x = PAD_L + (i / (n - 1)) * innerW;
      const s = h.pattern_score ?? 50;
      const y = PAD_T + ((100 - s) / 100) * innerH;
      return `${i === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
    })
    .join(" ");
}

// Local extrema 추출 — 6년 시계열의 위기/기회 peak/trough를 marker로 표시.
// 시나리오 §6: "1년 1-2 위기 + 분기 1-2 기회 + 매주 미세 조정" narrative 시각화.
type Extremum = { date: string; score: number; idx: number; kind: "crisis" | "opportunity" };

function findExtrema(history: PatternHistory[]): Extremum[] {
  const out: Extremum[] = [];
  // window 60일 — 위기/기회는 보통 수 주~수개월 단위. noise 컷.
  const WIN = 60;
  const seenIdx = new Set<number>();
  for (let i = WIN; i < history.length - WIN; i++) {
    const cur = history[i].pattern_score ?? 50;
    // crisis peak: 90+ 이고 ±60일 윈도우 내 maximum
    if (cur >= 90) {
      let isMax = true;
      for (let j = i - WIN; j <= i + WIN; j++) {
        if (j === i) continue;
        if ((history[j]?.pattern_score ?? 50) > cur) {
          isMax = false;
          break;
        }
      }
      if (isMax && !seenIdx.has(i)) {
        out.push({ date: history[i].date, score: cur, idx: i, kind: "crisis" });
        // 이웃 60일에 다른 peak 안 잡히게 mark
        for (let k = i - WIN; k <= i + WIN; k++) seenIdx.add(k);
      }
    }
    // opportunity trough: 10- 이고 ±60일 윈도우 내 minimum
    if (cur <= 10) {
      let isMin = true;
      for (let j = i - WIN; j <= i + WIN; j++) {
        if (j === i) continue;
        if ((history[j]?.pattern_score ?? 50) < cur) {
          isMin = false;
          break;
        }
      }
      if (isMin && !seenIdx.has(i)) {
        out.push({ date: history[i].date, score: cur, idx: i, kind: "opportunity" });
        for (let k = i - WIN; k <= i + WIN; k++) seenIdx.add(k);
      }
    }
  }
  return out;
}

export function PatternScoreLine({ days = 30, variant = "mini" }: Props) {
  const { data, isLoading, isError } = usePatternHistory(days);
  const history = useMemo(
    () => (data?.history ?? []).filter((h) => h.pattern_score != null),
    [data],
  );

  const extrema = useMemo(
    () => (variant === "long" ? findExtrema(history) : []),
    [history, variant],
  );

  const H = variant === "long" ? LONG_H : MINI_H;
  const innerW = VIEW_W - PAD_L - PAD_R;
  const innerH = H - PAD_T - PAD_B;

  // y for zones
  const yHedge = PAD_T + ((100 - 70) / 100) * innerH;
  const yOpp = PAD_T + ((100 - 30) / 100) * innerH;
  const yMid = PAD_T + ((100 - 50) / 100) * innerH;

  const path = buildPath(history, innerW, innerH);
  const last = history[history.length - 1];
  const first = history[0];

  const title = variant === "long" ? "위기 신호 점수 · 6년 평시 가치" : `위기 신호 점수 · ${days}일`;
  const subtitle =
    variant === "long"
      ? "호르무즈 봉우리 + 작은 봉우리들 (OPEC 회의, EIA 재고, 허리케인). 매주 작은 시그널 종합 = 일상 도구."
      : "70+ 위험방어 · 30- 기회포착 · 중간 관망";

  const crisisCount = extrema.filter((e) => e.kind === "crisis").length;
  const oppCount = extrema.filter((e) => e.kind === "opportunity").length;

  return (
    <section className="mb-8">
      <div className="flex items-baseline justify-between mb-2">
        <h2
          className={`font-display ${variant === "long" ? "text-xl" : "text-sm"} font-semibold tracking-tight`}
        >
          {title}
        </h2>
        <span className="text-[11px] text-ink-3 font-mono">
          {first?.date ?? "—"} → {last?.date ?? "—"} · n={history.length}
        </span>
      </div>
      {variant === "long" && (
        <div className="mb-3 flex flex-wrap items-baseline gap-x-4 gap-y-1">
          <p className="text-xs text-ink-3 flex-1 min-w-0">{subtitle}</p>
          <div className="flex items-center gap-3 text-[11px] text-ink-3">
            <span className="inline-flex items-center gap-1">
              <span className="inline-block w-2 h-2 rounded-full bg-crisis-500" />
              <span>
                위기 peak <span className="text-ink-1 font-medium tabular-nums">{crisisCount}</span>
              </span>
            </span>
            <span className="inline-flex items-center gap-1">
              <span className="inline-block w-2 h-2 rounded-full bg-opportunity-500" />
              <span>
                기회 trough <span className="text-ink-1 font-medium tabular-nums">{oppCount}</span>
              </span>
            </span>
          </div>
        </div>
      )}

      <div className="rounded-xl border border-line-1 bg-panel">
        <svg
          width="100%"
          height={H}
          viewBox={`0 0 ${VIEW_W} ${H}`}
          style={{ display: "block", background: "#FAFAF7" }}
        >
          <defs>
            <linearGradient id="pattern-line-grad" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="#FF3621" stopOpacity=".25" />
              <stop offset="50%" stopColor="#7A8A91" stopOpacity=".10" />
              <stop offset="100%" stopColor="#10B981" stopOpacity=".20" />
            </linearGradient>
          </defs>

          {/* Zone bands */}
          <rect
            x={PAD_L}
            y={PAD_T}
            width={innerW}
            height={yHedge - PAD_T}
            fill="#FF3621"
            fillOpacity="0.06"
          />
          <rect
            x={PAD_L}
            y={yOpp}
            width={innerW}
            height={PAD_T + innerH - yOpp}
            fill="#10B981"
            fillOpacity="0.06"
          />

          {/* Zone reference lines */}
          <line
            x1={PAD_L}
            y1={yHedge}
            x2={VIEW_W - PAD_R}
            y2={yHedge}
            stroke="#FF3621"
            strokeDasharray="3 3"
            strokeWidth="1"
            opacity=".5"
          />
          <line
            x1={PAD_L}
            y1={yMid}
            x2={VIEW_W - PAD_R}
            y2={yMid}
            stroke="#D6D6CF"
            strokeWidth="1"
          />
          <line
            x1={PAD_L}
            y1={yOpp}
            x2={VIEW_W - PAD_R}
            y2={yOpp}
            stroke="#10B981"
            strokeDasharray="3 3"
            strokeWidth="1"
            opacity=".5"
          />

          {/* Y axis labels */}
          {[
            { v: 100, y: PAD_T },
            { v: 70, y: yHedge },
            { v: 50, y: yMid },
            { v: 30, y: yOpp },
            { v: 0, y: PAD_T + innerH },
          ].map((tick) => (
            <text
              key={tick.v}
              x={PAD_L - 6}
              y={tick.y + 3}
              fontSize="9"
              fontFamily="JetBrains Mono"
              fill="#7A8A91"
              textAnchor="end"
            >
              {tick.v}
            </text>
          ))}

          {/* Line area fill */}
          {path && (
            <path
              d={`${path} L ${PAD_L + innerW} ${PAD_T + innerH} L ${PAD_L} ${PAD_T + innerH} Z`}
              fill="url(#pattern-line-grad)"
            />
          )}
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

          {/* Decision marker — 위기 peak / 기회 trough에 매니저 의사결정 cue */}
          {extrema.map((ex) => {
            const x = PAD_L + (ex.idx / Math.max(1, history.length - 1)) * innerW;
            const y = PAD_T + ((100 - ex.score) / 100) * innerH;
            const color = ex.kind === "crisis" ? "#FF3621" : "#10B981";
            const label = ex.kind === "crisis" ? "위기" : "기회";
            // 위기는 위로 spike, 기회는 아래로 spike
            const dir = ex.kind === "crisis" ? -1 : 1;
            return (
              <g key={`${ex.kind}-${ex.idx}`}>
                <line
                  x1={x}
                  y1={y}
                  x2={x}
                  y2={y + dir * 14}
                  stroke={color}
                  strokeWidth="1.5"
                  opacity="0.6"
                />
                <circle cx={x} cy={y + dir * 14} r="3" fill={color} />
                <title>
                  {`${label} 시점 · ${ex.date} · 위기 강도 ${Math.round(ex.score / 10)}/10`}
                </title>
              </g>
            );
          })}

          {/* Last point */}
          {last && (
            <g
              transform={`translate(${PAD_L + innerW}, ${
                PAD_T + ((100 - (last.pattern_score ?? 50)) / 100) * innerH
              })`}
            >
              <circle
                r="5"
                fill={
                  (last.pattern_score ?? 50) >= 70
                    ? "#FF3621"
                    : (last.pattern_score ?? 50) <= 30
                      ? "#10B981"
                      : "#7A8A91"
                }
                fillOpacity=".25"
              />
              <circle
                r="2.5"
                fill={
                  (last.pattern_score ?? 50) >= 70
                    ? "#FF3621"
                    : (last.pattern_score ?? 50) <= 30
                      ? "#10B981"
                      : "#7A8A91"
                }
              />
            </g>
          )}

          {/* Empty state */}
          {!isLoading && history.length === 0 && (
            <text
              x={VIEW_W / 2}
              y={H / 2}
              fontSize="11"
              fontFamily="JetBrains Mono"
              fill="#7A8A91"
              textAnchor="middle"
            >
              {isError ? "데이터 일시 불가" : "데이터 없음"}
            </text>
          )}

          {/* Loading state */}
          {isLoading && (
            <text
              x={VIEW_W / 2}
              y={H / 2}
              fontSize="11"
              fontFamily="JetBrains Mono"
              fill="#7A8A91"
              textAnchor="middle"
            >
              로딩 중…
            </text>
          )}

          {/* X axis date labels (first / mid / last) */}
          {history.length > 1 && (
            <>
              <text
                x={PAD_L}
                y={H - 6}
                fontSize="9"
                fontFamily="JetBrains Mono"
                fill="#7A8A91"
              >
                {first?.date.slice(0, 7)}
              </text>
              <text
                x={PAD_L + innerW / 2}
                y={H - 6}
                fontSize="9"
                fontFamily="JetBrains Mono"
                fill="#7A8A91"
                textAnchor="middle"
              >
                {history[Math.floor(history.length / 2)]?.date.slice(0, 7)}
              </text>
              <text
                x={PAD_L + innerW}
                y={H - 6}
                fontSize="9"
                fontFamily="JetBrains Mono"
                fill="#7A8A91"
                textAnchor="end"
              >
                {last?.date.slice(0, 7)}
              </text>
            </>
          )}
        </svg>
      </div>
    </section>
  );
}
