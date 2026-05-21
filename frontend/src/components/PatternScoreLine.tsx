/**
 * PatternScoreLine — Pattern Score 시계열 (Recharts).
 *
 * 2 모드:
 *   - 'mini' (default 30일): Discovery 페이지 sparkline
 *   - 'long' (2200일 ≈ 6년): "평시 가치 6년 그래프"
 *
 * 2026-05-21: SVG hand-rolled → Recharts.
 *  - Zone band (위험방어 70+ / 기회포착 30-)
 *  - Reference lines 30/70
 *  - 위기 peak / 기회 trough extrema marker (long variant)
 *  - hover tooltip
 */
import { useMemo } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceArea,
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { usePatternHistory } from "../lib/queries";
import type { PatternHistory } from "../lib/types";

interface Props {
  days?: number;
  variant?: "mini" | "long";
  hideTitle?: boolean;
}

type Extremum = { date: string; score: number; kind: "crisis" | "opportunity" };

function findExtrema(history: PatternHistory[]): Extremum[] {
  const out: Extremum[] = [];
  const WIN = 60;
  const seenIdx = new Set<number>();
  for (let i = WIN; i < history.length - WIN; i++) {
    const cur = history[i].pattern_score ?? 50;
    if (cur >= 90) {
      let isMax = true;
      for (let j = i - WIN; j <= i + WIN; j++) {
        if (j === i) continue;
        if ((history[j]?.pattern_score ?? 50) > cur) { isMax = false; break; }
      }
      if (isMax && !seenIdx.has(i)) {
        out.push({ date: history[i].date, score: cur, kind: "crisis" });
        for (let k = i - WIN; k <= i + WIN; k++) seenIdx.add(k);
      }
    }
    if (cur <= 10) {
      let isMin = true;
      for (let j = i - WIN; j <= i + WIN; j++) {
        if (j === i) continue;
        if ((history[j]?.pattern_score ?? 50) < cur) { isMin = false; break; }
      }
      if (isMin && !seenIdx.has(i)) {
        out.push({ date: history[i].date, score: cur, kind: "opportunity" });
        for (let k = i - WIN; k <= i + WIN; k++) seenIdx.add(k);
      }
    }
  }
  return out;
}

export function PatternScoreLine({ days = 30, variant = "mini", hideTitle = false }: Props) {
  const { data, isLoading, isError } = usePatternHistory(days);

  const history = useMemo(
    () => (data?.history ?? []).filter((h) => h.pattern_score != null),
    [data],
  );

  const chartData = useMemo(
    () => history.map((h) => ({ date: h.date, score: h.pattern_score })),
    [history],
  );

  const extrema = useMemo(
    () => (variant === "long" ? findExtrema(history) : []),
    [history, variant],
  );

  const last = history[history.length - 1];
  const first = history[0];
  const crisisCount = extrema.filter((e) => e.kind === "crisis").length;
  const oppCount = extrema.filter((e) => e.kind === "opportunity").length;

  const height = variant === "long" ? 260 : 100;
  const title =
    variant === "long" ? "위기 신호 점수 · 6년 평시 가치" : `위기 신호 점수 · ${days}일`;
  const subtitle =
    variant === "long"
      ? "호르무즈 봉우리 + 작은 봉우리들 (OPEC 회의, EIA 재고, 허리케인)."
      : "70+ 위험방어 · 30- 기회포착 · 중간 관망";

  return (
    <section className="mb-2">
      {!hideTitle && (
        <div className="flex items-baseline justify-between mb-2">
          <h2 className={`font-display ${variant === "long" ? "text-xl" : "text-sm"} font-semibold tracking-tight`}>
            {title}
          </h2>
          <span className="text-[11px] text-ink-3 font-mono">
            {first?.date ?? "—"} → {last?.date ?? "—"} · n={history.length}
          </span>
        </div>
      )}
      {hideTitle && (
        <div className="flex items-baseline justify-end mb-2">
          <span className="text-[11px] text-ink-3 font-mono">
            {first?.date ?? "—"} → {last?.date ?? "—"} · n={history.length}
          </span>
        </div>
      )}
      {variant === "long" && (
        <div className="mb-3 flex flex-wrap items-baseline gap-x-4 gap-y-1">
          <p className="text-xs text-ink-3 flex-1 min-w-0">{subtitle}</p>
          <div className="flex items-center gap-3 text-[11px] text-ink-3">
            <span className="inline-flex items-center gap-1">
              <span className="inline-block w-2 h-2 rounded-full bg-crisis-500" />
              <span>위기 peak <span className="text-ink-1 font-medium tabular-nums">{crisisCount}</span></span>
            </span>
            <span className="inline-flex items-center gap-1">
              <span className="inline-block w-2 h-2 rounded-full bg-opportunity-500" />
              <span>기회 trough <span className="text-ink-1 font-medium tabular-nums">{oppCount}</span></span>
            </span>
          </div>
        </div>
      )}

      <div className="rounded-xl border border-line-1 bg-panel">
        <div className="px-2 py-2" style={{ height }}>
          {isLoading ? (
            <div className="flex items-center justify-center h-full text-[11px] text-ink-3">로딩 중...</div>
          ) : isError || chartData.length === 0 ? (
            <div className="flex items-center justify-center h-full text-[11px] text-ink-3">데이터 없음</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 6, right: 12, bottom: 4, left: 4 }}>
                <defs>
                  <linearGradient id="pattern-score-grad" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor="#FF3621" stopOpacity="0.35" />
                    <stop offset="50%" stopColor="#7A8A91" stopOpacity="0.10" />
                    <stop offset="100%" stopColor="#10B981" stopOpacity="0.25" />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#EFEFEA" strokeDasharray="3 3" vertical={false} />
                {/* Zone bands */}
                <ReferenceArea y1={70} y2={100} fill="#FF3621" fillOpacity={0.06} />
                <ReferenceArea y1={0} y2={30} fill="#10B981" fillOpacity={0.06} />
                {/* Reference lines */}
                <ReferenceLine y={70} stroke="#FF3621" strokeDasharray="3 3" strokeOpacity={0.5} />
                <ReferenceLine y={30} stroke="#10B981" strokeDasharray="3 3" strokeOpacity={0.5} />
                <ReferenceLine y={50} stroke="#D6D6CF" />

                {variant === "long" && extrema.map((e) => (
                  <ReferenceDot
                    key={`${e.kind}-${e.date}`}
                    x={e.date}
                    y={e.score}
                    r={3.5}
                    fill={e.kind === "crisis" ? "#FF3621" : "#10B981"}
                    stroke="white"
                    strokeWidth={1}
                    ifOverflow="visible"
                  />
                ))}

                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 10, fill: "#7A8A91" }}
                  tickLine={false}
                  axisLine={{ stroke: "#CFCFC8" }}
                  minTickGap={60}
                  tickFormatter={(v) => v?.slice(2) ?? ""}
                />
                <YAxis
                  domain={[0, 100]}
                  tick={{ fontSize: 10, fill: "#7A8A91" }}
                  tickLine={false}
                  axisLine={false}
                  width={28}
                  ticks={[0, 30, 50, 70, 100]}
                />
                <Tooltip content={<ScoreTooltip />} />

                <Area
                  type="monotone"
                  dataKey="score"
                  stroke="#1B3139"
                  strokeWidth={1.6}
                  fill="url(#pattern-score-grad)"
                  fillOpacity={1}
                  activeDot={{ r: 4 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </section>
  );
}

function ScoreTooltip({ active, payload, label }: {
  active?: boolean;
  payload?: Array<{ value: number }>;
  label?: string;
}) {
  if (!active || !payload || payload.length === 0) return null;
  const v = payload[0].value;
  const zone = v >= 70 ? "위험방어" : v <= 30 ? "기회포착" : "관망";
  const tone = v >= 70 ? "text-crisis-700" : v <= 30 ? "text-opportunity-700" : "text-ink-3";
  return (
    <div className="rounded-md border border-line-2 bg-white shadow-md px-3 py-2 text-[11px] tabular-nums">
      <div className="text-ink-3 mb-1 font-medium">{label}</div>
      <div className="text-ink-1">
        Pattern Score{" "}
        <span className="font-semibold text-[13px]">{v?.toFixed(1) ?? "—"}</span>
      </div>
      <div className={`text-[10px] mt-0.5 ${tone}`}>{zone}</div>
    </div>
  );
}
