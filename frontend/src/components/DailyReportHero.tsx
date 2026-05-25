/**
 * DailyReportHero — Dashboard 상단 (reports model 2026-05-21 Phase 6).
 *
 * 매일 06:30 KST cron이 생성한 daily_report 1건 표시.
 * 매일의 산출물은 "오늘의 조달 전술" — 즉시 실행 가능한 행동 + 위험 경보.
 * - 오늘의 전술 (Spot 타이밍 · 헤지) + 위험 경보 + 신뢰도 = 주인공
 * - 중기 포지셔닝 방향 (lean_hedge / neutral / lean_opportunity) 배지
 * - 표준 비중 (Term/Spot)은 분기 단위 전략값 — 참고로 작게 표시 (결재는 매니저)
 * - 시나리오 scenarios (base/bull/bear 예상 절감) + reasoning 1단락
 * - read-only — 액션 없음
 */
import { Network } from "lucide-react";
import { useDailyReportToday } from "../lib/queries";
import { cn } from "../lib/utils";
import { labelTool } from "./ChatMessage";

const DIRECTION_META: Record<
  string,
  { label: string; tone: string; alert: string; action: string }
> = {
  lean_hedge: {
    label: "중기 · 위험방어 쪽",
    tone: "text-crisis-700 bg-crisis-50 border-crisis-200",
    alert: "위험 경보",
    action: "현물 발주 보류 · 헤지 확대 검토",
  },
  neutral: {
    label: "중기 · 중립",
    tone: "text-ink-2 bg-line-1 border-line-2",
    alert: "안정 구간",
    action: "현 운영 유지 · 모니터링",
  },
  lean_opportunity: {
    label: "중기 · 기회포착 쪽",
    tone: "text-opportunity-700 bg-opportunity-50 border-opportunity-200",
    alert: "기회 구간",
    action: "현물 발주 앞당김 검토",
  },
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
          오늘의 조달 권고
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
  const tactical = rs.qualitative?.trim() || meta.action;
  const baseTerm = 60;
  const baseSpot = 40;
  const scenarios = rs.scenarios || [];

  return (
    <section className="bg-panel border border-line-1 rounded-2xl p-5">
      <header className="flex items-baseline justify-between mb-3 flex-wrap gap-2">
        <div>
          <div className="text-[10px] uppercase tracking-[0.18em] text-ink-3 mb-0.5">
            오늘의 조달 권고 · 참고용
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
        {/* LEFT — 오늘의 전술 + 위험 경보 (행동 중심) */}
        <div className="flex flex-col gap-3">
          {/* 오늘의 전술 */}
          <div>
            <div className="text-[10px] uppercase tracking-wider text-ink-3 mb-1.5">
              오늘의 전술
            </div>
            <p className="font-display text-xl font-semibold text-ink-1 leading-snug tracking-tight">
              {tactical}
            </p>
          </div>
          {/* 신뢰도 + 위험 경보 */}
          <div className="flex items-baseline gap-6 tabular-nums">
            {daily.confidence !== null && (
              <div>
                <div className="text-[10px] uppercase tracking-wider text-ink-3 mb-1">신뢰도</div>
                <div className="font-display text-3xl font-semibold text-ink-1 leading-none">
                  {Math.round(daily.confidence)}
                  <span className="text-[11px] text-ink-3 ml-1 font-normal">/100</span>
                </div>
              </div>
            )}
            <div>
              <div className="text-[10px] uppercase tracking-wider text-ink-3 mb-1">위험 경보</div>
              <div className={cn("font-display text-xl font-semibold leading-none mt-0.5", meta.tone.split(" ")[0])}>
                {meta.alert}
              </div>
            </div>
          </div>
          {/* 표준 비중 — 분기 단위 전략값 (참고) */}
          <div className="pt-3 border-t border-line-1">
            <div className="flex items-baseline justify-between">
              <div className="text-[10px] uppercase tracking-wider text-ink-3">표준 비중</div>
              <div className="text-[10px] text-ink-3">분기 검토 · 매니저 결재</div>
            </div>
            <div className="flex items-baseline gap-2 mt-1 tabular-nums text-ink-2">
              <span className="text-[13px]">
                Term <span className="font-semibold text-ink-1">{baseTerm}</span>%
              </span>
              <span className="text-ink-3">·</span>
              <span className="text-[13px]">
                Spot <span className="font-semibold text-ink-1">{baseSpot}</span>%
              </span>
            </div>
          </div>
          {rs.agent_bricks?.enabled && (
            <div className="flex items-center gap-1.5 text-[10px] text-info-700">
              <Network className="w-3 h-3" />
              <span className="uppercase tracking-wider font-medium">
                Agent Bricks 종합
              </span>
              <span className="text-ink-3 normal-case tracking-normal">
                {rs.agent_bricks.tools_used && rs.agent_bricks.tools_used.length > 0
                  ? Array.from(new Set(rs.agent_bricks.tools_used.map((t) => labelTool(t.name)))).join(" · ")
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
