/**
 * IntradayChart — 30분 단위 raw 시계열 (Recharts).
 *
 * Brent / WTI 2 ticker overlay (실시간). 최근 24h default.
 * Dubai는 라이브 시세가 유료(Platts)라 공개 API에 없음 → 한국석유공사 OPINET
 * 공식 일별 종가(PriceLineChart)로 별도 노출. 여기선 실시간 가능한 2종만.
 */
import { useMemo } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useIntradayPrices } from "../lib/queries";

interface Props {
  hours?: number;
}

const TICKER_META: Record<string, { label: string; color: string; key: "brent" | "wti" }> = {
  brent: { label: "Brent", color: "#E0A30E", key: "brent" },
  wti: { label: "WTI", color: "#0E8F5E", key: "wti" },
};

interface ChartPoint {
  ts: number; // unix ms
  label: string; // HH:MM
  brent?: number;
  wti?: number;
}

function fmtTime(ms: number): string {
  const d = new Date(ms);
  const hh = `${d.getHours()}`.padStart(2, "0");
  const mi = `${d.getMinutes()}`.padStart(2, "0");
  return `${hh}:${mi}`;
}

export function IntradayChart({ hours = 24 }: Props) {
  const { data, isLoading, isError } = useIntradayPrices(hours);
  const series = data?.series ?? [];

  // Merge ticker series → unified [{ts, brent, wti}, ...]
  const chartData = useMemo<ChartPoint[]>(() => {
    const byTs = new Map<number, ChartPoint>();
    for (const s of series) {
      const key = TICKER_META[s.ticker]?.key;
      if (!key) continue;
      for (const p of s.points) {
        const ts = new Date(p.fetched_at).getTime();
        const existing = byTs.get(ts) ?? { ts, label: fmtTime(ts) };
        existing[key] = p.price_usd;
        byTs.set(ts, existing);
      }
    }
    return Array.from(byTs.values()).sort((a, b) => a.ts - b.ts);
  }, [series]);

  const hasAny = chartData.length > 0;
  if (!isLoading && (isError || !hasAny)) {
    return null;
  }

  // Y range
  const { yMin, yMax } = useMemo(() => {
    const all: number[] = [];
    for (const p of chartData) {
      for (const v of [p.brent, p.wti]) {
        if (v != null) all.push(v);
      }
    }
    if (all.length === 0) return { yMin: 0, yMax: 100 };
    const min = Math.min(...all);
    const max = Math.max(...all);
    const pad = (max - min) * 0.08 || 1;
    return { yMin: min - pad, yMax: max + pad };
  }, [chartData]);

  const decimals = yMax - yMin < 1 ? 3 : yMax - yMin < 10 ? 2 : 1;

  return (
    <div style={{ height: 280 }}>
      {isLoading ? (
        <div className="flex items-center justify-center h-full text-[11px] text-ink-3">
          로딩 중...
        </div>
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 6, right: 12, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="#EFEFEA" strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 10, fill: "#7A8A91" }}
              tickLine={false}
              axisLine={{ stroke: "#CFCFC8" }}
              minTickGap={50}
            />
            <YAxis
              domain={[yMin, yMax]}
              tick={{ fontSize: 10, fill: "#7A8A91" }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => `$${v.toFixed(decimals)}`}
              width={52}
            />
            <Tooltip content={<IntradayTooltip decimals={decimals} />} />
            {(["brent", "wti"] as const).map((k) => (
              <Line
                key={k}
                type="monotone"
                dataKey={k}
                name={TICKER_META[k].label}
                stroke={TICKER_META[k].color}
                strokeWidth={1.4}
                dot={false}
                activeDot={{ r: 3 }}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

function IntradayTooltip({
  active,
  payload,
  label,
  decimals,
}: {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
  decimals: number;
}) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="rounded-md border border-line-2 bg-white shadow-md px-3 py-2 text-[11px] tabular-nums">
      <div className="text-ink-3 mb-1 font-medium">{label}</div>
      {payload.map((p) => (
        <div key={p.name} className="flex items-center gap-2">
          <span className="inline-block w-2.5 h-0.5" style={{ background: p.color }} />
          <span className="text-ink-1">
            {p.name}{" "}
            <span className="font-medium">${p.value?.toFixed(decimals) ?? "—"}</span>
          </span>
        </div>
      ))}
    </div>
  );
}
