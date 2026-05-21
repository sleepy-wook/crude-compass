/**
 * FxLineChart — USD/KRW 일별 환율 (Recharts).
 *
 * 2026-05-21: SVG hand-rolled → Recharts.
 *  - hover crosshair + tooltip (rate + 1d/7d delta + 30d 변동성)
 *  - 자체 기간 toggle (7/30/90/180일)
 */
import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useFxHistory } from "../lib/queries";
import { cn } from "../lib/utils";

type DayRange = 7 | 30 | 90 | 180;
const DAY_OPTIONS: DayRange[] = [7, 30, 90, 180];

const COLOR = "#1B3139"; // ink-1 톤

interface ChartPoint {
  date: string;        // MM-DD label
  full_date: string;   // tooltip용 full
  rate: number | null;
  delta_1d: number | null;
  delta_7d: number | null;
  vol_30d: number | null;
}

export function FxLineChart({ days: initialDays = 90 }: { days?: number }) {
  const [days, setDays] = useState<DayRange>(
    (DAY_OPTIONS.includes(initialDays as DayRange) ? initialDays : 90) as DayRange,
  );
  const { data, isLoading, isError } = useFxHistory(days);

  const points = useMemo<ChartPoint[]>(() => {
    const raw = data?.history ?? [];
    return raw.map((p) => ({
      date: p.date.slice(5),
      full_date: p.date,
      rate: p.rate,
      delta_1d: p.delta_1d,
      delta_7d: p.delta_7d,
      vol_30d: p.vol_30d,
    }));
  }, [data]);

  const latest = points[points.length - 1];

  const { yMin, yMax } = useMemo(() => {
    const all = points.map((p) => p.rate).filter((v): v is number => v != null);
    if (all.length === 0) return { yMin: 1300, yMax: 1400 };
    const min = Math.min(...all);
    const max = Math.max(...all);
    const pad = (max - min) * 0.08 || 5;
    return { yMin: Math.floor(min - pad), yMax: Math.ceil(max + pad) };
  }, [points]);

  return (
    <section className="rounded-xl border border-line-1 bg-panel">
      <header className="flex items-baseline justify-between px-4 py-3 border-b border-line-1">
        <div className="flex items-baseline gap-2">
          <h3 className="font-display text-[13px] font-semibold text-ink-1">
            USD/KRW 환율
          </h3>
          <span className="text-[10px] text-ink-3">원유 매입 원가 압력</span>
        </div>
        <div className="flex items-center gap-0.5 rounded-md border border-line-2 bg-white p-0.5">
          {DAY_OPTIONS.map((d) => (
            <button
              key={d}
              type="button"
              onClick={() => setDays(d)}
              className={cn(
                "px-2 py-0.5 text-[10.5px] rounded transition-colors tabular-nums",
                days === d
                  ? "bg-line-1 text-ink-1 font-medium"
                  : "text-ink-3 hover:text-ink-1",
              )}
            >
              {d}일
            </button>
          ))}
        </div>
      </header>

      <div className="px-2 py-3" style={{ height: 280 }}>
        {isLoading ? (
          <div className="flex items-center justify-center h-full text-[11px] text-ink-3">로딩 중...</div>
        ) : isError || points.length === 0 ? (
          <div className="flex items-center justify-center h-full text-[11px] text-ink-3">데이터 없음</div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={points} margin={{ top: 6, right: 12, bottom: 4, left: 4 }}>
              <CartesianGrid stroke="#EFEFEA" strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 10, fill: "#7A8A91" }}
                tickLine={false}
                axisLine={{ stroke: "#CFCFC8" }}
                minTickGap={40}
              />
              <YAxis
                domain={[yMin, yMax]}
                tick={{ fontSize: 10, fill: "#7A8A91" }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) => v.toFixed(0)}
                width={48}
              />
              <Tooltip content={<FxTooltip />} />
              <Line
                type="monotone"
                dataKey="rate"
                name="USD/KRW"
                stroke={COLOR}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4 }}
                connectNulls
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Footer — latest + delta + vol */}
      <footer className="flex items-center gap-4 px-4 py-2 border-t border-line-1 bg-line-1/30 text-[11px] tabular-nums flex-wrap">
        <span className="text-ink-1 font-medium">
          USD/KRW {latest?.rate?.toFixed(2) ?? "—"}
        </span>
        {latest?.delta_1d != null && (
          <span className={cn(
            latest.delta_1d > 0 ? "text-crisis-700" : latest.delta_1d < 0 ? "text-opportunity-700" : "text-ink-3",
          )}>
            1d {latest.delta_1d > 0 ? "+" : ""}{latest.delta_1d.toFixed(2)}
          </span>
        )}
        {latest?.delta_7d != null && (
          <span className={cn(
            latest.delta_7d > 0 ? "text-crisis-700" : latest.delta_7d < 0 ? "text-opportunity-700" : "text-ink-3",
          )}>
            7d {latest.delta_7d > 0 ? "+" : ""}{latest.delta_7d.toFixed(2)}
          </span>
        )}
        {latest?.vol_30d != null && (
          <span className="ml-auto text-ink-3">
            30일 변동성 <span className="text-ink-2 font-medium">{latest.vol_30d.toFixed(2)}</span>
          </span>
        )}
      </footer>
    </section>
  );
}

function FxTooltip({ active, payload, label }: {
  active?: boolean;
  payload?: Array<{ value: number; payload: ChartPoint }>;
  label?: string;
}) {
  if (!active || !payload || payload.length === 0) return null;
  const p = payload[0].payload;
  return (
    <div className="rounded-md border border-line-2 bg-white shadow-md px-3 py-2 text-[11px] tabular-nums">
      <div className="text-ink-3 mb-1 font-medium">{label}</div>
      <div className="text-ink-1 font-semibold mb-0.5">
        ₩{p.rate?.toFixed(2) ?? "—"}
      </div>
      {p.delta_1d != null && (
        <div className="text-ink-3">
          1d <span className={p.delta_1d > 0 ? "text-crisis-700" : "text-opportunity-700"}>
            {p.delta_1d > 0 ? "+" : ""}{p.delta_1d.toFixed(2)}
          </span>
        </div>
      )}
      {p.delta_7d != null && (
        <div className="text-ink-3">
          7d <span className={p.delta_7d > 0 ? "text-crisis-700" : "text-opportunity-700"}>
            {p.delta_7d > 0 ? "+" : ""}{p.delta_7d.toFixed(2)}
          </span>
        </div>
      )}
    </div>
  );
}
