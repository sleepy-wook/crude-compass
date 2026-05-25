/**
 * DailyReportDetail — Archive 페이지 내 일일 보고서 detail (2026-05-21).
 *
 * 표시:
 *   - 비중 (Term/Spot delta + 신뢰도)
 *   - direction chip + qualitative
 *   - scenarios 3개 (base/bull/bear)
 *   - kept_summary (어제 활성화 보고서 종합)
 *   - market_context
 *   - reasoning (판단 근거)
 *   - prev_daily_summary (어제 daily report)
 *   - kept_report_ids list → 클릭 시 트리거 보고서 탭으로 navigate
 */
import { ArrowRight, TrendingUp } from "lucide-react";
import { cn } from "../lib/utils";
import type { DailyReport } from "../lib/types";

interface Props {
  daily: DailyReport | undefined;
  isLoading: boolean;
  onSelectKeptReport?: (reportId: string) => void;
}

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

export function DailyReportDetail({ daily, isLoading, onSelectKeptReport }: Props) {
  if (isLoading) {
    return (
      <div className="bg-white border border-line-2 rounded-2xl p-8 flex items-center text-sm text-ink-3 h-[680px] shadow-sm">
        불러오는 중...
      </div>
    );
  }

  if (!daily) {
    return (
      <div className="bg-white border border-line-2 rounded-2xl p-6 h-[680px] flex flex-col justify-center shadow-sm">
        <div className="text-[11px] uppercase tracking-wider text-ink-3 mb-2">일일 보고서</div>
        <div className="text-base text-ink-1 mb-3">선택된 일일 보고서 없음</div>
        <p className="text-[13px] text-ink-3 leading-relaxed">
          좌측에서 날짜를 선택하세요. 매일 06:35 KST에 자동 생성됩니다.
        </p>
      </div>
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
    <div className="bg-white border border-line-2 rounded-2xl p-6 flex flex-col h-[680px] overflow-y-auto shadow-sm">
      {/* Header */}
      <div className="flex items-baseline justify-between mb-4 flex-wrap gap-2">
        <div>
          <div className="text-[10px] uppercase tracking-[0.18em] text-ink-3 mb-0.5">
            일일 종합 보고서 · 참고용
          </div>
          <h3 className="font-display text-[17px] font-semibold text-ink-1 tracking-tight">
            {daily.report_date}{" "}
            <span className="text-ink-3 font-normal tabular-nums text-[12px] ml-1">
              · 보관 {daily.kept_count}건
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
      </div>

      {/* 오늘의 전술 */}
      <div className="mb-4">
        <div className="text-[10px] uppercase tracking-wider text-ink-3 mb-1.5">오늘의 전술</div>
        <p className="font-display text-xl font-semibold text-ink-1 leading-snug tracking-tight">
          {tactical}
        </p>
      </div>

      {/* 신뢰도 + 위험 경보 + 표준 비중 */}
      <div className="flex items-baseline gap-6 mb-4 tabular-nums">
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
        <div className="ml-auto text-right">
          <div className="text-[10px] uppercase tracking-wider text-ink-3 mb-1">표준 비중 · 분기</div>
          <div className="text-[13px] text-ink-2 tabular-nums">
            Term <span className="font-semibold text-ink-1">{baseTerm}</span>% · Spot{" "}
            <span className="font-semibold text-ink-1">{baseSpot}</span>%
          </div>
        </div>
      </div>

      {/* scenarios */}
      {scenarios.length > 0 && (
        <div className="mb-4">
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

      {/* kept_summary */}
      {daily.kept_summary && (
        <div className="mb-3 border-t border-line-1 pt-3">
          <div className="text-[10px] uppercase tracking-wider text-ink-3 mb-1">
            어제 활성화 보고서 종합
          </div>
          <p className="text-[12.5px] text-ink-2 leading-relaxed">{daily.kept_summary}</p>
        </div>
      )}

      {/* market_context */}
      {daily.market_context && (
        <div className="mb-3">
          <div className="text-[10px] uppercase tracking-wider text-ink-3 mb-1">
            시장 컨텍스트
          </div>
          <p className="text-[12.5px] text-ink-2 leading-relaxed">{daily.market_context}</p>
        </div>
      )}

      {/* reasoning */}
      {daily.reasoning && (
        <div className="mb-3">
          <div className="text-[10px] uppercase tracking-wider text-ink-3 mb-1">
            판단 근거
          </div>
          <p className="text-[12.5px] text-ink-2 leading-relaxed">{daily.reasoning}</p>
        </div>
      )}

      {/* prev_daily_summary */}
      {daily.prev_daily_summary && (
        <div className="mb-3">
          <div className="text-[10px] uppercase tracking-wider text-ink-3 mb-1">
            이전 일일 보고서 요약
          </div>
          <p className="text-[11.5px] text-ink-3 leading-relaxed italic">{daily.prev_daily_summary}</p>
        </div>
      )}

      {/* kept reports list — clickable */}
      {daily.kept_report_ids.length > 0 && (
        <div className="mt-auto pt-4 border-t border-line-1">
          <div className="text-[10px] uppercase tracking-wider text-ink-3 mb-2 inline-flex items-center gap-1.5">
            <TrendingUp className="w-3 h-3" />
            input으로 사용된 트리거 보고서 ({daily.kept_report_ids.length})
          </div>
          <div className="flex flex-wrap gap-1.5">
            {daily.kept_report_ids.map((id) => (
              <button
                key={id}
                type="button"
                onClick={() => onSelectKeptReport?.(id)}
                disabled={!onSelectKeptReport}
                className={cn(
                  "inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10.5px] border transition-colors tabular-nums",
                  onSelectKeptReport
                    ? "border-line-2 bg-white text-ink-2 hover:bg-line-1 hover:text-ink-1"
                    : "border-line-2 bg-white text-ink-3 cursor-default",
                )}
              >
                #{id.slice(0, 6)}
                {onSelectKeptReport && <ArrowRight className="w-2.5 h-2.5" />}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
