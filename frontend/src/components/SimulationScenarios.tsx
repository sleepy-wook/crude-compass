/**
 * SimulationScenarios — Sub-B Honest Simulation.
 *
 * spec: docs/superpowers/specs/2026-05-18-actionable-honest-redesign.md §5
 *
 * Best/Likely/Worst 3 scenarios with explicit assumptions.
 * Backend deterministic 계산 (Brent baseline × capacity × duration × ΔP × KRW).
 */
import type { SimulationScenario } from "../lib/types";

interface Props {
  scenarios: SimulationScenario[];
}

function scenarioOrder(s: SimulationScenario): number {
  // 시각화 순서: worst (좌) · likely (중) · best (우)
  if (s.name === "worst") return 0;
  if (s.name === "likely") return 1;
  return 2;
}

function scenarioLabel(name: SimulationScenario["name"]): string {
  if (name === "worst") return "비관";
  if (name === "likely") return "기준";
  return "낙관";
}

function tone(saving_oku: number): {
  text: string;
  border: string;
  bg: string;
} {
  if (saving_oku > 0) {
    return {
      text: "text-opportunity-700",
      border: "border-opportunity-100",
      bg: "bg-opportunity-50/40",
    };
  }
  if (saving_oku < 0) {
    return {
      text: "text-crisis-700",
      border: "border-crisis-100",
      bg: "bg-crisis-50/40",
    };
  }
  return { text: "text-ink-1", border: "border-line-1", bg: "bg-panel" };
}

export function SimulationScenarios({ scenarios }: Props) {
  if (scenarios.length === 0) return null;
  const sorted = [...scenarios].sort((a, b) => scenarioOrder(a) - scenarioOrder(b));

  return (
    <div className="mb-8 pb-8 border-b border-line-1">
      <div className="flex items-baseline justify-between mb-4">
        <div className="text-[11px] uppercase tracking-wider text-ink-3">
          시뮬레이션 — 가정별 결과
        </div>
        <span className="text-[10px] text-ink-3 italic">
          backtest n=298 ±20% 신뢰구간
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {sorted.map((s) => {
          const t = tone(s.saving_krw_oku);
          return (
            <div
              key={s.name}
              className={`rounded-lg border p-4 ${t.border} ${t.bg}`}
            >
              <div className="flex items-baseline justify-between mb-2">
                <span className="text-[10px] uppercase tracking-wider text-ink-3 font-medium">
                  {scenarioLabel(s.name)}
                </span>
                <span className="text-[10px] text-ink-3 font-mono tabular-nums">
                  {s.saving_pct > 0 ? "+" : ""}
                  {s.saving_pct.toFixed(2)}%
                </span>
              </div>

              <div className="text-xs text-ink-2 mb-3 leading-snug min-h-[2.2em]">
                {s.label}
              </div>

              <div className={`font-display text-2xl font-semibold tabular-nums mb-3 ${t.text}`}>
                {s.saving_krw_oku > 0 ? "+" : ""}
                {s.saving_krw_oku.toLocaleString()}억
              </div>

              {/* Assumptions explicit */}
              <div className="pt-3 border-t border-line-1 space-y-1 text-[11px]">
                <AssumeRow label="Brent" value={`$${s.assumptions.brent_usd.toFixed(0)}`} />
                <AssumeRow label="USD/KRW" value={s.assumptions.usd_krw.toFixed(0)} />
                <AssumeRow
                  label="VLCC 운임"
                  value={
                    s.assumptions.vlcc_freight_multiplier === 1.0
                      ? "평균"
                      : s.assumptions.vlcc_freight_multiplier > 1.0
                        ? `+${Math.round((s.assumptions.vlcc_freight_multiplier - 1) * 100)}%`
                        : `${Math.round((s.assumptions.vlcc_freight_multiplier - 1) * 100)}%`
                  }
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer disclaimer */}
      <p className="text-[11px] text-ink-3 mt-4 leading-relaxed">
        📌 K-Petroleum 80만 b/d × Term 비중 변화 × Brent 가격 차이 × USD/KRW 단순 공식.
        가정값은 시연용 baseline (2026/5 시장: Brent $108, KRW 1,500 / UBS forecast end 2026 $90 → 2027 $85).
      </p>
    </div>
  );
}

function AssumeRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between">
      <span className="text-ink-3">{label}</span>
      <span className="font-mono tabular-nums text-ink-1">{value}</span>
    </div>
  );
}
