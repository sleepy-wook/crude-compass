/**
 * BacktestPage — /backtest
 *
 * D-2 사용자 요청: Investigation 하단에 묻혀 있던 BacktestTimeSlider를 별도 메뉴로.
 * 과거 권고 적중률 검증 + detail row list 표시.
 *
 * 데이터 source: silver.backtest_predictions (현재 limit 300 fetch).
 * Investigation에서 "→ 과거 권고 검증" link로 진입.
 */
import { Link } from "react-router-dom";
import { useMemo, useState } from "react";
import { useBacktestPredictions } from "../lib/queries";
import type { BacktestPrediction } from "../lib/types";
import { formatPct, formatScore } from "../lib/utils";

type DirectionFilter = "all" | "HEDGE" | "OPPORTUNITY" | "wait";
type HitFilter = "all" | "hit" | "miss";

// Hit/miss derived from saving_30d_pct (>0 = hit, <0 = miss, null = unmeasurable)
function outcomeOf(p: BacktestPrediction): "hit" | "miss" | "unknown" {
  if (p.saving_30d_pct == null) return "unknown";
  return p.saving_30d_pct > 0 ? "hit" : "miss";
}

// Dubai 30-day price change pct derived from at_signal vs 30d snapshot
function dubaiChange30dPct(p: BacktestPrediction): number | null {
  if (p.dubai_at_signal_usd == null || p.dubai_30d_usd == null || p.dubai_at_signal_usd === 0) return null;
  return ((p.dubai_30d_usd - p.dubai_at_signal_usd) / p.dubai_at_signal_usd) * 100;
}

export function BacktestPage() {
  const preds = useBacktestPredictions(300);
  const [dir, setDir] = useState<DirectionFilter>("all");
  const [hit, setHit] = useState<HitFilter>("all");

  const sorted = useMemo(() => {
    if (!preds.data?.predictions) return [];
    // 최신순
    return [...preds.data.predictions].sort((a, b) =>
      a.as_of_date < b.as_of_date ? 1 : -1,
    );
  }, [preds.data]);

  const filtered = useMemo(() => {
    return sorted.filter((p) => {
      if (dir === "wait") {
        if (p.action_type !== "wait") return false;
      } else if (dir !== "all") {
        if (p.mission_type !== dir) return false;
      }
      const oc = outcomeOf(p);
      if (hit === "hit" && oc !== "hit") return false;
      if (hit === "miss" && oc !== "miss") return false;
      return true;
    });
  }, [sorted, dir, hit]);

  // Stats — outcome derived
  const stats = useMemo(() => {
    const total = sorted.length;
    const hedge = sorted.filter((p) => p.mission_type === "HEDGE").length;
    const opp = sorted.filter((p) => p.mission_type === "OPPORTUNITY").length;
    const wait = sorted.filter((p) => p.action_type === "wait").length;
    const hits = sorted.filter((p) => outcomeOf(p) === "hit").length;
    const misses = sorted.filter((p) => outcomeOf(p) === "miss").length;
    const measurable = hits + misses;
    const hitRate = measurable > 0 ? (hits / measurable) * 100 : null;
    return { total, hedge, opp, wait, hits, misses, hitRate };
  }, [sorted]);

  return (
    <div className="max-w-6xl mx-auto px-8 py-10">
      <header className="mb-8">
        <div className="text-[11px] uppercase tracking-[0.2em] text-ink-3 mb-1.5">Backtest</div>
        <h1 className="font-display text-[28px] md:text-[32px] font-semibold tracking-tight text-ink-1 leading-tight">
          과거 권고 검증
        </h1>
        <p className="text-[13px] text-ink-3 mt-2 leading-relaxed">
          silver.backtest_predictions — 지난 7년 동안 Supervisor가 동일 시그널 조합에 어떻게 권고했고
          실제 두바이유 가격이 30일 후 어떻게 변동했는지 검증.
        </p>
        <div className="mt-3">
          <Link to="/ask" className="text-[12px] text-ink-3 hover:text-ink-1">
            ← Investigation으로 돌아가기
          </Link>
        </div>
      </header>

      {/* Summary stats */}
      <section className="mb-8 grid grid-cols-2 md:grid-cols-5 gap-4">
        <StatCard label="전체 권고" value={`${stats.total}건`} />
        <StatCard label="위험방어" value={`${stats.hedge}건`} tone="crisis" />
        <StatCard label="기회포착" value={`${stats.opp}건`} tone="opportunity" />
        <StatCard label="관망" value={`${stats.wait}건`} />
        <StatCard
          label="적중률"
          value={stats.hitRate != null ? `${stats.hitRate.toFixed(1)}%` : "—"}
          sub={`${stats.hits} hit / ${stats.misses} miss`}
        />
      </section>

      {/* Filters */}
      <div className="mb-4 flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-1 text-[11px]">
          <span className="text-ink-3 uppercase tracking-wider mr-1">방향</span>
          {(["all", "HEDGE", "OPPORTUNITY", "wait"] as DirectionFilter[]).map((d) => (
            <button
              key={d}
              type="button"
              onClick={() => setDir(d)}
              className={
                dir === d
                  ? "px-2.5 py-1 rounded bg-ink-1 text-paper font-medium"
                  : "px-2.5 py-1 rounded text-ink-3 hover:text-ink-1 hover:bg-line-1"
              }
            >
              {d === "all" ? "전체" : d === "HEDGE" ? "위험방어" : d === "OPPORTUNITY" ? "기회포착" : "관망"}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1 text-[11px]">
          <span className="text-ink-3 uppercase tracking-wider mr-1">결과</span>
          {(["all", "hit", "miss"] as HitFilter[]).map((h) => (
            <button
              key={h}
              type="button"
              onClick={() => setHit(h)}
              className={
                hit === h
                  ? "px-2.5 py-1 rounded bg-ink-1 text-paper font-medium"
                  : "px-2.5 py-1 rounded text-ink-3 hover:text-ink-1 hover:bg-line-1"
              }
            >
              {h === "all" ? "전체" : h === "hit" ? "Hit" : "Miss"}
            </button>
          ))}
        </div>
        <span className="ml-auto text-[11px] text-ink-3">
          {filtered.length} / {sorted.length}건 표시
        </span>
      </div>

      {/* Predictions list */}
      <section className="border border-line-1 rounded-xl overflow-hidden">
        <div className="grid grid-cols-[110px_90px_80px_110px_1fr_80px] gap-4 px-4 py-2.5 bg-line-1/40 text-[10px] uppercase tracking-wider text-ink-3 font-medium border-b border-line-1">
          <div>날짜</div>
          <div>방향</div>
          <div>점수</div>
          <div>비중</div>
          <div>30일 후 변동</div>
          <div className="text-right">결과</div>
        </div>
        {preds.isLoading && (
          <div className="p-6 text-sm text-ink-3">불러오는 중...</div>
        )}
        {!preds.isLoading && filtered.length === 0 && (
          <div className="p-6 text-sm text-ink-3">필터 조건에 맞는 권고가 없습니다.</div>
        )}
        {!preds.isLoading &&
          filtered.slice(0, 100).map((p) => {
            const oc = outcomeOf(p);
            const isHit = oc === "hit";
            const isMiss = oc === "miss";
            const dubaiChange = dubaiChange30dPct(p);
            const typeColor =
              p.mission_type === "HEDGE"
                ? "text-crisis-700 bg-crisis-50"
                : p.mission_type === "OPPORTUNITY"
                  ? "text-opportunity-700 bg-opportunity-50"
                  : "text-ink-3 bg-line-1";
            const typeLabel =
              p.action_type === "wait"
                ? "관망"
                : p.mission_type === "HEDGE"
                  ? "위험방어"
                  : "기회포착";
            return (
              <div
                key={p.as_of_date + "-" + (p.mission_type ?? "wait")}
                className="grid grid-cols-[110px_90px_80px_110px_1fr_80px] gap-4 px-4 py-2.5 border-b border-line-1 last:border-0 text-[12px] hover:bg-line-1/30"
              >
                <div className="font-mono text-ink-2">{p.as_of_date}</div>
                <div>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-medium ${typeColor}`}>
                    {typeLabel}
                  </span>
                </div>
                <div className="font-mono text-ink-2 tabular-nums">{formatScore(p.pattern_score)}</div>
                <div className="font-mono text-ink-2 tabular-nums">
                  {p.target_pct != null ? `${p.target_pct}%` : "—"}
                </div>
                <div className="font-mono text-ink-2 tabular-nums">
                  {dubaiChange != null
                    ? `${dubaiChange > 0 ? "+" : ""}${formatPct(dubaiChange)}`
                    : "—"}
                  {p.saving_30d_pct != null && (
                    <span className="text-ink-3 ml-2">
                      절감 {p.saving_30d_pct > 0 ? "+" : ""}
                      {formatPct(p.saving_30d_pct)}
                    </span>
                  )}
                </div>
                <div className="text-right">
                  {isHit && (
                    <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-opportunity-50 text-opportunity-700">
                      Hit
                    </span>
                  )}
                  {isMiss && (
                    <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-crisis-50 text-crisis-700">
                      Miss
                    </span>
                  )}
                  {!isHit && !isMiss && (
                    <span className="text-[10px] text-ink-3">—</span>
                  )}
                </div>
              </div>
            );
          })}
        {!preds.isLoading && filtered.length > 100 && (
          <div className="px-4 py-2 text-[11px] text-ink-3 bg-line-1/30 text-center">
            처음 100건만 표시 — 필터로 좁히면 더 많이 볼 수 있습니다.
          </div>
        )}
      </section>

      <div className="h-20" />
    </div>
  );
}

function StatCard({
  label,
  value,
  sub,
  tone,
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: "crisis" | "opportunity";
}) {
  const toneCls =
    tone === "crisis"
      ? "text-crisis-700"
      : tone === "opportunity"
        ? "text-opportunity-700"
        : "text-ink-1";
  return (
    <div className="border border-line-2 rounded-lg p-3 bg-panel">
      <div className="text-[10px] uppercase tracking-wider text-ink-3 mb-1">{label}</div>
      <div className={`font-display text-lg font-semibold tabular-nums ${toneCls}`}>{value}</div>
      {sub && <div className="text-[10px] text-ink-3 mt-0.5 font-mono">{sub}</div>}
    </div>
  );
}
