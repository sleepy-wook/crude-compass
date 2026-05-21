/**
 * DailyReportHero — Dashboard 상단 (reports model 2026-05-21 Phase 6).
 *
 * 매일 06:30 KST cron이 생성한 daily_report 1건 표시.
 * - 비중 제안 (lean_hedge / neutral / lean_opportunity) + Term/Spot delta
 * - 신뢰도 + 시나리오 scenarios (base/bull/bear 예상 절감)
 * - 매니저용 reasoning 1단락
 * - "참고용" 라벨 (실제 OSP 결재는 매니저)
 * - read-only — 액션 없음
 */
import { Network } from "lucide-react";
import { useDailyReportToday } from "../lib/queries";
import { cn } from "../lib/utils";

const DIRECTION_META: Record<string, { label: string; tone: string }> = {
  lean_hedge: { label: "위험방어 쪽으로 소폭 이동", tone: "text-crisis-700 bg-crisis-50 border-crisis-200" },
  neutral: { label: "중립 유지", tone: "text-ink-2 bg-line-1 border-line-2" },
  lean_opportunity: { label: "기회포착 쪽으로 소폭 이동", tone: "text-opportunity-700 bg-opportunity-50 border-opportunity-200" },
};

export function DailyReportHero() {
  const { data, isLoading } = useDailyReportToday();
  const daily = data?.daily_report;

  if (isLoading) {
    return (
      <section className="bg-panel border border-line-1 rounded-2xl p-5 text-[12px] text-ink-3">
        오늘 일일 보고서 불러오는 중...
      </section>
    );
  }

  if (!daily) {
    return (
      <section className="bg-panel border border-line-1 rounded-2xl p-5">
        <div className="text-[10px] uppercase tracking-wider text-ink-3 mb-1">
          오늘의 비중 제안
        </div>
        <div className="text-[13px] text-ink-2">
          오늘 일일 보고서 미생성 (06:30 KST cron 대기 중)
        </div>
      </section>
    );
  }

  const rs = daily.ratio_suggestion || {};
  const dir = rs.direction || "neutral";
  const meta = DIRECTION_META[dir] ?? DIRECTION_META.neutral;
  const termDelta = rs.term_delta_pct || "0";
  const spotDelta = rs.spot_delta_pct || "0";
  const baseTerm = 60;
  const baseSpot = 40;
  const newTerm = baseTerm + parseInt(termDelta, 10);
  const newSpot = baseSpot + parseInt(spotDelta, 10);
  const scenarios = rs.scenarios || [];

  return (
    <section className="bg-panel border border-line-1 rounded-2xl p-5">
      <header className="flex items-baseline justify-between mb-3 flex-wrap gap-2">
        <div>
          <div className="text-[10px] uppercase tracking-[0.18em] text-ink-3 mb-0.5">
            오늘의 비중 제안 · 참고용
          </div>
          <h3 className="font-display text-base font-semibold text-ink-1 tracking-tight">
            일일 종합 보고서{" "}
            <span className="text-ink-3 font-normal tabular-nums text-[12px]">
              {daily.report_date} · 보관 {daily.kept_count}건
            </span>
          </h3>
        </div>
        <span
          className={cn(
            "inline-flex items-center px-2.5 py-1 rounded-md text-[11px] border font-medium",
            meta.tone,
          )}
        >
          {meta.label}
        </span>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-[1fr_1.4fr] gap-6">
        {/* LEFT — 비중 + 신뢰도 (수치 중심) */}
        <div className="flex flex-col gap-3">
          {/* 비중 행 */}
          <div className="flex items-baseline gap-5 tabular-nums">
            <div>
              <div className="text-[10px] uppercase tracking-wider text-ink-3 mb-1">Term</div>
              <div className="flex items-baseline gap-1.5">
                <span className="font-display text-3xl font-semibold text-ink-1">{newTerm}</span>
                <span className="text-[12px] text-ink-3">%</span>
                {termDelta !== "0" && (
                  <span className={cn(
                    "text-[12px] font-semibold ml-1.5",
                    termDelta.startsWith("+") ? "text-crisis-700" : "text-opportunity-700",
                  )}>
                    {termDelta}
                  </span>
                )}
              </div>
              <div className="text-[10px] text-ink-3 mt-0.5">기준 {baseTerm}%</div>
            </div>
            <div className="text-ink-3 text-[14px] self-center">·</div>
            <div>
              <div className="text-[10px] uppercase tracking-wider text-ink-3 mb-1">Spot</div>
              <div className="flex items-baseline gap-1.5">
                <span className="font-display text-3xl font-semibold text-ink-1">{newSpot}</span>
                <span className="text-[12px] text-ink-3">%</span>
                {spotDelta !== "0" && (
                  <span className={cn(
                    "text-[12px] font-semibold ml-1.5",
                    spotDelta.startsWith("+") ? "text-opportunity-700" : "text-crisis-700",
                  )}>
                    {spotDelta}
                  </span>
                )}
              </div>
              <div className="text-[10px] text-ink-3 mt-0.5">기준 {baseSpot}%</div>
            </div>
            {daily.confidence !== null && (
              <div className="ml-auto text-right">
                <div className="text-[10px] uppercase tracking-wider text-ink-3 mb-1">신뢰도</div>
                <div className="font-display text-3xl font-semibold text-ink-1 tabular-nums leading-none">
                  {Math.round(daily.confidence)}
                  <span className="text-[11px] text-ink-3 ml-1 font-normal">/100</span>
                </div>
              </div>
            )}
          </div>
          {rs.qualitative && (
            <p className="text-[12.5px] text-ink-2 leading-relaxed pt-3 border-t border-line-1">
              {rs.qualitative}
            </p>
          )}
          {rs.agent_bricks?.enabled && (
            <div className="flex items-center gap-1.5 text-[10px] text-info-700">
              <Network className="w-3 h-3" />
              <span className="uppercase tracking-wider font-medium">
                Agent Bricks 종합
              </span>
              <span className="text-ink-3 normal-case tracking-normal">
                {rs.agent_bricks.tools_used && rs.agent_bricks.tools_used.length > 0
                  ? rs.agent_bricks.tools_used.map((t) => t.name).join(" · ")
                  : "Supervisor 호출"}
              </span>
            </div>
          )}
        </div>

        {/* RIGHT — scenarios + reasoning (보조 정보) */}
        <div className="flex flex-col gap-3">
          {scenarios.length > 0 && (
            <div>
              <div className="text-[10px] uppercase tracking-wider text-ink-3 mb-1.5">
                시나리오별 예상 절감률
              </div>
              <div className="grid grid-cols-3 gap-2 tabular-nums">
                {scenarios.map((s) => (
                  <div
                    key={s.name}
                    className="rounded-md border border-line-1 bg-paper px-2.5 py-1.5"
                  >
                    <div className="text-[10px] text-ink-3 uppercase tracking-wider">
                      {s.name === "base" ? "기준" : s.name === "bull" ? "상승 시나리오" : s.name === "bear" ? "하락 시나리오" : s.name}
                    </div>
                    <div className={cn(
                      "font-display text-base font-semibold mt-0.5",
                      s.expected_saving_pct > 0 ? "text-opportunity-700"
                        : s.expected_saving_pct < 0 ? "text-crisis-700" : "text-ink-2",
                    )}>
                      {s.expected_saving_pct > 0 ? "+" : ""}{s.expected_saving_pct.toFixed(1)}%
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          {daily.reasoning && (
            <p className="text-[11.5px] text-ink-3 leading-relaxed line-clamp-3">
              {daily.reasoning}
            </p>
          )}
        </div>
      </div>
    </section>
  );
}
