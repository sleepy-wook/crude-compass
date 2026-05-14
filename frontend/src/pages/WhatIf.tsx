import { useState, useMemo, useEffect } from "react";
import { useBacktestPredictions, useBacktestResults } from "../lib/queries";
import { MissionTypePill } from "../components/StatusPill";
import { Term } from "../components/Glossary";
import { formatPct, formatScore, formatUsd } from "../lib/utils";

export function WhatIf() {
  const preds = useBacktestPredictions(300);
  const summary = useBacktestResults();
  const predictions = preds.data?.predictions || [];

  // Sort by date asc for slider
  const sorted = useMemo(
    () =>
      [...predictions].sort((a, b) =>
        a.as_of_date.localeCompare(b.as_of_date)
      ),
    [predictions]
  );

  // 첫 시점 자동 선택 = 가장 최근 (sorted.length-1)
  const [idx, setIdx] = useState<number | null>(null);
  useEffect(() => {
    if (idx === null && sorted.length > 0) {
      setIdx(sorted.length - 1);
    }
  }, [sorted.length, idx]);
  const current = idx === null ? undefined : sorted[idx];

  return (
    <div className="max-w-6xl mx-auto">
      <header className="mb-6">
        <h1 className="font-display text-3xl font-semibold">
          과거 시점 복원 + AI 추천 검증
        </h1>
        <p className="text-sm text-ink-2 mt-2 max-w-3xl">
          데이터: 2019-2026 사이 300개 시점 · 슬라이더로 과거 임의 시점 선택 → AI가
          <strong> 그 시점 데이터만 보고 추천한 결정</strong>과 실제 30/90일 후 가격 비교.
        </p>
      </header>

      {/* Backtest summary card */}
      {summary.data?.summary && (
        <section className="mb-6 bg-panel rounded-xl border border-line-1 p-6 grid grid-cols-5 gap-4">
          <Stat label="총 샘플" value={`${summary.data.summary.n_active}건`} />
          <Stat
            label="적중률"
            value={formatPct(summary.data.summary.hit_rate_pct)}
            accent="ok"
          />
          <Stat
            label="평균 비용 절감"
            value={formatPct(summary.data.summary.avg_save_pct, 2)}
            accent="ok"
          />
          <Stat label="HEDGE" value={`${summary.data.summary.n_hedge}건`} accent="crisis" />
          <Stat label="OPP" value={`${summary.data.summary.n_opp}건`} accent="opp" />
        </section>
      )}

      {/* Time travel slider */}
      <section className="mb-6 bg-panel rounded-xl border border-line-1 p-6">
        <div className="flex items-baseline justify-between mb-2">
          <h2 className="text-xs uppercase tracking-widest text-ink-3">
            시점 선택 ({sorted.length}개 중)
          </h2>
          <span className="text-xs font-mono text-ink-3">
            {sorted[0]?.as_of_date} → {sorted[sorted.length - 1]?.as_of_date}
          </span>
        </div>
        <p className="text-xs text-ink-3 mb-4 leading-relaxed">
          이 backtest는 4 source × 7년 (GDELT / EIA / OPEC / FX + Dubai 종가).
          <strong className="text-ink-2"> AIS · OilPriceAPI는 realtime-only이라 production 전용</strong> — backtest 데이터 자체가 없음.
        </p>

        {sorted.length > 0 && (
          <>
            <input
              type="range"
              min={0}
              max={sorted.length - 1}
              value={idx ?? 0}
              onChange={(e) => setIdx(Number(e.target.value))}
              className="w-full mb-3 accent-crisis-500"
            />
            {/* Zone legend — slider 자체에 띠 추가 대신 명료한 인라인 legend */}
            <div className="flex items-center justify-center gap-4 text-[11px] text-ink-3 mb-4">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-crisis-500" /> 위기 (70+)
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-ink-4" /> 관망 (30~70)
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-opportunity-500" /> 기회 (~30)
              </span>
            </div>
            <div className="text-center mb-6">
              <div className="text-xs text-ink-3 mb-1">선택된 시점</div>
              <div className="font-display text-2xl font-semibold flex items-center justify-center gap-3">
                {current?.as_of_date}
                {current && current.pattern_score != null && (() => {
                  const ps = current.pattern_score;
                  return (
                    <span
                      className={
                        ps >= 70
                          ? "text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-crisis-50 text-crisis-700 border border-crisis-100"
                          : ps <= 30
                          ? "text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-opportunity-50 text-opportunity-700 border border-opportunity-100"
                          : "text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-line-1 text-ink-3 border border-line-2"
                      }
                    >
                      {ps >= 70 ? "위기" : ps <= 30 ? "기회" : "관망"}
                    </span>
                  );
                })()}
              </div>
            </div>
          </>
        )}

        {current && (
          <div className="border-t border-line-1 pt-5 grid grid-cols-3 gap-6">
            <div>
              <div className="text-[10px] uppercase tracking-widest text-ink-3 mb-2">
                AI 추천 (그 날짜)
              </div>
              <div className="flex items-center gap-2 mb-1">
                {current.mission_type && <MissionTypePill type={current.mission_type} />}
                <span className="text-xs text-ink-3">
                  <Term name="PATTERN_SCORE" position="bottom">위기점수</Term>{" "}
                  {formatScore(current.pattern_score)}
                </span>
              </div>
              <div className="text-sm font-medium">
                {current.action_type === "new_mission"
                  ? `${current.mission_type === "HEDGE" ? "Term" : "Spot"} ${current.target_pct}% (${current.duration_days}일)`
                  : "관망 (대기)"}
              </div>
              <div className="text-xs text-ink-3 mt-1">
                자신감 {formatScore(current.confidence_score)}
              </div>
            </div>

            <div>
              <div className="text-[10px] uppercase tracking-widest text-ink-3 mb-2">
                Dubai유 가격 (그 날짜 → 30일 후)
              </div>
              <div className="text-2xl font-display font-semibold">
                {formatUsd(current.dubai_at_signal_usd)} →{" "}
                {formatUsd(current.dubai_30d_usd)}
              </div>
              <div className="text-xs text-ink-3 mt-1">
                30일 변동{" "}
                {current.dubai_at_signal_usd && current.dubai_30d_usd
                  ? formatPct(
                      ((current.dubai_30d_usd - current.dubai_at_signal_usd) /
                        current.dubai_at_signal_usd) *
                        100,
                      2
                    )
                  : "—"}
              </div>
            </div>

            <div>
              <div className="text-[10px] uppercase tracking-widest text-ink-3 mb-2">
                AI 추천 따랐을 때 절감률
              </div>
              <div className="grid grid-cols-3 gap-2">
                <Outcome label="7일" value={current.saving_7d_pct} />
                <Outcome label="30일" value={current.saving_30d_pct} />
                <Outcome label="90일" value={current.saving_90d_pct} />
              </div>
              <div className="text-[11px] text-ink-3 mt-2">
                양수 = 평시(Term 60 / Spot 40) 대비 절감 (좋음)
              </div>
            </div>
          </div>
        )}
      </section>

      {/* Sample list */}
      <section className="bg-panel rounded-xl border border-line-1 p-6">
        <h2 className="text-xs uppercase tracking-widest text-ink-3 mb-3">
          최근 30개 AI 추천 (Backtest sample · 클릭 시 슬라이더 이동)
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[10px] uppercase tracking-widest text-ink-3 border-b border-line-1">
                <th className="py-2">날짜</th>
                <th>추천</th>
                <th>위기점수</th>
                <th>자신감</th>
                <th>목표</th>
                <th>30일 절감</th>
              </tr>
            </thead>
            <tbody>
              {sorted.slice(-30).reverse().map((p, i) => (
                <tr
                  key={`${p.as_of_date}-${i}`}
                  onClick={() =>
                    setIdx(sorted.findIndex((x) => x.as_of_date === p.as_of_date))
                  }
                  className="border-b border-line-1 cursor-pointer hover:bg-paper"
                >
                  <td className="py-2 font-mono text-xs">{p.as_of_date}</td>
                  <td>
                    {p.mission_type && <MissionTypePill type={p.mission_type} />}
                  </td>
                  <td className="font-mono text-xs">{formatScore(p.pattern_score)}</td>
                  <td className="font-mono text-xs">{formatScore(p.confidence_score)}</td>
                  <td className="font-mono text-xs">{p.target_pct ?? "—"}%</td>
                  <td
                    className={`font-mono text-xs ${
                      (p.saving_30d_pct || 0) > 0
                        ? "text-opportunity-700"
                        : (p.saving_30d_pct || 0) < 0
                        ? "text-crisis-700"
                        : "text-ink-3"
                    }`}
                  >
                    {formatPct(p.saving_30d_pct, 2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function Stat({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: "ok" | "crisis" | "opp";
}) {
  const cls =
    accent === "ok" || accent === "opp"
      ? "text-opportunity-700"
      : accent === "crisis"
      ? "text-crisis-700"
      : "text-ink";
  return (
    <div>
      <div className="text-[10px] uppercase tracking-widest text-ink-3 mb-1">{label}</div>
      <div className={`font-display text-xl font-semibold ${cls}`}>{value}</div>
    </div>
  );
}

function Outcome({ label, value }: { label: string; value: number | null | undefined }) {
  const positive = (value || 0) > 0;
  const negative = (value || 0) < 0;
  return (
    <div className="text-center border border-line-1 rounded-md p-2">
      <div className="text-[10px] text-ink-3">{label}</div>
      <div
        className={`text-sm font-mono ${
          positive ? "text-opportunity-700" : negative ? "text-crisis-700" : "text-ink-3"
        }`}
      >
        {formatPct(value, 2)}
      </div>
    </div>
  );
}
