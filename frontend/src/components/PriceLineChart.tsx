/**
 * PriceLineChart — Dubai/Brent/WTI 일별 가격 (Recharts).
 *
 * 2026-05-21: SVG hand-rolled → Recharts 마이그레이션.
 *  - hover crosshair + tooltip
 *  - 자체 기간 toggle (7/30/90/180일)
 *  - legend는 카드 footer에 latest 값과 함께
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
import { usePricesWide } from "../lib/queries";
import { cn } from "../lib/utils";

type DayRange = 7 | 30 | 90 | 180;
const DAY_OPTIONS: DayRange[] = [7, 30, 90, 180];

const COLORS = {
  dubai: "#1B3139",
  brent: "#F59E0B",
  wti: "#10B981",
};

interface ChartPoint {
  trade_date: string;
  dubai?: number | null;
  brent?: number | null;
  wti?: number | null;
}

export function PriceLineChart({ days: initialDays = 90 }: { days?: number }) {
  const [days, setDays] = useState<DayRange>(
    (DAY_OPTIONS.includes(initialDays as DayRange) ? initialDays : 90) as DayRange,
  );
  const { data, isLoading, isError } = usePricesWide(days);

  const points = useMemo<ChartPoint[]>(() => {
    const raw = data?.prices ?? [];
    return raw.map((p) => ({
      trade_date: p.trade_date.slice(5), // MM-DD
      dubai: p.dubai_usd,
      brent: p.brent_usd,
      wti: p.wti_usd,
    }));
  }, [data]);

  const latest = (data?.prices ?? [])[(data?.prices ?? []).length - 1];
  const spread = latest?.brent_dubai_spread_usd;

  // Y range — 시각적 padding
  const { yMin, yMax } = useMemo(() => {
    const all: number[] = [];
    for (const p of points) {
      for (const v of [p.dubai, p.brent, p.wti]) {
        if (v != null) all.push(v);
      }
    }
    if (all.length === 0) return { yMin: 0, yMax: 100 };
    const min = Math.min(...all);
    const max = Math.max(...all);
    const pad = (max - min) * 0.08 || 1;
    return { yMin: Math.floor(min - pad), yMax: Math.ceil(max + pad) };
  }, [points]);

  return (
    <section className="rounded-xl border border-line-1 bg-panel">
      <header className="flex items-baseline justify-between px-4 py-3 border-b border-line-1">
        <div className="flex items-baseline gap-2">
          <h3 className="font-display text-[13px] font-semibold text-ink-1">
            유종별 가격
          </h3>
          <span className="text-[10px] text-ink-3">두바이 기준 · 한국석유공사 OPINET 공식 종가</span>
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
          <div className="flex items-center justify-center h-full text-[11px] text-ink-3">
            로딩 중...
          </div>
        ) : isError || points.length === 0 ? (
          <div className="flex items-center justify-center h-full text-[11px] text-ink-3">
            데이터 없음
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={points} margin={{ top: 6, right: 12, bottom: 4, left: 4 }}>
              <CartesianGrid stroke="#EFEFEA" strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="trade_date"
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
                tickFormatter={(v) => `$${v}`}
                width={40}
              />
              <Tooltip content={<PriceTooltip />} />
              <Line
                type="monotone"
                dataKey="dubai"
                name="Dubai"
                stroke={COLORS.dubai}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4 }}
                connectNulls
              />
              <Line
                type="monotone"
                dataKey="brent"
                name="Brent"
                stroke={COLORS.brent}
                strokeWidth={1.4}
                dot={false}
                activeDot={{ r: 3 }}
                connectNulls
              />
              <Line
                type="monotone"
                dataKey="wti"
                name="WTI"
                stroke={COLORS.wti}
                strokeWidth={1.4}
                dot={false}
                activeDot={{ r: 3 }}
                connectNulls
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Footer — latest values + spread */}
      <footer className="flex items-center gap-4 px-4 py-2 border-t border-line-1 bg-line-1/30 text-[11px] tabular-nums flex-wrap">
        <Legend color={COLORS.dubai} label="Dubai" value={latest?.dubai_usd} weight="bold" />
        <Legend color={COLORS.brent} label="Brent" value={latest?.brent_usd} />
        <Legend color={COLORS.wti} label="WTI" value={latest?.wti_usd} />
        {spread != null && (
          <span className="ml-auto text-ink-3">
            Brent-Dubai spread{" "}
            <span className="text-ink-2 font-medium">${spread.toFixed(2)}</span>
          </span>
        )}
      </footer>
    </section>
  );
}

function Legend({
  color,
  label,
  value,
  weight,
}: {
  color: string;
  label: string;
  value: number | null | undefined;
  weight?: "bold";
}) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="inline-block w-3 h-0.5" style={{ background: color }} />
      <span className={cn("text-ink-3", weight === "bold" && "text-ink-1 font-medium")}>
        {label} ${value?.toFixed(2) ?? "—"}
      </span>
    </span>
  );
}

function PriceTooltip({ active, payload, label }: {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
}) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="rounded-md border border-line-2 bg-white shadow-md px-3 py-2 text-[11px] tabular-nums">
      <div className="text-ink-3 mb-1 font-medium">{label}</div>
      {payload.map((p) => (
        <div key={p.name} className="flex items-center gap-2">
          <span className="inline-block w-2.5 h-0.5" style={{ background: p.color }} />
          <span className="text-ink-1">
            {p.name} <span className="font-medium">${p.value?.toFixed(2) ?? "—"}</span>
          </span>
        </div>
      ))}
    </div>
  );
}
