/**
 * SimilarPastWidget — ★ D-4 wow anchor.
 *
 * spec: docs/superpowers/specs/2026-05-18-market-memory-decision-platform.md §3 ★ Wow 1
 *
 * 오늘 시그널 입력 → backtest_predictions에서 비슷한 7건 retrieve.
 * 평균 outcome + best/worst case + 가장 유사한 3건 detail.
 *
 * 진짜 데이터 100%: 매니저가 "이거 어디서?" 물으면 backtest row 참조 가능.
 */
import { useMarketMemorySimilar } from "../lib/queries";
import { formatPct, formatUsd, formatScore } from "../lib/utils";
import type { PatternScoreCurrent } from "../lib/types";

interface Props {
  cur: PatternScoreCurrent | null | undefined;
}

function strengthBand(score: number | null | undefined): {
  label: string;
  level: string;
  tone: "crisis" | "ok" | "ink";
} {
  if (score == null) return { label: "데이터 없음", level: "—", tone: "ink" };
  if (score >= 70) return { label: "위기 시그널 강함", level: `${Math.round(score / 10)}/10`, tone: "crisis" };
  if (score <= 30) return { label: "기회 시그널 강함", level: `${Math.round((100 - score) / 10)}/10`, tone: "ok" };
  return { label: "혼재 신호", level: "5/10", tone: "ink" };
}

function missionTypeOf(cur: PatternScoreCurrent | null | undefined): string | null {
  if (!cur || cur.pattern_score == null) return null;
  if (cur.pattern_score >= 70) return "HEDGE";
  if (cur.pattern_score <= 30) return "OPPORTUNITY";
  return null;
}

export function SimilarPastWidget({ cur }: Props) {
  const score = cur?.pattern_score ?? null;
  const missionType = missionTypeOf(cur);
  const band = strengthBand(score);

  const { data, isLoading, isError } = useMarketMemorySimilar(score, missionType);

  return (
    <section className="bg-panel border border-line-1 rounded-2xl p-7 md:p-8">
      {/* Header */}
      <div className="flex items-baseline justify-between mb-5">
        <div>
          <h2 className="font-display text-xl md:text-2xl font-semibold tracking-tight text-ink-1">
            {band.label}{" "}
            <span className={`tabular-nums ${band.tone === "crisis" ? "text-crisis-700" : band.tone === "ok" ? "text-opportunity-700" : "text-ink-3"}`}>
              {band.level}
            </span>
          </h2>
        </div>
        <div className="text-[11px] text-ink-3 text-right">
          {data?.lakebase_available === false ? (
            <span>backtest 연결 준비 중</span>
          ) : (
            <span>n={data?.summary?.n ?? "—"} · 7y backtest</span>
          )}
        </div>
      </div>

      {/* Loading / Empty / Error */}
      {isLoading && (
        <div className="space-y-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-12 bg-line-1/40 rounded animate-pulse" />
          ))}
        </div>
      )}

      {!isLoading && (isError || data?.lakebase_available === false) && (
        <div className="bg-line-1/40 rounded-lg p-5 text-sm text-ink-2 leading-relaxed">
          과거 시장 메모리를 불러올 수 없습니다. 데이터 연결이 완료되면 비슷한
          시그널 조합의 과거 7년 결과 분포가 여기에 표시됩니다.
        </div>
      )}

      {!isLoading && data?.lakebase_available && data.summary?.n && data.summary.n > 0 && (
        <div className="space-y-5">
          {/* Hero stat — narrative */}
          <p className="text-base md:text-lg text-ink-1 leading-relaxed">
            지난 7년 비슷한 시장 상황이{" "}
            <span className="font-semibold text-ink-1">{data.summary.n}번</span>{" "}
            있었습니다. 그때 두바이유는 30일 후 평균{" "}
            <span
              className={`font-semibold tabular-nums ${
                (data.summary.avg_dubai_change_30d_pct ?? 0) >= 0
                  ? "text-crisis-700"
                  : "text-opportunity-700"
              }`}
            >
              {formatPct(data.summary.avg_dubai_change_30d_pct, 1)}
            </span>{" "}
            변동, AI 권고를 따랐다면 평균{" "}
            <span
              className={`font-semibold tabular-nums ${
                (data.summary.avg_saving_30d_pct ?? 0) > 0
                  ? "text-opportunity-700"
                  : "text-crisis-700"
              }`}
            >
              {formatPct(data.summary.avg_saving_30d_pct, 2)}
            </span>{" "}
            절감했습니다.
          </p>

          {/* Stat row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pb-5 border-b border-line-1">
            <Stat
              label="유사 사례"
              value={`${data.summary.n}건`}
              hint="n=4 · 7y backtest"
            />
            <Stat
              label="평균 절감"
              value={formatPct(data.summary.avg_saving_30d_pct, 2)}
              hint="30일 기준"
              tone={(data.summary.avg_saving_30d_pct ?? 0) > 0 ? "ok" : "crisis"}
            />
            <Stat
              label="적중률"
              value={formatPct(data.summary.hit_rate_pct, 1)}
              hint="긍정 outcome 비율"
              tone="ok"
            />
            <Stat
              label="가격 변동"
              value={formatPct(data.summary.avg_dubai_change_30d_pct, 1)}
              hint="두바이 30일"
              tone={(data.summary.avg_dubai_change_30d_pct ?? 0) >= 0 ? "crisis" : "ok"}
            />
          </div>

          {/* Best / Worst case */}
          {(data.summary.best_saving_30d_pct != null ||
            data.summary.worst_saving_30d_pct != null) && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pb-5 border-b border-line-1">
              <div className="bg-opportunity-50/50 border border-opportunity-100 rounded-lg p-3">
                <div className="text-[11px] text-ink-3 mb-1">최고 사례 (Best)</div>
                <div className="font-display text-base font-semibold text-opportunity-700 tabular-nums">
                  {formatPct(data.summary.best_saving_30d_pct, 2)}
                </div>
              </div>
              <div className="bg-crisis-50/50 border border-crisis-100 rounded-lg p-3">
                <div className="text-[11px] text-ink-3 mb-1">최악 사례 (Worst)</div>
                <div className="font-display text-base font-semibold text-crisis-700 tabular-nums">
                  {formatPct(data.summary.worst_saving_30d_pct, 2)}
                </div>
              </div>
            </div>
          )}

          {/* Top 3 most similar */}
          {data.top_matches.length > 0 && (
            <div>
              <div className="text-[11px] uppercase tracking-wider text-ink-3 mb-3">
                가장 유사한 과거 시점 {Math.min(3, data.top_matches.length)}건
              </div>
              <div className="space-y-2">
                {data.top_matches.slice(0, 3).map((m, i) => (
                  <div
                    key={`${m.as_of_date}-${i}`}
                    className="flex items-center gap-3 text-[13px] py-2 border-b border-line-1 last:border-0"
                  >
                    <span className="font-mono text-ink-3 tabular-nums w-24 shrink-0">
                      {m.as_of_date}
                    </span>
                    <span className="text-ink-2 w-16 shrink-0">
                      위기 {formatScore(m.pattern_score)}
                    </span>
                    <span className="text-ink-2 w-28 shrink-0">
                      두바이 {formatUsd(m.dubai_at_signal_usd)} → {formatUsd(m.dubai_30d_usd)}
                    </span>
                    <span
                      className={`font-mono tabular-nums ml-auto ${
                        (m.saving_30d_pct ?? 0) > 0
                          ? "text-opportunity-700"
                          : (m.saving_30d_pct ?? 0) < 0
                            ? "text-crisis-700"
                            : "text-ink-3"
                      }`}
                    >
                      {(m.saving_30d_pct ?? 0) > 0 ? "+" : ""}
                      {formatPct(m.saving_30d_pct, 2)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Honesty note — minimal */}
          <p className="text-[11px] text-ink-3 pt-3 border-t border-line-1">
            7년 백테스트 n={data.summary.n} · AI가 결정하지 않습니다
          </p>
        </div>
      )}

      {!isLoading &&
        data?.lakebase_available &&
        (!data.summary?.n || data.summary.n === 0) && (
          <div className="bg-line-1/40 rounded-lg p-5 text-sm text-ink-2 leading-relaxed">
            이 시그널 강도에 해당하는 과거 데이터가 부족합니다 (n=0). 시간이
            지나며 과거 검증 샘플이 누적되면 여기에 분포가 표시됩니다.
          </div>
        )}
    </section>
  );
}

function Stat({
  label,
  value,
  hint,
  tone,
}: {
  label: string;
  value: string;
  hint: string;
  tone?: "ok" | "crisis" | "ink";
}) {
  const color =
    tone === "ok"
      ? "text-opportunity-700"
      : tone === "crisis"
        ? "text-crisis-700"
        : "text-ink-1";
  return (
    <div>
      <div className="text-[10px] uppercase tracking-widest text-ink-3 mb-1">{label}</div>
      <div className={`font-display text-xl font-semibold tabular-nums ${color}`}>
        {value}
      </div>
      <div className="text-[10px] text-ink-3 mt-0.5">{hint}</div>
    </div>
  );
}
